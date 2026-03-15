"""Prepare upscaled textures for import into a WoW 3.3.5a client via MPQ patch.

Creates a staging directory with the correct WoW internal file paths, converts
PNGs to BLP format (palette-mode via Pillow), and generates a manifest for
MPQ packaging.

For higher quality BLP (DXT compression), use BLPConverter on Windows:
  BLPConverter.exe -i staging/ -o staging/ -f blp2 -t dxt1

For MPQ packaging, use mpqcli or StormLib:
  mpqcli create patch-D.mpq staging/

Usage:
  python -m pipeline.mpq_export             # stage all upscaled terrain textures
  python -m pipeline.mpq_export --convert   # also convert PNG -> BLP (palette)
  python -m pipeline.mpq_export --list      # show manifest only
"""

import argparse
import sys
from pathlib import Path

from PIL import Image

from pipeline.config import UPSCALED_DIR

STAGING_DIR = Path("assets/mpq_staging")

UPSCALED_TO_WOW_PATH = {
    "elwynngrassbase": "tileset/elwynn/elwynngrassbase.blp",
    "elwynndirtbase2": "tileset/elwynn/elwynndirtbase2.blp",
    "elwynnrockbasetest2": "tileset/elwynn/elwynnrockbasetest2.blp",
    "elwynncobblestonebase": "tileset/elwynn/elwynncobblestonebase.blp",
    "elwynnflowerbase": "tileset/elwynn/elwynnflowerbase.blp",
    "elwynnleaf": "tileset/elwynn/elwynnleaf.blp",
    "elwynnrockbase": "tileset/elwynn/elwynnrockbase.blp",
    "elwynnrockgravel": "tileset/elwynn/elwynnrockgravel.blp",
    "elwynndirtbase": "tileset/elwynn/elwynndirtbase.blp",
}


def find_upscaled_textures() -> list[tuple[str, Path, str]]:
    results = []
    for name, wow_path in UPSCALED_TO_WOW_PATH.items():
        for suffix in ["_4x_seamless.png", "_4x.png"]:
            candidate = UPSCALED_DIR / f"{name}{suffix}"
            if candidate.exists():
                results.append((name, candidate, wow_path))
                break
    return results


def stage_textures(convert_blp: bool = False) -> list[dict]:
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    textures = find_upscaled_textures()

    if not textures:
        print("No upscaled textures found.")
        return []

    manifest = []
    for name, src, wow_path in textures:
        if convert_blp:
            blp_path = STAGING_DIR / wow_path
            blp_path.parent.mkdir(parents=True, exist_ok=True)
            png_to_blp_palette(src, blp_path)
            manifest.append({"name": name, "src": str(src), "wow_path": wow_path, "staged": str(blp_path)})
            print(f"  {name} -> {wow_path} (BLP palette)")
        else:
            png_dest = STAGING_DIR / wow_path.replace(".blp", ".png")
            png_dest.parent.mkdir(parents=True, exist_ok=True)
            img = Image.open(src)
            img.save(png_dest, "PNG")
            manifest.append({"name": name, "src": str(src), "wow_path": wow_path, "staged": str(png_dest)})
            print(f"  {name} -> {png_dest.relative_to(STAGING_DIR)}")

    return manifest


WOW335_MAX_TEX = 1024


def png_to_blp_palette(src: Path, dst: Path):
    img = Image.open(src)
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (0, 0, 0))
        bg.paste(img, mask=img.split()[3])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    if img.width > WOW335_MAX_TEX or img.height > WOW335_MAX_TEX:
        img = img.resize((WOW335_MAX_TEX, WOW335_MAX_TEX), Image.LANCZOS)

    quantized = img.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    quantized.save(dst, "BLP")


def print_manifest():
    textures = find_upscaled_textures()
    if not textures:
        print("No upscaled textures found.")
        return

    print(f"Upscaled textures ready for MPQ export ({len(textures)}):\n")
    for name, src, wow_path in textures:
        img = Image.open(src)
        print(f"  {name}")
        print(f"    Source: {src.name} ({img.size[0]}x{img.size[1]})")
        print(f"    WoW path: {wow_path}")
        print()

    print("To create MPQ patch:")
    print("  1. python -m pipeline.mpq_export --convert")
    print("  2. Copy staging dir to Windows")
    print("  3. Use BLPConverter for DXT quality (optional):")
    print("     BLPConverter.exe -i staging/ -o staging/ -f blp2 -t dxt1")
    print("  4. Package with mpqcli or MPQ Editor:")
    print("     mpqcli create patch-D.mpq staging/")
    print("  5. Place patch-D.mpq in WoW 3.3.5a Data/ folder")


def main():
    global STAGING_DIR
    parser = argparse.ArgumentParser(description="Prepare upscaled textures for WoW MPQ patching")
    parser.add_argument("--convert", action="store_true", help="Convert PNGs to BLP (palette mode)")
    parser.add_argument("--list", action="store_true", help="Show manifest only")
    parser.add_argument("-o", "--output", help=f"Staging directory (default: {STAGING_DIR})")

    args = parser.parse_args()

    if args.output:
        STAGING_DIR = Path(args.output)

    if args.list:
        print_manifest()
    else:
        print(f"Staging upscaled textures to {STAGING_DIR}...")
        manifest = stage_textures(convert_blp=args.convert)
        print(f"\nStaged {len(manifest)} textures.")
        if not args.convert:
            print("Run with --convert to also generate BLP files.")


if __name__ == "__main__":
    main()
