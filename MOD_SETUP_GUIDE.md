# KanapuroEdit Setup Guide

## Files Changed for v0.1.0.4

This mod has been customized with the following changes:

| File | Change | Location |
|------|--------|----------|
| `scripts/housekeeping/version.py` | VERSION_NAME | Line 12 |
| `scripts/game_structure/game_essentials.py` | Window title | Line 641 |
| `pyproject.toml` | Package name & version | Lines 2-3 |
| `Clan-gen.iss` | Installer name & version | Lines 3, 8 |
| `Clangen.spec` | Executable name & version | Lines 31, 48, 55 |
| `changelog.txt` | Added mod changelog | Top of file |
| `README.md` | Updated title & description | Top of file |

## Current Configuration

- **Mod Name:** KanapuroEdit
- **Version:** v0.1.0.4
- **Window Title:** KanapuroEdit
- **Package Name:** kanapuroedit

## Building

To build the executable:
```bash
pyinstaller Clangen.spec
```

To run from source:
```bash
python main.py
```

## What NOT to Change

- Do not modify `SAVE_VERSION_NUMBER` in version.py (breaks old saves)
- Do not change file paths in scripts/ folder
- Do not modify import statements
