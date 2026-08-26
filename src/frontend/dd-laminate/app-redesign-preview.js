(() => {
  const isKo = document.documentElement.lang.toLowerCase().startsWith("ko");
  const result = document.querySelector("#result");
  const resultHead = result?.querySelector(".result-head");
  const accordionStorageKey = "imperialax.forecast.redesign.accordions.v1";

  if (!result || !resultHead) {
    return;
  }

  function readAccordionState() {
    try {
      return JSON.parse(sessionStorage.getItem(accordionStorageKey) || "{}");
    } catch {
      return {};
    }
  }

  function writeAccordionState(state) {
    try {
      sessionStorage.setItem(accordionStorageKey, JSON.stringify(state));
    } catch {
      // Accordion state is optional; the forecast must remain usable without storage.
    }
  }

  function createMetricCard(label, valueId, className = "") {
    const card = document.createElement("article");
    card.className = `forecast-summary-card ${className}`.trim();

    const name = document.createElement("span");
    name.textContent = label;

    const value = document.createElement("strong");
    value.dataset.summarySource = valueId;
    value.textContent = "-";

    card.append(name, value);
    return card;
  }

  const forecastSummary = document.createElement("section");
  forecastSummary.className = "forecast-summary";
  forecastSummary.id = "forecast-summary";
  forecastSummary.setAttribute("aria-label", isKo ? "핵심 예측 요약" : "Forecast summary");
  forecastSummary.append(
    createMetricCard(isKo ? "예측 Type" : "Predicted Type", "predicted-type", "primary-metric"),
    createMetricCard(isKo ? "예측 확률" : "Probability", "confidence"),
    createMetricCard(isKo ? "예측 Pt" : "Predicted Pt", "predicted-pt"),
    createMetricCard(isKo ? "최대 변위" : "Max. Displacement", "predicted-max-displacement"),
    createMetricCard(isKo ? "신뢰도" : "Reliability", "uncertainty-label")
  );
  result.insertBefore(forecastSummary, resultHead);

  function syncSummary() {
    forecastSummary.querySelectorAll("[data-summary-source]").forEach((target) => {
      const source = document.querySelector(`#${target.dataset.summarySource}`);
      target.textContent = source?.textContent?.trim() || "-";
    });

    const uncertainty = document.querySelector("#uncertainty-panel");
    const reliabilityCard = forecastSummary.querySelector('[data-summary-source="uncertainty-label"]')?.closest("article");
    if (reliabilityCard) {
      reliabilityCard.dataset.level = uncertainty?.classList.contains("high")
        ? "high"
        : uncertainty?.classList.contains("medium")
          ? "medium"
          : uncertainty?.classList.contains("low")
            ? "low"
            : "unknown";
    }
  }

  const summarySources = [
    "predicted-type",
    "confidence",
    "predicted-pt",
    "predicted-max-displacement",
    "uncertainty-label",
  ];
  summarySources.forEach((id) => {
    const source = document.querySelector(`#${id}`);
    if (!source) return;
    new MutationObserver(syncSummary).observe(source, {
      childList: true,
      characterData: true,
      subtree: true,
    });
  });
  const uncertaintyPanel = document.querySelector("#uncertainty-panel");
  if (uncertaintyPanel) {
    new MutationObserver(syncSummary).observe(uncertaintyPanel, {
      attributes: true,
      attributeFilter: ["class"],
    });
  }
  syncSummary();

  function wrapAccordion(panelId, label, defaultOpen) {
    const panel = document.querySelector(`#${panelId}`);
    if (!panel || panel.closest("details.result-accordion")) {
      return;
    }

    const state = readAccordionState();
    const details = document.createElement("details");
    details.className = `result-accordion result-accordion-${panelId}`;
    details.dataset.accordionId = panelId;
    details.open = typeof state[panelId] === "boolean" ? state[panelId] : defaultOpen;

    const summary = document.createElement("summary");
    const summaryText = document.createElement("span");
    summaryText.textContent = label;
    const status = document.createElement("span");
    status.className = "accordion-status";
    status.setAttribute("aria-hidden", "true");
    summary.append(summaryText, status);

    panel.parentNode.insertBefore(details, panel);
    details.append(summary, panel);
    panel.classList.add("result-accordion-body");

    const syncVisibility = () => {
      details.classList.toggle("hidden", panel.classList.contains("hidden"));
    };
    syncVisibility();
    new MutationObserver(syncVisibility).observe(panel, {
      attributes: true,
      attributeFilter: ["class"],
    });

    details.addEventListener("toggle", () => {
      const nextState = readAccordionState();
      nextState[panelId] = details.open;
      writeAccordionState(nextState);
    });
  }

  wrapAccordion("response-estimate", isKo ? "응답 곡선" : "Response curve", true);
  wrapAccordion("xai-panel", isKo ? "왜 이런 예측인가요? (XAI)" : "Why this prediction? (XAI)", false);
  wrapAccordion("research-panel", isKo ? "설계 공간과 심화 분석" : "Design space and deeper analysis", false);

  let hadResult = document.body.classList.contains("has-result");
  new MutationObserver(() => {
    const hasResult = document.body.classList.contains("has-result");
    syncSummary();
    if (hasResult && !hadResult) {
      forecastSummary.classList.remove("result-updated");
      requestAnimationFrame(() => {
        forecastSummary.classList.add("result-updated");
        if (window.matchMedia("(max-width: 1024px)").matches) {
          forecastSummary.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      });
    }
    hadResult = hasResult;
  }).observe(document.body, { attributes: true, attributeFilter: ["class"] });

  function showSampleResult() {
    if (new URLSearchParams(window.location.search).get("sample") !== "1") {
      return;
    }

    document.body.classList.add("sample-preview");

    const sampleCurve = Array.from({ length: 45 }, (_, index) => {
      const displacement = (0.08317 / 44) * index;
      const force = displacement <= 0.05
        ? 343800 * displacement
        : 17190 + (displacement - 0.05) * 125100;
      return { displacement, force };
    });
    const sampleXai = {
      title: isKo ? "왜 이런 예측인가요?" : "Why this prediction?",
      summary: isKo
        ? "A12 막 커플링과 굽힘 이방성이 Type 2 예측에 가장 큰 영향을 주었습니다."
        : "A12 membrane coupling and bending anisotropy contributed most to the Type 2 prediction.",
      method: isKo ? "로컬 feature masking" : "Local feature masking",
      feature_set: "theta + canonical CLT physics + panel geometry",
      top_features: [
        {
          name: "A12",
          label: "A12 membrane coupling",
          category: "physics",
          importance: 0.31,
          local_value: 184200,
          local_sensitivity: 0.128,
          explanation: "In-plane membrane coupling term from the laminate A matrix.",
        },
        {
          name: "bending_anisotropy",
          label: "Bending anisotropy",
          category: "physics",
          importance: 0.24,
          local_value: 0.418,
          local_sensitivity: 0.094,
          explanation: "Bending anisotropy ratio. It helps explain case/type differences driven by flexural stiffness balance.",
        },
        {
          name: "theta2",
          label: "θ₂",
          category: "angle",
          importance: 0.18,
          local_value: -30,
          local_sensitivity: 0.071,
          explanation: isKo ? "두 번째 Double-Double 각도군입니다." : "Second Double-Double angle family.",
        },
        {
          name: "D16",
          label: "D16 bend-twist coupling",
          category: "physics",
          importance: 0.15,
          local_value: 7350,
          local_sensitivity: 0.052,
          explanation: "D-matrix coupling between load-direction bending and twisting response.",
        },
        {
          name: "panel_aspect_ratio",
          label: isKo ? "패널 종횡비" : "Panel aspect ratio",
          category: "geometry",
          importance: 0.12,
          local_value: 1,
          local_sensitivity: 0.038,
          explanation: "Panel length-to-width ratio from the PPT mechanics setup.",
        },
      ],
      notes: [
        isKo
          ? "중요도는 현재 θ, Case 및 패널 크기 입력에 대한 로컬 설명입니다."
          : "Importance is local to the current theta, Case, and panel-size input.",
      ],
    };
    const mapPoints = ["Case2", "Case3", "Case4"].flatMap((caseName, caseIndex) => (
      [-75, -45, -15, 15, 45, 75].map((theta1, pointIndex) => ({
        case: caseName,
        theta1,
        theta2: -75 + ((pointIndex * 30 + caseIndex * 15) % 150),
        type: ((pointIndex + caseIndex) % 3) + 1,
        pt: 12800 + pointIndex * 1150 + caseIndex * 620,
        test_id: `${caseName}-S${pointIndex + 1}`,
      }))
    ));
    const sampleDesignSpace = {
      scope: "response",
      inputs: { theta1: 45, theta2: -30, case: "Case2" },
      map_points: mapPoints,
      case_summaries: [
        { case: "Case2", risk_label: "low", risk_score: 0.24, median_pt: 16840, max_pt: 22410, type_rates: { type1: 0.58, type2: 0.31, type3: 0.11 } },
        { case: "Case3", risk_label: "medium", risk_score: 0.46, median_pt: 15720, max_pt: 21180, type_rates: { type1: 0.39, type2: 0.44, type3: 0.17 } },
        { case: "Case4", risk_label: "high", risk_score: 0.67, median_pt: 14510, max_pt: 19860, type_rates: { type1: 0.25, type2: 0.47, type3: 0.28 } },
      ],
      nearest_points: [
        { case: "Case2", theta1: 45, theta2: -25, type: 2, pt: 17460, distance: 5.0 },
        { case: "Case2", theta1: 40, theta2: -35, type: 2, pt: 16980, distance: 7.1 },
        { case: "Case3", theta1: 50, theta2: -30, type: 1, pt: 18120, distance: 8.4 },
      ],
      recommendations: [
        {
          case: "Case2", theta1: 55, theta2: -20, expected_pt: 22410, observed_type: 1, score: 0.92,
          rationale: "High observed Pt with Type 1 preference in the curated Case2/3/4 simulations.",
          score_components: { pt: 0.96, type: 1, proximity: 0.74 },
        },
        {
          case: "Case3", theta1: 60, theta2: -15, expected_pt: 21180, observed_type: 1, score: 0.84,
          rationale: "Recommendations are simulation-backed observed candidates, not new finite-element simulations.",
          score_components: { pt: 0.88, type: 1, proximity: 0.61 },
        },
      ],
      notes: [
        "Laminate Forecast design-space context is based on the curated Case2/3/4 response dataset.",
        "Use high-Pt candidates as screening leads and validate final choices with simulation.",
      ],
    };
    const sampleData = {
      predicted_type: 2,
      confidence: 0.874,
      predicted_pt: 17190.1,
      predicted_max_displacement: 0.08317,
      predicted_max_force: 21340.22,
      model_key: "response_geometry_tree_3size_grouped_v1",
      model_label: "3-Size Pt-Consistent Machine Learning (Tree)",
      probabilities: { type1: 0.068, type2: 0.874, type3: 0.058 },
      inputs: { theta1: 45, theta2: -30, case: "Case2", panel_a_in: 8, panel_b_in: 8 },
      uncertainty: {
        confidence_label: "high",
        reliability_score: 0.912,
        pt_interval_low: 16820,
        pt_interval_high: 17560,
        interpolation_label: "interpolation",
        type_consistency: 0.9,
        notes: [],
      },
      teacher_student: null,
      notes: [],
      curve: sampleCurve,
      xai: sampleXai,
      design_space: sampleDesignSpace,
    };

    const responseModelSelect = document.querySelector("#response-model");
    if (responseModelSelect && responseModelSelect.options.length === 0) {
      const option = document.createElement("option");
      option.value = sampleData.model_key;
      option.textContent = sampleData.model_label;
      option.selected = true;
      responseModelSelect.appendChild(option);
    }

    renderResult(sampleData);
    responseEstimate.classList.remove("hidden");
    responseCurveTitle.textContent = isKo ? "예측 곡선" : "Predicted curve";
    predictedPt.textContent = formatMetric(sampleData.predicted_pt, 2);
    predictedMaxDisplacement.textContent = formatMetric(sampleData.predicted_max_displacement, 5);
    predictedMaxForce.textContent = formatMetric(sampleData.predicted_max_force, 2);
    updateResponseCurveLegend("standard");
    setResponseCurveSource(sampleCurve, sampleData.predicted_pt, "standard");
    renderXai(sampleXai);
    renderDesignSpace(sampleDesignSpace);

    const apiStatusElement = document.querySelector("#api-status");
    const errorElement = document.querySelector("#error");
    const sampleStatusText = isKo ? "샘플 데이터" : "Sample data";
    const apiErrorPattern = isKo ? "DD API" : "Start the DD API";

    function keepSampleStatusConsistent() {
      if (apiStatusElement && apiStatusElement.textContent !== sampleStatusText) {
        apiStatusElement.textContent = sampleStatusText;
        apiStatusElement.classList.remove("bad");
        apiStatusElement.classList.add("ok");
      }
      if (errorElement?.textContent.includes(apiErrorPattern)) {
        errorElement.textContent = "";
        errorElement.classList.add("hidden");
      }
    }

    keepSampleStatusConsistent();
    if (apiStatusElement) {
      new MutationObserver(keepSampleStatusConsistent).observe(apiStatusElement, {
        childList: true,
        characterData: true,
        subtree: true,
        attributes: true,
        attributeFilter: ["class"],
      });
    }
    if (errorElement) {
      new MutationObserver(keepSampleStatusConsistent).observe(errorElement, {
        childList: true,
        characterData: true,
        subtree: true,
        attributes: true,
        attributeFilter: ["class"],
      });
    }

    document.addEventListener("click", (event) => {
      const recommendation = event.target.closest(".recommendation-action");
      if (!recommendation) {
        return;
      }
      event.preventDefault();
      event.stopImmediatePropagation();
      forecastSummary.classList.remove("result-updated");
      requestAnimationFrame(() => forecastSummary.classList.add("result-updated"));
    }, true);

    syncSummary();
  }

  showSampleResult();
})();
