# Learnings

Things discovered while building the pipeline.

## fal.ai API

### Auth env variable

fal-client looks for `FAL_KEY`, not `FAL_API_KEY`. The config module remaps:

```python
fal_key = os.getenv("FAL_KEY") or os.getenv("FAL_API_KEY")
if fal_key:
    os.environ["FAL_KEY"] = fal_key
```

### TRELLIS response shape differs between v1 and v2

- TRELLIS 1 (`fal-ai/trellis`): `result["model_mesh"]["url"]`
- TRELLIS 2 (`fal-ai/trellis-2`): `result["model_glb"]["url"]`

### TRELLIS needs real objects, not flat textures

Flat textures return 422. It needs a recognizable 3D object with foreground/background separation.

### File upload workflow

`fal_client.upload_file()` -> URL -> pass as `image_url` -> download result URL. Each upload/download adds ~1-2s latency.

## WoW Asset Download

### wago.tools is the working API

- wow.tools (`wow.tools/casc/file/fdid?id=X`) returns 404/500 on all endpoints
- wago.tools (`wago.tools/api/casc/{fdid}`) works reliably and returns raw file bytes
- No authentication needed, reasonable rate limits

### Community listfile

`https://github.com/wowdev/wow-listfile/releases/latest/download/community-listfile.csv` -- 136 MB CSV mapping FileDataIDs to file paths. Format: `fdid;path`. Essential for finding specific WoW files.

### BLP texture format

Pillow has native BLP support -- `Image.open("texture.blp")` just works. Some BLP files produce RGB (no alpha), others RGBA. Tree leaf textures need the RGBA version.

### MDID stores specular texture FDIDs

The MDID chunk in tex0 ADTs stores `_s.blp` (specular) FDIDs, not diffuse. The diffuse texture typically has FDID = specular_FDID - 1. Always verify by looking up the path in the listfile.

## ADT Terrain Format

### Split files (Cata+)

Modern ADTs from wago.tools use the split format:
- Root `.adt`: MCNK chunks with MCVT heightmaps, MH2O water
- `_tex0.adt`: MCNK chunks (no header) with MCLY layers, MCAL alpha maps, MDID texture refs
- `_obj0.adt`: MDDF doodad placements, MODF WMO placements

### Chunk magic byte order

ADT files use **reversed** magic bytes (little-endian). `MVER` is stored as bytes `R E V M`.
M2 files use **forward** magic bytes. `MD21` is stored as bytes `M D 2 1`.
This caught us when we reused the ADT chunk reader for M2 files.

### MCNK chunk ordering is column-major

Chunks in ADT files are stored column-major, NOT row-major. Sequential chunk index maps to: `ix = idx % 16`, `iy = idx // 16`. Getting this wrong (using `ix = idx // 16`) causes the splatmap chunks to be transposed -- each chunk paints its alpha pattern in the wrong grid position, creating visible seams at chunk boundaries.

### MCVT height layout

145 floats per chunk: 9x9 outer vertices interleaved with 8x8 inner vertices. Row pattern: 9 outer, 8 inner, 9 outer, 8 inner... Heights are relative to MCNK position Z.

### MCVT axis mapping

The MCVT 9x9 outer vertex grid axes do NOT match the intuitive row/col-to-ix/iy mapping. Verified by comparing shared boundary vertices (zero diff) between adjacent chunks:

- **MCVT columns** (the `col` in `row * 17 + col`) correspond to the **ix** chunk direction
- **MCVT rows** correspond to the **iy** chunk direction

When building the global heightmap grid (`gx`/`gy`), the correct mapping is:

```python
gx = iy * 8 + row   # row goes along iy
gy = ix * 8 + col    # col goes along ix
```

Getting this backwards (using `gx = iy * 8 + col`, `gy = ix * 8 + row`) transposes each chunk's height grid, causing both artificial terrain bumpiness and large height mismatches at every chunk and tile boundary.

### MH2O water header

12 bytes per entry (not 24 as initially assumed): `offset_instances (u32)`, `layer_count (u32)`, `offset_attributes (u32)`. 256 entries = 3072 bytes header. Instance data at the offset has liquid type, min/max height, and extent.

### Global baseZ for multi-tile consistency

Each tile's MCNK chunks have different Z positions. Using per-tile minimum as baseZ causes height mismatches at tile boundaries. Fix: compute a global minimum across all tiles and export all heights relative to that single value.

## MCAL Alpha Map Compression

WoW uses a custom RLE scheme for alpha maps (flag 0x200 in MCLY):

```python
while len(alpha) < 4096:
    info = read_byte()
    fill = bool(info & 0x80)
    count = info & 0x7F
    if fill:
        alpha.extend([read_byte()] * count)
    else:
        alpha.extend(read_bytes(count))
```

Decompresses to 4096 bytes (64x64 alpha values per chunk per layer).

## Texture Splatting

### Layer-based vs texture-based splatmaps

WoW's ADT stores alpha per layer (up to 4 layers per chunk), where each layer can reference a different texture in different chunks. A "layer 1" could be grass in one chunk and rock in another.

For the shader, we remapped to texture-specific channels: R=dirt, G=rock, B=cobblestone, with grass as the implicit base. This gives consistent shader behavior across all chunks.

## M2 Model Format

### Chunked format (Legion+)

Modern M2 files start with `MD21` chunk containing the classic M2 header + vertex data. Additional chunks:
- `SFID`: skin file FDIDs (LOD data with triangle indices)
- `TXID`: texture file FDIDs (BLP textures)
- `TXAC`, `LDV1`: other metadata

### Vertex format (48 bytes)

```
0x00: position:     3 floats (12 bytes)
0x0C: bone_weights: 4 uint8  (4 bytes)
0x10: bone_indices: 4 uint8  (4 bytes)
0x14: normal:       3 floats (12 bytes)
0x20: uv:           2 floats (8 bytes)
0x28: uv2:          2 floats (8 bytes)
```

Normals are at offset **0x14 (20)**, NOT 0x18 (24). UVs are at **0x20 (32)**, NOT 0x24 (36). Getting these wrong by 4 bytes reads garbled normals (shifted by one component) and wrong UVs (V always zero because it reads from the uv2 channel, which is usually all zeros).

### Skin files

Separate `.skin` files contain vertex lookup tables and triangle indices. Header starts with `SKIN` magic (forward order). Key fields: vertex lookup (uint16 indices into M2 vertex list), triangle indices, submesh definitions.

### Multi-submesh models

WoW trees use separate submeshes for trunk and leaves, each with different textures. Our current parser puts all vertices in one mesh with one texture, which breaks multi-material models. Proper fix: iterate submesh definitions from the skin file and create separate BufferGeometry per submesh.

### Z-up to Y-up conversion

WoW uses Z-up coordinate system, Three.js uses Y-up. Vertex positions need axis swap: `newY = oldZ`, `newZ = -oldY`.

## Coordinate Systems

### WoW world coordinates

- Origin at map center (17066.67, 17066.67)
- X positive = north, Y positive = west, Z = height
- ADT tile formula: `tileCoord = floor(32 - worldPos / 533.33)`

### MDDF/MODF positions

Object positions in ADT files use a coordinate system relative to a map corner:
- `worldX = 17066.67 - MDDF.x`
- `worldY = 17066.67 - MDDF.z`
- `height = MDDF.y`

### Viewer coordinate transform

```javascript
viewerX = MDDF.z - ((BASE_TY - 32) * TILE_SIZE + 17066.67)
viewerZ = MDDF.x - ((BASE_TX - 32) * TILE_SIZE + 17066.67)
viewerY = MDDF.y - globalBaseZ
```

Getting this wrong (inverted signs) was the main cause of objects appearing at wrong positions.

## wow.export

### macOS compatibility

wow.export 0.2.13 is x86_64 only. On Apple Silicon Macs:
- macOS Gatekeeper blocks it: fix with `xattr -cr <folder>`
- Rosetta 2 crash: `EXC_CRASH (SIGABRT)` -- "multi-threaded process forked, crashed on child side of fork pre-exec"
- No workaround found. Need a Windows machine or wait for ARM64 build.

## Seamless Tiling

The 2x2 tile-and-crop technique preserves seamless tiling through upscaling:
1. Tile the texture 2x2
2. Upscale the tiled image
3. Crop the center tile-sized region

The upscaler sees full context across every seam, and the crop edges match perfectly when tiled again.

## WMO Building Format

### Root file structure

WMO root files contain: MOHD (header with group count), MOMT (materials, 64 bytes each), GFID (group file FDIDs). In modern WMO files, MOMT stores texture FDIDs directly at offset 0x0C (not MOTX string offsets).

### Group file structure

Group files wrap all geometry in a single MOGP container chunk (68-byte header). Sub-chunks inside MOGP: MOVT (vertices), MONR (normals), MOTV (UVs), MOVI (indices), MOBA (render batches).

### MOBA render batch format

24 bytes: 6 int16 (bounding box), uint32 startIndex, uint16 count, uint16 minVert, uint16 maxVert, uint8 flag, uint8 materialId. The materialId indexes into the root file's MOMT array.

### GFID location

GFID appears near the end of the root file. An initial chunk scan may miss it if it stops early -- need to scan the entire file.

## M2 Texture Lookup Chain

Mapping submeshes to textures requires a three-step lookup:
1. Skin file **batch** (texture_units) has `skinSectionIndex` (which submesh) and `textureComboIndex`
2. MD21 header **textureCombos** table (at offset 0x80) maps combo index to texture index
3. **TXID** chunk maps texture index to FDID

The skin file header stores batches at offset 0x24 (count) and 0x28 (offset). Each batch is 24 bytes.

## BLP Write Support

Pillow can read BLP natively but can only write BLP in palette (P) mode -- 256 colors max. For full-quality BLP2 with DXT compression, need external tools (BLPConverter). WoW 3.3.5a textures are max 1024x1024.

## WMO Texture Conventions

WMO textures use WoW's V=0-at-top convention. When converting to OpenGL (V=0 at bottom), flip the V coordinate in the vertex data: `v = 1.0 - v`. Do NOT use `flipY = false` on the texture -- instead keep default flipY and transform the UVs.

WMO UVs frequently exceed the 0-1 range (25%+ of vertices). Always use `RepeatWrapping` on WMO textures to enable proper tiling.

## M2 Texture Upscaling Strategy

### Procedural tree replacement doesn't work for WoW

Tried replacing M2 tree meshes with procedurally generated trees (`ez-tree` library). The results looked fundamentally wrong because WoW trees use alpha-tested billboard planes (flat quads with painted leaf textures), while procedural generators create realistic branching structures. The procedural trees looked plastic, responded to lighting incorrectly, and didn't match the WoW art style at all. Lesson: keep the original geometry, upgrade the textures.

### Image-to-image beats text-to-image for texture upscaling

Flux text-to-image generated textures with completely different UV layouts, breaking the mapping on M2 models. Flux img2img preserved layout but produced too-dark results. Nano Banana Pro edit (image-to-image) was the sweet spot: it preserves the spatial layout of the original texture while adding significant new detail, and the colors naturally match.

### Prompt aggressiveness matters

Conservative prompts ("keep EXACT same, only increase resolution") produce barely-visible changes. Aggressive prompts ("dramatically enhance, 4x surface detail, AAA fantasy RPG quality") produce clearly visible improvements while still preserving the overall layout. The AI needs permission to be creative.

### Resolution must exceed the original

Upscaling at 2K when the original is already 2K produces no visible improvement. Always use a higher resolution than the source (4K for originals that are 1K-2K).

### Alpha channel handling for leaf textures

WoW leaf textures are RGBA with carefully authored alpha masks defining leaf billboard shapes. The AI upscaler only processes the RGB channels; the alpha is upscaled separately via Lanczos interpolation and recombined. This preserves the exact silhouette of each leaf cluster while enhancing the color detail.

### M2 textures need RepeatWrapping

WoW M2 model UVs frequently extend outside the 0-1 range for tiling. Three.js defaults to `ClampToEdgeWrapping`, which creates visible seam lines at texture boundaries. Setting `wrapS = wrapT = RepeatWrapping` on all M2 textures fixes this.

### Parallel API calls for batch generation

Running 6 concurrent fal.ai workers cuts generation time from ~80 minutes to ~8 minutes for 39 prop textures. The fal.ai queue handles concurrent requests well.

## Tile Boundary Objects

WMO and M2 objects placed near ADT tile boundaries can have positions slightly outside their host tile's terrain area. The object placement data (obj0) is stored per-tile, but the actual position may spill into adjacent tiles. Loading border tiles is necessary to provide terrain under these edge objects. Goldshire required loading tile 31_49/31_50 even though the main Elwynn range starts at tile 32.

## Alpha Map Column-Major Storage

Alpha map pixel data within each MCNK chunk is stored column-major: byte index `i` maps to column `i // 64`, row `i % 64`. For the splatmap generator, use `ai = px * 64 + py` (not `py * 64 + px`). Verified by boundary continuity analysis across 480 chunk neighbor pairs.
