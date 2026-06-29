#!/usr/bin/env python3
"""Collect allowlisted online composite references for the RAG corpus."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.rag.collector import collect_sources, write_collection_manifest
from src.data.rag.sources import DEFAULT_ALLOWED_DOMAINS, load_sources


DEFAULT_SOURCE_FILE = PROJECT_ROOT / "data" / "rag" / "online_sources.seed.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "rag" / "online_corpus"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCE_FILE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Validate and write manifest entries without downloading source content.",
    )
    parser.add_argument(
        "--allow-domain",
        action="append",
        default=[],
        help="Additional allowed domain. Repeat for multiple domains.",
    )
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Exit non-zero when any source is blocked or fails to fetch.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sources = load_sources(args.sources)
    allowed_domains = (*DEFAULT_ALLOWED_DOMAINS, *tuple(args.allow_domain))
    results = collect_sources(
        sources,
        args.output_dir,
        allowed_domains=allowed_domains,
        download=not args.metadata_only,
        timeout=args.timeout,
        limit=args.limit,
    )
    manifest_path = args.output_dir / "collection_manifest.json"
    write_collection_manifest(manifest_path, results)

    status_counts: dict[str, int] = {}
    for result in results:
        status_counts[result.status] = status_counts.get(result.status, 0) + 1

    print(f"Wrote {manifest_path}")
    print("Status counts:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")

    if args.fail_on_error and any(result.status in {"blocked_domain", "fetch_error"} for result in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
