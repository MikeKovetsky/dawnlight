"""Enhance terrain textures via fal.ai Nano Banana Pro.

Not a simple upscale — uses creative prompts to add realistic detail
while keeping the World of Warcraft hand-painted art style.
Outputs to viewer/textures/v2/ at 4K resolution.

Seamless tiling: feeds the AI a 2x2 tiled input so it sees the
tiling pattern, then crops back the center tile at full resolution.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

import fal_client
import numpy as np
import requests
from PIL import Image

from pipeline.config import ensure_dirs

NANO_PRO = "fal-ai/nano-banana-pro/edit"

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


def tile_2x2(img):
    """Tile an image into a 2x2 grid so the AI sees the tiling pattern."""
    w, h = img.size
    tiled = Image.new(img.mode, (w * 2, h * 2))
    for dx in range(2):
        for dy in range(2):
            tiled.paste(img, (dx * w, dy * h))
    return tiled


def make_seamless(img, blend_pct=0.20):
    """Cross-blend edges to guarantee seamless tiling.

    Rolls the image by half in both axes, then blends the rolled and
    original versions using a smooth gradient mask.  The result tiles
    perfectly because the edges come from what was the interior.
    """
    arr = np.array(img, dtype=np.float32)
    h, w = arr.shape[:2]
    bw = int(w * blend_pct)
    bh = int(h * blend_pct)

    rolled = np.roll(np.roll(arr, w // 2, axis=1), h // 2, axis=0)

    mx = np.ones(w, dtype=np.float32)
    mx[:bw] = np.linspace(0, 1, bw)
    mx[-bw:] = np.linspace(1, 0, bw)

    my = np.ones(h, dtype=np.float32)
    my[:bh] = np.linspace(0, 1, bh)
    my[-bh:] = np.linspace(1, 0, bh)

    mask = np.outer(my, mx)
    if arr.ndim == 3:
        mask = mask[:, :, np.newaxis]

    out = arr * mask + rolled * (1.0 - mask)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def nano_pro_enhance(prompt, src_path, resolution="4K"):
    img_url = fal_client.upload_file(str(src_path))
    result = fal_client.subscribe(
        NANO_PRO,
        arguments={
            "prompt": prompt,
            "image_urls": [img_url],
            "resolution": resolution,
            "aspect_ratio": "1:1",
            "output_format": "png",
            "num_images": 1,
            "safety_tolerance": "6",
        },
        with_logs=True,
    )
    url = result["images"][0]["url"]
    resp = requests.get(url, timeout=180)
    resp.raise_for_status()
    return Image.open(BytesIO(resp.content))


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

    img = Image.open(src).convert("RGB")
    w, h = img.size
    print(f"  {name}: {w}x{h} -> Nano Banana Pro @ {resolution}")
    print(f"    prompt: {prompt[:80]}...")

    tiled = tile_2x2(img)
    tmp = TERRAIN_OUT / f"_tmp_{name}.png"
    tiled.save(tmp)
    print(f"    tiled 2x2 -> {tiled.size[0]}x{tiled.size[1]}, sending to AI...")

    raw = nano_pro_enhance(prompt, tmp, resolution=resolution)
    tmp.unlink(missing_ok=True)

    rw, rh = raw.size
    cx, cy = rw // 4, rh // 4
    cw, ch = rw // 2, rh // 2
    center = raw.crop((cx, cy, cx + cw, cy + ch))
    print(f"    cropped center tile: {center.size[0]}x{center.size[1]}")

    result = make_seamless(center)
    result.save(out)
    print(f"    saved {out.name} ({result.size[0]}x{result.size[1]}) [seamless]")
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
