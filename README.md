# UT99 BSP Extractor

Extract and export 3D map geometry from **Unreal Tournament 1999** (UT99) `.unr` files. This tool reads BSP polygon data from classic UT99 maps — including DM-Barricade, CTF-Command, DM-Morpheus, and any other stock or custom map — and exports them to standard 3D formats usable in Blender, Maya, Unity, Unreal Engine 5, and other 3D applications.

Output includes full **UV coordinates**, **vertex normals**, **per-texture material groups**, and **lightmap UVs** (as glTF `TEXCOORD_1`). Texture names are resolved from the original package's import/export tables, making it straightforward to reapply the correct source textures.

A cross-platform **PySide6 GUI** provides drag-and-drop batch processing with a real-time **3D wireframe preview** (mouse-drag rotation, scroll zoom), a Catppuccin Mocha dark theme, progress ETA, and keyboard shortcuts. A CLI is also available for headless/scripted use.

Also works with Unreal Engine 1 games built on the same engine, such as **Deus Ex**, **Rune**, and **Unreal (1998)**.

## Downloads

| Platform | Format | File |
|----------|--------|------|
| Linux | standalone binary | `UT99-BSP-Extractor-linux` |
| Linux | .deb (Debian/Ubuntu) | `ut99-bsp-extractor_1.0.0_amd64.deb` |
| Linux | .rpm (Fedora/RHEL) | `ut99-bsp-extractor-1.0.0-1.x86_64.rpm` |
| Windows | .exe | `UT99-BSP-Extractor-windows.exe` |
| macOS | standalone binary | `UT99-BSP-Extractor-macos` |

All assets built automatically by GitHub Actions on tag push.

## Features

- **Cross-platform GUI** — Native look on Linux, Windows, and macOS (PySide6)
- **Batch processing** — Drag & drop multiple maps, extract all at once
- **3D wireframe preview** — Rotate with mouse, zoom with scroll wheel
- **3 export formats** — OBJ (raw), OBJ+MTL (grouped by texture), glTF 2.0 (with lightmap UVs as `TEXCOORD_1`)
- **Modern dark theme** — Easy on the eyes, consistent across platforms
- **Settings persistence** — Remembers window size, last directory, format choice
- **Keyboard shortcuts** — Ctrl+O (add files), Ctrl+E (extract), Delete (remove)
- **Context menus** — Right-click queue items to remove, show in folder, quick-extract
- **Progress ETA** — Estimated time remaining during batch extraction
- **Stats dashboard** — Live polygon count, maps queued, last run time
- **Texture name resolution** — Reads texture references from package import/export tables
- **Lightmap UV support** — Second UV set in glTF output (`TEXCOORD_1`)
- **Python API** — `from ut99bsp import extract_map` for scripting

## Quick Start

### Install from source with one command

```sh
git clone https://github.com/Moloch-Lab/ut99-bsp-extractor.git
cd ut99-bsp-extractor
./install.sh              # creates venv + installs package
./run.sh                  # launch GUI
```

Or use the interactive installer to build a package for your OS:

```sh
./venv/bin/python3 installer.py            # interactive CLI menu
./venv/bin/python3 installer.py --gui       # GUI installer
./venv/bin/python3 installer.py --os linux --format appimage  # non-interactive
```

## Usage

### GUI

```sh
./run.sh
```

Drag & drop `.unr` files, select format (OBJ, OBJ+MTL, glTF), click **Extract All**. After extraction, click **Preview** to inspect the 3D geometry (drag to rotate, scroll to zoom).

### CLI

```sh
# Via installed package:
venv/bin/ut99-bsp-extractor map.unr [output] -f {obj,objmtl,gltf}

# Or directly:
python rip_unr.py map.unr [output] -f {obj,objmtl,gltf}
```

Formats:
- `obj` — Wavefront OBJ (no material library)
- `objmtl` — OBJ + MTL (polygons grouped by texture)
- `gltf` — glTF 2.0 (`.gltf` + `.bin` with per-material mesh primitives, includes lightmap UVs as `TEXCOORD_1`)

Output defaults to `<mapname>.obj` in the current directory.

### Python API

```python
from ut99bsp import extract_map

result = extract_map("DM-MyLevel.unr", "output.obj", fmt="objmtl")
print(f"{result.polygons} polygons written to {result.output_path}")
# result.triangles -> list of 3-tuples for preview
```

## Installer

The [`installer.py`](installer.py) script builds distribution packages for your target OS:

| OS | Formats | Requirements |
|----|---------|-------------|
| Linux | standalone binary, `.deb`, `.rpm`, pip | `dpkg-deb` for .deb, `rpmbuild` for .rpm (optional) |
| Windows | .exe (via PyInstaller on Windows), pip | Windows + PyInstaller for .exe |
| macOS | .app (via PyInstaller on macOS), pip | macOS + PyInstaller for .app |

Run the installer interactively:

```sh
./venv/bin/python3 installer.py          # CLI menu
./venv/bin/python3 installer.py --gui    # GUI (requires PySide6)
./venv/bin/python3 installer.py --os linux --format binary  # headless
```

## Project structure

```
ut99-bsp-extractor/
├── src/ut99bsp/          # Python package
│   ├── __init__.py       # public API
│   ├── extractor.py      # package reading + BSP extraction
│   ├── exporters.py      # OBJ/MTL + glTF writers
│   └── gui.py            # PySide6 GUI
├── rip_unr.py            # CLI script (imports from ut99bsp)
├── ut99_bsp_gui.py       # GUI script (imports from ut99bsp)
├── installer.py          # cross-platform installer / packager
├── pyproject.toml        # build config
├── install.sh            # one-step venv setup
├── run.sh                # GUI launcher
├── build.py              # PyInstaller packaging
└── requirements.txt      # PySide6 dependency
```

## How it works

1. Parses the UT99 package file format (header, name/import/export tables, compact indices)
2. Locates the Level export and follows its Model reference
3. Reads the Model's native data: bounding structures, then BSP arrays (Vectors, Points, Nodes, Surfaces, Verts)
4. Extracts polygon geometry by walking BSP nodes and computing UVs from texture axis vectors
5. Writes unique vertices, normals, and UVs to the requested format

### BSP structure

| Field | Type | Description |
|-------|------|-------------|
| `Vectors` | `TArray<FVector>` | Normal/axis vectors for surfaces |
| `Points` | `TArray<FVector>` | Actual vertex positions |
| `Nodes` | `TArray<FBspNode>` | BSP tree nodes with polygon references |
| `Surfaces` | `TArray<FBspSurface>` | Surface properties (texture, UV axes) |
| `Verts` | `TArray<FVert>` | Vertex-to-point mappings |

## Requirements

- Python 3.8+
- PySide6 >= 6.6 (GUI only; install with `pip install PySide6`)

## License

MIT
