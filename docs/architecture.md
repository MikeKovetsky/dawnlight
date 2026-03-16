# Architecture

## Pipeline Overview

```
WoW Game Data (CASC via wago.tools)
        │
        ├─── Textures (BLP → PNG)          extract/download.py
        ├─── Terrain (ADT → JSON)          pipeline/adt.py
        ├─── Objects (obj0 ADT → JSON)     pipeline/obj0.py
        ├─── Models (M2 → JSON)            pipeline/m2.py
        │
        ▼
  ┌──────────────────────────────────┐
  │       AI Upscale (fal.ai)       │
  │     Nano Banana Pro (4K)       │
  │  (textures: trees, bushes,     │
  │   props, terrain)              │
  └────────────────┬───────────────┘
                   │
                   ▼
         textures/nanobanana/
         models/creative_test/
           │             │
           └──────┬──────┘
                  ▼
         ┌──────────────┐
         │  Three.js    │  viewer/
         │  Viewer      │  Terrain + splatting + water + objects
         └──────────────┘
```

## Tech Stack

| Layer       | Technology              | Why                                          |
|-------------|-------------------------|----------------------------------------------|
| AI Infra    | fal.ai                  | No local GPU needed, hosts Nano Banana Pro   |
| Upscaling   | Nano Banana Pro (Gemini)| Best structure preservation for game textures |
| Viewer      | Three.js + GLSL         | Browser-based, custom splatting shader        |
| Pipeline    | Python 3.11+            | Pillow, fal-client, struct for binary parsing |
| Download    | wago.tools API          | Reliable CASC file download by FDID          |
| Listfile    | wowdev/wow-listfile     | FDID-to-path mapping (136 MB CSV)            |

## Module Reference

### pipeline/

| Module       | Purpose                                              |
|-------------|------------------------------------------------------|
| `config.py`  | Shared config, env loading, paths, fal.ai endpoints  |
| `upscale.py` | Real-ESRGAN batch upscaler (legacy)                  |
| `upscale_creative.py` | Nano Banana 2 upscaler with parallel batching |
| `gen_textures.py` | Nano Banana Pro 4K texture generator for trees, bushes, and props |
| `gen_normals.py` | Sobel normal map + heightmap generator from diffuse textures |
| `adt.py`     | ADT terrain parser: heightmaps, water, splatmaps     |
| `obj0.py`    | obj0 ADT parser: M2/WMO object placement data       |
| `m2.py`      | M2 model parser: multi-submesh geometry + textures   |
| `wmo.py`     | WMO building parser: root + group files, materials   |
| `mpq_export.py` | MPQ staging: maps textures to WoW paths, BLP conv |

### extract/

| Module        | Purpose                                             |
|--------------|------------------------------------------------------|
| `download.py` | Listfile search, wago.tools download, BLP conversion |

Subcommands: `fetch-listfile`, `search`, `get`, `elwynn`, `adt`, `list`, `convert`

### viewer/

| File          | Purpose                                             |
|--------------|------------------------------------------------------|
| `index.html`  | Page shell, HUD, importmap for Three.js              |
| `src/app.js`  | Scene, terrain, splatting shader, water, M2/WMO objects, camera controls |
| `preview.html` | Side-by-side model comparison page (Original vs Upscaled) |
| `src/preview.js` | Preview page logic: dual viewports, synced cameras, model browser |

Features: multi-texture splatting, water planes, M2 instanced rendering with multi-submesh + alpha, WMO buildings with tiled textures, T key texture toggle (Original ↔ Nano Banana Pro), F key camera mode toggle, model preview page with Prev/Next navigation across 61 models.

| File                  | Purpose                                        |
|-----------------------|------------------------------------------------|
| `textures/index.html` | Texture comparison browser (Grid + Compare views) |

### Data Flow

```
wago.tools/api/casc/{fdid}
       │
       ├── BLP textures ──► Pillow ──► PNG ──► fal.ai Nano Banana Pro ──► 4K upscaled PNG
       ├── ADT root ──► adt.py ──► terrain JSON (heights + water)
       ├── ADT tex0 ──► adt.py ──► splatmap PNG + texmap JSON
       ├── ADT obj0 ──► obj0.py ──► objects JSON (positions/rotations)
       ├── M2 + skin ──► m2.py ──► model JSON (verts/indices/textures)
       └── WMO root + groups ──► wmo.py ──► WMO JSON (verts/indices/batches/materials)
```

## Directory Layout

```
dawnlight/
├── pipeline/              Python processing pipeline
│   ├── config.py            Shared config, env loading
│   ├── upscale.py           Real-ESRGAN batch upscaler (legacy)
│   ├── upscale_creative.py  Nano Banana 2 upscaler (parallel batching)
│   ├── gen_textures.py      Nano Banana Pro 4K upscaler (trees, bushes, props)
│   ├── gen_normals.py       Sobel normal maps + heightmaps from diffuse
│   ├── adt.py               ADT terrain + water + splatmap parser
│   ├── obj0.py              Object placement parser
│   └── m2.py                M2 model geometry parser
├── extract/               Asset extraction from WoW data
│   ├── download.py          Listfile search, download, BLP convert
│   └── README.md            Extraction instructions
├── viewer/                Three.js web viewer
│   ├── index.html           Page shell
│   ├── src/app.js           Scene + shaders + controls
│   ├── terrain/             Terrain JSONs + splatmap PNGs
│   ├── textures/original/   Original WoW ground textures
│   ├── textures/upscaled/   ESRGAN-upscaled ground textures (legacy)
│   ├── textures/nanobanana/ Nano Banana 2 upscaled ground textures
│   ├── models/              M2 model JSONs + texture PNGs (62 models)
│   ├── models/originals/    Original M2 textures (for comparison)
│   ├── models/creative_test/ Nano Banana Pro upscaled M2 textures (4K)
│   └── wmo/                 WMO building JSONs + texture PNGs (17 buildings)
├── assets/                (gitignored) all binary assets
│   ├── input/               Original downloaded textures
│   ├── upscaled/            AI-upscaled textures
│   ├── meshes/              TRELLIS-generated GLBs
│   ├── terrain/             Parsed terrain data
│   ├── adt/                 Raw ADT files
│   ├── blp/                 Raw BLP files
│   ├── m2/                  Raw M2 + skin files
│   ├── models/              Parsed M2 model JSONs + textures
│   ├── wmo/                 Raw WMO root + group files
│   └── wmo_models/          Parsed WMO JSONs + textures
├── docs/                  Documentation
├── requirements.txt       Python dependencies
└── README.md              Project overview
```
