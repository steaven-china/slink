# Quick Start

## 1. Initialize

Set your master password on first run. This encrypts all stored credentials.

```bash
sli init
```

## 2. Add a Host

```bash
sli add web1 -h 192.168.1.100 -p 22 -u root -a www -a prod
```

Use `-a` to assign multiple aliases. The command will prompt for the SSH password and store it encrypted.

## 3. Connect

```bash
sli connect web1
sli connect www      # alias works too
```

## 4. Jump Hosts

Chain through bastion hosts automatically:

```bash
sli add db -h 10.0.0.5 --jump-host bastion
sli connect db       # translates to ssh -J user@bastion user@db
```

## 5. List & Show

```bash
sli list
sli show web1
```

## 6. JSON Export / Import

Backup or migrate your entire config:

```bash
sli export > backup.json
sli import-json backup.json
```

## 7. Rotate Master Password

```bash
sli passwd
```

## 8. Shell Completion

```bash
# Bash
eval "$(_SLI_COMPLETE=bash_source sli)"

# Zsh
eval "$(_SLI_COMPLETE=zsh_source sli)"
```
