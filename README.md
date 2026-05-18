# LifeGen Mega Merge - Kanapuro Edit (LGMMKE)

A ClanGen mod where you control your own cat! Choose your path and live out your life as a warrior. Personalized for Kanapuro's tastes!

## Requirements

To run LGMMKE from source code, you'll need:

- **Python 3.11.9 or earlier** (no later than 3.11.9)
- **Poetry** (Python dependency manager)
  
> **Note**: Poetry is optional — a simple local virtualenv or the embedded Python can also be used.

> **Note**: Python 3.12+ is not supported. Install Python 3.11.9 or earlier from [python.org](https://www.python.org/downloads)

## Installation & Setup

### 1. Install Python

Download Python 3.11.9 or earlier from [python.org](https://www.python.org/downloads)

Verify installation:
```bash
python3 --version
```

### 2. Install Poetry

Follow the [official Poetry installation guide](https://python-poetry.org/docs/#installing-with-pipx):

**Linux, macOS, or Windows (WSL/PowerShell):**
```bash
python3 -m pip install pipx --user
python3 -m pipx install poetry
python3 -m pipx ensurepath
```

Verify installation:
```bash
poetry --version
```

## How to Play

### Option 1: Run Script (Recommended)

**Windows:**
Double click the `run.bat` file in the game folder.

**Simple double-click (Windows, no global tools required):**
If you prefer a non-invasive way to run the game without installing Poetry or changing system state, use the provided `run_local.bat`. It prefers a project-local `.venv` (created for you) and falls back to the embedded Python at `C:\Users\henry.brown2\python-3.11.9-embed-amd64\python.exe` if present.

To run: double-click `run_local.bat` in the project root.

**Linux / macOS:**
Double click the `run.sh` file, or open a terminal in the game folder and run:
```bash
bash run.sh
```

**Chromebook (Optimized):**
Double click the `chosrun.sh` file, or open a terminal in the game folder and run:
```bash
bash chosrun.sh
```

### Option 2: Run from Terminal

Navigate to the game directory and use one of the following:

**Linux / macOS:**
```bash
cd kanapuroeditclangen
bash run.sh
```

**Windows:**
```bash
cd kanapuroeditclangen
run.bat
```

**Chromebook (Optimized):**
```bash
cd kanapuroeditclangen
bash chosrun.sh
```

### Option 3: Run from Visual Studio Code

1. Open the `kanapuroeditclangen` folder in VS Code
2. Open the integrated terminal (Ctrl + `)
3. Run:
   ```bash
   poetry config virtualenvs.in-project true
   poetry install --no-root
   ```
4. Select the Poetry virtual environment as your Python interpreter (Ctrl+Shift+P → "Python: Select Interpreter")
5. Open `main.py` and click the play button in the top right corner

## Features

- Play as your own custom cat
- Multiple life path choices
- Rich storytelling and events
- Colony management gameplay

## Support & Community

Have questions or found a bug? 

- Join our **Discord server** at [discord.gg/pB3XnFqenm](https://discord.gg/pB3XnFqenm) - check the `#lgmmke` channel for updates
- Visit my **Linktree** at [linktr.ee/kanapuro](https://linktr.ee/kanapuro) for multiple ways to contact me
- Check the **GitHub repository** for the latest source code and issue tracking

## Credits

- **Original Creator**: just-some-cat.tumblr.com
- **Lifegen Creator**: SableSteel and contributors
- **LifeGenMegaMerge**: Sel
- **Kanapuro Edit (LGMMKE)**: Current development

[View the original LifeGen credits](https://docs.google.com/document/d/1XCm5Eo-y5VA6W9quDMbF3VNyKL7S8_9Tl4c2buuiA8g/edit?usp=sharing)

## License

See [LICENSE.md](LICENSE.md) for details.
