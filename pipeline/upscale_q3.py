"""Upscale Quake 3 PK3 textures using Dawnlight pipeline.

Usage:
    python -m pipeline.upscale_q3 /path/to/extracted_pk3/ \
        -o /path/to/upscaled/ --workers 6

    python -m pipeline.upscale_q3 /path/to/extracted_pk3/ \
        -o /path/to/upscaled/ --dirs textures models --resolution 2K
"""

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from pipeline.core import upscale_texture, _IMG_EXTS

_Q3_PROMPT = (
    "Upscale this game texture to higher resolution. "
    "Keep the exact same composition, colors, and art style. "
    "Add fine surface detail and sharpen edges."
)

_TEX_DIRS = {"textures", "models"}


def main():
    ap = argparse.ArgumentParser(
        description="AI-upscale Quake 3 PK3 textures via fal.ai"
    )
    ap.add_argument("input", help="Extracted PK3 directory")
    ap.add_argument("-o", "--output", required=True,
                    help="Output directory for upscaled textures")
    ap.add_argument("-p", "--prompt", default=_Q3_PROMPT)
    ap.add_argument("-r", "--resolution", default="2K",
                    choices=["1K", "2K", "4K"])
    ap.add_argument("--seamless", action="store_true", default=True)
    ap.add_argument("--no-seamless", dest="seamless", action="store_false")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--skip-existing", action="store_true", default=True)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dirs", nargs="+", default=list(_TEX_DIRS),
                    help="Subdirs to upscale (default: textures models)")
    args = ap.parse_args()

    if args.force:
        args.skip_existing = False

    src = Path(args.input)
    out = Path(args.output)

    files = []
    for d in args.dirs:
        dp = src / d
        if not dp.exists():
            print(f"  SKIP dir: {d} (not found)")
            continue
        for f in sorted(dp.rglob("*")):
            if f.is_file() and f.suffix.lower() in _IMG_EXTS:
                files.append(f)

    if not files:
        print(f"No images found in {src}")
        sys.exit(1)

    def _do(src_path):
        rel = src_path.relative_to(src)
        out_path = out / rel
        if args.skip_existing and out_path.exists():
            return out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        return upscale_texture(
            src_path, out_path, args.prompt,
            resolution=args.resolution, seamless=args.seamless,
        )

    print(f"Upscaling {len(files)} textures with {args.workers} workers...")
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(_do, f): f for f in files}
        for i, fut in enumerate(as_completed(futs), 1):
            sf = futs[fut]
            rel = sf.relative_to(src)
            try:
                results.append(fut.result())
                print(f"  [{i}/{len(files)}] {rel} OK")
            except Exception as e:
                print(f"  [{i}/{len(files)}] {rel} FAILED: {e}")

    print(f"\nDone: {len(results)}/{len(files)} upscaled")


if __name__ == "__main__":
    main()
