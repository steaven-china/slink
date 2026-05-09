# Installation

## Requirements

- Python 3.8+
- `cryptography >= 41.0.0`
- `click >= 8.0.0`
- `pyyaml >= 6.0` (optional, for group support)
- OpenSSH client (`ssh` command)
- tkinter (optional, for GUI mode)

## From Source

```bash
git clone https://github.com/steaven-china/slink.git
cd slink
pip install -r requirements.txt
python setup.py install
```

## Editable Install (Development)

```bash
pip install -e .
```

## Windows Standalone

Build with Nuitka using `--standalone` (avoiding `--onefile` which triggers Windows Defender):

```bash
python -m nuitka --standalone --remove-output --output-dir=dist slink/cli.py
```

## WSL / Linux

Same Python setup. Data lives under `~/.slink/` by default.

## Verify

```bash
sli --version
sli --help
```
