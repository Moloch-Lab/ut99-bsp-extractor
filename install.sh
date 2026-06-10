#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Creating virtual environment..."
python3 -m venv "$DIR/venv"

echo "==> Installing ut99bsp package..."
"$DIR/venv/bin/pip" install --upgrade pip setuptools wheel
"$DIR/venv/bin/pip" install "$DIR"

echo ""
echo "Done! Run with:"
echo "  ./run.sh              (GUI)"
echo "  ./venv/bin/ut99-bsp-extractor  (CLI)"
echo "  ./venv/bin/ut99-bsp-gui        (GUI via installed entry point)"
