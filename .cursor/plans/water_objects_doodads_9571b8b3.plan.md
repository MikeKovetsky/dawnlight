---
name: Water Objects Doodads
overview: Parse MH2O water data from root ADTs, parse MDDF/MODF object placement from obj0 ADTs, build a basic M2 model parser to extract geometry + textures, download key Elwynn doodads (trees, props), and render water planes + placed 3D objects in the viewer.
todos:
  - id: obj0-download
    content: Download obj0 ADTs and parse MDDF/MODF object placement data, export as objects.json per tile
    status: completed
  - id: water-parse
    content: Parse MH2O water chunks from root ADTs, add water plane definitions to terrain JSON
    status: completed
  - id: m2-parser
    content: "Build pipeline/m2.py: parse MD21 header, vertices, skin file indices, texture refs, export as JSON"
    status: completed
  - id: m2-download
    content: Search listfile for Elwynn tree/prop M2 models, download M2 + skin + textures via wago.tools
    status: completed
  - id: render-water
    content: Render water as translucent blue planes at correct heights in the viewer
    status: completed
  - id: render-objects
    content: Load M2 geometry, place at MDDF positions with rotation/scale, use InstancedMesh for repeated models
    status: completed
isProject: false
---

# Phase 5: Water, Doodads, and Buildings

## What we're adding

Populate the terrain with water planes, trees, rocks, props, and building placeholders. The scene goes from bare terrain to a living Elwynn landscape.

```mermaid
flowchart TD
    subgraph data [Download + Parse]
        obj0["obj0 ADTs\n(placement data)"] --> mddf["MDDF: M2 positions\n(trees, props)"]
        obj0 --> modf["MODF: WMO positions\n(buildings)"]
        rootADT["Root ADTs\n(already have)"] --> mh2o["MH2O: water planes"]
        m2files["M2 model files\n(wago.tools)"] --> m2parse["M2 Parser:\nvertices + indices + textures"]
    end
    subgraph render [Viewer]
        mh2o --> water["Translucent blue\nwater planes"]
        mddf --> placement["Place models at\nworld positions"]
        m2parse --> glb["Convert to\nThree.js geometry"]
        modf --> boxes["Placeholder boxes\nfor buildings"]
    end
```



## Data sources

**obj0 ADT** (need to download): Contains MDDF and MODF chunks with object placements. Also has MMDX/MWMO (model file lists) and MMID/MWID (name indices).

In the modern chunked format, obj0 uses MLMD (MODF replacement with file data IDs) and MLDD (MDDF replacement with file data IDs).

**MH2O** (already in root ADT): Water planes -- height, type, and extent per chunk.

**M2 files** (download via wago.tools): Binary model files. Need the M2 + associated .skin file for each model.

## Implementation steps

### 1. Download obj0 ADTs and parse placement data

Extend [extract/download.py](extract/download.py) to also grab obj0 files. Parse MDDF/MLDD for M2 placements and MODF/MLMD for WMO placements from the obj0 ADTs. Each entry has:

- File data ID (or name index)
- World position (3 floats)
- Rotation (3 floats, degrees)
- Scale (uint16, 1024 = 1.0)

Export as `{tile}_objects.json` with arrays of positioned objects.

### 2. Parse MH2O water from root ADTs

The MH2O chunk in root ADTs has a 256-entry header table (one per MCNK chunk), each pointing to water layer data with:

- Water type (river, ocean, magma)
- Min/max height
- Which sub-cells have water (8x8 bitmask)

Export water plane definitions as part of the terrain JSON.

### 3. Build M2 model parser

Create [pipeline/m2.py](pipeline/m2.py):

- Parse MD21 chunked format (Legion+ M2 files)
- Extract global vertex list (48 bytes each: position, normals, UVs)
- Find and download associated .skin file (LOD 0)
- Parse skin file for triangle indices + submesh definitions
- Read texture file data IDs from M2 header
- Export as JSON (vertices, indices, texture FDIDs) for the viewer to build BufferGeometry

### 4. Download key Elwynn M2 models

Search the listfile for Elwynn-specific M2 models:

- Trees: `world/nodxt/detail/elwynntree*.m2` or similar
- Props: fences, barrels, signs, rocks
- Download the M2 + skin + texture BLP files via wago.tools

### 5. Render in the viewer

Upgrade [viewer/src/app.js](viewer/src/app.js):

- **Water**: For each chunk with MH2O data, create a translucent blue plane at the water height
- **M2 doodads**: Load parsed M2 geometry as BufferGeometry, place instances at MDDF positions with correct rotation/scale
- **WMO buildings**: Render as semi-transparent gray boxes at MODF positions (full WMO parsing is a separate phase)
- **Instancing**: Use InstancedMesh for repeated models (e.g. same tree type placed 200 times)

## Complexity notes

- **M2 parser scope**: Static geometry only (no animations, no particles, no ribbons). Just vertices, triangles, and diffuse textures.
- **WMO**: Placeholder boxes only in this phase. Proper WMO group parsing is Phase 6.
- **Texture handling**: Download referenced BLP textures, convert to PNG, load in viewer.

