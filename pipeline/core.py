"""Game-agnostic texture upscaling via fal.ai Nano Banana Pro.

Public API:
    upscale_texture()  -- upscale a single texture file
    upscale_textures() -- batch-upscale a directory of textures
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from math import gcd
from pathlib import Path

import fal_client
import numpy as np
import requests
from dotenv import load_dotenv
from PIL import Image, ImageFilter

load_dotenv()

_fal_key = os.getenv("FAL_KEY") or os.getenv("FAL_API_KEY")
if _fal_key:
    os.environ["FAL_KEY"] = _fal_key

_NANO_PRO = "fal-ai/nano-banana-2/edit"
_IMG_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tga", ".webp"}

_ASPECT_MAP = {
    (1, 1): "1:1", (4, 3): "4:3", (3, 4): "3:4",
    (16, 9): "16:9", (9, 16): "9:16", (3, 2): "3:2", (2, 3): "2:3",
    (5, 4): "5:4", (4, 5): "4:5", (21, 9): "21:9",
    (1, 2): "9:16", (2, 1): "16:9",
    (1, 4): "9:16", (4, 1): "16:9",
}


def _guess_aspect(w, h):
    g = gcd(w, h)
    ratio = (w // g, h // g)
    return _ASPECT_MAP.get(ratio, "auto")


def _tile_2x2(img):
    w, h = img.size
    tiled = Image.new(img.mode, (w * 2, h * 2))
    for dx in range(2):
        for dy in range(2):
            tiled.paste(img, (dx * w, dy * h))
    return tiled


def _make_seamless(img, blend_pct=0.20):
    arr = np.array(img, dtype=np.float32)
    h, w = arr.shape[:2]
    bw, bh = int(w * blend_pct), int(h * blend_pct)
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
    return Image.fromarray(
        np.clip(arr * mask + rolled * (1 - mask), 0, 255).astype(np.uint8)
    )


def _smooth_patches(img, radius=12):
    arr = np.array(img, dtype=np.float32)
    blurred = np.array(
        img.filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32
    )
    return Image.fromarray(
        np.clip(arr * 0.85 + blurred * 0.15, 0, 255).astype(np.uint8)
    )


def _nano_pro_edit(prompt, ref_path, resolution="4K", aspect="auto"):
    img_url = fal_client.upload_file(str(ref_path))
    result = fal_client.subscribe(
        _NANO_PRO,
        arguments={
            "prompt": prompt,
            "image_urls": [img_url],
            "resolution": resolution,
            "aspect_ratio": aspect,
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


def _gen_normal_map(img_path, strength=2.5):
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
    ln = np.sqrt(dx * dx + dy * dy + nz * nz)
    r = ((-dx / ln * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)
    g = ((-dy / ln * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)
    b = ((nz / ln * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)
    return Image.fromarray(np.stack([r, g, b], axis=-1))


def _gen_heightmap(img_path, blur_radius=1.0):
    img = Image.open(img_path).convert("L")
    if blur_radius > 0:
        img = img.filter(ImageFilter.GaussianBlur(blur_radius))
    return img


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def upscale_texture(src, out, prompt, resolution="4K", seamless=True,
                    normals=False, heights=False,
                    normals_dir=None, heights_dir=None):
    """AI-upscale a single texture via fal.ai Nano Banana Pro.

    Handles 2x2 tiling (seamless), cross-blend, alpha preservation,
    aspect detection, brightness smoothing, and optional PBR map
    generation -- all internally.

    Normal/height maps are written to *normals_dir* / *heights_dir* when
    provided, otherwise next to *out*.
    """
    src, out = Path(src), Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)

    orig = Image.open(src)
    has_alpha = orig.mode == "RGBA"
    alpha = orig.split()[3] if has_alpha else None
    rgb = orig.convert("RGB")
    aspect = _guess_aspect(*orig.size)

    tmp = out.parent / f"_tmp_{out.stem}.png"
    (_tile_2x2(rgb) if seamless else rgb).save(tmp)

    img = _nano_pro_edit(prompt, tmp, resolution=resolution, aspect=aspect)
    tmp.unlink(missing_ok=True)
    img = img.convert("RGB")

    if seamless:
        rw, rh = img.size
        img = img.crop((rw // 4, rh // 4, rw * 3 // 4, rh * 3 // 4))
        img = _make_seamless(img, blend_pct=0.35)

    img = _smooth_patches(img)

    if has_alpha and alpha is not None:
        up_alpha = alpha.resize(img.size, Image.LANCZOS)
        result = Image.merge("RGBA", (*img.split(), up_alpha))
    else:
        result = img

    result.save(out)

    if normals:
        n_dir = Path(normals_dir) if normals_dir else out.parent
        n_dir.mkdir(parents=True, exist_ok=True)
        _gen_normal_map(out).save(n_dir / f"{out.stem}_n{out.suffix}")
    if heights:
        h_dir = Path(heights_dir) if heights_dir else out.parent
        h_dir.mkdir(parents=True, exist_ok=True)
        _gen_heightmap(out).save(h_dir / f"{out.stem}_h{out.suffix}")

    return out


def upscale_textures(src_dir, out_dir, prompt, resolution="4K", seamless=True,
                     normals=False, heights=False, workers=6,
                     skip_existing=True, normals_dir=None, heights_dir=None):
    """Batch-upscale all textures in a directory.

    Walks *src_dir* for image files, calls :func:`upscale_texture` per
    file via ``ThreadPoolExecutor``.  Returns list of output paths.
    """
    src_dir, out_dir = Path(src_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(
        f for f in src_dir.iterdir()
        if f.is_file() and f.suffix.lower() in _IMG_EXTS
        and not f.name.startswith("_tmp_")
    )
    if not files:
        print(f"No images found in {src_dir}")
        return []

    def _do(src_path):
        out_path = out_dir / src_path.name
        if skip_existing and out_path.exists():
            print(f"  SKIP: {src_path.name}")
            return out_path
        print(f"  Upscaling {src_path.name}...")
        return upscale_texture(
            src_path, out_path, prompt,
            resolution=resolution, seamless=seamless,
            normals=normals, heights=heights,
            normals_dir=normals_dir, heights_dir=heights_dir,
        )

    results = []
    print(f"Upscaling {len(files)} textures with {workers} workers...")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(_do, f): f for f in files}
        for i, fut in enumerate(as_completed(futs), 1):
            src_f = futs[fut]
            try:
                results.append(fut.result())
                print(f"  [{i}/{len(files)}] {src_f.name} OK")
            except Exception as e:
                print(f"  [{i}/{len(files)}] {src_f.name} FAILED: {e}")

    print(f"\nDone: {len(results)}/{len(files)} upscaled")
    return results
