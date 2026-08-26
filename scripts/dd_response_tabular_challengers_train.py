"""Evaluate Laminate Forecast tabular challengers without touching Curve CSV models."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.base import clone
from sklearn.decomposition import PCA
from sklearn.ensemble import (
    ExtraTreesClassifier,
    ExtraTreesRegressor,
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import ElasticNet, LogisticRegression, Ridge
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error
from sklearn.model_selection import GroupKFold
from sklearn.multioutput import MultiOutputRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dd_response_physics_xai_train import make_response_targets
from src.ml.dd_laminate.response_feature_sets import (
    SUPPORTED_RESPONSE_FEATURE_SETS,
    response_feature_matrix,
)
from src.ml.dd_laminate.train_cases_2_3_4_classical import CURVE_GRID_LEN, load_records
from src.ml.dd_laminate.zero_based_classifier import ZeroBasedClassifier

METRIC_KEYS = (
    "accuracy",
    "macro_f1",
    "pt_mae",
    "max_displacement_mae",
    "max_force_mae",
    "curve_norm_rmse",
    "curve_force_rmse",
)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def _available_module(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def _hgb_regressor(seed: int) -> MultiOutputRegressor:
    return MultiOutputRegressor(
        HistGradientBoostingRegressor(
            random_state=seed,
            learning_rate=0.06,
            max_iter=140,
            l2_regularization=0.04,
            early_stopping=True,
        )
    )


def sklearn_candidates(seed: int) -> dict[str, dict[str, Any]]:
    return {
        "extra_trees": {
            "status": "available",
            "dependency": "sklearn",
            "classifier": ExtraTreesClassifier(
                n_estimators=850,
                random_state=seed,
                class_weight="balanced",
                min_samples_leaf=1,
                n_jobs=-1,
            ),
            "scalar_model": ExtraTreesRegressor(
                n_estimators=850,
                random_state=seed + 1,
                min_samples_leaf=1,
                n_jobs=-1,
            ),
            "curve_model": ExtraTreesRegressor(
                n_estimators=850,
                random_state=seed + 2,
                min_samples_leaf=1,
                n_jobs=-1,
            ),
        },
        "random_forest": {
            "status": "available",
            "dependency": "sklearn",
            "classifier": RandomForestClassifier(
                n_estimators=650,
                random_state=seed + 10,
                class_weight="balanced",
                min_samples_leaf=1,
                n_jobs=-1,
            ),
            "scalar_model": RandomForestRegressor(
                n_estimators=650,
                random_state=seed + 11,
                min_samples_leaf=1,
                n_jobs=-1,
            ),
            "curve_model": RandomForestRegressor(
                n_estimators=650,
                random_state=seed + 12,
                min_samples_leaf=1,
                n_jobs=-1,
            ),
        },
        "hist_gradient_boosting": {
            "status": "available",
            "dependency": "sklearn",
            "classifier": HistGradientBoostingClassifier(
                random_state=seed + 20,
                learning_rate=0.06,
                max_iter=140,
                l2_regularization=0.04,
                early_stopping=True,
            ),
            "scalar_model": _hgb_regressor(seed + 21),
            "curve_model": _hgb_regressor(seed + 22),
        },
        "ridge_linear": {
            "status": "available",
            "dependency": "sklearn",
            "classifier": Pipeline(
                [
                    ("scaler", StandardScaler()),
                    (
                        "model",
                        LogisticRegression(
                            class_weight="balanced",
                            max_iter=1200,
                            random_state=seed + 30,
                        ),
                    ),
                ]
            ),
            "scalar_model": Pipeline(
                [
                    ("scaler", StandardScaler()),
                    ("model", Ridge(alpha=8.0)),
                ]
            ),
            "curve_model": Pipeline(
                [
                    ("scaler", StandardScaler()),
                    ("model", Ridge(alpha=8.0)),
                ]
            ),
        },
        "elastic_net_linear": {
            "status": "available",
            "dependency": "sklearn",
            "classifier": Pipeline(
                [
                    ("scaler", StandardScaler()),
                    (
                        "model",
                        LogisticRegression(
                            class_weight="balanced",
                            max_iter=1200,
                            random_state=seed + 40,
                        ),
                    ),
                ]
            ),
            "scalar_model": MultiOutputRegressor(
                Pipeline(
                    [
                        ("scaler", StandardScaler()),
                        ("model", ElasticNet(alpha=0.01, l1_ratio=0.15, max_iter=6000, random_state=seed + 41)),
                    ]
                )
            ),
            "curve_model": MultiOutputRegressor(
                Pipeline(
                    [
                        ("scaler", StandardScaler()),
                        ("model", ElasticNet(alpha=0.01, l1_ratio=0.15, max_iter=6000, random_state=seed + 42)),
                    ]
                )
            ),
        },
    }


def optional_candidates(seed: int) -> dict[str, dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    if _available_module("xgboost"):
        from xgboost import XGBClassifier, XGBRegressor

        candidates["xgboost"] = {
            "status": "available",
            "dependency": "xgboost",
            "classifier": ZeroBasedClassifier(
                XGBClassifier(
                    n_estimators=450,
                    max_depth=4,
                    learning_rate=0.035,
                    subsample=0.9,
                    colsample_bytree=0.9,
                    objective="multi:softprob",
                    eval_metric="mlogloss",
                    random_state=seed + 100,
                    n_jobs=-1,
                )
            ),
            "scalar_model": MultiOutputRegressor(
                XGBRegressor(
                    n_estimators=450,
                    max_depth=4,
                    learning_rate=0.035,
                    subsample=0.9,
                    colsample_bytree=0.9,
                    objective="reg:squarederror",
                    random_state=seed + 101,
                    n_jobs=-1,
                )
            ),
            "curve_model": MultiOutputRegressor(
                XGBRegressor(
                    n_estimators=350,
                    max_depth=4,
                    learning_rate=0.04,
                    subsample=0.9,
                    colsample_bytree=0.9,
                    objective="reg:squarederror",
                    random_state=seed + 102,
                    n_jobs=-1,
                )
            ),
        }
    else:
        candidates["xgboost"] = {"status": "skipped", "dependency": "xgboost", "reason": "module not installed"}

    if _available_module("lightgbm"):
        from lightgbm import LGBMClassifier, LGBMRegressor

        candidates["lightgbm"] = {
            "status": "available",
            "dependency": "lightgbm",
            "classifier": LGBMClassifier(
                n_estimators=500,
                learning_rate=0.035,
                num_leaves=24,
                class_weight="balanced",
                random_state=seed + 110,
                n_jobs=-1,
                verbose=-1,
            ),
            "scalar_model": MultiOutputRegressor(
                LGBMRegressor(
                    n_estimators=500,
                    learning_rate=0.035,
                    num_leaves=24,
                    random_state=seed + 111,
                    n_jobs=-1,
                    verbose=-1,
                )
            ),
            "curve_model": MultiOutputRegressor(
                LGBMRegressor(
                    n_estimators=400,
                    learning_rate=0.04,
                    num_leaves=24,
                    random_state=seed + 112,
                    n_jobs=-1,
                    verbose=-1,
                )
            ),
        }
    else:
        candidates["lightgbm"] = {"status": "skipped", "dependency": "lightgbm", "reason": "module not installed"}

    if _available_module("catboost"):
        from catboost import CatBoostClassifier, CatBoostRegressor

        candidates["catboost"] = {
            "status": "available",
            "dependency": "catboost",
            "classifier": CatBoostClassifier(
                iterations=500,
                depth=4,
                learning_rate=0.04,
                loss_function="MultiClass",
                random_seed=seed + 120,
                verbose=False,
                allow_writing_files=False,
            ),
            "scalar_model": MultiOutputRegressor(
                CatBoostRegressor(
                    iterations=500,
                    depth=5,
                    learning_rate=0.04,
                    loss_function="RMSE",
                    random_seed=seed + 121,
                    verbose=False,
                    allow_writing_files=False,
                )
            ),
            "curve_model": MultiOutputRegressor(
                CatBoostRegressor(
                    iterations=400,
                    depth=5,
                    learning_rate=0.04,
                    loss_function="RMSE",
                    random_seed=seed + 122,
                    verbose=False,
                    allow_writing_files=False,
                )
            ),
        }
    else:
        candidates["catboost"] = {"status": "skipped", "dependency": "catboost", "reason": "module not installed"}

    if _available_module("tabpfn"):
        from tabpfn import TabPFNClassifier, TabPFNRegressor

        candidates["tabpfn"] = {
            "status": "available",
            "dependency": "tabpfn",
            "classifier": TabPFNClassifier(
                n_estimators=2,
                device="cpu",
                random_state=seed + 130,
                show_progress_bar=False,
            ),
            "scalar_model": MultiOutputRegressor(
                TabPFNRegressor(
                    n_estimators=2,
                    device="cpu",
                    random_state=seed + 131,
                    show_progress_bar=False,
                )
            ),
            "curve_model": MultiOutputRegressor(
                TabPFNRegressor(
                    n_estimators=2,
                    device="cpu",
                    random_state=seed + 132,
                    show_progress_bar=False,
                )
            ),
        }
    else:
        candidates["tabpfn"] = {"status": "skipped", "dependency": "tabpfn", "reason": "module not installed"}
    return candidates


def candidate_catalog(seed: int, include_optional: bool) -> dict[str, dict[str, Any]]:
    catalog = sklearn_candidates(seed)
    if include_optional:
        catalog.update(optional_candidates(seed))
    else:
        for name, dependency in (
            ("xgboost", "xgboost"),
            ("lightgbm", "lightgbm"),
            ("catboost", "catboost"),
            ("tabpfn", "tabpfn"),
        ):
            reason = "optional candidates disabled"
            if not _available_module(dependency):
                reason = "module not installed"
            catalog[name] = {"status": "skipped", "dependency": dependency, "reason": reason}
    return catalog


def _fit_predict_candidate(
    spec: dict[str, Any],
    x_train: np.ndarray,
    x_val: np.ndarray,
    y_class_train: np.ndarray,
    y_scalars_train: np.ndarray,
    y_curve_train: np.ndarray,
    n_components: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    classifier = clone(spec["classifier"])
    scalar_model = clone(spec["scalar_model"])
    curve_model = clone(spec["curve_model"])
    pca = PCA(n_components=min(n_components, y_curve_train.shape[0], y_curve_train.shape[1]), random_state=seed)
    curve_scores = pca.fit_transform(y_curve_train)

    classifier.fit(x_train, y_class_train)
    scalar_model.fit(x_train, y_scalars_train)
    curve_model.fit(x_train, curve_scores)

    pred_class = np.asarray(classifier.predict(x_val), dtype=int)
    pred_scalars = np.asarray(scalar_model.predict(x_val), dtype=float)
    pred_scores = np.asarray(curve_model.predict(x_val), dtype=float)
    pred_curve = np.clip(pca.inverse_transform(pred_scores), 0.0, None)
    return pred_class, pred_scalars, pred_curve


def evaluate_candidate(
    name: str,
    spec: dict[str, Any],
    x: np.ndarray,
    y_class: np.ndarray,
    y_scalars: np.ndarray,
    y_curve: np.ndarray,
    groups: np.ndarray,
    splits: int,
    n_components: int,
    seed: int,
) -> dict[str, Any]:
    fold_rows: list[dict[str, Any]] = []
    splitter = GroupKFold(n_splits=splits)
    total_fit_seconds = 0.0
    total_predict_seconds = 0.0
    total_pred_samples = 0
    for fold, (train_idx, val_idx) in enumerate(splitter.split(x, y_class, groups), start=1):
        start = time.perf_counter()
        pred_class, pred_scalars, pred_curve = _fit_predict_candidate(
            spec,
            x[train_idx],
            x[val_idx],
            y_class[train_idx],
            y_scalars[train_idx],
            y_curve[train_idx],
            n_components,
            seed + fold * 100,
        )
        elapsed = time.perf_counter() - start
        # Fit and validation prediction happen together here; a separate final
        # inference timing pass below gives a cleaner per-sample estimate.
        total_fit_seconds += elapsed

        true_force = y_curve[val_idx] * np.maximum(y_scalars[val_idx, 2:3], 1e-9)
        pred_force = pred_curve * np.maximum(pred_scalars[:, 2:3], 1e-9)
        fold_rows.append(
            {
                "fold": fold,
                "validation_samples": int(len(val_idx)),
                "accuracy": float(accuracy_score(y_class[val_idx], pred_class)),
                "macro_f1": float(f1_score(y_class[val_idx], pred_class, average="macro", zero_division=0)),
                "pt_mae": float(mean_absolute_error(y_scalars[val_idx, 0], pred_scalars[:, 0])),
                "max_displacement_mae": float(mean_absolute_error(y_scalars[val_idx, 1], pred_scalars[:, 1])),
                "max_force_mae": float(mean_absolute_error(y_scalars[val_idx, 2], pred_scalars[:, 2])),
                "curve_norm_rmse": float(np.sqrt(np.mean((pred_curve - y_curve[val_idx]) ** 2))),
                "curve_force_rmse": float(np.sqrt(np.mean((pred_force - true_force) ** 2))),
                "fit_plus_validation_predict_seconds": elapsed,
            }
        )
        print(
            f"  {name} fold {fold}: f1={fold_rows[-1]['macro_f1']:.4f}, "
            f"pt_mae={fold_rows[-1]['pt_mae']:.2f}, curve_rmse={fold_rows[-1]['curve_norm_rmse']:.5f}",
            flush=True,
        )

    summary: dict[str, Any] = {
        "status": "trained",
        "dependency": spec["dependency"],
        "fold_metrics": fold_rows,
        "fit_seconds_total": total_fit_seconds,
    }
    for key in METRIC_KEYS:
        values = [row[key] for row in fold_rows]
        summary[f"cv_{key}_mean"] = float(np.mean(values))
        summary[f"cv_{key}_std"] = float(np.std(values))

    # Final fit for artifact and model-size measurement.
    final_start = time.perf_counter()
    classifier = clone(spec["classifier"])
    scalar_model = clone(spec["scalar_model"])
    curve_model = clone(spec["curve_model"])
    pca = PCA(n_components=min(n_components, y_curve.shape[0], y_curve.shape[1]), random_state=seed)
    curve_scores = pca.fit_transform(y_curve)
    classifier.fit(x, y_class)
    scalar_model.fit(x, y_scalars)
    curve_model.fit(x, curve_scores)
    summary["final_fit_seconds"] = float(time.perf_counter() - final_start)

    predict_start = time.perf_counter()
    _ = classifier.predict(x)
    pred_scalars = np.asarray(scalar_model.predict(x), dtype=float)
    pred_scores = np.asarray(curve_model.predict(x), dtype=float)
    _ = np.clip(pca.inverse_transform(pred_scores), 0.0, None)
    total_predict_seconds += time.perf_counter() - predict_start
    total_pred_samples += len(x)
    summary["inference_seconds_per_sample"] = float(total_predict_seconds / max(total_pred_samples, 1))

    artifact = {
        "model_name": f"dd_response_tabular_challenger_{name}",
        "candidate_name": name,
        "feature_builder": None,
        "feature_columns": None,
        "classifier": classifier,
        "scalar_model": scalar_model,
        "scalar_columns": ["pt", "max_displacement", "max_force"],
        "pca": pca,
        "curve_model": curve_model,
        "metrics": {key: value for key, value in summary.items() if key != "fold_metrics"},
    }
    summary["_artifact"] = artifact
    _ = pred_scalars  # Keep linters quiet when only timing is needed.
    return summary


def load_reference_metrics(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"status": "missing", "path": str(path)}
    data = json.loads(path.read_text(encoding="utf-8"))
    metrics = data.get("metrics", data)
    metrics["status"] = "reference"
    metrics["path"] = str(path)
    return metrics


def _score_for_recommendation(metrics: dict[str, Any]) -> tuple[float, float, float]:
    return (
        float(metrics.get("cv_pt_mae_mean", float("inf"))),
        float(metrics.get("cv_curve_norm_rmse_mean", float("inf"))),
        -float(metrics.get("cv_macro_f1_mean", 0.0)),
    )


def write_reports(
    report_dir: Path,
    output_dir: Path,
    payload: dict[str, Any],
    baseline_tree: dict[str, Any],
    baseline_goint: dict[str, Any],
) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    serializable = _json_safe(payload)
    (report_dir / "model_comparison.json").write_text(json.dumps(serializable, indent=2), encoding="utf-8")

    trained = {
        name: row
        for name, row in payload["candidates"].items()
        if row.get("status") == "trained"
    }
    best_name = min(trained, key=lambda key: _score_for_recommendation(trained[key])) if trained else None
    baseline_pt = float(baseline_tree.get("cv_pt_mae_mean", float("inf")))
    baseline_curve = float(baseline_tree.get("cv_curve_norm_rmse_mean", float("inf")))
    baseline_f1 = float(baseline_tree.get("cv_macro_f1_mean", 0.0))

    recommendation = "No challenger was trained."
    if best_name is not None:
        best = trained[best_name]
        pt_delta = float(best["cv_pt_mae_mean"]) - baseline_pt
        curve_delta = float(best["cv_curve_norm_rmse_mean"]) - baseline_curve
        f1_delta = float(best["cv_macro_f1_mean"]) - baseline_f1
        if pt_delta < -1e-6 and curve_delta <= 0.001 and f1_delta > -0.01:
            recommendation = (
                f"`{best_name}` deserves a closer second pass, but should not be promoted until "
                "the artifact is reviewed against deployment constraints."
            )
        else:
            recommendation = (
                f"`{best_name}` is the best challenger in this run, but it does not clearly beat "
                "`response_surrogate_physics_v2` across Pt, curve, and Type metrics. Do not add a backend key yet."
            )

    lines = [
        "# DD Laminate Response Tabular Challengers v1",
        "",
        f"- Dataset: `{payload['dataset']}`",
        f"- Feature set: `{payload['feature_set']}`",
        f"- Samples: {payload['n_samples']}",
        f"- Validation: GroupKFold by theta pair, {payload['splits']} folds",
        f"- Curve surrogate: PCA on {payload['seq_len']}-point normalized force curves, {payload['n_components']} components",
        f"- Output artifacts: `{output_dir}`",
        "",
        "## Fair Comparison Contract",
        "",
        "All trained challengers keep the same comparison surface as `response_surrogate_physics_v2`:",
        "",
        "- Input features are fixed to `theta_physics_v2`, the compact CLT/ABD physics feature set.",
        "- Scalar targets are fixed to `pt`, `max_displacement`, and `max_force`.",
        "- Curve targets are fixed to normalized force curves on the shared response grid.",
        "- Each challenger fits a PCA curve surrogate with the same component budget and predicts PCA scores.",
        "- The only intended variable is the learner family used for Type, scalar, and curve-score prediction.",
        "",
        "## Reference Models",
        "",
        "| Model | Type Acc | Macro F1 | Pt MAE | Max Force MAE | Curve Norm RMSE | Curve Force RMSE |",
        "|---|---:|---:|---:|---:|---:|---:|",
        (
            f"| response_surrogate_physics_v2 | {baseline_tree.get('cv_accuracy_mean', 0):.4f} | "
            f"{baseline_tree.get('cv_macro_f1_mean', 0):.4f} | {baseline_tree.get('cv_pt_mae_mean', 0):.2f} | "
            f"{baseline_tree.get('cv_max_force_mae_mean', 0):.2f} | {baseline_tree.get('cv_curve_norm_rmse_mean', 0):.5f} | "
            f"{baseline_tree.get('cv_curve_force_rmse_mean', 0):.2f} |"
        ),
        (
            f"| response_goint_physics_nn_v2 | {baseline_goint.get('cv_accuracy_mean', 0):.4f} | "
            f"{baseline_goint.get('cv_macro_f1_mean', 0):.4f} | {baseline_goint.get('cv_pt_mae_mean', 0):.2f} | "
            f"{baseline_goint.get('cv_max_force_mae_mean', 0):.2f} | {baseline_goint.get('cv_curve_norm_rmse_mean', 0):.5f} | "
            f"{baseline_goint.get('cv_curve_force_rmse_mean', 0):.2f} |"
        ),
        "",
        "## Challenger Results",
        "",
        "| Candidate | Status | Type Acc | Macro F1 | Pt MAE | Max Force MAE | Curve Norm RMSE | Curve Force RMSE | Train s | Infer ms/sample | Size MB |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, row in payload["candidates"].items():
        if row.get("status") != "trained":
            reason = str(row.get("reason", "not trained")).splitlines()[0]
            lines.append(f"| {name} | {row.get('status', 'not trained')}: {reason} |  |  |  |  |  |  |  |  |  |")
            continue
        infer_ms = float(row.get("inference_seconds_per_sample", 0.0)) * 1000.0
        lines.append(
            f"| {name} | trained | {row['cv_accuracy_mean']:.4f} | {row['cv_macro_f1_mean']:.4f} | "
            f"{row['cv_pt_mae_mean']:.2f} | {row['cv_max_force_mae_mean']:.2f} | "
            f"{row['cv_curve_norm_rmse_mean']:.5f} | {row['cv_curve_force_rmse_mean']:.2f} | "
            f"{row.get('final_fit_seconds', 0.0):.2f} | {infer_ms:.4f} | {row.get('artifact_size_mb', 0.0):.3f} |"
        )
    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            recommendation,
            "",
            "No backend model key or UI/API default was changed in this pass.",
        ]
    )
    (report_dir / "model_comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    report_dir = Path(args.report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    records = load_records(data_dir)
    x, feature_names = response_feature_matrix(records, args.feature_set)
    y_class = np.asarray([record.label for record in records], dtype=int)
    y_scalars, y_curve, grid = make_response_targets(records, args.seq_len)
    groups = np.asarray([f"{record.theta1}:{record.theta2}" for record in records])

    baseline_tree = load_reference_metrics(Path(args.baseline_tree_metrics))
    baseline_goint = load_reference_metrics(Path(args.baseline_goint_metrics))
    candidates = candidate_catalog(args.seed, args.include_optional)
    results: dict[str, Any] = {}

    for name, spec in candidates.items():
        if spec.get("status") != "available":
            results[name] = spec
            print(f"skip {name}: {spec.get('reason')}", flush=True)
            continue
        print(f"training {name}...", flush=True)
        try:
            row = evaluate_candidate(
                name=name,
                spec=spec,
                x=x,
                y_class=y_class,
                y_scalars=y_scalars,
                y_curve=y_curve,
                groups=groups,
                splits=args.splits,
                n_components=args.n_components,
                seed=args.seed,
            )
            artifact = row.pop("_artifact")
            artifact["feature_builder"] = args.feature_set
            artifact["feature_columns"] = feature_names
            artifact["grid"] = grid
            artifact["seq_len"] = int(args.seq_len)
            artifact_path = output_dir / f"{name}.joblib"
            joblib.dump(artifact, artifact_path)
            row["artifact_path"] = str(artifact_path)
            row["artifact_size_mb"] = float(artifact_path.stat().st_size / (1024 * 1024))
            results[name] = row
            print(
                f"done {name}: f1={row['cv_macro_f1_mean']:.4f}, pt_mae={row['cv_pt_mae_mean']:.2f}, "
                f"curve_rmse={row['cv_curve_norm_rmse_mean']:.5f}",
                flush=True,
            )
        except Exception as exc:  # pragma: no cover - keeps optional experiments non-fatal.
            results[name] = {
                "status": "failed",
                "dependency": spec.get("dependency"),
                "reason": f"{type(exc).__name__}: {exc}",
            }
            print(f"failed {name}: {exc}", flush=True)

    payload = {
        "dataset": str(data_dir),
        "feature_set": args.feature_set,
        "n_samples": int(len(records)),
        "seq_len": int(args.seq_len),
        "n_components": int(args.n_components),
        "splits": int(args.splits),
        "feature_columns": feature_names,
        "reference_models": {
            "response_surrogate_physics_v2": baseline_tree,
            "response_goint_physics_nn_v2": baseline_goint,
        },
        "candidates": results,
    }
    write_reports(report_dir, output_dir, payload, baseline_tree, baseline_goint)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Train DD response tabular challengers without Curve CSV changes.")
    parser.add_argument("--data-dir", default="data/datasets/DD_cases_2_3_4_curated_v1")
    parser.add_argument("--output-dir", default="models/dd_laminate_response_tabular_challengers_v1")
    parser.add_argument("--report-dir", default="reports/dd_response_tabular_challengers_v1")
    parser.add_argument("--baseline-tree-metrics", default="models/dd_laminate_response_physics_xai_v2/response_surrogate_metrics.json")
    parser.add_argument("--baseline-goint-metrics", default="models/dd_laminate_response_goint_physics_nn_v2/response_goint_metrics.json")
    parser.add_argument(
        "--feature-set",
        choices=SUPPORTED_RESPONSE_FEATURE_SETS,
        default="theta_physics_v2",
    )
    parser.add_argument("--seq-len", type=int, default=CURVE_GRID_LEN)
    parser.add_argument("--n-components", type=int, default=18)
    parser.add_argument("--splits", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--include-optional", action="store_true")
    args = parser.parse_args()
    payload = run(args)
    print(json.dumps(_json_safe(payload), indent=2))


if __name__ == "__main__":
    main()
