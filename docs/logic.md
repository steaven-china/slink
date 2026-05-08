# sli ml — 逻辑设计文档

## 1. 数据模型

### 1.1 Group（分组）

```python
from typing import TypedDict

class GroupDef(TypedDict):
    hosts: list[str]          # 直接主机名
    groups: list[str]         # 嵌套引用的其他分组（以 @ 或裸名标识）
```

**内存结构**：
```python
groups: dict[str, GroupDef] = {
    "web": {"hosts": ["web1", "web2", "web3"], "groups": []},
    "db":  {"hosts": ["db-master", "db-slave"], "groups": []},
    "prod": {"hosts": [], "groups": ["web", "db"]},
}
```

### 1.2 Workspace（工作区）

```python
class Workspace(TypedDict):
    name: str
    hosts: list[str]
    blocked: list[str]
    focused: str | None
    mode: str           # "broadcast" | "focus"
    created_at: str     # ISO 8601
```

### 1.3 Session（运行时会话）

```python
class Session:
    name: str
    proc: subprocess.Popen   # ssh 子进程
    blocked: bool            # 是否被屏蔽
    online: bool             # 是否在线
    last_cmd: str | None     # 最后执行的命令
    in_raw_mode: bool        # 是否处于字符模式（vim/top/sudo）
```

---

## 2. 核心算法

### 2.1 Group 展开算法（resolve_group）

**输入**：`group_name`, `groups_dict`, `resolved=set()`  
**输出**：展开后的有序主机列表（去重，保持首次出现顺序）

```
function resolve_group(name, groups, resolved):
    if name in resolved:
        raise CircularReferenceError(name)
    resolved.add(name)

    group = groups.get(name)
    if not group:
        raise GroupNotFoundError(name)

    result = []
    for host in group["hosts"]:
        if host not in result:
            result.append(host)

    for sub_name in group["groups"]:
        # 去除可能的 @ 前缀
        sub_name = sub_name.lstrip("@")
        for h in resolve_group(sub_name, groups, resolved.copy()):
            if h not in result:
                result.append(h)

    return result
```

**复杂度**：O(N) 其中 N 为最终主机数，因为 `resolved` 集合防止重复展开。

### 2.2 Host 列表解析（parse_ml_targets）

**输入**：`["srv1", "@web", "srv2", "@prod"]`  
**输出**：`["srv1", "web1", "web2", "web3", "srv2", "web1", "web2", "web3", "db-master", "db-slave"]`（去重）

```
function parse_ml_targets(targets, groups, all_hosts):
    result = []
    for t in targets:
        if t.startswith("@"):
            for h in resolve_group(t[1:], groups):
                if h not in result:
                    result.append(h)
        else:
            # 校验主机是否存在于 hosts.enc
            if t not in all_hosts:
                raise HostNotFoundError(t)
            if t not in result:
                result.append(t)
    return result
```

### 2.3 输入分发（dispatch_input）

**主循环**：
```
readable, _, _ = select.select([sys.stdin] + session_fds, [], [], 0.05)

for fd in readable:
    if fd is sys.stdin:
        line = read_line_nonblock()
        if line.startswith(">"):
            handle_internal_command(line)
        else:
            dispatch_to_sessions(line)
    else:
        session = find_session_by_fd(fd)
        output = os.read(fd, 4096).decode("utf-8", errors="replace")
        display_output(session, output)
```

**dispatch_to_sessions**：
```
function dispatch_to_sessions(line):
    if current_mode == "focus" and focused_session:
        if focused_session.online and not focused_session.blocked:
            send(focused_session, line)
        return

    for s in sessions:
        if s.online and not s.blocked:
            send(s, line)
```

### 2.4 Raw 模式检测

通过会话输出流检测提示符变化或已知交互程序特征：

```python
RAW_MODE_TRIGGERS = [
    r"^\s*--\s*INSERT\s*--",       # vim
    r"^\s*:\s*$",                   # vim command mode
    r"^\s*\[sudo\]",                # sudo password
    r"^\s*Password:\s*$",           # generic password prompt
]

def detect_raw_mode(output: str) -> bool:
    for pattern in RAW_MODE_TRIGGERS:
        if re.search(pattern, output, re.IGNORECASE):
            return True
    return False
```

进入 raw 模式后，stdin 逐字符转发到该会话，其他会话不受影响。当检测到退出特征（如 vim 的 `:!q` 或提示符恢复）时退出 raw 模式。

---

## 3. 状态机

### 3.1 sli ml 会话状态机

```
[INIT] --连接成功--> [BROADCAST]
[BROADCAST] --focus host--> [FOCUS]
[FOCUS] --broadcast--> [BROADCAST]
[BROADCAST] --block all--> [SILENT]
[FOCUS] --block focused--> [SILENT]
[SILENT] --unblock--> [BROADCAST]
[Any] --exit--> [CLEANUP]
```

### 3.2 Session 个体状态

```
[CONNECTING] --ssh 成功--> [ONLINE]
[ONLINE] --block--> [BLOCKED]
[BLOCKED] --unblock--> [ONLINE]
[ONLINE] --断开--> [OFFLINE]
[BLOCKED] --断开--> [OFFLINE]
[OFFLINE] --reconnect（如启用）--> [CONNECTING]
```

---

## 4. 命令路由

### 4.1 内部命令解析器

```python
INTERNAL_COMMANDS = {
    "block": cmd_block,
    "b": cmd_block,
    "unblock": cmd_unblock,
    "ub": cmd_unblock,
    "list": cmd_list,
    "ls": cmd_list,
    "focus": cmd_focus,
    "f": cmd_focus,
    "broadcast": cmd_broadcast,
    "bc": cmd_broadcast,
    "status": cmd_status,
    "st": cmd_status,
    "save": cmd_save_workspace,
    "exit": cmd_exit,
    "quit": cmd_exit,
}

def handle_internal_command(raw: str):
    parts = raw[1:].strip().split()  # 去掉前缀 >
    if not parts:
        return
    cmd, args = parts[0], parts[1:]
    handler = INTERNAL_COMMANDS.get(cmd)
    if not handler:
        print(f"Unknown command: {cmd}")
        return
    handler(args)
```

### 4.2 危险命令拦截器

```python
DANGEROUS_PATTERNS = [
    re.compile(r"rm\s+(-[rf]*\s+)+(/\S*)"),
    re.compile(r"\bdd\b"),
    re.compile(r"\bmkfs\."),
    re.compile(r"\breboot\b"),
    re.compile(r"\bshutdown\b"),
    re.compile(r"init\s+0"),
    re.compile(r">\s*\S+"),  # 重定向覆盖
]

def check_dangerous(cmd_line: str) -> tuple[bool, int]:
    """返回 (是否危险, 影响主机数)"""
    for pattern in DANGEROUS_PATTERNS:
        if pattern.search(cmd_line):
            affected = sum(1 for s in sessions if s.online and not s.blocked)
            return True, affected
    return False, 0
```

---

## 5. 文件 IO 流程

### 5.1 groups.yml 加载

```
[CLI 启动]
  └── load_groups()
        ├── 路径: ~/.slink/groups.yml
        ├── 不存在 → 返回空 dict
        ├── 存在 → yaml.safe_load()
        └── 校验: 循环引用检测（在 resolve_group 时 lazy 检测）
```

### 5.2 workspace 保存

```
[用户输入 >save emergency]
  └── cmd_save_workspace(args)
        ├── 构造 Workspace dict
        ├── 路径: ~/.slink/workspaces/emergency.json
        ├── json.dump(indent=2)
        └── 权限: 0o600
```

### 5.3 workspace 加载

```
[CLI 启动带 --workspace emergency]
  └── load_workspace("emergency")
        ├── 路径: ~/.slink/workspaces/emergency.json
        ├── 不存在 → 报错
        ├── 存在 → json.load()
        ├── 校验 hosts 是否存在于当前 hosts.enc
        └── 恢复会话: 依次 connect(host)
```

---

## 6. 错误处理策略

| 错误场景 | 行为 |
|---------|------|
| 分组不存在 | 启动前报错，不进入 ml 模式 |
| 主机不存在 | 启动前报错，列出缺失的主机 |
| 分组循环引用 | 启动前报错，列出循环链 |
| SSH 连接失败 | 标记该会话 OFFLINE，继续对其他会话广播（除非 `--strict`） |
| 危险命令 | 二次确认，用户输入 `yes` 才执行 |
| workspace 损坏/不兼容 | 报错并建议重新保存 |
| 保存 workspace 时名称冲突 | 询问是否覆盖 |

---

## 7. 与现有代码的集成点

| 现有模块 | 集成方式 |
|---------|---------|
| `slink/crypto.py` | `load_hosts(password)` 读取主机库用于校验 |
| `slink/store.py` | `get_host(name, password)` 获取单主机配置（SSH 参数） |
| `slink/ssh_wrapper.py` | 复用 `connect()` 的逻辑构建 `ssh` 命令，但改用 `Popen` 而非 `call` |
| `slink/cli.py` | 新增 `ml` Click 命令，注册内部命令补全 |
| `slink/gui.py` | 远期：GUI 新增 "Multi-Login" 按钮，打开独立窗口 |
