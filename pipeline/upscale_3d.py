"""Mesh-to-mesh 3D upscaling via render -> AI upscale -> Trellis 2 -> GLB.

Pipeline: render mesh on white bg -> Nano Banana Pro 4K upscale -> Trellis 2
image-to-3D -> download high-poly GLB.
"""

import argparse
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

import fal_client
import numpy as np
import requests
from PIL import Image

from pipeline.config import MESHES_DIR, TRELLIS

MESH_EXTS = {".glb", ".gltf", ".obj", ".ply", ".stl"}
NANO_BANANA_PRO = "fal-ai/nano-banana-pro/edit"


def _look_at(eye, target, up=np.array([0, 1, 0])):
    """Build a 4x4 camera-to-world matrix (OpenGL convention: -Z forward)."""
    fwd = target - eye
    fwd = fwd / np.linalg.norm(fwd)
    right = np.cross(fwd, up)
    right = right / np.linalg.norm(right)
    true_up = np.cross(right, fwd)
    mat = np.eye(4)
    mat[:3, 0] = right
    mat[:3, 1] = true_up
    mat[:3, 2] = -fwd
    mat[:3, 3] = eye
    return mat


def _auto_orient(mesh):
    """Rotate mesh so the tallest axis becomes Y-up."""
    extents = mesh.extents
    tallest = int(np.argmax(extents))
    if tallest == 1:
        return mesh
    rot = np.eye(4)
    if tallest == 2:  # Z-up -> Y-up: rotate +90deg around X
        rot[:3, :3] = [[1, 0, 0], [0, 0, 1], [0, -1, 0]]
    elif tallest == 0:  # X-up -> Y-up: rotate -90deg around Z
        rot[:3, :3] = [[0, 1, 0], [-1, 0, 0], [0, 0, 1]]
    mesh.apply_transform(rot)
    return mesh


def _render_mesh(mesh_path: Path, img_size: int = 1024,
                 tmp_dir: Path | None = None) -> Path:
    """Render a mesh from a 3/4 elevated angle on a white background."""
    import pyrender
    import trimesh
    from PIL import Image

    raw = trimesh.load(str(mesh_path), force="mesh")
    if isinstance(raw, trimesh.Scene):
        raw = raw.dump(concatenate=True)

    raw = _auto_orient(raw)

    scene = pyrender.Scene(
        bg_color=[255, 255, 255, 255],
        ambient_light=[0.6, 0.6, 0.6],
    )
    scene.add(pyrender.Mesh.from_trimesh(raw, smooth=True))

    center = raw.centroid
    extent = np.max(raw.extents)
    dist = extent * 2.2

    azimuth = np.radians(30)
    elevation = np.radians(20)
    cam_pos = center + dist * np.array([
        np.cos(elevation) * np.sin(azimuth),
        np.sin(elevation),
        np.cos(elevation) * np.cos(azimuth),
    ])

    camera = pyrender.PerspectiveCamera(yfov=np.pi / 3.5)
    scene.add(camera, pose=_look_at(cam_pos, center))

    key = pyrender.DirectionalLight(color=np.ones(3), intensity=3.0)
    scene.add(key, pose=_look_at(cam_pos, center))

    fill_pos = center + dist * np.array([-0.7, 0.2, 0.3])
    fill = pyrender.DirectionalLight(color=np.ones(3), intensity=2.5)
    scene.add(fill, pose=_look_at(fill_pos, center))

    back_pos = center + dist * np.array([0.0, 0.5, -0.8])
    back = pyrender.DirectionalLight(color=np.ones(3), intensity=1.5)
    scene.add(back, pose=_look_at(back_pos, center))

    renderer = pyrender.OffscreenRenderer(img_size, img_size)
    color, _ = renderer.render(scene)
    renderer.delete()

    img = Image.fromarray(color)
    out_dir = Path(tmp_dir) if tmp_dir else Path(tempfile.mkdtemp())
    out_path = out_dir / f"{mesh_path.stem}_render.png"
    img.save(out_path)
    print(f"  Rendered {mesh_path.name} -> {out_path.name} ({img_size}x{img_size})")
    return out_path


def _upscale_render(image_path: Path, tmp_dir: Path) -> Path:
    """AI-upscale a render to 4K via Nano Banana Pro for better Trellis input."""
    url = fal_client.upload_file(str(image_path))

    prompt = (
        "Upscale this 3D character render to ultra high resolution. "
        "Keep the EXACT same pose, proportions, colors, and appearance. "
        "Add fine skin pores, muscle fiber detail, rough leather grain, scratched metal, "
        "and matte hand-painted textures. Avoid plastic, shiny, or glossy surfaces. "
        "Do not change the composition at all, only increase quality and detail."
    )

    print("  AI upscaling render via Nano Banana Pro -> 4K...")
    result = fal_client.subscribe(
        NANO_BANANA_PRO,
        arguments={
            "prompt": prompt,
            "image_urls": [url],
            "resolution": "4K",
            "aspect_ratio": "1:1",
            "output_format": "png",
            "num_images": 1,
            "safety_tolerance": "6",
        },
        with_logs=True,
    )

    img_url = result["images"][0]["url"]
    resp = requests.get(img_url, timeout=180)
    resp.raise_for_status()

    out_path = tmp_dir / f"{image_path.stem}_4k.png"
    out_path.write_bytes(resp.content)
    img = Image.open(BytesIO(resp.content))
    print(f"  -> {out_path.name} ({img.size[0]}x{img.size[1]})")
    return out_path


def _trellis_generate(image_path: Path, out_path: Path,
                      resolution: int = 1536, decimation: int = 100_000,
                      tex_size: int = 2048, seed: int | None = None) -> Path:
    """Upload render to fal.ai Trellis 2 and download resulting GLB."""
    url = fal_client.upload_file(str(image_path))

    args = {
        "image_url": url,
        "resolution": resolution,
        "decimation_target": decimation,
        "texture_size": tex_size,
        "remesh": True,
        "remesh_project": 0.8,
        "ss_guidance_strength": 7.5,
        "ss_guidance_rescale": 0.7,
        "ss_sampling_steps": 16,
        "shape_slat_guidance_strength": 6.0,
        "shape_slat_sampling_steps": 16,
        "shape_slat_rescale_t": 4,
        "tex_slat_guidance_strength": 3.0,
        "tex_slat_sampling_steps": 20,
        "tex_slat_rescale_t": 5,
    }
    if seed is not None:
        args["seed"] = seed

    print(f"  Trellis 2: res={resolution} verts={decimation} tex={tex_size}")
    result = fal_client.subscribe(TRELLIS, arguments=args, with_logs=True)

    glb_url = result["model_glb"]["url"]
    resp = requests.get(glb_url, timeout=300)
    resp.raise_for_status()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(resp.content)
    print(f"  -> {out_path.name} ({len(resp.content) / 1024 / 1024:.1f} MB)")
    return out_path


def upscale_3d_asset(
    src: Path,
    out_dir: Path = MESHES_DIR,
    ref_image: Path | None = None,
    resolution: int = 1536,
    decimation: int = 100_000,
    tex_size: int = 2048,
    img_size: int = 1024,
    ai_upscale: bool = True,
    seed: int | None = None,
) -> Path:
    """Upscale a mesh via render -> AI upscale -> Trellis 2 -> GLB.

    Pipeline (no ref_image): render mesh -> Nano Banana Pro 4K -> Trellis 2
    Pipeline (ref_image):    ref_image -> Trellis 2 (skip render + upscale)
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{src.stem}_up.glb"

    if ref_image:
        print(f"  Using reference image: {ref_image.name}")
        _trellis_generate(
            ref_image, out_path,
            resolution=resolution, decimation=decimation,
            tex_size=tex_size, seed=seed,
        )
    else:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            render = _render_mesh(src, img_size=img_size, tmp_dir=tmp_path)
            if ai_upscale:
                render = _upscale_render(render, tmp_path)
            _trellis_generate(
                render, out_path,
                resolution=resolution, decimation=decimation,
                tex_size=tex_size, seed=seed,
            )

    return out_path


def upscale_3d_assets(
    src_dir: Path,
    out_dir: Path = MESHES_DIR,
    *,
    ref_image: Path | None = None,
    resolution: int = 1536,
    decimation: int = 100_000,
    tex_size: int = 2048,
    img_size: int = 1024,
    ai_upscale: bool = True,
    seed: int | None = None,
    workers: int = 1,
    skip_existing: bool = True,
) -> list[Path]:
    """Batch-upscale all meshes in a directory."""
    files = sorted(f for f in src_dir.iterdir() if f.suffix.lower() in MESH_EXTS)
    if not files:
        print(f"No meshes found in {src_dir}")
        return []

    out_dir.mkdir(parents=True, exist_ok=True)
    results = []

    def _worker(f):
        out_path = out_dir / f"{f.stem}_up.glb"
        if skip_existing and out_path.exists():
            print(f"  SKIP: {out_path.name} exists")
            return None
        return upscale_3d_asset(
            f, out_dir, ref_image=ref_image,
            resolution=resolution, decimation=decimation,
            tex_size=tex_size, img_size=img_size,
            ai_upscale=ai_upscale, seed=seed,
        )

    print(f"Upscaling {len(files)} meshes (workers={workers})...")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_worker, f): f for f in files}
        for i, future in enumerate(as_completed(futures), 1):
            f = futures[future]
            try:
                out = future.result()
                if out:
                    results.append(out)
                    print(f"  [{i}/{len(files)}] {f.name} -> {out.name}")
                else:
                    print(f"  [{i}/{len(files)}] {f.name} skipped")
            except Exception as e:
                print(f"  [{i}/{len(files)}] {f.name} ERROR: {e}")

    print(f"Done: {len(results)} upscaled, {len(files) - len(results)} skipped/failed")
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Mesh-to-mesh 3D upscaling via Trellis 2",
    )
    parser.add_argument("input", help="Mesh file or directory")
    parser.add_argument("-o", "--output", help="Output directory (default: assets/meshes/)")
    parser.add_argument("--ref-image", help="Reference image (skip render + AI upscale)")
    parser.add_argument("-r", "--resolution", type=int, default=1536,
                        choices=[512, 1024, 1536])
    parser.add_argument("--verts", type=int, default=100_000,
                        help="Target vertex count (default 100k)")
    parser.add_argument("--tex-size", type=int, default=2048,
                        choices=[1024, 2048, 4096])
    parser.add_argument("--img-size", type=int, default=1024,
                        help="Render resolution (default 1024)")
    parser.add_argument("--no-ai-upscale", action="store_true",
                        help="Skip Nano Banana Pro AI upscale of render")
    parser.add_argument("--seed", type=int)
    parser.add_argument("-j", "--workers", type=int, default=1)

    args = parser.parse_args()
    out_dir = Path(args.output) if args.output else MESHES_DIR
    ref_img = Path(args.ref_image) if args.ref_image else None

    target = Path(args.input)
    ai_up = not args.no_ai_upscale

    if target.is_dir():
        upscale_3d_assets(
            target, out_dir, ref_image=ref_img,
            resolution=args.resolution, decimation=args.verts,
            tex_size=args.tex_size, img_size=args.img_size,
            ai_upscale=ai_up, seed=args.seed, workers=args.workers,
        )
    elif target.is_file():
        out = upscale_3d_asset(
            target, out_dir, ref_image=ref_img,
            resolution=args.resolution, decimation=args.verts,
            tex_size=args.tex_size, img_size=args.img_size,
            ai_upscale=ai_up, seed=args.seed,
        )
        print(f"Saved: {out}")
    else:
        print(f"Not found: {target}")
        sys.exit(1)


if __name__ == "__main__":
    main()
