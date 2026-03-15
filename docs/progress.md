# Progress Log

## Phase 1 - Project Bootstrap

Built the core project scaffold and AI pipeline.

- **Texture upscaling** (`pipeline/upscale.py`): Real-ESRGAN via fal.ai, batch processing, seamless tiling mode
- **3D mesh generation** (`pipeline/trellis_3d.py`): TRELLIS 2 via fal.ai, image-to-GLB
- **Asset extraction** (`extract/download.py`): BLP-to-PNG converter, known texture list
- **Three.js viewer** (`viewer/`): orbit camera, drag-and-drop, golden hour lighting
- Tested with procedural sample textures -- all pipelines working

## Phase 2 - Real WoW Textures

Downloaded actual Elwynn Forest textures from WoW's game data.

- Built automated download script using **wago.tools API** (`https://wago.tools/api/casc/{fdid}`)
- wow.tools was returning 404/500, wago.tools works reliably
- Downloaded community listfile (136 MB, 4.6M entries) from GitHub for FDID lookup
- Downloaded **33 Elwynn ground textures** (grass, dirt, cobblestone, rock, mud, flower, crop, leaf)
- Upscaled 7 key textures from 512-1024px to 2048-4096px with seamless tiling

## Phase 3 - Terrain in the Viewer

Parsed WoW ADT terrain files and rendered real Elwynn heightmaps.

- Built ADT binary parser (`pipeline/adt.py`): reads MVER, MHDR, MCNK chunks
- Extracts MCVT heightmaps (145 floats per chunk, 256 chunks = 129x129 grid per tile)
- Reads MDID texture references from tex0 ADT files
- Downloaded and parsed **4 terrain tiles** covering a section of Elwynn Forest
- Three.js viewer loads terrain as PlaneGeometry with displaced vertices
- Added PointerLockControls fly camera (WASD + mouse look) and orbit camera toggle

## Phase 4 - Multi-Texture Terrain Splatting

Added per-chunk texture blending using alpha maps from the ADT data.

- Extended ADT parser to read MCLY (layer definitions) and MCAL (compressed alpha maps)
- Implemented WoW alpha map RLE decompression algorithm
- Generated **1024x1024 splatmap PNGs** with texture-mapped channels (R=dirt, G=rock, B=cobblestone, base=grass)
- Built custom GLSL **ShaderMaterial** for texture splatting in Three.js
- 4 terrain textures blended per fragment based on splatmap weights
- Result: terrain shows realistic texture distribution -- grass fields, dirt paths, rocky outcrops

## Phase 5 - Water, Objects, and Models

Added water planes, parsed object placements, and built an M2 model parser.

- **Object placement** (`pipeline/obj0.py`): parses MDDF/MODF from obj0 ADT files
  - 3,589 M2 doodad placements and 22 WMO building placements across 4 tiles
  - Exports position, rotation, scale per object as JSON
- **Water** (MH2O parsing in `pipeline/adt.py`): 
  - Fixed header size (12 bytes per entry, not 24)
  - Renders as translucent blue planes at correct heights
  - 178 water chunks across 4 tiles
- **M2 model parser** (`pipeline/m2.py`):
  - Parses modern MD21 chunked format (forward-order magic, unlike ADT's reversed magic)
  - Extracts vertices (48 bytes each: position, normals, UVs), skin file indices, texture FDIDs
  - 8 Elwynn models parsed: 3 tree canopy variants, 1 mid tree, 2 plants, 1 bush, 1 fence
  - Automatic skin file + texture BLP download and PNG conversion
- **Coordinate transform**: WoW world coords to viewer local coords
  - `viewerX = MDDF.z - (BASE_TY * TILE_SIZE + 17066.67)`
  - `viewerZ = MDDF.x - 17066.67`
  - Global baseZ for consistent heights across tiles
- **InstancedMesh** rendering for repeated models (same tree placed hundreds of times)

## Phase 6 - M2 Multi-Submesh Rendering

Fixed tree and multi-material model rendering.

- Extended M2 parser to read **texture lookup table** from MD21 header (offset 0x80)
- Extended skin file parser to read **texture unit batches** (24 bytes each, skin_section_index -> texture_combo_index)
- Maps each submesh to its correct texture through batch -> tex_lookup -> TXID chain
- Model JSON now includes `submeshes` array with per-submesh `startIndex`, `indexCount`, `texFdid`
- Viewer creates **separate InstancedMesh per submesh** with correct texture and material
- Trunk submeshes: opaque, front-side rendering
- Leaf submeshes: `alphaTest: 0.5`, double-sided for correct foliage rendering
- Added `--reexport` flag to re-parse existing M2 files with new submesh data
- All 8 existing models re-exported; trees now correctly show trunk + canopy

## Phase 7 - Full Elwynn Zone Coverage

Expanded from 4 tiles to all 18 Elwynn Forest tiles.

- Downloaded **18 ADT tiles** (root + tex0 + obj0) covering (32-34) x (47-52)
- Computed **global baseZ** (12.936) across all tiles for seamless height matching
- Parsed all tiles with consistent baseZ -- no seam artifacts at tile boundaries
- ~15,000 M2 doodad placements and ~85 WMO placements across the full zone
- Downloaded and parsed **44 additional M2 models** (50+ placements each) -- rocks, fences, bushes, mushrooms, gate segments, lamp posts, barrels, etc.
- Total: **52 M2 models** covering the most visible objects in the zone
- Updated viewer with wider camera, fog, and render distance for the larger scene

## Phase 8 - Texture Upscale + Before/After Toggle

Completed all 4 terrain splatting textures and added live comparison.

- Upscaled **elwynndirtbase2** and **elwynnrockbasetest2** (the 2 missing terrain textures)
- All 4 splatting textures now available in both original and 4x upscaled versions
- Added **T key toggle** in the viewer to swap between original and AI-upscaled textures
- HUD shows "Original" vs "AI Upscaled (4x)" indicator
- Both texture sets preloaded; toggle is instant with no loading delay
- Shader uniforms updated on all splatting materials simultaneously

## Phase 9 - WMO Building Parser

Built a complete WMO parser for rendering buildings like farms, bridges, and abbey gates.

- Created `pipeline/wmo.py` -- parses WMO root and group files
- **Root file parsing**: MOHD header (group count), MOMT materials (texture FDIDs at offset 0x0C), GFID group file FDIDs
- **Group file parsing**: MOGP container with nested MOVT vertices, MONR normals, MOTV UVs, MOVI indices, MOBA render batches (24 bytes: start, count, material ID)
- Combines all group geometries with vertex offset tracking
- Downloaded and parsed **13 WMO buildings**: farms, bridges, abbey gates, barns, world trees, mine entrances, ruins
- Viewer renders WMOs at MODF positions with per-batch materials and textures
- ~100 WMO textures downloaded (walls, roofs, bricks, trim, floors, windows)

## Phase 10 - MPQ Export Pipeline

Built tooling to prepare upscaled textures for import into a WoW 3.3.5a client.

- Created `pipeline/mpq_export.py` with texture-to-WoW-path mapping
- Maps 9 upscaled textures to their correct `tileset/elwynn/*.blp` paths
- **BLP conversion**: Pillow palette-mode (256 colors, 1024x1024) as a working fallback
- Generates staging directory with correct WoW folder structure
- Documents the full workflow: BLP conversion -> MPQ packaging -> client installation
- Higher quality path documented: use BLPConverter for DXT compression, mpqcli for MPQ packaging

## Phase 11 - Bug Fixes and Polish

Multiple rendering fixes discovered through visual testing.

- **M2 vertex offset fix**: Normals were read at offset 24 (wrong), UVs at offset 36 (wrong). Correct offsets: normals at **20** (0x14), UVs at **32** (0x20). The 4-byte shift caused garbled normals and V=0 on all UVs, making tree canopies unrecognizable. All 52 M2 models re-exported.
- **Splatmap chunk ordering**: ADT MCNK chunks are stored **column-major** (`ix = idx % 16`), not row-major. Both tex0 alpha maps and MH2O water entries use the same sequential indexing. Fixed in both parsers.
- **Alpha map pixel indexing**: Alpha map data within each chunk is stored column-major (`ai = px * 64 + py`), verified by boundary matching analysis across 480 chunk pairs (avg diff 46.6 col-major vs 81.4 row-major).
- **Bush/plant alpha**: Single-submesh models with RGBA textures (bushes, plants) weren't getting alpha testing because the `isLeaf` heuristic required multiple submeshes. Fixed by enabling `alphaTest: 0.3` + `alphaHash` on all M2 materials unconditionally.
- **WMO texture UV flip**: WMO vertex UVs need `v = 1.0 - v` to convert from WoW's V=0-at-top to OpenGL's V=0-at-bottom convention. Without this, roof and wall textures appear upside-down.
- **WMO texture tiling**: WMO UVs go outside 0-1 range (25% of vertices). Added `RepeatWrapping` to WMO textures to enable proper tiling instead of edge clamping.
- **WMO untextured faces**: Submeshes with `texFdid=0` now get a neutral fallback color instead of being skipped, preventing invisible geometry.

## Phase 12 - Full Goldshire with NPCs

Expanded the viewer to show the complete Goldshire town with buildings, props, and NPC creatures.

- Added **tiles 31_49 and 31_50** to provide terrain under buildings at the tile 32 boundary (Goldshire sits right at the edge)
- Downloaded **4 additional WMOs**: Goldshire Inn (15K verts), blacksmith, stable, goldmine
- Downloaded **8 creature M2 models**: human male/female, horse, chicken, cat, wolf, boar, deer
- Fixed **creature replaceable textures**: creature M2 models use `texFdid=0` (runtime-assigned skins). Patched model JSONs with actual skin texture FDIDs (wolf black, brown boar, chicken, black cat, deer, brown horse, human skin)
- Placed **28 static NPCs** at approximate Goldshire spawn locations via hardcoded `GOLDSHIRE_NPCS` array
- Downloaded **10 village prop M2 models**: tent, wagon, lampposts, stone fences, gryphon roost, flagpoles, crates, training dummy, harness
- Total scene: **20 ADT tiles**, **17 WMO buildings**, **62 M2 models**, **28 NPCs**, **6 tiles rendered** (Goldshire area)

## Phase 13 - Nano Banana 2 Upscaling

Replaced ESRGAN with Nano Banana 2 (Gemini image-to-image via fal.ai) for higher-quality texture upscaling.

- Evaluated 3 upscaling approaches: ESRGAN (over-smooths painted textures), fal.ai Creative Upscaler (too much hallucination even at low creativity), **Nano Banana 2** (best structure preservation with natural detail)
- Built `pipeline/upscale_creative.py` -- Nano Banana 2 upscaler with parallel batch processing (5 workers), auto aspect ratio detection, and RGBA alpha channel handling
- Upscaled **17 tree M2 textures** to 2K via Nano Banana 2 (outputs in `viewer/models/creative_test/`)
- Upscaled **4 terrain ground textures** (grass, dirt, rock, cobblestone) to 2K (outputs in `viewer/textures/nanobanana/`)
- Updated viewer `T` key toggle: now cycles **Original ↔ Nano Banana 2** (removed ESRGAN from cycle)
- All 3 texture sets (original, nanobanana, terrain nanobanana) preloaded at startup for instant switching
- Built **texture comparison page** at `/textures/` with Grid and Compare view modes, showing all 80 textures with Original / ESRGAN / Nano Banana side-by-side

## Phase 14 - Trellis 2 Mesh Generation

Replaced low-poly M2 tree meshes with AI-generated high-poly 3D models via Trellis 2 on fal.ai.

- Built `pipeline/trellis_m2.py` -- three modes for M2 model replacement:
  - **Image-to-3D** (`generate`): feed a reference image, get a full high-poly GLB with PBR textures
  - **Multi-view** (`multi`): 1-4 views of the same object for better geometry reconstruction
  - **Retexture** (`retexture`): keep existing M2 geometry, generate new PBR textures from a reference image
  - **OBJ export** (`export-obj`): converts M2 JSON to OBJ format for retexture input or inspection
- Added `GLTFLoader` to the Three.js viewer for loading GLB files alongside existing JSON-based M2 models
- GLB models are **instanced** at the same positions as the original M2 placements via the MDDF transform matrices
- Per-model `GLB_XFORM` config for scale/rotation/offset adjustment (original tree is ~66 units tall, GLB is normalized to ~1 unit)
- Integrated with `T` key toggle: GLB models show in enhanced modes (ESRGAN/Nano Banana), original M2 meshes show in Original mode
- Dual mesh creation: both M2 and GLB instanced meshes are created at load time, toggled via `glbMeshes`/`glbOrigMeshes` visibility arrays
- HUD displays "Trellis 2 Models" indicator when GLB models are active
- First test: `elwynntreecanopy01` replaced (635 verts → 20k verts, 760 tris → ~40k tris, 1.4 MB GLB with 2048px PBR textures)
- 10 tree model names configured for generation: `elwynntreecanopy01-04`, `elwynntreemid01`, `canopylesstree01`, `duskwoodtreecanopy01-02`, `duskwoodtree06-07`

## Phase 15 - Nano Banana Pro 4K Texture Upscaling

Replaced Nano Banana 2 upscaling with Nano Banana Pro at 4K for dramatically better M2 textures.

- **Explored and abandoned ez-tree**: Tried procedural tree generation via `ez-tree` library to replace M2 tree meshes with high-poly generated trees. Results looked plastic and incompatible with WoW's art style (flat billboard-plane foliage vs procedural branch geometry). Reverted entirely.
- **Switched to texture-only upscaling**: Kept original M2 geometry (which has correct UV mapping and WoW art style), focused on dramatically enhancing the textures mapped onto them.
- **Built `pipeline/gen_textures.py`**: Nano Banana Pro image-to-image upscaler for M2 textures. Uses the original texture as reference to preserve UV layout while adding 4x detail.
  - `BARK_FDIDS`: 8 tree bark textures with per-texture descriptions
  - `LEAF_FDIDS`: 16 tree/bush leaf textures with alpha channel preservation
  - `PROP_FDIDS`: 39 prop textures (fences, barrels, rocks, lampposts, wagons, etc.)
  - `--only bark|leaf|prop|all` flag for selective regeneration
  - `--workers N` for parallel generation (default 6 concurrent API calls)
  - `--skip-existing` to avoid re-generating already-upscaled textures
  - Alpha channel handling: separates RGB for AI upscaling, upscales alpha via Lanczos, recombines
  - Aspect ratio auto-detection with fallback for unsupported ratios (1:4 → 9:16)
- Generated **63 upscaled textures** (24 tree/bush + 39 prop) at 4K resolution via Nano Banana Pro
- Added all 63 FDIDs to `UPSCALED_FDIDS` in both `app.js` and `preview.js`
- Copied all originals to `models/originals/` for the texture toggle comparison
- **Material improvements**: foliage models get `roughness: 1.0`, `metalness: 0` for matte WoW-style look. All M2 textures now use `RepeatWrapping` for proper UV tiling.
- **Shadow casting**: all M2 instanced meshes have `castShadow = true` and `receiveShadow = true`
- **Model preview page** (`preview.html`): side-by-side Original vs New Textures comparison with dual synced Three.js viewports, Prev/Next navigation, 61 models (trees, bushes, props)
- Evaluated and abandoned: Flux text-to-image (wrong UV layout), Flux img2img (too dark), Nano Banana 2 edit (too subtle at 2K). Nano Banana Pro at 4K with aggressive prompts was the winner.

## Tools Evaluated

| Tool | Status | Notes |
|---|---|---|
| wago.tools API | Working | `https://wago.tools/api/casc/{fdid}` -- reliable file download by FDID |
| wow.tools API | Broken | Returns 404/500 on all download endpoints |
| wow.export | Crashes on macOS ARM64 | x86_64 Electron app, Rosetta 2 fork crash |
| WebWowViewerCpp | Not tested | Windows/Linux only, no macOS builds |
| SPP Classics | Not tested | Windows-only WoW private server repack |
| Community listfile | Working | 136 MB CSV from GitHub, maps FDIDs to file paths |
| fal.ai Nano Banana Pro | Working | 4K image-to-image upscaling ($0.30/image). Best for M2/prop textures. |
| fal.ai Nano Banana 2 | Working | 2K image-to-image upscaling ($0.15/image). Used for terrain textures. |
| fal.ai Trellis 2 | Evaluated | Image-to-3D. Abandoned for trees -- wrong art style for WoW's billboard foliage. |
| fal.ai Flux Dev | Evaluated | Text-to-image/img2img. Wrong UV layout for texture upscaling. |
| ez-tree | Evaluated | Procedural tree lib. Looked plastic, incompatible with WoW lighting. Abandoned. |
