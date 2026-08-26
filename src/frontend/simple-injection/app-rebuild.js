(() => {
  if (!document.documentElement.classList.contains("injection-rebuild")) return;
  const localePack = window.ImperialAXInjectionLocale || { locale: "ko", t: (key) => key };
  const { locale, t } = localePack;
  const localeStateStorageKey = "imperialax.injection.v2.locale-state.v1";

  const workspace = document.querySelector(".workspace");
  const header = document.querySelector(".topbar");
  const grid = document.querySelector("#workspace-grid");
  const form = document.querySelector("#prediction-form");
  const inputPanel = document.querySelector(".input-panel");
  const visualPanel = document.querySelector(".visual-panel");
  const resultWorkspace = document.querySelector(".result-panel");
  const result = document.querySelector("#result");
  const emptyState = document.querySelector("#empty-state");
  const history = document.querySelector("#prediction-history");

  if (!workspace || !header || !grid || !form || !inputPanel || !visualPanel || !resultWorkspace || !result) {
    return;
  }

  function saveLocaleState(targetLocale) {
    const controls = {};
    [...form.elements].forEach((control) => {
      if (control.name && control.type !== "file") controls[control.name] = control.value;
    });
    try {
      sessionStorage.setItem(localeStateStorageKey, JSON.stringify({
        targetLocale,
        controls,
        mode: document.body.dataset.analysisMode || "quick",
        rerun: !result.classList.contains("hidden"),
      }));
    } catch {
      // Locale switching still works when session storage is unavailable.
    }
  }

  document.body.classList.add("injection-rebuild-body");
  workspace.classList.add("rebuild-workspace");
  header.classList.add("rebuild-header");
  grid.classList.add("forecast-layout");
  inputPanel.classList.add("forecast-setup");
  resultWorkspace.classList.add("analysis-workspace");

  const brandLockup = header.querySelector(".brand-lockup");
  if (brandLockup) {
    brandLockup.innerHTML = `
      <a class="rebuild-brand" href="/" aria-label="${t("returnCurrentAria")}">
        <img src="/brand/imperialax-logo-black.png" alt="ImperialAX" />
      </a>
      <div class="rebuild-title">
        <span>Injection Forecast</span>
        <strong id="app-title">${t("screeningTitle")}</strong>
      </div>
    `;
  }

  const topActions = header.querySelector(".top-actions");
  if (topActions) {
    topActions.classList.add("rebuild-actions");
    const links = [...topActions.querySelectorAll("a")];
    const accountLink = links[2];
    if (links[0]) {
      links[0].href = "/";
      links[0].textContent = t("previousUi");
    }
    if (links[1]) {
      links[1].remove();
    }
    const localeNav = document.createElement("nav");
    localeNav.className = "rebuild-locale-switcher";
    localeNav.setAttribute("aria-label", t("languageNav"));
    [["ko", "한국어"], ["en", "English"]].forEach(([code, label]) => {
      const link = document.createElement("a");
      link.className = "language-link";
      link.href = `/v2/${code}`;
      link.lang = code;
      link.textContent = label;
      if (locale === code) link.setAttribute("aria-current", "page");
      link.addEventListener("click", () => saveLocaleState(code));
      localeNav.appendChild(link);
    });

    const status = topActions.querySelector(".status-pill");
    topActions.querySelectorAll(".utility-trigger").forEach((button) => button.remove());
    if (links[0]) topActions.appendChild(links[0]);
    if (accountLink) topActions.appendChild(accountLink);
    if (status) topActions.appendChild(status);
    topActions.querySelectorAll(".top-action-group").forEach((group) => group.remove());
    topActions.appendChild(localeNav);
  }

  const commandBar = document.createElement("section");
  commandBar.className = "command-bar";
  commandBar.setAttribute("aria-label", t("analysisModeInput"));
  commandBar.innerHTML = `
    <div class="analysis-mode">
      <span>${t("analysisMode")}</span>
      <div class="segmented-control" role="radiogroup" aria-label="${t("analysisMode")}">
        <button type="button" role="radio" aria-checked="true" tabindex="0" data-analysis-mode="quick">${t("quick")}</button>
        <button type="button" role="radio" aria-checked="false" tabindex="-1" data-analysis-mode="deep">${t("deep")}</button>
      </div>
    </div>
    <p class="current-input">
      <span>${t("currentInput")}</span>
      <strong id="current-input-summary">${t("loadingDoe")}</strong>
    </p>
  `;
  header.insertAdjacentElement("afterend", commandBar);

  const formHeader = form.querySelector(".form-header");
  if (formHeader) {
    const eyebrow = formHeader.querySelector(".eyebrow");
    const title = formHeader.querySelector("h2");
    const copy = formHeader.querySelector("p:not(.eyebrow)");
    if (eyebrow) eyebrow.textContent = "Forecast setup";
    if (title) title.textContent = t("candidateSetup");
    if (copy) copy.textContent = t("setupCopy");
  }

  function replaceLabelText(control, text) {
    const label = control?.closest("label");
    const textNode = [...(label?.childNodes || [])].find(
      (node) => node.nodeType === Node.TEXT_NODE && node.textContent.trim(),
    );
    if (textNode) textNode.textContent = `\n                    ${text}\n                    `;
  }

  replaceLabelText(form.elements.model, t("sprueModel"));
  replaceLabelText(form.elements.filling_model, t("fillingModel"));
  replaceLabelText(form.elements.geometry_id, t("geometryDoe"));
  replaceLabelText(form.elements.process_id, t("processDoe"));

  const processLabels = {
    melt_temp_C: t("meltTemperature"),
    mold_temp_C: t("moldTemperature"),
    packing_pressure_MPa: t("packingPressure"),
    injection_time_s: t("injectionTime"),
    packing_time_s: t("packingTime"),
  };
  Object.entries(processLabels).forEach(([name, label]) => {
    const target = form.elements[name]?.closest("label")?.querySelector("span");
    if (target) target.textContent = label;
  });

  const geometryLabels = {
    L_mm: t("length"),
    W_mm: t("width"),
    t_mm: t("thickness"),
    D_mm: t("holeDiameter"),
    R_mm: t("holeRadius"),
  };
  Object.entries(geometryLabels).forEach(([name, label]) => {
    const target = form.elements[name]?.closest("label")?.querySelector("span");
    if (target) target.textContent = label;
  });

  const fixedGateCondition = form.querySelector(".fixed-gate-condition");
  if (fixedGateCondition) {
    fixedGateCondition.querySelector(".fixed-gate-head > span:first-child").textContent = t("gateCondition");
    fixedGateCondition.querySelector(".fixed-gate-badge").textContent = t("gateFixedStatus");
    fixedGateCondition.querySelector(".fixed-gate-type span").textContent = t("gateTypeLabel");
    fixedGateCondition.querySelector(".fixed-gate-type strong").textContent = t("gateTypeValue");
    fixedGateCondition.querySelector(".fixed-gate-size span").textContent = t("gateSizeLabel");
    fixedGateCondition.querySelector(".fixed-gate-size strong").textContent = t("gateSizeValue");
    fixedGateCondition.querySelector("small").textContent = t("gateFixedNote");
  }

  const modelLabels = {
    sprue_classical: t("machineLearning"),
    sprue_goint: t("deepLearning"),
    sprue_deeponet: t("operatorLearning"),
    filling_classical: t("machineLearning"),
    filling_goint: t("deepLearning"),
    filling_deeponet: t("operatorLearning"),
  };
  function localizeModelOptions(select) {
    [...(select?.options || [])].forEach((option, index) => {
      const label = modelLabels[option.value];
      if (!label) return;
      option.textContent = option.disabled
        ? `${label} (${t("unavailable")})`
        : `${label}${index === 0 ? ` · ${t("recommended")}` : ""}`;
    });
  }
  [form.elements.model, form.elements.filling_model].forEach((select) => {
    localizeModelOptions(select);
    if (select) {
      new MutationObserver(() => localizeModelOptions(select)).observe(select, { childList: true });
    }
  });

  const preventionTitle = document.querySelector("#prevention-title");
  function localizePreventionTitle() {
    if (preventionTitle?.textContent.includes("Prevention check")) {
      preventionTitle.textContent = t("preventionComplete");
    }
  }
  localizePreventionTitle();
  if (preventionTitle) {
    new MutationObserver(localizePreventionTitle).observe(preventionTitle, {
      childList: true,
      characterData: true,
      subtree: true,
    });
  }

  const geometryDetails = [...form.children].find(
    (element) => element.classList?.contains("advanced-fields") && !element.closest(".process-block"),
  );
  geometryDetails?.classList.add("geometry-details");

  const submitButton = form.querySelector('.primary[type="submit"]:not(.mobile-quick-run)');
  visualPanel.classList.add("embedded-preview");
  const doeSetup = form.elements.geometry_id?.closest(".setup-block");
  doeSetup?.after(visualPanel);
  if (submitButton) {
    submitButton.dataset.defaultText = t("runForecast");
    const decorateSubmitButton = () => {
      if (submitButton.textContent.trim() !== t("runForecast") || submitButton.querySelector("small")) return;
      submitButton.innerHTML = `<span>${t("runForecast")}</span><small>${t("runForecastDetail")}</small>`;
    };
    submitButton.textContent = t("runForecast");
    decorateSubmitButton();
    new MutationObserver(decorateSubmitButton).observe(submitButton, { childList: true });
  }

  const analysisHeading = document.createElement("div");
  analysisHeading.className = "analysis-heading";
  analysisHeading.innerHTML = `
    <div>
      <span>Analysis workspace</span>
      <h2>${t("results")}</h2>
    </div>
    <p id="result-status-copy">${t("noResultYet")}</p>
  `;

  const tabList = document.createElement("div");
  tabList.className = "result-tabs";
  tabList.setAttribute("role", "tablist");
  tabList.setAttribute("aria-label", t("resultViews"));

  const tabDefinitions = [
    ["summary", t("summary")],
    ["curve", t("sprueCurve")],
    ["filling", t("fillingDistribution")],
    ["xai", "XAI"],
    ["validation", t("validation")],
  ];

  tabDefinitions.forEach(([key, label], index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.id = `injection-tab-${key}`;
    button.textContent = label;
    button.dataset.resultTab = key;
    button.setAttribute("role", "tab");
    button.setAttribute("aria-controls", `injection-panel-${key}`);
    button.setAttribute("aria-selected", index === 0 ? "true" : "false");
    button.setAttribute("aria-disabled", index === 0 ? "false" : "true");
    button.tabIndex = index === 0 ? 0 : -1;
    tabList.appendChild(button);
  });

  resultWorkspace.insertBefore(analysisHeading, emptyState || resultWorkspace.firstChild);
  resultWorkspace.insertBefore(tabList, emptyState || resultWorkspace.firstChild);
  tabList.hidden = true;

  if (emptyState) {
    emptyState.innerHTML = `
      <div class="empty-state-mark" aria-hidden="true"><i></i><i></i><i></i></div>
      <span>Forecast result</span>
      <h2>${t("emptyTitle")}</h2>
      <p>${t("emptyCopy")}</p>
      <button type="button" id="show-injection-example">${t("showExample")}</button>
      <small>${t("exampleDisclaimer")}</small>
    `;
  }

  const deepDiveHint = document.createElement("p");
  deepDiveHint.className = "deep-dive-hint";
  deepDiveHint.innerHTML = `${t("deepHintBefore")} <button type="button">${t("deep")}</button>${t("deepHintAfter")}`;
  tabList.insertAdjacentElement("afterend", deepDiveHint);
  deepDiveHint.hidden = true;

  const resultHead = result.querySelector(".result-head");
  resultHead?.classList.add("rebuild-result-head");

  const panelNodes = {
    summary: document.createElement("section"),
    curve: result.querySelector(".chart-card"),
    filling: result.querySelector(".filling-card"),
    xai: result.querySelector(".xai-card"),
    validation: result.querySelector(".compare-card"),
  };

  const injectionXaiList = panelNodes.xai?.querySelector("#xai-feature-list");

  function normalizeInjectionXaiFeature(item) {
    if (!item || item.dataset.laminateXaiLayout === "true") return;
    const top = item.querySelector(":scope > .xai-feature-top");
    const heading = top?.querySelector(":scope > div");
    const title = heading?.querySelector(":scope > strong");
    const category = heading?.querySelector(":scope > span");
    const score = top?.querySelector(":scope > b");
    const bar = item.querySelector(":scope > i");
    const description = item.querySelector(":scope > p");
    const meta = item.querySelector(":scope > small");
    if (!title || !score || !bar) return;

    const copy = document.createElement("div");
    copy.className = "xai-feature-copy";
    const featureHeading = document.createElement("div");
    featureHeading.className = "xai-feature-heading";
    featureHeading.appendChild(title);
    if (category) {
      category.className = "xai-category";
      featureHeading.appendChild(category);
    }
    copy.appendChild(featureHeading);
    if (description) copy.appendChild(description);
    if (meta) {
      meta.className = "xai-feature-meta";
      copy.appendChild(meta);
    }

    bar.className = "xai-bar";
    bar.setAttribute("aria-hidden", "true");
    const fill = document.createElement("i");
    fill.style.width = "var(--bar, 0%)";
    bar.replaceChildren(fill);

    score.className = "xai-score";
    item.dataset.laminateXaiLayout = "true";
    item.replaceChildren(copy, bar, score);
  }

  function normalizeInjectionXaiFeatures() {
    injectionXaiList?.querySelectorAll(".xai-feature").forEach(normalizeInjectionXaiFeature);
  }

  if (injectionXaiList) {
    normalizeInjectionXaiFeatures();
    new MutationObserver(normalizeInjectionXaiFeatures).observe(injectionXaiList, { childList: true, subtree: true });
  }

  const xaiSectionHead = panelNodes.xai?.querySelector(".section-head");
  const xaiMethod = panelNodes.xai?.querySelector("#xai-method");
  const xaiSummary = panelNodes.xai?.querySelector("#xai-summary");
  if (xaiSectionHead && xaiMethod && xaiSummary) {
    const summaryCard = document.createElement("div");
    summaryCard.className = "injection-xai-summary-card";
    const methodGroup = document.createElement("div");
    const methodLabel = document.createElement("span");
    methodLabel.textContent = locale === "ko" ? "설명 방식" : "Method";
    methodGroup.append(methodLabel, xaiMethod);
    summaryCard.append(methodGroup, xaiSummary);
    xaiSectionHead.after(summaryCard);
  }

  const curveTitle = panelNodes.curve?.querySelector(".section-head h3");
  const fillingTitle = panelNodes.filling?.querySelector(".section-head h3");
  if (curveTitle) curveTitle.textContent = t("pressureCurve");
  if (fillingTitle) fillingTitle.textContent = t("pressureDistribution");

  const compareGrid = panelNodes.validation?.querySelector(".compare-grid");
  if (compareGrid) {
    replaceLabelText(compareGrid.querySelector("#comparison-sample-id"), t("sampleId"));
    replaceLabelText(compareGrid.querySelector("#comparison-sprue-file"), t("sprueCsv"));
    replaceLabelText(compareGrid.querySelector("#comparison-filling-file"), t("fillingCsv"));
    const guide = document.createElement("details");
    guide.className = "validation-guide";
    guide.innerHTML = `
      <summary>${t("csvGuide")}</summary>
      <div>
        <p>${t("csvGuideCopy")}</p>
        <ul>
          <li><strong>Sprue:</strong> <code>Time (sec)</code> ${t("sprueCsvRule")}</li>
          <li><strong>Filling:</strong> <code>[Distribution]</code> ${t("fillingCsvRule")}</li>
        </ul>
        <nav aria-label="${t("sampleNav")}">
          <a href="/samples/G01_P01_Sprue_Pressure.csv" download>${t("sprueSample")}</a>
          <a href="/samples/G01_P01_Filling_Pressure.csv" download>${t("fillingSample")}</a>
        </nav>
      </div>
    `;
    compareGrid.before(guide);
  }

  panelNodes.summary.className = "summary-panel";
  const resultHero = result.querySelector(".result-hero");
  const stats = result.querySelector(".stats");
  const notes = result.querySelector("#notes");
  [resultHero, stats, notes].forEach((node) => node && panelNodes.summary.appendChild(node));

  Object.entries(panelNodes).forEach(([key, panel]) => {
    if (!panel) return;
    panel.id = `injection-panel-${key}`;
    panel.dataset.resultPanel = key;
    panel.setAttribute("role", "tabpanel");
    panel.setAttribute("aria-labelledby", `injection-tab-${key}`);
    if (key !== "summary") panel.hidden = true;
    result.appendChild(panel);
  });

  if (history) {
    const comparison = document.createElement("section");
    comparison.className = "run-comparison";
    comparison.setAttribute("aria-labelledby", "run-comparison-title");
    comparison.innerHTML = `
      <div class="comparison-heading">
        <div>
          <span>Run comparison</span>
          <h2 id="run-comparison-title">${t("runComparison")}</h2>
        </div>
        <p>${t("runComparisonCopy")}</p>
      </div>
    `;
    comparison.appendChild(history);
    grid.insertAdjacentElement("afterend", comparison);

    const localizeHistoryLabels = () => {
      if (locale !== "ko") return;
      history.querySelectorAll(".history-run em").forEach((label) => {
        const localized = label.textContent
          .replaceAll("Operator Learning", "오퍼레이터 러닝")
          .replaceAll("Machine Learning", "머신러닝")
          .replaceAll("Deep Learning", "딥러닝");
        if (localized !== label.textContent) label.textContent = localized;
      });
    };
    localizeHistoryLabels();
    new MutationObserver(localizeHistoryLabels).observe(history, { childList: true, subtree: true });
  }

  let activeTab = "summary";
  const tabButtons = [...tabList.querySelectorAll("[data-result-tab]")];
  const showExampleButton = emptyState?.querySelector("#show-injection-example");
  const exampleCurvePoints = [
    [0, 0], [2.4, 16.8], [4.8, 31.4], [7.2, 44.1], [9.6, 54.3],
    [12, 61.8], [14.4, 66.2], [16.8, 68.3], [19.2, 69], [22.05, 68.7],
  ];

  function drawExamplePressureCurve() {
    const canvas = result.querySelector("#pressure-canvas");
    if (!canvas || result.dataset.resultSource !== "example") return;
    const rect = canvas.getBoundingClientRect();
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    const width = Math.max(360, Math.round(rect.width || 760));
    const height = Math.max(300, Math.round(width * 0.474));
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    canvas.style.height = `${height}px`;
    const ctx = canvas.getContext("2d");
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    const pad = { left: 58, right: 24, top: 24, bottom: 44 };
    const plotWidth = width - pad.left - pad.right;
    const plotHeight = height - pad.top - pad.bottom;
    const x = (value) => pad.left + (value / 22.05) * plotWidth;
    const y = (value) => pad.top + plotHeight - (value / 75) * plotHeight;
    ctx.fillStyle = "#fbfcfe";
    ctx.fillRect(0, 0, width, height);
    ctx.strokeStyle = "#e2e7ef";
    ctx.lineWidth = 1;
    ctx.font = '400 11px -apple-system, "Segoe UI", Inter, sans-serif';
    ctx.fillStyle = "#667085";
    for (let index = 0; index <= 4; index += 1) {
      const pressure = (75 * index) / 4;
      const chartY = y(pressure);
      ctx.beginPath();
      ctx.moveTo(pad.left, chartY);
      ctx.lineTo(width - pad.right, chartY);
      ctx.stroke();
      ctx.textAlign = "right";
      ctx.fillText(pressure.toFixed(0), pad.left - 9, chartY + 4);
      const time = (22.05 * index) / 4;
      const chartX = x(time);
      ctx.beginPath();
      ctx.moveTo(chartX, pad.top);
      ctx.lineTo(chartX, pad.top + plotHeight);
      ctx.stroke();
      ctx.textAlign = "center";
      ctx.fillText(time.toFixed(1), chartX, height - 20);
    }
    const gradient = ctx.createLinearGradient(pad.left, 0, width - pad.right, 0);
    gradient.addColorStop(0, "#0076bd");
    gradient.addColorStop(0.58, "#16aad8");
    gradient.addColorStop(1, "#00ad5a");
    ctx.strokeStyle = gradient;
    ctx.lineWidth = 3;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.beginPath();
    exampleCurvePoints.forEach(([time, pressure], index) => {
      if (index === 0) ctx.moveTo(x(time), y(pressure));
      else ctx.lineTo(x(time), y(pressure));
    });
    ctx.stroke();
  }

  function renderExampleFilling() {
    const histogram = result.querySelector("#filling-histogram");
    if (!histogram) return;
    histogram.innerHTML = "";
    [["G1", 100, "18.2%"], ["G2", 82, "15.0%"], ["G3", 64, "11.7%"], ["G4", 47, "8.6%"], ["G5", 31, "5.7%"]]
      .forEach(([label, bar, value]) => {
        const row = document.createElement("div");
        row.className = "filling-row";
        row.innerHTML = `<span>${label}</span><i style="--bar:${bar}%"></i><strong>${value}</strong>`;
        histogram.appendChild(row);
      });
  }

  function renderExampleXai() {
    const card = result.querySelector('[data-result-panel="xai"]');
    const method = result.querySelector("#xai-method");
    const summary = result.querySelector("#xai-summary");
    const list = result.querySelector("#xai-feature-list");
    const noteList = result.querySelector("#xai-notes");
    if (!card || !list) return;
    card.classList.remove("hidden");
    if (method) method.textContent = locale === "ko" ? "예시 local sensitivity" : "Example local sensitivity";
    if (summary) summary.textContent = t("exampleXaiSummary");
    list.innerHTML = "";
    const features = locale === "ko"
      ? [
        ["보압", "공정", 31, "충전 후반부의 압력 수준과 peak pressure에 영향을 줄 수 있습니다.", "현재값 69 · 국부 민감도 0.31 · 5% 증가"],
        ["수지 온도", "공정", 24, "온도가 높아지면 점도가 낮아져 필요한 압력이 줄어들 수 있습니다.", "현재값 226.1 · 국부 민감도 0.24 · 5% 증가"],
        ["제품 두께", "형상", 19, "두께는 캐비티의 유동 저항과 압력 민감도에 영향을 줍니다.", "현재값 2.207 · 국부 민감도 0.19 · 5% 증가"],
        ["유동 길이/두께 비율", "파생", 15, "유동 경로가 두께에 비해 얼마나 긴지 나타내는 지표입니다.", "현재값 69.783 · 국부 민감도 0.15 · 5% 증가"],
        ["게이트 면적", "게이트", 11, "게이트 단면적은 입구 부근의 국부 압력 손실에 영향을 줍니다.", "현재값 15 · 국부 민감도 0.11 · 5% 증가"],
      ]
      : [
        ["Packing pressure", "Process", 31, "Influences the late-fill pressure level and peak pressure.", "Current value 69 · Local sensitivity 0.31 · Increased by 5%"],
        ["Melt temperature", "Process", 24, "Higher temperature can lower viscosity and reduce the required pressure.", "Current value 226.1 · Local sensitivity 0.24 · Increased by 5%"],
        ["Part thickness", "Geometry", 19, "Controls cavity flow resistance and pressure sensitivity.", "Current value 2.207 · Local sensitivity 0.19 · Increased by 5%"],
        ["Flow length/thickness", "Derived", 15, "Describes how long the flow path is relative to part thickness.", "Current value 69.783 · Local sensitivity 0.15 · Increased by 5%"],
        ["Gate area", "Gate", 11, "Affects the local pressure loss near the cavity entrance.", "Current value 15 · Local sensitivity 0.11 · Increased by 5%"],
      ];
    features.forEach(([label, category, score, description, meta]) => {
      const item = document.createElement("article");
      item.className = "xai-feature";
      item.innerHTML = `<div class="xai-feature-top"><div><strong>${label}</strong><span>${category}</span></div><b>${score}%</b></div><i style="--bar:${score}%"></i><p>${description}</p><small>${meta}</small>`;
      list.appendChild(item);
    });
    normalizeInjectionXaiFeatures();
    if (noteList) noteList.innerHTML = `<li>${t("exampleNote")}</li>`;
  }

  function selectResultTab(nextTab, focus = false) {
    const targetButton = tabButtons.find((button) => button.dataset.resultTab === nextTab);
    if (!targetButton || targetButton.getAttribute("aria-disabled") === "true") return;
    activeTab = nextTab;
    tabButtons.forEach((button) => {
      const selected = button === targetButton;
      button.setAttribute("aria-selected", String(selected));
      button.tabIndex = selected ? 0 : -1;
    });
    Object.entries(panelNodes).forEach(([key, panel]) => {
      if (panel) panel.hidden = key !== nextTab;
    });
    if (focus) targetButton.focus();
    if (nextTab === "curve" && panelNodes.curve) {
      panelNodes.curve.classList.add("is-rendering");
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          window.dispatchEvent(new Event("injection:curve-tab-activated"));
          drawExamplePressureCurve();
          panelNodes.curve.classList.remove("is-rendering");
        });
      });
    }
  }

  tabButtons.forEach((button, index) => {
    button.addEventListener("click", () => selectResultTab(button.dataset.resultTab));
    button.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      const enabledButtons = tabButtons.filter((item) => item.getAttribute("aria-disabled") !== "true");
      const currentIndex = enabledButtons.indexOf(button);
      let nextIndex = currentIndex;
      if (event.key === "ArrowRight") nextIndex = (currentIndex + 1) % enabledButtons.length;
      if (event.key === "ArrowLeft") nextIndex = (currentIndex - 1 + enabledButtons.length) % enabledButtons.length;
      if (event.key === "Home") nextIndex = 0;
      if (event.key === "End") nextIndex = enabledButtons.length - 1;
      selectResultTab(enabledButtons[nextIndex].dataset.resultTab, true);
    });
  });

  function setResultReady() {
    if (result.classList.contains("hidden")) return;
    const isExample = result.dataset.resultSource === "example";
    tabList.hidden = false;
    deepDiveHint.hidden = false;
    tabButtons.forEach((button) => {
      const disabled = isExample && button.dataset.resultTab === "validation";
      button.setAttribute("aria-disabled", String(disabled));
    });
    const statusCopy = document.querySelector("#result-status-copy");
    if (statusCopy) statusCopy.textContent = isExample ? t("exampleResult") : t("resultNow");
    selectResultTab("summary");
  }

  function showExampleResult() {
    result.dataset.resultSource = "example";
    emptyState?.classList.add("hidden");
    result.classList.remove("hidden");
    result.querySelector("#max-pressure").textContent = "69.00 MPa";
    result.querySelector("#max-time").textContent = "22.053 s";
    result.querySelector("#curve-points").textContent = String(exampleCurvePoints.length);
    result.querySelector("#filling-max").textContent = "35.98 MPa";
    result.querySelector("#sprue-model-label").textContent = locale === "ko" ? "머신러닝 · 예시" : "Machine Learning · example";
    result.querySelector("#filling-model-label").textContent = locale === "ko" ? "머신러닝 · 예시" : "Machine Learning · example";
    const notes = result.querySelector("#notes");
    if (notes) notes.innerHTML = `<li>${t("exampleNote")}</li>`;
    renderExampleFilling();
    renderExampleXai();
    setResultReady();
  }

  new MutationObserver(setResultReady).observe(result, { attributes: true, attributeFilter: ["class"] });
  window.addEventListener("injection:result-rendered", () => {
    delete result.dataset.resultSource;
    setResultReady();
  });
  showExampleButton?.addEventListener("click", showExampleResult);
  setResultReady();

  const modeButtons = [...commandBar.querySelectorAll("[data-analysis-mode]")];
  function setAnalysisMode(mode, focus = false) {
    document.body.dataset.analysisMode = mode;
    modeButtons.forEach((button) => {
      const selected = button.dataset.analysisMode === mode;
      button.setAttribute("aria-checked", String(selected));
      button.tabIndex = selected ? 0 : -1;
      if (selected && focus) button.focus();
    });
    if (mode === "quick" && ["xai", "validation"].includes(activeTab)) {
      selectResultTab("summary");
    }
  }

  deepDiveHint.querySelector("button")?.addEventListener("click", () => setAnalysisMode("deep", true));

  modeButtons.forEach((button) => {
    button.addEventListener("click", () => setAnalysisMode(button.dataset.analysisMode));
    button.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      const currentIndex = modeButtons.indexOf(button);
      let nextIndex = currentIndex;
      if (event.key === "ArrowRight") nextIndex = (currentIndex + 1) % modeButtons.length;
      if (event.key === "ArrowLeft") nextIndex = (currentIndex - 1 + modeButtons.length) % modeButtons.length;
      if (event.key === "Home") nextIndex = 0;
      if (event.key === "End") nextIndex = modeButtons.length - 1;
      setAnalysisMode(modeButtons[nextIndex].dataset.analysisMode, true);
    });
  });

  function updateCurrentInput() {
    const geometry = document.querySelector("#geometry-select")?.value || "-";
    const process = document.querySelector("#process-select")?.value || "-";
    const melt = form.elements.melt_temp_C?.value || "-";
    const packing = form.elements.packing_pressure_MPa?.value || "-";
    const target = document.querySelector("#current-input-summary");
    if (target) target.textContent = t("inputSummary", { geometry, process, melt, packing });
  }

  function restoreLocaleState(attempt = 0) {
    let saved = null;
    try {
      saved = JSON.parse(sessionStorage.getItem(localeStateStorageKey) || "null");
    } catch {
      return;
    }
    if (!saved || saved.targetLocale !== locale) return;
    const selectsReady = [form.elements.model, form.elements.filling_model, form.elements.geometry_id, form.elements.process_id]
      .every((select) => select && select.options.length > 0);
    if (!selectsReady && attempt < 30) {
      window.setTimeout(() => restoreLocaleState(attempt + 1), 100);
      return;
    }
    Object.entries(saved.controls || {}).forEach(([name, value]) => {
      const control = form.elements[name];
      if (!control) return;
      if (control.tagName === "SELECT" && ![...control.options].some((option) => option.value === value)) return;
      control.value = value;
      control.dispatchEvent(new Event("change", { bubbles: true }));
    });
    setAnalysisMode(saved.mode || "quick");
    updateCurrentInput();
    try {
      sessionStorage.removeItem(localeStateStorageKey);
    } catch {
      // Ignore optional persistence cleanup failures.
    }
    if (saved.rerun) window.setTimeout(() => form.requestSubmit(), 150);
  }

  form.querySelectorAll("input, select").forEach((control) => {
    control.addEventListener("input", updateCurrentInput);
    control.addEventListener("change", updateCurrentInput);
  });
  [document.querySelector("#geometry-select"), document.querySelector("#process-select")]
    .filter(Boolean)
    .forEach((select) => new MutationObserver(updateCurrentInput).observe(select, { childList: true }));

  form.addEventListener("submit", () => {
    delete result.dataset.resultSource;
  });

  setAnalysisMode("quick");
  updateCurrentInput();
  restoreLocaleState();
  requestAnimationFrame(() => window.dispatchEvent(new Event("resize")));
})();
