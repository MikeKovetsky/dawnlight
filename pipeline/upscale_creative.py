"""Upscale WoW textures via Nano Banana Pro (upgraded from Nano Banana 2).

Delegates actual upscaling to pipeline.core.upscale_texture().
Supports both M2 model textures and terrain ground textures.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from pipeline.config import ensure_dirs
from pipeline.core import upscale_texture as _core_upscale

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "viewer" / "models"
ORIGINALS_DIR = MODELS_DIR / "originals"
COMPARE_DIR = MODELS_DIR / "creative_test"

TERRAIN_DIR = ROOT / "viewer" / "textures" / "original"
TERRAIN_OUT = ROOT / "viewer" / "textures" / "nanobanana"

TREE_FDIDS = [
    464350, 464351, 189570, 189563, 189520, 189554, 189519,
    131942, 198585, 189573, 189572, 189518, 249605, 189543,
    189542, 242694, 189403,
    132027, 132031, 189401, 189404, 189937, 202026, 321364,
]

TERRAIN_NAMES = [
    "elwynncobblestonebase",
    "elwynndirtbase2",
    "elwynngrassbase",
    "elwynnrockbasetest2",
]

_TEX_PROMPT = (
    "Upscale this video game texture to higher resolution. "
    "Keep the EXACT same composition, colors, shapes, and hand-painted art style. "
    "Add fine surface detail and sharpen edges. Do not change the content at all, "
    "only increase quality and resolution. This is a World of Warcraft tree texture."
)

_TERRAIN_PROMPT = (
    "Upscale this seamless tiling ground texture to higher resolution. "
    "Keep the EXACT same composition, colors, patterns, and hand-painted art style. "
    "Add fine surface detail. Do not change the content at all, "
    "only increase quality and resolution. This is a World of Warcraft terrain texture."
)


def upscale_texture(fdid, resolution="2K", skip_existing=True):
    out = COMPARE_DIR / f"tex_{fdid}_nanobanana.webp"
    if skip_existing and out.exists():
        print(f"  SKIP: {out.name} already exists")
        return out

    src = ORIGINALS_DIR / f"tex_{fdid}.webp"
    if not src.exists():
        src = MODELS_DIR / f"tex_{fdid}.webp"
    if not src.exists():
        print(f"  SKIP: tex_{fdid}.webp not found")
        return None

    print(f"  {src.name}: -> Nano Banana Pro @ {resolution}")
    _core_upscale(src, out, _TEX_PROMPT, resolution=resolution, seamless=False)
    print(f"    saved {out.name}")
    return out


def upscale_terrain(name, resolution="2K", skip_existing=True):
    TERRAIN_OUT.mkdir(parents=True, exist_ok=True)
    out = TERRAIN_OUT / f"{name}.webp"
    if skip_existing and out.exists():
        print(f"  SKIP: {out.name} already exists")
        return out

    src = TERRAIN_DIR / f"{name}.webp"
    if not src.exists():
        print(f"  SKIP: {name}.webp not found")
        return None

    print(f"  {src.name}: -> Nano Banana Pro @ {resolution}")
    _core_upscale(src, out, _TERRAIN_PROMPT, resolution=resolution, seamless=True)
    print(f"    saved {out.name}")
    return out


def _worker(key, resolution, is_terrain=False):
    try:
        if is_terrain:
            return key, upscale_terrain(key, resolution=resolution), None
        return key, upscale_texture(key, resolution=resolution), None
    except Exception as e:
        import traceback
        traceback.print_exc()
        return key, None, str(e)


def main():
    parser = argparse.ArgumentParser(description="Nano Banana Pro upscaling")
    parser.add_argument("--fdids", nargs="*", type=int)
    parser.add_argument("--all", action="store_true", help="All tree textures")
    parser.add_argument("--terrain", action="store_true", help="Terrain ground textures")
    parser.add_argument("-r", "--resolution", default="2K", choices=["0.5K", "1K", "2K", "4K"])
    parser.add_argument("-j", "--parallel", type=int, default=5, help="Parallel workers")
    parser.add_argument("--force", action="store_true", help="Re-process existing outputs")
    args = parser.parse_args()

    ensure_dirs()

    if args.terrain:
        keys = TERRAIN_NAMES
        is_terrain = True
        label = "terrain"
    else:
        keys = args.fdids or (TREE_FDIDS if args.all else [189563, 131942])
        is_terrain = False
        label = "M2"

    print(f"Nano Banana Pro upscaling {len(keys)} {label} textures @ {args.resolution} "
          f"(parallel={args.parallel})...\n")

    ok, skip, fail = 0, 0, 0

    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        futures = {
            pool.submit(_worker, k, args.resolution, is_terrain): k
            for k in keys
        }
        for i, future in enumerate(as_completed(futures), 1):
            key, result, error = future.result()
            tag = f"[{i}/{len(keys)}] {key}"
            if error:
                print(f"{tag} FAILED: {error}")
                fail += 1
            elif result:
                print(f"{tag} OK")
                ok += 1
            else:
                skip += 1

    out_dir = "viewer/textures/nanobanana/" if is_terrain else "viewer/models/creative_test/"
    print(f"\nDone: {ok} upscaled, {skip} skipped, {fail} failed")
    print(f"Results in {out_dir}")


if __name__ == "__main__":
    main()
