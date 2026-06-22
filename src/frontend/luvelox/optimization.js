const IS_KO = document.documentElement.lang.toLowerCase().startsWith("ko");

const TEXT = {
  searching: IS_KO ? "설계 후보를 탐색 중입니다." : "Searching design candidates.",
  ready: IS_KO ? "준비됨" : "Ready",
  error: IS_KO ? "후보 탐색에 실패했습니다." : "Could not search candidates.",
  noCase: IS_KO ? "하나 이상의 case를 선택하세요." : "Select at least one case.",
  targetRequired: IS_KO ? "목표 Pt를 입력하세요." : "Enter a target Pt.",
  searched: IS_KO ? "탐색" : "searched",
  feasible: IS_KO ? "가능 후보" : "feasible",
  skipped: IS_KO ? "건너뜀" : "skipped",
  rank: IS_KO ? "순위" : "Rank",
  type: "Type",
  confidence: "Confidence",
  pt: "Pt",
  force: "Force",
  displacement: "Displacement",
};

const form = document.querySelector("#optimization-form");
const statusText = document.querySelector("#optimization-status");
const searchButton = document.querySelector("#search-button");
const summary = document.querySelector("#search-summary");
const candidateList = document.querySelector("#candidate-list");

function numberValue(selector) {
  const value = document.querySelector(selector).value;
  return value === "" ? null : Number(value);
}

function selectedCases() {
  return Array.from(document.querySelectorAll("input[name='case']:checked")).map((input) => input.value);
}

function setStatus(text, isError = false) {
  statusText.textContent = text;
  statusText.classList.toggle("is-error", isError);
}

function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return Number(value).toLocaleString(IS_KO ? "ko-KR" : "en-US", {
    maximumFractionDigits: digits,
  });
}

function payloadFromForm() {
  const objective = document.querySelector("#objective-input").value;
  const cases = selectedCases();
  if (!cases.length) throw new Error(TEXT.noCase);
  const targetPt = numberValue("#target-pt-input");
  if (objective === "target_pt" && targetPt === null) throw new Error(TEXT.targetRequired);

  const constraints = {};
  const targetType = document.querySelector("#target-type-input").value;
  const minConfidence = numberValue("#min-confidence-input");
  const minForce = numberValue("#min-force-input");
  const maxDisplacement = numberValue("#max-displacement-input");
  if (targetType) constraints.target_type = Number(targetType);
  if (minConfidence !== null) constraints.min_confidence = minConfidence;
  if (minForce !== null) constraints.min_force = minForce;
  if (maxDisplacement !== null) constraints.max_displacement = maxDisplacement;

  const step = Number(document.querySelector("#step-input").value || 30);
  return {
    objective,
    target_pt: targetPt,
    top_k: Number(document.querySelector("#top-k-input").value || 5),
    max_candidates: 300,
    design_space: {
      cases,
      theta1_min: numberValue("#theta1-min-input"),
      theta1_max: numberValue("#theta1-max-input"),
      theta1_step: step,
      theta2_min: numberValue("#theta2-min-input"),
      theta2_max: numberValue("#theta2-max-input"),
      theta2_step: step,
    },
    constraints,
  };
}

function metric(label, value) {
  const item = document.createElement("div");
  item.className = "candidate-metric";
  const name = document.createElement("span");
  name.textContent = label;
  const number = document.createElement("strong");
  number.textContent = value;
  item.append(name, number);
  return item;
}

function renderCandidates(data) {
  candidateList.replaceChildren();
  summary.textContent = `${data.searched_count} ${TEXT.searched} · ${data.feasible_count} ${TEXT.feasible} · ${data.skipped_count} ${TEXT.skipped}`;
  for (const candidate of data.candidates || []) {
    const card = document.createElement("article");
    card.className = "candidate-card";
    const header = document.createElement("div");
    header.className = "candidate-card-head";
    header.innerHTML = `
      <span>${TEXT.rank} ${candidate.rank}</span>
      <strong>${candidate.case} · θ1 ${formatNumber(candidate.theta1, 1)}° · θ2 ${formatNumber(candidate.theta2, 1)}°</strong>
    `;

    const metrics = document.createElement("div");
    metrics.className = "candidate-metrics";
    metrics.append(
      metric(TEXT.type, String(candidate.predicted_type)),
      metric(TEXT.confidence, candidate.confidence === null ? "-" : formatNumber(candidate.confidence * 100, 1) + "%"),
      metric(TEXT.pt, formatNumber(candidate.predicted_pt)),
      metric(TEXT.force, formatNumber(candidate.predicted_max_force)),
      metric(TEXT.displacement, formatNumber(candidate.predicted_max_displacement, 4)),
    );

    const note = document.createElement("p");
    note.textContent = (candidate.notes || [])[0] || candidate.model_label;
    card.append(header, metrics, note);
    candidateList.append(card);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  searchButton.disabled = true;
  setStatus(TEXT.searching);
  try {
    const response = await fetch("/api/v1/optimization/search", {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify(payloadFromForm()),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Search failed: ${response.status}`);
    }
    const data = await response.json();
    renderCandidates(data);
    setStatus("");
  } catch (error) {
    setStatus(error.message || TEXT.error, true);
  } finally {
    searchButton.disabled = false;
  }
});

summary.textContent = TEXT.ready;
