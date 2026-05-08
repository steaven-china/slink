# sli ml — 技术选型文档

## 1. 配置文件格式

### 1.1 group_file（分组定义）

| 候选 | 评价 | 结论 |
|------|------|------|
| **YAML** | 缩进列表直观，原生支持注释，人类编辑友好，嵌套结构自然 | ✅ 选用 |
| TOML | 明确无歧义，但深层列表/嵌套分组语法冗长，Python 3.10 读写均需第三方库 | ❌ 放弃 |
| JSON | 不支持注释， trailing comma 敏感，不适合人类频繁编辑 | ❌ 放弃 |
| 纯文本 | 最简单，但无法表达嵌套、注释、元数据 | ❌ 放弃 |

**依赖**：`PyYAML>=6.0`（加入 `requirements.txt`）

**文件位置**：`~/.slink/groups.yml`

**兼容策略**：Python 3.10+ 均支持 PyYAML，无版本问题。

### 1.2 workspace_file（会话快照）

| 候选 | 评价 | 结论 |
|------|------|------|
| **JSON** | 标准库原生支持，机器生成/读取无外部依赖，结构清晰 | ✅ 选用 |
| YAML | 可以写注释，但 workspace 是机器生成的快照，人类不常编辑 | ❌ 过度设计 |

**文件位置**：`~/.slink/workspaces/<name>.json`

**兼容策略**：`json` 模块自 Python 2.6 起稳定，无兼容问题。

---

## 2. 依赖选型

| 依赖 | 用途 | 版本要求 |
|------|------|---------|
| `click>=8.0.0` | CLI 框架 | 已存在 |
| `cryptography>=41.0.0` | 加密存储 | 已存在 |
| `PyYAML>=6.0` | group_file 解析 | **新增** |

**不引入的依赖**：
- `toml` / `tomli` / `tomli-w`：TOML 方案已放弃
- `jsonschema`：workspace 结构简单，用 `TypedDict` + 手动校验足够，不引入重型验证框架
- `paramiko`：sli ml 底层仍复用系统 `ssh` 子进程，不引入纯 Python SSH 库（保持与现有 `ssh_wrapper.py` 一致，减少证书/密钥/主机密钥管理复杂度）

---

## 3. 文件系统布局

```
~/.slink/
├── hosts.enc              # 加密主机库（已有）
├── salt                   # PBKDF2 盐（已有）
├── .show_direct           # 明文索引（已有）
├── groups.yml             # 分组定义（新增）
├── workspaces/            # 工作区快照目录（新增）
│   ├── prod-debug.json
│   └── emergency.json
└── ml-logs/               # 审计日志目录（新增）
    └── 2026-05-08.log
```

**权限**：
- `groups.yml`：`0o600`（含主机名信息，虽非机密但遵循最小权限）
- `workspaces/` 下文件：`0o600`
- `ml-logs/` 下文件：`0o600`

---

## 4. PTY / 多会话实现方式

| 方案 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| **系统 `ssh` + PTY** | 复用现有 `ssh_wrapper.py`，无需管理密钥/主机密钥/加密算法 | 每个会话一个子进程，进程管理稍复杂 | ✅ 选用 |
| `paramiko` 纯 Python | 单进程，完全可控 | 需自行处理密钥、主机密钥、跳板机、代理等，与现有架构割裂 | ❌ 放弃 |
| `asyncssh` | 异步原生，性能高 | 引入额外大依赖，API 学习成本高 | ❌ 放弃 |

**实现细节**：
- 每个会话 = 一个 `subprocess.Popen(..., stdin=PIPE, stdout=PIPE, stderr=STDOUT)`
- 使用 `pexpect` 风格的 PTY 分配：在 `ssh` 命令中加 `-t -t` 强制分配伪终端
- 单线程 `select.select` 轮询所有会话 stdout + 用户 stdin

---

## 5. 输入处理模式

| 模式 | 触发方式 | 适用场景 |
|------|---------|---------|
| **Broadcast** | 默认 | 向所有未 block 的会话发送命令 |
| **Focus** | `focus <host>` | 仅与单个会话交互，其余自动 block |
| **Command** | 以 `>` 开头 | sli ml 内部命令（block/unblock/list/save/exit） |

**输入缓冲策略**：
- 行缓冲：用户按 Enter 后整行分发（默认）
- 特殊程序检测：若某会话正在运行 `vim`/`top`/`sudo` 等，自动切换为**字符模式**（逐字符转发），退出后恢复行缓冲

---

## 6. 安全与审计

- **危险命令列表**：`rm -rf`, `dd`, `mkfs.*`, `reboot`, `shutdown`, `init 0`, `>:`（重定向覆盖）
- **确认机制**：危险命令命中时，先显示影响范围（"Affects N hosts"），要求输入 `yes`
- **审计日志**：每个 `sli ml` 会话写独立日志，格式为纯文本，方便 `grep`/`awk` 分析
- **环境隔离**：`SLINK_USER` 继续生效，分组与工作区均隔离在用户目录下
