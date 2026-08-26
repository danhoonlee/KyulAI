from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.backend.simple_injection_app import app

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def local_prediction_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IMPERIALAX_DISABLE_AUTH_FOR_LOCAL_DEV", "1")
    monkeypatch.delenv("IMPERIALAX_ENV", raising=False)


def test_simple_injection_model_labels_use_actual_model_names() -> None:
    client = TestClient(app)

    ready = client.get("/ready")
    assert ready.status_code == 200
    ready_data = ready.json()
    assert ready_data["status"] == "ready"
    assert all(status == "ok" for status in ready_data["models"].values())

    response = client.get("/api/v1/simple-injection/models")

    assert response.status_code == 200
    data = response.json()
    sprue_labels = {model["key"]: model["label"] for model in data["sprue_pressure_models"]}
    filling_labels = {model["key"]: model["label"] for model in data["filling_pressure_models"]}

    assert sprue_labels == {
        "sprue_classical": "ExtraTrees + PCA",
        "sprue_goint": "GointMLP NN",
        "sprue_deeponet": "DeepONet NN",
    }
    assert filling_labels == {
        "filling_classical": "ExtraTrees histogram",
        "filling_goint": "GointMLP NN",
        "filling_deeponet": "DeepONet NN",
    }


def test_simple_injection_pages_link_back_to_imperialax_user_page() -> None:
    client = TestClient(app)

    english_v2 = client.get("/index-v2.html")
    korean_v2 = client.get("/index-v2.ko.html")
    english_classic = client.get("/index.html")
    korean_classic = client.get("/index.ko.html")

    assert english_v2.status_code == 200
    assert korean_v2.status_code == 200
    assert english_classic.status_code == 200
    assert korean_classic.status_code == 200
    assert 'href="https://ai.imperialax.com/index.html">Modules</a>' in english_v2.text
    assert 'href="https://ai.imperialax.com/index.ko.html">모듈 선택</a>' in korean_v2.text
    assert 'href="https://ai.imperialax.com/index.html">Modules</a>' in english_classic.text
    assert 'href="https://ai.imperialax.com/index.ko.html">모듈 선택</a>' in korean_classic.text


def test_injection_established_ui_is_root_and_rebuild_moves_to_v2() -> None:
    client = TestClient(app, follow_redirects=False)

    root = client.get("/")
    root_head = client.head("/")
    root_ko = client.get("/ko")
    root_en = client.get("/en")
    rebuild = client.get("/v2")
    rebuild_head = client.head("/v2")
    rebuild_slash = client.get("/v2/")
    rebuild_ko = client.get("/v2/ko")
    rebuild_en = client.get("/v2/en")

    assert root.status_code == 200
    assert root_head.status_code == 200
    assert root.headers.get("location") is None
    assert "/styles-v2.css?v=20260816-mobile-polish-1" in root.text
    assert "/imperialax-product-shell.css?v=20260816-mobile-polish-1" in root.text
    assert "공정·형상 DOE 선택" in root.text
    assert "세부 조건 확인" in root.text
    assert "/imperialax-product-shell.js?v=20260814-family-shell-1" in root.text
    assert "/locales-rebuild.js?v=20260814-gate-refine-1" in root.text
    assert "/app-v2.js?v=20260816-mobile-polish-1" in root.text
    assert "G1에서 G10으로 갈수록" in root.text
    assert 'aria-describedby="sprue-curve-help"' in root.text
    assert root_ko.status_code == 200
    assert root_en.status_code == 200
    assert "ImperialAX 사출 예측" in root_ko.text
    assert '<p class="eyebrow">사출 성형 AI</p>' in root_ko.text
    assert '<h1 id="app-title"><span>ImperialAX</span> <span>사출 예측</span></h1>' in root_ko.text
    assert "Injection Forecast" in root_en.text
    assert '<p class="eyebrow">Injection Molding AI</p>' in root_en.text
    assert "Select process and geometry DOE" in root_en.text
    assert "Check detailed conditions" in root_en.text
    assert "수지 온도 (°C)" in root_ko.text
    assert "형상 DOE" in root_ko.text
    assert 'class="fixed-gate-values"' in root_ko.text
    assert 'class="fixed-gate-type"' in root_ko.text
    assert 'class="fixed-gate-size"' in root_ko.text
    assert "학습 DOE에 포함된 조건이며 변경할 수 없습니다." in root_ko.text
    assert 'class="primary mobile-quick-run" type="submit">현재 DOE로 바로 예측' in root_ko.text
    assert "Melt temperature (°C)" in root_en.text
    assert "Hole diameter D (mm)" in root_en.text
    assert "This condition is included in the training DOE and cannot be changed." in root_en.text
    assert (
        'class="primary mobile-quick-run" type="submit">Forecast with current DOE' in root_en.text
    )
    assert 'href="/en">English</a>' in root_ko.text
    assert 'href="/ko">한국어</a>' in root_en.text
    for page in (root_ko, root_en):
        assert page.text.index("header-action-module") < page.text.index("header-action-assistant")
        assert page.text.index("header-action-assistant") < page.text.index(
            "header-action-research"
        )
        assert page.text.index("header-action-research") < page.text.index("header-action-language")
        assert page.text.index("header-action-language") < page.text.index("header-action-account")
        assert page.text.index("header-action-account") < page.text.index("header-action-status")
    assert 'href="https://ai.imperialax.com/index.ko.html?signout=1">로그아웃</a>' in root_ko.text
    assert 'href="https://ai.imperialax.com/index.html?signout=1">Sign out</a>' in root_en.text
    assert '<link rel="alternate" hreflang="ko" href="/ko" />' in root_ko.text
    assert '<link rel="alternate" hreflang="en" href="/en" />' in root_en.text
    for response in (root_ko, root_en):
        assert 'class="product-logo-link"' in response.text
        assert "/brand/imperialax-logo-black.png?v=20260814-logo-rollout-1" in response.text
        assert response.text.count('class="utility-trigger header-action') == 2
        assert response.text.count('class="utility-dialog"') == 2
        assert 'data-dialog-target="research-dialog"' in response.text
        assert 'data-dialog-target="assistant-dialog"' in response.text

    family_styles = client.get("/imperialax-product-shell.css")
    family_script = client.get("/imperialax-product-shell.js")
    assert family_styles.status_code == 200
    assert family_script.status_code == 200
    assert "body.product-standard .topbar" in family_styles.text
    hero_copy_rule = family_styles.text.split("body.product-standard .hero-copy {", 1)[1].split(
        "}", 1
    )[0]
    assert "width: max-content;" in hero_copy_rule
    assert "max-width: none;" in hero_copy_rule
    assert "white-space: nowrap;" in hero_copy_rule
    assert "body.product-standard .utility-dialog" in family_styles.text
    assert "body.injection-standard .process-control > b" in family_styles.text
    assert "body.injection-standard .process-control > i" in family_styles.text
    assert "body.injection-standard .fixed-gate-condition" in family_styles.text
    assert "body.injection-standard .fixed-gate-values" in family_styles.text
    assert "body.injection-standard .filling-row > i::after" in family_styles.text
    assert "background: var(--family-blue);" in family_styles.text
    assert "body.product-standard .language-link," in family_styles.text
    assert "body.product-standard .status-pill {\n    min-height: 36px;" in family_styles.text
    assert "body.product-standard .primary {\n    min-height: 44px;" in family_styles.text
    assert 'document.querySelectorAll("[data-dialog-target]")' in family_script.text
    assert 'dialog.addEventListener("close"' in family_script.text

    for response in (rebuild, rebuild_ko, rebuild_en):
        assert response.status_code == 200
        assert response.headers.get("x-robots-tag") is None
        assert "/styles-rebuild.css?v=20260816-mobile-polish-2" in response.text
        assert "/app-rebuild.js?v=20260816-mobile-polish-1" in response.text
        assert 'document.documentElement.classList.add("injection-rebuild")' in response.text

    assert rebuild_head.status_code == 200
    assert "Injection Forecast" in rebuild.text
    assert rebuild_ko.text.index('id="process-select"') < rebuild_ko.text.index(
        'id="geometry-select"'
    )
    assert rebuild_en.text.index('id="process-select"') < rebuild_en.text.index(
        'id="geometry-select"'
    )
    assert rebuild_slash.status_code == 308
    assert rebuild_slash.headers["location"] == "/v2"

    for asset in (
        "/styles-rebuild.css",
        "/app-rebuild.js",
        "/locales-rebuild.js",
        "/brand/imperialax-logo-black.png",
        "/brand/imperialax-mark-black.png",
    ):
        assert client.get(asset).status_code == 200

    rebuild_script = client.get("/app-rebuild.js").text
    rebuild_styles = client.get("/styles-rebuild.css").text
    established_script = client.get("/app-v2.js").text
    established_styles = client.get("/styles-v2.css").text
    assert '["curve", t("sprueCurve")]' in rebuild_script
    assert '["filling", t("fillingDistribution")]' in rebuild_script
    assert 't("csvGuide")' in rebuild_script
    assert 't("deepHintBefore")' in rebuild_script
    assert 'const doeSetup = form.elements.geometry_id?.closest(".setup-block");' in rebuild_script
    assert "doeSetup?.after(visualPanel);" in rebuild_script
    assert "submitButton.before(visualPanel);" not in rebuild_script
    assert "function showExampleResult" in rebuild_script
    assert "links[1].remove();" in rebuild_script
    assert 'links[0].href = "/";' in rebuild_script
    assert "if (accountLink) topActions.appendChild(accountLink);" in rebuild_script
    assert (
        'topActions.querySelectorAll(".top-action-group").forEach((group) => group.remove());'
        in rebuild_script
    )
    assert "link.href = `/v2/${code}`;" in rebuild_script
    assert 't("gateFixedNote")' in rebuild_script
    assert 't("gateTypeValue")' in rebuild_script
    assert 't("gateSizeValue")' in rebuild_script
    assert 't("holeDiameter")' in rebuild_script
    assert '.primary[type="submit"]:not(.mobile-quick-run)' in rebuild_script
    assert "querySelectorAll(\"button[type='submit']\")" in established_script
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in established_styles
    assert ".mobile-quick-run" in established_styles
    assert "height: clamp(210px, 64vw, 246px);" in rebuild_styles
    assert "국부 민감도 0.31" in rebuild_script
    assert "features.forEach(([label, category, score, description, meta])" in rebuild_script
    assert 'result.dataset.resultSource = "example"' in rebuild_script
    assert "tabList.hidden = true" in rebuild_script
    assert "deepDiveHint.hidden = true" in rebuild_script
    assert 'button.dataset.resultTab === "validation"' in rebuild_script
    assert '[data-analysis-mode="quick"] .geometry-details' not in rebuild_styles
    assert ".empty-state-mark" in rebuild_styles
    assert "grid-template-columns: 400px minmax(0, 1fr);" in rebuild_styles
    assert "font-weight: 500;" in rebuild_styles
    assert ".injection-rebuild .fixed-gate-condition" in rebuild_styles
    assert ".injection-rebuild .process-control b," in rebuild_styles
    assert ".injection-rebuild .process-control i" in rebuild_styles
    assert "display: none;" in rebuild_styles
    assert "grid-template-columns: 1fr;" in rebuild_styles
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in rebuild_styles
    assert "background: transparent;" in rebuild_styles
    assert "grid-template-rows: auto auto;" in rebuild_styles
    assert "font-size: 22px;" in rebuild_styles
    assert "font-size: 18px;" in rebuild_styles
    assert "min-height: 44px;" in rebuild_styles
    assert "min-height: 58px;" in rebuild_styles
    assert "padding: 18px;" in rebuild_styles
    assert "border-top: 0;" in rebuild_styles
    assert "background: var(--rebuild-canvas);" in rebuild_styles
    assert ".injection-rebuild .xai-feature-heading" in rebuild_styles
    assert ".injection-rebuild .xai-bar > i" in rebuild_styles
    assert "background: var(--rebuild-blue);" in rebuild_styles
    assert "background: #dce3ee;" in rebuild_styles
    assert ".injection-rebuild .filling-row > i::after" in rebuild_styles
    assert ".injection-rebuild .utility-trigger" in rebuild_styles
    assert "width: var(--bar, 0%);" in rebuild_styles
    assert "function normalizeInjectionXaiFeature" in rebuild_script
    assert 'item.dataset.laminateXaiLayout = "true"' in rebuild_script
    assert 'summaryCard.className = "injection-xai-summary-card"' in rebuild_script
    app_script = client.get("/app-v2.js").text
    assert 'new CustomEvent("injection:result-rendered"' in app_script
    assert 'value === "1" ? "로" : "으로"' in app_script
    locale_pack = client.get("/locales-rebuild.js").text
    assert '"Injection candidate screening"' in locale_pack
    assert '"No forecast has been run yet"' in locale_pack
    assert '"수지 온도 (°C)"' in locale_pack
    assert '"길이 L (mm)"' in locale_pack


def test_injection_validation_samples_are_narrowly_published() -> None:
    client = TestClient(app)

    sprue = client.get("/samples/G01_P01_Sprue_Pressure.csv")
    filling = client.get("/samples/G01_P01_Filling_Pressure.csv")
    unknown = client.get("/samples/not-a-public-file.csv")

    assert sprue.status_code == 200
    assert "Time (sec),Run 1 : G01_P01 (MPa)" in sprue.text
    assert filling.status_code == 200
    assert "[Distribution]" in filling.text
    assert "Group,From,To,Center,Count,Volume Ratio(%)" in filling.text
    assert unknown.status_code == 404


def test_injection_public_host_does_not_redirect_to_itself() -> None:
    client = TestClient(app, follow_redirects=False)

    response = client.get("/", headers={"host": "injection.imperialax.com"})

    assert response.status_code == 200
    assert response.headers.get("location") is None


def test_injection_standard_ui_hides_untrained_g11_geometry() -> None:
    script = (PROJECT_ROOT / "src/frontend/simple-injection/app-v2.js").read_text(encoding="utf-8")

    assert 'const HIDDEN_GEOMETRY_IDS = new Set(["G11"]);' in script
    assert "!HIDDEN_GEOMETRY_IDS.has(geometry.id)" in script


def test_simple_injection_does_not_publish_the_whole_data_directory() -> None:
    assert not any(getattr(route, "path", None) == "/data" for route in app.routes)
