import * as THREE from "three";
import { GLTFLoader } from "./vendor/GLTFLoader.r160.js";

const API_HOST = window.location.hostname || "localhost";
const URL_PARAMS = new URLSearchParams(window.location.search);
const API_PORT = URL_PARAMS.get("apiPort");
const API_BASE = URL_PARAMS.get("apiBase") || (
  API_PORT
    ? `http://${API_HOST}:${API_PORT}/api/v1/simple-injection`
    : window.location.port === "3010"
      ? `http://${API_HOST}:8010/api/v1/simple-injection`
      : `${window.location.origin}/api/v1/simple-injection`
);
const IS_KO = document.documentElement.lang.toLowerCase().startsWith("ko");
const TEXT = {
  loading: IS_KO ? "예측 중..." : "Predicting...",
  apiConnected: IS_KO ? "API: 연결됨" : "API: connected",
  apiOffline: IS_KO ? "API: 연결 안 됨" : "API: offline",
  apiStart: IS_KO
    ? "Simple Injection API를 먼저 실행해 주세요."
    : "Start the Simple Injection API before predicting.",
  customGeometry: IS_KO ? "사용자 입력 (형상)" : "User input (geometry)",
  customProcess: IS_KO ? "사용자 입력 (공정)" : "User input (process)",
  fixRequired: IS_KO ? "수정 필요" : "Fix required",
  warning: IS_KO ? "경고" : "warning",
  warnings: IS_KO ? "경고" : "warnings",
  error: IS_KO ? "오류" : "error",
  emptyCurve: IS_KO ? "압력 곡선이 여기에 표시됩니다." : "Pressure curve will appear here.",
  timeAxis: IS_KO ? "시간 (s)" : "Time (s)",
  pressureAxis: IS_KO ? "Sprue pressure (MPa)" : "Sprue pressure (MPa)",
  geometry: IS_KO ? "형상" : "Geometry",
  process: IS_KO ? "공정" : "Process",
  invalidInput: IS_KO ? "물리적으로 유효하지 않은 입력 조건이 있습니다." : "Input contains physically invalid conditions.",
  fillingNoSpatial: IS_KO
    ? "이 값은 Moldex3D histogram export 요약입니다. 메쉬 좌표가 없어 실제 contour 위치 정보는 포함하지 않습니다."
    : "This is a Moldex3D histogram export summary. Mesh coordinates are not included, so it is not a spatial contour field.",
  exactMode: IS_KO ? "STEP 형상" : "STEP geometry",
  parametricMode: IS_KO ? "Parametric preview" : "Parametric preview",
  exactUnavailable: IS_KO ? "선택한 DOE의 STEP GLB가 없어 parametric preview로 표시합니다." : "No STEP GLB is available for this DOE; showing the parametric preview.",
  customParametric: IS_KO ? "사용자 입력 형상은 parametric preview로 표시합니다." : "User-edited geometry is shown with the parametric preview.",
  doeParametric: IS_KO ? "DOE 치수 기반 parametric preview" : "Parametric preview from DOE dimensions",
};
const MODEL_LABELS_KO = {
  "Sprue pressure - ExtraTrees + PCA": "Sprue Pressure - ExtraTrees + PCA",
  "Sprue pressure - HistGradientBoosting + PCA": "Sprue Pressure - HistGradientBoosting + PCA",
  "Sprue pressure - GointMLP-style NN": "Sprue Pressure - GointMLP 스타일 신경망",
};
const NOTE_LABELS_KO = {
  "Current model is trained on 30 of the planned 300 Moldex3D runs.": "현재 모델은 계획된 300개 Moldex3D 해석 중 30개 결과로 학습된 초기 버전입니다.",
  "Current model is trained on the full 300 planned Moldex3D runs.": "현재 모델은 계획된 300개 Moldex3D 해석 전체 결과로 학습되었습니다.",
  "Use the ExtraTrees surrogate as the practical default until more geometry results are available.": "추가 형상 결과가 쌓이기 전까지는 ExtraTrees surrogate를 기본 모델로 사용하는 것을 권장합니다.",
  "Use the classical surrogate as the practical default for this Simple Injection DOE set.": "현재 Simple Injection DOE set에서는 classical surrogate를 기본 모델로 사용하는 것을 권장합니다.",
  "The GointMLP-style model is currently a deep-learning baseline and is less stable with 30 samples.": "GointMLP 스타일 모델은 현재 deep-learning baseline이며, 30개 샘플 기준으로는 안정성이 낮습니다.",
  "The GointMLP-style model is a deep-learning baseline and is less stable than the classical surrogate on this DOE set.": "GointMLP 스타일 모델은 deep-learning baseline이며, 현재 DOE set에서는 classical surrogate보다 안정성이 낮습니다.",
};

const apiStatus = document.querySelector("#api-status");
const form = document.querySelector("#prediction-form");
const modelSelect = document.querySelector("#model-select");
const geometrySelect = document.querySelector("#geometry-select");
const processSelect = document.querySelector("#process-select");
const emptyState = document.querySelector("#empty-state");
const resultPanel = document.querySelector("#result");
const errorPanel = document.querySelector("#error");
const maxPressure = document.querySelector("#max-pressure");
const maxTime = document.querySelector("#max-time");
const curvePoints = document.querySelector("#curve-points");
const pressureCanvas = document.querySelector("#pressure-canvas");
const modelLabel = document.querySelector("#model-label");
const inputSummary = document.querySelector("#input-summary");
const notes = document.querySelector("#notes");
const fillingSummary = document.querySelector("#filling-summary");
const fillingSource = document.querySelector("#filling-source");
const fillingMin = document.querySelector("#filling-min");
const fillingAvg = document.querySelector("#filling-avg");
const fillingMax = document.querySelector("#filling-max");
const fillingSd = document.querySelector("#filling-sd");
const fillingHistogram = document.querySelector("#filling-histogram");
const fillingNote = document.querySelector("#filling-note");
const preventionPanel = document.querySelector("#prevention-panel");
const preventionList = document.querySelector("#prevention-list");
const preventionCount = document.querySelector("#prevention-count");
const shapePreview = document.querySelector("#shape-preview");
const shapePreviewStatus = document.querySelector("#shape-preview-status");
const shapeMetricL = document.querySelector("#shape-metric-l");
const shapeMetricW = document.querySelector("#shape-metric-w");
const shapeMetricT = document.querySelector("#shape-metric-t");
const shapeMetricD = document.querySelector("#shape-metric-d");
const shapeModeButtons = Array.from(document.querySelectorAll("[data-shape-mode]"));
const shapeSource = document.querySelector("#shape-source");

const CUSTOM_GEOMETRY_ID = "__custom_geometry__";
const CUSTOM_PROCESS_ID = "__custom_process__";

let geometries = [];
let processes = [];
let applyingDoeValues = false;
let hasBlockingValidation = false;
let shapePreviewState = null;
let shapePreviewMode = "exact";
let shapeAssetMap = new Map();
let shapeLoadToken = 0;
let latestFillingPressureSummary = null;

function formatMetric(value, digits = 3) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "-";
  }
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: digits });
}

function setError(message) {
  errorPanel.textContent = message;
  errorPanel.classList.remove("hidden");
}

function clearError() {
  errorPanel.textContent = "";
  errorPanel.classList.add("hidden");
}

function setLoading(loading) {
  const button = form.querySelector("button[type='submit']");
  if (!button.dataset.defaultText) {
    button.dataset.defaultText = button.textContent;
  }
  button.disabled = loading || hasBlockingValidation;
  button.textContent = loading ? TEXT.loading : button.dataset.defaultText;
}

function fillModelSelect(models) {
  modelSelect.innerHTML = "";
  models.forEach((model) => {
    const option = document.createElement("option");
    option.value = model.key;
    option.textContent = model.available ? model.label : `${model.label} (missing)`;
    option.disabled = !model.available;
    option.dataset.description = model.description;
    modelSelect.appendChild(option);
  });
}

function fillDoeSelect(select, rows) {
  select.innerHTML = "";
  rows.forEach((row) => {
    const option = document.createElement("option");
    option.value = row.id;
    option.textContent = row.id;
    select.appendChild(option);
  });
}

function ensureCustomOption(select, value, label) {
  let option = Array.from(select.options).find((item) => item.value === value);
  if (!option) {
    option = document.createElement("option");
    option.value = value;
    select.prepend(option);
  }
  option.textContent = label;
  select.value = value;
}

function setField(name, value) {
  const input = form.elements[name];
  if (!input) {
    return;
  }
  input.value = value;
}

function applyGeometry(id) {
  if (id === CUSTOM_GEOMETRY_ID) {
    return;
  }
  const row = geometries.find((item) => item.id === id);
  if (!row) {
    return;
  }
  const values = row.values;
  applyingDoeValues = true;
  setField("L_mm", values.L_mm);
  setField("W_mm", values.W_mm);
  setField("t_mm", values.t_mm);
  setField("D_mm", values.D_mm);
  setField("R_mm", values.R_mm);
  setField("gate_type", values.gate_type);
  setField("gate_size_width_mm", values.gate_size_width_mm);
  setField("gate_size_height_mm", values.gate_size_height_mm);
  applyingDoeValues = false;
}

function applyProcess(id) {
  if (id === CUSTOM_PROCESS_ID) {
    return;
  }
  const row = processes.find((item) => item.id === id);
  if (!row) {
    return;
  }
  const values = row.values;
  applyingDoeValues = true;
  setField("melt_temp_C", values.melt_temp_C);
  setField("mold_temp_C", values.mold_temp_C);
  setField("injection_time_s", values.injection_time_s);
  setField("packing_pressure_MPa", values.packing_pressure_MPa);
  setField("packing_time_s", values.packing_time_s);
  applyingDoeValues = false;
}

function markCustomGeometry() {
  if (applyingDoeValues) {
    return;
  }
  ensureCustomOption(geometrySelect, CUSTOM_GEOMETRY_ID, TEXT.customGeometry);
}

function markCustomProcess() {
  if (applyingDoeValues) {
    return;
  }
  ensureCustomOption(processSelect, CUSTOM_PROCESS_ID, TEXT.customProcess);
}

async function loadBootstrapData() {
  try {
    const [modelsResponse, doeResponse] = await Promise.all([
      fetch(`${API_BASE}/models`),
      fetch(`${API_BASE}/doe`),
      loadShapeAssetManifest(),
    ]);
    if (!modelsResponse.ok || !doeResponse.ok) {
      throw new Error(`HTTP ${modelsResponse.status || doeResponse.status}`);
    }
    const models = await modelsResponse.json();
    const doe = await doeResponse.json();
    geometries = doe.geometries;
    processes = doe.processes;
    fillModelSelect(models.sprue_pressure_models);
    fillDoeSelect(geometrySelect, geometries);
    fillDoeSelect(processSelect, processes);
    if (geometries.length) {
      geometrySelect.value = "G01";
      applyGeometry(geometrySelect.value);
    }
    if (processes.length) {
      processSelect.value = "P01";
      applyProcess(processSelect.value);
    }
    updatePreventionCheck();
    apiStatus.textContent = TEXT.apiConnected;
    apiStatus.classList.add("ok");
  } catch (error) {
    apiStatus.textContent = TEXT.apiOffline;
    apiStatus.classList.add("bad");
    setError(TEXT.apiStart);
  }
}

async function loadShapeAssetManifest() {
  try {
    const response = await fetch("./assets/step-glb/manifest.json");
    if (!response.ok) {
      return;
    }
    const manifest = await response.json();
    shapeAssetMap = new Map(
      (manifest.geometries || [])
        .filter((row) => row.geometry_id && row.output && ["converted", "up_to_date"].includes(row.status))
        .map((row) => [row.geometry_id, `./assets/step-glb/${row.geometry_id}.glb`]),
    );
  } catch (error) {
    shapeAssetMap = new Map();
  }
}

function formPayload() {
  const data = new FormData(form);
  const numericFields = [
    "L_mm",
    "W_mm",
    "t_mm",
    "D_mm",
    "R_mm",
    "gate_size_width_mm",
    "gate_size_height_mm",
    "melt_temp_C",
    "mold_temp_C",
    "injection_time_s",
    "packing_pressure_MPa",
    "packing_time_s",
  ];
  const payload = {
    model: data.get("model"),
    geometry_id: data.get("geometry_id") === CUSTOM_GEOMETRY_ID ? null : data.get("geometry_id"),
    process_id: data.get("process_id") === CUSTOM_PROCESS_ID ? null : data.get("process_id"),
    gate_type: data.get("gate_type"),
  };
  numericFields.forEach((name) => {
    payload[name] = Number(data.get(name));
  });
  return payload;
}

function initShapePreview() {
  if (!shapePreview) {
    if (shapePreviewStatus) {
      shapePreviewStatus.textContent = IS_KO
        ? "3D 라이브러리를 불러오지 못했습니다."
        : "The 3D library could not be loaded.";
    }
    return;
  }

  try {
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf8fbfd);

    const camera = new THREE.OrthographicCamera(-100, 100, 100, -100, 0.1, 2000);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    shapePreview.appendChild(renderer.domElement);

    const group = new THREE.Group();
    group.rotation.x = -0.82;
    group.rotation.z = -0.58;
    scene.add(group);

    const ambient = new THREE.HemisphereLight(0xffffff, 0xc8d4df, 2.2);
    scene.add(ambient);
    const key = new THREE.DirectionalLight(0xffffff, 2.6);
    key.position.set(80, -120, 150);
    scene.add(key);
    const fill = new THREE.DirectionalLight(0xbfefff, 1.1);
    fill.position.set(-120, 80, 90);
    scene.add(fill);

    const grid = new THREE.GridHelper(220, 12, 0xc5d6e5, 0xe2ebf2);
    grid.rotation.x = Math.PI / 2;
    grid.position.z = -0.9;
    scene.add(grid);

    shapePreviewState = {
      scene,
      camera,
      renderer,
      group,
      loader: new GLTFLoader(),
      meshObjects: [],
      lastPayloadKey: "",
      pointer: { active: false, x: 0, y: 0 },
      autoRotate: true,
    };

    shapePreview.addEventListener("pointerdown", (event) => {
      shapePreviewState.pointer.active = true;
      shapePreviewState.pointer.x = event.clientX;
      shapePreviewState.pointer.y = event.clientY;
      shapePreviewState.autoRotate = false;
      shapePreview.setPointerCapture(event.pointerId);
    });
    shapePreview.addEventListener("pointermove", (event) => {
      if (!shapePreviewState.pointer.active) {
        return;
      }
      const dx = event.clientX - shapePreviewState.pointer.x;
      const dy = event.clientY - shapePreviewState.pointer.y;
      shapePreviewState.group.rotation.z += dx * 0.008;
      shapePreviewState.group.rotation.x = Math.max(
        -1.35,
        Math.min(-0.25, shapePreviewState.group.rotation.x + dy * 0.006),
      );
      shapePreviewState.pointer.x = event.clientX;
      shapePreviewState.pointer.y = event.clientY;
    });
    shapePreview.addEventListener("pointerup", (event) => {
      shapePreviewState.pointer.active = false;
      shapePreview.releasePointerCapture(event.pointerId);
    });
    shapePreview.addEventListener("pointerleave", () => {
      shapePreviewState.pointer.active = false;
    });

    new ResizeObserver(resizeShapePreview).observe(shapePreview);
    resizeShapePreview();
    animateShapePreview();
  } catch (error) {
    shapePreviewState = null;
    shapePreviewStatus.textContent = IS_KO
      ? "이 브라우저에서 WebGL preview를 시작하지 못했습니다."
      : "This browser could not start the WebGL preview.";
  }
}

function resizeShapePreview() {
  if (!shapePreviewState || !shapePreview) {
    return;
  }
  const rect = shapePreview.getBoundingClientRect();
  const width = Math.max(240, Math.floor(rect.width));
  const height = Math.max(220, Math.floor(rect.height));
  shapePreviewState.renderer.setSize(width, height, false);
  shapePreviewState.camera.left = -width / 2;
  shapePreviewState.camera.right = width / 2;
  shapePreviewState.camera.top = height / 2;
  shapePreviewState.camera.bottom = -height / 2;
  shapePreviewState.camera.updateProjectionMatrix();
}

function animateShapePreview() {
  if (!shapePreviewState) {
    return;
  }
  if (shapePreviewState.autoRotate) {
    shapePreviewState.group.rotation.z += 0.0035;
  }
  shapePreviewState.renderer.render(shapePreviewState.scene, shapePreviewState.camera);
  window.requestAnimationFrame(animateShapePreview);
}

function clearShapeObjects() {
  if (!shapePreviewState) {
    return;
  }
  shapeLoadToken += 1;
  shapePreviewState.meshObjects.forEach((object) => {
    shapePreviewState.group.remove(object);
    object.traverse((child) => {
      if (child.geometry) {
        child.geometry.dispose();
      }
      if (child.material) {
        if (Array.isArray(child.material)) {
          child.material.forEach((material) => material.dispose());
        } else {
          child.material.dispose();
        }
      }
    });
  });
  shapePreviewState.meshObjects = [];
}

function setShapeMode(mode) {
  shapePreviewMode = mode;
  shapeModeButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.shapeMode === mode);
  });
  if (shapePreviewState) {
    shapePreviewState.lastPayloadKey = "";
  }
  updateShapePreview();
}

function makePlateShape(length, width, holeRadius) {
  const shape = new THREE.Shape();
  shape.moveTo(-length / 2, -width / 2);
  shape.lineTo(length / 2, -width / 2);
  shape.lineTo(length / 2, width / 2);
  shape.lineTo(-length / 2, width / 2);
  shape.lineTo(-length / 2, -width / 2);

  const hole = new THREE.Path();
  hole.absellipse(0, 0, holeRadius, holeRadius, 0, Math.PI * 2, false, 0);
  shape.holes.push(hole);
  return shape;
}

function makePlateGeometry(length, width, thickness, holeRadius) {
  const shape = makePlateShape(length, width, holeRadius);
  const geometry = new THREE.ExtrudeGeometry(shape, {
    depth: thickness,
    bevelEnabled: true,
    bevelThickness: Math.min(thickness * 0.12, 0.18),
    bevelSize: Math.min(Math.min(length, width) * 0.004, 0.2),
    bevelSegments: 1,
    curveSegments: 64,
  });
  geometry.translate(0, 0, -thickness / 2);
  geometry.computeVertexNormals();
  return geometry;
}

function interpolateColor(stops, value) {
  const t = Math.max(0, Math.min(1, value));
  for (let index = 0; index < stops.length - 1; index += 1) {
    const [startAt, startColor] = stops[index];
    const [endAt, endColor] = stops[index + 1];
    if (t >= startAt && t <= endAt) {
      const local = (t - startAt) / Math.max(1e-9, endAt - startAt);
      return startColor.clone().lerp(endColor, local);
    }
  }
  return stops[stops.length - 1][1].clone();
}

function pressureFromDistribution(summary, flowFraction) {
  const bins = [...(summary?.bins || [])].sort((a, b) => Number(b.center_MPa) - Number(a.center_MPa));
  if (!bins.length) {
    return null;
  }
  const target = Math.max(0, Math.min(100, flowFraction * 100));
  let cumulative = 0;
  for (const bin of bins) {
    cumulative += Number(bin.volume_ratio_pct) || 0;
    if (target <= cumulative) {
      return Number(bin.center_MPa);
    }
  }
  return Number(bins[bins.length - 1].center_MPa);
}

function makeFillingContourOverlay(length, width, thickness, holeRadius, summary) {
  if (!summary?.bins?.length) {
    return null;
  }
  const geometry = new THREE.ShapeGeometry(makePlateShape(length, width, holeRadius), 96);
  geometry.translate(0, 0, thickness / 2 + 0.035);

  const stats = summary.stats || {};
  const minPressure = Number(stats.min_MPa) || 0;
  const maxPressure = Math.max(Number(stats.max_MPa) || 0, minPressure + 1e-9);
  const colorStops = [
    [0.0, new THREE.Color(0x0756d8)],
    [0.34, new THREE.Color(0x16aad8)],
    [0.55, new THREE.Color(0x00ad5a)],
    [0.76, new THREE.Color(0xf0d800)],
    [1.0, new THREE.Color(0xd40000)],
  ];
  const positions = geometry.getAttribute("position");
  const colors = [];
  for (let index = 0; index < positions.count; index += 1) {
    const x = positions.getX(index);
    const y = positions.getY(index);
    const xFlow = (x + length / 2) / Math.max(length, 1e-9);
    const ySpread = Math.abs(y) / Math.max(width / 2, 1e-9);
    const flowFraction = Math.max(0, Math.min(1, xFlow + ySpread * 0.18));
    const pressure = pressureFromDistribution(summary, flowFraction ** 0.86);
    const normalized = pressure === null ? 0 : (pressure - minPressure) / Math.max(maxPressure - minPressure, 1e-9);
    const color = interpolateColor(colorStops, normalized);
    colors.push(color.r, color.g, color.b);
  }
  geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  return new THREE.Mesh(
    geometry,
    new THREE.MeshBasicMaterial({
      vertexColors: true,
      transparent: true,
      opacity: 0.72,
      side: THREE.DoubleSide,
      depthWrite: false,
      polygonOffset: true,
      polygonOffsetFactor: -2,
    }),
  );
}

function applyFillingVertexColors(geometry, length, width, summary) {
  if (!summary?.bins?.length) {
    return false;
  }
  const stats = summary.stats || {};
  const minPressure = Number(stats.min_MPa) || 0;
  const maxPressure = Math.max(Number(stats.max_MPa) || 0, minPressure + 1e-9);
  const colorStops = [
    [0.0, new THREE.Color(0x0756d8)],
    [0.34, new THREE.Color(0x16aad8)],
    [0.55, new THREE.Color(0x00ad5a)],
    [0.76, new THREE.Color(0xf0d800)],
    [1.0, new THREE.Color(0xd40000)],
  ];
  const positions = geometry.getAttribute("position");
  const colors = [];
  for (let index = 0; index < positions.count; index += 1) {
    const x = positions.getX(index);
    const y = positions.getY(index);
    const xFlow = (x + length / 2) / Math.max(length, 1e-9);
    const ySpread = Math.abs(y) / Math.max(width / 2, 1e-9);
    const flowFraction = Math.max(0, Math.min(1, xFlow + ySpread * 0.18));
    const pressure = pressureFromDistribution(summary, flowFraction ** 0.86);
    const normalized = pressure === null ? 0 : (pressure - minPressure) / Math.max(maxPressure - minPressure, 1e-9);
    const color = interpolateColor(colorStops, normalized);
    colors.push(color.r, color.g, color.b);
  }
  geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  return true;
}

function addEdges(parent, mesh, color = 0x34556d) {
  const edges = new THREE.LineSegments(
    new THREE.EdgesGeometry(mesh.geometry, 24),
    new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.46 }),
  );
  edges.position.copy(mesh.position);
  edges.rotation.copy(mesh.rotation);
  parent.add(edges);
  return edges;
}

function updateShapeMetrics(payload) {
  if (!shapeMetricL) {
    return;
  }
  shapeMetricL.textContent = `${formatMetric(payload.L_mm, 1)} mm`;
  shapeMetricW.textContent = `${formatMetric(payload.W_mm, 1)} mm`;
  shapeMetricT.textContent = `${formatMetric(payload.t_mm, 2)} mm`;
  shapeMetricD.textContent = `${formatMetric(payload.D_mm, 1)} mm`;
}

function setShapeSource(text) {
  if (shapeSource) {
    shapeSource.textContent = text;
  }
}

function setPreviewStatus(message, visible = true) {
  shapePreviewStatus.textContent = message;
  shapePreviewStatus.classList.toggle("hidden", !visible);
}

function fitPreviewCamera(span) {
  const zoom = Math.min(
    shapePreview.clientWidth / Math.max(span * 1.72, 1),
    shapePreview.clientHeight / Math.max(span * 1.18, 1),
  );
  shapePreviewState.camera.zoom = Math.max(1.2, Math.min(5.8, zoom));
  shapePreviewState.camera.position.set(span * 0.58, -span * 0.78, span * 0.55);
  shapePreviewState.camera.lookAt(0, 0, 0);
  shapePreviewState.camera.updateProjectionMatrix();
}

function addMeshEdges(mesh, color = 0x34556d) {
  const edges = new THREE.LineSegments(
    new THREE.EdgesGeometry(mesh.geometry, 24),
    new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.38 }),
  );
  mesh.add(edges);
  return edges;
}

function styleExactShape(object) {
  object.traverse((child) => {
    if (!child.isMesh) {
      return;
    }
    child.castShadow = false;
    child.receiveShadow = false;
    child.material = new THREE.MeshStandardMaterial({
      color: 0x86c3df,
      roughness: 0.62,
      metalness: 0.04,
      side: THREE.DoubleSide,
    });
    addMeshEdges(child);
  });
}

function addExactGateOverlay(payload, bodyBox) {
  const size = bodyBox.getSize(new THREE.Vector3());
  const center = bodyBox.getCenter(new THREE.Vector3());
  // STEP files store the gate as a 5 mm curve marker, not as a solid body.
  const gateDepth = 5;
  const gateWidth = Math.min(Math.max(Number(payload.gate_size_width_mm), 0.2), Math.max(size.y * 0.36, 0.2));
  const gateHeight = Math.min(Math.max(Number(payload.gate_size_height_mm), 0.15), Math.max(size.z, 0.2));
  const gateOverlap = 0.35;
  const gate = new THREE.Mesh(
    new THREE.BoxGeometry(gateWidth, gateDepth, gateHeight),
    new THREE.MeshStandardMaterial({ color: 0xd40000, roughness: 0.5, metalness: 0.02 }),
  );
  gate.rotation.z = Math.PI / 2;
  gate.position.set(bodyBox.min.x - gateDepth / 2 + gateOverlap, center.y, bodyBox.max.z - gateHeight / 2);
  shapePreviewState.group.add(gate);
  const gateEdges = addEdges(shapePreviewState.group, gate, 0x7a0000);

  return [gate, gateEdges];
}

function resetCadQueryRootRotation(object, geometryId) {
  const cadRoot = object.children.find((child) => child.name === geometryId) || object.children[0];
  if (!cadRoot) {
    return;
  }
  cadRoot.quaternion.identity();
  cadRoot.rotation.set(0, 0, 0);
  cadRoot.updateMatrixWorld(true);
}

function centerExactShape(object) {
  const box = new THREE.Box3().setFromObject(object);
  const center = box.getCenter(new THREE.Vector3());
  object.position.sub(center);
  object.updateMatrixWorld(true);
  const centeredBox = new THREE.Box3().setFromObject(object);
  const size = centeredBox.getSize(new THREE.Vector3());
  return {
    box: centeredBox,
    span: Math.max(size.x, size.y, size.z * 8, 1),
  };
}

function loadExactShapePreview(payload) {
  const geometryId = payload.geometry_id;
  const assetUrl = shapeAssetMap.get(geometryId);
  if (!geometryId || !assetUrl) {
    renderParametricShape(payload, TEXT.exactUnavailable);
    return;
  }

  clearShapeObjects();
  const token = ++shapeLoadToken;
  setShapeSource(`${TEXT.exactMode}: ${geometryId}.glb`);
  setPreviewStatus(IS_KO ? `${geometryId} STEP 형상 로딩 중` : `Loading ${geometryId} STEP geometry`);
  shapePreviewState.loader.load(
    assetUrl,
    (gltf) => {
      if (token !== shapeLoadToken) {
        return;
      }
      clearShapeObjects();
      shapeLoadToken = token;
      const object = gltf.scene;
      object.name = `${geometryId}_step_glb`;
      resetCadQueryRootRotation(object, geometryId);
      styleExactShape(object);
      shapePreviewState.group.add(object);
      const exactFit = centerExactShape(object);
      const gateObjects = addExactGateOverlay(payload, exactFit.box);
      shapePreviewState.meshObjects.push(object, ...gateObjects);
      fitPreviewCamera(exactFit.span);
      setPreviewStatus("", false);
      setShapeSource(`${TEXT.exactMode}: ${geometryId}.glb`);
    },
    undefined,
    () => {
      if (token !== shapeLoadToken) {
        return;
      }
      renderParametricShape(payload, TEXT.exactUnavailable);
    },
  );
}

function renderParametricShape(payload, message = "") {
  const rawLength = Number(payload.L_mm);
  const rawWidth = Number(payload.W_mm);
  const rawThickness = Number(payload.t_mm);
  const rawDiameter = Number(payload.D_mm);
  const rawGateWidth = Number(payload.gate_size_width_mm);
  const rawGateHeight = Number(payload.gate_size_height_mm);
  const fillingKey = latestFillingPressureSummary?.sample_id || "no-filling";
  const key = [rawLength, rawWidth, rawThickness, rawDiameter, rawGateWidth, rawGateHeight, fillingKey].join("|");
  if (shapePreviewState.lastPayloadKey === key) {
    return;
  }
  shapePreviewState.lastPayloadKey = key;

  if (![rawLength, rawWidth, rawThickness, rawDiameter, rawGateWidth, rawGateHeight].every((value) => Number.isFinite(value) && value > 0)) {
    clearShapeObjects();
    setPreviewStatus(IS_KO ? "형상 치수를 입력하면 3D preview가 표시됩니다." : "Enter shape dimensions to show the 3D preview.");
    setShapeSource(TEXT.parametricMode);
    return;
  }

  const length = Math.max(rawLength, 1);
  const width = Math.max(rawWidth, 1);
  const thickness = Math.max(rawThickness, 0.2);
  const maxHoleRadius = Math.max(Math.min(length, width) * 0.47, 0.1);
  const holeRadius = Math.min(Math.max(rawDiameter / 2, 0.1), maxHoleRadius);
  const gateWidth = Math.min(Math.max(rawGateWidth, 0.2), Math.min(length, width) * 0.92);
  const gateHeight = Math.min(Math.max(rawGateHeight, 0.15), thickness);
  const gateDepth = 5;
  const gateOverlap = 0.35;

  clearShapeObjects();
  const plateGeometry = makePlateGeometry(length, width, thickness, holeRadius);
  const hasContour = applyFillingVertexColors(plateGeometry, length, width, latestFillingPressureSummary);
  const plate = new THREE.Mesh(
    plateGeometry,
    new THREE.MeshStandardMaterial({
      color: hasContour ? 0xffffff : 0x86c3df,
      roughness: hasContour ? 0.48 : 0.62,
      metalness: 0.04,
      vertexColors: hasContour,
    }),
  );
  shapePreviewState.group.add(plate);
  const plateEdges = addEdges(shapePreviewState.group, plate);

  const gate = new THREE.Mesh(
    new THREE.BoxGeometry(gateWidth, gateDepth, gateHeight),
    new THREE.MeshStandardMaterial({
      color: 0xd40000,
      roughness: 0.5,
      metalness: 0.02,
    }),
  );
  gate.rotation.z = Math.PI / 2;
  gate.position.set(-length / 2 - gateDepth / 2 + gateOverlap, 0, thickness / 2 - gateHeight / 2);
  shapePreviewState.group.add(gate);
  const gateEdges = addEdges(shapePreviewState.group, gate, 0x7a0000);

  shapePreviewState.meshObjects.push(
    plate,
    plateEdges,
    gate,
    gateEdges,
  );

  const span = Math.max(length + gateDepth * 3, width, thickness * 8);
  fitPreviewCamera(span);

  const clamped = holeRadius !== rawDiameter / 2 || gateWidth !== rawGateWidth || gateHeight !== rawGateHeight;
  const statusMessage = message || (clamped
    ? IS_KO
      ? "Preview는 표시를 위해 불가능한 치수를 일부 제한했습니다."
      : "Preview clamps impossible dimensions for display."
    : "");
  setPreviewStatus(statusMessage, Boolean(statusMessage));
  setShapeSource(payload.geometry_id ? `${TEXT.doeParametric}: ${payload.geometry_id}` : TEXT.customParametric);
}

function updateShapePreview() {
  const payload = formPayload();
  updateShapeMetrics(payload);
  if (!shapePreviewState) {
    return;
  }
  const rawLength = Number(payload.L_mm);
  const rawWidth = Number(payload.W_mm);
  const rawThickness = Number(payload.t_mm);
  const rawDiameter = Number(payload.D_mm);
  const rawGateWidth = Number(payload.gate_size_width_mm);
  const rawGateHeight = Number(payload.gate_size_height_mm);
  const canShowExact = shapePreviewMode === "exact" && payload.geometry_id && shapeAssetMap.has(payload.geometry_id);
  const activeMode = canShowExact ? "exact" : "parametric";
  const key = [
    activeMode,
    payload.geometry_id || "custom",
    rawLength,
    rawWidth,
    rawThickness,
    rawDiameter,
    rawGateWidth,
    rawGateHeight,
  ].join("|");
  if (shapePreviewState.lastPayloadKey === key) {
    return;
  }
  shapePreviewState.lastPayloadKey = key;
  if (canShowExact) {
    loadExactShapePreview(payload);
  } else {
    renderParametricShape(
      payload,
      shapePreviewMode === "exact" && !payload.geometry_id ? TEXT.customParametric : "",
    );
  }
}

function issue(severity, category, field, message) {
  return { severity, category, field, message };
}

function validatePayload(payload) {
  const issues = [];
  const length = Number(payload.L_mm);
  const width = Number(payload.W_mm);
  const thickness = Number(payload.t_mm);
  const diameter = Number(payload.D_mm);
  const radius = Number(payload.R_mm || diameter / 2);
  const gateWidth = Number(payload.gate_size_width_mm);
  const gateHeight = Number(payload.gate_size_height_mm);
  const meltTemp = Number(payload.melt_temp_C);
  const moldTemp = Number(payload.mold_temp_C);
  const injectionTime = Number(payload.injection_time_s);
  const packingPressure = Number(payload.packing_pressure_MPa);
  const packingTime = Number(payload.packing_time_s);

  [
    ["L_mm", length],
    ["W_mm", width],
    ["t_mm", thickness],
    ["D_mm", diameter],
    ["gate_size_width_mm", gateWidth],
    ["gate_size_height_mm", gateHeight],
    ["injection_time_s", injectionTime],
    ["packing_pressure_MPa", packingPressure],
    ["packing_time_s", packingTime],
  ].forEach(([field, value]) => {
    if (!Number.isFinite(value) || value <= 0) {
      issues.push(issue("error", "input", field, `${field} must be greater than 0.`));
    }
  });

  if (diameter > 0 && radius > 0 && Math.abs(radius - diameter / 2) > Math.max(0.05, diameter * 0.02)) {
    issues.push(issue("warning", "geometry", "R_mm", "Hole radius does not match D/2."));
  }

  if (Math.min(length, width, thickness, diameter) > 0) {
    const shortSide = Math.min(length, width);
    const longSide = Math.max(length, width);
    const clearance = (shortSide - diameter) / 2;
    if (diameter >= shortSide) {
      issues.push(issue("error", "geometry", "D_mm", "Hole diameter must be smaller than both L and W."));
    } else if (clearance < Math.max(1.0, thickness)) {
      issues.push(issue("warning", "geometry", "D_mm", "Wall clearance around the hole is very small."));
    }
    if (diameter / shortSide > 0.72) {
      issues.push(issue("warning", "geometry", "D_mm", "Hole diameter consumes most of the short side."));
    }
    if (longSide / shortSide > 4.0) {
      issues.push(issue("warning", "geometry", "L_mm", "L/W aspect ratio is far outside the current DOE range."));
    }
    if (length * width - Math.PI * radius ** 2 <= 0) {
      issues.push(issue("error", "geometry", "D_mm", "Hole area is larger than or equal to the rectangular area."));
    }
  }

  if (thickness > 0 && thickness < 0.6) {
    issues.push(issue("warning", "geometry", "t_mm", "Thickness is below a typical robust PP wall range."));
  } else if (thickness > 6.0) {
    issues.push(issue("warning", "geometry", "t_mm", "Thickness is high for a simple PP molded plate."));
  }

  if (Math.min(gateWidth, gateHeight, thickness, length, width) > 0) {
    if (gateHeight > thickness) {
      issues.push(issue("error", "gate", "gate_size_height_mm", "Gate height cannot exceed part thickness."));
    } else if (gateHeight > thickness * 0.85) {
      issues.push(issue("warning", "gate", "gate_size_height_mm", "Gate height is close to full wall thickness."));
    } else if (gateHeight < Math.max(0.15, thickness * 0.08)) {
      issues.push(issue("warning", "gate", "gate_size_height_mm", "Gate height is very small."));
    }
    if (gateWidth > Math.min(length, width)) {
      issues.push(issue("error", "gate", "gate_size_width_mm", "Gate width cannot be larger than the available side length."));
    } else if (gateWidth > Math.min(length, width) * 0.5) {
      issues.push(issue("warning", "gate", "gate_size_width_mm", "Gate width is more than half of the short side."));
    }
    const gateArea = gateWidth * gateHeight;
    const edgeSection = Math.min(length, width) * thickness;
    if (gateArea > edgeSection * 0.5) {
      issues.push(issue("warning", "gate", "gate_size_width_mm", "Gate area is unusually large relative to the edge cross-section."));
    }
    if (gateArea < 0.2) {
      issues.push(issue("warning", "gate", "gate_size_width_mm", "Gate area is extremely small."));
    }
  }

  if (meltTemp < 160 || meltTemp > 290) {
    issues.push(issue("error", "process", "melt_temp_C", "Melt temperature is outside a broad PP processing range."));
  } else if (meltTemp < 190 || meltTemp > 260) {
    issues.push(issue("warning", "process", "melt_temp_C", "Melt temperature is outside the current PP DOE neighborhood."));
  }
  if (moldTemp < 5 || moldTemp > 120) {
    issues.push(issue("error", "process", "mold_temp_C", "Mold temperature is outside a broad physical range."));
  } else if (moldTemp < 25 || moldTemp > 90) {
    issues.push(issue("warning", "process", "mold_temp_C", "Mold temperature is outside the current PP DOE neighborhood."));
  }
  if (injectionTime > 0 && injectionTime < 0.2) {
    issues.push(issue("warning", "process", "injection_time_s", "Injection time is very short."));
  } else if (injectionTime > 8.0) {
    issues.push(issue("warning", "process", "injection_time_s", "Injection time is much longer than the current DOE."));
  }
  if (packingPressure > 160) {
    issues.push(issue("error", "process", "packing_pressure_MPa", "Packing pressure is beyond the broad expected range."));
  } else if (packingPressure > 0 && (packingPressure < 10 || packingPressure > 120)) {
    issues.push(issue("warning", "process", "packing_pressure_MPa", "Packing pressure is outside the current DOE neighborhood."));
  }
  if (packingTime > 20) {
    issues.push(issue("warning", "process", "packing_time_s", "Packing time is much longer than the current DOE."));
  }

  return issues;
}

function renderPreventionIssues(issues) {
  preventionList.innerHTML = "";
  hasBlockingValidation = issues.some((item) => item.severity === "error");
  const button = form.querySelector("button[type='submit']");
  button.disabled = hasBlockingValidation;
  if (!issues.length) {
    preventionPanel.classList.add("hidden");
    return;
  }
  preventionPanel.classList.remove("hidden");
  preventionPanel.classList.toggle("has-errors", hasBlockingValidation);
  preventionCount.textContent = hasBlockingValidation ? TEXT.fixRequired : `${issues.length} ${issues.length > 1 ? TEXT.warnings : TEXT.warning}`;
  issues.forEach((item) => {
    const li = document.createElement("li");
    li.className = item.severity;
    const badge = document.createElement("span");
    badge.className = "issue-badge";
    badge.textContent = item.severity === "error" ? TEXT.error : TEXT.warning;
    const text = document.createElement("span");
    text.textContent = `${localizeCategory(item.category)} / ${item.field}: ${localizeMessage(item.message)}`;
    li.append(badge, text);
    preventionList.appendChild(li);
  });
}

function updatePreventionCheck() {
  renderPreventionIssues(validatePayload(formPayload()));
  updateShapePreview();
}

function localizeCategory(category) {
  if (!IS_KO) {
    return category;
  }
  return {
    input: "입력",
    geometry: "형상",
    gate: "게이트",
    process: "공정",
  }[category] || category;
}

function localizeMessage(message) {
  if (!IS_KO) {
    return message;
  }
  const messages = {
    "Hole radius does not match D/2.": "중앙 홀 반지름이 D/2와 일치하지 않습니다.",
    "Hole diameter must be smaller than both L and W.": "중앙 홀 직경은 L과 W보다 작아야 합니다.",
    "Wall clearance around the hole is very small.": "중앙 홀 주변 wall clearance가 매우 작습니다.",
    "Hole diameter consumes most of the short side.": "중앙 홀 직경이 짧은 변의 대부분을 차지합니다.",
    "L/W aspect ratio is far outside the current DOE range.": "L/W 비율이 현재 DOE 범위를 크게 벗어납니다.",
    "Hole area is larger than or equal to the rectangular area.": "중앙 홀 면적이 직사각형 면적보다 크거나 같습니다.",
    "Thickness is below a typical robust PP wall range.": "두께가 일반적인 PP 사출 wall 범위보다 작습니다.",
    "Thickness is high for a simple PP molded plate.": "두께가 단순 PP 사출 plate 기준으로 큰 편입니다.",
    "Gate height cannot exceed part thickness.": "Gate height는 제품 두께보다 클 수 없습니다.",
    "Gate height is close to full wall thickness.": "Gate height가 제품 두께에 너무 가깝습니다.",
    "Gate height is very small.": "Gate height가 매우 작습니다.",
    "Gate width cannot be larger than the available side length.": "Gate width는 사용 가능한 side length보다 클 수 없습니다.",
    "Gate width is more than half of the short side.": "Gate width가 짧은 변의 절반보다 큽니다.",
    "Gate area is unusually large relative to the edge cross-section.": "Gate 면적이 edge 단면 대비 지나치게 큽니다.",
    "Gate area is extremely small.": "Gate 면적이 매우 작습니다.",
    "Melt temperature is outside a broad PP processing range.": "수지 온도가 PP 공정 가능 범위를 크게 벗어납니다.",
    "Melt temperature is outside the current PP DOE neighborhood.": "수지 온도가 현재 PP DOE 범위를 벗어납니다.",
    "Mold temperature is outside a broad physical range.": "금형 온도가 물리적으로 보기 어려운 범위입니다.",
    "Mold temperature is outside the current PP DOE neighborhood.": "금형 온도가 현재 PP DOE 범위를 벗어납니다.",
    "Injection time is very short.": "Injection time이 매우 짧습니다.",
    "Injection time is much longer than the current DOE.": "Injection time이 현재 DOE보다 훨씬 깁니다.",
    "Packing pressure is beyond the broad expected range.": "Packing pressure가 예상 가능한 범위를 크게 벗어납니다.",
    "Packing pressure is outside the current DOE neighborhood.": "Packing pressure가 현재 DOE 범위를 벗어납니다.",
    "Packing time is much longer than the current DOE.": "Packing time이 현재 DOE보다 훨씬 깁니다.",
    "Hole diameter must be smaller than both L and W to preserve a rectangular wall around the hole.": "직사각형 wall을 유지하려면 중앙 홀 직경은 L과 W보다 작아야 합니다.",
    "Hole diameter consumes most of the short side, so the part may no longer behave like the intended block shape.": "중앙 홀이 짧은 변의 대부분을 차지해 의도한 block 형상으로 보기 어려울 수 있습니다.",
  };
  return messages[message] || message;
}

function localizeModelLabel(label) {
  return IS_KO ? MODEL_LABELS_KO[label] || label : label;
}

function localizeNote(note) {
  return IS_KO ? NOTE_LABELS_KO[note] || localizeMessage(note) : note;
}

function localizeInputValue(value) {
  if (!IS_KO) {
    return value;
  }
  if (value === "manual") {
    return "사용자 입력";
  }
  if (value === "edge_gate") {
    return "edge gate";
  }
  return value;
}

function drawPressureCurve(points) {
  const ctx = pressureCanvas.getContext("2d");
  const { width, height } = pressureCanvas;
  const pad = { left: 58, right: 18, top: 22, bottom: 44 };
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#f8fbfd";
  ctx.fillRect(0, 0, width, height);
  if (!points || !points.length) {
    ctx.fillStyle = "#637184";
    ctx.font = "14px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(TEXT.emptyCurve, width / 2, height / 2);
    return;
  }

  const xs = points.map((point) => Number(point.time_s));
  const ys = points.map((point) => Number(point.sprue_pressure_MPa));
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(0, ...ys);
  const maxY = Math.max(...ys) * 1.06;
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const scaleX = (value) => pad.left + ((value - minX) / Math.max(1e-9, maxX - minX)) * plotW;
  const scaleY = (value) => pad.top + (1 - (value - minY) / Math.max(1e-9, maxY - minY)) * plotH;

  ctx.strokeStyle = "#d2dee9";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(pad.left, pad.top);
  ctx.lineTo(pad.left, height - pad.bottom);
  ctx.lineTo(width - pad.right, height - pad.bottom);
  ctx.stroke();

  ctx.fillStyle = "#607086";
  ctx.font = "12px system-ui, sans-serif";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (let i = 0; i <= 4; i += 1) {
    const yValue = minY + ((maxY - minY) * i) / 4;
    const y = scaleY(yValue);
    ctx.strokeStyle = "#e7eef5";
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(width - pad.right, y);
    ctx.stroke();
    ctx.fillText(formatMetric(yValue, 1), pad.left - 8, y);
  }

  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  for (let i = 0; i <= 4; i += 1) {
    const xValue = minX + ((maxX - minX) * i) / 4;
    ctx.fillText(formatMetric(xValue, 2), scaleX(xValue), height - pad.bottom + 10);
  }

  const gradient = ctx.createLinearGradient(pad.left, 0, width - pad.right, 0);
  gradient.addColorStop(0, "#0076bd");
  gradient.addColorStop(0.55, "#16aad8");
  gradient.addColorStop(1, "#00ad5a");
  ctx.strokeStyle = gradient;
  ctx.lineWidth = 3;
  ctx.lineJoin = "round";
  ctx.lineCap = "round";
  ctx.beginPath();
  points.forEach((point, index) => {
    const x = scaleX(point.time_s);
    const y = scaleY(point.sprue_pressure_MPa);
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();

  ctx.fillStyle = "#132236";
  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  ctx.font = "12px system-ui, sans-serif";
  ctx.fillText(TEXT.timeAxis, pad.left + plotW / 2, height - 4);
  ctx.save();
  ctx.translate(14, pad.top + plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText(TEXT.pressureAxis, 0, 0);
  ctx.restore();
}

function renderInputSummary(inputs) {
  inputSummary.innerHTML = "";
  [
    [TEXT.geometry, inputs.geometry_id],
    [TEXT.process, inputs.process_id],
    ["L", `${formatMetric(inputs.L_mm, 2)} mm`],
    ["W", `${formatMetric(inputs.W_mm, 2)} mm`],
    ["t", `${formatMetric(inputs.t_mm, 3)} mm`],
    ["D", `${formatMetric(inputs.D_mm, 2)} mm`],
  ].forEach(([labelText, value]) => {
    const item = document.createElement("span");
    item.className = "input-token";
    const label = document.createElement("strong");
    label.textContent = labelText;
    const valueEl = document.createElement("span");
    valueEl.className = "input-token-value";
    valueEl.textContent = localizeInputValue(value);
    item.append(label, valueEl);
    inputSummary.appendChild(item);
  });
}

function renderFillingPressure(summary) {
  if (!fillingSummary) {
    return;
  }
  if (!summary) {
    fillingSummary.classList.add("hidden");
    return;
  }

  const stats = summary.stats || {};
  fillingSummary.classList.remove("hidden");
  fillingSource.textContent = summary.sample_id || summary.source_file || "-";
  fillingMin.textContent = `${formatMetric(stats.min_MPa, 3)} MPa`;
  fillingAvg.textContent = `${formatMetric(stats.avg_MPa, 3)} MPa`;
  fillingMax.textContent = `${formatMetric(stats.max_MPa, 3)} MPa`;
  fillingSd.textContent = `${formatMetric(stats.sd_MPa, 3)} MPa`;

  fillingHistogram.innerHTML = "";
  const bins = summary.bins || [];
  const maxRatio = Math.max(...bins.map((bin) => Number(bin.volume_ratio_pct) || 0), 1);
  bins.forEach((bin) => {
    const row = document.createElement("div");
    row.className = "filling-bar";

    const range = document.createElement("span");
    range.textContent = `${formatMetric(bin.from_MPa, 1)}-${formatMetric(bin.to_MPa, 1)}`;

    const track = document.createElement("div");
    track.className = "filling-bar-track";
    const fill = document.createElement("div");
    fill.className = "filling-bar-fill";
    fill.style.width = `${Math.max(1, (Number(bin.volume_ratio_pct) / maxRatio) * 100)}%`;
    track.appendChild(fill);

    const ratio = document.createElement("strong");
    ratio.textContent = `${formatMetric(bin.volume_ratio_pct, 2)}%`;

    row.append(range, track, ratio);
    fillingHistogram.appendChild(row);
  });

  fillingNote.textContent = TEXT.fillingNoSpatial;
}

function clearFillingPressureContext() {
  latestFillingPressureSummary = null;
  if (shapePreviewState) {
    shapePreviewState.lastPayloadKey = "";
  }
}

function renderResult(data) {
  emptyState.classList.add("hidden");
  resultPanel.classList.remove("hidden");
  maxPressure.textContent = `${formatMetric(data.predicted_max_pressure_MPa, 3)} MPa`;
  maxTime.textContent = `${formatMetric(data.predicted_max_time_s, 3)} s`;
  curvePoints.textContent = data.curve.length;
  modelLabel.textContent = localizeModelLabel(data.model_label);
  renderInputSummary(data.inputs);
  drawPressureCurve(data.curve);
  latestFillingPressureSummary = data.filling_pressure || null;
  renderFillingPressure(data.filling_pressure);
  if (shapePreviewMode === "parametric" && shapePreviewState) {
    shapePreviewState.lastPayloadKey = "";
    updateShapePreview();
  }

  notes.innerHTML = "";
  (data.validation_warnings || []).forEach((warning) => {
    const item = document.createElement("li");
    const severity = warning.severity === "error" ? TEXT.error : TEXT.warning;
    item.textContent = `${severity.toUpperCase()}: ${localizeMessage(warning.message)}`;
    notes.appendChild(item);
  });
  data.notes.forEach((note) => {
    const item = document.createElement("li");
    item.textContent = localizeNote(note);
    notes.appendChild(item);
  });
}

async function submitPrediction(event) {
  event.preventDefault();
  clearError();
  setLoading(true);
  try {
    const response = await fetch(`${API_BASE}/predict/sprue-pressure`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formPayload()),
    });
    const data = await response.json();
    if (!response.ok) {
      if (data.detail && data.detail.warnings) {
        renderPreventionIssues(data.detail.warnings);
        throw new Error(IS_KO ? TEXT.invalidInput : data.detail.message || TEXT.invalidInput);
      }
      throw new Error(data.detail || `HTTP ${response.status}`);
    }
    renderResult(data);
  } catch (error) {
    setError(error.message || "Prediction failed.");
  } finally {
    setLoading(false);
  }
}

geometrySelect.addEventListener("change", () => {
  clearFillingPressureContext();
  applyGeometry(geometrySelect.value);
  updatePreventionCheck();
});
processSelect.addEventListener("change", () => {
  clearFillingPressureContext();
  applyProcess(processSelect.value);
  updatePreventionCheck();
});
shapeModeButtons.forEach((button) => {
  button.addEventListener("click", () => {
    setShapeMode(button.dataset.shapeMode);
  });
});
[
  "L_mm",
  "W_mm",
  "t_mm",
  "D_mm",
  "R_mm",
  "gate_type",
  "gate_size_width_mm",
  "gate_size_height_mm",
].forEach((name) => {
  form.elements[name].addEventListener("input", () => {
    clearFillingPressureContext();
    markCustomGeometry();
    updatePreventionCheck();
  });
});
[
  "melt_temp_C",
  "mold_temp_C",
  "injection_time_s",
  "packing_pressure_MPa",
  "packing_time_s",
].forEach((name) => {
  form.elements[name].addEventListener("input", () => {
    clearFillingPressureContext();
    markCustomProcess();
    updatePreventionCheck();
  });
});
form.addEventListener("submit", submitPrediction);
initShapePreview();
drawPressureCurve([]);
loadBootstrapData();
