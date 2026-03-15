---
name: Fix Plastic Trees
overview: Fix the plastic/harsh look of ez-tree foliage by improving material properties, leaf texture quality, and lighting response to better match WoW's warm, painterly aesthetic.
todos:
  - id: fix-leaf-mat
    content: "Update freshLeafMat: roughness 1.0, metalness 0, darken color, add emissive from leafTint"
    status: completed
  - id: fix-normals
    content: Override merged leaf geometry normals to (0,1,0) for uniform canopy lighting
    status: completed
  - id: improve-tex
    content: "Upgrade makeLeafTex: 256px, hue variation, detail ellipses, edge outlines"
    status: completed
  - id: fix-bark-mat
    content: Set bark material roughness 1.0 and metalness 0
    status: completed
  - id: test-result
    content: Test in browser, compare with original M2 trees via T toggle
    status: completed
isProject: false
---

# Fix Plastic-Looking ez-tree Foliage

## Root Cause

The current leaf material (`freshLeafMat` in `app.js:464-470`) creates a plastic look because:

- **Pure white `color: 0xffffff`** amplifies specular highlights from the strong sun (intensity 2.5)
- `**roughness: 0.8**` is too shiny for foliage — leaves should be nearly fully matte
- **No `emissive`** — shadow-facing leaf cards go pitch black, creating harsh contrast
- **128x128 procedural texture** with flat-colored ellipses has no depth or painterly detail
- **Leaf normals** point in random billboard directions, causing some cards to catch full sun glare (the white fragments in the screenshot)

## Fixes (all in `viewer/src/app.js`)

### 1. Leaf material tuning

Change `freshLeafMat` (line ~464) to reduce plastic look:

```js
const freshLeafMat = new THREE.MeshStandardMaterial({
  map: leafTex,
  alphaTest: 0.1,
  side: THREE.DoubleSide,
  roughness: 1.0,        // was 0.8 — fully matte, no specular
  metalness: 0,           // explicit non-metal
  color: 0xcccccc,        // was 0xffffff — slightly darken to reduce blown highlights
  emissive: new THREE.Color(cfg.leafTint || 0x5a7a30).multiplyScalar(0.15),
                          // subtle self-illumination prevents pitch-black shadows
});
```

### 2. Override leaf normals to point up

After merging leaf geometries (line ~498), reset all normals to `(0, 1, 0)`. This makes the entire canopy respond uniformly to the sun instead of individual cards catching random glare:

```js
if (merged) {
  const nrm = merged.attributes.normal;
  for (let i = 0; i < nrm.count; i++) {
    nrm.setXYZ(i, 0, 1, 0);
  }
  nrm.needsUpdate = true;
  // ... existing scale + push
}
```

### 3. Improve procedural leaf texture

In `makeLeafTex` (line ~413):

- Increase resolution to 256x256 for less pixelation
- Add hue variation between ellipses (shift between yellow-green and blue-green)
- Draw smaller secondary ellipses for detail
- Add subtle dark edge outlines for depth

### 4. Bark material consistency

Set `roughness: 1.0` and `metalness: 0` on bark material too (line ~488) so trunks match the matte WoW style.

## Expected Result

- Canopy lights uniformly (no random white glare cards)
- Matte, non-reflective surface like painted foliage
- Subtle emissive prevents pitch-black shadows in canopy
- Warmer, more varied leaf texture with depth

