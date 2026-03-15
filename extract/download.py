"""Download and convert WoW textures for the upscale pipeline.

Subcommands:
  fetch-listfile  Download the community listfile from GitHub
  search          Search the listfile for textures by path pattern
  get             Download BLP files from wow.tools by FileDataID
  elwynn          Download all known Elwynn Forest ground textures
  list            List known Elwynn texture paths
  convert         Convert a directory of BLP files to PNG
"""

import argparse
import sys
import time
from pathlib import Path

import requests
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.config import ASSETS, INPUT_DIR, ensure_dirs

LISTFILE_URL = "https://github.com/wowdev/wow-listfile/releases/latest/download/community-listfile.csv"
LISTFILE_PATH = ASSETS / "listfile.csv"

WAGO_FILE_URL = "https://wago.tools/api/casc/{fdid}"
WOWTOOLS_FALLBACK_URL = "https://wow.tools/casc/file/fdid?id={fdid}"

ELWYNN_ADT_RANGE = {
    "x": range(32, 35),
    "y": range(47, 53),
}

ADT_DIR = ASSETS / "adt"

ELWYNN_PATTERNS = [
    "tileset/elwynn/",
    "tileset/elwynnforest/",
]

GENERIC_GROUND_PATTERNS = [
    "tileset/generic/grass",
    "tileset/generic/dirt",
    "tileset/generic/cobblestone",
    "tileset/generic/road",
    "tileset/generic/mud",
    "tileset/generic/farmland",
    "tileset/generic/rock",
]

REQUEST_HEADERS = {
    "User-Agent": "Dawnlight/1.0 (WoW texture upscale research project)",
}


# -- listfile operations --


def fetch_listfile(force: bool = False):
    if LISTFILE_PATH.exists() and not force:
        size_mb = LISTFILE_PATH.stat().st_size / (1024 * 1024)
        print(f"Listfile already cached at {LISTFILE_PATH} ({size_mb:.1f} MB)")
        print("Use --force to re-download.")
        return

    ASSETS.mkdir(parents=True, exist_ok=True)
    print(f"Downloading community listfile from GitHub...")
    print(f"  {LISTFILE_URL}")

    resp = requests.get(LISTFILE_URL, headers=REQUEST_HEADERS, stream=True, timeout=120)
    resp.raise_for_status()

    total = int(resp.headers.get("content-length", 0))
    downloaded = 0

    with open(LISTFILE_PATH, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1024 * 256):
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = downloaded * 100 // total
                print(f"\r  {downloaded // (1024*1024)} / {total // (1024*1024)} MB ({pct}%)", end="", flush=True)

    print(f"\n  Saved to {LISTFILE_PATH}")


def load_listfile() -> list[tuple[int, str]]:
    if not LISTFILE_PATH.exists():
        print("Listfile not found. Run: python -m extract.download fetch-listfile")
        sys.exit(1)

    entries = []
    with open(LISTFILE_PATH, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or ";" not in line:
                continue
            parts = line.split(";", 1)
            try:
                fdid = int(parts[0])
                path = parts[1].lower()
                entries.append((fdid, path))
            except (ValueError, IndexError):
                continue
    return entries


def search_listfile(query: str, blp_only: bool = True, limit: int = 100):
    entries = load_listfile()
    query_lower = query.lower()

    matches = []
    for fdid, path in entries:
        if blp_only and not path.endswith(".blp"):
            continue
        if query_lower in path:
            matches.append((fdid, path))

    if not matches:
        print(f"No matches for '{query}'")
        return matches

    print(f"Found {len(matches)} matches for '{query}':")
    for fdid, path in matches[:limit]:
        print(f"  {fdid:>8}  {path}")
    if len(matches) > limit:
        print(f"  ... and {len(matches) - limit} more")

    return matches


def find_elwynn_textures() -> list[tuple[int, str]]:
    entries = load_listfile()
    matches = []

    all_patterns = ELWYNN_PATTERNS + GENERIC_GROUND_PATTERNS
    for fdid, path in entries:
        if not path.endswith(".blp"):
            continue
        if any(pat in path for pat in all_patterns):
            if "_s.blp" not in path and "_h.blp" not in path and "_n.blp" not in path:
                matches.append((fdid, path))

    return matches


# -- download operations --


def download_by_fdid(fdid: int, out_dir: Path = None) -> Path | None:
    if out_dir is None:
        out_dir = ASSETS / "blp"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"{fdid}.blp"
    if out_path.exists():
        return out_path

    for base_url in [WAGO_FILE_URL, WOWTOOLS_FALLBACK_URL]:
        url = base_url.format(fdid=fdid)
        try:
            resp = requests.get(url, headers=REQUEST_HEADERS, timeout=30)
            if resp.status_code == 200 and len(resp.content) > 100:
                out_path.write_bytes(resp.content)
                return out_path
        except requests.RequestException:
            continue

    return None


def download_and_convert(fdid: int, filepath: str, out_dir: Path = INPUT_DIR) -> Path | None:
    blp_dir = ASSETS / "blp"
    blp_path = download_by_fdid(fdid, blp_dir)

    if blp_path is None:
        return None

    ensure_dirs()
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = Path(filepath).stem if filepath else str(fdid)
    png_path = out_dir / f"{stem}.png"

    try:
        img = Image.open(blp_path)
        img.save(png_path, "PNG")
        return png_path
    except Exception:
        blp_path.unlink(missing_ok=True)
        return None


def batch_download(items: list[tuple[int, str]], out_dir: Path = INPUT_DIR, delay: float = 0.5):
    print(f"Downloading {len(items)} textures...")
    ok, fail = 0, 0

    for i, (fdid, filepath) in enumerate(items, 1):
        name = Path(filepath).stem
        print(f"  [{i}/{len(items)}] {name} (fdid={fdid})", end=" ")

        result = download_and_convert(fdid, filepath, out_dir)
        if result:
            img = Image.open(result)
            print(f"-> {result.name} ({img.size[0]}x{img.size[1]})")
            ok += 1
        else:
            print("FAILED")
            fail += 1

        if i < len(items):
            time.sleep(delay)

    print(f"\nDone: {ok} downloaded, {fail} failed")
    if fail > 0:
        print("For failed downloads, try manually at: https://wowtools.work/files/")


# -- ADT terrain download --


def download_raw(fdid: int, out_path: Path) -> bool:
    if out_path.exists():
        return True
    out_path.parent.mkdir(parents=True, exist_ok=True)
    for base_url in [WAGO_FILE_URL, WOWTOOLS_FALLBACK_URL]:
        url = base_url.format(fdid=fdid)
        try:
            resp = requests.get(url, headers=REQUEST_HEADERS, timeout=60)
            if resp.status_code == 200 and len(resp.content) > 100:
                out_path.write_bytes(resp.content)
                return True
        except requests.RequestException:
            continue
    return False


def find_adt_fdids(tile_x: int, tile_y: int) -> dict[str, tuple[int, str]]:
    entries = load_listfile()
    prefix = f"world/maps/azeroth/azeroth_{tile_x}_{tile_y}"
    result = {}
    for fdid, path in entries:
        if path.startswith(prefix):
            if path.endswith(".adt"):
                if "_tex0" in path:
                    result["tex0"] = (fdid, path)
                elif "_obj0" in path:
                    result["obj0"] = (fdid, path)
                elif "_lod" not in path and "_obj1" not in path and "_tex1" not in path:
                    result["root"] = (fdid, path)
    return result


def download_adt_tile(tile_x: int, tile_y: int) -> dict[str, Path]:
    fdids = find_adt_fdids(tile_x, tile_y)
    if not fdids:
        print(f"  No ADT files found for tile ({tile_x}, {tile_y})")
        return {}

    paths = {}
    for kind in ["root", "tex0", "obj0"]:
        if kind not in fdids:
            continue
        fdid, filepath = fdids[kind]
        suffix = f"_{kind}" if kind != "root" else ""
        out = ADT_DIR / f"azeroth_{tile_x}_{tile_y}{suffix}.adt"
        print(f"  [{kind}] fdid={fdid}", end=" ")
        if download_raw(fdid, out):
            print(f"-> {out.name} ({out.stat().st_size // 1024} KB)")
            paths[kind] = out
        else:
            print("FAILED")
    return paths


def download_elwynn_adt(tiles: list[tuple[int, int]] | None = None):
    if tiles is None:
        tiles = [
            (x, y)
            for x in ELWYNN_ADT_RANGE["x"]
            for y in ELWYNN_ADT_RANGE["y"]
        ]

    ADT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {len(tiles)} ADT tiles for Elwynn Forest...")

    all_paths = {}
    for tx, ty in tiles:
        print(f"\nTile ({tx}, {ty}):")
        paths = download_adt_tile(tx, ty)
        if paths:
            all_paths[(tx, ty)] = paths
        time.sleep(0.3)

    print(f"\nDone: {len(all_paths)} tiles downloaded to {ADT_DIR}")
    return all_paths


# -- BLP conversion --


def blp_to_png(blp_path: Path, out_dir: Path = INPUT_DIR) -> Path:
    ensure_dirs()
    out_dir.mkdir(parents=True, exist_ok=True)

    img = Image.open(blp_path)
    out_path = out_dir / f"{blp_path.stem}.png"
    img.save(out_path, "PNG")
    print(f"  {blp_path.name} -> {out_path.name} ({img.size[0]}x{img.size[1]})")
    return out_path


def convert_dir(src_dir: Path, out_dir: Path = INPUT_DIR):
    blps = sorted(src_dir.glob("*.blp"))
    if not blps:
        print(f"No .blp files found in {src_dir}")
        return

    print(f"Converting {len(blps)} BLP files to PNG...")
    for f in blps:
        try:
            blp_to_png(f, out_dir)
        except Exception as e:
            print(f"  ERROR {f.name}: {e}")


# -- CLI --


def main():
    parser = argparse.ArgumentParser(description="WoW asset download and conversion")
    sub = parser.add_subparsers(dest="cmd")

    fl = sub.add_parser("fetch-listfile", help="Download the community listfile from GitHub")
    fl.add_argument("--force", action="store_true", help="Re-download even if cached")

    sr = sub.add_parser("search", help="Search the listfile for textures")
    sr.add_argument("query", help="Search query (e.g. 'elwynn', 'tileset/generic', 'goldshire')")
    sr.add_argument("--all-types", action="store_true", help="Include non-BLP files")
    sr.add_argument("--limit", type=int, default=100)

    gt = sub.add_parser("get", help="Download BLP files by FileDataID")
    gt.add_argument("fdids", nargs="+", type=int, help="FileDataIDs to download")
    gt.add_argument("-o", "--output", help="Output directory for PNGs")

    sub.add_parser("elwynn", help="Download all known Elwynn Forest ground textures")

    adt_p = sub.add_parser("adt", help="Download ADT terrain tiles for Elwynn Forest")
    adt_p.add_argument("--tile", help="Single tile as X,Y (e.g. 32,49)", default=None)

    sub.add_parser("list", help="List known Elwynn texture paths")

    conv = sub.add_parser("convert", help="Convert BLP files to PNG")
    conv.add_argument("dir", help="Directory containing .blp files")
    conv.add_argument("-o", "--output", help="Output directory")

    args = parser.parse_args()

    if args.cmd == "fetch-listfile":
        fetch_listfile(force=args.force)

    elif args.cmd == "search":
        search_listfile(args.query, blp_only=not args.all_types, limit=args.limit)

    elif args.cmd == "get":
        out = Path(args.output) if args.output else INPUT_DIR
        for fdid in args.fdids:
            result = download_and_convert(fdid, "", out)
            if result:
                print(f"  {fdid} -> {result}")
            else:
                print(f"  {fdid} FAILED")

    elif args.cmd == "elwynn":
        fetch_listfile()
        textures = find_elwynn_textures()
        if not textures:
            print("No Elwynn textures found in listfile.")
            return
        print(f"\nFound {len(textures)} Elwynn-related ground textures:")
        for fdid, path in textures:
            print(f"  {fdid:>8}  {path}")
        print()
        batch_download(textures)

    elif args.cmd == "adt":
        fetch_listfile()
        if args.tile:
            tx, ty = (int(v) for v in args.tile.split(","))
            download_elwynn_adt([(tx, ty)])
        else:
            download_elwynn_adt()

    elif args.cmd == "list":
        print("Known Elwynn Forest ground texture paths:")
        patterns = ELWYNN_PATTERNS + GENERIC_GROUND_PATTERNS
        for p in patterns:
            print(f"  {p}*")
        print(f"\nRun 'python -m extract.download elwynn' to download them all.")

    elif args.cmd == "convert":
        out = Path(args.output) if args.output else INPUT_DIR
        convert_dir(Path(args.dir), out)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
