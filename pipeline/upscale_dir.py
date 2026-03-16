"""Generic batch texture upscaler -- works with any game's textures.

Usage:
    python -m pipeline.upscale_dir ./textures/ -o ./upscaled/ \\
        --prompt "sci-fi arena shooter" --workers 6

    python -m pipeline.upscale_dir wall.jpg -o ./out/

    python -m pipeline.upscale_dir ./textures/ -o ./upscaled/ \\
        --prompt "gothic stone" --normals --heights --workers 6
"""

import argparse
import sys
from pathlib import Path

from pipeline.core import upscale_texture, upscale_textures

_DEFAULT_PROMPT = (
    "Upscale this game texture to higher resolution. "
    "Keep the exact same composition, colors, and art style. "
    "Add fine surface detail and sharpen edges."
)


def main():
    parser = argparse.ArgumentParser(
        description="AI-upscale game textures via fal.ai Nano Banana Pro"
    )
    parser.add_argument("input", help="Image file or directory of textures")
    parser.add_argument("-o", "--output", required=True, help="Output file or directory")
    parser.add_argument("-p", "--prompt", default=_DEFAULT_PROMPT,
                        help="Style prompt for AI upscaler")
    parser.add_argument("-r", "--resolution", default="4K",
                        choices=["1K", "2K", "4K"])
    parser.add_argument("--seamless", action="store_true",
                        help="Preserve seamless tiling (2x2 tile + crop)")
    parser.add_argument("--no-seamless", dest="seamless", action="store_false")
    parser.set_defaults(seamless=True)
    parser.add_argument("--normals", action="store_true",
                        help="Generate normal maps alongside upscaled textures")
    parser.add_argument("--normals-dir",
                        help="Write normals to this directory (default: next to output)")
    parser.add_argument("--heights", action="store_true",
                        help="Generate heightmaps alongside upscaled textures")
    parser.add_argument("--heights-dir",
                        help="Write heightmaps to this directory (default: next to output)")
    parser.add_argument("--workers", type=int, default=6,
                        help="Parallel workers for batch mode")
    parser.add_argument("--skip-existing", action="store_true", default=True)
    parser.add_argument("--force", action="store_true",
                        help="Re-process existing outputs")
    args = parser.parse_args()

    if args.force:
        args.skip_existing = False

    src = Path(args.input)
    out = Path(args.output)

    if src.is_file():
        if out.is_dir() or not out.suffix:
            out = out / src.name
        upscale_texture(
            src, out, args.prompt,
            resolution=args.resolution, seamless=args.seamless,
            normals=args.normals, heights=args.heights,
            normals_dir=args.normals_dir, heights_dir=args.heights_dir,
        )
        print(f"Saved: {out}")
    elif src.is_dir():
        upscale_textures(
            src, out, args.prompt,
            resolution=args.resolution, seamless=args.seamless,
            normals=args.normals, heights=args.heights,
            workers=args.workers, skip_existing=args.skip_existing,
            normals_dir=args.normals_dir, heights_dir=args.heights_dir,
        )
    else:
        print(f"Not found: {src}")
        sys.exit(1)


if __name__ == "__main__":
    main()
