import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const HEADER_H = document.getElementById("site-header")?.offsetHeight || 40;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x6b9bd2);
scene.fog = new THREE.FogExp2(0x8eb8e0, 0.0006);

const camera = new THREE.PerspectiveCamera(60, innerWidth / (innerHeight - HEADER_H), 0.1, 8000);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(innerWidth, innerHeight - HEADER_H);
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.3;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(renderer.domElement);

const orbitControls = new OrbitControls(camera, renderer.domElement);
orbitControls.enableDamping = true;
orbitControls.dampingFactor = 0.08;
orbitControls.maxDistance = 6000;
orbitControls.minDistance = 5;

const sun = new THREE.DirectionalLight(0xffe8c0, 2.5);
sun.position.set(1400 + 500, 600, 700 + 400);
sun.target.position.set(1400, 0, 700);
sun.castShadow = true;
sun.shadow.mapSize.width = 4096;
sun.shadow.mapSize.height = 4096;
sun.shadow.camera.near = 1;
sun.shadow.camera.far = 2000;
sun.shadow.camera.left = -1200;
sun.shadow.camera.right = 1200;
sun.shadow.camera.top = 1200;
sun.shadow.camera.bottom = -1200;
sun.shadow.bias = -0.0005;
scene.add(sun);
scene.add(sun.target);
scene.add(new THREE.HemisphereLight(0x87ceeb, 0x4a7a3a, 0.8));
scene.add(new THREE.AmbientLight(0xfff5e6, 0.3));

// -- zone config --

const ZONES = {
  elwynn: {
    label: "Elwynn Forest",
    tiles: ["azeroth_31_49", "azeroth_31_50", "azeroth_32_49", "azeroth_32_50"],
    baseTX: 31, baseTY: 47,
    texNames: ["elwynngrassbase", "elwynndirtbase2", "elwynnrockbasetest2", "elwynncobblestonebase"],
    texDir: "textures", texExt: ".webp",
    terrainDir: "terrain",
    hasNormals: true,
    camera: [1409.3, 57.3, 447.6], target: [1464, 15, 509],
  },
  nagrand: {
    label: "Nagrand",
    tiles: ["expansion01_17_35"],
    baseTX: 17, baseTY: 35,
    texNames: ["tex_187327", "tex_189024", "tex_187332", "tex_187357"],
    texDir: "textures/nagrand", texExt: ".png",
    terrainDir: "terrain/nagrand",
    hasNormals: true,
    camera: [446.8, 51.8, 404.2], target: [266, 20, 266],
  },
};

const urlZone = new URLSearchParams(location.search).get("zone") || "elwynn";
const zone = ZONES[urlZone] || ZONES.elwynn;

const zoneSelect = document.getElementById("zone-select");
if (zoneSelect) {
  zoneSelect.value = urlZone;
  zoneSelect.addEventListener("change", (e) => {
    window.location.search = `?zone=${e.target.value}`;
  });
}

camera.position.set(...zone.camera);
orbitControls.target.set(...zone.target);

// -- constants --

const TILES = zone.tiles;
const TILE_SIZE = 533.3333;
const CHUNK_SIZE = TILE_SIZE / 16;
const BASE_TX = zone.baseTX, BASE_TY = zone.baseTY;
const TEX_NAMES = zone.texNames;
const texLoader = new THREE.TextureLoader();
const maxAniso = renderer.capabilities.getMaxAnisotropy();

const UPSCALED_FDIDS = new Set([
  464350, 464351, 189570, 189563, 189520, 189554, 189519,
  131942, 198585, 189573, 189572, 189518, 249605, 189543,
  189542, 242694, 189403,
  132027, 132031, 189401, 189404, 189937, 202026, 321364,
  124303, 124306, 130279, 145513, 189080, 189082, 189421, 189422,
  189433, 189460, 189479, 189487, 189514, 189720, 189769, 189771,
  189773, 189799, 189800, 189814, 189822, 190367, 190368, 190369,
  190386, 190534, 190610, 190722, 191275, 197427, 198183, 198260,
  198287, 198298, 198305, 199564, 199633, 199814, 203474,
]);

const UPSCALED_WMO = new Set([
  126610, 126611, 126998, 126999, 127000, 127001, 127002, 127003, 127004, 127005, 127006,
  127093, 127095, 127100, 127187, 127212, 127216, 127221, 127280, 127299, 127301, 127322,
  127324, 127325, 127441, 127449, 127467, 127476, 127495, 127864, 127868, 127869, 127874,
  127877, 127915, 127917, 127977, 127979, 127980, 128157, 128159, 128160, 128331, 128470,
  128471, 128472, 128473, 128474, 128475, 128477, 128478, 128480, 128481, 128483, 128484,
  128566, 128567, 128568, 128569, 128570, 128571, 128572, 128597, 128599, 128600, 128694,
  128698, 128739, 128759, 128760, 128762, 128884, 129007, 129255, 129261, 129266, 129267,
  129268, 129317, 129318, 129395, 129400, 129402, 129403, 129891, 129892, 129893, 129895,
  129896, 129905, 129906, 129911, 129912, 130052, 130053, 130054, 130064, 130065, 130066,
  130081, 130116, 130117, 130118, 130119, 130120, 130258, 130279, 130281, 130302, 130307,
  130308, 130309, 130310, 130311, 130312, 130313, 130315, 130316, 189083, 190085, 190086,
  190092, 190094, 315088, 315089, 315090, 315091, 315092, 315093, 315094, 315095, 315096,
  353675,
]);

const m2TexPairs = {};
const m2SwapMats = [];
const wmoTexPairs = {};
const wmoSwapMats = [];

function configM2Tex(tex) {
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.flipY = false;
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.anisotropy = maxAniso;
  tex.minFilter = THREE.LinearMipmapLinearFilter;
  tex.magFilter = THREE.LinearFilter;
  return tex;
}

function loadM2Tex(fdid) {
  if (UPSCALED_FDIDS.has(fdid)) {
    if (!m2TexPairs[fdid]) {
      m2TexPairs[fdid] = {
        original: configM2Tex(texLoader.load(`models/originals/tex_${fdid}.webp`)),
        v2: configM2Tex(texLoader.load(`models/creative_test/tex_${fdid}_nanobanana.webp`)),
      };
    }
    return m2TexPairs[fdid][TEX_MODES[texModeIdx]];
  }
  return configM2Tex(texLoader.load(`models/tex_${fdid}.webp`));
}

function configWmoTex(tex) {
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.anisotropy = maxAniso;
  return tex;
}

function loadWmoTex(fdid) {
  if (UPSCALED_WMO.has(fdid)) {
    if (!wmoTexPairs[fdid]) {
      wmoTexPairs[fdid] = {
        original: configWmoTex(texLoader.load(`wmo/originals/tex_${fdid}.webp`)),
        v2: configWmoTex(texLoader.load(`wmo/creative_test/tex_${fdid}_nanobanana.webp`)),
      };
    }
    return wmoTexPairs[fdid][TEX_MODES[texModeIdx]];
  }
  const tex = texLoader.load(`wmo/tex_${fdid}.webp`);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  return tex;
}

const FDID_TO_MODEL = {
  189397: "duskwoodbush03", 189402: "duskwoodbush07",
  189406: "duskwoodspookybush02", 189408: "duskwoodspookybush04",
  189410: "pumpkinpatch01", 189432: "duskwoodmushroom01",
  189461: "duskwoodstraw", 189471: "duskwoodfencetop",
  189491: "gatepost", 189492: "gatesegment01", 189493: "gatesegment02",
  189511: "duskwoodruinsbrick", 189521: "duskwoodtreespookless01",
  189522: "duskwoodtreespookless02", 189544: "duskwoodbrowntree",
  189558: "duskwoodtree06", 189559: "duskwoodtree07",
  189560: "duskwoodtreecanopy01", 189561: "duskwoodtreecanopy02",
  189700: "elwynnbush09", 189715: "elwynncliffrock01",
  189716: "elwynncliffrock02", 189768: "elwynnrock1",
  189770: "elwynnrock2", 189772: "elwynnseaweed01",
  189795: "elwynnwoodfence01", 189796: "elwynnwoodpost01",
  189815: "jar01", 189816: "jar02",
  189919: "canopylesstree01", 189927: "elwynntreecanopy01",
  189928: "elwynntreecanopy02", 189929: "elwynntreecanopy03",
  189930: "elwynntreecanopy04", 189932: "elwynntreemid01",
  190375: "swampofsorrowlilypad01", 190376: "swampofsorrowlilypad02",
  190378: "swampplant04", 190379: "swampplant05",
  190535: "westfallbarrel01", 190659: "westfallfence",
  190660: "westfallfenceend", 190661: "westfallfencepost",
  190719: "bird01", 190731: "fireflies01",
  198303: "duskwoodlamppost", 199563: "barrel01",
  199815: "freestandingtorch01", 199820: "generaltorch01",
  202024: "kalidarbush04", 203480: "wetlandgrass02",
  321367: "hyjalbushburnt01",
  197108: "humantentlarge", 198288: "stormwindgypsywagon01",
  189825: "lamppost", 189793: "elwynnstonefence",
  189794: "elwynnstonefencepost", 198261: "gryphonroost01",
  198199: "flagpole01", 199632: "crate01",
  198666: "stormwindwoodendummy01", 190596: "harness",
  193043: "nagrandbush02", 203493: "wetlandsshrub04",
  203296: "lochmodanshrub01", 203498: "wetlandsshurb08",
  189959: "elwynntallwaterfall01", 193134: "nagrandtree08",
  203492: "wetlandshrub09", 193045: "nagrandbush03",
  191807: "ao_lamppost01",
};

const FOLIAGE_MODELS = new Set([
  "elwynntreecanopy01", "elwynntreecanopy02", "elwynntreecanopy03", "elwynntreecanopy04",
  "elwynntreemid01", "canopylesstree01",
  "duskwoodtreecanopy01", "duskwoodtreecanopy02", "duskwoodtree06", "duskwoodtree07",
  "duskwoodtreespookless01", "duskwoodtreespookless02", "duskwoodbrowntree",
  "elwynnbush09", "kalidarbush04", "duskwoodbush03", "duskwoodbush07",
  "duskwoodspookybush02", "duskwoodspookybush04", "hyjalbushburnt01",
]);

const WOW_CENTER = 17066.667;
const COORD_OX = (BASE_TY - 32) * TILE_SIZE + WOW_CENTER;
const COORD_OZ = (BASE_TX - 32) * TILE_SIZE + WOW_CENTER;

const tileBaseZ = {};

function mddfToViewer(mx, my, mz) {
  const bases = Object.values(tileBaseZ);
  const minBase = bases.length > 0 ? Math.min(...bases) : 42.86;
  return [mz - COORD_OX, my - minBase, mx - COORD_OZ];
}

// -- splatmap shader injection (for MeshStandardMaterial.onBeforeCompile) --

const SPLAT_UNIFORMS_GLSL = `
uniform sampler2D splatMap, texBase, texR, texG, texB;
uniform sampler2D texBaseN, texRN, texGN, texBN;
uniform sampler2D texBaseH, texRH, texGH, texBH;
uniform float texScale, heightScale, normalStrength;
varying vec2 vSplatUv;
varying vec3 vWorldPos;
vec2 pomTileUv;
`;

const SPLAT_DIFFUSE_GLSL = `{
  vec4 splat = texture2D(splatMap, vSplatUv);
  vec2 tUv = vWorldPos.xz * texScale;
  float baseW = max(0.0, 1.0 - splat.r - splat.g - splat.b);

  float dist = length(cameraPosition - vWorldPos);
  float pomFade = clamp(1.0 - (dist - 80.0) / 200.0, 0.0, 1.0);
  if (pomFade > 0.001) {
    float h = texture2D(texBaseH, tUv).r * baseW
            + texture2D(texRH, tUv).r * splat.r
            + texture2D(texGH, tUv).r * splat.g
            + texture2D(texBH, tUv).r * splat.b;
    vec3 N = normalize(vNormal);
    vec3 T = normalize(vec3(1.0, 0.0, 0.0) - N * N.x);
    vec3 B = cross(N, T);
    vec3 vDir = normalize(cameraPosition - vWorldPos);
    vec3 viewTS = normalize(transpose(mat3(T, B, N)) * vDir);
    tUv += viewTS.xy * h * heightScale * pomFade;
  }
  pomTileUv = tUv;

  diffuseColor = vec4(
    (texture2D(texBase, tUv) * baseW
   + texture2D(texR, tUv) * splat.r
   + texture2D(texG, tUv) * splat.g
   + texture2D(texB, tUv) * splat.b).rgb, 1.0);
}`;

const SPLAT_NORMAL_GLSL = `{
  if (normalStrength > 0.01) {
    vec4 splat = texture2D(splatMap, vSplatUv);
    float baseW = max(0.0, 1.0 - splat.r - splat.g - splat.b);
    vec3 nBase = texture2D(texBaseN, pomTileUv).rgb * 2.0 - 1.0;
    vec3 nR = texture2D(texRN, pomTileUv).rgb * 2.0 - 1.0;
    vec3 nG = texture2D(texGN, pomTileUv).rgb * 2.0 - 1.0;
    vec3 nB = texture2D(texBN, pomTileUv).rgb * 2.0 - 1.0;
    vec3 texNrm = normalize(nBase * baseW + nR * splat.r + nG * splat.g + nB * splat.b);
    texNrm = mix(vec3(0.0, 0.0, 1.0), texNrm, normalStrength);
    vec3 T = normalize(vec3(1.0, 0.0, 0.0) - normal * normal.x);
    vec3 B = cross(normal, T);
    normal = normalize(mat3(T, B, normal) * texNrm);
  }
}`;

// -- helpers --

function loadTileTex(name, subdir = "original", linear = false) {
  const dir = zone.texDir || "textures";
  const ext = zone.texExt || ".webp";
  const tex = texLoader.load(`${dir}/${subdir}/${name}${ext}`);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  if (!linear) tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = maxAniso;
  return tex;
}

function tileOffset(tileName) {
  const m = tileName.match(/(\d+)_(\d+)$/);
  if (!m) return [0, 0];
  return [(parseInt(m[2]) - BASE_TY) * TILE_SIZE, (parseInt(m[1]) - BASE_TX) * TILE_SIZE];
}

function wowToLocal(wx, wy, wz) {
  const lx = (17066.67 - wz);
  const lz = (17066.67 - wx);
  const ly = wy;
  const ox = lx - BASE_TY * TILE_SIZE;
  const oz = lz - BASE_TX * TILE_SIZE;
  return [ox, ly, oz];
}

const TEX_MODES = ["original", "v2"];
const TEX_LABELS = { original: "Original", v2: "Upscaled" };
let texModeIdx = 0;
const terrainTexSets = {};
const terrainNormals = {};
const terrainHeights = {};
const zoneModes = zone.hasNormals ? TEX_MODES : ["original"];
for (const mode of zoneModes) {
  terrainTexSets[mode] = {};
  const subdir = mode === "v2" ? "v2" : mode;
  for (const name of TEX_NAMES) {
    terrainTexSets[mode][name] = loadTileTex(name, subdir);
  }
}
if (!terrainTexSets.v2) terrainTexSets.v2 = terrainTexSets.original;
if (zone.hasNormals) {
  for (const name of TEX_NAMES) {
    terrainNormals[name] = loadTileTex(name + "_n", "normals", true);
    terrainHeights[name] = loadTileTex(name + "_h", "heights", true);
  }
}
const terrainTextures = () => terrainTexSets[TEX_MODES[texModeIdx]];

// -- terrain loading --

const terrainTiles = {};
const terrainMeshes = [];

async function loadTerrain() {
  const tDir = zone.terrainDir || "terrain";
  for (const tileName of TILES) {
    try {
      const resp = await fetch(`${tDir}/${tileName}.json`);
      if (!resp.ok) continue;
      const tile = await resp.json();

      let splatTex = null;
      try {
        splatTex = await new Promise((res, rej) =>
          texLoader.load(`${tDir}/${tileName}_splatmap.webp`, res, undefined, rej));
        splatTex.minFilter = splatTex.magFilter = THREE.LinearFilter;
      } catch {}

      tileBaseZ[tileName] = tile.baseZ || 0;
      terrainTiles[tileName] = tile;
      const mesh = buildTerrainMesh(tile, splatTex);
      terrainMeshes.push({ mesh, tile, splatTex });
      scene.add(mesh);

      if (tile.water) addWater(tile.water, tileName);
    } catch {}
  }
}

const splatShaders = [];

function makeSplatMaterial(splatTex) {
  const mat = new THREE.MeshStandardMaterial({ roughness: 0.85, metalness: 0.0 });
  mat.onBeforeCompile = (shader) => {
    const enhanced = texModeIdx > 0;
    const texSet = terrainTextures();
    shader.uniforms.splatMap = { value: splatTex };
    shader.uniforms.texBase = { value: texSet[TEX_NAMES[0]] };
    shader.uniforms.texR = { value: texSet[TEX_NAMES[1]] };
    shader.uniforms.texG = { value: texSet[TEX_NAMES[2]] };
    shader.uniforms.texB = { value: texSet[TEX_NAMES[3]] };
    const dummyTex = new THREE.DataTexture(new Uint8Array([128, 128, 255, 255]), 1, 1, THREE.RGBAFormat);
    dummyTex.needsUpdate = true;
    const dummyH = new THREE.DataTexture(new Uint8Array([128, 128, 128, 255]), 1, 1, THREE.RGBAFormat);
    dummyH.needsUpdate = true;
    shader.uniforms.texBaseN = { value: terrainNormals[TEX_NAMES[0]] || dummyTex };
    shader.uniforms.texRN = { value: terrainNormals[TEX_NAMES[1]] || dummyTex };
    shader.uniforms.texGN = { value: terrainNormals[TEX_NAMES[2]] || dummyTex };
    shader.uniforms.texBN = { value: terrainNormals[TEX_NAMES[3]] || dummyTex };
    shader.uniforms.texBaseH = { value: terrainHeights[TEX_NAMES[0]] || dummyH };
    shader.uniforms.texRH = { value: terrainHeights[TEX_NAMES[1]] || dummyH };
    shader.uniforms.texGH = { value: terrainHeights[TEX_NAMES[2]] || dummyH };
    shader.uniforms.texBH = { value: terrainHeights[TEX_NAMES[3]] || dummyH };
    shader.uniforms.texScale = { value: 0.15 };
    shader.uniforms.heightScale = { value: (enhanced && zone.hasNormals) ? 0.04 : 0 };
    shader.uniforms.normalStrength = { value: (enhanced && zone.hasNormals) ? 1.0 : 0 };

    shader.vertexShader = shader.vertexShader.replace(
      'void main() {',
      'varying vec2 vSplatUv;\nvarying vec3 vWorldPos;\nvoid main() {'
    );
    shader.vertexShader = shader.vertexShader.replace(
      '#include <begin_vertex>',
      '#include <begin_vertex>\nvSplatUv = uv;\nvWorldPos = (modelMatrix * vec4(transformed, 1.0)).xyz;'
    );

    shader.fragmentShader = shader.fragmentShader.replace(
      'void main() {',
      SPLAT_UNIFORMS_GLSL + '\nvoid main() {'
    );
    shader.fragmentShader = shader.fragmentShader.replace(
      '#include <map_fragment>', SPLAT_DIFFUSE_GLSL
    );
    shader.fragmentShader = shader.fragmentShader.replace(
      '#include <normal_fragment_maps>', SPLAT_NORMAL_GLSL
    );
    splatShaders.push(shader);
  };
  mat.customProgramCacheKey = () => 'splatTerrain';
  return mat;
}

function buildTerrainMesh(tile, splatTex) {
  const { gridSize, tileSize } = tile;
  const initHeights = tile.heights;
  const geo = new THREE.PlaneGeometry(tileSize, tileSize, gridSize - 1, gridSize - 1);
  geo.rotateX(-Math.PI / 2);
  const pos = geo.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    const hi = Math.floor(i / gridSize) * gridSize + (i % gridSize);
    if (hi < initHeights.length) pos.setY(i, initHeights[hi]);
  }
  geo.computeVertexNormals();

  const [ox, oz] = tileOffset(tile.tile);
  const mat = splatTex
    ? makeSplatMaterial(splatTex)
    : new THREE.MeshStandardMaterial({ color: 0x5a8a4a, roughness: 0.9 });

  const mesh = new THREE.Mesh(geo, mat);
  mesh.receiveShadow = true;
  mesh.position.set(ox + tileSize / 2, 0, oz + tileSize / 2);
  return mesh;
}

// -- water --

function addWater(waterChunks, tileName) {
  const [tileOx, tileOz] = tileOffset(tileName);
  const bases = Object.values(tileBaseZ);
  const minBase = bases.length > 0 ? Math.min(...bases) : 42.86;
  const waterMat = new THREE.MeshStandardMaterial({
    color: 0x2060a0,
    transparent: true,
    opacity: 0.6,
    roughness: 0.05,
    metalness: 0.4,
    side: THREE.DoubleSide,
  });

  for (const w of waterChunks) {
    const waterH = w.h - minBase;
    if (waterH < -20 || waterH > 500) continue;

    const cx = tileOx + w.iy * CHUNK_SIZE;
    const cz = tileOz + w.ix * CHUNK_SIZE;

    const geo = new THREE.PlaneGeometry(CHUNK_SIZE, CHUNK_SIZE);
    geo.rotateX(-Math.PI / 2);
    const mesh = new THREE.Mesh(geo, waterMat);
    mesh.position.set(cx + CHUNK_SIZE / 2, waterH, cz + CHUNK_SIZE / 2);
    scene.add(mesh);
  }
}

// -- M2 models --

const modelCache = {};
const glbMeshes = [];

async function loadModelJson(name) {
  if (modelCache[name]) return modelCache[name];
  try {
    const resp = await fetch(`models/${name}.json`);
    if (!resp.ok) return null;
    const data = await resp.json();
    modelCache[name] = data;
    return data;
  } catch { return null; }
}

function buildM2Submeshes(modelData) {
  const pos = modelData.positions;
  const nrm = modelData.normals;
  const swappedPos = new Float32Array(pos.length);
  const swappedNrm = new Float32Array(nrm.length);
  for (let i = 0; i < pos.length; i += 3) {
    swappedPos[i] = pos[i];
    swappedPos[i + 1] = pos[i + 2];
    swappedPos[i + 2] = -pos[i + 1];
    swappedNrm[i] = nrm[i];
    swappedNrm[i + 1] = nrm[i + 2];
    swappedNrm[i + 2] = -nrm[i + 1];
  }

  const posAttr = new THREE.Float32BufferAttribute(swappedPos, 3);
  const nrmAttr = new THREE.Float32BufferAttribute(swappedNrm, 3);
  const uvAttr = new THREE.Float32BufferAttribute(new Float32Array(modelData.uvs), 2);
  const allIndices = modelData.indices;

  const subs = modelData.submeshes;
  if (!subs || subs.length === 0) {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", posAttr);
    geo.setAttribute("normal", nrmAttr);
    geo.setAttribute("uv", uvAttr);
    if (allIndices.length > 0) geo.setIndex(allIndices);
    geo.computeBoundingSphere();
    const fdid = modelData.texFdids?.length > 0 ? modelData.texFdids[0] : 0;
    return [{ geo, texFdid: fdid }];
  }

  return subs.map((sm) => {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", posAttr);
    geo.setAttribute("normal", nrmAttr);
    geo.setAttribute("uv", uvAttr);
    const smIdx = allIndices.slice(sm.startIndex, sm.startIndex + sm.indexCount);
    geo.setIndex(smIdx);
    geo.computeBoundingSphere();
    return { geo, texFdid: sm.texFdid };
  });
}

async function loadObjects() {
  for (const tileName of TILES) {
    try {
      const tDir = zone.terrainDir || "terrain";
      const resp = await fetch(`${tDir}/${tileName}_objects.json`);
      if (!resp.ok) continue;
      const data = await resp.json();
      await placeM2Objects(data.m2);
      if (data.wmo) await placeWMOObjects(data.wmo);
    } catch {}
  }
}

async function placeM2Objects(placements) {
  const grouped = {};
  for (const p of placements) {
    const name = FDID_TO_MODEL[p.fdid];
    if (!name) continue;
    if (!grouped[name]) grouped[name] = [];
    grouped[name].push(p);
  }

  for (const [name, instances] of Object.entries(grouped)) {
    const matrices = [];
    const dummy = new THREE.Object3D();
    const euler = new THREE.Euler();

    for (const p of instances) {
      const [lx, ly, lz] = mddfToViewer(p.pos[0], p.pos[1], p.pos[2]);
      dummy.position.set(lx, ly, lz);
      const rx = THREE.MathUtils.degToRad(p.rot[0] || 0);
      const ry = THREE.MathUtils.degToRad(p.rot[1] || 0);
      const rz = THREE.MathUtils.degToRad(p.rot[2] || 0);
      euler.set(-rz, -ry, -rx, "YZX");
      dummy.rotation.copy(euler);
      dummy.scale.setScalar(p.scale);
      dummy.updateMatrix();
      matrices.push(dummy.matrix.clone());
    }

    const modelData = await loadModelJson(name);
    if (!modelData || modelData.nVerts < 3) continue;
    if (!modelData.texFdids || modelData.texFdids.length === 0) continue;

    const submeshes = buildM2Submeshes(modelData);

    const isFoliage = FOLIAGE_MODELS.has(name);

    for (let si = 0; si < submeshes.length; si++) {
      const { geo, texFdid } = submeshes[si];
      if (!texFdid) continue;

      const mat = new THREE.MeshStandardMaterial({
        roughness: isFoliage ? 1.0 : 0.8,
        metalness: isFoliage ? 0 : undefined,
        side: THREE.DoubleSide,
        alphaTest: 0.3,
        alphaHash: true,
      });

      mat.map = loadM2Tex(texFdid);
      if (UPSCALED_FDIDS.has(texFdid)) m2SwapMats.push({ mat, fdid: texFdid });

      const instMesh = new THREE.InstancedMesh(geo, mat, instances.length);
      instMesh.castShadow = true;
      instMesh.receiveShadow = true;
      for (let i = 0; i < matrices.length; i++) {
        instMesh.setMatrixAt(i, matrices[i]);
      }
      instMesh.instanceMatrix.needsUpdate = true;
      scene.add(instMesh);
    }
  }
}

const FDID_TO_WMO = {
  106965: "farm", 106735: "duskwood_human_farm",
  110342: "animalden", 111538: "md_spidermine",
  108069: "duskworldtree", 106800: "duskwoodabandoned_human_farm",
  113303: "taurentent01", 110497: "md_mushroomden",
  108121: "elwynnwidebridge", 108104: "abbeygate01",
  108106: "abbeygate02", 106973: "humantwostory",
  106899: "barn", 106851: "goldshireinn",
  106848: "goldshireblacksmith", 106905: "silo",
  107037: "magetower", 107232: "stable",
  108143: "redridgedocks02", 110773: "md_goldmine_varianta",
  111333: "md_grogremound", 115717: "ao_bridgelong01",
  115719: "ao_bridgelong02", 115727: "ao_footbridge01",
  115777: "ancdrae_terrace", 115783: "ancdraehuta",
  115792: "ancdraepost", 115848: "nagrand_rockfloating_01",
  115850: "nagrand_rockfloating_02", 115852: "nagrand_rockfloating_waterfalls",
};

const wmoCache = {};

async function loadWmoJson(name) {
  if (wmoCache[name]) return wmoCache[name];
  try {
    const resp = await fetch(`wmo/${name}.json`);
    if (!resp.ok) return null;
    const data = await resp.json();
    wmoCache[name] = data;
    return data;
  } catch { return null; }
}

function buildWmoSubmeshes(modelData) {
  const pos = modelData.positions;
  const nrm = modelData.normals;
  const swappedPos = new Float32Array(pos.length);
  const swappedNrm = new Float32Array(nrm.length);
  for (let i = 0; i < pos.length; i += 3) {
    swappedPos[i] = pos[i];
    swappedPos[i + 1] = pos[i + 2];
    swappedPos[i + 2] = -pos[i + 1];
    swappedNrm[i] = nrm[i];
    swappedNrm[i + 1] = nrm[i + 2];
    swappedNrm[i + 2] = -nrm[i + 1];
  }

  const posAttr = new THREE.Float32BufferAttribute(swappedPos, 3);
  const nrmAttr = new THREE.Float32BufferAttribute(swappedNrm, 3);
  const uvAttr = new THREE.Float32BufferAttribute(new Float32Array(modelData.uvs), 2);
  const allIndices = modelData.indices;

  const subs = modelData.submeshes;
  if (!subs || subs.length === 0) return [];

  const merged = {};
  for (const sm of subs) {
    const key = sm.texFdid || 0;
    if (!merged[key]) merged[key] = [];
    merged[key].push(sm);
  }

  return Object.entries(merged).map(([fdid, sms]) => {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", posAttr);
    geo.setAttribute("normal", nrmAttr);
    geo.setAttribute("uv", uvAttr);
    const combined = [];
    for (const sm of sms) {
      combined.push(...allIndices.slice(sm.startIndex, sm.startIndex + sm.indexCount));
    }
    geo.setIndex(combined);
    geo.computeBoundingSphere();
    return { geo, texFdid: parseInt(fdid) };
  });
}

async function placeWMOObjects(placements) {
  for (const p of placements) {
    const name = FDID_TO_WMO[p.fdid];
    if (!name) continue;

    const data = await loadWmoJson(name);
    if (!data || data.nVerts < 3) continue;

    const submeshes = buildWmoSubmeshes(data);
    const [lx, ly, lz] = mddfToViewer(p.pos[0], p.pos[1], p.pos[2]);
    const group = new THREE.Group();
    group.position.set(lx, ly, lz);

    const wrx = THREE.MathUtils.degToRad(p.rot[0] || 0);
    const wry = THREE.MathUtils.degToRad(p.rot[1] || 0);
    const wrz = THREE.MathUtils.degToRad(p.rot[2] || 0);
    group.rotation.set(-wrz, -wry, -wrx, "YZX");

    for (const { geo, texFdid } of submeshes) {
      const mat = new THREE.MeshStandardMaterial({
        roughness: 0.85,
        side: THREE.DoubleSide,
      });
      if (texFdid) {
        mat.map = loadWmoTex(texFdid);
        if (UPSCALED_WMO.has(texFdid)) wmoSwapMats.push({ mat, fdid: texFdid });
      } else {
        mat.color.set(0x8a7a6a);
      }
      const wmesh = new THREE.Mesh(geo, mat);
      wmesh.castShadow = true;
      wmesh.receiveShadow = true;
      group.add(wmesh);
    }
    scene.add(group);
  }
}

// -- music --

const MUSIC_TRACKS = [
  "music/dayforest01.mp3",
  "music/dayforest02.mp3",
  "music/dayforest03.mp3",
  "music/nightforest01.mp3",
];

const musicState = { playing: false, trackIdx: 0, volume: 0.4, fading: false };
const musicAudio = new Audio();
musicAudio.volume = 0;

function playMusic() {
  musicAudio.src = MUSIC_TRACKS[musicState.trackIdx];
  musicAudio.play().catch(() => {});
  fadeVolume(musicAudio, 0, musicState.volume, 2000);
  musicState.playing = true;
  updateMusicUI();
}

function stopMusic() {
  fadeVolume(musicAudio, musicAudio.volume, 0, 800, () => {
    musicAudio.pause();
    musicAudio.currentTime = 0;
  });
  musicState.playing = false;
  updateMusicUI();
}

function toggleMusic() {
  musicState.playing ? stopMusic() : playMusic();
}

function fadeVolume(audio, from, to, ms, onDone) {
  if (musicState.fading) return;
  musicState.fading = true;
  const steps = 30;
  const dt = ms / steps;
  let i = 0;
  const iv = setInterval(() => {
    i++;
    audio.volume = from + (to - from) * (i / steps);
    if (i >= steps) {
      clearInterval(iv);
      audio.volume = to;
      musicState.fading = false;
      onDone?.();
    }
  }, dt);
}

function nextTrack() {
  musicState.trackIdx = (musicState.trackIdx + 1) % MUSIC_TRACKS.length;
  if (musicState.playing) {
    fadeVolume(musicAudio, musicAudio.volume, 0, 1500, () => {
      musicAudio.src = MUSIC_TRACKS[musicState.trackIdx];
      musicAudio.play().catch(() => {});
      fadeVolume(musicAudio, 0, musicState.volume, 2000);
    });
  }
}

musicAudio.addEventListener("ended", nextTrack);

function updateMusicUI() {
  const btn = document.getElementById("btn-music");
  const iconOn = document.getElementById("music-icon-on");
  const iconOff = document.getElementById("music-icon-off");
  btn?.classList.toggle("playing", musicState.playing);
  if (iconOn) iconOn.style.display = musicState.playing ? "" : "none";
  if (iconOff) iconOff.style.display = musicState.playing ? "none" : "";
}

document.getElementById("btn-music")?.addEventListener("click", toggleMusic);


function applyHeights(geo, heights, gridSize) {
  const pos = geo.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    const hi = Math.floor(i / gridSize) * gridSize + (i % gridSize);
    if (hi < heights.length) pos.setY(i, heights[hi]);
  }
  pos.needsUpdate = true;
  geo.computeVertexNormals();
}

let texToggling = false;

function toggleTextures() {
  if (texToggling) return;
  texToggling = true;

  const overlay = document.getElementById("tex-transition");
  const nextMode = (texModeIdx + 1) % TEX_MODES.length;
  const label = document.getElementById("spinner-label");
  if (label) label.textContent = nextMode > 0 ? "Enhancing..." : "Restoring...";
  overlay.classList.add("active");

  setTimeout(() => {
    texModeIdx = nextMode;
    const mode = TEX_MODES[texModeIdx];
    const enhanced = texModeIdx > 0;
    const texSet = terrainTextures();
    for (const s of splatShaders) {
      s.uniforms.texBase.value = texSet[TEX_NAMES[0]];
      s.uniforms.texR.value = texSet[TEX_NAMES[1]];
      s.uniforms.texG.value = texSet[TEX_NAMES[2]];
      s.uniforms.texB.value = texSet[TEX_NAMES[3]];
      s.uniforms.heightScale.value = enhanced ? 0.04 : 0;
      s.uniforms.normalStrength.value = enhanced ? 1.0 : 0;
    }
    for (const { mat, fdid } of m2SwapMats) {
      const pair = m2TexPairs[fdid];
      if (pair) mat.map = pair[mode];
    }
    for (const { mat, fdid } of wmoSwapMats) {
      const pair = wmoTexPairs[fdid];
      if (pair) mat.map = pair[mode];
    }
    for (const m of nextGenMeshes) m.visible = enhanced;
    for (const m of glbMeshes) m.visible = enhanced;
    for (const m of grassMeshes) m.visible = enhanced;
    updateHUD();

    setTimeout(() => {
      overlay.classList.remove("active");
      texToggling = false;
    }, 350);
  }, 80);
}

const moveState = { forward: false, backward: false, left: false, right: false, up: false };

document.addEventListener("keydown", (e) => {
  if (e.code === "KeyW" || e.code === "ArrowUp") moveState.forward = true;
  if (e.code === "KeyS" || e.code === "ArrowDown") moveState.backward = true;
  if (e.code === "KeyA" || e.code === "ArrowLeft") moveState.left = true;
  if (e.code === "KeyD" || e.code === "ArrowRight") moveState.right = true;
  if (e.code === "Space") { e.preventDefault(); moveState.up = true; }
  if (e.code === "KeyT") toggleTextures();
  if (e.code === "KeyM") toggleMusic();
});
document.addEventListener("keyup", (e) => {
  if (e.code === "KeyW" || e.code === "ArrowUp") moveState.forward = false;
  if (e.code === "KeyS" || e.code === "ArrowDown") moveState.backward = false;
  if (e.code === "KeyA" || e.code === "ArrowLeft") moveState.left = false;
  if (e.code === "KeyD" || e.code === "ArrowRight") moveState.right = false;
  if (e.code === "Space") moveState.up = false;
});

const btnTexOrig = document.getElementById("btn-tex-orig");
const btnTexUp = document.getElementById("btn-tex-up");

function syncHeaderToggle() {
  btnTexOrig?.classList.toggle("active", texModeIdx === 0);
  btnTexUp?.classList.toggle("active", texModeIdx > 0);
}

btnTexOrig?.addEventListener("click", () => { if (texModeIdx !== 0) toggleTextures(); });
btnTexUp?.addEventListener("click", () => { if (texModeIdx !== 1) toggleTextures(); });

function updateHUD() {
  syncHeaderToggle();
}

addEventListener("resize", () => {
  camera.aspect = innerWidth / (innerHeight - HEADER_H);
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight - HEADER_H);
});

// -- render loop --

const clock = new THREE.Clock();
const _fwd = new THREE.Vector3();
const _right = new THREE.Vector3();
const _move = new THREE.Vector3();

function animate() {
  requestAnimationFrame(animate);
  const dt = clock.getDelta();
  grassWindUni.uTime.value += dt;

  _move.set(0, 0, 0);
  camera.getWorldDirection(_fwd);
  _fwd.y = 0;
  _fwd.normalize();
  _right.crossVectors(_fwd, camera.up).normalize();
  if (moveState.forward) _move.add(_fwd);
  if (moveState.backward) _move.sub(_fwd);
  if (moveState.right) _move.add(_right);
  if (moveState.left) _move.sub(_right);
  if (moveState.up) _move.y += 1;
  if (_move.lengthSq() > 0) {
    _move.normalize().multiplyScalar(80 * dt);
    camera.position.add(_move);
    orbitControls.target.add(_move);
  }

  orbitControls.update();
  renderer.render(scene, camera);
}

// -- procedural vegetation scatter --

const nextGenMeshes = [];
const grassMeshes = [];
const grassWindUni = { uTime: { value: 0 } };

const SCATTER_MODELS = {
  grass: [
    { name: "elwynnbush09", density: 0.025, baseScale: 0.5 },
    { name: "kalidarbush04", density: 0.025, baseScale: 0.4 },
    { name: "wetlandgrass02", density: 0.04, baseScale: 0.35 },
  ],
  rock: [
    { name: "elwynnrock1", density: 0.012, baseScale: 0.35 },
    { name: "elwynnrock2", density: 0.012, baseScale: 0.3 },
  ],
  dirt: [
    { name: "hyjalbushburnt01", density: 0.015, baseScale: 0.35 },
  ],
};

function readSplatmapData(tileName) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const cvs = document.createElement("canvas");
      cvs.width = img.width; cvs.height = img.height;
      const ctx = cvs.getContext("2d");
      ctx.drawImage(img, 0, 0);
      resolve(ctx.getImageData(0, 0, img.width, img.height));
    };
    img.onerror = () => resolve(null);
    const tDir = zone.terrainDir || "terrain";
    img.src = `${tDir}/${tileName}_splatmap.webp`;
  });
}

function sampleSplat(imgData, u, v) {
  const x = Math.min(Math.floor(u * imgData.width), imgData.width - 1);
  const y = Math.min(Math.floor(v * imgData.height), imgData.height - 1);
  const i = (y * imgData.width + x) * 4;
  return { r: imgData.data[i] / 255, g: imgData.data[i + 1] / 255, b: imgData.data[i + 2] / 255 };
}

function tileHeightAt(tile, fx, fz) {
  const { gridSize, heights } = tile;
  const gx = Math.min(Math.floor(fx * (gridSize - 1)), gridSize - 2);
  const gz = Math.min(Math.floor(fz * (gridSize - 1)), gridSize - 2);
  const tx = fx * (gridSize - 1) - gx;
  const tz = fz * (gridSize - 1) - gz;
  const h00 = heights[gz * gridSize + gx] || 0;
  const h10 = heights[gz * gridSize + gx + 1] || 0;
  const h01 = heights[(gz + 1) * gridSize + gx] || 0;
  const h11 = heights[(gz + 1) * gridSize + gx + 1] || 0;
  return h00 * (1 - tx) * (1 - tz) + h10 * tx * (1 - tz) + h01 * (1 - tx) * tz + h11 * tx * tz;
}

function pickScatterZone(splat) {
  const grassW = Math.max(0, 1 - splat.r - splat.g - splat.b);
  if (grassW > 0.5) return "grass";
  if (splat.g > 0.4) return "rock";
  if (splat.r > 0.4) return "dirt";
  return null;
}

async function scatterVegetation() {
  const spacing = 6;
  const allScatter = {};

  for (const tileName of TILES) {
    const tile = terrainTiles[tileName];
    if (!tile) continue;
    const splatImg = await readSplatmapData(tileName);
    if (!splatImg) continue;

    const [ox, oz] = tileOffset(tileName);
    const { tileSize } = tile;

    for (let gx = 0; gx < tileSize; gx += spacing) {
      for (let gz = 0; gz < tileSize; gz += spacing) {
        const jx = gx + (Math.random() - 0.5) * spacing * 0.8;
        const jz = gz + (Math.random() - 0.5) * spacing * 0.8;
        const fu = Math.max(0, Math.min(jx / tileSize, 1));
        const fv = Math.max(0, Math.min(jz / tileSize, 1));

        const splat = sampleSplat(splatImg, fu, fv);
        const zone = pickScatterZone(splat);
        if (!zone) continue;

        const models = SCATTER_MODELS[zone];
        const model = models[Math.floor(Math.random() * models.length)];
        if (Math.random() > model.density) continue;

        const h = tileHeightAt(tile, fu, fv);

        if (!allScatter[model.name]) allScatter[model.name] = [];
        allScatter[model.name].push({
          x: ox + jx, y: h, z: oz + jz,
          rot: Math.random() * Math.PI * 2,
          scale: model.baseScale * (0.8 + Math.random() * 0.4),
        });
      }
    }
  }

  const dummy = new THREE.Object3D();
  for (const [name, instances] of Object.entries(allScatter)) {
    const data = await loadModelJson(name);
    if (!data || data.nVerts < 3) continue;
    const submeshes = buildM2Submeshes(data);

    const matrices = instances.map(inst => {
      dummy.position.set(inst.x, inst.y, inst.z);
      dummy.rotation.set(0, inst.rot, 0);
      dummy.scale.setScalar(inst.scale);
      dummy.updateMatrix();
      return dummy.matrix.clone();
    });

    for (const { geo, texFdid } of submeshes) {
      if (!texFdid) continue;
      const mat = new THREE.MeshStandardMaterial({
        roughness: 0.8, side: THREE.DoubleSide, alphaTest: 0.3, alphaHash: true,
      });
      mat.map = loadM2Tex(texFdid);
      const instMesh = new THREE.InstancedMesh(geo, mat, instances.length);
      instMesh.castShadow = true;
      instMesh.receiveShadow = true;
      instMesh.visible = texModeIdx > 0;
      for (let i = 0; i < matrices.length; i++) instMesh.setMatrixAt(i, matrices[i]);
      instMesh.instanceMatrix.needsUpdate = true;
      nextGenMeshes.push(instMesh);
      scene.add(instMesh);
    }
  }
}

// -- volumetric grass (shell texturing) --

const SHELL_COUNT = 14;
const SHELL_HEIGHT = 1.4;
const SHELL_NOISE_SCALE = 0.25;

function makeGrassNoiseTex(size = 256) {
  const c = document.createElement("canvas");
  c.width = c.height = size;
  const ctx = c.getContext("2d");

  ctx.fillStyle = "black";
  ctx.fillRect(0, 0, size, size);
  const strandCount = size * size * 0.12;
  for (let i = 0; i < strandCount; i++) {
    const x = Math.random() * size;
    const y = Math.random() * size;
    const r = 0.4 + Math.random() * 1.3;
    const h = 0.08 + Math.random() * 0.92;
    const g = Math.floor(h * 255);
    ctx.fillStyle = `rgb(${g},${g},${g})`;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();
  }
  const strandData = ctx.getImageData(0, 0, size, size);

  ctx.fillStyle = "black";
  ctx.fillRect(0, 0, size, size);
  const clumpCount = Math.floor(size * size * 0.004);
  for (let i = 0; i < clumpCount; i++) {
    const x = Math.random() * size;
    const y = Math.random() * size;
    const r = 8 + Math.random() * 24;
    const grad = ctx.createRadialGradient(x, y, 0, x, y, r);
    grad.addColorStop(0, "white");
    grad.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();
  }
  const clumpData = ctx.getImageData(0, 0, size, size);

  const merged = ctx.createImageData(size, size);
  for (let i = 0; i < merged.data.length; i += 4) {
    merged.data[i] = strandData.data[i];
    merged.data[i + 1] = clumpData.data[i];
    merged.data[i + 2] = 0;
    merged.data[i + 3] = 255;
  }
  ctx.putImageData(merged, 0, 0);

  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.minFilter = THREE.NearestFilter;
  tex.magFilter = THREE.NearestFilter;
  return tex;
}

const SHELL_VERT_PREAMBLE = `
uniform float shellOff;
uniform float shellLevel;
uniform float uTime;
varying vec2 vShellSplatUv;
varying vec3 vShellWPos;
`;

const SHELL_VERT_BODY = `#include <begin_vertex>
  vShellSplatUv = uv;
  vec3 wBase = (modelMatrix * vec4(position, 1.0)).xyz;
  transformed += normal * shellOff;
  vShellWPos = (modelMatrix * vec4(transformed, 1.0)).xyz;
  float wStr = shellLevel * shellLevel;
  float wPhase = wBase.x * 0.06 + wBase.z * 0.08 + uTime * 1.2;
  float wPhase2 = wBase.x * 0.04 - wBase.z * 0.05 + uTime * 1.8;
  transformed.x += (sin(wPhase) * 0.35 + sin(wPhase2) * 0.15) * wStr;
  transformed.z += cos(wPhase * 0.7 + 1.5) * 0.22 * wStr;`;

const SHELL_FRAG_PREAMBLE = `
uniform sampler2D grassNoise;
uniform sampler2D shellSplat;
uniform sampler2D terrainGrassTex;
uniform float shellLevel;
uniform float noiseScale;
uniform float texScale;
varying vec2 vShellSplatUv;
varying vec3 vShellWPos;
`;

const SHELL_FRAG_DIFFUSE = `{
  vec4 splat = texture2D(shellSplat, vShellSplatUv);
  float grassW = max(0.0, 1.0 - splat.r - splat.g - splat.b);
  if (grassW < 0.2) discard;

  vec2 wUv = vShellWPos.xz * noiseScale;
  float strandH = texture2D(grassNoise, wUv).r;
  float clump = texture2D(grassNoise, wUv * 0.15).g;
  strandH *= smoothstep(0.1, 0.5, clump);

  float heightMod = smoothstep(0.2, 0.8, grassW);
  float threshold = shellLevel / max(heightMod, 0.01);
  if (strandH < threshold) discard;

  vec3 baseCol = vec3(0.05, 0.09, 0.02);
  vec3 midCol  = vec3(0.20, 0.30, 0.09);
  vec3 tipCol  = vec3(0.38, 0.46, 0.15);
  float sl = shellLevel;
  vec3 grassCol = sl < 0.5
    ? mix(baseCol, midCol, sl * 2.0)
    : mix(midCol, tipCol, (sl - 0.5) * 2.0);
  grassCol += strandH * vec3(0.06, 0.05, 0.01);

  vec3 groundCol = texture2D(terrainGrassTex, vShellWPos.xz * texScale).rgb;
  float ao = 0.35 + 0.65 * pow(shellLevel, 0.6);
  grassCol = mix(groundCol * ao, grassCol, shellLevel);

  diffuseColor = vec4(grassCol, 1.0);
}`;

function makeShellMat(shellIdx, noiseTex, splatTex) {
  const level = shellIdx / (SHELL_COUNT - 1);
  const offset = SHELL_HEIGHT * level;
  const mat = new THREE.MeshStandardMaterial({
    roughness: 0.88,
    metalness: 0.0,
    alphaTest: 0.01,
  });
  mat.onBeforeCompile = (shader) => {
    shader.uniforms.grassNoise = { value: noiseTex };
    shader.uniforms.shellSplat = { value: splatTex };
    shader.uniforms.terrainGrassTex = { value: terrainTexSets.v2[TEX_NAMES[0]] };
    shader.uniforms.shellLevel = { value: level };
    shader.uniforms.shellOff = { value: offset };
    shader.uniforms.uTime = grassWindUni.uTime;
    shader.uniforms.noiseScale = { value: SHELL_NOISE_SCALE };
    shader.uniforms.texScale = { value: 0.15 };
    shader.vertexShader = shader.vertexShader.replace(
      "void main() {", SHELL_VERT_PREAMBLE + "\nvoid main() {"
    );
    shader.vertexShader = shader.vertexShader.replace(
      "#include <begin_vertex>", SHELL_VERT_BODY
    );
    shader.fragmentShader = shader.fragmentShader.replace(
      "void main() {", SHELL_FRAG_PREAMBLE + "\nvoid main() {"
    );
    shader.fragmentShader = shader.fragmentShader.replace(
      "#include <map_fragment>", SHELL_FRAG_DIFFUSE
    );
  };
  mat.customProgramCacheKey = () => `grassShell_${shellIdx}`;
  return mat;
}

function createGrassShells() {
  const noiseTex = makeGrassNoiseTex();
  for (const { mesh, splatTex } of terrainMeshes) {
    if (!splatTex) continue;
    for (let i = 1; i < SHELL_COUNT; i++) {
      const shell = new THREE.Mesh(mesh.geometry, makeShellMat(i, noiseTex, splatTex));
      shell.position.copy(mesh.position);
      shell.receiveShadow = true;
      shell.visible = texModeIdx > 0;
      grassMeshes.push(shell);
      scene.add(shell);
    }
  }
}

function precompileShaders() {
  const hidden = [...grassMeshes, ...nextGenMeshes, ...glbMeshes].filter(m => !m.visible);
  for (const m of hidden) m.visible = true;
  renderer.compile(scene, camera);
  for (const m of hidden) m.visible = false;
}

loadTerrain().then(() => {
  createGrassShells();
  return loadObjects();
}).then(() => scatterVegetation()).then(() => precompileShaders());
updateHUD();

const onboard = document.getElementById("onboarding");
if (onboard) {
  const dismiss = () => {
    onboard.classList.add("hidden");
    setTimeout(() => onboard.remove(), 600);
  };
  setTimeout(dismiss, 8000);
  renderer.domElement.addEventListener("pointerdown", dismiss, { once: true });
}

animate();
