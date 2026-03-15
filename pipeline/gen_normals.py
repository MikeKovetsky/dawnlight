"""Generate normal maps and heightmaps from terrain diffuse textures.

Uses Sobel-based gradient extraction -- no external AI service needed.
"""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
TEX_ORIG = ROOT / "viewer" / "textures" / "original"
TEX_UP = ROOT / "viewer" / "textures" / "upscaled"
NORMALS_DIR = ROOT / "viewer" / "textures" / "normals"
HEIGHTS_DIR = ROOT / "viewer" / "textures" / "heights"

TEX_NAMES = [
    "elwynngrassbase",
    "elwynndirtbase2",
    "elwynnrockbasetest2",
    "elwynncobblestonebase",
]


def gen_normal_map(img_path: Path, strength: float = 2.0) -> Image.Image:
    img = Image.open(img_path).convert("L")
    h = np.array(img, dtype=np.float32) / 255.0

    dx = np.zeros_like(h)
    dy = np.zeros_like(h)
    dx[:, 1:-1] = (h[:, 2:] - h[:, :-2]) * strength
    dy[1:-1, :] = (h[2:, :] - h[:-2, :]) * strength
    dx[:, 0] = (h[:, 1] - h[:, 0]) * strength
    dx[:, -1] = (h[:, -1] - h[:, -2]) * strength
    dy[0, :] = (h[1, :] - h[0, :]) * strength
    dy[-1, :] = (h[-1, :] - h[-2, :]) * strength

    nz = np.ones_like(h)
    length = np.sqrt(dx * dx + dy * dy + nz * nz)
    nx = -dx / length
    ny = -dy / length
    nz = nz / length

    r = ((nx * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)
    g = ((ny * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)
    b = ((nz * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)

    return Image.fromarray(np.stack([r, g, b], axis=-1))


def gen_heightmap(img_path: Path, blur_radius: float = 1.0) -> Image.Image:
    img = Image.open(img_path).convert("L")
    if blur_radius > 0:
        img = img.filter(ImageFilter.GaussianBlur(blur_radius))
    return img


def main():
    parser = argparse.ArgumentParser(description="Generate normal maps & heightmaps")
    parser.add_argument("--strength", type=float, default=2.5)
    parser.add_argument("--blur", type=float, default=1.0, help="Heightmap blur radius")
    parser.add_argument("--upscaled", action="store_true", help="Use upscaled textures as source")
    parser.add_argument("--heights", action="store_true", help="Also generate heightmaps")
    args = parser.parse_args()

    src_dir = TEX_UP if args.upscaled else TEX_ORIG
    NORMALS_DIR.mkdir(parents=True, exist_ok=True)
    if args.heights:
        HEIGHTS_DIR.mkdir(parents=True, exist_ok=True)

    for name in TEX_NAMES:
        src = src_dir / f"{name}.webp"
        if not src.exists():
            print(f"  SKIP: {src} not found")
            continue

        out_n = NORMALS_DIR / f"{name}_n.webp"
        nmap = gen_normal_map(src, strength=args.strength)
        nmap.save(out_n)
        print(f"  normal: {out_n.name} ({nmap.size[0]}x{nmap.size[1]})")

        if args.heights:
            out_h = HEIGHTS_DIR / f"{name}_h.webp"
            hmap = gen_heightmap(src, blur_radius=args.blur)
            hmap.save(out_h)
            print(f"  height: {out_h.name} ({hmap.size[0]}x{hmap.size[1]})")

    print("\nDone.")


if __name__ == "__main__":
    main()
