# slink - Agent Development Guide

## 项目概述

`slink` 是一个轻量级的 SSH 连接管理工具，使用 Python 编写。它将 SSH 连接信息加密存储在本地，支持通过命令行或简单的 GUI 快速连接远程主机，无需记住 IP 地址和用户名。

主要特性：
- 使用 Fernet（AES-128-CBC + HMAC）加密存储连接信息
- 主密码通过 PBKDF2-HMAC-SHA256（480,000 次迭代）派生加密密钥
- 支持私钥文件路径或直接粘贴私钥内容
- 支持从 `~/.ssh/config` 导入已有配置
- 支持单文件明文/加密配置的直接连接
- 提供 CLI 和基于 tkinter 的简易 GUI 两种交互方式

## 技术栈

- **语言**：Python >= 3.8
- **核心依赖**：
  - `click` >= 8.0.0（命令行接口）
  - `cryptography` >= 41.0.0（加密/解密）
- **GUI 框架**：Python 标准库 `tkinter`
- **打包工具**：Nuitka（用于编译独立可执行文件）
- **构建配置**：`setup.py`（setuptools），`PKGBUILD`（Arch Linux 包）

## 项目结构

```
.
├── slink.py              # 直接运行入口（将本地包加入 sys.path 后调用 cli.main）
├── slink.bat             # Windows 快捷启动脚本
├── setup.py              # setuptools 配置，定义入口点 slink / slink-ui
├── requirements.txt      # 运行时依赖
├── PKGBUILD              # Arch Linux 打包脚本（使用 Nuitka 编译单文件二进制）
├── README.md             # 用户文档（中文）
├── .gitignore
└── slink/                # 核心包
    ├── __init__.py       # 版本号 0.1.0
    ├── cli.py            # Click 命令行接口（主入口）
    ├── gui.py            # tkinter GUI（slink-ui 入口）
    ├── crypto.py         # 加密/解密、密钥派生、文件读写
    ├── store.py          # 基于加密文件的主机存储层（增删改查）
    ├── parser.py         # 明文配置文件解析器（支持多行块）
    ├── ssh_config_parser.py  # ~/.ssh/config 解析器
    ├── ssh_wrapper.py    # 调用系统 ssh 命令的包装器
    └── lock.py           # 跨平台文件锁（Windows msvcrt / Unix fcntl）
```

## 模块职责

| 模块 | 说明 |
|------|------|
| `cli.py` | 提供所有子命令（`init`, `add`, `list`, `show`, `rm`, `connect`, `edit`, `import`, `encrypt`, `decrypt`, `names`）。支持通过 `SLINK_PASSWORD` 环境变量免交互输入主密码。支持 shell 补全（从 `.show_direct` 读取主机名）。支持“快速连接”：当第一个非选项参数是文件路径时，直接解析并连接。 |
| `gui.py` | 提供基于 `tkinter` 的图形界面，包含密码对话框、主机增删改查对话框、主机列表和详情展示。连接操作在独立线程中执行，避免阻塞 UI。 |
| `crypto.py` | 所有加密逻辑。使用 `cryptography.fernet.Fernet` 进行对称加密，PBKDF2HMAC（SHA256，480,000 轮）从主密码派生 32 字节密钥。数据存储在 `~/.slink/hosts.enc`，盐值存储在 `~/.slink/salt`。提供原子写入和安全的文件权限设置。 |
| `store.py` | 在 `crypto.py` 之上封装主机字典的 CRUD 操作。所有操作均通过 `FileLock` 加锁，并在每次修改后更新 `~/.slink/.show_direct`（用于 shell 补全的无密码主机名列表）。 |
| `parser.py` | 解析自定义明文配置文件（`key: value` 格式，支持 `#` 注释、多行块 `|` / `|end`）。`dump_config` 可将字典序列化为该格式。 |
| `ssh_config_parser.py` | 解析 OpenSSH 风格的 `~/.ssh/config` 文件，提取 `Host`、`Hostname`、`User`、`Port`、`IdentityFile` 等字段，跳过通配符主机名。 |
| `ssh_wrapper.py` | 根据主机信息构建并执行系统 `ssh` 命令。如果提供了内联私钥（`key` 字段），会写入临时文件并在连接后自动删除。如果安装了 `sshpass`，可支持密码自动填充（通过 `SSHPASS` 环境变量）。 |
| `lock.py` | 跨平台咨询文件锁。Windows 使用 `msvcrt.locking`，Unix/Linux/macOS 使用 `fcntl.flock`。 |

## 运行时数据文件

所有运行时数据位于用户主目录下的 `~/.slink/` 中：

| 文件 | 说明 |
|------|------|
| `hosts.enc` | 加密后的 JSON 数据库（存储所有主机配置） |
| `salt` | 16 字节随机盐，用于 PBKDF2 密钥派生 |
| `.show_direct` | 明文主机名列表，供 shell 补全使用（无需密码即可读取） |
| `.lock` | 咨询锁文件，用于多进程并发保护 |

在 Unix 系统上，`hosts.enc` 和 `salt` 的权限会被设置为 `0o600`（仅所有者可读写）。Windows 上则设置为只读。

## 构建与运行

### 开发环境安装

```bash
pip install -r requirements.txt
# 或
python setup.py install
```

### 运行方式

- **CLI**：`python slink.py <command>` 或安装后直接使用 `slink <command>`
- **GUI**：安装后使用 `slink-ui`
- **Windows**：可直接双击 `slink.bat`，或在命令行运行

### 编译独立二进制

项目使用 Nuitka 编译为单文件可执行文件，参考 `PKGBUILD` 中的命令：

```bash
python -m nuitka \
    --onefile \
    --standalone \
    --remove-output \
    --disable-plugin=pkg-resources \
    --include-package=click \
    --include-package=cryptography \
    --output-filename=slink \
    slink.py
```

## 主要命令

| 命令 | 作用 |
|------|------|
| `slink init` | 初始化主密码 |
| `slink add <name> -h <host> -u <user>` | 添加主机 |
| `slink list` | 列出所有主机 |
| `slink show <name>` | 查看主机详情 |
| `slink connect <name>` | 通过 SSH 连接主机 |
| `slink edit <name>` | 编辑主机 |
| `slink rm <name>` | 删除主机 |
| `slink import` | 从 `~/.ssh/config` 导入 |
| `slink encrypt <file>` | 加密明文配置文件 |
| `slink decrypt <file.enc>` | 解密配置文件 |

## 代码风格与开发约定

- 项目注释和文档以**中文**为主。
- 字符串格式化使用 f-string。
- 模块级常量使用全大写 + 下划线命名（如 `DEFAULT_CONFIG_DIR`, `SALT_FILE`）。
- 私有函数以下划线开头（如 `_derive_key`, `_write_temp_key`）。
- 使用 `click.echo(..., err=True)` 向 stderr 输出错误信息。
- 跨平台兼容通过 `sys.platform == "win32"` 进行分支处理。
- 临时文件和敏感文件在使用后必须清理（`ssh_wrapper.py` 中的 `finally` 块、`crypto.py` 中的原子写入异常清理）。

## 测试

**当前项目中未包含自动化测试。** 如需添加测试，建议在项目根目录创建 `tests/` 目录，并使用 `pytest` 进行单元测试。需要重点测试的模块：
- `parser.py`：各种格式的明文配置文件解析
- `crypto.py`：加密/解密、错误密码处理、盐值生成
- `store.py`：并发文件锁下的增删改查
- `ssh_config_parser.py`：不同风格的 SSH config 解析

## 安全注意事项

- **主密码从不存储在磁盘上**，仅用于实时派生加密密钥。用户可通过 `SLINK_PASSWORD` 环境变量传入，但在共享环境中存在风险。
- **盐值随机生成**，每个安装实例独立，防止彩虹表攻击。
- **临时私钥文件**在连接结束后会被立即删除；Windows 上需要先解除只读权限再删除。
- **原子写入**：`save_hosts` 先写入临时文件，再通过 `os.replace` 覆盖原文件，避免写入过程中数据损坏。
- 加密后的 `.enc` 配置文件可安全复制到其他机器，只要对方知道主密码即可使用。
