#!/usr/bin/env bash
# Minimal launch for low-RAM ChromeOS. Keeps everything as light as possible.

# hey kanapuro ur gonna forget how to do this so write it down
# cd kanapuroeditclangen/
# chmod +x chosrun.sh (ONLY NEED TO DO ONCE)
# bash chosrun.sh


set -e
cd "$(dirname "$0")"

# Lightweight env
export PIP_NO_CACHE_DIR=1
export SDL_VIDEODRIVER=x11
export SDL_AUDIODRIVER=dummy
export SDL_AUDIODEV=default
export PYGAME_BLEND_ALPHA_SDL2=1
export PYGAME_SDL2=1

# Small window to save memory; avoid fullscreen
WIDTH=${WIDTH:-960}
HEIGHT=${HEIGHT:-540}

# Use existing venv if present; otherwise install deps once with poetry (no dev extras)
if [ -f .venv/bin/python ]; then
    PYTHON=.venv/bin/python
else
    poetry install --no-root --no-interaction --only main
    PYTHON="$(poetry env info --path)/bin/python"
fi

# Run optimized, no bytecode writes, windowed, low res
PYTHONOPTIMIZE=2 PYTHONDONTWRITEBYTECODE=1 \
    "$PYTHON" main.py --windowed --width "$WIDTH" --height "$HEIGHT"