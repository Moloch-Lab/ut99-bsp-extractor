"""
UT99 BSP Extractor — extract BSP geometry from Unreal Tournament 99 .unr files.
"""

from ut99bsp.extractor import (
    PackageReader,
    ModelReader,
    extract_polygons_from_model,
    extract_map,
    ExtractionResult,
    skip_properties,
    read_compact_index,
    export_map,
)

from ut99bsp.exporters import write_obj_mtl, write_gltf

from ut99bsp.textures import (
    UTXReader,
    TextureInfo,
    decode_texture,
    save_texture_png,
    find_texture_packages,
    extract_map_textures,
)


def main():
    """CLI entry point."""
    from ut99bsp.extractor import main as _cli_main
    import sys
    sys.exit(_cli_main())


__all__ = [
    "PackageReader",
    "ModelReader",
    "extract_polygons_from_model",
    "extract_map",
    "ExtractionResult",
    "skip_properties",
    "read_compact_index",
    "export_map",
    "write_obj_mtl",
    "write_gltf",
]
