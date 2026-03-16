"""Batch texture upscaling via fal.ai.

Default: Nano Banana Pro (via core.upscale_texture).
Legacy:  Real-ESRGAN (--esrgan flag).
"""

import argparse
import sys
from io import BytesIO
from pathlib import Path

import fal_client
import requests
from PIL import Image

from pipeline.config import ESRGAN, IMG_EXTS, INPUT_DIR, UPSCALED_DIR, ensure_dirs
from pipeline.core import upscale_texture as _core_upscale


def _esrgan_upscale(path, scale=4, out_dir=UPSCALED_DIR):
    """Legacy Real-ESRGAN upscale (no prompt, pure resolution boost)."""
    url = fal_client.upload_file(str(path))
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
    out_path = out_dir / f"{path.stem}_{scale}x.png"
    out_path.write_bytes(resp.content)
    return out_path


def upscale(path, scale=4, seamless=False, out_dir=UPSCALED_DIR,
            legacy_esrgan=False):
    ensure_dirs()
    out_dir.mkdir(parents=True, exist_ok=True)

    if legacy_esrgan:
        return _esrgan_upscale(path, scale=scale, out_dir=out_dir)

    prompt = (
        "Upscale this game texture to higher resolution. "
        "Keep the EXACT same composition, colors, and style. "
        "Add fine surface detail. Do not change the content."
    )
    out_path = out_dir / f"{path.stem}_upscaled.png"
    return _core_upscale(path, out_path, prompt, seamless=seamless)


def batch(input_dir, scale=4, seamless=False, out_dir=UPSCALED_DIR,
          legacy_esrgan=False):
    files = sorted(f for f in input_dir.iterdir() if f.suffix.lower() in IMG_EXTS)
    if not files:
        print(f"No images found in {input_dir}")
        return

    label = "ESRGAN" if legacy_esrgan else "Nano Banana Pro"
    print(f"Upscaling {len(files)} textures via {label} (seamless={seamless})...")
    for i, f in enumerate(files, 1):
        print(f"  [{i}/{len(files)}] {f.name}")
        try:
            out = upscale(f, scale=scale, seamless=seamless, out_dir=out_dir,
                          legacy_esrgan=legacy_esrgan)
            print(f"    -> {out.name}")
        except Exception as e:
            print(f"    ERROR: {e}")


def main():
    parser = argparse.ArgumentParser(description="AI texture upscaling via fal.ai")
    parser.add_argument("input", nargs="?", help="Image file or directory (default: assets/input/)")
    parser.add_argument("-s", "--scale", type=int, default=4, choices=[2, 4], help="Upscale factor")
    parser.add_argument("--seamless", action="store_true", help="Preserve seamless tiling")
    parser.add_argument("--esrgan", action="store_true", help="Use legacy Real-ESRGAN instead of Nano Banana Pro")
    parser.add_argument("-o", "--output", help="Output directory (default: assets/upscaled/)")

    args = parser.parse_args()
    out_dir = Path(args.output) if args.output else UPSCALED_DIR

    target = Path(args.input) if args.input else INPUT_DIR
    if target.is_dir():
        batch(target, scale=args.scale, seamless=args.seamless, out_dir=out_dir,
              legacy_esrgan=args.esrgan)
    elif target.is_file():
        out = upscale(target, scale=args.scale, seamless=args.seamless, out_dir=out_dir,
                      legacy_esrgan=args.esrgan)
        print(f"Saved: {out}")
    else:
        print(f"Not found: {target}")
        sys.exit(1)


if __name__ == "__main__":
    main()
