# Building & Packaging

## Development Setup

```bash
git clone https://github.com/steaven-china/slink.git
cd slink
pip install -r requirements.txt
pip install -e .
```

## Nuitka Standalone Build

Windows Defender blocks `--onefile` (WinError 225). Use `--standalone`:

```bash
python -m nuitka \
    --standalone \
    --remove-output \
    --output-dir=dist \
    slink/cli.py
```

For the GUI entry point:

```bash
python -m nuitka \
    --standalone \
    --enable-plugin=tk-inter \
    --remove-output \
    --output-dir=dist \
    slink/gui.py
```

## CI/CD

GitHub Actions workflow (`.github/workflows/build.yml`):

- Test matrix: ubuntu / windows / macOS × Python 3.10 / 3.11 / 3.12
- Build triggered by `[build]` in commit message or `v*` tags
- Release artifacts on tags

## Version Format

```
0.1.0+<day>+<short-hash>
```

Example: `0.1.0+20240509+a1b2c3d`
