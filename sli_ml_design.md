# sli ml — 交互式多会话控制

## 简介

`sli ml`（multi-login）是 slink 的多会话控制模式。它允许你同时连接到多台服务器，在一个统一的交互界面中向它们发送命令，并实时查看所有会话的输出。

这不是批量执行工具（如 Ansible），而是为**交互式探索、快速排查、即时干预**设计的操作终端。

## 核心概念

- **会话（Session）**：一台已连接的 SSH 主机
- **广播（Broadcast）**：你的输入同时发送到所有**未屏蔽**的会话
- **屏蔽（Block）**：临时将某个会话从广播中排除，它不再接收你的命令
- **前缀回显**：每个会话的输出前自动标注来源主机，避免混淆

## 快速开始

```bash
# 同时连接 3 台服务器
$ sli ml srv1 srv2 srv3

Enter master password:
[Connected to srv1] root@web-prod:~#
[Connected to srv2] root@db-master:~#
[Connected to srv3] root@cache-node:~#

> ls -la
[← srv1] drwxr-xr-x  4 root root 4096 May  8 14:00 .
[← srv2] drwxr-xr-x  5 root root 4096 May  8 13:55 .
[← srv3] drwxr-xr-x  3 root root 4096 May  8 14:02 .

> block srv2
[⚡ srv2 blocked]

> apt update
[← srv1] Hit:1 http://archive.ubuntu.com/ubuntu jammy InRelease
[← srv3] Hit:1 http://archive.ubuntu.com/ubuntu jammy InRelease

> unblock srv2
[⚡ srv2 resumed]

> exit
[Disconnected from srv1]
[Disconnected from srv2]
[Disconnected from srv3]
```

## 命令格式

```
sli ml [OPTIONS] <host...>
```

### 参数

| 参数 | 说明 |
|------|------|
| `host...` | 一个或多个主机名/别名（至少一个） |

### 选项

| 选项 | 说明 |
|------|------|
| `-u, --user` | 指定连接用户名（覆盖配置） |
| `-p, --port` | 指定端口 |
| `--dry-run` | 模拟连接，不实际建立 SSH 会话 |
| `--workspace <name>` | 加载指定工作区 |
| `--save <name>` | 保存当前会话为工作区 |

## 分组文件（group_file）

在 `~/.slink/groups.yml` 中定义主机分组，支持 `@group` 语法快速引用：

```yaml
# ~/.slink/groups.yml
web:
  - web1
  - web2
  - web3
db:
  - db-master
  - db-slave
cache:
  - redis1
  - redis2
```

使用：

```bash
# 引用整组
$ sli ml @web

# 混合引用：组 + 独立主机
$ sli ml @web @db backup-node

# 查看所有分组
$ sli ml --list-groups
```

分组支持嵌套（组中包含其他组）：

```yaml
prod:
  - "@web"
  - "@db"
  - "@cache"
```

## 工作区文件（workspace_file）

工作区保存一次 `sli ml` 会话的完整状态，方便快速恢复排查现场。

**存储位置**：`~/.slink/workspaces/<name>.json`

**格式示例**：

```json
{
  "name": "prod-debug",
  "hosts": ["web1", "web2", "db-master"],
  "blocked": ["db-master"],
  "focused": null,
  "mode": "broadcast",
  "created_at": "2026-05-08T14:00:00Z"
}
```

**使用**：

```bash
# 加载工作区
$ sli ml --workspace prod-debug

# 保存当前会话为新工作区
> save emergency
[⚡ Workspace 'emergency' saved]

# 列出所有工作区
$ sli ml --list-workspaces
```

**自动加载**：如果在当前目录存在 `.sli-workspace.json`，`sli ml` 不带参数时自动加载。

## 交互命令

进入 `sli ml` 模式后，可以使用以下内部命令：

| 命令 | 缩写 | 说明 |
|------|------|------|
| `block <host>` | `b` | 屏蔽指定会话，不再接收广播 |
| `unblock <host>` | `ub` | 恢复指定会话的广播接收 |
| `block all` | | 屏蔽所有会话 |
| `unblock all` | | 恢复所有会话 |
| `list` | `ls` | 显示所有会话状态（在线/屏蔽/离线） |
| `focus <host>` | `f` | 仅与指定会话交互，其他会话自动屏蔽 |
| `broadcast` | `bc` | 恢复全局广播模式（退出 focus） |
| `status` | `st` | 显示各会话最后执行命令的摘要 |
| `exit` | `quit` | 退出 ml 模式，断开所有会话 |

> **注意**：以 `>` 开头的命令被识别为 sli ml 内部命令。如果要向远程发送以 `>` 开头的文字，使用 `\>` 转义。

## 输出格式

### 默认模式（带前缀）

```
[← srv1] Last login: Fri May 8 14:00:00 2026
[← srv1] root@web-prod:~# ls
[← srv1] app  logs  nginx.conf
```

### 紧凑模式

通过 `--compact` 启动，仅显示不同主机的输出差异：

```bash
$ sli ml --compact srv1 srv2 srv3
```

在紧凑模式下，相同输出只打印一次，标注 `[*]` 表示多机一致；差异部分单独列出并标注来源。

### 分屏模式（实验性）

与 tmux 集成时，可使用 `--tmux` 启动，每个会话独占一个窗格：

```bash
$ sli ml --tmux srv1 srv2 srv3
```

此时 sli 仅负责连接管理，tmux 负责窗格布局与输入同步。使用 tmux 原生的 `prefix :setw synchronize-panes` 控制广播。

## 使用场景

### 场景一：快速排查集群故障

3 台 Web 服务器响应异常，需要同时检查负载：

```bash
$ sli ml web1 web2 web3
> top
[← web1] %Cpu(s): 95.2 us,  4.1 sy...
[← web2] %Cpu(s): 12.3 us,  3.1 sy...
[← web3] %Cpu(s): 98.7 us,  1.2 sy...

> block web2  # web2 正常，不干扰
> kill -9 2847
[← web1] (killed)
[← web3] (killed)
```

### 场景二：配置分发与验证

向新集群推送 nginx 配置并验证语法：

```bash
$ sli ml node1 node2 node3
> nginx -t
[← node1] syntax is ok
[← node2] syntax is ok
[← node3] syntax is ok

> systemctl reload nginx
[← node1] Done
[← node2] Done
[← node3] Done
```

### 场景三：滚动更新（逐步操作）

逐台重启服务，避免同时中断：

```bash
$ sli ml api1 api2 api3 api4
> block api2 api3 api4  # 只操作 api1
> systemctl restart myapp
[← api1] (restarted)

> unblock api1
> block api1 api3 api4  # 切换到 api2
> systemctl restart myapp
[← api2] (restarted)

# 继续...
```

## 安全机制

### 危险命令确认

对于可能造成破坏的命令（`rm -rf`, `dd`, `mkfs`, `reboot` 等），sli ml 会自动要求二次确认：

```
> rm -rf /opt/data
⚠️  Dangerous command detected. Affects 3 hosts.
Type 'yes' to proceed, or 'block <host>' to exclude: 
```

可通过 `--no-confirm` 关闭（不推荐）。

### 离线会话处理

如果某个会话意外断开：
- 默认：会话标记为 `[OFFLINE]`，继续对其他会话广播
- `--strict` 模式：任何会话断开时暂停广播，等待用户处理

### 审计日志

启用 `--log` 后，所有交互记录写入 `~/.slink/ml-YYYY-MM-DD.log`：

```
[2026-05-08 14:32:01] ml start: srv1 srv2 srv3
[2026-05-08 14:32:15] broadcast: ls -la
[2026-05-08 14:32:18] output: srv1: total 128
[2026-05-08 14:32:18] output: srv2: total 64
[2026-05-08 14:32:19] block: srv2
[2026-05-08 14:32:22] broadcast: apt update
[2026-05-08 14:35:10] ml end
```

## 与现有方案的区别

| 方案 | 类型 | 交互性 | 实时反馈 | 会话控制 | 适用场景 |
|------|------|--------|---------|---------|---------|
| **sli ml** | 轻量 CLI | 实时交互 | 即时回显 | block/unblock/focus | 排查、验证、小规模变更 |
| pssh / parallel-ssh | 批量工具 | 非交互 | 汇总后输出 | 无 | 批量命令执行 |
| Ansible | 配置管理 | 剧本驱动 | 按 task 回显 | 主机清单控制 | 结构化部署、大规模变更 |
| tmux synchronize-panes | 终端复用 | 实时交互 | 即时回显 | 窗格选择 | 手动操作、需 tmux 环境 |
| Termius 多窗口 | GUI 客户端 | 实时交互 | 多标签 | 手动切换 | 可视化操作 |

sli ml 的定位：**比 pssh 更交互，比 Ansible 更轻量，比 tmux 更智能**。

## 技术实现要点

- **PTY 分配**：每个会话维护独立的伪终端，支持 sudo、vim 等交互程序
- **select/poll 驱动**：单线程监听多个 socket，避免多进程开销
- **信号隔离**：某会话崩溃/断开时，通过异常捕获隔离，不影响其他会话
- **输入缓冲**：用户输入暂存，逐字符/逐行分发到各活跃会话

## 未来扩展

- [x] `group_file` + `workspace_file`：主机分组与会话快照
- [ ] `sli ml --from <json>`：从一次性 JSON 文件读取主机列表（不写入工作区）
- [ ] `sli ml --record`：录制会话，支持后续回放或生成 Ansible playbook
- [ ] `sli ml --diff`：对比各会话输出差异，高亮不一致项
- [ ] 集成 `sli ml` 到 CTF 靶场自动化：批量分发 `team-x.enc` 并进入多控模式

## 结语

`sli ml` 不是企业级运维平台，而是开发者手边的一个**快速反应工具**。当你面对多台服务器，不想写 playbook、不想开五个终端标签、不想手动复制粘贴时，它让你用一行命令进入统一控制台，指哪打哪，错了立刻 block。

**一行命令，多机在手。**

---

**注意**：`sli ml` 处于设计阶段，API 与交互细节可能调整。欢迎通过 issue 提交使用场景与改进建议。
