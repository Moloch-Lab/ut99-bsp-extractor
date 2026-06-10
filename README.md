# UT99 BSP Extractor

Extracts BSP polygon geometry from Unreal Tournament 99 `.unr` map files and exports to Wavefront OBJ format with UV coordinates and vertex normals.

## Usage

```sh
python rip_unr.py path/to/DM-MyLevel.unr [output.obj]
```

If no output path is given, it defaults to `<mapname>.obj` in the current directory.

## How it works

1. Parses the UT99 package file format (header, name/import/export tables, compact indices)
2. Locates the Level export and follows its Model reference
3. Reads the Model's native data: bounding structures, then BSP arrays (Vectors, Points, Nodes, Surfaces, Verts)
4. Extracts polygon geometry by walking BSP nodes and computing UVs from texture axis vectors
5. Writes unique vertices, normals, and UVs to a valid OBJ file

## Structure

| Field | Type | Description |
|-------|------|-------------|
| `Vectors` | `TArray<FVector>` | Normal/axis vectors for surfaces |
| `Points` | `TArray<FVector>` | Actual vertex positions |
| `Nodes` | `TArray<FBspNode>` | BSP tree nodes with polygon references |
| `Surfaces` | `TArray<FBspSurface>` | Surface properties (texture, UV axes) |
| `Verts` | `TArray<FVert>` | Vertex-to-point mappings |

## Requirements

- Python 3.6+
- A UT99 map file (`.unr`)

## License

MIT
