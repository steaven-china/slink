# Chain Connections

Chain files let you define multi-hop SSH routes with per-hop credentials.
Unlike simple `jump_host` strings, chains support individual keys and
passwords for each intermediate hop.

## When to Use Chains

| Scenario | Simple `jump_host` | Chain file |
|----------|-------------------|------------|
| 1–2 hops, same key/agent | ✅ | Optional |
| 3+ hops | Works but messy | ✅ Clean |
| Per-hop different keys | ❌ Not supported | ✅ Supported |
| Share topology without secrets | ❌ | ✅ `.chain` |
| One-password encrypted bundle | ❌ | ✅ `.chain.enc` |

## Creating a Chain

### Interactive CLI

```bash
sli chain-create prod.chain
```

Menu flow:

1. **Pick endpoint** — from stored hosts or manual input
2. **Add jumps** — insert at any position
3. **Edit / Remove** — adjust the chain
4. **Preview** — see the JSON before saving
5. **Encrypt?** — optionally bundle into `.chain.enc`

### From the GUI

Select a host that has `jump_host` configured and click **Export Chain**.
The GUI resolves stored jump hosts and writes a `.chain` file.

## File Formats

### Plain `.chain`

```json
{
  "jumps": [
    {"hostname": "bastion", "username": "ops", "port": 2222},
    {"hostname": "10.0.0.1", "username": "root"}
  ],
  "endpoint": {
    "hostname": "10.0.0.5",
    "username": "dbadmin",
    "port": 22
  }
}
```

Safe to version-control or share — contains no passwords or keys.

### Encrypted `.chain.enc`

```json
{
  "topology": { "jumps": [...], "endpoint": {...} },
  "secrets": {
    "jumps": [
      {"password": "...", "key_file": "..."},
      ...
    ],
    "endpoint": {"password": "...", "key": "..."}
  }
}
```

One master password decrypts the entire bundle. Secrets are auto-merged
into the topology on load.

## Connecting

### CLI Quick-Connect

```bash
sli prod.chain
sli prod.chain.enc      # prompts for master password
```

### Explicit Connect

```bash
sli connect prod.chain
```

### GUI

Click **Open Chain** and select the file.

## How It Works

When you connect a chain, slink:

1. Decrypts `.chain.enc` if needed
2. Unpacks `topology` + `secrets`
3. Generates a temporary SSH config with `Host slk_jump_0`, `slk_jump_1`, ...
4. Assigns `IdentityFile` per hop
5. Invokes `ssh -F <tmp_config> -J slk_jump_0,slk_jump_1 user@endpoint`
6. Cleans up temp files on exit

> **Note:** Intermediate hops must use key-based auth or SSH agent.
> Password-only jumps are not supported by OpenSSH `ProxyJump`.
