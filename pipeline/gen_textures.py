"""Generate improved tree/bush textures via fal.ai Nano Banana Pro.

Uses 2x2 tiling + center-crop + cross-blend to ensure seamless output.
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from math import gcd
from pathlib import Path

import fal_client
import numpy as np
import requests
from PIL import Image, ImageFilter

from pipeline.config import ensure_dirs
from pipeline.gen_terrain_v2 import make_seamless, tile_2x2

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "viewer" / "models"
ORIGINALS_DIR = MODELS_DIR / "originals"
OUT_DIR = MODELS_DIR / "creative_test"

WMO_DIR = ROOT / "viewer" / "wmo"
WMO_ORIGINALS = WMO_DIR / "originals"
WMO_OUT = WMO_DIR / "creative_test"

NANO_PRO = "fal-ai/nano-banana-pro/edit"

BARK_FDIDS = {
    464350: {"desc": "warm oak bark, rich brown", "w": 2048, "h": 2048},
    131942: {"desc": "rough oak bark, grey-brown with moss patches", "w": 1024, "h": 1024},
    189570: {"desc": "dark twisted bark, blackened oak", "w": 512, "h": 1024},
    189520: {"desc": "gnarled dark bark, vertical grain", "w": 256, "h": 1024},
    189572: {"desc": "dark brown bark with deep crevices", "w": 512, "h": 1024},
    249605: {"desc": "pale grey bark, birch-like with dark streaks", "w": 256, "h": 1024},
    189543: {"desc": "dark knotted bark, spooky forest", "w": 512, "h": 1024},
    189542: {"desc": "cracked dark bark, aged wood grain", "w": 512, "h": 1024},
}

LEAF_FDIDS = {
    464351: {"desc": "oak leaves, warm green, golden highlights", "w": 2048, "h": 2048},
    198585: {"desc": "scattered oak leaves, varied green tones", "w": 1024, "h": 1024},
    189563: {"desc": "dark forest leaves, deep green, moody", "w": 1024, "h": 1024},
    189554: {"desc": "dense dark canopy leaves, blue-green", "w": 1024, "h": 1024},
    189519: {"desc": "dark forest foliage, shadowy green", "w": 1024, "h": 1024},
    189573: {"desc": "autumn-tinged leaves, brown-green", "w": 1024, "h": 1024},
    189518: {"desc": "sparse dark leaves, grey-green", "w": 1024, "h": 1024},
    242694: {"desc": "dark twisted leaves, muted green", "w": 512, "h": 1024},
    189403: {"desc": "small dark leaf cluster", "w": 256, "h": 128},
    132027: {"desc": "dense bush foliage, forest green", "w": 1024, "h": 1024},
    132031: {"desc": "spooky bush, dark leaves with thorns", "w": 1024, "h": 512},
    189401: {"desc": "dark bush leaves, muted forest", "w": 512, "h": 512},
    189404: {"desc": "spooky bush thorns, dark purple-green", "w": 512, "h": 512},
    189937: {"desc": "bright bush foliage, sunlit green", "w": 512, "h": 512},
    202026: {"desc": "wild bush, yellow-green mixed", "w": 1024, "h": 512},
    321364: {"desc": "burnt bush, charred brown-black foliage", "w": 2048, "h": 2048},
}

PROP_FDIDS = {
    124303: "gryphon roost structure",
    124306: "gryphon roost wood plank",
    130279: "wooden fence and post planks",
    145513: "torch flame and glow",
    189080: "gypsy wagon painted wood",
    189082: "wagon wheel and axle",
    189421: "gate iron and wood",
    189422: "gate stone pillar",
    189433: "mushroom cap and stem",
    189460: "straw bale and thatch",
    189479: "wooden fence rail and post",
    189487: "gate post stone column",
    189514: "ruins brick wall",
    189720: "cliff rock surface",
    189769: "small rock boulder",
    189771: "mossy rock surface",
    189773: "seaweed and kelp strands",
    189799: "stone fence block",
    189800: "stone fence wall surface",
    189814: "ceramic jar and pot",
    189822: "lamppost metal and glass",
    190367: "lilypad leaf",
    190368: "lilypad flower",
    190369: "lilypad small",
    190386: "swamp plant fronds",
    190534: "barrel wood staves and iron bands",
    190610: "torch wooden handle",
    190722: "bird feathers and beak",
    191275: "swamp plant tall reed",
    197427: "wagon canvas cover",
    198183: "wooden crate and target dummy planks",
    198260: "gryphon roost roof shingles",
    198287: "wagon decorative panel",
    198298: "torch iron bracket",
    198305: "lamppost ornamental detail",
    199564: "barrel lid and base",
    199633: "flagpole wood and rope",
    199814: "torch fire particle",
    203474: "wetland grass blades",
}

ASPECT_MAP = {
    (1, 1): "1:1", (4, 3): "4:3", (3, 4): "3:4",
    (16, 9): "16:9", (9, 16): "9:16", (3, 2): "3:2", (2, 3): "2:3",
    (5, 4): "5:4", (4, 5): "4:5", (21, 9): "21:9",
    (1, 2): "9:16", (2, 1): "16:9",
    (1, 4): "9:16", (4, 1): "16:9",
}


def guess_aspect(w, h):
    g = gcd(w, h)
    ratio = (w // g, h // g)
    return ASPECT_MAP.get(ratio, "auto")


def nano_pro_edit(prompt, ref_img_path, resolution="2K", aspect="auto"):
    img_url = fal_client.upload_file(str(ref_img_path))
    result = fal_client.subscribe(
        NANO_PRO,
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


def load_orig(fdid):
    p = ORIGINALS_DIR / f"tex_{fdid}.webp"
    if not p.exists():
        p = MODELS_DIR / f"tex_{fdid}.webp"
    return Image.open(p) if p.exists() else None


def seamless_enhance(orig_rgb, prompt, aspect, fdid, label, tmp_prefix):
    """Tile 2x2, send to AI, crop center, cross-blend edges."""
    tiled = tile_2x2(orig_rgb)
    tmp = OUT_DIR / f"_tmp_{tmp_prefix}_{fdid}.png"
    tiled.save(tmp)
    print(f"    tiled 2x2 -> {tiled.size[0]}x{tiled.size[1]}")

    img = nano_pro_edit(prompt, tmp, resolution="4K", aspect=aspect)
    tmp.unlink(missing_ok=True)
    img = img.convert("RGB")

    rw, rh = img.size
    cx, cy = rw // 4, rh // 4
    cw, ch = rw // 2, rh // 2
    center = img.crop((cx, cy, cx + cw, cy + ch))
    result = make_seamless(center, blend_pct=0.35)
    print(f"    cropped center {center.size[0]}x{center.size[1]} [seamless]")
    return result


def smooth_patches(img, radius=12):
    """Blend with a blurred copy to reduce patch-to-patch brightness jumps."""
    arr = np.array(img, dtype=np.float32)
    blurred = np.array(img.filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32)
    out = arr * 0.85 + blurred * 0.15
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def gen_bark(fdid, info, skip_existing=True):
    out = OUT_DIR / f"tex_{fdid}_nanobanana.webp"
    if skip_existing and out.exists():
        print(f"  SKIP bark {fdid}: already exists")
        return out

    orig = load_orig(fdid)
    if not orig:
        print(f"  SKIP bark {fdid}: original not found")
        return None

    prompt = (
        f"Enhance this {info['desc']} tree bark game texture to higher quality. "
        "Add richer wood grain detail, deeper crevices, subtle moss and knots. "
        "Keep uniform brightness and consistent style across the ENTIRE texture. "
        "No patchy regions or uneven lighting. "
        "Stylized World of Warcraft aesthetic, painterly, not photorealistic."
    )

    tw, th = info["w"], info["h"]
    tmp = OUT_DIR / f"_tmp_bark_{fdid}.png"
    orig.convert("RGB").save(tmp)
    aspect = guess_aspect(tw, th)

    print(f"  Generating bark {fdid} ({tw}x{th} aspect={aspect})...")
    img = nano_pro_edit(prompt, tmp, resolution="4K", aspect=aspect)
    tmp.unlink(missing_ok=True)
    img = img.convert("RGB")
    img = smooth_patches(img)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(f"  Saved bark {fdid}: {out.name} ({img.size[0]}x{img.size[1]})")
    return out


def sharpen_alpha(alpha_img, threshold=80):
    """Make alpha crisper: push values towards 0 or 255."""
    arr = np.array(alpha_img, dtype=np.float32)
    arr = np.where(arr < threshold, arr * 0.3, np.minimum(arr * 1.3, 255))
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def bleed_edges(rgb_img, alpha_img, iterations=8):
    """Spread opaque pixel colors into transparent border areas.

    Prevents white/bright fringing at alpha-tested edges by ensuring
    the RGB content under semi-transparent pixels matches nearby leaves.
    """
    rgb = np.array(rgb_img, dtype=np.float32)
    a = np.array(alpha_img, dtype=np.float32)
    opaque = a > 60

    for _ in range(iterations):
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            shifted_opaque = np.roll(np.roll(opaque, dy, axis=0), dx, axis=1)
            shifted_rgb = np.roll(np.roll(rgb, dy, axis=0), dx, axis=1)
            fill = ~opaque & shifted_opaque
            rgb[fill] = shifted_rgb[fill]
            opaque |= fill

    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))


def gen_leaf(fdid, info, skip_existing=True):
    out = OUT_DIR / f"tex_{fdid}_nanobanana.webp"
    if skip_existing and out.exists():
        print(f"  SKIP leaf {fdid}: already exists")
        return out

    orig_path = ORIGINALS_DIR / f"tex_{fdid}.webp"
    if not orig_path.exists():
        orig_path = MODELS_DIR / f"tex_{fdid}.webp"
    if not orig_path.exists():
        print(f"  SKIP leaf {fdid}: original not found")
        return None

    orig = Image.open(orig_path).convert("RGBA")
    alpha = orig.split()[3]

    prompt = (
        f"Enhance this {info['desc']} tree foliage game texture to higher quality. "
        "Add richer individual leaf detail and color variation. "
        "Keep uniform style across the entire texture, preserve transparent areas as-is. "
        "Do NOT fill in empty/dark regions. "
        "Stylized World of Warcraft aesthetic, painterly, not photorealistic."
    )

    tw, th = info["w"], info["h"]
    tmp = OUT_DIR / f"_tmp_leaf_{fdid}.png"
    orig.convert("RGB").save(tmp)
    aspect = guess_aspect(tw, th)

    print(f"  Generating leaf {fdid} ({tw}x{th}): {info['desc']}...")
    img = nano_pro_edit(prompt, tmp, resolution="4K", aspect=aspect)
    tmp.unlink(missing_ok=True)
    img = img.convert("RGB")

    up_alpha = sharpen_alpha(alpha.resize(img.size, Image.LANCZOS))
    img = bleed_edges(img, up_alpha)
    result = Image.merge("RGBA", (*img.split(), up_alpha))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    result.save(out)
    print(f"  Saved leaf {fdid}: {out.name} ({result.size[0]}x{result.size[1]})")
    return out


def gen_prop(fdid, desc, skip_existing=True):
    out = OUT_DIR / f"tex_{fdid}_nanobanana.webp"
    if skip_existing and out.exists():
        print(f"  SKIP prop {fdid}: already exists")
        return out

    orig = load_orig(fdid)
    if not orig:
        print(f"  SKIP prop {fdid}: original not found")
        return None

    has_alpha = orig.mode == "RGBA"
    alpha = orig.split()[3] if has_alpha else None
    w, h = orig.size

    prompt = (
        f"Dramatically enhance this {desc} game texture. "
        "Keep the same layout but add much richer surface detail: "
        "wood grain, metal rivets, stone cracks, fabric weave as appropriate. "
        "Make it look like a high-budget AAA fantasy RPG texture with painterly brushstrokes. "
        "4x the surface detail. Stylized World of Warcraft aesthetic, not photorealistic."
    )

    aspect = guess_aspect(w, h)
    print(f"  Generating prop {fdid} ({w}x{h}): {desc}...")

    img = seamless_enhance(orig.convert("RGB"), prompt, aspect, fdid, "prop", "prop")

    if has_alpha and alpha is not None:
        up_alpha = sharpen_alpha(alpha.resize(img.size, Image.LANCZOS))
        img = bleed_edges(img, up_alpha)
        result = Image.merge("RGBA", (*img.split(), up_alpha))
    else:
        result = img

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    result.save(out)
    print(f"  Saved prop {fdid}: {out.name} ({result.size[0]}x{result.size[1]})")
    return out


WMO_FDIDS = [
    126610, 126611, 126998, 126999, 127000, 127001, 127002, 127003, 127004, 127005, 127006,
    127093, 127095, 127100, 127187, 127212, 127216, 127221, 127280, 127299, 127301, 127322,
    127324, 127325, 127441, 127449, 127467, 127476, 127495, 127864, 127868, 127869, 127874,
    127877, 127915, 127917, 127977, 127979, 127980, 128157, 128159, 128160, 128331, 128470,
    128471, 128472, 128473, 128474, 128475, 128477, 128478, 128480, 128481, 128483, 128484,
    128566, 128567, 128568, 128569, 128570, 128571, 128572, 128597, 128599, 128600, 128694,
    128698, 128739, 128759, 128760, 128762, 128884, 129007, 129255, 129261, 129266, 129267,
    129268, 129317, 129318, 129395, 129400, 129402, 129403, 129891, 129892, 129893, 129895,
    129896, 129905, 129906, 129911, 129912, 130052, 130053, 130054, 130064, 130065, 130066,
    130081, 130116, 130117, 130118, 130119, 130120, 130258, 130279, 130281, 130302, 130307,
    130308, 130309, 130310, 130311, 130312, 130313, 130315, 130316, 189083, 190085, 190086,
    190092, 190094, 315088, 315089, 315090, 315091, 315092, 315093, 315094, 315095, 315096,
    353675,
]


def gen_wmo(fdid, skip_existing=True):
    out = WMO_OUT / f"tex_{fdid}_nanobanana.webp"
    if skip_existing and out.exists():
        print(f"  SKIP wmo {fdid}: already exists")
        return out

    orig_path = WMO_ORIGINALS / f"tex_{fdid}.webp"
    if not orig_path.exists():
        orig_path = WMO_DIR / f"tex_{fdid}.webp"
    if not orig_path.exists():
        print(f"  SKIP wmo {fdid}: original not found")
        return None

    orig = Image.open(orig_path)
    has_alpha = orig.mode == "RGBA"
    alpha = orig.split()[3] if has_alpha else None
    w, h = orig.size

    prompt = (
        "Dramatically enhance this building texture from a fantasy RPG game. "
        "Keep the same layout but add much richer surface detail: "
        "stone mortar lines, wood grain, roof shingle texture, brick weathering. "
        "Make it look like a high-budget AAA fantasy game texture. "
        "4x the surface detail. Stylized World of Warcraft aesthetic, not photorealistic."
    )

    tmp = WMO_OUT / f"_tmp_wmo_{fdid}.png"
    orig.convert("RGB").save(tmp)
    aspect = guess_aspect(w, h)

    print(f"  Generating wmo {fdid} ({w}x{h})...")
    img = nano_pro_edit(prompt, tmp, resolution="4K", aspect=aspect)
    tmp.unlink(missing_ok=True)
    img = img.convert("RGB")

    if has_alpha and alpha is not None:
        up_alpha = alpha.resize(img.size, Image.LANCZOS)
        result = Image.merge("RGBA", (*img.split(), up_alpha))
    else:
        result = img

    WMO_OUT.mkdir(parents=True, exist_ok=True)
    result.save(out)
    print(f"  Saved wmo {fdid}: {out.name} ({result.size[0]}x{result.size[1]})")
    return out


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=["bark", "leaf", "prop", "wmo", "all"], default="all")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()

    ensure_dirs()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    WMO_OUT.mkdir(parents=True, exist_ok=True)

    jobs = []

    if args.only in ("bark", "all"):
        for fdid, info in BARK_FDIDS.items():
            jobs.append(("bark", fdid, lambda f=fdid, i=info: gen_bark(f, i, args.skip_existing)))

    if args.only in ("leaf", "all"):
        for fdid, info in LEAF_FDIDS.items():
            jobs.append(("leaf", fdid, lambda f=fdid, i=info: gen_leaf(f, i, args.skip_existing)))

    if args.only in ("prop", "all"):
        for fdid, desc in PROP_FDIDS.items():
            jobs.append(("prop", fdid, lambda f=fdid, d=desc: gen_prop(f, d, args.skip_existing)))

    if args.only in ("wmo", "all"):
        for fdid in WMO_FDIDS:
            jobs.append(("wmo", fdid, lambda f=fdid: gen_wmo(f, args.skip_existing)))

    print(f"=== Generating {len(jobs)} textures with {args.workers} workers ===")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(fn): (kind, fdid) for kind, fdid, fn in jobs}
        for f in as_completed(futs):
            kind, fdid = futs[f]
            try:
                f.result()
            except Exception as e:
                print(f"  ERROR {kind} {fdid}: {e}")

    print("\nDone!")


if __name__ == "__main__":
    main()
