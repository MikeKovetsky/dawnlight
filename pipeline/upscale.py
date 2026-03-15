"""Batch texture upscaling via fal.ai Real-ESRGAN."""

import argparse
import sys
from io import BytesIO
from pathlib import Path

import fal_client
import requests
from PIL import Image

from pipeline.config import ESRGAN, IMG_EXTS, INPUT_DIR, UPSCALED_DIR, ensure_dirs


def upscale(path: Path, scale: int = 4, seamless: bool = False, out_dir: Path = UPSCALED_DIR) -> Path:
    ensure_dirs()
    out_dir.mkdir(parents=True, exist_ok=True)

    orig_size = None
    src = path

    if seamless:
        img = Image.open(path)
        orig_size = img.size
        src = _tile_2x2(path, img)

    url = fal_client.upload_file(str(src))

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

    out_url = result["image"]["url"]
    resp = requests.get(out_url, timeout=120)
    resp.raise_for_status()

    suffix = f"_{scale}x" if not seamless else f"_{scale}x_seamless"
    out_path = out_dir / f"{path.stem}{suffix}.webp"
    Image.open(BytesIO(resp.content)).save(out_path)

    if seamless:
        _crop_center_tile(out_path, orig_size, scale)
        src.unlink(missing_ok=True)

    return out_path


def _tile_2x2(path: Path, img: Image.Image) -> Path:
    w, h = img.size
    tiled = Image.new(img.mode, (w * 2, h * 2))
    for r in range(2):
        for c in range(2):
            tiled.paste(img, (c * w, r * h))

    tmp = path.parent / f"_tiled_{path.name}"
    tiled.save(tmp)
    return tmp


def _crop_center_tile(path: Path, orig_size: tuple[int, int], scale: int):
    img = Image.open(path)
    tw, th = orig_size[0] * scale, orig_size[1] * scale
    left = (img.width - tw) // 2
    top = (img.height - th) // 2
    cropped = img.crop((left, top, left + tw, top + th))
    cropped.save(path)


def batch(input_dir: Path, scale: int = 4, seamless: bool = False, out_dir: Path = UPSCALED_DIR):
    files = sorted(f for f in input_dir.iterdir() if f.suffix.lower() in IMG_EXTS)

    if not files:
        print(f"No images found in {input_dir}")
        return

    print(f"Upscaling {len(files)} textures at {scale}x (seamless={seamless})...")
    for i, f in enumerate(files, 1):
        print(f"  [{i}/{len(files)}] {f.name}")
        try:
            out = upscale(f, scale=scale, seamless=seamless, out_dir=out_dir)
            print(f"    -> {out.name}")
        except Exception as e:
            print(f"    ERROR: {e}")


def main():
    parser = argparse.ArgumentParser(description="AI texture upscaling via fal.ai Real-ESRGAN")
    parser.add_argument("input", nargs="?", help="Image file or directory (default: assets/input/)")
    parser.add_argument("-s", "--scale", type=int, default=4, choices=[2, 4], help="Upscale factor")
    parser.add_argument("--seamless", action="store_true", help="Preserve seamless tiling for ground textures")
    parser.add_argument("-o", "--output", help="Output directory (default: assets/upscaled/)")

    args = parser.parse_args()
    out_dir = Path(args.output) if args.output else UPSCALED_DIR

    target = Path(args.input) if args.input else INPUT_DIR
    if target.is_dir():
        batch(target, scale=args.scale, seamless=args.seamless, out_dir=out_dir)
    elif target.is_file():
        out = upscale(target, scale=args.scale, seamless=args.seamless, out_dir=out_dir)
        print(f"Saved: {out}")
    else:
        print(f"Not found: {target}")
        sys.exit(1)


if __name__ == "__main__":
    main()
