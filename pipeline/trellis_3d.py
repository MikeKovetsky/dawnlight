"""3D mesh generation from reference images via fal.ai TRELLIS."""

import argparse
import sys
from pathlib import Path

import fal_client
import requests

from pipeline.config import IMG_EXTS, INPUT_DIR, MESHES_DIR, TRELLIS, ensure_dirs


def generate(
    path: Path,
    texture_size: int = 2048,
    mesh_detail: int = 500_000,
    out_dir: Path = MESHES_DIR,
) -> Path:
    ensure_dirs()
    out_dir.mkdir(parents=True, exist_ok=True)

    url = fal_client.upload_file(str(path))

    result = fal_client.subscribe(
        TRELLIS,
        arguments={
            "image_url": url,
            "texture_size": texture_size,
            "decimation_target": mesh_detail,
            "remesh": True,
        },
        with_logs=True,
    )

    glb_url = result["model_glb"]["url"]
    resp = requests.get(glb_url, timeout=180)
    resp.raise_for_status()

    out_path = out_dir / f"{path.stem}.glb"
    out_path.write_bytes(resp.content)
    return out_path


def batch(
    input_dir: Path,
    texture_size: int = 2048,
    mesh_detail: int = 500_000,
    out_dir: Path = MESHES_DIR,
):
    files = sorted(f for f in input_dir.iterdir() if f.suffix.lower() in IMG_EXTS)

    if not files:
        print(f"No images found in {input_dir}")
        return

    print(f"Generating 3D meshes for {len(files)} images...")
    for i, f in enumerate(files, 1):
        print(f"  [{i}/{len(files)}] {f.name}")
        try:
            out = generate(f, texture_size=texture_size, mesh_detail=mesh_detail, out_dir=out_dir)
            print(f"    -> {out.name}")
        except Exception as e:
            print(f"    ERROR: {e}")


def main():
    parser = argparse.ArgumentParser(description="3D mesh generation via fal.ai TRELLIS")
    parser.add_argument("input", nargs="?", help="Reference image or directory (default: assets/input/)")
    parser.add_argument("--texture-size", type=int, default=2048, choices=[1024, 2048, 4096])
    parser.add_argument("--mesh-detail", type=int, default=500_000, help="Target vertex count")
    parser.add_argument("-o", "--output", help="Output directory (default: assets/meshes/)")

    args = parser.parse_args()
    out_dir = Path(args.output) if args.output else MESHES_DIR

    target = Path(args.input) if args.input else INPUT_DIR
    if target.is_dir():
        batch(target, texture_size=args.texture_size, mesh_detail=args.mesh_detail, out_dir=out_dir)
    elif target.is_file():
        out = generate(target, texture_size=args.texture_size, mesh_detail=args.mesh_detail, out_dir=out_dir)
        print(f"Saved: {out}")
    else:
        print(f"Not found: {target}")
        sys.exit(1)


if __name__ == "__main__":
    main()
