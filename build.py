#!/usr/bin/env python3
import subprocess, sys, os, shutil

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(THIS_DIR, "dist")

VENV_PYTHON = os.path.join(THIS_DIR, "venv", "bin", "python3")
python = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable

os.makedirs(DIST_DIR, exist_ok=True)

cmd = [
    python, "-m", "PyInstaller",
    "--onefile",
    "--windowed",
    "--name", "UT99-BSP-Extractor",
    "--distpath", DIST_DIR,
    "--add-data", f"exporters.py{os.pathsep}.",
    os.path.join(THIS_DIR, "ut99_bsp_gui.py"),
]

subprocess.check_call(cmd, cwd=THIS_DIR)
print(f"\nDone! Executable in: {os.path.join(DIST_DIR, 'UT99-BSP-Extractor')}")
