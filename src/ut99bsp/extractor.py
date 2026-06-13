#!/usr/bin/env python3
"""
UT99 Map Ripper - Extracts BSP geometry from Unreal Tournament 99 .unr files to OBJ format.

Usage:
    python rip_unr.py DM-MyLevel.unr [output.obj]

Extracts all BSP polygon geometry with UV coordinates and normals.
"""

import struct
import os
import sys
import math

MAGIC = 0x9E2A83C1


# ── Compact Index ──────────────────────────────────────────────────────

def read_compact_index(data, offset):
    b = data[offset]
    is_negative = (b >> 7) & 1     # bit7 = sign
    read_next = (b >> 6) & 1       # bit6 = more bytes follow
    value = b & 0x3F
    offset += 1
    for byte_num in range(1, 5):
        if not read_next:
            break
        b = data[offset]
        read_next = (b >> 7) & 1
        bit_count = 7 if byte_num < 4 else 8
        mask = (1 << bit_count) - 1
        value |= (b & mask) << (6 + (byte_num - 1) * 7)
        offset += 1
    if is_negative:
        value = -value
    return value, offset


# ── Property Skip ─────────────────────────────────────────────────────

def skip_properties_old(data, offset):
    """Skip properties using CI-based format (for older packages)."""
    while offset < len(data):
        name, offset = read_compact_index(data, offset)
        if name == 0:
            break
        typ, offset = read_compact_index(data, offset)
        size, offset = read_compact_index(data, offset)
        offset += size
    return offset


PROP_TYPE_NAMES = [
    "Unknown", "Byte", "Integer", "Boolean", "Float", "Object",
    "Name", "String", "Class", "Array", "Struct", "Vector",
    "Rotator", "Str", "Map", "Fixed Array",
]


def skip_properties(data, offset, name_resolver=None):
    """Skip UE1 properties (1-byte flags format)."""
    while offset < len(data):
        name_ci, offset = read_compact_index(data, offset)
        if name_resolver:
            if name_resolver(name_ci) == "None":
                break
        elif name_ci == 0:
            break
        info_byte = data[offset]
        offset += 1
        prop_type = PROP_TYPE_NAMES[info_byte & 0xF] if (info_byte & 0xF) < len(PROP_TYPE_NAMES) else "Unknown"
        is_array = bool(info_byte >> 7)
        size_info = (info_byte >> 4) & 0x7
        if size_info == 0:
            prop_size = 1
        elif size_info == 1:
            prop_size = 2
        elif size_info == 2:
            prop_size = 4
        elif size_info == 3:
            prop_size = 12
        elif size_info == 4:
            prop_size = 16
        elif size_info == 5:
            prop_size = data[offset]
            offset += 1
        elif size_info == 6:
            prop_size = struct.unpack('<H', data[offset:offset+2])[0]
            offset += 2
        elif size_info == 7:
            prop_size = struct.unpack('<I', data[offset:offset+4])[0]
            offset += 4
        else:
            prop_size = 1
        if prop_type == "Struct":
            sub_type, _ = read_compact_index(data, offset)
        offset += prop_size

    return offset


# ── Structure Readers ─────────────────────────────────────────────────

def read_fvector(data, offset):
    x, y, z = struct.unpack('<fff', data[offset:offset+12])
    return (x, y, z), offset + 12


class ModelReader:
    """Reads a UModel's native data section."""

    def __init__(self, data, offset=0, version=68):
        self.data = data
        self.offset = offset
        self.version = version

    def read_ci(self):
        v, self.offset = read_compact_index(self.data, self.offset)
        return v

    def read_u8(self):
        v = self.data[self.offset]
        self.offset += 1
        return v

    def read_u16(self):
        v = struct.unpack('<H', self.data[self.offset:self.offset+2])[0]
        self.offset += 2
        return v

    def read_i16(self):
        v = struct.unpack('<h', self.data[self.offset:self.offset+2])[0]
        self.offset += 2
        return v

    def read_u32(self):
        v = struct.unpack('<I', self.data[self.offset:self.offset+4])[0]
        self.offset += 4
        return v

    def read_i32(self):
        v = struct.unpack('<i', self.data[self.offset:self.offset+4])[0]
        self.offset += 4
        return v

    def read_f32(self):
        v = struct.unpack('<f', self.data[self.offset:self.offset+4])[0]
        self.offset += 4
        return v

    def read_u64(self):
        v = struct.unpack('<Q', self.data[self.offset:self.offset+8])[0]
        self.offset += 8
        return v

    def read_vector(self):
        x = self.read_f32()
        y = self.read_f32()
        z = self.read_f32()
        return (x, y, z)

    def read_tarray(self, reader_method):
        count = self.read_ci()
        if reader_method is None:
            self.offset += count
            return count
        result = []
        for _ in range(count):
            result.append(reader_method())
        return result

    def read_bbox(self):
        mn = self.read_vector()
        mx = self.read_vector()
        valid = self.read_u8() != 0
        return (mn, mx, valid)

    def read_bsphere(self):
        centre = self.read_vector()
        if self.version > 61:
            radius = self.read_f32()
        else:
            radius = None
        return (centre, radius)

    def read_bsp_node(self):
        plane = (self.read_f32(), self.read_f32(), self.read_f32(), self.read_f32())
        zone_mask = self.read_u64()
        node_flags = self.read_u8()
        i_vert_pool = self.read_ci()
        i_surf = self.read_ci()
        i_front = self.read_ci()
        i_back = self.read_ci()
        i_plane = self.read_ci()
        i_collision_bound = self.read_ci()
        i_render_bound = self.read_ci()
        i_zone0 = self.read_ci()
        i_zone1 = self.read_ci()
        num_vertices = self.read_u8()
        i_leaf0 = self.read_u32()
        i_leaf1 = self.read_u32()
        return {
            'plane': plane,
            'zone_mask': zone_mask,
            'node_flags': node_flags,
            'i_vert_pool': i_vert_pool,
            'i_surf': i_surf,
            'i_front': i_front,
            'i_back': i_back,
            'i_plane': i_plane,
            'i_collision_bound': i_collision_bound,
            'i_render_bound': i_render_bound,
            'i_zone': (i_zone0, i_zone1),
            'num_vertices': num_vertices,
            'i_leaf': (i_leaf0, i_leaf1),
        }

    def read_surface(self):
        texture = self.read_ci()
        poly_flags = self.read_u32()
        p_base = self.read_ci()
        v_normal = self.read_ci()
        v_texture_u = self.read_ci()
        v_texture_v = self.read_ci()
        i_light_map = self.read_ci()
        i_brush_poly = self.read_ci()
        pan_u = self.read_i16()
        pan_v = self.read_i16()
        actor = self.read_ci()
        return {
            'texture': texture,
            'poly_flags': poly_flags,
            'p_base': p_base,
            'v_normal': v_normal,
            'v_texture_u': v_texture_u,
            'v_texture_v': v_texture_v,
            'i_light_map': i_light_map,
            'i_brush_poly': i_brush_poly,
            'pan_u': pan_u,
            'pan_v': pan_v,
            'actor': actor,
        }

    def read_vertex(self):
        vert = self.read_ci()
        side = self.read_ci()
        return {'vertex': vert, 'i_side': side}

    def read_model(self):
        bbox = self.read_bbox()
        bsphere = self.read_bsphere()

        vectors = self.read_tarray(self.read_vector)
        points = self.read_tarray(self.read_vector)
        nodes = self.read_tarray(self.read_bsp_node)
        surfaces = self.read_tarray(self.read_surface)
        verts = self.read_tarray(self.read_vertex)

        num_shared_sides = self.read_i32()
        num_zones = self.read_i32()
        zones = []
        for _ in range(num_zones):
            zones.append({'zone_actor': self.read_ci(),
                          'connectivity': self.read_u64(),
                          'visibility': self.read_u64()})
            if self.version < 63:
                self.read_f32()

        polys = self.read_ci()
        light_maps_count = self.read_ci()
        self.offset += light_maps_count
        light_bits_count = self.read_ci()
        self.offset += light_bits_count
        bounds_count = self.read_ci()
        self.offset += bounds_count * 25
        leaf_hulls_count = self.read_ci()
        self.offset += leaf_hulls_count * 4
        leaves_count = self.read_ci()
        self.offset += leaves_count * (8 + 8 + 8 + 8)
        lights_count = self.read_ci()
        self.offset += lights_count

        self.read_u32()
        self.read_u32()

        return {
            'vectors': vectors,
            'points': points,
            'verts': verts,
            'nodes': nodes,
            'surfaces': surfaces,
            'bbox': bbox,
        }


# ── BSP Extraction ───────────────────────────────────────────────────

def compute_uv(vertex, base, tex_u, tex_v):
    dx = vertex[0] - base[0]
    dy = vertex[1] - base[1]
    dz = vertex[2] - base[2]
    u = dx * tex_u[0] + dy * tex_u[1] + dz * tex_u[2]
    v = dx * tex_v[0] + dy * tex_v[1] + dz * tex_v[2]
    return u, -v


def extract_polygons_from_model(model):
    polygons = []
    vectors = model['vectors']
    points = model['points']
    for ni, node in enumerate(model['nodes']):
        nv = node['num_vertices']
        if nv < 3:
            continue
        if node['i_surf'] >= len(model['surfaces']):
            continue
        surf = model['surfaces'][node['i_surf']]
        if (surf['v_normal'] >= len(vectors) or surf['p_base'] >= len(vectors) or
            surf['v_texture_u'] >= len(vectors) or surf['v_texture_v'] >= len(vectors)):
            continue
        normal = vectors[surf['v_normal']]
        base = vectors[surf['p_base']]
        tex_u = vectors[surf['v_texture_u']]
        tex_v = vectors[surf['v_texture_v']]

        vert_positions = []
        vert_uvs = []
        for vi in range(nv):
            if node['i_vert_pool'] + vi >= len(model['verts']):
                break
            fv = model['verts'][node['i_vert_pool'] + vi]
            if fv['vertex'] >= len(points):
                break
            pos = points[fv['vertex']]
            u, v = compute_uv(pos, base, tex_u, tex_v)
            vert_positions.append(pos)
            vert_uvs.append((u, v))

        if len(vert_positions) >= 3:
            # Lightmap UVs use the same tangent-space projection
            uv2 = [(u, v) for u, v in vert_uvs]
            polygons.append({
                'vertices': vert_positions,
                'uvs': vert_uvs,
                'uv2': uv2,
                'normal': normal,
                'node_index': ni,
                'surf_index': node['i_surf'],
                'pan_u': surf['pan_u'],
                'pan_v': surf['pan_v'],
            })
    return polygons


# ── OBJ Export ────────────────────────────────────────────────────────

def export_obj(polygons, output_path):
    if not polygons:
        print("  No polygons to export.", file=sys.stderr)
        return

    lines = [f"# UT99 Map Export\n# Polygons: {len(polygons)}\n"]

    unique_verts = {}
    unique_uvs = {}
    unique_normals = {}
    vert_map = {}
    vi = uvi = ni = 0

    for poly in polygons:
        for i in range(len(poly['vertices'])):
            pos = poly['vertices'][i]
            uv = poly['uvs'][i]
            nrm = poly['normal']
            key = (pos, uv, nrm)

            if pos not in unique_verts:
                unique_verts[pos] = vi
                vx, vy, vz = pos
                lines.append(f"v {vx:.6f} {vy:.6f} {vz:.6f}")
                vi += 1
            if uv not in unique_uvs:
                unique_uvs[uv] = uvi
                ux, uy = uv
                lines.append(f"vt {ux:.6f} {uy:.6f} 0.000000")
                uvi += 1
            if nrm not in unique_normals:
                unique_normals[nrm] = ni
                nx, ny, nz = nrm
                length = math.sqrt(nx*nx + ny*ny + nz*nz)
                if length > 0:
                    nx, ny, nz = nx/length, ny/length, nz/length
                else:
                    nx, ny, nz = 0.0, 0.0, 1.0
                lines.append(f"vn {nx:.6f} {ny:.6f} {nz:.6f}")
                ni += 1
            vert_map[key] = (unique_verts[pos], unique_uvs[uv], unique_normals[nrm])

    lines.append("")

    for pi, poly in enumerate(polygons):
        lines.append(f"g poly_{pi}")
        face_indices = []
        for i in range(len(poly['vertices'])):
            pos = poly['vertices'][i]
            uv = poly['uvs'][i]
            nrm = poly['normal']
            key = (pos, uv, nrm)
            vi_idx, uvi_idx, ni_idx = vert_map[key]
            face_indices.append(f"{vi_idx+1}/{uvi_idx+1}/{ni_idx+1}")
        lines.append(f"f {' '.join(face_indices)}")

    with open(output_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print(f"  Wrote {len(unique_verts)} vertices, {len(unique_normals)} normals, "
          f"{len(unique_uvs)} UVs, {len(polygons)} polygons")
    print(f"  -> {output_path}")


# ── Package Reader ────────────────────────────────────────────────────

class PackageReader:
    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            self.data = f.read()
        self.names = []
        self.imports = []
        self.exports = []
        self._read_header()
        self._read_name_table()
        self._read_import_table()
        self._read_export_table()

    def _read_header(self):
        magic, ver, lic_mode, flags, \
            nc, no, ec, eo, ic, io = struct.unpack('<IIHHIIIIII', self.data[:36])
        if magic != MAGIC:
            raise ValueError(f"Not a UT99 package (magic: {magic:#010x})")
        self.version = ver
        self.license_mode = lic_mode
        self.flags = flags
        self.name_count = nc
        self.name_offset = no
        self.export_count = ec
        self.export_offset = eo
        self.import_count = ic
        self.import_offset = io

    def _read_name_table(self):
        self.names = []
        offset = self.name_offset
        for _ in range(self.name_count):
            length, offset = read_compact_index(self.data, offset)
            raw = self.data[offset:offset + length]
            name = raw.decode('windows-1252', errors='replace').rstrip('\0')
            offset += length
            flags = struct.unpack('<I', self.data[offset:offset + 4])[0]
            offset += 4
            self.names.append((name, flags))

    def _read_import_table(self):
        self.imports = []
        offset = self.import_offset
        for _ in range(self.import_count):
            cp, offset = read_compact_index(self.data, offset)
            cn, offset = read_compact_index(self.data, offset)
            pi = struct.unpack('<I', self.data[offset:offset + 4])[0]
            offset += 4
            on, offset = read_compact_index(self.data, offset)
            self.imports.append({'class_package': cp, 'class_name': cn,
                                 'package_index': pi, 'name_index': on})

    def _read_export_table(self):
        self.exports = []
        offset = self.export_offset
        for _ in range(self.export_count):
            ci, offset = read_compact_index(self.data, offset)
            si, offset = read_compact_index(self.data, offset)
            pi = struct.unpack('<I', self.data[offset:offset + 4])[0]
            offset += 4
            ni, offset = read_compact_index(self.data, offset)
            of = struct.unpack('<I', self.data[offset:offset + 4])[0]
            offset += 4
            ss, offset = read_compact_index(self.data, offset)
            so, offset = read_compact_index(self.data, offset)
            self.exports.append({
                'class_idx': ci, 'super_idx': si, 'pkg_idx': pi,
                'name_idx': ni, 'flags': of, 'serial_size': ss, 'serial_offset': so
            })

    def resolve_name(self, idx):
        if 0 <= idx < len(self.names):
            return self.names[idx][0]
        return f"Name_{idx}"

    def resolve_object_name(self, idx):
        if idx == 0:
            return "None"
        if idx > 0:
            e = idx - 1
            if e < len(self.exports):
                return self.resolve_name(self.exports[e]['name_idx'])
        if idx < 0:
            i = -idx - 1
            if i < len(self.imports):
                return self.resolve_name(self.imports[i]['name_index'])
        return f"Obj_{idx}"

    def resolve_texture_name(self, idx):
        if idx == 0:
            return None
        if idx > 0:
            e = idx - 1
            if e < len(self.exports):
                return self.resolve_name(self.exports[e]['name_idx'])
        if idx < 0:
            ci = -idx - 1
            if ci < len(self.imports):
                imp = self.imports[ci]
                cp = self.resolve_name(imp['class_package'])
                cn = self.resolve_name(imp['class_name'])
                return f"{cp}.{cn}"
        return None

    def get_export_data(self, idx):
        if idx < 0 or idx >= len(self.exports):
            return None
        e = self.exports[idx]
        if e['serial_size'] == 0 or e['serial_offset'] < 0:
            return None
        return self.data[e['serial_offset']:e['serial_offset'] + e['serial_size']]


def main():
    import argparse
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



# ── Library API ────────────────────────────────────────────────────────

class ExtractionResult:
    def __init__(self):
        self.map_name = ""
        self.version = 0
        self.names_count = 0
        self.exports_count = 0
        self.imports_count = 0
        self.model_name = ""
        self.vectors = 0
        self.points = 0
        self.nodes = 0
        self.surfaces = 0
        self.verts = 0
        self.polygons = 0
        self.polygons_data = []
        self.triangles = []
        self.output_path = ""
        self.format = "obj"
        self.textures_extracted = 0


def export_map(polygons, output_path, fmt="obj", include_texture_refs=True):
    """Write geometry in the requested format.  Returns output_path."""
    from ut99bsp.exporters import write_obj_mtl, write_gltf

    if fmt == "obj":
        return write_obj_mtl(polygons, output_path, include_texture_refs=include_texture_refs)
    elif fmt == "objmtl":
        return write_obj_mtl(polygons, output_path, include_texture_refs=include_texture_refs)
    elif fmt == "gltf":
        return write_gltf(polygons, output_path, include_texture_refs=include_texture_refs)
    else:
        raise ValueError(f"Unknown format: {fmt}")


def extract_map(map_path, output_path=None, fmt="obj", progress_callback=None,
                export_geometry=True, export_textures=False, include_texture_refs=True):
    """Full extraction pipeline.
    fmt: 'obj', 'objmtl', 'gltf'
    export_geometry: write polygon mesh
    export_textures: extract .png from .utx packages
    include_texture_refs: include material/texture references in output
    """
    result = ExtractionResult()
    result.format = fmt
    result.map_name = os.path.basename(map_path)

    def report(msg, pct=None):
        if progress_callback:
            progress_callback(msg, pct)

    report("Reading package...", 0)
    pkg = PackageReader(map_path)
    result.version = pkg.version
    result.names_count = pkg.name_count
    result.exports_count = pkg.export_count
    result.imports_count = pkg.import_count

    ext_map = {"obj": ".obj", "objmtl": ".obj", "gltf": ".gltf"}
    default_ext = ext_map.get(fmt, ".obj")
    if not output_path:
        output_path = os.path.splitext(map_path)[0] + default_ext

    if export_textures:
        tex_dir = os.path.join(os.path.dirname(output_path) or ".", "textures")
        os.makedirs(tex_dir, exist_ok=True)
        report(f"Extracting textures to {tex_dir}...", 3)
        from ut99bsp.textures import extract_map_textures as _extract_tex
        tex_list = _extract_tex(map_path, tex_dir, progress=report)
        result.textures_extracted = len(tex_list)
        if tex_list:
            report(f"Saved {len(tex_list)} textures to {tex_dir}", 5)
        else:
            report("No textures found", 5)

    if not export_geometry:
        result.output_path = output_path
        report("Done!", 100)
        return result

    report("Locating Level...", 10)
    level_idx = None
    for idx, exp in enumerate(pkg.exports):
        if pkg.resolve_object_name(exp['class_idx']) == "Level":
            level_idx = idx
            break
    if level_idx is None:
        raise ValueError("No Level export found in package.")

    data = pkg.get_export_data(level_idx)
    if data is None:
        raise ValueError("Level export has no data.")

    report("Parsing Level data...", 15)
    off = skip_properties(data, 0, pkg.resolve_name)
    if off >= len(data):
        raise ValueError("Level data too short after properties.")

    actors_count = struct.unpack('<I', data[off:off+4])[0]
    off += 8
    for _ in range(actors_count):
        v, off = read_compact_index(data, off)

    def skip_sized_text(d, o):
        if o >= len(d):
            return o, ""
        sz = d[o]
        text = d[o+1:o+1+sz].decode('windows-1252', errors='replace').rstrip('\0')
        return o + 1 + sz, text

    off, _ = skip_sized_text(data, off)
    off, _ = skip_sized_text(data, off)
    off, _ = skip_sized_text(data, off)
    opt_count, off = read_compact_index(data, off)
    for _ in range(opt_count):
        off, _ = skip_sized_text(data, off)
    off, _ = skip_sized_text(data, off)
    off += 8

    model_ref, _ = read_compact_index(data, off)
    if model_ref <= 0:
        raise ValueError("Level has no Model reference.")

    model_idx = model_ref - 1
    if model_idx >= len(pkg.exports):
        raise ValueError(f"Model reference {model_ref} out of range.")

    model_name = pkg.resolve_name(pkg.exports[model_idx]['name_idx'])
    result.model_name = model_name

    report(f"Reading Model ({model_name})...", 30)
    model_data = pkg.get_export_data(model_idx)
    if model_data is None:
        raise ValueError("Model has no data.")

    model_off = skip_properties(model_data, 0, pkg.resolve_name)

    report("Parsing BSP structures...", 40)
    reader = ModelReader(model_data, model_off, pkg.version)
    model_obj = reader.read_model()

    result.vectors = len(model_obj['vectors'])
    result.points = len(model_obj['points'])
    result.nodes = len(model_obj['nodes'])
    result.surfaces = len(model_obj['surfaces'])
    result.verts = len(model_obj['verts'])

    if len(model_obj['nodes']) == 0:
        raise ValueError("No BSP nodes found in model.")

    report("Extracting polygons...", 60)
    polygons = extract_polygons_from_model(model_obj)
    result.polygons = len(polygons)
    result.polygons_data = polygons

    # Attach texture names to polygons
    for p in polygons:
        si = p['surf_index']
        if si < len(model_obj['surfaces']):
            tex_idx = model_obj['surfaces'][si]['texture']
            p['texture_name'] = pkg.resolve_texture_name(tex_idx) if include_texture_refs else None
        else:
            p['texture_name'] = None

    # Build triangle list for preview
    for p in polygons:
        verts = p['vertices']
        for i in range(1, len(verts) - 1):
            result.triangles.append((verts[0], verts[i], verts[i + 1]))

    if not polygons:
        raise ValueError("No polygons extracted from model.")

    report(f"Writing {fmt.upper()}...", 80)
    export_map(polygons, output_path, fmt, include_texture_refs=include_texture_refs)
    result.output_path = output_path

    report("Done!", 100)
    return result


def main():
    """CLI entry point for `ut99-bsp-extractor`."""
    import argparse
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


if __name__ == '__main__':
    sys.exit(main())
