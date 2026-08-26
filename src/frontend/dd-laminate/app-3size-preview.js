const API_BASE = `${window.location.origin}/api/v1/dd-laminate`;
const params = new URLSearchParams(window.location.search);
const IS_KO = params.get("lang") === "ko";

const COPY = {
  en: {
    previewEyebrow: "Research preview",
    title: "3-Size Laminate Forecast",
    subtitle: "Compare the grouped-holdout models trained across 6x4, 6x8, and 8x8 panels.",
    training: "Development",
    trainingNote: "718 design groups",
    holdout: "Locked holdout",
    holdoutNote: "182 unseen groups",
    geometry: "Panel sizes",
    curveMode: "Curve mode",
    rawOutput: "Raw model output",
    rawNote: "No force rescaling",
    setupTitle: "Forecast inputs",
    model: "Model",
    case: "Case",
    panelSize: "Panel size (in)",
    quickPresets: "Quick presets",
    panelLength: "Length",
    panelWidth: "Width",
    geometryNote: "The model was trained on 6×4, 6×8, and 8×8 panels. Other sizes are exploratory interpolation or extrapolation.",
    run: "Run preview forecast",
    previewOnly: "Preview only",
    previewOnlyNote: "This page is isolated from the current production model selection.",
    resultTitle: "Raw response forecast",
    emptyTitle: "Ready for a 3-size prediction",
    emptyCopy: "Choose a model and supported panel size, then run the forecast.",
    prediction: "Prediction",
    maxDisplacement: "Max. Displacement",
    maxForce: "Max. Force",
    fitIntersection: "P1 fit Pt",
    predictedPt: "Predicted Pt",
    modelPt: "Model Pt",
    kinkStart: "Kink start",
    curveView: "Curve view",
    reset: "Reset",
    predictedCurve: "Predicted curve",
    linearFits: "Linear fits",
    curveNote: "The dashed lines follow the original P1 method: an initial linear window and a late linear window. The amber diamond is their intersection, the purple line is the detected kink start, and the red point is the independently predicted model Pt. The curve and force scale are not modified.",
    ptConsistentCurveNote: "The dashed lines are predicted P1 linear regions. Their purple intersection is the predicted Pt. The response curve remains the raw model output and is not forced through the Pt or rescaled.",
    outputMode: "Output mode",
    forceScale: "Force scale correction",
    sampleCount: "Training samples",
    apiReady: "API ready",
    apiOffline: "API offline",
    loading: "Loading model…",
    fitDelta: (delta, percent) => `Model Pt − P1 fit Pt: ${delta} kips (${percent})`,
    curvePoint: "Curve point",
  },
  ko: {
    previewEyebrow: "연구용 프리뷰",
    title: "3-Size 적층 예측",
    subtitle: "6×4, 6×8, 8×8 패널로 학습한 고정 Holdout 기반 모델을 비교합니다.",
    training: "개발 데이터",
    trainingNote: "718개 설계 조합",
    holdout: "고정 Holdout",
    holdoutNote: "미학습 182개 조합",
    geometry: "패널 크기",
    curveMode: "곡선 출력",
    rawOutput: "모델 원시 예측",
    rawNote: "Force 재스케일링 없음",
    setupTitle: "예측 조건",
    model: "모델",
    case: "케이스",
    panelSize: "패널 크기 (in)",
    quickPresets: "빠른 선택",
    panelLength: "길이",
    panelWidth: "너비",
    geometryNote: "모델은 6×4, 6×8, 8×8 패널로 학습했습니다. 그 외 크기는 탐색적 보간 또는 외삽 결과입니다.",
    run: "프리뷰 예측 실행",
    previewOnly: "프리뷰 전용",
    previewOnlyNote: "현재 운영 페이지의 모델 선택에는 영향을 주지 않습니다.",
    resultTitle: "원시 응답 예측",
    emptyTitle: "3-size 예측 준비 완료",
    emptyCopy: "모델과 지원 패널 크기를 선택한 다음 예측을 실행하세요.",
    prediction: "예측 결과",
    maxDisplacement: "최대 변위",
    maxForce: "최대 하중",
    fitIntersection: "P1 피팅 Pt",
    predictedPt: "Predicted Pt",
    modelPt: "모델 예측 Pt",
    kinkStart: "굴곡 시작점",
    curveView: "곡선 보기",
    reset: "초기화",
    predictedCurve: "예측 곡선",
    linearFits: "선형 피팅",
    curveNote: "점선은 원본 P1 방식의 초기 선형 구간과 말단 선형 구간입니다. 주황색 마름모는 두 직선의 교점, 보라색 선은 자동 검출된 굴곡 시작점, 빨간 점은 모델이 독립적으로 예측한 Pt입니다. 곡선이나 하중축은 보정하지 않습니다.",
    ptConsistentCurveNote: "점선은 모델이 예측한 P1 초기·말단 선형 구간입니다. 두 직선이 만나는 보라색 교점이 Predicted Pt입니다. 응답 곡선은 원시 모델 출력 그대로이며 Pt를 통과하도록 강제하거나 하중축을 재조정하지 않습니다.",
    outputMode: "출력 방식",
    forceScale: "하중 보정 배율",
    sampleCount: "학습 샘플",
    apiReady: "API 준비됨",
    apiOffline: "API 연결 안 됨",
    loading: "모델 불러오는 중…",
    fitDelta: (delta, percent) => `모델 Pt − P1 피팅 Pt: ${delta} kips (${percent})`,
    curvePoint: "곡선 좌표",
  },
};
const T = IS_KO ? COPY.ko : COPY.en;

const FORMULAS = {
  Case2: "[[±θ₁]/[±θ₂]]₄",
  Case3: "[[±θ₁]/[±θ₂]/[∓θ₁]/[∓θ₂]]₂",
  Case4: "[([±θ₁]/[±θ₂])₂ / ([∓θ₁]/[∓θ₂])₂]",
};

const form = document.querySelector("#preview-form");
const modelSelect = document.querySelector("#model-select");
const modelDescription = document.querySelector("#model-description");
const caseSelect = document.querySelector("#case-select");
const caseFormula = document.querySelector("#case-formula");
const apiStatus = document.querySelector("#api-status");
const languageButton = document.querySelector("#language-button");
const emptyState = document.querySelector("#empty-state");
const resultContent = document.querySelector("#result-content");
const resultModel = document.querySelector("#result-model");
const errorPanel = document.querySelector("#error-panel");
const canvas = document.querySelector("#response-canvas");
const canvasWrap = document.querySelector("#canvas-wrap");
const tooltip = document.querySelector("#curve-tooltip");
const zoomValue = document.querySelector("#zoom-value");
const panelAInput = document.querySelector("#panel-a-input");
const panelBInput = document.querySelector("#panel-b-input");
const panelPresets = [...document.querySelectorAll('input[name="panel"]')];

const modelMetadata = new Map();
const chart = {
  data: null,
  zoom: 1,
  centerX: null,
  centerY: null,
  baseDomain: null,
  viewDomain: null,
  plot: null,
  drag: null,
};

function applyLanguage() {
  document.documentElement.lang = IS_KO ? "ko" : "en";
  document.querySelectorAll("[data-copy]").forEach((element) => {
    const key = element.dataset.copy;
    if (typeof T[key] === "string") {
      element.textContent = T[key];
    }
  });
  languageButton.textContent = IS_KO ? "English" : "한국어";
}

function formatNumber(value, digits = 2) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "–";
  return numeric.toLocaleString(IS_KO ? "ko-KR" : "en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function formatAxis(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "";
  if (Math.abs(numeric) >= 1000) return numeric.toLocaleString("en-US", { maximumFractionDigits: 0 });
  if (Math.abs(numeric) >= 1) return numeric.toFixed(1).replace(/\.0$/, "");
  return numeric.toFixed(3).replace(/0+$/, "").replace(/\.$/, "");
}

function syncPanelPreset() {
  const panelA = Number(panelAInput.value);
  const panelB = Number(panelBInput.value);
  panelPresets.forEach((preset) => {
    const [presetA, presetB] = preset.value.split("x").map(Number);
    preset.checked = Math.abs(panelA - presetA) < 1e-9 && Math.abs(panelB - presetB) < 1e-9;
  });
}

function signedAngle(value) {
  const numeric = Math.round(Number(value) || 0);
  if (numeric > 0) return `+${numeric}°`;
  if (numeric < 0) return `−${Math.abs(numeric)}°`;
  return "0°";
}

function parseAngleValue(value) {
  const rawValue = String(value ?? "").trim();
  if (["", "-", "+", "−"].includes(rawValue)) return null;
  const numeric = Number(rawValue.replace("−", "-"));
  if (!Number.isFinite(numeric)) return null;
  return Math.max(-90, Math.min(90, Math.round(numeric)));
}

function setError(message = "") {
  errorPanel.textContent = message;
  errorPanel.classList.toggle("hidden", !message);
}

function setLoading(loading) {
  const button = form.querySelector("button[type='submit']");
  if (!button.dataset.defaultText) button.dataset.defaultText = button.textContent;
  button.disabled = loading;
  button.textContent = loading ? T.loading : button.dataset.defaultText;
}

function syncAngles(name, value, { writeNumberInput = true } = {}) {
  const clamped = parseAngleValue(value);
  const output = document.querySelector(`#${name}-output`);
  if (clamped === null) {
    if (!writeNumberInput) output.textContent = "–";
    return null;
  }
  if (writeNumberInput) form.elements[name].value = String(clamped);
  document.querySelector(`[data-angle="${name}"]`).value = String(clamped);
  output.textContent = signedAngle(clamped);
  return clamped;
}

function updateModelDescription() {
  modelDescription.textContent = modelMetadata.get(modelSelect.value)?.description || "";
}

async function loadModels() {
  try {
    const response = await fetch(`${API_BASE}/models/3size-preview`, { cache: "no-store" });
    const models = await response.json();
    if (!response.ok) throw new Error(models.detail || `HTTP ${response.status}`);
    modelSelect.innerHTML = "";
    models.forEach((model) => {
      modelMetadata.set(model.key, model);
      const option = document.createElement("option");
      option.value = model.key;
      option.textContent = model.available ? model.label : `${model.label} (missing)`;
      option.disabled = !model.available;
      modelSelect.appendChild(option);
    });
    const first = Array.from(modelSelect.options).find((option) => !option.disabled);
    if (first) modelSelect.value = first.value;
    updateModelDescription();
    apiStatus.textContent = T.apiReady;
    apiStatus.classList.add("ok");
  } catch (error) {
    apiStatus.textContent = T.apiOffline;
    apiStatus.classList.add("bad");
    setError(error.message || String(error));
  }
}

function renderProbabilities(probabilities = {}) {
  const container = document.querySelector("#probabilities");
  container.innerHTML = "";
  [1, 2, 3].forEach((type) => {
    const value = Number(probabilities[`type${type}`] || 0);
    const row = document.createElement("div");
    row.className = "probability-row";
    row.innerHTML = `
      <span>Type ${type}</span>
      <span class="probability-track"><i style="width:${Math.max(0, Math.min(100, value * 100))}%"></i></span>
      <span>${formatNumber(value * 100, 1)}%</span>
    `;
    container.appendChild(row);
  });
}

function lineValue(line, x) {
  if (!line || !Number.isFinite(Number(line.slope)) || !Number.isFinite(Number(line.intercept))) return null;
  return Number(line.slope) * x + Number(line.intercept);
}

function pointAtForce(points, force) {
  if (!points.length || !Number.isFinite(force)) return null;
  for (let index = 1; index < points.length; index += 1) {
    const left = points[index - 1];
    const right = points[index];
    const low = Math.min(left.force, right.force);
    const high = Math.max(left.force, right.force);
    if (force >= low && force <= high && right.force !== left.force) {
      const ratio = (force - left.force) / (right.force - left.force);
      return { x: left.displacement + ratio * (right.displacement - left.displacement), y: force };
    }
  }
  const nearest = points.reduce((best, point) => (
    Math.abs(point.force - force) < Math.abs(best.force - force) ? point : best
  ));
  return { x: nearest.displacement, y: force };
}

function fitGeometry(data) {
  const fit = data?.curve_fit || {};
  const first = fit.first_line;
  const second = fit.second_line;
  const intersection = fit.kink && Number.isFinite(Number(fit.kink.displacement))
    ? { x: Number(fit.kink.displacement), y: Number(fit.kink.force) }
    : null;
  const detectedKink = fit.detected_kink && Number.isFinite(Number(fit.detected_kink.displacement))
    ? { x: Number(fit.detected_kink.displacement), y: Number(fit.detected_kink.force) }
    : null;
  const segments = [];
  if (first) {
    const x1 = Number(fit.first_start_x ?? data.curve[0]?.displacement ?? 0);
    const x2 = Number(fit.first_end_x ?? intersection?.x ?? x1);
    segments.push({ x1, y1: lineValue(first, x1), x2, y2: lineValue(first, x2) });
  }
  if (second) {
    const x1 = Number(fit.second_start_x ?? intersection?.x ?? 0);
    const x2 = Number(fit.second_end_x ?? data.curve.at(-1)?.displacement ?? x1);
    segments.push({ x1, y1: lineValue(second, x1), x2, y2: lineValue(second, x2) });
  }
  return {
    intersection,
    detectedKink,
    segments: segments.filter((segment) => [segment.x1, segment.y1, segment.x2, segment.y2].every(Number.isFinite)),
  };
}

function isPtConsistentResult(data) {
  return data?.metrics?.response_output_mode === "pt_consistent_p1_head_v1";
}

function computeBaseDomain(data) {
  const points = data.curve.map((point) => ({ x: Number(point.displacement), y: Number(point.force) }));
  const fit = fitGeometry(data);
  const predicted = pointAtForce(
    data.curve.map((point) => ({ displacement: Number(point.displacement), force: Number(point.force) })),
    Number(data.predicted_pt),
  );
  const xs = points.map((point) => point.x);
  const ys = points.map((point) => point.y);
  fit.segments.forEach((segment) => {
    xs.push(segment.x1, segment.x2);
    ys.push(segment.y1, segment.y2);
  });
  if (fit.intersection) {
    xs.push(fit.intersection.x);
    ys.push(fit.intersection.y);
  }
  if (fit.detectedKink) {
    xs.push(fit.detectedKink.x);
    ys.push(fit.detectedKink.y);
  }
  if (predicted) {
    xs.push(predicted.x);
    ys.push(predicted.y);
  }
  const xMin = Math.min(0, ...xs);
  const xMax = Math.max(...xs, 0.001);
  const yMin = Math.min(0, ...ys);
  const yMax = Math.max(...ys, 1);
  const xPad = Math.max((xMax - xMin) * 0.035, 0.001);
  const yPad = Math.max((yMax - yMin) * 0.09, 1);
  return { xMin: Math.max(0, xMin - xPad), xMax: xMax + xPad, yMin: Math.min(0, yMin - yPad * 0.15), yMax: yMax + yPad };
}

function resetChartView() {
  chart.zoom = 1;
  if (chart.baseDomain) {
    chart.centerX = (chart.baseDomain.xMin + chart.baseDomain.xMax) / 2;
    chart.centerY = (chart.baseDomain.yMin + chart.baseDomain.yMax) / 2;
  }
  zoomValue.textContent = "100%";
}

function viewDomain() {
  const base = chart.baseDomain;
  const xSpan = (base.xMax - base.xMin) / chart.zoom;
  const ySpan = (base.yMax - base.yMin) / chart.zoom;
  const halfX = xSpan / 2;
  const halfY = ySpan / 2;
  const minCenterX = base.xMin + halfX;
  const maxCenterX = base.xMax - halfX;
  const minCenterY = base.yMin + halfY;
  const maxCenterY = base.yMax - halfY;
  chart.centerX = minCenterX > maxCenterX ? (base.xMin + base.xMax) / 2 : Math.max(minCenterX, Math.min(maxCenterX, chart.centerX));
  chart.centerY = minCenterY > maxCenterY ? (base.yMin + base.yMax) / 2 : Math.max(minCenterY, Math.min(maxCenterY, chart.centerY));
  return {
    xMin: chart.centerX - halfX,
    xMax: chart.centerX + halfX,
    yMin: chart.centerY - halfY,
    yMax: chart.centerY + halfY,
  };
}

function roundedRect(ctx, x, y, width, height, radius) {
  ctx.beginPath();
  ctx.roundRect(x, y, width, height, radius);
}

function drawMarkerLabel(
  ctx,
  { text, value, x, y, color, horizontal = "right", vertical = "above", bounds },
) {
  ctx.save();
  ctx.textAlign = "left";
  ctx.textBaseline = "alphabetic";
  ctx.font = "800 13px Inter, system-ui, sans-serif";
  const valueFont = "900 17px Inter, system-ui, sans-serif";
  const textWidth = ctx.measureText(text).width;
  ctx.font = valueFont;
  const valueWidth = ctx.measureText(value).width;
  const width = Math.max(textWidth, valueWidth, 104) + 22;
  const height = 52;
  const gap = 14;
  let left = horizontal === "left" ? x - width - gap : x + gap;
  let top = vertical === "below" ? y + gap : y - height - gap;
  left = Math.max(bounds.left + 6, Math.min(bounds.right - width - 6, left));
  top = Math.max(bounds.top + 6, Math.min(bounds.bottom - height - 6, top));

  const connectorX = Math.max(left, Math.min(left + width, x));
  const connectorY = Math.max(top, Math.min(top + height, y));
  ctx.beginPath();
  ctx.moveTo(x, y);
  ctx.lineTo(connectorX, connectorY);
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.5;
  ctx.stroke();

  roundedRect(ctx, left, top, width, height, 7);
  ctx.fillStyle = "rgba(255,255,255,0.96)";
  ctx.fill();
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.5;
  ctx.stroke();
  ctx.fillStyle = color;
  ctx.font = "800 13px Inter, system-ui, sans-serif";
  ctx.fillText(text, left + 11, top + 18);
  ctx.font = valueFont;
  ctx.fillText(value, left + 11, top + 41);
  ctx.restore();
}

function drawChart() {
  if (!chart.data) return;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  if (!width || !height) return;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);

  const margin = { left: width < 620 ? 62 : 84, right: 24, top: 28, bottom: 64 };
  const plot = { x: margin.left, y: margin.top, width: width - margin.left - margin.right, height: height - margin.top - margin.bottom };
  const domain = viewDomain();
  chart.viewDomain = domain;
  chart.plot = plot;
  const sx = (x) => plot.x + ((x - domain.xMin) / (domain.xMax - domain.xMin)) * plot.width;
  const sy = (y) => plot.y + plot.height - ((y - domain.yMin) / (domain.yMax - domain.yMin)) * plot.height;

  ctx.fillStyle = "#f8fafc";
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = "#dbe4ee";
  ctx.lineWidth = 1;
  ctx.font = "700 14px Inter, system-ui, sans-serif";
  ctx.fillStyle = "#657389";
  for (let index = 0; index <= 5; index += 1) {
    const ratio = index / 5;
    const x = plot.x + ratio * plot.width;
    const y = plot.y + ratio * plot.height;
    ctx.beginPath(); ctx.moveTo(x, plot.y); ctx.lineTo(x, plot.y + plot.height); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(plot.x, y); ctx.lineTo(plot.x + plot.width, y); ctx.stroke();
    const xValue = domain.xMin + ratio * (domain.xMax - domain.xMin);
    const yValue = domain.yMax - ratio * (domain.yMax - domain.yMin);
    ctx.textAlign = "center";
    ctx.fillText(formatAxis(xValue), x, plot.y + plot.height + 25);
    ctx.textAlign = "right";
    ctx.fillText(formatAxis(yValue), plot.x - 10, y + 5);
  }

  ctx.save();
  ctx.beginPath();
  ctx.rect(plot.x, plot.y, plot.width, plot.height);
  ctx.clip();

  const points = chart.data.curve.map((point) => ({ x: Number(point.displacement), y: Number(point.force) }));
  ctx.strokeStyle = "#087e78";
  ctx.lineWidth = 4;
  ctx.lineJoin = "round";
  ctx.lineCap = "round";
  ctx.beginPath();
  points.forEach((point, index) => {
    const px = sx(point.x); const py = sy(point.y);
    if (index === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
  });
  ctx.stroke();

  const fit = fitGeometry(chart.data);
  const ptConsistent = isPtConsistentResult(chart.data);
  ctx.strokeStyle = "#e23b2f";
  ctx.lineWidth = 2.5;
  ctx.setLineDash([8, 6]);
  fit.segments.forEach((segment) => {
    ctx.beginPath();
    ctx.moveTo(sx(segment.x1), sy(segment.y1));
    ctx.lineTo(sx(segment.x2), sy(segment.y2));
    ctx.stroke();
  });
  ctx.setLineDash([]);

  if (fit.detectedKink) {
    const px = sx(fit.detectedKink.x);
    ctx.strokeStyle = "#7c3aed";
    ctx.lineWidth = 2;
    ctx.setLineDash([8, 7]);
    ctx.beginPath(); ctx.moveTo(px, plot.y); ctx.lineTo(px, plot.y + plot.height); ctx.stroke();
    ctx.setLineDash([]);
  }

  if (fit.intersection) {
    const px = sx(fit.intersection.x);
    const py = sy(fit.intersection.y);
    ctx.save();
    ctx.translate(px, py); ctx.rotate(Math.PI / 4);
    ctx.fillStyle = "white"; ctx.strokeStyle = ptConsistent ? "#7c3aed" : "#d97706"; ctx.lineWidth = 3;
    ctx.fillRect(-6, -6, 12, 12); ctx.strokeRect(-6, -6, 12, 12);
    ctx.restore();
  }

  const predicted = pointAtForce(
    chart.data.curve.map((point) => ({ displacement: Number(point.displacement), force: Number(point.force) })),
    Number(chart.data.predicted_pt),
  );
  if (predicted && !ptConsistent) {
    ctx.beginPath();
    ctx.arc(sx(predicted.x), sy(predicted.y), 6.5, 0, Math.PI * 2);
    ctx.fillStyle = "#e23b2f"; ctx.fill();
    ctx.strokeStyle = "white"; ctx.lineWidth = 2.5; ctx.stroke();
  }
  ctx.restore();

  const fitPoint = fit.intersection;
  const predictedPoint = pointAtForce(
    chart.data.curve.map((point) => ({ displacement: Number(point.displacement), force: Number(point.force) })),
    Number(chart.data.predicted_pt),
  );
  const labelBounds = {
    left: plot.x,
    right: plot.x + plot.width,
    top: plot.y,
    bottom: plot.y + plot.height,
  };
  if (fitPoint) {
    drawMarkerLabel(ctx, {
      text: ptConsistent ? T.predictedPt : T.fitIntersection,
      value: formatNumber(fitPoint.y, 2),
      x: sx(fitPoint.x),
      y: sy(fitPoint.y),
      color: ptConsistent ? "#6d28d9" : "#b45309",
      horizontal: "right",
      vertical: "below",
      bounds: labelBounds,
    });
  }
  if (predictedPoint && !ptConsistent) {
    drawMarkerLabel(ctx, {
      text: T.modelPt,
      value: formatNumber(chart.data.predicted_pt, 2),
      x: sx(predictedPoint.x),
      y: sy(predictedPoint.y),
      color: "#c92a20",
      horizontal: "right",
      vertical: "above",
      bounds: labelBounds,
    });
  }

  ctx.fillStyle = "#526176";
  ctx.font = "800 15px Inter, system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("Displacement (in)", plot.x + plot.width / 2, height - 17);
  ctx.save();
  ctx.translate(20, plot.y + plot.height / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText("Force (kips)", 0, 0);
  ctx.restore();
}

function renderResult(data) {
  chart.data = data;
  chart.baseDomain = computeBaseDomain(data);
  resetChartView();
  emptyState.classList.add("hidden");
  resultContent.classList.remove("hidden");
  const panelA = formatNumber(data.inputs?.panel_a_in, 1);
  const panelB = formatNumber(data.inputs?.panel_b_in, 1);
  resultModel.textContent = `${data.model_label} · ${panelA} × ${panelB} in`;
  document.querySelector("#predicted-type").textContent = `Type ${data.predicted_type}`;
  document.querySelector("#confidence-value").textContent = `${formatNumber(Number(data.confidence || 0) * 100, 1)}%`;
  renderProbabilities(data.probabilities);
  document.querySelector("#predicted-pt").textContent = formatNumber(data.predicted_pt, 2);
  document.querySelector("#max-displacement").textContent = formatNumber(data.predicted_max_displacement, 4);
  document.querySelector("#max-force").textContent = formatNumber(data.predicted_max_force, 2);
  const fit = fitGeometry(data).intersection;
  const ptConsistent = isPtConsistentResult(data);
  document.querySelector("#fit-force").textContent = fit ? formatNumber(fit.y, 2) : "–";
  document.querySelector("#fit-force-label").textContent = T.fitIntersection;
  const fitPointLegend = document.querySelector("#fit-point-legend");
  fitPointLegend.querySelector("b").textContent = ptConsistent ? T.predictedPt : T.fitIntersection;
  fitPointLegend.querySelector("i").classList.toggle("pt-consistent", ptConsistent);
  document.querySelector("#model-pt-legend").classList.toggle("hidden", ptConsistent);
  document.querySelector("#kink-line-legend").classList.toggle("hidden", !data.curve_fit?.detected_kink);
  document.querySelector("#curve-note").textContent = ptConsistent ? T.ptConsistentCurveNote : T.curveNote;
  if (fit) {
    const delta = Number(data.predicted_pt) - fit.y;
    const percent = Math.abs(delta) / Math.max(Math.abs(Number(data.predicted_pt)), 1) * 100;
    document.querySelector("#curve-delta").textContent = T.fitDelta(formatNumber(delta, 2), `${formatNumber(percent, 1)}%`);
  } else {
    document.querySelector("#curve-delta").textContent = "";
  }
  document.querySelector("#output-mode").textContent = data.metrics?.response_output_mode || "–";
  document.querySelector("#force-scale").textContent = formatNumber(data.metrics?.pt_curve_force_scale_correction ?? 1, 3);
  document.querySelector("#sample-count").textContent = formatNumber(data.metrics?.n_samples, 0);
  requestAnimationFrame(drawChart);
}

async function runPrediction(event) {
  event.preventDefault();
  setError();
  setLoading(true);
  const payload = {
    theta1: Number(form.elements.theta1.value),
    theta2: Number(form.elements.theta2.value),
    case: form.elements.case.value,
    model: modelSelect.value,
    panel_a_in: Number(panelAInput.value),
    panel_b_in: Number(panelBInput.value),
  };
  try {
    const response = await fetch(`${API_BASE}/predict/response/3size-preview`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    renderResult(data);
  } catch (error) {
    setError(error.message || String(error));
  } finally {
    setLoading(false);
  }
}

function setZoom(nextZoom, anchorX = 0.5, anchorY = 0.5) {
  if (!chart.baseDomain) return;
  const previous = chart.viewDomain || viewDomain();
  const worldX = previous.xMin + anchorX * (previous.xMax - previous.xMin);
  const worldY = previous.yMax - anchorY * (previous.yMax - previous.yMin);
  chart.zoom = Math.max(1, Math.min(8, nextZoom));
  const xSpan = (chart.baseDomain.xMax - chart.baseDomain.xMin) / chart.zoom;
  const ySpan = (chart.baseDomain.yMax - chart.baseDomain.yMin) / chart.zoom;
  chart.centerX = worldX - (anchorX - 0.5) * xSpan;
  chart.centerY = worldY + (anchorY - 0.5) * ySpan;
  zoomValue.textContent = `${Math.round(chart.zoom * 100)}%`;
  drawChart();
}

function canvasPosition(event) {
  const rect = canvas.getBoundingClientRect();
  return { x: event.clientX - rect.left, y: event.clientY - rect.top, rect };
}

function nearestVisibleCurvePoint(screenX) {
  if (!chart.data || !chart.plot || !chart.viewDomain) return null;
  const domain = chart.viewDomain;
  const sx = (x) => chart.plot.x + ((x - domain.xMin) / (domain.xMax - domain.xMin)) * chart.plot.width;
  return chart.data.curve.reduce((best, point) => {
    const distance = Math.abs(sx(Number(point.displacement)) - screenX);
    return !best || distance < best.distance ? { point, distance } : best;
  }, null)?.point || null;
}

canvasWrap.addEventListener("wheel", (event) => {
  if (!chart.data) return;
  event.preventDefault();
  const position = canvasPosition(event);
  const anchorX = Math.max(0, Math.min(1, (position.x - chart.plot.x) / chart.plot.width));
  const anchorY = Math.max(0, Math.min(1, (position.y - chart.plot.y) / chart.plot.height));
  setZoom(chart.zoom * (event.deltaY < 0 ? 1.25 : 0.8), anchorX, anchorY);
}, { passive: false });

canvasWrap.addEventListener("pointerdown", (event) => {
  if (!chart.data || chart.zoom <= 1) return;
  canvasWrap.setPointerCapture(event.pointerId);
  chart.drag = { x: event.clientX, y: event.clientY, centerX: chart.centerX, centerY: chart.centerY };
  canvas.style.cursor = "grabbing";
});

canvasWrap.addEventListener("pointermove", (event) => {
  const position = canvasPosition(event);
  if (chart.drag && chart.viewDomain) {
    const dx = event.clientX - chart.drag.x;
    const dy = event.clientY - chart.drag.y;
    chart.centerX = chart.drag.centerX - dx / chart.plot.width * (chart.viewDomain.xMax - chart.viewDomain.xMin);
    chart.centerY = chart.drag.centerY + dy / chart.plot.height * (chart.viewDomain.yMax - chart.viewDomain.yMin);
    drawChart();
    tooltip.classList.add("hidden");
    return;
  }
  const point = nearestVisibleCurvePoint(position.x);
  if (!point || position.x < chart.plot?.x || position.x > chart.plot.x + chart.plot.width) {
    tooltip.classList.add("hidden");
    return;
  }
  tooltip.innerHTML = `<strong>${T.curvePoint}</strong><br>Displacement ${formatNumber(point.displacement, 5)} in<br>Force ${formatNumber(point.force, 2)} kips`;
  tooltip.style.left = `${Math.min(canvas.clientWidth - 172, Math.max(8, position.x + 14))}px`;
  tooltip.style.top = `${Math.min(canvas.clientHeight - 80, Math.max(8, position.y - 52))}px`;
  tooltip.classList.remove("hidden");
});

function endDrag(event) {
  if (chart.drag && canvasWrap.hasPointerCapture(event.pointerId)) canvasWrap.releasePointerCapture(event.pointerId);
  chart.drag = null;
  canvas.style.cursor = "crosshair";
}
canvasWrap.addEventListener("pointerup", endDrag);
canvasWrap.addEventListener("pointercancel", endDrag);
canvasWrap.addEventListener("pointerleave", () => { if (!chart.drag) tooltip.classList.add("hidden"); });

document.querySelector("#zoom-in").addEventListener("click", () => setZoom(chart.zoom * 1.3));
document.querySelector("#zoom-out").addEventListener("click", () => setZoom(chart.zoom / 1.3));
document.querySelector("#zoom-reset").addEventListener("click", () => { resetChartView(); drawChart(); });
window.addEventListener("resize", () => { if (chart.data) drawChart(); });

document.querySelectorAll("[data-angle]").forEach((range) => {
  range.addEventListener("input", () => syncAngles(range.dataset.angle, range.value));
});
["theta1", "theta2"].forEach((name) => {
  const numberInput = form.elements[name];
  const rangeInput = document.querySelector(`[data-angle="${name}"]`);
  numberInput.addEventListener("input", () => {
    syncAngles(name, numberInput.value, { writeNumberInput: false });
  });
  numberInput.addEventListener("change", () => {
    if (syncAngles(name, numberInput.value) === null) {
      syncAngles(name, rangeInput.value);
    }
  });
});
caseSelect.addEventListener("change", () => { caseFormula.textContent = FORMULAS[caseSelect.value]; });
modelSelect.addEventListener("change", updateModelDescription);
panelPresets.forEach((preset) => {
  preset.addEventListener("change", () => {
    if (!preset.checked) return;
    const [panelA, panelB] = preset.value.split("x").map(Number);
    panelAInput.value = String(panelA);
    panelBInput.value = String(panelB);
  });
});
[panelAInput, panelBInput].forEach((input) => {
  input.addEventListener("input", syncPanelPreset);
});
form.addEventListener("submit", runPrediction);
languageButton.addEventListener("click", () => {
  const next = new URL(window.location.href);
  if (IS_KO) next.searchParams.delete("lang"); else next.searchParams.set("lang", "ko");
  window.location.href = next.toString();
});

applyLanguage();
syncAngles("theta1", form.elements.theta1.value);
syncAngles("theta2", form.elements.theta2.value);
loadModels();
