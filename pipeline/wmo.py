"""Parse WoW WMO building files and export geometry as JSON for the viewer.

WMO format reference: https://wowdev.wiki/WMO
Root file: MOHD header, MOMT materials, GFID group FDIDs
Group files: MOGP container with MOVT/MONR/MOTV/MOVI geometry, MOBA batches
"""

import json
import struct
import sys
from pathlib import Path

from PIL import Image

from pipeline.adt import read_chunk_header

MOGP_HEADER_SIZE = 68
MOMT_SIZE = 64
MOBA_SIZE = 24


def scan_chunks(data: bytes, start: int, end: int) -> dict[str, tuple[int, int]]:
    chunks = {}
    pos = start
    while pos < end - 8:
        magic, size, ds = read_chunk_header(data, pos)
        if not magic or size == 0 or ds + size > end:
            pos += 1
            continue
        if magic not in chunks:
            chunks[magic] = (ds, size)
        pos = ds + size
    return chunks


def parse_wmo_root(data: bytes) -> dict:
    chunks = scan_chunks(data, 0, len(data))

    if "MOHD" not in chunks:
        return {}
    ds, _ = chunks["MOHD"]
    n_tex, n_groups = struct.unpack_from("<II", data, ds)

    materials = []
    if "MOMT" in chunks:
        ds, sz = chunks["MOMT"]
        for i in range(sz // MOMT_SIZE):
            mo = ds + i * MOMT_SIZE
            flags = struct.unpack_from("<I", data, mo)[0]
            tex_fdid = struct.unpack_from("<I", data, mo + 12)[0]
            materials.append({"flags": flags, "texFdid": tex_fdid})

    group_fdids = []
    if "GFID" in chunks:
        ds, sz = chunks["GFID"]
        n = sz // 4
        group_fdids = list(struct.unpack_from(f"<{n}I", data, ds))

    return {
        "nGroups": n_groups,
        "materials": materials,
        "groupFdids": group_fdids,
    }


def parse_wmo_group(data: bytes) -> dict | None:
    chunks = scan_chunks(data, 0, len(data))
    if "MOGP" not in chunks:
        return None

    mogp_ds, mogp_sz = chunks["MOGP"]
    inner_start = mogp_ds + MOGP_HEADER_SIZE
    inner_end = mogp_ds + mogp_sz
    sub = scan_chunks(data, inner_start, inner_end)

    verts, normals, uvs, indices, batches = [], [], [], [], []

    if "MOVT" in sub:
        ds, sz = sub["MOVT"]
        n = sz // 12
        for i in range(n):
            x, y, z = struct.unpack_from("<3f", data, ds + i * 12)
            verts.append((round(x, 4), round(y, 4), round(z, 4)))

    if "MONR" in sub:
        ds, sz = sub["MONR"]
        n = sz // 12
        for i in range(n):
            nx, ny, nz = struct.unpack_from("<3f", data, ds + i * 12)
            normals.append((round(nx, 4), round(ny, 4), round(nz, 4)))

    if "MOTV" in sub:
        ds, sz = sub["MOTV"]
        n = sz // 8
        for i in range(n):
            u, v = struct.unpack_from("<2f", data, ds + i * 8)
            uvs.append((round(u, 5), round(1.0 - v, 5)))

    if "MOVI" in sub:
        ds, sz = sub["MOVI"]
        n = sz // 2
        indices = list(struct.unpack_from(f"<{n}H", data, ds))

    if "MOBA" in sub:
        ds, sz = sub["MOBA"]
        n = sz // MOBA_SIZE
        for i in range(n):
            bo = ds + i * MOBA_SIZE
            start_idx = struct.unpack_from("<I", data, bo + 12)[0]
            count = struct.unpack_from("<H", data, bo + 16)[0]
            mat_id = data[bo + 23]
            batches.append({
                "startIndex": start_idx,
                "indexCount": count,
                "matId": mat_id,
            })

    return {
        "verts": verts,
        "normals": normals,
        "uvs": uvs,
        "indices": indices,
        "batches": batches,
    }


def export_wmo(root_path: Path, out_dir: Path) -> Path | None:
    from extract.download import download_raw

    out_dir.mkdir(parents=True, exist_ok=True)
    wmo_dir = root_path.parent

    root_data = root_path.read_bytes()
    root_info = parse_wmo_root(root_data)
    if not root_info or not root_info["groupFdids"]:
        print(f"  Failed to parse {root_path.name}")
        return None

    all_positions = []
    all_normals = []
    all_uvs = []
    all_indices = []
    all_submeshes = []
    vert_offset = 0

    for gi, gfid in enumerate(root_info["groupFdids"]):
        grp_path = wmo_dir / f"{root_path.stem}_{gi:03d}.wmo"
        download_raw(gfid, grp_path)
        if not grp_path.exists():
            continue

        grp = parse_wmo_group(grp_path.read_bytes())
        if not grp or not grp["verts"]:
            continue

        for v in grp["verts"]:
            all_positions.extend(v)
        for n in grp["normals"]:
            all_normals.extend(n)
        for uv in grp["uvs"]:
            all_uvs.extend(uv)

        for idx in grp["indices"]:
            all_indices.append(idx + vert_offset)

        idx_offset = len(all_indices) - len(grp["indices"])
        for b in grp["batches"]:
            tex_fdid = 0
            if b["matId"] < len(root_info["materials"]):
                tex_fdid = root_info["materials"][b["matId"]]["texFdid"]
            all_submeshes.append({
                "startIndex": b["startIndex"] + idx_offset,
                "indexCount": b["indexCount"],
                "texFdid": tex_fdid,
            })

        vert_offset += len(grp["verts"])

    if not all_positions:
        return None

    tex_fdids = list({s["texFdid"] for s in all_submeshes if s["texFdid"]})
    for fdid in tex_fdids:
        webp_path = out_dir / f"tex_{fdid}.webp"
        if not webp_path.exists():
            blp_path = wmo_dir / f"tex_{fdid}.blp"
            download_raw(fdid, blp_path)
            if blp_path.exists():
                try:
                    img = Image.open(blp_path)
                    img.save(webp_path)
                except Exception:
                    pass

    out = {
        "name": root_path.stem,
        "nVerts": vert_offset,
        "positions": [round(v, 4) for v in all_positions],
        "normals": [round(v, 4) for v in all_normals],
        "uvs": [round(v, 5) for v in all_uvs],
        "indices": all_indices,
        "submeshes": all_submeshes,
        "texFdids": tex_fdids,
        "isWmo": True,
    }

    out_path = out_dir / f"{root_path.stem}.json"
    with open(out_path, "w") as f:
        json.dump(out, f)

    n_tris = len(all_indices) // 3
    n_sub = len(all_submeshes)
    print(f"  {root_path.stem}: {vert_offset} verts, {n_tris} tris, {n_sub} submeshes, {len(tex_fdids)} textures")
    return out_path


def download_and_export(fdid: int, out_dir: Path = Path("assets/wmo_models")) -> Path | None:
    from extract.download import download_raw, load_listfile

    wmo_dir = Path("assets/wmo")
    wmo_dir.mkdir(parents=True, exist_ok=True)

    entries = {f: p for f, p in load_listfile() if f == fdid}
    name = Path(entries.get(fdid, f"{fdid}.wmo")).stem

    wmo_path = wmo_dir / f"{name}.wmo"
    download_raw(fdid, wmo_path)
    if not wmo_path.exists():
        return None

    return export_wmo(wmo_path, out_dir)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m pipeline.wmo <fdid> [fdid...]")
        sys.exit(1)

    out_dir = Path("assets/wmo_models")
    for arg in sys.argv[1:]:
        fdid = int(arg)
        print(f"Processing WMO fdid={fdid}...")
        result = download_and_export(fdid, out_dir)
        if result:
            print(f"  -> {result}")
