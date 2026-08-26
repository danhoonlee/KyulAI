(() => {
  const routePath = window.location.pathname.replace(/\/+$/, "") || "/";
  const locale = routePath === "/v2/en" ? "en" : "ko";
  const numberLocale = locale === "ko" ? "ko-KR" : "en-US";

  const staticEnglish = {
    "ImperialAX 적층 예측 — 구조 재설계": "ImperialAX Laminate Forecast — Rebuild",
    "적층 후보 스크리닝": "Laminate candidate screening",
    "현재 운영 화면": "Current production UI",
    "분석 모드": "Analysis mode",
    "빠른 스크리닝": "Quick screening",
    "딥 다이브": "Deep dive",
    "현재 입력": "Current input",
    "후보 조건 설정": "Candidate setup",
    "핵심 변수만 조정해 빠르게 후보를 선별합니다.": "Adjust the key variables to screen candidates quickly.",
    "모델": "Model",
    "빠르고 안정적인 Tree 기반 3-Size Pt 일관성 모델입니다.": "A fast, stable Tree-based 3-Size Pt-consistent model.",
    "패널 길이 a (in)": "Panel length a (in)",
    "패널 폭 b (in)": "Panel width b (in)",
    "적층 미리보기": "Laminate preview",
    "θ₁ 계열": "θ₁ family",
    "θ₂ 계열": "θ₂ family",
    "예측 실행": "Run forecast",
    "새 결과를 비교 목록에 추가": "Add the new result to comparison",
    "예측 결과": "Forecast results",
    "아직 실행된 결과 없음": "No result yet",
    "아직 실행된 예측이 없습니다": "No forecast has been run yet",
    "왼쪽에서 조건을 설정한 후 예측을 실행하세요.": "Set the conditions on the left, then run the forecast.",
    "예시 결과 보기": "View example result",
    "예시 데이터는 모델을 실행한 결과가 아닙니다.": "Example data is not a model-run result.",
    "요약": "Summary",
    "곡선": "Curve",
    "디자인 스페이스": "Design space",
    "예측 거동": "Predicted behavior",
    "Type 확률": "Type probability",
    "3D에서 보기": "View in 3D",
    "전체 Ply Sequence": "Full ply sequence",
    "16개 ply의 3D 적층 방향을 확인합니다.": "Inspect the 3D orientation of all 16 plies.",
    "색은 θ 계열을, 사선 방향은 각 ply의 양·음 방향을 나타냅니다.": "Color identifies the θ family; the diagonal indicates each ply's positive or negative direction.",
    "표면에서 바닥 방향 · P1 → P16": "Surface to bottom · P1 → P16",
    "학습 범위": "Training domain",
    "현재 위치": "Current position",
    "XAI 보기": "View XAI",
    "최대 변위": "Maximum displacement",
    "신뢰도": "Reliability",
    "높음": "High",
    "딥 다이브 검토 권장": "Deep-dive review recommended",
    "Pt는 상위권이지만 Type 2 전환 거동이 보여 곡선과 XAI 확인이 유용합니다.": "Pt is competitive, but the Type 2 transition makes the curve and XAI worth reviewing.",
    "예측 하중–변위 곡선": "Predicted load–displacement curve",
    "곡선 상세 보기": "Curve detail",
    "곡선 상세 보기 · 드래그 이동 · 두 손가락 확대": "Curve detail · Drag to pan · Pinch to zoom",
    "예측 곡선": "Predicted curve",
    "P1 선형 피팅": "P1 linear fits",
    "예측 Pt": "Predicted Pt",
    "최대 하중": "Maximum force",
    "전이점 Pt": "Transition Pt",
    "모델이 예측한 원시 곡선과 전이점 Pt를 함께 표시합니다.": "Displays the model's raw predicted curve and transition Pt together.",
    "왜 이런 예측인가요?": "Why this prediction?",
    "현재 입력이 예측에 미치는 영향을 비교합니다.": "Compare how the current inputs influence the prediction.",
    "설명 방식": "Explanation method",
    "현재 입력에서 예측 변화가 큰 물리 feature 순서입니다.": "Physics features ranked by their effect on the current prediction.",
    "추가 Feature": "Additional features",
    "현재 후보의 설계 공간 위치": "Current candidate in the design space",
    "기존 해석 데이터와 현재 위치를 비교합니다.": "Compare the current position with existing analysis data.",
    "현재 Case": "Current case",
    "전체": "All",
    "데이터 불러오는 중": "Loading data",
    "Case 위험도": "Case risk",
    "낮음 · 24%": "Low · 24%",
    "가까운 해석": "Nearest analysis",
    "추천 후보": "Recommended candidate",
    "현재 Case는 진하게 표시": "Current case is emphasized",
    "현재 패널 크기와 가장 가까운 기존 해석 데이터를 기준으로 비교합니다.": "Compares against existing analyses nearest to the current panel size.",
    "실행 이력 비교": "Run comparison",
    "행을 선택하면 입력값을 다시 불러옵니다.": "Select a row to restore its inputs.",
    "아직 실행 이력이 없습니다. 예측을 실행하면 결과가 여기에 추가됩니다.": "No run history yet. Forecast results will appear here after execution.",
  };

  const messages = {
    modelTreeDescription: ["빠르고 안정적인 Tree 기반 3-Size Pt 일관성 모델입니다.", "A fast, stable Tree-based 3-Size Pt-consistent model."],
    modelGointDescription: ["물리 feature와 각도·패널 형상을 함께 학습한 심층 모델입니다.", "A deep model trained jointly on physics features, angles, and panel geometry."],
    modelHybridDescription: ["Tree teacher와 경량 student를 결합한 Pt 일관성 Hybrid 모델입니다.", "A Pt-consistent hybrid combining a Tree teacher with a lightweight student."],
    modelGenericDescription: ["Type, Pt와 응답 곡선을 함께 예측하는 Laminate Forecast 모델입니다.", "A Laminate Forecast model that predicts Type, Pt, and the response curve together."],
    unavailable: ["사용 불가", "Unavailable"],
    apiReady: ["모델 API 연결됨", "Model API connected"],
    apiOffline: ["시안 데이터 모드", "Preview data mode"],
    apiChecking: ["모델 확인 중", "Checking model"],
    reliabilityHigh: ["높음", "High"],
    reliabilityMedium: ["보통", "Medium"],
    reliabilityLow: ["낮음", "Low"],
    interpolation: ["보간 영역", "Interpolation region"],
    nearEdge: ["경계 영역", "Near-edge region"],
    extrapolation: ["외삽 영역", "Extrapolation region"],
    actualCurve: ["{model}의 실제 예측 곡선과 전이점 Pt입니다.", "Actual predicted curve and transition Pt from {model}."],
    previewCurve: ["모델 API가 연결되면 실제 원시 곡선과 전이점 Pt로 교체됩니다.", "The actual raw curve and transition Pt will replace this preview when the model API connects."],
    exampleCurve: ["화면 구성을 확인하기 위한 예시 곡선이며 모델 실행 결과가 아닙니다.", "This example curve demonstrates the interface and is not a model-run result."],
    keepCandidate: ["빠른 후보군에 유지", "Keep in quick-screen candidates"],
    reviewDeep: ["딥 다이브 검토 권장", "Deep-dive review recommended"],
    typeOneCopy: ["Type 1과 높은 신뢰도가 함께 나타나 우선 후보로 유지할 수 있습니다.", "Type 1 and high reliability support keeping this as a priority candidate."],
    transitionCopy: ["Pt는 경쟁력이 있지만 Type {type} 전환 거동이 보여 곡선과 XAI 확인이 유용합니다.", "Pt is competitive, but the Type {type} transition makes the curve and XAI worth reviewing."],
    actualResult: ["실제 모델 결과", "Actual model result"],
    exampleResult: ["예시 데이터", "Example data"],
    previewResult: ["시안 결과", "Preview result"],
    noResultYet: ["아직 실행된 결과 없음", "No result yet"],
    justNow: ["방금 전", "just now"],
    displacementAxis: ["변위 (in)", "Displacement (in)"],
    forceAxis: ["하중 (N)", "Force (N)"],
    predictedPt: ["예측 Pt", "Predicted Pt"],
    currentCase: ["현재 Case · {case}", "Current case · {case}"],
    experiments: ["{count}개 실험", "{count} experiments"],
    experimentsLocations: ["{experiments}개 실험 · {locations}개 위치", "{experiments} experiments · {locations} locations"],
    currentInput: ["현재 입력", "Current input"],
    modelPrediction: ["모델 예측", "Model prediction"],
    sameLocation: ["같은 θ 위치의 기존 해석", "Existing analyses at the same θ location"],
    selectedCaseAnalysis: ["선택한 Case의 기존 해석", "Existing analysis for the selected case"],
    otherCaseAnalysis: ["다른 Case의 기존 해석", "Existing analysis for another case"],
    reliability: ["신뢰도", "Reliability"],
    xaiPreviewSummary: ["현재 입력에서 예측 변화가 큰 물리 feature를 시안용 민감도로 정렬했습니다.", "Physics features are ranked by preview sensitivity for the current input."],
    xaiNormalized: ["각 수치는 전체 계산값을 100%로 정규화한 상대 기여도입니다.", "Each value is a relative contribution normalized across the full calculation."],
    xaiFallbackNote: ["실제 모델이 연결되면 선택한 모델의 local XAI 결과로 교체됩니다.", "This will be replaced by local XAI from the selected model when the model is connected."],
    localSensitivity: ["국부 민감도 {value}", "Local sensitivity {value}"],
    relativeContribution: ["상대 기여도 {value}%", "Relative contribution {value}%"],
    moreCount: ["{count}개", "{count}"],
    designSpaceDefault: ["현재 입력과 가까운 기존 해석 데이터를 기준으로 비교합니다.", "Compares against existing analyses nearest to the current input."],
    restoredRun: ["선택한 실행 조건을 입력 패널에 불러왔습니다.", "The selected run inputs were restored to the setup panel."],
    invalidTheta: ["Theta 값은 −90°에서 +90° 사이여야 합니다.", "Theta values must be between −90° and +90°."],
    invalidPanel: ["패널 치수는 0보다 커야 합니다.", "Panel dimensions must be greater than zero."],
    calculating: ["예측 결과를 계산하고 있습니다…", "Calculating the forecast…"],
    predictionComplete: ["실제 모델 예측을 완료했습니다. XAI와 설계 공간을 이어서 불러옵니다.", "Model prediction complete. Loading XAI and the design space."],
    apiFallback: ["모델 API가 연결되지 않아 동일 입력의 시안 결과를 표시했습니다.", "The model API is unavailable, so a preview result for the same inputs is shown."],
    languageKorean: ["한국어", "Korean"],
    languageEnglish: ["영어", "English"],
    languageNav: ["언어 선택", "Language selection"],
    stackAriaLabel: ["{case} 적층 · θ₁ {theta1}, θ₂ {theta2} · {count} plies", "{case} laminate · θ₁ {theta1}, θ₂ {theta2} · {count} plies"],
    xaiCurrentValue: ["현재값 {value}", "Current {value}"],
    xaiMaskedValue: ["{value}(으)로 대체", "Replaced with {value}"],
  };

  const xaiKoreanByName = {
    angle_min_abs: ["최소 |θ|", "두 각도군 중 더 작은 절대각입니다. 0°/90° 축 방향에 지나치게 가까운 조합인지 보여줍니다."],
    panel_aspect: ["패널 종횡비", "패널 길이를 폭으로 나눈 값으로, 형상에 따른 구조 응답 차이를 나타냅니다."],
    case_case2: ["Case 2 표시자", "현재 적층 구조가 Case 2인지 모델에 알려주는 표시자입니다."],
    case_case3: ["Case 3 표시자", "현재 적층 구조가 Case 3인지 모델에 알려주는 표시자입니다."],
    case_case4: ["Case 4 표시자", "현재 적층 구조가 Case 4인지 모델에 알려주는 표시자입니다."],
    d11: ["D11 굽힘 강성", "적층판의 길이 방향 굽힘 강성으로, 하중 방향의 굽힘 저항과 직접 관련됩니다."],
    d22: ["D22 굽힘 강성", "적층판의 폭 방향 굽힘 강성입니다."],
    d12: ["D12 굽힘 커플링", "두 굽힘 방향의 결합을 나타내며 Pt 이후 곡선 형상에 영향을 줄 수 있습니다."],
    d66: ["D66 비틀림 강성", "비틀림과 전단 굽힘에 대한 강성으로, 모드 전환과 Pt 이후 거동에 영향을 줄 수 있습니다."],
    a11: ["A11 막 강성", "적층판의 길이 방향 막 강성입니다."],
    a22: ["A22 막 강성", "적층판의 폭 방향 막 강성입니다."],
    a12: ["A12 막 커플링", "적층 A 행렬의 평면 내 막 커플링 항입니다."],
    a66: ["A66 전단 강성", "적층 A 행렬의 평면 내 전단 강성입니다."],
    angle_abs_mean: ["평균 |θ|", "전체 적층에서 절대각의 평균으로, ±45° 계열 영역과의 거리를 보여줍니다."],
    abs_theta1: ["|θ₁|", "첫 번째 각도군이 0° 축 방향에서 얼마나 벗어났는지 나타냅니다."],
    abs_theta2: ["|θ₂|", "두 번째 각도군이 0° 축 방향에서 얼마나 벗어났는지 나타냅니다."],
    angle_max_abs: ["최대 |θ|", "두 각도군 중 더 큰 절대각으로, 90°에 가까운 적층 여부를 구분하는 데 도움이 됩니다."],
    b_coupling_norm: ["B 행렬 커플링 크기", "B16과 B26 막-굽힘 커플링 항을 합친 크기입니다."],
    stack_symmetry_mismatch: ["적층 대칭 불일치", "상·하부 플라이 각도의 불일치 정도로, 막-굽힘 커플링 가능성을 나타냅니다."],
    bending_anisotropy: ["굽힘 이방성", "D11과 D22의 정규화된 차이로 방향별 굽힘 거동을 나타냅니다."],
    d11_d22_ratio: ["D11/D22 비율", "길이·폭 방향 굽힘 강성의 균형을 나타내는 이방성 비율입니다."],
    a11_a22_ratio: ["A11/A22 비율", "길이·폭 방향 막 강성의 균형을 나타내는 이방성 비율입니다."],
    d16: ["D16 굽힘-비틀림 커플링", "하중 방향 굽힘과 비틀림 응답 사이의 D 행렬 커플링입니다."],
    d26: ["D26 굽힘-비틀림 커플링", "폭 방향 굽힘과 비틀림 응답 사이의 D 행렬 커플링입니다."],
    theta_abs_diff: ["|θ₁ − θ₂|", "두 Double-Double 각도군 사이의 절대 간격입니다."],
    membrane_anisotropy: ["막 이방성", "A11과 A22의 정규화된 차이로 방향별 막 거동을 나타냅니다."],
    theta_diff: ["θ 차이", "두 각도군의 차이를 나타내는 모델 파생 Feature입니다."],
    stack_balance_cos_sum: ["적층 밸런스 cosine", "전체 플라이의 ±θ 균형을 모델이 구분하도록 돕는 삼각함수 기반 지표입니다."],
    theta1: ["θ₁", "첫 번째 Double-Double 각도군의 모델 입력값입니다."],
    theta2: ["θ₂", "두 번째 Double-Double 각도군의 모델 입력값입니다."],
    theta_product: ["θ₁ × θ₂", "두 각도군의 부호와 조합 효과를 나타내는 상호작용 Feature입니다."],
    d_coupling_norm: ["D 행렬 커플링 크기", "D16과 D26 굽힘-비틀림 커플링 항을 합친 크기입니다."],
    b16: ["B16 굽힘-비틀림 커플링", "하중 방향 굽힘과 비틀림·전단 응답 사이의 B 행렬 커플링입니다."],
    b26: ["B26 굽힘-비틀림 커플링", "폭 방향 굽힘과 비틀림·전단 응답 사이의 B 행렬 커플링입니다."],
    theta_sum: ["θ 합", "두 각도군의 합을 나타내는 모델 파생 Feature입니다."],
    panel_b_in: ["패널 폭", "해석 모델에 입력된 패널 폭 b(in)입니다."],
    b_slenderness: ["폭 세장비", "패널 폭을 전체 적층 두께로 나눈 값입니다."],
    angle_abs_std: ["|θ| 분산", "두 Double-Double 각도군의 절대각이 얼마나 퍼져 있는지 나타냅니다."],
    a_slenderness: ["길이 세장비", "패널 길이를 전체 적층 두께로 나눈 값입니다."],
    panel_a_in: ["패널 길이", "해석 모델에 입력된 패널 길이 a(in)입니다."],
  };

  const xaiKoreanText = {
    "Tree ensemble live local feature masking": "Tree ensemble 입력별 Feature masking",
    "GointMLP live local feature masking": "GointMLP 입력별 Feature masking",
    "Teacher-Student neural live local feature masking": "Teacher-Student 입력별 Feature masking",
    "Occlusion sensitivity · preview": "Occlusion sensitivity · 예시",
    "Feature importance is local to this exact theta, Case, and panel-size input.": "Feature 중요도는 현재 θ, Case, 패널 크기에 맞춰 계산한 local 결과입니다.",
    "Each bar measures the relative model-output change after masking one feature.": "각 막대는 Feature 하나를 기준값으로 가렸을 때 모델 출력이 얼마나 변하는지 나타냅니다.",
    "The explanation uses the deployed 3-size model directly rather than borrowing an older global XAI report.": "기존 global 보고서가 아니라 현재 배포된 3-Size 모델을 직접 설명합니다.",
    "Use the explanation as engineering guidance; promising candidates still need simulation validation.": "설계 방향을 잡는 참고값으로 사용하고, 중요한 후보는 해석으로 검증하는 것이 좋습니다.",
    "theta + canonical CLT physics + panel geometry": "θ + 정규화 CLT 물리 Feature + 패널 형상",
  };

  function localizeXaiText(text) {
    const value = String(text || "");
    if (locale !== "ko" || !value) return value;
    if (value.startsWith("This explanation evaluates ") && value.includes("actual 3-size model")) {
      return "현재 선택한 3-Size 모델을 θ, Case, 패널 형상 조건에서 직접 평가했습니다. CLT·각도·형상 Feature를 하나씩 기준값으로 가린 뒤 예측 응답의 변화량을 계산합니다.";
    }
    return xaiKoreanText[value] || value;
  }

  function localizeXaiFeature(feature = {}) {
    if (locale !== "ko") {
      return {
        title: feature.label || feature.name || "-",
        description: feature.explanation || "",
      };
    }
    const copy = xaiKoreanByName[feature.name];
    return {
      title: copy?.[0] || feature.label || feature.name || "-",
      description: copy?.[1] || localizeXaiText(feature.explanation),
    };
  }

  function xaiCategoryLabel(category, featureName = "") {
    const isGeometry = featureName.startsWith("panel_") || featureName.endsWith("_slenderness");
    const labels = locale === "ko"
      ? { angle: "각도", stiffness: "강성", coupling: "커플링", case: "Case", curve: "곡선", other: isGeometry ? "형상" : "기타" }
      : { angle: "Angle", stiffness: "Stiffness", coupling: "Coupling", case: "Case", curve: "Curve", other: isGeometry ? "Geometry" : "Other" };
    return labels[category] || labels.other;
  }

  function localizeXaiPerturbation(perturbation) {
    const value = String(perturbation || "");
    const match = value.match(/^masked to\s+(.+)$/i);
    if (!match) return value;
    if (locale === "ko") return `${match[1]}${match[1] === "1" ? "로" : "으로"} 대체`;
    return t("xaiMaskedValue", { value: match[1] });
  }

  function format(template, values = {}) {
    return Object.entries(values).reduce(
      (output, [key, value]) => output.replaceAll(`{${key}}`, String(value)),
      template,
    );
  }

  function t(key, values) {
    const pair = messages[key];
    if (!pair) return key;
    return format(pair[locale === "ko" ? 0 : 1], values);
  }

  function translateStatic(root = document) {
    if (locale !== "en") return;
    document.title = staticEnglish[document.title] || document.title;
    const walker = document.createTreeWalker(root.body || root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach((node) => {
      const trimmed = node.textContent.trim();
      const translated = staticEnglish[trimmed];
      if (!translated) return;
      node.textContent = node.textContent.replace(trimmed, translated);
    });
    const attributeTranslations = {
      "현재 운영 화면으로 돌아가기": "Return to the current production UI",
      "분석 모드와 현재 입력": "Analysis mode and current input",
      "분석 모드": "Analysis mode",
      "Theta 1 슬라이더": "Theta 1 slider",
      "Theta 2 슬라이더": "Theta 2 slider",
      "Double-Double 적층 미리보기": "Double-Double laminate preview",
      "적층 미리보기 범례": "Laminate preview legend",
      "예측 결과 보기": "Forecast result views",
      "요약 예측 응답 곡선": "Summary predicted response curve",
      "요약 적층 fingerprint": "Summary laminate fingerprint",
      "상세 3D 적층 구조": "Detailed 3D laminate stack",
      "적층 구조 요약": "Laminate stack summary",
      "Ply Sequence 범례": "Ply sequence legend",
      "전체 Ply Sequence": "Full ply sequence",
      "핵심 예측 지표": "Key forecast metrics",
      "예측 문맥": "Prediction context",
      "곡선 핵심 지표": "Key curve metrics",
      "예측 응답 곡선": "Predicted response curve",
      "응답 곡선 확대/축소": "Response curve zoom controls",
      "응답 곡선 범례": "Response curve legend",
      "설계 공간 Case 필터": "Design-space case filter",
      "설계 공간 산점도": "Design-space scatter plot",
      "설계 공간 지도 범례": "Design-space map legend",
      "곡선 축소": "Zoom curve out",
      "곡선 확대": "Zoom curve in",
      "곡선 보기 초기화": "Reset curve view",
    };
    root.querySelectorAll?.("[aria-label]").forEach((element) => {
      const translated = attributeTranslations[element.getAttribute("aria-label")];
      if (translated) element.setAttribute("aria-label", translated);
    });
  }

  document.documentElement.lang = locale;
  window.ImperialAXLaminateLocale = {
    locale,
    numberLocale,
    t,
    translateStatic,
    localizeXaiText,
    localizeXaiFeature,
    xaiCategoryLabel,
    localizeXaiPerturbation,
  };
})();
