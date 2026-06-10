"""OBJ+MTL and glTF exporters for UT99 BSP geometry."""

import os
import math
import json
import struct
from collections import defaultdict


# ── helpers ─────────────────────────────────────────────────────────

def _normalize(v):
    x, y, z = v
    length = math.sqrt(x*x + y*y + z*z)
    if length > 0:
        return (x/length, y/length, z/length)
    return (0.0, 0.0, 1.0)


def _group_by_texture(polygons):
    groups = defaultdict(list)
    for p in polygons:
        key = p.get('texture_name') or "_null"
        groups[key].append(p)
    return groups


# ── OBJ + MTL ──────────────────────────────────────────────────────

def write_obj_mtl(polygons, base_path, include_texture_refs=True):
    """Write .obj + .mtl pair.  base_path is the .obj path (e.g. map.obj)."""
    obj_path = base_path
    mtl_path = os.path.splitext(base_path)[0] + ".mtl"
    mtl_rel = os.path.basename(mtl_path)

    groups = _group_by_texture(polygons)

    unique_verts = {}
    unique_uvs = {}
    unique_normals = {}
    unique_uv2s = {}
    vert_map = {}
    vi = uvi = ni = uv2i = 0

    obj_lines = [f"# UT99 Map Export\n# Polygons: {len(polygons)}\n"]
    if include_texture_refs:
        obj_lines[0] = f"# UT99 Map Export\n# Polygons: {len(polygons)}\nmtllib {mtl_rel}\n"

    # Pass 1: collect unique vert/uv/normal combos
    for poly in polygons:
        for i in range(len(poly['vertices'])):
            pos = poly['vertices'][i]
            uv = poly['uvs'][i]
            nrm = poly['normal']
            uv2 = poly.get('uv_lightmap', (0.0, 0.0))
            key = (pos, uv, nrm, uv2)

            if pos not in unique_verts:
                unique_verts[pos] = vi
                vx, vy, vz = pos
                obj_lines.append(f"v {vx:.6f} {vy:.6f} {vz:.6f}")
                vi += 1
            if uv not in unique_uvs:
                unique_uvs[uv] = uvi
                ux, uy = uv
                obj_lines.append(f"vt {ux:.6f} {uy:.6f} 0.000000")
                uvi += 1
            if uv2 not in unique_uv2s:
                unique_uv2s[uv2] = uv2i
                ux, uy = uv2
                obj_lines.append(f"vt {ux:.6f} {uy:.6f} 0.000000")
                uv2i += 1
            if nrm not in unique_normals:
                unique_normals[nrm] = ni
                nx, ny, nz = _normalize(nrm)
                obj_lines.append(f"vn {nx:.6f} {ny:.6f} {nz:.6f}")
                ni += 1
            vert_map[key] = (unique_verts[pos], unique_uvs[uv], unique_normals[nrm])

    obj_lines.append("")

    # Pass 2: write faces
    if include_texture_refs:
        used_materials = set()
        for tex_name, tex_polys in sorted(groups.items()):
            mat_name = tex_name.replace(".", "_").replace("/", "_") if tex_name != "_null" else "null"
            obj_lines.append(f"usemtl {mat_name}")
            used_materials.add(tex_name)
            for poly in tex_polys:
                face = []
                for i in range(len(poly['vertices'])):
                    pos = poly['vertices'][i]
                    uv = poly['uvs'][i]
                    nrm = poly['normal']
                    uv2 = poly.get('uv_lightmap', (0.0, 0.0))
                    key = (pos, uv, nrm, uv2)
                    v_idx, vt_idx, vn_idx = vert_map[key]
                    face.append(f"{v_idx+1}/{vt_idx+1}/{vn_idx+1}")
                obj_lines.append(f"f {' '.join(face)}")
            obj_lines.append("")
    else:
        used_materials = set()
        for poly in polygons:
            face = []
            for i in range(len(poly['vertices'])):
                pos = poly['vertices'][i]
                uv = poly['uvs'][i]
                nrm = poly['normal']
                uv2 = poly.get('uv_lightmap', (0.0, 0.0))
                key = (pos, uv, nrm, uv2)
                v_idx, vt_idx, vn_idx = vert_map[key]
                face.append(f"{v_idx+1}/{vt_idx+1}/{vn_idx+1}")
            obj_lines.append(f"f {' '.join(face)}")
        obj_lines.append("")

    with open(obj_path, 'w') as f:
        f.write('\n'.join(obj_lines) + '\n')

    # Write MTL (only if texture refs enabled)
    if include_texture_refs:
        mtl_lines = [f"# UT99 Map Materials\n"]
        for tex_name in sorted(used_materials):
            mat_name = tex_name.replace(".", "_").replace("/", "_") if tex_name != "_null" else "null"
            tex_file = tex_name.replace('.', '/') if tex_name != "_null" else ""
            mtl_lines.append(f"newmtl {mat_name}")
            mtl_lines.append("Kd 0.8 0.8 0.8")
            mtl_lines.append("Ka 0.2 0.2 0.2")
            mtl_lines.append("Ks 0.0 0.0 0.0")
            mtl_lines.append("d 1.0")
            mtl_lines.append("illum 2")
            if tex_name and tex_name != "_null":
                tex_filename = tex_name.replace('.', '_') + ".png"
                mtl_lines.append(f"map_Kd {tex_filename}")
            mtl_lines.append("")

        with open(mtl_path, 'w') as f:
            f.write('\n'.join(mtl_lines) + '\n')
    else:
        # Still write a minimal .obj with geometry only
        pass

    print(f"  Wrote {len(unique_verts)} v, {len(unique_uvs)} vt, {len(unique_normals)} vn, "
          f"{len(polygons)} polys -> {obj_path} + .mtl")
    return obj_path


# ── glTF 2.0 ────────────────────────────────────────────────────────

def _gltf_component_type(typ):
    return {
        'float': 5126,
        'vec2': 5126,
        'vec3': 5126,
    }.get(typ, 5126)


def _gltf_type_str(typ):
    return {
        'scalar': "SCALAR",
        'vec2': "VEC2",
        'vec3': "VEC3",
        'vec4': "VEC4",
    }.get(typ, "SCALAR")


def write_gltf(polygons, output_path, include_texture_refs=True):
    """Write a .gltf + .bin pair."""
    groups = _group_by_texture(polygons)
    bin_path = os.path.splitext(output_path)[0] + ".bin"
    bin_rel = os.path.basename(bin_path)

    # Collect unique data per material group
    mesh_data = {}  # mat_name -> {positions, normals, uvs, indices}
    mat_names = []
    mat_map = {}  # tex_name -> mat_name

    for tex_name in sorted(groups):
        mat_name = tex_name.replace(".", "_").replace("/", "_") if tex_name != "_null" else "null"
        mat_names.append(mat_name)
        mat_map[tex_name] = mat_name
        mesh_data[mat_name] = {
            'positions': [],
            'normals': [],
            'uvs': [],
            'uv2': [],
            'indices': [],
            'vert_map': {},
        }

    # Build per-material vertex/index arrays
    for tex_name, tex_polys in sorted(groups.items()):
        mat_name = mat_map[tex_name]
        md = mesh_data[mat_name]
        for poly in tex_polys:
            nv = len(poly['vertices'])
            if nv < 3:
                continue
            # Store all vertices first, then emit triangle fan indices
            vert_ids = []
            for i in range(nv):
                pos = poly['vertices'][i]
                nrm = poly['normal']
                uv = poly['uvs'][i]
                uv2 = poly['uv2'][i] if 'uv2' in poly else uv
                vert = (pos, nrm, uv)
                if vert not in md['vert_map']:
                    md['vert_map'][vert] = len(md['positions'])
                    md['positions'].append(pos)
                    md['normals'].append(nrm)
                    md['uvs'].append(uv)
                    md['uv2'].append(uv2)
                vert_ids.append(md['vert_map'][vert])
            # Triangle fan: (0,1,2), (0,2,3), (0,3,4), ...
            for i in range(1, nv - 1):
                md['indices'].extend([vert_ids[0], vert_ids[i], vert_ids[i + 1]])

    # Build binary buffer
    buffer = bytearray()
    accessors = []
    buffer_views = []

    for mat_name in mat_names:
        md = mesh_data[mat_name]
        if not md['positions']:
            continue
        nverts = len(md['positions'])
        nindices = len(md['indices'])

        # Positions (3 floats per vertex)
        pos_offset = len(buffer)
        for v in md['positions']:
            buffer.extend(struct.pack('<fff', *v))
        view_idx = len(buffer_views)
        buffer_views.append({
            'buffer': 0,
            'byteOffset': pos_offset,
            'byteLength': nverts * 12,
        })
        accessors.append({
            'bufferView': view_idx,
            'componentType': 5126,
            'count': nverts,
            'type': "VEC3",
            'min': [min(v[0] for v in md['positions']),
                    min(v[1] for v in md['positions']),
                    min(v[2] for v in md['positions'])],
            'max': [max(v[0] for v in md['positions']),
                    max(v[1] for v in md['positions']),
                    max(v[2] for v in md['positions'])],
        })
        pos_accessor = len(accessors) - 1

        # Normals (3 floats per vertex)
        nrm_offset = len(buffer)
        for v in md['normals']:
            nx, ny, nz = _normalize(v)
            buffer.extend(struct.pack('<fff', nx, ny, nz))
        buffer_views.append({
            'buffer': 0,
            'byteOffset': nrm_offset,
            'byteLength': nverts * 12,
        })
        accessors.append({
            'bufferView': len(buffer_views) - 1,
            'componentType': 5126,
            'count': nverts,
            'type': "VEC3",
        })
        nrm_accessor = len(accessors) - 1

        # UVs (2 floats per vertex)
        uv_offset = len(buffer)
        for v in md['uvs']:
            buffer.extend(struct.pack('<ff', v[0], v[1]))
        buffer_views.append({
            'buffer': 0,
            'byteOffset': uv_offset,
            'byteLength': nverts * 8,
        })
        accessors.append({
            'bufferView': len(buffer_views) - 1,
            'componentType': 5126,
            'count': nverts,
            'type': "VEC2",
        })
        uv_accessor = len(accessors) - 1

        # Lightmap UVs (2 floats per vertex)
        lm_offset = len(buffer)
        for v in md['uv2']:
            buffer.extend(struct.pack('<ff', v[0], v[1]))
        buffer_views.append({
            'buffer': 0,
            'byteOffset': lm_offset,
            'byteLength': nverts * 8,
        })
        accessors.append({
            'bufferView': len(buffer_views) - 1,
            'componentType': 5126,
            'count': nverts,
            'type': "VEC2",
        })
        lm_accessor = len(accessors) - 1

        # Indices (uint16)
        idx_offset = len(buffer)
        for i in range(0, nindices, 3):
            buffer.extend(struct.pack('<HHH', md['indices'][i], md['indices'][i+1], md['indices'][i+2]))
        buffer_views.append({
            'buffer': 0,
            'byteOffset': idx_offset,
            'byteLength': nindices * 2,
        })
        accessors.append({
            'bufferView': len(buffer_views) - 1,
            'componentType': 5123,
            'count': nindices,
            'type': "SCALAR",
        })
        idx_accessor = len(accessors) - 1

        # Store primitive info for the mesh
        if not hasattr(write_gltf, '_primitives'):
            write_gltf._primitives = []
        write_gltf._primitives.append({
            'attributes': {
                'POSITION': pos_accessor,
                'NORMAL': nrm_accessor,
                'TEXCOORD_0': uv_accessor,
                'TEXCOORD_1': lm_accessor,
            },
            'indices': idx_accessor,
            'material': mat_names.index(mat_name),
        })

    primitives = getattr(write_gltf, '_primitives', [])
    write_gltf._primitives = []

    # Write binary
    with open(bin_path, 'wb') as f:
        f.write(buffer)

    # Build glTF JSON
    mat_index = 0
    materials = []
    textures = []
    images = []
    for tex_name in sorted(groups):
        mat_name = tex_name.replace(".", "_").replace("/", "_") if tex_name != "_null" else "null"
        mat = {
            'name': mat_name,
            'pbrMetallicRoughness': {
                'baseColorFactor': [0.8, 0.8, 0.8, 1.0],
                'metallicFactor': 0.0,
                'roughnessFactor': 0.8,
            },
        }
        if include_texture_refs and tex_name and tex_name != "_null":
            tex_filename = tex_name.replace('.', '_') + ".png"
            mat['pbrMetallicRoughness']['baseColorTexture'] = {
                'index': mat_index,
            }
            textures.append({
                'name': tex_filename,
                'source': len(images),
            })
            images.append({'uri': tex_filename})
        materials.append(mat)
        mat_index += 1

    doc = {
        'asset': {'version': "2.0", 'generator': "UT99 BSP Extractor"},
        'scene': 0,
        'scenes': [{'nodes': [0]}],
        'nodes': [{'mesh': 0}],
        'meshes': [{
            'primitives': primitives,
        }],
        'accessors': accessors,
        'bufferViews': buffer_views,
        'buffers': [{
            'uri': bin_rel,
            'byteLength': len(buffer),
        }],
        'materials': materials,
    }
    if textures:
        doc['textures'] = textures
    if images:
        doc['images'] = images
    if textures:
        doc['samplers'] = [{'magFilter': 9729, 'minFilter': 9987}]

    with open(output_path, 'w') as f:
        json.dump(doc, f, indent=2)

    print(f"  Wrote {len(polygons)} polys -> {output_path} + .bin")
    return output_path
