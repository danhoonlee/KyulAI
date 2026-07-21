"""Train a compact distilled Laminate Forecast student from the active Tree teacher."""

from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import torch
import torch.nn.functional as F
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error
from sklearn.model_selection import GroupKFold
from torch.utils.data import DataLoader, Dataset, Subset

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dd_response_physics_xai_train import _fit_tree, make_response_targets
from src.ml.dd_laminate.response_deep import DDResponseGointSurrogate, ordinal_targets, predict_from_logits
from src.ml.dd_laminate.response_feature_sets import ResponseFeatureRecord, response_feature_matrix
from src.ml.dd_laminate.train_cases_2_3_4_classical import CASES
from src.ml.dd_laminate.train_cases_2_3_4_classical import load_records
from src.ml.dd_laminate.train_cases_2_3_4_goint import normalize


METRIC_KEYS = (
    "accuracy",
    "macro_f1",
    "teacher_agreement",
    "pt_mae",
    "teacher_pt_mae",
    "max_displacement_mae",
    "max_force_mae",
    "curve_norm_rmse",
    "teacher_curve_norm_rmse",
    "curve_force_rmse",
)


class DistillationDataset(Dataset):
    def __init__(
        self,
        x: np.ndarray,
        y_class: np.ndarray,
        y_scalars_norm: np.ndarray,
        y_curve: np.ndarray,
        teacher_probs: np.ndarray,
        teacher_scalars_norm: np.ndarray,
        teacher_curve: np.ndarray,
        sample_weight: np.ndarray | None = None,
    ):
        self.x = torch.tensor(x, dtype=torch.float32)
        self.y_class = torch.tensor(y_class - 1, dtype=torch.long)
        self.y_scalars_norm = torch.tensor(y_scalars_norm, dtype=torch.float32)
        self.y_curve = torch.tensor(y_curve, dtype=torch.float32)
        self.teacher_probs = torch.tensor(teacher_probs, dtype=torch.float32)
        self.teacher_scalars_norm = torch.tensor(teacher_scalars_norm, dtype=torch.float32)
        self.teacher_curve = torch.tensor(teacher_curve, dtype=torch.float32)
        if sample_weight is None:
            sample_weight = np.ones(len(y_class), dtype=float)
        self.sample_weight = torch.tensor(sample_weight, dtype=torch.float32)

    def __len__(self) -> int:
        return len(self.y_class)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        return {
            "x": self.x[idx],
            "label": self.y_class[idx],
            "scalars": self.y_scalars_norm[idx],
            "curve": self.y_curve[idx],
            "teacher_probs": self.teacher_probs[idx],
            "teacher_scalars": self.teacher_scalars_norm[idx],
            "teacher_curve": self.teacher_curve[idx],
            "sample_weight": self.sample_weight[idx],
        }


@dataclass(frozen=True)
class DistillationArrays:
    x_norm: np.ndarray
    y_class: np.ndarray
    y_scalars_norm: np.ndarray
    y_curve: np.ndarray
    teacher_probs: np.ndarray
    teacher_scalars_norm: np.ndarray
    teacher_curve: np.ndarray
    sample_weight: np.ndarray


@dataclass(frozen=True)
class SyntheticRawArrays:
    x_raw: np.ndarray
    y_class: np.ndarray
    y_scalars: np.ndarray
    y_curve: np.ndarray
    teacher_probs: np.ndarray
    sample_weight: np.ndarray
    records: list[ResponseFeatureRecord]


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def parse_panel_sizes(value: str) -> list[tuple[float, float]]:
    sizes: list[tuple[float, float]] = []
    for chunk in value.split(","):
        token = chunk.strip().lower().replace(" ", "")
        if not token:
            continue
        if "x" not in token:
            raise ValueError(f"Invalid panel size {chunk!r}; expected format like 6x4 or 6x8.")
        a_text, b_text = token.split("x", 1)
        sizes.append((float(a_text), float(b_text)))
    if not sizes:
        raise ValueError("At least one synthetic panel size is required.")
    return sizes


def resolve_device(device: str) -> torch.device:
    if device == "auto":
        if torch.cuda.is_available():
            return torch.device("cuda")
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")
    requested = torch.device(device)
    if requested.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested, but PyTorch cannot see a CUDA-capable GPU.")
    if requested.type == "mps" and (not hasattr(torch.backends, "mps") or not torch.backends.mps.is_available()):
        raise RuntimeError("MPS was requested, but PyTorch MPS is not available on this machine.")
    return requested


def describe_device(device: torch.device) -> str:
    if device.type == "cuda":
        name = torch.cuda.get_device_name(device)
        capability = torch.cuda.get_device_capability(device)
        return f"cuda ({name}, compute capability {capability[0]}.{capability[1]})"
    if device.type == "mps":
        return "mps (Apple Metal Performance Shaders)"
    return "cpu"


def make_model(input_dim: int, seq_len: int, args) -> DDResponseGointSurrogate:
    return DDResponseGointSurrogate(
        input_dim=input_dim,
        seq_len=seq_len,
        hidden_dim=args.hidden_dim,
        num_branches=args.branches,
        dropout=args.dropout,
    ).to(args.device_torch)


def _pin_memory(args) -> bool:
    if args.pin_memory == "on":
        return True
    if args.pin_memory == "off":
        return False
    return args.device_torch.type == "cuda"


def _loader(dataset, args, *, shuffle: bool) -> DataLoader:
    kwargs = {
        "batch_size": args.batch_size,
        "shuffle": shuffle,
        "num_workers": args.num_workers,
        "pin_memory": _pin_memory(args),
    }
    if args.num_workers > 0:
        kwargs["persistent_workers"] = True
        kwargs["prefetch_factor"] = args.prefetch_factor
    return DataLoader(dataset, **kwargs)


def teacher_predictions(teacher: dict, x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    classifier = teacher["classifier"]
    scalar_model = teacher["scalar_model"]
    pca = teacher["pca"]
    curve_model = teacher["curve_model"]

    probs = np.zeros((len(x), 3), dtype=float)
    raw_probs = classifier.predict_proba(x)
    for source_col, cls in enumerate(classifier.classes_):
        probs[:, int(cls) - 1] = raw_probs[:, source_col]
    scalars = np.asarray(scalar_model.predict(x), dtype=float)
    curve = np.clip(pca.inverse_transform(curve_model.predict(x)), 0.0, None)
    return probs, scalars, curve


def tree_bundle_from_parts(classifier, scalar_model, pca, curve_model) -> dict:
    return {
        "classifier": classifier,
        "scalar_model": scalar_model,
        "pca": pca,
        "curve_model": curve_model,
    }


def denormalize_scalars(values_norm: np.ndarray, scalar_mean: np.ndarray, scalar_std: np.ndarray) -> np.ndarray:
    return np.expm1(values_norm * scalar_std + scalar_mean)


def run_epoch(
    model: DDResponseGointSurrogate,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer | None,
    args,
) -> dict[str, np.ndarray | float]:
    train = optimizer is not None
    model.train(mode=train)
    y_true: list[np.ndarray] = []
    y_pred: list[np.ndarray] = []
    teacher_pred: list[np.ndarray] = []
    scalar_pred: list[np.ndarray] = []
    scalar_true: list[np.ndarray] = []
    scalar_teacher: list[np.ndarray] = []
    curve_pred: list[np.ndarray] = []
    curve_true: list[np.ndarray] = []
    curve_teacher: list[np.ndarray] = []
    total_loss = 0.0
    total_n = 0
    non_blocking = bool(getattr(args, "non_blocking", False))

    with torch.set_grad_enabled(train):
        for batch in loader:
            x = batch["x"].to(args.device_torch, non_blocking=non_blocking)
            labels = batch["label"].to(args.device_torch, non_blocking=non_blocking)
            scalars = batch["scalars"].to(args.device_torch, non_blocking=non_blocking)
            curve = batch["curve"].to(args.device_torch, non_blocking=non_blocking)
            teacher_probs = batch["teacher_probs"].to(args.device_torch, non_blocking=non_blocking)
            teacher_scalars = batch["teacher_scalars"].to(args.device_torch, non_blocking=non_blocking)
            teacher_curve = batch["teacher_curve"].to(args.device_torch, non_blocking=non_blocking)
            sample_weight = batch["sample_weight"].to(args.device_torch, non_blocking=non_blocking)

            if train:
                optimizer.zero_grad(set_to_none=True)

            class_logits, ordinal_logits, pred_scalars, pred_curve = model(x)
            hard_class_loss = F.cross_entropy(class_logits, labels, reduction="none")
            temperature = args.temperature
            soft_class_loss = F.kl_div(
                F.log_softmax(class_logits / temperature, dim=1),
                torch.clamp(teacher_probs, min=1e-7),
                reduction="none",
            ).sum(dim=1) * (temperature**2)
            ordinal_loss = F.binary_cross_entropy_with_logits(ordinal_logits, ordinal_targets(labels), reduction="none").mean(dim=1)
            hard_scalar_loss = F.smooth_l1_loss(pred_scalars, scalars, reduction="none").mean(dim=1)
            soft_scalar_loss = F.smooth_l1_loss(pred_scalars, teacher_scalars, reduction="none").mean(dim=1)
            hard_curve_loss = F.smooth_l1_loss(pred_curve, curve, reduction="none").mean(dim=1)
            soft_curve_loss = F.smooth_l1_loss(pred_curve, teacher_curve, reduction="none").mean(dim=1)
            per_sample_loss = (
                args.hard_class_weight * hard_class_loss
                + args.soft_class_weight * soft_class_loss
                + args.ordinal_weight * ordinal_loss
                + args.hard_scalar_weight * hard_scalar_loss
                + args.soft_scalar_weight * soft_scalar_loss
                + args.hard_curve_weight * hard_curve_loss
                + args.soft_curve_weight * soft_curve_loss
            )
            loss = (per_sample_loss * sample_weight).sum() / torch.clamp(sample_weight.sum(), min=1e-6)

            if train:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), args.clip_grad)
                optimizer.step()

            pred = predict_from_logits(class_logits)
            total_loss += float(loss.detach().cpu()) * labels.numel()
            total_n += labels.numel()
            y_true.append(labels.detach().cpu().numpy())
            y_pred.append(pred.detach().cpu().numpy())
            teacher_pred.append(torch.argmax(teacher_probs, dim=1).detach().cpu().numpy())
            scalar_pred.append(pred_scalars.detach().cpu().numpy())
            scalar_true.append(scalars.detach().cpu().numpy())
            scalar_teacher.append(teacher_scalars.detach().cpu().numpy())
            curve_pred.append(pred_curve.detach().cpu().numpy())
            curve_true.append(curve.detach().cpu().numpy())
            curve_teacher.append(teacher_curve.detach().cpu().numpy())

    return {
        "loss": total_loss / max(1, total_n),
        "y_true": np.concatenate(y_true),
        "y_pred": np.concatenate(y_pred),
        "teacher_pred": np.concatenate(teacher_pred),
        "scalar_pred_norm": np.concatenate(scalar_pred),
        "scalar_true_norm": np.concatenate(scalar_true),
        "scalar_teacher_norm": np.concatenate(scalar_teacher),
        "curve_pred": np.concatenate(curve_pred),
        "curve_true": np.concatenate(curve_true),
        "curve_teacher": np.concatenate(curve_teacher),
    }


def metric_row(out: dict[str, np.ndarray | float], scalar_mean: np.ndarray, scalar_std: np.ndarray) -> dict[str, float]:
    y_true = np.asarray(out["y_true"], dtype=int)
    y_pred = np.asarray(out["y_pred"], dtype=int)
    teacher_pred = np.asarray(out["teacher_pred"], dtype=int)
    pred_scalars = denormalize_scalars(np.asarray(out["scalar_pred_norm"]), scalar_mean, scalar_std)
    true_scalars = denormalize_scalars(np.asarray(out["scalar_true_norm"]), scalar_mean, scalar_std)
    teacher_scalars = denormalize_scalars(np.asarray(out["scalar_teacher_norm"]), scalar_mean, scalar_std)
    pred_curve = np.clip(np.asarray(out["curve_pred"]), 0.0, None)
    true_curve = np.asarray(out["curve_true"])
    teacher_curve = np.asarray(out["curve_teacher"])
    pred_force = pred_curve * np.maximum(pred_scalars[:, 2:3], 1e-9)
    true_force = true_curve * np.maximum(true_scalars[:, 2:3], 1e-9)
    return {
        "loss": float(out["loss"]),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "teacher_agreement": float(np.mean(y_pred == teacher_pred)),
        "pt_mae": float(mean_absolute_error(true_scalars[:, 0], pred_scalars[:, 0])),
        "teacher_pt_mae": float(mean_absolute_error(teacher_scalars[:, 0], pred_scalars[:, 0])),
        "max_displacement_mae": float(mean_absolute_error(true_scalars[:, 1], pred_scalars[:, 1])),
        "max_force_mae": float(mean_absolute_error(true_scalars[:, 2], pred_scalars[:, 2])),
        "curve_norm_rmse": float(np.sqrt(np.mean((pred_curve - true_curve) ** 2))),
        "teacher_curve_norm_rmse": float(np.sqrt(np.mean((pred_curve - teacher_curve) ** 2))),
        "curve_force_rmse": float(np.sqrt(np.mean((pred_force - true_force) ** 2))),
    }


def train_cv(
    x_norm: np.ndarray,
    y_class: np.ndarray,
    y_scalars_norm: np.ndarray,
    y_curve: np.ndarray,
    teacher_probs: np.ndarray,
    teacher_scalars_norm: np.ndarray,
    teacher_curve: np.ndarray,
    groups: np.ndarray,
    scalar_mean: np.ndarray,
    scalar_std: np.ndarray,
    args,
    synthetic: DistillationArrays | None = None,
) -> list[dict[str, float]]:
    real_dataset = DistillationDataset(
        x_norm,
        y_class,
        y_scalars_norm,
        y_curve,
        teacher_probs,
        teacher_scalars_norm,
        teacher_curve,
        np.ones(len(y_class), dtype=float),
    )
    rows: list[dict[str, float]] = []
    splitter = GroupKFold(n_splits=args.splits)
    for fold, (train_idx, val_idx) in enumerate(splitter.split(x_norm, y_class, groups), start=1):
        if synthetic is None or len(synthetic.y_class) == 0:
            train_dataset = Subset(real_dataset, train_idx.tolist())
        else:
            train_dataset = DistillationDataset(
                np.concatenate([x_norm[train_idx], synthetic.x_norm], axis=0),
                np.concatenate([y_class[train_idx], synthetic.y_class], axis=0),
                np.concatenate([y_scalars_norm[train_idx], synthetic.y_scalars_norm], axis=0),
                np.concatenate([y_curve[train_idx], synthetic.y_curve], axis=0),
                np.concatenate([teacher_probs[train_idx], synthetic.teacher_probs], axis=0),
                np.concatenate([teacher_scalars_norm[train_idx], synthetic.teacher_scalars_norm], axis=0),
                np.concatenate([teacher_curve[train_idx], synthetic.teacher_curve], axis=0),
                np.concatenate([np.ones(len(train_idx), dtype=float), synthetic.sample_weight], axis=0),
            )
        train_loader = _loader(train_dataset, args, shuffle=True)
        val_loader = _loader(Subset(real_dataset, val_idx.tolist()), args, shuffle=False)
        model = make_model(x_norm.shape[1], y_curve.shape[1], args)
        optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
        best_state = None
        best_score = -1e9
        best_epoch = 0
        stale = 0
        for epoch in range(1, args.epochs + 1):
            run_epoch(model, train_loader, optimizer, args)
            out = run_epoch(model, val_loader, None, args)
            row = metric_row(out, scalar_mean, scalar_std)
            score = row["macro_f1"] - args.pt_score_weight * (row["pt_mae"] / 1000.0) - args.curve_score_weight * row["curve_norm_rmse"]
            if score > best_score:
                best_score = score
                best_epoch = epoch
                best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
                stale = 0
            else:
                stale += 1
            if stale >= args.patience:
                break
        if best_state is not None:
            model.load_state_dict(best_state)
        row = metric_row(run_epoch(model, val_loader, None, args), scalar_mean, scalar_std)
        row["fold"] = float(fold)
        row["best_epoch"] = float(best_epoch)
        rows.append(row)
        print(
            f"fold {fold}: acc={row['accuracy']:.4f}, f1={row['macro_f1']:.4f}, "
            f"pt_mae={row['pt_mae']:.2f}, teacher_agree={row['teacher_agreement']:.4f}"
        )
    return rows


def make_synthetic_raw_arrays(
    *,
    teacher: dict,
    feature_set: str,
    panel_sizes: list[tuple[float, float]],
    theta_min: float,
    theta_max: float,
    grid_step: float,
    synthetic_weight: float,
    confidence_power: float,
    min_confidence_weight: float,
) -> SyntheticRawArrays | None:
    if not grid_step or grid_step <= 0:
        return None
    theta_values = np.arange(theta_min, theta_max + 1e-9, grid_step, dtype=float)
    synthetic_records = [
        ResponseFeatureRecord(case=case, theta1=float(theta1), theta2=float(theta2), panel_a_in=panel_a, panel_b_in=panel_b)
        for panel_a, panel_b in panel_sizes
        for case in CASES
        for theta1 in theta_values
        for theta2 in theta_values
    ]
    x_synth_raw, _ = response_feature_matrix(synthetic_records, feature_set)
    synth_probs, synth_scalars, synth_curve = teacher_predictions(teacher, x_synth_raw)
    synth_class = np.argmax(synth_probs, axis=1).astype(int) + 1
    synth_confidence = np.max(synth_probs, axis=1)
    if confidence_power > 0:
        confidence_multiplier = np.clip(
            synth_confidence ** float(confidence_power),
            float(min_confidence_weight),
            1.0,
        )
    else:
        confidence_multiplier = np.ones_like(synth_confidence)
    synth_weight = float(synthetic_weight) * confidence_multiplier
    return SyntheticRawArrays(
        x_raw=x_synth_raw,
        y_class=synth_class,
        y_scalars=synth_scalars,
        y_curve=synth_curve,
        teacher_probs=synth_probs,
        sample_weight=synth_weight.astype(float),
        records=synthetic_records,
    )


def synthetic_exclusion_mask(
    synthetic_records: list[ResponseFeatureRecord],
    val_records: list,
    *,
    radius: float,
) -> np.ndarray:
    if radius < 0:
        return np.ones(len(synthetic_records), dtype=bool)
    val_by_case: dict[str, list[tuple[float, float]]] = {}
    for record in val_records:
        val_by_case.setdefault(record.case, []).append((float(record.theta1), float(record.theta2)))
    keep = np.ones(len(synthetic_records), dtype=bool)
    for idx, record in enumerate(synthetic_records):
        for theta1, theta2 in val_by_case.get(record.case, []):
            if max(abs(float(record.theta1) - theta1), abs(float(record.theta2) - theta2)) <= radius:
                keep[idx] = False
                break
    return keep


def train_strict_cv(
    records,
    x_raw: np.ndarray,
    y_class: np.ndarray,
    y_scalars: np.ndarray,
    y_curve: np.ndarray,
    args,
) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    groups = np.asarray([f"{record.theta1}:{record.theta2}" for record in records])
    splitter = GroupKFold(n_splits=args.splits)
    for fold, (train_idx, val_idx) in enumerate(splitter.split(x_raw, y_class, groups), start=1):
        fold_teacher = tree_bundle_from_parts(
            *_fit_tree(
                x_raw[train_idx],
                y_class[train_idx],
                y_scalars[train_idx],
                y_curve[train_idx],
                args.teacher_n_components,
                args.seed + fold * 101,
                args.tree_n_jobs,
            )
        )
        feature_mean = np.mean(x_raw[train_idx], axis=0)
        feature_std = np.std(x_raw[train_idx], axis=0)
        feature_std = np.where(feature_std < 1e-9, 1.0, feature_std)
        scalar_log_train = np.log1p(y_scalars[train_idx])
        scalar_mean = np.mean(scalar_log_train, axis=0)
        scalar_std = np.std(scalar_log_train, axis=0)
        scalar_std = np.where(scalar_std < 1e-9, 1.0, scalar_std)

        train_teacher_probs, train_teacher_scalars, train_teacher_curve = teacher_predictions(fold_teacher, x_raw[train_idx])
        val_teacher_probs, val_teacher_scalars, val_teacher_curve = teacher_predictions(fold_teacher, x_raw[val_idx])

        train_x_norm = (x_raw[train_idx] - feature_mean) / feature_std
        val_x_norm = (x_raw[val_idx] - feature_mean) / feature_std
        train_scalars_norm = (np.log1p(y_scalars[train_idx]) - scalar_mean) / scalar_std
        val_scalars_norm = (np.log1p(y_scalars[val_idx]) - scalar_mean) / scalar_std
        train_teacher_scalars_norm = (np.log1p(np.clip(train_teacher_scalars, 0.0, None)) - scalar_mean) / scalar_std
        val_teacher_scalars_norm = (np.log1p(np.clip(val_teacher_scalars, 0.0, None)) - scalar_mean) / scalar_std

        synthetic: DistillationArrays | None = None
        synthetic_count_total = 0
        synthetic_count_kept = 0
        if args.synthetic_grid_step and args.synthetic_grid_step > 0:
            synthetic_raw = make_synthetic_raw_arrays(
                teacher=fold_teacher,
                feature_set=args.feature_set,
                panel_sizes=args.synthetic_panel_size_values,
                theta_min=args.synthetic_theta_min,
                theta_max=args.synthetic_theta_max,
                grid_step=args.synthetic_grid_step,
                synthetic_weight=args.synthetic_weight,
                confidence_power=args.synthetic_confidence_power,
                min_confidence_weight=args.synthetic_min_confidence_weight,
            )
            if synthetic_raw is not None:
                synthetic_count_total = len(synthetic_raw.y_class)
                keep = synthetic_exclusion_mask(
                    synthetic_raw.records,
                    [records[int(i)] for i in val_idx],
                    radius=args.strict_synthetic_exclusion_radius,
                )
                synthetic_count_kept = int(np.sum(keep))
                if synthetic_count_kept:
                    synth_scalars_norm = (np.log1p(np.clip(synthetic_raw.y_scalars[keep], 0.0, None)) - scalar_mean) / scalar_std
                    synthetic = DistillationArrays(
                        x_norm=(synthetic_raw.x_raw[keep] - feature_mean) / feature_std,
                        y_class=synthetic_raw.y_class[keep],
                        y_scalars_norm=synth_scalars_norm,
                        y_curve=synthetic_raw.y_curve[keep],
                        teacher_probs=synthetic_raw.teacher_probs[keep],
                        teacher_scalars_norm=synth_scalars_norm,
                        teacher_curve=synthetic_raw.y_curve[keep],
                        sample_weight=synthetic_raw.sample_weight[keep],
                    )

        real_train = DistillationDataset(
            train_x_norm,
            y_class[train_idx],
            train_scalars_norm,
            y_curve[train_idx],
            train_teacher_probs,
            train_teacher_scalars_norm,
            train_teacher_curve,
            np.ones(len(train_idx), dtype=float),
        )
        if synthetic is not None and len(synthetic.y_class) > 0:
            train_dataset = DistillationDataset(
                np.concatenate([train_x_norm, synthetic.x_norm], axis=0),
                np.concatenate([y_class[train_idx], synthetic.y_class], axis=0),
                np.concatenate([train_scalars_norm, synthetic.y_scalars_norm], axis=0),
                np.concatenate([y_curve[train_idx], synthetic.y_curve], axis=0),
                np.concatenate([train_teacher_probs, synthetic.teacher_probs], axis=0),
                np.concatenate([train_teacher_scalars_norm, synthetic.teacher_scalars_norm], axis=0),
                np.concatenate([train_teacher_curve, synthetic.teacher_curve], axis=0),
                np.concatenate([np.ones(len(train_idx), dtype=float), synthetic.sample_weight], axis=0),
            )
        else:
            train_dataset = real_train
        val_dataset = DistillationDataset(
            val_x_norm,
            y_class[val_idx],
            val_scalars_norm,
            y_curve[val_idx],
            val_teacher_probs,
            val_teacher_scalars_norm,
            val_teacher_curve,
            np.ones(len(val_idx), dtype=float),
        )

        train_loader = _loader(train_dataset, args, shuffle=True)
        val_loader = _loader(val_dataset, args, shuffle=False)
        model = make_model(x_raw.shape[1], y_curve.shape[1], args)
        optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
        best_state = None
        best_score = -1e9
        best_epoch = 0
        stale = 0
        for epoch in range(1, args.epochs + 1):
            run_epoch(model, train_loader, optimizer, args)
            out = run_epoch(model, val_loader, None, args)
            row = metric_row(out, scalar_mean, scalar_std)
            score = row["macro_f1"] - args.pt_score_weight * (row["pt_mae"] / 1000.0) - args.curve_score_weight * row["curve_norm_rmse"]
            if score > best_score:
                best_score = score
                best_epoch = epoch
                best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
                stale = 0
            else:
                stale += 1
            if stale >= args.patience:
                break
        if best_state is not None:
            model.load_state_dict(best_state)
        row = metric_row(run_epoch(model, val_loader, None, args), scalar_mean, scalar_std)
        row["fold"] = float(fold)
        row["best_epoch"] = float(best_epoch)
        row["synthetic_total"] = float(synthetic_count_total)
        row["synthetic_kept"] = float(synthetic_count_kept)
        rows.append(row)
        print(
            f"strict fold {fold}: acc={row['accuracy']:.4f}, f1={row['macro_f1']:.4f}, "
            f"pt_mae={row['pt_mae']:.2f}, teacher_agree={row['teacher_agreement']:.4f}, "
            f"synthetic_kept={synthetic_count_kept}/{synthetic_count_total}"
        )
    return rows


def train_final(
    x_norm: np.ndarray,
    y_class: np.ndarray,
    y_scalars_norm: np.ndarray,
    y_curve: np.ndarray,
    teacher_probs: np.ndarray,
    teacher_scalars_norm: np.ndarray,
    teacher_curve: np.ndarray,
    args,
    synthetic: DistillationArrays | None = None,
) -> DDResponseGointSurrogate:
    if synthetic is not None and len(synthetic.y_class) > 0:
        x_norm = np.concatenate([x_norm, synthetic.x_norm], axis=0)
        y_class = np.concatenate([y_class, synthetic.y_class], axis=0)
        y_scalars_norm = np.concatenate([y_scalars_norm, synthetic.y_scalars_norm], axis=0)
        y_curve = np.concatenate([y_curve, synthetic.y_curve], axis=0)
        teacher_probs = np.concatenate([teacher_probs, synthetic.teacher_probs], axis=0)
        teacher_scalars_norm = np.concatenate([teacher_scalars_norm, synthetic.teacher_scalars_norm], axis=0)
        teacher_curve = np.concatenate([teacher_curve, synthetic.teacher_curve], axis=0)
        sample_weight = np.concatenate([np.ones(len(y_class) - len(synthetic.y_class), dtype=float), synthetic.sample_weight], axis=0)
    else:
        sample_weight = np.ones(len(y_class), dtype=float)
    dataset = DistillationDataset(
        x_norm,
        y_class,
        y_scalars_norm,
        y_curve,
        teacher_probs,
        teacher_scalars_norm,
        teacher_curve,
        sample_weight,
    )
    loader = _loader(dataset, args, shuffle=True)
    model = make_model(x_norm.shape[1], y_curve.shape[1], args)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    for epoch in range(1, args.final_epochs + 1):
        out = run_epoch(model, loader, optimizer, args)
        if epoch == 1 or epoch % 50 == 0 or epoch == args.final_epochs:
            print(f"final epoch {epoch}: loss={out['loss']:.5f}")
    return model


def summarize_metrics(rows: list[dict[str, float]], *, n_samples: int, input_dim: int, seq_len: int, args) -> dict[str, float | int | str]:
    metrics: dict[str, float | int | str] = {
        "model_name": str(args.model_name),
        "teacher_model": str(args.teacher_model),
        "n_samples": int(n_samples),
        "n_synthetic_samples": int(getattr(args, "n_synthetic_samples", 0)),
        "input_dim": int(input_dim),
        "seq_len": int(seq_len),
        "feature_builder": args.feature_set,
        "hidden_dim": int(args.hidden_dim),
        "branches": int(args.branches),
        "dropout": float(args.dropout),
        "temperature": float(args.temperature),
        "synthetic_grid_step": float(args.synthetic_grid_step),
        "synthetic_panel_sizes": str(args.synthetic_panel_sizes),
        "synthetic_weight": float(args.synthetic_weight),
        "synthetic_confidence_power": float(args.synthetic_confidence_power),
        "synthetic_min_confidence_weight": float(args.synthetic_min_confidence_weight),
        "synthetic_effective_weight_mean": float(getattr(args, "synthetic_effective_weight_mean", 0.0)),
        "synthetic_teacher_confidence_mean": float(getattr(args, "synthetic_teacher_confidence_mean", 0.0)),
        "strict_cv": bool(args.strict_cv),
        "strict_cv_only": bool(args.strict_cv_only),
        "strict_synthetic_exclusion_radius": float(args.strict_synthetic_exclusion_radius),
        "teacher_n_components": int(args.teacher_n_components),
    }
    for key in METRIC_KEYS:
        values = [row[key] for row in rows]
        metrics[f"cv_{key}_mean"] = float(np.mean(values))
        metrics[f"cv_{key}_std"] = float(np.std(values))
    return metrics


def write_report(output_dir: Path, metrics: dict[str, float | int | str], fold_rows: list[dict[str, float]]) -> None:
    title = (
        "Laminate Forecast Synthetic Grid Distillation"
        if int(metrics.get("n_synthetic_samples", 0)) > 0
        else "Laminate Forecast Distillation"
    )
    lines = [
        f"# {title}",
        "",
        "Student model distilled from the active Tree + Physics ABD teacher.",
        "",
        "## Teacher",
        "",
        f"- `{metrics['teacher_model']}`",
        "",
        "## Student",
        "",
        f"- Samples: {metrics['n_samples']}",
        f"- Synthetic samples: {metrics['n_synthetic_samples']}",
        f"- Input features: {metrics['input_dim']}",
        f"- Sequence length: {metrics['seq_len']}",
        f"- Hidden dim: {metrics['hidden_dim']}",
        f"- Branches: {metrics['branches']}",
        f"- Synthetic grid step: {metrics['synthetic_grid_step']}",
        f"- Synthetic panel sizes: `{metrics.get('synthetic_panel_sizes', '6x4')}`",
        f"- Synthetic base weight: {metrics['synthetic_weight']}",
        f"- Synthetic confidence power: {metrics['synthetic_confidence_power']}",
        f"- Synthetic effective weight mean: {metrics['synthetic_effective_weight_mean']:.4f}",
        f"- Synthetic teacher confidence mean: {metrics['synthetic_teacher_confidence_mean']:.4f}",
        f"- Strict CV: {metrics['strict_cv']}",
        f"- Strict synthetic exclusion radius: {metrics['strict_synthetic_exclusion_radius']}",
        f"- Fold-local teacher PCA components: {metrics['teacher_n_components']}",
        "",
    ]
    if "cv_accuracy_mean" in metrics:
        lines.extend(
            [
                "## Cross-validation",
                "",
                f"- Type accuracy: {metrics['cv_accuracy_mean']:.4f} +/- {metrics['cv_accuracy_std']:.4f}",
                f"- Macro F1: {metrics['cv_macro_f1_mean']:.4f} +/- {metrics['cv_macro_f1_std']:.4f}",
                f"- Teacher Type agreement: {metrics['cv_teacher_agreement_mean']:.4f}",
                f"- Pt MAE vs ground truth: {metrics['cv_pt_mae_mean']:.2f} kips",
                f"- Pt MAE vs teacher: {metrics['cv_teacher_pt_mae_mean']:.2f} kips",
                f"- Curve normalized RMSE vs ground truth: {metrics['cv_curve_norm_rmse_mean']:.5f}",
                f"- Curve normalized RMSE vs teacher: {metrics['cv_teacher_curve_norm_rmse_mean']:.5f}",
                "",
                "## Interpretation",
                "",
                "Strict CV uses fold-local teachers and removes synthetic grid points near validation inputs when enabled. "
                "This gives a more conservative performance estimate than the optimistic deployment-style distillation run, "
                "where the final teacher is trained on all available data.",
            ]
        )
    else:
        lines.extend(
            [
                "## Cross-validation",
                "",
                "- Not included in this final-only artifact. Pass `--reference-metrics` to attach a validation report.",
            ]
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "distillation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output_dir / "response_distilled_metrics.json").write_text(
        json.dumps({"metrics": metrics, "fold_metrics": fold_rows}, indent=2),
        encoding="utf-8",
    )


def load_reference_metrics(path: str | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not path:
        return {}, []
    report_path = Path(path)
    if not report_path.exists():
        raise FileNotFoundError(report_path)
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    return dict(payload.get("metrics", {})), list(payload.get("fold_metrics", []))


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Laminate Forecast Distillation")
    parser.add_argument("--data-dir", default="data/datasets/DD_cases_2_3_4_curated_v1")
    parser.add_argument("--teacher-model", default="models/dd_laminate_response_physics_abd_v1/response_surrogate.joblib")
    parser.add_argument("--output-dir", default="models/dd_laminate_response_distilled_v1")
    parser.add_argument("--model-name", default="laminate_forecast_distilled_student_v1")
    parser.add_argument(
        "--feature-set",
        default="theta_physics_v2",
        choices=["theta", "theta_physics", "theta_physics_v2", "theta_physics_nn_v2", "theta_physics_geometry_v1"],
    )
    parser.add_argument("--splits", type=int, default=5)
    parser.add_argument("--epochs", type=int, default=220)
    parser.add_argument("--final-epochs", type=int, default=180)
    parser.add_argument("--patience", type=int, default=36)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--prefetch-factor", type=int, default=2)
    parser.add_argument("--pin-memory", choices=["auto", "on", "off"], default="auto")
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--branches", type=int, default=6)
    parser.add_argument("--dropout", type=float, default=0.10)
    parser.add_argument("--lr", type=float, default=7e-4)
    parser.add_argument("--weight-decay", type=float, default=8e-4)
    parser.add_argument("--temperature", type=float, default=2.5)
    parser.add_argument("--hard-class-weight", type=float, default=0.45)
    parser.add_argument("--soft-class-weight", type=float, default=0.75)
    parser.add_argument("--ordinal-weight", type=float, default=0.12)
    parser.add_argument("--hard-scalar-weight", type=float, default=0.28)
    parser.add_argument("--soft-scalar-weight", type=float, default=0.55)
    parser.add_argument("--hard-curve-weight", type=float, default=0.18)
    parser.add_argument("--soft-curve-weight", type=float, default=0.38)
    parser.add_argument("--pt-score-weight", type=float, default=0.015)
    parser.add_argument("--curve-score-weight", type=float, default=0.6)
    parser.add_argument("--clip-grad", type=float, default=3.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=["auto", "cpu", "mps", "cuda"], default="auto")
    parser.add_argument("--tree-n-jobs", type=int, default=-1)
    parser.add_argument("--strict-cv", action="store_true", help="Use fold-local teachers and remove validation-near synthetic points from each fold.")
    parser.add_argument("--strict-cv-only", action="store_true", help="Run strict CV/report only and skip final deployment model training.")
    parser.add_argument("--final-only", action="store_true", help="Skip CV and train only the final deployment artifact.")
    parser.add_argument("--reference-metrics", default="", help="Optional metrics JSON to copy into a final-only deployment artifact/report.")
    parser.add_argument("--strict-synthetic-exclusion-radius", type=float, default=0.0, help="Chebyshev theta radius around validation case/theta points to remove from synthetic fold training.")
    parser.add_argument("--teacher-n-components", type=int, default=18)
    parser.add_argument("--synthetic-grid-step", type=float, default=0.0, help="Theta grid step in degrees. Use 0 to disable synthetic grid distillation.")
    parser.add_argument("--synthetic-theta-min", type=float, default=-90.0)
    parser.add_argument("--synthetic-theta-max", type=float, default=90.0)
    parser.add_argument(
        "--synthetic-panel-sizes",
        default="6x4",
        help="Comma-separated panel sizes for synthetic grid records, e.g. '6x4' or '6x4,6x8'.",
    )
    parser.add_argument("--synthetic-weight", type=float, default=0.35)
    parser.add_argument(
        "--synthetic-confidence-power",
        type=float,
        default=0.0,
        help="Raise teacher max probability to this power when weighting synthetic samples. 0 keeps uniform synthetic weights.",
    )
    parser.add_argument(
        "--synthetic-min-confidence-weight",
        type=float,
        default=0.35,
        help="Lower bound multiplier for confidence-weighted synthetic samples.",
    )
    args = parser.parse_args()
    args.device_torch = resolve_device(args.device)
    args.synthetic_panel_size_values = parse_panel_sizes(args.synthetic_panel_sizes)
    args.non_blocking = _pin_memory(args)
    print(f"Using device: {describe_device(args.device_torch)}")
    set_seed(args.seed)

    records = load_records(Path(args.data_dir))
    x_raw, feature_names = response_feature_matrix(records, args.feature_set)
    x_norm, feature_mean, feature_std = normalize(x_raw, x_raw)
    y_class = np.asarray([record.label for record in records], dtype=int)
    y_scalars, y_curve, grid = make_response_targets(records, seq_len=128)
    y_scalars_log = np.log1p(y_scalars)
    y_scalars_norm, scalar_mean, scalar_std = normalize(y_scalars_log, y_scalars_log)

    teacher = joblib.load(args.teacher_model)
    teacher_probs, teacher_scalars, teacher_curve = teacher_predictions(teacher, x_raw)
    teacher_scalars_norm = (np.log1p(np.clip(teacher_scalars, 0.0, None)) - scalar_mean) / scalar_std

    synthetic: DistillationArrays | None = None
    args.n_synthetic_samples = 0
    if args.synthetic_grid_step and args.synthetic_grid_step > 0:
        theta_values = np.arange(args.synthetic_theta_min, args.synthetic_theta_max + 1e-9, args.synthetic_grid_step, dtype=float)
        synthetic_records = [
            ResponseFeatureRecord(case=case, theta1=float(theta1), theta2=float(theta2), panel_a_in=panel_a, panel_b_in=panel_b)
            for panel_a, panel_b in args.synthetic_panel_size_values
            for case in CASES
            for theta1 in theta_values
            for theta2 in theta_values
        ]
        x_synth_raw, _ = response_feature_matrix(synthetic_records, args.feature_set)
        synth_probs, synth_scalars, synth_curve = teacher_predictions(teacher, x_synth_raw)
        synth_class = np.argmax(synth_probs, axis=1).astype(int) + 1
        synth_confidence = np.max(synth_probs, axis=1)
        if args.synthetic_confidence_power > 0:
            confidence_multiplier = np.clip(
                synth_confidence ** float(args.synthetic_confidence_power),
                float(args.synthetic_min_confidence_weight),
                1.0,
            )
        else:
            confidence_multiplier = np.ones_like(synth_confidence)
        synth_weight = float(args.synthetic_weight) * confidence_multiplier
        synth_scalars_norm = (np.log1p(np.clip(synth_scalars, 0.0, None)) - scalar_mean) / scalar_std
        synth_x_norm = (x_synth_raw - feature_mean) / np.maximum(feature_std, 1e-9)
        synthetic = DistillationArrays(
            x_norm=synth_x_norm,
            y_class=synth_class,
            y_scalars_norm=synth_scalars_norm,
            y_curve=synth_curve,
            teacher_probs=synth_probs,
            teacher_scalars_norm=synth_scalars_norm,
            teacher_curve=synth_curve,
            sample_weight=synth_weight.astype(float),
        )
        args.n_synthetic_samples = int(len(synth_class))
        args.synthetic_effective_weight_mean = float(np.mean(synth_weight))
        args.synthetic_teacher_confidence_mean = float(np.mean(synth_confidence))
        print(
            f"synthetic grid: {args.n_synthetic_samples} teacher-labeled samples "
            f"({len(theta_values)} theta values x {len(theta_values)} x {len(CASES)} cases, "
            f"base_weight={args.synthetic_weight}, effective_weight_mean={args.synthetic_effective_weight_mean:.4f}, "
            f"teacher_confidence_mean={args.synthetic_teacher_confidence_mean:.4f})"
        )
    else:
        args.synthetic_effective_weight_mean = 0.0
        args.synthetic_teacher_confidence_mean = 0.0

    if args.final_only:
        fold_rows = []
    elif args.strict_cv:
        fold_rows = train_strict_cv(
            records,
            x_raw,
            y_class,
            y_scalars,
            y_curve,
            args,
        )
    else:
        groups = np.asarray([f"{record.theta1}:{record.theta2}" for record in records])
        fold_rows = train_cv(
            x_norm,
            y_class,
            y_scalars_norm,
            y_curve,
            teacher_probs,
            teacher_scalars_norm,
            teacher_curve,
            groups,
            scalar_mean,
            scalar_std,
            args,
            synthetic,
        )
    if args.final_only:
        metrics, fold_rows = load_reference_metrics(args.reference_metrics)
        metrics = {
            **metrics,
            "model_name": args.model_name,
            "teacher_model": str(args.teacher_model),
            "n_samples": int(len(records)),
            "n_synthetic_samples": int(getattr(args, "n_synthetic_samples", 0)),
            "input_dim": int(x_norm.shape[1]),
            "seq_len": int(y_curve.shape[1]),
            "feature_builder": args.feature_set,
            "hidden_dim": int(args.hidden_dim),
            "branches": int(args.branches),
            "dropout": float(args.dropout),
            "temperature": float(args.temperature),
            "synthetic_grid_step": float(args.synthetic_grid_step),
            "synthetic_panel_sizes": str(args.synthetic_panel_sizes),
            "synthetic_weight": float(args.synthetic_weight),
            "synthetic_confidence_power": float(args.synthetic_confidence_power),
            "synthetic_min_confidence_weight": float(args.synthetic_min_confidence_weight),
            "synthetic_effective_weight_mean": float(getattr(args, "synthetic_effective_weight_mean", 0.0)),
            "synthetic_teacher_confidence_mean": float(getattr(args, "synthetic_teacher_confidence_mean", 0.0)),
            "strict_cv": bool(args.strict_cv),
            "strict_cv_only": bool(args.strict_cv_only),
            "strict_synthetic_exclusion_radius": float(args.strict_synthetic_exclusion_radius),
            "teacher_n_components": int(args.teacher_n_components),
            "final_only": True,
            "reference_metrics": args.reference_metrics or None,
        }
    else:
        metrics = summarize_metrics(
            fold_rows,
            n_samples=len(records),
            input_dim=x_norm.shape[1],
            seq_len=y_curve.shape[1],
            args=args,
        )

    output_dir = Path(args.output_dir)
    if args.strict_cv_only:
        output_dir.mkdir(parents=True, exist_ok=True)
        write_report(output_dir, metrics, fold_rows)
        print(json.dumps({"metrics": metrics, "output_dir": str(output_dir), "strict_cv_only": True}, indent=2))
        return

    final_model = train_final(
        x_norm,
        y_class,
        y_scalars_norm,
        y_curve,
        teacher_probs,
        teacher_scalars_norm,
        teacher_curve,
        args,
        synthetic,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": final_model.state_dict(),
            "model_config": {
                "input_dim": int(x_norm.shape[1]),
                "seq_len": int(y_curve.shape[1]),
                "hidden_dim": int(args.hidden_dim),
                "num_branches": int(args.branches),
                "dropout": float(args.dropout),
            },
            "distillation": {
                "teacher_model": str(args.teacher_model),
                "temperature": float(args.temperature),
                "hard_class_weight": float(args.hard_class_weight),
                "soft_class_weight": float(args.soft_class_weight),
                "hard_scalar_weight": float(args.hard_scalar_weight),
                "soft_scalar_weight": float(args.soft_scalar_weight),
                "hard_curve_weight": float(args.hard_curve_weight),
                "soft_curve_weight": float(args.soft_curve_weight),
                "synthetic_grid_step": float(args.synthetic_grid_step),
                "synthetic_weight": float(args.synthetic_weight),
                "synthetic_confidence_power": float(args.synthetic_confidence_power),
                "synthetic_min_confidence_weight": float(args.synthetic_min_confidence_weight),
                "synthetic_effective_weight_mean": float(getattr(args, "synthetic_effective_weight_mean", 0.0)),
            },
            "feature_builder": args.feature_set,
            "feature_columns": feature_names,
            "feature_mean": feature_mean,
            "feature_std": feature_std,
            "scalar_columns": ["pt", "max_displacement", "max_force"],
            "scalar_log_mean": scalar_mean,
            "scalar_log_std": scalar_std,
            "grid": grid,
            "metrics": metrics,
            "fold_metrics": fold_rows,
            "label_names": {0: "Type 1", 1: "Type 2", 2: "Type 3"},
        },
        output_dir / "response_distilled.pt",
    )
    # Save a compatibility filename so existing deep predictor loaders can read this artifact.
    torch.save(torch.load(output_dir / "response_distilled.pt", map_location="cpu", weights_only=False), output_dir / "response_goint.pt")
    write_report(output_dir, metrics, fold_rows)
    print(json.dumps({"metrics": metrics, "output_dir": str(output_dir)}, indent=2))


if __name__ == "__main__":
    main()
