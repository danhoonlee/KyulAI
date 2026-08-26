(() => {
  const localePack = window.ImperialAXLaminateLocale || {
    locale: "ko",
    numberLocale: "ko-KR",
    t: (key) => key,
    translateStatic: () => {},
  };
  const {
    locale,
    numberLocale,
    t,
    localizeXaiText = (value) => String(value || ""),
    localizeXaiFeature = (feature = {}) => ({
      title: feature.label || feature.name || "-",
      description: feature.explanation || "",
    }),
    xaiCategoryLabel = (category) => category || "Other",
    localizeXaiPerturbation = (value) => String(value || ""),
  } = localePack;
  localePack.translateStatic(document);
  const isLocalStaticHost = ["localhost", "127.0.0.1"].includes(window.location.hostname)
    && !["8000", "80", "443"].includes(window.location.port);
  const API_BASE = isLocalStaticHost
    ? `http://${window.location.hostname || "localhost"}:8000/api/v1/dd-laminate`
    : `${window.location.origin}/api/v1/dd-laminate`;
  const form = document.querySelector("#rebuild-forecast-form");
  const setupPanel = document.querySelector("#setup-panel");
  const modeButtons = [...document.querySelectorAll("[data-analysis-mode]")];
  const tabButtons = [...document.querySelectorAll("[data-result-tab]")];
  const tabPanels = [...document.querySelectorAll("[data-result-panel]")];
  const resultTabs = document.querySelector(".result-tabs");
  const tabPanelsContainer = document.querySelector(".tab-panels");
  const resultEmptyState = document.querySelector("#result-empty-state");
  const resultWorkspace = document.querySelector(".result-workspace");
  const showExampleButton = document.querySelector("#show-example-result");
  const resultTimestamp = document.querySelector("#result-timestamp");
  const historyBody = document.querySelector("#comparison-body");
  const comparisonTable = document.querySelector("#comparison-table");
  const comparisonEmpty = document.querySelector("#comparison-empty");
  const inlineState = document.querySelector("#inline-state");
  const runButton = form?.querySelector(".run-button");
  const currentInputSummary = document.querySelector("#current-input-summary strong");
  const modelSelect = document.querySelector("#rebuild-model-select");
  const modelDescription = document.querySelector("#model-description");
  const apiStatus = document.querySelector(".status-badge");
  const designSpaceCanvas = document.querySelector("#rebuild-space-canvas");
  const designSpaceTooltip = document.querySelector("#rebuild-space-tooltip");
  const designSpaceFilterButtons = [...document.querySelectorAll("[data-space-case]")];
  const designSpaceFilterCount = document.querySelector("#space-filter-count");
  const xaiMore = document.querySelector("#rebuild-xai-more");
  const xaiMoreCount = document.querySelector("#rebuild-xai-more-count");
  const xaiMoreList = document.querySelector("#rebuild-xai-more-list");
  const stackPreviewVisual = document.querySelector("#stack-preview-visual");
  const stackPreviewSummary = document.querySelector("#stack-preview-summary");
  const stackPreviewCount = document.querySelector("#stack-preview-count");
  const stackFormula = document.querySelector("#stack-formula");
  const summaryStackVisual = document.querySelector("#summary-stack-visual");
  const summaryStackLabel = document.querySelector("#summary-stack-label");
  const summaryStackMeta = document.querySelector("#summary-stack-meta");
  const resultStackVisual = document.querySelector("#result-stack-visual");
  const resultPlySequence = document.querySelector("#result-ply-sequence");
  const resultStackSummary = document.querySelector("#result-stack-summary");
  const resultStackFormula = document.querySelector("#result-stack-formula");
  const resultStackCount = document.querySelector("#result-stack-count");
  const summaryCurveCanvas = document.querySelector("#rebuild-summary-curve-canvas");
  const detailedCurveCanvas = document.querySelector("#rebuild-curve-canvas");
  const detailedCurveZoomLabel = document.querySelector("#rebuild-curve-zoom-label");
  const detailedCurveZoomButtons = [...document.querySelectorAll("[data-curve-zoom]")];
  const trustModel = document.querySelector("#trust-model");
  const trustPosition = document.querySelector("#trust-position");
  const metricMaxForceSummary = document.querySelector("#metric-max-force-summary");
  const modeStorageKey = "imperialax.forecast.rebuild.mode.v1";
  const localeStateStorageKey = "imperialax.laminate.v2.locale-state.v1";
  const chartColors = {
    ink: "#101114",
    muted: "#667085",
    line: "#dce1e9",
    blue: "#2563eb",
    red: "#c43b35",
    green: "#158f63",
  };
  const stackFormulas = {
    Case2: "[[±θ₁]/[±θ₂]]₄",
    Case3: "[[±θ₁]/[±θ₂]/[∓θ₁]/[∓θ₂]]₂",
    Case4: "[([±θ₁]/[±θ₂])₂ / ([∓θ₁]/[∓θ₂])₂]",
  };
  const stackColors = {
    theta1: { topA: "#9aa9ed", topB: "#657bd4", sideA: "#7f90d4", sideB: "#5e70ba", edge: "#4e60aa" },
    theta2: { topA: "#e0bda0", topB: "#bc8f70", sideA: "#caa68b", sideB: "#a77e63", edge: "#8e684f" },
  };
  const twoDecimalFormatter = new Intl.NumberFormat(numberLocale, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const oneDecimalFormatter = new Intl.NumberFormat(numberLocale, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const fourDecimalFormatter = new Intl.NumberFormat(numberLocale, { minimumFractionDigits: 4, maximumFractionDigits: 4 });
  const supportedModelKeys = [
    "response_pt_consistent_tree_3size_grouped_v1",
    "response_pt_consistent_goint_3size_grouped_v1",
    "response_pt_consistent_hybrid_3size_grouped_v1",
  ];
  const fallbackModels = [
    {
      key: supportedModelKeys[0],
      label: "3-Size Pt-Consistent Machine Learning (Tree)",
      description: t("modelTreeDescription"),
      available: true,
    },
    {
      key: supportedModelKeys[1],
      label: "3-Size Pt-Consistent Deep Learning (GointMLP)",
      description: t("modelGointDescription"),
      available: true,
    },
    {
      key: supportedModelKeys[2],
      label: "3-Size Pt-Consistent Hybrid (Teacher–Student)",
      description: t("modelHybridDescription"),
      available: true,
    },
  ];
  let modelCatalog = [...fallbackModels];
  let apiConnected = false;

  if (!form || !runButton || !historyBody) {
    return;
  }

  function serializeLocaleState(targetLocale) {
    const controls = {};
    [...form.elements].forEach((control) => {
      if (control.name && !control.name.endsWith("_range")) controls[control.name] = control.value;
    });
    try {
      sessionStorage.setItem(localeStateStorageKey, JSON.stringify({
        targetLocale,
        controls,
        mode: currentMode,
        rerun: Boolean(inlineState?.textContent.trim()),
      }));
    } catch {
      // Locale switching still works when session storage is unavailable.
    }
  }

  function installLanguageSwitcher() {
    const headerActions = document.querySelector(".header-actions");
    if (!headerActions) return;
    const nav = document.createElement("nav");
    nav.className = "locale-switcher";
    nav.setAttribute("aria-label", t("languageNav"));
    [["ko", "한국어"], ["en", "English"]].forEach(([code, label]) => {
      const link = document.createElement("a");
      link.href = `/v2/${code}`;
      link.lang = code;
      link.textContent = label;
      if (locale === code) link.setAttribute("aria-current", "page");
      link.addEventListener("click", () => serializeLocaleState(code));
      nav.appendChild(link);
    });
    headerActions.appendChild(nav);
  }

  function restoreLocaleState() {
    let saved = null;
    try {
      saved = JSON.parse(sessionStorage.getItem(localeStateStorageKey) || "null");
      if (!saved || saved.targetLocale !== locale) return;
      sessionStorage.removeItem(localeStateStorageKey);
    } catch {
      return;
    }
    Object.entries(saved.controls || {}).forEach(([name, value]) => {
      const control = form.elements[name];
      if (!control) return;
      if (control.tagName === "SELECT" && ![...control.options].some((option) => option.value === value)) return;
      control.value = value;
      const range = form.elements[`${name}_range`];
      if (range) range.value = value;
    });
    setAnalysisMode(saved.mode || "quick");
    syncInputInterface();
    updateModelDescription();
    if (saved.rerun) window.setTimeout(() => form.requestSubmit(), 120);
  }

  installLanguageSwitcher();

  const xaiFeatures = [
    ["A12 membrane coupling", locale === "ko" ? "평면 내 막 커플링이 Type 전환에 미치는 영향" : "Effect of in-plane membrane coupling on Type transition", 23],
    ["Bending anisotropy", locale === "ko" ? "D11/D22 굽힘 강성 균형과 후반 곡률" : "D11/D22 bending-stiffness balance and late-stage curvature", 17],
    ["θ₂ angle family", locale === "ko" ? "두 번째 Double-Double 각도군의 국부 민감도" : "Local sensitivity of the second Double-Double angle family", 13],
    ["D16 bend–twist", locale === "ko" ? "하중 방향 굽힘과 비틀림 응답의 결합" : "Coupling between load-direction bending and twisting", 11],
    ["Panel aspect ratio", locale === "ko" ? "패널 길이와 폭 비율에 따른 형상 영향" : "Geometric effect of the panel length-to-width ratio", 9],
    ["A11 membrane stiffness", locale === "ko" ? "하중 방향의 면내 인장 강성이 예측에 미치는 영향" : "Influence of load-direction in-plane stiffness on the prediction", 7],
    ["D22 bending stiffness", locale === "ko" ? "횡방향 굽힘 저항과 곡선 형상의 관계" : "Relationship between transverse bending resistance and curve shape", 6],
    ["B coupling norm", locale === "ko" ? "막–굽힘 결합 강도의 전체 크기" : "Overall magnitude of membrane-bending coupling", 4.5],
    ["Membrane anisotropy", locale === "ko" ? "A11/A22 면내 강성 불균형의 영향" : "Effect of the A11/A22 in-plane stiffness imbalance", 3.5],
    ["Angle family separation", locale === "ko" ? "두 각도군 사이 간격이 응답 전이에 미치는 영향" : "Effect of separation between the two angle families on response transition", 2.5],
    ["Stack symmetry mismatch", locale === "ko" ? "적층 상·하부 비대칭이 결합 응답에 미치는 영향" : "Effect of top-bottom stack asymmetry on coupled response", 2],
    ["Panel slenderness", locale === "ko" ? "패널 크기 대비 굽힘 강성의 상대적 영향" : "Relative effect of bending stiffness against panel dimensions", 1.5],
  ];
  const xaiPrimaryFeatureCount = 5;

  let currentMode = "quick";
  let currentTab = "summary";
  let currentResult = null;
  let designSpaceHoverPoints = [];
  let activeDesignSpaceCase = "current";
  let sortState = { key: "createdAt", direction: "descending" };
  const detailedCurveView = {
    result: null,
    scale: 1,
    centerXNorm: 0.5,
    centerYNorm: 0.5,
    logicalWidth: 720,
    logicalHeight: 432,
    domain: null,
    plot: null,
    drag: null,
    pointers: new Map(),
    pinch: null,
  };
  const detailedCurveMinZoom = 1;
  const detailedCurveMaxZoom = 6;
  let runs = [];
  const exampleResult = {
    ...makeResult({ modelKey: supportedModelKeys[0], modelLabel: fallbackModels[0].label, caseName: "Case2", theta1: 30, theta2: -30, panelA: 6, panelB: 4 }, 1),
    source: "example",
  };

  function number(value, fallback = 0) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function clampNumber(value, minValue, maxValue) {
    return Math.min(maxValue, Math.max(minValue, value));
  }

  function signedAngle(value) {
    const angle = number(value);
    const formatted = new Intl.NumberFormat(numberLocale, { maximumFractionDigits: 1 }).format(Math.abs(angle));
    if (angle > 0) return `+${formatted}°`;
    if (angle < 0) return `−${formatted}°`;
    return "0°";
  }

  function formatPercent(value, digits = 1) {
    return new Intl.NumberFormat(numberLocale, {
      style: "percent",
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }).format(number(value));
  }

  function integerFormatterForAxis(value) {
    return new Intl.NumberFormat(numberLocale, { maximumFractionDigits: 0 }).format(number(value));
  }

  function caseDisplay(caseName) {
    return String(caseName).replace("Case", "Case ");
  }

  function inputValues() {
    const data = new FormData(form);
    const modelKey = String(data.get("model") || supportedModelKeys[0]);
    const model = modelCatalog.find((item) => item.key === modelKey);
    return {
      modelKey,
      modelLabel: model?.label || modelSelect?.selectedOptions[0]?.textContent?.trim() || "Laminate Forecast",
      caseName: String(data.get("case") || "Case2"),
      theta1: number(data.get("theta1"), 30),
      theta2: number(data.get("theta2"), -30),
      panelA: number(data.get("panel_a"), 6),
      panelB: number(data.get("panel_b"), 4),
    };
  }

  function makeResult(inputs, sequence = Date.now()) {
    const caseIndex = { Case2: 0, Case3: 1, Case4: 2 }[inputs.caseName] ?? 0;
    const angleSpread = Math.abs(inputs.theta1 - inputs.theta2);
    const balance = Math.abs(inputs.theta1 + inputs.theta2);
    const panelScale = Math.sqrt(Math.max(0.1, inputs.panelA * inputs.panelB) / 24);
    const type = angleSpread > 92 || caseIndex === 2
      ? 3
      : angleSpread > 48 || balance > 38
        ? 2
        : 1;
    const confidence = Math.min(0.96, Math.max(0.69, 0.91 - balance * 0.0018 - caseIndex * 0.035));
    const modelIndex = Math.max(0, supportedModelKeys.indexOf(inputs.modelKey));
    const modelFactor = [1, 1.035, 1.018, 0.972, 1.012, 0.996][modelIndex] || 1;
    const pt = Math.round((15100 + Math.cos((inputs.theta1 - 10) * Math.PI / 180) * 2350
      + Math.cos((inputs.theta2 + 24) * Math.PI / 180) * 1220
      - caseIndex * 610) * panelScale * modelFactor);
    const displacement = 0.067 + angleSpread * 0.00024 + caseIndex * 0.0041;
    const reliabilityScore = Math.min(0.97, Math.max(0.66, confidence + 0.038 - Math.abs(panelScale - 1) * 0.05));
    const reliability = reliabilityScore >= 0.86 ? t("reliabilityHigh") : reliabilityScore >= 0.76 ? t("reliabilityMedium") : t("reliabilityLow");
    return {
      ...inputs,
      type,
      confidence,
      pt,
      displacement,
      maxForce: Math.round(pt * (1.22 + type * 0.035)),
      reliability,
      reliabilityScore,
      source: "preview",
      createdAt: Date.now() + sequence,
    };
  }

  function modelDisplayLabel(model) {
    const replacements = {
      "3-Size Pt-Consistent Machine Learning (Tree)": "Machine Learning · Tree",
      "3-Size Pt-Consistent Deep Learning (GointMLP)": "Deep Learning · GointMLP",
      "3-Size Pt-Consistent Hybrid (Teacher-Student)": "Hybrid · Teacher–Student",
      "3-Size Pt-Consistent Hybrid (Teacher–Student)": "Hybrid · Teacher–Student",
    };
    return replacements[model.label] || model.label;
  }

  function renderModelOptions(models, selectedKey = modelSelect.value) {
    modelSelect.innerHTML = "";
    const optgroup = document.createElement("optgroup");
    optgroup.label = "3-Size Pt-Consistent";
    models.forEach((model) => {
      const option = document.createElement("option");
      option.value = model.key;
      option.textContent = model.available ? modelDisplayLabel(model) : `${modelDisplayLabel(model)} · ${t("unavailable")}`;
      option.disabled = !model.available;
      optgroup.appendChild(option);
    });
    modelSelect.appendChild(optgroup);
    const selectedAvailable = models.some((model) => model.key === selectedKey && model.available);
    modelSelect.value = selectedAvailable ? selectedKey : (models.find((model) => model.available)?.key || supportedModelKeys[0]);
    updateModelDescription();
  }

  function updateModelDescription() {
    const model = modelCatalog.find((item) => item.key === modelSelect.value);
    if (modelDescription) {
      modelDescription.textContent = model?.description || t("modelGenericDescription");
    }
  }

  function setApiStatus(state) {
    if (!apiStatus) return;
    apiConnected = state === "ready";
    apiStatus.classList.toggle("offline", state === "offline");
    apiStatus.classList.toggle("ready", state === "ready");
    apiStatus.innerHTML = `<i></i>${state === "ready" ? t("apiReady") : state === "offline" ? t("apiOffline") : t("apiChecking")}`;
  }

  async function fetchJson(path, options = {}, timeout = 9000) {
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), timeout);
    try {
      const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        signal: controller.signal,
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
      return data;
    } finally {
      window.clearTimeout(timer);
    }
  }

  async function loadModels() {
    setApiStatus("loading");
    try {
      const received = await fetchJson("/models/3size-preview", { cache: "no-store" }, 4000);
      modelCatalog = supportedModelKeys
        .map((key) => {
          const model = received.find((item) => item.key === key);
          const fallback = fallbackModels.find((item) => item.key === key);
          return model ? { ...model, description: fallback?.description || model.description } : null;
        })
        .filter(Boolean);
      if (modelCatalog.length !== supportedModelKeys.length) {
        modelCatalog = supportedModelKeys.map((key) => {
          const model = received.find((item) => item.key === key);
          const fallback = fallbackModels.find((item) => item.key === key);
          return model ? { ...model, description: fallback?.description || model.description } : fallback;
        });
      }
      renderModelOptions(modelCatalog);
      setApiStatus("ready");
    } catch {
      modelCatalog = [...fallbackModels];
      renderModelOptions(modelCatalog);
      setApiStatus("offline");
    }
  }

  function normalizePrediction(data, inputs) {
    const uncertainty = data.uncertainty || {};
    const reliabilityScore = number(uncertainty.reliability_score, number(data.confidence, 0.78));
    const reliability = uncertainty.confidence_label === "high" || reliabilityScore >= 0.86
      ? t("reliabilityHigh")
      : uncertainty.confidence_label === "low" || reliabilityScore < 0.76
        ? t("reliabilityLow")
        : t("reliabilityMedium");
    return {
      ...inputs,
      modelKey: data.model_key || inputs.modelKey,
      modelLabel: data.model_label || inputs.modelLabel,
      type: number(data.predicted_type, 1),
      confidence: number(data.confidence, 0.78),
      pt: number(data.predicted_pt),
      displacement: number(data.predicted_max_displacement),
      maxForce: number(data.predicted_max_force, number(data.predicted_pt) * 1.25),
      curve: Array.isArray(data.curve) ? data.curve : [],
      curveFit: data.curve_fit || null,
      reliability,
      reliabilityScore,
      interpolationLabel: uncertainty.interpolation_label || "interpolation",
      notes: data.notes || [],
      source: "api",
      createdAt: Date.now(),
    };
  }

  function setAnalysisMode(mode, persist = true) {
    currentMode = mode === "deep" ? "deep" : "quick";
    modeButtons.forEach((button) => {
      const active = button.dataset.analysisMode === currentMode;
      button.setAttribute("aria-checked", String(active));
      button.tabIndex = active ? 0 : -1;
    });
    tabButtons.forEach((button) => {
      const disabled = !currentResult || (currentMode === "quick" && button.dataset.resultTab !== "summary");
      button.setAttribute("aria-disabled", String(disabled));
    });
    if (currentMode === "quick" && currentTab !== "summary") {
      activateTab("summary");
    }
    if (persist) {
      try {
        sessionStorage.setItem(modeStorageKey, currentMode);
      } catch {
        // Session persistence is optional.
      }
    }
  }

  function handleModeKeydown(event) {
    const index = modeButtons.indexOf(event.currentTarget);
    let nextIndex = null;
    if (event.key === "ArrowRight" || event.key === "ArrowDown") nextIndex = (index + 1) % modeButtons.length;
    if (event.key === "ArrowLeft" || event.key === "ArrowUp") nextIndex = (index - 1 + modeButtons.length) % modeButtons.length;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = modeButtons.length - 1;
    if (nextIndex === null) return;
    event.preventDefault();
    const nextButton = modeButtons[nextIndex];
    setAnalysisMode(nextButton.dataset.analysisMode);
    nextButton.focus();
  }

  function activateTab(tabName, focus = false) {
    if (!currentResult) return;
    if (currentMode === "quick" && tabName !== "summary") {
      return;
    }
    currentTab = tabName;
    tabButtons.forEach((button) => {
      const active = button.dataset.resultTab === tabName;
      button.setAttribute("aria-selected", String(active));
      button.tabIndex = active ? 0 : -1;
      if (active && focus) button.focus();
    });
    tabPanels.forEach((panel) => {
      panel.hidden = panel.dataset.resultPanel !== tabName;
    });
    requestAnimationFrame(() => {
      if (tabName === "summary") drawSummaryCurve(currentResult);
      if (tabName === "curve") drawCurve(currentResult);
      if (tabName === "space") drawDesignSpace(currentResult);
    });
  }

  function setResultPresence(hasResult) {
    if (resultEmptyState) resultEmptyState.hidden = hasResult;
    if (resultTabs) resultTabs.hidden = !hasResult;
    if (tabPanelsContainer) tabPanelsContainer.hidden = !hasResult;
    if (resultWorkspace) resultWorkspace.classList.toggle("has-result", hasResult);
    if (!hasResult && resultTimestamp) resultTimestamp.textContent = t("noResultYet");
    setAnalysisMode(currentMode, false);
  }

  function handleTabKeydown(event) {
    const enabledTabs = tabButtons.filter((button) => button.getAttribute("aria-disabled") !== "true");
    const index = enabledTabs.indexOf(event.currentTarget);
    let nextIndex = null;
    if (event.key === "ArrowRight") nextIndex = (index + 1) % enabledTabs.length;
    if (event.key === "ArrowLeft") nextIndex = (index - 1 + enabledTabs.length) % enabledTabs.length;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = enabledTabs.length - 1;
    if (nextIndex === null) return;
    event.preventDefault();
    activateTab(enabledTabs[nextIndex].dataset.resultTab, true);
  }

  function stackAnglePair(angle, family) {
    return [{ angle, family }, { angle: -angle, family }];
  }

  function stackInversePair(angle, family) {
    return [{ angle: -angle, family }, { angle, family }];
  }

  function repeatStackPattern(pattern, count) {
    return Array.from({ length: count }).flatMap(() => pattern.map((ply) => ({ ...ply })));
  }

  function buildStackSequence({ caseName, theta1, theta2 }) {
    const theta1Pair = stackAnglePair(theta1, "theta1");
    const theta2Pair = stackAnglePair(theta2, "theta2");
    const theta1Inverse = stackInversePair(theta1, "theta1");
    const theta2Inverse = stackInversePair(theta2, "theta2");
    if (caseName === "Case3") {
      return repeatStackPattern([...theta1Pair, ...theta2Pair, ...theta1Inverse, ...theta2Inverse], 2);
    }
    if (caseName === "Case4") {
      return [
        ...repeatStackPattern([...theta1Pair, ...theta2Pair], 2),
        ...repeatStackPattern([...theta1Inverse, ...theta2Inverse], 2),
      ];
    }
    return repeatStackPattern([...theta1Pair, ...theta2Pair], 4);
  }

  function panelLengthScale(panelA) {
    return Math.max(0.68, Math.min(1.28, number(panelA, 6) / 6));
  }

  function panelWidthScale(panelB) {
    return Math.max(0.68, Math.min(1.28, number(panelB, 4) / 4));
  }

  function stackPlyGeometry(lengthScale, widthScale) {
    const center = [210, 91];
    const lengthX = 282 * lengthScale;
    const lengthY = -158 * lengthScale;
    const widthX = 138 * widthScale;
    const widthY = 80 * widthScale;
    const a = [center[0] - (lengthX + widthX) / 2, center[1] - (lengthY + widthY) / 2];
    const b = [a[0] + widthX, a[1] + widthY];
    const c = [b[0] + lengthX, b[1] + lengthY];
    const d = [a[0] + lengthX, a[1] + lengthY];
    const point = ([x, y]) => `${x.toFixed(2)},${y.toFixed(2)}`;
    return {
      top: [a, b, c, d].map(point).join(" "),
      sideLeft: [a, b, [b[0], b[1] + 20], [a[0], a[1] + 20]].map(point).join(" "),
      sideRight: [b, c, [c[0], c[1] + 20], [b[0], b[1] + 20]].map(point).join(" "),
      labelX: a[0] + 12,
      labelY: a[1] + 13,
    };
  }

  function renderStackPly(ply, index, total, uid, lengthScale, widthScale) {
    const palette = stackColors[ply.family];
    const x = 555 - index * 30;
    const y = 470 - index * 28;
    const labelFill = ply.angle >= 0 ? "#087443" : "#b42318";
    const geometry = stackPlyGeometry(lengthScale, widthScale);
    return `
      <g transform="translate(${x} ${y})">
        <defs>
          <pattern id="${uid}-ply-hatch-${index}" width="24" height="24" patternUnits="userSpaceOnUse" patternTransform="rotate(${-ply.angle})">
            <path d="M-6 12 H30" stroke="${labelFill}" stroke-width="3" stroke-linecap="round" opacity="0.82" />
          </pattern>
        </defs>
        <polygon points="${geometry.sideLeft}" fill="${palette.sideA}" />
        <polygon points="${geometry.sideRight}" fill="${palette.sideB}" />
        <polygon points="${geometry.top}" fill="url(#${uid}-top-${ply.family})" stroke="${palette.edge}" stroke-width="1.4" />
        <polygon points="${geometry.top}" fill="url(#${uid}-ply-hatch-${index})" opacity="0.88" />
        <polygon points="${geometry.top}" fill="transparent" stroke="rgba(255,255,255,0.64)" stroke-width="1" />
        ${index === 0 || index === total - 1 ? `<rect x="${(geometry.labelX - 5).toFixed(2)}" y="${(geometry.labelY - 15).toFixed(2)}" width="36" height="22" rx="11" fill="#102033" opacity="0.9" /><text x="${(geometry.labelX + 13).toFixed(2)}" y="${geometry.labelY.toFixed(2)}" text-anchor="middle" fill="#ffffff" font-size="11" font-weight="900">P${index + 1}</text>` : ""}
      </g>
    `;
  }

  function renderPlySequence(sequence) {
    return sequence.map((ply, index) => {
      const familyClass = ply.family === "theta1" ? "theta-one" : "theta-two";
      const directionClass = ply.angle >= 0 ? "is-positive" : "is-negative";
      const visualAngle = Math.max(-90, Math.min(90, -number(ply.angle)));
      const angle = signedAngle(ply.angle);
      const family = ply.family === "theta1" ? "θ₁" : "θ₂";
      return `
        <span class="ply-sequence-cell ${familyClass} ${directionClass}" style="--ply-angle: ${visualAngle}deg" tabindex="0" aria-label="Ply ${index + 1} · ${angle} · ${family}" title="Ply ${index + 1} · ${angle} · ${family}">
          <small>P${index + 1}</small>
          <i aria-hidden="true"></i>
          <strong>${angle}</strong>
        </span>
      `;
    }).join("");
  }

  function renderStackPreview(values) {
    if (!stackPreviewVisual) return;
    const sequence = buildStackSequence(values);
    const uid = "rebuild-stack";
    const lengthScale = panelLengthScale(values.panelA);
    const widthScale = panelWidthScale(values.panelB);
    const plies = sequence.map((ply, index) => renderStackPly(ply, index, sequence.length, uid, lengthScale, widthScale)).join("");
    const label = t("stackAriaLabel", {
      case: caseDisplay(values.caseName),
      theta1: signedAngle(values.theta1),
      theta2: signedAngle(values.theta2),
      count: sequence.length,
    });
    const stackMarkup = `
      <svg viewBox="0 0 1160 760" role="img" aria-label="${label}" data-panel-length="${values.panelA}" data-panel-length-scale="${lengthScale.toFixed(3)}" data-panel-width="${values.panelB}" data-panel-width-scale="${widthScale.toFixed(3)}">
        <defs>
          <linearGradient id="${uid}-top-theta1" x1="0" x2="1">
            <stop offset="0" stop-color="${stackColors.theta1.topA}" />
            <stop offset="1" stop-color="${stackColors.theta1.topB}" />
          </linearGradient>
          <linearGradient id="${uid}-top-theta2" x1="0" x2="1">
            <stop offset="0" stop-color="${stackColors.theta2.topA}" />
            <stop offset="1" stop-color="${stackColors.theta2.topB}" />
          </linearGradient>
          <filter id="${uid}-stack-shadow" x="-20%" y="-20%" width="140%" height="150%">
            <feDropShadow dx="0" dy="14" stdDeviation="14" flood-color="#667085" flood-opacity="0.18" />
          </filter>
        </defs>
        <rect x="34" y="34" width="1092" height="700" rx="8" fill="#eef1f5" stroke="#d7dce5" stroke-width="2" />
        <g filter="url(#${uid}-stack-shadow)">${plies}</g>
      </svg>
    `;
    const sequenceMarkup = renderPlySequence(sequence);
    stackPreviewVisual.innerHTML = stackMarkup;
    if (summaryStackVisual) summaryStackVisual.innerHTML = sequenceMarkup;
    if (resultPlySequence) resultPlySequence.innerHTML = sequenceMarkup;
    if (resultStackVisual) resultStackVisual.innerHTML = stackMarkup.replaceAll(uid, "rebuild-result-stack");
    stackPreviewVisual.setAttribute("aria-label", label);
    resultStackVisual?.setAttribute("aria-label", label);
    if (stackPreviewSummary) stackPreviewSummary.textContent = `${caseDisplay(values.caseName)} · θ ${signedAngle(values.theta1)} / ${signedAngle(values.theta2)}`;
    if (stackPreviewCount) stackPreviewCount.textContent = `${sequence.length} plies`;
    if (stackFormula) stackFormula.textContent = `${caseDisplay(values.caseName)} · ${stackFormulas[values.caseName]}`;
    if (summaryStackLabel) summaryStackLabel.textContent = `${caseDisplay(values.caseName)} · θ ${signedAngle(values.theta1)} / ${signedAngle(values.theta2)}`;
    if (summaryStackMeta) summaryStackMeta.textContent = `${sequence.length} plies · Double-Double laminate`;
    if (resultStackSummary) resultStackSummary.textContent = `${caseDisplay(values.caseName)} · θ ${signedAngle(values.theta1)} / ${signedAngle(values.theta2)}`;
    if (resultStackFormula) resultStackFormula.textContent = stackFormulas[values.caseName];
    if (resultStackCount) resultStackCount.textContent = `${sequence.length} plies`;
  }

  function syncInputInterface() {
    const values = inputValues();
    form.querySelector('[data-angle-output="theta1"]').textContent = signedAngle(values.theta1);
    form.querySelector('[data-angle-output="theta2"]').textContent = signedAngle(values.theta2);
    currentInputSummary.textContent = `${caseDisplay(values.caseName)} · θ ${signedAngle(values.theta1)} / ${signedAngle(values.theta2)} · ${oneDecimalFormatter.format(values.panelA)} × ${oneDecimalFormatter.format(values.panelB)} in`;
    renderStackPreview(values);
    highlightMatchingRun(values);
  }

  function syncAnglePair(source) {
    const name = source.name.replace("_range", "");
    const numberInput = form.elements[name];
    const rangeInput = form.elements[`${name}_range`];
    const value = Math.max(-90, Math.min(90, number(source.value)));
    numberInput.value = String(value);
    rangeInput.value = String(value);
    syncInputInterface();
  }

  function updateSummary(result) {
    currentResult = result;
    setResultPresence(true);
    document.querySelector("#metric-type").textContent = `Type ${result.type}`;
    document.querySelector("#metric-probability").textContent = formatPercent(result.confidence);
    document.querySelector("#metric-pt").textContent = twoDecimalFormatter.format(result.pt);
    document.querySelector("#metric-displacement").textContent = fourDecimalFormatter.format(result.displacement);
    document.querySelector("#metric-reliability").textContent = result.reliability;
    const interpolationCopy = result.interpolationLabel === "extrapolation" ? t("extrapolation") : result.interpolationLabel === "near-edge" ? t("nearEdge") : t("interpolation");
    document.querySelector("#metric-reliability-score").textContent = formatPercent(result.reliabilityScore);
    if (metricMaxForceSummary) metricMaxForceSummary.textContent = twoDecimalFormatter.format(result.maxForce || result.pt * 1.25);
    if (trustModel) trustModel.textContent = modelDisplayLabel({ label: result.modelLabel });
    if (trustPosition) trustPosition.textContent = interpolationCopy;
    document.querySelector("#curve-max-force").textContent = twoDecimalFormatter.format(result.maxForce || result.pt * 1.25);
    document.querySelector("#curve-max-displacement").textContent = fourDecimalFormatter.format(result.displacement);
    document.querySelector("#curve-pt").textContent = twoDecimalFormatter.format(result.pt);
    document.querySelector("#curve-note").textContent = result.source === "api"
      ? t("actualCurve", { model: result.modelLabel })
      : result.source === "example"
        ? t("exampleCurve")
        : t("previewCurve");
    document.querySelector("#space-risk").textContent = result.type === 1 ? `${t("reliabilityLow")} · 18%` : result.type === 2 ? `${t("reliabilityLow")} · 24%` : `${t("reliabilityMedium")} · 47%`;
    document.querySelector("#space-nearest").textContent = `${caseDisplay(result.caseName)} · Δθ ${oneDecimalFormatter.format(Math.abs(result.theta1 + result.theta2) / 6 + 5)}°`;
    const verdict = result.type === 1 ? t("keepCandidate") : t("reviewDeep");
    const copy = result.type === 1
      ? t("typeOneCopy")
      : t("transitionCopy", { type: result.type });
    document.querySelector("#screening-verdict").textContent = verdict;
    document.querySelector("#screening-copy").textContent = copy;
    if (resultTimestamp) {
      const resultLabel = result.source === "api"
        ? t("actualResult")
        : result.source === "example"
          ? t("exampleResult")
          : t("previewResult");
      resultTimestamp.textContent = result.source === "example" ? resultLabel : `${resultLabel} · ${t("justNow")}`;
    }
    renderXai(result);
    drawSummaryCurve(result);
    detailedCurveView.result = result;
    resetDetailedCurveView(false);
    if (currentTab === "curve") drawCurve(result);
    drawDesignSpace(result);
  }

  function prepareCanvas(canvas) {
    const rect = canvas.getBoundingClientRect();
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    const width = Math.max(320, Math.round(rect.width || canvas.width));
    const baseHeight = Math.round(width * (Number(canvas.getAttribute("height")) / Number(canvas.getAttribute("width"))));
    const isMobileViewport = window.matchMedia("(max-width: 620px)").matches;
    const isMobileCurve = (canvas === summaryCurveCanvas || canvas === detailedCurveCanvas) && isMobileViewport;
    const isMobileDesignSpace = canvas === designSpaceCanvas && isMobileViewport;
    const height = isMobileCurve
      ? clampNumber(Math.round(width * 0.64), 220, 280)
      : isMobileDesignSpace
        ? clampNumber(Math.round(width * 0.98), 340, 440)
        : baseHeight;
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    canvas.style.height = `${height}px`;
    const ctx = canvas.getContext("2d");
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    return { ctx, width, height };
  }

  function drawAxes(ctx, width, height, pad, xTicks, yTicks, xLabel, yLabel) {
    const plotWidth = width - pad.left - pad.right;
    const plotHeight = height - pad.top - pad.bottom;
    const compactChart = width <= 520;
    ctx.fillStyle = "#f8fafc";
    ctx.fillRect(0, 0, width, height);
    ctx.strokeStyle = chartColors.line;
    ctx.lineWidth = 1;
    ctx.font = `400 ${compactChart ? 9 : 11}px -apple-system, "Segoe UI", Inter, sans-serif`;
    ctx.fillStyle = chartColors.muted;
    ctx.textAlign = "center";
    xTicks.forEach((label, index) => {
      const x = pad.left + (plotWidth * index) / (xTicks.length - 1);
      ctx.beginPath();
      ctx.moveTo(x, pad.top);
      ctx.lineTo(x, pad.top + plotHeight);
      ctx.stroke();
      ctx.fillText(label, x, height - (compactChart ? 16 : 22));
    });
    ctx.textAlign = "right";
    yTicks.forEach((label, index) => {
      const y = pad.top + plotHeight - (plotHeight * index) / (yTicks.length - 1);
      ctx.beginPath();
      ctx.moveTo(pad.left, y);
      ctx.lineTo(pad.left + plotWidth, y);
      ctx.stroke();
      ctx.fillText(label, pad.left - (compactChart ? 7 : 10), y + 4);
    });
    ctx.textAlign = "center";
    ctx.fillText(xLabel, pad.left + plotWidth / 2, height - (compactChart ? 3 : 5));
    ctx.save();
    ctx.translate(compactChart ? 10 : 15, pad.top + plotHeight / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText(yLabel, 0, 0);
    ctx.restore();
    return { plotWidth, plotHeight };
  }

  function buildCurveRenderModel(result) {
    const receivedPoints = Array.isArray(result.curve)
      ? result.curve.map((point) => ({ displacement: number(point.displacement), force: number(point.force) })).filter((point) => Number.isFinite(point.displacement) && Number.isFinite(point.force))
      : [];
    const fit = result.curveFit || {};
    const firstLine = fit.first_line || fit.firstLine;
    const secondLine = fit.second_line || fit.secondLine;
    const fitKink = fit.kink;
    const validLine = (line) => Number.isFinite(Number(line?.slope)) && Number.isFinite(Number(line?.intercept));
    const validKink = Number.isFinite(Number(fitKink?.displacement)) && Number.isFinite(Number(fitKink?.force));
    const hasBilinearFit = validLine(firstLine) && validLine(secondLine) && validKink;
    const lineForce = (line, displacement) => Number(line.slope) * displacement + Number(line.intercept);
    const maxDisplacement = Math.max(0.08, result.displacement, ...receivedPoints.map((point) => point.displacement));
    const fallbackTransitionX = maxDisplacement * 0.59;
    const points = receivedPoints.length > 1 ? receivedPoints : Array.from({ length: 46 }, (_, index) => {
      const displacement = (maxDisplacement * index) / 45;
      const firstSlope = result.pt / fallbackTransitionX;
      const force = displacement <= fallbackTransitionX
        ? firstSlope * displacement
        : result.pt + (displacement - fallbackTransitionX) * firstSlope * (result.type === 1 ? 0.78 : result.type === 2 ? 0.38 : 0.18);
      return { displacement, force };
    });
    const firstStartX = hasBilinearFit ? number(fit.first_start_x ?? fit.firstStartX, 0) : 0;
    const firstEndX = hasBilinearFit ? number(fit.first_end_x ?? fit.firstEndX, Number(fitKink.displacement)) : 0;
    const secondStartX = hasBilinearFit ? number(fit.second_start_x ?? fit.secondStartX, Number(fitKink.displacement)) : 0;
    const secondEndX = hasBilinearFit ? number(fit.second_end_x ?? fit.secondEndX, maxDisplacement) : 0;
    const fitForces = hasBilinearFit
      ? [lineForce(firstLine, firstStartX), lineForce(firstLine, firstEndX), lineForce(secondLine, secondStartX), lineForce(secondLine, secondEndX)]
      : [];
    const baseMinX = Math.min(0, ...points.map((point) => point.displacement));
    const baseMaxX = Math.max(maxDisplacement, ...points.map((point) => point.displacement));
    const baseMinY = Math.min(0, ...points.map((point) => point.force), ...fitForces);
    const baseMaxY = Math.max(result.pt * 1.08, result.maxForce || 0, ...points.map((point) => point.force), ...fitForces) * 1.06;
    const ptPoint = hasBilinearFit
      ? { displacement: Number(fitKink.displacement), force: Number(fitKink.force) }
      : points.reduce((closest, point) => Math.abs(point.force - result.pt) < Math.abs(closest.force - result.pt) ? point : closest, points[0]);
    return {
      points,
      firstLine,
      secondLine,
      hasBilinearFit,
      lineForce,
      firstStartX,
      firstEndX,
      secondStartX,
      secondEndX,
      fallbackTransitionX,
      baseMinX,
      baseMaxX,
      baseMinY,
      baseMaxY,
      baseSpanX: Math.max(1e-9, baseMaxX - baseMinX),
      baseSpanY: Math.max(1e-9, baseMaxY - baseMinY),
      ptPoint,
    };
  }

  function drawSummaryCurve(result) {
    const canvas = summaryCurveCanvas;
    if (!canvas || !result) return;
    const { ctx, width, height } = prepareCanvas(canvas);
    const compactMobileChart = width <= 520;
    const pad = compactMobileChart
      ? { left: 18, right: 18, top: 14, bottom: 16 }
      : { left: 26, right: 26, top: 20, bottom: 20 };
    const plotWidth = width - pad.left - pad.right;
    const plotHeight = height - pad.top - pad.bottom;
    const curveModel = buildCurveRenderModel(result);
    const {
      points,
      firstLine,
      secondLine,
      hasBilinearFit,
      lineForce,
      firstStartX,
      firstEndX,
      secondStartX,
      secondEndX,
      fallbackTransitionX,
      baseMinX,
      baseMinY,
      baseSpanX,
      baseSpanY,
      ptPoint,
    } = curveModel;
    const x = (value) => pad.left + ((value - baseMinX) / baseSpanX) * plotWidth;
    const y = (value) => pad.top + plotHeight - ((value - baseMinY) / baseSpanY) * plotHeight;

    ctx.fillStyle = "#f8fafc";
    ctx.fillRect(0, 0, width, height);
    ctx.strokeStyle = "#e4e8ef";
    ctx.lineWidth = 1;
    [0.25, 0.5, 0.75].forEach((ratio) => {
      const gridY = pad.top + plotHeight * ratio;
      const gridX = pad.left + plotWidth * ratio;
      ctx.beginPath();
      ctx.moveTo(pad.left, gridY);
      ctx.lineTo(width - pad.right, gridY);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(gridX, pad.top);
      ctx.lineTo(gridX, height - pad.bottom);
      ctx.stroke();
    });

    if (hasBilinearFit) {
      ctx.setLineDash([7, 5]);
      ctx.strokeStyle = chartColors.red;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(x(firstStartX), y(lineForce(firstLine, firstStartX)));
      ctx.lineTo(x(firstEndX), y(lineForce(firstLine, firstEndX)));
      ctx.moveTo(x(secondStartX), y(lineForce(secondLine, secondStartX)));
      ctx.lineTo(x(secondEndX), y(lineForce(secondLine, secondEndX)));
      ctx.stroke();
      ctx.setLineDash([]);
    }

    ctx.beginPath();
    points.forEach((point, index) => {
      if (index === 0) ctx.moveTo(x(point.displacement), y(point.force));
      else ctx.lineTo(x(point.displacement), y(point.force));
    });
    ctx.strokeStyle = "#0f766e";
    ctx.lineWidth = compactMobileChart ? 2.5 : 3;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.stroke();

    const ptX = x(ptPoint?.displacement ?? fallbackTransitionX);
    const ptY = y(ptPoint?.force ?? result.pt);
    if (!hasBilinearFit) {
      ctx.setLineDash([5, 5]);
      ctx.strokeStyle = "rgba(196, 59, 53, 0.62)";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(ptX, pad.top);
      ctx.lineTo(ptX, pad.top + plotHeight);
      ctx.stroke();
      ctx.setLineDash([]);
    }
    const markerRadius = 5;
    ctx.beginPath();
    ctx.moveTo(ptX, ptY - markerRadius);
    ctx.lineTo(ptX + markerRadius, ptY);
    ctx.lineTo(ptX, ptY + markerRadius);
    ctx.lineTo(ptX - markerRadius, ptY);
    ctx.closePath();
    ctx.fillStyle = "#ffffff";
    ctx.fill();
    ctx.strokeStyle = "#7c3aed";
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.fillStyle = "#5b21b6";
    ctx.font = `500 ${compactMobileChart ? 9 : 11}px -apple-system, "Segoe UI", Inter, sans-serif`;
    ctx.textAlign = ptX > width * 0.72 ? "right" : "left";
    ctx.fillText(`Pt ${twoDecimalFormatter.format(result.pt)}${compactMobileChart ? "" : " N"}`, ptX + (ptX > width * 0.72 ? -7 : 7), Math.max(13, ptY - 8));
  }

  function updateDetailedCurveZoomControls() {
    if (detailedCurveZoomLabel) detailedCurveZoomLabel.textContent = `${Math.round(detailedCurveView.scale * 100)}%`;
    detailedCurveZoomButtons.forEach((button) => {
      const action = button.dataset.curveZoom;
      button.disabled = action === "in"
        ? detailedCurveView.scale >= detailedCurveMaxZoom - 0.01
        : detailedCurveView.scale <= detailedCurveMinZoom + 0.01;
    });
  }

  function resetDetailedCurveView(redraw = false) {
    detailedCurveView.scale = 1;
    detailedCurveView.centerXNorm = 0.5;
    detailedCurveView.centerYNorm = 0.5;
    detailedCurveView.domain = null;
    detailedCurveView.plot = null;
    detailedCurveView.drag = null;
    detailedCurveView.pointers.clear();
    detailedCurveView.pinch = null;
    updateDetailedCurveZoomControls();
    if (redraw && detailedCurveView.result) drawCurve(detailedCurveView.result);
  }

  function detailedCurvePointFromEvent(event) {
    if (!detailedCurveCanvas) return null;
    const rect = detailedCurveCanvas.getBoundingClientRect();
    return {
      x: ((event.clientX - rect.left) / Math.max(1, rect.width)) * detailedCurveView.logicalWidth,
      y: ((event.clientY - rect.top) / Math.max(1, rect.height)) * detailedCurveView.logicalHeight,
    };
  }

  function detailedCurvePointerPoint(event) {
    const point = detailedCurvePointFromEvent(event);
    return point ? { ...point, clientX: event.clientX, clientY: event.clientY } : null;
  }

  function detailedCurvePinchMetrics() {
    const points = [...detailedCurveView.pointers.values()].slice(0, 2);
    if (points.length < 2) return null;
    return {
      distance: Math.max(1, Math.hypot(points[1].clientX - points[0].clientX, points[1].clientY - points[0].clientY)),
      anchor: {
        x: (points[0].x + points[1].x) / 2,
        y: (points[0].y + points[1].y) / 2,
      },
    };
  }

  function setDetailedCurveZoom(nextScale, anchor = null) {
    const previousDomain = detailedCurveView.domain;
    const previousPlot = detailedCurveView.plot;
    const previousScale = detailedCurveView.scale;
    detailedCurveView.scale = clampNumber(nextScale, detailedCurveMinZoom, detailedCurveMaxZoom);
    if (anchor && previousDomain && previousPlot && detailedCurveView.scale !== previousScale) {
      const plotX = clampNumber(anchor.x, previousPlot.left, previousPlot.right);
      const plotY = clampNumber(anchor.y, previousPlot.top, previousPlot.bottom);
      const xRatio = (plotX - previousPlot.left) / Math.max(1e-9, previousPlot.width);
      const yRatio = 1 - ((plotY - previousPlot.top) / Math.max(1e-9, previousPlot.height));
      const anchorDataX = previousDomain.visibleMinX + previousDomain.visibleSpanX * xRatio;
      const anchorDataY = previousDomain.visibleMinY + previousDomain.visibleSpanY * yRatio;
      const nextSpanX = previousDomain.baseSpanX / detailedCurveView.scale;
      const nextSpanY = previousDomain.baseSpanY / detailedCurveView.scale;
      detailedCurveView.centerXNorm = clampNumber((anchorDataX + (0.5 - xRatio) * nextSpanX - previousDomain.baseMinX) / previousDomain.baseSpanX, 0, 1);
      detailedCurveView.centerYNorm = clampNumber((anchorDataY + (0.5 - yRatio) * nextSpanY - previousDomain.baseMinY) / previousDomain.baseSpanY, 0, 1);
    }
    if (detailedCurveView.result) drawCurve(detailedCurveView.result);
  }

  function panDetailedCurve(dx, dy) {
    const domain = detailedCurveView.domain;
    const plot = detailedCurveView.plot;
    if (!domain || !plot || detailedCurveView.scale <= detailedCurveMinZoom + 0.01) return;
    const centerX = domain.baseMinX + domain.baseSpanX * detailedCurveView.centerXNorm;
    const centerY = domain.baseMinY + domain.baseSpanY * detailedCurveView.centerYNorm;
    const nextCenterX = centerX - (dx / Math.max(1, plot.width)) * domain.visibleSpanX;
    const nextCenterY = centerY + (dy / Math.max(1, plot.height)) * domain.visibleSpanY;
    detailedCurveView.centerXNorm = clampNumber((nextCenterX - domain.baseMinX) / domain.baseSpanX, 0, 1);
    detailedCurveView.centerYNorm = clampNumber((nextCenterY - domain.baseMinY) / domain.baseSpanY, 0, 1);
    drawCurve(detailedCurveView.result);
  }

  function drawCurve(result) {
    const canvas = detailedCurveCanvas;
    if (!canvas || !result) return;
    const { ctx, width, height } = prepareCanvas(canvas);
    const compactMobileChart = width <= 520;
    const pad = compactMobileChart
      ? { left: 46, right: 18, top: 12, bottom: 36 }
      : { left: 64, right: 24, top: 20, bottom: 44 };
    const curveModel = buildCurveRenderModel(result);
    const {
      points,
      firstLine,
      secondLine,
      hasBilinearFit,
      lineForce,
      firstStartX,
      firstEndX,
      secondStartX,
      secondEndX,
      fallbackTransitionX,
      baseMinX,
      baseMaxX,
      baseMinY,
      baseMaxY,
      baseSpanX,
      baseSpanY,
      ptPoint,
    } = curveModel;
    const zoom = clampNumber(detailedCurveView.scale, detailedCurveMinZoom, detailedCurveMaxZoom);
    const visibleSpanX = baseSpanX / zoom;
    const visibleSpanY = baseSpanY / zoom;
    const centerX = baseMinX + baseSpanX * clampNumber(detailedCurveView.centerXNorm, 0, 1);
    const centerY = baseMinY + baseSpanY * clampNumber(detailedCurveView.centerYNorm, 0, 1);
    const visibleMinX = clampNumber(centerX - visibleSpanX / 2, baseMinX, baseMaxX - visibleSpanX);
    const visibleMinY = clampNumber(centerY - visibleSpanY / 2, baseMinY, baseMaxY - visibleSpanY);
    const visibleMaxX = visibleMinX + visibleSpanX;
    const visibleMaxY = visibleMinY + visibleSpanY;
    detailedCurveView.centerXNorm = clampNumber(((visibleMinX + visibleSpanX / 2) - baseMinX) / baseSpanX, 0, 1);
    detailedCurveView.centerYNorm = clampNumber(((visibleMinY + visibleSpanY / 2) - baseMinY) / baseSpanY, 0, 1);
    const tickCount = compactMobileChart ? 4 : 6;
    const xTickLabels = Array.from({ length: tickCount }, (_, index) => {
      const value = visibleMinX + (visibleSpanX * index) / (tickCount - 1);
      return Math.abs(value) < 1e-9 ? "0" : new Intl.NumberFormat(numberLocale, { maximumFractionDigits: 4 }).format(value);
    });
    const yTickLabels = Array.from({ length: tickCount }, (_, index) => integerFormatterForAxis(visibleMinY + (visibleSpanY * index) / (tickCount - 1)));
    const axes = drawAxes(
      ctx,
      width,
      height,
      pad,
      xTickLabels,
      yTickLabels,
      t("displacementAxis"),
      t("forceAxis"),
    );
    detailedCurveView.logicalWidth = width;
    detailedCurveView.logicalHeight = height;
    detailedCurveView.domain = { baseMinX, baseMaxX, baseMinY, baseMaxY, baseSpanX, baseSpanY, visibleMinX, visibleMaxX, visibleMinY, visibleMaxY, visibleSpanX, visibleSpanY };
    detailedCurveView.plot = { left: pad.left, right: width - pad.right, top: pad.top, bottom: height - pad.bottom, width: axes.plotWidth, height: axes.plotHeight };
    updateDetailedCurveZoomControls();
    const x = (value) => pad.left + ((value - visibleMinX) / visibleSpanX) * axes.plotWidth;
    const y = (value) => pad.top + axes.plotHeight - ((value - visibleMinY) / visibleSpanY) * axes.plotHeight;
    if (hasBilinearFit) {
      ctx.save();
      ctx.beginPath();
      ctx.rect(pad.left, pad.top, axes.plotWidth, axes.plotHeight);
      ctx.clip();
      ctx.setLineDash([7, 5]);
      ctx.strokeStyle = chartColors.red;
      ctx.lineWidth = 2.25;
      ctx.beginPath();
      ctx.moveTo(x(firstStartX), y(lineForce(firstLine, firstStartX)));
      ctx.lineTo(x(firstEndX), y(lineForce(firstLine, firstEndX)));
      ctx.moveTo(x(secondStartX), y(lineForce(secondLine, secondStartX)));
      ctx.lineTo(x(secondEndX), y(lineForce(secondLine, secondEndX)));
      ctx.stroke();
      ctx.restore();
    }
    ctx.save();
    ctx.beginPath();
    ctx.rect(pad.left, pad.top, axes.plotWidth, axes.plotHeight);
    ctx.clip();
    ctx.beginPath();
    points.forEach((point, index) => {
      if (index === 0) ctx.moveTo(x(point.displacement), y(point.force));
      else ctx.lineTo(x(point.displacement), y(point.force));
    });
    ctx.strokeStyle = "#0f766e";
    ctx.lineWidth = 4;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.stroke();
    ctx.restore();
    const ptX = x(ptPoint?.displacement ?? fallbackTransitionX);
    const ptY = y(ptPoint?.force ?? result.pt);
    const ptIsVisible = ptX >= pad.left && ptX <= width - pad.right && ptY >= pad.top && ptY <= height - pad.bottom;
    if (!ptIsVisible) return;
    if (!hasBilinearFit) {
      ctx.setLineDash([6, 6]);
      ctx.strokeStyle = "rgba(196, 59, 53, 0.55)";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(ptX, pad.top);
      ctx.lineTo(ptX, pad.top + axes.plotHeight);
      ctx.stroke();
      ctx.setLineDash([]);
    }
    const markerRadius = 6;
    ctx.beginPath();
    ctx.moveTo(ptX, ptY - markerRadius);
    ctx.lineTo(ptX + markerRadius, ptY);
    ctx.lineTo(ptX, ptY + markerRadius);
    ctx.lineTo(ptX - markerRadius, ptY);
    ctx.closePath();
    ctx.fillStyle = "#ffffff";
    ctx.fill();
    ctx.strokeStyle = "#7c3aed";
    ctx.lineWidth = 2.5;
    ctx.stroke();
    ctx.fillStyle = "rgba(255,255,255,0.96)";
    ctx.strokeStyle = "#c4b5fd";
    ctx.lineWidth = 1;
    const labelWidth = compactMobileChart ? 88 : 124;
    const labelHeight = compactMobileChart ? 24 : 38;
    const labelX = Math.max(pad.left + 4, Math.min(width - labelWidth - 8, ptX - labelWidth / 2));
    const labelY = pad.top + (compactMobileChart ? 6 : 10);
    ctx.strokeStyle = "rgba(124, 58, 237, 0.66)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(ptX, labelY + labelHeight);
    ctx.lineTo(ptX, ptY - markerRadius - 2);
    ctx.stroke();
    ctx.beginPath();
    ctx.roundRect(labelX, labelY, labelWidth, labelHeight, compactMobileChart ? 6 : 7);
    ctx.fillStyle = "rgba(245,243,255,0.97)";
    ctx.fill();
    ctx.strokeStyle = "#c4b5fd";
    ctx.stroke();
    ctx.textAlign = "left";
    if (compactMobileChart) {
      ctx.fillStyle = "#5b21b6";
      ctx.font = '500 10px -apple-system, "Segoe UI", Inter, sans-serif';
      ctx.fillText(`Pt ${twoDecimalFormatter.format(result.pt)}`, labelX + 7, labelY + 16);
    } else {
      ctx.fillStyle = "#5b21b6";
      ctx.font = '500 11px -apple-system, "Segoe UI", Inter, sans-serif';
      ctx.fillText(t("predictedPt"), labelX + 10, labelY + 14);
      ctx.fillStyle = chartColors.ink;
      ctx.font = '500 14px -apple-system, "Segoe UI", Inter, sans-serif';
      ctx.fillText(twoDecimalFormatter.format(result.pt), labelX + 10, labelY + 30);
    }
  }

  function selectedDesignSpaceCase(result) {
    return activeDesignSpaceCase === "current" ? result?.caseName : activeDesignSpaceCase;
  }

  function updateDesignSpaceFilterUI(result, visiblePoints, visibleLocations) {
    const selectedCase = selectedDesignSpaceCase(result);
    designSpaceFilterButtons.forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.spaceCase === activeDesignSpaceCase));
      if (button.dataset.spaceCase === "current") {
        button.textContent = t("currentCase", { case: caseDisplay(result.caseName) });
      }
    });
    if (designSpaceFilterCount) {
      designSpaceFilterCount.textContent = visiblePoints === visibleLocations
        ? t("experiments", { count: visiblePoints })
        : t("experimentsLocations", { experiments: visiblePoints, locations: visibleLocations });
      designSpaceFilterCount.dataset.case = selectedCase;
    }
  }

  function drawDesignSpace(result) {
    const canvas = designSpaceCanvas;
    if (!canvas || !result) return;
    const { ctx, width, height } = prepareCanvas(canvas);
    const pad = { left: 62, right: 28, top: 24, bottom: 50 };
    const axes = drawAxes(ctx, width, height, pad, ["−90", "−45", "0", "45", "90"], ["−90", "−45", "0", "45", "90"], "θ₁", "θ₂");
    const x = (value) => pad.left + ((value + 90) / 180) * axes.plotWidth;
    const y = (value) => pad.top + axes.plotHeight - ((value + 90) / 180) * axes.plotHeight;
    const colors = ["#0f9f6e", "#0c8fd8", "#df4b3f"];
    const mapPoints = result.designSpace?.map_points || [];
    const fallbackPoints = Array.from({ length: 27 }, (_, flatIndex) => {
      const caseIndex = Math.floor(flatIndex / 9);
      const index = flatIndex % 9;
      return {
        theta1: -76 + index * 19 + caseIndex * 4,
        theta2: -68 + ((index * 37 + caseIndex * 22) % 142),
        type: ((index + caseIndex) % 3) + 1,
        case: `Case${caseIndex + 2}`,
      };
    });
    const allPoints = mapPoints.length ? mapPoints : fallbackPoints;
    const selectedCase = selectedDesignSpaceCase(result);
    const points = selectedCase === "all"
      ? allPoints
      : allPoints.filter((point) => point.case === selectedCase);
    const locationGroups = new Map();
    points.forEach((point, index) => {
      const typeIndex = Math.max(0, Math.min(2, number(point.type, (index % 3) + 1) - 1));
      const pointX = x(number(point.theta1));
      const pointY = y(number(point.theta2));
      const pointRadius = 3.5 + Math.min(3, Math.max(0, number(point.pt) / 12000));
      const key = `${number(point.theta1).toFixed(4)}|${number(point.theta2).toFixed(4)}`;
      const group = locationGroups.get(key) || { x: pointX, y: pointY, radius: pointRadius, points: [] };
      group.points.push(point);
      group.radius = Math.max(group.radius, group.points.length > 1 ? 7 : pointRadius);
      locationGroups.set(key, group);
      ctx.beginPath();
      ctx.arc(pointX, pointY, group.radius, 0, Math.PI * 2);
      ctx.fillStyle = colors[typeIndex];
      ctx.globalAlpha = mapPoints.length
        ? selectedCase === "all" ? (point.case === result.caseName ? 0.78 : 0.32) : 0.72
        : 0.34;
      ctx.fill();
      if (group.points.length > 1) {
        ctx.strokeStyle = "rgba(255,255,255,0.9)";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    });
    designSpaceHoverPoints = [...locationGroups.values()];
    updateDesignSpaceFilterUI(result, points.length, locationGroups.size);
    ctx.globalAlpha = 1;
    const showCurrentInput = selectedCase === "all" || selectedCase === result.caseName;
    if (showCurrentInput) {
      const currentX = x(result.theta1);
      const currentY = y(result.theta2);
      designSpaceHoverPoints.push({
        x: currentX,
        y: currentY,
        radius: 9,
        points: [{
          isCurrentInput: true,
          theta1: result.theta1,
          theta2: result.theta2,
          case: result.caseName,
          type: result.type,
          pt: result.pt,
          confidence: result.confidence,
        }],
      });
      ctx.beginPath();
      ctx.arc(currentX, currentY, 9, 0, Math.PI * 2);
      ctx.fillStyle = "#6d28d9";
      ctx.fill();
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 3;
      ctx.stroke();
      ctx.fillStyle = chartColors.ink;
      ctx.font = '500 11px -apple-system, "Segoe UI", Inter, sans-serif';
      ctx.textAlign = "left";
      ctx.fillText(t("currentInput"), Math.min(width - 72, currentX + 13), Math.max(18, currentY - 10));
    }
    hideDesignSpaceTooltip();
  }

  function hideDesignSpaceTooltip() {
    if (!designSpaceTooltip) return;
    designSpaceTooltip.classList.add("hidden");
    designSpaceTooltip.innerHTML = "";
    if (designSpaceCanvas) designSpaceCanvas.style.cursor = "default";
  }

  function appendTooltipField(list, label, value) {
    const group = document.createElement("div");
    const term = document.createElement("dt");
    const detail = document.createElement("dd");
    term.textContent = label;
    detail.textContent = value;
    group.append(term, detail);
    list.appendChild(group);
  }

  function renderDesignSpaceTooltip(points) {
    if (!designSpaceTooltip || !points?.length) return;
    designSpaceTooltip.innerHTML = "";
    const point = points[0];
    const title = document.createElement("strong");
    title.textContent = point.isCurrentInput
      ? `${t("currentInput")} · ${caseDisplay(point.case)}`
      : points.length > 1
        ? `${signedAngle(point.theta1)} / ${signedAngle(point.theta2)} · ${t("experiments", { count: points.length })}`
        : `${caseDisplay(point.case)} · ${point.type == null ? "Type -" : `Type ${point.type}`}`;
    const context = document.createElement("span");
    context.textContent = point.isCurrentInput
      ? t("modelPrediction")
      : points.length > 1 ? t("sameLocation") : point.case === currentResult?.caseName ? t("selectedCaseAnalysis") : t("otherCaseAnalysis");
    const list = document.createElement("dl");
    appendTooltipField(list, "θ₁", signedAngle(point.theta1));
    appendTooltipField(list, "θ₂", signedAngle(point.theta2));
    if (point.isCurrentInput) {
      appendTooltipField(list, "Pt", point.pt == null ? "-" : twoDecimalFormatter.format(number(point.pt)));
      appendTooltipField(list, t("reliability"), point.confidence == null ? "-" : formatPercent(point.confidence, 1));
      designSpaceTooltip.append(title, context, list);
      return;
    }
    const results = document.createElement("div");
    results.className = "space-tooltip-results";
    points
      .slice()
      .sort((left, right) => left.case.localeCompare(right.case))
      .forEach((entry) => {
        const row = document.createElement("div");
        row.className = "space-tooltip-result";
        const label = document.createElement("strong");
        label.textContent = `${caseDisplay(entry.case)} · ${entry.type == null ? "Type -" : `Type ${entry.type}`}`;
        const test = document.createElement("span");
        test.textContent = entry.test_id || "Test -";
        const pt = document.createElement("b");
        pt.textContent = `Pt ${twoDecimalFormatter.format(number(entry.pt))}`;
        row.append(label, test, pt);
        results.appendChild(row);
      });
    designSpaceTooltip.append(title, context, list, results);
  }

  function handleDesignSpacePointerMove(event) {
    if (!designSpaceCanvas || !designSpaceTooltip) return;
    const rect = designSpaceCanvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const cssX = event.clientX - rect.left;
    const cssY = event.clientY - rect.top;
    const canvasX = cssX;
    const canvasY = cssY;
    const nearest = designSpaceHoverPoints.reduce((best, entry) => {
      const distance = Math.hypot(entry.x - canvasX, entry.y - canvasY);
      if (distance > Math.max(12, entry.radius + 7)) return best;
      const primaryPoint = entry.points[0];
      const priority = primaryPoint.isCurrentInput ? -10 : entry.points.some((point) => point.case === currentResult?.caseName) ? -2 : 0;
      const score = distance + priority;
      return !best || score < best.score ? { entry, score } : best;
    }, null);
    if (!nearest) {
      hideDesignSpaceTooltip();
      return;
    }
    renderDesignSpaceTooltip(nearest.entry.points);
    designSpaceTooltip.classList.remove("hidden");
    designSpaceCanvas.style.cursor = "pointer";
    const tooltipRect = designSpaceTooltip.getBoundingClientRect();
    const gap = 14;
    let left = cssX + gap;
    let top = cssY + gap;
    if (left + tooltipRect.width > rect.width - 8) left = cssX - tooltipRect.width - gap;
    if (top + tooltipRect.height > rect.height - 8) top = cssY - tooltipRect.height - gap;
    designSpaceTooltip.style.left = `${Math.max(8, left)}px`;
    designSpaceTooltip.style.top = `${Math.max(8, top)}px`;
  }

  function renderXai(result) {
    const list = document.querySelector("#rebuild-xai-list");
    const explanation = result?.xai;
    document.querySelector("#xai-method").textContent = localizeXaiText(explanation?.method || "Occlusion sensitivity · preview");
    const summary = explanation?.summary || t("xaiPreviewSummary");
    document.querySelector("#xai-summary").textContent = `${localizeXaiText(summary)} ${t("xaiNormalized")}`;
    const notes = document.querySelector("#xai-notes");
    notes.innerHTML = "";
    (explanation?.notes || [t("xaiFallbackNote")]).slice(0, 3).forEach((note) => {
      const item = document.createElement("li");
      item.textContent = localizeXaiText(note);
      notes.appendChild(item);
    });
    const influenceShift = result ? Math.min(6, Math.abs(result.theta1 + result.theta2) / 12) : 0;
    list.innerHTML = "";
    if (xaiMoreList) xaiMoreList.innerHTML = "";
    const receivedFeatures = explanation?.top_features || [];
    const features = receivedFeatures.length
      ? receivedFeatures.map((feature) => [feature.label || feature.name, feature.explanation, Math.min(100, Math.abs(number(feature.importance)) * 100), feature])
      : xaiFeatures.map((feature) => [...feature, null]);
    const appendFeature = (target, [title, description, baseScore, feature], index) => {
      const score = receivedFeatures.length ? baseScore : Math.max(0.1, baseScore + (index === 0 ? influenceShift : -influenceShift / 4));
      const displayScore = oneDecimalFormatter.format(score);
      const barWidth = score > 0 ? Math.max(2, score) : 0;
      const localizedFeature = feature
        ? localizeXaiFeature(feature)
        : { title: localizeXaiText(title), description: localizeXaiText(description) };
      const item = document.createElement("article");
      item.className = "xai-item";

      const copy = document.createElement("div");
      const heading = document.createElement("div");
      heading.className = "xai-item-heading";
      const featureTitle = document.createElement("strong");
      featureTitle.textContent = localizedFeature.title;
      heading.appendChild(featureTitle);
      if (feature) {
        const category = document.createElement("span");
        category.className = "xai-category";
        category.textContent = xaiCategoryLabel(feature.category, feature.name);
        heading.appendChild(category);
      }
      const featureDescription = document.createElement("small");
      featureDescription.textContent = localizedFeature.description;
      copy.append(heading, featureDescription);

      if (feature) {
        const metaParts = [];
        if (feature.local_value != null) {
          metaParts.push(t("xaiCurrentValue", {
            value: new Intl.NumberFormat(numberLocale, { maximumFractionDigits: 4 }).format(number(feature.local_value)),
          }));
        }
        if (feature.local_sensitivity != null) {
          metaParts.push(t("localSensitivity", {
            value: new Intl.NumberFormat(numberLocale, { maximumFractionDigits: 5 }).format(Math.abs(number(feature.local_sensitivity))),
          }));
        }
        if (feature.perturbation) metaParts.push(localizeXaiPerturbation(feature.perturbation));
        if (metaParts.length) {
          const meta = document.createElement("small");
          meta.className = "xai-feature-meta";
          meta.textContent = metaParts.join(" · ");
          copy.appendChild(meta);
        }
      }

      const bar = document.createElement("div");
      bar.className = "xai-bar";
      bar.setAttribute("aria-hidden", "true");
      const fill = document.createElement("i");
      fill.style.width = `${barWidth}%`;
      bar.appendChild(fill);

      const scoreLabel = document.createElement("span");
      scoreLabel.className = "xai-score";
      scoreLabel.setAttribute("aria-label", t("relativeContribution", { value: displayScore }));
      scoreLabel.textContent = `${displayScore}%`;

      item.append(copy, bar, scoreLabel);
      target.appendChild(item);
    };
    features.slice(0, xaiPrimaryFeatureCount).forEach((feature, index) => appendFeature(list, feature, index));
    const additionalFeatures = features.slice(xaiPrimaryFeatureCount);
    if (xaiMore && xaiMoreCount && xaiMoreList && additionalFeatures.length) {
      xaiMore.classList.remove("hidden");
      xaiMore.open = false;
      xaiMoreCount.textContent = t("moreCount", { count: additionalFeatures.length });
      additionalFeatures.forEach((feature, index) => appendFeature(xaiMoreList, feature, index + xaiPrimaryFeatureCount));
    } else if (xaiMore) {
      xaiMore.classList.add("hidden");
      xaiMore.open = false;
      if (xaiMoreCount) xaiMoreCount.textContent = t("moreCount", { count: 0 });
    }
  }

  function setDesignSpaceCaseFilter(value) {
    activeDesignSpaceCase = value;
    if (currentResult) drawDesignSpace(currentResult);
  }

  function handleDesignSpacePointerDown(event) {
    if (event.pointerType === "mouse") return;
    handleDesignSpacePointerMove(event);
  }

  function applyDesignSpace(result, designSpace) {
    result.designSpace = designSpace;
    const caseSummary = designSpace.case_summaries?.find((item) => item.case === result.caseName);
    const nearest = designSpace.nearest_points?.[0];
    const recommendation = designSpace.recommendations?.[0];
    if (caseSummary) {
      const labels = { low: t("reliabilityLow"), medium: t("reliabilityMedium"), high: t("reliabilityHigh") };
      document.querySelector("#space-risk").textContent = `${labels[caseSummary.risk_label] || t("reliabilityMedium")} · ${formatPercent(caseSummary.risk_score, 0)}`;
    }
    if (nearest) {
      document.querySelector("#space-nearest").textContent = `${caseDisplay(nearest.case)} · Δθ ${oneDecimalFormatter.format(nearest.distance)}°`;
    }
    if (recommendation) {
      document.querySelector("#space-recommendation").textContent = `${caseDisplay(recommendation.case)} · θ ${signedAngle(recommendation.theta1)} / ${signedAngle(recommendation.theta2)}`;
    }
    document.querySelector("#space-note").textContent = designSpace.notes?.[0] || t("designSpaceDefault");
    if (currentTab === "space") drawDesignSpace(result);
  }

  function comparisonValue(run, key) {
    if (key === "case") return run.caseName;
    if (key === "type") return run.type;
    return run[key];
  }

  function renderHistory() {
    const hasRuns = runs.length > 0;
    if (comparisonTable) comparisonTable.hidden = !hasRuns;
    if (comparisonEmpty) comparisonEmpty.hidden = hasRuns;
    const direction = sortState.direction === "ascending" ? 1 : -1;
    const sorted = [...runs].sort((left, right) => {
      const a = comparisonValue(left, sortState.key);
      const b = comparisonValue(right, sortState.key);
      if (typeof a === "string") return a.localeCompare(b) * direction;
      return (number(a) - number(b)) * direction;
    });
    historyBody.innerHTML = "";
    sorted.forEach((run) => {
      const row = document.createElement("tr");
      row.tabIndex = 0;
      row.dataset.runId = String(run.createdAt);
      row.setAttribute("aria-label", `${caseDisplay(run.caseName)}, ${run.modelLabel}, θ₁ ${run.theta1}, θ₂ ${run.theta2}, Type ${run.type}, Pt ${run.pt}`);
      row.innerHTML = `
        <td data-label="Case"><strong>${caseDisplay(run.caseName)}</strong></td>
        <td data-label="${locale === "ko" ? "모델" : "Model"}"><span class="model-chip">${modelDisplayLabel({ label: run.modelLabel || "Laminate Forecast" })}</span></td>
        <td data-label="Theta 1">${signedAngle(run.theta1)}</td>
        <td data-label="Theta 2">${signedAngle(run.theta2)}</td>
        <td data-label="Type"><span class="type-chip">Type ${run.type}</span></td>
        <td data-label="Pt"><strong>${twoDecimalFormatter.format(run.pt)}</strong></td>
        <td data-label="${t("reliability")}"><span class="reliability-chip ${run.reliability === t("reliabilityHigh") ? "high" : "medium"}">${run.reliability} · ${formatPercent(run.reliabilityScore, 0)}</span></td>
      `;
      const reuse = () => reuseRun(run);
      row.addEventListener("click", reuse);
      row.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          reuse();
        }
      });
      historyBody.appendChild(row);
    });
    highlightMatchingRun(inputValues());
  }

  function showExampleResult() {
    updateSummary(exampleResult);
    activateTab("summary");
  }

  function highlightMatchingRun(values) {
    [...historyBody.querySelectorAll("tr")].forEach((row) => {
      const run = runs.find((item) => String(item.createdAt) === row.dataset.runId);
      const matches = run
        && run.modelKey === values.modelKey
        && run.caseName === values.caseName
        && run.theta1 === values.theta1
        && run.theta2 === values.theta2
        && run.panelA === values.panelA
        && run.panelB === values.panelB;
      row.classList.toggle("current", Boolean(matches));
    });
  }

  function reuseRun(run) {
    if ([...modelSelect.options].some((option) => option.value === run.modelKey && !option.disabled)) {
      form.elements.model.value = run.modelKey;
      updateModelDescription();
    }
    form.elements.case.value = run.caseName;
    form.elements.theta1.value = String(run.theta1);
    form.elements.theta1_range.value = String(run.theta1);
    form.elements.theta2.value = String(run.theta2);
    form.elements.theta2_range.value = String(run.theta2);
    form.elements.panel_a.value = String(run.panelA);
    form.elements.panel_b.value = String(run.panelB);
    syncInputInterface();
    updateSummary(run);
    activateTab("summary");
    setupPanel.scrollIntoView({ behavior: "smooth", block: "start" });
    inlineState.textContent = t("restoredRun");
    inlineState.className = "inline-state success";
  }

  function validateInputs(values) {
    if (Math.abs(values.theta1) > 90 || Math.abs(values.theta2) > 90) {
      return t("invalidTheta");
    }
    if (values.panelA <= 0 || values.panelB <= 0) {
      return t("invalidPanel");
    }
    return "";
  }

  async function loadSupportingInsights(result) {
    const payload = {
      theta1: result.theta1,
      theta2: result.theta2,
      case: result.caseName,
      panel_a_in: result.panelA,
      panel_b_in: result.panelB,
    };
    const designSpaceRequest = fetchJson("/design-space", {
        method: "POST",
        body: JSON.stringify({
          ...payload,
          scope: "response",
          dataset: "three_size",
        }),
      }, 30000)
      .then((designSpace) => {
        if (currentResult !== result) return;
        applyDesignSpace(result, designSpace);
      })
      .catch(() => {});
    const xaiRequest = fetchJson("/xai/local", {
        method: "POST",
        body: JSON.stringify({ ...payload, model: result.modelKey }),
      }, 30000)
      .then((xai) => {
        if (currentResult !== result) return;
        result.xai = xai;
        renderXai(result);
      })
      .catch(() => {
        if (currentResult !== result) return;
        document.querySelector("#xai-method").textContent = "Physics feature sensitivity · fallback";
      });
    await Promise.allSettled([designSpaceRequest, xaiRequest]);
  }

  async function runForecast(event) {
    event.preventDefault();
    const values = inputValues();
    const validationMessage = validateInputs(values);
    if (validationMessage) {
      inlineState.textContent = validationMessage;
      inlineState.className = "inline-state error";
      return;
    }
    runButton.disabled = true;
    inlineState.textContent = t("calculating");
    inlineState.className = "inline-state";
    try {
      if (!apiConnected) {
        await new Promise((resolve) => window.setTimeout(resolve, 320));
        throw new Error("preview mode");
      }
      const data = await fetchJson("/predict/response/3size-preview", {
        method: "POST",
        body: JSON.stringify({
          theta1: values.theta1,
          theta2: values.theta2,
          case: values.caseName,
          model: values.modelKey,
          panel_a_in: values.panelA,
          panel_b_in: values.panelB,
        }),
      });
      const result = normalizePrediction(data, values);
      runs.unshift(result);
      updateSummary(result);
      renderHistory();
      activateTab("summary");
      inlineState.textContent = t("predictionComplete");
      inlineState.className = "inline-state success";
      loadSupportingInsights(result);
      document.querySelector(".result-workspace").animate(
        [
          { borderColor: "#8fa9eb" },
          { borderColor: "#dce1e9" },
        ],
        { duration: 900, easing: "ease-out" },
      );
      if (window.innerWidth < 1024) {
        document.querySelector(".result-workspace").scrollIntoView({ behavior: "smooth", block: "start" });
      }
    } catch {
      const result = makeResult(values);
      runs.unshift(result);
      updateSummary(result);
      renderHistory();
      activateTab("summary");
      inlineState.textContent = t("apiFallback");
      inlineState.className = "inline-state warning";
    } finally {
      runButton.disabled = false;
    }
  }

  modeButtons.forEach((button) => {
    button.addEventListener("click", () => setAnalysisMode(button.dataset.analysisMode));
    button.addEventListener("keydown", handleModeKeydown);
  });

  tabButtons.forEach((button) => {
    button.addEventListener("click", () => activateTab(button.dataset.resultTab));
    button.addEventListener("keydown", handleTabKeydown);
  });

  form.addEventListener("submit", runForecast);
  showExampleButton?.addEventListener("click", showExampleResult);
  form.addEventListener("input", (event) => {
    if (event.target.matches('[name="theta1"], [name="theta1_range"], [name="theta2"], [name="theta2_range"]')) {
      syncAnglePair(event.target);
      return;
    }
    syncInputInterface();
  });
  form.addEventListener("change", syncInputInterface);
  modelSelect.addEventListener("change", updateModelDescription);
  detailedCurveZoomButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const action = button.dataset.curveZoom;
      if (action === "in") setDetailedCurveZoom(detailedCurveView.scale * 1.35);
      else if (action === "out") setDetailedCurveZoom(detailedCurveView.scale / 1.35);
      else resetDetailedCurveView(true);
    });
  });
  detailedCurveCanvas?.addEventListener("wheel", (event) => {
    if (!detailedCurveView.result) return;
    event.preventDefault();
    const factor = event.deltaY < 0 ? 1.15 : 1 / 1.15;
    setDetailedCurveZoom(detailedCurveView.scale * factor, detailedCurvePointFromEvent(event));
  }, { passive: false });
  detailedCurveCanvas?.addEventListener("pointerdown", (event) => {
    if (!detailedCurveView.result) return;
    const point = detailedCurvePointerPoint(event);
    if (!point) return;
    event.preventDefault();
    detailedCurveView.pointers.set(event.pointerId, point);
    detailedCurveCanvas.setPointerCapture?.(event.pointerId);
    if (detailedCurveView.pointers.size >= 2) {
      const metrics = detailedCurvePinchMetrics();
      detailedCurveView.pinch = metrics ? {
        startDistance: metrics.distance,
        startScale: detailedCurveView.scale,
        anchor: metrics.anchor,
      } : null;
      detailedCurveView.drag = null;
    } else if (detailedCurveView.scale > detailedCurveMinZoom + 0.01) {
      detailedCurveView.drag = point;
    }
  });
  detailedCurveCanvas?.addEventListener("pointermove", (event) => {
    if (!detailedCurveView.pointers.has(event.pointerId)) return;
    const point = detailedCurvePointerPoint(event);
    if (!point) return;
    event.preventDefault();
    detailedCurveView.pointers.set(event.pointerId, point);
    if (detailedCurveView.pointers.size >= 2 && detailedCurveView.pinch) {
      const metrics = detailedCurvePinchMetrics();
      if (metrics) {
        const factor = metrics.distance / detailedCurveView.pinch.startDistance;
        setDetailedCurveZoom(detailedCurveView.pinch.startScale * factor, detailedCurveView.pinch.anchor);
      }
      return;
    }
    if (!detailedCurveView.drag) return;
    panDetailedCurve(point.x - detailedCurveView.drag.x, point.y - detailedCurveView.drag.y);
    detailedCurveView.drag = point;
  });
  ["pointerup", "pointercancel", "pointerleave"].forEach((eventName) => {
    detailedCurveCanvas?.addEventListener(eventName, (event) => {
      detailedCurveView.pointers.delete(event.pointerId);
      if (detailedCurveCanvas.hasPointerCapture?.(event.pointerId)) {
        detailedCurveCanvas.releasePointerCapture(event.pointerId);
      }
      detailedCurveView.pinch = null;
      const remainingPoint = [...detailedCurveView.pointers.values()][0] || null;
      detailedCurveView.drag = remainingPoint && detailedCurveView.scale > detailedCurveMinZoom + 0.01
        ? remainingPoint
        : null;
    });
  });
  detailedCurveCanvas?.addEventListener("dblclick", () => resetDetailedCurveView(true));
  designSpaceCanvas?.addEventListener("pointermove", handleDesignSpacePointerMove);
  designSpaceCanvas?.addEventListener("pointerdown", handleDesignSpacePointerDown);
  designSpaceCanvas?.addEventListener("pointerleave", hideDesignSpaceTooltip);
  designSpaceFilterButtons.forEach((button) => {
    button.addEventListener("click", () => setDesignSpaceCaseFilter(button.dataset.spaceCase));
  });

  document.querySelectorAll("[data-open-deep]").forEach((button) => {
    button.addEventListener("click", (event) => {
      setAnalysisMode("deep");
      activateTab(event.currentTarget.dataset.openDeep, true);
    });
  });

  document.querySelectorAll("[data-sort]").forEach((button) => {
    button.addEventListener("click", () => {
      const key = button.dataset.sort;
      const direction = sortState.key === key && sortState.direction === "descending" ? "ascending" : "descending";
      sortState = { key, direction };
      document.querySelectorAll("[data-sort]").forEach((candidate) => {
        candidate.setAttribute("aria-sort", candidate === button ? direction : "none");
      });
      renderHistory();
    });
  });

  let resizeTimer = null;
  window.addEventListener("resize", () => {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(() => {
      drawSummaryCurve(currentResult);
      if (currentTab === "curve") drawCurve(currentResult);
      if (currentTab === "space") drawDesignSpace(currentResult);
    }, 100);
  });

  try {
    currentMode = sessionStorage.getItem(modeStorageKey) || "quick";
  } catch {
    currentMode = "quick";
  }
  setAnalysisMode(currentMode, false);
  syncInputInterface();
  setResultPresence(false);
  renderHistory();
  loadModels().finally(restoreLocaleState);
})();
