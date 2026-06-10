#!/usr/bin/env bash
DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -d "$DIR/venv" ]; then
    PYTHON="$DIR/venv/bin/python3"
else
    PYTHON="python3"
fi
exec "$PYTHON" "$DIR/ut99_bsp_gui.py" "$@"
