"""Create a portable Windows serving bundle for KyulAI.

The Git repository intentionally ignores large dataset folders, so a Git clone
alone may not be enough for a Windows server handoff. This script zips the
runtime code, selected model artifacts, selected datasets, docs, and Windows
helper scripts needed to serve DD Laminate and Simple Injection.
"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

DEFAULT_INCLUDE_DIRS = [
    "src/backend",
    "src/frontend/dd-laminate",
    "src/frontend/imperialax",
    "src/frontend/simple-injection",
    "src/ml/dd_laminate",
    "src/ml/simple_injection",
    "models/dd_laminate_cases_2_3_4_csv_v1",
    "models/dd_laminate_cases_2_3_4_deep_sequence_v1",
    "models/dd_laminate_cases_2_3_4_response_goint_v1",
    "models/dd_laminate_cases_2_3_4_response_surrogate_v1",
    "models/dd_laminate_cases_2_3_4_theta_goint_v1",
    "models/dd_laminate_cases_2_3_4_theta_v1",
    "models/dd_laminate_csv_meta_v1",
    "models/dd_laminate_deep_sequence_grouped_v1",
    "models/dd_laminate_response_goint_v1",
    "models/dd_laminate_response_goint_physics_nn_abd_v1",
    "models/dd_laminate_response_goint_physics_xai_v2",
    "models/dd_laminate_response_goint_physics_xai_v1",
    "models/dd_laminate_response_distilled_v1",
    "models/dd_laminate_response_distilled_grid_v1",
    "models/dd_laminate_response_distilled_grid_conf_v1",
    "models/dd_laminate_response_geometry_tree_v1",
    "models/dd_laminate_response_geometry_goint_v1",
    "models/dd_laminate_response_hybrid_student_deploy_quick_v1",
    "models/dd_laminate_response_physics_abd_v1",
    "models/dd_laminate_response_physics_xai_v1",
    "models/dd_laminate_response_surrogate_v1",
    "models/dd_laminate_theta_goint_grouped_v1",
    "models/dd_laminate_theta_v1",
    "models/dd_laminate_u3_forecast_v2",
    "models/dd_laminate_u3_forecast_physics_abd_v1",
    "models/dd_laminate_u3_forecast_physics_v2",
    "models/dd_laminate_u3_pt_goint_v2",
    "models/dd_laminate_u3_pt_ml_v2",
    "reports/dd_response_physics_xai_v2",
    "reports/dd_response_physics_xai_v1",
    "reports/dd_response_xai_goint_physics_nn_abd_v1",
    "reports/dd_response_xai_goint_physics_v2",
    "reports/dd_response_xai_goint_physics_v1",
    "reports/dd_response_xai_distilled_v1",
    "reports/dd_response_xai_distilled_grid_v1",
    "reports/dd_response_xai_distilled_grid_conf_v1",
    "reports/dd_response_xai_geometry_tree_v1",
    "reports/dd_response_xai_geometry_goint_v1",
    "reports/dd_response_xai_hybrid_student_deploy_quick_v1",
    "reports/dd_response_xai_physics_abd_v1",
    "reports/dd_response_xai_physics_v1",
    "reports/dd_u3_forecast_physics_abd_v1",
    "reports/dd_u3_forecast_physics_v3",
    "reports/dd_u3_xai_goint_physics_abd_v1",
    "reports/dd_u3_xai_goint_physics_v2",
    "reports/dd_u3_xai_goint_v2",
    "reports/dd_u3_xai_physics_abd_v1",
    "reports/dd_u3_xai_physics_v2",
    "reports/dd_u3_xai_v1",
    "models/simple_injection_filling_pressure_deeponet_v1",
    "models/simple_injection_filling_pressure_goint_v1",
    "models/simple_injection_filling_pressure_v1",
    "models/simple_injection_sprue_deeponet_v1",
    "models/simple_injection_sprue_goint_v1",
    "models/simple_injection_sprue_pressure_v1",
    "data/datasets/DD_cases_2_3_4_curated_v1",
    "data/datasets/DD_cases_2_3_4_geometry_v1",
    "data/datasets/DD_curated_csv_v2",
    "data/datasets/DD_u3_pt_v2",
    "data/datasets/DD_new",
    "data/datasets/Double-Double",
    "data/datasets/Simple_Injection",
    "docs",
    "infrastructure/cloudflare",
    "scripts/windows",
]

DEFAULT_INCLUDE_FILES = [
    "requirements-serving.txt",
    "requirements-api.txt",
    "requirements-ml.txt",
    "pyproject.toml",
    ".env.windows.example",
    "CLAUDE.md",
    "scripts/dd_response_distillation_train.py",
    "scripts/dd_response_physics_xai_train.py",
]

SKIP_NAMES = {
    ".DS_Store",
    "Thumbs.db",
}


def should_include(path: Path) -> bool:
    return path.name not in SKIP_NAMES and "__pycache__" not in path.parts


def add_path(zf: zipfile.ZipFile, root: Path, path: Path) -> None:
    if path.is_file() and should_include(path):
        zf.write(path, path.relative_to(root))
        return
    if path.is_dir():
        for child in sorted(path.rglob("*")):
            if child.is_file() and should_include(child):
                zf.write(child, child.relative_to(root))


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Windows serving bundle zip")
    parser.add_argument("--output", default="KyulAI_windows_server_bundle.zip")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    output = Path(args.output).expanduser()
    if not output.is_absolute():
        output = root / output

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for rel in DEFAULT_INCLUDE_FILES:
            path = root / rel
            if path.exists():
                add_path(zf, root, path)
        for rel in DEFAULT_INCLUDE_DIRS:
            path = root / rel
            if path.exists():
                add_path(zf, root, path)

    print(f"Created {output}")


if __name__ == "__main__":
    main()
