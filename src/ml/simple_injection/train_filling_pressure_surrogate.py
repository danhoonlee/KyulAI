"""Train Simple Injection filling pressure distribution surrogates."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import cast

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "8")

import joblib
import numpy as np
from sklearn.base import clone
from sklearn.ensemble import (
    ExtraTreesRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import GroupKFold, KFold
from sklearn.multioutput import MultiOutputRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .data import DEFAULT_DATA_DIR, load_filling_pressure_training_arrays

MetricRow = dict[str, float | int]
CVSummary = dict[str, object]


def candidate_models(random_state: int) -> dict[str, object]:
    return {
        "extra_trees": ExtraTreesRegressor(
            n_estimators=700,
            min_samples_leaf=1,
            random_state=random_state,
        ),
        "random_forest": RandomForestRegressor(
            n_estimators=700,
            min_samples_leaf=1,
            random_state=random_state,
        ),
        "hist_gradient_boosting": MultiOutputRegressor(
            HistGradientBoostingRegressor(
                learning_rate=0.05,
                max_iter=300,
                l2_regularization=0.05,
                random_state=random_state,
            )
        ),
        "ridge": Pipeline(
            [
                ("scaler", StandardScaler()),
                ("model", RidgeCV(alphas=np.logspace(-4, 4, 25))),
            ]
        ),
    }


def split_iter(cv_mode: str, splits: int, seed: int, x: np.ndarray, groups: np.ndarray):
    if cv_mode == "grouped":
        unique_groups = np.unique(groups)
        n_splits = min(splits, len(unique_groups))
        if n_splits < 2:
            raise ValueError("Grouped CV needs at least two geometry groups.")
        yield from GroupKFold(n_splits=n_splits).split(x, groups=groups)
    elif cv_mode == "sample":
        n_splits = min(splits, len(x))
        if n_splits < 2:
            raise ValueError("Sample CV needs at least two samples.")
        yield from KFold(n_splits=n_splits, shuffle=True, random_state=seed).split(x)
    else:
        raise ValueError(cv_mode)


def _metric_row(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    y_pred = np.clip(y_pred, 0.0, None)
    true_stats = y_true[:, :4]
    pred_stats = y_pred[:, :4]
    true_ratios = y_true[:, 4:]
    pred_ratios = y_pred[:, 4:]
    ratio_sum = np.maximum(np.sum(pred_ratios, axis=1, keepdims=True), 1e-9)
    pred_ratios = pred_ratios / ratio_sum * 100.0
    return {
        "stats_mae_MPa": float(mean_absolute_error(true_stats, pred_stats)),
        "volume_ratio_mae_pct": float(mean_absolute_error(true_ratios, pred_ratios)),
        "volume_ratio_rmse_pct": float(np.sqrt(np.mean((true_ratios - pred_ratios) ** 2))),
    }


def cross_validate(
    models: dict[str, object],
    x: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    splits: int,
    cv_mode: str,
    random_state: int,
) -> tuple[str, dict[str, CVSummary]]:
    results: dict[str, CVSummary] = {}
    for name, base_model in models.items():
        fold_rows: list[MetricRow] = []
        for fold, (train_idx, val_idx) in enumerate(
            split_iter(cv_mode, splits, random_state, x, groups), start=1
        ):
            model = clone(base_model)
            model.fit(x[train_idx], y[train_idx])
            pred = model.predict(x[val_idx])
            row = _metric_row(y[val_idx], pred)
            row["fold"] = fold
            row["n_val"] = len(val_idx)
            fold_rows.append(row)
        summary: CVSummary = {"cv_mode": cv_mode, "fold_scores": fold_rows}
        for key in ["stats_mae_MPa", "volume_ratio_mae_pct", "volume_ratio_rmse_pct"]:
            values = [float(row[key]) for row in fold_rows]
            summary[f"mean_{key}"] = float(np.mean(values))
            summary[f"std_{key}"] = float(np.std(values))
        results[name] = summary
    best = min(
        results,
        key=lambda name: (
            cast(float, results[name]["mean_volume_ratio_rmse_pct"]),
            cast(float, results[name]["mean_volume_ratio_mae_pct"]),
            cast(float, results[name]["mean_stats_mae_MPa"]),
        ),
    )
    return best, results


def write_report(
    out: Path,
    data_dir: str | Path,
    best: str,
    metrics: dict,
    n_samples: int,
    n_geometries: int,
    n_processes: int,
    target_columns: list[str],
    feature_columns: list[str],
) -> None:
    lines = [
        "# Simple Injection Filling Pressure Distribution Report",
        "",
        f"Dataset: `{data_dir}`",
        "",
        "This model predicts Moldex3D filling pressure histogram summaries from geometry DOE and process DOE inputs.",
        "Targets are `min/max/avg/sd` plus 10 volume-ratio bins from Moldex3D's histogram CSV export.",
        "",
        "## Data",
        "",
        f"- Samples with filling pressure CSV: {n_samples}",
        f"- Geometry groups represented: {n_geometries}",
        f"- Process combinations represented: {n_processes}",
        f"- Target columns: {len(target_columns)}",
        f"- Input features used internally: {len(feature_columns)}",
        "",
        "## Classical ML Validation",
        "",
        f"Best model: `{best}`",
        "",
        "| Model | Ratio RMSE (%) | Ratio MAE (%) | Stats MAE (MPa) |",
        "|---|---:|---:|---:|",
    ]
    for name, row in sorted(
        metrics.items(), key=lambda item: item[1]["mean_volume_ratio_rmse_pct"]
    ):
        lines.append(
            f"| {name} | {row['mean_volume_ratio_rmse_pct']:.4f} ± {row['std_volume_ratio_rmse_pct']:.4f} "
            f"| {row['mean_volume_ratio_mae_pct']:.4f} ± {row['std_volume_ratio_mae_pct']:.4f} "
            f"| {row['mean_stats_mae_MPa']:.4f} ± {row['std_stats_mae_MPa']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Caveat",
            "",
            "This model predicts a histogram distribution, not a spatial contour field.",
            "A true contour surrogate needs mesh-point or image/field exports with spatial coordinates.",
        ]
    )
    (out / "filling_pressure_surrogate_report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def train_filling_pressure_surrogate(
    data_dir: str | Path,
    output_dir: str | Path,
    splits: int = 3,
    cv_mode: str = "grouped",
    random_state: int = 42,
    min_samples: int = 20,
) -> dict:
    records, x, y, target_columns, feature_columns, gate_types = (
        load_filling_pressure_training_arrays(data_dir)
    )
    if len(records) < min_samples:
        raise ValueError(
            f"Need at least {min_samples} filling pressure CSV samples to train; found {len(records)}. "
            "Add more Gxx_Pyy_Filling_Pressure.csv exports and rerun."
        )
    groups = np.asarray([record.geometry_id for record in records])
    process_ids = {record.process_id for record in records}
    models = candidate_models(random_state)
    best, cv_results = cross_validate(
        models,
        x,
        y,
        groups,
        splits=splits,
        cv_mode=cv_mode,
        random_state=random_state,
    )
    model = clone(models[best])
    model.fit(x, y)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    bundle = {
        "model_name": "simple_injection_filling_pressure_surrogate",
        "best_model": best,
        "feature_columns": feature_columns,
        "gate_types": gate_types,
        "target_columns": target_columns,
        "model": model,
        "metrics": cv_results[best],
        "all_model_metrics": cv_results,
        "sample_ids": [record.sample_id for record in records],
    }
    model_path = out / "filling_pressure_surrogate.joblib"
    joblib.dump(bundle, model_path)
    (out / "filling_pressure_surrogate_metrics.json").write_text(
        json.dumps(
            {
                "best_model": best,
                "metrics": cv_results[best],
                "all_model_metrics": cv_results,
                "n_samples": len(records),
                "feature_columns": feature_columns,
                "target_columns": target_columns,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    write_report(
        out=out,
        data_dir=data_dir,
        best=best,
        metrics=cv_results,
        n_samples=len(records),
        n_geometries=len(set(groups)),
        n_processes=len(process_ids),
        target_columns=target_columns,
        feature_columns=feature_columns,
    )
    return {"model_path": str(model_path), "best_model": best, "metrics": cv_results[best]}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train Simple Injection filling pressure histogram surrogate"
    )
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--output-dir", default="models/simple_injection_filling_pressure_v1")
    parser.add_argument("--splits", type=int, default=3)
    parser.add_argument("--cv-mode", choices=["grouped", "sample"], default="grouped")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min-samples", type=int, default=20)
    args = parser.parse_args()
    result = train_filling_pressure_surrogate(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        splits=args.splits,
        cv_mode=args.cv_mode,
        random_state=args.seed,
        min_samples=args.min_samples,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
