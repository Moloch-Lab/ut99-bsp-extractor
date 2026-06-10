# UT99 BSP Extractor

Extracts BSP polygon geometry from Unreal Tournament 99 `.unr` map files and exports to Wavefront OBJ (with MTL) or glTF 2.0 formats, with UV coordinates and vertex normals.

## Quick Start

### Download (no Python required)

Grab the standalone executable from the [releases page](https://github.com/Moloch-Lab/ut99-bsp-extractor/releases) (Linux, 86 MB).

### Install from source

```sh
git clone https://github.com/Moloch-Lab/ut99-bsp-extractor.git
cd ut99-bsp-extractor
./install.sh              # creates venv + installs package
./run.sh                  # launch GUI
```

Or install manually:

```sh
python3 -m venv venv
venv/bin/pip install .    # installs the ut99bsp package + CLI entry points
venv/bin/pip install PySide6  # GUI only
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

### Batch

The GUI processes all dropped maps sequentially. For CLI batch:

```sh
for f in Maps/*.unr; do
    ut99-bsp-extractor "$f" -f gltf
done
```

### Python API

```python
from ut99bsp import extract_map

result = extract_map("DM-MyLevel.unr", "output.obj", fmt="objmtl")
print(f"{result.polygons} polygons written to {result.output_path}")
# result.triangles -> list of 3-tuples for preview
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
├── pyproject.toml        # build config
├── install.sh            # one-step install script
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

## Build standalone executable

```sh
python build.py    # requires PyInstaller; output in dist/
```

## Requirements

- Python 3.8+
- PySide6 >= 6.6 (GUI only; install with `pip install PySide6`)

## License

MIT
