"""Train first-pass classical models for the new Case2/Case3/Case4 DD dataset."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
from sklearn.base import clone
from sklearn.decomposition import PCA
from sklearn.ensemble import ExtraTreesClassifier, ExtraTreesRegressor, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error
from sklearn.model_selection import GroupKFold
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


CASES = ("Case2", "Case3", "Case4")
CASE_TO_INDEX = {case: idx for idx, case in enumerate(CASES)}
LABEL_NAMES = {1: "Type 1", 2: "Type 2", 3: "Type 3"}
THETA_FEATURE_COLUMNS = [
    "theta1",
    "theta2",
    "case_case2",
    "case_case3",
    "case_case4",
    "abs_theta1",
    "abs_theta2",
    "theta_diff",
    "theta_sum",
    "theta_product",
    "theta_abs_diff",
]
CURVE_GRID_LEN = 128


@dataclass(frozen=True)
class DDRecord:
    case: str
    test_id: str
    theta1: float
    theta2: float
    pt: float
    label: int
    csv_path: Path


def _float(row: dict[str, str], key: str) -> float:
    return float(str(row[key]).strip())


def load_records(data_dir: Path) -> list[DDRecord]:
    records: list[DDRecord] = []
    for case in CASES:
        transition_path = data_dir / case / "transition_load.csv"
        if not transition_path.exists():
            raise FileNotFoundError(transition_path)
        with transition_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                test_id = f"{int(float(row['Test_ID'])):03d}"
                csv_path = data_dir / case / "csv_load" / f"force_disp_Test_{test_id}.csv"
                if not csv_path.exists():
                    raise FileNotFoundError(csv_path)
                records.append(
                    DDRecord(
                        case=case,
                        test_id=test_id,
                        theta1=_float(row, "theta1"),
                        theta2=_float(row, "theta2"),
                        pt=_float(row, "Pt"),
                        label=int(float(row["type"])),
                        csv_path=csv_path,
                    )
                )
    return records


def theta_feature_row(record: DDRecord) -> list[float]:
    one_hot = [1.0 if record.case == case else 0.0 for case in CASES]
    return [
        record.theta1,
        record.theta2,
        *one_hot,
        abs(record.theta1),
        abs(record.theta2),
        record.theta1 - record.theta2,
        record.theta1 + record.theta2,
        record.theta1 * record.theta2,
        abs(record.theta1 - record.theta2),
    ]


def read_curve(path: Path) -> tuple[np.ndarray, np.ndarray]:
    arr = np.loadtxt(path, delimiter=",")
    if arr.ndim != 2 or arr.shape[1] < 2:
        raise ValueError(f"Expected at least two columns: {path}")
    x = arr[:, 0].astype(float)
    y = arr[:, 1].astype(float)
    valid = np.isfinite(x) & np.isfinite(y)
    x = x[valid]
    y = y[valid]
    order = np.argsort(x)
    x = x[order]
    y = y[order]
    unique_x, inverse = np.unique(x, return_inverse=True)
    if len(unique_x) != len(x):
        sums = np.zeros_like(unique_x, dtype=float)
        counts = np.zeros_like(unique_x, dtype=float)
        np.add.at(sums, inverse, y)
        np.add.at(counts, inverse, 1.0)
        y = sums / np.maximum(counts, 1.0)
        x = unique_x
    return x, y


def _linear_slope(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2 or np.ptp(x) <= 1e-12:
        return 0.0
    return float(np.polyfit(x, y, 1)[0])


def curve_feature_row(record: DDRecord) -> list[float]:
    x, y = read_curve(record.csv_path)
    max_disp = max(float(np.max(x)), 1e-9)
    max_force = max(float(np.max(y)), 1e-9)
    x_norm = x / max_disp
    y_norm = y / max_force

    pt_force_norm = record.pt / max_force
    pt_idx = int(np.argmin(np.abs(y - record.pt)))
    split_idx = max(3, min(len(x) - 3, pt_idx))
    pre_x, pre_y = x_norm[:split_idx], y_norm[:split_idx]
    post_x, post_y = x_norm[split_idx:], y_norm[split_idx:]
    pre_slope = _linear_slope(pre_x, pre_y)
    post_slope = _linear_slope(post_x, post_y)

    if len(post_x) >= 5:
        second_derivative = np.diff(post_y, n=2)
        post_curvature_mean = float(np.mean(np.abs(second_derivative)))
        post_curvature_max = float(np.max(np.abs(second_derivative)))
    else:
        post_curvature_mean = 0.0
        post_curvature_max = 0.0

    gradients = np.gradient(y_norm, x_norm, edge_order=1) if len(x_norm) >= 2 else np.asarray([0.0])
    tail_start = int(max(0, np.floor(len(gradients) * 0.8)))
    tail_slope = float(np.mean(gradients[tail_start:]))
    return [
        max_disp,
        max_force,
        pt_force_norm,
        float(x_norm[split_idx]),
        pre_slope,
        post_slope,
        post_slope / max(abs(pre_slope), 1e-9),
        post_curvature_mean,
        post_curvature_max,
        float(np.mean(y_norm)),
        float(np.std(y_norm)),
        float(np.mean(gradients)),
        float(np.std(gradients)),
        tail_slope,
        tail_slope / max(abs(post_slope), 1e-9),
    ]


CURVE_FEATURE_COLUMNS = [
    "max_displacement_observed",
    "max_force_observed",
    "pt_force_norm",
    "pt_displacement_norm_observed",
    "pre_slope_norm",
    "post_slope_norm",
    "post_pre_slope_ratio",
    "post_curvature_mean",
    "post_curvature_max",
    "force_norm_mean",
    "force_norm_std",
    "gradient_mean",
    "gradient_std",
    "tail_slope_norm",
    "tail_post_slope_ratio",
]


def make_theta_matrix(records: list[DDRecord]) -> np.ndarray:
    return np.asarray([theta_feature_row(record) for record in records], dtype=float)


def make_curve_matrix(records: list[DDRecord]) -> np.ndarray:
    theta = make_theta_matrix(records)
    curve = np.asarray([curve_feature_row(record) for record in records], dtype=float)
    return np.hstack([theta, curve])


def make_response_arrays(records: list[DDRecord]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    grid = np.linspace(0.0, 1.0, CURVE_GRID_LEN)
    scalars = []
    curves = []
    for record in records:
        x, y = read_curve(record.csv_path)
        max_disp = max(float(np.max(x)), 1e-9)
        max_force = max(float(np.max(y)), 1e-9)
        x_norm = x / max_disp
        y_interp = np.interp(grid, x_norm, y)
        y_norm = np.clip(y_interp / max_force, 0.0, None)
        scalars.append([record.pt, max_disp, max_force])
        curves.append(y_norm)
    return np.asarray(scalars, dtype=float), np.asarray(curves, dtype=float), grid, make_theta_matrix(records)


def candidate_classifiers(random_state: int) -> dict[str, object]:
    return {
        "extra_trees": ExtraTreesClassifier(
            n_estimators=600,
            random_state=random_state,
            class_weight="balanced",
            min_samples_leaf=1,
            n_jobs=-1,
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=500,
            random_state=random_state + 1,
            class_weight="balanced",
            min_samples_leaf=1,
            n_jobs=-1,
        ),
        "hist_gradient_boosting": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    HistGradientBoostingClassifier(
                        random_state=random_state + 2,
                        learning_rate=0.045,
                        max_iter=450,
                        l2_regularization=0.03,
                    ),
                ),
            ]
        ),
        "mlp_classifier": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "model",
                    MLPClassifier(
                        hidden_layer_sizes=(80, 40),
                        activation="relu",
                        alpha=0.01,
                        learning_rate_init=0.001,
                        max_iter=1200,
                        early_stopping=True,
                        random_state=random_state + 3,
                    ),
                ),
            ]
        ),
    }


def cross_validate_classifier(
    x: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    models: dict[str, object],
    n_splits: int,
) -> tuple[str, dict[str, dict[str, float]], list[dict[str, object]]]:
    group_kfold = GroupKFold(n_splits=n_splits)
    summary: dict[str, dict[str, float]] = {}
    fold_rows: list[dict[str, object]] = []
    for name, estimator in models.items():
        accuracies = []
        f1s = []
        for fold, (train_idx, val_idx) in enumerate(group_kfold.split(x, y, groups), start=1):
            model = clone(estimator)
            model.fit(x[train_idx], y[train_idx])
            pred = model.predict(x[val_idx])
            accuracy = float(accuracy_score(y[val_idx], pred))
            macro_f1 = float(f1_score(y[val_idx], pred, average="macro"))
            accuracies.append(accuracy)
            f1s.append(macro_f1)
            fold_rows.append(
                {
                    "model": name,
                    "fold": fold,
                    "accuracy": accuracy,
                    "macro_f1": macro_f1,
                    "validation_samples": int(len(val_idx)),
                }
            )
        summary[name] = {
            "accuracy_mean": float(np.mean(accuracies)),
            "accuracy_std": float(np.std(accuracies)),
            "macro_f1_mean": float(np.mean(f1s)),
            "macro_f1_std": float(np.std(f1s)),
        }
    best_name = max(summary, key=lambda model_name: summary[model_name]["macro_f1_mean"])
    return best_name, summary, fold_rows


def train_response_surrogate(
    records: list[DDRecord],
    output_dir: Path,
    random_state: int,
    n_splits: int,
) -> dict[str, object]:
    y_scalars, y_curve, grid, x = make_response_arrays(records)
    y_class = np.asarray([record.label for record in records], dtype=int)
    groups = np.asarray([f"{record.theta1}:{record.theta2}" for record in records])
    fold_rows = []
    group_kfold = GroupKFold(n_splits=n_splits)
    for fold, (train_idx, val_idx) in enumerate(group_kfold.split(x, y_class, groups), start=1):
        classifier = ExtraTreesClassifier(
            n_estimators=600,
            random_state=random_state + fold,
            class_weight="balanced",
            n_jobs=-1,
        )
        scalar_model = ExtraTreesRegressor(n_estimators=600, random_state=random_state + 100 + fold, n_jobs=-1)
        pca = PCA(n_components=min(18, y_curve.shape[1], len(train_idx)), random_state=random_state + fold)
        curve_scores = pca.fit_transform(y_curve[train_idx])
        curve_model = ExtraTreesRegressor(n_estimators=600, random_state=random_state + 200 + fold, n_jobs=-1)

        classifier.fit(x[train_idx], y_class[train_idx])
        scalar_model.fit(x[train_idx], y_scalars[train_idx])
        curve_model.fit(x[train_idx], curve_scores)

        pred_class = classifier.predict(x[val_idx])
        pred_scalars = scalar_model.predict(x[val_idx])
        pred_curve = np.clip(pca.inverse_transform(curve_model.predict(x[val_idx])), 0.0, None)
        fold_rows.append(
            {
                "fold": fold,
                "accuracy": float(accuracy_score(y_class[val_idx], pred_class)),
                "macro_f1": float(f1_score(y_class[val_idx], pred_class, average="macro")),
                "pt_mae": float(mean_absolute_error(y_scalars[val_idx, 0], pred_scalars[:, 0])),
                "max_displacement_mae": float(mean_absolute_error(y_scalars[val_idx, 1], pred_scalars[:, 1])),
                "max_force_mae": float(mean_absolute_error(y_scalars[val_idx, 2], pred_scalars[:, 2])),
                "curve_norm_rmse": float(np.sqrt(np.mean((pred_curve - y_curve[val_idx]) ** 2))),
            }
        )

    metrics = {
        "n_samples": len(records),
        "seq_len": CURVE_GRID_LEN,
    }
    for key in ["accuracy", "macro_f1", "pt_mae", "max_displacement_mae", "max_force_mae", "curve_norm_rmse"]:
        values = [row[key] for row in fold_rows]
        metrics[f"cv_{key}_mean"] = float(np.mean(values))
        metrics[f"cv_{key}_std"] = float(np.std(values))

    classifier = ExtraTreesClassifier(
        n_estimators=800,
        random_state=random_state,
        class_weight="balanced",
        n_jobs=-1,
    )
    scalar_model = ExtraTreesRegressor(n_estimators=800, random_state=random_state + 1, n_jobs=-1)
    pca = PCA(n_components=min(18, y_curve.shape[1], len(records)), random_state=random_state)
    curve_scores = pca.fit_transform(y_curve)
    curve_model = ExtraTreesRegressor(n_estimators=800, random_state=random_state + 2, n_jobs=-1)

    classifier.fit(x, y_class)
    scalar_model.fit(x, y_scalars)
    curve_model.fit(x, curve_scores)

    output_dir.mkdir(parents=True, exist_ok=True)
    bundle = {
        "model_name": "cases_2_3_4_response_extra_trees_pca",
        "cases": CASES,
        "label_names": LABEL_NAMES,
        "feature_columns": THETA_FEATURE_COLUMNS,
        "grid": grid,
        "seq_len": CURVE_GRID_LEN,
        "classifier": classifier,
        "scalar_model": scalar_model,
        "scalar_columns": ["pt", "max_displacement", "max_force"],
        "pca": pca,
        "curve_model": curve_model,
        "metrics": metrics,
        "fold_metrics": fold_rows,
    }
    joblib.dump(bundle, output_dir / "response_surrogate.joblib")
    (output_dir / "response_surrogate_metrics.json").write_text(
        json.dumps({"metrics": metrics, "fold_metrics": fold_rows}, indent=2),
        encoding="utf-8",
    )
    return {"metrics": metrics, "fold_metrics": fold_rows}


def fit_and_save_classifier(
    records: list[DDRecord],
    x: np.ndarray,
    feature_columns: list[str],
    output_dir: Path,
    dataset_dir: Path,
    random_state: int,
    n_splits: int,
    model_kind: str,
) -> dict[str, object]:
    y = np.asarray([record.label for record in records], dtype=int)
    groups = np.asarray([f"{record.theta1}:{record.theta2}" for record in records])
    models = candidate_classifiers(random_state)
    best_name, cv_summary, fold_rows = cross_validate_classifier(x, y, groups, models, n_splits)
    best_model = clone(models[best_name])
    best_model.fit(x, y)

    output_dir.mkdir(parents=True, exist_ok=True)
    bundle = {
        "model_name": f"cases_2_3_4_{model_kind}_{best_name}",
        "best_model_name": best_name,
        "cases": CASES,
        "label_names": LABEL_NAMES,
        "feature_columns": feature_columns,
        "model": best_model,
        "metrics": cv_summary,
        "fold_metrics": fold_rows,
        "training_data_dir": str(dataset_dir),
    }
    model_filename = "theta_classifier.joblib" if model_kind == "theta" else "curve_classifier.joblib"
    joblib.dump(bundle, output_dir / model_filename)
    (output_dir / f"{model_kind}_classifier_metrics.json").write_text(
        json.dumps({"best_model": best_name, "metrics": cv_summary, "fold_metrics": fold_rows}, indent=2),
        encoding="utf-8",
    )
    return {"best_model": best_name, "metrics": cv_summary, "fold_metrics": fold_rows}


def write_report(output_root: Path, data_dir: Path, results: dict[str, object]) -> None:
    lines = [
        "# DD Cases 2/3/4 Training Report",
        "",
        f"- Dataset: `{data_dir}`",
        f"- Total samples: {results['total_samples']}",
        f"- Validation: GroupKFold by theta pair, so the same theta pair is not split across train/validation.",
        "",
        "## Type Counts",
    ]
    for key, value in results["type_counts"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Best Models"])
    for section in ("theta", "curve"):
        section_result = results[section]
        best = section_result["best_model"]
        metrics = section_result["metrics"][best]
        lines.append(
            f"- {section}: `{best}` / accuracy {metrics['accuracy_mean']:.3f} +/- {metrics['accuracy_std']:.3f}, "
            f"macro F1 {metrics['macro_f1_mean']:.3f} +/- {metrics['macro_f1_std']:.3f}"
        )
    response = results["response"]["metrics"]
    lines.extend(
        [
            "",
            "## Laminate Forecast Surrogate",
            f"- Type accuracy: {response['cv_accuracy_mean']:.3f} +/- {response['cv_accuracy_std']:.3f}",
            f"- Type macro F1: {response['cv_macro_f1_mean']:.3f} +/- {response['cv_macro_f1_std']:.3f}",
            f"- Pt MAE: {response['cv_pt_mae_mean']:.2f}",
            f"- Max. Displacement MAE: {response['cv_max_displacement_mae_mean']:.5f}",
            f"- Max. Force MAE: {response['cv_max_force_mae_mean']:.2f}",
            f"- Normalized curve RMSE: {response['cv_curve_norm_rmse_mean']:.4f}",
            "",
            "## Note",
            "- This is a separate new-model experiment. Existing DD production model folders are not overwritten.",
        ]
    )
    (output_root / "cases_2_3_4_training_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/datasets/DD_cases_2_3_4_curated_v1")
    parser.add_argument("--output-root", default="models")
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--folds", type=int, default=5)
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_root = Path(args.output_root)
    records = load_records(data_dir)
    type_counts = {name: 0 for name in LABEL_NAMES.values()}
    for record in records:
        type_counts[LABEL_NAMES[record.label]] += 1

    theta_x = make_theta_matrix(records)
    curve_x = make_curve_matrix(records)

    theta_result = fit_and_save_classifier(
        records=records,
        x=theta_x,
        feature_columns=THETA_FEATURE_COLUMNS,
        output_dir=output_root / "dd_laminate_cases_2_3_4_theta_v1",
        dataset_dir=data_dir,
        random_state=args.random_state,
        n_splits=args.folds,
        model_kind="theta",
    )
    curve_result = fit_and_save_classifier(
        records=records,
        x=curve_x,
        feature_columns=THETA_FEATURE_COLUMNS + CURVE_FEATURE_COLUMNS,
        output_dir=output_root / "dd_laminate_cases_2_3_4_csv_v1",
        dataset_dir=data_dir,
        random_state=args.random_state + 10,
        n_splits=args.folds,
        model_kind="curve",
    )
    response_result = train_response_surrogate(
        records=records,
        output_dir=output_root / "dd_laminate_cases_2_3_4_response_surrogate_v1",
        random_state=args.random_state,
        n_splits=args.folds,
    )

    results = {
        "total_samples": len(records),
        "type_counts": type_counts,
        "theta": theta_result,
        "curve": curve_result,
        "response": response_result,
    }
    write_report(output_root / "dd_laminate_cases_2_3_4_response_surrogate_v1", data_dir, results)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
