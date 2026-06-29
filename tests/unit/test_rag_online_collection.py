from __future__ import annotations

import json
from pathlib import Path

from src.data.rag.collector import chunk_text, collect_source, extract_html_text
from src.data.rag.sources import DEFAULT_ALLOWED_DOMAINS, RagSource, is_allowed_domain, load_sources


def test_online_source_catalog_is_allowlisted() -> None:
    sources = load_sources(Path("data/rag/online_sources.seed.json"))

    assert sources
    assert all(is_allowed_domain(source.hostname, DEFAULT_ALLOWED_DOMAINS) for source in sources)


def test_metadata_only_source_does_not_download(tmp_path: Path) -> None:
    source = RagSource(
        source_id="aiaa_test",
        title="AIAA landing page",
        url="https://arc.aiaa.org/doi/10.2514/1.J060659",
        topic="double_double_laminate",
        source_type="journal_landing_page",
        priority=1,
        ingest_mode="metadata_only",
    )

    result = collect_source(source, tmp_path)

    assert result.status == "metadata_only"
    assert result.raw_path == ""


def test_collect_source_writes_raw_text_and_chunks(tmp_path: Path) -> None:
    source = RagSource(
        source_id="stanford_test",
        title="Stanford test page",
        url="https://techfinder.stanford.edu/example",
        topic="double_double_laminate",
        source_type="institutional_web_page",
        priority=1,
    )

    def fake_fetcher(url: str, timeout: int) -> tuple[bytes, str]:
        assert url == source.url
        assert timeout == 30
        return (
            b"<html><body><h1>Double-Double</h1><script>x()</script>"
            b"<p>Composite laminate text for retrieval.</p></body></html>",
            "text/html",
        )

    result = collect_source(source, tmp_path, fetcher=fake_fetcher)

    assert result.status == "collected"
    assert result.bytes_downloaded > 0
    assert Path(result.raw_path).exists()
    assert Path(result.text_path).read_text(encoding="utf-8") == (
        "Double-Double Composite laminate text for retrieval.\n"
    )
    chunk_lines = Path(result.chunks_path).read_text(encoding="utf-8").splitlines()
    assert len(chunk_lines) == 1
    assert json.loads(chunk_lines[0])["source_id"] == "stanford_test"


def test_blocked_domain_is_not_collected(tmp_path: Path) -> None:
    source = RagSource(
        source_id="blocked",
        title="Blocked",
        url="https://example.com/page",
        topic="general",
        source_type="web",
        priority=1,
    )

    result = collect_source(source, tmp_path)

    assert result.status == "blocked_domain"
    assert "example.com" in result.error


def test_html_extraction_and_chunking() -> None:
    text = extract_html_text(
        b"<html><body><style>.x{}</style><h1>Title</h1><p>First sentence. Second sentence.</p></body></html>"
    )
    chunks = chunk_text(text, max_chars=24, overlap=5)

    assert text == "Title First sentence. Second sentence."
    assert chunks == ["Title First sentence.", "ence. Second sentence."]
