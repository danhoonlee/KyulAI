"""Train theta/case DD laminate Type predictor.

This model intentionally uses only pre-Abaqus design inputs: theta1, theta2,
and Case. Unlike curve classifiers, it does not use Pt or the
force-displacement CSV curve.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "8")

import joblib
import numpy as np
from sklearn.ensemble import (
    ExtraTreesClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


def load_theta_rows(data_dir: str | Path, cases=("Case3", "Case4")) -> list[dict]:
    data_path = Path(data_dir)
    rows = []
    for case in cases:
        with (data_path / case / "transition_load.csv").open(newline="") as f:
            for row in csv.DictReader(f):
                rows.append(
                    {
                        "case": case,
                        "test_id": row["Test_ID"],
                        "theta1": float(row["Theta1"]),
                        "theta2": float(row["Theta2"]),
                        "label": int(row["type"]),
                    }
                )
    return rows


def theta_matrix(rows: list[dict]):
    x = np.array(
        [[r["theta1"], r["theta2"], 1.0 if r["case"] == "Case4" else 0.0] for r in rows],
        dtype=float,
    )
    y = np.array([r["label"] for r in rows], dtype=int)
    groups = np.array([r["test_id"] for r in rows], dtype=str)
    return x, y, groups


def candidate_models(random_state: int) -> dict[str, Pipeline]:
    return {
        "hist_gradient_boosting": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    HistGradientBoostingClassifier(
                        learning_rate=0.04,
                        max_iter=300,
                        l2_regularization=0.05,
                        random_state=random_state,
                    ),
                ),
            ]
        ),
        "random_forest": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=500,
                        class_weight="balanced",
                        min_samples_leaf=2,
                        random_state=random_state,
                    ),
                ),
            ]
        ),
        "extra_trees": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    ExtraTreesClassifier(
                        n_estimators=500,
                        class_weight="balanced",
                        min_samples_leaf=2,
                        random_state=random_state,
                    ),
                ),
            ]
        ),
        "svc_rbf": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "model",
                    SVC(
                        C=5.0,
                        gamma="scale",
                        class_weight="balanced",
                        probability=True,
                        random_state=random_state,
                    ),
                ),
            ]
        ),
        "neural_net_mlp_lbfgs": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "model",
                    MLPClassifier(
                        hidden_layer_sizes=(32, 16),
                        activation="relu",
                        solver="lbfgs",
                        alpha=1e-2,
                        max_iter=2000,
                        random_state=random_state,
                    ),
                ),
            ]
        ),
        "neural_net_mlp_adam": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "model",
                    MLPClassifier(
                        hidden_layer_sizes=(48, 24),
                        activation="relu",
                        solver="adam",
                        alpha=1e-3,
                        learning_rate_init=3e-3,
                        max_iter=1500,
                        early_stopping=True,
                        validation_fraction=0.15,
                        n_iter_no_change=60,
                        random_state=random_state,
                    ),
                ),
            ]
        ),
    }


def split_iter(cv_mode: str, splits: int, random_state: int, x, y, groups):
    if cv_mode == "sample":
        yield from StratifiedKFold(n_splits=splits, shuffle=True, random_state=random_state).split(
            x, y
        )
    elif cv_mode == "grouped":
        yield from StratifiedGroupKFold(
            n_splits=splits, shuffle=True, random_state=random_state
        ).split(x, y, groups)
    else:
        raise ValueError(cv_mode)


def cross_validate(models, x, y, groups, splits: int, random_state: int, cv_mode: str):
    results = {}
    for name, model in models.items():
        fold_scores = []
        all_true = []
        all_pred = []
        for train_idx, val_idx in split_iter(cv_mode, splits, random_state, x, y, groups):
            model.fit(x[train_idx], y[train_idx])
            pred = model.predict(x[val_idx])
            fold_scores.append(
                {
                    "accuracy": accuracy_score(y[val_idx], pred),
                    "macro_f1": f1_score(y[val_idx], pred, average="macro", zero_division=0),
                    "weighted_f1": f1_score(y[val_idx], pred, average="weighted", zero_division=0),
                }
            )
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
            "classification_report": classification_report(
                all_true,
                all_pred,
                labels=[1, 2, 3],
                target_names=["Type 1", "Type 2", "Type 3"],
                output_dict=True,
                zero_division=0,
            ),
        }
    best = max(results, key=lambda n: (results[n]["mean_macro_f1"], results[n]["mean_accuracy"]))
    return best, results


def find_conflicts(rows: list[dict]) -> list[dict]:
    by_theta = defaultdict(list)
    for r in rows:
        by_theta[(r["theta1"], r["theta2"])].append(r)
    conflicts = []
    for (theta1, theta2), vals in by_theta.items():
        labels = sorted({v["label"] for v in vals})
        if len(labels) > 1:
            conflicts.append(
                {
                    "theta1": theta1,
                    "theta2": theta2,
                    "labels": labels,
                    "samples": vals,
                }
            )
    return conflicts


def write_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_report(
    out: Path,
    data_dir: str,
    best: str,
    primary: dict,
    secondary: dict,
    conflicts: list[dict],
    rows: list[dict],
) -> None:
    counts = {label: sum(r["label"] == label for r in rows) for label in [1, 2, 3]}
    max_deterministic_accuracy = 1.0 - len(conflicts) / len(rows)
    lines = [
        "# DD Theta-Only Type Predictor Report",
        "",
        f"Dataset: `{data_dir}`",
        "",
        "This model predicts Type 1/2/3 using only `theta1`, `theta2`, and `case`. It does not use Pt or force-displacement curves.",
        "Because this is a pre-Abaqus surrogate, performance is expected to be lower than curve-based models.",
        "",
        "## Label Counts",
        "",
        f"- Type 1: {counts[1]}",
        f"- Type 2: {counts[2]}",
        f"- Type 3: {counts[3]}",
        "",
        "## Intrinsic Ambiguity",
        "",
        f"There are {len(conflicts)} theta pairs with conflicting labels across Case3/Case4.",
        f"The deterministic theta-only ceiling on the {len(rows)}-row dataset is approximately {max_deterministic_accuracy:.4f} if one label must be assigned per theta pair.",
        "",
    ]
    if conflicts:
        lines.extend(["| theta1 | theta2 | samples |", "|---:|---:|---|"])
        for c in conflicts:
            sample_text = "; ".join(
                f"{s['case']}/{s['test_id']}=Type{s['label']}" for s in c["samples"]
            )
            lines.append(f"| {c['theta1']:.0f} | {c['theta2']:.0f} | {sample_text} |")
        lines.append("")
    lines.extend(
        [
            "## Primary Sample CV",
            "",
            "| Model | Accuracy | Macro F1 | Weighted F1 |",
            "|---|---:|---:|---:|",
        ]
    )
    for name, r in sorted(primary.items(), key=lambda item: item[1]["mean_macro_f1"], reverse=True):
        lines.append(
            f"| {name} | {r['mean_accuracy']:.4f} ± {r['std_accuracy']:.4f} | {r['mean_macro_f1']:.4f} ± {r['std_macro_f1']:.4f} | {r['mean_weighted_f1']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Secondary Grouped CV",
            "",
            "This grouped check keeps matching Case3/Case4 Test_ID pairs together and is the better estimate for unseen theta pairs.",
            "",
            "| Model | Accuracy | Macro F1 | Weighted F1 |",
            "|---|---:|---:|---:|",
        ]
    )
    for name, r in sorted(
        secondary.items(), key=lambda item: item[1]["mean_macro_f1"], reverse=True
    ):
        lines.append(
            f"| {name} | {r['mean_accuracy']:.4f} ± {r['std_accuracy']:.4f} | {r['mean_macro_f1']:.4f} ± {r['std_macro_f1']:.4f} | {r['mean_weighted_f1']:.4f} |"
        )
    lines.extend(
        [
            "",
            f"Selected production theta/case model: `{best}` from primary CV.",
            "",
            "## Selected Model Confusion Matrix",
            "",
            "Rows=true, columns=predicted `[Type1, Type2, Type3]`.",
            "",
            "```text",
            str(np.array(primary[best]["confusion_matrix"])),
            "```",
        ]
    )
    (out / "theta_classifier_report.md").write_text("\n".join(lines) + "\n")


def train_theta_classifier(data_dir: str, output_dir: str, splits: int = 5, random_state: int = 42):
    rows = load_theta_rows(data_dir)
    x, y, groups = theta_matrix(rows)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_rows(
        out / "theta_training_rows.csv", rows, ["case", "test_id", "theta1", "theta2", "label"]
    )
    conflicts = find_conflicts(rows)
    conflict_rows = []
    for c in conflicts:
        for sample in c["samples"]:
            conflict_rows.append(sample)
    if conflict_rows:
        write_rows(
            out / "theta_label_conflicts.csv",
            conflict_rows,
            ["case", "test_id", "theta1", "theta2", "label"],
        )

    best, primary = cross_validate(
        candidate_models(random_state), x, y, groups, splits, random_state, "sample"
    )
    _, secondary = cross_validate(
        candidate_models(random_state), x, y, groups, splits, random_state, "grouped"
    )
    final = candidate_models(random_state)[best]
    final.fit(x, y)

    bundle = {
        "model": final,
        "model_name": best,
        "feature_columns": ["theta1", "theta2", "case_is_case4"],
        "label_names": {1: "Type 1", 2: "Type 2", 3: "Type 3"},
        "data_dir": str(Path(data_dir).resolve()),
        "primary_sample_cv_results": primary,
        "secondary_grouped_cv_results": secondary,
        "conflicts": conflicts,
    }
    joblib.dump(bundle, out / "theta_classifier.joblib")
    (out / "theta_classifier_metrics.json").write_text(json.dumps(bundle, indent=2, default=str))
    write_report(out, data_dir, best, primary, secondary, conflicts, rows)
    print(f"Saved model: {out / 'theta_classifier.joblib'}")
    print(f"Saved report: {out / 'theta_classifier_report.md'}")
    print(f"Best sample-CV model: {best}")
    print(f"Sample CV accuracy: {primary[best]['mean_accuracy']:.4f}")
    print(f"Sample CV macro F1: {primary[best]['mean_macro_f1']:.4f}")
    grouped_best = max(
        secondary, key=lambda n: (secondary[n]["mean_macro_f1"], secondary[n]["mean_accuracy"])
    )
    print(f"Best grouped-CV model: {grouped_best}")
    print(f"Grouped CV accuracy: {secondary[grouped_best]['mean_accuracy']:.4f}")
    print(f"Grouped CV macro F1: {secondary[grouped_best]['mean_macro_f1']:.4f}")
    print(np.array(primary[best]["confusion_matrix"]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Train theta/case DD Type predictor")
    parser.add_argument("--data-dir", default="data/datasets/DD_curated_csv_v1")
    parser.add_argument("--output-dir", default="models/dd_laminate_theta_v1")
    parser.add_argument("--splits", type=int, default=5)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()
    train_theta_classifier(args.data_dir, args.output_dir, args.splits, args.random_state)


if __name__ == "__main__":
    main()
