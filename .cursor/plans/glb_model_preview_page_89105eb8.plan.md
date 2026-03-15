---
name: GLB Model Preview Page
overview: Build a standalone HTML preview page at `viewer/preview.html` that lets you inspect a GLB model side-by-side with the original M2 mesh, tweak transforms interactively, and verify quality before deploying to the main viewer.
todos:
  - id: preview-html
    content: Create viewer/preview.html with dual-viewport layout, transform sliders, model selector, and stats overlay
    status: completed
  - id: preview-js
    content: Create viewer/src/preview.js with dual Three.js scenes, synced OrbitControls, M2 JSON + GLB loading, live transform controls, and auto-fit camera
    status: completed
isProject: false
---

# GLB Model Preview Page

## Problem

There is no way to inspect Trellis 2 GLB output before deploying it into the full Elwynn scene. The current workflow is blind: generate GLB, add to `GLB_MODELS`, reload the full viewer, then fly around trying to find one of the hundreds of tree instances. This makes it impossible to judge quality, tune scale/rotation, or compare against the original M2 mesh.

## Solution

A standalone preview page at `viewer/preview.html` with a focused Three.js scene showing:

- **Left**: original M2 model (loaded from JSON)
- **Right**: Trellis 2 GLB model (loaded from `models/glb/`)
- **Interactive controls** for scale, rotation, offset (writes the `GLB_XFORM` config values)
- **Model selector** dropdown populated from the `models/glb/` directory

## Implementation

### 1. Create `viewer/preview.html`

Single self-contained page using the same Three.js importmap as `index.html`. Two side-by-side viewports, each with its own camera/controls:

- **Left viewport**: loads `models/{name}.json`, builds geometry via the same `buildM2Submeshes` logic, applies textures from `models/tex_{fdid}.png`. Label: "Original M2 (635 verts)"
- **Right viewport**: loads `models/glb/{name}.glb` via `GLTFLoader`. Label: "Trellis 2 (20k verts)"
- Both orbit around origin with synced camera angles (OrbitControls linked)
- Neutral background (gradient or checkerboard) with directional + ambient lighting matching the main viewer
- Model name selector dropdown at the top, pre-populated with known tree models from `GLB_MODELS` + any `.glb` files found in `models/glb/`

### 2. Create `viewer/src/preview.js`

Reuses key functions from `app.js`:

- `loadModelJson(name)` -- fetch JSON
- `buildM2Submeshes(modelData)` -- geometry builder
- `loadM2Tex(fdid)` -- texture loader (simplified, always loads from `models/tex_{fdid}.png`)
- `loadGLBModel(name)` -- GLTFLoader

New features:

- **Dual renderer**: two `WebGLRenderer` instances in side-by-side containers, each with `OrbitControls`
- **Camera sync**: right camera copies left camera's spherical position on each frame
- **Transform sliders**: scale (0.1-200), rotY (-180 to 180 deg), offsetY (-50 to 50). Updates the GLB model transform live. Displays the `GLB_XFORM` config line to copy-paste into `app.js`
- **Stats overlay**: vertex count, triangle count, texture resolution, file size for both models
- **Auto-fit**: compute bounding box of the M2 model, position camera to frame it, apply same framing to GLB side

### 3. Wire into main viewer

Add a link in `index.html` controls hint or HUD: "P -- open model preview". Or just document the URL `/preview.html?model=elwynntreecanopy01`.

## Key Files

- `viewer/preview.html` -- page shell with dual viewport layout, sliders, model selector
- `viewer/src/preview.js` -- Three.js dual scene with synced cameras, M2 + GLB loading, transform controls
- `viewer/src/app.js` -- no changes needed (GLB_MODELS/GLB_XFORM stay as-is)

## URL API

`/preview.html?model=elwynntreecanopy01` loads that model directly. Changing the dropdown reloads with the new model.