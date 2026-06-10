#!/usr/bin/env python3
"""
UT99 Map Ripper — CLI entry point.

Usage:
    python rip_unr.py DM-MyLevel.unr [output.obj] -f {obj,objmtl,gltf}
"""

import sys
import argparse

from ut99bsp import extract_map


def main():
    parser = argparse.ArgumentParser(description="Extract BSP geometry from UT99 .unr files")
    parser.add_argument("map", help="Path to .unr map file")
    parser.add_argument("output", nargs="?", help="Output path (default: map name + ext)")
    parser.add_argument("-f", "--format", choices=["obj", "objmtl", "gltf"], default="obj",
                        help="Output format (default: obj)")
    parser.add_argument("--export-textures", action="store_true",
                        help="Extract .png textures from .utx packages")
    parser.add_argument("--no-geometry", action="store_true",
                        help="Skip geometry export (useful with --export-textures)")
    parser.add_argument("--no-texture-refs", action="store_true",
                        help="Omit texture references from output")
    args = parser.parse_args()

    def report(msg, pct):
        print(f"  [{pct}%] {msg}")

    try:
        result = extract_map(args.map, args.output, fmt=args.format,
                              export_geometry=not args.no_geometry,
                              export_textures=args.export_textures,
                              include_texture_refs=not args.no_texture_refs,
                              progress_callback=report)
        print(f"\nDone! {result.polygons} polygons -> {result.output_path}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
