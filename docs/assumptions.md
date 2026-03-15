# Assumptions

## Target Version: WoW 3.3.5a (Wrath of the Lich King)

For the long-term playable goal, we target WotLK:
- **Best modding support**: MPQ archives, simple patching
- **Mature emulators**: AzerothCore, TrinityCore, SPP Classics (CMaNGOS)
- **Elwynn unchanged**: Same assets from Vanilla through WotLK

For asset extraction, we pull from the **current retail/classic CDN** via wago.tools. Elwynn's core terrain and textures are essentially the same across versions, though modern files use the split ADT format (Cata+) with MDID/MHID instead of MTEX.

### Client availability

The 3.3.5a client is community-archived (not sold by Blizzard). SPP Classics provides a ready-to-run server repack supporting Vanilla 1.12, TBC 2.4.3, and WotLK 3.3.5 (Windows only).

## Zone: Elwynn Forest

- **Iconic**: Goldshire, Northshire Abbey, Crystal Lake
- **Simple geometry**: Rolling hills, scattered trees, small buildings
- **High contrast potential**: 2004-era textures vs AI-upscaled
- **Moderate scope**: ~10-15 unique ground textures, ~15-20 doodad models, ~5-10 buildings

Current coverage: 4 ADT tiles (32-33, 48-49), full zone is ~18 tiles (32-34, 47-52).

## AI Model Choices

### Nano Banana Pro for M2/prop textures

Google's Gemini-based image editor via fal.ai. Used in image-to-image mode: feeds the original texture as reference, prompts for dramatic detail enhancement at 4K resolution. Preserves UV layout while adding visible surface detail (wood grain, metal rivets, leaf veins). $0.30 per 4K image.

### Nano Banana 2 for terrain textures

Earlier Gemini model, used for the 4 terrain ground textures. Slightly more conservative than Pro, which works well for seamless tileable terrain textures. $0.15 per 2K image.

### Models evaluated and abandoned

- **Real-ESRGAN**: Over-smooths painted textures, loses the hand-painted WoW aesthetic
- **TRELLIS 2**: Image-to-3D mesh generation. Generated trees didn't match WoW's billboard-plane foliage style
- **ez-tree**: Procedural tree generation. Looked plastic, incompatible with WoW's lighting and art style
- **Flux Dev**: Text-to-image generated textures with wrong UV layouts. Img2img was too dark
- **fal.ai Creative Upscaler**: Too much hallucination even at low creativity settings

### Key insight

Keep original M2 geometry (it has correct UVs, art-directed silhouettes, and proper alpha masking). Only upgrade the textures. This preserves the WoW art style while dramatically improving surface detail.

## Infrastructure

### Why fal.ai

No local GPU. Pay-per-use (~pennies per texture). No model weight management. Trade-off: requires internet, adds latency.

### Why custom terrain rendering instead of wow.export

wow.export would be ideal (pre-assembled glTF scenes) but:
- x86_64 only, crashes on Apple Silicon Macs via Rosetta 2
- No ARM64/macOS native build available
- So we built custom ADT parsing + Three.js rendering

The custom approach works well for terrain and texture splatting. M2 model rendering needs more work (multi-submesh support, proper alpha). WMO building parsing is future work.

## Legal Position

Fan/research project for personal use. Original assets stay gitignored. AI outputs are derivative works for portfolio/demo. Credit Blizzard as original creator in any public posts.
