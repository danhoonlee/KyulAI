"""Data interface contract for KyulAI ML training.

Defines the canonical data model and dataset abstractions that the Data
Engineering team implements and the AI/ML team consumes.

KyulAISample is the atomic unit of data flowing through the pipeline:
  - Produced by CAE parsers (Data Engineering team)
  - Consumed by Dataset.__getitem__ (AI/ML team)
  - Validated by Domain Validation team (physics checks on targets)

Design decisions:
  - Pydantic v2 for KyulAISample: validates at the data boundary so model
    code never sees malformed inputs.
  - SimulationDataset: concrete stub backed by HDF5; structure is defined,
    load impl defers to the Data Engineering team's HDF5 schema.
  - create_dataloaders: stratified split by fidelity_level when possible,
    per the Research Team's multi-fidelity hierarchy recommendation.
  - OOD splits (not random) are mandatory for final reporting; the random
    split here is the training split only.
"""

from __future__ import annotations

import abc
import logging
from pathlib import Path
from typing import Any

import torch
from pydantic import BaseModel, Field, model_validator
from torch.utils.data import DataLoader, Dataset, Subset

logger = logging.getLogger(__name__)


# ── Data model ────────────────────────────────────────────────────────────────


class KyulAISample(BaseModel):
    """Atomic data sample flowing from CAE parsers to model inputs.

    This Pydantic model is the contract between the Data Engineering team
    (which populates it from CAE output files) and the AI/ML team (which
    reads it to construct training tensors).

    Fidelity hierarchy (Research Team recommendation, NARGP multi-fidelity):
        1 = Moldex3D fast mode (~5 min)
        2 = Digimat mean-field (~60 min)
        3 = Abaqus linear FEA (~120 min)
        4 = Abaqus nonlinear FEA (~480 min)
        5 = Experimental coupon test (days)

    All tensor fields carry their natural physical shape before batching.
    The DataLoader's collate_fn handles padding to a common shape per batch.
    """

    # ── Inputs ────────────────────────────────────────────────────────────────
    process_params: torch.Tensor = Field(
        ...,
        description=(
            "Flat feature vector of process parameters and material properties. "
            "Shape (D_in,).  Produced by FeatureExtractor.extract(record)."
        ),
    )
    simulation_fields: dict[str, torch.Tensor] = Field(
        default_factory=dict,
        description=(
            "Intermediate spatial fields from this simulation level "
            "(e.g. fiber orientation tensor grid from Moldex3D).  "
            "Used as input to higher-fidelity models in the NARGP chain."
        ),
    )

    # ── Targets ───────────────────────────────────────────────────────────────
    experimental_targets: dict[str, torch.Tensor] | None = Field(
        None,
        description=(
            "Ground truth measurements from physical coupon tests. "
            "None for pure simulation records (fidelity_level < 5). "
            "When present, drives sim-to-real fine-tuning."
        ),
    )

    # ── Metadata ──────────────────────────────────────────────────────────────
    tool_name: str = Field(
        ...,
        description=(
            "Source CAE tool: 'moldex3d' | 'aniform' | 'digimat' | "
            "'abaqus' | 'simutence' | 'cadfil' | 'experiment'."
        ),
    )
    fidelity_level: int = Field(
        ...,
        ge=1,
        le=5,
        description="Fidelity level in the NARGP hierarchy (1 = cheapest, 5 = experiment).",
    )
    sample_id: str = Field(
        ...,
        description="Unique identifier for this sample (UUID or file path stem).",
    )

    model_config = {
        "arbitrary_types_allowed": True,
        "extra": "forbid",
    }

    @model_validator(mode="after")
    def _experimental_targets_require_level5(self) -> KyulAISample:
        if self.fidelity_level == 5 and self.experimental_targets is None:
            logger.warning(
                "Sample %s has fidelity_level=5 (experiment) but no experimental_targets.",
                self.sample_id,
            )
        return self


# ── Abstract dataset ──────────────────────────────────────────────────────────


class KyulAIDataset(Dataset, abc.ABC):
    """Abstract base dataset for KyulAI ML training.

    Subclasses must implement __len__ and __getitem__ returning KyulAISample.
    The Data Engineering team provides the concrete implementations backed
    by HDF5, database queries, or in-memory lists.
    """

    @abc.abstractmethod
    def __len__(self) -> int:
        """Total number of samples in this dataset."""

    @abc.abstractmethod
    def __getitem__(self, idx: int) -> KyulAISample:
        """Return the KyulAISample at position idx."""

    def fidelity_levels(self) -> list[int]:
        """Return per-sample fidelity levels for stratified splitting.

        Default: linear scan over __getitem__ — override for efficient
        implementations (e.g., read from HDF5 metadata without loading tensors).
        """
        return [self[i].fidelity_level for i in range(len(self))]


# ── Concrete stub: SimulationDataset (HDF5-backed) ────────────────────────────


class SimulationDataset(KyulAIDataset):
    """Simulation dataset loading KyulAISamples from an HDF5 file.

    HDF5 structure (defined, implementation deferred to Data Engineering team):

        /samples/{sample_id}/
            process_params          float32 (D_in,)
            fidelity_level          int8    scalar
            tool_name               bytes   scalar
            simulation_fields/{field_name}  float32 (...)
            experimental_targets/{field_name}  float32 (...)   [optional]

    Parameters
    ----------
    hdf5_path:
        Path to the HDF5 file produced by the Data Engineering pipeline.
    fidelity_filter:
        If specified, only load samples at these fidelity levels.
        Useful for training level-specific models in the NARGP chain.
    """

    def __init__(
        self,
        hdf5_path: Path | str,
        fidelity_filter: list[int] | None = None,
    ) -> None:
        self._path = Path(hdf5_path)
        self._fidelity_filter = fidelity_filter
        self._sample_ids: list[str] = self._index_samples()

    def _index_samples(self) -> list[str]:
        """Build the sample index from HDF5 metadata (stub).

        The Data Engineering team implements the actual HDF5 reading logic.
        This stub returns an empty list so the class can be instantiated
        and the interface validated without data.
        """
        if not self._path.exists():
            logger.warning(
                "SimulationDataset: HDF5 file not found at %s — returning empty dataset.",
                self._path,
            )
            return []

        try:
            import h5py  # lazy import
        except ImportError:
            logger.warning("h5py not installed — SimulationDataset stub will be empty.")
            return []

        with h5py.File(self._path, "r") as f:
            all_ids = list(f.get("samples", {}).keys())

        if self._fidelity_filter is not None:
            filtered: list[str] = []
            try:
                import h5py

                with h5py.File(self._path, "r") as f:
                    for sid in all_ids:
                        lvl = int(f[f"samples/{sid}/fidelity_level"][()])
                        if lvl in self._fidelity_filter:
                            filtered.append(sid)
            except Exception as exc:
                logger.error("Error filtering by fidelity: %s", exc)
                filtered = all_ids
            return filtered

        return all_ids

    def __len__(self) -> int:
        return len(self._sample_ids)

    def __getitem__(self, idx: int) -> KyulAISample:
        """Load and return the sample at position idx from HDF5 (stub).

        The Data Engineering team replaces the stub body with actual HDF5
        reads.  The return type contract (KyulAISample) must not change.
        """
        # Stub: Data Engineering team implements HDF5 loading here.
        raise NotImplementedError(
            "SimulationDataset.__getitem__ is a stub.  "
            "The Data Engineering team provides the HDF5 load implementation."
        )

    def fidelity_levels(self) -> list[int]:
        """Efficient fidelity level index without loading full samples."""
        if not self._path.exists():
            return []

        try:
            import h5py
        except ImportError:
            return []

        levels: list[int] = []
        try:
            with h5py.File(self._path, "r") as f:
                for sid in self._sample_ids:
                    lvl = int(f[f"samples/{sid}/fidelity_level"][()])
                    levels.append(lvl)
        except Exception as exc:
            logger.error("Error reading fidelity levels from HDF5: %s", exc)
        return levels


# ── DataLoader factory ────────────────────────────────────────────────────────


def _collate_kyulai_samples(samples: list[KyulAISample]) -> dict[str, Any]:
    """Collate a list of KyulAISamples into batch tensors.

    Returns a dict (not a single tensor) so the caller can unpack fields
    by name.  Models access process_params, simulation_fields, etc. directly.
    """
    process_params = torch.stack([s.process_params for s in samples], dim=0)
    fidelity_levels = torch.tensor([s.fidelity_level for s in samples], dtype=torch.long)
    tool_names = [s.tool_name for s in samples]
    sample_ids = [s.sample_id for s in samples]

    # Collate simulation_fields: only include fields present in all samples
    all_sim_keys = set(samples[0].simulation_fields.keys())
    sim_fields_batch: dict[str, torch.Tensor] = {}
    for key in all_sim_keys:
        if all(key in s.simulation_fields for s in samples):
            sim_fields_batch[key] = torch.stack([s.simulation_fields[key] for s in samples], dim=0)

    # Collate experimental_targets (optional)
    exp_targets_batch: dict[str, torch.Tensor] | None = None
    if any(s.experimental_targets is not None for s in samples):
        exp_keys: set[str] = set()
        for s in samples:
            if s.experimental_targets:
                exp_keys.update(s.experimental_targets.keys())
        exp_targets_batch = {}
        for key in exp_keys:
            tensors = [
                s.experimental_targets[key]
                for s in samples
                if s.experimental_targets and key in s.experimental_targets
            ]
            if len(tensors) == len(samples):
                exp_targets_batch[key] = torch.stack(tensors, dim=0)

    return {
        "process_params": process_params,
        "simulation_fields": sim_fields_batch,
        "experimental_targets": exp_targets_batch,
        "fidelity_levels": fidelity_levels,
        "tool_names": tool_names,
        "sample_ids": sample_ids,
    }


def create_dataloaders(
    dataset: KyulAIDataset,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    batch_size: int = 32,
    seed: int = 42,
    num_workers: int = 0,
) -> tuple[DataLoader, DataLoader, DataLoader]:
    """Split a KyulAIDataset and return (train, val, test) DataLoaders.

    Splitting strategy:
    - Stratified by fidelity_level when possible: ensures each split has
      representative samples from each level of the NARGP hierarchy.
    - Falls back to random split when fidelity level metadata is unavailable
      or when the dataset is too small for stratification.

    The conformal calibration set (15% of train) is NOT carved out here —
    that is the responsibility of CAEDataLoader.build_loaders(), which is
    called when training with simulation data.  This factory is for the
    simplified KyulAISample-based pipeline.

    Parameters
    ----------
    dataset:
        Any KyulAIDataset subclass.
    train_ratio, val_ratio, test_ratio:
        Split fractions — must sum to 1.0.
    batch_size:
        Batch size for all loaders.
    seed:
        Random seed for reproducibility.
    num_workers:
        DataLoader worker processes (0 = main process).

    Returns
    -------
    (train_loader, val_loader, test_loader)
    """
    total = train_ratio + val_ratio + test_ratio
    if not (0.999 < total < 1.001):
        raise ValueError(f"train_ratio + val_ratio + test_ratio must equal 1.0, got {total:.4f}")

    n = len(dataset)
    if n == 0:
        raise ValueError("Dataset is empty — cannot create DataLoaders.")

    import numpy as np

    rng = np.random.default_rng(seed)

    # Attempt stratified split by fidelity_level
    try:
        fidelity_levels = dataset.fidelity_levels()
        stratified = len(fidelity_levels) == n and len(fidelity_levels) > 0
    except Exception:
        stratified = False
        fidelity_levels = []

    if stratified:
        train_idx, val_idx, test_idx = _stratified_split(
            fidelity_levels, train_ratio, val_ratio, test_ratio, rng
        )
        logger.info(
            "Stratified split by fidelity_level | train=%d val=%d test=%d",
            len(train_idx),
            len(val_idx),
            len(test_idx),
        )
    else:
        indices = rng.permutation(n).tolist()
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)
        train_idx = indices[:n_train]
        val_idx = indices[n_train : n_train + n_val]
        test_idx = indices[n_train + n_val :]
        logger.info(
            "Random split (fidelity info unavailable) | train=%d val=%d test=%d",
            len(train_idx),
            len(val_idx),
            len(test_idx),
        )

    def _make_loader(indices: list[int], shuffle: bool) -> DataLoader:
        subset = Subset(dataset, indices)
        return DataLoader(
            subset,
            batch_size=batch_size,
            shuffle=shuffle,
            num_workers=num_workers,
            collate_fn=_collate_kyulai_samples,
            pin_memory=torch.cuda.is_available(),
        )

    return (
        _make_loader(train_idx, shuffle=True),
        _make_loader(val_idx, shuffle=False),
        _make_loader(test_idx, shuffle=False),
    )


def _stratified_split(
    fidelity_levels: list[int],
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
    rng: Any,
) -> tuple[list[int], list[int], list[int]]:
    """Stratified split that preserves fidelity_level distribution across splits."""
    import numpy as np

    levels = np.array(fidelity_levels)
    unique = np.unique(levels)

    train_idx: list[int] = []
    val_idx: list[int] = []
    test_idx: list[int] = []

    for lvl in unique:
        lvl_indices = np.where(levels == lvl)[0].tolist()
        rng.shuffle(lvl_indices)
        n = len(lvl_indices)
        n_train = max(1, int(n * train_ratio))
        n_val = max(0, int(n * val_ratio))
        # Assign remainder to test
        train_idx.extend(lvl_indices[:n_train])
        val_idx.extend(lvl_indices[n_train : n_train + n_val])
        test_idx.extend(lvl_indices[n_train + n_val :])

    return train_idx, val_idx, test_idx
