"""Parse WoW M2 model files and export geometry as JSON for the viewer.

M2 format reference: https://wowdev.wiki/M2
Handles modern chunked format (MD21) with separate .skin files.
Static geometry only (no animations).
"""

import json
import struct
import sys
from pathlib import Path

from PIL import Image

M2_VERTEX_SIZE = 48


def read_m2_chunk(data: bytes, pos: int) -> tuple[str, int, int]:
    if pos + 8 > len(data):
        return ("", 0, pos)
    magic = data[pos:pos + 4].decode("ascii", errors="replace")
    size = struct.unpack_from("<I", data, pos + 4)[0]
    return (magic, size, pos + 8)


def parse_m2(m2_path: Path) -> dict:
    data = m2_path.read_bytes()
    md21_data = None
    skin_fdids = []
    tex_fdids = []

    pos = 0
    while pos < len(data) - 8:
        magic, size, data_start = read_m2_chunk(data, pos)
        if size > len(data) - pos or (size == 0 and magic != "MD21"):
            break

        if magic == "MD21":
            md21_data = data[data_start:data_start + size]
        elif magic == "SFID":
            n = size // 4
            skin_fdids = list(struct.unpack_from(f"<{n}I", data, data_start))
        elif magic == "TXID":
            n = size // 4
            tex_fdids = list(struct.unpack_from(f"<{n}I", data, data_start))

        pos = data_start + size

    if not md21_data:
        return {}

    hdr = md21_data
    n_verts = struct.unpack_from("<I", hdr, 0x3C)[0]
    o_verts = struct.unpack_from("<I", hdr, 0x40)[0]

    vertices = []
    for i in range(n_verts):
        vo = o_verts + i * M2_VERTEX_SIZE
        if vo + M2_VERTEX_SIZE > len(hdr):
            break
        px, py, pz = struct.unpack_from("<3f", hdr, vo)
        nx, ny, nz = struct.unpack_from("<3f", hdr, vo + 20)
        u, v = struct.unpack_from("<2f", hdr, vo + 32)
        vertices.append({
            "p": [round(px, 4), round(py, 4), round(pz, 4)],
            "n": [round(nx, 4), round(ny, 4), round(nz, 4)],
            "uv": [round(u, 5), round(v, 5)],
        })

    tex_lookup = []
    if len(hdr) >= 0x88:
        n_tex_lookup = struct.unpack_from("<I", hdr, 0x80)[0]
        o_tex_lookup = struct.unpack_from("<I", hdr, 0x84)[0]
        if n_tex_lookup > 0 and o_tex_lookup + n_tex_lookup * 2 <= len(hdr):
            tex_lookup = list(struct.unpack_from(f"<{n_tex_lookup}H", hdr, o_tex_lookup))

    return {
        "name": m2_path.stem,
        "vertices": vertices,
        "skin_fdids": skin_fdids,
        "tex_fdids": tex_fdids,
        "tex_lookup": tex_lookup,
    }


def parse_skin(skin_path: Path) -> dict:
    data = skin_path.read_bytes()
    if len(data) < 48 or data[:4] != b"SKIN":
        return {}

    n_indices, o_indices = struct.unpack_from("<II", data, 4)
    n_tris, o_tris = struct.unpack_from("<II", data, 12)
    n_submesh, o_submesh = struct.unpack_from("<II", data, 28)
    n_batches, o_batches = struct.unpack_from("<II", data, 36)

    vert_lookup = list(struct.unpack_from(f"<{n_indices}H", data, o_indices))
    tri_indices = list(struct.unpack_from(f"<{n_tris}H", data, o_tris))

    submeshes = []
    for i in range(n_submesh):
        so = o_submesh + i * 48
        if so + 48 > len(data):
            break
        sm_id = struct.unpack_from("<H", data, so)[0]
        start_vert, n_vert = struct.unpack_from("<HH", data, so + 4)
        start_tri, n_tri = struct.unpack_from("<HH", data, so + 8)
        submeshes.append({
            "id": sm_id,
            "startVert": start_vert,
            "nVert": n_vert,
            "startTri": start_tri,
            "nTri": n_tri,
        })

    batches = []
    for i in range(n_batches):
        bo = o_batches + i * 24
        if bo + 24 > len(data):
            break
        submesh_idx = struct.unpack_from("<H", data, bo + 4)[0]
        tex_count = struct.unpack_from("<H", data, bo + 14)[0]
        tex_combo_idx = struct.unpack_from("<H", data, bo + 16)[0]
        batches.append({
            "submeshIdx": submesh_idx,
            "texCount": tex_count,
            "texComboIdx": tex_combo_idx,
        })

    return {
        "vertLookup": vert_lookup,
        "indices": tri_indices,
        "submeshes": submeshes,
        "batches": batches,
    }


def export_model(m2_path: Path, skin_path: Path | None, out_dir: Path) -> Path | None:
    out_dir.mkdir(parents=True, exist_ok=True)

    m2_data = parse_m2(m2_path)
    if not m2_data or not m2_data["vertices"]:
        print(f"  Failed to parse {m2_path.name}")
        return None

    skin_data = None
    if skin_path and skin_path.exists():
        skin_data = parse_skin(skin_path)

    positions = []
    normals = []
    uvs = []
    for v in m2_data["vertices"]:
        positions.extend(v["p"])
        normals.extend(v["n"])
        uvs.extend(v["uv"])

    indices = []
    if skin_data and skin_data["indices"]:
        lookup = skin_data["vertLookup"]
        for idx in skin_data["indices"]:
            indices.append(lookup[idx] if idx < len(lookup) else 0)
    else:
        indices = list(range(len(m2_data["vertices"])))

    submeshes_out = []
    if skin_data and skin_data.get("submeshes") and skin_data.get("batches"):
        tex_lookup = m2_data.get("tex_lookup", [])
        tex_fdids = m2_data.get("tex_fdids", [])
        for i, sm in enumerate(skin_data["submeshes"]):
            tex_fdid = 0
            for batch in skin_data["batches"]:
                if batch["submeshIdx"] == i:
                    combo_idx = batch["texComboIdx"]
                    if combo_idx < len(tex_lookup):
                        tex_idx = tex_lookup[combo_idx]
                        if tex_idx < len(tex_fdids):
                            tex_fdid = tex_fdids[tex_idx]
                    break
            submeshes_out.append({
                "startIndex": sm["startTri"],
                "indexCount": sm["nTri"],
                "texFdid": tex_fdid,
            })

    out = {
        "name": m2_data["name"],
        "nVerts": len(m2_data["vertices"]),
        "positions": [round(v, 4) for v in positions],
        "normals": [round(v, 4) for v in normals],
        "uvs": [round(v, 5) for v in uvs],
        "indices": indices,
        "texFdids": m2_data["tex_fdids"],
        "submeshes": submeshes_out,
    }

    out_path = out_dir / f"{m2_data['name']}.json"
    with open(out_path, "w") as f:
        json.dump(out, f)

    n_sub = len(submeshes_out)
    print(f"  {m2_data['name']}: {out['nVerts']} verts, {len(indices)//3} tris, {n_sub} submeshes, {len(m2_data['tex_fdids'])} textures")
    return out_path


def download_and_export(fdid: int, out_dir: Path = Path("assets/models")) -> Path | None:
    from extract.download import download_raw, load_listfile

    out_dir.mkdir(parents=True, exist_ok=True)
    m2_dir = Path("assets/m2")
    m2_dir.mkdir(parents=True, exist_ok=True)

    entries = {f: p for f, p in load_listfile() if f == fdid}
    name = Path(entries.get(fdid, f"{fdid}.m2")).stem

    m2_path = m2_dir / f"{name}.m2"
    download_raw(fdid, m2_path)
    if not m2_path.exists():
        return None

    m2_data = parse_m2(m2_path)
    if not m2_data:
        return None

    skin_path = None
    if m2_data["skin_fdids"]:
        skin_path = m2_dir / f"{name}_00.skin"
        download_raw(m2_data["skin_fdids"][0], skin_path)

    for tex_fdid in m2_data["tex_fdids"]:
        blp_path = m2_dir / f"tex_{tex_fdid}.blp"
        webp_path = out_dir / f"tex_{tex_fdid}.webp"
        if not webp_path.exists():
            download_raw(tex_fdid, blp_path)
            if blp_path.exists():
                try:
                    img = Image.open(blp_path)
                    img.save(webp_path)
                except Exception:
                    pass

    return export_model(m2_path, skin_path, out_dir)


def reexport_all(m2_dir: Path = Path("assets/m2"), out_dir: Path = Path("assets/models")):
    m2_files = sorted(m2_dir.glob("*.m2"))
    if not m2_files:
        print(f"No M2 files in {m2_dir}")
        return
    print(f"Re-exporting {len(m2_files)} models...")
    for m2 in m2_files:
        skin = m2_dir / f"{m2.stem}_00.skin"
        skin_path = skin if skin.exists() else None
        result = export_model(m2, skin_path, out_dir)
        if result:
            print(f"  -> {result}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m pipeline.m2 <fdid|--reexport> [fdid...]")
        sys.exit(1)

    if sys.argv[1] == "--reexport":
        reexport_all()
    else:
        out_dir = Path("assets/models")
        for arg in sys.argv[1:]:
            fdid = int(arg)
            print(f"Processing fdid={fdid}...")
            result = download_and_export(fdid, out_dir)
            if result:
                print(f"  -> {result}")
