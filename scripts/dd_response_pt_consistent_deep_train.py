#!/usr/bin/env python3
"""Train Pt/P1-consistent GointMLP and distilled Hybrid challengers."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import torch
import torch.nn.functional as F  # noqa: N812
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error
from torch.utils.data import DataLoader, Dataset, TensorDataset

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dd_response_distillation_train import (  # noqa: E402
    parse_panel_sizes,
    resolve_device,
    synthetic_exclusion_mask,
)
from scripts.dd_response_pt_consistent_tree_train import (  # noqa: E402
    make_targets,
    split_indices,
)
from src.ml.dd_laminate.pt_consistent_tree import (  # noqa: E402
    CURVE_REPRESENTATION,
    PT_CONSISTENT_SCALAR_COLUMNS,
    PT_CONSISTENT_SCALAR_TRANSFORMS,
    inverse_transform_pt_consistent_scalars,
    transform_pt_consistent_scalars,
)
from src.ml.dd_laminate.response_deep import (  # noqa: E402
    DDResponseGointSurrogate,
    ordinal_targets,
    predict_from_logits,
)
from src.ml.dd_laminate.response_feature_sets import (  # noqa: E402
    ResponseFeatureRecord,
    response_feature_matrix,
)
from src.ml.dd_laminate.train_cases_2_3_4_classical import (  # noqa: E402
    CASES,
    DDRecord,
    load_records,
)


@dataclass(frozen=True)
class TeacherOutputs:
    probabilities: np.ndarray
    scalars: np.ndarray
    curves: np.ndarray


class PtConsistentDataset(Dataset):
    def __init__(
        self,
        x: np.ndarray,
        labels: np.ndarray,
        scalars: np.ndarray,
        curves: np.ndarray,
        *,
        teacher: TeacherOutputs | None = None,
        sample_weight: np.ndarray | None = None,
    ) -> None:
        self.x = torch.tensor(x, dtype=torch.float32)
        self.labels = torch.tensor(labels - 1, dtype=torch.long)
        self.scalars = torch.tensor(scalars, dtype=torch.float32)
        self.curves = torch.tensor(curves, dtype=torch.float32)
        self.teacher_probabilities = (
            torch.tensor(teacher.probabilities, dtype=torch.float32) if teacher else None
        )
        self.teacher_scalars = (
            torch.tensor(teacher.scalars, dtype=torch.float32) if teacher else None
        )
        self.teacher_curves = torch.tensor(teacher.curves, dtype=torch.float32) if teacher else None
        weights = np.ones(len(labels), dtype=float) if sample_weight is None else sample_weight
        self.sample_weight = torch.tensor(weights, dtype=torch.float32)

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        item = {
            "x": self.x[index],
            "label": self.labels[index],
            "scalars": self.scalars[index],
            "curve": self.curves[index],
            "sample_weight": self.sample_weight[index],
        }
        if self.teacher_probabilities is not None:
            assert self.teacher_scalars is not None
            assert self.teacher_curves is not None
            item.update(
                {
                    "teacher_probabilities": self.teacher_probabilities[index],
                    "teacher_scalars": self.teacher_scalars[index],
                    "teacher_curve": self.teacher_curves[index],
                }
            )
        return item


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def normalize_fit(
    train: np.ndarray, values: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = np.mean(train, axis=0)
    std = np.std(train, axis=0)
    std = np.where(std < 1e-9, 1.0, std)
    return (values - mean) / std, mean, std


def record_cache_key(record: DDRecord) -> str:
    return (
        f"{record.case}|{record.theta1:.8g}|{record.theta2:.8g}|"
        f"{record.panel_a_in:.8g}|{record.panel_b_in:.8g}|{record.test_id}"
    )


def record_keys_sha256(records: list[DDRecord]) -> str:
    payload = "\n".join(record_cache_key(record) for record in records).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_or_make_targets(
    records: list[DDRecord], cache_path: Path, *, seq_len: int, workers: int
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    expected_sha = record_keys_sha256(records)
    if cache_path.exists():
        cached = np.load(cache_path, allow_pickle=False)
        cached_sha = str(cached["record_keys_sha256"].item())
        if cached_sha == expected_sha and int(cached["seq_len"].item()) == seq_len:
            audit = json.loads(str(cached["audit_json"].item()))
            return np.asarray(cached["scalars"]), np.asarray(cached["curves"]), audit

    scalars, curves, guided_gaps, independent_gaps = make_targets(
        records, seq_len=seq_len, workers=workers
    )
    audit = {
        "guided_source_gap_median": float(np.median(guided_gaps)),
        "guided_source_gap_p95": float(np.quantile(guided_gaps, 0.95)),
        "independent_source_gap_median": float(np.median(independent_gaps)),
        "independent_source_gap_p95": float(np.quantile(independent_gaps, 0.95)),
    }
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        cache_path,
        scalars=scalars,
        curves=curves,
        record_keys_sha256=np.asarray(expected_sha),
        seq_len=np.asarray(seq_len),
        audit_json=np.asarray(json.dumps(audit)),
    )
    return scalars, curves, audit


def make_model(checkpoint: dict[str, Any], device: torch.device) -> DDResponseGointSurrogate:
    config = checkpoint["model_config"]
    return DDResponseGointSurrogate(
        input_dim=int(config["input_dim"]),
        seq_len=int(config["seq_len"]),
        hidden_dim=int(config["hidden_dim"]),
        num_branches=int(config["num_branches"]),
        dropout=float(config["dropout"]),
        scalar_dim=6,
    ).to(device)


def warm_start(model: DDResponseGointSurrogate, checkpoint: dict[str, Any]) -> None:
    source = checkpoint["model_state_dict"]
    target = model.state_dict()
    final_weight_key = "scalar_head.3.weight"
    final_bias_key = "scalar_head.3.bias"
    for key, value in source.items():
        if key in {final_weight_key, final_bias_key}:
            continue
        if key in target and target[key].shape == value.shape:
            target[key] = value.detach().clone()
    source_weight = source[final_weight_key]
    source_bias = source[final_bias_key]
    target[final_weight_key][:3] = source_weight[:3].detach().clone()
    target[final_bias_key][:3] = source_bias[:3].detach().clone()
    model.load_state_dict(target)


def make_loader(dataset: Dataset, args: argparse.Namespace, *, shuffle: bool) -> DataLoader:
    kwargs: dict[str, Any] = {
        "batch_size": args.batch_size,
        "shuffle": shuffle,
        "num_workers": args.num_workers,
        "pin_memory": args.device_torch.type == "cuda",
    }
    if args.num_workers > 0:
        kwargs.update({"persistent_workers": True, "prefetch_factor": 2})
    return DataLoader(dataset, **kwargs)


def run_response_pretrain_epoch(
    model: DDResponseGointSurrogate,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer | None,
    args: argparse.Namespace,
) -> float:
    """Pretrain shared response representations without using P1 or teacher targets."""
    train = optimizer is not None
    model.train(mode=train)
    total_loss = 0.0
    total_weight = 0.0
    ordinal_weight = float(getattr(args, "pretrain_ordinal_weight", args.ordinal_weight))
    scalar_weight = float(getattr(args, "pretrain_scalar_weight", args.scalar_weight))
    curve_weight = float(getattr(args, "pretrain_curve_weight", args.curve_weight))
    with torch.set_grad_enabled(train):
        for batch in loader:
            x = batch["x"].to(args.device_torch, non_blocking=True)
            labels = batch["label"].to(args.device_torch, non_blocking=True)
            scalars = batch["scalars"].to(args.device_torch, non_blocking=True)
            curves = batch["curve"].to(args.device_torch, non_blocking=True)
            weights = batch["sample_weight"].to(args.device_torch, non_blocking=True)
            if optimizer is not None:
                optimizer.zero_grad(set_to_none=True)
            class_logits, ordinal_logits, pred_scalars, pred_curves = model(x)
            class_loss = F.cross_entropy(class_logits, labels, reduction="none")
            ordinal_loss = F.binary_cross_entropy_with_logits(
                ordinal_logits, ordinal_targets(labels), reduction="none"
            ).mean(dim=1)
            response_loss = F.smooth_l1_loss(
                pred_scalars[:, :3], scalars[:, :3], reduction="none"
            ).mean(dim=1)
            curve_loss = F.smooth_l1_loss(pred_curves, curves, reduction="none").mean(dim=1)
            per_sample = (
                class_loss
                + ordinal_weight * ordinal_loss
                + scalar_weight * response_loss
                + curve_weight * curve_loss
            )
            loss = (per_sample * weights).sum() / torch.clamp(weights.sum(), min=1e-6)
            if optimizer is not None:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 3.0)
                optimizer.step()
            batch_weight = float(weights.sum().detach().cpu())
            total_loss += float(loss.detach().cpu()) * batch_weight
            total_weight += batch_weight
    return total_loss / max(total_weight, 1e-9)


def run_goint_epoch(
    model: DDResponseGointSurrogate,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer | None,
    args: argparse.Namespace,
) -> float:
    train = optimizer is not None
    model.train(mode=train)
    total_loss = 0.0
    total_weight = 0.0
    with torch.set_grad_enabled(train):
        for batch in loader:
            x = batch["x"].to(args.device_torch, non_blocking=True)
            labels = batch["label"].to(args.device_torch, non_blocking=True)
            scalars = batch["scalars"].to(args.device_torch, non_blocking=True)
            curves = batch["curve"].to(args.device_torch, non_blocking=True)
            weights = batch["sample_weight"].to(args.device_torch, non_blocking=True)
            if optimizer is not None:
                optimizer.zero_grad(set_to_none=True)
            class_logits, ordinal_logits, pred_scalars, pred_curves = model(x)
            class_loss = F.cross_entropy(class_logits, labels, reduction="none")
            ordinal_loss = F.binary_cross_entropy_with_logits(
                ordinal_logits, ordinal_targets(labels), reduction="none"
            ).mean(dim=1)
            response_loss = F.smooth_l1_loss(
                pred_scalars[:, :3], scalars[:, :3], reduction="none"
            ).mean(dim=1)
            p1_loss = F.smooth_l1_loss(pred_scalars[:, 3:], scalars[:, 3:], reduction="none").mean(
                dim=1
            )
            curve_loss = F.smooth_l1_loss(pred_curves, curves, reduction="none").mean(dim=1)
            per_sample = (
                class_loss
                + args.ordinal_weight * ordinal_loss
                + args.scalar_weight * response_loss
                + args.p1_weight * p1_loss
                + args.curve_weight * curve_loss
            )
            loss = (per_sample * weights).sum() / torch.clamp(weights.sum(), min=1e-6)
            if optimizer is not None:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 3.0)
                optimizer.step()
            total_loss += float(loss.detach().cpu()) * float(weights.sum().detach().cpu())
            total_weight += float(weights.sum().detach().cpu())
    return total_loss / max(total_weight, 1e-9)


def run_hybrid_epoch(
    model: DDResponseGointSurrogate,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer | None,
    args: argparse.Namespace,
) -> float:
    train = optimizer is not None
    model.train(mode=train)
    total_loss = 0.0
    total_weight = 0.0
    with torch.set_grad_enabled(train):
        for batch in loader:
            x = batch["x"].to(args.device_torch, non_blocking=True)
            labels = batch["label"].to(args.device_torch, non_blocking=True)
            scalars = batch["scalars"].to(args.device_torch, non_blocking=True)
            curves = batch["curve"].to(args.device_torch, non_blocking=True)
            teacher_probs = batch["teacher_probabilities"].to(args.device_torch, non_blocking=True)
            teacher_scalars = batch["teacher_scalars"].to(args.device_torch, non_blocking=True)
            teacher_curves = batch["teacher_curve"].to(args.device_torch, non_blocking=True)
            weights = batch["sample_weight"].to(args.device_torch, non_blocking=True)
            if optimizer is not None:
                optimizer.zero_grad(set_to_none=True)
            class_logits, ordinal_logits, pred_scalars, pred_curves = model(x)
            hard_class = F.cross_entropy(class_logits, labels, reduction="none")
            temperature = args.temperature
            soft_class = F.kl_div(
                F.log_softmax(class_logits / temperature, dim=1),
                torch.clamp(teacher_probs, min=1e-7),
                reduction="none",
            ).sum(dim=1) * (temperature**2)
            ordinal_loss = F.binary_cross_entropy_with_logits(
                ordinal_logits, ordinal_targets(labels), reduction="none"
            ).mean(dim=1)
            hard_response = F.smooth_l1_loss(
                pred_scalars[:, :3], scalars[:, :3], reduction="none"
            ).mean(dim=1)
            soft_response = F.smooth_l1_loss(
                pred_scalars[:, :3], teacher_scalars[:, :3], reduction="none"
            ).mean(dim=1)
            hard_p1 = F.smooth_l1_loss(pred_scalars[:, 3:], scalars[:, 3:], reduction="none").mean(
                dim=1
            )
            soft_p1 = F.smooth_l1_loss(
                pred_scalars[:, 3:], teacher_scalars[:, 3:], reduction="none"
            ).mean(dim=1)
            hard_curve = F.smooth_l1_loss(pred_curves, curves, reduction="none").mean(dim=1)
            soft_curve = F.smooth_l1_loss(pred_curves, teacher_curves, reduction="none").mean(dim=1)
            per_sample = (
                args.hard_class_weight * hard_class
                + args.soft_class_weight * soft_class
                + args.hybrid_ordinal_weight * ordinal_loss
                + args.hard_scalar_weight * hard_response
                + args.soft_scalar_weight * soft_response
                + args.hard_p1_weight * hard_p1
                + args.soft_p1_weight * soft_p1
                + args.hard_curve_weight * hard_curve
                + args.soft_curve_weight * soft_curve
            )
            loss = (per_sample * weights).sum() / torch.clamp(weights.sum(), min=1e-6)
            if optimizer is not None:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 3.0)
                optimizer.step()
            total_loss += float(loss.detach().cpu()) * float(weights.sum().detach().cpu())
            total_weight += float(weights.sum().detach().cpu())
    return total_loss / max(total_weight, 1e-9)


def _scalar_output_layer(model: DDResponseGointSurrogate) -> torch.nn.Linear:
    layer = model.scalar_head[-1]
    if not isinstance(layer, torch.nn.Linear) or layer.out_features < 3:
        raise TypeError(
            "Max. Force calibration requires a scalar output Linear with three outputs."
        )
    return layer


def run_force_head_calibration_epoch(
    model: DDResponseGointSurrogate,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    args: argparse.Namespace,
    *,
    reference_weight: torch.Tensor,
    reference_bias: torch.Tensor,
) -> float:
    """Calibrate only the Max. Force scalar row on real fold-fit targets."""
    model.train()
    layer = _scalar_output_layer(model)
    total_loss = 0.0
    total_weight = 0.0
    beta = float(getattr(args, "force_head_huber_beta", 1.0))
    anchor_weight = float(getattr(args, "force_head_anchor_weight", 0.0))
    for batch in loader:
        x = batch["x"].to(args.device_torch, non_blocking=True)
        scalars = batch["scalars"].to(args.device_torch, non_blocking=True)
        weights = batch["sample_weight"].to(args.device_torch, non_blocking=True)
        optimizer.zero_grad(set_to_none=True)
        _, _, pred_scalars, _ = model(x)
        per_sample = F.smooth_l1_loss(
            pred_scalars[:, 2], scalars[:, 2], beta=beta, reduction="none"
        )
        data_loss = (per_sample * weights).sum() / torch.clamp(weights.sum(), min=1e-6)
        anchor_loss = (
            torch.mean((layer.weight[2] - reference_weight) ** 2)
            + (layer.bias[2] - reference_bias) ** 2
        )
        loss = data_loss + anchor_weight * anchor_loss
        loss.backward()
        torch.nn.utils.clip_grad_norm_([layer.weight, layer.bias], 3.0)
        optimizer.step()
        batch_weight = float(weights.sum().detach().cpu())
        total_loss += float(loss.detach().cpu()) * batch_weight
        total_weight += batch_weight
    return total_loss / max(total_weight, 1e-9)


def calibrate_force_head(
    model: DDResponseGointSurrogate,
    dataset: PtConsistentDataset,
    args: argparse.Namespace,
) -> tuple[list[float], dict[str, float]]:
    """Apply an anchored residual update to only scalar-head row 2 (Max. Force)."""
    epochs = int(getattr(args, "force_head_epochs", 0))
    if epochs <= 0:
        return [], {"weight_delta_l2": 0.0, "bias_delta": 0.0}

    layer = _scalar_output_layer(model)
    reference_weight = layer.weight[2].detach().clone()
    reference_bias = layer.bias[2].detach().clone()
    original_requires_grad = {
        name: parameter.requires_grad for name, parameter in model.named_parameters()
    }
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    layer.weight.requires_grad_(True)
    layer.bias.requires_grad_(True)

    weight_mask = torch.zeros_like(layer.weight)
    weight_mask[2] = 1.0
    bias_mask = torch.zeros_like(layer.bias)
    bias_mask[2] = 1.0
    weight_hook = layer.weight.register_hook(lambda gradient: gradient * weight_mask)
    bias_hook = layer.bias.register_hook(lambda gradient: gradient * bias_mask)
    optimizer = torch.optim.AdamW(
        [layer.weight, layer.bias],
        lr=float(getattr(args, "force_head_lr", 5e-4)),
        weight_decay=0.0,
    )
    loader = make_loader(dataset, args, shuffle=True)
    history: list[float] = []
    try:
        for epoch in range(1, epochs + 1):
            loss = run_force_head_calibration_epoch(
                model,
                loader,
                optimizer,
                args,
                reference_weight=reference_weight,
                reference_bias=reference_bias,
            )
            history.append(float(loss))
            if epoch == 1 or epoch % 10 == 0 or epoch == epochs:
                print(
                    f"[hybrid] Max. Force head {epoch}/{epochs}: loss={loss:.6f}",
                    flush=True,
                )
    finally:
        weight_hook.remove()
        bias_hook.remove()
        for name, parameter in model.named_parameters():
            parameter.requires_grad_(original_requires_grad[name])

    audit = {
        "weight_delta_l2": float(
            torch.linalg.vector_norm(layer.weight[2] - reference_weight).detach()
        ),
        "bias_delta": float((layer.bias[2] - reference_bias).detach()),
    }
    return history, audit


def predict_model(
    model: DDResponseGointSurrogate,
    x: np.ndarray,
    scalar_mean: np.ndarray,
    scalar_std: np.ndarray,
    args: argparse.Namespace,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    model.eval()
    classes: list[np.ndarray] = []
    scalars: list[np.ndarray] = []
    curves: list[np.ndarray] = []
    dataset = TensorDataset(torch.tensor(x, dtype=torch.float32))
    loader: DataLoader[Any] = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=False,
    )
    with torch.inference_mode():
        for (batch,) in loader:
            class_logits, _, scalar_norm, curve = model(batch.to(args.device_torch))
            classes.append((predict_from_logits(class_logits) + 1).cpu().numpy())
            transformed = scalar_norm.cpu().numpy() * scalar_std + scalar_mean
            scalars.append(inverse_transform_pt_consistent_scalars(transformed))
            curves.append(torch.clamp(curve, min=0.0).cpu().numpy())
    return np.concatenate(classes), np.concatenate(scalars), np.concatenate(curves)


def predict_baseline(
    checkpoint_path: Path,
    records: list[DDRecord],
    indices: np.ndarray,
    args: argparse.Namespace,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    checkpoint = torch.load(checkpoint_path, map_location=args.device_torch, weights_only=False)
    x_raw, _ = response_feature_matrix(records, str(checkpoint["feature_builder"]))
    mean = np.asarray(checkpoint["feature_mean"], dtype=float)
    std = np.asarray(checkpoint["feature_std"], dtype=float)
    x = (x_raw[indices] - mean) / np.maximum(std, 1e-9)
    config = checkpoint["model_config"]
    model = DDResponseGointSurrogate(
        input_dim=int(config["input_dim"]),
        seq_len=int(config["seq_len"]),
        hidden_dim=int(config["hidden_dim"]),
        num_branches=int(config["num_branches"]),
        dropout=float(config["dropout"]),
        scalar_dim=int(config.get("scalar_dim", 3)),
    ).to(args.device_torch)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    class_parts: list[np.ndarray] = []
    scalar_parts: list[np.ndarray] = []
    curve_parts: list[np.ndarray] = []
    scalar_mean = np.asarray(checkpoint["scalar_log_mean"], dtype=float)
    scalar_std = np.asarray(checkpoint["scalar_log_std"], dtype=float)
    with torch.inference_mode():
        for start in range(0, len(x), args.batch_size):
            tensor = torch.tensor(
                x[start : start + args.batch_size], dtype=torch.float32, device=args.device_torch
            )
            logits, _, scalar_norm, curve = model(tensor)
            class_parts.append((predict_from_logits(logits) + 1).cpu().numpy())
            scalar_parts.append(np.expm1(scalar_norm.cpu().numpy() * scalar_std + scalar_mean))
            curve_parts.append(torch.clamp(curve, min=0.0).cpu().numpy())
    return np.concatenate(class_parts), np.concatenate(scalar_parts), np.concatenate(curve_parts)


def metric_row(
    name: str,
    y_class: np.ndarray,
    y_scalars: np.ndarray,
    y_curves: np.ndarray,
    pred_class: np.ndarray,
    pred_scalars: np.ndarray,
    pred_curves: np.ndarray,
    *,
    p1_head: bool,
) -> dict[str, float | str]:
    pred_force = pred_curves * np.maximum(pred_scalars[:, 2:3], 1e-9)
    true_force = y_curves * np.maximum(y_scalars[:, 2:3], 1e-9)
    row: dict[str, float | str] = {
        "name": name,
        "accuracy": float(accuracy_score(y_class, pred_class)),
        "macro_f1": float(f1_score(y_class, pred_class, average="macro", zero_division=0)),
        "pt_mae": float(mean_absolute_error(y_scalars[:, 0], pred_scalars[:, 0])),
        "max_displacement_mae": float(mean_absolute_error(y_scalars[:, 1], pred_scalars[:, 1])),
        "max_force_mae": float(mean_absolute_error(y_scalars[:, 2], pred_scalars[:, 2])),
        "curve_norm_rmse": float(np.sqrt(np.mean((pred_curves - y_curves) ** 2))),
        "curve_force_rmse": float(np.sqrt(np.mean((pred_force - true_force) ** 2))),
    }
    if p1_head:
        row.update(
            {
                "pt_displacement_norm_mae": float(
                    mean_absolute_error(y_scalars[:, 3], pred_scalars[:, 3])
                ),
                "first_slope_norm_mae": float(
                    mean_absolute_error(y_scalars[:, 4], pred_scalars[:, 4])
                ),
                "second_slope_norm_mae": float(
                    mean_absolute_error(y_scalars[:, 5], pred_scalars[:, 5])
                ),
                "displayed_p1_direct_pt_gap": 0.0,
            }
        )
    return row


def tree_teacher_predictions(bundle: dict[str, Any], x: np.ndarray) -> TeacherOutputs:
    classifier = bundle["classifier"]
    probabilities = np.zeros((len(x), 3), dtype=float)
    raw_probabilities = classifier.predict_proba(x)
    for source_column, label in enumerate(classifier.classes_):
        probabilities[:, int(label) - 1] = raw_probabilities[:, source_column]
    scalars = np.asarray(bundle["scalar_model"].predict(x), dtype=float)
    curves = np.clip(bundle["pca"].inverse_transform(bundle["curve_model"].predict(x)), 0.0, None)
    return TeacherOutputs(probabilities=probabilities, scalars=scalars, curves=curves)


def normalized_teacher(
    outputs: TeacherOutputs, scalar_mean: np.ndarray, scalar_std: np.ndarray
) -> TeacherOutputs:
    transformed = transform_pt_consistent_scalars(outputs.scalars)
    return TeacherOutputs(
        probabilities=outputs.probabilities,
        scalars=(transformed - scalar_mean) / scalar_std,
        curves=outputs.curves,
    )


def synthetic_teacher_dataset(
    *,
    bundle: dict[str, Any],
    feature_set: str,
    feature_mean: np.ndarray,
    feature_std: np.ndarray,
    scalar_mean: np.ndarray,
    scalar_std: np.ndarray,
    locked_records: list[DDRecord],
    args: argparse.Namespace,
) -> PtConsistentDataset:
    theta_values = np.arange(
        args.synthetic_theta_min,
        args.synthetic_theta_max + 1e-9,
        args.synthetic_grid_step,
        dtype=float,
    )
    records = [
        ResponseFeatureRecord(
            case=case,
            theta1=float(theta1),
            theta2=float(theta2),
            panel_a_in=panel_a,
            panel_b_in=panel_b,
        )
        for panel_a, panel_b in args.synthetic_panel_size_values
        for case in CASES
        for theta1 in theta_values
        for theta2 in theta_values
    ]
    x_raw, _ = response_feature_matrix(records, feature_set)
    outputs = tree_teacher_predictions(bundle, x_raw)
    keep = synthetic_exclusion_mask(
        records,
        locked_records,
        radius=args.locked_synthetic_exclusion_radius,
    )
    x_raw = x_raw[keep]
    outputs = TeacherOutputs(
        probabilities=outputs.probabilities[keep],
        scalars=outputs.scalars[keep],
        curves=outputs.curves[keep],
    )
    confidence = np.max(outputs.probabilities, axis=1)
    confidence_multiplier = np.clip(
        confidence**args.synthetic_confidence_power,
        args.synthetic_min_confidence_weight,
        1.0,
    )
    sample_weight = args.synthetic_weight * confidence_multiplier
    teacher = normalized_teacher(outputs, scalar_mean, scalar_std)
    labels = np.argmax(outputs.probabilities, axis=1) + 1
    x_norm = (x_raw - feature_mean) / feature_std
    return PtConsistentDataset(
        x_norm,
        labels,
        teacher.scalars,
        outputs.curves,
        teacher=teacher,
        sample_weight=sample_weight,
    )


def concatenate_datasets(*datasets: PtConsistentDataset) -> PtConsistentDataset:
    teacher_probabilities: list[np.ndarray] = []
    teacher_scalars: list[np.ndarray] = []
    teacher_curves: list[np.ndarray] = []
    for dataset in datasets:
        if (
            dataset.teacher_probabilities is None
            or dataset.teacher_scalars is None
            or dataset.teacher_curves is None
        ):
            raise ValueError("Hybrid concatenation requires teacher outputs for every dataset.")
        teacher_probabilities.append(dataset.teacher_probabilities.numpy())
        teacher_scalars.append(dataset.teacher_scalars.numpy())
        teacher_curves.append(dataset.teacher_curves.numpy())
    return PtConsistentDataset(
        np.concatenate([dataset.x.numpy() for dataset in datasets]),
        np.concatenate([dataset.labels.numpy() + 1 for dataset in datasets]),
        np.concatenate([dataset.scalars.numpy() for dataset in datasets]),
        np.concatenate([dataset.curves.numpy() for dataset in datasets]),
        teacher=TeacherOutputs(
            probabilities=np.concatenate(teacher_probabilities),
            scalars=np.concatenate(teacher_scalars),
            curves=np.concatenate(teacher_curves),
        ),
        sample_weight=np.concatenate([dataset.sample_weight.numpy() for dataset in datasets]),
    )


def train_model(
    *,
    mode: str,
    baseline_path: Path,
    x_norm: np.ndarray,
    y_class: np.ndarray,
    y_scalars_norm: np.ndarray,
    y_curves: np.ndarray,
    scalar_mean: np.ndarray,
    scalar_std: np.ndarray,
    teacher_bundle: dict[str, Any] | None,
    x_raw: np.ndarray,
    locked_records: list[DDRecord],
    feature_set: str,
    feature_mean: np.ndarray,
    feature_std: np.ndarray,
    args: argparse.Namespace,
    warm_start_weights: bool = True,
    training_context: dict[str, Any] | None = None,
) -> tuple[DDResponseGointSurrogate, dict[str, Any]]:
    checkpoint = torch.load(baseline_path, map_location="cpu", weights_only=False)
    model = make_model(checkpoint, args.device_torch)
    if warm_start_weights:
        warm_start(model, checkpoint)
    epochs = args.goint_epochs if mode == "goint" else args.hybrid_epochs
    lr = args.goint_lr if mode == "goint" else args.hybrid_lr

    pretrain_epochs = int(
        getattr(
            args,
            "pretrain_goint_epochs" if mode == "goint" else "pretrain_hybrid_epochs",
            0,
        )
    )
    pretrain_lr = float(
        getattr(
            args,
            "pretrain_goint_lr" if mode == "goint" else "pretrain_hybrid_lr",
            lr,
        )
    )
    pretrain_history: list[float] = []
    if pretrain_epochs > 0:
        pretrain_dataset = PtConsistentDataset(x_norm, y_class, y_scalars_norm, y_curves)
        pretrain_loader = make_loader(pretrain_dataset, args, shuffle=True)
        pretrain_optimizer = torch.optim.AdamW(
            model.parameters(), lr=pretrain_lr, weight_decay=args.weight_decay
        )
        for epoch in range(1, pretrain_epochs + 1):
            loss = run_response_pretrain_epoch(model, pretrain_loader, pretrain_optimizer, args)
            pretrain_history.append(float(loss))
            if epoch == 1 or epoch % 10 == 0 or epoch == pretrain_epochs:
                print(
                    f"[{mode}] response pretrain {epoch}/{pretrain_epochs}: loss={loss:.6f}",
                    flush=True,
                )

    force_calibration_dataset: PtConsistentDataset | None = None
    if mode == "goint":
        dataset = PtConsistentDataset(x_norm, y_class, y_scalars_norm, y_curves)
        epoch_runner = run_goint_epoch
        synthetic_rows = 0
    else:
        if teacher_bundle is None:
            raise ValueError("Hybrid training requires a Pt-consistent Tree teacher.")
        teacher_outputs = normalized_teacher(
            tree_teacher_predictions(teacher_bundle, x_raw), scalar_mean, scalar_std
        )
        real_dataset = PtConsistentDataset(
            x_norm,
            y_class,
            y_scalars_norm,
            y_curves,
            teacher=teacher_outputs,
        )
        force_calibration_dataset = PtConsistentDataset(
            x_norm,
            y_class,
            y_scalars_norm,
            y_curves,
        )
        synthetic_dataset = synthetic_teacher_dataset(
            bundle=teacher_bundle,
            feature_set=feature_set,
            feature_mean=feature_mean,
            feature_std=feature_std,
            scalar_mean=scalar_mean,
            scalar_std=scalar_std,
            locked_records=locked_records,
            args=args,
        )
        dataset = concatenate_datasets(real_dataset, synthetic_dataset)
        epoch_runner = run_hybrid_epoch
        synthetic_rows = len(synthetic_dataset)

    loader = make_loader(dataset, args, shuffle=True)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=args.weight_decay)
    history: list[float] = []
    for epoch in range(1, epochs + 1):
        loss = epoch_runner(model, loader, optimizer, args)
        history.append(float(loss))
        if epoch == 1 or epoch % 10 == 0 or epoch == epochs:
            print(f"[{mode}] epoch {epoch}/{epochs}: loss={loss:.6f}", flush=True)
    force_history: list[float] = []
    force_audit = {"weight_delta_l2": 0.0, "bias_delta": 0.0}
    force_epochs = int(getattr(args, "force_head_epochs", 0)) if mode == "hybrid" else 0
    if force_epochs > 0:
        if force_calibration_dataset is None:
            raise ValueError("Hybrid Max. Force calibration requires real fold-fit rows.")
        force_history, force_audit = calibrate_force_head(
            model,
            force_calibration_dataset,
            args,
        )
    return model, {
        "mode": mode,
        "provenance": dict(training_context or {}),
        "epochs": epochs,
        "learning_rate": lr,
        "warm_start_model": str(baseline_path),
        "warm_start_weights": warm_start_weights,
        "training_stages": [
            {
                "stage": "fold_local_response_pretraining",
                "enabled": pretrain_epochs > 0,
                "epochs": pretrain_epochs,
                "learning_rate": pretrain_lr,
                "rows": len(y_class),
                "uses_p1_targets": False,
                "uses_teacher_targets": False,
                "uses_synthetic_rows": False,
                "loss_first": pretrain_history[0] if pretrain_history else None,
                "loss_final": pretrain_history[-1] if pretrain_history else None,
            },
            {
                "stage": "pt_consistent_fine_tuning",
                "enabled": True,
                "epochs": epochs,
                "learning_rate": lr,
                "real_rows": len(y_class),
                "synthetic_rows": synthetic_rows,
                "uses_p1_targets": True,
                "uses_teacher_targets": mode == "hybrid",
            },
            {
                "stage": "fold_local_max_force_head_calibration",
                "enabled": force_epochs > 0,
                "epochs": force_epochs,
                "learning_rate": float(getattr(args, "force_head_lr", 0.0)),
                "real_rows": len(y_class),
                "target": "max_force",
                "scalar_output_row": 2,
                "uses_teacher_targets": False,
                "uses_synthetic_rows": False,
                "huber_beta": float(getattr(args, "force_head_huber_beta", 1.0)),
                "anchor_weight": float(getattr(args, "force_head_anchor_weight", 0.0)),
                "weight_delta_l2": force_audit["weight_delta_l2"],
                "bias_delta": force_audit["bias_delta"],
                "loss_first": force_history[0] if force_history else None,
                "loss_final": force_history[-1] if force_history else None,
            },
        ],
        "synthetic_rows": synthetic_rows,
        "loss_first": history[0],
        "loss_final": history[-1],
    }


def save_checkpoint(
    *,
    model: DDResponseGointSurrogate,
    baseline_path: Path,
    output_dir: Path,
    model_name: str,
    feature_set: str,
    feature_columns: list[str],
    feature_mean: np.ndarray,
    feature_std: np.ndarray,
    scalar_mean: np.ndarray,
    scalar_std: np.ndarray,
    grid: np.ndarray,
    metrics: dict[str, Any],
    training: dict[str, Any],
    split_manifest: Path,
) -> Path:
    baseline = torch.load(baseline_path, map_location="cpu", weights_only=False)
    config = dict(baseline["model_config"])
    config["scalar_dim"] = 6
    checkpoint = {
        "model_state_dict": {
            key: value.detach().cpu() for key, value in model.state_dict().items()
        },
        "model_config": config,
        "model_name": model_name,
        "curve_representation": CURVE_REPRESENTATION,
        "feature_builder": feature_set,
        "feature_columns": feature_columns,
        "feature_mean": feature_mean,
        "feature_std": feature_std,
        "scalar_columns": list(PT_CONSISTENT_SCALAR_COLUMNS),
        "scalar_transforms": list(PT_CONSISTENT_SCALAR_TRANSFORMS),
        "scalar_log_mean": scalar_mean,
        "scalar_log_std": scalar_std,
        "grid": grid,
        "metrics": metrics,
        "training": training,
        "split_manifest": str(split_manifest),
        "label_names": {0: "Type 1", 1: "Type 2", 2: "Type 3"},
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "response_goint.pt"
    torch.save(checkpoint, path)
    return path


def write_report(report_dir: Path, payload: dict[str, Any]) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "validation_metrics.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    lines = [
        "# Pt-Consistent Neural Challengers",
        "",
        "## Protocol",
        "",
        f"- Development rows: {payload['split']['development_rows']}",
        f"- Locked Holdout rows: {payload['split']['holdout_rows']}",
        "- Split key: Case + theta1 + theta2 across all three panel sizes",
        "- Existing GointMLP and Hybrid artifacts are preserved.",
        "- Raw neural curve and Max. Force are not rescaled.",
        "- Display P1 intercepts are solved so the two predicted P1 slopes intersect at predicted Pt.",
        "",
        "## Locked Holdout",
        "",
        "| Model | Type acc. | Pt MAE | Max force MAE | Curve force RMSE | Display P1 gap |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for metrics in payload["metrics"].values():
        gap = metrics.get("displayed_p1_direct_pt_gap")
        gap_text = "N/A" if gap is None else f"{gap:.4f}"
        lines.append(
            f"| {metrics['name']} | {metrics['accuracy']:.4f} | {metrics['pt_mae']:.2f} | "
            f"{metrics['max_force_mae']:.2f} | {metrics['curve_force_rmse']:.2f} | {gap_text} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "These are locked-Holdout challengers, not replacements for the current models. The neural "
            "heads learn Pt displacement and both P1 slopes in addition to the existing response outputs. "
            "The displayed P1 intersection is exact by construction, while the independently predicted "
            "response curve remains untouched.",
            "",
        ]
    )
    (report_dir / "validation_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/datasets/DD_cases_2_3_4_geometry_3size_v1"),
    )
    parser.add_argument(
        "--split-manifest",
        type=Path,
        default=Path("data/datasets/DD_cases_2_3_4_geometry_grouped_v1/split_manifest.csv"),
    )
    parser.add_argument(
        "--goint-baseline",
        type=Path,
        default=Path(
            "models/dd_laminate_response_geometry_goint_3size_grouped_v1/response_goint.pt"
        ),
    )
    parser.add_argument(
        "--hybrid-baseline",
        type=Path,
        default=Path(
            "models/dd_laminate_response_hybrid_student_3size_grouped_v1/response_goint.pt"
        ),
    )
    parser.add_argument(
        "--teacher-model",
        type=Path,
        default=Path(
            "models/dd_laminate_response_pt_consistent_tree_3size_grouped_v1/response_surrogate.joblib"
        ),
    )
    parser.add_argument(
        "--goint-output-dir",
        type=Path,
        default=Path("models/dd_laminate_response_pt_consistent_goint_3size_grouped_v1"),
    )
    parser.add_argument(
        "--hybrid-output-dir",
        type=Path,
        default=Path("models/dd_laminate_response_pt_consistent_hybrid_3size_grouped_v1"),
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=Path("reports/dd_response_pt_consistent_deep_3size_grouped_v1"),
    )
    parser.add_argument("--mode", choices=["goint", "hybrid", "both"], default="both")
    parser.add_argument("--feature-set", default="theta_physics_geometry_v1")
    parser.add_argument("--seq-len", type=int, default=128)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--num-workers", type=int, default=2)
    parser.add_argument("--goint-epochs", type=int, default=60)
    parser.add_argument("--hybrid-epochs", type=int, default=35)
    parser.add_argument("--goint-lr", type=float, default=2e-4)
    parser.add_argument("--hybrid-lr", type=float, default=1.5e-4)
    parser.add_argument("--weight-decay", type=float, default=8e-4)
    parser.add_argument("--ordinal-weight", type=float, default=0.25)
    parser.add_argument("--scalar-weight", type=float, default=0.45)
    parser.add_argument("--p1-weight", type=float, default=0.35)
    parser.add_argument("--curve-weight", type=float, default=0.25)
    parser.add_argument("--temperature", type=float, default=2.5)
    parser.add_argument("--hard-class-weight", type=float, default=0.45)
    parser.add_argument("--soft-class-weight", type=float, default=0.75)
    parser.add_argument("--hybrid-ordinal-weight", type=float, default=0.12)
    parser.add_argument("--hard-scalar-weight", type=float, default=0.28)
    parser.add_argument("--soft-scalar-weight", type=float, default=0.55)
    parser.add_argument("--hard-p1-weight", type=float, default=0.25)
    parser.add_argument("--soft-p1-weight", type=float, default=0.40)
    parser.add_argument("--hard-curve-weight", type=float, default=0.18)
    parser.add_argument("--soft-curve-weight", type=float, default=0.38)
    parser.add_argument("--synthetic-grid-step", type=float, default=2.5)
    parser.add_argument("--synthetic-theta-min", type=float, default=-90.0)
    parser.add_argument("--synthetic-theta-max", type=float, default=90.0)
    parser.add_argument("--synthetic-panel-sizes", default="6x4,6x8,8x8")
    parser.add_argument("--synthetic-weight", type=float, default=0.28)
    parser.add_argument("--synthetic-confidence-power", type=float, default=1.5)
    parser.add_argument("--synthetic-min-confidence-weight", type=float, default=0.45)
    parser.add_argument("--locked-synthetic-exclusion-radius", type=float, default=2.5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=["auto", "cpu", "mps", "cuda"], default="auto")
    args = parser.parse_args()
    args.device_torch = resolve_device(args.device)
    args.synthetic_panel_size_values = parse_panel_sizes(args.synthetic_panel_sizes)
    set_seed(args.seed)
    print(f"Using device: {args.device_torch}", flush=True)

    records = load_records(args.data_dir)
    train_idx, holdout_idx = split_indices(records, args.split_manifest)
    x_raw, feature_columns = response_feature_matrix(records, args.feature_set)
    x_norm, feature_mean, feature_std = normalize_fit(x_raw[train_idx], x_raw)
    y_class = np.asarray([record.label for record in records], dtype=int)
    cache_path = args.report_dir / "p1_targets.npz"
    y_scalars, y_curves, target_audit = load_or_make_targets(
        records, cache_path, seq_len=args.seq_len, workers=args.workers
    )
    transformed_scalars = transform_pt_consistent_scalars(y_scalars)
    y_scalars_norm, scalar_mean, scalar_std = normalize_fit(
        transformed_scalars[train_idx], transformed_scalars
    )
    grid = np.linspace(0.0, 1.0, args.seq_len)

    payload: dict[str, Any] = {
        "dataset": str(args.data_dir),
        "split_manifest": str(args.split_manifest),
        "split": {
            "development_rows": len(train_idx),
            "holdout_rows": len(holdout_idx),
        },
        "device": str(args.device_torch),
        "target_audit": target_audit,
        "metrics": {},
        "training": {},
        "artifacts": {},
    }

    for mode, baseline_path in (
        ("goint", args.goint_baseline),
        ("hybrid", args.hybrid_baseline),
    ):
        baseline_class, baseline_scalars, baseline_curves = predict_baseline(
            baseline_path, records, holdout_idx, args
        )
        payload["metrics"][f"baseline_{mode}"] = metric_row(
            f"Existing 3-Size {'GointMLP' if mode == 'goint' else 'Hybrid'}",
            y_class[holdout_idx],
            y_scalars[holdout_idx],
            y_curves[holdout_idx],
            baseline_class,
            baseline_scalars,
            baseline_curves,
            p1_head=False,
        )

    teacher_bundle = joblib.load(args.teacher_model) if args.mode in {"hybrid", "both"} else None
    locked_records = [records[int(index)] for index in holdout_idx]
    requested_modes = ["goint", "hybrid"] if args.mode == "both" else [args.mode]
    for mode in requested_modes:
        baseline_path = args.goint_baseline if mode == "goint" else args.hybrid_baseline
        output_dir = args.goint_output_dir if mode == "goint" else args.hybrid_output_dir
        model, training = train_model(
            mode=mode,
            baseline_path=baseline_path,
            x_norm=x_norm[train_idx],
            y_class=y_class[train_idx],
            y_scalars_norm=y_scalars_norm[train_idx],
            y_curves=y_curves[train_idx],
            scalar_mean=scalar_mean,
            scalar_std=scalar_std,
            teacher_bundle=teacher_bundle,
            x_raw=x_raw[train_idx],
            locked_records=locked_records,
            feature_set=args.feature_set,
            feature_mean=feature_mean,
            feature_std=feature_std,
            args=args,
        )
        pred_class, pred_scalars, pred_curves = predict_model(
            model, x_norm[holdout_idx], scalar_mean, scalar_std, args
        )
        model_label = "GointMLP" if mode == "goint" else "Hybrid"
        metrics = metric_row(
            f"Pt-Consistent {model_label} v1",
            y_class[holdout_idx],
            y_scalars[holdout_idx],
            y_curves[holdout_idx],
            pred_class,
            pred_scalars,
            pred_curves,
            p1_head=True,
        )
        payload["metrics"][f"pt_consistent_{mode}"] = metrics
        payload["training"][mode] = training
        artifact = save_checkpoint(
            model=model,
            baseline_path=baseline_path,
            output_dir=output_dir,
            model_name=f"laminate_forecast_pt_consistent_{mode}_3size_grouped_v1",
            feature_set=args.feature_set,
            feature_columns=feature_columns,
            feature_mean=feature_mean,
            feature_std=feature_std,
            scalar_mean=scalar_mean,
            scalar_std=scalar_std,
            grid=grid,
            metrics=metrics,
            training=training,
            split_manifest=args.split_manifest,
        )
        payload["artifacts"][mode] = str(artifact)
        print(
            f"[{mode}] locked holdout: acc={metrics['accuracy']:.4f}, "
            f"Pt MAE={metrics['pt_mae']:.2f}, curve force RMSE={metrics['curve_force_rmse']:.2f}",
            flush=True,
        )

    write_report(args.report_dir, payload)
    print(json.dumps(payload, indent=2), flush=True)


if __name__ == "__main__":
    main()
