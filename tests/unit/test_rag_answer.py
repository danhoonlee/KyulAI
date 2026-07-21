from __future__ import annotations

import json
from pathlib import Path

from src.data.rag.answer import (
    RagCitation,
    answer_query,
    build_extractive_answer,
    clean_answer_text,
    compact_prediction_context,
    contains_korean,
    matched_feature_explanations,
)
from src.data.rag.indexer import DEFAULT_INDEX_PATH, build_knowledge_index, query_index


def test_extractive_answer_uses_korean_for_korean_query(tmp_path: Path) -> None:
    project_root = tmp_path
    docs = project_root / "docs"
    docs.mkdir()
    (docs / "DD_Laminate_Test.md").write_text(
        "Double-Double laminate forecast predicts Pt using theta angles and Case inputs.",
        encoding="utf-8",
    )
    output = project_root / "index.json"
    build_knowledge_index(project_root=project_root, output_path=output)

    result = answer_query("Pt 예측은 어떤 입력을 사용해?", index_path=output, use_llm=False)

    assert result.provider == "extractive"
    assert result.used_llm is False
    assert "로컬 RAG" in result.answer
    assert result.citations


def test_build_extractive_answer_can_use_english() -> None:
    citation = RagCitation(
        index=1,
        title="Test",
        source_id="test",
        source_kind="internal",
        source="/tmp/test.md",
        score=0.5,
        topic="double_double_laminate",
        chunk_id="internal:test:0",
        excerpt="Double-Double laminates simplify composite design.",
    )

    answer = build_extractive_answer("What is DD?", [citation], language="en")

    assert answer.startswith("Grounded local RAG answer")
    assert "did not detect a specific feature name" in answer


def test_build_extractive_answer_uses_injection_prediction_context() -> None:
    citation = RagCitation(
        index=1,
        title="Injection surrogate note",
        source_id="injection",
        source_kind="internal",
        source="/tmp/injection.md",
        score=0.5,
        topic="injection_surrogate",
        chunk_id="internal:injection:0",
        excerpt="Injection surrogate predicts sprue pressure from geometry and process parameters.",
    )

    answer = build_extractive_answer(
        "수지 온도가 Sprue Pressure에 왜 영향을 주나요?",
        [citation],
        language="ko",
        prediction_context={
            "mode": "Injection Forecast",
            "inputs": {
                "geometry_id": "G01",
                "process_id": "P01",
                "melt_temp_C": 216.2,
                "gate_type": "edge_gate",
            },
            "predicted_max_pressure_MPa": 69.0,
            "predicted_max_time_s": 2.1,
            "xai": {
                "top_features": [
                    {
                        "label": "수지 온도",
                        "importance": 0.247754,
                        "local_sensitivity": 0.382825,
                        "local_value": 216.2,
                        "perturbation": "5% 증가",
                    }
                ]
            },
        },
    )

    assert "Injection 예측" in answer
    assert "수지 온도" in answer
    assert "Sprue Pressure 최대값 69.0 MPa" in answer
    assert "DD Laminate" not in answer


def test_answer_query_uses_prediction_context_when_retrieval_is_empty(tmp_path: Path) -> None:
    empty_index = tmp_path / "empty_index.json"
    empty_index.write_text(
        json.dumps(
            {
                "schema_version": "local-tfidf-v1",
                "generated_at": "2026-06-26T00:00:00+00:00",
                "chunk_count": 0,
                "source_count": 0,
                "chunks": [],
            }
        ),
        encoding="utf-8",
    )

    result = answer_query(
        "왜 수지 온도가 가장 큰 영향력을 주는 것 같아?",
        index_path=empty_index,
        use_llm=False,
        language="ko",
        prediction_context={
            "mode": "Injection Forecast",
            "inputs": {"melt_temp_C": 216.2},
            "predicted_max_pressure_MPa": 72.4,
            "xai": {
                "top_features": [
                    {
                        "label": "수지 온도",
                        "importance": 0.256,
                        "local_sensitivity": 0.31,
                        "local_value": 216.2,
                        "perturbation": "5% 증가",
                    }
                ]
            },
        },
    )

    assert result.provider == "extractive"
    assert result.model == "local-prediction-context"
    assert result.retrieval_count == 0
    assert "수지 온도" in result.answer
    assert "25.6%" in result.answer
    assert "점도" in result.answer
    assert "유동 저항" in result.answer
    assert "관련 근거를 찾지 못했습니다" not in result.answer


def test_injection_answer_focuses_on_requested_xai_feature() -> None:
    answer = build_extractive_answer(
        "보압 시간이 왜 영향력을 주는 것 같아?",
        [],
        language="ko",
        prediction_context={
            "mode": "Injection Forecast",
            "inputs": {"melt_temp_C": 216.2, "packing_time_s": 7.4},
            "xai": {
                "top_features": [
                    {
                        "name": "melt_temp_C",
                        "label": "수지 온도",
                        "importance": 0.256,
                        "local_sensitivity": 0.31,
                        "local_value": 216.2,
                    },
                    {
                        "name": "packing_time_s",
                        "label": "보압 시간",
                        "importance": 0.091,
                        "local_sensitivity": 0.12,
                        "local_value": 7.4,
                        "perturbation": "5% 증가",
                    },
                ]
            },
        },
    )

    assert "질문에서 물어본 보압 시간" in answer
    assert "importance 9.1%" in answer
    assert "importance 25.6%" not in answer
    assert "후반부 pressure tail" in answer
    assert "초기 충전 peak" in answer


def test_injection_answer_does_not_confuse_packing_time_with_packing_pressure() -> None:
    answer = build_extractive_answer(
        "보압 시간은 왜 중요해?",
        [],
        language="ko",
        prediction_context={
            "mode": "Injection Forecast",
            "xai": {
                "top_features": [
                    {"name": "packing_pressure_MPa", "label": "보압", "importance": 0.2},
                    {"name": "packing_time_s", "label": "보압 시간", "importance": 0.1},
                ]
            },
        },
    )

    assert "질문에서 물어본 보압 시간" in answer
    assert "importance 10.0%" in answer
    assert "importance 20.0%" not in answer


def test_extractive_answer_explains_physics_feature_question() -> None:
    citation = RagCitation(
        index=1,
        title="response xai report",
        source_id="report",
        source_kind="internal",
        source="/tmp/report.md",
        score=0.5,
        topic="double_double_laminate",
        chunk_id="internal:report:0",
        excerpt="Feature set includes D11 bending stiffness and CLT ABD descriptors.",
    )

    answer = build_extractive_answer("D11 굽힘 강성이 왜 중요한가요?", [citation], language="ko")

    assert "D11 bending stiffness" in answer
    assert "굽힘 저항" in answer
    assert "response xai report" not in answer


def test_matched_feature_explanations_detects_label_terms() -> None:
    matches = matched_feature_explanations("Why is A12 membrane coupling important?", korean=False)

    assert matches
    assert "A12 membrane coupling" in matches[0]


def test_clean_answer_text_removes_markdown_and_latex() -> None:
    answer = clean_answer_text(
        "**D11**은 \\(A_{12}\\)와 함께 중요합니다.\n"
        "1. **첫 번째 이유**는 굽힘 강성입니다.\n"
        "- \\(D_{11}\\) 값이 커지면 변형이 줄어듭니다.\n"
        "- \\(B_{ij}=0\\)이면 결합항이 사라집니다.\n"
        "Retrieved context에서도 중요합니다."
    )

    assert "**" not in answer
    assert "\\(" not in answer
    assert "A12" in answer
    assert "D11" in answer
    assert "Bij=0" in answer
    assert "1." not in answer
    assert "Retrieved context" not in answer


def test_compact_prediction_context_includes_current_d11_physics() -> None:
    context = compact_prediction_context(
        {
            "mode": "Laminate Forecast",
            "inputs": {"theta1": 30, "theta2": -30, "case": "Case2"},
            "predicted_type": 2,
            "predicted_pt": 17163.21,
            "xai": {
                "method": "Tree ensemble feature importance + live local feature masking",
                "feature_set": "theta + CLT physics",
                "top_features": [
                    {
                        "label": "D11 bending stiffness",
                        "importance": 0.23,
                        "local_sensitivity": 0.25,
                        "local_value": 1.06895,
                        "perturbation": "masked to 0",
                    }
                ],
            },
        }
    )

    assert "Case2 = [[±θ₁]/[±θ₂]]₄" in context
    assert "Expanded stack" in context
    assert "D11 calculation basis" in context
    assert "normalized d11=12.8274" in context
    assert "surrogate forecast" in context
    assert "Type definitions used by this project" in context
    assert "Type 2: initial branch is nearly linear" in context
    assert "Target distribution for Case2" in context
    assert "Current predicted Pt percentile within Case2" in context


def test_compact_prediction_context_includes_injection_values() -> None:
    context = compact_prediction_context(
        {
            "mode": "Injection Forecast",
            "inputs": {
                "geometry_id": "G01",
                "process_id": "P01",
                "melt_temp_C": 216.2,
                "gate_type": "edge_gate",
            },
            "filling_model_label": "Filling - Machine Learning",
            "predicted_max_pressure_MPa": 69.0,
            "predicted_filling_max_MPa": 41.5,
            "xai": {
                "method": "local perturbation",
                "feature_set": "geometry + process + gate + derived flow descriptors",
                "top_features": [
                    {
                        "label": "Melt temperature",
                        "importance": 0.24,
                        "local_sensitivity": 0.38,
                        "local_value": 216.2,
                        "perturbation": "5% increase",
                    }
                ],
            },
        }
    )

    assert "Prediction mode: Injection Forecast" in context
    assert "geometry_id=G01" in context
    assert "melt_temp_C=216.2" in context
    assert "Predicted max sprue pressure: 69.0" in context
    assert "Predicted filling max pressure: 41.5" in context
    assert "perturbation=5% increase" in context
    assert "Expanded stack" not in context


def test_contains_korean() -> None:
    assert contains_korean("복합재")
    assert not contains_korean("composite")


def test_answer_endpoint_contract_shape() -> None:
    payload = {
        "query": "Double-Double laminate",
        "answer": "A grounded answer",
        "provider": "extractive",
        "model": "local-fallback",
        "citations": [],
        "retrieval_count": 0,
        "used_llm": False,
        "error": "",
    }

    assert json.loads(json.dumps(payload))["provider"] == "extractive"


def test_query_index_handles_common_english_assistant_question() -> None:
    results = query_index(
        DEFAULT_INDEX_PATH,
        "Why is the top XAI feature important in this prediction?",
        top_k=3,
    )

    assert isinstance(results, list)
