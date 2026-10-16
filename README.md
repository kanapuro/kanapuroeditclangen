# LifeGen Mega Merge - Kanapuro Edit (LGMMKE)

An edit of LifeGen MegaMerge, a ClanGen mod where you play as your own cat and live out their life in a Clan.

## Getting started

These instructions are for running the game from source. You don't need a code editor, but you do need Python and Poetry. Poetry installs the game's Python dependencies for you.

1. Open [this repository](https://github.com/kanapuro/kanapuroeditclangen), click **Code**, then **Download ZIP**.
2. Extract the ZIP into a folder. Don't run the game from inside the ZIP.
3. Install **Python 3.11** from [python.org](https://www.python.org/downloads/). On Windows, tick **Add python.exe to PATH** in the installer.
4. Follow the instructions below for your operating system.

Use Python 3.11 for this setup; the project's builds use that version. You don't need the exact 3.11.9 patch version.

### Windows

Open PowerShell from the Start menu. Run these commands one at a time to install Poetry:

```powershell
py -3.11 -m pip install --user pipx
py -3.11 -m pipx ensurepath
py -3.11 -m pipx install poetry
```

Close PowerShell and open it again so it can find Poetry. Check that the installation worked:

```powershell
poetry --version
```

Next, open the extracted game folder in File Explorer. This is the folder containing `main.py` and `pyproject.toml`. Click the address bar, type `powershell`, and press Enter to open PowerShell in that folder.

Run:

```powershell
poetry env use 3.11
poetry install --no-root
poetry run python main.py
```

The first installation may take a few minutes. Once setup is complete, you can double-click `run.bat` in the game folder to play again.

### Linux / macOS

Install Poetry using the [Poetry installation instructions](https://python-poetry.org/docs/#installation). Close and reopen your terminal afterward, then check:

```sh
poetry --version
```

Open a terminal in the extracted game folder, the one containing `main.py` and `pyproject.toml`. If your file manager doesn't offer an option to open a terminal there, type `cd ` followed by the folder's path in quotes, then press Enter.

Run:

```sh
poetry env use python3.11
poetry install --no-root
poetry run python main.py
```

The first installation may take a few minutes. To play again, open a terminal in the same folder and run:

```sh
bash run.sh
```

## Character customization

Open a cat's profile and choose **Customize Cat** to use the same editor as colony creation. It includes trait locks, randomization, Undo/Redo, Reset, skills, permanent conditions, and multiple scars. Age previews show the cat at different life stages; their actual age stays the same.

Edits stay in a draft until **Apply**. **Cancel** or **Back** discards them, and changing display size keeps the draft and Undo/Redo history. Cats created through the console use **Create** to confirm their draft.

## F3 commands

Load a colony and press **F3** to open the console. Enter `help` to list commands, or use commands such as `help cats create` and `help changeclan` for their syntax. Press F3 again to close it.

| Command | What it does |
| --- | --- |
| `cats list` | Shows cat names and IDs. |
| `cats create 24` | Opens the shared customizer for a new cat aged 24 moons. Omitting the age defaults to 1 moon. Cancel discards the cat. |
| `cats age CAT_ID` | Shows the cat's current age; replace `CAT_ID` with an ID from `cats list`. |
| `cats age CAT_ID 30` | Sets the cat's age to 30 moons. Signed values such as `+2` adjust it relative to the current age. Existing roles are retained. |
| `renameclan "New Colony"` | Renames the loaded colony and its save files. Names can contain letters, numbers, and spaces. |
| `location get` | Shows the current biome, camp, and available camps. |
| `changeclan Beach 4` | Moves to Beach, camp 4, regenerates neighboring colonies, and keeps existing outside cats. |
| `changeclan random` | Picks a random biome and camp and regenerates neighboring colonies. |

Relocation also accepts optional counts and switches:

```text
changeclan BIOME CAMP OTHER_COUNT OUTSIDER_COUNT REGENERATE_OTHER_CLANS WIPE_OUTSIDERS
```

Use `Forest`, `Mountainous`, `Plains`, or `Beach` for the biome, and a camp number or `random` for the camp. Use `true` or `false` for switches. For example, `changeclan Beach 4 3 5 true true` creates three neighboring colonies and replaces the outsider population with five cats. Counts apply when the corresponding switch is enabled. `changeclan Beach 4 false false` keeps both neighboring colonies and outside cats.

Relocation saves immediately and returns to camp. Keep a backup before using the outsider-wipe option: it permanently removes outside cats and their family, mate, and mentor links. The player, afterlife guides, and cats holding colony roles are retained. New outsiders receive relationships and inheritance data; unrelated resident families and mates stay intact.

## If the game won't start

- **`poetry` isn't recognized:** Close and reopen your terminal after installing it. If it still isn't found, check the [Poetry installation instructions](https://python-poetry.org/docs/#installation).
- **Python 3.11 can't be found:** Check that you installed it. On Windows, run `py -3.11 --version`; on Linux or macOS, run `python3.11 --version`.
- **Poetry can't find `pyproject.toml`:** Your terminal is in the wrong folder. Open it in the folder containing `main.py` and `pyproject.toml`.
- **The game window closes immediately:** Run `poetry run python main.py` from a terminal in the game folder so you can read the error. Include that error when asking for help.

## Support & Community

- [Discord server](https://discord.gg/pB3XnFqenm): check the `#lgmmke` channel for updates and help.
- [GitHub issues](https://github.com/kanapuro/kanapuroeditclangen/issues): report bugs here, including what happened and any error message.
- [Linktree](https://linktr.ee/kanapuro): other ways to contact me.

## Credits

- **Original Creator**: just-some-cat.tumblr.com
- **Lifegen Creator**: SableSteel and contributors
- **LifeGenMegaMerge**: Sel
- **Kanapuro Edit (LGMMKE)**: Current development

[View the original LifeGen credits](https://docs.google.com/document/d/1XCm5Eo-y5VA6W9quDMbF3VNyKL7S8_9Tl4c2buuiA8g/edit?usp=sharing)

## License

See [LICENSE.md](LICENSE.md) for details.
