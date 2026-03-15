"""Upscale textures via fal.ai Nano Banana 2 (Gemini image-to-image).

Uses the edit endpoint to regenerate textures at higher resolution
while preserving the hand-painted WoW art style.
Supports both M2 model textures and terrain ground textures.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

import fal_client
import requests
from PIL import Image

from pipeline.config import ensure_dirs

NANO_BANANA = "fal-ai/nano-banana-2/edit"

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

ASPECT_MAP = {
    (1, 1): "1:1", (4, 3): "4:3", (3, 4): "3:4",
    (16, 9): "16:9", (9, 16): "9:16", (3, 2): "3:2", (2, 3): "2:3",
    (5, 4): "5:4", (4, 5): "4:5", (21, 9): "21:9",
    (1, 2): "9:16", (2, 1): "16:9",
    (1, 4): "1:4", (4, 1): "4:1", (1, 8): "1:8", (8, 1): "8:1",
}


def guess_aspect(w, h):
    from math import gcd
    g = gcd(w, h)
    ratio = (w // g, h // g)
    if ratio in ASPECT_MAP:
        return ASPECT_MAP[ratio]
    return "auto"


def nano_banana_upscale(img_path: Path, resolution: str = "2K",
                        aspect: str = "auto", prompt: str = "") -> bytes:
    url = fal_client.upload_file(str(img_path))

    if not prompt:
        prompt = (
            "Upscale this video game texture to higher resolution. "
            "Keep the EXACT same composition, colors, shapes, and hand-painted art style. "
            "Add fine surface detail and sharpen edges. Do not change the content at all, "
            "only increase quality and resolution. This is a World of Warcraft tree texture."
        )

    result = fal_client.subscribe(
        NANO_BANANA,
        arguments={
            "prompt": prompt,
            "image_urls": [url],
            "resolution": resolution,
            "aspect_ratio": aspect,
            "output_format": "png",
            "num_images": 1,
            "safety_tolerance": "6",
            "limit_generations": True,
        },
        with_logs=True,
    )

    img_data = result["images"][0]
    resp = requests.get(img_data["url"], timeout=180)
    resp.raise_for_status()
    return resp.content


def upscale_texture(fdid: int, resolution: str = "2K", skip_existing: bool = True, **kwargs):
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

    img = Image.open(src)
    w, h = img.size
    has_alpha = img.mode == "RGBA"
    aspect = guess_aspect(w, h)

    print(f"  {src.name}: {w}x{h} {img.mode} aspect={aspect} -> Nano Banana @ {resolution}")

    COMPARE_DIR.mkdir(parents=True, exist_ok=True)

    if has_alpha:
        rgb = img.convert("RGB")
        alpha = img.split()[3]

        tmp_rgb = COMPARE_DIR / f"_tmp_rgb_{fdid}.png"
        rgb.save(tmp_rgb)

        print(f"    uploading & upscaling RGB...")
        rgb_bytes = nano_banana_upscale(tmp_rgb, resolution=resolution, aspect=aspect, **kwargs)
        tmp_rgb.unlink(missing_ok=True)

        up_rgb = Image.open(BytesIO(rgb_bytes)).convert("RGB")
        up_alpha = alpha.resize(up_rgb.size, Image.LANCZOS)
        result = Image.merge("RGBA", (*up_rgb.split(), up_alpha))
    else:
        print(f"    uploading & upscaling...")
        data = nano_banana_upscale(src, resolution=resolution, aspect=aspect, **kwargs)
        result = Image.open(BytesIO(data))

    result.save(out)
    print(f"    saved {out.name} ({result.size[0]}x{result.size[1]} {result.mode})")
    return out


def upscale_terrain(name: str, resolution: str = "2K", skip_existing: bool = True):
    TERRAIN_OUT.mkdir(parents=True, exist_ok=True)
    out = TERRAIN_OUT / f"{name}.webp"
    if skip_existing and out.exists():
        print(f"  SKIP: {out.name} already exists")
        return out

    src = TERRAIN_DIR / f"{name}.webp"
    if not src.exists():
        print(f"  SKIP: {name}.webp not found")
        return None

    img = Image.open(src)
    w, h = img.size
    print(f"  {src.name}: {w}x{h} {img.mode} -> Nano Banana @ {resolution}")

    prompt = (
        "Upscale this seamless tiling ground texture to higher resolution. "
        "Keep the EXACT same composition, colors, patterns, and hand-painted art style. "
        "Add fine surface detail. Do not change the content at all, "
        "only increase quality and resolution. This is a World of Warcraft terrain texture."
    )

    print(f"    uploading & upscaling...")
    data = nano_banana_upscale(src, resolution=resolution,
                               aspect=guess_aspect(w, h), prompt=prompt)
    result = Image.open(BytesIO(data))
    result.save(out)
    print(f"    saved {out.name} ({result.size[0]}x{result.size[1]})")
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
    parser = argparse.ArgumentParser(description="Nano Banana 2 upscaling")
    parser.add_argument("--fdids", nargs="*", type=int)
    parser.add_argument("--all", action="store_true", help="All tree textures")
    parser.add_argument("--terrain", action="store_true", help="Terrain ground textures")
    parser.add_argument("-r", "--resolution", default="2K", choices=["0.5K", "1K", "2K", "4K"])
    parser.add_argument("-j", "--parallel", type=int, default=5, help="Parallel workers")
    parser.add_argument("--force", action="store_true", help="Re-process existing outputs")
    args = parser.parse_args()

    if args.terrain:
        keys = TERRAIN_NAMES
        is_terrain = True
        label = "terrain"
    else:
        keys = args.fdids or (TREE_FDIDS if args.all else [189563, 131942])
        is_terrain = False
        label = "M2"

    print(f"Nano Banana 2 upscaling {len(keys)} {label} textures @ {args.resolution} "
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
