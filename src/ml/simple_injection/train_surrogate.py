"""Train classical ML sprue pressure curve surrogates for Simple Injection."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "8")

import joblib
import numpy as np
from sklearn.base import clone
from sklearn.decomposition import PCA
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import GroupKFold, KFold
from sklearn.multioutput import MultiOutputRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .data import DEFAULT_DATA_DIR, load_training_arrays
from .metrics import normalize_curve_shape, sprue_curve_shape_metrics


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
        "neural_net_mlp_lbfgs": Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "model",
                    MLPRegressor(
                        hidden_layer_sizes=(64, 32),
                        activation="relu",
                        solver="lbfgs",
                        alpha=1e-2,
                        max_iter=2500,
                        random_state=random_state,
                    ),
                ),
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


def _fit_bundle(
    base_model,
    x_train: np.ndarray,
    y_scalars_train: np.ndarray,
    y_curve_train: np.ndarray,
    n_components: int,
    random_state: int,
) -> tuple[object, PCA, object]:
    scalar_model = clone(base_model)
    curve_model = clone(base_model)
    pca = PCA(
        n_components=min(n_components, y_curve_train.shape[0], y_curve_train.shape[1]),
        random_state=random_state,
    )
    curve_scores = pca.fit_transform(y_curve_train)
    scalar_model.fit(x_train, np.log1p(y_scalars_train))
    curve_model.fit(x_train, curve_scores)
    return scalar_model, pca, curve_model


def _predict_bundle(
    scalar_model,
    pca: PCA,
    curve_model,
    x: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    pred_scalars = np.expm1(scalar_model.predict(x))
    pred_scalars = np.maximum(pred_scalars, 1e-9)
    pred_curve = np.clip(pca.inverse_transform(curve_model.predict(x)), 0.0, None)
    return pred_scalars, pred_curve


def _metric_row(
    y_scalars_true: np.ndarray,
    y_curve_true: np.ndarray,
    y_scalars_pred: np.ndarray,
    y_curve_pred: np.ndarray,
    grid: np.ndarray,
) -> dict[str, float]:
    y_curve_pred_shape = normalize_curve_shape(y_curve_pred)
    true_pressure = y_curve_true * np.maximum(y_scalars_true[:, 1:2], 1e-9)
    pred_pressure = y_curve_pred_shape * np.maximum(y_scalars_pred[:, 1:2], 1e-9)
    row = {
        "max_time_mae": float(mean_absolute_error(y_scalars_true[:, 0], y_scalars_pred[:, 0])),
        "max_pressure_mae": float(mean_absolute_error(y_scalars_true[:, 1], y_scalars_pred[:, 1])),
        "curve_norm_rmse": float(np.sqrt(np.mean((y_curve_pred_shape - y_curve_true) ** 2))),
        "curve_pressure_rmse": float(np.sqrt(np.mean((pred_pressure - true_pressure) ** 2))),
    }
    row.update(sprue_curve_shape_metrics(y_scalars_true, y_curve_true, y_scalars_pred, y_curve_pred, grid))
    return row


def cross_validate(
    models: dict[str, object],
    x: np.ndarray,
    y_scalars: np.ndarray,
    y_curve: np.ndarray,
    grid: np.ndarray,
    groups: np.ndarray,
    splits: int,
    cv_mode: str,
    n_components: int,
    random_state: int,
) -> tuple[str, dict[str, dict]]:
    results = {}
    for name, base_model in models.items():
        fold_rows = []
        for fold, (train_idx, val_idx) in enumerate(split_iter(cv_mode, splits, random_state, x, groups), start=1):
            scalar_model, pca, curve_model = _fit_bundle(
                base_model,
                x[train_idx],
                y_scalars[train_idx],
                y_curve[train_idx],
                n_components=n_components,
                random_state=random_state + fold,
            )
            pred_scalars, pred_curve = _predict_bundle(scalar_model, pca, curve_model, x[val_idx])
            row = _metric_row(y_scalars[val_idx], y_curve[val_idx], pred_scalars, pred_curve, grid)
            row["fold"] = fold
            row["n_val"] = int(len(val_idx))
            fold_rows.append(row)
        summary = {"cv_mode": cv_mode, "fold_scores": fold_rows}
        for key in [
            "max_time_mae",
            "max_pressure_mae",
            "curve_norm_rmse",
            "curve_pressure_rmse",
            "shape_corr_mean",
            "shape_corr_min",
            "norm_auc_mae",
            "pressure_time_auc_mae",
            "peak_position_mae_norm_time",
            "rise_slope_mae_norm",
        ]:
            values = [row[key] for row in fold_rows]
            summary[f"mean_{key}"] = float(np.mean(values))
            summary[f"std_{key}"] = float(np.std(values))
        results[name] = summary
    best = min(
        results,
        key=lambda name: (
            results[name]["mean_curve_pressure_rmse"],
            results[name]["mean_max_pressure_mae"],
            results[name]["mean_curve_norm_rmse"],
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
    seq_len: int,
    feature_columns: list[str],
) -> None:
    lines = [
        "# Simple Injection Sprue Pressure Surrogate Report",
        "",
        f"Dataset: `{data_dir}`",
        "",
        "This model predicts a Moldex3D sprue pressure time curve from geometry DOE and process DOE inputs.",
        "The saved model predicts `max_time`, `max_pressure`, and a normalized pressure curve sampled on a fixed 0-1 time grid.",
        "",
        "## Data",
        "",
        f"- Samples with results: {n_samples}",
        f"- Geometry groups represented: {n_geometries}",
        f"- Process combinations represented: {n_processes}",
        f"- Curve sequence length: {seq_len}",
        f"- Input features used internally: {len(feature_columns)}",
        "",
        "## Classical ML Validation",
        "",
        f"Best model: `{best}`",
        "",
        "| Model | Pressure RMSE (MPa) | Max pressure MAE (MPa) | Max time MAE (s) | Norm curve RMSE |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, row in sorted(metrics.items(), key=lambda item: item[1]["mean_curve_pressure_rmse"]):
        lines.append(
            f"| {name} | {row['mean_curve_pressure_rmse']:.4f} ± {row['std_curve_pressure_rmse']:.4f} "
            f"| {row['mean_max_pressure_mae']:.4f} ± {row['std_max_pressure_mae']:.4f} "
            f"| {row['mean_max_time_mae']:.4f} ± {row['std_max_time_mae']:.4f} "
            f"| {row['mean_curve_norm_rmse']:.5f} ± {row['std_curve_norm_rmse']:.5f} |"
        )
    lines.extend(
        [
            "",
            "## Shape-Oriented Metrics",
            "",
            "| Model | Shape corr ↑ | Norm AUC MAE ↓ | Pressure-time AUC MAE (MPa*s) ↓ | Peak position MAE ↓ | Rise slope MAE ↓ |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for name, row in sorted(metrics.items(), key=lambda item: item[1]["mean_curve_pressure_rmse"]):
        lines.append(
            f"| {name} | {row['mean_shape_corr_mean']:.4f} ± {row['std_shape_corr_mean']:.4f} "
            f"| {row['mean_norm_auc_mae']:.5f} ± {row['std_norm_auc_mae']:.5f} "
            f"| {row['mean_pressure_time_auc_mae']:.4f} ± {row['std_pressure_time_auc_mae']:.4f} "
            f"| {row['mean_peak_position_mae_norm_time']:.5f} ± {row['std_peak_position_mae_norm_time']:.5f} "
            f"| {row['mean_rise_slope_mae_norm']:.4f} ± {row['std_rise_slope_mae_norm']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Caveat",
            "",
            f"Only {n_samples} of the planned 300 CAE runs are available, so geometry-group validation is intentionally harsh.",
            "Treat these metrics as a baseline and retrain after each new geometry batch is added.",
        ]
    )
    (out / "sprue_pressure_surrogate_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def train_surrogate(
    data_dir: str | Path,
    output_dir: str | Path,
    seq_len: int = 128,
    n_components: int = 12,
    splits: int = 3,
    cv_mode: str = "grouped",
    random_state: int = 42,
) -> dict:
    records, x, y_scalars, y_curve, grid, feature_columns, gate_types = load_training_arrays(data_dir, seq_len)
    groups = np.asarray([record.geometry_id for record in records])
    process_ids = {record.process_id for record in records}
    models = candidate_models(random_state)
    best, cv_results = cross_validate(
        models,
        x,
        y_scalars,
        y_curve,
        grid,
        groups,
        splits=splits,
        cv_mode=cv_mode,
        n_components=n_components,
        random_state=random_state,
    )
    scalar_model, pca, curve_model = _fit_bundle(
        models[best],
        x,
        y_scalars,
        y_curve,
        n_components=n_components,
        random_state=random_state,
    )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    bundle = {
        "model_name": "simple_injection_sprue_pressure_surrogate",
        "best_model": best,
        "feature_columns": feature_columns,
        "gate_types": gate_types,
        "seq_len": seq_len,
        "grid": grid,
        "scalar_columns": ["max_time_s", "max_pressure_MPa"],
        "scalar_model": scalar_model,
        "pca": pca,
        "curve_model": curve_model,
        "metrics": cv_results[best],
        "all_model_metrics": cv_results,
        "sample_ids": [record.sample_id for record in records],
    }
    model_path = out / "sprue_pressure_surrogate.joblib"
    joblib.dump(bundle, model_path)
    (out / "sprue_pressure_surrogate_metrics.json").write_text(
        json.dumps(
            {
                "best_model": best,
                "metrics": cv_results[best],
                "all_model_metrics": cv_results,
                "n_samples": len(records),
                "feature_columns": feature_columns,
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
        seq_len=seq_len,
        feature_columns=feature_columns,
    )
    return {"model_path": str(model_path), "best_model": best, "metrics": cv_results[best]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Simple Injection sprue pressure classical surrogate")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--output-dir", default="models/simple_injection_sprue_pressure_v1")
    parser.add_argument("--seq-len", type=int, default=128)
    parser.add_argument("--n-components", type=int, default=12)
    parser.add_argument("--splits", type=int, default=3)
    parser.add_argument("--cv-mode", choices=["grouped", "sample"], default="grouped")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    result = train_surrogate(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        seq_len=args.seq_len,
        n_components=args.n_components,
        splits=args.splits,
        cv_mode=args.cv_mode,
        random_state=args.seed,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
