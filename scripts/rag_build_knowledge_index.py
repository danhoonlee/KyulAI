#!/usr/bin/env python3
"""Build the local Composite RAG knowledge index."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.rag.indexer import DEFAULT_INDEX_PATH, build_knowledge_index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_INDEX_PATH)
    parser.add_argument("--online-only", action="store_true")
    parser.add_argument("--internal-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.online_only and args.internal_only:
        raise SystemExit("--online-only and --internal-only cannot be used together")

    payload = build_knowledge_index(
        project_root=PROJECT_ROOT,
        output_path=args.output,
        include_online=not args.internal_only,
        include_internal=not args.online_only,
    )
    print(f"Wrote {args.output}")
    print(f"Chunks: {payload['chunk_count']}")
    print(f"Sources: {payload['source_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
