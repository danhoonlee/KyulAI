"""Data loading interface contract between Data Engineering and AI/ML teams.

This module defines the interfaces and classes that the AI/ML training
infrastructure uses to consume data.  The Data Engineering team builds
the concrete implementations; the AI/ML team codes against these abstractions.

Interface contract (for Data Engineering team)
----------------------------------------------
1. ``KyulDataset.__getitem__`` must return a ``ModelBatch`` where:
   - ``process_features`` is a float32 tensor of shape (D_in,) — the
     feature vector extracted from ``UnifiedCAERecord.input_fields`` and
     ``UnifiedCAERecord.metadata`` by a ``FeatureExtractor``.
   - ``feature_mask`` is a bool tensor of shape (D_in,) — True where the
     original value was present (not None).
   - ``target_scalars``, ``target_vectors``, ``target_tensors`` hold field
     values from ``UnifiedCAERecord.output_fields``.

2. ``FeatureExtractor.extract(record) -> (tensor, mask)`` converts one
   ``UnifiedCAERecord`` to the flat feature vector.  The feature schema
   (which fields in what order) must be serialised alongside each checkpoint
   so models can be re-loaded correctly.

3. ``CAEDataLoader`` wraps ``KyulDataset`` in a PyTorch ``DataLoader`` with
   the ``ModelBatch`` collator applied automatically.

OOD Split Strategy
------------------
Per the Research Team's methodology recommendations (MaterialDA finding):
random splits overestimate performance by 2–5×.  All evaluation splits must
use one of the ``OODSplitStrategy`` variants (process parameter OOD, geometry
OOD, material OOD, or cross-tool).  ``SplitConfig`` controls which strategy
is used.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset

from src.ml.models.base import ModelBatch

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OOD split strategies
# ---------------------------------------------------------------------------


class OODSplitStrategy(str, Enum):
    """How to split a dataset into train / val / test sets.

    Per the Research Team's recommendation (MaterialDA, arXiv 2308.02937):
    random splits overestimate surrogate performance by 2–5×.  Always prefer
    an OOD-aware split for final reporting.

    RANDOM:
        Baseline only — use for sanity checks, never for final results.
    PROCESS_PARAM_OOD:
        Hold out samples from a different range of process parameters
        (e.g. train on injection temperature 200–230°C, test on 240–260°C).
    GEOMETRY_OOD:
        Hold out samples from geometrically dissimilar parts
        (e.g. train on flat laminates, test on curved panels).
    MATERIAL_OOD:
        Hold out a different material system
        (e.g. train on CFRP, test on GFRP).
    CROSS_TOOL:
        Hold out a different CAE tool
        (e.g. train on Moldex3D + Digimat, evaluate on Abaqus).
    EXPERIMENTAL:
        Test set consists exclusively of experimental measurements.
        This is the true sim-to-real evaluation split.
    """

    RANDOM = "random"
    PROCESS_PARAM_OOD = "process_param_ood"
    GEOMETRY_OOD = "geometry_ood"
    MATERIAL_OOD = "material_ood"
    CROSS_TOOL = "cross_tool"
    EXPERIMENTAL = "experimental"


@dataclass
class SplitConfig:
    """Configuration for dataset splitting.

    Attributes
    ----------
    strategy:
        Which OOD split strategy to use.
    train_fraction:
        Fraction of data for training (only used with RANDOM strategy).
    val_fraction:
        Fraction of data for validation.
    test_fraction:
        Fraction of data for test.
    ood_column:
        Column/attribute name used for OOD splitting
        (e.g. "injection_temperature_K" for PROCESS_PARAM_OOD,
        "source_tool" for CROSS_TOOL).
    ood_test_values:
        Values that go to the test set.  All other values go to train.
        Used by non-random OOD strategies.
    random_seed:
        Seed for reproducible random splits.
    """

    strategy: OODSplitStrategy = OODSplitStrategy.PROCESS_PARAM_OOD
    train_fraction: float = 0.70
    val_fraction: float = 0.15
    test_fraction: float = 0.15
    ood_column: str | None = None
    ood_test_values: list[Any] = field(default_factory=list)
    random_seed: int = 42

    def __post_init__(self) -> None:
        total = self.train_fraction + self.val_fraction + self.test_fraction
        if not (0.99 < total < 1.01):
            raise ValueError(f"train + val + test fractions must sum to 1.0, got {total:.3f}")
        if self.strategy != OODSplitStrategy.RANDOM and self.ood_column is None:
            logger.warning(
                "OOD split strategy '%s' selected but ood_column is None — "
                "falling back to random split.",
                self.strategy,
            )


# ---------------------------------------------------------------------------
# Data split result
# ---------------------------------------------------------------------------


@dataclass
class DataSplit:
    """Indices (or record IDs) for a train / val / test split.

    Attributes
    ----------
    train_indices, val_indices, test_indices:
        Integer indices into the source dataset.
    strategy:
        Which OOD strategy produced this split (for logging).
    ood_column:
        Column used for OOD stratification (may be None).
    ood_test_values:
        Values assigned to the test set.
    """

    train_indices: list[int]
    val_indices: list[int]
    test_indices: list[int]
    strategy: OODSplitStrategy = OODSplitStrategy.RANDOM
    ood_column: str | None = None
    ood_test_values: list[Any] = field(default_factory=list)

    @property
    def n_train(self) -> int:
        return len(self.train_indices)

    @property
    def n_val(self) -> int:
        return len(self.val_indices)

    @property
    def n_test(self) -> int:
        return len(self.test_indices)

    def summary(self) -> str:
        return (
            f"DataSplit(strategy={self.strategy.value}, "
            f"train={self.n_train}, val={self.n_val}, test={self.n_test})"
        )


# ---------------------------------------------------------------------------
# Feature extraction (interface + reference implementation)
# ---------------------------------------------------------------------------


class FeatureExtractor:
    """Converts a UnifiedCAERecord to a flat float32 feature tensor.

    This is the boundary between the Data Engineering team's schema and the
    AI/ML team's model inputs.  The canonical feature vector is defined by the
    ordered list of ``feature_spec`` entries — each entry specifies a dotted
    attribute path into the ``UnifiedCAERecord`` and its expected shape.

    The Data Engineering team populates the concrete records; this class
    extracts the agreed feature vector from them.

    Parameters
    ----------
    feature_spec:
        Ordered list of (attribute_path, expected_size) pairs.
        ``attribute_path`` is a dot-separated path into UnifiedCAERecord,
        e.g. "input_fields.material_properties.elastic.E1_Pa".
        ``expected_size`` is 1 for scalars, 3 for 3-vectors, etc.
    normalisation_stats:
        Dict mapping feature index → (mean, std) for z-score normalisation.
        Populated by ``fit(records)`` and serialised to disk alongside
        model checkpoints.
    """

    def __init__(
        self,
        feature_spec: list[tuple[str, int]] | None = None,
        normalisation_stats: dict[int, tuple[float, float]] | None = None,
    ) -> None:
        self.feature_spec: list[tuple[str, int]] = feature_spec or []
        self.normalisation_stats: dict[int, tuple[float, float]] = normalisation_stats or {}

    @property
    def feature_dim(self) -> int:
        """Total number of scalar features in the feature vector."""
        return sum(size for _, size in self.feature_spec)

    def extract(self, record: Any) -> tuple[torch.Tensor, torch.Tensor]:
        """Extract feature vector from a UnifiedCAERecord.

        Parameters
        ----------
        record:
            A UnifiedCAERecord instance from the unified schema.

        Returns
        -------
        features:
            Float32 tensor of shape (D_in,).
        mask:
            Bool tensor of shape (D_in,): True where feature was present.
        """
        values: list[float] = []
        mask_bits: list[bool] = []

        idx = 0
        for attr_path, size in self.feature_spec:
            val = self._get_attr(record, attr_path)
            stats = self.normalisation_stats.get(idx)

            if val is None:
                values.extend([0.0] * size)
                mask_bits.extend([False] * size)
            else:
                if isinstance(val, (int, float)):
                    raw = [float(val)]
                else:
                    raw = [float(v) for v in val]

                if len(raw) != size:
                    logger.warning(
                        "Feature '%s' expected size %d, got %d — padding with zeros.",
                        attr_path,
                        size,
                        len(raw),
                    )
                    raw = (raw + [0.0] * size)[:size]

                if stats is not None:
                    mean, std = stats
                    raw = [(r - mean) / (std + 1e-8) for r in raw]

                values.extend(raw)
                mask_bits.extend([True] * size)

            idx += size

        features = torch.tensor(values, dtype=torch.float32)
        mask = torch.tensor(mask_bits, dtype=torch.bool)
        return features, mask

    def fit(self, records: Sequence[Any]) -> None:
        """Compute per-feature normalisation statistics from a list of records.

        Call on training records only — never on validation or test data.
        """
        if not self.feature_spec:
            raise RuntimeError("feature_spec is empty — define it before calling fit().")

        all_features: list[list[float]] = [[] for _ in range(self.feature_dim)]

        for record in records:
            feats, mask = self.extract(record)
            for i, (v, m) in enumerate(zip(feats.tolist(), mask.tolist(), strict=False)):
                if m:
                    all_features[i].append(v)

        for i, vals in enumerate(all_features):
            if vals:
                arr = np.array(vals, dtype=np.float64)
                self.normalisation_stats[i] = (float(arr.mean()), float(arr.std()))

    @staticmethod
    def _get_attr(obj: Any, dotted_path: str) -> Any:
        """Traverse a dotted attribute path on obj, returning None if missing."""
        for attr in dotted_path.split("."):
            if obj is None:
                return None
            try:
                obj = getattr(obj, attr)
            except AttributeError:
                return None
        return obj


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------


class KyulDataset(Dataset):
    """PyTorch Dataset wrapping a list of UnifiedCAERecord objects.

    Converts each record to a (ModelBatch item) on access via the
    ``FeatureExtractor`` and target field extraction.

    Parameters
    ----------
    records:
        Sequence of ``UnifiedCAERecord`` objects.
    extractor:
        Fitted ``FeatureExtractor`` instance (call ``.fit(records)`` first).
    target_scalar_fields:
        Names of scalar fields from ``OutputFields`` to include as targets.
    target_vector_fields:
        Names of vector fields to include as targets.
    target_tensor_fields:
        Names of tensor fields to include as targets.
    include_grid:
        If True, extract the structured grid from geometry.nodes and place it
        in ``batch.grid_input`` for CNN models.  Requires structured mesh.
    """

    def __init__(
        self,
        records: Sequence[Any],
        extractor: FeatureExtractor,
        target_scalar_fields: list[str] | None = None,
        target_vector_fields: list[str] | None = None,
        target_tensor_fields: list[str] | None = None,
        include_grid: bool = False,
    ) -> None:
        self.records = list(records)
        self.extractor = extractor
        self.target_scalar_fields = target_scalar_fields or []
        self.target_vector_fields = target_vector_fields or []
        self.target_tensor_fields = target_tensor_fields or []
        self.include_grid = include_grid

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int) -> ModelBatch:
        record = self.records[idx]
        features, mask = self.extractor.extract(record)

        target_scalars: dict[str, torch.Tensor] = {}
        for fname in self.target_scalar_fields:
            sf = record.output_fields.get_scalar(fname)
            if sf is not None:
                target_scalars[fname] = torch.from_numpy(sf.values.copy()).float()

        target_vectors: dict[str, torch.Tensor] = {}
        for fname in self.target_vector_fields:
            vf = record.output_fields.get_vector(fname)
            if vf is not None:
                target_vectors[fname] = torch.from_numpy(vf.values.copy()).float()

        target_tensors: dict[str, torch.Tensor] = {}
        for fname in self.target_tensor_fields:
            tf = record.output_fields.get_tensor(fname)
            if tf is not None:
                target_tensors[fname] = torch.from_numpy(tf.values.copy()).float()

        grid_input: torch.Tensor | None = None
        if self.include_grid:
            # Structured grid: nodes are (N, 3); reshape to (3, *grid_dims)
            grid_dims = record.geometry.grid_dimensions
            if grid_dims is not None:
                coords = record.geometry.nodes  # (N, 3)
                n_dims = len(grid_dims)
                grid = torch.from_numpy(coords.copy()).float()
                # Reshape: (N, 3) → (3, nx, ny[, nz])
                grid = grid.view(*grid_dims, 3).permute(n_dims, *range(n_dims)).contiguous()
                grid_input = grid

        return ModelBatch(
            process_features=features,
            feature_mask=mask,
            grid_input=grid_input,
            target_scalars=target_scalars,
            target_vectors=target_vectors,
            target_tensors=target_tensors,
            source_tools=[record.source_tool],
            record_ids=[str(record.record_id)],
        )


# ---------------------------------------------------------------------------
# Collator
# ---------------------------------------------------------------------------


def collate_model_batches(items: list[ModelBatch]) -> ModelBatch:
    """Collate a list of single-record ModelBatches into a batched ModelBatch.

    This is the custom ``collate_fn`` for ``CAEDataLoader``.
    """
    process_features = torch.stack([b.process_features for b in items], dim=0)
    feature_mask = torch.stack([b.feature_mask for b in items], dim=0)

    grid_input: torch.Tensor | None = None
    if items[0].grid_input is not None:
        grid_tensors: list[torch.Tensor] = []
        for batch in items:
            if batch.grid_input is None:
                raise ValueError("All ModelBatch items must include grid_input when the first does")
            grid_tensors.append(batch.grid_input)
        grid_input = torch.stack(grid_tensors, dim=0)

    # Collate target dicts — only include fields present in all items
    def _collate_dict(
        key: str,
    ) -> dict[str, torch.Tensor]:
        dicts = [getattr(b, key) for b in items]
        all_keys = set(dicts[0].keys())
        result: dict[str, torch.Tensor] = {}
        for fname in all_keys:
            if all(fname in d for d in dicts):
                tensors = [d[fname] for d in dicts]
                # Pad to same length if node counts differ (e.g. different meshes)
                max_len = max(t.shape[0] for t in tensors)
                padded = [
                    torch.nn.functional.pad(
                        t, (0,) * (2 * (t.ndim - 1)) + (0, max_len - t.shape[0])
                    )
                    for t in tensors
                ]
                result[fname] = torch.stack(padded, dim=0)
        return result

    return ModelBatch(
        process_features=process_features,
        feature_mask=feature_mask,
        grid_input=grid_input,
        target_scalars=_collate_dict("target_scalars"),
        target_vectors=_collate_dict("target_vectors"),
        target_tensors=_collate_dict("target_tensors"),
        source_tools=[b.source_tools[0] for b in items],
        record_ids=[b.record_ids[0] for b in items],
    )


# ---------------------------------------------------------------------------
# Data loader factory
# ---------------------------------------------------------------------------


class CAEDataLoader:
    """Factory for creating train / val / test DataLoaders from a KyulDataset.

    Handles:
    - Applying the ``ModelBatch`` collator automatically
    - OOD-aware splitting via ``SplitConfig``
    - Conformal calibration subset reservation (15% of training data held
      out as a CP calibration set, separate from validation)

    Usage
    -----
    >>> loader_factory = CAEDataLoader(dataset, config)
    >>> train_dl, val_dl, test_dl, cp_cal_dl = loader_factory.build_loaders()
    """

    def __init__(
        self,
        dataset: KyulDataset,
        split_config: SplitConfig,
        batch_size: int = 32,
        num_workers: int = 0,
        conformal_cal_fraction: float = 0.15,
    ) -> None:
        self.dataset = dataset
        self.split_config = split_config
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.conformal_cal_fraction = conformal_cal_fraction

    def build_split(self) -> DataSplit:
        """Compute train / val / test index split per the configured strategy."""
        n = len(self.dataset)
        cfg = self.split_config
        rng = np.random.default_rng(cfg.random_seed)

        if cfg.strategy == OODSplitStrategy.RANDOM:
            indices = rng.permutation(n).tolist()
            n_train = int(n * cfg.train_fraction)
            n_val = int(n * cfg.val_fraction)
            return DataSplit(
                train_indices=indices[:n_train],
                val_indices=indices[n_train : n_train + n_val],
                test_indices=indices[n_train + n_val :],
                strategy=cfg.strategy,
            )

        # OOD splits: partition by attribute value
        if cfg.ood_column is None:
            logger.warning("OOD split requires ood_column — falling back to random.")
            return self.build_split()

        test_idx, train_val_idx = [], []
        for i, record in enumerate(self.dataset.records):
            val = FeatureExtractor._get_attr(record, cfg.ood_column)
            if val in cfg.ood_test_values:
                test_idx.append(i)
            else:
                train_val_idx.append(i)

        # Further split train_val into train / val randomly
        rng.shuffle(train_val_idx)
        n_val = int(len(train_val_idx) * cfg.val_fraction)
        val_idx = train_val_idx[:n_val]
        train_idx = train_val_idx[n_val:]

        logger.info(
            "OOD split | strategy=%s ood_col=%s | train=%d val=%d test=%d",
            cfg.strategy.value,
            cfg.ood_column,
            len(train_idx),
            len(val_idx),
            len(test_idx),
        )

        return DataSplit(
            train_indices=train_idx,
            val_indices=val_idx,
            test_indices=test_idx,
            strategy=cfg.strategy,
            ood_column=cfg.ood_column,
            ood_test_values=cfg.ood_test_values,
        )

    def build_loaders(
        self,
    ) -> tuple[DataLoader, DataLoader, DataLoader, DataLoader]:
        """Build (train, val, test, conformal_cal) DataLoaders.

        Returns 4 loaders:
        - train: for gradient updates
        - val: for early stopping / hyperparameter selection
        - test: for final OOD performance reporting
        - conformal_cal: 15% subset of training data reserved for conformal
          prediction calibration (separate from model training)

        The conformal calibration set is carved out of training indices to
        ensure it never leaks into model fitting.
        """
        split = self.build_split()
        rng = np.random.default_rng(self.split_config.random_seed + 1)

        # Carve out conformal calibration subset from training indices
        train_idx = list(split.train_indices)
        rng.shuffle(train_idx)
        n_cal = max(1, int(len(train_idx) * self.conformal_cal_fraction))
        cal_idx = train_idx[:n_cal]
        fit_idx = train_idx[n_cal:]

        def _make_subset(indices: list[int], shuffle: bool) -> DataLoader:
            from torch.utils.data import Subset

            subset = Subset(self.dataset, indices)
            return DataLoader(
                subset,
                batch_size=self.batch_size,
                shuffle=shuffle,
                num_workers=self.num_workers,
                collate_fn=collate_model_batches,
                pin_memory=torch.cuda.is_available(),
            )

        train_dl = _make_subset(fit_idx, shuffle=True)
        val_dl = _make_subset(split.val_indices, shuffle=False)
        test_dl = _make_subset(split.test_indices, shuffle=False)
        cal_dl = _make_subset(cal_idx, shuffle=False)

        logger.info(
            "DataLoaders built | fit=%d val=%d test=%d cp_cal=%d",
            len(fit_idx),
            len(split.val_indices),
            len(split.test_indices),
            len(cal_idx),
        )
        return train_dl, val_dl, test_dl, cal_dl
