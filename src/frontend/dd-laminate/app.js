const API_HOST = window.location.hostname || "localhost";
const API_BASE = `http://${API_HOST}:8000/api/v1/dd-laminate`;

const apiStatus = document.querySelector("#api-status");
const workspaceGrid = document.querySelector("#workspace-grid");
const inputPanel = document.querySelector(".input-panel");
const thetaForm = document.querySelector("#theta-form");
const curveForm = document.querySelector("#curve-form");
const responseForm = document.querySelector("#response-form");
const thetaModel = document.querySelector("#theta-model");
const curveModel = document.querySelector("#curve-model");
const responseModel = document.querySelector("#response-model");
const emptyState = document.querySelector("#empty-state");
const resultPanel = document.querySelector("#result");
const errorPanel = document.querySelector("#error");
const predictedType = document.querySelector("#predicted-type");
const confidenceEl = document.querySelector("#confidence");
const probabilityBars = document.querySelector("#probability-bars");
const modelLabel = document.querySelector("#model-label");
const inputSummary = document.querySelector("#input-summary");
const notes = document.querySelector("#notes");
const curveFile = document.querySelector("#curve-file");
const curvePreviewPanel = document.querySelector("#curve-preview-panel");
const curvePreviewTitle = document.querySelector("#curve-preview-title");
const curvePreviewCanvas = document.querySelector("#curve-preview-canvas");
const curvePointCount = document.querySelector("#curve-point-count");
const curveMaxDisplacement = document.querySelector("#curve-max-displacement");
const curveMaxForce = document.querySelector("#curve-max-force");
const clearCurvePreview = document.querySelector("#clear-curve-preview");
const responseEstimate = document.querySelector("#response-estimate");
const responseCurveCanvas = document.querySelector("#response-curve-canvas");
const predictedPt = document.querySelector("#predicted-pt");
const predictedMaxDisplacement = document.querySelector("#predicted-max-displacement");
const predictedMaxForce = document.querySelector("#predicted-max-force");

if ("scrollRestoration" in history) {
  history.scrollRestoration = "manual";
}

function percent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "-";
  }
  return `${Math.round(Number(value) * 1000) / 10}%`;
}

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

function setLoading(form, loading) {
  const button = form.querySelector("button[type='submit']");
  if (!button.dataset.defaultText) {
    button.dataset.defaultText = button.textContent;
  }
  button.disabled = loading;
  button.textContent = loading ? "Predicting..." : button.dataset.defaultText;
}

function fillModelSelect(select, models) {
  select.innerHTML = "";
  models.forEach((model) => {
    const option = document.createElement("option");
    option.value = model.key;
    option.textContent = model.available ? model.label : `${model.label} (missing)`;
    option.disabled = !model.available;
    select.appendChild(option);
  });
  const firstAvailable = Array.from(select.options).find((option) => !option.disabled);
  if (firstAvailable) {
    select.value = firstAvailable.value;
  }
}

async function loadModels() {
  try {
    const response = await fetch(`${API_BASE}/models`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    fillModelSelect(thetaModel, data.theta_models);
    fillModelSelect(curveModel, data.curve_models);
    fillModelSelect(responseModel, data.response_models || []);
    apiStatus.textContent = "API: connected";
    apiStatus.classList.add("ok");
  } catch (error) {
    apiStatus.textContent = "API: offline";
    apiStatus.classList.add("bad");
    setError("Start the DD API at http://localhost:8000 before predicting.");
  }
}

function renderProbabilities(probabilities) {
  probabilityBars.innerHTML = "";
  if (!probabilities) {
    probabilityBars.textContent = "No probability output for this model.";
    return;
  }

  Object.entries(probabilities).forEach(([label, value]) => {
    const row = document.createElement("div");
    row.className = "bar-row";

    const labelEl = document.createElement("div");
    labelEl.className = "bar-label";
    labelEl.innerHTML = `<span>${label.toUpperCase()}</span><span>${percent(value)}</span>`;

    const track = document.createElement("div");
    track.className = "bar-track";

    const fill = document.createElement("div");
    fill.className = "bar-fill";
    fill.style.width = `${Math.max(0, Math.min(1, Number(value))) * 100}%`;

    track.appendChild(fill);
    row.append(labelEl, track);
    probabilityBars.appendChild(row);
  });
}

function renderResult(data) {
  emptyState.classList.add("hidden");
  resultPanel.classList.remove("hidden");
  resultPanel.classList.remove("type-1", "type-2", "type-3");
  resultPanel.classList.add(`type-${data.predicted_type}`);
  predictedType.textContent = `Type ${data.predicted_type}`;
  confidenceEl.textContent = percent(data.confidence);
  modelLabel.textContent = data.model_label;
  const inputLabels = {
    theta1: "θ₁",
    theta2: "θ₂",
    case: "Case",
  };
  const inputValueLabels = {
    Case3: "Case 3",
    Case4: "Case 4",
  };
  inputSummary.innerHTML = "";
  const inputEntries = Object.entries(data.inputs)
    .filter(([, value]) => value !== null && value !== "")
  inputEntries
    .forEach(([key, value]) => {
      const item = document.createElement("span");
      item.className = "input-token";

      const label = document.createElement("strong");
      label.textContent = inputLabels[key] || key;

      const valueEl = document.createElement("span");
      valueEl.className = "input-token-value";
      valueEl.textContent = inputValueLabels[value] || value;

      item.append(label, valueEl);
      inputSummary.appendChild(item);
    });
  renderProbabilities(data.probabilities);
  responseEstimate.classList.add("hidden");

  notes.innerHTML = "";
  data.notes.forEach((note) => {
    const item = document.createElement("li");
    item.textContent = note;
    notes.appendChild(item);
  });
}

function pointAtForce(points, targetForce) {
  if (!points || !points.length || !Number.isFinite(Number(targetForce))) {
    return null;
  }
  const force = Number(targetForce);
  for (let index = 1; index < points.length; index += 1) {
    const previous = points[index - 1];
    const current = points[index];
    const lower = Math.min(previous.force, current.force);
    const upper = Math.max(previous.force, current.force);
    if (force >= lower && force <= upper) {
      const delta = current.force - previous.force;
      const ratio = Math.abs(delta) < 1e-9 ? 0 : (force - previous.force) / delta;
      return {
        displacement: previous.displacement + ratio * (current.displacement - previous.displacement),
        force,
      };
    }
  }
  return points.reduce((closest, point) => (
    Math.abs(point.force - force) < Math.abs(closest.force - force) ? point : closest
  ), points[0]);
}

function linearFit(samples) {
  const valid = samples.filter((point) => (
    Number.isFinite(point.displacement) && Number.isFinite(point.force)
  ));
  if (valid.length < 2) {
    return null;
  }

  const meanX = valid.reduce((sum, point) => sum + point.displacement, 0) / valid.length;
  const meanY = valid.reduce((sum, point) => sum + point.force, 0) / valid.length;
  const numerator = valid.reduce((sum, point) => (
    sum + (point.displacement - meanX) * (point.force - meanY)
  ), 0);
  const denominator = valid.reduce((sum, point) => (
    sum + (point.displacement - meanX) ** 2
  ), 0);

  if (Math.abs(denominator) < 1e-12) {
    return null;
  }
  const slope = numerator / denominator;
  return {
    slope,
    intercept: meanY - slope * meanX,
  };
}

function lineY(line, x) {
  return line.slope * x + line.intercept;
}

function rightUpperEnvelopeSlope(points, kinkX, kinkForce, proposedSlope) {
  let requiredSlope = proposedSlope;
  points.forEach((point) => {
    const deltaX = point.displacement - kinkX;
    if (deltaX > 1e-9) {
      requiredSlope = Math.max(requiredSlope, (point.force - kinkForce) / deltaX);
    }
  });
  return Math.max(requiredSlope * 1.015, proposedSlope);
}

function leftUpperEnvelopeSlope(points, kinkX, kinkForce, proposedSlope) {
  let cappedSlope = proposedSlope;
  points.forEach((point) => {
    const deltaX = kinkX - point.displacement;
    if (deltaX > 1e-9) {
      const upperSlope = (kinkForce - point.force) / deltaX;
      if (Number.isFinite(upperSlope) && upperSlope > 0) {
        cappedSlope = Math.min(cappedSlope, upperSlope * 0.985);
      }
    }
  });
  return Math.max(cappedSlope, proposedSlope * 0.72);
}

function buildBilinearFit(points, predictedPtValue) {
  const predictedPt = Number(predictedPtValue);
  const ptOnCurve = pointAtForce(points, predictedPt);
  if (!ptOnCurve || !Number.isFinite(predictedPt)) {
    return null;
  }

  const minX = Math.min(...points.map((point) => point.displacement));
  const maxX = Math.max(...points.map((point) => point.displacement));
  const spanX = Math.max(maxX - minX, 1e-9);
  const firstFitSamples = points.filter((point) => (
    point.displacement > minX + spanX * 0.01 &&
    point.displacement <= Math.max(ptOnCurve.displacement * 0.92, minX + spanX * 0.18) &&
    point.force <= predictedPt * 0.82
  ));
  const firstFallbackEnd = Math.max(8, Math.floor(points.length * 0.28));
  const firstFit = linearFit(firstFitSamples.length >= 4 ? firstFitSamples : points.slice(1, firstFallbackEnd));

  const tailStart = Math.max(ptOnCurve.displacement + spanX * 0.08, minX + spanX * 0.58);
  const secondFitSamples = points.filter((point) => point.displacement >= tailStart);
  const secondFallbackStart = Math.max(0, Math.floor(points.length * 0.72));
  const secondFit = linearFit(secondFitSamples.length >= 4 ? secondFitSamples : points.slice(secondFallbackStart));

  if (!firstFit || !secondFit || firstFit.slope <= 0 || secondFit.slope <= 0) {
    return null;
  }

  let kinkX = (predictedPt - firstFit.intercept) / firstFit.slope;
  const minKinkX = minX + spanX * 0.08;
  const maxKinkX = minX + spanX * 0.78;
  if (!Number.isFinite(kinkX) || kinkX < minKinkX || kinkX > maxKinkX) {
    kinkX = ptOnCurve.displacement;
  }

  const leftEnvelopeSamples = points.filter((point) => (
    point.displacement < kinkX - spanX * 0.006 &&
    point.force <= predictedPt
  ));
  const rightEnvelopeSamples = points.filter((point) => (
    point.displacement > kinkX + spanX * 0.006 &&
    point.force >= predictedPt * 0.96
  ));
  const firstSlope = leftUpperEnvelopeSlope(leftEnvelopeSamples, kinkX, predictedPt, firstFit.slope);
  const secondSlope = rightUpperEnvelopeSlope(rightEnvelopeSamples, kinkX, predictedPt, secondFit.slope);

  const firstLine = {
    slope: firstSlope,
    intercept: predictedPt - firstSlope * kinkX,
  };
  const secondLine = {
    slope: secondSlope,
    intercept: predictedPt - secondSlope * kinkX,
  };

  return {
    kink: {
      displacement: kinkX,
      force: predictedPt,
    },
    firstLine,
    secondLine,
    firstStartX: minX,
    firstEndX: Math.min(maxX, kinkX + spanX * 0.045),
    secondStartX: Math.max(minX, kinkX - spanX * 0.025),
    secondEndX: maxX,
  };
}

function drawResponseCurve(points, predictedPtValue) {
  const ctx = responseCurveCanvas.getContext("2d");
  const { width, height } = responseCurveCanvas;
  const pad = { left: 54, right: 18, top: 20, bottom: 42 };
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#f8fafc";
  ctx.fillRect(0, 0, width, height);
  if (!points || !points.length) {
    ctx.fillStyle = "#637184";
    ctx.font = "14px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("Estimated curve will appear here.", width / 2, height / 2);
    return;
  }
  const bilinearFit = buildBilinearFit(points, predictedPtValue);
  const xs = points.map((point) => point.displacement);
  const ys = points.map((point) => point.force);
  if (Number.isFinite(Number(predictedPtValue))) {
    ys.push(Number(predictedPtValue));
  }
  if (bilinearFit) {
    ys.push(
      lineY(bilinearFit.firstLine, bilinearFit.firstStartX),
      lineY(bilinearFit.firstLine, bilinearFit.firstEndX),
      lineY(bilinearFit.secondLine, bilinearFit.secondStartX),
      lineY(bilinearFit.secondLine, bilinearFit.secondEndX),
      bilinearFit.kink.force,
    );
  }
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys) * 1.06;
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const scaleX = (value) => pad.left + ((value - minX) / Math.max(1e-9, maxX - minX)) * plotW;
  const scaleY = (value) => height - pad.bottom - ((value - minY) / Math.max(1e-9, maxY - minY)) * plotH;

  ctx.strokeStyle = "#d8e0e8";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(pad.left, pad.top);
  ctx.lineTo(pad.left, height - pad.bottom);
  ctx.lineTo(width - pad.right, height - pad.bottom);
  ctx.stroke();

  if (bilinearFit) {
    const kinkX = scaleX(bilinearFit.kink.displacement);
    const kinkY = scaleY(bilinearFit.kink.force);
    ctx.save();
    ctx.setLineDash([6, 4]);
    ctx.strokeStyle = "#ef4444";
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    ctx.moveTo(scaleX(bilinearFit.firstStartX), scaleY(lineY(bilinearFit.firstLine, bilinearFit.firstStartX)));
    ctx.lineTo(scaleX(bilinearFit.firstEndX), scaleY(lineY(bilinearFit.firstLine, bilinearFit.firstEndX)));
    ctx.moveTo(scaleX(bilinearFit.secondStartX), scaleY(lineY(bilinearFit.secondLine, bilinearFit.secondStartX)));
    ctx.lineTo(scaleX(bilinearFit.secondEndX), scaleY(lineY(bilinearFit.secondLine, bilinearFit.secondEndX)));
    ctx.stroke();

    ctx.setLineDash([7, 4]);
    ctx.strokeStyle = "#7c3aed";
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.moveTo(kinkX, pad.top);
    ctx.lineTo(kinkX, height - pad.bottom);
    ctx.stroke();
    ctx.restore();
  }

  ctx.strokeStyle = "#0f766e";
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  points.forEach((point, index) => {
    const x = scaleX(point.displacement);
    const y = scaleY(point.force);
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();

  if (bilinearFit) {
    const ptX = scaleX(bilinearFit.kink.displacement);
    const ptY = scaleY(bilinearFit.kink.force);
    const label = `Pt ${formatMetric(bilinearFit.kink.force, 2)}`;

    ctx.fillStyle = "#ef4444";
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(ptX, ptY, 5.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    ctx.font = "12px system-ui, sans-serif";
    const labelWidth = ctx.measureText(label).width + 14;
    const labelHeight = 24;
    const labelX = Math.min(Math.max(ptX + 9, pad.left), width - pad.right - labelWidth);
    const labelY = Math.max(ptY - labelHeight - 8, pad.top + 4);
    ctx.fillStyle = "#fff7ed";
    ctx.strokeStyle = "#fed7aa";
    ctx.lineWidth = 1;
    ctx.fillRect(labelX, labelY, labelWidth, labelHeight);
    ctx.strokeRect(labelX, labelY, labelWidth, labelHeight);
    ctx.fillStyle = "#9a3412";
    ctx.textAlign = "left";
    ctx.fillText(label, labelX + 7, labelY + 16);
  }

  ctx.fillStyle = "#637184";
  ctx.font = "12px system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("Displacement", pad.left + plotW / 2, height - 12);
  ctx.save();
  ctx.translate(16, pad.top + plotH / 2 + 18);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText("Force", 0, 0);
  ctx.restore();
}

function renderResponseEstimate(data) {
  renderResult(data);
  responseEstimate.classList.remove("hidden");
  predictedPt.textContent = formatMetric(data.predicted_pt, 2);
  predictedMaxDisplacement.textContent = formatMetric(data.predicted_max_displacement, 5);
  predictedMaxForce.textContent = formatMetric(data.predicted_max_force, 2);
  drawResponseCurve(data.curve, data.predicted_pt);
}

function parseCurveCsv(text) {
  return text
    .trim()
    .split(/\r?\n/)
    .map((line) => line.split(",").map((value) => Number(value.trim())))
    .filter((row) => row.length >= 2 && Number.isFinite(row[0]) && Number.isFinite(row[1]))
    .map(([displacement, force]) => ({ displacement, force }));
}

function drawEmptyCurvePreview(message = "Select a two-column force-displacement CSV.") {
  const ctx = curvePreviewCanvas.getContext("2d");
  const { width, height } = curvePreviewCanvas;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#f8fafc";
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = "#d8e0e8";
  ctx.strokeRect(0.5, 0.5, width - 1, height - 1);
  ctx.fillStyle = "#637184";
  ctx.font = "14px system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(message, width / 2, height / 2);
}

function drawCurvePreview(points) {
  const ctx = curvePreviewCanvas.getContext("2d");
  const { width, height } = curvePreviewCanvas;
  const pad = { left: 54, right: 18, top: 20, bottom: 42 };

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#f8fafc";
  ctx.fillRect(0, 0, width, height);

  if (!points.length) {
    drawEmptyCurvePreview();
    return;
  }

  const xs = points.map((point) => point.displacement);
  const ys = points.map((point) => point.force);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const scaleX = (value) => pad.left + ((value - minX) / Math.max(1e-9, maxX - minX)) * plotW;
  const scaleY = (value) => height - pad.bottom - ((value - minY) / Math.max(1e-9, maxY - minY)) * plotH;

  ctx.strokeStyle = "#d8e0e8";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(pad.left, pad.top);
  ctx.lineTo(pad.left, height - pad.bottom);
  ctx.lineTo(width - pad.right, height - pad.bottom);
  ctx.stroke();

  ctx.strokeStyle = "#0f766e";
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  points.forEach((point, index) => {
    const x = scaleX(point.displacement);
    const y = scaleY(point.force);
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();

  ctx.fillStyle = "#637184";
  ctx.font = "12px system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("Displacement", pad.left + plotW / 2, height - 12);
  ctx.save();
  ctx.translate(16, pad.top + plotH / 2 + 18);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText("Force", 0, 0);
  ctx.restore();

  ctx.textAlign = "left";
  ctx.fillText(formatMetric(maxY, 1), 8, pad.top + 4);
  ctx.fillText(formatMetric(minY, 1), 8, height - pad.bottom);
  ctx.textAlign = "right";
  ctx.fillText(formatMetric(maxX, 4), width - pad.right, height - 25);
}

function updateCurvePreview(points, fileName = "No file selected") {
  curvePreviewTitle.textContent = fileName;
  curvePointCount.textContent = points.length ? String(points.length) : "-";
  curveMaxDisplacement.textContent = points.length
    ? formatMetric(Math.max(...points.map((point) => point.displacement)), 5)
    : "-";
  curveMaxForce.textContent = points.length
    ? formatMetric(Math.max(...points.map((point) => point.force)), 2)
    : "-";
  drawCurvePreview(points);
}

async function postJson(path, payload) {
  const response = await fetch(`${API_BASE}${path}`, {
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

async function postForm(path, formData) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    body: formData,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || `HTTP ${response.status}`);
  }
  return data;
}

document.querySelectorAll(".mode-button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".mode-button").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    const mode = button.dataset.mode;
    thetaForm.classList.toggle("active", mode === "theta");
    curveForm.classList.toggle("active", mode === "curve");
    responseForm.classList.toggle("active", mode === "response");
    curvePreviewPanel.classList.toggle("hidden", mode !== "curve");
    workspaceGrid.classList.toggle("curve-active", mode === "curve");
    clearError();
    inputPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

thetaForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();
  setLoading(thetaForm, true);
  const formData = new FormData(thetaForm);
  try {
    const data = await postJson("/predict/theta", {
      theta1: Number(formData.get("theta1")),
      theta2: Number(formData.get("theta2")),
      case: formData.get("case"),
      model: formData.get("model"),
    });
    renderResult(data);
  } catch (error) {
    setError(error.message);
  } finally {
    setLoading(thetaForm, false);
  }
});

curveForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();
  setLoading(curveForm, true);
  const formData = new FormData(curveForm);
  try {
    const data = await postForm("/predict/curve", formData);
    renderResult(data);
  } catch (error) {
    setError(error.message);
  } finally {
    setLoading(curveForm, false);
  }
});

responseForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();
  setLoading(responseForm, true);
  const formData = new FormData(responseForm);
  try {
    const data = await postJson("/predict/response", {
      theta1: Number(formData.get("theta1")),
      theta2: Number(formData.get("theta2")),
      case: formData.get("case"),
      model: formData.get("model"),
    });
    renderResponseEstimate(data);
  } catch (error) {
    setError(error.message);
  } finally {
    setLoading(responseForm, false);
  }
});

curveFile.addEventListener("change", async () => {
  clearError();
  const file = curveFile.files[0];
  if (!file) {
    updateCurvePreview([]);
    return;
  }
  try {
    const text = await file.text();
    const points = parseCurveCsv(text);
    if (!points.length) {
      throw new Error("CSV preview failed: expected at least one numeric displacement,force row.");
    }
    updateCurvePreview(points, file.name);
  } catch (error) {
    updateCurvePreview([], file.name);
    drawEmptyCurvePreview("Could not parse this CSV.");
    setError(error.message);
  }
});

clearCurvePreview.addEventListener("click", () => {
  curveFile.value = "";
  updateCurvePreview([]);
  clearError();
});

updateCurvePreview([]);
loadModels();
