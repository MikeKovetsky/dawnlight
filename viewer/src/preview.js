import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const KNOWN_MODELS = [
  "orcmalewarriorheavy",
  "elwynntreecanopy01", "elwynntreecanopy02", "elwynntreecanopy03", "elwynntreecanopy04",
  "elwynntreemid01", "canopylesstree01",
  "duskwoodtreecanopy01", "duskwoodtreecanopy02", "duskwoodtree06", "duskwoodtree07",
  "duskwoodtreespookless01", "duskwoodtreespookless02", "duskwoodbrowntree",
  "elwynnbush09", "kalidarbush04",
  "duskwoodbush03", "duskwoodbush07", "duskwoodspookybush02", "duskwoodspookybush04",
  "hyjalbushburnt01",
  "elwynnwoodfence01", "elwynnwoodpost01", "elwynnstonefence", "elwynnstonefencepost",
  "elwynncliffrock01", "elwynncliffrock02", "elwynnrock1", "elwynnrock2",
  "barrel01", "crate01", "jar01", "jar02",
  "lamppost", "duskwoodlamppost", "freestandingtorch01", "generaltorch01",
  "gatepost", "gatesegment01", "gatesegment02",
  "flagpole01", "gryphonroost01", "stormwindgypsywagon01", "humantentlarge",
  "stormwindwoodendummy01", "harness",
  "pumpkinpatch01", "duskwoodmushroom01", "duskwoodstraw", "duskwoodfencetop",
  "duskwoodruinsbrick", "elwynnseaweed01",
  "swampofsorrowlilypad01", "swampofsorrowlilypad02", "swampplant04", "swampplant05",
  "westfallbarrel01", "westfallfence", "westfallfenceend", "westfallfencepost",
  "bird01", "wetlandgrass02",
];

const UPSCALED_FDIDS = new Set([
  125375, 125373,
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

const texLoader = new THREE.TextureLoader();
const gltfLoader = new GLTFLoader();

const GLB_MODELS = new Set(["orcmalewarriorheavy"]);

function configTex(tex) {
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.flipY = false;
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.minFilter = THREE.LinearMipmapLinearFilter;
  tex.magFilter = THREE.LinearFilter;
  return tex;
}

function createViewport(container) {
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.3;
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x2a2a3e);

  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 2000);
  camera.position.set(40, 30, 60);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;

  scene.add(new THREE.DirectionalLight(0xffe8c0, 2.5)).position.set(400, 500, 300);
  scene.add(new THREE.HemisphereLight(0x87ceeb, 0x4a7a3a, 0.8));
  scene.add(new THREE.AmbientLight(0xfff5e6, 0.3));

  const grid = new THREE.GridHelper(200, 40, 0x3a3a5e, 0x252540);
  scene.add(grid);

  return { renderer, scene, camera, controls, grid };
}

const vpLeft = createViewport(document.getElementById("vp-left"));
const vpMid = createViewport(document.getElementById("vp-mid"));
const vpRight = createViewport(document.getElementById("vp-right"));
const allVps = [
  [vpLeft, "vp-left"], [vpMid, "vp-mid"], [vpRight, "vp-right"],
];

function resize() {
  for (const [vp, id] of allVps) {
    const el = document.getElementById(id);
    const w = el.clientWidth, h = el.clientHeight;
    vp.renderer.setSize(w, h);
    vp.camera.aspect = w / h;
    vp.camera.updateProjectionMatrix();
  }
}
addEventListener("resize", resize);
resize();

function buildM2Submeshes(data) {
  const pos = data.positions, nrm = data.normals;
  const swP = new Float32Array(pos.length), swN = new Float32Array(nrm.length);
  for (let i = 0; i < pos.length; i += 3) {
    swP[i] = pos[i]; swP[i+1] = pos[i+2]; swP[i+2] = -pos[i+1];
    swN[i] = nrm[i]; swN[i+1] = nrm[i+2]; swN[i+2] = -nrm[i+1];
  }
  const pA = new THREE.Float32BufferAttribute(swP, 3);
  const nA = new THREE.Float32BufferAttribute(swN, 3);
  const uA = new THREE.Float32BufferAttribute(new Float32Array(data.uvs), 2);
  const idx = data.indices;
  const subs = data.submeshes;
  if (!subs || !subs.length) {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", pA); g.setAttribute("normal", nA); g.setAttribute("uv", uA);
    if (idx.length) g.setIndex(idx);
    g.computeBoundingSphere();
    return [{ geo: g, texFdid: data.texFdids?.[0] || 0 }];
  }
  return subs.map((sm) => {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", pA); g.setAttribute("normal", nA); g.setAttribute("uv", uA);
    g.setIndex(idx.slice(sm.startIndex, sm.startIndex + sm.indexCount));
    g.computeBoundingSphere();
    return { geo: g, texFdid: sm.texFdid };
  });
}

let leftGroup = null, midGroup = null, rightGroup = null, currentModel = "";

const selectEl = document.getElementById("model-select");
for (const name of KNOWN_MODELS) {
  const opt = document.createElement("option");
  opt.value = name; opt.textContent = name;
  selectEl.appendChild(opt);
}
selectEl.addEventListener("change", () => loadModel(selectEl.value));

document.getElementById("btn-prev").addEventListener("click", () => {
  const idx = KNOWN_MODELS.indexOf(currentModel);
  loadModel(KNOWN_MODELS[(idx - 1 + KNOWN_MODELS.length) % KNOWN_MODELS.length]);
});
document.getElementById("btn-next").addEventListener("click", () => {
  const idx = KNOWN_MODELS.indexOf(currentModel);
  loadModel(KNOWN_MODELS[(idx + 1) % KNOWN_MODELS.length]);
});

function clearGroup(scene, group) {
  if (!group) return;
  group.traverse((o) => {
    if (o.isMesh) { o.geometry?.dispose(); o.material?.dispose?.(); }
  });
  scene.remove(group);
}

function countGeo(group) {
  let v = 0, t = 0;
  group.traverse((o) => {
    if (o.isMesh && o.geometry) {
      v += o.geometry.attributes.position?.count || 0;
      t += o.geometry.index ? o.geometry.index.count / 3 : (o.geometry.attributes.position?.count || 0) / 3;
    }
  });
  return { verts: Math.round(v), tris: Math.round(t) };
}

function fitCamera(vp, group) {
  const box = new THREE.Box3().setFromObject(group);
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());
  const dist = Math.max(size.x, size.y, size.z) * 1.5;
  vp.controls.target.copy(center);
  vp.camera.position.set(center.x + dist * 0.6, center.y + dist * 0.4, center.z + dist * 0.8);
  vp.controls.update();
}

function loadM2Into(vp, name, texPath, labelEl, statsEl) {
  return new Promise(async (resolve) => {
    const group = new THREE.Group();
    labelEl.textContent = "Loading...";
    statsEl.textContent = "";
    try {
      const resp = await fetch(`models/${name}.json`);
      if (!resp.ok) throw new Error("not found");
      const data = await resp.json();
      const submeshes = buildM2Submeshes(data);
      for (const { geo, texFdid } of submeshes) {
        const mat = new THREE.MeshStandardMaterial({
          roughness: 1.0, metalness: 0, side: THREE.DoubleSide,
          alphaTest: 0.3, alphaHash: true,
        });
        if (texFdid) {
          mat.map = configTex(texLoader.load(texPath(texFdid)));
        }
        group.add(new THREE.Mesh(geo, mat));
      }
      vp.scene.add(group);
      fitCamera(vp, group);
      const st = countGeo(group);
      labelEl.textContent = `${st.verts.toLocaleString()} verts`;
      statsEl.textContent = `Verts: ${st.verts.toLocaleString()}\nTris: ${st.tris.toLocaleString()}\nSubmeshes: ${submeshes.length}`;
    } catch {
      labelEl.textContent = "Not found";
    }
    resolve(group);
  });
}

function loadGlbInto(vp, name, refGroup, labelEl, statsEl) {
  return new Promise((resolve) => {
    labelEl.textContent = "Loading GLB...";
    statsEl.textContent = "";
    gltfLoader.load(`models/glb/${name}_up.glb`, (gltf) => {
      const group = new THREE.Group();
      const inner = gltf.scene;
      group.add(inner);

      inner.updateMatrixWorld(true);
      const box = new THREE.Box3().setFromObject(group);
      const size = box.getSize(new THREE.Vector3());

      if (refGroup?.children.length) {
        const refBox = new THREE.Box3().setFromObject(refGroup);
        const refSize = refBox.getSize(new THREE.Vector3());
        const scl = Math.max(refSize.x, refSize.y, refSize.z) / Math.max(size.x, size.y, size.z);
        group.scale.setScalar(scl);
      }

      vp.scene.add(group);
      fitCamera(vp, group);
      const st = countGeo(group);
      labelEl.textContent = `${st.verts.toLocaleString()} verts`;
      statsEl.textContent = `Verts: ${st.verts.toLocaleString()}\nTris: ${st.tris.toLocaleString()}\nMethod: Trellis 2 upscale`;
      resolve(group);
    }, undefined, () => {
      labelEl.textContent = "GLB not found";
      resolve(new THREE.Group());
    });
  });
}

async function loadModel(name) {
  currentModel = name;
  selectEl.value = name;
  history.replaceState(null, "", `?model=${name}`);

  clearGroup(vpLeft.scene, leftGroup);
  vpLeft.scene.add(vpLeft.grid);
  clearGroup(vpMid.scene, midGroup);
  vpMid.scene.add(vpMid.grid);
  clearGroup(vpRight.scene, rightGroup);
  vpRight.scene.add(vpRight.grid);

  const origTex = (fdid) => {
    const origPath = `models/originals/tex_${fdid}.webp`;
    const fallback = `models/tex_${fdid}.webp`;
    return UPSCALED_FDIDS.has(fdid) ? origPath : fallback;
  };

  const newTex = (fdid) => {
    return UPSCALED_FDIDS.has(fdid)
      ? `models/creative_test/tex_${fdid}_nanobanana.webp`
      : `models/tex_${fdid}.webp`;
  };

  leftGroup = await loadM2Into(vpLeft, name, origTex,
    document.getElementById("stats-left-label"),
    document.getElementById("stats-left"));

  midGroup = await loadM2Into(vpMid, name, newTex,
    document.getElementById("stats-mid-label"),
    document.getElementById("stats-mid"));

  if (GLB_MODELS.has(name)) {
    document.getElementById("vp-right").style.display = "";
    rightGroup = await loadGlbInto(vpRight, name, leftGroup,
      document.getElementById("stats-right-label"),
      document.getElementById("stats-right"));
  } else {
    document.getElementById("vp-right").style.display = "none";
    rightGroup = null;
  }

  resize();
}

function syncCamera(src, dst, dstGroup) {
  if (!dstGroup?.children.length) return;
  const off = src.camera.position.clone().sub(src.controls.target);
  const rc = new THREE.Vector3();
  new THREE.Box3().setFromObject(dstGroup).getCenter(rc);
  dst.controls.target.copy(rc);
  dst.camera.position.copy(rc).add(off);
  dst.camera.lookAt(rc);
  dst.controls.update();
}

function animate() {
  requestAnimationFrame(animate);
  vpLeft.controls.update();
  syncCamera(vpLeft, vpMid, midGroup);
  vpRight.controls.update();
  vpLeft.renderer.render(vpLeft.scene, vpLeft.camera);
  vpMid.renderer.render(vpMid.scene, vpMid.camera);
  vpRight.renderer.render(vpRight.scene, vpRight.camera);
}

animate();

const params = new URLSearchParams(location.search);
loadModel(params.get("model") || KNOWN_MODELS[0]);
