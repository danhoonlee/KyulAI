#!/usr/bin/env python3
"""Verify immutable DD laminate baseline artifacts against their manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


DEFAULT_MANIFEST = Path(
    "research/dd_aicomp2026/baselines/dd_3size_pt_consistent_v1.json"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_records(manifest: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    dataset = manifest["dataset"]
    yield "dataset.manifest", dataset["manifest"]
    yield "dataset.summary", dataset["summary"]
    yield "evaluation_protocol.split_manifest", manifest["evaluation_protocol"][
        "split_manifest"
    ]
    for model in manifest["models"]:
        yield f"model.{model['id']}", model["artifact"]
    for index, evidence in enumerate(manifest.get("evidence", []), start=1):
        yield f"evidence.{index}", evidence


def verify(manifest_path: Path, repo_root: Path, quick: bool) -> int:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []

    for label, record in _artifact_records(manifest):
        relative_path = Path(record["path"])
        path = (repo_root / relative_path).resolve()
        try:
            path.relative_to(repo_root)
        except ValueError:
            failures.append(f"{label}: path escapes repository: {relative_path}")
            continue

        if not path.is_file():
            failures.append(f"{label}: missing: {relative_path}")
            continue

        actual_size = path.stat().st_size
        expected_size = int(record["size_bytes"])
        if actual_size != expected_size:
            failures.append(
                f"{label}: size mismatch for {relative_path}: "
                f"expected {expected_size}, got {actual_size}"
            )
            continue

        if not quick:
            actual_hash = _sha256(path)
            expected_hash = str(record["sha256"])
            if actual_hash != expected_hash:
                failures.append(
                    f"{label}: SHA-256 mismatch for {relative_path}: "
                    f"expected {expected_hash}, got {actual_hash}"
                )
                continue

        mode = "size" if quick else "size+sha256"
        print(f"OK  {label:<48} {mode}  {relative_path}")

    if failures:
        print("\nBaseline verification failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"\nVerified baseline: {manifest['baseline_id']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--quick",
        action="store_true",
        help="check file existence and size without hashing large model files",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    manifest_path = args.manifest
    if not manifest_path.is_absolute():
        manifest_path = repo_root / manifest_path
    return verify(manifest_path.resolve(), repo_root.resolve(), args.quick)


if __name__ == "__main__":
    raise SystemExit(main())
