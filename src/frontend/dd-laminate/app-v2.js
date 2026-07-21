const isLocalStaticHost = ["localhost", "127.0.0.1"].includes(window.location.hostname)
  && !["8000", "80", "443"].includes(window.location.port);
const API_BASE = isLocalStaticHost
  ? `http://${window.location.hostname || "localhost"}:8000/api/v1/dd-laminate`
  : `${window.location.origin}/api/v1/dd-laminate`;
const RAG_BASE = API_BASE.replace(/\/dd-laminate$/, "/rag");
const IS_KO = document.documentElement.lang.toLowerCase().startsWith("ko");
const TEXT = {
  predicting: IS_KO ? "예측 중..." : "Predicting...",
  apiConnected: IS_KO ? "API 준비됨" : "API ready",
  apiOffline: IS_KO ? "오프라인" : "Offline",
  apiStart: IS_KO
    ? "예측하기 전에 DD API를 먼저 실행해 주세요."
    : "Start the DD API at http://localhost:8000 before predicting.",
  noProbability: IS_KO ? "이 모델은 확률 출력을 제공하지 않습니다." : "No probability output for this model.",
  unknown: IS_KO ? "알 수 없음" : "Unknown",
  estimatedCurveEmpty: IS_KO ? "예측 곡선이 여기에 표시됩니다." : "Estimated curve will appear here.",
  displacementAxis: IS_KO ? "변위" : "Displacement",
  forceAxis: IS_KO ? "하중" : "Force",
  predictedPtLabel: IS_KO ? "예측 Pt" : "Predicted Pt",
  curveFitPtLabel: IS_KO ? "곡선 Pt" : "Curve-fit Pt",
  fitIntersectionLabel: IS_KO ? "Fit Intersection" : "Fit Intersection",
  kinkGuideLabel: IS_KO ? "Kink 기준선" : "Kink guide",
  selectCsv: IS_KO
    ? "두 열로 된 force-displacement CSV를 선택해 주세요."
    : "Select a two-column force-displacement CSV.",
  csvPreviewFailed: IS_KO
    ? "CSV 미리보기 실패: 숫자 displacement,force 행이 1개 이상 필요합니다."
    : "CSV preview failed: expected at least one numeric displacement,force row.",
  csvParseFailed: IS_KO ? "이 CSV를 읽을 수 없습니다." : "Could not parse this CSV.",
  batchPredicting: IS_KO ? "일괄 예측 중..." : "Batch predicting...",
  batchResults: IS_KO ? "일괄 분류 결과" : "Batch classification results",
  batchDownload: IS_KO ? "CSV 다운로드" : "Download CSV",
  batchSummary: (ok, total) => IS_KO ? `${total}개 중 ${ok}개 분류 완료` : `${ok} of ${total} files classified`,
  batchMetadataHint: IS_KO
    ? "metadata CSV가 없으면 화면 입력값을 모든 파일에 공통 적용했습니다."
    : "Without metadata CSV, the shared form inputs were reused for every file.",
  stackSequenceFailed: IS_KO
    ? "Ply sequence를 읽을 수 없습니다. 예: 30,-30,-60,60 형식으로 입력해 주세요."
    : "Could not parse the ply sequence. Use a format like 30,-30,-60,60.",
  noFileSelected: IS_KO ? "선택된 파일 없음" : "No file selected",
  reportTitle: IS_KO ? "Double-Double 적층 예측 리포트" : "Double-Double Laminate Prediction Report",
  reportCreated: IS_KO ? "생성 시간" : "Created",
  reportInputs: IS_KO ? "입력 조건" : "Inputs",
  reportProbabilities: IS_KO ? "Type 확률" : "Type Probabilities",
  reportCurve: IS_KO ? "예측 곡선" : "Predicted Curve",
  reportNotes: IS_KO ? "노트" : "Notes",
  reportPdfHint: IS_KO ? "인쇄 창에서 PDF로 저장을 선택하세요." : "Choose Save as PDF in the print dialog.",
  reportNoResult: IS_KO ? "내보낼 예측 결과가 없습니다." : "No prediction result is available to export.",
  reportExportFailed: IS_KO ? "리포트 내보내기에 실패했습니다." : "Report export failed.",
  u3PtTitle: IS_KO ? "u3 Pt 예측" : "u3 Pt Prediction",
  u3ForecastSummary: IS_KO
    ? "θ₁, θ₂, Case만으로 u3 Type, 전이하중 Pt, 대략적인 곡선을 예측했습니다."
    : "Predicted u3 Type, transition load Pt, and an approximate curve from theta and case.",
  xaiLoadingTitle: IS_KO ? "XAI 계산 중" : "Loading XAI",
  xaiLoadingSummary: IS_KO
    ? "예측 결과를 먼저 표시했고, feature 영향도는 별도로 계산하고 있습니다."
    : "The prediction is ready. Feature influence is being calculated separately.",
  xaiLoadingMethod: IS_KO ? "XAI 별도 로딩" : "Deferred XAI loading",
  xaiLoadFailed: IS_KO
    ? "XAI 설명을 불러오지 못했습니다. 예측 결과는 정상적으로 사용할 수 있습니다."
    : "Could not load the XAI explanation. The prediction result is still usable.",
  xaiMore: (count) => IS_KO ? `나머지 ${count}개 feature 더보기` : `Show ${count} more features`,
  xaiLocalValue: IS_KO ? "현재값" : "Current",
  xaiLocalSensitivity: IS_KO ? "민감도" : "Sensitivity",
  xaiPerturbation: IS_KO ? "가상 제거" : "Virtual removal",
  researchLoadingTitle: IS_KO ? "설계 공간 분석 중" : "Loading design-space insight",
  researchLoadingSummary: IS_KO
    ? "현재 θ/Case 입력이 학습 데이터 공간 어디에 있는지 계산하고 있습니다."
    : "Checking where this theta/case input sits in the curated design space.",
  researchFailed: IS_KO
    ? "설계 공간 분석을 불러오지 못했습니다. 예측 결과는 정상적으로 사용할 수 있습니다."
    : "Could not load design-space insight. The prediction result is still usable.",
  designSpaceTitle: IS_KO ? "설계 공간 해석" : "Design-space context",
  caseRisk: IS_KO ? "Case 위험도" : "Case risk",
  nearestSimulations: IS_KO ? "가까운 해석 데이터" : "Nearest simulations",
  recommendedCandidates: IS_KO ? "추천 후보" : "Recommended candidates",
  applyCandidate: IS_KO ? "입력에 적용하고 예측" : "Apply and forecast",
  comparisonTitle: IS_KO ? "현재 입력 vs 추천 후보" : "Current input vs top candidate",
  currentPrediction: IS_KO ? "현재 예측" : "Current forecast",
  topCandidate: IS_KO ? "추천 후보" : "Top candidate",
  modelEstimate: IS_KO ? "모델 예측" : "Model estimate",
  datasetObservation: IS_KO ? "Dataset 관측값" : "Dataset observation",
  ptDelta: IS_KO ? "Pt 차이" : "Pt delta",
  caseRiskLabel: IS_KO ? "Case 위험도" : "Case risk",
  whyCandidate: IS_KO ? "왜 이 후보인가요?" : "Why this candidate?",
  selectedCasePoint: IS_KO ? "선택한 Case 데이터" : "Selected Case data",
  otherCasePoint: IS_KO ? "다른 Case 데이터" : "Other Case data",
  currentInputPoint: IS_KO ? "현재 입력" : "Current input",
  predictionHistory: IS_KO ? "예측 기록" : "Prediction history",
  predictionHistoryHint: IS_KO ? "카드를 누르면 해당 입력 조건을 다시 불러옵니다." : "Tap a card to reuse its setup.",
  manageHistory: IS_KO ? "관리" : "Manage",
  historyDeleteHint: IS_KO ? "삭제할 기록을 선택하세요." : "Select records to delete.",
  selectAllHistory: IS_KO ? "전체 선택" : "Select all",
  clearHistorySelection: IS_KO ? "선택 해제" : "Clear",
  deleteSelectedHistory: IS_KO ? "선택 삭제" : "Delete selected",
  cancelHistoryManage: IS_KO ? "취소" : "Cancel",
  selectedHistoryCount: (count) => IS_KO ? `${count}개 선택됨` : `${count} selected`,
  latest: IS_KO ? "최근" : "Latest",
  caseBehaviorZones: IS_KO ? "Case별 유리 영역" : "Case behavior zones",
  type1Zone: IS_KO ? "상위 Pt Type 1 영역" : "High-Pt Type 1 zone",
  highPtZone: IS_KO ? "상위 Pt 영역" : "High-Pt zone",
  thetaWindow: IS_KO ? "Theta 범위" : "Theta range",
  bestObserved: IS_KO ? "최고 관측값" : "Best observed",
  bestPt: IS_KO ? "최고 Pt" : "Best Pt",
  bestTheta: IS_KO ? "최고 θ" : "Best θ",
  bestType: IS_KO ? "최고 Type" : "Best Type",
  coverage: IS_KO ? "영역 샘플" : "Zone samples",
  scoringBasis: IS_KO ? "추천 점수 구성" : "Recommendation score",
  ptContribution: IS_KO ? "Pt 기여" : "Pt",
  typeContribution: IS_KO ? "Type 기여" : "Type",
  proximityContribution: IS_KO ? "거리 기여" : "Distance",
  totalScore: IS_KO ? "총점" : "Total",
  noComparison: IS_KO
    ? "비교할 추천 후보가 아직 없습니다."
    : "No recommendation candidate is available for comparison yet.",
  riskLow: IS_KO ? "낮음" : "Low",
  riskMedium: IS_KO ? "중간" : "Medium",
  riskHigh: IS_KO ? "높음" : "High",
  observedType: IS_KO ? "관측 Type" : "Observed Type",
  score: IS_KO ? "점수" : "Score",
  reliabilityTitle: IS_KO ? "예측 안정성" : "Prediction reliability",
  reliabilityHigh: IS_KO ? "높은 신뢰" : "High confidence",
  reliabilityMedium: IS_KO ? "중간 신뢰" : "Medium confidence",
  reliabilityLow: IS_KO ? "주의 필요" : "Use caution",
  reliabilityScore: IS_KO ? "종합 신뢰도" : "Reliability",
  ptRange: IS_KO ? "Pt 예상 범위" : "Pt screening range",
  designCoverage: IS_KO ? "설계공간 커버리지" : "Design-space coverage",
  typeAgreement: IS_KO ? "주변 Type 일치도" : "Nearby Type agreement",
  teacherStudentTitle: IS_KO ? "Tree vs Student 일치도" : "Tree vs Student agreement",
  teacherStudentAgreement: IS_KO ? "모델 일치도" : "Agreement",
  teacherStudentType: IS_KO ? "Type 비교" : "Type comparison",
  teacherStudentPtDelta: IS_KO ? "Pt 차이" : "Pt delta",
  teacherStudentCurveDelta: IS_KO ? "곡선 차이" : "Curve delta",
  teacherStudentStudent: IS_KO ? "Student 예측" : "Student prediction",
  teacherStudentMatch: IS_KO ? "일치" : "Match",
  teacherStudentMismatch: IS_KO ? "불일치" : "Mismatch",
  interpolation: IS_KO ? "보간 영역" : "Interpolation",
  nearEdge: IS_KO ? "경계 근처" : "Near edge",
  extrapolation: IS_KO ? "외삽 주의" : "Extrapolation",
  ragAsking: IS_KO ? "답변 생성 중..." : "Answering...",
  ragAnswerTitle: IS_KO ? "Composite AI 답변" : "Composite AI answer",
  ragCitations: IS_KO ? "근거 자료" : "Citations",
  ragShowCitations: IS_KO ? "근거 보기" : "Show citations",
  ragHideCitations: IS_KO ? "근거 숨기기" : "Hide citations",
  ragFailed: IS_KO ? "Composite AI 답변을 불러오지 못했습니다." : "Could not load the Composite AI answer.",
};
const MODEL_LABELS_KO = {
  "Theta + case - ExtraTrees": "θ + Case - ExtraTrees",
  "Theta + case - HistGradientBoosting": "θ + Case - HistGradientBoosting",
  "Theta + Case - RandomForest": "θ + Case - RandomForest",
  "Theta + case - GointMLP-style NN": "θ + Case - GointMLP 스타일 신경망",
  "Curve + metadata - HistGradientBoosting": "곡선 + 메타데이터 - HistGradientBoosting",
  "Curve + metadata - RandomForest": "곡선 + 메타데이터 - RandomForest",
  "Curve + metadata - ExtraTrees": "곡선 + 메타데이터 - ExtraTrees",
  "Curve + metadata - Goint sequence NN": "곡선 + 메타데이터 - Goint sequence 신경망",
  "RandomForest": "RandomForest",
  "ExtraTrees": "ExtraTrees",
  "ExtraTrees + PCA": "ExtraTrees + PCA",
  "GointMLP NN": "GointMLP 신경망",
  "GRU + GointMLP NN": "GRU + GointMLP 신경망",
  "Estimated response - ExtraTrees + PCA + CLT": "적층 예측 - ExtraTrees + PCA + CLT",
  "Estimated response - GointMLP NN + CLT": "적층 예측 - GointMLP 신경망 + CLT",
  "Laminate Forecast - ExtraTrees + PCA + CLT": "적층 예측 - ExtraTrees + PCA + CLT",
  "Laminate Forecast - Cases 2/3/4": "적층 예측 - Case 2/3/4",
  "Laminate Forecast - GointMLP NN + CLT": "적층 예측 - GointMLP 신경망 + CLT",
  "Laminate Forecast - GointMLP NN + CLT (legacy Case3/4)": "적층 예측 - GointMLP 신경망 + CLT (기존 Case3/4)",
  "Laminate Forecast - Tree (Theta)": "적층 예측 - Tree (θ)",
  "Laminate Forecast - GointMLP (Theta)": "적층 예측 - GointMLP (θ)",
  "Laminate Forecast - Tree + Physics XAI": "적층 예측 - Tree + Physics XAI",
  "Laminate Forecast - GointMLP + Physics XAI": "적층 예측 - GointMLP + Physics XAI",
  "Tree + Compact XAI": "Tree + Compact XAI",
  "GointMLP + NN-Friendly XAI": "GointMLP + NN-Friendly XAI",
  "Laminate Forecast - Tree + Compact Physics XAI": "적층 예측 - Tree + Compact Physics XAI",
  "Laminate Forecast - GointMLP + NN-Friendly Physics XAI": "적층 예측 - GointMLP + NN-Friendly Physics XAI",
  "Laminate Forecast - Geometry ML": "적층 예측 - Geometry ML",
  "Laminate Forecast - Geometry DL": "적층 예측 - Geometry DL",
  "Laminate Forecast - Machine Learning": "적층 예측 - Machine Learning",
  "Laminate Forecast - Deep Learning": "적층 예측 - Deep Learning",
  "u3 Forecast - ExtraTrees + PCA": "u3 예측 - ExtraTrees + PCA",
  "u3 Forecast - Physics XAI": "u3 예측 - Physics XAI",
  "u3 Forecast - GointMLP NN": "u3 예측 - GointMLP 신경망",
  "u3 Forecast - Tree (Theta)": "u3 예측 - Tree (θ)",
  "u3 Forecast - Tree + Physics XAI": "u3 예측 - Tree + Physics XAI",
  "u3 Forecast - GointMLP (Theta)": "u3 예측 - GointMLP (θ)",
  "u3 Forecast - GointMLP + Physics XAI": "u3 예측 - GointMLP + Physics XAI",
  "u3 Forecast - Machine Learning": "u3 예측 - Machine Learning",
  "u3 Forecast - Deep Learning": "u3 예측 - Deep Learning",
};
const NOTE_LABELS_KO = {
  "Theta/case prediction is an estimate; curve-based models are preferred once simulation CSV is available.":
    "θ/Case 기반 예측입니다. 해석 CSV가 있으면 곡선 기반 모델 사용을 권장합니다.",
  "Estimated response is a surrogate prediction; validate promising candidates with simulation.":
    "모델 예측 결과입니다. 유망한 후보는 해석으로 검증해 주세요.",
  "Laminate Forecast is a surrogate prediction; validate promising candidates with simulation.":
    "모델 예측 결과입니다. 유망한 후보는 해석으로 검증해 주세요.",
  "ExtraTrees + PCA is a surrogate prediction; validate promising candidates with simulation.":
    "ExtraTrees + PCA 예측 결과입니다. 유망한 후보는 해석으로 검증해 주세요.",
  "GointMLP NN is a surrogate prediction; validate promising candidates with simulation.":
    "GointMLP 신경망 예측 결과입니다. 유망한 후보는 해석으로 검증해 주세요.",
  "ExtraTrees + PCA prediction; validate promising candidates with simulation.":
    "ExtraTrees + PCA 예측 결과입니다. 유망한 후보는 해석으로 검증해 주세요.",
  "GointMLP NN prediction; validate promising candidates with simulation.":
    "GointMLP 신경망 예측 결과입니다. 유망한 후보는 해석으로 검증해 주세요.",
  "u3 Forecast - ExtraTrees + PCA prediction; validate promising candidates with simulation.":
    "u3 Forecast 예측 결과입니다. 유망한 후보는 해석으로 검증해 주세요.",
  "u3 Forecast - GointMLP NN prediction; validate promising candidates with simulation.":
    "u3 Forecast GointMLP 신경망 예측 결과입니다. 유망한 후보는 해석으로 검증해 주세요.",
  "This u3 forecast uses only theta and case inputs; u3 Type is predicted, not user-selected.":
    "이 u3 Forecast는 θ/Case만 사용하며, u3 Type은 사용자가 고르는 값이 아니라 모델이 예측합니다.",
};

const apiStatus = document.querySelector("#api-status");
const workspaceGrid = document.querySelector("#workspace-grid");
const summaryStrip = document.querySelector(".summary-strip");
const inputPanel = document.querySelector(".input-panel");
const visualPanel = document.querySelector(".visual-panel");
const dynamicStackVisuals = Array.from(
  document.querySelectorAll("#dynamic-stack-visual, [data-dynamic-stack-visual]")
);
const dynamicStackFormula = document.querySelector("#dynamic-stack-formula");
const dynamicStackCount = document.querySelector("#dynamic-stack-count");
const thetaForm = document.querySelector("#theta-form");
const curveForm = document.querySelector("#curve-form");
const responseForm = document.querySelector("#response-form");
const u3PtForm = document.querySelector("#u3-pt-form");
const stackPreviewForm = document.querySelector("#stack-preview-form");
const thetaModel = document.querySelector("#theta-model");
const curveModel = document.querySelector("#curve-model");
const responseModel = document.querySelector("#response-model");
const u3PtModel = document.querySelector("#u3-pt-model");
const emptyState = document.querySelector("#empty-state");
const readyCopy = document.querySelector("#ready-copy");
const predictionHistory = document.querySelector("#prediction-history");
const resultPanel = document.querySelector("#result");
const stackPreviewResult = document.querySelector("#stack-preview-result");
const stackPreviewTitle = document.querySelector("#stack-preview-title");
const stackPreviewMetrics = document.querySelector("#stack-preview-metrics");
const stackPreviewSequence = document.querySelector("#stack-preview-sequence");
const stackPreviewPhysics = document.querySelector("#stack-preview-physics");
const stackPreviewNotes = document.querySelector("#stack-preview-notes");
const errorPanel = document.querySelector("#error");
const predictedType = document.querySelector("#predicted-type");
const confidenceEl = document.querySelector("#confidence");
const probabilityBars = document.querySelector("#probability-bars");
const modelLabel = document.querySelector("#model-label");
const inputSummary = document.querySelector("#input-summary");
const notes = document.querySelector("#notes");
const curveFile = document.querySelector("#curve-file");
const curveMetadataFile = document.querySelector("#curve-metadata-file");
const curveBatchResults = document.querySelector("#curve-batch-results");
const curvePreviewPanel = document.querySelector("#curve-preview-panel");
const curvePreviewTitle = document.querySelector("#curve-preview-title");
const curvePreviewCanvas = document.querySelector("#curve-preview-canvas");
const curvePointCount = document.querySelector("#curve-point-count");
const curveMaxDisplacement = document.querySelector("#curve-max-displacement");
const curveMaxForce = document.querySelector("#curve-max-force");
const clearCurvePreview = document.querySelector("#clear-curve-preview");
const responseEstimate = document.querySelector("#response-estimate");
const responseCurveCanvas = document.querySelector("#response-curve-canvas");
const responseCurveTitle = document.querySelector("#response-curve-title");
const responseCurveLegend = document.querySelector(".curve-legend");
const responseCurveZoomLabel = document.querySelector("#response-curve-zoom-label");
const responseCurveZoomButtons = Array.from(document.querySelectorAll("[data-curve-zoom]"));
const predictedPt = document.querySelector("#predicted-pt");
const predictedMaxDisplacement = document.querySelector("#predicted-max-displacement");
const predictedMaxForce = document.querySelector("#predicted-max-force");
const uncertaintyPanel = document.querySelector("#uncertainty-panel");
const uncertaintyLabel = document.querySelector("#uncertainty-label");
const uncertaintyGrid = document.querySelector("#uncertainty-grid");
const uncertaintyNotes = document.querySelector("#uncertainty-notes");
const teacherStudentPanel = document.querySelector("#teacher-student-panel");
const teacherStudentTitle = document.querySelector("#teacher-student-title");
const teacherStudentLabel = document.querySelector("#teacher-student-label");
const teacherStudentGrid = document.querySelector("#teacher-student-grid");
const teacherStudentNotes = document.querySelector("#teacher-student-notes");
const xaiPanel = document.querySelector("#xai-panel");
const xaiTitle = document.querySelector("#xai-title");
const xaiSummary = document.querySelector("#xai-summary");
const xaiMethod = document.querySelector("#xai-method");
const xaiFeatures = document.querySelector("#xai-features");
const xaiNotes = document.querySelector("#xai-notes");
const researchPanel = document.querySelector("#research-panel");
const researchTitle = document.querySelector("#research-title");
const researchSummary = document.querySelector("#research-summary");
const researchMapCanvas = document.querySelector("#research-map-canvas");
const researchMapTooltip = document.querySelector("#research-map-tooltip");
const researchComparison = document.querySelector("#research-comparison");
const researchCaseInsights = document.querySelector("#research-case-insights");
const researchCaseInsightList = document.querySelector("#research-case-insight-list");
const researchCaseList = document.querySelector("#research-case-list");
const researchNearestList = document.querySelector("#research-nearest-list");
const researchRecommendations = document.querySelector("#research-recommendations");
const researchNotes = document.querySelector("#research-notes");
const exportReportPng = document.querySelector("#export-report-png");
const exportReportPdf = document.querySelector("#export-report-pdf");
const ragForm = document.querySelector("#rag-form");
const ragAnswer = document.querySelector("#rag-answer");
const ragQueryInput = ragForm?.querySelector('textarea[name="query"]');
let latestPredictionData = null;
const RESPONSE_CURVE_MIN_ZOOM = 1;
const RESPONSE_CURVE_MAX_ZOOM = 6;
const responseCurveView = {
  points: null,
  predictedPtValue: null,
  fitMode: "standard",
  backendFit: null,
  scale: 1,
  centerXNorm: 0.5,
  centerYNorm: 0.5,
  logicalWidth: 720,
  logicalHeight: 432,
  domain: null,
  plot: null,
  drag: null,
};
let responseCurveResizeTimer = null;
let xaiRequestSerial = 0;
let researchRequestSerial = 0;
let researchMapState = { hoverPoints: [], inputs: null };

const PRIMARY_RESPONSE_MODEL_KEYS = [
  "response_geometry_tree_v1",
  "response_geometry_goint_v1",
  "response_hybrid_student_deploy_quick_v1",
];
const PREDICTION_HISTORY_KEY = "ddLaminate.predictionHistory.v1";
const PREDICTION_HISTORY_LIMIT = 5;
const selectedHistorySignatures = new Set();
let historyDeleteMode = false;
const XAI_VISIBLE_LIMIT = 5;
const STACK_FORMULAS = {
  Case2: "[[±θ₁]/[±θ₂]]₄",
  Case3: "[[±θ₁]/[±θ₂]/[∓θ₁]/[∓θ₂]]₂",
  Case4: "[([±θ₁]/[±θ₂])₂ / ([∓θ₁]/[∓θ₂])₂]",
};
const STACK_COLORS = {
  theta1: {
    topA: "#9aa9ed",
    topB: "#657bd4",
    sideA: "#7f90d4",
    sideB: "#5e70ba",
    edge: "#4e60aa",
  },
  theta2: {
    topA: "#e0bda0",
    topB: "#bc8f70",
    sideA: "#caa68b",
    sideB: "#a77e63",
    edge: "#8e684f",
  },
};

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

function formatCompactNumber(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "-";
  }
  const absolute = Math.abs(numeric);
  if (absolute > 0 && absolute < 0.001) {
    return numeric.toExponential(2);
  }
  const digits = absolute >= 100 ? 1 : absolute >= 1 ? 3 : 5;
  return numeric.toLocaleString(undefined, { maximumFractionDigits: digits });
}

function formatSignedAngle(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "-";
  }
  return `${numeric >= 0 ? "+" : ""}${formatMetric(numeric, 1)}°`;
}

function physicsLabel(label) {
  if (!IS_KO) {
    return label;
  }
  const labels = {
    "D11 bending stiffness": "D11 굽힘 강성",
    "D22 bending stiffness": "D22 굽힘 강성",
    "D66 twisting stiffness": "D66 비틀림 강성",
    "D11/D22 ratio": "D11/D22 비율",
    "Bending anisotropy": "굽힘 이방성",
    "A11 membrane stiffness": "A11 막 강성",
    "A22 membrane stiffness": "A22 막 강성",
    "Stack symmetry mismatch": "적층 대칭 불일치",
    "Mean |θ|": "평균 |θ|",
    "|θ| spread": "|θ| 분산",
    "Panel aspect ratio": "패널 종횡비",
    "Length slenderness": "길이 방향 세장비",
    "Width slenderness": "폭 방향 세장비",
    "Panel length": "패널 길이",
    "Panel width": "패널 폭",
  };
  return labels[label] || label;
}

function formatAxisTick(value, smallValueDigits = 4) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "0";
  }
  const absolute = Math.abs(numeric);
  const digits = absolute >= 100 ? 0 : absolute >= 10 ? 1 : absolute >= 1 ? 2 : smallValueDigits;
  const rounded = Number(numeric.toFixed(digits));
  return rounded.toLocaleString(undefined, { maximumFractionDigits: digits });
}

function inputDisplayValue(key, value, labels = {}) {
  if (key === "theta1" || key === "theta2") {
    return formatMetric(value, 0);
  }
  return labels[value] || value;
}

function cleanModelLabel(label) {
  const cleaned = String(label || "").trim();
  const aliases = {
    "Laminate Forecast - Cases 2/3/4": "ExtraTrees + PCA",
    "Laminate Forecast - GointMLP NN + CLT (legacy Case3/4)": "GointMLP NN",
    "Laminate Forecast - Tree + Compact Physics XAI": "Tree + Compact XAI",
    "Laminate Forecast - GointMLP + NN-Friendly Physics XAI": "GointMLP + NN-Friendly XAI",
    "Laminate Forecast - Geometry ML": "Geometry ML",
    "Laminate Forecast - Geometry DL": "Geometry DL",
    "Estimated response - ExtraTrees + PCA + CLT": "ExtraTrees + PCA",
    "Estimated response - GointMLP NN + CLT": "GointMLP NN",
    "Theta + Case - RandomForest": "RandomForest",
    "Theta + case - GointMLP-style NN": "GointMLP NN",
    "Curve + metadata - ExtraTrees": "ExtraTrees",
    "Curve + metadata - Goint sequence NN": "GRU + GointMLP NN",
    "Extra trees + PCA": "ExtraTrees + PCA",
    "GointMLP-style NN": "GointMLP NN",
    "u3 Forecast - ExtraTrees + PCA": "ExtraTrees + PCA",
  };
  return aliases[cleaned] || cleaned;
}

function displayModelLabel(label) {
  const cleaned = cleanModelLabel(label);
  return IS_KO ? (MODEL_LABELS_KO[cleaned] || cleaned) : cleaned;
}

function primaryModels(models, keys) {
  const byKey = new Map((models || []).map((model) => [model.key, model]));
  return keys.map((key) => byKey.get(key)).filter(Boolean);
}

function clampStackAngle(value) {
  const parsed = Number.parseFloat(value);
  if (!Number.isFinite(parsed)) {
    return 0;
  }
  return Math.max(-90, Math.min(90, Math.round(parsed)));
}

function formatThetaReadout(value) {
  const rounded = clampStackAngle(value);
  return `${rounded > 0 ? "+" : ""}${rounded}°`;
}

function activePredictionMode() {
  return document.querySelector(".mode-button.active")?.dataset.mode || "response";
}

function historyKindForMode(mode = activePredictionMode()) {
  return mode === "u3" ? "u3" : mode === "response" ? "response" : null;
}

function loadPredictionHistory() {
  try {
    const parsed = JSON.parse(localStorage.getItem(PREDICTION_HISTORY_KEY) || "[]");
    return Array.isArray(parsed) ? parsed.filter((run) => run && (run.kind === "response" || run.kind === "u3")) : [];
  } catch {
    return [];
  }
}

function writePredictionHistory(runs) {
  try {
    localStorage.setItem(PREDICTION_HISTORY_KEY, JSON.stringify(runs.slice(0, PREDICTION_HISTORY_LIMIT * 2)));
  } catch {
    // History is a convenience feature; prediction should keep working if storage is blocked.
  }
}

function historySignature(run) {
  return [run.kind, run.caseName, run.theta1, run.theta2, run.panelAIn ?? "-", run.panelBIn ?? "-", run.modelKey].join("|");
}

function currentPredictionHistoryRuns() {
  const kind = historyKindForMode();
  return kind
    ? loadPredictionHistory().filter((run) => run.kind === kind).slice(0, PREDICTION_HISTORY_LIMIT)
    : [];
}

function resetHistoryDeleteState() {
  historyDeleteMode = false;
  selectedHistorySignatures.clear();
}

function pruneHistorySelection(runs) {
  const visibleSignatures = new Set(runs.map((run) => historySignature(run)));
  Array.from(selectedHistorySignatures).forEach((signature) => {
    if (!visibleSignatures.has(signature)) {
      selectedHistorySignatures.delete(signature);
    }
  });
}

function deleteSelectedPredictionHistory() {
  if (!selectedHistorySignatures.size) {
    return;
  }
  const nextRuns = loadPredictionHistory().filter((run) => !selectedHistorySignatures.has(historySignature(run)));
  writePredictionHistory(nextRuns);
  resetHistoryDeleteState();
  renderPredictionHistory();
}

function savePredictionHistory(kind, data) {
  if (!kind || !data) {
    return;
  }
  const inputs = data.inputs || {};
  const run = {
    kind,
    caseName: inputs.case || "Case2",
    theta1: clampStackAngle(inputs.theta1),
    theta2: clampStackAngle(inputs.theta2),
    panelAIn: kind === "response" ? Number(inputs.panel_a_in || 6) : null,
    panelBIn: kind === "response" ? Number(inputs.panel_b_in || 4) : null,
    modelKey: data.model_key || historyFormForKind(kind)?.querySelector('select[name="model"]')?.value || "",
    modelLabel: displayModelLabel(data.model_label || ""),
    predictedType: data.predicted_type ?? null,
    confidence: data.confidence ?? null,
    predictedPt: data.predicted_pt ?? null,
    createdAt: new Date().toISOString(),
  };
  const allRuns = loadPredictionHistory();
  const nextRuns = [run, ...allRuns.filter((item) => historySignature(item) !== historySignature(run))];
  const trimmedByKind = ["response", "u3"].flatMap((itemKind) =>
    nextRuns.filter((item) => item.kind === itemKind).slice(0, PREDICTION_HISTORY_LIMIT)
  );
  writePredictionHistory(trimmedByKind);
  renderPredictionHistory();
}

function signedTheta(value) {
  const rounded = clampStackAngle(value);
  return `${rounded > 0 ? "+" : ""}${rounded}°`;
}

function historyFormForKind(kind) {
  return kind === "u3" ? u3PtForm : responseForm;
}

function applyPredictionHistoryRun(run) {
  const form = historyFormForKind(run.kind);
  if (!form) {
    return;
  }
  const modeButton = document.querySelector(`.mode-button[data-mode="${run.kind === "u3" ? "u3" : "response"}"]`);
  if (modeButton && !modeButton.classList.contains("active")) {
    modeButton.click();
  }
  const theta1Input = form.querySelector('input[name="theta1"]');
  const theta2Input = form.querySelector('input[name="theta2"]');
  const panelAInput = form.querySelector('input[name="panel_a_in"]');
  const panelBInput = form.querySelector('input[name="panel_b_in"]');
  const caseSelect = form.querySelector('select[name="case"]');
  const modelSelect = form.querySelector('select[name="model"]');
  if (theta1Input) theta1Input.value = String(clampStackAngle(run.theta1));
  if (theta2Input) theta2Input.value = String(clampStackAngle(run.theta2));
  if (panelAInput && run.panelAIn) panelAInput.value = String(run.panelAIn);
  if (panelBInput && run.panelBIn) panelBInput.value = String(run.panelBIn);
  if (caseSelect) caseSelect.value = run.caseName || "Case2";
  if (modelSelect && run.modelKey && Array.from(modelSelect.options).some((option) => option.value === run.modelKey)) {
    modelSelect.value = run.modelKey;
  }
  form.querySelectorAll('input[name="theta1"], input[name="theta2"]').forEach((input) => {
    input.dispatchEvent(new Event("change", { bubbles: true }));
  });
  updateDynamicStackPreview();
  inputPanel?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderPredictionHistory() {
  if (!predictionHistory || !readyCopy || !emptyState) {
    return;
  }
  const kind = historyKindForMode();
  const runs = currentPredictionHistoryRuns();
  pruneHistorySelection(runs);
  document.body.classList.toggle("has-history", runs.length > 0 && !document.body.classList.contains("has-result"));

  if (!runs.length) {
    resetHistoryDeleteState();
    readyCopy.classList.remove("hidden");
    predictionHistory.classList.add("hidden");
    predictionHistory.innerHTML = "";
    return;
  }

  readyCopy.classList.add("hidden");
  predictionHistory.classList.remove("hidden");
  predictionHistory.innerHTML = "";

  const head = document.createElement("div");
  head.className = "prediction-history-head";
  head.innerHTML = `
    <div>
      <p class="eyebrow">${kind === "u3" ? TEXT.u3PtTitle : (IS_KO ? "적층 예측" : "Laminate Forecast")}</p>
      <h2>${TEXT.predictionHistory}</h2>
      <p>${historyDeleteMode ? TEXT.historyDeleteHint : TEXT.predictionHistoryHint}</p>
    </div>
    <div class="prediction-history-actions"></div>
  `;
  const actions = head.querySelector(".prediction-history-actions");
  const countBadge = document.createElement("span");
  countBadge.className = "prediction-history-count";
  countBadge.textContent = historyDeleteMode ? TEXT.selectedHistoryCount(selectedHistorySignatures.size) : String(runs.length);
  actions.appendChild(countBadge);

  if (historyDeleteMode) {
    const selectAllButton = document.createElement("button");
    selectAllButton.type = "button";
    selectAllButton.className = "history-action-button";
    selectAllButton.textContent = TEXT.selectAllHistory;
    selectAllButton.disabled = selectedHistorySignatures.size === runs.length;
    selectAllButton.addEventListener("click", () => {
      runs.forEach((run) => selectedHistorySignatures.add(historySignature(run)));
      renderPredictionHistory();
    });

    const clearButton = document.createElement("button");
    clearButton.type = "button";
    clearButton.className = "history-action-button";
    clearButton.textContent = TEXT.clearHistorySelection;
    clearButton.disabled = selectedHistorySignatures.size === 0;
    clearButton.addEventListener("click", () => {
      selectedHistorySignatures.clear();
      renderPredictionHistory();
    });

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "history-action-button danger";
    deleteButton.textContent = TEXT.deleteSelectedHistory;
    deleteButton.disabled = selectedHistorySignatures.size === 0;
    deleteButton.addEventListener("click", deleteSelectedPredictionHistory);

    const cancelButton = document.createElement("button");
    cancelButton.type = "button";
    cancelButton.className = "history-action-button";
    cancelButton.textContent = TEXT.cancelHistoryManage;
    cancelButton.addEventListener("click", () => {
      resetHistoryDeleteState();
      renderPredictionHistory();
    });

    actions.append(selectAllButton, clearButton, deleteButton, cancelButton);
  } else {
    const manageButton = document.createElement("button");
    manageButton.type = "button";
    manageButton.className = "history-action-button danger";
    manageButton.textContent = TEXT.manageHistory;
    manageButton.addEventListener("click", () => {
      historyDeleteMode = true;
      selectedHistorySignatures.clear();
      renderPredictionHistory();
    });
    actions.appendChild(manageButton);
  }

  const list = document.createElement("div");
  list.className = "prediction-history-list";
  runs.forEach((run, index) => {
    const signature = historySignature(run);
    const isSelected = selectedHistorySignatures.has(signature);
    const button = document.createElement("button");
    button.type = "button";
    button.className = `prediction-history-card${historyDeleteMode ? " delete-mode" : ""}${isSelected ? " selected" : ""}`;
    button.setAttribute("aria-pressed", historyDeleteMode ? String(isSelected) : "false");
    button.innerHTML = `
      <div class="prediction-history-main">
        ${historyDeleteMode ? `<span class="prediction-history-check">${isSelected ? "✓" : ""}</span>` : ""}
        <span class="prediction-history-index">${index === 0 ? TEXT.latest : `#${index + 1}`}</span>
        <strong class="prediction-history-case">${run.caseName || "Case2"}</strong>
      </div>
      <div class="prediction-history-model">${run.modelLabel || "-"}</div>
      <div class="prediction-history-chips">
        <span>θ₁ ${signedTheta(run.theta1)}</span>
        <span>θ₂ ${signedTheta(run.theta2)}</span>
        ${run.kind === "response" ? `<span>Panel ${formatMetric(run.panelAIn || 6, 3)} × ${formatMetric(run.panelBIn || 4, 3)} in</span>` : ""}
        <span>${run.predictedType ? `Type ${run.predictedType}` : "Type -"}</span>
        <span>${percent(run.confidence)}</span>
        <span>Pt ${formatMetric(run.predictedPt, 2)}</span>
      </div>
    `;
    button.addEventListener("click", () => {
      if (!historyDeleteMode) {
        applyPredictionHistoryRun(run);
        return;
      }
      if (selectedHistorySignatures.has(signature)) {
        selectedHistorySignatures.delete(signature);
      } else {
        selectedHistorySignatures.add(signature);
      }
      renderPredictionHistory();
    });
    list.appendChild(button);
  });

  predictionHistory.append(head, list);
}

function formatThetaInputValue(value) {
  return String(clampStackAngle(value));
}

function setupThetaSliders(form) {
  if (!form) {
    return;
  }

  ["theta1", "theta2"].forEach((thetaName) => {
    const numberInput = form.querySelector(`input[name="${thetaName}"][type="number"]`);
    const rangeInput = form.querySelector(`[data-theta-range="${thetaName}"]`);
    const readout = form.querySelector(`[data-theta-readout="${thetaName}"]`);

    if (!numberInput || !rangeInput) {
      return;
    }

    const paintRange = (value) => {
      const progress = ((clampStackAngle(value) + 90) / 180) * 100;
      rangeInput.style.setProperty("--angle-progress", `${progress}%`);
    };

    const sync = (source) => {
      const rawValue = String(source.value).trim();
      if (source === numberInput && ["", "-", "+", ".", "-.", "+."].includes(rawValue)) {
        if (readout) {
          readout.textContent = "—";
        }
        return;
      }
      const nextValue = formatThetaInputValue(source.value);
      numberInput.value = nextValue;
      rangeInput.value = nextValue;
      paintRange(nextValue);
      if (readout) {
        readout.textContent = formatThetaReadout(nextValue);
      }
      updateDynamicStackPreview();
    };

    numberInput.addEventListener("input", () => sync(numberInput));
    numberInput.addEventListener("change", () => sync(numberInput));
    rangeInput.addEventListener("input", () => sync(rangeInput));
    rangeInput.addEventListener("change", () => sync(rangeInput));
    sync(numberInput);
  });
}

function stackAnglePair(angle, family) {
  return [
    { angle, family },
    { angle: -angle, family },
  ];
}

function stackInversePair(angle, family) {
  return [
    { angle: -angle, family },
    { angle, family },
  ];
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

function parsePlySequence(text) {
  return String(text || "")
    .replace(/[()[\]{}]/g, " ")
    .split(/[,\s/]+/)
    .map((value) => Number(value.trim()))
    .filter((value) => Number.isFinite(value));
}

function normalizeStackFormula(formula) {
  const subscriptDigits = {
    "₀": "0",
    "₁": "1",
    "₂": "2",
    "₃": "3",
    "₄": "4",
    "₅": "5",
    "₆": "6",
    "₇": "7",
    "₈": "8",
    "₉": "9",
  };
  let text = String(formula || "")
    .replace(/[₀₁₂₃₄₅₆₇₈₉]/g, (digit) => subscriptDigits[digit] || digit)
    .replace(/[θΘ]/g, "theta")
    .replace(/theta\s*[_-]?\s*1/gi, "theta1")
    .replace(/theta\s*[_-]?\s*2/gi, "theta2")
    .replace(/\+\/-/g, "±")
    .replace(/-\/\+/g, "∓")
    .replace(/[×✕]/g, "x");
  const colon = text.indexOf(":");
  if (colon >= 0 && /(?:theta[12]|±|∓)/i.test(text.slice(colon + 1))) {
    text = text.slice(colon + 1);
  }
  return text;
}

function parseStackFormula(formula, theta1, theta2) {
  const source = normalizeStackFormula(formula);
  if (!/(?:theta[12]|±|∓)/i.test(source)) {
    return [];
  }

  let index = 0;
  const matching = { "[": "]", "(": ")", "{": "}" };

  function skipSeparators() {
    while (index < source.length && /[\s,;/]+/.test(source[index])) {
      index += 1;
    }
  }

  function readRepeat() {
    skipSeparators();
    if (source[index] === "_" || source[index] === "^") {
      index += 1;
      skipSeparators();
    } else if (source[index]?.toLowerCase() === "x") {
      index += 1;
      skipSeparators();
    }
    const match = source.slice(index).match(/^\d+/);
    if (!match) {
      return 1;
    }
    index += match[0].length;
    return Math.max(1, Math.min(64, Number(match[0])));
  }

  function readPlyToken() {
    const match = source.slice(index).match(/^(±|∓|\+|-)?\s*theta([12])/i);
    if (!match) {
      return null;
    }
    index += match[0].length;
    const value = match[2] === "1" ? theta1 : theta2;
    const sign = match[1] || "";
    if (sign === "±") {
      return [value, -value];
    }
    if (sign === "∓") {
      return [-value, value];
    }
    if (sign === "-") {
      return [-value];
    }
    return [value];
  }

  function readSequence(stopChar = "") {
    const sequence = [];
    while (index < source.length) {
      skipSeparators();
      if (stopChar && source[index] === stopChar) {
        index += 1;
        break;
      }

      const char = source[index];
      if (matching[char]) {
        index += 1;
        const group = readSequence(matching[char]);
        const repeat = readRepeat();
        sequence.push(...repeatStackPattern(group.map((angle) => ({ angle })), repeat).map((ply) => ply.angle));
        continue;
      }

      const token = readPlyToken();
      if (token) {
        const repeat = readRepeat();
        sequence.push(...repeatStackPattern(token.map((angle) => ({ angle })), repeat).map((ply) => ply.angle));
        continue;
      }

      index += 1;
    }
    return sequence;
  }

  return readSequence().filter((value) => Number.isFinite(value));
}

function formatPlySequence(sequence) {
  return sequence.map((value) => formatMetric(value, 1).replace(/\.0$/, "")).join(",");
}

function stackSequenceFromFormulaOrManual(formData, theta1, theta2) {
  const fromFormula = parseStackFormula(formData.get("formula"), theta1, theta2);
  if (fromFormula.length) {
    return { sequence: fromFormula, generated: true };
  }
  return { sequence: parsePlySequence(formData.get("ply_sequence")), generated: false };
}

function insertFormulaToken(form, token) {
  const input = form?.querySelector('textarea[name="formula"]');
  if (!input) {
    return;
  }
  const start = input.selectionStart ?? input.value.length;
  const end = input.selectionEnd ?? input.value.length;
  input.value = `${input.value.slice(0, start)}${token}${input.value.slice(end)}`;
  const nextPosition = start + token.length;
  input.focus();
  input.setSelectionRange(nextPosition, nextPosition);
  input.dispatchEvent(new Event("input", { bubbles: true }));
}

function attachFormulaToolbar(form) {
  if (!form) {
    return;
  }
  form.querySelectorAll("[data-formula-token]").forEach((button) => {
    button.addEventListener("click", () => {
      insertFormulaToken(form, button.dataset.formulaToken || "");
    });
  });
}

function sequenceToStackPlies(sequence, theta1, theta2) {
  return sequence.map((angle) => {
    const theta1Distance = Math.abs(Math.abs(angle) - Math.abs(theta1));
    const theta2Distance = Math.abs(Math.abs(angle) - Math.abs(theta2));
    return {
      angle,
      family: theta2Distance < theta1Distance ? "theta2" : "theta1",
    };
  });
}

function customStackSequenceFromForm(form) {
  const formData = new FormData(form);
  const theta1 = clampStackAngle(formData.get("theta1"));
  const theta2 = clampStackAngle(formData.get("theta2"));
  const { sequence, generated } = stackSequenceFromFormulaOrManual(formData, theta1, theta2);
  if (generated) {
    const sequenceInput = form.querySelector('textarea[name="ply_sequence"]');
    if (sequenceInput && sequenceInput.value !== formatPlySequence(sequence)) {
      sequenceInput.value = formatPlySequence(sequence);
    }
  }
  return {
    caseName: String(formData.get("case") || "Case5"),
    formula: String(formData.get("formula") || "").trim(),
    theta1,
    theta2,
    rawSequence: sequence,
    sequence: sequenceToStackPlies(sequence, theta1, theta2),
  };
}

function renderStackPly(ply, index, uid) {
  const palette = STACK_COLORS[ply.family];
  const x = 555 - index * 30;
  const y = 470 - index * 28;
  const labelFill = ply.angle >= 0 ? "#087443" : "#b42318";
  const topPoints = "0,130 138,210 420,52 282,-28";
  const sideLeft = "0,130 138,210 138,230 0,150";
  const sideRight = "138,210 420,52 420,72 138,230";
  const labelX = 426;
  const labelY = 36;

  return `
    <g transform="translate(${x} ${y})">
      <defs>
        <pattern id="${uid}-ply-hatch-${index}" width="24" height="24" patternUnits="userSpaceOnUse" patternTransform="rotate(${-ply.angle})">
          <path d="M-6 12 H30" stroke="${labelFill}" stroke-width="3" stroke-linecap="round" opacity="0.82" />
        </pattern>
      </defs>
      <polygon points="${sideLeft}" fill="${palette.sideA}" />
      <polygon points="${sideRight}" fill="${palette.sideB}" />
      <polygon points="${topPoints}" fill="url(#${uid}-top-${ply.family})" stroke="${palette.edge}" stroke-width="1.4" />
      <polygon points="${topPoints}" fill="url(#${uid}-ply-hatch-${index})" opacity="0.88" />
      <polygon points="${topPoints}" fill="transparent" stroke="rgba(255,255,255,0.64)" stroke-width="1" />
      <line x1="400" y1="61" x2="${labelX}" y2="${labelY + 15}" stroke="#f4ff17" stroke-width="2.2" opacity="0.92" />
      <rect x="${labelX}" y="${labelY}" width="126" height="34" rx="7" fill="#102033" opacity="0.96" stroke="#f4ff17" stroke-width="1.8" />
      <text x="${labelX + 11}" y="${labelY + 24}" fill="#f4ff17" font-size="22" font-weight="950">Ply-${index + 1}</text>
      <text x="12" y="143" fill="#ffffff" font-size="12" font-weight="900">P${index + 1}</text>
    </g>
  `;
}

function renderStackSvg(sequence, uid = "app-stack") {
  const safeUid = uid.replace(/[^a-zA-Z0-9_-]/g, "-");
  const plies = sequence.map((ply, index) => renderStackPly(ply, index, safeUid)).join("");
  return `
    <svg viewBox="0 0 1160 760" role="img" aria-label="Angle-aware Double-Double laminate ply stack">
      <defs>
        <linearGradient id="${safeUid}-bg-plane" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0" stop-color="#1c334e" />
          <stop offset="0.56" stop-color="#2f4966" />
          <stop offset="1" stop-color="#8998a8" />
        </linearGradient>
        <linearGradient id="${safeUid}-top-theta1" x1="0" x2="1">
          <stop offset="0" stop-color="${STACK_COLORS.theta1.topA}" />
          <stop offset="1" stop-color="${STACK_COLORS.theta1.topB}" />
        </linearGradient>
        <linearGradient id="${safeUid}-top-theta2" x1="0" x2="1">
          <stop offset="0" stop-color="${STACK_COLORS.theta2.topA}" />
          <stop offset="1" stop-color="${STACK_COLORS.theta2.topB}" />
        </linearGradient>
        <filter id="${safeUid}-stack-shadow" x="-20%" y="-20%" width="140%" height="150%">
          <feDropShadow dx="0" dy="14" stdDeviation="14" flood-color="#081426" flood-opacity="0.22" />
        </filter>
      </defs>

      <rect x="34" y="34" width="1092" height="700" rx="8" fill="url(#${safeUid}-bg-plane)" />
      <g opacity="0.22" stroke="#edf7ff" stroke-width="1">
        <path d="M118 42 L992 524" />
        <path d="M70 94 L944 576" />
        <path d="M22 146 L896 628" />
        <path d="M214 660 L1088 178" />
        <path d="M48 536 L742 150" />
        <path d="M122 578 L816 192" />
        <path d="M196 620 L890 234" />
        <path d="M270 662 L964 276" />
      </g>

      <g filter="url(#${safeUid}-stack-shadow)" opacity="0.96">
        <polygon points="98,456 574,704 1018,458 542,210" fill="#b9977f" />
        <polygon points="98,456 574,704 574,728 98,480" fill="#c8a78e" />
        <polygon points="574,704 1018,458 1018,482 574,728" fill="#98765f" />
        <path d="M138 468 L574 706 L976 482" fill="none" stroke="#ead3c2" stroke-width="2" opacity="0.44" />
      </g>

      <g filter="url(#${safeUid}-stack-shadow)">
        ${plies}
      </g>
    </svg>
  `;
}

function activeStackForm() {
  const mode = document.querySelector(".mode-button.active")?.dataset.mode;
  if (mode === "stack" && stackPreviewForm) {
    return stackPreviewForm;
  }
  if (mode === "u3" && u3PtForm) {
    return u3PtForm;
  }
  return responseForm;
}

function readStackState() {
  const form = activeStackForm();
  if (form === stackPreviewForm) {
    return customStackSequenceFromForm(form);
  }
  const formData = new FormData(form);
  return {
    caseName: String(formData.get("case") || "Case2"),
    theta1: clampStackAngle(formData.get("theta1")),
    theta2: clampStackAngle(formData.get("theta2")),
  };
}

function updateDynamicStackPreview() {
  if (!dynamicStackVisuals.length) {
    return;
  }
  const stackState = readStackState();
  const sequence = stackState.sequence || buildStackSequence(stackState);
  dynamicStackVisuals.forEach((visual, index) => {
    visual.innerHTML = renderStackSvg(sequence, `app-stack-${index}`);
  });
  if (dynamicStackFormula) {
    dynamicStackFormula.textContent = stackState.formula || STACK_FORMULAS[stackState.caseName] || STACK_FORMULAS.Case2;
  }
  if (dynamicStackCount) {
    dynamicStackCount.textContent = String(sequence.length);
  }
}

function attachDynamicStackPreview(form) {
  if (!form) {
    return;
  }
  form.querySelectorAll('input[name="theta1"], input[name="theta2"], select[name="case"], textarea[name="formula"], textarea[name="ply_sequence"]').forEach((control) => {
    control.addEventListener("input", updateDynamicStackPreview);
    control.addEventListener("change", updateDynamicStackPreview);
  });
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
  button.textContent = loading ? TEXT.predicting : button.dataset.defaultText;
}

function fillModelSelect(select, models) {
  if (!select) {
    return;
  }
  select.innerHTML = "";
  models.forEach((model) => {
    const option = document.createElement("option");
    option.value = model.key;
    const label = displayModelLabel(model.label);
    option.textContent = model.available ? label : `${label} (${IS_KO ? "없음" : "missing"})`;
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
    fillModelSelect(responseModel, primaryModels(data.response_models, PRIMARY_RESPONSE_MODEL_KEYS));
    fillModelSelect(u3PtModel, data.u3_pt_models || []);
    apiStatus.textContent = TEXT.apiConnected;
    apiStatus.classList.add("ok");
  } catch (error) {
    apiStatus.textContent = TEXT.apiOffline;
    apiStatus.classList.add("bad");
    setError(TEXT.apiStart);
  }
}

function renderProbabilities(probabilities) {
  probabilityBars.innerHTML = "";
  if (!probabilities) {
    probabilityBars.textContent = TEXT.noProbability;
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

function uncertaintyLabelText(label) {
  if (label === "high") return TEXT.reliabilityHigh;
  if (label === "medium") return TEXT.reliabilityMedium;
  return TEXT.reliabilityLow;
}

function interpolationLabelText(label) {
  if (label === "interpolation") return TEXT.interpolation;
  if (label === "near-edge") return TEXT.nearEdge;
  return TEXT.extrapolation;
}

function renderUncertainty(uncertainty) {
  if (!uncertaintyPanel || !uncertaintyLabel || !uncertaintyGrid || !uncertaintyNotes) {
    return;
  }
  if (!uncertainty) {
    uncertaintyPanel.classList.add("hidden");
    uncertaintyPanel.classList.remove("high", "medium", "low");
    uncertaintyGrid.innerHTML = "";
    uncertaintyNotes.innerHTML = "";
    return;
  }

  const confidenceLabel = uncertainty.confidence_label || "low";
  uncertaintyPanel.classList.remove("hidden", "high", "medium", "low");
  uncertaintyPanel.classList.add(confidenceLabel);
  uncertaintyLabel.textContent = uncertaintyLabelText(confidenceLabel);
  const ptLow = uncertainty.pt_interval_low;
  const ptHigh = uncertainty.pt_interval_high;
  const ptRange = ptLow != null && ptHigh != null
    ? `${formatMetric(ptLow, 0)} - ${formatMetric(ptHigh, 0)}`
    : "-";
  const cards = [
    [TEXT.reliabilityScore, percent(uncertainty.reliability_score)],
    [TEXT.ptRange, ptRange],
    [TEXT.designCoverage, interpolationLabelText(uncertainty.interpolation_label)],
    [TEXT.typeAgreement, uncertainty.type_consistency != null ? percent(uncertainty.type_consistency) : "-"],
  ];
  uncertaintyGrid.innerHTML = "";
  cards.forEach(([label, value]) => {
    const card = document.createElement("div");
    card.className = "uncertainty-card";
    const labelEl = document.createElement("span");
    labelEl.textContent = label;
    const valueEl = document.createElement("strong");
    valueEl.textContent = value;
    card.append(labelEl, valueEl);
    uncertaintyGrid.appendChild(card);
  });

  uncertaintyNotes.innerHTML = "";
  (uncertainty.notes || []).slice(0, 3).forEach((note) => {
    const item = document.createElement("li");
    item.textContent = IS_KO ? translateUncertaintyNote(note) : note;
    uncertaintyNotes.appendChild(item);
  });
}

function agreementLabelText(label) {
  if (label === "high") return TEXT.reliabilityHigh;
  if (label === "medium") return TEXT.reliabilityMedium;
  return TEXT.reliabilityLow;
}

function translateTeacherStudentNote(note) {
  const labels = {
    "Teacher is the deployment Tree model; Student is the distilled Hybrid neural model.":
      "Teacher는 배포 기본 Tree 모델이고, Student는 distillation 기반 Hybrid 신경망 모델입니다.",
    "Agreement compares Type, Pt, max force, and response-curve shape for the same theta/case input.":
      "같은 θ/Case 입력에 대해 Type, Pt, 최대 하중, 응답 곡선 형태가 얼마나 일치하는지 비교합니다.",
    "Tree and Student disagree on Type, so validate this candidate before treating the classification as stable.":
      "Tree와 Student의 Type 예측이 달라서, 이 후보는 안정적인 분류로 보기 전에 추가 검증이 필요합니다.",
    "Type agrees, but Pt differs by more than 8%; treat the Pt estimate as a screening value.":
      "Type은 일치하지만 Pt 차이가 8%를 넘어, Pt 값은 screening 용도로 해석하는 것이 좋습니다.",
    "Tree and Student are locally consistent, which supports using this result as an early screening candidate.":
      "Tree와 Student가 현재 입력 주변에서 일관된 결과를 보여, 초기 screening 후보로 활용하기에 비교적 안정적입니다.",
    "Teacher/Student agreement is included as a deployment consistency check, not as a replacement for simulation validation.":
      "Teacher/Student 일치도는 배포용 일관성 체크이며, 최종 해석 검증을 대체하지는 않습니다.",
  };
  return labels[note] || note;
}

function renderTeacherStudentAgreement(agreement) {
  if (!teacherStudentPanel || !teacherStudentLabel || !teacherStudentGrid || !teacherStudentNotes) {
    return;
  }
  if (!agreement) {
    teacherStudentPanel.classList.add("hidden");
    teacherStudentPanel.classList.remove("high", "medium", "low");
    teacherStudentGrid.innerHTML = "";
    teacherStudentNotes.innerHTML = "";
    return;
  }

  const confidenceLabel = agreement.confidence_label || "low";
  teacherStudentPanel.classList.remove("hidden", "high", "medium", "low");
  teacherStudentPanel.classList.add(confidenceLabel);
  if (teacherStudentTitle) {
    teacherStudentTitle.textContent = TEXT.teacherStudentTitle;
  }
  teacherStudentLabel.textContent = agreementLabelText(confidenceLabel);

  const typeText = agreement.type_agreement
    ? `${TEXT.teacherStudentMatch} · Type ${agreement.teacher?.predicted_type ?? "-"}`
    : `${TEXT.teacherStudentMismatch} · T${agreement.teacher?.predicted_type ?? "-"} / S${agreement.student?.predicted_type ?? "-"}`;
  const curveText = agreement.curve_norm_rmse != null
    ? `${formatMetric(agreement.curve_norm_rmse * 100, 2)}%`
    : "-";
  const studentText = agreement.student
    ? `Type ${agreement.student.predicted_type}, Pt ${formatMetric(agreement.student.predicted_pt, 0)}`
    : "-";
  const cards = [
    [TEXT.teacherStudentAgreement, percent(agreement.agreement_score)],
    [TEXT.teacherStudentType, typeText],
    [TEXT.teacherStudentPtDelta, `${formatMetric(agreement.pt_delta, 0)} (${percent(agreement.pt_delta_percent)})`],
    [TEXT.teacherStudentCurveDelta, curveText],
    [TEXT.teacherStudentStudent, studentText],
  ];
  teacherStudentGrid.innerHTML = "";
  cards.forEach(([label, value]) => {
    const card = document.createElement("div");
    card.className = "uncertainty-card";
    const labelEl = document.createElement("span");
    labelEl.textContent = label;
    const valueEl = document.createElement("strong");
    valueEl.textContent = value;
    card.append(labelEl, valueEl);
    teacherStudentGrid.appendChild(card);
  });

  teacherStudentNotes.innerHTML = "";
  (agreement.notes || []).slice(0, 3).forEach((note) => {
    const item = document.createElement("li");
    item.textContent = IS_KO ? translateTeacherStudentNote(note) : note;
    teacherStudentNotes.appendChild(item);
  });
}

function translateUncertaintyNote(note) {
  const labels = {
    "Reliability combines model confidence, distance to nearby curated simulations, and local Type agreement.":
      "종합 신뢰도는 모델 확률, 가까운 curated 해석 데이터와의 거리, 주변 Type 일치도를 함께 반영합니다.",
    "Pt interval is a screening band from nearby Pt scatter, not a formal statistical confidence interval.":
      "Pt 범위는 주변 Pt 산포 기반의 screening band이며, 엄밀한 통계적 신뢰구간은 아닙니다.",
    "This theta/case input is far from nearby curated simulations; validate before treating the recommendation as stable.":
      "현재 θ/Case 입력은 가까운 curated 해석 데이터에서 멀어, 안정적인 추천으로 보기 전에 검증이 필요합니다.",
    "This theta/case input is close to the edge of the observed design space.":
      "현재 θ/Case 입력은 관측된 설계 공간의 경계에 가까운 편입니다.",
    "This theta/case input is within a well-covered region of the observed design space.":
      "현재 θ/Case 입력은 관측된 설계 공간 안에서 비교적 잘 커버된 영역에 있습니다.",
  };
  return labels[note] || note;
}

function renderResult(data) {
  latestPredictionData = data;
  document.body.classList.add("has-result");
  emptyState.classList.add("hidden");
  stackPreviewResult?.classList.add("hidden");
  resultPanel.classList.remove("hidden");
  resultPanel.classList.remove("type-1", "type-2", "type-3");
  resultPanel.classList.add(`type-${data.predicted_type}`);
  predictedType.textContent = `Type ${data.predicted_type}`;
  confidenceEl.textContent = percent(data.confidence);
  modelLabel.textContent = displayModelLabel(data.model_label);
  const inputLabels = {
    theta1: "θ₁",
    theta2: "θ₂",
    case: "Case",
  };
  const inputValueLabels = {
    Case2: "Case 2",
    Case3: "Case 3",
    Case4: "Case 4",
    Unknown: TEXT.unknown,
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
      valueEl.textContent = inputDisplayValue(key, value, inputValueLabels);

      item.append(label, valueEl);
      inputSummary.appendChild(item);
  });
  renderProbabilities(data.probabilities);
  renderUncertainty(data.uncertainty);
  renderTeacherStudentAgreement(data.teacher_student);
  responseEstimate.classList.add("hidden");
  xaiRequestSerial += 1;
  renderXai(null);
  renderResearchHidden();

  notes.innerHTML = "";
  data.notes.forEach((note) => {
    const item = document.createElement("li");
    item.textContent = IS_KO ? (NOTE_LABELS_KO[note] || note) : note;
    notes.appendChild(item);
  });
}

function curveBatchCsv(data) {
  const headers = [
    "filename",
    "test_id",
    "case",
    "theta1",
    "theta2",
    "pt",
    "predicted_type",
    "confidence",
    "type1",
    "type2",
    "type3",
    "status",
    "error",
  ];
  const rows = (data.results || []).map((row) => {
    const probabilities = row.probabilities || {};
    return [
      row.filename,
      row.test_id,
      row.case,
      row.theta1,
      row.theta2,
      row.pt,
      row.predicted_type ? `Type ${row.predicted_type}` : "",
      row.confidence ?? "",
      probabilities.type1 ?? "",
      probabilities.type2 ?? "",
      probabilities.type3 ?? "",
      row.status,
      row.error || "",
    ];
  });
  return [headers, ...rows]
    .map((items) => items.map((item) => `"${String(item ?? "").replace(/"/g, '""')}"`).join(","))
    .join("\n");
}

function downloadCurveBatchCsv(data) {
  const blob = new Blob(["\ufeff" + curveBatchCsv(data)], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `curve-batch-classification-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function renderCurveBatchResults(data, usedMetadata) {
  latestPredictionData = null;
  document.body.classList.remove("has-result");
  resultPanel.classList.add("hidden");
  responseEstimate.classList.add("hidden");
  emptyState.classList.remove("hidden");
  renderXai(null);
  renderResearchHidden();

  if (!curveBatchResults) {
    return;
  }
  curveBatchResults.innerHTML = "";
  curveBatchResults.classList.remove("hidden");

  const header = document.createElement("div");
  header.className = "batch-results-head";
  const title = document.createElement("div");
  const eyebrow = document.createElement("span");
  eyebrow.textContent = data.model_label || "-";
  const heading = document.createElement("strong");
  heading.textContent = TEXT.batchResults;
  const summary = document.createElement("p");
  summary.textContent = `${TEXT.batchSummary(data.ok_count, data.total_files)}${usedMetadata ? "" : ` · ${TEXT.batchMetadataHint}`}`;
  title.append(eyebrow, heading, summary);

  const download = document.createElement("button");
  download.type = "button";
  download.textContent = TEXT.batchDownload;
  download.addEventListener("click", () => downloadCurveBatchCsv(data));
  header.append(title, download);

  const tableWrap = document.createElement("div");
  tableWrap.className = "batch-table-wrap";
  const table = document.createElement("table");
  table.className = "batch-table";
  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  [
    "File",
    "Test ID",
    "Case",
    "θ₁",
    "θ₂",
    "Pt",
    "Type",
    "Confidence",
    "Status",
  ].forEach((label) => {
    const th = document.createElement("th");
    th.textContent = label;
    headRow.appendChild(th);
  });
  thead.appendChild(headRow);

  const tbody = document.createElement("tbody");
  (data.results || []).forEach((row) => {
    const tr = document.createElement("tr");
    if (row.status !== "ok") {
      tr.className = "batch-error-row";
    }
    [
      row.filename,
      row.test_id,
      row.case,
      row.theta1,
      row.theta2,
      Number(row.pt).toLocaleString(undefined, { maximumFractionDigits: 2 }),
      row.predicted_type ? `Type ${row.predicted_type}` : "-",
      row.confidence == null ? "-" : percent(row.confidence),
      row.status === "ok" ? "OK" : row.error || "Error",
    ].forEach((value) => {
      const td = document.createElement("td");
      td.textContent = String(value ?? "-");
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.append(thead, tbody);
  tableWrap.appendChild(table);
  curveBatchResults.append(header, tableWrap);
}

function clearResponseCurveCanvas() {
  if (!responseCurveCanvas) {
    return;
  }
  const ctx = responseCurveCanvas.getContext("2d");
  ctx.clearRect(0, 0, responseCurveCanvas.width, responseCurveCanvas.height);
}

function updateResponseCurveZoomControls() {
  const zoomPercent = `${Math.round(responseCurveView.scale * 100)}%`;
  if (responseCurveZoomLabel) {
    responseCurveZoomLabel.textContent = zoomPercent;
  }
  responseCurveZoomButtons.forEach((button) => {
    const action = button.dataset.curveZoom;
    button.disabled = (action === "out" || action === "reset")
      ? responseCurveView.scale <= RESPONSE_CURVE_MIN_ZOOM + 0.01
      : responseCurveView.scale >= RESPONSE_CURVE_MAX_ZOOM - 0.01;
  });
}

function resetResponseCurveView(redraw = false) {
  responseCurveView.scale = 1;
  responseCurveView.centerXNorm = 0.5;
  responseCurveView.centerYNorm = 0.5;
  responseCurveView.drag = null;
  if (redraw) {
    redrawResponseCurve();
  } else {
    updateResponseCurveZoomControls();
  }
}

function setResponseCurveSource(points, predictedPtValue, fitMode = "standard", backendFit = null) {
  responseCurveView.points = points;
  responseCurveView.predictedPtValue = predictedPtValue;
  responseCurveView.fitMode = fitMode;
  responseCurveView.backendFit = backendFit;
  resetResponseCurveView();
  drawResponseCurve(points, predictedPtValue, fitMode, backendFit);
}

function redrawResponseCurve() {
  if (!responseCurveView.points) {
    updateResponseCurveZoomControls();
    return;
  }
  drawResponseCurve(
    responseCurveView.points,
    responseCurveView.predictedPtValue,
    responseCurveView.fitMode,
    responseCurveView.backendFit,
  );
}

function responseCurvePointFromEvent(event) {
  if (!responseCurveCanvas) {
    return null;
  }
  const rect = responseCurveCanvas.getBoundingClientRect();
  return {
    x: ((event.clientX - rect.left) / Math.max(1, rect.width)) * responseCurveView.logicalWidth,
    y: ((event.clientY - rect.top) / Math.max(1, rect.height)) * responseCurveView.logicalHeight,
  };
}

function responseCurveDomainCenter(domain, axis) {
  const min = axis === "x" ? domain.baseMinX : domain.baseMinY;
  const span = axis === "x" ? domain.baseSpanX : domain.baseSpanY;
  const norm = axis === "x" ? responseCurveView.centerXNorm : responseCurveView.centerYNorm;
  return min + span * norm;
}

function setResponseCurveZoom(nextScale, anchor = null) {
  const previousDomain = responseCurveView.domain;
  const previousPlot = responseCurveView.plot;
  const previousScale = responseCurveView.scale;
  responseCurveView.scale = clampNumber(nextScale, RESPONSE_CURVE_MIN_ZOOM, RESPONSE_CURVE_MAX_ZOOM);

  if (anchor && previousDomain && previousPlot && responseCurveView.scale !== previousScale) {
    const plotX = clampNumber(anchor.x, previousPlot.left, previousPlot.right);
    const plotY = clampNumber(anchor.y, previousPlot.top, previousPlot.bottom);
    const xRatio = (plotX - previousPlot.left) / Math.max(1e-9, previousPlot.width);
    const yRatio = 1 - ((plotY - previousPlot.top) / Math.max(1e-9, previousPlot.height));
    const anchorDataX = previousDomain.visibleMinX + previousDomain.visibleSpanX * xRatio;
    const anchorDataY = previousDomain.visibleMinY + previousDomain.visibleSpanY * yRatio;
    const nextSpanX = previousDomain.baseSpanX / responseCurveView.scale;
    const nextSpanY = previousDomain.baseSpanY / responseCurveView.scale;
    const nextCenterX = anchorDataX + (0.5 - xRatio) * nextSpanX;
    const nextCenterY = anchorDataY + (0.5 - yRatio) * nextSpanY;
    responseCurveView.centerXNorm = clampNumber(
      (nextCenterX - previousDomain.baseMinX) / previousDomain.baseSpanX,
      0,
      1,
    );
    responseCurveView.centerYNorm = clampNumber(
      (nextCenterY - previousDomain.baseMinY) / previousDomain.baseSpanY,
      0,
      1,
    );
  }

  redrawResponseCurve();
}

function panResponseCurve(dx, dy) {
  const domain = responseCurveView.domain;
  const plot = responseCurveView.plot;
  if (!domain || !plot || responseCurveView.scale <= RESPONSE_CURVE_MIN_ZOOM + 0.01) {
    return;
  }
  const nextCenterX = responseCurveDomainCenter(domain, "x") - (dx / Math.max(1, plot.width)) * domain.visibleSpanX;
  const nextCenterY = responseCurveDomainCenter(domain, "y") + (dy / Math.max(1, plot.height)) * domain.visibleSpanY;
  responseCurveView.centerXNorm = clampNumber((nextCenterX - domain.baseMinX) / domain.baseSpanX, 0, 1);
  responseCurveView.centerYNorm = clampNumber((nextCenterY - domain.baseMinY) / domain.baseSpanY, 0, 1);
  redrawResponseCurve();
}

function installResponseCurveZoomControls() {
  if (!responseCurveCanvas) {
    return;
  }

  responseCurveZoomButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const action = button.dataset.curveZoom;
      if (action === "in") {
        setResponseCurveZoom(responseCurveView.scale * 1.35);
      } else if (action === "out") {
        setResponseCurveZoom(responseCurveView.scale / 1.35);
      } else {
        resetResponseCurveView(true);
      }
    });
  });

  responseCurveCanvas.addEventListener("wheel", (event) => {
    if (!responseCurveView.points) {
      return;
    }
    event.preventDefault();
    const factor = event.deltaY < 0 ? 1.15 : 1 / 1.15;
    setResponseCurveZoom(responseCurveView.scale * factor, responseCurvePointFromEvent(event));
  }, { passive: false });

  responseCurveCanvas.addEventListener("pointerdown", (event) => {
    if (!responseCurveView.points || responseCurveView.scale <= RESPONSE_CURVE_MIN_ZOOM + 0.01) {
      return;
    }
    responseCurveView.drag = responseCurvePointFromEvent(event);
    responseCurveCanvas.setPointerCapture(event.pointerId);
  });

  responseCurveCanvas.addEventListener("pointermove", (event) => {
    if (!responseCurveView.drag) {
      return;
    }
    const point = responseCurvePointFromEvent(event);
    if (!point) {
      return;
    }
    panResponseCurve(point.x - responseCurveView.drag.x, point.y - responseCurveView.drag.y);
    responseCurveView.drag = point;
  });

  ["pointerup", "pointercancel", "pointerleave"].forEach((eventName) => {
    responseCurveCanvas.addEventListener(eventName, () => {
      responseCurveView.drag = null;
    });
  });

  responseCurveCanvas.addEventListener("dblclick", () => resetResponseCurveView(true));
  window.addEventListener("resize", () => {
    window.clearTimeout(responseCurveResizeTimer);
    responseCurveResizeTimer = window.setTimeout(() => redrawResponseCurve(), 120);
  });
  updateResponseCurveZoomControls();
}

function updateResponseCurveLegend(mode = "standard") {
  if (!responseCurveLegend) {
    return;
  }
  const curveLabel = IS_KO ? "예측 곡선" : "Predicted curve";
  const fitLabel = IS_KO ? "선형 피팅" : "Linear fits";
  const predictedLabel = TEXT.predictedPtLabel;
  const fitIntersectionLabel = TEXT.fitIntersectionLabel;
  responseCurveLegend.innerHTML = mode === "u3"
    ? `
      <span><i class="legend-swatch curve"></i>${curveLabel}</span>
      <span><i class="legend-swatch guide"></i>${fitLabel}</span>
      <span><i class="legend-swatch pt"></i>${predictedLabel}</span>
      <span><i class="legend-swatch kink"></i>${fitIntersectionLabel}</span>
    `
    : `
      <span><i class="legend-swatch curve"></i>${curveLabel}</span>
      <span><i class="legend-swatch guide"></i>${fitLabel}</span>
      <span><i class="legend-swatch kink"></i>${predictedLabel}</span>
    `;
}

function resetPredictionState() {
  latestPredictionData = null;
  resetHistoryDeleteState();
  document.body.classList.remove("has-result");
  emptyState.classList.remove("hidden");
  resultPanel.classList.add("hidden");
  stackPreviewResult?.classList.add("hidden");
  resultPanel.classList.remove("type-1", "type-2", "type-3");
  responseEstimate.classList.add("hidden");
  predictedType.textContent = "-";
  confidenceEl.textContent = "-";
  modelLabel.textContent = "-";
  inputSummary.innerHTML = "";
  probabilityBars.innerHTML = "";
  renderUncertainty(null);
  notes.innerHTML = "";
  predictedPt.textContent = "-";
  predictedMaxDisplacement.textContent = "-";
  predictedMaxForce.textContent = "-";
  clearResponseCurveCanvas();
  xaiRequestSerial += 1;
  renderXai(null);
  renderResearchHidden();
  curveBatchResults?.classList.add("hidden");
  if (curveBatchResults) {
    curveBatchResults.innerHTML = "";
  }
  renderPredictionHistory();
}

function metricCard(label, value, suffix = "") {
  const item = document.createElement("div");
  const labelEl = document.createElement("span");
  const valueEl = document.createElement("strong");
  labelEl.textContent = label;
  valueEl.textContent = value === null || value === undefined || value === "" ? "-" : `${value}${suffix}`;
  item.append(labelEl, valueEl);
  return item;
}

function renderPhysicsMetric(label, value) {
  const item = document.createElement("div");
  item.className = "stack-physics-item";
  const name = document.createElement("span");
  const number = document.createElement("strong");
  name.textContent = label;
  number.textContent = Number.isFinite(Number(value)) ? formatMetric(Number(value), 4) : String(value ?? "-");
  item.append(name, number);
  return item;
}

function renderStackPreviewResult(data) {
  latestPredictionData = null;
  document.body.classList.add("has-result");
  emptyState.classList.add("hidden");
  resultPanel.classList.add("hidden");
  stackPreviewResult?.classList.remove("hidden");

  const physics = data.physics || {};
  const designSpace = data.design_space || {};
  if (stackPreviewTitle) {
    const label = data.case === "Custom" ? "Custom" : String(data.case || "Case5").replace("Case", "Case ");
    stackPreviewTitle.textContent = IS_KO ? `${label} 적층 물리값` : `${label} stack physics`;
  }

  if (stackPreviewMetrics) {
    stackPreviewMetrics.innerHTML = "";
    stackPreviewMetrics.append(
      metricCard(IS_KO ? "Ply 수" : "Plies", data.ply_count),
      metricCard(IS_KO ? "전체 두께" : "Total thickness", formatMetric(data.total_thickness_in, 4), " in"),
      metricCard(IS_KO ? "신뢰도" : "Reliability", percent(designSpace.reliability_score ?? 0)),
      metricCard(IS_KO ? "설계공간" : "Coverage", designSpace.interpolation_label || "-")
    );
  }

  if (stackPreviewSequence) {
    stackPreviewSequence.innerHTML = "";
    (data.ply_sequence || []).forEach((angle, index) => {
      const chip = document.createElement("span");
      chip.className = "stack-sequence-chip";
      chip.textContent = `P${index + 1} ${formatSignedAngle(angle)}`;
      stackPreviewSequence.appendChild(chip);
    });
  }

  if (stackPreviewPhysics) {
    const featured = [
      ["D11 bending stiffness", physics.d11],
      ["D22 bending stiffness", physics.d22],
      ["D66 twisting stiffness", physics.d66],
      ["D11/D22 ratio", physics.d11_d22_ratio],
      ["Bending anisotropy", physics.bending_anisotropy],
      ["A11 membrane stiffness", physics.a11],
      ["A22 membrane stiffness", physics.a22],
      ["Stack symmetry mismatch", physics.stack_symmetry_mismatch],
      ["Mean |θ|", physics.angle_abs_mean],
      ["|θ| spread", physics.angle_abs_std],
    ];
    stackPreviewPhysics.innerHTML = "";
    featured.forEach(([label, value]) => {
      stackPreviewPhysics.appendChild(renderPhysicsMetric(physicsLabel(label), value));
    });
  }

  if (stackPreviewNotes) {
    stackPreviewNotes.innerHTML = "";
    [
      ...(data.notes || []),
      ...(designSpace.notes || []),
      IS_KO
        ? "이 탭은 새 적층식을 학습 모델에 넣기 전 물리 feature와 설계공간 위치를 확인하는 실험용 preview입니다."
        : "This tab previews physics descriptors and design-space position before the new stack is added to trained forecast models.",
    ].forEach((note) => {
      const item = document.createElement("li");
      item.textContent = IS_KO ? (NOTE_LABELS_KO[note] || note) : note;
      stackPreviewNotes.appendChild(item);
    });
  }
}

function xaiCategoryLabel(category) {
  const labels = {
    angle: IS_KO ? "각도" : "Angle",
    stiffness: IS_KO ? "강성" : "Stiffness",
    coupling: IS_KO ? "커플링" : "Coupling",
    case: "Case",
    curve: IS_KO ? "곡선" : "Curve",
    other: IS_KO ? "기타" : "Other",
  };
  return labels[category] || labels.other;
}

function xaiImportancePercent(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "-";
  }
  return `${(numeric * 100).toLocaleString(undefined, { maximumFractionDigits: 1 })}%`;
}

function localizeXaiText(text) {
  if (!IS_KO || !text) {
    return text || "";
  }
  const map = {
    "Why this prediction?": "왜 이런 예측이 나왔나요?",
    "This explanation uses the PPT-based physics-feature model. It combines θ₁, θ₂, Case, CLT ABD stiffness terms, membrane-bending coupling, and laminate anisotropy descriptors.":
      "PPT 기반 물리 feature 모델의 설명입니다. θ₁, θ₂, Case에 CLT ABD 강성, membrane-bending coupling, 적층 anisotropy descriptor를 함께 사용합니다.",
    "This explanation uses the Tree + Physics XAI model. It combines θ₁, θ₂, Case, CLT ABD stiffness terms, membrane-bending coupling, and laminate anisotropy descriptors.":
      "Tree + Physics XAI 모델의 설명입니다. θ₁, θ₂, Case에 CLT ABD 강성, membrane-bending coupling, 적층 anisotropy descriptor를 함께 사용합니다.",
    "This explanation uses the GointMLP + Physics XAI model. It masks one physics feature at a time and measures how much the neural Pt, max-value, and curve heads move.":
      "GointMLP + Physics XAI 모델의 설명입니다. 물리 feature를 하나씩 가리고 neural Pt, max value, curve head가 얼마나 움직이는지 측정합니다.",
    "This explanation uses the Laminate Forecast Tree + Physics XAI model. It combines θ₁, θ₂, Case, CLT ABD stiffness terms, membrane-bending coupling, and laminate anisotropy descriptors.":
      "Laminate Forecast Tree + Physics XAI 모델의 설명입니다. θ₁, θ₂, Case에 CLT ABD 강성, membrane-bending coupling, 적층 anisotropy descriptor를 함께 사용합니다.",
    "This explanation uses the Laminate Forecast GointMLP + Physics XAI model. It masks one physics feature at a time and measures how much the neural Type, Pt, max-value, and curve heads move.":
      "Laminate Forecast GointMLP + Physics XAI 모델의 설명입니다. 물리 feature를 하나씩 가리고 neural Type, Pt, max value, curve head가 얼마나 움직이는지 측정합니다.",
    "This explanation uses the Laminate Forecast Machine Learning model. It keeps the strongest θ, Case, CLT stiffness, coupling, anisotropy, and stack-shape features.":
      "Laminate Forecast Machine Learning 모델의 설명입니다. θ, Case, CLT 강성, coupling, anisotropy, 적층 형상 feature 중 영향이 큰 항목을 사용합니다.",
    "This explanation uses the Laminate Forecast Machine Learning model. It keeps the strongest θ, Case, CLT stiffness, coupling, anisotropy, and stack-shape features with ABD terms normalized as A/h, 2B/h², and 12D/h³.":
      "Laminate Forecast Machine Learning 모델의 설명입니다. θ, Case, CLT 강성, coupling, anisotropy, 적층 형상 feature 중 영향이 큰 항목을 사용하며, ABD 항은 A/h, 2B/h², 12D/h³ 기준으로 정규화했습니다.",
    "This explanation uses the Laminate Forecast Machine Learning model. It keeps the strongest θ, Case, normalized CLT stiffness, coupling, anisotropy, and stack-shape features.":
      "Laminate Forecast Machine Learning 모델의 설명입니다. θ, Case, 정규화된 CLT 강성, coupling, anisotropy, 적층 형상 feature 중 영향이 큰 항목을 사용합니다.",
    "This explanation uses the Laminate Forecast Deep Learning model. It keeps physics descriptors and selected basis terms that improved the neural multi-task surrogate.":
      "Laminate Forecast Deep Learning 모델의 설명입니다. neural multi-task surrogate에 도움이 된 물리 descriptor와 선택된 basis 항목을 사용합니다.",
    "This explanation uses the Laminate Forecast Deep Learning model. It masks one physics feature at a time for the current θ/Case input.":
      "Laminate Forecast Deep Learning 모델의 설명입니다. 현재 θ/Case 입력에서 물리 feature를 하나씩 가려 민감도를 확인합니다.",
    "This explanation uses the u3 Forecast Machine Learning model. It keeps θ periodicity, CLT stiffness, coupling, anisotropy, and stack-shape features.":
      "u3 Forecast Machine Learning 모델의 설명입니다. θ 주기성, CLT 강성, coupling, anisotropy, 적층 형상 feature를 사용합니다.",
    "This explanation uses the u3 Forecast Machine Learning model. It keeps θ periodicity, normalized CLT stiffness, coupling, anisotropy, and stack-shape features.":
      "u3 Forecast Machine Learning 모델의 설명입니다. θ 주기성, 정규화된 CLT 강성, coupling, anisotropy, 적층 형상 feature를 사용합니다.",
    "This explanation uses the u3 Forecast Deep Learning model. It masks one physics feature at a time and measures how much the neural Pt, max-value, and curve heads move for the current θ/Case input.":
      "u3 Forecast Deep Learning 모델의 설명입니다. 현재 θ/Case 입력에서 물리 feature를 하나씩 가리고 neural Pt, max value, curve head 변화량을 측정합니다.",
    "This explanation uses the GointMLP theta/case model. It masks one theta feature at a time and measures how much the neural Pt, max-value, and curve heads move.":
      "GointMLP θ/Case 모델의 설명입니다. θ feature를 하나씩 가리고 neural Pt, max value, curve head가 얼마나 움직이는지 측정합니다.",
    "This explanation uses the original theta/case model. It mainly shows angle periodicity and case effects, not full laminate physics.":
      "기존 θ/Case 모델의 설명입니다. 전체 적층 물리보다는 각도 주기성과 Case 효과를 주로 보여줍니다.",
    "This explanation uses the original Tree theta/case model. It mainly shows angle periodicity and case effects, not full laminate physics.":
      "기존 Tree θ/Case 모델의 설명입니다. 전체 적층 물리보다는 각도 주기성과 Case 효과를 주로 보여줍니다.",
    "Tree ensemble feature importance + local finite-difference sensitivity":
      "Tree ensemble feature importance + local finite-difference sensitivity",
    "GointMLP occlusion sensitivity + local finite-difference sensitivity":
      "GointMLP occlusion sensitivity + local finite-difference sensitivity",
    "Tree ensemble feature importance + local finite-difference sensitivity · live local feature masking":
      "Tree ensemble feature importance + 입력별 live feature masking",
    "GointMLP occlusion sensitivity + local finite-difference sensitivity · live local feature masking":
      "GointMLP occlusion sensitivity + 입력별 live feature masking",
    "Feature importance is global: it summarizes the trained model, not only this single input.":
      "Feature importance는 global 설명입니다. 현재 입력 하나만이 아니라 학습된 모델 전체의 경향을 요약합니다.",
    "Feature importance is local: values are recomputed for this theta/case input by masking one feature at a time.":
      "Feature importance는 local 설명입니다. 현재 θ/Case 입력에서 feature를 하나씩 가려 다시 계산한 값입니다.",
    "A small global prior is blended in to keep known model-level drivers visible.":
      "모델 전체에서 알려진 주요 driver도 보이도록 작은 global prior를 함께 섞었습니다.",
    "Feature importance is global because live local masking was unavailable for this model response.":
      "이 모델 응답에서는 live local masking을 사용할 수 없어 global importance를 표시합니다.",
    "Use the explanation as engineering guidance; promising candidates still need simulation validation.":
      "설명은 엔지니어링 가이드로 활용하고, 유망한 후보는 해석으로 검증해 주세요.",
    "Minimum |θ|": "최소 |θ|",
    "Mean |θ|": "평균 |θ|",
    "Maximum |θ|": "최대 |θ|",
    "|θ| spread": "|θ| 분산",
    "|θ₁|": "|θ₁|",
    "|θ₂|": "|θ₂|",
    "|θ₁ - θ₂|": "|θ₁ - θ₂|",
    "θ₁ × θ₂": "θ₁ × θ₂",
    "cos(2θ₁)": "cos(2θ₁)",
    "cos(2θ₂)": "cos(2θ₂)",
    "sin(4θ₁)": "sin(4θ₁)",
    "sin(4θ₂)": "sin(4θ₂)",
    "cos(4θ₁)": "cos(4θ₁)",
    "cos(4θ₂)": "cos(4θ₂)",
    "Angle spread": "각도 간격",
    "D11 bending stiffness": "D11 굽힘 강성",
    "D22 bending stiffness": "D22 굽힘 강성",
    "D12 bending coupling": "D12 굽힘 커플링",
    "D66 twisting stiffness": "D66 비틀림 강성",
    "A11 membrane stiffness": "A11 막 강성",
    "A22 membrane stiffness": "A22 막 강성",
    "A12 membrane coupling": "A12 막 커플링",
    "A66 shear stiffness": "A66 전단 강성",
    "A16 extension-shear coupling": "A16 인장-전단 커플링",
    "A26 extension-shear coupling": "A26 인장-전단 커플링",
    "A11/A22 ratio": "A11/A22 비율",
    "D11/D22 ratio": "D11/D22 비율",
    "A66 geometry ratio": "A66 기하 비율",
    "Membrane anisotropy": "막 이방성",
    "Bending anisotropy": "굽힘 이방성",
    "Stack balance cosine": "적층 balance cosine",
    "Stack balance sine": "적층 balance sine",
    "Stack symmetry mismatch": "적층 대칭 불일치",
    "DD angle center": "DD 각도 중심",
    "Mean signed angle": "평균 부호 각도",
    "B11 membrane-bending coupling": "B11 막-굽힘 커플링",
    "B22 membrane-bending coupling": "B22 막-굽힘 커플링",
    "B12 membrane-bending coupling": "B12 막-굽힘 커플링",
    "B66 shear-bending coupling": "B66 전단-굽힘 커플링",
    "B16 bend-twist coupling": "B16 굽힘-비틀림 커플링",
    "B26 bend-twist coupling": "B26 굽힘-비틀림 커플링",
    "B11/D11 coupling ratio": "B11/D11 커플링 비율",
    "B22/D22 coupling ratio": "B22/D22 커플링 비율",
    "A-matrix coupling norm": "A 행렬 커플링 크기",
    "B-matrix coupling norm": "B 행렬 커플링 크기",
    "D-matrix coupling norm": "D 행렬 커플링 크기",
    "D16 bend-twist coupling": "D16 굽힘-비틀림 커플링",
    "D26 bend-twist coupling": "D26 굽힘-비틀림 커플링",
    "Ply count": "플라이 수",
    "Total thickness": "전체 두께",
    "Panel aspect ratio": "패널 종횡비",
    "Length slenderness": "길이 slenderness",
    "Width slenderness": "폭 slenderness",
    "Case pattern II": "Case pattern II",
    "Case 2 flag": "Case 2 표시자",
    "Case 3 flag": "Case 3 표시자",
    "Case 4 flag": "Case 4 표시자",
    "Smallest absolute ply-family angle. The PPT shows high-performing regions away from 0°/90°, so this captures whether either family is too close to an axial baseline.":
      "가장 작은 절대 적층 각도입니다. 0°/90° 축 방향에 너무 가까운 각도 조합인지 판단하는 데 도움이 됩니다.",
    "Average absolute angle across the expanded laminate stack; helps identify the ±45°-type region emphasized in the PPT.":
      "확장된 적층 구조의 평균 절대각입니다. PPT에서 강조된 ±45° 계열 영역을 파악하는 데 도움이 됩니다.",
    "Largest absolute ply-family angle; helps separate ±45°-type candidates from near-90° dominated stacks.":
      "가장 큰 절대 적층 각도입니다. ±45° 계열 후보와 90°에 가까운 적층을 구분하는 데 도움이 됩니다.",
    "Spread of absolute angles in the expanded laminate stack. It captures how strongly the two Double-Double angle families differ.":
      "확장된 적층 구조에서 절대각의 퍼짐입니다. 두 Double-Double 각도군이 얼마나 다른지 나타냅니다.",
    "Absolute value of θ₁. This captures how far the first angle family is from the axial 0° direction.":
      "θ₁의 절대값입니다. 첫 번째 각도군이 0° 축 방향에서 얼마나 벗어났는지 나타냅니다.",
    "Absolute value of θ₂. This captures how far the second angle family is from the axial 0° direction.":
      "θ₂의 절대값입니다. 두 번째 각도군이 0° 축 방향에서 얼마나 벗어났는지 나타냅니다.",
    "Absolute separation between the two Double-Double angle families.":
      "두 Double-Double 각도군 사이의 절대 간격입니다.",
    "Interaction feature between θ₁ and θ₂. It helps the model distinguish angle pairs with opposite or same signs.":
      "θ₁과 θ₂의 상호작용 feature입니다. 두 각도가 같은 부호인지 반대 부호인지 구분하는 데 도움이 됩니다.",
    "Periodic angle descriptor for θ₁, commonly useful for laminate stiffness terms that repeat with 180° symmetry.":
      "θ₁의 주기적 각도 descriptor입니다. 180° 대칭으로 반복되는 적층 강성 항을 표현하는 데 유용합니다.",
    "Periodic angle descriptor for θ₂, commonly useful for laminate stiffness terms that repeat with 180° symmetry.":
      "θ₂의 주기적 각도 descriptor입니다. 180° 대칭으로 반복되는 적층 강성 항을 표현하는 데 유용합니다.",
    "Higher-order periodic descriptor for θ₁. It helps represent angle effects that appear in transformed laminate stiffness.":
      "θ₁의 고차 주기 descriptor입니다. 변환된 적층 강성에서 나타나는 각도 효과를 표현합니다.",
    "Higher-order periodic descriptor for θ₂. It helps represent angle effects that appear in transformed laminate stiffness.":
      "θ₂의 고차 주기 descriptor입니다. 변환된 적층 강성에서 나타나는 각도 효과를 표현합니다.",
    "Higher-order periodic descriptor for θ₁. It is strongly related to transformed orthotropic stiffness variation with angle.":
      "θ₁의 고차 주기 descriptor입니다. 각도에 따른 직교이방성 강성 변화와 관련이 큽니다.",
    "Higher-order periodic descriptor for θ₂. It is strongly related to transformed orthotropic stiffness variation with angle.":
      "θ₂의 고차 주기 descriptor입니다. 각도에 따른 직교이방성 강성 변화와 관련이 큽니다.",
    "Longitudinal bending stiffness term from the laminate D matrix. It is directly related to bending resistance under the panel loading setup.":
      "적층 D 행렬의 길이 방향 굽힘 강성 항입니다. 패널 하중 조건에서 굽힘 저항과 직접 관련됩니다.",
    "Transverse bending stiffness term from the laminate D matrix.":
      "적층 D 행렬의 횡방향 굽힘 강성 항입니다.",
    "Bending coupling term from the D matrix; useful for distinguishing how the post-transition response bends after the knee point.":
      "D 행렬의 굽힘 커플링 항입니다. Pt 이후 응답이 어떻게 휘어지는지 구분하는 데 유용합니다.",
    "Twisting/shear bending stiffness. It often matters for buckling-like mode transitions and post-transition curve shape.":
      "비틀림/전단 굽힘 강성입니다. 좌굴 유사 모드 전환과 Pt 이후 곡선 형상에 영향을 줄 수 있습니다.",
    "Longitudinal membrane stiffness from the laminate A matrix.":
      "적층 A 행렬의 길이 방향 막 강성 항입니다.",
    "Transverse membrane stiffness from the laminate A matrix.":
      "적층 A 행렬의 횡방향 막 강성 항입니다.",
    "In-plane membrane coupling term from the laminate A matrix.":
      "적층 A 행렬의 평면 내 막 커플링 항입니다.",
    "In-plane shear stiffness from the laminate A matrix.":
      "적층 A 행렬의 평면 내 전단 강성 항입니다.",
    "A-matrix coupling between axial extension and in-plane shear. It reflects unbalanced angle effects in the laminate.":
      "축방향 인장과 평면 내 전단 사이의 A 행렬 커플링입니다. 적층각 불균형 효과를 반영합니다.",
    "A-matrix coupling between transverse extension and in-plane shear. It can indicate directional imbalance in the stack.":
      "횡방향 인장과 평면 내 전단 사이의 A 행렬 커플링입니다. 적층의 방향성 불균형을 나타낼 수 있습니다.",
    "Membrane anisotropy ratio. This tells whether the laminate is biased toward the load direction or transverse direction.":
      "막 강성 이방성 비율입니다. 적층판이 하중 방향 또는 횡방향 중 어디에 더 치우쳤는지 보여줍니다.",
    "Shear stiffness ratio normalized by the laminate membrane stiffness scale; useful for comparing shear contribution across angle pairs.":
      "막 강성 스케일로 정규화한 전단 강성 비율입니다. 각도 조합별 전단 기여를 비교하는 데 유용합니다.",
    "Bending anisotropy ratio. It helps explain case/type differences driven by flexural stiffness balance.":
      "굽힘 이방성 비율입니다. 굽힘 강성 균형에 의해 발생하는 Case/Type 차이를 설명하는 데 도움이 됩니다.",
    "Normalized difference between D11 and D22; a compact descriptor for direction-dependent bending behavior.":
      "D11과 D22의 정규화된 차이입니다. 방향별 굽힘 거동을 간단히 나타냅니다.",
    "Normalized difference between A11 and A22; a compact descriptor for direction-dependent membrane behavior.":
      "A11과 A22의 정규화된 차이입니다. 방향별 막 거동을 간단히 나타냅니다.",
    "A trigonometric balance descriptor over all plies; helps the model recognize balanced ±θ families.":
      "전체 플라이에 대한 삼각함수 기반 balance descriptor입니다. 모델이 balanced ±θ 계열을 인식하는 데 도움이 됩니다.",
    "Sine-based balance descriptor over all plies. Values near zero indicate stronger ±θ cancellation in the expanded stack.":
      "전체 플라이에 대한 sine 기반 balance descriptor입니다. 0에 가까울수록 확장 적층에서 ±θ 상쇄가 강하다는 뜻입니다.",
    "Distance-like descriptor for top/bottom ply-angle mismatch. Larger values suggest more membrane-bending coupling potential.":
      "상/하부 플라이 각도 불일치를 나타내는 거리형 descriptor입니다. 값이 클수록 막-굽힘 커플링 가능성이 커질 수 있습니다.",
    "Average center of the two Double-Double angle families.":
      "두 Double-Double 각도군의 평균 중심값입니다.",
    "Average signed angle across the expanded stack. It helps detect directional bias not visible from absolute angles alone.":
      "확장된 적층 구조의 평균 부호 각도입니다. 절대각만으로 보이지 않는 방향성 편향을 감지하는 데 도움이 됩니다.",
    "Membrane-bending coupling term in the load direction. Nonzero B terms indicate asymmetric coupling effects in the laminate response.":
      "하중 방향의 막-굽힘 커플링 항입니다. B 항이 0이 아니면 적층 응답에 비대칭 커플링 효과가 있음을 의미합니다.",
    "Transverse membrane-bending coupling term from the laminate B matrix.":
      "적층 B 행렬의 횡방향 막-굽힘 커플링 항입니다.",
    "Cross membrane-bending coupling term from the laminate B matrix.":
      "적층 B 행렬의 교차 막-굽힘 커플링 항입니다.",
    "Shear-related membrane-bending coupling term from the laminate B matrix.":
      "적층 B 행렬의 전단 관련 막-굽힘 커플링 항입니다.",
    "B-matrix coupling between load-direction bending and twisting/shear response.":
      "하중 방향 굽힘과 비틀림/전단 응답 사이의 B 행렬 커플링입니다.",
    "B-matrix coupling between transverse bending and twisting/shear response.":
      "횡방향 굽힘과 비틀림/전단 응답 사이의 B 행렬 커플링입니다.",
    "Load-direction membrane-bending coupling normalized by bending stiffness.":
      "하중 방향 membrane-bending coupling을 굽힘 강성으로 정규화한 값입니다.",
    "Transverse membrane-bending coupling normalized by transverse bending stiffness.":
      "횡방향 membrane-bending coupling을 횡방향 굽힘 강성으로 정규화한 값입니다.",
    "Combined magnitude of A16 and A26 extension-shear coupling terms.":
      "A16과 A26 인장-전단 커플링 항의 결합 크기입니다.",
    "Combined magnitude of B16 and B26 membrane-bending coupling terms.":
      "B16과 B26 막-굽힘 커플링 항의 결합 크기입니다.",
    "Combined magnitude of D16 and D26 bend-twist coupling terms.":
      "D16과 D26 굽힘-비틀림 커플링 항의 결합 크기입니다.",
    "D-matrix coupling between load-direction bending and twisting response.":
      "하중 방향 굽힘과 비틀림 응답 사이의 D 행렬 커플링입니다.",
    "D-matrix coupling between transverse bending and twisting response.":
      "횡방향 굽힘과 비틀림 응답 사이의 D 행렬 커플링입니다.",
    "Number of plies in the expanded laminate stack.":
      "확장된 적층 구조의 플라이 개수입니다.",
    "Total laminate thickness in inches based on the PPT ply thickness.":
      "PPT의 플라이 두께를 기준으로 계산한 전체 적층 두께(in)입니다.",
    "Panel length-to-width ratio from the PPT mechanics setup.":
      "PPT mechanics setup의 패널 길이/폭 비율입니다.",
    "Panel length divided by total laminate thickness.":
      "패널 길이를 전체 적층 두께로 나눈 값입니다.",
    "Panel width divided by total laminate thickness.":
      "패널 폭을 전체 적층 두께로 나눈 값입니다.",
    "Binary descriptor for the Case3-style Double-Double stack pattern.":
      "Case3 방식 Double-Double 적층 패턴을 나타내는 이진 descriptor입니다.",
    "One-hot indicator that the selected laminate structure is Case 2.":
      "선택한 적층 구조가 Case 2인지 나타내는 one-hot 표시자입니다.",
    "One-hot indicator that the selected laminate structure is Case 3.":
      "선택한 적층 구조가 Case 3인지 나타내는 one-hot 표시자입니다.",
    "One-hot indicator that the selected laminate structure is Case 4.":
      "선택한 적층 구조가 Case 4인지 나타내는 one-hot 표시자입니다.",
    "Feature importance is local: the strongest 12 global candidates are recomputed for this theta/case input by feature masking.":
      "Feature 중요도는 현재 θ/Case 입력에 맞춰 계산됩니다. global 기준 상위 12개 후보 feature를 feature masking으로 다시 평가합니다.",
    "Local sensitivity reports how much the model output changes when the current feature value is masked for this single input.":
      "Local sensitivity는 현재 입력에서 해당 feature 값을 가렸을 때 모델 출력이 얼마나 변하는지 나타냅니다.",
    "A small global prior is blended in to keep known model-level drivers visible.":
      "모델 전체에서 중요한 feature도 함께 보이도록 작은 global prior를 섞었습니다.",
    "Feature importance is global because live local masking was unavailable for this model response.":
      "이 모델 응답에서는 실시간 local masking을 사용할 수 없어 global feature 중요도를 표시합니다.",
  };
  return map[text] || text;
}

function localizeXaiFeatureSet(featureSet) {
  if (!IS_KO) {
    return featureSet;
  }
  const map = {
    "theta + case": "θ + Case",
    "theta + CLT physics": "θ + CLT 물리 feature",
  };
  return map[featureSet] || featureSet;
}

function localizeXaiPerturbation(text) {
  const normalized = String(text);
  const maskedMatch = normalized.match(/^masked to\s+(.+)$/i);
  if (maskedMatch) {
    const replacement = maskedMatch[1];
    return IS_KO ? `${replacement}으로 대체` : `replaced with ${replacement}`;
  }
  if (!IS_KO) {
    return normalized;
  }
  return normalized;
}

function renderXai(xai) {
  if (!xaiPanel) {
    return;
  }
  if (!xai) {
    xaiPanel.classList.add("hidden");
    return;
  }
  xaiPanel.classList.remove("hidden");
  xaiTitle.textContent = localizeXaiText(xai.title);
  xaiSummary.textContent = localizeXaiText(xai.summary);
  xaiMethod.textContent = `${IS_KO ? "방법" : "Method"}: ${localizeXaiText(xai.method)} · ${IS_KO ? "특징 세트" : "Feature set"}: ${localizeXaiFeatureSet(xai.feature_set)}`;
  xaiFeatures.innerHTML = "";
  const features = [...(xai.top_features || [])].sort(
    (left, right) => (Number(right.importance) || 0) - (Number(left.importance) || 0),
  );
  const maxImportance = Math.max(...features.map((feature) => Number(feature.importance) || 0), 1e-9);
  const visibleFeatures = features.slice(0, XAI_VISIBLE_LIMIT);
  const extraFeatures = features.slice(XAI_VISIBLE_LIMIT);
  visibleFeatures.forEach((feature) => {
    xaiFeatures.appendChild(createXaiFeatureItem(feature, maxImportance));
  });
  if (extraFeatures.length > 0) {
    const details = document.createElement("details");
    details.className = "xai-more";
    const summary = document.createElement("summary");
    summary.textContent = TEXT.xaiMore(extraFeatures.length);
    const list = document.createElement("div");
    list.className = "xai-more-list";
    extraFeatures.forEach((feature) => {
      list.appendChild(createXaiFeatureItem(feature, maxImportance));
    });
    details.append(summary, list);
    xaiFeatures.appendChild(details);
  }

  xaiNotes.innerHTML = "";
  (xai.notes || []).forEach((note) => {
    const item = document.createElement("li");
    item.textContent = localizeXaiText(note);
    xaiNotes.appendChild(item);
  });
}

function renderXaiLoading() {
  if (!xaiPanel) {
    return;
  }
  xaiPanel.classList.remove("hidden");
  xaiTitle.textContent = TEXT.xaiLoadingTitle;
  xaiSummary.textContent = TEXT.xaiLoadingSummary;
  xaiMethod.textContent = `${IS_KO ? "방법" : "Method"}: ${TEXT.xaiLoadingMethod}`;
  xaiFeatures.innerHTML = `<div class="xai-loading">${TEXT.xaiLoadingSummary}</div>`;
  xaiNotes.innerHTML = "";
}

function renderXaiLoadFailed() {
  if (!xaiPanel) {
    return;
  }
  xaiPanel.classList.remove("hidden");
  xaiTitle.textContent = "XAI";
  xaiSummary.textContent = TEXT.xaiLoadFailed;
  xaiMethod.textContent = "";
  xaiFeatures.innerHTML = "";
  xaiNotes.innerHTML = "";
}

async function requestLazyXai(data) {
  const inputs = data?.inputs || {};
  if (!data?.model_key || inputs.theta1 === undefined || inputs.theta2 === undefined || !inputs.case) {
    renderXai(null);
    return;
  }

  const serial = ++xaiRequestSerial;
  renderXaiLoading();
  try {
    const xai = await postJson("/xai/local", {
      theta1: Number(inputs.theta1),
      theta2: Number(inputs.theta2),
      case: inputs.case,
      model: data.model_key,
      panel_a_in: Number(inputs.panel_a_in || 6),
      panel_b_in: Number(inputs.panel_b_in || 4),
    });
    if (serial === xaiRequestSerial) {
      if (latestPredictionData) {
        latestPredictionData = { ...latestPredictionData, xai };
      }
      renderXai(xai);
    }
  } catch (error) {
    if (serial === xaiRequestSerial) {
      renderXaiLoadFailed();
    }
  }
}

function createXaiFeatureItem(feature, maxImportance) {
  const item = document.createElement("article");
  item.className = "xai-feature";
  item.title = localizeXaiText(feature.explanation || "");

  const main = document.createElement("div");
  main.className = "xai-feature-main";

  const head = document.createElement("div");
  head.className = "xai-feature-head";
  const title = document.createElement("strong");
  title.textContent = localizeXaiText(feature.label || feature.name);
  const category = document.createElement("span");
  category.textContent = xaiCategoryLabel(feature.category);
  head.append(title, category);

  const description = document.createElement("p");
  description.className = "xai-feature-description";
  description.textContent = localizeXaiText(feature.explanation || "");

  main.append(head, description);

  const detailParts = [];
  if (feature.local_value !== null && feature.local_value !== undefined) {
    detailParts.push(`${TEXT.xaiLocalValue}: ${formatCompactNumber(feature.local_value)}`);
  }
  if (feature.local_sensitivity !== null && feature.local_sensitivity !== undefined) {
    detailParts.push(`${TEXT.xaiLocalSensitivity}: ${formatCompactNumber(feature.local_sensitivity)}`);
  }
  if (feature.perturbation) {
    detailParts.push(`${TEXT.xaiPerturbation}: ${localizeXaiPerturbation(String(feature.perturbation))}`);
  }
  if (detailParts.length) {
    const localDetail = document.createElement("p");
    localDetail.className = "xai-feature-local";
    localDetail.textContent = detailParts.join(" · ");
    main.appendChild(localDetail);
  }

  const score = document.createElement("div");
  score.className = "xai-feature-score";
  const percentText = document.createElement("span");
  percentText.textContent = xaiImportancePercent(feature.importance);

  const bar = document.createElement("div");
  bar.className = "xai-bar";
  const fill = document.createElement("i");
  fill.style.width = `${Math.max(4, (Number(feature.importance) / maxImportance) * 100)}%`;
  bar.appendChild(fill);

  score.append(percentText, bar);
  item.append(main, score);
  return item;
}

function riskLabel(value) {
  const labels = {
    low: TEXT.riskLow,
    medium: TEXT.riskMedium,
    high: TEXT.riskHigh,
  };
  return labels[value] || value;
}

function typeLabel(typeValue) {
  return typeValue === null || typeValue === undefined ? "-" : `Type ${typeValue}`;
}

function localizeResearchText(text) {
  if (!IS_KO || !text) {
    return text || "";
  }
  const map = {
    "Laminate Forecast design-space context is based on the curated Case2/3/4 response dataset.":
      "Laminate Forecast 설계 공간은 정리된 Case2/3/4 응답 데이터셋을 기준으로 계산했습니다.",
    "Risk combines nonlinear Type 2/3 prevalence and below-median Pt prevalence within each Case.":
      "위험도는 각 Case 안에서 비선형 Type 2/3 비율과 중앙값보다 낮은 Pt 비율을 함께 반영합니다.",
    "Recommendations favor high observed Pt and Type 1 behavior, then proximity to the current theta input.":
      "추천 후보는 높은 관측 Pt와 Type 1 거동을 우선하고, 그 다음 현재 θ 입력과의 거리를 반영합니다.",
    "u3 design-space context is based on the curated u3 Pt dataset; Type 2/3 is treated as curve-family context.":
      "u3 설계 공간은 정리된 u3 Pt 데이터셋을 기준으로 계산했으며, Type 2/3은 곡선 계열 정보로 표시합니다.",
    "Recommendations are simulation-backed observed candidates, not new finite-element simulations.":
      "추천 후보는 이미 수행된 해석 데이터 기반이며, 새 유한요소 해석 결과는 아닙니다.",
    "Use high-Pt candidates as screening leads and validate final choices with simulation.":
      "Pt가 높은 후보는 선별용 리드로 사용하고, 최종 후보는 해석으로 다시 검증해 주세요.",
    "High observed Pt with Type 1 preference in the curated Case2/3/4 simulations.":
      "정리된 Case2/3/4 해석에서 높은 Pt와 Type 1 선호 조건을 만족한 후보입니다.",
    "High observed Pt candidate; Type shape should be reviewed before simulation follow-up.":
      "관측 Pt가 높은 후보입니다. 추가 해석 전에 Type 곡선 형태를 함께 확인하는 것이 좋습니다.",
    "High observed u3 Pt in the curated u3 dataset; Type is shown as curve-family context.":
      "정리된 u3 데이터셋에서 관측 Pt가 높은 후보입니다. Type은 곡선 계열 정보로 표시합니다.",
  };
  return map[text] || text;
}

function renderResearchHidden() {
  researchRequestSerial += 1;
  if (!researchPanel) {
    return;
  }
  researchPanel.classList.add("hidden");
  hideResearchMapTooltip();
  researchMapState = { hoverPoints: [], inputs: null };
  if (researchComparison) {
    researchComparison.classList.add("hidden");
    researchComparison.innerHTML = "";
  }
  if (researchCaseInsights) {
    researchCaseInsights.classList.add("hidden");
  }
  if (researchCaseInsightList) {
    researchCaseInsightList.innerHTML = "";
  }
  if (researchMapCanvas) {
    const ctx = researchMapCanvas.getContext("2d");
    ctx.clearRect(0, 0, researchMapCanvas.width, researchMapCanvas.height);
  }
}

function renderResearchLoading() {
  if (!researchPanel) {
    return;
  }
  researchPanel.classList.remove("hidden");
  researchTitle.textContent = TEXT.researchLoadingTitle;
  researchSummary.textContent = TEXT.researchLoadingSummary;
  hideResearchMapTooltip();
  if (researchComparison) {
    researchComparison.classList.add("hidden");
    researchComparison.innerHTML = "";
  }
  if (researchCaseInsights) {
    researchCaseInsights.classList.add("hidden");
  }
  if (researchCaseInsightList) {
    researchCaseInsightList.innerHTML = "";
  }
  researchCaseList.innerHTML = "";
  researchNearestList.innerHTML = "";
  researchRecommendations.innerHTML = "";
  researchNotes.innerHTML = "";
  drawDesignSpaceMap([], null);
}

function renderResearchFailed() {
  if (!researchPanel) {
    return;
  }
  researchPanel.classList.remove("hidden");
  researchTitle.textContent = TEXT.designSpaceTitle;
  researchSummary.textContent = TEXT.researchFailed;
  hideResearchMapTooltip();
  if (researchComparison) {
    researchComparison.classList.add("hidden");
    researchComparison.innerHTML = "";
  }
  if (researchCaseInsights) {
    researchCaseInsights.classList.add("hidden");
  }
  if (researchCaseInsightList) {
    researchCaseInsightList.innerHTML = "";
  }
  researchCaseList.innerHTML = "";
  researchNearestList.innerHTML = "";
  researchRecommendations.innerHTML = "";
  researchNotes.innerHTML = "";
  drawDesignSpaceMap([], null);
}

async function requestDesignSpace(data, scope) {
  const inputs = data?.inputs || {};
  if (inputs.theta1 === undefined || inputs.theta2 === undefined || !inputs.case) {
    renderResearchHidden();
    return;
  }

  const serial = ++researchRequestSerial;
  renderResearchLoading();
  try {
    const insight = await postJson("/design-space", {
      theta1: Number(inputs.theta1),
      theta2: Number(inputs.theta2),
      case: inputs.case,
      scope,
    });
    if (serial === researchRequestSerial) {
      if (latestPredictionData) {
        latestPredictionData = { ...latestPredictionData, design_space: insight };
      }
      renderDesignSpace(insight);
    }
  } catch (error) {
    if (serial === researchRequestSerial) {
      renderResearchFailed();
    }
  }
}

function hideResearchMapTooltip() {
  if (!researchMapTooltip) {
    return;
  }
  researchMapTooltip.classList.add("hidden");
  researchMapTooltip.innerHTML = "";
}

function mapEventPosition(event) {
  if (!researchMapCanvas) {
    return null;
  }
  const rect = researchMapCanvas.getBoundingClientRect();
  if (!rect.width || !rect.height) {
    return null;
  }
  const cssX = event.clientX - rect.left;
  const cssY = event.clientY - rect.top;
  return {
    canvasX: cssX * (researchMapCanvas.width / rect.width),
    canvasY: cssY * (researchMapCanvas.height / rect.height),
    cssX,
    cssY,
  };
}

function nearestResearchMapPoint(canvasX, canvasY) {
  let best = null;
  let bestScore = Number.POSITIVE_INFINITY;
  (researchMapState.hoverPoints || []).forEach((entry) => {
    const distance = Math.hypot(entry.x - canvasX, entry.y - canvasY);
    const threshold = Math.max(11, entry.radius + 6);
    if (distance > threshold) {
      return;
    }
    const selectedCaseBonus = entry.point.case === researchMapState.inputs?.case ? -2.5 : 0;
    const currentInputBonus = entry.point.isCurrentInput ? -10 : 0;
    const score = distance + selectedCaseBonus + currentInputBonus;
    if (score < bestScore) {
      best = { ...entry, distance };
      bestScore = score;
    }
  });
  return best;
}

function addTooltipField(list, label, value) {
  const group = document.createElement("div");
  const term = document.createElement("dt");
  const detail = document.createElement("dd");
  term.textContent = label;
  detail.textContent = value;
  group.append(term, detail);
  list.appendChild(group);
}

function renderResearchMapTooltip(point) {
  if (!researchMapTooltip || !point) {
    return;
  }
  researchMapTooltip.innerHTML = "";
  const isCurrentInput = Boolean(point.isCurrentInput);
  const title = document.createElement("strong");
  title.textContent = isCurrentInput
    ? `${TEXT.currentInputPoint} · ${caseLabel(point.case)}`
    : `${caseLabel(point.case)} · ${typeLabel(point.type)}`;
  const meta = document.createElement("span");
  meta.textContent = isCurrentInput
    ? TEXT.modelEstimate
    : point.case === researchMapState.inputs?.case
    ? TEXT.selectedCasePoint
    : TEXT.otherCasePoint;
  const list = document.createElement("dl");
  addTooltipField(list, "θ₁", formatMetric(point.theta1, 0));
  addTooltipField(list, "θ₂", formatMetric(point.theta2, 0));
  addTooltipField(list, "Pt", formatMetric(point.pt, 2));
  addTooltipField(list, isCurrentInput ? "Type" : "Test", isCurrentInput ? typeLabel(point.type) : (point.test_id || "-"));
  if (isCurrentInput && point.confidence !== undefined && point.confidence !== null) {
    addTooltipField(list, IS_KO ? "신뢰도" : "Confidence", percent(point.confidence));
  }
  researchMapTooltip.append(title, meta, list);
}

function showResearchMapTooltip(point, cssX, cssY) {
  if (!researchMapTooltip) {
    return;
  }
  renderResearchMapTooltip(point);
  researchMapTooltip.classList.remove("hidden");
  const shell = researchMapTooltip.parentElement;
  if (!shell) {
    return;
  }
  const shellRect = shell.getBoundingClientRect();
  const tooltipRect = researchMapTooltip.getBoundingClientRect();
  const gap = 14;
  let left = cssX + gap;
  let top = cssY + gap;
  if (left + tooltipRect.width > shellRect.width - 8) {
    left = cssX - tooltipRect.width - gap;
  }
  if (top + tooltipRect.height > shellRect.height - 8) {
    top = cssY - tooltipRect.height - gap;
  }
  researchMapTooltip.style.left = `${Math.max(8, left)}px`;
  researchMapTooltip.style.top = `${Math.max(8, top)}px`;
}

function handleResearchMapPointer(event) {
  const position = mapEventPosition(event);
  if (!position) {
    hideResearchMapTooltip();
    return;
  }
  const nearest = nearestResearchMapPoint(position.canvasX, position.canvasY);
  if (!nearest) {
    hideResearchMapTooltip();
    if (researchMapCanvas) {
      researchMapCanvas.style.cursor = "default";
    }
    return;
  }
  if (researchMapCanvas) {
    researchMapCanvas.style.cursor = "pointer";
  }
  showResearchMapTooltip(nearest.point, position.cssX, position.cssY);
}

function handleResearchMapDocumentPointer(event) {
  if (!researchMapTooltip || researchMapTooltip.classList.contains("hidden")) {
    return;
  }
  const shell = researchMapTooltip.parentElement;
  if (!shell || shell.contains(event.target)) {
    return;
  }
  hideResearchMapTooltip();
  if (researchMapCanvas) {
    researchMapCanvas.style.cursor = "default";
  }
}

function drawDesignSpaceMap(points, inputs) {
  if (!researchMapCanvas) {
    return;
  }
  const canvas = researchMapCanvas;
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const pad = { left: 46, right: 18, top: 18, bottom: 42 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const xMin = -90;
  const xMax = 90;
  const yMin = -90;
  const yMax = 90;
  const x = (value) => pad.left + ((Number(value) - xMin) / (xMax - xMin)) * plotW;
  const y = (value) => pad.top + plotH - ((Number(value) - yMin) / (yMax - yMin)) * plotH;

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#f8fbfe";
  ctx.fillRect(0, 0, width, height);

  ctx.strokeStyle = "#dfe8f2";
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let tick = -90; tick <= 90; tick += 30) {
    ctx.moveTo(x(tick), pad.top);
    ctx.lineTo(x(tick), pad.top + plotH);
    ctx.moveTo(pad.left, y(tick));
    ctx.lineTo(pad.left + plotW, y(tick));
  }
  ctx.stroke();

  ctx.strokeStyle = "#94a3b8";
  ctx.strokeRect(pad.left, pad.top, plotW, plotH);

  const colors = {
    1: "#0f9f6e",
    2: "#0c8fd8",
    3: "#df4b3f",
  };
  const hoverPoints = [];
  (points || []).forEach((point) => {
    const type = point.type || 0;
    const radius = 3.5 + Math.min(3, Math.max(0, Number(point.pt || 0) / 12000));
    const pointX = x(point.theta1);
    const pointY = y(point.theta2);
    hoverPoints.push({
      x: pointX,
      y: pointY,
      radius,
      point,
    });
    ctx.beginPath();
    ctx.fillStyle = colors[type] || "#708195";
    ctx.globalAlpha = point.case === inputs?.case ? 0.78 : 0.32;
    ctx.arc(pointX, pointY, radius, 0, Math.PI * 2);
    ctx.fill();
  });
  ctx.globalAlpha = 1;

  if (inputs) {
    const currentTheta1 = Number(inputs.theta1);
    const currentTheta2 = Number(inputs.theta2);
    if (Number.isFinite(currentTheta1) && Number.isFinite(currentTheta2)) {
      const currentX = x(currentTheta1);
      const currentY = y(currentTheta2);
      hoverPoints.push({
        x: currentX,
        y: currentY,
        radius: 10,
        point: {
          isCurrentInput: true,
          theta1: currentTheta1,
          theta2: currentTheta2,
          case: inputs.case,
          type: latestPredictionData?.predicted_type ?? null,
          pt: latestPredictionData?.predicted_pt ?? latestPredictionData?.inputs?.pt ?? null,
          confidence: latestPredictionData?.confidence ?? null,
          test_id: TEXT.currentInputPoint,
        },
      });
      ctx.save();
      ctx.translate(currentX, currentY);
      ctx.fillStyle = "#7c3aed";
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(0, 0, 8, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = "#111827";
      ctx.font = "700 12px system-ui, sans-serif";
      ctx.textAlign = "left";
      ctx.fillText(TEXT.currentInputPoint, 12, -10);
      ctx.restore();
    }
  }
  researchMapState = { hoverPoints, inputs };
  hideResearchMapTooltip();

  ctx.fillStyle = "#617086";
  ctx.font = "700 12px system-ui, sans-serif";
  ctx.textAlign = "center";
  for (let tick = -90; tick <= 90; tick += 30) {
    ctx.fillText(String(tick), x(tick), height - 18);
  }
  ctx.textAlign = "right";
  for (let tick = -90; tick <= 90; tick += 30) {
    ctx.fillText(String(tick), pad.left - 9, y(tick) + 4);
  }
  ctx.textAlign = "center";
  ctx.fillText("θ₁", pad.left + plotW / 2, height - 3);
  ctx.save();
  ctx.translate(15, pad.top + plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText("θ₂", 0, 0);
  ctx.restore();
}

function setForecastControlValue(form, name, value) {
  if (!form) {
    return;
  }
  const control = form.querySelector(`[name="${name}"]`);
  if (!control) {
    return;
  }
  control.value = name === "theta1" || name === "theta2"
    ? formatThetaInputValue(value)
    : String(value);
  control.dispatchEvent(new Event(name === "case" ? "change" : "input", { bubbles: true }));
}

function submitForecastForm(form) {
  if (!form) {
    return;
  }
  const submitButton = form.querySelector('button[type="submit"]');
  if (submitButton?.disabled) {
    return;
  }
  if (typeof form.requestSubmit === "function") {
    form.requestSubmit();
    return;
  }
  form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
}

function applyRecommendationCandidate(candidate, scope) {
  const form = scope === "u3" ? u3PtForm : responseForm;
  if (!form || !candidate) {
    return;
  }
  setForecastControlValue(form, "theta1", candidate.theta1);
  setForecastControlValue(form, "theta2", candidate.theta2);
  setForecastControlValue(form, "case", candidate.case);
  updateDynamicStackPreview();
  clearError();
  submitForecastForm(form);
}

function caseLabel(caseValue) {
  return String(caseValue || TEXT.unknown).replace("Case", "Case ");
}

function caseRiskSummary(caseSummaries, caseValue) {
  return (caseSummaries || []).find((summary) => summary.case === caseValue) || null;
}

function formatRiskSummary(summary) {
  if (!summary) {
    return "-";
  }
  return `${riskLabel(summary.risk_label)} · ${percent(summary.risk_score)}`;
}

function signedMetric(value, digits = 0) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "-";
  }
  const sign = numeric > 0 ? "+" : "";
  return `${sign}${formatMetric(numeric, digits)}`;
}

function renderScoreBreakdown(candidate) {
  const components = candidate?.score_components;
  if (!components) {
    return "";
  }
  const items = [
    [TEXT.ptContribution, components.pt],
    [TEXT.typeContribution, components.type],
    [TEXT.proximityContribution, components.proximity],
    [TEXT.totalScore, candidate.score],
  ];
  return `
    <div class="comparison-score">
      <span>${TEXT.scoringBasis}</span>
      <div>
        ${items.map(([label, value]) => `<i><strong>${label}</strong>${percent(value)}</i>`).join("")}
      </div>
    </div>
  `;
}

function renderResearchComparison(insight) {
  if (!researchComparison) {
    return;
  }
  const topCandidate = (insight.recommendations || [])[0];
  if (!topCandidate) {
    researchComparison.classList.remove("hidden");
    researchComparison.innerHTML = `<p>${TEXT.noComparison}</p>`;
    return;
  }

  const inputs = latestPredictionData?.inputs || insight.inputs || {};
  const currentCase = inputs.case || insight.inputs?.case;
  const currentRisk = caseRiskSummary(insight.case_summaries, currentCase);
  const candidateRisk = caseRiskSummary(insight.case_summaries, topCandidate.case);
  const currentPt = Number(latestPredictionData?.predicted_pt);
  const candidatePt = Number(topCandidate.expected_pt);
  const deltaPt = Number.isFinite(currentPt) && Number.isFinite(candidatePt)
    ? candidatePt - currentPt
    : null;
  const currentType = latestPredictionData?.predicted_type;
  const candidateCase = caseLabel(topCandidate.case);
  const currentCaseLabel = caseLabel(currentCase);
  const currentPtText = formatMetric(currentPt, 0);
  const candidatePtText = formatMetric(candidatePt, 0);
  const deltaClass = Number.isFinite(Number(deltaPt))
    ? (Number(deltaPt) >= 0 ? "positive" : "negative")
    : "neutral";

  researchComparison.classList.remove("hidden");
  researchComparison.innerHTML = `
    <div class="comparison-head">
      <div>
        <h3>${TEXT.comparisonTitle}</h3>
        <p>${TEXT.modelEstimate} ↔ ${TEXT.datasetObservation}</p>
      </div>
      <span class="comparison-delta ${deltaClass}">${TEXT.ptDelta} ${signedMetric(deltaPt, 0)}</span>
    </div>
    <div class="comparison-grid">
      <article class="comparison-card current">
        <span>${TEXT.currentPrediction}</span>
        <strong>${currentCaseLabel} · θ₁ ${formatMetric(inputs.theta1, 0)} / θ₂ ${formatMetric(inputs.theta2, 0)}</strong>
        <dl>
          <div><dt>Pt</dt><dd>${currentPtText}</dd></div>
          <div><dt>Type</dt><dd>${typeLabel(currentType)}</dd></div>
          <div><dt>${TEXT.caseRiskLabel}</dt><dd>${formatRiskSummary(currentRisk)}</dd></div>
        </dl>
      </article>
      <article class="comparison-card candidate">
        <span>${TEXT.topCandidate}</span>
        <strong>${candidateCase} · θ₁ ${formatMetric(topCandidate.theta1, 0)} / θ₂ ${formatMetric(topCandidate.theta2, 0)}</strong>
        <dl>
          <div><dt>Pt</dt><dd>${candidatePtText}</dd></div>
          <div><dt>Type</dt><dd>${typeLabel(topCandidate.observed_type)}</dd></div>
          <div><dt>${TEXT.caseRiskLabel}</dt><dd>${formatRiskSummary(candidateRisk)}</dd></div>
        </dl>
      </article>
    </div>
    ${renderScoreBreakdown(topCandidate)}
    <p class="comparison-rationale"><strong>${TEXT.whyCandidate}</strong> ${localizeResearchText(topCandidate.rationale)}</p>
  `;
}

function focusKindLabel(kind) {
  return kind === "type1" ? TEXT.type1Zone : TEXT.highPtZone;
}

function formatThetaRange(minValue, maxValue) {
  const min = Number(minValue);
  const max = Number(maxValue);
  if (!Number.isFinite(min) || !Number.isFinite(max)) {
    return "-";
  }
  if (Math.round(min) === Math.round(max)) {
    return formatMetric(min, 0);
  }
  return `${formatMetric(min, 0)} ~ ${formatMetric(max, 0)}`;
}

function caseInsightClass(caseValue) {
  const normalized = String(caseValue || "").toLowerCase();
  if (normalized.includes("case2")) {
    return "case-2";
  }
  if (normalized.includes("case3")) {
    return "case-3";
  }
  if (normalized.includes("case4")) {
    return "case-4";
  }
  return "case-unknown";
}

function renderCaseInsights(insight) {
  if (!researchCaseInsights || !researchCaseInsightList) {
    return;
  }
  const items = insight.case_insights || [];
  if (!items.length) {
    researchCaseInsights.classList.add("hidden");
    researchCaseInsightList.innerHTML = "";
    return;
  }
  const selectedCase = insight.inputs?.case;
  researchCaseInsights.classList.remove("hidden");
  researchCaseInsightList.innerHTML = "";
  items.forEach((item) => {
    const card = document.createElement("article");
    card.className = `case-insight-card ${caseInsightClass(item.case)}${item.case === selectedCase ? " selected" : ""}`;
    card.innerHTML = `
      <div class="case-insight-head">
        <span class="case-insight-badge">${caseLabel(item.case)}</span>
        <strong>${focusKindLabel(item.focus_kind)}</strong>
        <em>${percent(item.focus_rate)}</em>
      </div>
      <div class="case-theta-window">
        <span>${TEXT.thetaWindow}</span>
        <dl class="case-theta-grid">
          <div class="case-theta-chip">
            <dt>θ₁</dt>
            <dd>${formatThetaRange(item.theta1_min, item.theta1_max)}</dd>
          </div>
          <div class="case-theta-chip">
            <dt>θ₂</dt>
            <dd>${formatThetaRange(item.theta2_min, item.theta2_max)}</dd>
          </div>
        </dl>
      </div>
      <dl class="case-insight-metrics">
        <div>
          <dt>${TEXT.bestPt}</dt>
          <dd>${formatMetric(item.best_pt, 0)}</dd>
        </div>
        <div>
          <dt>${TEXT.bestTheta}</dt>
          <dd>θ₁ ${formatMetric(item.best_theta1, 0)} · θ₂ ${formatMetric(item.best_theta2, 0)}</dd>
        </div>
        <div>
          <dt>${TEXT.bestType}</dt>
          <dd>${typeLabel(item.best_type)}</dd>
        </div>
        <div>
          <dt>${TEXT.coverage}</dt>
          <dd>${item.focus_count}/${item.count}</dd>
        </div>
      </dl>
    `;
    researchCaseInsightList.appendChild(card);
  });
}

function renderDesignSpace(insight) {
  if (!researchPanel) {
    return;
  }
  const inputs = insight.inputs || {};
  researchPanel.classList.remove("hidden");
  researchTitle.textContent = TEXT.designSpaceTitle;
  researchSummary.textContent = insight.scope === "u3"
    ? (IS_KO ? "현재 θ 조합이 u3 Pt 데이터 공간 어디에 있는지와 Case별 위험도를 보여줍니다." : "Shows where the current theta pair sits in the u3 Pt design space.")
    : (IS_KO ? "현재 θ 조합이 Case2/3/4 응답 데이터 공간 어디에 있는지와 Type/Pt 경향을 보여줍니다." : "Shows where the current theta pair sits in the Case2/3/4 response design space.");

  drawDesignSpaceMap(insight.map_points || [], inputs);
  renderResearchComparison(insight);
  renderCaseInsights(insight);

  researchCaseList.innerHTML = "";
  (insight.case_summaries || []).forEach((summary) => {
    const item = document.createElement("article");
    item.className = `case-risk-card risk-${summary.risk_label}`;
    const rates = Object.entries(summary.type_rates || {})
      .map(([key, value]) => `${key.replace("type", "Type ")} ${percent(value)}`)
      .join(" · ");
    item.innerHTML = `
      <div>
        <strong>${summary.case.replace("Case", "Case ")}</strong>
        <span>${riskLabel(summary.risk_label)} · ${percent(summary.risk_score)}</span>
      </div>
      <p>Median Pt ${formatMetric(summary.median_pt, 0)} · Max ${formatMetric(summary.max_pt, 0)}</p>
      <small>${rates || "-"}</small>
    `;
    researchCaseList.appendChild(item);
  });

  researchNearestList.innerHTML = "";
  (insight.nearest_points || []).slice(0, 6).forEach((point) => {
    const item = document.createElement("div");
    item.className = "nearest-item";
    item.innerHTML = `
      <strong>${point.case.replace("Case", "Case ")} · θ₁ ${formatMetric(point.theta1, 0)} / θ₂ ${formatMetric(point.theta2, 0)}</strong>
      <span>${typeLabel(point.type)} · Pt ${formatMetric(point.pt, 0)} · Δθ ${formatMetric(point.distance, 1)}</span>
    `;
    researchNearestList.appendChild(item);
  });

  researchRecommendations.innerHTML = "";
  (insight.recommendations || []).slice(0, 5).forEach((candidate, index) => {
    const candidateCaseLabel = caseLabel(candidate.case);
    const item = document.createElement("button");
    item.type = "button";
    item.className = "recommendation-card recommendation-action";
    item.setAttribute(
      "aria-label",
      `${TEXT.applyCandidate}: ${candidateCaseLabel} θ₁ ${formatMetric(candidate.theta1, 0)} θ₂ ${formatMetric(candidate.theta2, 0)}`,
    );
    item.innerHTML = `
      <div class="recommendation-rank">${index + 1}</div>
      <div>
        <strong>${candidateCaseLabel} · θ₁ ${formatMetric(candidate.theta1, 0)} / θ₂ ${formatMetric(candidate.theta2, 0)}</strong>
        <span>Pt ${formatMetric(candidate.expected_pt, 0)} · ${TEXT.observedType} ${candidate.observed_type ?? "-"} · ${TEXT.score} ${percent(candidate.score)}</span>
        <p>${localizeResearchText(candidate.rationale)}</p>
        <small class="recommendation-apply">${TEXT.applyCandidate}</small>
      </div>
    `;
    item.addEventListener("click", () => applyRecommendationCandidate(candidate, insight.scope));
    researchRecommendations.appendChild(item);
  });

  researchNotes.innerHTML = "";
  (insight.notes || []).forEach((note) => {
    const item = document.createElement("li");
    item.textContent = localizeResearchText(note);
    researchNotes.appendChild(item);
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

function lineIntersection(firstLine, secondLine) {
  const denominator = firstLine.slope - secondLine.slope;
  if (!Number.isFinite(denominator) || Math.abs(denominator) < 1e-9) {
    return null;
  }
  const displacement = (secondLine.intercept - firstLine.intercept) / denominator;
  const force = lineY(firstLine, displacement);
  if (!Number.isFinite(displacement) || !Number.isFinite(force)) {
    return null;
  }
  return { displacement, force };
}

function lineSse(samples, line) {
  return samples.reduce((sum, point) => {
    const residual = point.force - lineY(line, point.displacement);
    return sum + residual * residual;
  }, 0);
}

function lineR2(samples, line) {
  if (!samples || samples.length < 2 || !line) {
    return Number.NEGATIVE_INFINITY;
  }
  const meanY = samples.reduce((sum, point) => sum + point.force, 0) / samples.length;
  const ssTot = samples.reduce((sum, point) => sum + (point.force - meanY) ** 2, 0);
  if (ssTot <= 1e-18) {
    return lineSse(samples, line) <= 1e-18 ? 1 : 0;
  }
  return 1 - lineSse(samples, line) / ssTot;
}

function clampNumber(value, minValue, maxValue) {
  return Math.min(maxValue, Math.max(minValue, value));
}

function drawRoundedRect(ctx, x, y, width, height, radius) {
  const r = Math.min(radius, width / 2, height / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + width - r, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + r);
  ctx.lineTo(x + width, y + height - r);
  ctx.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
  ctx.lineTo(x + r, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}

function drawPtLabel(ctx, label, value, ptX, ptY, pad, width, height, options = {}) {
  const colors = {
    line: options.lineColor || "rgba(239, 68, 68, 0.72)",
    fill: options.fillColor || "rgba(255, 247, 237, 0.96)",
    border: options.borderColor || "#fdba74",
    title: options.titleColor || "#9a3412",
    value: options.valueColor || "#7c2d12",
  };
  ctx.save();
  ctx.font = "700 17px Inter, system-ui, sans-serif";
  const titleWidth = ctx.measureText(label).width;
  ctx.font = "800 22px Inter, system-ui, sans-serif";
  const valueWidth = ctx.measureText(value).width;

  const labelWidth = Math.max(titleWidth, valueWidth) + 36;
  const labelHeight = 66;
  const gapX = options.gapX ?? 24;
  const gapY = options.gapY ?? 22;
  const autoRight = ptX + gapX + labelWidth < width - pad.right;
  const side = options.side || (autoRight ? "right" : "left");
  const wantsRight = side === "right";
  const autoLabelX = wantsRight
    ? ptX + gapX
    : ptX - gapX - labelWidth;
  const labelX = clampNumber(
    Number.isFinite(Number(options.labelX)) ? Number(options.labelX) : autoLabelX,
    pad.left + 8,
    width - pad.right - labelWidth - 8,
  );
  const preferredLabelY = options.placement === "below"
    ? ptY + gapY
    : ptY - labelHeight - gapY;
  const labelY = clampNumber(
    Number.isFinite(Number(options.labelY)) ? Number(options.labelY) : preferredLabelY,
    pad.top + 8,
    height - pad.bottom - labelHeight - 8,
  );
  const anchorX = ptX < labelX ? labelX : ptX > labelX + labelWidth ? labelX + labelWidth : labelX + labelWidth / 2;
  const anchorY = labelY + labelHeight * 0.62;

  ctx.strokeStyle = colors.line;
  ctx.lineWidth = 1.8;
  ctx.beginPath();
  ctx.moveTo(ptX, ptY);
  ctx.lineTo(anchorX, anchorY);
  ctx.stroke();

  drawRoundedRect(ctx, labelX, labelY, labelWidth, labelHeight, 10);
  ctx.fillStyle = colors.fill;
  ctx.fill();
  ctx.strokeStyle = colors.border;
  ctx.lineWidth = 1.4;
  ctx.stroke();

  ctx.textAlign = "left";
  ctx.textBaseline = "alphabetic";
  ctx.fillStyle = colors.title;
  ctx.font = "700 17px Inter, system-ui, sans-serif";
  ctx.fillText(label, labelX + 18, labelY + 25);
  ctx.fillStyle = colors.value;
  ctx.font = "800 22px Inter, system-ui, sans-serif";
  ctx.fillText(value, labelX + 18, labelY + 52);
  ctx.restore();
}

function prepareResponseCurveCanvas() {
  const ctx = responseCurveCanvas.getContext("2d");
  const rect = responseCurveCanvas.getBoundingClientRect();
  const parentWidth = responseCurveCanvas.parentElement?.clientWidth || 720;
  const logicalWidth = Math.max(320, rect.width || parentWidth || 720);
  const logicalHeight = logicalWidth * 0.6;
  const dpr = Math.min(window.devicePixelRatio || 1, 2.5);
  const pixelWidth = Math.round(logicalWidth * dpr);
  const pixelHeight = Math.round(logicalHeight * dpr);

  if (responseCurveCanvas.width !== pixelWidth || responseCurveCanvas.height !== pixelHeight) {
    responseCurveCanvas.width = pixelWidth;
    responseCurveCanvas.height = pixelHeight;
  }
  responseCurveCanvas.style.height = `${logicalHeight}px`;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  responseCurveView.logicalWidth = logicalWidth;
  responseCurveView.logicalHeight = logicalHeight;
  return { ctx, width: logicalWidth, height: logicalHeight };
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

const KINK_FIT_CONFIG = {
  kinkWin: 7,
  slopeDropFrac: 0.65,
  kinkHold: 3,
  postSkipAfterKink: 2,
  initialMaxLen: 7,
  secondLen: 5,
  preKinkEps: 1e-5,
  nearWeight: 1.0,
  secondFitMaxU: 0.3,
};

function fitWindow(points, start, end) {
  const window = points.slice(start, end + 1);
  const line = linearFit(window);
  if (!line) {
    return null;
  }
  return {
    start,
    end,
    line,
    r2: lineR2(window, line),
    mse: lineSse(window, line) / Math.max(window.length, 1),
  };
}

function bestInitialWindowForKink(points) {
  const minLen = 3;
  const maxLen = 5;
  const halfIndex = Math.floor(points.length * 0.5);
  const endMax = Math.min(halfIndex - 1, maxLen - 1);
  let best = null;
  for (let end = minLen - 1; end <= endMax; end += 1) {
    const candidate = fitWindow(points, 0, end);
    if (!candidate) {
      continue;
    }
    const sse = lineSse(points.slice(0, end + 1), candidate.line);
    if (!best || sse < best.sse) {
      best = { ...candidate, sse };
    }
  }
  return best;
}

function slidingSlopes(points, win = KINK_FIT_CONFIG.kinkWin) {
  const adjustedWin = win % 2 === 0 ? win + 1 : win;
  const half = Math.floor(adjustedWin / 2);
  return points.map((_, index) => {
    if (index < half || index >= points.length - half) {
      return Number.NaN;
    }
    const line = linearFit(points.slice(index - half, index + half + 1));
    return line ? line.slope : Number.NaN;
  });
}

function detectKinkStart(points, initialSlope, startIndexMin) {
  const slopes = slidingSlopes(points);
  const threshold = initialSlope * KINK_FIT_CONFIG.slopeDropFrac;
  const limit = points.length - KINK_FIT_CONFIG.kinkHold;
  for (let index = Math.max(startIndexMin, 0); index <= limit; index += 1) {
    const segment = slopes.slice(index, index + KINK_FIT_CONFIG.kinkHold);
    if (segment.every((slope) => Number.isFinite(slope) && slope <= threshold)) {
      return index;
    }
  }
  return null;
}

function bestInitialLinearWindow(points, endIndex) {
  let best = null;
  const cappedEnd = clampNumber(Math.floor(endIndex), 0, points.length - 1);
  for (let length = 3; length <= KINK_FIT_CONFIG.initialMaxLen; length += 1) {
    const startMax = cappedEnd - (length - 1);
    for (let start = 0; start <= startMax; start += 1) {
      const candidate = fitWindow(points, start, start + length - 1);
      if (!candidate) {
        continue;
      }
      if (!best || candidate.r2 > best.r2 || (Math.abs(candidate.r2 - best.r2) < 1e-12 && length > (best.end - best.start + 1))) {
        best = candidate;
      }
    }
  }
  return best;
}

function bestSecondWindowPostKink(points, startAfterIndex, kinkIndex, firstLine, kinkX) {
  const length = KINK_FIT_CONFIG.secondLen;
  const startMin = Math.max(Math.floor(startAfterIndex), kinkIndex + 1);
  const maxU = KINK_FIT_CONFIG.secondFitMaxU;

  function sweep(strict = true, useMaxU = true) {
    let startMax = points.length - length;
    if (useMaxU && Number.isFinite(maxU)) {
      const lastWithinMax = points.reduce((last, point, index) => (
        point.displacement <= maxU ? index : last
      ), -1);
      if (lastWithinMax >= 0 && lastWithinMax - (length - 1) >= startMin) {
        startMax = Math.min(startMax, lastWithinMax - (length - 1));
      }
    }
    let best = null;
    for (let start = startMin; start <= startMax; start += 1) {
      const candidate = fitWindow(points, start, start + length - 1);
      if (!candidate) {
        continue;
      }
      const pt = lineIntersection(firstLine, candidate.line);
      if (!pt) {
        continue;
      }
      if (strict && pt.displacement > kinkX + KINK_FIT_CONFIG.preKinkEps) {
        continue;
      }
      const dist = Math.max(0, kinkX - pt.displacement);
      const score = candidate.mse + KINK_FIT_CONFIG.nearWeight * (Math.abs(firstLine.slope) ** 2) * (dist ** 2);
      if (!best || score < best.score) {
        best = { ...candidate, score };
      }
    }
    return best;
  }

  return sweep(true, true) || sweep(false, true) || sweep(true, false) || sweep(false, false);
}

function bestFallbackSecondWindow(points, startAfterIndex) {
  let best = null;
  for (let start = Math.max(0, startAfterIndex); start <= points.length - KINK_FIT_CONFIG.secondLen; start += 1) {
    const candidate = fitWindow(points, start, start + KINK_FIT_CONFIG.secondLen - 1);
    if (!candidate) {
      continue;
    }
    if (!best || candidate.mse < best.mse) {
      best = candidate;
    }
  }
  return best;
}

function buildKinkBilinearFit(points, predictedPtValue) {
  if (!points || points.length < 10) {
    return null;
  }
  const sorted = [...points]
    .filter((point) => Number.isFinite(point.displacement) && Number.isFinite(point.force))
    .sort((a, b) => a.displacement - b.displacement);
  if (sorted.length < 10) {
    return null;
  }
  const minX = sorted[0].displacement;
  const maxX = sorted[sorted.length - 1].displacement;
  const initialKink = bestInitialWindowForKink(sorted);
  const kinkIndex = initialKink
    ? detectKinkStart(sorted, initialKink.line.slope, initialKink.end + 1)
    : null;
  const endForInitial = kinkIndex === null ? sorted.length - 1 : Math.max(0, kinkIndex - 1);
  const first = bestInitialLinearWindow(sorted, endForInitial);
  if (!first) {
    return null;
  }

  let second = null;
  let detectedKinkX = null;
  if (kinkIndex !== null) {
    detectedKinkX = sorted[kinkIndex].displacement;
    const secondStart = Math.max(first.end + 1, kinkIndex + KINK_FIT_CONFIG.postSkipAfterKink);
    second = bestSecondWindowPostKink(sorted, secondStart, kinkIndex, first.line, detectedKinkX);
  } else {
    second = bestFallbackSecondWindow(sorted, first.end + 1);
  }
  if (!second) {
    return null;
  }

  let pt = lineIntersection(first.line, second.line);
  if (!pt || pt.force <= 0) {
    return null;
  }
  if (detectedKinkX !== null && pt.displacement > detectedKinkX + KINK_FIT_CONFIG.preKinkEps) {
    const clampedX = detectedKinkX - KINK_FIT_CONFIG.preKinkEps;
    pt = {
      displacement: clampedX,
      force: lineY(first.line, clampedX),
    };
  }
  pt = {
    displacement: clampNumber(pt.displacement, minX, maxX),
    force: lineY(first.line, clampNumber(pt.displacement, minX, maxX)),
  };
  const spanX = Math.max(maxX - minX, 1e-9);
  const predictedPt = Number(predictedPtValue);
  const predictedPoint = Number.isFinite(predictedPt) ? pointAtForce(sorted, predictedPt) : null;

  return {
    kink: {
      displacement: pt.displacement,
      force: pt.force,
    },
    detectedKink: detectedKinkX === null ? null : {
      displacement: detectedKinkX,
      force: sorted[kinkIndex].force,
    },
    predictedPoint,
    firstLine: first.line,
    secondLine: second.line,
    firstStartX: minX,
    firstEndX: Math.min(maxX, pt.displacement + spanX * 0.045),
    secondStartX: Math.max(minX, pt.displacement - spanX * 0.025),
    secondEndX: maxX,
  };
}

function buildBilinearFit(points, predictedPtValue) {
  return buildKinkBilinearFit(points, predictedPtValue);
}

function buildU3BilinearFit(points, predictedPtValue) {
  const fit = buildKinkBilinearFit(points, predictedPtValue);
  return normalizeU3BilinearFit(fit, points);
}

function normalizeU3BilinearFit(fit, points) {
  if (!fit || !points || !points.length) {
    return fit;
  }
  const sorted = [...points]
    .filter((point) => Number.isFinite(point.displacement) && Number.isFinite(point.force))
    .sort((a, b) => a.displacement - b.displacement);
  const minX = sorted[0].displacement;
  const maxX = sorted[sorted.length - 1].displacement;
  const spanX = Math.max(maxX - minX, 1e-9);
  const kinkX = clampNumber(fit.kink.displacement, minX, maxX);
  return {
    ...fit,
    firstStartX: minX,
    firstEndX: Math.min(maxX, kinkX + spanX * 0.035),
    secondStartX: kinkX,
    secondEndX: maxX,
  };
}

function backendLine(line) {
  if (!line) {
    return null;
  }
  const slope = Number(line.slope);
  const intercept = Number(line.intercept);
  if (!Number.isFinite(slope) || !Number.isFinite(intercept)) {
    return null;
  }
  return { slope, intercept };
}

function backendPoint(point) {
  if (!point) {
    return null;
  }
  const displacement = Number(point.displacement);
  const force = Number(point.force);
  if (!Number.isFinite(displacement) || !Number.isFinite(force)) {
    return null;
  }
  return { displacement, force };
}

function buildBackendBilinearFit(points, predictedPtValue, backendFit) {
  if (!backendFit || !points || points.length < 2) {
    return null;
  }
  const sorted = [...points]
    .filter((point) => Number.isFinite(point.displacement) && Number.isFinite(point.force))
    .sort((a, b) => a.displacement - b.displacement);
  if (sorted.length < 2) {
    return null;
  }
  const firstLine = backendLine(backendFit.first_line || backendFit.firstLine);
  const secondLine = backendLine(backendFit.second_line || backendFit.secondLine);
  const kink = backendPoint(backendFit.kink);
  if (!firstLine || !secondLine || !kink) {
    return null;
  }

  const minX = sorted[0].displacement;
  const maxX = sorted[sorted.length - 1].displacement;
  const predictedPt = Number(predictedPtValue);
  const predictedPoint = Number.isFinite(predictedPt) ? pointAtForce(sorted, predictedPt) : null;
  const firstStartX = Number(backendFit.first_start_x ?? backendFit.firstStartX);
  const firstEndX = Number(backendFit.first_end_x ?? backendFit.firstEndX);
  const secondStartX = Number(backendFit.second_start_x ?? backendFit.secondStartX);
  const secondEndX = Number(backendFit.second_end_x ?? backendFit.secondEndX);

  return {
    kink,
    detectedKink: backendPoint(backendFit.detected_kink || backendFit.detectedKink),
    predictedPoint,
    firstLine,
    secondLine,
    firstStartX: Number.isFinite(firstStartX) ? firstStartX : minX,
    firstEndX: Number.isFinite(firstEndX) ? firstEndX : Math.min(maxX, kink.displacement),
    secondStartX: Number.isFinite(secondStartX) ? secondStartX : Math.max(minX, kink.displacement),
    secondEndX: Number.isFinite(secondEndX) ? secondEndX : maxX,
  };
}

function drawResponseCurve(points, predictedPtValue, fitMode = "standard", backendFit = null) {
  const { ctx, width, height } = prepareResponseCurveCanvas();
  const pad = { left: 92, right: 28, top: 36, bottom: 76 };
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#f8fafc";
  ctx.fillRect(0, 0, width, height);
  if (!points || !points.length) {
    ctx.fillStyle = "#637184";
    ctx.font = "16px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(TEXT.estimatedCurveEmpty, width / 2, height / 2);
    return;
  }
  const bilinearFit = fitMode === "u3"
    ? buildU3BilinearFit(points, predictedPtValue)
    : (buildBackendBilinearFit(points, predictedPtValue, backendFit) || buildBilinearFit(points, predictedPtValue));
  const xs = points.map((point) => point.displacement);
  const ys = points.map((point) => point.force);
  const rawFitIntersection = bilinearFit ? lineIntersection(bilinearFit.firstLine, bilinearFit.secondLine) : null;
  const fitIntersection = rawFitIntersection && Number.isFinite(rawFitIntersection.displacement) && Number.isFinite(rawFitIntersection.force)
    ? rawFitIntersection
    : null;
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
    if (fitIntersection) {
      ys.push(fitIntersection.force);
    }
    if (bilinearFit.detectedKink) {
      ys.push(bilinearFit.detectedKink.force);
    }
  }
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(0, ...ys);
  const maxY = Math.max(...ys) * 1.06;
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const baseSpanX = Math.max(1e-9, maxX - minX);
  const baseSpanY = Math.max(1e-9, maxY - minY);
  const zoom = clampNumber(responseCurveView.scale || 1, RESPONSE_CURVE_MIN_ZOOM, RESPONSE_CURVE_MAX_ZOOM);
  const visibleSpanX = baseSpanX / zoom;
  const visibleSpanY = baseSpanY / zoom;
  const centerX = minX + baseSpanX * clampNumber(responseCurveView.centerXNorm, 0, 1);
  const centerY = minY + baseSpanY * clampNumber(responseCurveView.centerYNorm, 0, 1);
  let visibleMinX = centerX - visibleSpanX / 2;
  let visibleMinY = centerY - visibleSpanY / 2;
  visibleMinX = clampNumber(visibleMinX, minX, maxX - visibleSpanX);
  visibleMinY = clampNumber(visibleMinY, minY, maxY - visibleSpanY);
  const visibleMaxX = visibleMinX + visibleSpanX;
  const visibleMaxY = visibleMinY + visibleSpanY;
  responseCurveView.centerXNorm = clampNumber(((visibleMinX + visibleSpanX / 2) - minX) / baseSpanX, 0, 1);
  responseCurveView.centerYNorm = clampNumber(((visibleMinY + visibleSpanY / 2) - minY) / baseSpanY, 0, 1);
  responseCurveView.domain = {
    baseMinX: minX,
    baseMaxX: maxX,
    baseMinY: minY,
    baseMaxY: maxY,
    baseSpanX,
    baseSpanY,
    visibleMinX,
    visibleMaxX,
    visibleMinY,
    visibleMaxY,
    visibleSpanX,
    visibleSpanY,
  };
  responseCurveView.plot = {
    left: pad.left,
    right: width - pad.right,
    top: pad.top,
    bottom: height - pad.bottom,
    width: plotW,
    height: plotH,
  };
  updateResponseCurveZoomControls();
  const scaleX = (value) => pad.left + ((value - visibleMinX) / Math.max(1e-9, visibleMaxX - visibleMinX)) * plotW;
  const scaleY = (value) => height - pad.bottom - ((value - visibleMinY) / Math.max(1e-9, visibleMaxY - visibleMinY)) * plotH;
  const xTicks = Array.from({ length: 6 }, (_, index) => visibleMinX + ((visibleMaxX - visibleMinX) / 5) * index);
  const yTicks = Array.from({ length: 6 }, (_, index) => visibleMinY + ((visibleMaxY - visibleMinY) / 5) * index);

  ctx.strokeStyle = "#e6edf3";
  ctx.lineWidth = 1;
  ctx.beginPath();
  yTicks.slice(1, -1).forEach((value) => {
    const y = scaleY(value);
    ctx.moveTo(pad.left, y);
    ctx.lineTo(width - pad.right, y);
  });
  xTicks.slice(1, -1).forEach((value) => {
    const x = scaleX(value);
    ctx.moveTo(x, pad.top);
    ctx.lineTo(x, height - pad.bottom);
  });
  ctx.stroke();

  ctx.strokeStyle = "#d8e0e8";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(pad.left, pad.top);
  ctx.lineTo(pad.left, height - pad.bottom);
  ctx.lineTo(width - pad.right, height - pad.bottom);
  ctx.stroke();

  ctx.fillStyle = "#647184";
  ctx.font = "16px Inter, system-ui, sans-serif";
  ctx.textBaseline = "middle";
  ctx.textAlign = "right";
  yTicks.forEach((value) => {
    ctx.fillText(formatAxisTick(value, 2), pad.left - 12, scaleY(value));
  });
  ctx.textBaseline = "top";
  ctx.textAlign = "center";
  xTicks.forEach((value) => {
    ctx.fillText(formatAxisTick(value, 4), scaleX(value), height - pad.bottom + 20);
  });

  if (bilinearFit) {
    const kinkMarker = fitMode === "u3"
      ? (fitIntersection || bilinearFit.kink)
      : (bilinearFit.detectedKink || bilinearFit.kink);
    const kinkX = scaleX(kinkMarker.displacement);
    ctx.save();
    ctx.setLineDash([6, 4]);
    ctx.strokeStyle = "#ef4444";
    ctx.lineWidth = 2.2;
    ctx.beginPath();
    ctx.rect(pad.left, pad.top, plotW, plotH);
    ctx.clip();
    ctx.beginPath();
    ctx.moveTo(scaleX(bilinearFit.firstStartX), scaleY(lineY(bilinearFit.firstLine, bilinearFit.firstStartX)));
    ctx.lineTo(scaleX(bilinearFit.firstEndX), scaleY(lineY(bilinearFit.firstLine, bilinearFit.firstEndX)));
    ctx.moveTo(scaleX(bilinearFit.secondStartX), scaleY(lineY(bilinearFit.secondLine, bilinearFit.secondStartX)));
    ctx.lineTo(scaleX(bilinearFit.secondEndX), scaleY(lineY(bilinearFit.secondLine, bilinearFit.secondEndX)));
    ctx.stroke();

    ctx.setLineDash([7, 4]);
    ctx.strokeStyle = "#7c3aed";
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    ctx.moveTo(kinkX, pad.top);
    ctx.lineTo(kinkX, height - pad.bottom);
    ctx.stroke();
    ctx.restore();
  }

  ctx.save();
  ctx.beginPath();
  ctx.rect(pad.left, pad.top, plotW, plotH);
  ctx.clip();
  ctx.strokeStyle = "#0f766e";
  ctx.lineWidth = 4;
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
  ctx.restore();

  if (bilinearFit) {
    const marker = fitMode === "u3"
      ? (fitIntersection || bilinearFit.kink)
      : bilinearFit.kink;
    const ptX = scaleX(marker.displacement);
    const ptY = scaleY(marker.force);
    const ptLabel = fitMode === "u3" ? TEXT.fitIntersectionLabel : TEXT.predictedPtLabel;
    const ptValue = formatMetric(marker.force, 2);
    const u3LabelX = fitMode === "u3"
      ? Math.min(width - pad.right - 170, Math.max(pad.left + 18, ptX + 42))
      : null;
    const u3FitLabelY = pad.top + 14;
    const u3PredictedLabelY = pad.top + 74;
    const ptIsVisible = ptX >= pad.left
      && ptX <= width - pad.right
      && ptY >= pad.top
      && ptY <= height - pad.bottom;

    if (ptIsVisible) {
      ctx.fillStyle = "#ffffff";
      ctx.strokeStyle = "#7c3aed";
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(ptX, ptY - 9);
      ctx.lineTo(ptX + 9, ptY);
      ctx.lineTo(ptX, ptY + 9);
      ctx.lineTo(ptX - 9, ptY);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();

      drawPtLabel(ctx, ptLabel, ptValue, ptX, ptY, pad, width, height, {
        placement: "below",
        side: fitMode === "u3" ? "right" : undefined,
        labelX: u3LabelX,
        labelY: fitMode === "u3" ? u3FitLabelY : undefined,
        gapX: fitMode === "u3" ? 48 : undefined,
        lineColor: "rgba(124, 58, 237, 0.62)",
        fillColor: "rgba(245, 243, 255, 0.96)",
        borderColor: "#c4b5fd",
        titleColor: "#5b21b6",
        valueColor: "#4c1d95",
      });
    }

    if (fitMode === "u3" && bilinearFit.predictedPoint) {
      const predictedMarker = bilinearFit.predictedPoint;
      const predictedX = scaleX(predictedMarker.displacement);
      const predictedY = scaleY(predictedMarker.force);
      const labelIsTooClose = Math.hypot(predictedX - ptX, predictedY - ptY) < 34;
      const predictedIsVisible = predictedX >= pad.left
        && predictedX <= width - pad.right
        && predictedY >= pad.top
        && predictedY <= height - pad.bottom;

      if (predictedIsVisible) {
        ctx.fillStyle = "#ef4444";
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.arc(predictedX, predictedY, 8, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();

        drawPtLabel(ctx, TEXT.predictedPtLabel, formatMetric(predictedMarker.force, 2), predictedX, predictedY, pad, width, height, {
          placement: labelIsTooClose ? "above" : "below",
          side: "right",
          labelX: u3LabelX,
          labelY: u3PredictedLabelY,
          gapX: 48,
          lineColor: "rgba(239, 68, 68, 0.62)",
          fillColor: "rgba(255, 247, 247, 0.96)",
          borderColor: "#fecaca",
          titleColor: "#991b1b",
          valueColor: "#7f1d1d",
        });
      }
    }
  }

  ctx.fillStyle = "#637184";
  ctx.font = "17px Inter, system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(TEXT.displacementAxis, pad.left + plotW / 2, height - 18);
  ctx.save();
  ctx.translate(24, pad.top + plotH / 2 + 24);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText(TEXT.forceAxis, 0, 0);
  ctx.restore();
}

function renderResponseEstimate(data) {
  renderResult(data);
  responseEstimate.classList.remove("hidden");
  responseCurveTitle.textContent = IS_KO ? "예측 곡선" : "Predicted curve";
  predictedPt.textContent = formatMetric(data.predicted_pt, 2);
  predictedMaxDisplacement.textContent = formatMetric(data.predicted_max_displacement, 5);
  predictedMaxForce.textContent = formatMetric(data.predicted_max_force, 2);
  updateResponseCurveLegend("standard");
  setResponseCurveSource(data.curve, data.predicted_pt, "standard", data.curve_fit);
  if (data.xai) {
    renderXai(data.xai);
  } else {
    requestLazyXai(data);
  }
  requestDesignSpace(data, "response");
  savePredictionHistory("response", data);
}

function renderU3PtResult(data) {
  latestPredictionData = data;
  document.body.classList.add("has-result");
  emptyState.classList.add("hidden");
  stackPreviewResult?.classList.add("hidden");
  resultPanel.classList.remove("hidden", "type-1", "type-2", "type-3");
  predictedType.textContent = data.predicted_type ? `u3 Type ${data.predicted_type}` : TEXT.u3PtTitle;
  confidenceEl.textContent = data.confidence != null ? percent(data.confidence) : formatMetric(data.predicted_pt, 2);
  modelLabel.textContent = displayModelLabel(data.model_label);

  const inputLabels = {
    theta1: "θ₁",
    theta2: "θ₂",
    case: "Case",
    test_id: "Test ID",
  };
  const inputValueLabels = {
    Case2: "Case 2",
    Case3: "Case 3",
    Case4: "Case 4",
  };
  inputSummary.innerHTML = "";
  Object.entries(data.inputs || {})
    .filter(([, value]) => value !== null && value !== "")
    .forEach(([key, value]) => {
      const item = document.createElement("span");
      item.className = "input-token";

      const label = document.createElement("strong");
      label.textContent = inputLabels[key] || key;

      const valueEl = document.createElement("span");
      valueEl.className = "input-token-value";
      valueEl.textContent = inputDisplayValue(key, value, inputValueLabels);

      item.append(label, valueEl);
      inputSummary.appendChild(item);
    });

  probabilityBars.innerHTML = "";
  if (data.probabilities) {
    renderProbabilities(data.probabilities);
  } else {
    const summary = document.createElement("p");
    summary.textContent = TEXT.u3ForecastSummary;
    probabilityBars.appendChild(summary);
  }
  renderUncertainty(data.uncertainty);
  renderTeacherStudentAgreement(null);

  responseEstimate.classList.remove("hidden");
  responseCurveTitle.textContent = IS_KO ? "예측 u3 곡선과 Pt" : "Predicted u3 curve with Pt";
  predictedPt.textContent = formatMetric(data.predicted_pt, 2);
  predictedMaxDisplacement.textContent = formatMetric(data.predicted_max_displacement, 5);
  predictedMaxForce.textContent = formatMetric(data.predicted_max_force, 2);
  updateResponseCurveLegend("u3");
  setResponseCurveSource(data.curve, data.predicted_pt, "u3", data.curve_fit);
  if (data.xai) {
    renderXai(data.xai);
  } else {
    requestLazyXai(data);
  }
  requestDesignSpace(data, "u3");

  notes.innerHTML = "";
  (data.notes || []).forEach((note) => {
    const item = document.createElement("li");
    item.textContent = IS_KO ? (NOTE_LABELS_KO[note] || note) : note;
    notes.appendChild(item);
  });
  savePredictionHistory("u3", data);
}

function parseCurveCsv(text) {
  return text
    .trim()
    .split(/\r?\n/)
    .map((line) => line.split(",").map((value) => Number(value.trim())))
    .filter((row) => row.length >= 2 && Number.isFinite(row[0]) && Number.isFinite(row[1]))
    .map(([displacement, force]) => ({ displacement, force }));
}

function drawEmptyCurvePreview(message = TEXT.selectCsv) {
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
  ctx.fillText(TEXT.displacementAxis, pad.left + plotW / 2, height - 12);
  ctx.save();
  ctx.translate(16, pad.top + plotH / 2 + 18);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText(TEXT.forceAxis, 0, 0);
  ctx.restore();

  ctx.textAlign = "left";
  ctx.fillText(formatMetric(maxY, 1), 8, pad.top + 4);
  ctx.fillText(formatMetric(minY, 1), 8, height - pad.bottom);
  ctx.textAlign = "right";
  ctx.fillText(formatMetric(maxX, 4), width - pad.right, height - 25);
}

function updateCurvePreview(points, fileName = TEXT.noFileSelected) {
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

function drawWrappedText(ctx, text, x, y, maxWidth, lineHeight, maxLines = 4) {
  const words = String(text || "").split(/\s+/).filter(Boolean);
  let line = "";
  let lines = 0;
  words.forEach((word) => {
    const candidate = line ? `${line} ${word}` : word;
    if (ctx.measureText(candidate).width > maxWidth && line) {
      if (lines < maxLines) {
        ctx.fillText(line, x, y + lines * lineHeight);
      }
      lines += 1;
      line = word;
    } else {
      line = candidate;
    }
  });
  if (line && lines < maxLines) {
    ctx.fillText(line, x, y + lines * lineHeight);
  }
}

function drawReportCard(ctx, x, y, width, height, label, value) {
  ctx.save();
  drawRoundedRect(ctx, x, y, width, height, 12);
  ctx.fillStyle = "#f8fbfd";
  ctx.fill();
  ctx.strokeStyle = "#d5e1ec";
  ctx.lineWidth = 1;
  ctx.stroke();
  ctx.fillStyle = "#607086";
  ctx.font = "800 17px Inter, system-ui, sans-serif";
  ctx.fillText(label, x + 22, y + 34);
  ctx.fillStyle = "#132236";
  ctx.font = "900 30px Inter, system-ui, sans-serif";
  ctx.fillText(value, x + 22, y + 78);
  ctx.restore();
}

function drawReportProbabilities(ctx, probabilities, x, y, width, height) {
  const entries = Object.entries(probabilities || {});
  if (!entries.length) {
    ctx.fillStyle = "#607086";
    ctx.font = "18px Inter, system-ui, sans-serif";
    ctx.fillText(TEXT.noProbability, x, y + 34);
    return;
  }

  const rowGap = 18;
  const rowH = (height - rowGap * (entries.length - 1)) / entries.length;
  const trackX = x + 128;
  const trackW = width - 220;
  ctx.font = "800 18px Inter, system-ui, sans-serif";
  ctx.textBaseline = "middle";
  entries.forEach(([label, value], index) => {
    const rowY = y + index * (rowH + rowGap);
    const safeValue = Math.max(0, Math.min(1, Number(value) || 0));
    ctx.fillStyle = "#607086";
    ctx.textAlign = "right";
    ctx.fillText(label.toUpperCase(), x + 104, rowY + rowH / 2);
    ctx.fillStyle = "#e6eef5";
    drawRoundedRect(ctx, trackX, rowY + rowH * 0.25, trackW, rowH * 0.5, 999);
    ctx.fill();
    ctx.fillStyle = "#0f91c9";
    drawRoundedRect(ctx, trackX, rowY + rowH * 0.25, Math.max(3, trackW * safeValue), rowH * 0.5, 999);
    ctx.fill();
    ctx.fillStyle = "#132236";
    ctx.textAlign = "left";
    ctx.fillText(percent(value), trackX + trackW + 22, rowY + rowH / 2);
  });
  ctx.textBaseline = "alphabetic";
  ctx.textAlign = "left";
}

function isReportVisible(element) {
  return Boolean(element && !element.classList.contains("hidden"));
}

function cleanReportText(text) {
  return String(text || "").replace(/\s+/g, " ").trim();
}

function reportDomLines(root, selector, limit = Number.POSITIVE_INFINITY) {
  if (!root) {
    return [];
  }
  return Array.from(root.querySelectorAll(selector))
    .map((element) => cleanReportText(element.textContent))
    .filter(Boolean)
    .slice(0, limit);
}

function wrapReportLines(ctx, text, maxWidth) {
  const words = cleanReportText(text).split(/\s+/).filter(Boolean);
  const lines = [];
  let line = "";
  words.forEach((word) => {
    const candidate = line ? `${line} ${word}` : word;
    if (ctx.measureText(candidate).width > maxWidth && line) {
      lines.push(line);
      line = word;
    } else {
      line = candidate;
    }
  });
  if (line) {
    lines.push(line);
  }
  return lines;
}

function drawReportHeader(ctx, title, x, y) {
  ctx.fillStyle = "#132236";
  ctx.font = "900 24px Inter, system-ui, sans-serif";
  ctx.fillText(title, x, y);
}

function drawReportTextBlock(ctx, lines, x, y, width, options = {}) {
  const font = options.font || "18px Inter, system-ui, sans-serif";
  const color = options.color || "#607086";
  const lineHeight = options.lineHeight || 27;
  const maxLines = options.maxLines || Number.POSITIVE_INFINITY;
  let drawn = 0;
  ctx.fillStyle = color;
  ctx.font = font;
  lines.filter(Boolean).some((line) => {
    const wrapped = wrapReportLines(ctx, line, width);
    return wrapped.some((wrappedLine) => {
      if (drawn >= maxLines) {
        return true;
      }
      ctx.fillText(wrappedLine, x, y + drawn * lineHeight);
      drawn += 1;
      return false;
    });
  });
  return y + Math.max(drawn, 1) * lineHeight;
}

function drawReportSection(ctx, title, lines, x, y, width, options = {}) {
  if (!lines.length && !options.force) {
    return y;
  }
  drawReportHeader(ctx, title, x, y);
  return drawReportTextBlock(ctx, lines, x, y + 36, width, options) + (options.gap ?? 34);
}

function reportXaiLines(data = {}) {
  if (!isReportVisible(xaiPanel) && !data.xai) {
    return [];
  }
  const lines = [];
  const title = cleanReportText(xaiTitle?.textContent || data.xai?.title);
  const summary = cleanReportText(xaiSummary?.textContent || data.xai?.summary);
  const method = cleanReportText(xaiMethod?.textContent || data.xai?.method);
  if (title) {
    lines.push(title);
  }
  if (summary) {
    lines.push(summary);
  }
  if (method) {
    lines.push(method);
  }

  const featureLines = xaiFeatures
    ? Array.from(xaiFeatures.querySelectorAll(".xai-feature")).map((feature, index) => {
      const label = cleanReportText(feature.querySelector(".xai-feature-head strong")?.textContent);
      const category = cleanReportText(feature.querySelector(".xai-feature-head span")?.textContent);
      const score = cleanReportText(feature.querySelector(".xai-feature-score span")?.textContent);
      const description = cleanReportText(feature.querySelector(".xai-feature-description")?.textContent);
      const headline = [label, category ? `(${category})` : "", score ? `- ${score}` : ""]
        .filter(Boolean)
        .join(" ");
      return `${index + 1}. ${headline}${description ? `: ${description}` : ""}`;
    }).filter(Boolean)
    : [];
  if (!featureLines.length) {
    featureLines.push(...reportDomLines(xaiFeatures, ".xai-loading"));
  }
  const noteLines = reportDomLines(xaiNotes, "li").map((line) => `${IS_KO ? "노트" : "Note"}: ${line}`);
  return [...lines, ...featureLines, ...noteLines];
}

function reportResearchLines(data = {}) {
  if (!isReportVisible(researchPanel) && !data.design_space) {
    return [];
  }
  const lines = [];
  const title = cleanReportText(researchTitle?.textContent);
  const summary = cleanReportText(researchSummary?.textContent);
  if (title) {
    lines.push(title);
  }
  if (summary) {
    lines.push(summary);
  }
  reportDomLines(researchComparison, ".comparison-card").forEach((line) => {
    lines.push(`${IS_KO ? "비교" : "Comparison"}: ${line}`);
  });
  reportDomLines(researchComparison, ".comparison-score i").forEach((line) => {
    lines.push(`${IS_KO ? "점수" : "Score"}: ${line}`);
  });
  reportDomLines(researchComparison, ".comparison-rationale").forEach((line) => {
    lines.push(line);
  });
  reportDomLines(researchCaseInsightList, ".case-insight-card").forEach((line) => {
    lines.push(`${IS_KO ? "Case 유리 영역" : "Case behavior zone"}: ${line}`);
  });
  reportDomLines(researchCaseList, ".case-risk-card").forEach((line) => {
    lines.push(`${IS_KO ? "Case 위험도" : "Case risk"}: ${line}`);
  });
  reportDomLines(researchNearestList, ".nearest-item").forEach((line) => {
    lines.push(`${IS_KO ? "가까운 해석" : "Nearest simulation"}: ${line}`);
  });
  reportDomLines(researchRecommendations, ".recommendation-card").forEach((line, index) => {
    lines.push(`${IS_KO ? "추천 후보" : "Recommended candidate"} ${index + 1}: ${line}`);
  });
  reportDomLines(researchNotes, "li").forEach((line) => {
    lines.push(`${IS_KO ? "노트" : "Note"}: ${line}`);
  });
  return lines;
}

function reportUncertaintyLines(data = {}) {
  const uncertainty = data.uncertainty;
  if (!uncertainty) {
    return [];
  }
  const ptLow = uncertainty.pt_interval_low;
  const ptHigh = uncertainty.pt_interval_high;
  const range = ptLow != null && ptHigh != null
    ? `${formatMetric(ptLow, 0)} - ${formatMetric(ptHigh, 0)}`
    : "-";
  return [
    `${TEXT.reliabilityScore}: ${percent(uncertainty.reliability_score)} (${uncertaintyLabelText(uncertainty.confidence_label)})`,
    `${TEXT.ptRange}: ${range}`,
    `${TEXT.designCoverage}: ${interpolationLabelText(uncertainty.interpolation_label)}`,
    `${TEXT.typeAgreement}: ${uncertainty.type_consistency != null ? percent(uncertainty.type_consistency) : "-"}`,
    ...(uncertainty.notes || []).slice(0, 2).map((note) => IS_KO ? translateUncertaintyNote(note) : note),
  ];
}

function reportResultNotes(data = {}) {
  const domNotes = reportDomLines(notes, "li");
  if (domNotes.length) {
    return domNotes;
  }
  return (data.notes || []).map((note) => IS_KO ? (NOTE_LABELS_KO[note] || note) : note);
}

function estimateReportHeight(data, sections) {
  const measureCanvas = document.createElement("canvas");
  const measureCtx = measureCanvas.getContext("2d");
  measureCtx.font = "18px Inter, system-ui, sans-serif";
  let height = 960;
  if (data.curve?.length) {
    height += 900;
  }
  if (isReportVisible(researchPanel) && researchMapCanvas) {
    height += 430;
  }
  sections.forEach((section) => {
    const wrappedLineCount = section.lines.reduce((count, line) => (
      count + Math.max(1, wrapReportLines(measureCtx, line, 1072).length)
    ), 0);
    height += 118 + wrappedLineCount * 32;
  });
  return Math.max(1200, Math.min(22000, height + 120));
}

function drawCanvasImage(ctx, sourceCanvas, x, y, width, height) {
  if (!sourceCanvas) {
    return;
  }
  ctx.save();
  drawRoundedRect(ctx, x, y, width, height, 12);
  ctx.fillStyle = "#f8fbfd";
  ctx.fill();
  ctx.clip();
  ctx.drawImage(sourceCanvas, x, y, width, height);
  ctx.restore();
  ctx.strokeStyle = "#d5e1ec";
  ctx.lineWidth = 1;
  drawRoundedRect(ctx, x, y, width, height, 12);
  ctx.stroke();
}

function reportInputText(inputs = {}) {
  const inputValueLabels = {
    Case2: "Case 2",
    Case3: "Case 3",
    Case4: "Case 4",
    Unknown: TEXT.unknown,
  };
  return [
    `θ₁ ${formatMetric(inputs.theta1, 0)}`,
    `θ₂ ${formatMetric(inputs.theta2, 0)}`,
    inputs.pt !== undefined && inputs.pt !== null ? `Pt ${formatMetric(inputs.pt, 2)}` : "",
    `${IS_KO ? "Case" : "Case"} ${inputValueLabels[inputs.case] || inputs.case || TEXT.unknown}`,
    inputs.test_id ? `Test ID ${inputs.test_id}` : "",
  ].filter(Boolean).join("   |   ");
}

function exportFileStem() {
  const inputs = latestPredictionData?.inputs || {};
  const caseName = inputs.case || "case";
  const theta1 = Number.isFinite(Number(inputs.theta1)) ? `t1_${Math.round(Number(inputs.theta1))}` : "t1";
  const theta2 = Number.isFinite(Number(inputs.theta2)) ? `t2_${Math.round(Number(inputs.theta2))}` : "t2";
  const stamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  return `double_double_${caseName}_${theta1}_${theta2}_${stamp}`;
}

function buildResultReportCanvas() {
  if (!latestPredictionData) {
    return null;
  }

  const data = latestPredictionData;
  const hasCurve = Boolean(data.curve?.length);
  const noteLines = reportResultNotes(data).map((note, index) => `${index + 1}. ${note}`);
  const uncertaintyLines = reportUncertaintyLines(data);
  const xaiLines = reportXaiLines(data);
  const researchLines = reportResearchLines(data);
  const sections = [
    { title: IS_KO ? "예측 안정성" : "Prediction Reliability", lines: uncertaintyLines },
    { title: "XAI", lines: xaiLines },
    { title: IS_KO ? "연구 인사이트" : "Research Insight", lines: researchLines },
    { title: TEXT.reportNotes, lines: noteLines },
  ].filter((section) => section.lines.length);
  const canvas = document.createElement("canvas");
  canvas.width = 1200;
  canvas.height = estimateReportHeight(data, sections);
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  ctx.fillStyle = "#0076bd";
  ctx.font = "900 28px Inter, system-ui, sans-serif";
  ctx.fillText("Composite AI", 64, 72);
  ctx.fillStyle = "#132236";
  ctx.font = "900 44px Inter, system-ui, sans-serif";
  ctx.fillText(TEXT.reportTitle, 64, 126);
  ctx.fillStyle = "#607086";
  ctx.font = "18px Inter, system-ui, sans-serif";
  ctx.fillText(`${TEXT.reportCreated}: ${new Date().toLocaleString()}`, 64, 164);

  const resultTitle = data.predicted_type ? `Type ${data.predicted_type}` : TEXT.u3PtTitle;
  const confidenceText = data.confidence !== undefined && data.confidence !== null
    ? percent(data.confidence)
    : (data.input_mode === "u3_pt" ? "Pt" : "-");
  drawReportCard(ctx, 64, 210, 250, 116, IS_KO ? "예측 결과" : "Prediction", resultTitle);
  drawReportCard(ctx, 338, 210, 250, 116, IS_KO ? "신뢰도" : "Confidence", confidenceText);
  drawReportCard(ctx, 612, 210, 250, 116, "Predicted Pt", formatMetric(data.predicted_pt ?? data.inputs?.pt, 2));
  drawReportCard(ctx, 886, 210, 250, 116, IS_KO ? "곡선 포인트" : "Curve points", String(data.curve?.length || "-"));

  let y = 386;
  y = drawReportSection(ctx, TEXT.reportInputs, [reportInputText(data.inputs)], 64, y, 1072, { gap: 30 });
  y = drawReportSection(ctx, IS_KO ? "모델" : "Model", [displayModelLabel(data.model_label)], 64, y, 1072, { gap: 34 });

  drawReportHeader(ctx, TEXT.reportProbabilities, 64, y);
  drawReportProbabilities(ctx, data.probabilities, 64, y + 34, 1072, 150);
  y += 224;

  if (hasCurve) {
    drawReportHeader(ctx, TEXT.reportCurve, 64, y);
    drawCanvasImage(ctx, responseCurveCanvas, 64, y + 30, 1072, 643);
    y += 740;
    drawReportCard(ctx, 64, y, 330, 104, "Max. Displacement", formatMetric(data.predicted_max_displacement, 5));
    drawReportCard(ctx, 428, y, 330, 104, "Max. Force", formatMetric(data.predicted_max_force, 2));
    drawReportCard(ctx, 792, y, 330, 104, "Input Mode", data.input_mode || "-");
    y += 170;
  }

  if (isReportVisible(researchPanel) && researchMapCanvas) {
    drawReportHeader(ctx, IS_KO ? "Design-space map" : "Design-space Map", 64, y);
    drawCanvasImage(ctx, researchMapCanvas, 64, y + 30, 1072, 476);
    y += 570;
  }

  sections.forEach((section) => {
    y = drawReportSection(ctx, section.title, section.lines, 64, y, 1072, {
      lineHeight: 30,
      gap: 40,
    });
  });

  if (y + 80 < canvas.height) {
    ctx.fillStyle = "#f1f7fb";
    ctx.fillRect(0, y + 20, canvas.width, canvas.height - y - 20);
  }

  return canvas;
}

function reportCanvasPageDataUrls(canvas, pageHeight = 1600) {
  const pages = [];
  for (let y = 0; y < canvas.height; y += pageHeight) {
    const sliceHeight = Math.min(pageHeight, canvas.height - y);
    const page = document.createElement("canvas");
    page.width = canvas.width;
    page.height = sliceHeight;
    const ctx = page.getContext("2d");
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, page.width, page.height);
    ctx.drawImage(canvas, 0, y, canvas.width, sliceHeight, 0, 0, page.width, sliceHeight);
    pages.push(page.toDataURL("image/png"));
  }
  return pages;
}

function exportReportAsPng() {
  try {
    const canvas = buildResultReportCanvas();
    if (!canvas) {
      setError(TEXT.reportNoResult);
      return;
    }
    canvas.toBlob((blob) => {
      if (!blob) {
        setError(TEXT.reportExportFailed);
        return;
      }
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${exportFileStem()}.png`;
      link.style.display = "none";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    }, "image/png");
  } catch (error) {
    setError(`${TEXT.reportExportFailed} ${error.message || error}`);
  }
}

function exportReportAsPdf() {
  try {
    const canvas = buildResultReportCanvas();
    if (!canvas) {
      setError(TEXT.reportNoResult);
      return;
    }
    const popup = window.open("", "_blank");
    if (!popup) {
      setError(IS_KO ? "팝업 차단을 해제한 뒤 다시 시도해 주세요." : "Allow pop-ups and try again.");
      return;
    }
    const pageImages = reportCanvasPageDataUrls(canvas);
    const pageMarkup = pageImages.map((dataUrl, index) => (
      `<section class="report-page"><img src="${dataUrl}" alt="${TEXT.reportTitle} ${index + 1}" /></section>`
    )).join("");
    popup.document.write(`<!doctype html><html><head><title>${TEXT.reportTitle}</title><style>
      body { margin: 0; padding: 24px; font-family: system-ui, sans-serif; color: #132236; background: #f4f8fb; }
      .report-page { width: 980px; margin: 0 auto 24px; break-after: page; page-break-after: always; }
      .report-page:last-of-type { break-after: auto; page-break-after: auto; }
      img { display: block; width: 100%; box-shadow: 0 18px 46px rgba(19,34,54,0.16); }
      p { max-width: 980px; margin: 16px auto 0; color: #607086; font-weight: 700; }
      @media print {
        body { padding: 0; background: #fff; }
        .report-page { width: 100%; margin: 0; }
        img { width: 100%; box-shadow: none; }
        p { display: none; }
      }
    </style></head><body>${pageMarkup}<p>${TEXT.reportPdfHint}</p></body></html>`);
    popup.document.close();
    popup.focus();
    popup.print();
  } catch (error) {
    setError(`${TEXT.reportExportFailed} ${error.message || error}`);
  }
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

async function ensurePredictionXaiForAssistant(data) {
  const inputs = data?.inputs || {};
  if (data?.xai || !data?.model_key || inputs.theta1 === undefined || inputs.theta2 === undefined || !inputs.case) {
    return data?.xai || null;
  }
  try {
    const xai = await postJson("/xai/local", {
      theta1: Number(inputs.theta1),
      theta2: Number(inputs.theta2),
      case: inputs.case,
      model: data.model_key,
      panel_a_in: Number(inputs.panel_a_in || 6),
      panel_b_in: Number(inputs.panel_b_in || 4),
    });
    latestPredictionData = { ...data, xai };
    renderXai(xai);
    return xai;
  } catch {
    return null;
  }
}

function buildAssistantPredictionContext(data, xai = data?.xai || null) {
  if (!data) {
    return null;
  }
  const topFeatures = Array.isArray(xai?.top_features)
    ? xai.top_features.slice(0, 8).map((feature) => ({
      name: feature.name,
      label: feature.label,
      category: feature.category,
      importance: feature.importance,
      local_sensitivity: feature.local_sensitivity,
      local_value: feature.local_value,
      perturbation: feature.perturbation,
      explanation: feature.explanation,
    }))
    : [];
  return {
    mode: data.model_key?.startsWith("u3_") ? "u3 Forecast" : "Laminate Forecast",
    inputs: data.inputs || {},
    model_key: data.model_key || "",
    model_label: data.model_label || "",
    predicted_type: data.predicted_type ?? null,
    confidence: data.confidence ?? null,
    probabilities: data.probabilities || null,
    predicted_pt: data.predicted_pt ?? null,
    predicted_max_displacement: data.predicted_max_displacement ?? null,
    predicted_max_force: data.predicted_max_force ?? null,
    xai: xai ? {
      title: xai.title,
      summary: xai.summary,
      method: xai.method,
      feature_set: xai.feature_set,
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
  const citationToggle = document.createElement("button");
  citationToggle.className = "rag-citation-toggle";
  citationToggle.type = "button";
  citationToggle.textContent = TEXT.ragShowCitations;
  citationToggle.setAttribute("aria-expanded", "false");
  actions.append(provider, citationToggle);
  head.append(title, actions);

  const answerText = document.createElement("p");
  answerText.className = "rag-answer-text";
  answerText.textContent = data.answer || "";

  const citationBlock = document.createElement("div");
  citationBlock.className = "rag-citations hidden";
  const citationTitle = document.createElement("strong");
  citationTitle.textContent = TEXT.ragCitations;
  citationBlock.append(citationTitle);

  (data.citations || []).forEach((citation) => {
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

  citationToggle.addEventListener("click", () => {
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

if (ragQueryInput) {
  ragQueryInput.addEventListener("focus", clearDefaultRagQuestion, { once: true });
  ragQueryInput.addEventListener("beforeinput", clearDefaultRagQuestion, { once: true });
}

document.querySelectorAll(".mode-button").forEach((button) => {
  button.addEventListener("click", () => {
    const previousMode = document.querySelector(".mode-button.active")?.dataset.mode;
    const mode = button.dataset.mode;
    if (mode !== previousMode) {
      resetPredictionState();
    }
    document.querySelectorAll(".mode-button").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    if (thetaForm) {
      thetaForm.classList.toggle("active", mode === "theta");
    }
    curveForm.classList.toggle("active", mode === "curve");
    responseForm.classList.toggle("active", mode === "response");
    if (u3PtForm) {
      u3PtForm.classList.toggle("active", mode === "u3");
    }
    if (stackPreviewForm) {
      stackPreviewForm.classList.toggle("active", mode === "stack");
    }
    visualPanel.classList.toggle("hidden", mode === "curve");
    curvePreviewPanel.classList.toggle("hidden", mode !== "curve");
    workspaceGrid.classList.toggle("curve-active", mode === "curve");
    workspaceGrid.classList.toggle("u3-active", mode === "u3");
    workspaceGrid.classList.toggle("stack-active", mode === "stack");
    summaryStrip?.classList.toggle("curve-active", mode === "curve");
    summaryStrip?.classList.toggle("u3-active", mode === "u3");
    summaryStrip?.classList.toggle("stack-active", mode === "stack");
    updateDynamicStackPreview();
    renderPredictionHistory();
    clearError();
    inputPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

if (thetaForm) {
  thetaForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearError();
    setLoading(thetaForm, true);
    const formData = new FormData(thetaForm);
    try {
      const data = await postJson("/predict/theta", {
        theta1: clampStackAngle(formData.get("theta1")),
        theta2: clampStackAngle(formData.get("theta2")),
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
}

curveForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();
  setLoading(curveForm, true);
  const formData = new FormData(curveForm);
  formData.set("theta1", String(clampStackAngle(formData.get("theta1"))));
  formData.set("theta2", String(clampStackAngle(formData.get("theta2"))));
  try {
    curveBatchResults?.classList.add("hidden");
    const selectedFiles = Array.from(curveFile.files || []);
    if (selectedFiles.length > 1) {
      const batchData = new FormData();
      selectedFiles.forEach((file) => batchData.append("files", file));
      const metadata = curveMetadataFile?.files?.[0];
      if (metadata) {
        batchData.append("metadata_file", metadata);
      }
      ["theta1", "theta2", "pt", "case", "model"].forEach((key) => {
        batchData.set(key, formData.get(key));
      });
      const data = await postForm("/predict/curve-batch", batchData);
      renderCurveBatchResults(data, Boolean(metadata));
    } else {
      const data = await postForm("/predict/curve", formData);
      renderResult(data);
    }
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
    const selectedModel = String(formData.get("model") || "response_geometry_tree_v1");
    const useTeacherStudent = selectedModel === "response_geometry_tree_v1";
    const data = await postJson(useTeacherStudent ? "/predict/response-ensemble" : "/predict/response", {
      theta1: clampStackAngle(formData.get("theta1")),
      theta2: clampStackAngle(formData.get("theta2")),
      case: formData.get("case"),
      ...(useTeacherStudent
        ? {
          teacher_model: "response_geometry_tree_v1",
          student_model: "response_hybrid_student_deploy_quick_v1",
        }
        : { model: selectedModel }),
      panel_a_in: Number(formData.get("panel_a_in") || 6),
      panel_b_in: Number(formData.get("panel_b_in") || 4),
    });
    renderResponseEstimate(data);
  } catch (error) {
    setError(error.message);
  } finally {
    setLoading(responseForm, false);
  }
});

if (u3PtForm) {
  u3PtForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearError();
    setLoading(u3PtForm, true);
    const formData = new FormData(u3PtForm);
    try {
      const selectedModel = String(formData.get("model") || "");
      const data = await postJson("/predict/u3-forecast", {
        theta1: clampStackAngle(formData.get("theta1")),
        theta2: clampStackAngle(formData.get("theta2")),
        case: formData.get("case"),
        test_id: "Forecast",
        model: selectedModel,
      });
      renderU3PtResult(data);
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(u3PtForm, false);
    }
  });
}

if (stackPreviewForm) {
  stackPreviewForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearError();
    setLoading(stackPreviewForm, true);
    const formData = new FormData(stackPreviewForm);
    const theta1 = clampStackAngle(formData.get("theta1"));
    const theta2 = clampStackAngle(formData.get("theta2"));
    const { sequence: plySequence } = stackSequenceFromFormulaOrManual(formData, theta1, theta2);
    try {
      if (!plySequence.length) {
        throw new Error(TEXT.stackSequenceFailed);
      }
      const data = await postJson("/stack/preview", {
        theta1,
        theta2,
        case: formData.get("case"),
        formula: String(formData.get("formula") || ""),
        ply_sequence: plySequence,
      });
      renderStackPreviewResult(data);
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(stackPreviewForm, false);
    }
  });
}

async function previewCsvFile(fileInput) {
  clearError();
  const file = fileInput.files[0];
  if (!file) {
    updateCurvePreview([]);
    return;
  }
  try {
    const text = await file.text();
    const points = parseCurveCsv(text);
    if (!points.length) {
      throw new Error(TEXT.csvPreviewFailed);
    }
    updateCurvePreview(points, file.name);
  } catch (error) {
    updateCurvePreview([], file.name);
    drawEmptyCurvePreview(TEXT.csvParseFailed);
    setError(error.message);
  }
}

curveFile.addEventListener("change", () => previewCsvFile(curveFile));

if (exportReportPng) {
  exportReportPng.addEventListener("click", exportReportAsPng);
}

if (exportReportPdf) {
  exportReportPdf.addEventListener("click", exportReportAsPdf);
}

if (researchMapCanvas) {
  researchMapCanvas.addEventListener("mousemove", handleResearchMapPointer);
  researchMapCanvas.addEventListener("click", handleResearchMapPointer);
  researchMapCanvas.addEventListener("mouseleave", () => {
    researchMapCanvas.style.cursor = "default";
    hideResearchMapTooltip();
  });
  document.addEventListener("mousemove", handleResearchMapDocumentPointer);
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
      const predictionXai = await ensurePredictionXaiForAssistant(latestPredictionData);
      const data = await postRagJson("/answer", {
        query: String(formData.get("query") || ""),
        top_k: 5,
        use_llm: formData.get("use_llm") === "on",
        language: IS_KO ? "ko" : "en",
        prediction_context: buildAssistantPredictionContext(latestPredictionData, predictionXai),
      });
      renderRagAnswer(data);
    } catch (error) {
      setError(`${TEXT.ragFailed} ${error.message}`);
    } finally {
      if (submitButton) {
        submitButton.textContent = originalText;
      }
      setLoading(ragForm, false);
    }
  });
}

setupThetaSliders(responseForm);
setupThetaSliders(u3PtForm);
setupThetaSliders(stackPreviewForm);
attachDynamicStackPreview(responseForm);
attachDynamicStackPreview(u3PtForm);
attachDynamicStackPreview(stackPreviewForm);
attachFormulaToolbar(stackPreviewForm);

clearCurvePreview.addEventListener("click", () => {
  curveFile.value = "";
  if (curveMetadataFile) {
    curveMetadataFile.value = "";
  }
  curveBatchResults?.classList.add("hidden");
  if (curveBatchResults) {
    curveBatchResults.innerHTML = "";
  }
  updateCurvePreview([]);
  clearError();
});

installResponseCurveZoomControls();
updateCurvePreview([]);
updateDynamicStackPreview();
renderPredictionHistory();
loadModels();
