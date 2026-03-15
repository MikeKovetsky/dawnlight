---
name: Dawnlight Next Steps
overview: Prioritized roadmap for the next phases of Dawnlight, based on what's been completed (Phases 1-5) and the known gaps and long-term goals documented across the project.
todos:
  - id: phase6-submesh
    content: "Phase 6: Fix M2 multi-submesh rendering -- parse skin file submesh defs, export per-submesh data, render with separate geometries/materials in viewer"
    status: completed
  - id: phase7-tiles
    content: "Phase 7: Expand to all ~18 Elwynn tiles -- download, parse, and render remaining ADTs"
    status: completed
  - id: phase8-upscale
    content: "Phase 8: Batch upscale remaining 26 textures + add before/after toggle (T key) in viewer"
    status: completed
  - id: phase9-wmo
    content: "Phase 9: WMO building parser -- parse root + group files, export geometry, render Goldshire Inn etc."
    status: completed
  - id: phase10-mpq
    content: "Phase 10: MPQ export pipeline for playable 3.3.5a client (stretch goal)"
    status: completed
isProject: false
---

# Dawnlight -- Next Steps

## Current State (Phases 1-5 Complete)

- 4 Elwynn terrain tiles with multi-texture splatting (grass, dirt, rock, cobblestone)
- Water planes at correct heights (178 water chunks)
- 8 M2 doodad models placed via InstancedMesh (3,589 placements)
- 33 original textures downloaded, 7 upscaled
- Flyable Three.js viewer with orbit + FPS camera

## Known Issues (from [docs/progress.md](docs/progress.md))

- **M2 models render incorrectly**: All vertices in one mesh with one texture. WoW trees use trunk + leaves as separate submeshes with different materials. Trees are currently unrecognizable.
- **Alpha transparency**: `alphaTest: 0.5` isn't enough for multi-submesh leaf textures.
- **WMO buildings**: 22 WMO placements shown as semi-transparent boxes. No actual geometry.
- **Before/after toggle**: Mentioned in Phase 3 plan but not present in [viewer/src/app.js](viewer/src/app.js).

## Recommended Next Phases (in priority order)

### Phase 6: M2 Multi-Submesh Rendering (High Impact, Medium Effort)

The single highest-impact visual fix. Trees are the most common doodad (~3,500 placements) and currently look wrong.

**What to do:**

- Extend [pipeline/m2.py](pipeline/m2.py) to parse submesh definitions from `.skin` files (start offset, index count, texture index per submesh)
- Export per-submesh data in the model JSON: `submeshes: [{startIndex, indexCount, textureFdid}, ...]`
- Update [viewer/src/app.js](viewer/src/app.js) `buildM2Geometry()` to create a `THREE.Group` with separate `BufferGeometry` per submesh
- Each submesh gets its own `MeshStandardMaterial` with the correct texture
- Trunk submeshes: opaque material
- Leaf submeshes: `alphaTest: 0.5`, `side: DoubleSide`, `transparent: true`

### Phase 7: Full Elwynn Zone Coverage (Medium Impact, Low Effort)

Expand from 4 tiles to all ~18 Elwynn tiles. The pipeline already works -- it's just running it on more tiles.

**What to do:**

- Download remaining ADT tiles (root + tex0 + obj0) for tiles (32-34) x (47-52)
- Parse all tiles with `pipeline/adt.py` and `pipeline/obj0.py` using a shared global `baseZ`
- Copy terrain JSONs + splatmaps to `viewer/terrain/`
- Update `TILES` array in [viewer/src/app.js](viewer/src/app.js)
- May need to download + parse additional M2 models referenced by new tiles

### Phase 8: Batch Upscale All Textures + Before/After Toggle (Medium Impact, Low Effort)

Only 7 of 33 textures are upscaled. Complete the set and add a comparison toggle.

**What to do:**

- Batch upscale remaining 26 textures with `pipeline/upscale.py --seamless`
- Add upscaled texture set to `viewer/textures/upscaled/`
- Add `T` key toggle in the viewer to swap between original and upscaled texture uniforms in the splatting shader
- HUD indicator showing "Original" vs "AI Upscaled"

### Phase 9: WMO Building Parsing (High Impact, High Effort)

Goldshire Inn, Northshire Abbey, and farmhouses are currently invisible boxes. This is a significant parser effort.

**What to do:**

- Research WMO format at [wowdev.wiki/WMO](https://wowdev.wiki/WMO)
- Build `pipeline/wmo.py`: parse WMO root file (MOHD header, MOTX textures, MOMT materials, group count)
- Parse WMO group files: MOVT vertices, MOVI indices, MONR normals, MOTV UVs, MOBA render batches
- Export as JSON (vertices, indices, UVs, materials per batch)
- Place in viewer at MODF positions with correct rotation/scale
- Download WMO textures and convert BLP to PNG

### Phase 10: MPQ Export for Playable WoW (Stretch Goal)

The long-term goal: import upscaled assets into a 3.3.5a client.

**What to do:**

- Research MPQ patch format (patch-X.MPQ loaded after base archives)
- Build a `pipeline/mpq_export.py` that:
  - Takes upscaled PNGs and converts back to BLP format
  - Packages them into an MPQ archive with correct internal paths
  - Preserves the original file paths so the client loads replacements
- Test with AzerothCore or SPP Classics on a Windows machine
- This phase has the dependency of needing a Windows environment for testing

## Suggested Order

Phase 6 (multi-submesh) is the clear next step -- it's the most visually broken thing right now and the fix is well-understood. Phase 7 (more tiles) and Phase 8 (upscale + toggle) are quick wins that can follow in either order. Phase 9 (WMO) is a bigger undertaking. Phase 10 (MPQ) is the long-term moonshot.