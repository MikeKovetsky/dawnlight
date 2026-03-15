---
name: Goldshire NPCs and Player
overview: Fix invisible NPCs (wrong scale), then add a distinguishable player character at Goldshire center.
todos:
  - id: fix-npc-scale
    content: "Fix NPC scale: character models are ~2 units tall vs trees at ~60 units. Scale 0.7 makes them invisible. Increase to ~4.0-5.0"
    status: completed
  - id: add-player
    content: "Add loadPlayer() function: loads humanmale at Goldshire center with green selection ring"
    status: completed
  - id: wire-loading
    content: Add loadPlayer() call to the loading chain after loadNPCs()
    status: completed
isProject: false
---

# Goldshire NPCs and Player Character

## Investigation: Why NPCs Are Invisible

NPCs exist in `GOLDSHIRE_NPCS` ([viewer/src/app.js](viewer/src/app.js) line 737) with 29 entries. The model JSONs and textures all exist. The coordinates are in MDDF space (same as doodads) and map to loaded tiles. **The root cause is wrong scale.**

### Scale mismatch (main problem)

Character/creature M2 models use a much smaller local unit than doodad M2 models:

- `humanmale`: 2.14 units tall, placed at scale 0.7 = **1.5 units** in scene
- `humanfemale`: 1.94 units tall, at scale 0.65 = **1.26 units**
- `chicken`: 0.44 units tall, at scale 1.0 = **0.44 units**
- `elwynntreecanopy01` (tree): **66 units** tall at scale ~1.0

A human at 1.5 units next to a 66-unit tree is 1/44th the tree height. Correct ratio should be ~~1/6. At the camera distance (~~300 units), these NPCs would be **~5 pixels tall** -- effectively invisible.

### Fix

Increase NPC scales by roughly 5-7x:

- `humanmale`: 0.7 -> **~4.5** (2.14 * 4.5 = 9.6 units, ~1/7 tree height)
- `humanfemale`: 0.65 -> **~4.5** (1.94 * 4.5 = 8.7 units)
- `horse`: 1.0 -> **~4.5** (2.58 * 4.5 = 11.6 units)
- `chicken`: 1.0 -> **~4.5** (0.44 * 4.5 = 2.0 units)
- `cat`: 1.0 -> **~4.5** (0.77 * 4.5 = 3.5 units)
- `wolf`: 1.0 -> **~4.5** (1.87 * 4.5 = 8.4 units)
- `boar`: 1.0 -> **~4.5** (2.09 * 4.5 = 9.4 units)
- `deer`: 1.0 -> **~4.5** (1.68 * 4.5 = 7.6 units)

Exact scale may need visual tuning. Start with 4.5 and adjust.

## 1. Fix NPC Scales in `GOLDSHIRE_NPCS`

Update all scale values in the `GOLDSHIRE_NPCS` array (line 737 of [viewer/src/app.js](viewer/src/app.js)). Use ~4.5 as a baseline scale for all models.

## 2. Add Player Character

Add a `loadPlayer()` function in [viewer/src/app.js](viewer/src/app.js) that:

- Loads `humanmale` model JSON (reuses `loadModelJson` + `buildM2Submeshes`)
- Places it as a regular `THREE.Mesh` (not instanced) at the center of Goldshire
- Position: MDDF coords approximately `[17075, 76, 26370]` (crossroads near the inn), converted via `mddfToViewer()`
- Scale ~4.5 (matching corrected NPC scale)

### Selection Ring

Add a WoW-style green selection circle underneath the player:

- `THREE.RingGeometry` (inner ~3.0, outer ~4.0, scaled to match the larger model)
- Green emissive material (`0x00ff00`), transparent, slight opacity (~0.6)
- Rotated flat on ground (`-PI/2` on X), parented to the player group

## 3. Wire into Loading Chain

At line 1119 of [viewer/src/app.js](viewer/src/app.js):

```javascript
loadTerrain().then(() => {
  createGrassShells();
  return loadObjects();
}).then(() => loadNPCs()).then(() => loadPlayer()).then(() => scatterVegetation());
```

All changes are in a single file: [viewer/src/app.js](viewer/src/app.js).