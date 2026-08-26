"""Online source collector for a composite-domain RAG corpus."""

from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import ssl
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.data.rag.sources import DEFAULT_ALLOWED_DOMAINS, RagSource, is_allowed_domain

FetchBytes = Callable[[str, int], tuple[bytes, str]]


@dataclass(frozen=True)
class CollectionResult:
    """Result for one source collection attempt."""

    source_id: str
    title: str
    url: str
    hostname: str
    topic: str
    source_type: str
    priority: int
    ingest_mode: str
    status: str
    fetched_at: str
    content_type: str = ""
    raw_path: str = ""
    text_path: str = ""
    chunks_path: str = ""
    bytes_downloaded: int = 0
    sha256: str = ""
    chunk_count: int = 0
    error: str = ""
    license_note: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._hidden_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self._hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self._hidden_depth:
            self._hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._hidden_depth == 0:
            text = normalize_text(data)
            if text:
                self.parts.append(text)


def collect_sources(
    sources: list[RagSource],
    output_dir: str | Path,
    *,
    allowed_domains: tuple[str, ...] = DEFAULT_ALLOWED_DOMAINS,
    download: bool = True,
    timeout: int = 30,
    limit: int | None = None,
    fetcher: FetchBytes | None = None,
) -> list[CollectionResult]:
    """Collect a list of online sources into raw, text, and chunk artifacts."""
    selected = sources[:limit] if limit is not None else sources
    return [
        collect_source(
            source,
            output_dir,
            allowed_domains=allowed_domains,
            download=download,
            timeout=timeout,
            fetcher=fetcher,
        )
        for source in selected
    ]


def collect_source(
    source: RagSource,
    output_dir: str | Path,
    *,
    allowed_domains: tuple[str, ...] = DEFAULT_ALLOWED_DOMAINS,
    download: bool = True,
    timeout: int = 30,
    fetcher: FetchBytes | None = None,
) -> CollectionResult:
    output_path = Path(output_dir)
    fetched_at = datetime.now(timezone.utc).isoformat()
    if not is_allowed_domain(source.hostname, allowed_domains):
        return _result(
            source, fetched_at, "blocked_domain", error=f"Domain not allowed: {source.hostname}"
        )

    if source.ingest_mode == "metadata_only" or not download:
        return _result(source, fetched_at, "metadata_only")

    raw_dir = output_path / "raw"
    text_dir = output_path / "text"
    chunks_dir = output_path / "chunks"
    for directory in (raw_dir, text_dir, chunks_dir):
        directory.mkdir(parents=True, exist_ok=True)

    try:
        raw_bytes, content_type = (fetcher or fetch_url_bytes)(source.url, timeout)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        return _result(source, fetched_at, "fetch_error", error=str(exc))

    suffix = guess_suffix(source.url, content_type)
    safe_id = sanitize_source_id(source.source_id)
    raw_path = raw_dir / f"{safe_id}{suffix}"
    text_path = text_dir / f"{safe_id}.txt"
    chunks_path = chunks_dir / f"{safe_id}.jsonl"

    raw_path.write_bytes(raw_bytes)
    text, extraction_note = extract_text(raw_bytes, content_type, source.url)
    if text:
        text_path.write_text(text + "\n", encoding="utf-8")
        chunks = chunk_text(text)
        chunks_path.write_text(
            "".join(
                json.dumps(
                    {
                        "source_id": source.source_id,
                        "chunk_index": index,
                        "text": chunk,
                        "url": source.url,
                        "title": source.title,
                        "topic": source.topic,
                        "tags": list(source.tags),
                    },
                    ensure_ascii=False,
                )
                + "\n"
                for index, chunk in enumerate(chunks)
            ),
            encoding="utf-8",
        )
        status = "collected"
    else:
        chunks = []
        status = "raw_only"

    digest = hashlib.sha256(raw_bytes).hexdigest()
    notes = source.notes
    if extraction_note:
        notes = f"{notes} {extraction_note}".strip()

    return CollectionResult(
        source_id=source.source_id,
        title=source.title,
        url=source.url,
        hostname=source.hostname,
        topic=source.topic,
        source_type=source.source_type,
        priority=source.priority,
        ingest_mode=source.ingest_mode,
        status=status,
        fetched_at=fetched_at,
        content_type=content_type,
        raw_path=str(raw_path),
        text_path=str(text_path) if text else "",
        chunks_path=str(chunks_path) if chunks else "",
        bytes_downloaded=len(raw_bytes),
        sha256=digest,
        chunk_count=len(chunks),
        license_note=source.license_note,
        notes=notes,
    )


def write_collection_manifest(path: str | Path, results: list[CollectionResult]) -> None:
    manifest_path = Path(path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "result_count": len(results),
        "results": [result.to_dict() for result in results],
    }
    manifest_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def fetch_url_bytes(url: str, timeout: int) -> tuple[bytes, str]:
    headers = {
        "User-Agent": "KyulAI-RAG-Collector/0.1 (+https://local.kyulai)",
        "Accept": "text/html,application/pdf,text/plain;q=0.9,*/*;q=0.5",
    }
    request = Request(url, headers=headers)
    ssl_context = ssl.create_default_context()
    with urlopen(request, timeout=timeout, context=ssl_context) as response:
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        return response.read(), content_type


def extract_text(raw_bytes: bytes, content_type: str, url: str) -> tuple[str, str]:
    lowered_url = url.lower()
    if "pdf" in content_type or lowered_url.endswith(".pdf"):
        return extract_pdf_text(raw_bytes)
    if "html" in content_type or lowered_url.endswith((".html", ".htm", "/")):
        return extract_html_text(raw_bytes), ""
    if "text" in content_type:
        return normalize_text(raw_bytes.decode("utf-8", errors="replace")), ""
    return "", f"No text extractor for content type {content_type or '<unknown>'}."


def extract_html_text(raw_bytes: bytes) -> str:
    payload = raw_bytes.decode("utf-8", errors="replace")
    parser = _VisibleTextParser()
    parser.feed(payload)
    return normalize_text(html.unescape(" ".join(parser.parts)))


def extract_pdf_text(raw_bytes: bytes) -> tuple[str, str]:
    try:
        from io import BytesIO

        from pypdf import PdfReader
    except ImportError:
        return extract_pdf_text_with_pdftotext(raw_bytes)

    reader = PdfReader(BytesIO(raw_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return normalize_text("\n\n".join(pages)), ""


def extract_pdf_text_with_pdftotext(raw_bytes: bytes) -> tuple[str, str]:
    if shutil.which("pdftotext") is None:
        return "", "Install pypdf or pdftotext to extract PDF text; raw PDF was saved."

    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "source.pdf"
        txt_path = Path(tmpdir) / "source.txt"
        pdf_path.write_bytes(raw_bytes)
        completed = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), str(txt_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            error = completed.stderr.strip() or "pdftotext failed"
            return "", f"pdftotext extraction failed: {error}"
        return normalize_text(txt_path.read_text(encoding="utf-8", errors="replace")), ""


def chunk_text(text: str, *, max_chars: int = 1800, overlap: int = 200) -> list[str]:
    cleaned = normalize_text(text)
    if not cleaned:
        return []
    if max_chars <= overlap:
        raise ValueError("max_chars must be greater than overlap")

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(start + max_chars, len(cleaned))
        if end < len(cleaned):
            sentence_end = max(cleaned.rfind(". ", start, end), cleaned.rfind("\n", start, end))
            if sentence_end > start + max_chars // 2:
                end = sentence_end + 1
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(cleaned):
            break
        start = max(0, end - overlap)
    return chunks


def guess_suffix(url: str, content_type: str) -> str:
    lowered_url = url.lower()
    if "pdf" in content_type or lowered_url.endswith(".pdf"):
        return ".pdf"
    if "html" in content_type or lowered_url.endswith((".html", ".htm", "/")):
        return ".html"
    if "text" in content_type:
        return ".txt"
    return ".bin"


def sanitize_source_id(source_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", source_id).strip("_") or "source"


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _result(
    source: RagSource, fetched_at: str, status: str, *, error: str = ""
) -> CollectionResult:
    return CollectionResult(
        source_id=source.source_id,
        title=source.title,
        url=source.url,
        hostname=source.hostname,
        topic=source.topic,
        source_type=source.source_type,
        priority=source.priority,
        ingest_mode=source.ingest_mode,
        status=status,
        fetched_at=fetched_at,
        error=error,
        license_note=source.license_note,
        notes=source.notes,
    )
