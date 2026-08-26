"""Train u3 DD Pt/curve forecast models from theta/case only."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, cast

import joblib
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.decomposition import PCA
from sklearn.ensemble import ExtraTreesClassifier, ExtraTreesRegressor, RandomForestRegressor
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import GroupKFold
from torch.utils.data import DataLoader, Dataset, Subset

from src.ml.dd_laminate.laminate_physics import (
    CANONICAL_STACK_VERSION,
    COMPACT_PHYSICS_FEATURE_COLUMNS,
    EXTENDED_PHYSICS_FEATURE_COLUMNS,
    LEGACY_STACK_VERSION,
    compact_physics_feature_vector,
    extended_physics_feature_vector,
)
from src.ml.dd_laminate.train_u3_pt_models import (
    CASES,
    FOLDERS,
    GRID_LEN,
    curve_arrays,
    load_records,
)


def u3_theta_features(records) -> tuple[np.ndarray, list[str]]:
    names = [
        "theta1",
        "theta2",
        "abs_theta1",
        "abs_theta2",
        "theta_sum",
        "theta_diff",
        "theta_abs_diff",
        "theta_product",
        "theta1_sin_2",
        "theta1_cos_2",
        "theta2_sin_2",
        "theta2_cos_2",
        "theta1_sin_4",
        "theta1_cos_4",
        "theta2_sin_4",
        "theta2_cos_4",
        *[f"case_{case.lower()}" for case in CASES],
    ]
    rows: list[list[float]] = []
    for record in records:
        theta1_rad = np.deg2rad(record.theta1)
        theta2_rad = np.deg2rad(record.theta2)
        rows.append(
            [
                record.theta1,
                record.theta2,
                abs(record.theta1),
                abs(record.theta2),
                record.theta1 + record.theta2,
                record.theta1 - record.theta2,
                abs(record.theta1 - record.theta2),
                record.theta1 * record.theta2,
                float(np.sin(2.0 * theta1_rad)),
                float(np.cos(2.0 * theta1_rad)),
                float(np.sin(2.0 * theta2_rad)),
                float(np.cos(2.0 * theta2_rad)),
                float(np.sin(4.0 * theta1_rad)),
                float(np.cos(4.0 * theta1_rad)),
                float(np.sin(4.0 * theta2_rad)),
                float(np.cos(4.0 * theta2_rad)),
                *[1.0 if record.case == case else 0.0 for case in CASES],
            ]
        )
    return np.asarray(rows, dtype=float), names


def u3_theta_physics_features(records) -> tuple[np.ndarray, list[str]]:
    theta_x, theta_names = u3_theta_features(records)
    physics_x = np.vstack(
        [
            extended_physics_feature_vector(
                record.case,
                record.theta1,
                record.theta2,
                stack_version=LEGACY_STACK_VERSION,
            )
            for record in records
        ]
    )
    return np.hstack([theta_x, physics_x]), [*theta_names, *EXTENDED_PHYSICS_FEATURE_COLUMNS]


def u3_theta_physics_v2_features(records) -> tuple[np.ndarray, list[str]]:
    theta_x, theta_names = u3_theta_features(records)
    physics_x = np.vstack(
        [
            compact_physics_feature_vector(
                record.case,
                record.theta1,
                record.theta2,
                stack_version=LEGACY_STACK_VERSION,
            )
            for record in records
        ]
    )
    return np.hstack([theta_x, physics_x]), [*theta_names, *COMPACT_PHYSICS_FEATURE_COLUMNS]


def u3_theta_physics_canonical_features(records) -> tuple[np.ndarray, list[str]]:
    theta_x, theta_names = u3_theta_features(records)
    physics_x = np.vstack(
        [
            extended_physics_feature_vector(
                record.case,
                record.theta1,
                record.theta2,
                stack_version=CANONICAL_STACK_VERSION,
            )
            for record in records
        ]
    )
    return np.hstack([theta_x, physics_x]), [*theta_names, *EXTENDED_PHYSICS_FEATURE_COLUMNS]


def u3_theta_physics_compact_canonical_features(records) -> tuple[np.ndarray, list[str]]:
    theta_x, theta_names = u3_theta_features(records)
    physics_x = np.vstack(
        [
            compact_physics_feature_vector(
                record.case,
                record.theta1,
                record.theta2,
                stack_version=CANONICAL_STACK_VERSION,
            )
            for record in records
        ]
    )
    return np.hstack([theta_x, physics_x]), [*theta_names, *COMPACT_PHYSICS_FEATURE_COLUMNS]


def u3_feature_matrix(records, feature_set: str = "theta") -> tuple[np.ndarray, list[str]]:
    if feature_set == "theta":
        return u3_theta_features(records)
    if feature_set == "theta_physics":
        return u3_theta_physics_features(records)
    if feature_set == "theta_physics_v2":
        return u3_theta_physics_v2_features(records)
    if feature_set == "theta_physics_canonical_v2":
        return u3_theta_physics_canonical_features(records)
    if feature_set == "theta_physics_compact_canonical_v2":
        return u3_theta_physics_compact_canonical_features(records)
    raise ValueError(f"Unsupported u3 feature set: {feature_set}")


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2_score(y_true, y_pred)),
    }


def scalar_candidates(seed: int) -> dict[str, Any]:
    return {
        "extra_trees": ExtraTreesRegressor(
            n_estimators=900,
            random_state=seed,
            min_samples_leaf=1,
            n_jobs=-1,
        ),
        "random_forest": RandomForestRegressor(
            n_estimators=650,
            random_state=seed + 1,
            min_samples_leaf=1,
            n_jobs=-1,
        ),
    }


def type_label(record) -> int:
    return int(record.u3_bucket)


def type_probabilities(classifier, x: np.ndarray) -> tuple[np.ndarray, list[dict[str, float]]]:
    classes = [int(value) for value in classifier.classes_]
    probs = classifier.predict_proba(x)
    labels = []
    for row in probs:
        labels.append({f"type{cls}": float(prob) for cls, prob in zip(classes, row, strict=True)})
    return np.asarray(classes, dtype=int)[np.argmax(probs, axis=1)], labels


class U3ForecastDataset(Dataset):
    def __init__(self, x: np.ndarray, scalar_targets: np.ndarray, curve_targets: np.ndarray):
        self.x = torch.tensor(x, dtype=torch.float32)
        self.scalar_targets = torch.tensor(scalar_targets, dtype=torch.float32)
        self.curve_targets = torch.tensor(curve_targets, dtype=torch.float32)

    def __len__(self) -> int:
        return len(self.x)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        return {
            "x": self.x[idx],
            "scalars": self.scalar_targets[idx],
            "curve": self.curve_targets[idx],
        }


class U3ForecastGointMLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        curve_len: int,
        hidden_dim: int = 128,
        branches: int = 4,
        dropout: float = 0.12,
    ):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.LayerNorm(hidden_dim),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
        )
        self.branches = nn.ModuleList(
            [
                nn.Sequential(
                    nn.Linear(hidden_dim, hidden_dim),
                    nn.GELU(),
                    nn.Dropout(dropout),
                    nn.Linear(hidden_dim, hidden_dim),
                    nn.GELU(),
                )
                for _ in range(branches)
            ]
        )
        self.gate = nn.Sequential(nn.Linear(hidden_dim, branches), nn.Softmax(dim=-1))
        self.scalar_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.GELU(),
            nn.Linear(hidden_dim // 2, 3),
        )
        self.curve_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, curve_len),
        )

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        latent = self.stem(x)
        gates = self.gate(latent).unsqueeze(-1)
        branch_values = torch.stack([branch(latent) for branch in self.branches], dim=1)
        mixed = (gates * branch_values).sum(dim=1)
        scalars = self.scalar_head(mixed)
        curve = torch.sigmoid(self.curve_head(mixed))
        return scalars, curve


def _normalize(train: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = train.mean(axis=0)
    std = train.std(axis=0)
    std = np.where(std < 1e-9, 1.0, std)
    return (values - mean) / std, mean, std


def _run_goint_epoch(
    model: U3ForecastGointMLP,
    loader: DataLoader,
    optimizer,
    device: torch.device,
    train: bool,
) -> tuple[float, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    model.train(mode=train)
    total = 0.0
    total_n = 0
    scalar_preds: list[np.ndarray] = []
    scalar_trues: list[np.ndarray] = []
    curve_preds: list[np.ndarray] = []
    curve_trues: list[np.ndarray] = []
    with torch.set_grad_enabled(train):
        for batch in loader:
            x = batch["x"].to(device)
            scalars = batch["scalars"].to(device)
            curve = batch["curve"].to(device)
            if train:
                optimizer.zero_grad(set_to_none=True)
            pred_scalars, pred_curve = model(x)
            loss = F.smooth_l1_loss(pred_scalars, scalars) + 0.65 * F.mse_loss(pred_curve, curve)
            if train:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 3.0)
                optimizer.step()
            total += float(loss.detach().cpu()) * len(x)
            total_n += len(x)
            scalar_preds.append(pred_scalars.detach().cpu().numpy())
            scalar_trues.append(scalars.detach().cpu().numpy())
            curve_preds.append(pred_curve.detach().cpu().numpy())
            curve_trues.append(curve.detach().cpu().numpy())
    return (
        total / max(total_n, 1),
        np.vstack(scalar_trues),
        np.vstack(scalar_preds),
        np.vstack(curve_trues),
        np.vstack(curve_preds),
    )


def train_goint_forecast(
    x: np.ndarray,
    y_scalars: np.ndarray,
    y_curve: np.ndarray,
    groups: np.ndarray,
    output_dir: Path,
    seed: int,
    splits: int,
    device_name: str,
    feature_names: list[str],
    feature_set: str,
) -> dict[str, object]:
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    device = torch.device(
        device_name if device_name != "auto" else ("cuda" if torch.cuda.is_available() else "cpu")
    )
    scalar_log = np.log1p(np.maximum(y_scalars, 0.0))
    splitter = GroupKFold(n_splits=splits)
    fold_rows = []
    for fold, (train_idx, val_idx) in enumerate(
        splitter.split(x, y_scalars[:, 0], groups), start=1
    ):
        x_norm, x_mean, x_std = _normalize(x[train_idx], x)
        scalar_norm, scalar_mean, scalar_std = _normalize(scalar_log[train_idx], scalar_log)
        dataset = U3ForecastDataset(x_norm, scalar_norm, y_curve)
        train_loader = DataLoader(Subset(dataset, train_idx.tolist()), batch_size=64, shuffle=True)
        val_loader = DataLoader(Subset(dataset, val_idx.tolist()), batch_size=128, shuffle=False)
        model = U3ForecastGointMLP(x.shape[1], y_curve.shape[1]).to(device)
        optimizer = torch.optim.AdamW(model.parameters(), lr=8e-4, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=220)
        best_state = None
        best_mae = float("inf")
        best_epoch = 0
        stale = 0
        for epoch in range(1, 241):
            _run_goint_epoch(model, train_loader, optimizer, device, train=True)
            scheduler.step()
            _, _true_norm, pred_norm, true_curve, pred_curve = _run_goint_epoch(
                model, val_loader, optimizer, device, train=False
            )
            pred_scalars = np.expm1(pred_norm * scalar_std + scalar_mean)
            mae = mean_absolute_error(y_scalars[val_idx, 0], pred_scalars[:, 0])
            if mae < best_mae:
                best_mae = float(mae)
                best_epoch = epoch
                best_state = {
                    key: value.detach().cpu().clone() for key, value in model.state_dict().items()
                }
                stale = 0
            else:
                stale += 1
            if stale >= 42:
                break
        if best_state is not None:
            model.load_state_dict(best_state)
        _, _true_norm, pred_norm, true_curve, pred_curve = _run_goint_epoch(
            model, val_loader, optimizer, device, train=False
        )
        pred_scalars = np.expm1(pred_norm * scalar_std + scalar_mean)
        fold_metrics = {
            "fold": fold,
            "best_epoch": best_epoch,
            "pt_mae": float(mean_absolute_error(y_scalars[val_idx, 0], pred_scalars[:, 0])),
            "pt_r2": float(r2_score(y_scalars[val_idx, 0], pred_scalars[:, 0])),
            "max_displacement_mae": float(
                mean_absolute_error(y_scalars[val_idx, 1], pred_scalars[:, 1])
            ),
            "max_force_mae": float(mean_absolute_error(y_scalars[val_idx, 2], pred_scalars[:, 2])),
            "curve_norm_rmse": float(np.sqrt(np.mean((pred_curve - true_curve) ** 2))),
        }
        fold_rows.append(fold_metrics)
        print(
            f"goint fold {fold}: pt_mae={fold_metrics['pt_mae']:.2f}, curve_rmse={fold_metrics['curve_norm_rmse']:.4f}",
            flush=True,
        )

    x_norm, x_mean, x_std = _normalize(x, x)
    scalar_norm, scalar_mean, scalar_std = _normalize(scalar_log, scalar_log)
    final_dataset = U3ForecastDataset(x_norm, scalar_norm, y_curve)
    final_loader = DataLoader(final_dataset, batch_size=64, shuffle=True)
    final_model = U3ForecastGointMLP(x.shape[1], y_curve.shape[1]).to(device)
    optimizer = torch.optim.AdamW(final_model.parameters(), lr=8e-4, weight_decay=1e-4)
    for _ in range(180):
        _run_goint_epoch(final_model, final_loader, optimizer, device, train=True)

    metrics = {
        "n_samples": len(x),
        "grid_len": int(y_curve.shape[1]),
        "cv_pt_mae_mean": float(np.mean([row["pt_mae"] for row in fold_rows])),
        "cv_pt_mae_std": float(np.std([row["pt_mae"] for row in fold_rows])),
        "cv_pt_r2_mean": float(np.mean([row["pt_r2"] for row in fold_rows])),
        "cv_max_displacement_mae_mean": float(
            np.mean([row["max_displacement_mae"] for row in fold_rows])
        ),
        "cv_max_force_mae_mean": float(np.mean([row["max_force_mae"] for row in fold_rows])),
        "curve_cv_norm_rmse_mean": float(np.mean([row["curve_norm_rmse"] for row in fold_rows])),
        "curve_cv_norm_rmse_std": float(np.std([row["curve_norm_rmse"] for row in fold_rows])),
        "folds": fold_rows,
        "device": str(device),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": final_model.state_dict(),
            "model_config": {
                "input_dim": int(x.shape[1]),
                "curve_len": int(y_curve.shape[1]),
                "hidden_dim": 128,
                "branches": 4,
                "dropout": 0.12,
            },
            "feature_mean": x_mean,
            "feature_std": x_std,
            "scalar_log_mean": scalar_mean,
            "scalar_log_std": scalar_std,
            "grid": np.linspace(0.0, 1.0, y_curve.shape[1]),
            "feature_names": feature_names,
            "feature_builder": feature_set,
            "metrics": metrics,
        },
        output_dir / "u3_forecast_goint.pt",
    )
    (output_dir / "u3_forecast_goint_metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )
    return metrics


def train_forecast(
    manifest: Path,
    output_dir: Path,
    report_dir: Path,
    seed: int,
    splits: int,
    feature_set: str,
) -> dict[str, object]:
    records = load_records(manifest)
    seq, max_force, max_disp, _curve_meta = curve_arrays(records, GRID_LEN)
    x, feature_names = u3_feature_matrix(records, feature_set)
    y_pt = np.asarray([record.pt for record in records], dtype=float)
    y_type = np.asarray([type_label(record) for record in records], dtype=int)
    y_scalars = np.column_stack([y_pt, max_disp, max_force])
    y_curve = seq[:, 1, :]
    groups = np.asarray([record.test_id for record in records])

    splitter = GroupKFold(n_splits=splits)
    candidate_rows: dict[str, list[dict[str, float]]] = {}
    oof_rows: list[dict[str, object]] = []
    for name, estimator in scalar_candidates(seed).items():
        rows: list[dict[str, float]] = []
        for fold, (train_idx, val_idx) in enumerate(splitter.split(x, y_pt, groups), start=1):
            from sklearn.base import clone

            model = cast(Any, clone(estimator))
            model.fit(x[train_idx], y_scalars[train_idx])
            pred_scalars = np.asarray(model.predict(x[val_idx]), dtype=float)
            fold_metrics = {
                "fold": fold,
                "pt_mae": float(mean_absolute_error(y_scalars[val_idx, 0], pred_scalars[:, 0])),
                "max_displacement_mae": float(
                    mean_absolute_error(y_scalars[val_idx, 1], pred_scalars[:, 1])
                ),
                "max_force_mae": float(
                    mean_absolute_error(y_scalars[val_idx, 2], pred_scalars[:, 2])
                ),
                "pt_r2": float(r2_score(y_scalars[val_idx, 0], pred_scalars[:, 0])),
            }
            rows.append(fold_metrics)
            for idx, pred_value in zip(val_idx, pred_scalars[:, 0], strict=True):
                oof_rows.append(
                    {
                        "model": name,
                        "fold": fold,
                        "case": records[int(idx)].case,
                        "u3_folder": records[int(idx)].u3_folder,
                        "test_id": records[int(idx)].test_id,
                        "pt_true": float(y_pt[idx]),
                        "pt_pred": float(pred_value),
                        "abs_error": float(abs(y_pt[idx] - pred_value)),
                    }
                )
        candidate_rows[name] = rows
        print(f"{name}: pt_mae={np.mean([row['pt_mae'] for row in rows]):.2f}", flush=True)

    metrics_by_model: dict[str, dict[str, Any]] = {
        name: {
            "cv_pt_mae_mean": float(np.mean([row["pt_mae"] for row in rows])),
            "cv_pt_mae_std": float(np.std([row["pt_mae"] for row in rows])),
            "cv_max_displacement_mae_mean": float(
                np.mean([row["max_displacement_mae"] for row in rows])
            ),
            "cv_max_force_mae_mean": float(np.mean([row["max_force_mae"] for row in rows])),
            "cv_pt_r2_mean": float(np.mean([row["pt_r2"] for row in rows])),
            "folds": rows,
        }
        for name, rows in candidate_rows.items()
    }
    best_name = min(
        metrics_by_model, key=lambda key: float(metrics_by_model[key]["cv_pt_mae_mean"])
    )

    type_fold_rows = []
    type_oof_rows: list[dict[str, object]] = []
    type_model = ExtraTreesClassifier(
        n_estimators=700,
        random_state=seed + 200,
        min_samples_leaf=2,
        class_weight="balanced",
        n_jobs=-1,
    )
    from sklearn.base import clone

    for fold, (train_idx, val_idx) in enumerate(splitter.split(x, y_type, groups), start=1):
        fold_type_model = clone(type_model)
        fold_type_model.fit(x[train_idx], y_type[train_idx])
        pred_type = fold_type_model.predict(x[val_idx])
        pred_proba = fold_type_model.predict_proba(x[val_idx])
        class_values = [int(value) for value in fold_type_model.classes_]
        type_fold_rows.append(
            {
                "fold": fold,
                "accuracy": float(accuracy_score(y_type[val_idx], pred_type)),
                "macro_f1": float(f1_score(y_type[val_idx], pred_type, average="macro")),
            }
        )
        for local_index, idx in enumerate(val_idx):
            type_oof_rows.append(
                {
                    "fold": fold,
                    "case": records[int(idx)].case,
                    "test_id": records[int(idx)].test_id,
                    "type_true": int(y_type[idx]),
                    "type_pred": int(pred_type[local_index]),
                    **{
                        f"prob_type{cls}": float(prob)
                        for cls, prob in zip(class_values, pred_proba[local_index], strict=True)
                    },
                }
            )

    final_scalar_model = scalar_candidates(seed)[best_name]

    final_scalar_model = cast(Any, clone(final_scalar_model))
    final_scalar_model.fit(x, y_scalars)
    final_type_model = clone(type_model)
    final_type_model.fit(x, y_type)

    curve_components = min(22, y_curve.shape[1], len(records))
    pca = PCA(n_components=curve_components, random_state=seed)
    curve_scores = pca.fit_transform(y_curve)
    curve_model = ExtraTreesRegressor(
        n_estimators=900,
        random_state=seed + 100,
        min_samples_leaf=1,
        n_jobs=-1,
    )

    curve_fold_rows = []
    for fold, (train_idx, val_idx) in enumerate(splitter.split(x, y_pt, groups), start=1):
        fold_pca = PCA(n_components=min(curve_components, len(train_idx)), random_state=seed + fold)
        fold_scores = fold_pca.fit_transform(y_curve[train_idx])
        fold_curve_model = ExtraTreesRegressor(
            n_estimators=650,
            random_state=seed + 100 + fold,
            min_samples_leaf=1,
            n_jobs=-1,
        )
        fold_curve_model.fit(x[train_idx], fold_scores)
        pred_curve = np.clip(
            fold_pca.inverse_transform(fold_curve_model.predict(x[val_idx])), 0.0, None
        )
        curve_fold_rows.append(
            {
                "fold": fold,
                "curve_norm_rmse": float(np.sqrt(np.mean((pred_curve - y_curve[val_idx]) ** 2))),
            }
        )
    curve_model.fit(x, curve_scores)

    metrics: dict[str, Any] = {
        "n_samples": len(records),
        "grid_len": GRID_LEN,
        "best_scalar_model": best_name,
        "models": metrics_by_model,
        "curve_cv_norm_rmse_mean": float(
            np.mean([row["curve_norm_rmse"] for row in curve_fold_rows])
        ),
        "curve_cv_norm_rmse_std": float(
            np.std([row["curve_norm_rmse"] for row in curve_fold_rows])
        ),
        "curve_folds": curve_fold_rows,
        "type_accuracy_mean": float(np.mean([row["accuracy"] for row in type_fold_rows])),
        "type_macro_f1_mean": float(np.mean([row["macro_f1"] for row in type_fold_rows])),
        "type_folds": type_fold_rows,
    }

    goint_metrics = train_goint_forecast(
        x=x,
        y_scalars=y_scalars,
        y_curve=y_curve,
        groups=groups,
        output_dir=output_dir,
        seed=seed,
        splits=splits,
        device_name="auto",
        feature_names=feature_names,
        feature_set=feature_set,
    )
    metrics["goint"] = goint_metrics

    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model_name": "u3_forecast_extra_trees_pca",
            "feature_builder": feature_set,
            "feature_names": feature_names,
            "cases": CASES,
            "folders": FOLDERS,
            "grid": np.linspace(0.0, 1.0, GRID_LEN),
            "scalar_model_name": best_name,
            "scalar_model": final_scalar_model,
            "scalar_columns": ["pt", "max_displacement", "max_force"],
            "type_model": final_type_model,
            "type_labels": [2, 3],
            "pca": pca,
            "curve_model": curve_model,
            "metrics": metrics,
        },
        output_dir / "u3_forecast.joblib",
    )
    (output_dir / "u3_forecast_metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )
    with (output_dir / "oof_predictions.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "model",
                "fold",
                "case",
                "u3_folder",
                "test_id",
                "pt_true",
                "pt_pred",
                "abs_error",
            ],
        )
        writer.writeheader()
        writer.writerows(oof_rows)
    with (output_dir / "type_oof_predictions.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        fieldnames = [
            "fold",
            "case",
            "test_id",
            "type_true",
            "type_pred",
            "prob_type2",
            "prob_type3",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(type_oof_rows)

    lines = [
        "# DD u3 Forecast Training Report",
        "",
        f"- Dataset: `{manifest}`",
        f"- Samples: {len(records)}",
        "- Input: theta1, theta2, and Case only. No force-displacement CSV or known Type is used at prediction time.",
        f"- Feature set: `{feature_set}`",
        "- Validation: GroupKFold by Test ID.",
        "",
        "## Best Scalar Model",
        f"- `{best_name}`",
        f"- Pt MAE: {metrics_by_model[best_name]['cv_pt_mae_mean']:.2f} +/- {metrics_by_model[best_name]['cv_pt_mae_std']:.2f} kips",
        f"- Pt R2: {metrics_by_model[best_name]['cv_pt_r2_mean']:.3f}",
        f"- Max. Displacement MAE: {metrics_by_model[best_name]['cv_max_displacement_mae_mean']:.5f}",
        f"- Max. Force MAE: {metrics_by_model[best_name]['cv_max_force_mae_mean']:.2f}",
        f"- Normalized curve RMSE: {metrics['curve_cv_norm_rmse_mean']:.4f}",
        f"- u3 Type accuracy: {metrics['type_accuracy_mean']:.3f}",
        f"- u3 Type macro F1: {metrics['type_macro_f1_mean']:.3f}",
        "",
        "## GointMLP Forecast",
        f"- Pt MAE: {goint_metrics['cv_pt_mae_mean']:.2f} +/- {goint_metrics['cv_pt_mae_std']:.2f} kips",
        f"- Pt R2: {goint_metrics['cv_pt_r2_mean']:.3f}",
        f"- Max. Displacement MAE: {goint_metrics['cv_max_displacement_mae_mean']:.5f}",
        f"- Max. Force MAE: {goint_metrics['cv_max_force_mae_mean']:.2f}",
        f"- Normalized curve RMSE: {goint_metrics['curve_cv_norm_rmse_mean']:.4f}",
        "",
        "## Model Candidates",
    ]
    for name, row in metrics_by_model.items():
        lines.append(
            f"- `{name}`: Pt MAE {row['cv_pt_mae_mean']:.2f}, Pt R2 {row['cv_pt_r2_mean']:.3f}"
        )
    (report_dir / "u3_forecast_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return cast(dict[str, object], metrics)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest", default="/Users/danlee/KyulAI_codex/data/datasets/DD_u3_pt_v2/manifest.csv"
    )
    parser.add_argument(
        "--output-dir", default="/Users/danlee/KyulAI_codex/models/dd_laminate_u3_forecast_v2"
    )
    parser.add_argument(
        "--report-dir", default="/Users/danlee/KyulAI_codex/reports/dd_u3_forecast_v2"
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--splits", type=int, default=5)
    parser.add_argument(
        "--feature-set",
        choices=[
            "theta",
            "theta_physics",
            "theta_physics_v2",
            "theta_physics_canonical_v2",
            "theta_physics_compact_canonical_v2",
        ],
        default="theta",
    )
    args = parser.parse_args()
    metrics = train_forecast(
        manifest=Path(args.manifest),
        output_dir=Path(args.output_dir),
        report_dir=Path(args.report_dir),
        seed=args.seed,
        splits=args.splits,
        feature_set=args.feature_set,
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
