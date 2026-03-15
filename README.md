# Dawnlight

AI-upscale World of Warcraft's Elwynn Forest. Takes the classic 2004-era textures and low-poly models and runs them through modern AI to produce high-resolution PBR textures and detailed 3D meshes.

## What it does

1. **Downloads** real WoW terrain data, textures, and models from Blizzard's CDN via [wago.tools](https://wago.tools)
2. **Parses** ADT terrain files (heightmaps, texture splatmaps, water, object placements) and M2 model files
3. **Renders** the zone in a Three.js viewer with multi-texture splatting, water, and placed objects
4. **Upscales** textures via fal.ai Nano Banana Pro (Gemini image-to-image) at 4K resolution

## Current state

- **20 Elwynn terrain tiles** with multi-texture splatting (grass, dirt, rock, cobblestone)
- Water planes at correct heights across the full zone
- **62 M2 models** with multi-submesh rendering, alpha transparency, and creature skins
- **17 WMO buildings** (Goldshire Inn, blacksmith, stable, farms, bridges, abbey gates, barns, mage tower) with tiled textures
- **28 static NPCs** placed at Goldshire spawn locations (humans, horses, chickens, wolves, boars, deer, cats)
- **63 AI-upscaled textures** (24 tree/bush + 39 prop) via Nano Banana Pro at 4K, with originals preserved for comparison
- **4 AI-upscaled terrain textures** (grass, dirt, rock, cobblestone) via Nano Banana Pro
- **T key** toggles Original ↔ Upscaled textures live in the viewer
- **Model preview page** (`/preview.html`) with side-by-side Original vs Upscaled comparison for all 61 models
- Flyable Three.js viewer with orbit and FPS camera modes
- MPQ export pipeline for importing upscaled textures into a 3.3.5a WoW client

### Next-gen terrain (enabled in upscaled modes)

- **Normal maps** on all 4 terrain layers -- Sobel-generated from diffuse textures, blended per splatmap weight, perturbed via TBN matrix
- **Parallax heightmaps** -- per-pixel UV offset from view-angle with distance fade (80-280 units)
- **Shadow mapping** -- 4096x4096 PCF soft shadow map from the sun, cast by all M2/WMO objects onto terrain
- **Procedural vegetation scatter** -- bushes, rocks, and grass clumps auto-placed by splatmap zone (grid-jitter with bilinear height lookup)
- **GPU-instanced grass** -- up to 120k multi-segment blades with dual-frequency wind animation, per-instance color variation, and distance-based alpha LOD

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file:

```
FAL_KEY=your_fal_ai_key_here
```

## Quick Start

```bash
# Download Elwynn textures
python -m extract.download fetch-listfile
python -m extract.download elwynn

# Download terrain tiles
python -m extract.download adt --tile 32,49

# Parse terrain (heightmap + splatmap)
python -m pipeline.adt assets/adt/azeroth_32_49.adt --base-z 42.86

# Parse object placements
python -m pipeline.obj0 assets/adt/azeroth_32_49_obj0.adt

# Download and parse M2 models
python -m pipeline.m2 189932   # Elwynn tree

# Upscale all M2 textures (trees, bushes, props) via Nano Banana Pro at 4K
python -m pipeline.gen_textures --only all --workers 6

# Upscale just props (fences, barrels, rocks, etc.)
python -m pipeline.gen_textures --only prop --workers 6

# Re-run without regenerating existing textures
python -m pipeline.gen_textures --only all --workers 6 --skip-existing

# Upscale terrain textures (Nano Banana 2)
python -m pipeline.upscale_creative --terrain -r 2K

# Generate normal maps + heightmaps for terrain
python -m pipeline.gen_normals --heights

# View results
cd viewer && python -m http.server 8081
# Open http://localhost:8081
# Open http://localhost:8081/preview.html?model=barrel01 for side-by-side comparison
```

## Pipeline

```
WoW CDN (wago.tools) ──► Download ──► BLP/ADT/M2 files
                                          │
                         ┌────────────────┼────────────────┐
                         ▼                ▼                ▼
                    ADT Parser       Texture Conv      M2 Parser
                   (heightmap,      (BLP → PNG)      (vertices,
                    splatmap,                         indices,
                    water)                            textures)
                         │                │                │
                         ▼                ▼                ▼
                    terrain JSON     assets/input/    model JSON
                         │                │                │
                         │         Nano Banana Pro     gen_normals.py
                         │        (fal.ai Gemini)    (Sobel normals
                         │              │             + heightmaps)
                         │              ▼                  │
                         │    models/creative_test/        │
                         │    textures/nanobanana/         │
                         │         (4K upscaled            │
                         │          textures)              │
                         │              │                  │
                         └──────────────┼──────────────────┘
                                        ▼
                                  Three.js Viewer
                               (PBR splatting shader,
                                shadow mapping,
                                parallax heightmaps,
                                procedural grass,
                                vegetation scatter,
                                water planes,
                                instanced objects,
                                T key texture toggle)
```

## Docs

- [Architecture](docs/architecture.md) -- modules, data flow, tech stack
- [Progress](docs/progress.md) -- what was built in each phase
- [Learnings](docs/learnings.md) -- technical discoveries and gotchas
- [Assumptions](docs/assumptions.md) -- design decisions and rationale
- [Extraction](extract/README.md) -- how to get WoW assets

## Long-term Goals

- **Playable in WoW**: Import upscaled assets into a 3.3.5a client via custom MPQ patches, running against [AzerothCore](https://github.com/azerothcore/azerothcore-wotlk) or [SPP Classics](https://github.com/celguar/spp-classics-cmangos). MPQ export pipeline built, needs Windows testing.
- ~~**Full zone coverage**: Expand from 4 tiles to all 18 Elwynn tiles.~~ Done.
- ~~**M2 model rendering**: Multi-submesh support with per-submesh materials.~~ Done.
- ~~**WMO buildings**: Parse WMO group files for farms, bridges, abbey gates.~~ Done.
- ~~**Before/after comparison**: Original vs AI-upscaled texture toggle.~~ Done (T key).
- ~~**AI upscale all textures**: Batch upscale remaining ground textures and M2 textures.~~ Done (Nano Banana 2).
- ~~**PBR materials**: Generate normal maps and roughness maps from upscaled diffuse textures.~~ Done (normal maps + heightmaps via gen_normals.py, PBR via MeshStandardMaterial).
- **NPC animations**: Skeletal animation from M2 bone data for idle/walk cycles.
- **More NPCs**: Pull actual spawn coordinates from AzerothCore database instead of hardcoded positions.
- **WMO texture upscaling**: Apply Nano Banana Pro to WMO building textures (roofs, walls, trim).
