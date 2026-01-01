# KanapuroEdit Setup Guide

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
