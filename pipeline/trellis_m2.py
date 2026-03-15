"""Generate high-poly 3D models from WoW M2 meshes via Trellis 2 on fal.ai.

Two modes:
  generate  - Image-to-3D: feed a reference image, get a full high-poly 3D GLB
  retexture - Keep existing geometry, generate new PBR textures
"""

import argparse
import json
from pathlib import Path

import fal_client
import requests

from pipeline.config import TRELLIS, ensure_dirs

MODELS_DIR = Path(__file__).resolve().parent.parent / "viewer" / "models"
GLB_DIR = MODELS_DIR / "glb"

TREE_MODELS = [
    "elwynntreecanopy01", "elwynntreecanopy02",
    "elwynntreecanopy03", "elwynntreecanopy04",
    "elwynntreemid01", "canopylesstree01",
    "duskwoodtreecanopy01", "duskwoodtreecanopy02",
    "duskwoodtree06", "duskwoodtree07",
]


def m2_to_obj(name: str) -> Path:
    """Convert M2 model JSON to OBJ for retexture input."""
    json_path = MODELS_DIR / f"{name}.json"
    if not json_path.exists():
        raise FileNotFoundError(f"Model JSON not found: {json_path}")

    with open(json_path) as f:
        data = json.load(f)

    GLB_DIR.mkdir(parents=True, exist_ok=True)
    obj_path = GLB_DIR / f"{name}.obj"

    pos = data["positions"]
    nrm = data["normals"]
    uvs = data["uvs"]
    indices = data["indices"]
    n_verts = len(pos) // 3

    with open(obj_path, "w") as f:
        f.write(f"# {name} - WoW M2 export\n")
        for i in range(n_verts):
            f.write(f"v {pos[i*3]:.4f} {pos[i*3+1]:.4f} {pos[i*3+2]:.4f}\n")
        for i in range(n_verts):
            f.write(f"vn {nrm[i*3]:.4f} {nrm[i*3+1]:.4f} {nrm[i*3+2]:.4f}\n")
        for i in range(n_verts):
            f.write(f"vt {uvs[i*2]:.5f} {uvs[i*2+1]:.5f}\n")
        for i in range(0, len(indices), 3):
            a, b, c = indices[i] + 1, indices[i+1] + 1, indices[i+2] + 1
            f.write(f"f {a}/{a}/{a} {b}/{b}/{b} {c}/{c}/{c}\n")

    print(f"  OBJ: {obj_path.name} ({n_verts} verts, {len(indices)//3} tris)")
    return obj_path


def upload(path_or_url: str) -> str:
    if path_or_url.startswith("http"):
        return path_or_url
    return fal_client.upload_file(path_or_url)


def generate(image: str, name: str, resolution: int = 1024,
             decimation: int = 20000, tex_size: int = 2048,
             seed: int | None = None) -> Path:
    """Image-to-3D via Trellis 2. Returns path to downloaded GLB."""
    GLB_DIR.mkdir(parents=True, exist_ok=True)
    image_url = upload(image)

    args = {
        "image_url": image_url,
        "resolution": resolution,
        "decimation_target": decimation,
        "texture_size": tex_size,
        "remesh": True,
        "ss_guidance_strength": 7.5,
        "shape_slat_guidance_strength": 7.5,
        "shape_slat_sampling_steps": 12,
        "tex_slat_sampling_steps": 12,
    }
    if seed is not None:
        args["seed"] = seed

    print(f"  Trellis 2 generate: res={resolution} verts={decimation} tex={tex_size}")
    result = fal_client.subscribe(TRELLIS, arguments=args, with_logs=True)

    out = GLB_DIR / f"{name}.glb"
    resp = requests.get(result["model_glb"]["url"], timeout=300)
    resp.raise_for_status()
    out.write_bytes(resp.content)
    print(f"  -> {out.name} ({len(resp.content)/1024/1024:.1f} MB)")
    return out


def generate_multi(images: list[str], name: str, resolution: int = 1024,
                   decimation: int = 20000, tex_size: int = 2048,
                   seed: int | None = None) -> Path:
    """Multi-image-to-3D via Trellis 2 (1-4 views of same object)."""
    GLB_DIR.mkdir(parents=True, exist_ok=True)
    image_urls = [upload(img) for img in images]

    args = {
        "image_urls": image_urls,
        "resolution": resolution,
        "decimation_target": decimation,
        "texture_size": tex_size,
        "remesh": True,
        "ss_guidance_strength": 7.5,
        "shape_slat_guidance_strength": 7.5,
        "shape_slat_sampling_steps": 12,
        "tex_slat_sampling_steps": 12,
    }
    if seed is not None:
        args["seed"] = seed

    print(f"  Trellis 2 multi-image: {len(images)} views, res={resolution}")
    result = fal_client.subscribe(
        f"{TRELLIS}/multi-image", arguments=args, with_logs=True,
    )

    out = GLB_DIR / f"{name}.glb"
    resp = requests.get(result["model_glb"]["url"], timeout=300)
    resp.raise_for_status()
    out.write_bytes(resp.content)
    print(f"  -> {out.name} ({len(resp.content)/1024/1024:.1f} MB)")
    return out


def retexture(name: str, image: str, tex_size: int = 2048,
              seed: int | None = None) -> Path:
    """Retexture existing mesh geometry with new PBR textures."""
    GLB_DIR.mkdir(parents=True, exist_ok=True)

    obj_path = GLB_DIR / f"{name}.obj"
    if not obj_path.exists():
        obj_path = m2_to_obj(name)

    mesh_url = fal_client.upload_file(str(obj_path))
    image_url = upload(image)

    args = {
        "image_url": image_url,
        "mesh_url": mesh_url,
        "texture_size": tex_size,
        "resolution": 1024,
        "tex_slat_sampling_steps": 12,
    }
    if seed is not None:
        args["seed"] = seed

    print(f"  Trellis 2 retexture: {name} tex={tex_size}")
    result = fal_client.subscribe(
        f"{TRELLIS}/retexture", arguments=args, with_logs=True,
    )

    out = GLB_DIR / f"{name}_retex.glb"
    resp = requests.get(result["model_glb"]["url"], timeout=300)
    resp.raise_for_status()
    out.write_bytes(resp.content)
    print(f"  -> {out.name} ({len(resp.content)/1024/1024:.1f} MB)")
    return out


def main():
    parser = argparse.ArgumentParser(
        description="Generate high-poly 3D models via Trellis 2",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    gen = sub.add_parser("generate", help="Image-to-3D generation")
    gen.add_argument("image", help="Image path or URL")
    gen.add_argument("--name", "-n", required=True, help="Output model name")
    gen.add_argument("--resolution", "-r", type=int, default=1024,
                     choices=[512, 1024, 1536])
    gen.add_argument("--verts", "-v", type=int, default=20000,
                     help="Target vertex count (default 20k for web)")
    gen.add_argument("--tex-size", "-t", type=int, default=2048,
                     choices=[1024, 2048, 4096])
    gen.add_argument("--seed", type=int)

    multi = sub.add_parser("multi", help="Multi-image-to-3D (1-4 views)")
    multi.add_argument("images", nargs="+", help="Image paths or URLs (1-4)")
    multi.add_argument("--name", "-n", required=True)
    multi.add_argument("--resolution", "-r", type=int, default=1024,
                       choices=[512, 1024, 1536])
    multi.add_argument("--verts", "-v", type=int, default=20000)
    multi.add_argument("--tex-size", "-t", type=int, default=2048,
                       choices=[1024, 2048, 4096])
    multi.add_argument("--seed", type=int)

    retex = sub.add_parser("retexture", help="Retexture existing M2 mesh")
    retex.add_argument("name", help="Model name (e.g. elwynntreecanopy01)")
    retex.add_argument("image", help="Reference image path or URL")
    retex.add_argument("--tex-size", "-t", type=int, default=2048,
                       choices=[1024, 2048, 4096])
    retex.add_argument("--seed", type=int)

    obj = sub.add_parser("export-obj", help="Export M2 JSON to OBJ")
    obj.add_argument("names", nargs="+", help="Model names")

    args = parser.parse_args()

    if args.cmd == "generate":
        generate(args.image, args.name, args.resolution,
                 args.verts, args.tex_size, args.seed)

    elif args.cmd == "multi":
        if len(args.images) > 4:
            parser.error("Trellis 2 supports max 4 images")
        generate_multi(args.images, args.name, args.resolution,
                       args.verts, args.tex_size, args.seed)

    elif args.cmd == "retexture":
        retexture(args.name, args.image, args.tex_size, args.seed)

    elif args.cmd == "export-obj":
        for name in args.names:
            print(f"Exporting {name}...")
            m2_to_obj(name)


if __name__ == "__main__":
    main()
