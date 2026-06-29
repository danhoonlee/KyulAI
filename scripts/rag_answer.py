#!/usr/bin/env python3
"""Ask the local Composite RAG assistant."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.rag.answer import answer_query
from src.data.rag.indexer import DEFAULT_INDEX_PATH


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="+")
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX_PATH)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--language", choices=["auto", "ko", "en"], default="auto")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = answer_query(
        " ".join(args.query),
        index_path=args.index,
        top_k=args.top_k,
        use_llm=not args.no_llm,
        language=args.language,
    )
    print(result.answer)
    print()
    print(f"provider={result.provider} model={result.model} retrieval_count={result.retrieval_count}")
    if result.error:
        print(f"warning={result.error}")
    print("citations:")
    for citation in result.citations:
        print(f"  [{citation.index}] {citation.title} | {citation.source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
