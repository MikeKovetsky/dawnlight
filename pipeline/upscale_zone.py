"""Upscale all terrain textures for a WoW zone.

Usage:
    python -m pipeline.upscale_zone nagrand
    python -m pipeline.upscale_zone elwynn --resolution 2K
    python -m pipeline.upscale_zone nagrand --force --workers 4

Reads zone config from pipeline.zones, upscales textures with the right
prompts, and writes output to the directories the viewer expects:
    v2/       -- upscaled diffuse textures
    normals/  -- normal maps
    heights/  -- heightmaps
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from pipeline.core import upscale_texture
from pipeline.zones import (
    ZONES,
    get_zone,
    prompt_for,
    zone_heights_dir,
    zone_normals_dir,
    zone_out_dir,
    zone_src_dir,
)


def _upscale_one(src, out, prompt, resolution, normals_dir, heights_dir):
    return upscale_texture(
        src, out, prompt,
        resolution=resolution, seamless=True,
        normals=True, heights=True,
        normals_dir=normals_dir, heights_dir=heights_dir,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Upscale terrain textures for a WoW zone",
        epilog=f"Available zones: {', '.join(sorted(ZONES))}",
    )
    parser.add_argument("zone", help="Zone name (e.g. nagrand, elwynn)")
    parser.add_argument("-r", "--resolution", default="4K",
                        choices=["1K", "2K", "4K"])
    parser.add_argument("-j", "--workers", type=int, default=4)
    parser.add_argument("--force", action="store_true",
                        help="Re-process existing outputs")
    parser.add_argument("--no-normals", action="store_true",
                        help="Skip normal map generation")
    parser.add_argument("--no-heights", action="store_true",
                        help="Skip heightmap generation")
    args = parser.parse_args()

    zone = get_zone(args.zone)
    src_dir = zone_src_dir(zone)
    out_dir = zone_out_dir(zone)
    n_dir = None if args.no_normals else zone_normals_dir(zone)
    h_dir = None if args.no_heights else zone_heights_dir(zone)
    ext = zone["tex_ext"]

    out_dir.mkdir(parents=True, exist_ok=True)
    if n_dir:
        n_dir.mkdir(parents=True, exist_ok=True)
    if h_dir:
        h_dir.mkdir(parents=True, exist_ok=True)

    textures = [
        (name, src_dir / f"{name}{ext}", out_dir / f"{name}{ext}")
        for name in zone["tex_names"]
    ]

    missing = [(n, s) for n, s, _ in textures if not s.exists()]
    if missing:
        for name, path in missing:
            print(f"  WARNING: {path} not found, skipping")
        textures = [(n, s, o) for n, s, o in textures if s.exists()]

    if not textures:
        print(f"No textures found in {src_dir}")
        return

    skip_existing = not args.force
    work = []
    for name, src, out in textures:
        if skip_existing and out.exists():
            print(f"  SKIP: {name} (already exists)")
            continue
        work.append((name, src, out))

    if not work:
        print("All textures already upscaled. Use --force to re-process.")
        return

    print(f"Upscaling {zone['label']}: {len(work)} textures @ {args.resolution}")
    print(f"  Source:  {src_dir}")
    print(f"  Output:  {out_dir}")
    if n_dir:
        print(f"  Normals: {n_dir}")
    if h_dir:
        print(f"  Heights: {h_dir}")
    print()

    ok, fail = 0, 0

    def _do(name, src, out):
        prompt = prompt_for(zone, name)
        return _upscale_one(
            src, out, prompt, args.resolution,
            normals_dir=n_dir if not args.no_normals else None,
            heights_dir=h_dir if not args.no_heights else None,
        )

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(_do, n, s, o): n for n, s, o in work}
        for i, fut in enumerate(as_completed(futs), 1):
            name = futs[fut]
            try:
                fut.result()
                print(f"  [{i}/{len(work)}] {name} OK")
                ok += 1
            except Exception as e:
                print(f"  [{i}/{len(work)}] {name} FAILED: {e}")
                fail += 1

    print(f"\nDone: {ok} upscaled, {fail} failed")

    print(f"\nTo enable in the viewer, set hasNormals: true for "
          f"'{args.zone}' in viewer/src/app.js")


if __name__ == "__main__":
    main()
