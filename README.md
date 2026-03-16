# Dawnlight

AI-upscaled World of Warcraft landscapes in your browser.

**[Live Demo →](https://mikekovetsky.github.io/dawnlight/)**

https://github.com/MikeKovetsky/dawnlight/raw/main/demo/demo.mp4

| Original | AI-Upscaled |
|----------|-------------|
| ![Original](screenshots/original.webp) | ![Upscaled](screenshots/hero.webp) |

Toggle between original and AI-enhanced textures in real-time. Classic 2004-era textures and low-poly models go through an AI pipeline that produces 4K PBR materials with normal maps, parallax heightmaps, and real-time shadows -- all rendered in Three.js.

Zones: **Elwynn Forest** (Goldshire) · **Nagrand**

## How it works

**1. Extract** -- Download terrain, textures, and models directly from Blizzard's CDN via [wago.tools](https://wago.tools). ADT terrain files are parsed into heightmaps, texture splatmaps, and water planes. M2/WMO model files are parsed into renderable geometry.

**2. Upscale textures** -- Each texture goes through [fal.ai](https://fal.ai) Nano Banana Pro (Gemini image-to-image). A 2x2 tiling trick preserves seamless edges: tile the input, upscale, crop the center, cross-blend. Sobel-generated normal maps and heightmaps are derived from the upscaled diffuse for PBR shading.

![Texture comparison](screenshots/textures.webp)

**3. Upscale models** -- Low-poly M2 models (7K verts) can be fed through [Trellis 2](https://fal.ai/models/fal-ai/trellis-2) to generate high-poly meshes (65K+ verts) with clean topology and baked textures.

![Model comparison](screenshots/orc-preview.webp)

**4. Render** -- A Three.js viewer composites everything: multi-texture splatting with 4-layer blending, shadow mapping, parallax displacement, GPU-instanced grass (120K blades with wind), procedural vegetation scatter, and water planes. Press **T** to toggle between original and upscaled textures live.

<details>
<summary>Developer Setup</summary>

### Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd viewer && python -m http.server 8081
```

### Upscale any game's textures

Create `.env` with `FAL_KEY=your_key`, then:

```bash
python -m pipeline.upscale_dir ./textures/ -o ./upscaled/ \
  --prompt "fantasy RPG" --normals --heights --workers 6
```

Use `--normals-dir` / `--heights-dir` to write PBR maps to separate
directories instead of alongside the diffuse textures.

For WoW zones there's a shortcut that picks the right prompts and output
layout automatically:

```bash
python -m pipeline.upscale_zone nagrand
```

### Add a WoW zone

```bash
python -m extract.download adt --tile 17,35 --map expansion01
python -m pipeline.adt assets/adt/expansion01_17_35.adt
python -m pipeline.obj0 assets/adt/expansion01_17_35_obj0.adt
```

See [docs/](docs/) for architecture, progress, and learnings.

</details>

<details>
<summary>Pipeline</summary>

```
WoW CDN ──► Download ──► BLP/ADT/M2 files
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
        ADT Parser       Texture Conv      M2 Parser
             │                │                │
             ▼                ▼                ▼
        terrain JSON     Nano Banana Pro    model JSON
             │           (fal.ai, 4K)          │
             └────────────────┼────────────────┘
                              ▼
                        Three.js Viewer
```

</details>
