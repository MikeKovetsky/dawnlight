---
name: Refactor reusable core
overview: Extract game-agnostic texture processing into `pipeline/core.py` with a single public function `upscale_texture()` that handles AI upscaling, seamless tiling, alpha, and optional PBR map generation. Add a generic CLI for any game's textures.
todos:
  - id: create-core
    content: Create pipeline/core.py with upscale_texture() as sole public API (normals/heights as flags), all internals private
    status: completed
  - id: update-gen-textures
    content: "Refactor gen_textures.py: replace inline upscale logic with core.upscale_texture() calls"
    status: completed
  - id: update-gen-terrain
    content: "Refactor gen_terrain_v2.py: replace inline upscale logic with core.upscale_texture() calls"
    status: completed
  - id: update-upscale-creative
    content: "Refactor upscale_creative.py: replace inline upscale logic with core.upscale_texture() calls"
    status: completed
  - id: update-upscale
    content: "Refactor upscale.py: replace inline tile/crop logic with core.upscale_texture()"
    status: completed
  - id: update-gen-normals
    content: "Refactor gen_normals.py: delegate to core.upscale_texture() with normals/heights flags, add --input/--output CLI args"
    status: completed
  - id: create-upscale-dir
    content: Create pipeline/upscale_dir.py -- generic batch upscaler CLI using core.upscale_texture()
    status: completed
isProject: false
---

# Refactor Pipeline into Reusable Core

## Design: Two Public Functions

`pipeline/core.py` exposes exactly **two functions** -- singular and plural:

```python
def upscale_texture(src, out, prompt, resolution="4K", seamless=True,
                    normals=False, heights=False) -> Path:
    """AI-upscale a single texture via fal.ai Nano Banana Pro.
    
    Handles tiling, seamless blending, alpha preservation, aspect
    detection, and optional PBR map generation internally.
    
    If normals=True, writes {stem}_n.png next to out.
    If heights=True, writes {stem}_h.png next to out.
    """

def upscale_textures(src_dir, out_dir, prompt, resolution="4K", seamless=True,
                     normals=False, heights=False, workers=6,
                     skip_existing=True) -> list[Path]:
    """Batch-upscale all textures in a directory.
    
    Walks src_dir for image files, calls upscale_texture() per file
    via ThreadPoolExecutor. Returns list of output paths.
    """
```

Everything else stays **private** inside `core.py` with underscore prefixes.

## What `upscale_texture()` does internally

```
src image
  |
  ├─ detect alpha? split RGB + A
  ├─ _guess_aspect(w, h)
  ├─ if seamless: _tile_2x2 -> 2x2 grid
  ├─ _nano_pro_edit(prompt, tmp, resolution, aspect) -> AI result
  ├─ if seamless: crop center tile -> _make_seamless(blend)
  ├─ _smooth_patches() for brightness uniformity
  ├─ if had alpha: resize alpha, merge back
  ├─ save to out path
  ├─ if normals: _gen_normal_map(out) -> {stem}_n.png
  └─ if heights: _gen_heightmap(out) -> {stem}_h.png
```

One call does everything. No knowledge of fal.ai, tiling tricks, or PBR math needed by callers.

## Step 1: Create `pipeline/core.py` (~200 lines)

Public API: `upscale_texture()` + `upscale_textures()`.

Private internals (underscore-prefixed):

- `_tile_2x2()`, `_make_seamless()`, `_smooth_patches()`
- `_nano_pro_edit()`, `_guess_aspect()`, `_ASPECT_MAP`
- `_gen_normal_map()`, `_gen_heightmap()`

## Step 2: Update WoW modules to use `upscale_texture()`

Each WoW module replaces its own upscale logic with a single `core.upscale_texture()` call:

- **[pipeline/gen_textures.py](pipeline/gen_textures.py)**: `gen_bark()`, `gen_leaf()`, `gen_prop()`, `gen_wmo()` each become thin wrappers that build a WoW-specific prompt and call `core.upscale_texture()`. Remove `nano_pro_edit`, `seamless_enhance`, `guess_aspect`, `ASPECT_MAP`, `smooth_patches` (~60 lines deleted). Remove `from pipeline.gen_terrain_v2 import make_seamless, tile_2x2` import.
- **[pipeline/gen_terrain_v2.py](pipeline/gen_terrain_v2.py)**: `enhance_terrain()` becomes: build prompt, call `core.upscale_texture(src, out, prompt, seamless=True)`. Remove `tile_2x2`, `make_seamless`, `nano_pro_enhance` (~60 lines deleted).
- **[pipeline/upscale_creative.py](pipeline/upscale_creative.py)**: `upscale_texture()` and `upscale_terrain()` call `core.upscale_texture()`. Remove `nano_banana_upscale`, `guess_aspect`, `ASPECT_MAP` (~30 lines deleted).
- **[pipeline/upscale.py](pipeline/upscale.py)**: `upscale()` calls `core.upscale_texture()` with ESRGAN fallback path. Remove `_tile_2x2`, `_crop_center_tile` (~20 lines deleted).
- **[pipeline/gen_normals.py](pipeline/gen_normals.py)**: `main()` calls `core.upscale_texture()` with `normals=True, heights=True` (no AI upscale needed -- just PBR generation on already-upscaled textures). Or kept as a thin CLI that generates normals/heights from existing diffuse textures. Add `--input`/`--output` CLI args (WoW paths remain as defaults).

## Step 3: Add generic CLI `pipeline/upscale_dir.py` (~60 lines)

```bash
# Upscale any directory of game textures
python -m pipeline.upscale_dir ./textures/ -o ./upscaled/ \
  --prompt "sci-fi arena shooter" --workers 6

# Single file
python -m pipeline.upscale_dir wall.jpg -o ./out/

# With PBR generation
python -m pipeline.upscale_dir ./textures/ -o ./upscaled/ \
  --prompt "gothic stone" --normals --heights --workers 6
```

Internally: just argparse + a single `core.upscale_textures()` call. All parallelism, skip-existing, and PBR generation handled by core.

## Files summary

- **New**: `pipeline/core.py` (~220 lines) -- 2 public functions (`upscale_texture` + `upscale_textures`), all internals private
- **New**: `pipeline/upscale_dir.py` (~60 lines) -- generic CLI
- **Modified**: 5 WoW modules shrink by removing duplicated logic
- **Not touched**: `adt.py`, `obj0.py`, `m2.py`, `wmo.py`, `mpq_export.py`, `config.py`, viewer, extract

