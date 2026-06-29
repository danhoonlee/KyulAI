#!/usr/bin/env python3
"""Query the local Composite RAG knowledge index."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.rag.indexer import DEFAULT_INDEX_PATH, query_index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="+")
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX_PATH)
    parser.add_argument("--top-k", type=int, default=5)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    query = " ".join(args.query)
    results = query_index(args.index, query, top_k=args.top_k)
    for rank, result in enumerate(results, start=1):
        chunk = result.chunk
        citation = chunk.url or chunk.source_path
        preview = chunk.text[:260].replace("\n", " ")
        print(f"{rank}. score={result.score:.4f} [{chunk.source_kind}] {chunk.title}")
        print(f"   source: {citation}")
        print(f"   text: {preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
