"""Answer synthesis layer for the Composite RAG index."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
import csv
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from src.ml.dd_laminate.laminate_physics import (
    COMPACT_PHYSICS_FEATURE_COLUMNS,
    DEFAULT_MATERIAL,
    abd_matrices,
    compact_physics_feature_vector,
)
from src.data.rag.indexer import DEFAULT_INDEX_PATH, QueryResult, query_index


AnswerProvider = Literal["extractive", "openai"]

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RESPONSE_MANIFEST_PATH = PROJECT_ROOT / "data/datasets/DD_cases_2_3_4_curated_v1/label_manifest.csv"

TYPE_DEFINITIONS = {
    1: "Type 1: clear bilinear force-displacement response; initial and post-transition branches are both approximately linear, and Pt is the intersection of the two fitted lines.",
    2: "Type 2: initial branch is nearly linear, but the post-transition branch is curved; knee point is less clear, so u3 information is used with force-plot fitting.",
    3: "Type 3: initial branch is nearly linear, but post-transition curvature is strong and force bilinear fitting is unreliable; Pt is mainly based on the u3-plot intersection.",
}

FEATURE_GLOSSARY: dict[str, tuple[str, str, str]] = {
    "d11": (
        "D11 bending stiffness",
        "D 행렬의 하중 방향 굽힘 강성입니다.",
        "현재 패널 문제에서는 굽힘 저항과 kink 이후 응답 곡선의 기울기 변화에 직접 연결되므로 Pt와 Type 예측에서 중요한 물리 feature가 됩니다.",
    ),
    "d22": (
        "D22 bending stiffness",
        "D 행렬의 횡방향 굽힘 강성입니다.",
        "D11과의 균형 또는 anisotropy가 곡선 형태와 좌굴/후좌굴성 전이 거동을 구분하는 신호가 될 수 있습니다.",
    ),
    "d12": (
        "D12 bending coupling",
        "D 행렬의 굽힘 커플링 항입니다.",
        "knee point 이후 곡선이 선형에 가까운지, 더 강하게 휘는지를 구분하는 데 도움이 되는 굽힘 상호작용 정보입니다.",
    ),
    "d66": (
        "D66 twisting stiffness",
        "D 행렬의 비틀림/전단 굽힘 강성입니다.",
        "좌굴 모드 전환이나 transition 이후 곡선 형태에 영향을 줄 수 있어 Type 구분과 u3 거동 해석에 의미가 있습니다.",
    ),
    "a11": (
        "A11 membrane stiffness",
        "A 행렬의 하중 방향 막 강성입니다.",
        "초기 하중-변위 기울기와 축방향 하중 전달 능력을 설명하는 기본 강성 항입니다.",
    ),
    "a22": (
        "A22 membrane stiffness",
        "A 행렬의 횡방향 막 강성입니다.",
        "A11과의 비율은 적층이 하중 방향에 치우쳤는지 또는 횡방향 강성이 큰지를 보여주는 membrane anisotropy 신호입니다.",
    ),
    "a12": (
        "A12 membrane coupling",
        "A 행렬의 in-plane membrane coupling 항입니다.",
        "축방향/횡방향 변형이 서로 얼마나 묶여 움직이는지를 나타내며, 같은 theta라도 Case 구조에 따라 응답 곡선과 Type이 달라지는 이유를 설명하는 데 도움이 됩니다.",
    ),
    "a66": (
        "A66 shear stiffness",
        "A 행렬의 in-plane shear 강성입니다.",
        "전단 기여도를 통해 각도 조합이 단순 축방향 강성만이 아니라 전단 변형을 얼마나 억제하는지도 설명합니다.",
    ),
    "b11": (
        "B11 membrane-bending coupling",
        "B 행렬의 하중 방향 membrane-bending coupling 항입니다.",
        "비대칭 적층에서는 막 변형과 굽힘이 서로 연결되므로, force/u3 곡선의 전이 위치와 후반 곡률에 영향을 줄 수 있습니다.",
    ),
    "b22": (
        "B22 membrane-bending coupling",
        "B 행렬의 횡방향 membrane-bending coupling 항입니다.",
        "횡방향 굽힘-막 결합 정도를 나타내며 Case별 적층 순서 차이를 설명하는 보조 신호입니다.",
    ),
    "b12": (
        "B12 membrane-bending coupling",
        "B 행렬의 cross membrane-bending coupling 항입니다.",
        "막-굽힘 상호작용이 커질수록 bilinear 전이 이후 응답 곡선이 더 복잡해질 수 있습니다.",
    ),
}


@dataclass(frozen=True)
class RagCitation:
    """Citation metadata exposed to the UI and API clients."""

    index: int
    title: str
    source_id: str
    source_kind: str
    source: str
    score: float
    topic: str
    chunk_id: str
    excerpt: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RagAnswer:
    """Grounded answer generated from retrieved Composite RAG chunks."""

    query: str
    answer: str
    provider: AnswerProvider
    model: str
    citations: list[RagCitation]
    retrieval_count: int
    used_llm: bool
    error: str = ""

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["citations"] = [citation.to_dict() for citation in self.citations]
        return payload


def answer_query(
    query: str,
    *,
    index_path: str | Path = DEFAULT_INDEX_PATH,
    top_k: int = 5,
    use_llm: bool = True,
    language: str = "auto",
    prediction_context: dict[str, Any] | None = None,
) -> RagAnswer:
    """Retrieve relevant chunks and synthesize an answer."""
    ensure_openai_env_loaded()
    retrievals = query_index(index_path, query, top_k=top_k)
    citations = citations_from_results(retrievals)
    context_explanations = current_prediction_explanations(
        prediction_context,
        query=query,
        korean=language == "ko" or (language == "auto" and contains_korean(query)),
    )
    if not citations:
        context_answer = build_extractive_answer(
            query,
            citations,
            language=language,
            prediction_context=prediction_context,
        )
        if context_explanations:
            return RagAnswer(
                query=query,
                answer=context_answer,
                provider="extractive",
                model="local-prediction-context",
                citations=[],
                retrieval_count=0,
                used_llm=False,
            )
        return RagAnswer(
            query=query,
            answer="관련 근거를 찾지 못했습니다. 질문을 더 구체적으로 입력해 주세요.",
            provider="extractive",
            model="local-fallback",
            citations=[],
            retrieval_count=0,
            used_llm=False,
        )

    if is_injection_prediction(prediction_context) and context_explanations:
        return RagAnswer(
            query=query,
            answer=build_extractive_answer(
                query,
                [],
                language=language,
                prediction_context=prediction_context,
            ),
            provider="extractive",
            model="local-prediction-context",
            citations=[],
            retrieval_count=0,
            used_llm=False,
        )

    if use_llm and os.environ.get("OPENAI_API_KEY"):
        model = os.environ.get("OPENAI_RAG_MODEL", "gpt-5.4-mini")
        try:
            answer = call_openai_responses(
                query,
                retrievals,
                model=model,
                language=language,
                prediction_context=prediction_context,
            )
            answer = clean_answer_text(answer)
            answer = format_answer_for_display(answer, prediction_context=prediction_context)
            return RagAnswer(
                query=query,
                answer=answer,
                provider="openai",
                model=model,
                citations=citations,
                retrieval_count=len(retrievals),
                used_llm=True,
            )
        except Exception as exc:
            fallback = build_extractive_answer(
                query,
                citations,
                language=language,
                prediction_context=prediction_context,
            )
            return RagAnswer(
                query=query,
                answer=fallback,
                provider="extractive",
                model="local-fallback",
                citations=citations,
                retrieval_count=len(retrievals),
                used_llm=False,
                error=f"OpenAI response failed; used local fallback. {exc}",
            )

    return RagAnswer(
        query=query,
        answer=build_extractive_answer(
            query,
            citations,
            language=language,
            prediction_context=prediction_context,
        ),
        provider="extractive",
        model="local-fallback",
        citations=citations,
        retrieval_count=len(retrievals),
        used_llm=False,
    )


def ensure_openai_env_loaded() -> None:
    """Load local OpenAI RAG secrets for direct uvicorn/server launches."""
    if os.environ.get("OPENAI_API_KEY"):
        return
    env_path = PROJECT_ROOT / ".env.local"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in {"OPENAI_API_KEY", "OPENAI_RAG_MODEL"}:
            continue
        value = value.strip().strip('"').strip("'")
        if value:
            os.environ.setdefault(key, value)


def citations_from_results(results: list[QueryResult]) -> list[RagCitation]:
    citations: list[RagCitation] = []
    for index, result in enumerate(results, start=1):
        chunk = result.chunk
        source = chunk.url or chunk.source_path
        citations.append(
            RagCitation(
                index=index,
                title=chunk.title,
                source_id=chunk.source_id,
                source_kind=chunk.source_kind,
                source=source,
                score=round(result.score, 6),
                topic=chunk.topic,
                chunk_id=chunk.chunk_id,
                excerpt=chunk.text[:420],
            )
        )
    return citations


def build_extractive_answer(
    query: str,
    citations: list[RagCitation],
    *,
    language: str = "auto",
    prediction_context: dict[str, Any] | None = None,
) -> str:
    korean = language == "ko" or (language == "auto" and contains_korean(query))
    feature_explanations = matched_feature_explanations(query, korean=korean)
    prediction_explanations = current_prediction_explanations(prediction_context, query=query, korean=korean)
    if korean:
        lines = [
            "로컬 RAG 근거와 현재 예측 컨텍스트를 기준으로 정리하면 다음과 같습니다."
            if prediction_explanations
            else "로컬 RAG 근거를 기준으로 정리하면 다음과 같습니다.",
        ]
        if prediction_explanations:
            lines.extend(prediction_explanations)
        elif feature_explanations:
            lines.extend(feature_explanations)
            if should_include_citation_takeaways(query, citations):
                lines.extend(citation_takeaways(citations, korean=True))
        else:
            if is_injection_prediction(prediction_context):
                lines.append(
                    "질문과 가까운 Injection/CAE 참고 자료는 찾았지만, 현재 질문과 직접 연결되는 feature 설명은 제한적입니다. "
                    "예측을 먼저 실행하면 현재 Sprue Pressure, Filling Pressure, 그리고 XAI 상위 인자를 함께 설명할 수 있습니다."
                )
            else:
                if should_include_citation_takeaways(query, citations):
                    takeaways = citation_takeaways(citations, korean=True)
                    lines.extend(takeaways)
                else:
                    lines.append("질문과 가장 가까운 DD Laminate/XAI 문서 근거를 찾았지만, 특정 feature 설명은 감지하지 못했습니다.")
        return "\n\n".join(lines)

    lines = [
        "Grounded local RAG answer with the current prediction context:"
        if prediction_explanations
        else "Grounded local RAG answer:",
    ]
    if prediction_explanations:
        lines.extend(prediction_explanations)
    elif feature_explanations:
        lines.extend(feature_explanations)
        if should_include_citation_takeaways(query, citations):
            lines.extend(citation_takeaways(citations, korean=False))
    else:
        if is_injection_prediction(prediction_context):
            lines.append(
                "I found related Injection/CAE context, but did not detect a specific feature explanation. "
                "Run a prediction first to connect the answer to sprue pressure, filling pressure, and local XAI drivers."
            )
        else:
            if should_include_citation_takeaways(query, citations):
                takeaways = citation_takeaways(citations, korean=False)
                lines.extend(takeaways)
            else:
                lines.append("I found related DD Laminate/XAI context, but did not detect a specific feature name in the question.")
    return "\n\n".join(lines)


def should_include_citation_takeaways(query: str, citations: list[RagCitation]) -> bool:
    """Keep legacy fallback terse except for comparison-style knowledge questions."""
    haystack = " ".join([query, *[citation.title for citation in citations], *[citation.excerpt for citation in citations]]).lower()
    comparison_terms = ("tac", "case 4", "case4", "case 5", "case5", "case 6", "case6", "비교", "대안")
    return any(term in haystack for term in comparison_terms)


def citation_takeaways(citations: list[RagCitation], *, korean: bool, limit: int = 3) -> list[str]:
    """Return compact source-grounded snippets for local fallback answers."""
    takeaways: list[str] = []
    seen: set[str] = set()
    for citation in citations:
        text = clean_local_excerpt(citation.excerpt)
        if not text or text in seen:
            continue
        seen.add(text)
        if korean:
            takeaways.append(f"근거 [{citation.index}] {citation.title}: {text}")
        else:
            takeaways.append(f"Source [{citation.index}] {citation.title}: {text}")
        if len(takeaways) >= limit:
            break
    return takeaways


def clean_local_excerpt(text: str, max_chars: int = 360) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return ""
    if len(clean) <= max_chars:
        return clean
    truncated = clean[:max_chars].rsplit(" ", 1)[0].strip()
    return f"{truncated}..."


def is_injection_prediction(prediction_context: dict[str, Any] | None) -> bool:
    if not isinstance(prediction_context, dict):
        return False
    mode = str(prediction_context.get("mode") or prediction_context.get("prediction_mode") or "")
    return mode.lower().startswith("injection")


def current_prediction_explanations(
    prediction_context: dict[str, Any] | None,
    *,
    query: str = "",
    korean: bool,
) -> list[str]:
    if not isinstance(prediction_context, dict):
        return []
    if is_injection_prediction(prediction_context):
        return current_injection_prediction_explanations(prediction_context, query=query, korean=korean)
    return []


def current_injection_prediction_explanations(
    prediction_context: dict[str, Any],
    *,
    query: str = "",
    korean: bool,
) -> list[str]:
    inputs = prediction_context.get("inputs")
    xai = prediction_context.get("xai")
    if not isinstance(inputs, dict) and not isinstance(xai, dict):
        return []

    top_features: list[dict[str, Any]] = []
    if isinstance(xai, dict) and isinstance(xai.get("top_features"), list):
        top_features = [feature for feature in xai["top_features"] if isinstance(feature, dict)]

    feature_line = injection_feature_summary_line(top_features, query=query, korean=korean)
    pressure_line = injection_pressure_summary_line(prediction_context, korean=korean)
    input_line = injection_input_summary_line(inputs if isinstance(inputs, dict) else {}, korean=korean)

    if korean:
        lines = [
            "핵심부터 보면, 현재 Injection 예측은 Moldex3D 결과를 직접 다시 계산한 값이 아니라 저장된 DOE/CAE 데이터로 학습한 surrogate 모델의 결과입니다."
        ]
        if input_line:
            lines.append(input_line)
        if pressure_line:
            lines.append(pressure_line)
        if feature_line:
            lines.append(feature_line)
        else:
            lines.append("현재 prediction context에는 XAI 상위 feature가 없어서, 정량적인 영향도는 예측 실행 후 확인하는 것이 좋습니다.")
        lines.append("정리하면, 이 해석은 현재 앱에 표시된 surrogate 예측과 local XAI 기준의 설명입니다. 최종 설계 판단에는 Moldex3D 또는 실험 검증을 함께 보는 것이 안전합니다.")
        return lines

    lines = [
        "In short, the current Injection prediction is a surrogate-model result trained from DOE/CAE data, not a fresh Moldex3D solve."
    ]
    if input_line:
        lines.append(input_line)
    if pressure_line:
        lines.append(pressure_line)
    if feature_line:
        lines.append(feature_line)
    else:
        lines.append("The current prediction context does not include top XAI features, so quantitative influence should be checked after running a forecast.")
    lines.append("Treat this as a local explanation of the app prediction and XAI result. Final process decisions should still be checked with Moldex3D or experiment.")
    return lines


def injection_feature_summary_line(features: list[dict[str, Any]], *, query: str = "", korean: bool) -> str:
    if not features:
        return ""
    requested_keys = requested_injection_feature_keys(query)
    requested_feature = find_requested_injection_feature(features, requested_keys)
    if requested_keys and requested_feature is None:
        return missing_requested_injection_feature_line(features, requested_keys, korean=korean)
    if requested_feature is not None:
        return requested_injection_feature_line(requested_feature, features, korean=korean)
    top = features[:3]
    names = [str(feature.get("label") or feature.get("name") or f"feature {index}") for index, feature in enumerate(top, start=1)]
    lead = top[0]
    lead_name = names[0]
    lead_key = canonical_injection_feature_key(lead)
    importance = safe_float(lead.get("importance"))
    sensitivity = safe_float(lead.get("local_sensitivity"))
    current_value = lead.get("local_value")
    perturbation = lead.get("perturbation")
    if korean:
        details = []
        if importance is not None:
            details.append(f"importance {importance * 100:.1f}%")
        if sensitivity is not None:
            details.append(f"local sensitivity {sensitivity * 100:.1f}%")
        if current_value not in (None, ""):
            details.append(f"현재값 {current_value}")
        if perturbation:
            details.append(f"변화 조건 {perturbation}")
        detail_text = ", ".join(details)
        detail_text = f" ({detail_text})" if detail_text else ""
        return (
            f"현재 XAI에서 가장 큰 영향 인자는 {lead_name}{detail_text}입니다. "
            f"상위 인자는 {', '.join(names)} 순서로 나타납니다. "
            f"왜 크게 나왔는지를 공정 관점에서 보면, {INJECTION_FEATURE_EXPLANATIONS_KO.get(lead_key, '이 feature가 현재 압력 응답의 주요 변동 축과 연결되어 있기 때문일 가능성이 큽니다.')} "
            "다만 이 비율은 물리 법칙 자체가 아니라 현재 surrogate 모델의 local sensitivity이므로, 현재 입력 주변에서 이 값을 조금 바꿨을 때 Sprue Pressure 곡선과 Filling Pressure 분포 예측이 크게 흔들렸다는 뜻으로 해석하는 것이 맞습니다."
        )
    details = []
    if importance is not None:
        details.append(f"importance {importance * 100:.1f}%")
    if sensitivity is not None:
        details.append(f"local sensitivity {sensitivity * 100:.1f}%")
    if current_value not in (None, ""):
        details.append(f"current value {current_value}")
    if perturbation:
        details.append(f"perturbation {perturbation}")
    detail_text = ", ".join(details)
    detail_text = f" ({detail_text})" if detail_text else ""
    return (
        f"The strongest current XAI driver is {lead_name}{detail_text}. "
        f"The leading drivers are {', '.join(names)}. "
        f"Mechanistically, {INJECTION_FEATURE_EXPLANATIONS_EN.get(lead_key, 'this feature is likely tied to a major variation axis of the current pressure response.')} "
        "The percentage is not a physical law by itself; it means that around the current input, changing this feature caused a relatively large change in the surrogate sprue-pressure curve and filling-pressure field."
    )


INJECTION_FEATURE_ALIASES: dict[str, tuple[str, ...]] = {
    "melt_temp_C": ("수지 온도", "용융 온도", "melt temperature", "melt temp", "melttemp", "resin temperature"),
    "mold_temp_C": ("금형 온도", "mold temperature", "mold temp", "moldtemp"),
    "injection_time_s": ("사출 시간", "injection time", "injectiontime"),
    "packing_pressure_MPa": ("보압", "보압 압력", "packing pressure", "packingpressure"),
    "packing_time_s": ("보압 시간", "보압 유지 시간", "packing time", "packingtime", "holding time"),
    "process_total_time_s": ("총 공정 시간", "total process time", "process total time"),
    "gate_area_mm2": ("게이트 면적", "gate area"),
    "flow_length_to_thickness": ("유동 길이 두께비", "flow length thickness", "flow length to thickness"),
}

INJECTION_FEATURE_LABELS_KO: dict[str, str] = {
    "melt_temp_C": "수지 온도",
    "mold_temp_C": "금형 온도",
    "injection_time_s": "사출 시간",
    "packing_pressure_MPa": "보압",
    "packing_time_s": "보압 시간",
    "process_total_time_s": "총 공정 시간",
    "gate_area_mm2": "게이트 면적",
    "flow_length_to_thickness": "유동 길이/두께 비",
}

INJECTION_FEATURE_EXPLANATIONS_KO: dict[str, str] = {
    "melt_temp_C": "수지 온도는 점도를 바꾸는 가장 직접적인 공정 변수입니다. 온도가 높아지면 일반적으로 점도가 낮아져 같은 유량을 밀어 넣는 데 필요한 압력이 낮아지고, 온도가 낮으면 유동 저항이 커져 Sprue Pressure가 더 민감하게 변할 수 있습니다. 그래서 데이터셋 안에서 온도 변화가 압력 곡선의 높이와 기울기를 반복적으로 바꿨다면 XAI 비율이 크게 나오는 것이 자연스럽습니다.",
    "mold_temp_C": "금형 온도는 수지가 금형 벽 근처에서 얼마나 빨리 식고 점도가 올라가는지를 좌우합니다. 금형이 차가우면 유동 중 냉각이 빨라져 압력 손실이 커질 수 있고, 금형이 따뜻하면 유동성이 오래 유지됩니다. 따라서 얇은 형상이나 긴 유동 경로에서는 금형 온도가 압력 상승과 filling pressure 분포에 크게 작용할 수 있습니다.",
    "injection_time_s": "사출 시간은 같은 부피를 얼마나 빠르게 채우는지, 즉 평균 유량과 직접 연결됩니다. 짧은 시간에 채우면 유량 요구가 커져 압력 peak가 커질 수 있고, 긴 시간에서는 압력 상승이 완만해질 수 있습니다. 그래서 초기 Sprue Pressure 상승 구간과 peak 위치를 설명하는 데 중요한 신호가 됩니다.",
    "packing_pressure_MPa": "보압은 충전 이후 압력을 유지하는 설정값입니다. 충전 말기 이후에도 압력이 유지되면 late-stage pressure level과 pressure tail이 달라지고, 일부 조건에서는 peak pressure에도 영향을 줄 수 있습니다. 따라서 보압이 중요하다는 것은 모델이 충전 후반부 압력 유지 구간을 예측에 활용했다는 뜻에 가깝습니다.",
    "packing_time_s": "보압 시간은 충전 이후 보압을 얼마나 오래 유지하는지를 나타냅니다. 물리적으로는 초기 충전 peak보다는 후반부 pressure tail, 압력 유지 시간, filling pressure가 천천히 떨어지는 구간에 더 직접적으로 연결됩니다. 그래서 이 값의 영향이 크다면, 현재 예측에서 모델이 단순 peak 하나보다 압력 곡선의 후반 형태나 유지 구간을 중요하게 보고 있다는 해석이 더 적절합니다.",
    "process_total_time_s": "총 공정 시간은 사출 시간과 보압 시간을 합친 descriptor라 전체 압력 응답의 시간 스케일을 나타냅니다. 이 값이 중요하면 모델이 특정 한 순간의 압력보다 충전-보압으로 이어지는 전체 시간축의 길이와 곡선 형태를 함께 사용하고 있다는 의미일 수 있습니다.",
    "gate_area_mm2": "게이트 면적은 수지가 캐비티로 들어가는 입구의 유동 저항을 결정합니다. 게이트가 작으면 같은 유량에서 압력 손실이 커지고, 게이트가 크면 압력 손실이 줄어들 수 있습니다. 따라서 gate area가 중요하면 압력 예측이 공정 조건뿐 아니라 유동 입구 형상에도 민감하다는 뜻입니다.",
    "flow_length_to_thickness": "유동 길이/두께 비는 얇고 긴 유동 경로에서 압력 손실이 커지는 경향을 반영합니다. 값이 클수록 수지가 더 긴 거리 또는 더 얇은 단면을 지나야 하므로 Sprue Pressure와 filling pressure 분포가 커질 수 있습니다.",
}

INJECTION_FEATURE_EXPLANATIONS_EN: dict[str, str] = {
    "melt_temp_C": "Melt temperature is a direct process variable for viscosity. Higher melt temperature usually lowers viscosity and reduces the pressure needed for the same flow rate, while lower temperature increases flow resistance. If temperature changes repeatedly shift the pressure-curve level or slope in the dataset, it is reasonable for XAI to assign it a high share.",
    "mold_temp_C": "Mold temperature controls how quickly the melt cools near the wall. A colder mold can raise viscosity during filling and increase pressure loss, while a warmer mold helps the melt stay mobile for longer. This can strongly affect pressure buildup in thin or long-flow geometries.",
    "injection_time_s": "Injection time controls the required average flow rate. Shorter fill time tends to require higher flow and can raise the pressure peak, while longer fill time can smooth the pressure rise. It is therefore tied to the early sprue-pressure ramp and peak timing.",
    "packing_pressure_MPa": "Packing pressure is the late-stage pressure setpoint. It affects the post-filling pressure level and tail, and in some cases the peak pressure response. A high importance means the model is using the late pressure-holding phase, not only the initial filling peak.",
    "packing_time_s": "Packing time controls how long pressure is held after filling. It is more directly connected to the late pressure tail and sustained filling-pressure region than to the initial filling peak. If it is influential, the model is likely using the later shape of the pressure curve and the duration of the holding phase.",
    "process_total_time_s": "Total process time combines injection and packing duration, so it represents the overall time scale of the response. High importance can mean the model uses the full fill-to-pack curve shape rather than a single pressure value.",
    "gate_area_mm2": "Gate area controls inlet flow resistance. A smaller gate increases pressure loss for the same flow rate; a larger gate can reduce it. High gate-area importance indicates pressure prediction is sensitive to the inlet geometry.",
    "flow_length_to_thickness": "Flow length to thickness captures the pressure-loss tendency of long, thin flow paths. Larger values usually require higher pressure and can change the filling-pressure distribution.",
}


def requested_injection_feature_keys(query: str) -> list[str]:
    normalized = normalize_feature_text(query)
    if not normalized:
        return []
    matches: list[tuple[int, str]] = []
    for key, aliases in INJECTION_FEATURE_ALIASES.items():
        matched_alias_lengths = [len(normalize_feature_text(alias)) for alias in aliases if normalize_feature_text(alias) in normalized]
        if matched_alias_lengths:
            matches.append((max(matched_alias_lengths), key))
    return [key for _, key in sorted(matches, key=lambda item: item[0], reverse=True)]


def find_requested_injection_feature(features: list[dict[str, Any]], requested_keys: list[str]) -> dict[str, Any] | None:
    if not requested_keys:
        return None
    for key in requested_keys:
        for feature in features:
            feature_name = normalize_feature_text(str(feature.get("name") or ""))
            feature_label = normalize_feature_text(str(feature.get("label") or ""))
            aliases = (key, *INJECTION_FEATURE_ALIASES.get(key, ()))
            if any(normalize_feature_text(alias) in {feature_name, feature_label} for alias in aliases):
                return feature
    return None


def requested_injection_feature_line(
    feature: dict[str, Any],
    features: list[dict[str, Any]],
    *,
    korean: bool,
) -> str:
    name = str(feature.get("name") or "")
    key = canonical_injection_feature_key(feature)
    label = str(feature.get("label") or "") or INJECTION_FEATURE_LABELS_KO.get(key, name) or name
    importance = safe_float(feature.get("importance"))
    sensitivity = safe_float(feature.get("local_sensitivity"))
    current_value = feature.get("local_value")
    perturbation = feature.get("perturbation")
    rank = next((index for index, item in enumerate(features, start=1) if item is feature), None)
    if korean:
        details = []
        if importance is not None:
            details.append(f"importance {importance * 100:.1f}%")
        if sensitivity is not None:
            details.append(f"local sensitivity {sensitivity * 100:.1f}%")
        if current_value not in (None, ""):
            details.append(f"현재값 {current_value}")
        if perturbation:
            details.append(f"변화 조건 {perturbation}")
        rank_text = f"현재 XAI 상위 feature 중 {rank}번째로 표시되며, " if rank is not None else "현재 XAI에서 "
        explanation = INJECTION_FEATURE_EXPLANATIONS_KO.get(key) or str(feature.get("explanation") or "")
        return (
            f"질문에서 물어본 {label}{korean_topic_particle(label)} {rank_text}{', '.join(details)}입니다.\n\n"
            f"{explanation} "
            "따라서 이 항목의 영향은 전체 1등 feature를 설명하는 것이 아니라, 사용자가 물어본 feature가 현재 입력 주변에서 압력 곡선의 어느 구간을 흔드는지를 보여주는 값으로 해석해야 합니다.\n\n"
            "XAI 비율이 크다면 해당 feature가 모델의 예측 벡터를 많이 바꿨다는 뜻이고, 비율이 작다면 물리적으로 의미가 없다는 뜻이 아니라 현재 조건에서는 다른 변수보다 예측 민감도가 작았다는 뜻입니다."
        )
    details = []
    if importance is not None:
        details.append(f"importance {importance * 100:.1f}%")
    if sensitivity is not None:
        details.append(f"local sensitivity {sensitivity * 100:.1f}%")
    if current_value not in (None, ""):
        details.append(f"current value {current_value}")
    if perturbation:
        details.append(f"perturbation {perturbation}")
    rank_text = f"ranked #{rank} among the current XAI features and " if rank is not None else ""
    explanation = INJECTION_FEATURE_EXPLANATIONS_EN.get(key) or str(feature.get("explanation") or "")
    return (
        f"The requested feature, {label}, is {rank_text}{', '.join(details)}.\n\n"
        f"{explanation} "
        "This explains the requested feature specifically, rather than repeating the strongest overall feature.\n\n"
        "A high XAI share means the feature changed the model output vector substantially around the current input; a low share does not mean the physics is irrelevant, only that other variables were more locally sensitive in this prediction."
    )


def missing_requested_injection_feature_line(features: list[dict[str, Any]], requested_keys: list[str], *, korean: bool) -> str:
    requested = requested_keys[0]
    requested_label = INJECTION_FEATURE_LABELS_KO.get(requested, requested) if korean else requested.replace("_", " ")
    top_names = [str(feature.get("label") or feature.get("name") or "") for feature in features[:3]]
    if korean:
        return (
            f"질문에서 물어본 {requested_label}은 현재 Assistant에 전달된 XAI 상위 feature 목록 안에서는 찾지 못했습니다. "
            f"현재 전달된 상위 인자는 {', '.join(top_names)}입니다.\n\n"
            "그래서 이 경우에는 수지 온도 같은 1등 feature를 대신 설명하기보다, 보압 시간의 정량 영향도를 보려면 해당 feature가 포함된 전체 XAI 목록을 함께 전달해야 합니다."
        )
    return (
        f"The requested feature, {requested_label}, was not found in the XAI features currently sent to the assistant. "
        f"The leading transmitted features are {', '.join(top_names)}.\n\n"
        "In this case, it is better to report that the requested feature is unavailable than to repeat the strongest overall driver."
    )


def canonical_injection_feature_key(feature: dict[str, Any]) -> str:
    raw_values = [str(feature.get("name") or ""), str(feature.get("label") or "")]
    for key, aliases in INJECTION_FEATURE_ALIASES.items():
        normalized_aliases = {normalize_feature_text(alias) for alias in (key, *aliases)}
        if any(normalize_feature_text(value) in normalized_aliases for value in raw_values):
            return key
    return str(feature.get("name") or feature.get("label") or "")


def injection_feature_mechanism_for_name(name: Any) -> str:
    feature = {"name": str(name), "label": str(name)}
    key = canonical_injection_feature_key(feature)
    return INJECTION_FEATURE_EXPLANATIONS_EN.get(key) or INJECTION_FEATURE_EXPLANATIONS_KO.get(key) or ""


def korean_topic_particle(label: str) -> str:
    text = str(label).strip()
    if not text:
        return "은"
    last = text[-1]
    if not ("가" <= last <= "힣"):
        return "은"
    code = ord(last) - ord("가")
    has_final_consonant = code % 28 != 0
    return "은" if has_final_consonant else "는"


def normalize_feature_text(value: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]+", "", value.lower())


def injection_pressure_summary_line(prediction_context: dict[str, Any], *, korean: bool) -> str:
    max_pressure = prediction_context.get("predicted_max_pressure_MPa")
    max_time = prediction_context.get("predicted_max_time_s")
    filling_max = prediction_context.get("predicted_filling_max_MPa")
    parts = []
    if max_pressure not in (None, ""):
        parts.append(f"Sprue Pressure 최대값 {max_pressure} MPa" if korean else f"maximum sprue pressure {max_pressure} MPa")
    if max_time not in (None, ""):
        parts.append(f"발생 시간 {max_time} s" if korean else f"time {max_time} s")
    if filling_max not in (None, ""):
        parts.append(f"Filling Pressure 최대값 {filling_max} MPa" if korean else f"maximum filling pressure {filling_max} MPa")
    if not parts:
        return ""
    if korean:
        return "현재 출력 기준으로는 " + ", ".join(parts) + "가 함께 제공되어 공정 조건 변화가 압력 응답에 어떻게 연결되는지 볼 수 있습니다."
    return "The current output provides " + ", ".join(parts) + ", so the process-condition effect can be interpreted against the pressure response."


def injection_input_summary_line(inputs: dict[str, Any], *, korean: bool) -> str:
    if not inputs:
        return ""
    keys = (
        ("geometry_id", "Geometry", "형상"),
        ("process_id", "Process", "공정"),
        ("melt_temp_C", "melt temperature", "수지 온도"),
        ("mold_temp_C", "mold temperature", "금형 온도"),
        ("injection_time_s", "injection time", "사출 시간"),
        ("packing_pressure_MPa", "packing pressure", "보압"),
        ("packing_time_s", "packing time", "보압 시간"),
        ("gate_type", "gate type", "게이트 형식"),
    )
    parts = []
    for key, en_label, ko_label in keys:
        value = inputs.get(key)
        if value not in (None, ""):
            parts.append(f"{ko_label} {value}" if korean else f"{en_label} {value}")
    if not parts:
        return ""
    if korean:
        return "현재 입력 조건은 " + ", ".join(parts[:7]) + "입니다."
    return "The current input condition is " + ", ".join(parts[:7]) + "."


def safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def compact_prediction_context(prediction_context: dict[str, Any] | None) -> str:
    if not prediction_context:
        return ""
    allowed_top = 24
    lines: list[str] = []
    mode = prediction_context.get("mode") or prediction_context.get("prediction_mode")
    if mode:
        lines.append(f"Prediction mode: {mode}")

    inputs = prediction_context.get("inputs")
    if isinstance(inputs, dict):
        input_parts = []
        for key in (
            "theta1",
            "theta2",
            "case",
            "test_id",
            "geometry_id",
            "process_id",
            "L_mm",
            "W_mm",
            "t_mm",
            "D_mm",
            "R_mm",
            "gate_type",
            "gate_size_width_mm",
            "gate_size_height_mm",
            "melt_temp_C",
            "mold_temp_C",
            "injection_time_s",
            "packing_pressure_MPa",
            "packing_time_s",
        ):
            value = inputs.get(key)
            if value not in (None, ""):
                input_parts.append(f"{key}={value}")
        if input_parts:
            lines.append("Inputs: " + ", ".join(input_parts))
        if not str(mode or "").lower().startswith("injection"):
            physics_context = current_laminate_physics_context(inputs)
            if physics_context:
                lines.extend(physics_context)

    for label, key in (
        ("Model", "model_label"),
        ("Model key", "model_key"),
        ("Filling model", "filling_model_label"),
        ("Filling model key", "filling_model_key"),
        ("Predicted Type", "predicted_type"),
        ("Confidence", "confidence"),
        ("Predicted Pt", "predicted_pt"),
        ("Max displacement", "predicted_max_displacement"),
        ("Max force", "predicted_max_force"),
        ("Predicted max sprue pressure", "predicted_max_pressure_MPa"),
        ("Predicted max pressure time", "predicted_max_time_s"),
        ("Predicted filling max pressure", "predicted_filling_max_MPa"),
        ("Curve point count", "curve_points"),
    ):
        value = prediction_context.get(key)
        if value not in (None, ""):
            lines.append(f"{label}: {value}")

    if not str(mode or "").lower().startswith("injection"):
        distribution_context = current_target_distribution_context(prediction_context)
        if distribution_context:
            lines.extend(distribution_context)

    xai = prediction_context.get("xai")
    if isinstance(xai, dict):
        method = xai.get("method")
        feature_set = xai.get("feature_set")
        if method:
            lines.append(f"XAI method: {method}")
        if feature_set:
            lines.append(f"XAI feature set: {feature_set}")
        features = xai.get("top_features")
        if isinstance(features, list) and features:
            lines.append("Top local XAI features:")
            for index, feature in enumerate(features[:allowed_top], start=1):
                if not isinstance(feature, dict):
                    continue
                name = feature.get("label") or feature.get("name") or f"feature {index}"
                importance = feature.get("importance")
                sensitivity = feature.get("local_sensitivity")
                current_value = feature.get("local_value")
                perturbation = feature.get("perturbation")
                explanation = feature.get("explanation")
                mechanism = injection_feature_mechanism_for_name(name) if str(mode or "").lower().startswith("injection") else ""
                parts = [str(name)]
                if importance is not None:
                    parts.append(f"importance={importance}")
                if sensitivity is not None:
                    parts.append(f"local_sensitivity={sensitivity}")
                if current_value is not None:
                    parts.append(f"current_value={current_value}")
                if perturbation:
                    parts.append(f"perturbation={perturbation}")
                if explanation:
                    parts.append(f"app_explanation={explanation}")
                if mechanism:
                    parts.append(f"process_mechanism={mechanism}")
                lines.append(f"{index}. " + ", ".join(parts))

    return "\n".join(lines[:65])


@lru_cache(maxsize=1)
def response_target_distribution() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    if not RESPONSE_MANIFEST_PATH.exists():
        return {"rows": [], "cases": {}}
    with RESPONSE_MANIFEST_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                rows.append(
                    {
                        "case": str(row["case"]),
                        "type": int(float(row["type"])),
                        "pt": float(row["pt"]),
                    }
                )
            except (KeyError, TypeError, ValueError):
                continue
    cases: dict[str, dict[str, Any]] = {}
    all_pts = sorted(float(row["pt"]) for row in rows)
    for case in ("Case2", "Case3", "Case4"):
        case_rows = [row for row in rows if row["case"] == case]
        pts = sorted(float(row["pt"]) for row in case_rows)
        type_counts = {
            type_id: sum(1 for row in case_rows if row["type"] == type_id)
            for type_id in (1, 2, 3)
        }
        cases[case] = {
            "count": len(case_rows),
            "type_counts": type_counts,
            "pts": pts,
            "min_pt": min(pts) if pts else None,
            "median_pt": percentile_value(pts, 0.5) if pts else None,
            "max_pt": max(pts) if pts else None,
        }
    return {
        "rows": rows,
        "all_pts": all_pts,
        "all_count": len(rows),
        "all_min_pt": min(all_pts) if all_pts else None,
        "all_median_pt": percentile_value(all_pts, 0.5) if all_pts else None,
        "all_max_pt": max(all_pts) if all_pts else None,
        "cases": cases,
    }


def percentile_value(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    position = max(0.0, min(1.0, fraction)) * (len(values) - 1)
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    weight = position - lower
    return values[lower] * (1.0 - weight) + values[upper] * weight


def percentile_rank(values: list[float], value: float) -> float | None:
    if not values:
        return None
    below_or_equal = sum(1 for item in values if item <= value)
    return below_or_equal / len(values)


def current_target_distribution_context(prediction_context: dict[str, Any]) -> list[str]:
    predicted_type = prediction_context.get("predicted_type")
    predicted_pt = _float_or_none(prediction_context.get("predicted_pt"))
    inputs = prediction_context.get("inputs")
    case = str(inputs.get("case") if isinstance(inputs, dict) else "").replace(" ", "")
    distribution = response_target_distribution()
    if not distribution.get("rows"):
        return []

    lines = [
        "Type definitions used by this project:",
        TYPE_DEFINITIONS[1],
        TYPE_DEFINITIONS[2],
        TYPE_DEFINITIONS[3],
    ]
    cases = distribution.get("cases", {})
    case_summary = cases.get(case) if isinstance(cases, dict) else None
    if isinstance(case_summary, dict) and case_summary.get("count"):
        count = int(case_summary["count"])
        type_counts = case_summary.get("type_counts") or {}
        type_parts = []
        for type_id in (1, 2, 3):
            type_count = int(type_counts.get(type_id, 0))
            type_parts.append(f"Type {type_id}={type_count} ({type_count / count:.1%})")
        lines.append(
            f"Target distribution for {case}: {count} curated response samples; "
            + ", ".join(type_parts)
            + "."
        )
        lines.append(
            f"Pt distribution for {case}: min={case_summary['min_pt']:.2f}, "
            f"median={case_summary['median_pt']:.2f}, max={case_summary['max_pt']:.2f}."
        )
        if predicted_pt is not None:
            rank = percentile_rank(case_summary.get("pts") or [], predicted_pt)
            if rank is not None:
                lines.append(f"Current predicted Pt percentile within {case}: {rank * 100:.1f}%.")

    if predicted_type is not None:
        try:
            type_id = int(float(predicted_type))
            if type_id in TYPE_DEFINITIONS:
                lines.append(f"Current predicted Type meaning: {TYPE_DEFINITIONS[type_id]}")
        except (TypeError, ValueError):
            pass
    return lines


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def current_laminate_physics_context(inputs: dict[str, Any]) -> list[str]:
    theta1 = _float_or_none(inputs.get("theta1"))
    theta2 = _float_or_none(inputs.get("theta2"))
    case = str(inputs.get("case") or "").replace(" ", "")
    if theta1 is None or theta2 is None or case not in {"Case2", "Case3", "Case4"}:
        return []
    try:
        _a, _b, d_matrix, stack = abd_matrices(case, theta1, theta2)
        feature_values = dict(
            zip(
                COMPACT_PHYSICS_FEATURE_COLUMNS,
                compact_physics_feature_vector(case, theta1, theta2),
                strict=True,
            )
        )
    except (ValueError, FloatingPointError):
        return []

    h = DEFAULT_MATERIAL.ply_thickness_in * len(stack)
    pattern = {
        "Case2": "[[±θ₁]/[±θ₂]]₄",
        "Case3": "[[±θ₁]/[±θ₂]/[∓θ₁]/[∓θ₂]]₂",
        "Case4": "[([±θ₁]/[±θ₂])₂ / ([∓θ₁]/[∓θ₂])₂]",
    }[case]
    stack_preview = ", ".join(f"{angle:g}" for angle in stack)
    return [
        f"Laminate stack formula: {case} = {pattern}.",
        f"Expanded stack for current input: [{stack_preview}] degrees.",
        (
            "D11 calculation basis: D11 is the (1,1) term of the CLT bending stiffness matrix "
            "D = sum(Qbar_k * (z_k^3 - z_{k-1}^3) / 3) through the ply thickness."
        ),
        (
            "Current material and geometry constants: "
            f"E11={DEFAULT_MATERIAL.e11_msi} Msi, E22={DEFAULT_MATERIAL.e22_msi} Msi, "
            f"G12={DEFAULT_MATERIAL.g12_msi} Msi, nu12={DEFAULT_MATERIAL.nu12}, "
            f"ply thickness={DEFAULT_MATERIAL.ply_thickness_in} in, total thickness={h:.6g} in."
        ),
        (
            "Current computed stiffness descriptors: "
            f"raw D11={d_matrix[0, 0]:.6g}, normalized d11={feature_values['d11']:.6g}, "
            f"d22={feature_values['d22']:.6g}, d11/d22={feature_values['d11_d22_ratio']:.6g}, "
            f"bending anisotropy={feature_values['bending_anisotropy']:.6g}."
        ),
        (
            "Simulation data status: this app prediction is a surrogate forecast from theta/case. "
            "Unless a source_csv or test_id is attached, it should not be described as an exact Abaqus result for this exact input."
        ),
    ]


def matched_feature_explanations(query: str, *, korean: bool) -> list[str]:
    normalized = query.lower().replace("-", "_").replace(" ", "_")
    matches: list[str] = []
    for key, (label, ko_summary, ko_importance) in FEATURE_GLOSSARY.items():
        label_normalized = label.lower().replace("-", "_").replace(" ", "_")
        if key in normalized or label_normalized in normalized:
            if korean:
                matches.append(f"- {label}은 {ko_summary} {ko_importance}")
            else:
                matches.append(f"- {label}: {english_feature_summary(key, ko_summary, ko_importance)}")
    return matches


def english_feature_summary(key: str, ko_summary: str, ko_importance: str) -> str:
    english = {
        "d11": (
            "the load-direction bending stiffness term in the laminate D matrix. "
            "It matters because it is directly tied to bending resistance, Pt, and post-kink response shape."
        ),
        "d22": (
            "the transverse bending stiffness term in the laminate D matrix. "
            "Its balance with D11 helps describe bending anisotropy and transition behavior."
        ),
        "d12": (
            "a bending-coupling term in the D matrix. "
            "It helps explain whether the post-transition curve stays near-bilinear or becomes more curved."
        ),
        "d66": (
            "the twisting/shear bending stiffness term in the D matrix. "
            "It can influence buckling-like mode changes and post-transition curve shape."
        ),
        "a11": (
            "the load-direction membrane stiffness term in the A matrix. "
            "It helps explain the early force-displacement slope and axial load transfer."
        ),
        "a22": (
            "the transverse membrane stiffness term in the A matrix. "
            "Its ratio with A11 indicates membrane anisotropy."
        ),
        "a12": (
            "the in-plane membrane coupling term in the A matrix. "
            "It helps explain how axial and transverse deformation are coupled across theta/case choices."
        ),
        "a66": (
            "the in-plane shear stiffness term in the A matrix. "
            "It describes how much shear contribution the angle pair provides."
        ),
        "b11": (
            "the load-direction membrane-bending coupling term in the B matrix. "
            "In asymmetric laminates, it can affect transition location and post-transition curvature."
        ),
        "b22": (
            "the transverse membrane-bending coupling term in the B matrix. "
            "It helps distinguish case-dependent stacking-order effects."
        ),
        "b12": (
            "a cross membrane-bending coupling term in the B matrix. "
            "Larger membrane-bending interaction can make the response curve more complex after the knee."
        ),
    }
    return english.get(key, f"{ko_summary} {ko_importance}")


def call_openai_responses(
    query: str,
    results: list[QueryResult],
    *,
    model: str,
    language: str,
    prediction_context: dict[str, Any] | None = None,
    timeout: int = 45,
) -> str:
    api_key = os.environ["OPENAI_API_KEY"]
    context = "\n\n".join(
        f"[{index}] {result.chunk.title}\n"
        f"Source: {result.chunk.url or result.chunk.source_path}\n"
        f"Topic: {result.chunk.topic}\n"
        f"Excerpt: {result.chunk.text[:1600]}"
        for index, result in enumerate(results, start=1)
    )
    language_instruction = (
        "Answer in Korean unless the user explicitly asks for English."
        if language in {"auto", "ko"}
        else "Answer in English."
    )
    prediction_summary = compact_prediction_context(prediction_context)
    prediction_instruction = (
            "If Current prediction context is provided, use it as the active result currently shown in the app. "
            "You may describe quantitative contribution only from the supplied predicted values and XAI fields such as importance and local_sensitivity. "
            "If Type definitions or target distributions are present in Current prediction context, use them directly and do not say they are missing. "
            "Clearly distinguish this current-model explanation from general laminate, injection molding, or CAE theory. "
        "If no Current prediction context is provided, say that quantitative contribution needs a prediction result and XAI context."
    )
    prediction_block = (
        f"Current prediction context:\n{prediction_summary}\n\n"
        if prediction_summary
        else "Current prediction context:\nNone. The user has not supplied an active prediction result to this request.\n\n"
    )
    payload = {
        "model": model,
        "store": False,
        "instructions": (
            "You are a composites and CAE surrogate-model research assistant for Double-Double laminate AI and Moldex3D injection AI. "
            "Use only the provided retrieved context and cite sources with bracketed citation numbers. "
            "If the context is insufficient, say what is missing. "
            "Do not invent experimental results, model metrics, or material properties. "
            "Write like a careful human engineer explaining the topic to another engineer. "
            "Use natural connected paragraphs. Avoid Markdown formatting, bold markers, headings, and bullet lists unless absolutely necessary. "
            "Do not use LaTeX notation such as \\(A_{12}\\); write engineering terms as plain text such as A12 and D11. "
            "For laminate case formulas, use the app notation with Greek symbols and subscripts, such as θ₁ and θ₂. "
            "For injection predictions, explain geometry, process, gate, and derived-flow features in terms of sprue pressure curves and filling pressure distributions. "
            "When the user asks why an Injection XAI feature matters, do not only repeat the percentage. Explain the likely causal chain: process/geometry input -> viscosity, flow resistance, pressure loss, fill/pack timing, or curve shape -> model sensitivity. "
            "If the user names a specific feature, answer about that named feature even when another feature has the highest importance. "
            "Do not say 'retrieved context'; say 'the reference material' or use a natural Korean equivalent. "
            f"{prediction_instruction} "
            f"{language_instruction}"
        ),
        "input": (
            f"User question:\n{query}\n\n"
            f"{prediction_block}"
            f"Retrieved context:\n{context}\n\n"
            "Write a concise, natural answer in plain text. Include citations like [1] or [2]."
        ),
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
    output_text = body.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()
    return extract_response_text(body)


def clean_answer_text(text: str) -> str:
    """Normalize model output for plain web copy."""
    cleaned = text.strip()
    cleaned = re.sub(r"\\\((.*?)\\\)", r"\1", cleaned)
    cleaned = re.sub(r"\\\[(.*?)\\\]", r"\1", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"\$([^$]+)\$", r"\1", cleaned)
    cleaned = re.sub(r"\{([A-Za-z])\}_\{?([A-Za-z0-9]+)\}?", r"\1\2", cleaned)
    cleaned = re.sub(r"([A-Za-z])_\{?([A-Za-z0-9]+)\}?", r"\1\2", cleaned)
    cleaned = cleaned.replace("**", "")
    cleaned = cleaned.replace("__", "")
    cleaned = cleaned.replace("Retrieved context에서도", "근거 자료에서도")
    cleaned = cleaned.replace("Retrieved context에서", "근거 자료에서")
    cleaned = cleaned.replace("retrieved context", "reference material")
    cleaned = cleaned.replace("Retrieved context", "Reference material")
    cleaned = re.sub(r"\blocalsensitivity\b", "local sensitivity", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bvirtualremoval\b", "virtual removal", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bcurrentvalue\b", "current value", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bbendinganisotropy\b", "bending anisotropy", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bd11_d22_ratio\b", "d11/d22 ratio", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bangleminabs\b", "angle min abs", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\banglemaxabs\b", "angle max abs", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bangleabsstd\b", "angle abs std", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\babstheta([12])\b", r"abs theta\1", cleaned, flags=re.IGNORECASE)
    if contains_korean(cleaned):
        cleaned = re.sub(r"\bmasked to 0\b", "0으로 대체", cleaned, flags=re.IGNORECASE)
    else:
        cleaned = re.sub(r"\bmasked to 0\b", "replaced with 0", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", cleaned)
    cleaned = re.sub(r"(?m)^\s*[-*]\s+", "", cleaned)
    cleaned = re.sub(r"(?m)^\s*\d+\.\s+", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def format_answer_for_display(text: str, *, prediction_context: dict[str, Any] | None = None) -> str:
    """Keep assistant answers readable in compact web and native cards."""
    cleaned = clean_answer_text(text)
    if not is_injection_prediction(prediction_context):
        return cleaned
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n{2,}", cleaned) if paragraph.strip()]
    if len(paragraphs) >= 2:
        return "\n\n".join(paragraphs)

    sentences = re.split(r"(?<=[.!?。]|다\.|요\.)\s+", cleaned)
    sentences = [sentence.strip() for sentence in sentences if sentence.strip()]
    if len(sentences) <= 3:
        return cleaned
    grouped = [
        " ".join(sentences[:1]),
        " ".join(sentences[1:3]),
        " ".join(sentences[3:5]),
    ]
    if len(sentences) > 5:
        grouped.append(" ".join(sentences[5:]))
    return "\n\n".join(part for part in grouped if part)


def extract_response_text(response_body: dict[str, object]) -> str:
    parts: list[str] = []
    for item in response_body.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str):
                parts.append(text)
    answer = "\n".join(part.strip() for part in parts if part.strip())
    if not answer:
        raise ValueError("OpenAI response did not contain output text")
    return answer


def contains_korean(text: str) -> bool:
    return any("가" <= char <= "힣" for char in text)


def trim_excerpt(text: str, *, limit: int = 240) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."
