# Asset Extraction

## Option 1: wow.export (Recommended)

[wow.export](https://github.com/Kruithne/wow.export) can download assets directly from Blizzard's CDN without a local WoW installation.

1. Download wow.export from the [releases page](https://github.com/Kruithne/wow.export/releases)
2. Launch and select the WoW version (target 3.3.5a / WotLK Classic)
3. Navigate to the Elwynn Forest map tiles
4. Export terrain as OBJ/glTF, textures as PNG
5. Place exported textures in `assets/input/`

### Key files to export

**Ground textures** (tileable, these cover the entire zone):
- Grass variants, dirt, cobblestone, mud, road textures
- Usually found under `tileset/elwynn/` or `tileset/generic/`

**Models** (export as glTF):
- WMOs: Goldshire Inn, Northshire Abbey, farmhouses
- M2s: Trees, bushes, fences, barrels, rocks

## Option 2: wow.tools (Browser)

Browse and download individual files at [wowtools.work/files](https://wowtools.work/files/).

1. Search for textures by path (e.g. `tileset/elwynn`)
2. Download BLP files
3. Convert to PNG using the included script:

```bash
# List known Elwynn Forest texture paths
python -m extract.download list

# Convert downloaded BLP files to PNG
python -m extract.download convert path/to/blp/files/
```

## Option 3: CASCExplorer

[CASCExplorer](https://github.com/WoW-Tools/CASCExplorer) is a GUI tool for browsing and extracting CASC data directly. Export BLP files and convert them with the script above.
