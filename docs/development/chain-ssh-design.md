# Chain SSH Connection Design

## Problem

`slink` supports multi-hop SSH connections via `.chain` / `.chain.enc` files. The current `ssh -J` approach works for simple username@host:port chains, but **fails when individual jumps require distinct private keys**.

OpenSSH's `-J` (ProxyJump) does **not** accept per-hop `-i` flags. The `-i` before `-J` applies only to the final destination, not intermediate jumps.

## Goal

Implement `connect_chain()` in `ssh_wrapper.py` that transparently handles per-hop keys by generating a temporary SSH config file.

## Design

### Option A: Temporary SSH Config (Selected)

Generate a temp config file with `Host` aliases for each jump, assign `IdentityFile` per alias, then invoke:

```bash
ssh -F /tmp/slink_cfg_xxx -J slk_jump_0,slk_jump_1 user@endpoint
```

Config contents:

```
Host slk_jump_0
    HostName bastion.example.com
    User ops
    Port 2222
    IdentityFile /tmp/key_xxx
    StrictHostKeyChecking accept-new

Host slk_jump_1
    HostName 10.0.0.1
    User root
    Port 22
    IdentityFile /tmp/key_yyy
    StrictHostKeyChecking accept-new
```

**Pros:**
- Native OpenSSH; no external tools.
- Supports all SSH features (agent forwarding, ciphers, etc.) per hop.
- Clean error messages from `ssh` itself.

**Cons:**
- Temp files must be securely cleaned up on success/failure/termination.
- Windows path escaping for `IdentityFile` needs care.

### Option B: Nested ProxyCommand

Chain `ssh -W` manually:

```bash
ssh -o ProxyCommand="ssh -W %%h:%%p jump1" -i endpoint_key user@endpoint
```

For N hops this requires N-1 nested ProxyCommands. Implementation complexity grows quadratically.

**Rejected:** Too complex, harder to debug, temp key cleanup scattered across N processes.

### Option C: sshpass + Multiple Sequential ssh

Run `ssh` to jump1, establish tunnel, then `ssh` through it. Requires background daemon processes.

**Rejected:** Process management nightmare; incompatible with interactive shell expectations.

## Consequences

1. **Temp file lifecycle:** Must delete config + temp keys in `finally` block and on GUI window close.
2. **Windows Defender:** Temp `.tmp` key files have caused issues before; use `mkstemp` + explicit `chmod`.
3. **Password-based jumps:** SSH `-J` does not support interactive password prompts for intermediate hops. This design **requires key-based auth for jumps** (or SSH agent). Document this limitation.
4. **Agent forwarding:** `-A` should probably be added to jump host config so agent is usable through the chain.

## Interface

```python
def connect_chain(chain: list[dict], endpoint: dict) -> None:
    """
    Connect through a chain of jumps to an endpoint.

    chain: list of dicts, each with hostname, username, port, key, key_file, password
    endpoint: dict with hostname, username, port, key, key_file, password, extra_args
    """
```

The caller (`cli.py` / `gui.py`) unpacks `.chain` into `(jumps, endpoint)` and calls this.

## Code Locations

| File | Change |
|------|--------|
| `ssh_wrapper.py` | Add `connect_chain()`, temp config generation, temp key collection |
| `cli.py` | `main()` quick-connect: detect `_chain` key and call `connect_chain` instead of `connect` |
| `cli.py` | `connect_cmd`: same detection for stored hosts with `_chain` |
| `gui.py` | (Future) Bind chain connect to listbox selection |

## Test Plan

1. Unit test: `_build_chain_config(jumps, endpoint)` produces valid OpenSSH config syntax.
2. Unit test: temp keys written with `0o600` / `S_IREAD`.
3. Integration test (manual): Connect through 2-hop chain with distinct ed25519 keys.
