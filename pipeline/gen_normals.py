"""Generate normal maps and heightmaps from diffuse textures.

Uses Sobel-based gradient extraction via pipeline.core internals.
No external AI service needed -- runs locally with numpy/Pillow.

Supports arbitrary input/output dirs; WoW Elwynn paths are defaults.
"""

import argparse
from pathlib import Path

from pipeline.core import _gen_normal_map, _gen_heightmap, _IMG_EXTS

ROOT = Path(__file__).resolve().parent.parent
TEX_ORIG = ROOT / "viewer" / "textures" / "original"
TEX_UP = ROOT / "viewer" / "textures" / "upscaled"
NORMALS_DIR = ROOT / "viewer" / "textures" / "normals"
HEIGHTS_DIR = ROOT / "viewer" / "textures" / "heights"

WOW_TEX_NAMES = [
    "elwynngrassbase",
    "elwynndirtbase2",
    "elwynnrockbasetest2",
    "elwynncobblestonebase",
]


def main():
    parser = argparse.ArgumentParser(description="Generate normal maps & heightmaps")
    parser.add_argument("input", nargs="?", help="Input file or directory (default: WoW originals)")
    parser.add_argument("-o", "--output", help="Output directory for normal maps")
    parser.add_argument("--strength", type=float, default=2.5)
    parser.add_argument("--blur", type=float, default=1.0, help="Heightmap blur radius")
    parser.add_argument("--upscaled", action="store_true", help="Use WoW upscaled textures as source")
    parser.add_argument("--heights", action="store_true", help="Also generate heightmaps")
    parser.add_argument("--heights-dir", help="Output directory for heightmaps (default: next to normals)")
    args = parser.parse_args()

    if args.input:
        src = Path(args.input)
        if src.is_file():
            files = [src]
        else:
            files = sorted(
                f for f in src.iterdir()
                if f.is_file() and f.suffix.lower() in _IMG_EXTS
            )
    else:
        src_dir = TEX_UP if args.upscaled else TEX_ORIG
        files = [src_dir / f"{n}.webp" for n in WOW_TEX_NAMES]

    normals_dir = Path(args.output) if args.output else NORMALS_DIR
    heights_dir = Path(args.heights_dir) if args.heights_dir else HEIGHTS_DIR
    normals_dir.mkdir(parents=True, exist_ok=True)
    if args.heights:
        heights_dir.mkdir(parents=True, exist_ok=True)

    for src_file in files:
        if not src_file.exists():
            print(f"  SKIP: {src_file} not found")
            continue

        out_n = normals_dir / f"{src_file.stem}_n{src_file.suffix}"
        nmap = _gen_normal_map(src_file, strength=args.strength)
        nmap.save(out_n)
        print(f"  normal: {out_n.name} ({nmap.size[0]}x{nmap.size[1]})")

        if args.heights:
            out_h = heights_dir / f"{src_file.stem}_h{src_file.suffix}"
            hmap = _gen_heightmap(src_file, blur_radius=args.blur)
            hmap.save(out_h)
            print(f"  height: {out_h.name} ({hmap.size[0]}x{hmap.size[1]})")

    print("\nDone.")


if __name__ == "__main__":
    main()
