"""Repack a Quake 3 PK3 with upscaled textures.

Usage:
    python -m pipeline.pk3_repack /path/to/extracted/ \
        --upscaled /path/to/upscaled/ -o DEMO_HD.pk3
"""

import argparse
import zipfile
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description="Repack PK3 with upscaled textures")
    ap.add_argument("input", help="Original extracted PK3 directory")
    ap.add_argument("--upscaled", required=True,
                    help="Directory with upscaled textures")
    ap.add_argument("-o", "--output", required=True, help="Output PK3 file")
    args = ap.parse_args()

    src = Path(args.input)
    upscaled = Path(args.upscaled)
    out = Path(args.output)

    files = sorted(f for f in src.rglob("*") if f.is_file())
    replaced = 0

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            rel = f.relative_to(src)
            up = upscaled / rel
            if up.exists():
                zf.write(up, str(rel))
                replaced += 1
            else:
                zf.write(f, str(rel))

    total = len(files)
    print(f"Packed {total} files into {out.name}")
    print(f"  Replaced: {replaced} textures with upscaled versions")
    print(f"  Original: {total - replaced} files kept as-is")
    print(f"  Size: {out.stat().st_size / 1048576:.1f} MB")


if __name__ == "__main__":
    main()
