# SSH Config Import

Import existing `~/.ssh/config` entries into slink:

```bash
sli import
sli import --file /path/to/custom_ssh_config
```

## Imported Fields

Only the following fields are recognized:

| SSH Config | slink Field |
|------------|-------------|
| `Host` | Name + aliases |
| `Hostname` | `hostname` |
| `User` | `username` |
| `Port` | `port` |
| `IdentityFile` | `key_file` |

Passwords are prompted afterward (`sli edit <name> --ask-password`).

## Wildcards

Wildcard host patterns (`Host *`, `Host *.example.com`) are skipped during import.

## Multiple Aliases

If an SSH config block defines multiple aliases:

```
Host web1 www prod
    Hostname 192.168.1.100
    User root
```

All aliases receive the same configuration and are imported as separate entries pointing to the same host info.
