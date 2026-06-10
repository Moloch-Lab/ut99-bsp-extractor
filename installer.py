"""Cross-platform installer / packager for UT99 BSP Extractor.

If run from the project's venv, it uses that Python. Otherwise falls
back to the system Python.

Usage:
    python installer.py                  # interactive CLI
    python installer.py --cli            # interactive CLI (explicit)
    python installer.py --gui            # GUI mode (requires PySide6)
    python installer.py --os linux --format binary  # non-interactive
    python installer.py --os linux --format deb     # build .deb
    python installer.py --os linux --format rpm     # build .rpm
    python installer.py --os linux --format appimage
    python installer.py --os linux --format pip     # pip install into venv
"""

import os
import sys
import subprocess
import platform
import shutil
import argparse

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(THIS_DIR, "dist")
VENV_DIR = os.path.join(THIS_DIR, "venv")
VENV_BIN = os.path.join(VENV_DIR, "bin", "python3")
VENV_PIP = os.path.join(VENV_DIR, "bin", "pip")

# Re-exec with venv Python if available and not already using it
if os.path.isdir(VENV_DIR) and sys.executable != VENV_BIN:
    os.execv(VENV_BIN, [VENV_BIN] + sys.argv)


# ── helpers ───────────────────────────────────────────────────────

def _log(msg):
    print(f"  {msg}")


def _run(cmd, cwd=None, **kw):
    kw.setdefault("check", True)
    return subprocess.run(cmd, cwd=cwd or THIS_DIR, **kw)


def _require_venv():
    if not os.path.isdir(VENV_DIR):
        _log("Creating virtual environment...")
        _run([sys.executable, "-m", "venv", VENV_DIR])
    # Check if package is already installed by looking for the entry point
    entry = os.path.join(VENV_DIR, "bin", "ut99-bsp-extractor")
    if not os.path.exists(entry):
        _log("Installing ut99bsp package in venv...")
        _run([VENV_PIP, "install", "-e", THIS_DIR])


def _host_os():
    s = platform.system().lower()
    if s == "linux":
        return "linux"
    elif s == "windows":
        return "windows"
    elif s == "darwin":
        return "macos"
    return s


def _linux_distro():
    try:
        import distro
        return distro.id()
    except ImportError:
        pass
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("ID="):
                    return line.strip().split("=", 1)[1].strip('"')
    except FileNotFoundError:
        pass
    return "unknown"


def _format_size(path):
    sz = os.path.getsize(path)
    for unit in ("B", "KB", "MB", "GB"):
        if sz < 1024:
            return f"{sz:.0f} {unit}"
        sz /= 1024
    return f"{sz:.1f} GB"


def _build_binary():
    """Build standalone PyInstaller binary."""
    out = os.path.join(DIST_DIR, "UT99-BSP-Extractor")
    if os.path.exists(out):
        _log(f"Found existing binary ({_format_size(out)})")
        return out

    _log("Building standalone binary with PyInstaller...")
    _require_venv()
    _run([VENV_PIP, "install", "pyinstaller"])
    pyinstaller = os.path.join(VENV_DIR, "bin", "pyinstaller")
    _run([
        pyinstaller, "--onefile", "--windowed",
        "--name", "UT99-BSP-Extractor",
        "--distpath", DIST_DIR,
        "--add-data", f"src/ut99bsp{os.pathsep}ut99bsp",
        os.path.join(THIS_DIR, "ut99_bsp_gui.py"),
    ])
    if os.path.exists(out):
        _log(f"Binary built: {out} ({_format_size(out)})")
    return out


def _build_deb(binary_path):
    """Wrap the binary in a .deb package."""
    if not shutil.which("dpkg-deb"):
        _log("dpkg-deb not found — skipping .deb")
        return None
    _log("Building .deb package...")
    pkg_dir = os.path.join(DIST_DIR, "deb_pkg")
    deb_root = os.path.join(pkg_dir, "ut99-bsp-extractor_0.2.0_amd64")
    usr_bin = os.path.join(deb_root, "usr", "bin")
    os.makedirs(usr_bin, exist_ok=True)
    shutil.copy2(binary_path, os.path.join(usr_bin, "ut99-bsp-extractor"))

    deb_out = os.path.join(DIST_DIR, "ut99-bsp-extractor_0.2.0_amd64.deb")
    os.makedirs(os.path.join(deb_root, "DEBIAN"), exist_ok=True)
    with open(os.path.join(deb_root, "DEBIAN", "control"), "w") as f:
        f.write(
            "Package: ut99-bsp-extractor\n"
            "Version: 0.2.0\n"
            "Architecture: amd64\n"
            "Maintainer: Moloch Lab\n"
            "Description: Extract BSP geometry from UT99 .unr map files\n"
            " GUI and CLI tool for exporting to OBJ/MTL and glTF formats.\n"
        )
    _run(["dpkg-deb", "--build", deb_root, deb_out], check=False)
    if os.path.exists(deb_out):
        _log(f".deb built: {deb_out} ({_format_size(deb_out)})")
        return deb_out
    _log("dpkg-deb not available — skipping .deb")
    return None


def _build_rpm(binary_path):
    """Wrap the binary in a .rpm package."""
    if not shutil.which("rpmbuild"):
        _log("rpmbuild not found — skipping .rpm")
        return None
    _log("Building .rpm package...")
    home = os.path.expanduser("~")
    rpm_root = os.path.join(home, "rpmbuild")
    os.makedirs(os.path.join(rpm_root, "SOURCES"), exist_ok=True)
    os.makedirs(os.path.join(rpm_root, "SPECS"), exist_ok=True)
    os.makedirs(os.path.join(rpm_root, "BUILD"), exist_ok=True)

    shutil.copy2(binary_path, os.path.join(rpm_root, "SOURCES", "ut99-bsp-extractor"))

    spec = os.path.join(rpm_root, "SPECS", "ut99-bsp-extractor.spec")
    with open(spec, "w") as f:
        f.write(
            "Name: ut99-bsp-extractor\n"
            "Version: 0.2.0\n"
            "Release: 1\n"
            "Summary: UT99 BSP geometry extractor\n"
            "License: MIT\n"
            "BuildArch: x86_64\n"
            "%description\n"
            "Extract BSP geometry from Unreal Tournament 99 .unr files.\n"
            "%install\n"
            "mkdir -p %{buildroot}/usr/bin\n"
            "install -m 755 %{_sourcedir}/ut99-bsp-extractor %{buildroot}/usr/bin/\n"
            "%files\n"
            "/usr/bin/ut99-bsp-extractor\n"
        )
    _run(["rpmbuild", "-bb", spec], check=False)
    rpm_out = os.path.join(home, "rpmbuild", "RPMS", "x86_64",
                           f"ut99-bsp-extractor-0.2.0-1.x86_64.rpm")
    if os.path.exists(rpm_out):
        dest = os.path.join(DIST_DIR, os.path.basename(rpm_out))
        shutil.copy2(rpm_out, dest)
        _log(f".rpm built: {dest} ({_format_size(dest)})")
        return dest
    _log("rpmbuild not available — skipping .rpm")
    return None


def _build_appimage(binary_path):
    """Wrap the binary in an AppImage."""
    _log("Building AppImage...")

    appimagetool = shutil.which("appimagetool")
    if not appimagetool:
        # Try the cached download
        appimagetool = os.path.join(DIST_DIR, "appimagetool")
        if not os.path.exists(appimagetool):
            _log("Downloading appimagetool...")
            import urllib.request
            url = ("https://github.com/AppImage/AppImageKit/releases/download/"
                   "continuous/appimagetool-x86_64.AppImage")
            try:
                urllib.request.urlretrieve(url, appimagetool)
                os.chmod(appimagetool, 0o755)
            except Exception as e:
                _log(f"Failed to download appimagetool: {e}")
                return None

    appdir = os.path.join(DIST_DIR, "UT99-BSP-Extractor.AppDir")
    usr_bin = os.path.join(appdir, "usr", "bin")
    os.makedirs(usr_bin, exist_ok=True)
    shutil.copy2(binary_path, os.path.join(usr_bin, "ut99-bsp-extractor"))

    desktop = os.path.join(appdir, "ut99-bsp-extractor.desktop")
    with open(desktop, "w") as f:
        f.write(
            "[Desktop Entry]\n"
            "Name=UT99 BSP Extractor\n"
            "Exec=ut99-bsp-extractor\n"
            "Type=Application\n"
            "Categories=Graphics;3DGraphics;\n"
        )
    with open(os.path.join(appdir, "AppRun"), "w") as f:
        f.write("#!/bin/bash\n")
        f.write('HERE="$(dirname "$(readlink -f "$0")")"\n')
        f.write('exec "$HERE/usr/bin/ut99-bsp-extractor" "$@"\n')
    os.chmod(os.path.join(appdir, "AppRun"), 0o755)

    out = os.path.join(DIST_DIR, "UT99-BSP-Extractor-x86_64.AppImage")
    _run([appimagetool, appdir, out], check=False)

    if os.path.exists(out):
        _log(f"AppImage built: {out} ({_format_size(out)})")
        return out
    _log("AppImage build failed — skipping")
    return None


def _pip_install():
    """Install via pip into venv."""
    _log("Installing package into virtual environment...")
    _require_venv()
    _run([VENV_PIP, "install", "-e", THIS_DIR])
    _log("Done. Run with:")
    _log(f"  {os.path.join(VENV_DIR, 'bin', 'ut99-bsp-extractor')}  (CLI)")
    _log(f"  {os.path.join(VENV_DIR, 'bin', 'ut99-bsp-gui')}        (GUI)")
    _log(f"  ./run.sh                                            (GUI)")


# ── Linux build dispatcher ────────────────────────────────────────

LINUX_FORMATS = {
    "binary": ("Standalone executable", _build_binary),
    "deb": (".deb package (Debian/Ubuntu)", lambda: _build_deb(_build_binary())),
    "rpm": (".rpm package (Fedora/RHEL)", lambda: _build_rpm(_build_binary())),
    "appimage": ("AppImage (universal Linux)", lambda: _build_appimage(_build_binary())),
    "pip": ("pip install into venv", _pip_install),
}

WINDOWS_FORMATS = {
    "exe": ("Windows .exe", lambda: _log(
        "Build on Windows natively:\n"
        "  pyinstaller --onefile --windowed --name UT99-BSP-Extractor "
        "--add-data \"src/ut99bsp;ut99bsp\" ut99_bsp_gui.py\n\n"
        "Or push a tag to trigger GitHub Actions which builds all platforms.")),
    "pip": ("pip install into venv", _pip_install),
    "source": ("Download source zip", lambda: _log("Download from github.com/Moloch-Lab/ut99-bsp-extractor")),
}

MACOS_FORMATS = {
    "app": ("macOS .app bundle", lambda: _log(
        "Build on macOS natively:\n"
        "  pyinstaller --onefile --windowed --name UT99-BSP-Extractor "
        "--add-data \"src/ut99bsp:ut99bsp\" ut99_bsp_gui.py\n\n"
        "Or push a tag to trigger GitHub Actions which builds all platforms.")),
    "pip": ("pip install into venv", _pip_install),
    "source": ("Download source zip", lambda: _log("Download from github.com/Moloch-Lab/ut99-bsp-extractor")),
}


# ── CLI mode ──────────────────────────────────────────────────────

def _run_cli_interactive():
    print()
    print("UT99 BSP Extractor — Installer")
    print("=" * 40)
    print(f"Host OS: {_host_os()} ({_linux_distro() if _host_os() == 'linux' else platform.machine()})")
    print()

    # 1. Choose target OS
    os_options = ["linux", "windows", "macos"]
    print("Select target OS:")
    for i, o in enumerate(os_options):
        tag = " (current)" if o == _host_os() else ""
        print(f"  [{i + 1}] {o}{tag}")
    try:
        choice = input(f"Choice [1-{len(os_options)}] (default=1): ").strip()
        target_os = os_options[int(choice) - 1] if choice else "linux"
    except (ValueError, IndexError):
        target_os = "linux"

    formats = {"linux": LINUX_FORMATS, "windows": WINDOWS_FORMATS, "macos": MACOS_FORMATS}[target_os]

    if target_os == "linux":
        distro = _linux_distro()
        print(f"\nLinux distro detected: {distro}")
        print("Available formats:")
    else:
        print(f"\nBuilding for {target_os} — cross-compilation limited.")
        print("The build must typically run on the target OS.")

    fmt_keys = list(formats.keys())
    print()
    for i, k in enumerate(fmt_keys):
        desc = formats[k][0]
        print(f"  [{i + 1}] {desc}")
    try:
        choice = input(f"Choice [1-{len(fmt_keys)}] (default=1): ").strip()
        fmt = fmt_keys[int(choice) - 1] if choice else fmt_keys[0]
    except (ValueError, IndexError):
        fmt = fmt_keys[0]

    print()
    formats[fmt][1]()


# ── GUI mode ──────────────────────────────────────────────────────

def _run_gui():
    try:
        from PySide6.QtWidgets import (
            QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
            QPushButton, QLabel, QComboBox, QTextEdit, QGroupBox,
            QMessageBox, QProgressBar,
        )
        from PySide6.QtCore import Qt, QThread, Signal, QObject
        from PySide6.QtGui import QFont
    except ImportError:
        print("PySide6 not available. Install with: pip install PySide6")
        sys.exit(1)

    class BuildWorker(QObject):
        log = Signal(str)
        done = Signal()
        error = Signal(str)

        def __init__(self, target_os, fmt):
            super().__init__()
            self.target_os = target_os
            self.fmt = fmt

        def run(self):
            try:
                formats = {"linux": LINUX_FORMATS, "windows": WINDOWS_FORMATS,
                           "macos": MACOS_FORMATS}[self.target_os]
                action = formats[self.fmt][1]

                # Redirect prints to log signal
                import io
                buf = io.StringIO()
                old_stdout = sys.stdout
                sys.stdout = buf
                try:
                    action()
                finally:
                    sys.stdout = old_stdout

                for line in buf.getvalue().split("\n"):
                    if line.strip():
                        self.log.emit(line)
                self.done.emit()
            except Exception as e:
                self.error.emit(str(e))

    class InstallerWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("UT99 BSP Extractor — Installer")
            self.setMinimumSize(600, 500)
            self.resize(700, 550)
            self.setStyleSheet("""
                QMainWindow { background-color: #1e1e2e; }
                QLabel { color: #cdd6f4; font-size: 13px; }
                QPushButton {
                    background-color: #89b4fa; color: #1e1e2e;
                    border: none; padding: 8px 18px; border-radius: 6px;
                    font-weight: bold; font-size: 13px;
                }
                QPushButton:hover { background-color: #74c7ec; }
                QPushButton:disabled { background-color: #45475a; color: #6c7086; }
                QComboBox {
                    background-color: #313244; color: #cdd6f4;
                    border: 1px solid #45475a; border-radius: 6px;
                    padding: 6px 12px; font-size: 13px;
                }
                QComboBox::drop-down { border: none; }
                QComboBox QAbstractItemView {
                    background-color: #313244; color: #cdd6f4;
                    selection-background-color: #45475a;
                }
                QTextEdit {
                    background-color: #181825; color: #cdd6f4;
                    border: 1px solid #45475a; border-radius: 6px;
                    font-family: monospace; font-size: 12px;
                }
                QGroupBox {
                    color: #cdd6f4; font-weight: bold;
                    border: 1px solid #45475a; border-radius: 8px;
                    margin-top: 12px; padding-top: 16px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin; left: 12px; padding: 0 6px;
                }
                QProgressBar {
                    border: none; border-radius: 6px; background-color: #313244;
                    height: 16px; text-align: center; color: #cdd6f4;
                }
                QProgressBar::chunk { background-color: #a6e3a1; border-radius: 6px; }
            """)

            self.worker = None
            self.worker_thread = None

            central = QWidget()
            self.setCentralWidget(central)
            layout = QVBoxLayout(central)
            layout.setSpacing(12)
            layout.setContentsMargins(16, 16, 16, 16)

            # Host info
            host = f"Host: {_host_os()} ({platform.machine()})"
            if _host_os() == "linux":
                host += f" — {_linux_distro()}"
            info = QLabel(host)
            info.setStyleSheet("color: #a6adc8;")
            layout.addWidget(info)

            # Target OS selection
            os_row = QHBoxLayout()
            os_row.addWidget(QLabel("Target OS:"))
            self.os_combo = QComboBox()
            self.os_combo.addItems(["linux", "windows", "macos"])
            # Set current OS as default
            host_idx = {"linux": 0, "windows": 1, "macos": 2}.get(_host_os(), 0)
            self.os_combo.setCurrentIndex(host_idx)
            self.os_combo.currentTextChanged.connect(self._update_formats)
            os_row.addWidget(self.os_combo)
            os_row.addStretch()
            layout.addLayout(os_row)

            # Format selection
            fmt_row = QHBoxLayout()
            fmt_row.addWidget(QLabel("Package format:"))
            self.fmt_combo = QComboBox()
            fmt_row.addWidget(self.fmt_combo)
            fmt_row.addStretch()
            layout.addLayout(fmt_row)

            # Build button
            self.build_btn = QPushButton("Build")
            self.build_btn.clicked.connect(self._start_build)
            layout.addWidget(self.build_btn)

            # Progress
            self.progress = QProgressBar()
            self.progress.setVisible(False)
            layout.addWidget(self.progress)

            # Log
            self.log = QTextEdit()
            self.log.setReadOnly(True)
            layout.addWidget(self.log, stretch=1)

            self._update_formats()

        def _update_formats(self):
            self.fmt_combo.clear()
            target = self.os_combo.currentText()
            formats = {"linux": LINUX_FORMATS, "windows": WINDOWS_FORMATS,
                       "macos": MACOS_FORMATS}.get(target, LINUX_FORMATS)
            for key, (desc, _) in formats.items():
                self.fmt_combo.addItem(desc, key)

        def _start_build(self):
            if self.worker is not None:
                return

            target = self.os_combo.currentText()
            fmt = self.fmt_combo.currentData()
            if not fmt:
                return

            self.build_btn.setEnabled(False)
            self.os_combo.setEnabled(False)
            self.fmt_combo.setEnabled(False)
            self.progress.setVisible(True)
            self.progress.setRange(0, 0)
            self.log.clear()
            self._log(f"Building {fmt} package for {target}...\n")

            self.worker = BuildWorker(target, fmt)
            self.worker_thread = QThread()
            self.worker.moveToThread(self.worker_thread)
            self.worker_thread.started.connect(self.worker.run)
            self.worker.done.connect(self._on_done)
            self.worker.error.connect(self._on_error)
            self.worker.log.connect(self._log)
            self.worker_thread.finished.connect(self.worker_thread.deleteLater)
            self.worker_thread.start()

        def _log(self, msg):
            self.log.append(msg)
            sb = self.log.verticalScrollBar()
            sb.setValue(sb.maximum())

        def _on_done(self):
            self._log("\n✔ Done!")
            self.progress.setRange(0, 100)
            self.progress.setValue(100)
            self._cleanup()

        def _on_error(self, msg):
            self._log(f"\n✖ Error: {msg}")
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            self._cleanup()

        def _cleanup(self):
            self.build_btn.setEnabled(True)
            self.os_combo.setEnabled(True)
            self.fmt_combo.setEnabled(True)
            if self.worker_thread:
                self.worker_thread.quit()
                self.worker_thread.wait()
            self.worker = None
            self.worker_thread = None

    app = QApplication(sys.argv)
    win = InstallerWindow()
    win.show()
    sys.exit(app.exec())


# ── Entry point ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="UT99 BSP Extractor — Installer / Packager")
    parser.add_argument("--cli", action="store_true", help="Force CLI mode (default)")
    parser.add_argument("--gui", action="store_true", help="GUI mode (requires PySide6)")
    parser.add_argument("--os", choices=["linux", "windows", "macos"],
                        help="Target OS (non-interactive)")
    parser.add_argument("--format",
                        help="Package format (non-interactive; depends on OS)")
    args = parser.parse_args()

    # Non-interactive mode
    if args.os and args.format:
        formats = {"linux": LINUX_FORMATS, "windows": WINDOWS_FORMATS,
                   "macos": MACOS_FORMATS}.get(args.os)
        if not formats:
            print(f"Unknown OS: {args.os}")
            return 1
        if args.format not in formats:
            print(f"Format '{args.format}' not valid for {args.os}. Choose from: {', '.join(formats)}")
            return 1
        formats[args.format][1]()
        return 0

    # GUI mode
    if args.gui or (not args.cli and "PySide6" in sys.modules):
        try:
            import PySide6
            _run_gui()
            return 0
        except ImportError:
            if args.gui:
                print("PySide6 not installed. Install with: pip install PySide6")
                return 1

    # CLI mode (default)
    _run_cli_interactive()
    return 0


if __name__ == "__main__":
    sys.exit(main())
