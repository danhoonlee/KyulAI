"""Convert Simple Injection STEP geometry files to browser-ready GLB assets.

This script is intentionally optional: the web app can still render the DOE
parametric preview without CadQuery. When CadQuery is installed, this creates a
GLB file per geometry plus a small manifest that can be consumed by the UI later.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STEP_DIR = PROJECT_ROOT / "data/datasets/Simple_Injection/step"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "src/frontend/simple-injection/assets/step-glb"
GEOMETRY_RE = re.compile(r"^(G\d{2})\.(?:stp|step)$", re.IGNORECASE)


@dataclass
class ConversionResult:
    geometry_id: str
    source: str
    output: str | None
    status: str
    message: str = ""
    source_bytes: int | None = None
    output_bytes: int | None = None


def find_step_files(step_dir: Path) -> list[Path]:
    """Find Gxx STEP files even if the user put them in a nested folder."""
    files = []
    for path in step_dir.rglob("*"):
        if path.is_file() and GEOMETRY_RE.match(path.name):
            files.append(path)
    return sorted(files, key=lambda item: item.name.upper())


def import_cadquery():
    os.environ.setdefault("XDG_CACHE_HOME", str(Path(tempfile.gettempdir()) / "kyulai-cadquery-cache"))
    try:
        import cadquery as cq  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "CadQuery is not installed. Install it with:\n"
            "  /Users/danlee/KyulAI_codex/.venv/bin/python -m pip install 'cadquery>=2.5,<3'\n"
            "Then rerun this script."
        ) from exc
    return cq


def convert_one(cq, step_path: Path, output_dir: Path, force: bool) -> ConversionResult:
    match = GEOMETRY_RE.match(step_path.name)
    if not match:
        return ConversionResult(
            geometry_id=step_path.stem,
            source=str(step_path.relative_to(PROJECT_ROOT)),
            output=None,
            status="skipped",
            message="filename does not match Gxx STEP pattern",
        )
    geometry_id = match.group(1).upper()
    output_path = output_dir / f"{geometry_id}.glb"
    source_rel = str(step_path.relative_to(PROJECT_ROOT))
    output_rel = str(output_path.relative_to(PROJECT_ROOT))

    if output_path.exists() and not force and output_path.stat().st_mtime >= step_path.stat().st_mtime:
        return ConversionResult(
            geometry_id=geometry_id,
            source=source_rel,
            output=output_rel,
            status="up_to_date",
            source_bytes=step_path.stat().st_size,
            output_bytes=output_path.stat().st_size,
        )

    try:
        imported = cq.importers.importStep(str(step_path))
        assembly = cq.Assembly(name=geometry_id)
        assembly.add(
            imported,
            name=f"{geometry_id}_body",
            color=cq.Color(0.45, 0.72, 0.86, 1.0),
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        assembly.export(str(output_path))
    except Exception as exc:  # pragma: no cover - depends on local OpenCascade build
        return ConversionResult(
            geometry_id=geometry_id,
            source=source_rel,
            output=output_rel,
            status="failed",
            message=str(exc),
            source_bytes=step_path.stat().st_size,
        )

    return ConversionResult(
        geometry_id=geometry_id,
        source=source_rel,
        output=output_rel,
        status="converted",
        source_bytes=step_path.stat().st_size,
        output_bytes=output_path.stat().st_size,
    )


def write_manifest(output_dir: Path, results: Iterable[ConversionResult]) -> Path:
    manifest_path = output_dir / "manifest.json"
    rows = list(results)
    manifest = {
        "asset_type": "simple_injection_step_glb",
        "generator": "scripts/simple_injection/convert_step_to_glb.py",
        "count": sum(1 for row in rows if row.output and row.status in {"converted", "up_to_date"}),
        "geometries": [asdict(row) for row in rows],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert Simple Injection Gxx STEP files to GLB assets.")
    parser.add_argument("--step-dir", type=Path, default=DEFAULT_STEP_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--only", nargs="*", default=None, help="Optional geometry ids such as G01 G02.")
    parser.add_argument("--force", action="store_true", help="Regenerate GLB files even when they are newer than STEP.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    step_dir = args.step_dir.resolve()
    output_dir = args.output_dir.resolve()
    if not step_dir.exists():
        raise SystemExit(f"STEP directory does not exist: {step_dir}")

    only = {item.upper() for item in args.only} if args.only else None
    step_files = find_step_files(step_dir)
    if only:
        step_files = [path for path in step_files if path.stem.upper() in only]
    if not step_files:
        raise SystemExit(f"No Gxx STEP files found under: {step_dir}")

    cq = import_cadquery()
    results = [convert_one(cq, path, output_dir, force=args.force) for path in step_files]
    manifest_path = write_manifest(output_dir, results)
    for row in results:
        print(f"{row.geometry_id}: {row.status} -> {row.output or '-'}")
        if row.message:
            print(f"  {row.message}")
    print(f"manifest: {manifest_path.relative_to(PROJECT_ROOT)}")
    failures = [row for row in results if row.status == "failed"]
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
