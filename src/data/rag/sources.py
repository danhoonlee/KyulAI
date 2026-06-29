"""Source metadata and allowlist rules for online RAG ingestion."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import urlparse


DEFAULT_ALLOWED_DOMAINS: tuple[str, ...] = (
    "nasa.gov",
    "faa.gov",
    "cmh17.org",
    "stanford.edu",
    "dlr.de",
    "qub.ac.uk",
    "westernsydney.edu.au",
    "doi.org",
    "arc.aiaa.org",
)


@dataclass(frozen=True)
class RagSource:
    """One external knowledge source candidate for the composite RAG corpus."""

    source_id: str
    title: str
    url: str
    topic: str
    source_type: str
    priority: int
    tags: tuple[str, ...] = field(default_factory=tuple)
    ingest_mode: str = "download"
    license_note: str = ""
    notes: str = ""

    @property
    def hostname(self) -> str:
        host = urlparse(self.url).hostname or ""
        return host.removeprefix("www.").lower()

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> RagSource:
        tags = data.get("tags", ())
        if isinstance(tags, list):
            tags_value = tuple(str(tag) for tag in tags)
        elif isinstance(tags, tuple):
            tags_value = tuple(str(tag) for tag in tags)
        else:
            tags_value = ()

        source = cls(
            source_id=str(data["source_id"]),
            title=str(data["title"]),
            url=str(data["url"]),
            topic=str(data.get("topic", "composites")),
            source_type=str(data.get("source_type", "web")),
            priority=int(data.get("priority", 3)),
            tags=tags_value,
            ingest_mode=str(data.get("ingest_mode", "download")),
            license_note=str(data.get("license_note", "")),
            notes=str(data.get("notes", "")),
        )
        source.validate()
        return source

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["tags"] = list(self.tags)
        data["hostname"] = self.hostname
        return data

    def validate(self) -> None:
        if not self.source_id:
            raise ValueError("source_id is required")
        if not self.title:
            raise ValueError(f"{self.source_id}: title is required")
        parsed = urlparse(self.url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"{self.source_id}: url must be http(s): {self.url}")
        if self.priority < 1:
            raise ValueError(f"{self.source_id}: priority must be >= 1")
        if self.ingest_mode not in {"download", "metadata_only"}:
            raise ValueError(f"{self.source_id}: unsupported ingest_mode {self.ingest_mode}")


def normalize_domain(domain: str) -> str:
    return domain.strip().lower().removeprefix("www.")


def is_allowed_domain(hostname: str, allowed_domains: tuple[str, ...]) -> bool:
    host = normalize_domain(hostname)
    for domain in allowed_domains:
        allowed = normalize_domain(domain)
        if host == allowed or host.endswith(f".{allowed}"):
            return True
    return False


def load_sources(path: str | Path) -> list[RagSource]:
    source_path = Path(path)
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("sources", [])
    if not isinstance(payload, list):
        raise ValueError(f"Expected a list of RAG sources in {source_path}")
    return [RagSource.from_dict(item) for item in payload]


def dump_source_catalog(path: str | Path, sources: list[RagSource]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"sources": [source.to_dict() for source in sources]}
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
