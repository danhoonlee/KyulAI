const API_BASE = "http://localhost:8000/api/v1/dd-laminate";

const apiStatus = document.querySelector("#api-status");
const thetaForm = document.querySelector("#theta-form");
const curveForm = document.querySelector("#curve-form");
const thetaModel = document.querySelector("#theta-model");
const curveModel = document.querySelector("#curve-model");
const emptyState = document.querySelector("#empty-state");
const resultPanel = document.querySelector("#result");
const errorPanel = document.querySelector("#error");
const predictedType = document.querySelector("#predicted-type");
const confidenceEl = document.querySelector("#confidence");
const probabilityBars = document.querySelector("#probability-bars");
const modelLabel = document.querySelector("#model-label");
const inputSummary = document.querySelector("#input-summary");
const notes = document.querySelector("#notes");

function percent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "-";
  }
  return `${Math.round(Number(value) * 1000) / 10}%`;
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
  button.disabled = loading;
  button.textContent = loading ? "Predicting..." : "Predict Type";
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
  predictedType.textContent = `Type ${data.predicted_type}`;
  confidenceEl.textContent = percent(data.confidence);
  modelLabel.textContent = data.model_label;
  inputSummary.textContent = Object.entries(data.inputs)
    .filter(([, value]) => value !== null && value !== "")
    .map(([key, value]) => `${key}: ${value}`)
    .join(", ");
  renderProbabilities(data.probabilities);

  notes.innerHTML = "";
  data.notes.forEach((note) => {
    const item = document.createElement("li");
    item.textContent = note;
    notes.appendChild(item);
  });
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
    clearError();
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

loadModels();
