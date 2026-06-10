# UT99 BSP Extractor

Extracts BSP polygon geometry from Unreal Tournament 99 `.unr` map files and exports to Wavefront OBJ (with MTL) or glTF 2.0 formats, with UV coordinates and vertex normals.

## Download

Grab the latest standalone executable from the [releases page](https://github.com/Moloch-Lab/ut99-bsp-extractor/releases) (Linux, 86 MB, no Python required).

## Usage

### GUI (recommended)

```sh
./run.sh
```

Drag & drop `.unr` files, select format, click **Extract All**. After extraction, click **Preview** to inspect the 3D geometry (drag to rotate, scroll to zoom).

### CLI

```sh
python rip_unr.py map.unr [output] -f {obj,objmtl,gltf}
```

Formats:
- `obj` — Wavefront OBJ (no material library)
- `objmtl` — OBJ + MTL (polygons grouped by texture)
- `gltf` — glTF 2.0 (`.gltf` + `.bin` with per-material mesh primitives)

Output defaults to `<mapname>.obj` in the current directory. glTF includes lightmap UVs as `TEXCOORD_1`.

### Batch

The GUI processes all dropped maps sequentially. For CLI batch:

```sh
for f in Maps/*.unr; do
    python rip_unr.py "$f" -f gltf
done
```

## How it works

1. Parses the UT99 package file format (header, name/import/export tables, compact indices)
2. Locates the Level export and follows its Model reference
3. Reads the Model's native data: bounding structures, then BSP arrays (Vectors, Points, Nodes, Surfaces, Verts)
4. Extracts polygon geometry by walking BSP nodes and computing UVs from texture axis vectors
5. Writes unique vertices, normals, and UVs to the requested format

## Structure

| Field | Type | Description |
|-------|------|-------------|
| `Vectors` | `TArray<FVector>` | Normal/axis vectors for surfaces |
| `Points` | `TArray<FVector>` | Actual vertex positions |
| `Nodes` | `TArray<FBspNode>` | BSP tree nodes with polygon references |
| `Surfaces` | `TArray<FBspSurface>` | Surface properties (texture, UV axes) |
| `Verts` | `TArray<FVert>` | Vertex-to-point mappings |

## Requirements (Python)

- Python 3.6+
- `PySide6>=6.6` (GUI only)

Install with: `pip install -r requirements.txt`

## Build standalone executable

```sh
python build.py
```

Requires PyInstaller (`pip install pyinstaller`). Output in `dist/UT99-BSP-Extractor`.

## License

MIT
