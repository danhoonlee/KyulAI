"""Train theta/case -> Type, Pt, and estimated force-displacement curve surrogate."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
from sklearn.decomposition import PCA
from sklearn.ensemble import ExtraTreesClassifier, ExtraTreesRegressor
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error
from sklearn.model_selection import GroupKFold

from .curve_features import DDCurveRecord, load_curve_records
from .laminate_physics import PHYSICS_FEATURE_COLUMNS, physics_feature_vector

BASE_FEATURE_COLUMNS = [
    "theta1",
    "theta2",
    "case_id",
    "abs_theta1",
    "abs_theta2",
    "theta_diff",
    "theta_sum",
    "theta_product",
]
FEATURE_COLUMNS = BASE_FEATURE_COLUMNS + PHYSICS_FEATURE_COLUMNS


@dataclass(frozen=True)
class ResponseTarget:
    pt: float
    max_displacement: float
    max_force: float
    force_norm: np.ndarray


def _case_id(case: str) -> int:
    return 0 if case == "Case3" else 1


def make_feature_matrix(records: list[DDCurveRecord]) -> np.ndarray:
    rows = []
    for record in records:
        base = [
            record.theta1,
            record.theta2,
            _case_id(record.case),
            abs(record.theta1),
            abs(record.theta2),
            record.theta1 - record.theta2,
            record.theta1 + record.theta2,
            record.theta1 * record.theta2,
        ]
        physics = physics_feature_vector(record.case, record.theta1, record.theta2).tolist()
        rows.append(base + physics)
    return np.asarray(rows, dtype=float)


def _load_target(record: DDCurveRecord, grid: np.ndarray) -> ResponseTarget:
    arr = np.loadtxt(record.csv_path, delimiter=",")
    if arr.ndim != 2 or arr.shape[1] < 2:
        raise ValueError(f"Expected two-column CSV: {record.csv_path}")
    x = arr[:, 0].astype(float)
    y = arr[:, 1].astype(float)
    order = np.argsort(x)
    x = x[order]
    y = y[order]

    max_disp = max(float(np.max(x)), 1e-9)
    max_force = max(float(np.max(y)), 1e-9)
    x_norm = x / max_disp
    force_interp = np.interp(grid, x_norm, y)
    force_norm = np.clip(force_interp / max_force, 0.0, None)
    return ResponseTarget(
        pt=float(record.pt),
        max_displacement=max_disp,
        max_force=max_force,
        force_norm=force_norm,
    )


def load_training_arrays(
    data_dir: str | Path, seq_len: int
) -> tuple[list[DDCurveRecord], np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    records = load_curve_records(data_dir)
    grid = np.linspace(0.0, 1.0, seq_len)
    targets = [_load_target(record, grid) for record in records]
    x = make_feature_matrix(records)
    y_class = np.asarray([record.label for record in records], dtype=int)
    y_scalars = np.asarray(
        [[target.pt, target.max_displacement, target.max_force] for target in targets],
        dtype=float,
    )
    y_curve = np.asarray([target.force_norm for target in targets], dtype=float)
    return records, x, y_class, y_scalars, y_curve, grid


def _fit_models(
    x_train: np.ndarray,
    y_class_train: np.ndarray,
    y_scalars_train: np.ndarray,
    y_curve_train: np.ndarray,
    n_components: int,
    random_state: int,
):
    classifier = ExtraTreesClassifier(
        n_estimators=700,
        random_state=random_state,
        class_weight="balanced",
        min_samples_leaf=1,
    )
    scalar_model = ExtraTreesRegressor(
        n_estimators=700,
        random_state=random_state + 1,
        min_samples_leaf=1,
    )
    pca = PCA(
        n_components=min(n_components, y_curve_train.shape[0], y_curve_train.shape[1]),
        random_state=random_state,
    )
    curve_scores = pca.fit_transform(y_curve_train)
    curve_model = ExtraTreesRegressor(
        n_estimators=700,
        random_state=random_state + 2,
        min_samples_leaf=1,
    )

    classifier.fit(x_train, y_class_train)
    scalar_model.fit(x_train, y_scalars_train)
    curve_model.fit(x_train, curve_scores)
    return classifier, scalar_model, pca, curve_model


def train_response_surrogate(
    data_dir: str | Path,
    output_dir: str | Path,
    seq_len: int = 128,
    n_components: int = 16,
    random_state: int = 42,
) -> dict:
    records, x, y_class, y_scalars, y_curve, grid = load_training_arrays(data_dir, seq_len)
    groups = np.asarray([f"{record.theta1}:{record.theta2}" for record in records])

    metrics: dict[str, float | int] = {
        "n_samples": len(records),
        "seq_len": seq_len,
        "n_components": n_components,
    }

    fold_rows = []
    group_kfold = GroupKFold(n_splits=5)
    for fold, (train_idx, val_idx) in enumerate(group_kfold.split(x, y_class, groups), start=1):
        classifier, scalar_model, pca, curve_model = _fit_models(
            x[train_idx],
            y_class[train_idx],
            y_scalars[train_idx],
            y_curve[train_idx],
            n_components=n_components,
            random_state=random_state + fold * 10,
        )
        pred_class = classifier.predict(x[val_idx])
        pred_scalars = scalar_model.predict(x[val_idx])
        pred_curve_norm = np.clip(pca.inverse_transform(curve_model.predict(x[val_idx])), 0.0, None)

        actual_force = y_curve[val_idx] * y_scalars[val_idx, 2:3]
        pred_force = pred_curve_norm * np.maximum(pred_scalars[:, 2:3], 1e-9)
        fold_metrics = {
            "fold": fold,
            "accuracy": float(accuracy_score(y_class[val_idx], pred_class)),
            "macro_f1": float(f1_score(y_class[val_idx], pred_class, average="macro")),
            "pt_mae": float(mean_absolute_error(y_scalars[val_idx, 0], pred_scalars[:, 0])),
            "max_disp_mae": float(mean_absolute_error(y_scalars[val_idx, 1], pred_scalars[:, 1])),
            "max_force_mae": float(mean_absolute_error(y_scalars[val_idx, 2], pred_scalars[:, 2])),
            "curve_norm_rmse": float(np.sqrt(np.mean((pred_curve_norm - y_curve[val_idx]) ** 2))),
            "curve_force_rmse": float(np.sqrt(np.mean((pred_force - actual_force) ** 2))),
        }
        fold_rows.append(fold_metrics)

    for key in [
        "accuracy",
        "macro_f1",
        "pt_mae",
        "max_disp_mae",
        "max_force_mae",
        "curve_norm_rmse",
        "curve_force_rmse",
    ]:
        values = [row[key] for row in fold_rows]
        metrics[f"cv_{key}_mean"] = float(np.mean(values))
        metrics[f"cv_{key}_std"] = float(np.std(values))

    classifier, scalar_model, pca, curve_model = _fit_models(
        x,
        y_class,
        y_scalars,
        y_curve,
        n_components=n_components,
        random_state=random_state,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    bundle = {
        "model_name": "response_surrogate_extra_trees_pca",
        "feature_columns": FEATURE_COLUMNS,
        "seq_len": seq_len,
        "grid": grid,
        "classifier": classifier,
        "scalar_model": scalar_model,
        "pca": pca,
        "curve_model": curve_model,
        "scalar_columns": ["pt", "max_displacement", "max_force"],
        "metrics": metrics,
        "fold_metrics": fold_rows,
    }
    model_path = output_path / "response_surrogate.joblib"
    joblib.dump(bundle, model_path)

    (output_path / "response_surrogate_metrics.json").write_text(
        json.dumps({"metrics": metrics, "fold_metrics": fold_rows}, indent=2),
        encoding="utf-8",
    )
    report = [
        "# DD Response Surrogate Report",
        "",
        f"- Samples: {len(records)}",
        f"- Input features: {len(FEATURE_COLUMNS)} including CLT laminate physics features",
        f"- Sequence length: {seq_len}",
        f"- PCA components: {bundle['pca'].n_components_}",
        f"- Grouped CV accuracy: {metrics['cv_accuracy_mean']:.4f} +/- {metrics['cv_accuracy_std']:.4f}",
        f"- Grouped CV macro F1: {metrics['cv_macro_f1_mean']:.4f} +/- {metrics['cv_macro_f1_std']:.4f}",
        f"- Grouped CV Pt MAE: {metrics['cv_pt_mae_mean']:.2f} +/- {metrics['cv_pt_mae_std']:.2f}",
        f"- Grouped CV curve force RMSE: {metrics['cv_curve_force_rmse_mean']:.2f} +/- {metrics['cv_curve_force_rmse_std']:.2f}",
        "",
        "This model is a surrogate estimate from theta1/theta2/case only. It is not a replacement for Abaqus.",
    ]
    (output_path / "response_surrogate_report.md").write_text(
        "\n".join(report) + "\n", encoding="utf-8"
    )
    return {"model_path": str(model_path), "metrics": metrics}


def main() -> None:
    parser = argparse.ArgumentParser(description="Train DD response surrogate")
    parser.add_argument("--data-dir", default="data/datasets/DD_curated_csv_v1")
    parser.add_argument("--output-dir", default="models/dd_laminate_response_surrogate_v1")
    parser.add_argument("--seq-len", type=int, default=128)
    parser.add_argument("--n-components", type=int, default=16)
    args = parser.parse_args()
    result = train_response_surrogate(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        seq_len=args.seq_len,
        n_components=args.n_components,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
