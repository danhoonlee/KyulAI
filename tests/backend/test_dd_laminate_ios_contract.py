from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import pytest
from fastapi.testclient import TestClient

from src.backend.dd_laminate_app import app

FIXTURE_PATH = Path("tests/fixtures/dd_laminate/predict_response_case2.json")
REQUIRED_RESPONSE_FIELDS = {
    "predicted_type",
    "confidence",
    "probabilities",
    "model_key",
    "model_label",
    "input_mode",
    "inputs",
    "notes",
    "features",
    "predicted_pt",
    "predicted_max_displacement",
    "predicted_max_force",
    "curve",
    "metrics",
}


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("IMPERIALAX_DISABLE_AUTH_FOR_LOCAL_DEV", "1")
    monkeypatch.delenv("IMPERIALAX_ENV", raising=False)
    return TestClient(app)


@pytest.fixture()
def ios_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_ios_fixture_documents_response_prediction_contract(ios_fixture: dict) -> None:
    assert ios_fixture["method"] == "POST"
    assert ios_fixture["endpoint"] == "/api/v1/dd-laminate/predict/response"
    assert ios_fixture["request"] == {
        "theta1": 30,
        "theta2": -30,
        "case": "Case2",
        "model": "response_geometry_tree_canonical_v2",
        "panel_a_in": 6.0,
        "panel_b_in": 4.0,
    }

    response = ios_fixture["response"]
    assert REQUIRED_RESPONSE_FIELDS.issubset(response)
    assert response["input_mode"] == "response"
    assert response["model_key"] == "response_geometry_tree_canonical_v2"
    assert response["inputs"] == {
        "theta1": 30.0,
        "theta2": -30.0,
        "case": "Case2",
        "panel_a_in": 6.0,
        "panel_b_in": 4.0,
    }
    assert isinstance(response["predicted_type"], int)
    assert isinstance(response["notes"], list)
    assert response["curve"], "fixture should include chart-ready force-displacement points"
    assert {"displacement", "force"}.issubset(response["curve"][0])


def test_standalone_dd_laminate_app_health_and_models_for_mobile(client: TestClient) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    ready = client.get("/ready")
    assert ready.status_code == 200
    ready_data = ready.json()
    assert ready_data["status"] == "ready"
    assert set(ready_data["models"]) == {
        "response_geometry_tree_canonical_v2",
        "response_geometry_goint_canonical_v2",
        "response_hybrid_student_canonical_v2",
        "u3_forecast_physics_canonical_v2",
        "u3_forecast_goint_physics_canonical_v2",
    }
    assert all(status == "ok" for status in ready_data["models"].values())

    models = client.get("/api/v1/dd-laminate/models")
    assert models.status_code == 200
    data = models.json()
    assert {"theta_models", "curve_models", "response_models"}.issubset(data)

    response_models = {model["key"]: model for model in data["response_models"]}
    assert list(response_models) == [
        "response_geometry_tree_canonical_v2",
        "response_geometry_goint_canonical_v2",
        "response_hybrid_student_canonical_v2",
    ]
    assert response_models["response_geometry_tree_canonical_v2"]["input_mode"] == "response"
    assert (
        response_models["response_geometry_tree_canonical_v2"]["label"]
        == "Laminate Forecast - Machine Learning"
    )
    assert "available" in response_models["response_geometry_tree_canonical_v2"]

    u3_pt_models = {model["key"]: model for model in data["u3_pt_models"]}
    assert list(u3_pt_models) == [
        "u3_forecast_physics_canonical_v2",
        "u3_forecast_goint_physics_canonical_v2",
    ]
    assert u3_pt_models["u3_forecast_physics_canonical_v2"]["input_mode"] == "u3_pt"
    assert (
        u3_pt_models["u3_forecast_physics_canonical_v2"]["label"]
        == "u3 Forecast - Machine Learning"
    )
    assert "available" in u3_pt_models["u3_forecast_physics_canonical_v2"]


def test_three_size_preview_models_and_page_are_isolated_from_mobile_registry(
    client: TestClient,
) -> None:
    preview_models = client.get("/api/v1/dd-laminate/models/3size-preview")

    assert preview_models.status_code == 200
    models = preview_models.json()
    assert [model["key"] for model in models] == [
        "response_pt_consistent_tree_3size_grouped_v1",
        "response_pt_consistent_goint_3size_grouped_v1",
        "response_pt_consistent_hybrid_3size_grouped_v1",
    ]
    assert all(model["input_mode"] == "response" for model in models)
    assert all(model["available"] for model in models)

    production_models = client.get("/api/v1/dd-laminate/models").json()["response_models"]
    assert [model["key"] for model in production_models] == [
        "response_geometry_tree_canonical_v2",
        "response_geometry_goint_canonical_v2",
        "response_hybrid_student_canonical_v2",
    ]

    preview_page = client.get("/preview/3size")
    assert preview_page.status_code == 200
    assert "ImperialAX Laminate Forecast" in preview_page.text
    assert (
        "Forecast laminate Type, Pt, and response curve from case and theta inputs."
        in preview_page.text
    )
    assert "Case와 theta 입력으로" not in preview_page.text
    assert "/app-v2.js" in preview_page.text
    assert preview_page.headers["x-robots-tag"] == "noindex, nofollow"
    assert 'name="panel_a_in"' in preview_page.text
    assert 'name="panel_b_in"' in preview_page.text

    korean_preview_page = client.get("/preview/3size?lang=ko")
    assert korean_preview_page.status_code == 200
    assert '<html lang="ko">' in korean_preview_page.text
    assert "Double-Double 적층 예측" in korean_preview_page.text
    assert (
        "Case와 theta 입력으로 적층 Type, Pt, 응답 곡선을 예측합니다." in korean_preview_page.text
    )
    assert "Forecast laminate Type" not in korean_preview_page.text

    for asset_path in (
        "/preview/styles-v2.css",
        "/preview/app-v2.js",
        "/preview/auth-gate.js",
        "/preview/3size/styles-v2.css",
        "/preview/3size/app-v2.js",
        "/preview/3size/auth-gate.js",
    ):
        assert client.get(asset_path).status_code == 200

    rejected = client.post(
        "/api/v1/dd-laminate/predict/response/3size-preview",
        json={
            "theta1": 30,
            "theta2": -30,
            "case": "Case2",
            "model": "response_geometry_tree_canonical_v2",
            "panel_a_in": 6.0,
            "panel_b_in": 4.0,
        },
    )
    assert rejected.status_code == 422
    assert "only accepts preview model keys" in rejected.json()["detail"]


def test_main_web_laminate_forecast_uses_three_size_pt_consistent_models(
    client: TestClient,
) -> None:
    script_response = client.get("/app-v2.js")

    assert script_response.status_code == 200
    script = script_response.text
    primary_models = script.split("const PRIMARY_RESPONSE_MODEL_KEYS = [", 1)[1].split("];", 1)[0]
    assert "response_pt_consistent_tree_3size_grouped_v1" in primary_models
    assert "response_pt_consistent_goint_3size_grouped_v1" in primary_models
    assert "response_pt_consistent_hybrid_3size_grouped_v1" in primary_models
    assert "response_geometry_tree_canonical_v2" not in primary_models
    assert "fetch(`${API_BASE}/models/3size-preview`)" in script
    assert '? "/predict/response/3size-preview"' in script
    assert '? "three_size"' in script
    assert 'stroke="#edf7ff"' not in script
    assert "M118 42 L992 524" not in script


def test_three_size_preview_tree_has_live_local_xai(client: TestClient) -> None:
    response = client.post(
        "/api/v1/dd-laminate/xai/local",
        json={
            "theta1": 30,
            "theta2": -30,
            "case": "Case2",
            "model": "response_pt_consistent_tree_3size_grouped_v1",
            "panel_a_in": 6.0,
            "panel_b_in": 4.0,
        },
    )

    assert response.status_code == 200
    xai = response.json()
    assert xai["top_features"]
    assert len(xai["top_features"]) > 5
    assert sum(feature["importance"] for feature in xai["top_features"]) == pytest.approx(
        1.0, abs=5e-6
    )
    assert max(feature["importance"] for feature in xai["top_features"]) < 1.0
    assert "panel geometry" in xai["feature_set"]
    assert "Tree ensemble" in xai["method"]
    assert "3-size model directly" in " ".join(xai["notes"])


def test_three_size_preview_design_space_matches_selected_panel(client: TestClient) -> None:
    response = client.post(
        "/api/v1/dd-laminate/design-space",
        json={
            "theta1": 30,
            "theta2": -30,
            "case": "Case2",
            "scope": "response",
            "dataset": "three_size",
            "panel_a_in": 8.0,
            "panel_b_in": 8.0,
        },
    )

    assert response.status_code == 200
    insight = response.json()
    assert insight["map_points"]
    assert len(insight["map_points"]) == 900
    assert {
        case: sum(point["case"] == case for point in insight["map_points"])
        for case in ("Case2", "Case3", "Case4")
    } == {"Case2": 300, "Case3": 300, "Case4": 300}
    assert all(point["test_id"] for point in insight["map_points"])
    assert {point["source"] for point in insight["map_points"]} == {"three_size_response"}
    assert insight["inputs"]["panel_a_in"] == 8.0
    assert insight["inputs"]["panel_b_in"] == 8.0
    assert "8\u00d78 in panel" in " ".join(insight["notes"])


@pytest.mark.parametrize(
    "model_key",
    [
        "response_pt_consistent_goint_3size_grouped_v1",
        "response_pt_consistent_hybrid_3size_grouped_v1",
    ],
)
def test_pt_consistent_deep_preview_keeps_raw_curve_and_exact_p1_pt(
    client: TestClient,
    model_key: str,
) -> None:
    response = client.post(
        "/api/v1/dd-laminate/predict/response/3size-preview",
        json={
            "theta1": 30,
            "theta2": -25,
            "case": "Case2",
            "model": model_key,
            "panel_a_in": 6.0,
            "panel_b_in": 4.0,
        },
    )

    assert response.status_code == 200
    data = response.json()
    fit = data["curve_fit"]
    kink = fit["kink"]
    first_line = fit["first_line"]
    second_line = fit["second_line"]
    kink_x = kink["displacement"]

    assert len(data["curve"]) == 128
    assert data["predicted_max_force"] == pytest.approx(data["curve"][-1]["force"], rel=0.1)
    assert kink["force"] == pytest.approx(data["predicted_pt"])
    assert first_line["slope"] * kink_x + first_line["intercept"] == pytest.approx(
        data["predicted_pt"]
    )
    assert second_line["slope"] * kink_x + second_line["intercept"] == pytest.approx(
        data["predicted_pt"]
    )
    assert data["metrics"]["response_output_mode"] == "pt_consistent_p1_head_v1"
    assert data["metrics"]["displayed_p1_direct_pt_gap"] == 0.0
    assert data["metrics"]["pt_curve_force_postprocessing_applied"] == 0.0


def test_design_space_endpoint_returns_research_context(client: TestClient) -> None:
    response = client.post(
        "/api/v1/dd-laminate/design-space",
        json={"theta1": 30, "theta2": -30, "case": "Case2", "scope": "response"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["scope"] == "response"
    assert data["inputs"] == {"theta1": 30.0, "theta2": -30.0, "case": "Case2"}
    assert data["map_points"]
    assert data["nearest_points"]
    assert len(data["case_summaries"]) == 3
    assert len(data["case_insights"]) == 3
    assert data["recommendations"]
    assert {"case", "risk_score", "risk_label", "type_rates"}.issubset(data["case_summaries"][0])
    assert {"case", "focus_kind", "focus_rate", "best_pt"}.issubset(data["case_insights"][0])
    assert {"pt", "type", "proximity", "pt_raw", "type_raw", "proximity_raw"}.issubset(
        data["recommendations"][0]["score_components"]
    )


def test_u3_design_space_endpoint_returns_curve_family_context(client: TestClient) -> None:
    response = client.post(
        "/api/v1/dd-laminate/design-space",
        json={"theta1": -20, "theta2": 74, "case": "Case4", "scope": "u3"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["scope"] == "u3"
    assert data["map_points"]
    assert data["nearest_points"]
    assert data["case_summaries"]
    assert data["case_insights"]
    assert data["recommendations"]
    assert {insight["focus_kind"] for insight in data["case_insights"]} == {"high_pt"}
    assert {"pt", "type", "proximity"}.issubset(data["recommendations"][0]["score_components"])
    assert all(point["source"] == "curated_u3" for point in data["nearest_points"])


def test_legacy_cafedecafe_hosts_are_not_treated_as_laminate_deployments(
    client: TestClient,
) -> None:
    for host in ("laminate.cafedecafe.co.kr", "cafedecafe.co.kr"):
        response = client.get("/", headers={"host": host})

        assert response.status_code == 200
        assert "Composite Laminate AI" not in response.text


def test_public_root_serves_established_laminate_for_imperialax(client: TestClient) -> None:
    response = client.get("/", headers={"host": "laminate.imperialax.com"})

    assert response.status_code == 200
    assert "복합재 적층 AI" in response.text
    assert "후보 조건 설정" not in response.text
    assert "/app-v2.js?v=20260819-viewer-fiber-4" in response.text
    assert "/imperialax-product-shell.css?v=20260816-mobile-polish-1" in response.text
    assert "Case·각도 설정" in response.text
    assert "패널·적층 확인" in response.text
    assert "/imperialax-product-shell.js?v=20260814-family-shell-1" in response.text
    assert 'data-dialog-target="research-dialog"' in response.text
    assert 'data-dialog-target="assistant-dialog"' in response.text
    assert 'class="product-logo-link"' in response.text
    assert "/assets/imperialax-logo-black.png?v=20260814-logo-rollout-1" in response.text
    assert '<dialog class="utility-dialog" id="research-dialog"' in response.text
    assert '<dialog class="utility-dialog" id="assistant-dialog"' in response.text
    assert 'href="/en">English</a>' in response.text
    assert response.text.index("header-action-module") < response.text.index(
        "header-action-assistant"
    )
    assert response.text.index("header-action-assistant") < response.text.index(
        "header-action-research"
    )
    assert response.text.index("header-action-research") < response.text.index(
        "header-action-language"
    )
    assert response.text.index("header-action-language") < response.text.index(
        "header-action-status"
    )


def test_laminate_established_ui_is_root_and_rebuild_moves_to_v2(
    client: TestClient,
) -> None:
    headers = {"host": "laminate.imperialax.com"}
    root = client.get("/", headers=headers)
    root_ko = client.get("/ko", headers=headers)
    root_en = client.get("/en", headers=headers)
    rebuild = client.get("/v2", headers=headers)
    rebuild_slash = client.get("/v2/", headers=headers, follow_redirects=False)
    rebuild_ko = client.get("/v2/ko", headers=headers)
    rebuild_en = client.get("/v2/en", headers=headers)

    assert root.status_code == 200
    assert root_ko.status_code == 200
    assert root_en.status_code == 200

    assert "복합재 적층 AI" in root.text
    assert 'href="/en">English</a>' in root.text
    assert "복합재 적층 AI" in root_ko.text
    assert 'href="/en">English</a>' in root_ko.text
    assert "Composite Laminate AI" in root_en.text
    assert 'href="/ko">한국어</a>' in root_en.text
    assert "Set case and angles" in root_en.text
    assert "Check panel and stack" in root_en.text
    for response in (root, root_ko, root_en):
        assert "후보 조건 설정" not in response.text
        assert "/styles-rebuild.css" not in response.text
        assert "/app-rebuild-preview.js" not in response.text
        assert "/imperialax-product-shell.css?v=20260816-mobile-polish-1" in response.text
        assert "/auth-gate.js?v=20260814-header-utilities-1" in response.text
        assert response.text.index("header-action-module") < response.text.index(
            "header-action-assistant"
        )
        assert response.text.index("header-action-assistant") < response.text.index(
            "header-action-research"
        )
        assert response.text.index("header-action-research") < response.text.index(
            "header-action-language"
        )
        assert response.text.index("header-action-language") < response.text.index(
            "header-action-status"
        )
        assert response.headers.get("x-robots-tag") is None

    for response in (rebuild, rebuild_ko, rebuild_en):
        assert response.status_code == 200
        assert "/styles-rebuild.css?v=20260816-mobile-polish-2" in response.text
        assert "/locales-rebuild.js?v=20260813-mobile-design-space-1" in response.text
        assert "/app-rebuild-preview.js?v=20260816-clean-preview-1" in response.text
        assert 'id="stack-preview-visual"' in response.text
        assert 'id="stack-preview-summary"' in response.text
        assert 'id="rebuild-summary-curve-canvas"' in response.text
        assert 'id="summary-stack-visual"' in response.text
        assert 'id="tab-ply"' in response.text
        assert 'id="panel-ply"' in response.text
        assert 'id="result-stack-visual"' in response.text
        assert 'id="result-ply-sequence"' in response.text
        assert 'class="result-metric-strip"' in response.text
        assert 'id="result-context"' in response.text
        assert 'id="rebuild-curve-zoom-label"' in response.text
        assert 'data-curve-zoom="in"' in response.text
        assert 'class="space-map-legend"' in response.text
        assert "이 결과를 믿을 근거" not in response.text
        assert 'id="metric-decision-state"' not in response.text
        assert "/assets/imperialax-logo-black.png?v=20260812-v2-logo-1" in response.text
        assert response.text.count('value="response_pt_consistent_') == 3
        assert 'value="response_geometry_tree_canonical_v2"' not in response.text
        assert 'value="response_geometry_goint_canonical_v2"' not in response.text
        assert 'value="response_hybrid_student_canonical_v2"' not in response.text
        assert response.headers.get("x-robots-tag") is None
    for response in (rebuild, rebuild_ko):
        assert '<html lang="ko">' in response.text
        assert "후보 조건 설정" in response.text
        assert 'href="/">현재 운영 화면</a>' in response.text
        assert "P1 선형 피팅" in response.text
    assert '<html lang="en">' in rebuild_en.text
    assert "Candidate setup" in rebuild_en.text
    assert 'href="/">Current production UI</a>' in rebuild_en.text
    assert not re.search(r"[가-힣]", rebuild_en.text)

    assert rebuild.status_code == 200
    assert rebuild_ko.status_code == 200
    assert rebuild_en.status_code == 200
    assert rebuild_slash.status_code == 308
    assert rebuild_slash.headers["location"] == "/v2"

    assert client.head("/", headers=headers).status_code == 200
    assert client.head("/ko", headers=headers).status_code == 200
    assert client.head("/en", headers=headers).status_code == 200
    assert client.head("/v2", headers=headers).status_code == 200
    assert client.get("/styles-rebuild.css", headers=headers).status_code == 200
    assert (
        "grid-template-columns: 400px minmax(0, 1fr);"
        in client.get("/styles-rebuild.css", headers=headers).text
    )
    locale_pack = client.get("/locales-rebuild.js", headers=headers)
    assert locale_pack.status_code == 200
    assert '"Candidate setup"' in locale_pack.text
    assert 'angle_min_abs: ["최소 |θ|"' in locale_pack.text
    assert "function localizeXaiFeature" in locale_pack.text
    logo = client.get("/assets/imperialax-logo-black.png", headers=headers)
    assert logo.status_code == 200
    assert logo.headers["content-type"] == "image/png"
    script = client.get("/app-rebuild-preview.js", headers=headers)
    assert script.status_code == 200
    assert "localizeXaiFeature(feature)" in script.text
    assert 'category.className = "xai-category"' in script.text
    assert 'meta.className = "xai-feature-meta"' in script.text
    assert "function buildStackSequence" in script.text
    assert "function renderStackPreview" in script.text
    assert "function renderPlySequence" in script.text
    assert 'style="--ply-angle: ${visualAngle}deg"' in script.text
    assert "function drawSummaryCurve" in script.text
    assert "function buildCurveRenderModel" in script.text
    assert 'height="320" aria-label="요약 예측 응답 곡선"' in rebuild_ko.text
    assert 'height="480" aria-label="예측 응답 곡선"' in rebuild_ko.text
    assert 'resultWorkspace.classList.toggle("has-result", hasResult)' in script.text
    styles = client.get("/styles-rebuild.css", headers=headers).text
    established_styles = client.get("/styles-v2.css", headers=headers).text
    assert ".result-workspace.has-result .tab-panels" in styles
    assert ".result-workspace.has-result .summary-stack-visual .ply-sequence-cell" in styles
    assert "min-height: 44px;" in styles
    assert "height: clamp(228px, 70vw, 272px);" in established_styles
    assert (
        'const mobileMap = window.matchMedia("(max-width: 760px)").matches;'
        in client.get("/app-v2.js", headers=headers).text
    )
    assert (
        "const targetHeight = mobileMap ? 500 : 320;"
        in client.get("/app-v2.js", headers=headers).text
    )
    assert 'id="result-empty-state"' in rebuild_ko.text
    assert 'id="show-example-result"' in rebuild_ko.text
    assert (
        'class="result-tabs" role="tablist" aria-label="예측 결과 보기" hidden' in rebuild_ko.text
    )
    assert 'class="tab-panels" hidden' in rebuild_ko.text
    assert 'id="comparison-table" hidden' in rebuild_ko.text
    assert "let runs = [];" in script.text
    assert 'source: "example"' in script.text
    assert "function setResultPresence" in script.text
    assert "function showExampleResult" in script.text
    assert "function setDetailedCurveZoom" in script.text
    assert "function panDetailedCurve" in script.text
    assert 'detailedCurveCanvas?.addEventListener("wheel"' in script.text
    assert 'detailedCurveCanvas?.addEventListener("pointermove"' in script.text
    assert "pointers: new Map()" in script.text
    assert "function detailedCurvePinchMetrics" in script.text
    assert "detailedCurveView.pointers.size >= 2" in script.text
    assert "detailedCurveView.pinch.startScale * factor" in script.text
    assert 'window.matchMedia("(max-width: 620px)").matches' in script.text
    assert "(canvas === summaryCurveCanvas || canvas === detailedCurveCanvas)" in script.text
    assert "clampNumber(Math.round(width * 0.64), 220, 280)" in script.text
    assert "canvas === designSpaceCanvas && isMobileViewport" in script.text
    assert "clampNumber(Math.round(width * 0.98), 340, 440)" in script.text
    assert "const labelWidth = compactMobileChart ? 88 : 124" in script.text
    assert "const tickCount = compactMobileChart ? 4 : 6" in script.text
    assert 'querySelectorAll("[data-open-deep]")' in script.text
    assert 'patternTransform="rotate(${-ply.angle})"' in script.text
    assert "const x = 555 - index * 30" in script.text
    assert "const y = 470 - index * 28" in script.text
    assert "function panelLengthScale(panelA)" in script.text
    assert "function panelWidthScale(panelB)" in script.text
    assert "function stackPlyGeometry(lengthScale, widthScale)" in script.text
    assert "const lengthScale = panelLengthScale(values.panelA)" in script.text
    assert "const widthScale = panelWidthScale(values.panelB)" in script.text
    assert 'data-panel-length="${values.panelA}"' in script.text
    assert 'data-panel-width="${values.panelB}"' in script.text
    assert '<svg viewBox="0 0 1160 760"' in script.text
    assert 'fill="#eef1f5" stroke="#d7dce5"' in script.text
    assert 'stroke="#cbd2dc"' not in script.text
    assert "M118 42 L992 524" not in script.text
    assert 'transform="translate(540 0) scale(-1 1)"' not in script.text
    assert '"/predict/response/3size-preview"' in script.text
    assert '"/xai/local"' in script.text
    assert '"/design-space"' in script.text
    assert "minimumFractionDigits: 2, maximumFractionDigits: 2" in script.text
    assert "twoDecimalFormatter.format(result.pt)" in script.text
    assert "twoDecimalFormatter.format(result.maxForce || result.pt * 1.25)" in script.text
    assert "const firstLine = fit.first_line || fit.firstLine" in script.text
    assert "const secondLine = fit.second_line || fit.secondLine" in script.text
    assert "ctx.setLineDash([7, 5])" in script.text
    assert 'fetchJson("/models/3size-preview"' in script.text
    assert 'fetchJson("/predict/response/3size-preview"' in script.text
    assert 'dataset: "three_size"' in script.text
    assert "}, 30000)" in script.text
    assert "Math.abs(number(feature.importance)) * 100" in script.text
    assert " / maxImportance" not in script.text
    assert 'designSpaceCanvas?.addEventListener("pointermove"' in script.text
    assert 'designSpaceCanvas?.addEventListener("pointerdown"' in script.text
    assert "function renderDesignSpaceTooltip" in script.text
    assert "const canvasX = cssX;" in script.text
    assert "designSpaceCanvas.width / rect.width" not in script.text
    assert "const xaiPrimaryFeatureCount = 5" in script.text
    assert "features.slice(0, xaiPrimaryFeatureCount)" in script.text
    assert "const additionalFeatures = features.slice(xaiPrimaryFeatureCount)" in script.text
    assert '"A11 membrane stiffness"' in script.text
    assert 'data-space-case="current"' in rebuild_ko.text
    assert 'id="rebuild-xai-more"' in rebuild_ko.text
    assert 'id="rebuild-space-tooltip"' in rebuild_ko.text
    assert "link.href = `/v2/${code}`;" in script.text
    assert 'routePath === "/v2/en" ? "en" : "ko"' in locale_pack.text
    assert '<link rel="alternate" hreflang="ko" href="/v2/ko" />' in rebuild_ko.text
    assert '<link rel="alternate" hreflang="en" href="/v2/en" />' in rebuild_ko.text
    assert '<link rel="alternate" hreflang="ko" href="/ko" />' in root.text
    assert '<link rel="alternate" hreflang="en" href="/en" />' in root.text
    assert "isThreeSizeModel" not in script.text
    assert 'fetchJson("/models"' not in script.text
    assert '"response_geometry_tree_canonical_v2"' not in script.text
    assert '"response_geometry_goint_canonical_v2"' not in script.text
    assert '"response_hybrid_student_canonical_v2"' not in script.text


def test_rebuild_locale_pages_resolve_static_assets_from_root(client: TestClient) -> None:
    headers = {"host": "laminate.imperialax.com"}
    expected_paths = ["/styles-rebuild.css", "/locales-rebuild.js", "/app-rebuild-preview.js"]
    asset_pattern = re.compile(r'(?:href|src)="([^"]+\.(?:css|js)(?:\?[^"]*)?)"')

    for page_path in ("/v2/ko", "/v2/en"):
        response = client.get(page_path, headers=headers)

        assert response.status_code == 200
        asset_refs = asset_pattern.findall(response.text)
        assert all(asset_ref.startswith("/") for asset_ref in asset_refs)
        resolved_paths = [
            urlsplit(urljoin(f"https://laminate.imperialax.com{page_path}", asset_ref)).path
            for asset_ref in asset_refs
        ]
        assert resolved_paths == expected_paths
        for asset_path in resolved_paths:
            assert client.get(asset_path, headers=headers).status_code == 200


def test_established_locale_pages_resolve_static_assets_from_root(client: TestClient) -> None:
    headers = {"host": "laminate.imperialax.com"}
    expected_paths = [
        "/styles-v2.css",
        "/imperialax-product-shell.css",
        "/imperialax-product-shell.js",
        "/auth-gate.js",
        "/app-v2.js",
    ]
    asset_pattern = re.compile(r'(?:href|src)="([^"]+\.(?:css|js)(?:\?[^"]*)?)"')

    for page_path in ("/ko", "/en"):
        response = client.get(page_path, headers=headers)

        assert response.status_code == 200
        asset_refs = asset_pattern.findall(response.text)
        assert all(asset_ref.startswith("/") for asset_ref in asset_refs)
        resolved_paths = [
            urlsplit(urljoin(f"https://laminate.imperialax.com{page_path}", asset_ref)).path
            for asset_ref in asset_refs
        ]
        assert resolved_paths == expected_paths
        for asset_path in resolved_paths:
            assert client.get(asset_path, headers=headers).status_code == 200


def test_established_laminate_response_viewer_assets_and_contract(client: TestClient) -> None:
    headers = {"host": "laminate.imperialax.com"}
    script = client.get("/app-v2.js", headers=headers)
    styles = client.get("/styles-v2.css", headers=headers)

    for page_path in ("/ko", "/en"):
        page = client.get(page_path, headers=headers)
        assert page.status_code == 200
        assert '"three":"/laminate-viewer/vendor/three.module.r160.js"' in page.text
        assert "/styles-v2.css?v=20260819-viewer-fiber-4" in page.text
        assert "/app-v2.js?v=20260819-viewer-fiber-4" in page.text

    for asset_path in ("/laminate-viewer/vendor/three.module.r160.js",):
        asset = client.get(asset_path, headers=headers)
        assert asset.status_code == 200
        assert "javascript" in asset.headers["content-type"]

    assert script.status_code == 200
    assert styles.status_code == 200
    assert '["viewer", "3D Viewer"]' in script.text
    assert "function setLaminateViewerProgress" in script.text
    assert "responseCurveView.playbackProgress" in script.text
    assert "16-ply 접합 적층" in script.text
    assert "층 사이 간격은 없습니다" in script.text
    assert "LAMINATE_VIEWER_PLY_COUNT = 16" in script.text
    assert "new THREE.BoxGeometry(6, 4, LAMINATE_VIEWER_PLY_THICKNESS" in script.text
    assert 'predictedPt: "예측 Pt"' in script.text
    assert "data-viewer-pt-ratio" in script.text
    assert 'fiberDirection: "섬유 방향 표시"' in script.text
    assert "data-viewer-orientation" in script.text
    assert "laminateViewerFiberBasePositions" in script.text
    assert "LAMINATE_VIEWER_FIBER_SUBDIVISIONS = 28" in script.text
    assert "step < LAMINATE_VIEWER_FIBER_SUBDIVISIONS" in script.text
    assert "orientationGroup.visible = laminateViewerState.orientationVisible" in script.text
    assert ".laminate-viewer-stage" in styles.text
    assert ".laminate-viewer-controls" in styles.text


def test_established_prediction_modes_keep_only_the_active_form_visible(
    client: TestClient,
) -> None:
    headers = {"host": "laminate.imperialax.com"}

    for page_path in ("/ko", "/en"):
        response = client.get(page_path, headers=headers)

        assert response.status_code == 200
        assert '<form id="response-form" class="form active">' in response.text
        assert '<form id="u3-pt-form" class="form">' in response.text
        assert '<form id="stack-preview-form" class="form">' in response.text
        assert '<form id="curve-form" class="form">' in response.text

    local_css = client.get("/styles-v2.css", headers=headers).text
    shared_css = client.get("/imperialax-product-shell.css", headers=headers).text
    shared_form_rule = re.search(
        r"html:not\(\.injection-rebuild\) body\.product-standard \.form\s*\{([^}]*)\}",
        shared_css,
    )

    assert ".form {\n  display: none;\n}" in local_css
    assert ".form.active {\n  display: grid;" in local_css
    assert shared_form_rule is not None
    assert "display:" not in shared_form_rule.group(1)


def test_laminate_pages_link_back_to_imperialax_user_page(client: TestClient) -> None:
    english_v2 = client.get("/dd-laminate-v2")
    korean_v2 = client.get("/dd-laminate-v2-ko")
    english_classic = client.get("/index.html")
    korean_classic = client.get("/index.ko.html")

    assert english_v2.status_code == 200
    assert korean_v2.status_code == 200
    assert english_classic.status_code == 200
    assert korean_classic.status_code == 200
    assert 'href="https://ai.imperialax.com/index.html">Modules</a>' in english_v2.text
    assert 'href="https://ai.imperialax.com/index.ko.html">모듈 선택</a>' in korean_v2.text
    assert "./index-v2.html" in english_classic.text
    assert "./index-v2.ko.html" in korean_classic.text


def test_ai_imperialax_root_serves_canonical_workspace_entry_from_public_app(
    client: TestClient,
) -> None:
    response = client.get("/", headers={"host": "ai.imperialax.com"})
    canonical = client.get("/index.html", headers={"host": "ai.imperialax.com"})

    assert response.status_code == 200
    assert response.text == canonical.text
    assert "ImperialAX AI Workspace" in response.text
    assert "./app.js" in response.text
    assert "/brand/imperialax-logo-black.png?v=20260814-logo-rollout-1" in response.text

    logo = client.get(
        "/brand/imperialax-logo-black.png",
        headers={"host": "ai.imperialax.com"},
    )
    assert logo.status_code == 200
    assert logo.headers["content-type"] == "image/png"


def test_ai_imperialax_workspace_static_files_are_host_routed(client: TestClient) -> None:
    index_response = client.get("/index.html", headers={"host": "ai.imperialax.com"})
    ko_index_response = client.get("/index.ko.html", headers={"host": "ai.imperialax.com"})
    app_response = client.get("/app.js", headers={"host": "ai.imperialax.com"})
    styles_response = client.get("/styles.css", headers={"host": "ai.imperialax.com"})

    assert index_response.status_code == 200
    assert ko_index_response.status_code == 200
    assert "ImperialAX AI Workspace" in index_response.text
    assert "ImperialAX 예측 워크스페이스" in ko_index_response.text
    assert "/api/v1/modules/auth/login" in app_response.text
    assert "demo-token" not in app_response.text
    assert ".login-view" in styles_response.text


def test_ai_imperialax_signup_static_files_are_served_from_public_app(client: TestClient) -> None:
    signup_response = client.get("/signup-v2.html", headers={"host": "ai.imperialax.com"})
    ko_signup_response = client.get("/signup-v2.ko.html", headers={"host": "ai.imperialax.com"})
    forgot_response = client.get("/forgot-v2.html", headers={"host": "ai.imperialax.com"})
    ko_forgot_response = client.get("/forgot-v2.ko.html", headers={"host": "ai.imperialax.com"})
    script_response = client.get("/signup-v2.js", headers={"host": "ai.imperialax.com"})
    forgot_script_response = client.get("/forgot-v2.js", headers={"host": "ai.imperialax.com"})

    assert signup_response.status_code == 200
    assert ko_signup_response.status_code == 200
    assert forgot_response.status_code == 200
    assert ko_forgot_response.status_code == 200
    assert script_response.status_code == 200
    assert forgot_script_response.status_code == 200
    assert "Create ImperialAX Account" in signup_response.text
    assert "ImperialAX 계정 만들기" in ko_signup_response.text
    assert "Reset ImperialAX Password" in forgot_response.text
    assert "ImperialAX 비밀번호 재설정" in ko_forgot_response.text
    assert "/api/v1/modules/auth/signup" in script_response.text
    assert "/api/v1/modules/auth/forgot-password" in forgot_script_response.text


def test_ai_imperialax_admin_static_files_are_served_from_public_app(client: TestClient) -> None:
    admin_response = client.get("/admin.html", headers={"host": "ai.imperialax.com"})
    admin_ko_response = client.get("/admin.ko.html", headers={"host": "ai.imperialax.com"})
    script_response = client.get("/admin.js", headers={"host": "ai.imperialax.com"})

    assert admin_response.status_code == 200
    assert admin_ko_response.status_code == 200
    assert script_response.status_code == 200
    assert "ImperialAX Admin" in admin_response.text
    assert "ImperialAX 관리자" in admin_ko_response.text
    assert "/api/v1/modules/admin/users" in script_response.text


def test_ai_imperialax_optimization_static_files_are_served_from_public_app(
    client: TestClient,
) -> None:
    optimization_response = client.get("/optimization.html", headers={"host": "ai.imperialax.com"})
    optimization_ko_response = client.get(
        "/optimization.ko.html", headers={"host": "ai.imperialax.com"}
    )
    script_response = client.get("/optimization.js", headers={"host": "ai.imperialax.com"})

    assert optimization_response.status_code == 200
    assert optimization_ko_response.status_code == 200
    assert script_response.status_code == 200
    assert "Design Search" in optimization_response.text
    assert "설계 탐색" in optimization_ko_response.text
    assert "/api/v1/optimization/search" in script_response.text


def test_local_root_serves_forecast_entry_default(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert 'lang="ko"' in response.text
    assert "ImperialAX 적층 예측" in response.text
    assert "/app-v2.js" in response.text


def test_v2_korean_page_serves_translated_current_ui(client: TestClient) -> None:
    response = client.get("/dd-laminate-v2-ko")

    assert response.status_code == 200
    assert 'lang="ko"' in response.text
    assert "복합재 적층 AI" in response.text
    assert "ImperialAX 적층 예측" in response.text
    assert "응답 예측" in response.text
    assert "/app-v2.js" in response.text


def test_predict_response_matches_ios_contract_shape(client: TestClient, ios_fixture: dict) -> None:
    models = client.get("/api/v1/dd-laminate/models").json()
    response_surrogate = next(
        model
        for model in models["response_models"]
        if model["key"] == "response_geometry_tree_canonical_v2"
    )
    if not response_surrogate["available"]:
        pytest.skip("response_surrogate model artifact or runtime dependency is unavailable")

    response = client.post(ios_fixture["endpoint"], json=ios_fixture["request"])
    assert response.status_code == 200
    data = response.json()

    assert REQUIRED_RESPONSE_FIELDS.issubset(data)
    assert data["input_mode"] == "response"
    assert data["model_key"] == "response_geometry_tree_canonical_v2"
    assert data["inputs"] == ios_fixture["response"]["inputs"]
    assert isinstance(data["predicted_pt"], float)
    assert isinstance(data["predicted_max_displacement"], float)
    assert isinstance(data["predicted_max_force"], float)
    assert len(data["curve"]) == len(ios_fixture["response"]["curve"])
    assert {"displacement", "force"}.issubset(data["curve"][0])


def test_predict_response_validation_error_is_stable_for_ios(client: TestClient) -> None:
    response = client.post(
        "/api/v1/dd-laminate/predict/response",
        json={"theta1": 120, "theta2": -30, "case": "Case2", "model": "response_surrogate"},
    )

    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    assert isinstance(body["detail"], list)
    assert any("theta1" in str(error.get("loc", [])) for error in body["detail"])
