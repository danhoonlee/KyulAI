"""Train a CSV-curve classifier for DD laminate Type 1/2/3 labels."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold
from sklearn.inspection import permutation_importance
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from .curve_features import FEATURE_SETS, build_feature_rows, feature_matrix


def _candidate_models(random_state: int) -> dict[str, Pipeline]:
    return {
        "extra_trees": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", ExtraTreesClassifier(
                n_estimators=500,
                class_weight="balanced",
                min_samples_leaf=2,
                random_state=random_state,
            )),
        ]),
        "random_forest": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", RandomForestClassifier(
                n_estimators=500,
                class_weight="balanced",
                min_samples_leaf=2,
                random_state=random_state,
            )),
        ]),
        "hist_gradient_boosting": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", HistGradientBoostingClassifier(
                learning_rate=0.05,
                max_iter=300,
                l2_regularization=0.02,
                random_state=random_state,
            )),
        ]),
        "svc_rbf": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", SVC(C=10.0, gamma="scale", class_weight="balanced", probability=True, random_state=random_state)),
        ]),
        "neural_net_mlp_adam": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", MLPClassifier(
                hidden_layer_sizes=(64, 32),
                activation="relu",
                solver="adam",
                alpha=1e-3,
                learning_rate_init=5e-3,
                max_iter=1500,
                early_stopping=True,
                validation_fraction=0.15,
                n_iter_no_change=50,
                random_state=random_state,
            )),
        ]),
        "neural_net_mlp_lbfgs": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", MLPClassifier(
                hidden_layer_sizes=(48, 24),
                activation="relu",
                solver="lbfgs",
                alpha=1e-2,
                max_iter=2000,
                random_state=random_state,
            )),
        ]),
    }


def _write_feature_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _splitter(cv_mode: str, splits: int, random_state: int):
    if cv_mode == "sample":
        return StratifiedKFold(n_splits=splits, shuffle=True, random_state=random_state)
    if cv_mode == "grouped":
        return StratifiedGroupKFold(n_splits=splits, shuffle=True, random_state=random_state)
    raise ValueError(f"Unknown cv_mode: {cv_mode}")


def _cross_validate(
    models: dict[str, Pipeline],
    x: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    splits: int,
    random_state: int,
    cv_mode: str,
) -> tuple[str, dict]:
    splitter = _splitter(cv_mode, splits, random_state)
    results = {}
    for name, model in models.items():
        fold_scores = []
        all_true = []
        all_pred = []
        split_iter = splitter.split(x, y, groups) if cv_mode == "grouped" else splitter.split(x, y)
        for train_idx, val_idx in split_iter:
            model.fit(x[train_idx], y[train_idx])
            pred = model.predict(x[val_idx])
            fold_scores.append({
                "accuracy": accuracy_score(y[val_idx], pred),
                "macro_f1": f1_score(y[val_idx], pred, average="macro"),
                "weighted_f1": f1_score(y[val_idx], pred, average="weighted"),
            })
            all_true.extend(y[val_idx].tolist())
            all_pred.extend(pred.tolist())
        results[name] = {
            "cv_mode": cv_mode,
            "fold_scores": fold_scores,
            "mean_accuracy": float(np.mean([s["accuracy"] for s in fold_scores])),
            "std_accuracy": float(np.std([s["accuracy"] for s in fold_scores])),
            "mean_macro_f1": float(np.mean([s["macro_f1"] for s in fold_scores])),
            "std_macro_f1": float(np.std([s["macro_f1"] for s in fold_scores])),
            "mean_weighted_f1": float(np.mean([s["weighted_f1"] for s in fold_scores])),
            "confusion_matrix": confusion_matrix(all_true, all_pred, labels=[1, 2, 3]).tolist(),
            "classification_report": classification_report(all_true, all_pred, labels=[1, 2, 3], target_names=["Type 1", "Type 2", "Type 3"], output_dict=True, zero_division=0),
        }
    best_name = max(results, key=lambda n: (results[n]["mean_macro_f1"], results[n]["mean_accuracy"]))
    return best_name, results


def _write_report(path: Path, dataset: str, best_name: str, results: dict, feature_columns: list[str], rows: list[dict], feature_set: str, cv_mode: str, secondary_results: dict | None = None) -> None:
    counts = {label: sum(int(row["label"]) == label for row in rows) for label in (1, 2, 3)}
    lines = [
        "# DD CSV Curve Classifier Report",
        "",
        f"Dataset: `{dataset}`",
        "",
        "This model classifies DD laminate response Type 1/2/3 from transition metadata plus raw force-displacement CSV-derived shape features.",
        "Candidate models include tree ensembles, SVC, HistGradientBoosting, and neural-network MLP baselines.",
        f"Feature set: `{feature_set}`.",
        f"Primary validation mode: `{cv_mode}`. `sample` uses shuffled StratifiedKFold; `grouped` keeps matching Case3/Case4 Test_ID pairs together.",
        "",
        "## Label Counts",
        "",
        f"- Type 1: {counts[1]}",
        f"- Type 2: {counts[2]}",
        f"- Type 3: {counts[3]}",
        "",
        "## Feature Columns",
        "",
        "`" + "`, `".join(feature_columns) + "`",
        "",
        "## Cross-Validation Summary",
        "",
        "| Model | Accuracy | Macro F1 | Weighted F1 |",
        "|---|---:|---:|---:|",
    ]
    for name, result in sorted(results.items(), key=lambda item: item[1]["mean_macro_f1"], reverse=True):
        lines.append(
            f"| {name} | {result['mean_accuracy']:.4f} ± {result['std_accuracy']:.4f} | "
            f"{result['mean_macro_f1']:.4f} ± {result['std_macro_f1']:.4f} | {result['mean_weighted_f1']:.4f} |"
        )
    if secondary_results:
        lines.extend([
            "",
            "## Secondary Conservative Check",
            "",
            "| Model | Accuracy | Macro F1 | Weighted F1 |",
            "|---|---:|---:|---:|",
        ])
        for name, result in sorted(secondary_results.items(), key=lambda item: item[1]["mean_macro_f1"], reverse=True):
            lines.append(
                f"| {name} | {result['mean_accuracy']:.4f} ± {result['std_accuracy']:.4f} | "
                f"{result['mean_macro_f1']:.4f} ± {result['std_macro_f1']:.4f} | {result['mean_weighted_f1']:.4f} |"
            )

    lines.extend([
        "",
        f"Selected model: `{best_name}`",
        "",
        "## Selected Model Confusion Matrix",
        "",
        "Rows are true labels, columns are predictions `[Type1, Type2, Type3]`.",
        "",
        "```text",
        str(np.array(results[best_name]["confusion_matrix"])),
        "```",
    ])
    path.write_text("\n".join(lines) + "\n")


def train_curve_classifier(
    data_dir: str,
    output_dir: str,
    splits: int = 5,
    random_state: int = 42,
    feature_set: str = "combined",
    cv_mode: str = "sample",
    include_grouped_check: bool = True,
) -> dict:
    rows = build_feature_rows(data_dir)
    feature_columns = FEATURE_SETS[feature_set]
    x, y, groups = feature_matrix(rows, feature_columns)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    _write_feature_csv(out / "curve_features.csv", rows)

    models = _candidate_models(random_state)
    best_name, results = _cross_validate(models, x, y, groups, splits, random_state, cv_mode)
    secondary_results = None
    if include_grouped_check and cv_mode != "grouped":
        _, secondary_results = _cross_validate(_candidate_models(random_state), x, y, groups, splits, random_state, "grouped")

    final_model = _candidate_models(random_state)[best_name]
    final_model.fit(x, y)

    feature_importance_rows = []
    fitted_estimator = final_model.named_steps["model"]
    if hasattr(fitted_estimator, "feature_importances_"):
        feature_importance_rows = [
            {"feature": feature, "importance": float(importance)}
            for feature, importance in sorted(
                zip(feature_columns, fitted_estimator.feature_importances_),
                key=lambda item: item[1],
                reverse=True,
            )
        ]
        with (out / "feature_importances.csv").open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["feature", "importance"])
            writer.writeheader()
            writer.writerows(feature_importance_rows)

    bundle = {
        "model": final_model,
        "model_name": best_name,
        "feature_columns": feature_columns,
        "feature_set": feature_set,
        "cv_mode": cv_mode,
        "label_names": {1: "Type 1", 2: "Type 2", 3: "Type 3"},
        "data_dir": str(Path(data_dir).resolve()),
        "cv_results": results,
        "feature_importances": feature_importance_rows,
        "permutation_importances": [],
    }
    permutation_rows = []
    perm = permutation_importance(
        final_model,
        x,
        y,
        n_repeats=20,
        random_state=random_state,
        scoring="f1_macro",
    )
    permutation_rows = [
        {
            "feature": feature,
            "importance_mean": float(mean),
            "importance_std": float(std),
        }
        for feature, mean, std in sorted(
            zip(feature_columns, perm.importances_mean, perm.importances_std),
            key=lambda item: item[1],
            reverse=True,
        )
    ]
    with (out / "permutation_importances.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["feature", "importance_mean", "importance_std"])
        writer.writeheader()
        writer.writerows(permutation_rows)

    candidate_model_paths = {}
    candidate_dir = out / "candidate_models"
    candidate_dir.mkdir(exist_ok=True)
    for candidate_name, candidate_model in _candidate_models(random_state).items():
        fitted_model = final_model if candidate_name == best_name else candidate_model.fit(x, y)
        candidate_path = candidate_dir / f"{candidate_name}.joblib"
        joblib.dump({
            "model": fitted_model,
            "model_name": candidate_name,
            "feature_columns": feature_columns,
            "feature_set": feature_set,
            "cv_mode": cv_mode,
            "label_names": {1: "Type 1", 2: "Type 2", 3: "Type 3"},
            "data_dir": str(Path(data_dir).resolve()),
            "cv_results": {candidate_name: results[candidate_name]},
        }, candidate_path)
        candidate_model_paths[candidate_name] = str(candidate_path)

    summary = {
        "best_model": best_name,
        "feature_columns": feature_columns,
        "feature_set": feature_set,
        "cv_mode": cv_mode,
        "cv_results": results,
        "secondary_grouped_cv_results": secondary_results,
        "candidate_model_paths": candidate_model_paths,
        "feature_importances": feature_importance_rows,
        "permutation_importances": permutation_rows,
    }
    bundle["permutation_importances"] = permutation_rows
    bundle["secondary_grouped_cv_results"] = secondary_results
    bundle["candidate_model_paths"] = candidate_model_paths
    joblib.dump(bundle, out / "curve_classifier.joblib")
    (out / "curve_classifier_metrics.json").write_text(json.dumps(summary, indent=2))
    _write_report(out / "curve_classifier_report.md", data_dir, best_name, results, feature_columns, rows, feature_set, cv_mode, secondary_results)

    print(f"Saved model bundle: {out / 'curve_classifier.joblib'}")
    print(f"Saved feature table: {out / 'curve_features.csv'}")
    if feature_importance_rows:
        print(f"Saved feature importances: {out / 'feature_importances.csv'}")
    print(f"Saved permutation importances: {out / 'permutation_importances.csv'}")
    print(f"Saved candidate model bundles: {out / 'candidate_models'}")
    print(f"Saved report: {out / 'curve_classifier_report.md'}")
    print(f"Best model: {best_name}")
    print(f"Mean {cv_mode} CV accuracy: {results[best_name]['mean_accuracy']:.4f}")
    print(f"Mean {cv_mode} CV macro F1: {results[best_name]['mean_macro_f1']:.4f}")
    print(np.array(results[best_name]["confusion_matrix"]))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a DD laminate CSV-curve classifier")
    parser.add_argument("--data-dir", default="data/datasets/DD_curated_csv_v1")
    parser.add_argument("--output-dir", default="models/dd_laminate_csv_v1")
    parser.add_argument("--splits", type=int, default=5)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--feature-set", choices=sorted(FEATURE_SETS), default="combined")
    parser.add_argument("--cv-mode", choices=["sample", "grouped"], default="sample")
    parser.add_argument("--no-grouped-check", action="store_true")
    args = parser.parse_args()
    train_curve_classifier(
        args.data_dir,
        args.output_dir,
        args.splits,
        args.random_state,
        args.feature_set,
        args.cv_mode,
        include_grouped_check=not args.no_grouped_check,
    )


if __name__ == "__main__":
    main()
