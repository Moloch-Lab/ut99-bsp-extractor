# UT99 BSP Extractor

Extracts BSP polygon geometry from Unreal Tournament 99 `.unr` map files and exports to Wavefront OBJ (with MTL) or glTF 2.0 formats, with UV coordinates and vertex normals.

## Quick Start

### Download (no Python required)

Grab the standalone executable for your platform from the [releases page](https://github.com/Moloch-Lab/ut99-bsp-extractor/releases):

| Platform | File |
|----------|------|
| Linux | `UT99-BSP-Extractor-linux` |
| Windows | `UT99-BSP-Extractor-windows.exe` |
| macOS | `UT99-BSP-Extractor-macos` |

Windows and macOS builds are produced automatically by [GitHub Actions](.github/workflows/build.yml) when a tag is pushed. Maintainers push a tag and the workflow builds on all three OS runners, then uploads the artifacts to the release.

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
| Linux | standalone binary, `.deb`, `.rpm`, AppImage, pip | `dpkg-deb` for .deb, `rpmbuild` for .rpm (optional) |
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
