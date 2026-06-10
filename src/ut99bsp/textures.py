"""Extract texture images from UT99 .utx package files."""

import os
import struct
import zlib
from collections import defaultdict


# ── DXT Decoding ────────────────────────────────────────────────────

def _decompress_dxt1(data, w, h):
    buf = bytearray(w * h * 4)
    block_w = max((w + 3) // 4, 1)
    block_h = max((h + 3) // 4, 1)
    for by in range(block_h):
        for bx in range(block_w):
            off = (by * block_w + bx) * 8
            if off + 8 > len(data):
                continue
            c0, c1 = struct.unpack_from('<HH', data, off)
            bits = struct.unpack_from('<I', data, off + 4)[0]
            col0 = _rgb565(c0)
            col1 = _rgb565(c1)
            code = [bits >> (i * 2) & 3 for i in range(16)]
            for i in range(16):
                x = bx * 4 + i % 4
                y = by * 4 + i // 4
                if x >= w or y >= h:
                    continue
                idx = code[i]
                if c0 > c1:
                    t = (2.0 / 3.0) if idx == 2 else (1.0 / 3.0) if idx == 3 else 0
                    r = int(col0[0] + t * (col1[0] - col0[0])) if idx == 2 else \
                        int(col1[0] + t * (col0[0] - col1[0])) if idx == 3 else \
                        col0[0] if idx == 0 else col1[0]
                    g = int(col0[1] + t * (col1[1] - col0[1])) if idx == 2 else \
                        int(col1[1] + t * (col0[1] - col1[1])) if idx == 3 else \
                        col0[1] if idx == 0 else col1[1]
                    b = int(col0[2] + t * (col1[2] - col0[2])) if idx == 2 else \
                        int(col1[2] + t * (col0[2] - col1[2])) if idx == 3 else \
                        col0[2] if idx == 0 else col1[2]
                    a = 255
                else:
                    t3 = 0.5 if idx == 2 else 0
                    if idx == 0:
                        r, g, b, a = col0[0], col0[1], col0[2], 255
                    elif idx == 1:
                        r, g, b, a = col1[0], col1[1], col1[2], 255
                    elif idx == 2:
                        r = (col0[0] + col1[0]) // 2
                        g = (col0[1] + col1[1]) // 2
                        b = (col0[2] + col1[2]) // 2
                        a = 255
                    else:
                        r = g = b = 0
                        a = 0
                pos = (y * w + x) * 4
                if pos + 4 <= len(buf):
                    buf[pos:pos+3] = bytes([r, g, b])
                    buf[pos+3] = a
    return bytes(buf)


def _decompress_dxt3(data, w, h):
    buf = bytearray(w * h * 4)
    block_w = max((w + 3) // 4, 1)
    block_h = max((h + 3) // 4, 1)
    for by in range(block_h):
        for bx in range(block_w):
            off = (by * block_w + bx) * 16
            if off + 16 > len(data):
                continue
            alphas = struct.unpack_from('<Q', data, off)[0]
            c0, c1 = struct.unpack_from('<HH', data, off + 8)
            bits = struct.unpack_from('<I', data, off + 12)[0]
            col0 = _rgb565(c0)
            col1 = _rgb565(c1)
            code = [bits >> (i * 2) & 3 for i in range(16)]
            for i in range(16):
                x = bx * 4 + i % 4
                y = by * 4 + i // 4
                if x >= w or y >= h:
                    continue
                a = (alphas >> (i * 4) & 0xF) * 17
                idx = code[i]
                t = (2.0 / 3.0) if idx == 2 else (1.0 / 3.0) if idx == 3 else 0
                r = int(col0[0] + t * (col1[0] - col0[0])) if idx == 2 else \
                    int(col1[0] + t * (col0[0] - col1[0])) if idx == 3 else \
                    col0[0] if idx == 0 else col1[0]
                g = int(col0[1] + t * (col1[1] - col0[1])) if idx == 2 else \
                    int(col1[1] + t * (col0[1] - col1[1])) if idx == 3 else \
                    col0[1] if idx == 0 else col1[1]
                b = int(col0[2] + t * (col1[2] - col0[2])) if idx == 2 else \
                    int(col1[2] + t * (col0[2] - col1[2])) if idx == 3 else \
                    col0[2] if idx == 0 else col1[2]
                pos = (y * w + x) * 4
                if pos + 4 <= len(buf):
                    buf[pos:pos+3] = bytes([r, g, b])
                    buf[pos+3] = a
    return bytes(buf)


def _decompress_dxt5(data, w, h):
    buf = bytearray(w * h * 4)
    block_w = max((w + 3) // 4, 1)
    block_h = max((h + 3) // 4, 1)
    for by in range(block_h):
        for bx in range(block_w):
            off = (by * block_w + bx) * 16
            if off + 16 > len(data):
                continue
            a0, a1 = struct.unpack_from('<BB', data, off)
            alpha_bits = struct.unpack_from('<Q', data, off)[0] >> 16
            c0, c1 = struct.unpack_from('<HH', data, off + 8)
            bits = struct.unpack_from('<I', data, off + 12)[0]
            col0 = _rgb565(c0)
            col1 = _rgb565(c1)
            code = [bits >> (i * 2) & 3 for i in range(16)]
            for i in range(16):
                x = bx * 4 + i % 4
                y = by * 4 + i // 4
                if x >= w or y >= h:
                    continue
                a_idx = (alpha_bits >> (i * 3)) & 7
                if a0 > a1:
                    a = a0 + (a1 - a0) * a_idx // 7 if a_idx <= 4 else \
                        a0 + (a1 - a0) * (8 - a_idx) // 7
                else:
                    a_codes = [a0, a1, (6 * a0 + 1 * a1) // 7, (5 * a0 + 2 * a1) // 7,
                                (4 * a0 + 3 * a1) // 7, (3 * a0 + 4 * a1) // 7,
                                (2 * a0 + 5 * a1) // 7, (1 * a0 + 6 * a1) // 7]
                    a = a_codes[a_idx]
                idx = code[i]
                t = (2.0 / 3.0) if idx == 2 else (1.0 / 3.0) if idx == 3 else 0
                r = int(col0[0] + t * (col1[0] - col0[0])) if idx == 2 else \
                    int(col1[0] + t * (col0[0] - col1[0])) if idx == 3 else \
                    col0[0] if idx == 0 else col1[0]
                g = int(col0[1] + t * (col1[1] - col0[1])) if idx == 2 else \
                    int(col1[1] + t * (col0[1] - col1[1])) if idx == 3 else \
                    col0[1] if idx == 0 else col1[1]
                b = int(col0[2] + t * (col1[2] - col0[2])) if idx == 2 else \
                    int(col1[2] + t * (col0[2] - col1[2])) if idx == 3 else \
                    col0[2] if idx == 0 else col1[2]
                pos = (y * w + x) * 4
                if pos + 4 <= len(buf):
                    buf[pos:pos+3] = bytes([r, g, b])
                    buf[pos+3] = max(0, min(255, a))
    return bytes(buf)


def _rgb565(v):
    r = (v >> 11) & 0x1F
    g = (v >> 5) & 0x3F
    b = v & 0x1F
    return (r << 3 | r >> 2, g << 2 | g >> 4, b << 3 | b >> 2)


# ── PNG writer ──────────────────────────────────────────────────────

def _write_png(path, pixels, w, h, has_alpha=True):
    """Write raw RGBA pixels to a PNG file (no external deps)."""
    raw = b""
    for y in range(h):
        raw += b"\x00"
        for x in range(w):
            off = (y * w + x) * 4
            raw += bytes(pixels[off:off+4])
    compressed = zlib.compress(raw)

    def _chunk(ctype, data):
        chunk = ctype + data
        crc = struct.pack('>I', zlib.crc32(chunk) & 0xFFFFFFFF)
        return struct.pack('>I', len(data)) + chunk + crc

    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = struct.pack('>IIBBBBB', w, h, 8, 6 if has_alpha else 2, 0, 0, 0)
    iend = _chunk(b'IEND', b'')

    with open(path, 'wb') as f:
        f.write(sig)
        f.write(_chunk(b'IHDR', ihdr))
        f.write(_chunk(b'IDAT', compressed))
        f.write(iend)


# ── UTX Package Reader ─────────────────────────────────────────────

MAGIC = 0x9E2A83C1


def _read_compact_index(data, offset):
    b = data[offset]
    is_neg = (b >> 7) & 1
    more = (b >> 6) & 1
    val = b & 0x3F
    offset += 1
    for bn in range(1, 5):
        if not more:
            break
        b = data[offset]
        more = (b >> 7) & 1
        bc = 7 if bn < 4 else 8
        val |= (b & ((1 << bc) - 1)) << (6 + (bn - 1) * 7)
        offset += 1
    if is_neg:
        val = -val
    return val, offset


def _resolve_name(data, name_table, idx):
    if 0 <= idx < len(name_table):
        return name_table[idx]
    return f"Name_{idx}"


class TextureInfo:
    def __init__(self):
        self.name = ""
        self.width = 0
        self.height = 0
        self.format = 0  # 0=DXT1, 1=DXT3, 2=DXT5, 3=P8, 4=RGBA7, 5=RGB8, 6=RGBA8
        self.mipmaps = []
        self.export_idx = -1


class UTXReader:
    """Read a .utx package and list available textures."""

    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            self.data = f.read()
        self.names = []
        self.imports = []
        self.exports = []
        self.textures = []
        self._read_header()
        self._read_names()
        self._read_imports()
        self._read_exports()
        self._find_textures()

    def _read_header(self):
        fields = struct.unpack('<IIHHIIIIII', self.data[:36])
        magic, self.version, lic_mode, self.flags = fields[0], fields[1], fields[2], fields[3]
        self.name_count, self.name_offset = fields[4], fields[5]
        self.export_count, self.export_offset = fields[6], fields[7]
        self.import_count, self.import_offset = fields[8], fields[9]
        if magic != MAGIC:
            raise ValueError(f"Not a UT99 package: magic={magic:#010x}")

    def _read_names(self):
        self.names = []
        off = self.name_offset
        for _ in range(self.name_count):
            length, off = _read_compact_index(self.data, off)
            name = self.data[off:off+length].decode('windows-1252', errors='replace').rstrip('\0')
            off += length
            flags = struct.unpack('<I', self.data[off:off+4])[0]
            off += 4
            self.names.append(name)

    def _read_imports(self):
        self.imports = []
        off = self.import_offset
        for _ in range(self.import_count):
            cp, off = _read_compact_index(self.data, off)
            cn, off = _read_compact_index(self.data, off)
            pi = struct.unpack('<I', self.data[off:off+4])[0]
            off += 4
            on, off = _read_compact_index(self.data, off)
            self.imports.append({'class_package': cp, 'class_name': cn,
                                  'package_index': pi, 'name_index': on})

    def _read_exports(self):
        self.exports = []
        off = self.export_offset
        for _ in range(self.export_count):
            ci, off = _read_compact_index(self.data, off)
            si, off = _read_compact_index(self.data, off)
            pi = struct.unpack('<I', self.data[off:off+4])[0]
            off += 4
            ni, off = _read_compact_index(self.data, off)
            of = struct.unpack('<I', self.data[off:off+4])[0]
            off += 4
            ss, off = _read_compact_index(self.data, off)
            so, off = _read_compact_index(self.data, off)
            self.exports.append({
                'class_idx': ci, 'super_idx': si, 'pkg_idx': pi,
                'name_idx': ni, 'flags': of, 'serial_size': ss,
                'serial_offset': so,
            })

    def resolve_name(self, idx):
        return _resolve_name(self.data, self.names, idx)

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

    def get_export_data(self, idx):
        if idx < 0 or idx >= len(self.exports):
            return None
        e = self.exports[idx]
        if e['serial_size'] == 0 or e['serial_offset'] < 0:
            return None
        return self.data[e['serial_offset']:e['serial_offset'] + e['serial_size']]

    def _find_textures(self):
        for idx, exp in enumerate(self.exports):
            class_name = self.resolve_object_name(exp['class_idx'])
            if class_name in ("Mipmap", "Texture", "FireTexture", "Subs"):
                data = self.get_export_data(idx)
                if data is None or len(data) < 16:
                    continue
                name = self.resolve_name(exp['name_idx'])
                tex = TextureInfo()
                tex.name = name
                tex.export_idx = idx
                self._parse_mipmap(data, tex)
                if tex.width > 0 and tex.mipmaps:
                    self.textures.append(tex)

    def _parse_mipmap(self, data, tex):
        off = 0
        while off < len(data):
            try:
                mip_w, off = _read_compact_index(data, off)
                mip_h, off = _read_compact_index(data, off)
                if mip_w == 0 or mip_h == 0:
                    break
                u_flag, off = _read_compact_index(data, off)
                u_val, off = _read_compact_index(data, off)
                tex.format = u_flag
                if off >= len(data):
                    break
                if u_flag in (0, 1, 2):
                    bpp = 8
                    block_size = 8 if u_flag == 0 else 16
                    bw = max((mip_w + 3) // 4, 1)
                    bh = max((mip_h + 3) // 4, 1)
                    mip_size = bw * bh * block_size
                elif u_flag == 3:
                    mip_size = mip_w * mip_h
                elif u_flag == 4:
                    mip_size = mip_w * mip_h * 2
                elif u_flag in (5, 6):
                    mip_size = mip_w * mip_h * 4
                else:
                    break
                if off + mip_size > len(data):
                    break
                mip_data = data[off:off+mip_size]
                if tex.width == 0:
                    tex.width = mip_w
                    tex.height = mip_h
                tex.mipmaps.append({
                    'width': mip_w, 'height': mip_h,
                    'format': u_flag, 'data': mip_data,
                })
                off += mip_size
            except (struct.error, ValueError):
                break


def decode_texture(tex, mip_level=0):
    """Decode a mipmap level to RGBA bytes."""
    if mip_level >= len(tex.mipmaps):
        return None
    mip = tex.mipmaps[mip_level]
    w, h, fmt = mip['width'], mip['height'], mip['format']
    data = mip['data']
    if fmt == 0:
        return _decompress_dxt1(data, w, h)
    elif fmt == 1:
        return _decompress_dxt3(data, w, h)
    elif fmt == 2:
        return _decompress_dxt5(data, w, h)
    elif fmt == 5:
        return data
    elif fmt == 6:
        return data
    return None


def save_texture_png(tex, output_dir, mip_level=0):
    """Decode a texture mip level and write it as PNG."""
    pixels = decode_texture(tex, mip_level)
    if pixels is None:
        return None
    mip = tex.mipmaps[mip_level]
    w, h = mip['width'], mip['height']
    fmt = mip['format']
    has_alpha = fmt in (1, 2, 4, 6)
    safe_name = tex.name.replace('/', '_').replace('\\', '_').replace(':', '_')
    path = os.path.join(output_dir, f"{safe_name}.png")
    _write_png(path, pixels, w, h, has_alpha)
    return path


# ── Map-level extraction ────────────────────────────────────────────

def find_texture_packages(map_path, search_paths=None):
    """Find .utx files that the map references."""
    if search_paths is None:
        search_paths = []
    map_dir = os.path.dirname(os.path.abspath(map_path))
    search_paths = [map_dir] + search_paths + [
        os.path.join(map_dir, "Textures"),
        os.path.join(map_dir, "..", "Textures"),
    ]
    from ut99bsp.extractor import PackageReader as MapReader
    try:
        pkg = MapReader(map_path)
    except Exception:
        return {}
    tex_packages = set()
    for imp in pkg.imports:
        pkg_name = pkg.resolve_name(imp['class_package'])
        if pkg_name:
            tex_packages.add(pkg_name)
    found = {}
    for pkg_name in tex_packages:
        utx_name = f"{pkg_name}.utx"
        for sp in search_paths:
            sp_norm = os.path.normpath(sp)
            candidate = os.path.join(sp_norm, utx_name)
            if os.path.isfile(candidate):
                found[pkg_name] = candidate
                break
    return found


def extract_map_textures(map_path, output_dir, search_paths=None, progress=None):
    """Extract all textures referenced by a map into output_dir. Returns list of (name, path)."""
    tex_packages = find_texture_packages(map_path, search_paths)
    if not tex_packages:
        if progress:
            progress("No texture packages found", 0)
        return []
    extracted = []
    for pkg_name, utx_path in sorted(tex_packages.items()):
        if progress:
            progress(f"Reading {pkg_name}.utx...", 0)
        try:
            reader = UTXReader(utx_path)
        except Exception as e:
            if progress:
                progress(f"  Skipping {pkg_name}.utx: {e}", 0)
            continue
        for tex in reader.textures:
            try:
                path = save_texture_png(tex, output_dir)
                if path:
                    extracted.append((tex.name, path))
                    if progress:
                        progress(f"  {tex.name}.png ({tex.width}x{tex.height})", 0)
            except Exception as e:
                if progress:
                    progress(f"  Failed {tex.name}: {e}", 0)
    return extracted
