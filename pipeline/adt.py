"""Parse WoW ADT terrain files and export heightmaps + splatmaps for the viewer.

ADT format reference: https://wowdev.wiki/ADT/v18
Modern (Cata+) split format: root ADT has heights, tex0 ADT has texture info.
"""

import argparse
import json
import struct
import sys
from pathlib import Path

from PIL import Image

CHUNK_SIZE_YARDS = 33.3333
TILE_SIZE_YARDS = CHUNK_SIZE_YARDS * 16
OUTER_VERTS = 9
INNER_VERTS = 8
VERTS_PER_CHUNK = OUTER_VERTS * OUTER_VERTS + INNER_VERTS * INNER_VERTS
MCNK_HEADER_SIZE = 128
ALPHA_MAP_SIZE = 64
ALPHA_PIXELS = ALPHA_MAP_SIZE * ALPHA_MAP_SIZE

FDID_TO_DIFFUSE = {
    187127: "elwynngrassbase",
    187115: "elwynndirtbase2",
    187138: "elwynnrockbasetest2",
    187125: "elwynnflowerbase",
    187100: "elwynncobblestonebase",
    186770: "elwynngrassbase",
    186951: "elwynnrockbase",
    186934: "elwynndirtbase",
    321215: "elwynndirtmud",
    242660: "elwynndirtbase",
    187901: "elwynndirtbase",
    188986: "elwynncrop",
}

SPLAT_CHANNELS = {
    "elwynndirtbase2": 0,
    "elwynndirtbase": 0,
    "elwynndirtmud": 0,
    "elwynncrop": 0,
    "elwynnrockbasetest2": 1,
    "elwynnrockbase": 1,
    "elwynncobblestonebase": 2,
    "elwynnflowerbase": 2,
}
SPLAT_TEX_NAMES = ["elwynndirtbase2", "elwynnrockbasetest2", "elwynncobblestonebase"]
SPLAT_BASE = "elwynngrassbase"


def read_chunk_header(data: bytes, pos: int) -> tuple[str, int, int]:
    if pos + 8 > len(data):
        return ("", 0, pos)
    magic = data[pos:pos + 4][::-1].decode("ascii", errors="replace")
    size = struct.unpack_from("<I", data, pos + 4)[0]
    return (magic, size, pos + 8)


# -- root ADT: heightmaps --


def parse_root_adt(data: bytes) -> list[dict]:
    chunks = []
    pos = 0
    while pos < len(data) - 8:
        magic, size, data_start = read_chunk_header(data, pos)
        if not magic or size == 0 and magic != "MVER":
            pos += 1
            continue
        if magic == "MCNK":
            chunk = parse_mcnk_root(data, data_start, size)
            if chunk:
                chunks.append(chunk)
        pos = data_start + size
    return chunks


def parse_mcnk_root(data: bytes, offset: int, size: int) -> dict | None:
    if size < MCNK_HEADER_SIZE:
        return None
    hdr = data[offset:offset + MCNK_HEADER_SIZE]
    ix = struct.unpack_from("<I", hdr, 4)[0]
    iy = struct.unpack_from("<I", hdr, 8)[0]
    pos_x, pos_y, pos_z = struct.unpack_from("<3f", hdr, 0x68)
    mcnk_end = offset + size
    heights = find_subchunk_data(data, offset + MCNK_HEADER_SIZE, mcnk_end, "MCVT", VERTS_PER_CHUNK * 4)
    if heights:
        heights = list(struct.unpack_from(f"<{VERTS_PER_CHUNK}f", heights))
    else:
        heights = [0.0] * VERTS_PER_CHUNK
    return {"ix": ix, "iy": iy, "pos": [pos_x, pos_y, pos_z], "heights": heights}


def find_subchunk_data(data: bytes, start: int, end: int, target: str, min_size: int = 0) -> bytes | None:
    pos = start
    while pos < end - 8:
        magic, size, data_start = read_chunk_header(data, pos)
        if magic == target and size >= min_size:
            return data[data_start:data_start + size]
        if size == 0:
            pos += 1
            continue
        pos = data_start + size
    return None


def build_heightmap(chunks: list[dict], global_base_z: float | None = None) -> dict:
    grid_size = 16 * (OUTER_VERTS - 1) + 1
    heights = [0.0] * (grid_size * grid_size)
    heights_orig = [0.0] * (grid_size * grid_size)
    base_z = global_base_z if global_base_z is not None else (min(c["pos"][2] for c in chunks) if chunks else 0.0)

    for chunk in chunks:
        ix, iy = chunk["ix"], chunk["iy"]
        cz = chunk["pos"][2]
        h = chunk["heights"]
        for row in range(OUTER_VERTS):
            for col in range(OUTER_VERTS):
                vert_idx = row * 17 + col
                height = (h[vert_idx] if vert_idx < len(h) else 0.0) + cz - base_z
                gx = iy * (OUTER_VERTS - 1) + row
                gy = ix * (OUTER_VERTS - 1) + col
                if gx < grid_size and gy < grid_size:
                    heights[gy * grid_size + gx] = height
                gx_o = iy * (OUTER_VERTS - 1) + col
                gy_o = ix * (OUTER_VERTS - 1) + row
                if gx_o < grid_size and gy_o < grid_size:
                    heights_orig[gy_o * grid_size + gx_o] = height

    return {"gridSize": grid_size, "tileSize": TILE_SIZE_YARDS, "baseZ": base_z,
            "heights": heights, "heightsOrig": heights_orig}


# -- tex0 ADT: texture layers + alpha maps --


def parse_tex0_adt(data: bytes) -> tuple[list[int], list[dict]]:
    tex_fdids = []
    tex_chunks = []
    pos = 0
    chunk_idx = 0

    while pos < len(data) - 8:
        magic, size, data_start = read_chunk_header(data, pos)
        if not magic or (size == 0 and magic != "MVER"):
            pos += 1
            continue

        if magic == "MDID":
            n = size // 4
            tex_fdids = list(struct.unpack_from(f"<{n}I", data, data_start))

        elif magic == "MCNK":
            tc = parse_mcnk_tex0(data, data_start, size, chunk_idx)
            tex_chunks.append(tc)
            chunk_idx += 1

        pos = data_start + size

    return tex_fdids, tex_chunks


def parse_mcnk_tex0(data: bytes, offset: int, size: int, idx: int) -> dict:
    mcnk_end = offset + size
    layers = []
    alphas = []

    mcly_data = find_subchunk_data(data, offset, mcnk_end, "MCLY")
    mcal_data = find_subchunk_data(data, offset, mcnk_end, "MCAL")

    if mcly_data:
        n_layers = len(mcly_data) // 16
        for i in range(n_layers):
            tex_id, flags, alpha_off, _ = struct.unpack_from("<IIII", mcly_data, i * 16)
            layers.append({"tex_id": tex_id, "flags": flags, "alpha_off": alpha_off})

    if mcal_data and len(layers) > 1:
        for layer in layers[1:]:
            compressed = layer["flags"] & 0x200
            alpha_off = layer["alpha_off"]
            if compressed:
                alpha = decompress_alpha(mcal_data, alpha_off)
            else:
                if alpha_off + ALPHA_PIXELS <= len(mcal_data):
                    alpha = list(mcal_data[alpha_off:alpha_off + ALPHA_PIXELS])
                else:
                    alpha = [0] * ALPHA_PIXELS
            alphas.append(alpha)

    ix = idx % 16
    iy = idx // 16
    return {"ix": ix, "iy": iy, "layers": layers, "alphas": alphas}


def decompress_alpha(mcal_data: bytes, offset: int) -> list[int]:
    alpha = []
    pos = offset
    while len(alpha) < ALPHA_PIXELS and pos < len(mcal_data):
        info = mcal_data[pos]
        pos += 1
        fill = bool(info & 0x80)
        count = info & 0x7F
        if fill:
            if pos >= len(mcal_data):
                break
            val = mcal_data[pos]
            pos += 1
            alpha.extend([val] * count)
        else:
            end = min(pos + count, len(mcal_data))
            alpha.extend(mcal_data[pos:end])
            pos = end

    while len(alpha) < ALPHA_PIXELS:
        alpha.append(0)
    return alpha[:ALPHA_PIXELS]


# -- MH2O water parsing --


def parse_mh2o(data: bytes) -> list[dict]:
    pos = 0
    mh2o_data = None

    while pos < len(data) - 8:
        magic, size, data_start = read_chunk_header(data, pos)
        if not magic or (size == 0 and magic != "MVER"):
            pos += 1
            continue
        if magic == "MH2O":
            mh2o_data = data[data_start:data_start + size]
            break
        pos = data_start + size

    if not mh2o_data or len(mh2o_data) < 256 * 12:
        return []

    water_chunks = []
    for i in range(256):
        hdr_off = i * 12
        inst_off, layer_count, _ = struct.unpack_from("<III", mh2o_data, hdr_off)
        if layer_count == 0 or inst_off == 0:
            continue
        if inst_off + 24 > len(mh2o_data):
            continue

        liquid_type, lvf = struct.unpack_from("<HH", mh2o_data, inst_off)
        min_h, max_h = struct.unpack_from("<ff", mh2o_data, inst_off + 4)
        x_off, y_off, w, h = struct.unpack_from("<BBBB", mh2o_data, inst_off + 12)

        if abs(min_h) > 10000 or abs(max_h) > 10000:
            continue

        ix = i % 16
        iy = i // 16
        water_chunks.append({
            "ix": ix, "iy": iy,
            "type": liquid_type & 0x1F,
            "h": round(max_h if max_h != 0 else min_h, 2),
            "x": x_off, "y": y_off, "w": max(1, w), "h2": max(1, h),
        })

    return water_chunks


# -- splatmap generation --


def _auto_assign_channels(tex_chunks, tex_fdids):
    """Pick base + 3 channel textures by usage frequency across all chunks."""
    from collections import Counter
    usage = Counter()
    base_usage = Counter()
    for tc in tex_chunks:
        if tc["layers"]:
            base_tid = tc["layers"][0]["tex_id"]
            if base_tid < len(tex_fdids):
                base_usage[tex_fdids[base_tid]] += 1
            for layer in tc["layers"]:
                tid = layer["tex_id"]
                if tid < len(tex_fdids):
                    usage[tex_fdids[tid]] += 1

    base_fdid = base_usage.most_common(1)[0][0] if base_usage else (tex_fdids[0] if tex_fdids else 0)
    others = [fdid for fdid, _ in usage.most_common() if fdid != base_fdid]
    chan_fdids = others[:3]
    while len(chan_fdids) < 3:
        chan_fdids.append(0)

    return base_fdid, chan_fdids


def generate_splatmap(tex_chunks, tex_fdids, out_dir, tile_name,
                      fdid_names=None, splat_channels=None, splat_base=None):
    has_elwynn = any(fdid in FDID_TO_DIFFUSE for fdid in tex_fdids)

    if fdid_names is None:
        fdid_names = {fdid: FDID_TO_DIFFUSE.get(fdid, f"tex_{fdid}") for fdid in tex_fdids}
    tex_names = [fdid_names.get(fdid, f"tex_{fdid}") for fdid in tex_fdids]

    if has_elwynn and splat_channels is None:
        splat_channels_map = SPLAT_CHANNELS
        splat_base_name = SPLAT_BASE
        splat_tex_names = list(SPLAT_TEX_NAMES)
    else:
        base_fdid, chan_fdids = _auto_assign_channels(tex_chunks, tex_fdids)
        splat_base_name = fdid_names.get(base_fdid, f"tex_{base_fdid}")
        splat_tex_names = [fdid_names.get(f, f"tex_{f}") for f in chan_fdids]
        splat_channels_map = {}
        for i, name in enumerate(splat_tex_names):
            splat_channels_map[name] = i

    if splat_base is not None:
        splat_base_name = splat_base
    if splat_channels is not None:
        splat_channels_map = splat_channels

    splat_size = 16 * ALPHA_MAP_SIZE
    img = Image.new("RGB", (splat_size, splat_size), (0, 0, 0))
    pixels = img.load()

    for tc in tex_chunks:
        cx, cy = tc["iy"], tc["ix"]
        layers = tc["layers"]
        alphas = tc["alphas"]

        channels = [0] * (ALPHA_PIXELS * 3)

        base_tex = tex_names[layers[0]["tex_id"]] if layers else splat_base_name
        base_chan = splat_channels_map.get(base_tex, -1)
        if base_chan >= 0:
            for i in range(ALPHA_PIXELS):
                channels[i * 3 + base_chan] = 255

        for li, layer in enumerate(layers[1:]):
            if li >= len(alphas):
                break
            layer_tex = tex_names[layer["tex_id"]] if layer["tex_id"] < len(tex_names) else splat_base_name
            chan = splat_channels_map.get(layer_tex, -1)
            if chan < 0:
                continue
            alpha = alphas[li]
            for i in range(ALPHA_PIXELS):
                a = alpha[i]
                if a == 0:
                    continue
                if base_chan >= 0 and base_chan != chan:
                    old_base = channels[i * 3 + base_chan]
                    channels[i * 3 + base_chan] = max(0, old_base - a)
                channels[i * 3 + chan] = min(255, channels[i * 3 + chan] + a)

        for py in range(ALPHA_MAP_SIZE):
            for px in range(ALPHA_MAP_SIZE):
                ai = px * ALPHA_MAP_SIZE + py
                r = channels[ai * 3]
                g = channels[ai * 3 + 1]
                b = channels[ai * 3 + 2]
                gx = cx * ALPHA_MAP_SIZE + px
                gy = cy * ALPHA_MAP_SIZE + py
                if gx < splat_size and gy < splat_size:
                    pixels[gx, gy] = (r, g, b)

    splat_path = out_dir / f"{tile_name}_splatmap.webp"
    img.save(splat_path)
    print(f"  Splatmap: {splat_path.name} ({splat_size}x{splat_size})")
    print(f"  Channels: R={splat_tex_names[0]}, G={splat_tex_names[1]}, B={splat_tex_names[2]}, base={splat_base_name}")

    texmap = {
        "base": splat_base_name,
        "channels": {"R": splat_tex_names[0], "G": splat_tex_names[1], "B": splat_tex_names[2]},
        "fdids": tex_fdids,
        "names": tex_names,
    }
    texmap_path = out_dir / f"{tile_name}_texmap.json"
    with open(texmap_path, "w") as f:
        json.dump(texmap, f, indent=2)

    return splat_path, texmap


# -- export --


def export_terrain(root_path: Path, tex0_path: Path | None, out_dir: Path, global_base_z: float | None = None):
    out_dir.mkdir(parents=True, exist_ok=True)
    tile_name = root_path.stem

    root_data = root_path.read_bytes()
    chunks = parse_root_adt(root_data)
    print(f"  Parsed {len(chunks)} MCNK chunks from {root_path.name}")

    if not chunks:
        print("  ERROR: No MCNK chunks found")
        return

    hmap = build_heightmap(chunks, global_base_z)

    textures = []
    if tex0_path and tex0_path.exists():
        tex_data = tex0_path.read_bytes()
        tex_fdids, tex_chunks = parse_tex0_adt(tex_data)
        textures = tex_fdids
        print(f"  Found {len(tex_fdids)} textures, {len(tex_chunks)} tex chunks")

        if tex_chunks:
            generate_splatmap(tex_chunks, tex_fdids, out_dir, tile_name)

    out = {
        "tile": tile_name,
        "gridSize": hmap["gridSize"],
        "tileSize": hmap["tileSize"],
        "baseZ": hmap["baseZ"],
        "heights": [round(h, 3) for h in hmap["heights"]],
        "heightsOrig": [round(h, 3) for h in hmap["heightsOrig"]],
        "textures": textures,
    }

    water = parse_mh2o(root_data)
    if water:
        out["water"] = water
        print(f"  Water: {len(water)} chunks with water")

    if tex0_path and tex0_path.exists() and tex_chunks:
        chunk_base = []
        for tc in tex_chunks:
            base_tid = tc["layers"][0]["tex_id"] if tc["layers"] else 0
            chunk_base.append(base_tid)
        out["chunkBase"] = chunk_base

    out_path = out_dir / f"{tile_name}.json"
    with open(out_path, "w") as f:
        json.dump(out, f)

    size_kb = out_path.stat().st_size // 1024
    h_min, h_max = min(hmap["heights"]), max(hmap["heights"])
    print(f"  Exported {out_path.name} ({size_kb} KB)")
    print(f"  Grid: {hmap['gridSize']}x{hmap['gridSize']}, height range: {h_min:.1f} - {h_max:.1f}")


def main():
    parser = argparse.ArgumentParser(description="Parse WoW ADT terrain files")
    parser.add_argument("root_adt", help="Path to root .adt file")
    parser.add_argument("--tex0", help="Path to _tex0.adt file (optional)")
    parser.add_argument("-o", "--output", default="assets/terrain", help="Output directory")
    parser.add_argument("--base-z", type=float, default=None, help="Global base Z height")

    args = parser.parse_args()
    root = Path(args.root_adt)
    tex0 = Path(args.tex0) if args.tex0 else None
    if not tex0:
        guess = root.parent / root.name.replace(".adt", "_tex0.adt")
        if guess.exists():
            tex0 = guess

    export_terrain(root, tex0, Path(args.output), args.base_z)


if __name__ == "__main__":
    main()
