# slink - Secure SSH Connection Manager

[![License: LGPL v3](https://img.shields.io/badge/License-LGPLv3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)

A lightweight SSH connection manager that encrypts your connection info locally and lets you connect with a single command — no need to remember IPs or usernames.

## Features

- **Encrypted Storage**: AES-128-CBC + HMAC (Fernet) encryption, key derived from your master password via PBKDF2-HMAC-SHA256 (1,000,000 iterations)
- **Master Password Protection**: All connection info is protected by a single master password
- **Key Management**: Support private key file paths or inline key pasting
- **Aliases**: Assign multiple aliases to a single host for quick access
- **Shell Completion**: Tab-completion for host names (powered by a plaintext `.show_direct` index)
- **JSON Support**: Export/import hosts as JSON, and connect via `.json` config files
- **Single-File Config**: One file = one host, supports both plaintext and encrypted formats
- **SSH Config Import**: Bulk import from `~/.ssh/config`
- **Password Rotation**: Change your master password anytime without losing data
- **Cross-Platform**: Works on Windows, Linux, and macOS

## Installation

```bash
pip install -r requirements.txt
# or
python setup.py install
```

Windows users can also use the standalone binaries (`sli.exe` / `sli-ui.exe`) built with Nuitka.

## Quick Start

### 1. Initialize

```bash
sli init
```

### 2. Add a Host

```bash
sli add myserver -h 192.168.1.100 -u root

# with a private key file
sli add myserver -h 192.168.1.100 -u root -i ~/.ssh/id_rsa

# with inline key text
sli add myserver -h 192.168.1.100 -u root --key-text "-----BEGIN OPENSSH PRIVATE KEY-----\n..."

# with aliases
sli add web1 -h 10.0.0.5 -u root -a www -a prod
```

### 3. List / Show / Connect

```bash
sli list              # table view
sli list --json       # JSON output
sli names             # list host names (no password needed)
sli show myserver     # host details
sli show myserver --json
sli connect myserver  # connect via SSH
```

### 4. Edit / Remove

```bash
sli edit myserver -h new.ip.address -u newuser
sli rm myserver --yes
```

### 5. Connect by Alias

```bash
sli connect www       # resolves to 'web1' if 'www' is an alias
sli show prod
sli rm www --yes      # removes the main host record
```

### 6. Import from SSH Config

```bash
sli import            # import all hosts from ~/.ssh/config
sli import -h myserver # import a specific host
```

### 7. Single-File Quick Connect

**Plaintext** (`host.txt`):
```text
hostname: 192.168.1.100
port: 22
username: root
key_file: ~/.ssh/id_rsa
```

**JSON** (`host.json`):
```json
{
  "hostname": "192.168.1.100",
  "port": 22,
  "username": "root",
  "key_file": "~/.ssh/id_rsa"
}
```

**Encrypted** (`host.txt.enc`):
```bash
sli encrypt host.txt        # creates host.txt.enc
sli decrypt host.txt.enc    # restores host.txt
```

Connect directly:
```bash
sli host.txt
sli host.json
sli host.txt.enc
```

### 8. Export / Import JSON

```bash
sli export -o backup.json            # sanitized (no passwords/keys)
sli export -o backup.json --with-secrets
sli import-json backup.json
```

### 9. Change Master Password

```bash
sli passwd
```

## Environment Variables

Avoid typing your master password repeatedly:

```bash
export SLINK_PASSWORD="your_master_password"
sli list
sli connect myserver
```

> **Warning**: Storing passwords in environment variables is risky on shared machines.

### Multi-User Isolation (Jump Hosts / Shared Servers)

On a shared bastion/jump host, each SSH user can have their own isolated slink configs:

```bash
# In ~/.bashrc or ~/.bash_profile on the jump host
export SLINK_USER=$USER
```

Now user `alice` and user `bob` each get their own encrypted store:
- Alice: `~/.slink/users/alice/hosts.enc`
- Bob:   `~/.slink/users/bob/hosts.enc`

Admins can inspect any user's config:
```bash
SLINK_USER=alice sli list
SLINK_USER=bob sli show web1
```

## Data Files

All runtime data is stored in `~/.slink/`:

| File | Description |
|------|-------------|
| `hosts.enc` | Encrypted JSON database |
| `salt` | Random 16-byte salt for PBKDF2 |
| `.show_direct` | Plaintext host name + alias index (for shell completion) |
| `.lock` | Advisory lock file for concurrency |

## Shell Completion

### Bash

```bash
eval "$(_SLI_COMPLETE=bash_source sli)"
```

### Zsh

```zsh
eval "$(_SLI_COMPLETE=zsh_source sli)"
```

### Fish

```fish
eval (env _SLI_COMPLETE=fish_source sli)
```

Host name and alias completion works out of the box (reads `.show_direct`, no password required).

## Dependencies

- Python >= 3.8
- click >= 8.0.0
- cryptography >= 41.0.0

## Security Notes

- The master password is **never stored on disk**; it is only used to derive the encryption key
- A random salt prevents rainbow table attacks
- PBKDF2 uses 1,000,000 iterations (reads legacy 480,000 data transparently)
- Temporary private key files are deleted immediately after SSH disconnect
- Atomic writes prevent data corruption during power loss

## Building Standalone Binaries

```bash
# CLI
python -m nuitka --standalone --include-package=click --include-package=cryptography --output-filename=sli slink.py

# GUI
python -m nuitka --standalone --enable-plugin=tk-inter --include-package=click --include-package=cryptography --output-filename=sli-ui slink-ui.py
```

## License

This project is licensed under the **GNU Lesser General Public License v3.0 (LGPL-3.0)**.  
See [LICENSE](LICENSE) for details.

## Disclaimer

This tool is provided as-is. The authors are not responsible for any data loss or security incidents arising from its use. Always keep backups of your SSH configurations.
