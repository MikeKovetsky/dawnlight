---
name: Shell Grass Improvements
overview: Improve the shell-textured volumetric grass with terrain texture blending, deeper AO, warmer colors, splatmap-driven height variation, and dual-octave noise for clumpy natural patterns.
todos:
  - id: terrain-blend
    content: Pass terrain grass texture + texScale to shell material; blend ground color into lower shells in fragment shader
    status: completed
  - id: ao-darken
    content: Add pow-curve AO factor darkening base shells more aggressively
    status: completed
  - id: warm-colors
    content: Shift base/mid/tip color palette warmer to match Elwynn golden-green
    status: completed
  - id: height-var
    content: Use splatmap grassW to modulate effective shell height at zone transitions
    status: completed
  - id: clump-noise
    content: Add green channel to noise texture with large-scale clump pattern; multiply strand height by clump in shader
    status: completed
isProject: false
---

# Shell Grass Visual Improvements

All changes in [viewer/src/app.js](viewer/src/app.js).

## 1. Terrain texture blending into lower shells

Pass the upscaled grass terrain texture (`terrainTexSets["nanobanana"]["elwynngrassbase"]`) and `texScale` (0.15) as uniforms to the shell material. In the fragment shader, sample the terrain texture at `vShellWPos.xz * texScale` and blend it into the shell color based on shell level:

```glsl
vec3 groundCol = texture2D(terrainGrassTex, vShellWPos.xz * texScale).rgb;
grassCol = mix(groundCol * aoFactor, grassCol, shellLevel);
```

Lower shells look like the ground texture (continuity), upper shells transition to pure grass-tip green.

**Where**: Add `terrainGrassTex` + `texScale` uniforms in `makeShellMat` (line ~1034), add to `SHELL_FRAG_PREAMBLE` and `SHELL_FRAG_DIFFUSE`.

## 2. Deeper ambient occlusion

Replace the current flat base color with a stronger AO curve. Use `pow(shellLevel, 0.6)` as the AO factor so the bottom 3-4 shells are significantly darker, creating a deeper understory feel:

```glsl
float ao = 0.35 + 0.65 * pow(shellLevel, 0.6);
```

**Where**: `SHELL_FRAG_DIFFUSE` block, apply `ao` as a multiplier to the final grassCol.

## 3. Warmer color palette

Shift the tip color warmer to match Elwynn's golden-green, and add straw/yellow variation:

- Base: `vec3(0.08, 0.12, 0.03)` (darker for AO)
- Mid: `vec3(0.28, 0.40, 0.12)` (warm green)
- Tip: `vec3(0.50, 0.58, 0.20)` (golden-green)
- Variation adds `vec3(0.10, 0.08, 0.02)` scaled by noise

**Where**: `SHELL_FRAG_DIFFUSE`, replace the three color constants.

## 4. Splatmap-driven height variation

Use `grassW` (grass weight from splatmap) to modulate the effective shell height. Where grass dominates (grassW near 1.0), strands reach full height. At transition zones (grassW near 0.3), strands are much shorter:

```glsl
float heightMod = smoothstep(0.2, 0.8, grassW);
float threshold = shellLevel / heightMod;
if (strandH < threshold) discard;
```

This replaces the current `edgeFade` + `adjLevel` approach with a cleaner modulation.

**Where**: `SHELL_FRAG_DIFFUSE`, replace the threshold logic.

## 5. Second noise octave for clumpy patches

Generate a two-channel noise texture: R channel keeps the existing fine strand pattern, G channel adds larger-scale "clump" noise (fewer, bigger dots). In the fragment shader, multiply the strand height by the clump value so grass naturally grows in patches:

```glsl
float strandH = texture2D(grassNoise, wUv * noiseScale).r;
float clump = texture2D(grassNoise, wUv * noiseScale * 0.15).g;
strandH *= smoothstep(0.1, 0.5, clump);
```

**Where**: `makeGrassNoiseTex` -- draw large soft circles into the green channel. `SHELL_FRAG_DIFFUSE` -- sample and apply the clump factor.
