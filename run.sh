#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

# Use venv if present, otherwise try installed package
if [ -d "$DIR/venv" ]; then
    PYTHON="$DIR/venv/bin/python3"
else
    PYTHON="python3"
fi

# Try installed package first, fall back to local source
if "$PYTHON" -c "import ut99bsp" 2>/dev/null; then
    exec "$PYTHON" -m ut99bsp.gui "$@"
else
    # Add src/ to path for local development
    export PYTHONPATH="$DIR/src:$PYTHONPATH"
    exec "$PYTHON" -c "
import sys
sys.path.insert(0, '$DIR/src')
from ut99bsp.gui import main
sys.exit(main())
" "$@"
fi
