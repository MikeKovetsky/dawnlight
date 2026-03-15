"""Upscale M2 model textures (trees, fences) via fal.ai Real-ESRGAN.

Handles RGBA textures by upscaling RGB and alpha channels separately,
then recombining. Backs up originals before overwriting.
"""

import argparse
import sys
from pathlib import Path

import fal_client
import requests
from PIL import Image

from pipeline.config import ESRGAN, ensure_dirs

MODELS_DIR = Path(__file__).resolve().parent.parent / "viewer" / "models"
BACKUP_DIR = MODELS_DIR / "originals"

TREE_FDIDS = [
    464350, 464351, 189570, 189563, 189520, 189554, 189519,
    131942, 198585, 189573, 189572, 189518, 249605, 189543,
    189542, 242694, 189403,
]

FENCE_FDIDS = [
    189799, 189800, 130279, 189479, 189421, 189422, 189487,
]

ALL_FDIDS = TREE_FDIDS + FENCE_FDIDS


def esrgan_upscale(img_path: Path, scale: int) -> bytes:
    url = fal_client.upload_file(str(img_path))
    result = fal_client.subscribe(
        ESRGAN,
        arguments={
            "image_url": url,
            "scale": scale,
            "model": "RealESRGAN_x4plus",
            "output_format": "png",
        },
        with_logs=True,
    )
    resp = requests.get(result["image"]["url"], timeout=120)
    resp.raise_for_status()
    return resp.content


def upscale_texture(fdid: int, scale: int = 4, models_dir: Path = MODELS_DIR):
    src = models_dir / f"tex_{fdid}.webp"
    if not src.exists():
        print(f"  SKIP: {src.name} not found")
        return None

    img = Image.open(src)
    w, h = img.size
    has_alpha = img.mode == "RGBA"

    auto_scale = 2 if max(w, h) >= 2048 else scale

    print(f"  {src.name}: {w}x{h} {img.mode} -> {auto_scale}x = {w*auto_scale}x{h*auto_scale}")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup = BACKUP_DIR / src.name
    if not backup.exists():
        img.save(backup)
        print(f"    backed up -> originals/{src.name}")

    if has_alpha:
        rgb = img.convert("RGB")
        alpha = img.split()[3].convert("RGB")

        tmp_rgb = models_dir / f"_tmp_rgb_{fdid}.png"
        tmp_alpha = models_dir / f"_tmp_alpha_{fdid}.png"
        rgb.save(tmp_rgb)
        alpha.save(tmp_alpha)

        print(f"    upscaling RGB...")
        rgb_bytes = esrgan_upscale(tmp_rgb, auto_scale)
        print(f"    upscaling alpha...")
        alpha_bytes = esrgan_upscale(tmp_alpha, auto_scale)

        tmp_rgb.unlink(missing_ok=True)
        tmp_alpha.unlink(missing_ok=True)

        from io import BytesIO
        up_rgb = Image.open(BytesIO(rgb_bytes)).convert("RGB")
        up_alpha = Image.open(BytesIO(alpha_bytes)).convert("L")

        result = Image.merge("RGBA", (*up_rgb.split(), up_alpha))
    else:
        tmp = models_dir / f"_tmp_{fdid}.png"
        img.save(tmp)
        print(f"    upscaling...")
        data = esrgan_upscale(tmp, auto_scale)
        tmp.unlink(missing_ok=True)

        from io import BytesIO
        result = Image.open(BytesIO(data))

    result.save(src)
    print(f"    saved {result.size[0]}x{result.size[1]} {result.mode}")
    return src


def main():
    parser = argparse.ArgumentParser(description="Upscale M2 model textures")
    parser.add_argument("--fdids", nargs="*", type=int, help="Specific FDIDs (default: all trees+fences)")
    parser.add_argument("-s", "--scale", type=int, default=4, choices=[2, 4])
    parser.add_argument("--trees", action="store_true", help="Only tree textures")
    parser.add_argument("--fences", action="store_true", help="Only fence textures")
    args = parser.parse_args()

    if args.fdids:
        fdids = args.fdids
    elif args.trees:
        fdids = TREE_FDIDS
    elif args.fences:
        fdids = FENCE_FDIDS
    else:
        fdids = ALL_FDIDS

    print(f"Upscaling {len(fdids)} M2 textures...")
    ok, fail = 0, 0
    for i, fdid in enumerate(fdids, 1):
        print(f"[{i}/{len(fdids)}] tex_{fdid}")
        try:
            upscale_texture(fdid, scale=args.scale)
            ok += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            fail += 1

    print(f"\nDone: {ok} upscaled, {fail} failed")


if __name__ == "__main__":
    main()
