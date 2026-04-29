"""Data loading utilities for the KyulAI ML pipeline.

Bridges the Data Engineering team's UnifiedCAERecord schema and the ML team's
ModelBatch format consumed by all surrogate models.

Key components
--------------
CAEDataset
    PyTorch Dataset that wraps a list of UnifiedCAERecords, applies feature
    extraction, and produces ModelBatch-compatible item dicts.

collate_fn
    Custom collate function that handles:
    - Fixed-size targets (pad or truncate to a reference node count)
    - Variable-size targets (returns ragged lists — used when node count varies)

create_dataloaders
    Convenience factory: splits records into train/val(/test), creates datasets
    and DataLoaders with sensible defaults.

FieldConfig
    Pydantic model specifying which output fields to load as targets and their
    expected sizes.  Passed to CAEDataset at construction time.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import torch
from pydantic import BaseModel, Field
from torch.utils.data import DataLoader, Dataset

from src.data.schemas.record import UnifiedCAERecord
from src.ml.models.base import ModelBatch
from src.ml.training.feature_extractor import FeatureExtractor, Normalizer


# ── Field configuration ───────────────────────────────────────────────────────


class TargetFieldSpec(BaseModel):
    """Specification for a single target output field to load.

    Attributes
    ----------
    name:
        Field name as it appears in ``UnifiedCAERecord.output_fields``.
    field_type:
        Whether this is a scalar, vector, or tensor field.
    expected_size:
        If set, pads/truncates the field to this many nodes.
        If None, uses the field's natural size (requires all records to have
        the same mesh size, or use the ragged collate strategy).
    """

    name: str
    field_type: Literal["scalar", "vector", "tensor"] = "scalar"
    expected_size: int | None = None  # N_nodes for scalar, N_nodes*3 for vector, etc.

    model_config = {"extra": "forbid"}


class DatasetConfig(BaseModel):
    """Configuration for CAEDataset.

    Attributes
    ----------
    target_fields:
        Which output fields to load as prediction targets.
    mode:
        'mlp' — only process features; 'cnn' — also loads grid_input.
    normalizer_path:
        Path to a saved Normalizer (.npz).  If None, features are not
        z-score normalised (scale-only normalisation from FEATURE_REGISTRY still
        applies).
    """

    target_fields: list[TargetFieldSpec] = Field(default_factory=list)
    mode: Literal["mlp", "cnn"] = "mlp"
    normalizer_path: str | None = None

    model_config = {"extra": "forbid"}


# ── Dataset ───────────────────────────────────────────────────────────────────


class CAEDataset(Dataset):
    """PyTorch Dataset over a list of UnifiedCAERecord objects.

    Each ``__getitem__`` call returns a dict that the collate function converts
    into a ModelBatch.

    Parameters
    ----------
    records:
        Loaded UnifiedCAERecord objects.  The dataset holds them in memory; for
        very large datasets, replace the list with a lazy reader (e.g., HDF5).
    config:
        DatasetConfig specifying which fields to load and normalisation.
    extractor:
        Pre-built FeatureExtractor (shared across train/val datasets).
    normalizer:
        Optional Normalizer.  If provided, z-score normalisation is applied on
        top of the scale normalisation done by the extractor.
    """

    def __init__(
        self,
        records: list[UnifiedCAERecord],
        config: DatasetConfig,
        extractor: FeatureExtractor,
        normalizer: Normalizer | None = None,
    ) -> None:
        self.records = records
        self.config = config
        self.extractor = extractor
        self.normalizer = normalizer
        self._field_specs = {spec.name: spec for spec in config.target_fields}

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        record = self.records[idx]

        # ── Process features ──────────────────────────────────────────────────
        features, mask = self.extractor.extract(record)
        if self.normalizer is not None:
            features = self.normalizer.transform(features)

        item: dict[str, Any] = {
            "process_features": torch.from_numpy(features),   # (D,)
            "feature_mask": torch.from_numpy(mask),           # (D,) bool
            "source_tool": record.metadata.source_tool.value,
            "record_id": str(record.record_id),
        }

        # ── Target scalar fields ──────────────────────────────────────────────
        for spec in self.config.target_fields:
            if spec.field_type == "scalar":
                field_data = record.output_fields.get_scalar(spec.name)
                if field_data is not None:
                    values = field_data.values.astype(np.float32)
                    # Flatten time-varying fields to last frame for Phase 1
                    if values.ndim == 2:
                        values = values[-1]  # (N,)
                    tensor = torch.from_numpy(values)
                    if spec.expected_size is not None:
                        tensor = _pad_or_truncate_1d(tensor, spec.expected_size)
                    item[f"target_scalar_{spec.name}"] = tensor
                else:
                    item[f"target_scalar_{spec.name}"] = None

            elif spec.field_type == "vector":
                field_data = record.output_fields.get_vector(spec.name)
                if field_data is not None:
                    values = field_data.values.astype(np.float32)
                    if values.ndim == 3:
                        values = values[-1]  # (N, 3) last frame
                    tensor = torch.from_numpy(values)  # (N, 3)
                    if spec.expected_size is not None:
                        tensor = _pad_or_truncate_2d(tensor, spec.expected_size, 3)
                    item[f"target_vector_{spec.name}"] = tensor
                else:
                    item[f"target_vector_{spec.name}"] = None

            elif spec.field_type == "tensor":
                field_data = record.output_fields.get_tensor(spec.name)
                if field_data is not None:
                    values = field_data.values.astype(np.float32)
                    if values.ndim > 2 and values.shape[0] != record.geometry.num_nodes:
                        values = values[-1]  # last frame if time-varying
                    item[f"target_tensor_{spec.name}"] = torch.from_numpy(values)
                else:
                    item[f"target_tensor_{spec.name}"] = None

        # ── Grid input (CNN mode) ─────────────────────────────────────────────
        if self.config.mode == "cnn":
            # Grid input construction is domain-specific and handled by subclasses
            # or pre-processing pipelines.  Reserve the key for the collate fn.
            item["grid_input"] = None  # populated by a grid builder transform

        return item


# ── Padding helpers ───────────────────────────────────────────────────────────


def _pad_or_truncate_1d(t: torch.Tensor, size: int) -> torch.Tensor:
    """Pad with zeros or truncate a 1D tensor to exactly *size* elements."""
    n = t.shape[0]
    if n == size:
        return t
    if n > size:
        return t[:size]
    return torch.cat([t, torch.zeros(size - n, dtype=t.dtype)])


def _pad_or_truncate_2d(t: torch.Tensor, n_rows: int, n_cols: int) -> torch.Tensor:
    """Pad or truncate a 2D (N, C) tensor to (n_rows, n_cols)."""
    t = t[:n_rows] if t.shape[0] > n_rows else torch.cat(
        [t, torch.zeros(n_rows - t.shape[0], n_cols, dtype=t.dtype)], dim=0
    )
    return t


# ── Collate function ──────────────────────────────────────────────────────────


def collate_cae(batch: list[dict[str, Any]]) -> ModelBatch:
    """Convert a list of dataset items into a ModelBatch.

    Items with None targets (field not present in that record) contribute zeros
    to the batch tensor.  A separate ``target_*_mask`` is NOT produced here —
    the trainer/evaluator should skip records where targets are missing.
    """
    process_features = torch.stack([item["process_features"] for item in batch])  # (B, D)
    feature_masks = torch.stack([item["feature_mask"] for item in batch])          # (B, D)

    source_tools = [item["source_tool"] for item in batch]
    record_ids = [item["record_id"] for item in batch]

    # Gather grid inputs if present
    grid_inputs = [item.get("grid_input") for item in batch]
    grid_input_tensor: torch.Tensor | None = None
    if any(g is not None for g in grid_inputs):
        grid_input_tensor = torch.stack([g for g in grid_inputs if g is not None])

    # Gather targets: look for all target_scalar_*, target_vector_*, target_tensor_* keys
    target_scalars: dict[str, torch.Tensor] = {}
    target_vectors: dict[str, torch.Tensor] = {}
    target_tensors: dict[str, torch.Tensor] = {}

    if batch:
        for key in batch[0]:
            if key.startswith("target_scalar_"):
                field_name = key[len("target_scalar_"):]
                tensors = [
                    item[key] if item[key] is not None
                    else torch.zeros_like(batch[0][key])
                    if batch[0][key] is not None
                    else torch.zeros(1)
                    for item in batch
                ]
                target_scalars[field_name] = torch.stack(tensors)

            elif key.startswith("target_vector_"):
                field_name = key[len("target_vector_"):]
                tensors = [
                    item[key] if item[key] is not None
                    else torch.zeros_like(batch[0][key])
                    if batch[0][key] is not None
                    else torch.zeros(1, 3)
                    for item in batch
                ]
                target_vectors[field_name] = torch.stack(tensors)

            elif key.startswith("target_tensor_"):
                field_name = key[len("target_tensor_"):]
                tensors = [
                    item[key] if item[key] is not None
                    else torch.zeros_like(batch[0][key])
                    if batch[0][key] is not None
                    else torch.zeros(1)
                    for item in batch
                ]
                target_tensors[field_name] = torch.stack(tensors)

    return ModelBatch(
        process_features=process_features,
        feature_mask=feature_masks,
        grid_input=grid_input_tensor,
        target_scalars=target_scalars,
        target_vectors=target_vectors,
        target_tensors=target_tensors,
        source_tools=source_tools,
        record_ids=record_ids,
    )


# ── DataLoader factory ────────────────────────────────────────────────────────


@dataclass
class DataLoaderConfig:
    """Configuration for DataLoader creation."""

    batch_size: int = 32
    num_workers: int = 4
    val_fraction: float = 0.15
    test_fraction: float = 0.0
    shuffle_train: bool = True
    seed: int = 42
    pin_memory: bool = True


def create_dataloaders(
    records: list[UnifiedCAERecord],
    dataset_config: DatasetConfig,
    loader_config: DataLoaderConfig | None = None,
    normalizer: Normalizer | None = None,
    fit_normalizer: bool = True,
) -> dict[str, DataLoader]:
    """Build train/val(/test) DataLoaders from a list of UnifiedCAERecords.

    Parameters
    ----------
    records:
        All available UnifiedCAERecord objects.
    dataset_config:
        Specifies target fields and mode.
    loader_config:
        DataLoader parameters (batch size, splits, etc.).
    normalizer:
        Pre-fitted Normalizer.  If None and fit_normalizer=True, fits one on
        the training split.
    fit_normalizer:
        Whether to fit a new Normalizer on the training set.

    Returns
    -------
    Dict with keys "train", "val", and optionally "test", each a DataLoader.
    Also includes "normalizer" key with the fitted Normalizer instance.
    """
    cfg = loader_config or DataLoaderConfig()
    rng = random.Random(cfg.seed)

    # Deterministic shuffle then split
    indices = list(range(len(records)))
    rng.shuffle(indices)

    n_test = int(len(indices) * cfg.test_fraction)
    n_val = int(len(indices) * cfg.val_fraction)
    n_train = len(indices) - n_val - n_test

    train_idx = indices[:n_train]
    val_idx = indices[n_train: n_train + n_val]
    test_idx = indices[n_train + n_val:]

    train_records = [records[i] for i in train_idx]
    val_records = [records[i] for i in val_idx]
    test_records = [records[i] for i in test_idx] if test_idx else []

    # Feature extractor (shared across splits — stateless)
    extractor = FeatureExtractor()

    # Fit normalizer on training set if needed
    if normalizer is None and fit_normalizer:
        train_feats, train_masks = extractor.extract_batch(train_records)
        normalizer = Normalizer.fit(train_feats, train_masks)

    def make_loader(split_records: list[UnifiedCAERecord], shuffle: bool) -> DataLoader:
        ds = CAEDataset(split_records, dataset_config, extractor, normalizer)
        return DataLoader(
            ds,
            batch_size=cfg.batch_size,
            shuffle=shuffle,
            num_workers=cfg.num_workers,
            collate_fn=collate_cae,
            pin_memory=cfg.pin_memory,
            drop_last=shuffle,  # drop last incomplete batch during training
        )

    loaders: dict[str, Any] = {
        "train": make_loader(train_records, cfg.shuffle_train),
        "val": make_loader(val_records, False),
        "normalizer": normalizer,
        "feature_dim": extractor.feature_dim,
    }
    if test_records:
        loaders["test"] = make_loader(test_records, False)

    return loaders
