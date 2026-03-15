"""Parse obj0 ADT files for object placement data (MDDF/MODF)."""

import json
import struct
import sys
from pathlib import Path

from pipeline.adt import read_chunk_header

MDDF_ENTRY_SIZE = 36
MODF_ENTRY_SIZE = 64


def parse_obj0(data: bytes) -> dict:
    m2_placements = []
    wmo_placements = []
    pos = 0

    while pos < len(data) - 8:
        magic, size, data_start = read_chunk_header(data, pos)
        if not magic or (size == 0 and magic != "MVER"):
            pos += 1
            continue

        if magic == "MDDF":
            n = size // MDDF_ENTRY_SIZE
            for i in range(n):
                off = data_start + i * MDDF_ENTRY_SIZE
                fdid, uid = struct.unpack_from("<II", data, off)
                px, py, pz = struct.unpack_from("<3f", data, off + 8)
                rx, ry, rz = struct.unpack_from("<3f", data, off + 20)
                scale, flags = struct.unpack_from("<HH", data, off + 32)
                m2_placements.append({
                    "fdid": fdid,
                    "pos": [round(px, 2), round(py, 2), round(pz, 2)],
                    "rot": [round(rx, 2), round(ry, 2), round(rz, 2)],
                    "scale": round(scale / 1024, 3),
                })

        elif magic == "MODF":
            n = size // MODF_ENTRY_SIZE
            for i in range(n):
                off = data_start + i * MODF_ENTRY_SIZE
                fdid, uid = struct.unpack_from("<II", data, off)
                px, py, pz = struct.unpack_from("<3f", data, off + 8)
                rx, ry, rz = struct.unpack_from("<3f", data, off + 20)
                ex1, ey1, ez1, ex2, ey2, ez2 = struct.unpack_from("<6f", data, off + 32)
                wmo_placements.append({
                    "fdid": fdid,
                    "pos": [round(px, 2), round(py, 2), round(pz, 2)],
                    "rot": [round(rx, 2), round(ry, 2), round(rz, 2)],
                    "extents": [[round(ex1, 1), round(ey1, 1), round(ez1, 1)],
                                [round(ex2, 1), round(ey2, 1), round(ez2, 1)]],
                })

        pos = data_start + size

    return {"m2": m2_placements, "wmo": wmo_placements}


def export_objects(obj0_path: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    data = obj0_path.read_bytes()
    result = parse_obj0(data)

    tile_name = obj0_path.stem.replace("_obj0", "")
    out_path = out_dir / f"{tile_name}_objects.json"
    with open(out_path, "w") as f:
        json.dump(result, f)

    print(f"  {tile_name}: {len(result['m2'])} M2 placements, {len(result['wmo'])} WMO placements")
    return out_path


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if not path:
        print("Usage: python -m pipeline.obj0 <obj0.adt>")
        sys.exit(1)
    export_objects(path, Path("assets/terrain"))
