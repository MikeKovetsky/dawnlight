---
name: Full Goldshire with NPCs
overview: Expand the viewer to show the full Goldshire area with all buildings and static NPC creature models placed at approximate spawn locations.
todos:
  - id: fix-water-all
    content: Re-parse all 18 tiles with column-major water fix, copy to viewer
    status: completed
  - id: expand-tiles
    content: Set viewer TILES to 4 Goldshire-area tiles
    status: completed
  - id: download-wmos
    content: Download and parse 4 missing Goldshire WMOs (inn, silo, tower, dock)
    status: completed
  - id: download-npcs
    content: Download ~8 creature M2 models (human, horse, chicken, wolf, etc.)
    status: completed
  - id: place-npcs
    content: Add hardcoded GOLDSHIRE_NPCS array and render static creature models at spawn locations
    status: completed
isProject: false
---

# Full Goldshire with NPCs

## 1. Expand tiles to cover Goldshire area

Currently only `azeroth_32_49` is loaded. Goldshire sits across tile boundaries, with the inn, blacksmith, and nearby farms spanning 32_49, 33_49, and 32_50. Load 4 tiles centered on Goldshire:

**In [viewer/src/app.js](viewer/src/app.js):**

```javascript
const TILES = ["azeroth_32_49", "azeroth_33_49", "azeroth_32_50", "azeroth_33_50"];
```

Also re-parse the remaining tiles with the water column-major fix (only 32_49 was re-parsed; the other 17 still have old water data).

## 2. Download missing Goldshire WMOs

Four WMOs placed in the Goldshire area are not yet downloaded:

- **106851**: `goldshireinn.wmo` -- Lion's Pride Inn (the centerpiece of Goldshire)
- **106905**: `silo.wmo` -- barn silo
- **107037**: `magetower.wmo` -- mage tower
- **108143**: `redridgedocks02.wmo` -- dock platforms

Download with `pipeline/wmo.py`, copy to `viewer/wmo/`.

## 3. Add NPC creature models

Download ~8 iconic creature M2 models and place them at hardcoded Goldshire spawn positions. NPC spawn data from AzerothCore uses WoW world coordinates which we convert with `mddfToViewer()`.

**Creature models to download** (via `pipeline/m2.py`):


| FDID   | Model          | Placement                       |
| ------ | -------------- | ------------------------------- |
| 119940 | humanmale.m2   | Guards, Marshal Dughan, vendors |
| 119369 | humanfemale.m2 | Innkeeper, trainers             |
| 124427 | horse.m2       | Stables near the inn            |
| 123200 | chicken.m2     | Roaming around town             |
| 123162 | cat.m2         | Near buildings                  |
| 126487 | wolf.m2        | Forest edges                    |
| 123090 | boar.m2        | Forest/fields                   |
| 123362 | deer.m2        | Forest clearings                |


**Spawn placement approach**: Hardcode ~20-30 NPC positions in [viewer/src/app.js](viewer/src/app.js) as a `GOLDSHIRE_NPCS` array with WoW world coordinates. These approximate the actual spawn locations from the AzerothCore database. Each entry: `{model, pos: [x, y, z], rot: y_rotation}`.

NPCs are rendered the same way as M2 doodads -- static T-pose geometry with textures, placed via `InstancedMesh` grouped by model type. No animation.

## 4. Also fix water on remaining tiles

Re-run `pipeline/adt.py` on all 18 tiles (we only re-parsed 32_49 after the water column-major fix). Copy updated JSONs to viewer.