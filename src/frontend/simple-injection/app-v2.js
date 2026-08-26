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
const RAG_BASE = API_BASE.replace(/\/simple-injection$/, "/rag");
const IS_KO = document.documentElement.lang.toLowerCase().startsWith("ko");

const TEXT = {
  checking: IS_KO ? "확인 중" : "Checking",
  apiReady: IS_KO ? "모델 API 연결됨" : "Model API connected",
  apiOffline: IS_KO ? "API offline" : "API offline",
  loading: IS_KO ? "예측 중..." : "Predicting...",
  ready: IS_KO ? "준비됨" : "Ready",
  customGeometry: IS_KO ? "사용자 입력 (형상)" : "User input (geometry)",
  customProcess: IS_KO ? "사용자 입력 (공정)" : "User input (process)",
  preventionOk: IS_KO ? "Prevention check 통과" : "Prevention check passed",
  preventionWarn: IS_KO ? "확인 필요" : "Check inputs",
  geometryTooLarge: IS_KO ? "Hole D가 plate 폭보다 큽니다." : "Hole D is larger than the plate width.",
  gateTooLarge: IS_KO ? "Gate width가 plate 폭보다 큽니다." : "Gate width is larger than the plate width.",
  missingUpload: IS_KO ? "비교할 CSV 파일을 하나 이상 업로드해 주세요." : "Upload at least one CSV file to compare.",
  compareReady: IS_KO ? "비교 완료" : "Comparison ready",
  compareRunning: IS_KO ? "비교 중..." : "Comparing...",
  compareNeedPrediction: IS_KO ? "먼저 예측을 실행해 주세요." : "Run a prediction first.",
  noFilling: IS_KO ? "Filling Pressure 결과가 없습니다." : "No filling pressure result.",
  noCurve: IS_KO ? "Sprue Pressure 곡선이 없습니다." : "No sprue pressure curve.",
  timeAxis: IS_KO ? "시간 (s)" : "Time (s)",
  pressureAxis: IS_KO ? "Sprue pressure (MPa)" : "Sprue pressure (MPa)",
  xaiUnavailable: IS_KO ? "XAI 결과가 없습니다." : "No XAI explanation is available.",
  currentValue: IS_KO ? "현재값" : "Current",
  sensitivity: IS_KO ? "민감도" : "Sensitivity",
  ragAsking: IS_KO ? "답변 생성 중..." : "Answering...",
  ragAnswerTitle: IS_KO ? "Injection AI 답변" : "Injection AI answer",
  ragCitations: IS_KO ? "근거 자료" : "Citations",
  ragShowCitations: IS_KO ? "근거 보기" : "Show citations",
  ragHideCitations: IS_KO ? "근거 숨기기" : "Hide citations",
  ragFailed: IS_KO ? "Injection AI 답변을 불러오지 못했습니다." : "Could not load the Injection AI answer.",
  ragSummary: IS_KO ? "요약" : "Summary",
  ragReasoning: IS_KO ? "해석" : "Reasoning",
  historyLatest: IS_KO ? "최신" : "Latest",
  historyEmpty: IS_KO ? "예측을 실행하면 최근 Injection 기록이 여기에 표시됩니다." : "Run an Injection forecast and recent runs will appear here.",
  historyClear: IS_KO ? "기록 삭제" : "Clear history",
  xaiMore: (count) => IS_KO ? `나머지 ${count}개 feature 더보기` : `Show ${count} more features`,
};

const CUSTOM_GEOMETRY_ID = "manual";
const CUSTOM_PROCESS_ID = "manual";

const MODEL_LABELS = {
  sprue_classical: IS_KO ? "Machine Learning" : "Machine Learning",
  sprue_goint: IS_KO ? "Deep Learning" : "Deep Learning",
  sprue_deeponet: IS_KO ? "Operator Learning" : "Operator Learning",
  filling_classical: IS_KO ? "Machine Learning" : "Machine Learning",
  filling_goint: IS_KO ? "Deep Learning" : "Deep Learning",
  filling_deeponet: IS_KO ? "Operator Learning" : "Operator Learning",
};

const PROCESS_RANGES = {
  melt_temp_C: [180, 320, "C"],
  mold_temp_C: [20, 130, "C"],
  packing_pressure_MPa: [10, 130, "MPa"],
  injection_time_s: [0.2, 4.0, "s"],
  packing_time_s: [0.2, 8.0, "s"],
};

const GEOMETRY_RANGES = {
  L_mm: [20, 140, "mm", 1],
  W_mm: [20, 120, "mm", 1],
  t_mm: [0.5, 5, "mm", 2],
  D_mm: [0, 80, "mm", 1],
  R_mm: [0, 40, "mm", 1],
  gate_size_width_mm: [0, 30, "mm", 1],
  gate_size_height_mm: [0, 5, "mm", 2],
};

const XAI_KO_FEATURES = {
  L_mm: ["길이", "전체 제품 길이입니다. 유동 거리가 길어지면 필요한 압력이 커지고 압력 곡선의 시간 위치가 달라질 수 있습니다."],
  W_mm: ["폭", "전체 제품 폭입니다. 투영 면적과 유동 가능한 영역을 바꿉니다."],
  t_mm: ["두께", "제품 두께입니다. 두꺼운 캐비티는 대체로 유동 저항을 낮추고, 얇은 구간은 압력 민감도를 키울 수 있습니다."],
  D_mm: ["홀 직경", "중앙 홀의 직경입니다. 순 유동 면적을 줄이고 홀 주변의 충전 경로를 바꿉니다."],
  R_mm: ["홀 반경", "중앙 홀의 반경입니다. 홀 직경과 함께 사용되며 유효 단면에 영향을 줍니다."],
  gate_size_width_mm: ["게이트 폭", "게이트 개구부의 폭입니다. 게이트 면적이 커지면 입구 부근의 국부 압력 손실이 줄어들 수 있습니다."],
  gate_size_height_mm: ["게이트 높이", "게이트 개구부의 높이입니다. 게이트 면적과 제한 정도를 직접 바꿉니다."],
  melt_temp_C: ["수지 온도", "수지 온도입니다. 온도가 높아지면 일반적으로 점도가 낮아져 필요한 압력이 줄어들 수 있습니다."],
  mold_temp_C: ["금형 온도", "금형 온도입니다. 냉각 속도, 점도 증가, 벽면 근처 유동 저항에 영향을 줍니다."],
  injection_time_s: ["사출 시간", "충전 시간 조건입니다. 빠른 사출은 peak pressure를 높일 수 있고, 느린 사출은 압력 곡선 형태를 바꿉니다."],
  packing_pressure_MPa: ["보압", "보압 설정값입니다. 충전 후반부 압력 수준과 peak pressure 응답에 영향을 줄 수 있습니다."],
  packing_time_s: ["보압 시간", "보압 유지 시간입니다. 주로 충전 이후 후반 압력 거동에 영향을 줍니다."],
  area_mm2: ["제품 면적", "길이와 폭으로 계산한 제품 면적입니다."],
  hole_area_mm2: ["홀 면적", "중앙 홀 때문에 제거되는 면적입니다."],
  net_area_mm2: ["순 면적", "전체 면적에서 홀 면적을 뺀 유효 면적입니다."],
  volume_mm3: ["제품 부피", "순 면적과 두께로 계산한 캐비티 부피입니다."],
  aspect_ratio: ["형상비", "길이와 폭의 비율입니다. 유동 영역이 얼마나 길쭉한지 나타냅니다."],
  hole_diameter_ratio: ["홀 직경 비율", "홀 직경을 제품의 짧은 변 기준으로 정규화한 값입니다."],
  gate_area_mm2: ["게이트 면적", "게이트 폭과 높이로 계산한 게이트 단면적입니다."],
  gate_to_thickness_ratio: ["게이트/두께 비율", "제품 두께 대비 게이트 높이의 비율입니다."],
  flow_length_to_thickness: ["유동 길이/두께 비율", "유동 경로가 두께에 비해 얼마나 긴지 나타내는 지표입니다. 값이 커지면 충전 압력 민감도가 커지는 경우가 많습니다."],
  process_total_time_s: ["총 공정 시간", "사출 시간과 보압 시간을 더한 값입니다."],
};

const XAI_KO_COPY = {
  summary: "현재 선택한 Injection 입력에서 형상, 공정, 게이트, 파생 유동 feature를 하나씩 변화시켜 Sprue Pressure 곡선과 Filling Pressure 분포가 얼마나 변하는지 계산한 설명입니다.",
  method: "형상 + 공정 + 게이트 + 파생 유동 descriptor",
  perturbations: {
    "increased by 5%": "5% 증가",
    "raised from 0 to 1": "0에서 1로 변경",
  },
  notes: [
    "중요도는 현재 DOE/입력 조건에 대한 local 값이므로, 형상, 공정값, 모델 선택이 바뀌면 결과도 달라질 수 있습니다.",
    "파생 feature는 surrogate 모델 내부에서 사용하는 설명 변수입니다. 설계 방향을 잡는 참고값으로 보고, 중요한 후보는 Moldex3D로 검증하는 것이 좋습니다.",
  ],
};

const apiStatus = document.querySelector("#api-status");
const form = document.querySelector("#prediction-form");
const modelSelect = document.querySelector("#model-select");
const fillingModelSelect = document.querySelector("#filling-model-select");
const geometrySelect = document.querySelector("#geometry-select");
const processSelect = document.querySelector("#process-select");
const preventionCard = document.querySelector("#prevention-card");
const preventionState = document.querySelector("#prevention-state");
const preventionTitle = document.querySelector("#prevention-title");
const shapeVisual = document.querySelector("#shape-visual");
const shapePreviewStatus = document.querySelector("#shape-preview-status");
const shapeZoomIn = document.querySelector("#shape-zoom-in");
const shapeZoomOut = document.querySelector("#shape-zoom-out");
const shapeViewReset = document.querySelector("#shape-view-reset");
const activeRun = document.querySelector("#active-run");
const previewTitle = document.querySelector("#preview-title");
const previewCopy = document.querySelector("#preview-copy");
const metricL = document.querySelector("#metric-l");
const metricW = document.querySelector("#metric-w");
const metricT = document.querySelector("#metric-t");
const metricD = document.querySelector("#metric-d");
const emptyState = document.querySelector("#empty-state");
const resultPanel = document.querySelector("#result");
const maxPressure = document.querySelector("#max-pressure");
const maxTime = document.querySelector("#max-time");
const curvePoints = document.querySelector("#curve-points");
const fillingMax = document.querySelector("#filling-max");
const pressureCanvas = document.querySelector("#pressure-canvas");
const fillingHistogram = document.querySelector("#filling-histogram");
const xaiCard = document.querySelector("#xai-card");
const xaiMethod = document.querySelector("#xai-method");
const xaiSummary = document.querySelector("#xai-summary");
const xaiFeatureList = document.querySelector("#xai-feature-list");
const xaiNotes = document.querySelector("#xai-notes");
const sprueModelLabel = document.querySelector("#sprue-model-label");
const fillingModelLabel = document.querySelector("#filling-model-label");
const notes = document.querySelector("#notes");
const historyCard = document.querySelector("#prediction-history");
const historyList = document.querySelector("#prediction-history-list");
const historyClear = document.querySelector("#prediction-history-clear");
const errorPanel = document.querySelector("#error");
const comparisonStatus = document.querySelector("#comparison-status");
const comparisonSampleId = document.querySelector("#comparison-sample-id");
const comparisonSprueFile = document.querySelector("#comparison-sprue-file");
const comparisonFillingFile = document.querySelector("#comparison-filling-file");
const comparisonSubmit = document.querySelector("#comparison-submit");
const comparisonOutput = document.querySelector("#comparison-output");
const ragForm = document.querySelector("#rag-form");
const ragAnswer = document.querySelector("#rag-answer");
const ragQueryInput = ragForm?.querySelector('textarea[name="query"]');

let geometries = [];
let processes = [];
let latestPredictionData = null;
let predictionProgressTimer = 0;
let standardResultTabs = null;
let hasBlockingValidation = false;
let THREE = null;
let shapeEnginePromise = null;
let shapeEngineUnavailable = false;
let shapePreviewState = null;
let shapeAnimationFrame = 0;
let activePredictionFlowData = null;
let applyingDoeValues = false;
const PREDICTION_FLOW_DURATION_MS = 5200;
const SHAPE_DEFAULT_ROTATION = { x: -0.82, z: -0.58 };
const INJECTION_HISTORY_KEY = "imperialax.injection.recentRuns.v1";
const HIDDEN_GEOMETRY_IDS = new Set(["G11"]);

function formatMetric(value, digits = 2) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "-";
  }
  return numeric.toLocaleString(undefined, { maximumFractionDigits: digits });
}

function numberField(name) {
  const value = Number(form.elements[name]?.value);
  return Number.isFinite(value) ? value : 0;
}

function setError(message) {
  errorPanel.textContent = message;
  errorPanel.classList.remove("hidden");
}

function clearError() {
  errorPanel.textContent = "";
  errorPanel.classList.add("hidden");
}

function ensurePredictionProgress() {
  let progress = document.querySelector("#prediction-progress");
  const workspace = resultPanel?.parentElement;
  if (progress || !workspace) return progress;
  progress = document.createElement("section");
  progress.id = "prediction-progress";
  progress.className = "prediction-progress hidden";
  progress.setAttribute("role", "status");
  progress.setAttribute("aria-live", "polite");
  progress.setAttribute("aria-atomic", "true");
  progress.innerHTML = `
    <span class="prediction-progress-spinner" aria-hidden="true"></span>
    <div><strong>${IS_KO ? "예측 진행 중" : "Forecast in progress"}</strong><span id="prediction-progress-detail"></span></div>
    <i aria-hidden="true"></i>
  `;
  workspace.insertBefore(progress, emptyState);
  return progress;
}

function setPredictionProgress(loading) {
  const progress = ensurePredictionProgress();
  if (!progress) return;
  window.clearInterval(predictionProgressTimer);
  predictionProgressTimer = 0;
  progress.classList.toggle("hidden", !loading);
  progress.parentElement?.setAttribute("aria-busy", String(loading));
  if (!loading) return;
  const messages = IS_KO
    ? ["DOE 입력을 확인하고 있습니다.", "Sprue·Filling 모델을 실행하고 있습니다.", "곡선과 XAI 결과를 준비하고 있습니다."]
    : ["Checking the DOE inputs.", "Running the Sprue and Filling models.", "Preparing curve and XAI results."];
  let messageIndex = 0;
  const detail = progress.querySelector("#prediction-progress-detail");
  if (detail) detail.textContent = messages[messageIndex];
  predictionProgressTimer = window.setInterval(() => {
    messageIndex = Math.min(messageIndex + 1, messages.length - 1);
    if (detail) detail.textContent = messages[messageIndex];
  }, 2400);
}

function setupStandardResultTabs() {
  if (!resultPanel || document.documentElement.classList.contains("injection-rebuild")) return null;
  const definitions = [
    ["summary", IS_KO ? "요약" : "Summary"],
    ["curve", IS_KO ? "스프루 곡선" : "Sprue Curve"],
    ["filling", IS_KO ? "필링 분포" : "Filling Distribution"],
    ["xai", "XAI"],
    ["validation", IS_KO ? "검증" : "Validation"],
    ["history", IS_KO ? "기록" : "History"],
  ];
  const tabList = document.createElement("div");
  tabList.className = "standard-result-tabs";
  tabList.setAttribute("role", "tablist");
  tabList.setAttribute("aria-label", IS_KO ? "예측 결과 보기" : "Prediction result views");
  const panels = {};
  definitions.forEach(([key, label], index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.standardResultTab = key;
    button.id = `standard-injection-tab-${key}`;
    button.textContent = label;
    button.setAttribute("role", "tab");
    button.setAttribute("aria-controls", `standard-injection-panel-${key}`);
    button.setAttribute("aria-selected", String(index === 0));
    button.tabIndex = index === 0 ? 0 : -1;
    tabList.appendChild(button);
    const panel = document.createElement("section");
    panel.id = `standard-injection-panel-${key}`;
    panel.className = "standard-result-panel";
    panel.dataset.standardResultPanel = key;
    panel.setAttribute("role", "tabpanel");
    panel.setAttribute("aria-labelledby", button.id);
    panel.hidden = index !== 0;
    panels[key] = panel;
  });
  [resultPanel.querySelector(":scope > .result-head"), resultPanel.querySelector(":scope > .result-hero"), resultPanel.querySelector(":scope > .stats"), notes]
    .filter(Boolean).forEach((node) => panels.summary.appendChild(node));
  const cardMap = {
    curve: resultPanel.querySelector(":scope > .chart-card"),
    filling: resultPanel.querySelector(":scope > .filling-card"),
    xai: xaiCard,
    validation: resultPanel.querySelector(":scope > .compare-card"),
    history: historyCard,
  };
  Object.entries(cardMap).forEach(([key, node]) => { if (node) panels[key].appendChild(node); });
  resultPanel.append(tabList, ...definitions.map(([key]) => panels[key]));
  const buttons = [...tabList.querySelectorAll("[data-standard-result-tab]")];
  const select = (key, focus = false) => {
    const target = buttons.find((button) => button.dataset.standardResultTab === key);
    if (!target || target.getAttribute("aria-disabled") === "true") return;
    buttons.forEach((button) => {
      const selected = button === target;
      button.setAttribute("aria-selected", String(selected));
      button.tabIndex = selected ? 0 : -1;
    });
    Object.entries(panels).forEach(([panelKey, panel]) => { panel.hidden = panelKey !== key; });
    if (key === "curve") requestAnimationFrame(() => drawPressureCurve(latestPredictionData?.curve || []));
    if (focus) target.focus();
  };
  buttons.forEach((button) => {
    button.addEventListener("click", () => select(button.dataset.standardResultTab));
    button.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      const enabled = buttons.filter((item) => item.getAttribute("aria-disabled") !== "true");
      const current = enabled.indexOf(button);
      const next = event.key === "Home" ? 0 : event.key === "End" ? enabled.length - 1
        : event.key === "ArrowRight" ? (current + 1) % enabled.length
          : (current - 1 + enabled.length) % enabled.length;
      select(enabled[next].dataset.standardResultTab, true);
    });
  });
  const updateAvailability = () => {
    buttons.forEach((button) => {
      const source = cardMap[button.dataset.standardResultTab];
      const disabled = Boolean(source?.classList.contains("hidden"));
      button.setAttribute("aria-disabled", String(disabled));
    });
  };
  if (xaiCard) new MutationObserver(updateAvailability).observe(xaiCard, { attributes: true, attributeFilter: ["class"] });
  updateAvailability();
  return { select, updateAvailability };
}

function setLoading(targetOrLoading, maybeLoading) {
  const targetForm = typeof targetOrLoading === "boolean" ? form : targetOrLoading;
  const loading = typeof targetOrLoading === "boolean" ? targetOrLoading : Boolean(maybeLoading);
  const buttons = [...(targetForm?.querySelectorAll("button[type='submit']") || [])];
  if (!buttons.length) return;
  buttons.forEach((button) => {
    if (!button.dataset.defaultText) {
      button.dataset.defaultText = button.textContent;
    }
    button.disabled = loading || hasBlockingValidation;
    button.textContent = loading ? TEXT.loading : button.dataset.defaultText;
  });
  if (targetForm === form) setPredictionProgress(loading);
}

function simplifiedModelLabel(model) {
  return MODEL_LABELS[model.key] || model.label;
}

function fillModelSelect(select, models) {
  select.innerHTML = "";
  models.forEach((model, index) => {
    const option = document.createElement("option");
    option.value = model.key;
    option.textContent = model.available
      ? `${simplifiedModelLabel(model)}${index === 0 ? ` (${IS_KO ? "추천" : "Recommended"})` : ""}`
      : `${simplifiedModelLabel(model)} (${IS_KO ? "없음" : "missing"})`;
    option.disabled = !model.available;
    option.dataset.description = model.description;
    select.appendChild(option);
  });
}

function fillDoeSelect(select, rows, preferredId) {
  select.innerHTML = "";
  rows.forEach((row) => {
    const option = document.createElement("option");
    option.value = row.id;
    option.textContent = row.id;
    select.appendChild(option);
  });
  if (preferredId && rows.some((row) => row.id === preferredId)) {
    select.value = preferredId;
  }
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
  if (input) {
    input.value = value ?? "";
  }
}

function applyGeometry(id) {
  if (id === CUSTOM_GEOMETRY_ID) {
    return;
  }
  const row = geometries.find((item) => item.id === id) || geometries[0];
  if (!row) {
    return;
  }
  applyingDoeValues = true;
  Object.entries(row.values).forEach(([key, value]) => setField(key, value));
  applyingDoeValues = false;
}

function applyProcess(id) {
  if (id === CUSTOM_PROCESS_ID) {
    return;
  }
  const row = processes.find((item) => item.id === id) || processes[0];
  if (!row) {
    return;
  }
  applyingDoeValues = true;
  Object.entries(row.values).forEach(([key, value]) => setField(key, value));
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

function payloadFromForm() {
  return {
    model: modelSelect.value,
    filling_model: fillingModelSelect.value,
    geometry_id: geometrySelect.value,
    process_id: processSelect.value,
    L_mm: numberField("L_mm"),
    W_mm: numberField("W_mm"),
    t_mm: numberField("t_mm"),
    D_mm: numberField("D_mm"),
    R_mm: numberField("R_mm"),
    gate_type: form.elements.gate_type?.value || "edge_gate",
    gate_size_width_mm: numberField("gate_size_width_mm"),
    gate_size_height_mm: numberField("gate_size_height_mm"),
    melt_temp_C: numberField("melt_temp_C"),
    mold_temp_C: numberField("mold_temp_C"),
    injection_time_s: numberField("injection_time_s"),
    packing_pressure_MPa: numberField("packing_pressure_MPa"),
    packing_time_s: numberField("packing_time_s"),
  };
}

function processPercent(name, value) {
  const [min, max] = PROCESS_RANGES[name] || [0, 1];
  return Math.max(0, Math.min(100, ((Number(value) - min) / (max - min)) * 100));
}

function geometryPercent(name, value) {
  const [min, max] = GEOMETRY_RANGES[name] || [0, 1];
  return Math.max(0, Math.min(100, ((Number(value) - min) / (max - min)) * 100));
}

function updateProcessReadouts() {
  Object.entries(PROCESS_RANGES).forEach(([name, range]) => {
    const input = form.elements[name];
    if (!input) {
      return;
    }
    const readout = document.querySelector(`[data-process-readout="${name}"]`);
    const bar = document.querySelector(`[data-process-bar="${name}"]`);
    const unit = range[2];
    if (readout) {
      readout.textContent = `${formatMetric(input.value, name.endsWith("_s") ? 3 : 1)} ${unit}`;
    }
    if (bar) {
      bar.style.setProperty("--value", `${processPercent(name, input.value)}%`);
    }
  });
}

function updateGeometryReadouts() {
  Object.entries(GEOMETRY_RANGES).forEach(([name, range]) => {
    const input = form.elements[name];
    if (!input) {
      return;
    }
    const readout = document.querySelector(`[data-geometry-readout="${name}"]`);
    const bar = document.querySelector(`[data-geometry-bar="${name}"]`);
    const unit = range[2];
    const digits = range[3] ?? 1;
    if (readout) {
      readout.textContent = `${formatMetric(input.value, digits)} ${unit}`;
    }
    if (bar) {
      bar.style.setProperty("--value", `${geometryPercent(name, input.value)}%`);
    }
  });

  const gateReadout = document.querySelector('[data-geometry-readout="gate_type"]');
  if (gateReadout) {
    gateReadout.textContent = form.elements.gate_type?.value || "-";
  }
}

function validationIssues(payload) {
  const issues = [];
  if (payload.D_mm >= Math.min(payload.L_mm, payload.W_mm)) {
    issues.push(TEXT.geometryTooLarge);
  }
  if (payload.gate_size_width_mm >= payload.W_mm) {
    issues.push(TEXT.gateTooLarge);
  }
  if (payload.injection_time_s <= 0 || payload.packing_pressure_MPa <= 0 || payload.packing_time_s <= 0) {
    issues.push(IS_KO ? "공정 값은 0보다 커야 합니다." : "Process values must be greater than 0.");
  }
  return issues;
}

function updatePreventionCheck() {
  const issues = validationIssues(payloadFromForm());
  hasBlockingValidation = issues.length > 0;
  preventionCard.classList.toggle("error", hasBlockingValidation);
  preventionCard.classList.toggle("warn", false);
  preventionState.textContent = hasBlockingValidation ? (IS_KO ? "수정 필요" : "Fix required") : TEXT.ready;
  preventionTitle.textContent = hasBlockingValidation ? issues.join(" ") : TEXT.preventionOk;
  setLoading(false);
}

function setShapePreviewStatus(message, visible = true) {
  if (!shapePreviewStatus) {
    return;
  }
  shapePreviewStatus.textContent = message;
  shapePreviewStatus.classList.toggle("hidden", !visible);
}

function disposeObject(object) {
  if (object.geometry) {
    object.geometry.dispose();
  }
  const materials = Array.isArray(object.material) ? object.material : [object.material];
  materials.filter(Boolean).forEach((material) => material.dispose());
}

function clearShapeObjects() {
  if (!shapePreviewState) {
    return;
  }
  shapePreviewState.predictionFlow = null;
  shapePreviewState.objects.forEach((object) => {
    shapePreviewState.group.remove(object);
    disposeObject(object);
  });
  shapePreviewState.objects = [];
}

function resizeShapePreview() {
  if (!shapePreviewState || !shapeVisual) {
    return;
  }
  const rect = shapeVisual.getBoundingClientRect();
  const width = Math.max(260, rect.width);
  const height = Math.max(210, rect.height);
  shapePreviewState.renderer.setSize(width, height, false);
  shapePreviewState.camera.left = -width / 2;
  shapePreviewState.camera.right = width / 2;
  shapePreviewState.camera.top = height / 2;
  shapePreviewState.camera.bottom = -height / 2;
  const span = Math.max(120, shapePreviewState.span);
  const fitZoom = Math.min(width / (span * 1.72), height / (span * 1.18));
  shapePreviewState.camera.zoom = Math.max(1.15, Math.min(10, fitZoom * shapePreviewState.zoomFactor));
  shapePreviewState.camera.updateProjectionMatrix();
}

function setShapeCamera(span) {
  if (!shapePreviewState) {
    return;
  }
  shapePreviewState.span = span;
  shapePreviewState.camera.position.set(span * 0.58, -span * 0.78, span * 0.55);
  shapePreviewState.camera.lookAt(0, 0, 0);
  resizeShapePreview();
}

function resetShapeView() {
  if (!shapePreviewState) {
    return;
  }
  shapePreviewState.group.rotation.x = SHAPE_DEFAULT_ROTATION.x;
  shapePreviewState.group.rotation.z = SHAPE_DEFAULT_ROTATION.z;
  shapePreviewState.zoomFactor = 1;
  setShapeCamera(shapePreviewState.span);
}

function zoomShape(multiplier) {
  if (!shapePreviewState) {
    return;
  }
  shapePreviewState.zoomFactor = Math.max(0.65, Math.min(3.2, shapePreviewState.zoomFactor * multiplier));
  resizeShapePreview();
}

function animateShapePreview() {
  if (!shapePreviewState) {
    return;
  }
  updatePredictionFlowAnimation(performance.now());
  shapePreviewState.renderer.render(shapePreviewState.scene, shapePreviewState.camera);
  shapeAnimationFrame = window.requestAnimationFrame(animateShapePreview);
}

function initShapeEngine() {
  if (shapePreviewState || !THREE || !shapeVisual) {
    return;
  }
  shapeVisual.innerHTML = "";
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xf8fbfd);
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 5000);
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setClearColor(0xf8fbfd, 1);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  shapeVisual.appendChild(renderer.domElement);

  const group = new THREE.Group();
  group.rotation.x = SHAPE_DEFAULT_ROTATION.x;
  group.rotation.z = SHAPE_DEFAULT_ROTATION.z;
  scene.add(group);

  const ambient = new THREE.HemisphereLight(0xffffff, 0xc8d4df, 2.2);
  scene.add(ambient);
  const keyLight = new THREE.DirectionalLight(0xffffff, 2.6);
  keyLight.position.set(80, -120, 150);
  scene.add(keyLight);
  const rimLight = new THREE.DirectionalLight(0xbfefff, 1.1);
  rimLight.position.set(-120, 80, 90);
  scene.add(rimLight);
  const grid = new THREE.GridHelper(220, 12, 0xc5d6e5, 0xe2ebf2);
  grid.rotation.x = Math.PI / 2;
  grid.position.z = -0.9;
  scene.add(grid);

  shapePreviewState = {
    scene,
    camera,
    renderer,
    group,
    objects: [],
    predictionFlow: null,
    pointer: { active: false, x: 0, y: 0 },
    span: 320,
    zoomFactor: 1,
  };

  shapeVisual.addEventListener("pointerdown", (event) => {
    shapePreviewState.pointer.active = true;
    shapePreviewState.pointer.x = event.clientX;
    shapePreviewState.pointer.y = event.clientY;
    shapeVisual.setPointerCapture?.(event.pointerId);
  });
  shapeVisual.addEventListener("pointermove", (event) => {
    if (!shapePreviewState.pointer.active) {
      return;
    }
    const dx = event.clientX - shapePreviewState.pointer.x;
    const dy = event.clientY - shapePreviewState.pointer.y;
    shapePreviewState.group.rotation.z += dx * 0.008;
    shapePreviewState.group.rotation.x += dy * 0.006;
    shapePreviewState.pointer.x = event.clientX;
    shapePreviewState.pointer.y = event.clientY;
  });
  shapeVisual.addEventListener("pointerup", (event) => {
    shapePreviewState.pointer.active = false;
    shapeVisual.releasePointerCapture?.(event.pointerId);
  });
  shapeVisual.addEventListener("pointerleave", () => {
    shapePreviewState.pointer.active = false;
  });
  shapeVisual.addEventListener("pointercancel", () => {
    shapePreviewState.pointer.active = false;
  });
  shapeVisual.addEventListener("wheel", (event) => {
    event.preventDefault();
    zoomShape(event.deltaY > 0 ? 0.9 : 1.1);
  }, { passive: false });

  new ResizeObserver(resizeShapePreview).observe(shapeVisual);
  if (!shapeAnimationFrame) {
    animateShapePreview();
  }
}

function ensureShapeEngine() {
  if (shapeEngineUnavailable) {
    return Promise.resolve();
  }
  if (shapeEnginePromise) {
    return shapeEnginePromise;
  }
  setShapePreviewStatus(IS_KO ? "Parametric preview 로딩 중" : "Loading Parametric preview", true);
  shapeEnginePromise = import("./vendor/three.module.r160.js")
    .then((module) => {
      THREE = module;
      initShapeEngine();
      renderParametricShape(payloadFromForm(), activePredictionFlowData);
      setShapePreviewStatus("", false);
    })
    .catch(() => {
      shapeEngineUnavailable = true;
      shapePreviewState = null;
      shapeVisual.innerHTML = shapeSvg(payloadFromForm(), activePredictionFlowData);
      setShapePreviewStatus("", false);
    });
  return shapeEnginePromise;
}

function makePlateShape(length, width, holeRadius) {
  const shape = new THREE.Shape();
  shape.moveTo(-length / 2, -width / 2);
  shape.lineTo(length / 2, -width / 2);
  shape.lineTo(length / 2, width / 2);
  shape.lineTo(-length / 2, width / 2);
  shape.lineTo(-length / 2, -width / 2);
  if (holeRadius > 0) {
    const hole = new THREE.Path();
    hole.absellipse(0, 0, holeRadius, holeRadius, 0, Math.PI * 2, false);
    shape.holes.push(hole);
  }
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

function addEdges(object, color = 0xe7f2ff) {
  const edges = new THREE.LineSegments(
    new THREE.EdgesGeometry(object.geometry, 24),
    new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.58 })
  );
  edges.position.copy(object.position);
  edges.rotation.copy(object.rotation);
  edges.scale.copy(object.scale);
  shapePreviewState.group.add(edges);
  shapePreviewState.objects.push(edges);
  return edges;
}

function addFlowTube(points, color, radius, opacity = 0.78) {
  const curve = new THREE.CatmullRomCurve3(points);
  const tube = new THREE.Mesh(
    new THREE.TubeGeometry(curve, 48, radius, 12, false),
    new THREE.MeshStandardMaterial({
      color,
      roughness: 0.5,
      transparent: true,
      opacity,
      emissive: color,
      emissiveIntensity: 0.16,
    })
  );
  shapePreviewState.group.add(tube);
  shapePreviewState.objects.push(tube);
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

function fillingColorStops() {
  return [
    [0.0, new THREE.Color(0x074bd8)],
    [0.25, new THREE.Color(0x0092ff)],
    [0.42, new THREE.Color(0x12dfe3)],
    [0.56, new THREE.Color(0x00d45b)],
    [0.70, new THREE.Color(0xd8ea00)],
    [0.84, new THREE.Color(0xff8a00)],
    [1.0, new THREE.Color(0xd40000)],
  ];
}

function fillingVisualFlowFraction(x, y, length, width) {
  const xFlow = (x + length / 2) / Math.max(length, 1e-9);
  const ySpread = Math.abs(y) / Math.max(width / 2, 1e-9);
  const gateHotspot = Math.exp(-((xFlow / 0.14) ** 2 + (ySpread / 0.42) ** 2));
  const stream = Math.max(0, Math.min(1, xFlow + Math.max(0, ySpread - 0.12) * 0.12));
  return Math.max(0, Math.min(1, stream ** 1.55 - gateHotspot * 0.08));
}

function applyFillingVertexColors(geometry, length, width, summary) {
  if (!summary?.bins?.length) {
    return false;
  }
  const stats = summary.stats || {};
  const minPressure = Number(stats.min_MPa) || 0;
  const maxPressure = Math.max(Number(stats.max_MPa) || 0, minPressure + 1e-9);
  const colorStops = fillingColorStops();
  const positions = geometry.getAttribute("position");
  const colors = [];
  for (let index = 0; index < positions.count; index += 1) {
    const x = positions.getX(index);
    const y = positions.getY(index);
    const pressure = pressureFromDistribution(summary, fillingVisualFlowFraction(x, y, length, width));
    const normalized = pressure === null ? 0 : (pressure - minPressure) / Math.max(maxPressure - minPressure, 1e-9);
    const color = interpolateColor(colorStops, normalized);
    colors.push(color.r, color.g, color.b);
  }
  geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  return true;
}

function predictionFillingSummary(predictionData) {
  return predictionData?.predicted_filling_pressure || predictionData?.filling_pressure || null;
}

function normalizedPredictionPressure(summary, flowFraction) {
  const pressure = pressureFromDistribution(summary, flowFraction);
  const maxPressure = Math.max(Number(summary?.stats?.max_MPa) || 0, 1e-9);
  return pressure == null ? 0.38 : Math.max(0, Math.min(1, pressure / maxPressure));
}

function addPredictionHeatLayer(payload, predictionData, dimensions) {
  const summary = predictionFillingSummary(predictionData);
  if (!summary?.bins?.length) {
    return [];
  }
  const { length, width, holeRadius, zTop } = dimensions;
  const colorStops = fillingColorStops();
  const heatObjects = [];
  const xCells = 32;
  const yCells = 13;
  const cellLength = length / xCells;
  const cellWidth = width / yCells;
  const geometry = new THREE.PlaneGeometry(cellLength * 0.96, cellWidth * 0.88);
  for (let xi = 0; xi < xCells; xi += 1) {
    for (let yi = 0; yi < yCells; yi += 1) {
      const yNorm = (yi + 0.5) / yCells;
      const x = -length / 2 + cellLength * (xi + 0.5);
      const y = -width / 2 + cellWidth * (yi + 0.5);
      if (Math.hypot(x, y) < holeRadius * 1.18) {
        continue;
      }
      const xProgress = (xi + 0.5) / xCells;
      const edgeDelay = Math.abs(yNorm - 0.5) * 0.16;
      const holeWake = x > -holeRadius * 1.35 && x < holeRadius * 1.8
        ? Math.max(0, 1 - Math.abs(y) / Math.max(holeRadius * 1.8, 1)) * 0.1
        : 0;
      const flowFraction = Math.max(0, Math.min(1, xProgress + edgeDelay + holeWake));
      const pressureNorm = normalizedPredictionPressure(summary, flowFraction);
      const pressureDrop = Math.max(0.64, 1 - flowFraction * 0.28);
      const centerWeight = Math.max(0.46, 1 - Math.abs(yNorm - 0.5) * 0.9);
      const intensity = Math.max(0, Math.min(1, pressureNorm * pressureDrop * centerWeight));
      const material = new THREE.MeshBasicMaterial({
        color: interpolateColor(colorStops, intensity),
        transparent: true,
        opacity: 0.05,
        depthWrite: false,
        side: THREE.DoubleSide,
      });
      const cell = new THREE.Mesh(geometry.clone(), material);
      cell.position.set(x, y, zTop + 0.08);
      cell.userData.flowFraction = flowFraction;
      cell.userData.baseOpacity = 0.1 + intensity * 0.32;
      cell.userData.phase = (xi / xCells) * 0.72 + (yi / yCells) * 0.18;
      shapePreviewState.group.add(cell);
      shapePreviewState.objects.push(cell);
      heatObjects.push(cell);
    }
  }
  geometry.dispose();
  return heatObjects;
}

function fillFrontSegments(x, width, holeRadius) {
  const margin = width * 0.08;
  const yMin = -width / 2 + margin;
  const yMax = width / 2 - margin;
  const clearance = holeRadius * 1.22;
  if (Math.abs(x) >= clearance) {
    return [[yMin, yMax]];
  }
  const gap = Math.sqrt(Math.max(0, clearance * clearance - x * x));
  return [
    [yMin, Math.min(-gap, yMax)],
    [Math.max(gap, yMin), yMax],
  ].filter(([start, end]) => end - start > width * 0.08);
}

function addPredictionFrontBand(x, dimensions, color, opacity, phase) {
  const { length, width, holeRadius, zTop } = dimensions;
  const flowFraction = Math.max(0, Math.min(1, (x + length / 2) / length));
  const z = zTop + Math.max(0.42, dimensions.thickness * 0.1);
  const radius = Math.max(0.45, Math.min(1.2, width * 0.0032));
  const bands = [];
  fillFrontSegments(x, width, holeRadius).forEach(([y0, y1]) => {
    const curve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(x - length * 0.012, y0, z),
      new THREE.Vector3(x + length * 0.006, (y0 + y1) / 2, z + 0.18),
      new THREE.Vector3(x - length * 0.012, y1, z),
    ]);
    const material = new THREE.MeshStandardMaterial({
      color,
      roughness: 0.36,
      transparent: true,
      opacity,
      depthWrite: false,
      emissive: color,
      emissiveIntensity: 0.34,
    });
    const band = new THREE.Mesh(
      new THREE.TubeGeometry(curve, 24, radius, 8, false),
      material
    );
    band.userData.baseOpacity = opacity;
    band.userData.phase = phase;
    band.userData.flowFraction = flowFraction;
    shapePreviewState.group.add(band);
    shapePreviewState.objects.push(band);
    bands.push(band);
  });
  return bands;
}

function addPredictionTube(points, color, radius, opacity, phase) {
  const curve = new THREE.CatmullRomCurve3(points);
  const material = new THREE.MeshStandardMaterial({
    color,
    roughness: 0.34,
    transparent: true,
    opacity,
    depthWrite: false,
    emissive: color,
    emissiveIntensity: 0.55,
  });
  const tube = new THREE.Mesh(
    new THREE.TubeGeometry(curve, 96, radius, 14, false),
    material
  );
  tube.userData.baseOpacity = opacity;
  tube.userData.phase = phase;
  tube.userData.curve = curve;
  shapePreviewState.group.add(tube);
  shapePreviewState.objects.push(tube);
  return tube;
}

function addPredictionParticle(curve, color, radius, phase) {
  const material = new THREE.MeshStandardMaterial({
    color,
    roughness: 0.22,
    transparent: true,
    opacity: 0.92,
    depthWrite: false,
    emissive: color,
    emissiveIntensity: 0.8,
  });
  const particle = new THREE.Mesh(
    new THREE.SphereGeometry(radius, 18, 12),
    material
  );
  particle.userData.curve = curve;
  particle.userData.phase = phase;
  particle.userData.radius = radius;
  shapePreviewState.group.add(particle);
  shapePreviewState.objects.push(particle);
  return particle;
}

function addPredictionFlowLayer(payload, predictionData, dimensions) {
  const summary = predictionFillingSummary(predictionData);
  if (!summary?.bins?.length || !shapePreviewState) {
    return;
  }
  const { length, width, holeRadius, gateDepth, zTop } = dimensions;
  const maxSprue = Math.max(Number(predictionData?.predicted_max_pressure_MPa) || 0, 1);
  const maxFill = Math.max(Number(summary.stats?.max_MPa) || 0, 1);
  const pressureScale = Math.max(0.75, Math.min(1.45, (maxSprue + maxFill) / 180));
  const colorStops = fillingColorStops();
  const entryColor = maxFill > 70 ? 0xff6a00 : 0xff9d32;
  const radius = Math.max(0.55, Math.min(1.55, width * 0.0048 * pressureScale));
  const z = zTop + Math.max(0.35, dimensions.thickness * 0.08);
  const entryGuides = [
    [
      new THREE.Vector3(-length / 2 - gateDepth * 0.6, 0, z + 0.2),
      new THREE.Vector3(-length * 0.42, -width * 0.16, z + 0.36),
      new THREE.Vector3(-length * 0.28, -width * 0.26, z + 0.32),
    ],
    [
      new THREE.Vector3(-length / 2 - gateDepth * 0.4, 0, z + 0.55),
      new THREE.Vector3(-length * 0.4, width * 0.16, z + 0.38),
      new THREE.Vector3(-length * 0.27, width * 0.26, z + 0.34),
    ],
    [
      new THREE.Vector3(-length / 2 - gateDepth * 0.2, 0, z + 0.25),
      new THREE.Vector3(-length * 0.39, 0, z + 0.42),
      new THREE.Vector3(-length * 0.22, 0, z + 0.38),
    ],
  ];
  const heatObjects = addPredictionHeatLayer(payload, predictionData, dimensions);
  const guideTubes = entryGuides.map((points, index) => addPredictionTube(
    points,
    index === 2 ? 0xffd28f : entryColor,
    radius * (index === 2 ? 0.86 : 0.72),
    index === 2 ? 0.42 : 0.34,
    index * 0.19
  ));
  const frontBands = [];
  const bandCount = 9;
  for (let index = 0; index < bandCount; index += 1) {
    const flowFraction = 0.1 + (index / (bandCount - 1)) * 0.84;
    const x = -length / 2 + length * flowFraction;
    const pressureNorm = normalizedPredictionPressure(summary, flowFraction);
    frontBands.push(...addPredictionFrontBand(
      x,
      dimensions,
      interpolateColor(colorStops, pressureNorm),
      0.52,
      index * 0.08
    ));
  }
  shapePreviewState.predictionFlow = {
    startedAt: performance.now(),
    heatObjects,
    frontBands,
    guideTubes,
  };
}

function updatePredictionFlowAnimation(now) {
  const flow = shapePreviewState?.predictionFlow;
  if (!flow) {
    return;
  }
  const progress = ((now - flow.startedAt) % PREDICTION_FLOW_DURATION_MS) / PREDICTION_FLOW_DURATION_MS;
  const front = Math.min(1, progress * 1.18);
  flow.heatObjects.forEach((cell) => {
    const local = (progress + cell.userData.phase) % 1;
    const pulse = 0.64 + Math.sin(local * Math.PI * 2) * 0.26;
    const reveal = cell.userData.flowFraction <= front ? 1 : 0.12;
    cell.material.opacity = cell.userData.baseOpacity * pulse * reveal;
  });
  (flow.frontBands || []).forEach((band) => {
    const distance = Math.abs(front - band.userData.flowFraction);
    const nearFront = Math.max(0, 1 - distance / 0.16);
    const revealed = band.userData.flowFraction <= front ? 1 : 0.1;
    const pulse = 0.45 + nearFront * 0.72;
    band.material.opacity = band.userData.baseOpacity * Math.max(revealed * 0.42, pulse);
    band.material.emissiveIntensity = 0.18 + nearFront * 0.74;
  });
  (flow.guideTubes || []).forEach((tube) => {
    const local = (progress + tube.userData.phase) % 1;
    const pulse = 0.62 + Math.sin(local * Math.PI * 2) * 0.18;
    tube.material.opacity = tube.userData.baseOpacity * Math.max(0.35, pulse);
    tube.material.emissiveIntensity = 0.18 + pulse * 0.26;
  });
  (flow.particles || []).forEach((particle) => {
    const t = (progress + particle.userData.phase) % 1;
    particle.position.copy(particle.userData.curve.getPoint(t));
    const scale = 0.72 + Math.sin(t * Math.PI) * 0.8;
    particle.scale.setScalar(scale);
    particle.material.opacity = 0.22 + Math.sin(t * Math.PI) * 0.76;
  });
}

function renderParametricShape(payload, predictionData = null) {
  if (!shapePreviewState) {
    if (shapeEngineUnavailable) {
      shapeVisual.innerHTML = shapeSvg(payload, predictionData);
      return;
    }
    shapeVisual.innerHTML = "";
    ensureShapeEngine();
    return;
  }
  clearShapeObjects();
  const rawLength = Number(payload.L_mm);
  const rawWidth = Number(payload.W_mm);
  const rawThickness = Number(payload.t_mm);
  const rawDiameter = Number(payload.D_mm);
  const rawGateWidth = Number(payload.gate_size_width_mm);
  const rawGateHeight = Number(payload.gate_size_height_mm);
  if (![rawLength, rawWidth, rawThickness, rawDiameter, rawGateWidth, rawGateHeight].every((value) => Number.isFinite(value) && value > 0)) {
    setShapePreviewStatus(IS_KO ? "형상 치수를 입력하면 3D preview가 표시됩니다." : "Enter shape dimensions to show the 3D preview.");
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
  const fillingSummary = predictionFillingSummary(predictionData);

  const bodyGeometry = makePlateGeometry(length, width, thickness, holeRadius);
  const hasContour = applyFillingVertexColors(bodyGeometry, length, width, fillingSummary);
  const plate = new THREE.Mesh(
    bodyGeometry,
    hasContour
      ? new THREE.MeshBasicMaterial({
          color: 0xffffff,
          vertexColors: true,
          side: THREE.DoubleSide,
        })
      : new THREE.MeshStandardMaterial({
          color: 0x86c3df,
          roughness: 0.62,
          metalness: 0.04,
        })
  );
  shapePreviewState.group.add(plate);
  shapePreviewState.objects.push(plate);
  addEdges(plate, 0x34556d);

  const gate = new THREE.Mesh(
    new THREE.BoxGeometry(gateWidth, gateDepth, gateHeight),
    new THREE.MeshStandardMaterial({
      color: 0xd40000,
      roughness: 0.5,
      metalness: 0.02,
    })
  );
  gate.rotation.z = Math.PI / 2;
  gate.position.set(-length / 2 - gateDepth / 2 + gateOverlap, 0, thickness / 2 - gateHeight / 2);
  shapePreviewState.group.add(gate);
  shapePreviewState.objects.push(gate);
  addEdges(gate, 0x7a0000);

  const span = Math.max(length + gateDepth * 3, width, thickness * 8);
  shapePreviewState.group.rotation.x = SHAPE_DEFAULT_ROTATION.x;
  shapePreviewState.group.rotation.z = SHAPE_DEFAULT_ROTATION.z;
  shapePreviewState.zoomFactor = 1;
  setShapeCamera(span);

  const clamped = holeRadius !== rawDiameter / 2 || gateWidth !== rawGateWidth || gateHeight !== rawGateHeight;
  setShapePreviewStatus(
    clamped
      ? (IS_KO ? "Preview는 표시를 위해 불가능한 치수를 일부 제한했습니다." : "Preview clamps impossible dimensions for display.")
      : "",
    clamped
  );
}

function shapeSvg(payload, predictionData = null) {
  const length = Math.max(1, payload.L_mm);
  const width = Math.max(1, payload.W_mm);
  const hole = Math.max(1, payload.D_mm);
  const gateWidth = Math.max(4, payload.gate_size_width_mm);
  const thickness = Math.max(0.2, payload.t_mm);
  const plateW = 520;
  const plateH = Math.max(150, Math.min(250, plateW * (width / length)));
  const holeR = Math.max(14, Math.min(plateH * 0.32, plateH * (hole / width) * 0.5));
  const gateH = Math.max(18, Math.min(48, plateH * 0.14));
  const gateW = Math.max(30, Math.min(108, plateW * (gateWidth / length)));
  const x = 104;
  const y = Math.max(82, Math.min(114, (430 - plateH) / 2 - 4));
  const depthX = 34;
  const depthY = 28;
  const holeCx = x + plateW * 0.56;
  const holeCy = y + plateH * 0.5;
  const gateX = x - gateW + 5;
  const gateY = y + plateH * 0.5 - gateH / 2;
  const lengthLabel = `L ${formatMetric(length, 1)} mm`;
  const widthLabel = `W ${formatMetric(width, 1)} mm`;
  const holeLabel = `D ${formatMetric(hole, 1)} mm`;
  const gateLabel = `Gate ${formatMetric(gateWidth, 1)} mm`;
  const thicknessLabel = `t ${formatMetric(thickness, 2)} mm`;
  const predictedSummary = predictionFillingSummary(predictionData);
  const predictedMax = Math.max(
    Number(predictionData?.predicted_max_pressure_MPa) || 0,
    Number(predictedSummary?.stats?.max_MPa) || 0
  );
  const frontStart = x + 20;
  const frontEnd = x + plateW - 20;
  const predictionOverlay = predictedSummary?.bins?.length ? `
      <clipPath id="inj-v2-fill-front-clip">
        <rect x="${x + 12}" y="${y + 12}" width="0" height="${plateH - 24}" rx="14">
          <animate attributeName="width" values="0;${plateW - 24};${plateW - 24}" dur="3.2s" repeatCount="indefinite" />
        </rect>
      </clipPath>
      <g class="predicted-flow-svg" clip-path="url(#inj-v2-fill-front-clip)">
        <rect x="${x + 12}" y="${y + 12}" width="${plateW - 24}" height="${plateH - 24}" rx="14" fill="#1fe3ff" opacity="0.13" />
        <rect x="${x + 12}" y="${y + 12}" width="${plateW * 0.28}" height="${plateH - 24}" rx="14" fill="#ff9a32" opacity="0.16" />
        <rect x="${x + plateW * 0.34}" y="${y + 12}" width="${plateW * 0.22}" height="${plateH - 24}" fill="#e6ec37" opacity="0.1" />
        <rect x="${x + plateW * 0.62}" y="${y + 12}" width="${plateW * 0.3}" height="${plateH - 24}" rx="14" fill="#168cff" opacity="0.11" />
      </g>
      <g class="predicted-flow-svg">
        <line x1="${frontStart}" y1="${y + 22}" x2="${frontStart}" y2="${holeCy - holeR - 16}" stroke="#ffffff" stroke-width="6" stroke-linecap="round" opacity="0.78">
          <animate attributeName="x1" values="${frontStart};${frontEnd};${frontEnd}" dur="3.2s" repeatCount="indefinite" />
          <animate attributeName="x2" values="${frontStart};${frontEnd};${frontEnd}" dur="3.2s" repeatCount="indefinite" />
          <animate attributeName="opacity" values="0.16;0.82;0.2" dur="3.2s" repeatCount="indefinite" />
        </line>
        <line x1="${frontStart}" y1="${holeCy + holeR + 16}" x2="${frontStart}" y2="${y + plateH - 22}" stroke="#ffffff" stroke-width="6" stroke-linecap="round" opacity="0.78">
          <animate attributeName="x1" values="${frontStart};${frontEnd};${frontEnd}" dur="3.2s" repeatCount="indefinite" />
          <animate attributeName="x2" values="${frontStart};${frontEnd};${frontEnd}" dur="3.2s" repeatCount="indefinite" />
          <animate attributeName="opacity" values="0.16;0.82;0.2" dur="3.2s" repeatCount="indefinite" />
        </line>
        <path d="M${x + 8} ${holeCy} C ${x + 88} ${holeCy - 38}, ${x + 140} ${holeCy - 58}, ${x + 190} ${holeCy - 70}" fill="none" stroke="#ffb15f" stroke-width="7" stroke-linecap="round" opacity="0.36" />
        <path d="M${x + 8} ${holeCy} C ${x + 88} ${holeCy + 38}, ${x + 140} ${holeCy + 58}, ${x + 190} ${holeCy + 70}" fill="none" stroke="#ffb15f" stroke-width="7" stroke-linecap="round" opacity="0.28" />
        <circle cx="${holeCx}" cy="${holeCy}" r="${holeR + 17}" fill="none" stroke="#ffffff" stroke-width="5" opacity="0.26" stroke-dasharray="18 16" />
        <text class="part-label" x="${x + 16}" y="${y + plateH - 18}">${IS_KO ? "예측 압력 Map" : "Predicted pressure map"} ${formatMetric(predictedMax, 1)} MPa</text>
      </g>
  ` : "";
  return `
    <svg class="shape-svg" viewBox="0 0 720 430" role="img" aria-label="Parametric injection mold preview">
      <defs>
        <linearGradient id="inj-v2-plate" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0" stop-color="#f5fbff" />
          <stop offset="0.48" stop-color="#bdd4e6" />
          <stop offset="1" stop-color="#88a7bf" />
        </linearGradient>
        <linearGradient id="inj-v2-side" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0" stop-color="#7f9bb3" />
          <stop offset="1" stop-color="#526d84" />
        </linearGradient>
        <linearGradient id="inj-v2-flow" x1="0" x2="1">
          <stop offset="0" stop-color="#ff7a1a" />
          <stop offset="1" stop-color="#1763ff" />
        </linearGradient>
        <marker id="inj-v2-arrow" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">
          <path d="M0,0 L8,4 L0,8 Z" fill="#d8ecff" />
        </marker>
      </defs>
      <path d="M${x} ${y + plateH} L${x + depthX} ${y + plateH + depthY} L${x + plateW + depthX} ${y + plateH + depthY} L${x + plateW} ${y + plateH} Z" fill="url(#inj-v2-side)" opacity="0.82" />
      <path d="M${x + plateW} ${y} L${x + plateW + depthX} ${y + depthY} L${x + plateW + depthX} ${y + plateH + depthY} L${x + plateW} ${y + plateH} Z" fill="#6d879d" opacity="0.8" />
      <rect x="${x}" y="${y}" width="${plateW}" height="${plateH}" rx="18" fill="url(#inj-v2-plate)" stroke="#e5f0f8" stroke-width="4" />
      <rect x="${gateX}" y="${gateY}" width="${gateW}" height="${gateH}" rx="8" fill="#ff7a1a" stroke="#ffe0c6" stroke-width="3" />
      <circle cx="${holeCx}" cy="${holeCy}" r="${holeR}" fill="#21364c" opacity="0.96" />
      <circle cx="${holeCx}" cy="${holeCy}" r="${holeR + 8}" fill="none" stroke="#ffffff" stroke-width="4" opacity="0.58" />
      <path d="M${x + 10} ${holeCy} C ${x + 78} ${holeCy - 30}, ${x + 132} ${holeCy - 48}, ${x + 190} ${holeCy - 62}" fill="none" stroke="url(#inj-v2-flow)" stroke-width="8" stroke-linecap="round" opacity="0.46" />
      <path d="M${x + 18} ${holeCy + 20} C ${x + 92} ${holeCy + 48}, ${x + 138} ${holeCy + 64}, ${x + 190} ${holeCy + 72}" fill="none" stroke="#ffb15f" stroke-width="6" stroke-linecap="round" opacity="0.36" />
      <path d="M${x + 12} ${holeCy} C ${x + 86} ${holeCy}, ${x + 134} ${holeCy}, ${x + 194} ${holeCy}" fill="none" stroke="#ffd28f" stroke-width="5" stroke-linecap="round" opacity="0.32" />
      ${predictionOverlay}
      <line x1="${x}" y1="${y + plateH + 58}" x2="${x + plateW}" y2="${y + plateH + 58}" stroke="#d8ecff" stroke-width="2" marker-start="url(#inj-v2-arrow)" marker-end="url(#inj-v2-arrow)" />
      <line x1="${x + plateW + 64}" y1="${y}" x2="${x + plateW + 64}" y2="${y + plateH}" stroke="#d8ecff" stroke-width="2" marker-start="url(#inj-v2-arrow)" marker-end="url(#inj-v2-arrow)" />
      <line x1="${holeCx}" y1="${holeCy}" x2="${holeCx + holeR + 62}" y2="${holeCy - holeR - 30}" stroke="#edf6ff" stroke-width="2" opacity="0.72" />
      <line x1="${gateX + gateW * 0.5}" y1="${gateY}" x2="${gateX + gateW * 0.5}" y2="${gateY - 42}" stroke="#ffe7d1" stroke-width="2" opacity="0.74" />
      <text class="dimension-label" x="${x + plateW / 2 - 56}" y="${y + plateH + 84}">${lengthLabel}</text>
      <text class="dimension-label" x="${x + plateW + 76}" y="${y + plateH / 2 + 5}" transform="rotate(90 ${x + plateW + 76} ${y + plateH / 2 + 5})">${widthLabel}</text>
      <text class="dimension-label" x="${x + plateW + 12}" y="${y + plateH + depthY + 24}">${thicknessLabel}</text>
      <text class="part-label" x="${x + 18}" y="${y + 30}">${geometrySelect.value || "-"}</text>
      <text class="small-label" x="${gateX - 4}" y="${gateY - 50}">${gateLabel}</text>
      <text class="small-label" x="${holeCx + holeR + 66}" y="${holeCy - holeR - 28}">${holeLabel}</text>
      <text class="part-label" x="${gateX + 8}" y="${gateY + gateH / 2 + 5}">Gate</text>
      <text class="part-label" x="${holeCx - 25}" y="${holeCy + 5}">Hole</text>
    </svg>
  `;
}

function updateShapePreview(options = {}) {
  const { preservePredictionFlow = false } = options;
  const payload = payloadFromForm();
  if (!preservePredictionFlow) {
    activePredictionFlowData = null;
  }
  renderParametricShape(payload, preservePredictionFlow ? activePredictionFlowData : null);
  activeRun.textContent = `${geometrySelect.value || "-"} / ${processSelect.value || "-"}`;
  previewTitle.textContent = IS_KO ? "Parametric DOE 미리보기" : "Parametric DOE preview";
  previewCopy.textContent = IS_KO
    ? `DOE 치수 기반 parametric preview: ${geometrySelect.value || "-"}`
    : `Parametric preview from DOE dimensions: ${geometrySelect.value || "-"}`;
  metricL.textContent = `${formatMetric(payload.L_mm, 1)} mm`;
  metricW.textContent = `${formatMetric(payload.W_mm, 1)} mm`;
  metricT.textContent = `${formatMetric(payload.t_mm, 2)} mm`;
  metricD.textContent = `${formatMetric(payload.D_mm, 1)} mm`;
  updateProcessReadouts();
  updateGeometryReadouts();
  updatePreventionCheck();
}

function renderPredictionFlowPreview(data) {
  const payload = {
    ...payloadFromForm(),
    ...(data.inputs || {}),
    model: data.model_key || modelSelect.value,
    filling_model: data.filling_model_key || fillingModelSelect.value,
  };
  const filling = predictionFillingSummary(data);
  activePredictionFlowData = filling?.bins?.length ? data : null;
  renderParametricShape(payload, activePredictionFlowData);
  const geometryId = data.inputs?.geometry_id || geometrySelect.value || "-";
  const processId = data.inputs?.process_id || processSelect.value || "-";
  const maxSprue = Number(data.predicted_max_pressure_MPa);
  const maxFill = Number(filling?.stats?.max_MPa);
  activeRun.textContent = activePredictionFlowData
    ? `${geometryId} / ${processId} · ${formatMetric(Math.max(maxSprue || 0, maxFill || 0), 1)} MPa`
    : `${geometryId} / ${processId}`;
  previewTitle.textContent = activePredictionFlowData
    ? (IS_KO ? "예측 Filling Pressure preview" : "Predicted filling pressure preview")
    : (IS_KO ? "Parametric DOE 미리보기" : "Parametric DOE preview");
  previewCopy.textContent = activePredictionFlowData
    ? (IS_KO
      ? `Surrogate 결과의 Filling Pressure 분포를 게이트 기준 fill-front map으로 표시합니다. Sprue peak ${formatMetric(maxSprue, 2)} MPa.`
      : `Surrogate filling pressure is shown as a gate-based fill-front map. Sprue peak ${formatMetric(maxSprue, 2)} MPa.`)
    : (IS_KO
      ? "Filling Pressure 결과가 없어 기본 parametric preview만 표시합니다."
      : "No filling pressure result was returned, so the default parametric preview remains visible.");
}

function drawEmptyCurve(message = TEXT.noCurve) {
  const ctx = pressureCanvas.getContext("2d");
  const { width, height } = pressureCanvas;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#f8fbfd";
  ctx.fillRect(0, 0, width, height);
  ctx.fillStyle = "#637184";
  ctx.font = "14px system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(message, width / 2, height / 2);
}

function drawPressureCurve(points) {
  if (!points || points.length < 2) {
    drawEmptyCurve();
    return;
  }
  const ctx = pressureCanvas.getContext("2d");
  const { width, height } = pressureCanvas;
  const pad = { left: 58, right: 18, top: 22, bottom: 44 };
  const times = points.map((point) => Number(point.time_s));
  const pressures = points.map((point) => Number(point.sprue_pressure_MPa));
  const minT = Math.min(...times);
  const maxT = Math.max(...times);
  const minP = Math.min(0, ...pressures);
  const maxP = Math.max(...pressures, 1) * 1.06;
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const sx = (time) => pad.left + ((time - minT) / Math.max(maxT - minT, 1e-9)) * plotW;
  const sy = (pressure) => pad.top + (1 - (pressure - minP) / Math.max(maxP - minP, 1e-9)) * plotH;

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#f8fbfd";
  ctx.fillRect(0, 0, width, height);

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
    const yValue = minP + ((maxP - minP) * i) / 4;
    const y = sy(yValue);
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
    const xValue = minT + ((maxT - minT) * i) / 4;
    ctx.fillText(formatMetric(xValue, 2), sx(xValue), height - pad.bottom + 10);
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
    const x = sx(Number(point.time_s));
    const y = sy(Number(point.sprue_pressure_MPa));
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

window.addEventListener("injection:curve-tab-activated", () => {
  if (!latestPredictionData) {
    return;
  }
  requestAnimationFrame(() => drawPressureCurve(latestPredictionData.curve || []));
});

function renderFillingPressure(summary) {
  fillingHistogram.innerHTML = "";
  if (!summary || !summary.bins || !summary.bins.length) {
    fillingHistogram.textContent = TEXT.noFilling;
    fillingMax.textContent = "-";
    return;
  }
  const bins = summary.bins;
  const maxRatio = Math.max(...bins.map((bin) => Number(bin.volume_ratio_pct)), 1);
  fillingMax.textContent = `${formatMetric(summary.stats?.max_MPa, 2)} MPa`;
  bins.forEach((bin) => {
    const row = document.createElement("div");
    row.className = "filling-row";
    row.innerHTML = `
      <span>G${bin.group}</span>
      <i style="--bar: ${(Number(bin.volume_ratio_pct) / maxRatio) * 100}%"></i>
      <strong>${formatMetric(bin.volume_ratio_pct, 1)}%</strong>
    `;
    fillingHistogram.appendChild(row);
  });
}

function renderNotes(data) {
  notes.innerHTML = "";
  [...(data.validation_warnings || []), ...(data.notes || []).map((message) => ({ message }))].forEach((item) => {
    const li = document.createElement("li");
    li.textContent = localizeRuntimeNote(item.message || String(item));
    notes.appendChild(li);
  });
}

function localizeRuntimeNote(message) {
  if (!IS_KO) {
    return message;
  }
  const translations = {
    "Current model is trained on 360 Moldex3D cases covering G01-G42.": "현재 모델은 G01-G42 범위의 360개 Moldex3D DOE 케이스로 학습되었습니다.",
    "Use the classical surrogate as the practical default for this Simple Injection DOE set.": "이 Simple Injection DOE 세트에서는 Machine Learning surrogate를 기본 모델로 사용하는 것이 가장 실용적입니다.",
    "The GointMLP-style model is a deep-learning baseline and is less stable than the classical surrogate on this DOE set.": "GointMLP-style 모델은 딥러닝 baseline이며, 이 DOE 세트에서는 Machine Learning surrogate보다 안정성이 낮을 수 있습니다.",
    "The DeepONet model is an operator-learning research model for smoother curve behavior on user-edited DOE conditions.": "DeepONet 모델은 사용자가 수정한 DOE 조건에서 더 부드러운 곡선 거동을 보기 위한 operator-learning 연구 모델입니다.",
  };
  return translations[message] || message;
}

function loadPredictionHistory() {
  try {
    const raw = localStorage.getItem(INJECTION_HISTORY_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.slice(0, 5) : [];
  } catch {
    return [];
  }
}

function savePredictionHistory(runs) {
  try {
    localStorage.setItem(INJECTION_HISTORY_KEY, JSON.stringify(runs.slice(0, 5)));
  } catch {
    // Ignore storage failures; prediction still works.
  }
}

function predictionHistorySignature(run) {
  return [
    run.geometryId,
    run.processId,
    run.modelKey,
    run.fillingModelKey,
    run.meltTempC,
    run.injectionTimeS,
    run.packingPressureMPa,
  ].join("|");
}

function makePredictionHistoryRun(data) {
  const inputs = data.inputs || {};
  return {
    geometryId: inputs.geometry_id || geometrySelect.value || "-",
    processId: inputs.process_id || processSelect.value || "-",
    modelKey: data.model_key || modelSelect.value || "",
    fillingModelKey: data.filling_model_key || fillingModelSelect.value || "",
    modelLabel: MODEL_LABELS[data.model_key] || data.model_label || "-",
    fillingModelLabel: MODEL_LABELS[data.filling_model_key] || data.filling_model_label || "-",
    meltTempC: inputs.melt_temp_C ?? form.elements.melt_temp_C?.value ?? "-",
    injectionTimeS: inputs.injection_time_s ?? form.elements.injection_time_s?.value ?? "-",
    packingPressureMPa: inputs.packing_pressure_MPa ?? form.elements.packing_pressure_MPa?.value ?? "-",
    pressureMPa: data.predicted_max_pressure_MPa ?? null,
    createdAt: new Date().toISOString(),
  };
}

function addPredictionHistory(data) {
  const run = makePredictionHistoryRun(data);
  const signature = predictionHistorySignature(run);
  const runs = [run, ...loadPredictionHistory().filter((item) => predictionHistorySignature(item) !== signature)];
  savePredictionHistory(runs);
  renderPredictionHistory();
}

function applyPredictionHistoryRun(run) {
  if (run.geometryId) {
    geometrySelect.value = run.geometryId;
    applyGeometry(run.geometryId);
  }
  if (run.processId) {
    processSelect.value = run.processId;
    applyProcess(run.processId);
  }
  if (run.modelKey) {
    modelSelect.value = run.modelKey;
  }
  if (run.fillingModelKey) {
    fillingModelSelect.value = run.fillingModelKey;
  }
  updateShapePreview();
  updatePreventionCheck();
}

function renderPredictionHistory() {
  if (!historyCard || !historyList) {
    return;
  }
  const runs = loadPredictionHistory();
  historyList.innerHTML = "";
  if (!runs.length) {
    const empty = document.createElement("p");
    empty.className = "history-empty";
    empty.textContent = TEXT.historyEmpty;
    historyList.appendChild(empty);
  } else {
    runs.forEach((run, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `history-run${index === 0 ? " latest" : ""}`;
      button.innerHTML = `
        <span>${index === 0 ? TEXT.historyLatest : `#${index + 1}`}</span>
        <strong>${run.geometryId} / ${run.processId}</strong>
        <small>${formatMetric(run.meltTempC, 1)} C · ${formatMetric(run.injectionTimeS, 3)} s · ${formatMetric(run.packingPressureMPa, 1)} MPa</small>
        <em>${run.modelLabel} · ${run.fillingModelLabel}${run.pressureMPa == null ? "" : ` · ${formatMetric(run.pressureMPa, 2)} MPa`}</em>
      `;
      button.addEventListener("click", () => applyPredictionHistoryRun(run));
      historyList.appendChild(button);
    });
  }
  historyCard.classList.remove("hidden");
  if (historyClear) {
    historyClear.disabled = runs.length === 0;
  }
}

function xaiCategoryLabel(category) {
  const labels = {
    geometry: IS_KO ? "형상" : "Geometry",
    process: IS_KO ? "공정" : "Process",
    gate: IS_KO ? "게이트" : "Gate",
    derived: IS_KO ? "파생" : "Derived",
    other: IS_KO ? "기타" : "Other",
  };
  return labels[category] || labels.other;
}

function translatedXaiLabel(feature) {
  if (!IS_KO) {
    return feature.label || feature.name;
  }
  if (feature.name?.startsWith("gate_type__")) {
    return `게이트 타입: ${feature.name.split("__", 2)[1] || ""}`;
  }
  return XAI_KO_FEATURES[feature.name]?.[0] || feature.label || feature.name;
}

function translatedXaiExplanation(feature) {
  if (!IS_KO) {
    return feature.explanation || "";
  }
  if (feature.name?.startsWith("gate_type__")) {
    return "게이트 타입을 구분하기 위한 one-hot feature입니다. 입구 경계 조건 차이를 모델이 구분하는 데 사용됩니다.";
  }
  return XAI_KO_FEATURES[feature.name]?.[1] || feature.explanation || "";
}

function translatedPerturbation(perturbation) {
  if (!IS_KO || !perturbation) {
    return perturbation;
  }
  if (perturbation.startsWith("toggled to ")) {
    const value = perturbation.replace("toggled to ", "");
    return `${value}${value === "1" ? "로" : "으로"} 전환`;
  }
  return XAI_KO_COPY.perturbations[perturbation] || perturbation;
}

function renderXaiFeature(feature, totalImportance) {
  const importance = Number(feature.importance) || 0;
  const percent = totalImportance > 0 ? (importance / totalImportance) * 100 : 0;
  const item = document.createElement("article");
  item.className = `xai-feature xai-feature-${feature.category || "other"}`;
  const meta = [
    `${TEXT.currentValue}: ${formatMetric(feature.local_value, 3)}`,
    `${TEXT.sensitivity}: ${formatMetric(feature.local_sensitivity, 5)}`,
    translatedPerturbation(feature.perturbation),
  ].filter(Boolean);
  item.innerHTML = `
    <div class="xai-feature-top">
      <div>
        <strong>${translatedXaiLabel(feature)}</strong>
        <span>${xaiCategoryLabel(feature.category)}</span>
      </div>
      <b>${formatMetric(percent, 1)}%</b>
    </div>
    <i style="--bar: ${Math.max(2, Math.min(100, percent))}%"></i>
    <p>${translatedXaiExplanation(feature)}</p>
    <small>${meta.join(" · ")}</small>
  `;
  return item;
}

function renderXai(xai) {
  if (!xaiCard || !xaiFeatureList) {
    return;
  }
  xaiFeatureList.innerHTML = "";
  xaiNotes.innerHTML = "";
  if (!xai || !Array.isArray(xai.top_features) || !xai.top_features.length) {
    xaiCard.classList.add("hidden");
    return;
  }
  xaiCard.classList.remove("hidden");
  xaiMethod.textContent = IS_KO ? XAI_KO_COPY.method : (xai.feature_set || xai.method || "Local sensitivity");
  xaiSummary.textContent = IS_KO ? XAI_KO_COPY.summary : (xai.summary || TEXT.xaiUnavailable);
  const topFeatures = [...xai.top_features]
    .sort((left, right) => (Number(right.importance) || 0) - (Number(left.importance) || 0));
  const totalImportance = topFeatures.reduce((sum, feature) => sum + Math.max(Number(feature.importance) || 0, 0), 0);
  const visibleFeatures = topFeatures.slice(0, 5);
  const extraFeatures = topFeatures.slice(5);
  visibleFeatures.forEach((feature) => {
    xaiFeatureList.appendChild(renderXaiFeature(feature, totalImportance));
  });
  if (extraFeatures.length) {
    const details = document.createElement("details");
    details.className = "xai-more";
    const summary = document.createElement("summary");
    summary.textContent = TEXT.xaiMore(extraFeatures.length);
    const list = document.createElement("div");
    list.className = "xai-more-list";
    extraFeatures.forEach((feature) => {
      list.appendChild(renderXaiFeature(feature, totalImportance));
    });
    details.append(summary, list);
    xaiFeatureList.appendChild(details);
  }
  (IS_KO ? XAI_KO_COPY.notes : (xai.notes || [])).forEach((note) => {
    const li = document.createElement("li");
    li.textContent = note;
    xaiNotes.appendChild(li);
  });
}

function renderResult(data) {
  latestPredictionData = data;
  emptyState.classList.add("hidden");
  resultPanel.classList.remove("hidden");
  standardResultTabs?.select("summary");
  maxPressure.textContent = `${formatMetric(data.predicted_max_pressure_MPa, 2)} MPa`;
  maxTime.textContent = `${formatMetric(data.predicted_max_time_s, 3)} s`;
  curvePoints.textContent = String(data.curve?.length || 0);
  sprueModelLabel.textContent = MODEL_LABELS[data.model_key] || data.model_label || "-";
  fillingModelLabel.textContent = MODEL_LABELS[data.filling_model_key] || data.filling_model_label || "-";
  const filling = data.predicted_filling_pressure || data.filling_pressure;
  renderFillingPressure(filling);
  drawPressureCurve(data.curve || []);
  renderXai(data.xai);
  renderNotes(data);
  renderPredictionFlowPreview(data);
  const geometryId = data.inputs?.geometry_id;
  const processId = data.inputs?.process_id;
  comparisonSampleId.value = geometryId && processId && geometryId !== CUSTOM_GEOMETRY_ID && processId !== CUSTOM_PROCESS_ID
    ? `${geometryId}_${processId}`
    : "";
  comparisonOutput.classList.add("hidden");
  comparisonOutput.innerHTML = "";
  window.dispatchEvent(new CustomEvent("injection:result-rendered", { detail: { source: "api" } }));
  if (standardResultTabs) {
    requestAnimationFrame(() => resultPanel.parentElement?.scrollIntoView({ behavior: "smooth", block: "start" }));
  }
}

async function submitPrediction(event) {
  event.preventDefault();
  clearError();
  updatePreventionCheck();
  if (hasBlockingValidation) {
    setError(preventionTitle.textContent);
    return;
  }
  setLoading(true);
  try {
    const response = await fetch(`${API_BASE}/predict/sprue-pressure`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payloadFromForm()),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(typeof data.detail === "string" ? data.detail : data.detail?.message || `HTTP ${response.status}`);
    }
    renderResult(data);
    addPredictionHistory(data);
  } catch (error) {
    setError(error.message || "Prediction failed.");
  } finally {
    setLoading(false);
  }
}

function metricCard(label, value) {
  const item = document.createElement("div");
  const labelEl = document.createElement("span");
  const valueEl = document.createElement("strong");
  labelEl.textContent = label;
  valueEl.textContent = value;
  item.append(labelEl, valueEl);
  return item;
}

function renderComparison(data) {
  comparisonOutput.innerHTML = "";
  if (data.sprue_pressure?.metrics) {
    const metrics = data.sprue_pressure.metrics;
    comparisonOutput.append(
      metricCard("Sprue RMSE", `${formatMetric(metrics.rmse_MPa, 2)} MPa`),
      metricCard("Peak error", `${formatMetric(metrics.peak_error_MPa, 2)} MPa`)
    );
  }
  if (data.filling_pressure?.metrics) {
    const metrics = data.filling_pressure.metrics;
    comparisonOutput.append(
      metricCard("Filling MAE", `${formatMetric(metrics.volume_ratio_mae_pct, 2)}%`),
      metricCard("Filling RMSE", `${formatMetric(metrics.volume_ratio_rmse_pct, 2)}%`)
    );
  }
  comparisonOutput.classList.toggle("hidden", comparisonOutput.children.length === 0);
}

async function submitComparison() {
  clearError();
  if (!latestPredictionData) {
    setError(TEXT.compareNeedPrediction);
    return;
  }
  if (!comparisonSprueFile.files[0] && !comparisonFillingFile.files[0]) {
    setError(TEXT.missingUpload);
    return;
  }
  comparisonStatus.textContent = TEXT.compareRunning;
  try {
    const formData = new FormData();
    formData.append("prediction_json", JSON.stringify(latestPredictionData));
    formData.append("sample_id", comparisonSampleId.value || "");
    if (comparisonSprueFile.files[0]) {
      formData.append("sprue_pressure_csv", comparisonSprueFile.files[0]);
    }
    if (comparisonFillingFile.files[0]) {
      formData.append("filling_pressure_csv", comparisonFillingFile.files[0]);
    }
    const response = await fetch(`${API_BASE}/compare/moldex3d`, {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || `HTTP ${response.status}`);
    }
    comparisonStatus.textContent = TEXT.compareReady;
    renderComparison(data);
  } catch (error) {
    comparisonStatus.textContent = IS_KO ? "비교 실패" : "Compare failed";
    setError(error.message || "Comparison failed.");
  }
}

async function postRagJson(path, payload) {
  const response = await fetch(`${RAG_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || `HTTP ${response.status}`);
  }
  return data;
}

function buildAssistantPredictionContext(data) {
  if (!data) {
    return { mode: "Injection Forecast", inputs: {} };
  }
  const filling = data.predicted_filling_pressure || data.filling_pressure || null;
  const topFeatures = Array.isArray(data.xai?.top_features)
    ? data.xai.top_features.map((feature) => ({
      name: feature.name,
      label: IS_KO ? translatedXaiLabel(feature) : feature.label,
      category: feature.category,
      importance: feature.importance,
      local_sensitivity: feature.local_sensitivity,
      local_value: feature.local_value,
      perturbation: IS_KO ? translatedPerturbation(feature.perturbation) : feature.perturbation,
      explanation: IS_KO ? translatedXaiExplanation(feature) : feature.explanation,
    }))
    : [];
  return {
    mode: "Injection Forecast",
    inputs: data.inputs || {},
    model_key: data.model_key || "",
    model_label: data.model_label || "",
    filling_model_key: data.filling_model_key || "",
    filling_model_label: data.filling_model_label || "",
    predicted_max_pressure_MPa: data.predicted_max_pressure_MPa ?? null,
    predicted_max_time_s: data.predicted_max_time_s ?? null,
    curve_points: data.curve?.length || null,
    predicted_filling_max_MPa: filling?.stats?.max_MPa ?? null,
    xai: data.xai ? {
      title: data.xai.title,
      summary: IS_KO ? XAI_KO_COPY.summary : data.xai.summary,
      method: data.xai.method,
      feature_set: IS_KO ? XAI_KO_COPY.method : data.xai.feature_set,
      top_features: topFeatures,
    } : null,
  };
}

function renderRagAnswer(data) {
  if (!ragAnswer) {
    return;
  }
  ragAnswer.classList.remove("hidden");
  ragAnswer.textContent = "";

  const head = document.createElement("div");
  head.className = "rag-answer-head";
  const title = document.createElement("strong");
  title.textContent = TEXT.ragAnswerTitle;
  const actions = document.createElement("div");
  actions.className = "rag-answer-actions";
  const provider = document.createElement("span");
  provider.className = "rag-provider";
  provider.textContent = `${data.provider || "rag"} · ${data.model || "local"}`;
  const citations = Array.isArray(data.citations) ? data.citations : [];
  let citationToggle = null;
  actions.append(provider);
  if (citations.length) {
    citationToggle = document.createElement("button");
    citationToggle.className = "rag-citation-toggle";
    citationToggle.type = "button";
    citationToggle.textContent = TEXT.ragShowCitations;
    citationToggle.setAttribute("aria-expanded", "false");
    actions.append(citationToggle);
  }
  head.append(title, actions);

  const answerText = document.createElement("div");
  answerText.className = "rag-answer-text";
  const answerParagraphs = String(data.answer || "")
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);
  (answerParagraphs.length ? answerParagraphs : [""]).forEach((paragraph, index) => {
    const paragraphNode = document.createElement("article");
    paragraphNode.className = `rag-answer-paragraph${index === 0 ? " lead" : ""}`;
    const badge = document.createElement("span");
    badge.textContent = index === 0 ? TEXT.ragSummary : `${TEXT.ragReasoning} ${index}`;
    const body = document.createElement("p");
    body.textContent = paragraph;
    paragraphNode.append(badge, body);
    answerText.append(paragraphNode);
  });

  const citationBlock = document.createElement("div");
  citationBlock.className = "rag-citations hidden";
  const citationTitle = document.createElement("strong");
  citationTitle.textContent = TEXT.ragCitations;
  citationBlock.append(citationTitle);

  citations.forEach((citation) => {
    const item = document.createElement("div");
    item.className = "rag-citation";
    const itemTitle = document.createElement("strong");
    itemTitle.textContent = `[${citation.index}] ${citation.title}`;
    const source = citation.source && /^https?:\/\//.test(citation.source)
      ? document.createElement("a")
      : document.createElement("span");
    source.textContent = citation.source || citation.source_id || "";
    if (source.tagName === "A") {
      source.href = citation.source;
      source.target = "_blank";
      source.rel = "noreferrer";
    }
    const excerpt = document.createElement("p");
    excerpt.textContent = citation.excerpt || "";
    item.append(itemTitle, source, excerpt);
    citationBlock.append(item);
  });

  citationToggle?.addEventListener("click", () => {
    const isHidden = citationBlock.classList.toggle("hidden");
    citationToggle.textContent = isHidden ? TEXT.ragShowCitations : TEXT.ragHideCitations;
    citationToggle.setAttribute("aria-expanded", String(!isHidden));
  });

  ragAnswer.append(head, answerText, citationBlock);
}

function clearDefaultRagQuestion() {
  if (!ragQueryInput) {
    return;
  }
  const defaultQuery = ragQueryInput.dataset.defaultQuery || "";
  if (ragQueryInput.value.trim() === defaultQuery.trim()) {
    ragQueryInput.value = "";
  }
}

async function loadBootstrapData() {
  apiStatus.textContent = TEXT.checking;
  try {
    const [modelsResponse, doeResponse] = await Promise.all([
      fetch(`${API_BASE}/models`),
      fetch(`${API_BASE}/doe`),
    ]);
    if (!modelsResponse.ok || !doeResponse.ok) {
      throw new Error("API bootstrap failed.");
    }
    const models = await modelsResponse.json();
    const doe = await doeResponse.json();
    geometries = (doe.geometries || []).filter((geometry) => !HIDDEN_GEOMETRY_IDS.has(geometry.id));
    processes = doe.processes || [];
    fillModelSelect(modelSelect, models.sprue_pressure_models || []);
    fillModelSelect(fillingModelSelect, models.filling_pressure_models || []);
    fillDoeSelect(geometrySelect, geometries, "G01");
    fillDoeSelect(processSelect, processes, "P01");
    applyGeometry(geometrySelect.value);
    applyProcess(processSelect.value);
    updateShapePreview();
    apiStatus.textContent = TEXT.apiReady;
    apiStatus.classList.add("ok");
    apiStatus.classList.remove("bad");
  } catch (error) {
    apiStatus.textContent = TEXT.apiOffline;
    apiStatus.classList.add("bad");
    apiStatus.classList.remove("ok");
    setError(error.message || "API offline.");
    drawEmptyCurve();
  }
}

geometrySelect.addEventListener("change", () => {
  applyGeometry(geometrySelect.value);
  updateShapePreview();
});

processSelect.addEventListener("change", () => {
  applyProcess(processSelect.value);
  updateShapePreview();
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
  form.elements[name]?.addEventListener("input", markCustomGeometry);
  form.elements[name]?.addEventListener("change", markCustomGeometry);
});

[
  "melt_temp_C",
  "mold_temp_C",
  "injection_time_s",
  "packing_pressure_MPa",
  "packing_time_s",
].forEach((name) => {
  form.elements[name]?.addEventListener("input", markCustomProcess);
  form.elements[name]?.addEventListener("change", markCustomProcess);
});

form.querySelectorAll("input, select").forEach((control) => {
  control.addEventListener("input", updateShapePreview);
  control.addEventListener("change", updateShapePreview);
});

form.addEventListener("submit", submitPrediction);
comparisonSubmit.addEventListener("click", submitComparison);
shapeZoomIn?.addEventListener("click", () => zoomShape(1.12));
shapeZoomOut?.addEventListener("click", () => zoomShape(0.88));
shapeViewReset?.addEventListener("click", resetShapeView);
historyClear?.addEventListener("click", () => {
  savePredictionHistory([]);
  renderPredictionHistory();
});

if (ragQueryInput) {
  ragQueryInput.addEventListener("focus", clearDefaultRagQuestion, { once: true });
  ragQueryInput.addEventListener("beforeinput", clearDefaultRagQuestion, { once: true });
}

if (ragForm) {
  ragForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearError();
    setLoading(ragForm, true);
    const submitButton = ragForm.querySelector('button[type="submit"]');
    const originalText = submitButton?.textContent || "";
    if (submitButton) {
      submitButton.textContent = TEXT.ragAsking;
    }
    try {
      const formData = new FormData(ragForm);
      const data = await postRagJson("/answer", {
        query: String(formData.get("query") || ""),
        top_k: 5,
        use_llm: formData.get("use_llm") === "on",
        language: IS_KO ? "ko" : "en",
        prediction_context: buildAssistantPredictionContext(latestPredictionData),
      });
      renderRagAnswer(data);
    } catch (error) {
      setError(`${TEXT.ragFailed} ${error.message || error}`);
    } finally {
      if (submitButton) {
        submitButton.textContent = originalText;
      }
      setLoading(ragForm, false);
    }
  });
}

drawEmptyCurve();
standardResultTabs = setupStandardResultTabs();
renderPredictionHistory();
loadBootstrapData();
