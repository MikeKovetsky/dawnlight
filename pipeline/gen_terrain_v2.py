"""Enhance terrain textures via fal.ai Nano Banana Pro.

WoW-specific terrain prompts. Delegates actual upscaling to
pipeline.core.upscale_texture() which handles seamless tiling internally.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from pipeline.config import ensure_dirs
from pipeline.core import upscale_texture

ROOT = Path(__file__).resolve().parent.parent
TERRAIN_SRC = ROOT / "viewer" / "textures" / "original"
TERRAIN_OUT = ROOT / "viewer" / "textures" / "v2"

TERRAIN_PROMPTS = {
    "elwynngrassbase": (
        "Transform this grass ground texture into a highly detailed, realistic yet "
        "stylized lush meadow grass. Add individual grass blade detail, natural color "
        "variation from golden-green to deep emerald, subtle wildflower specks, and "
        "rich organic depth. Keep the hand-painted World of Warcraft art style with "
        "warm fantasy lighting. Seamless tiling ground texture for a fantasy RPG."
    ),
    "elwynndirtbase2": (
        "Transform this dirt ground texture into a highly detailed, realistic yet "
        "stylized forest floor earth. Add natural soil grain, tiny scattered pebbles, "
        "fine root impressions, dried leaf fragments, and organic debris. Rich brown "
        "earth tones with natural moisture variation. Keep the hand-painted World of "
        "Warcraft art style. Seamless tiling ground texture for a fantasy RPG."
    ),
    "elwynnrockbasetest2": (
        "Transform this rock ground texture into a highly detailed, realistic yet "
        "stylized natural stone surface. Add realistic weathering, fine grain structure, "
        "subtle lichen patches, natural cracks and stratification layers, and mineral "
        "color variation. Keep the hand-painted World of Warcraft art style with warm "
        "fantasy tones. Seamless tiling ground texture for a fantasy RPG."
    ),
    "elwynncobblestonebase": (
        "Transform this cobblestone ground texture into a highly detailed, realistic "
        "yet stylized medieval cobblestone road. Add individual stone detail with "
        "subtle chisel marks, worn surfaces, moss growing between stones, fine mortar "
        "lines, and natural wear patterns. Keep the hand-painted World of Warcraft "
        "art style with warm fantasy lighting. Seamless tiling ground texture."
    ),
}


def enhance_terrain(name, resolution="4K", skip_existing=True):
    TERRAIN_OUT.mkdir(parents=True, exist_ok=True)
    out = TERRAIN_OUT / f"{name}.webp"
    if skip_existing and out.exists():
        print(f"  SKIP: {out.name} already exists")
        return out

    src = TERRAIN_SRC / f"{name}.webp"
    if not src.exists():
        print(f"  SKIP: {name}.webp not found in {TERRAIN_SRC}")
        return None

    prompt = TERRAIN_PROMPTS.get(name)
    if not prompt:
        print(f"  SKIP: no prompt defined for {name}")
        return None

    print(f"  {name}: -> Nano Banana Pro @ {resolution}")
    upscale_texture(src, out, prompt, resolution=resolution, seamless=True)
    print(f"  saved {out.name} [seamless]")
    return out


def _worker(name, resolution):
    try:
        return name, enhance_terrain(name, resolution=resolution, skip_existing=False), None
    except Exception as e:
        import traceback
        traceback.print_exc()
        return name, None, str(e)


def main():
    parser = argparse.ArgumentParser(description="Nano Banana Pro terrain enhancement (v2)")
    parser.add_argument("--names", nargs="*", help="Specific texture names to process")
    parser.add_argument("-r", "--resolution", default="4K", choices=["1K", "2K", "4K"])
    parser.add_argument("-j", "--parallel", type=int, default=4)
    args = parser.parse_args()

    ensure_dirs()
    names = args.names or list(TERRAIN_PROMPTS.keys())

    print(f"Nano Banana Pro terrain enhancement: {len(names)} textures @ {args.resolution}\n")

    ok, fail = 0, 0
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        futures = {pool.submit(_worker, n, args.resolution): n for n in names}
        for i, future in enumerate(as_completed(futures), 1):
            name, result, error = future.result()
            tag = f"[{i}/{len(names)}] {name}"
            if error:
                print(f"{tag} FAILED: {error}")
                fail += 1
            elif result:
                print(f"{tag} OK")
                ok += 1

    print(f"\nDone: {ok} enhanced, {fail} failed")
    print(f"Results in viewer/textures/v2/")


if __name__ == "__main__":
    main()
