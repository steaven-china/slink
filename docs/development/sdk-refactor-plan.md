# SDK Refactor Plan

## Problem

Core logic (chain unpacking, file loading, jump resolution, secret collection) is trapped inside `cli.py`. This makes `slink` unusable as a library — other Python projects cannot `import slink` and programmatically manage hosts or connections.

## Goal

Extract a clean `slink.api` module so that CLI/GUI become thin consumers.

## Target API

```python
import slink

# Host CRUD
slink.add_host("web1", {"hostname": "10.0.0.5", "username": "root"}, password="pw")
info = slink.get_host("web1", password="pw")
hosts = slink.list_hosts(password="pw")

# File loading (chain / enc / json / plain)
info = slink.load_file("prod.chain.enc")   # auto-detect, decrypt, unpack

# Chain
chain = slink.unpack_chain({"jumps": [...], "endpoint": {...}})
slink.connect_chain(chain["jumps"], chain["endpoint"])

# SSH
slink.connect(info)
slink.terminate_all()
```

## Refactor Steps

1. **Create `slink/api.py`**
   - Move `_try_load_file` -> `load_file`
   - Move `_unpack_chain` -> `unpack_chain`
   - Move `_collect_chain_secrets` -> `collect_chain_secrets`
   - Move `_resolve_jump_chain` -> `resolve_jump_chain`
   - Move `_parse_jump_spec` (from gui.py) -> `parse_jump_spec`

2. **Update `slink/__init__.py`**
   - Expose stable public symbols:
     `connect`, `connect_chain`, `load_file`, `list_hosts`, `add_host`, ...

3. **Thin `cli.py`**
   - Import from `slink.api` instead of local functions
   - Keep only Click decorators and `click.echo` calls

4. **Thin `gui.py`**
   - Import from `slink.api` instead of duplicating logic

5. **Tests**
   - Move `test_cli_chain.py` -> `test_api_chain.py`
   - Add `test_api.py` for public surface

## Effort Estimate

- Refactor + tests: ~1-2 hours
- Verification (CLI/GUI still work): 30 min

## Risk

- Low. We are only moving code, not changing behavior.
- Need to watch for circular imports (`cli.py` -> `api.py` -> `store.py` is fine).
