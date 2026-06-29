from __future__ import annotations

import json
from pathlib import Path

from src.data.rag.indexer import (
    build_knowledge_index,
    extract_pptx_text_from_zip,
    load_online_chunks,
    query_index,
    tokenize,
)


def test_load_online_chunks_from_jsonl(tmp_path: Path) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    (chunks_dir / "source.jsonl").write_text(
        json.dumps(
            {
                "source_id": "nasa_doc",
                "chunk_index": 0,
                "title": "NASA laminate guide",
                "text": "Composite laminated plates and stiffness matrix.",
                "url": "https://nasa.gov/example.pdf",
                "topic": "laminate_mechanics",
                "tags": ["NASA"],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    chunks = load_online_chunks(chunks_dir)

    assert len(chunks) == 1
    assert chunks[0].chunk_id == "online:nasa_doc:0"
    assert chunks[0].tags == ["NASA"]


def test_build_and_query_index_with_internal_markdown(tmp_path: Path) -> None:
    project_root = tmp_path
    docs_dir = project_root / "docs"
    docs_dir.mkdir()
    (docs_dir / "DD_Laminate_Test.md").write_text(
        "Double-Double laminate Type prediction uses theta angles and Pt response.",
        encoding="utf-8",
    )
    online_chunks = project_root / "data" / "rag" / "online_corpus" / "chunks"
    online_chunks.mkdir(parents=True)
    (online_chunks / "online.jsonl").write_text(
        json.dumps(
            {
                "source_id": "stanford",
                "chunk_index": 0,
                "title": "Double-Double manufacturing",
                "text": "Double-Double laminates simplify composite manufacturing.",
                "url": "https://stanford.edu/example",
                "topic": "double_double_laminate",
                "tags": ["double-double"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    output = project_root / "index.json"

    payload = build_knowledge_index(project_root=project_root, output_path=output)
    results = query_index(output, "theta Pt Double-Double", top_k=2)

    assert payload["chunk_count"] >= 2
    assert output.exists()
    assert results
    assert any("Pt response" in result.chunk.text for result in results)


def test_tokenize_keeps_korean_and_domain_terms() -> None:
    tokens = tokenize("Double-Double 적층 예측 θ1 theta1 A12 membrane coupling")

    assert "double-double" in tokens
    assert "적층" in tokens
    assert "theta1" in tokens
    assert "a12" in tokens


def test_extract_pptx_text_from_zip_fallback(tmp_path: Path) -> None:
    pptx_path = tmp_path / "sample.pptx"
    slide_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        "<p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>Laminate purpose</a:t>"
        "</a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>"
    )
    import zipfile

    with zipfile.ZipFile(pptx_path, "w") as archive:
        archive.writestr("ppt/slides/slide1.xml", slide_xml)

    text = extract_pptx_text_from_zip(pptx_path)

    assert "Slide 1: Laminate purpose" in text
