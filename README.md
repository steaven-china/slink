# slink - Secure SSH Connection Manager

一个轻量级的 SSH 连接管理工具，将连接信息加密存储在本地，支持通过命令行快速连接远程主机。

## 特性

- **加密存储**：使用 AES-128-CBC + HMAC（Fernet）加密，密钥通过 PBKDF2-HMAC-SHA256 从主密码派生
- **密码保护**：支持主密码保护所有连接信息
- **密钥管理**：支持私钥文件路径或直接粘贴私钥内容
- **简单连接**：一条命令即可连接，无需记住 IP 和用户名

## 安装

```bash
pip install -r requirements.txt
# 或直接安装
python setup.py install
```

Windows 用户也可以直接使用 `slink.bat` 或 `python slink.py`。

## 使用

### 1. 初始化

首次使用需要设置主密码：

```bash
slink init
```

### 2. 添加主机

交互式添加：

```bash
slink add myserver -h 192.168.1.100 -u root
```

使用私钥文件：

```bash
slink add myserver -h 192.168.1.100 -u root -i ~/.ssh/id_rsa
```

直接粘贴私钥内容（适合没有本地密钥文件的场景）：

```bash
slink add myserver -h 192.168.1.100 -u root --key-text "-----BEGIN OPENSSH PRIVATE KEY-----
..."
```

### 3. 列出所有主机

```bash
slink list
```

### 4. 查看主机详情

```bash
slink show myserver
```

### 5. 连接主机

```bash
slink connect myserver
```

这会调用系统自带的 `ssh` 命令，所以你完全保留正常的 Shell 体验（补全、历史记录、SSH Agent 转发等）。

### 6. 编辑主机

```bash
slink edit myserver -h new.ip.address -u newuser
```

### 7. 删除主机

```bash
slink rm myserver
```

### 8. 从 SSH Config 导入

如果你已经有很多主机配在 `~/.ssh/config` 里：

```bash
# 导入全部
slink import

# 导入单个主机
slink import -h myserver

# 从指定文件导入
slink import -c /path/to/ssh_config
```

### 9. 从明文/加密文件直接连接（单文件单主机）

纯文本格式，易看易编辑。一个文件 = 一个主机：

```bash
# 明文直接连
slink web1.txt

# 加密文件连（需要主密码）
slink web1.txt.enc
```

配置文件示例 `web1.txt`：

```text
# slink host config
hostname: 192.168.1.100
port: 22
username: root
key_file: ~/.ssh/id_rsa
```

内联私钥（多行值）：

```text
hostname: 10.0.0.5
port: 2222
username: admin
key: |
  -----BEGIN OPENSSH PRIVATE KEY-----
  ...
  -----END OPENSSH PRIVATE KEY-----
|end
```

**加密分享**：

```bash
slink encrypt web1.txt              # 生成 web1.txt.enc
slink decrypt web1.txt.enc          # 解密回 web1.txt
slink encrypt web1.txt -o share.enc # 指定输出名
```

加密后的 `.enc` 文件可以安全地复制到其他机器，只要对方知道主密码就能连接。

## 环境变量

为了避免每次输入主密码，可以设置环境变量：

```bash
export SLINK_PASSWORD="your_master_password"
slink list
```

> 注意：将密码写入环境变量在共享环境中存在风险，请谨慎使用。

## 文件存储位置

- 加密数据：`~/.slink/hosts.enc`
- 盐值：`~/.slink/salt`

这两个文件权限会被自动设置为仅当前用户可读写（Unix 系统）。

## 依赖

- Python >= 3.8
- click
- cryptography

## 安全说明

- 主密码不会存储在磁盘上，只用于派生加密密钥
- 盐值（salt）随机生成，防止彩虹表攻击
- PBKDF2 迭代次数为 480,000 次
- 临时私钥文件在使用后会自动删除
