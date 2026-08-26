"""Feature extractor: converts UnifiedCAERecord → flat feature tensor.

This module defines the contract between the Data Engineering team's unified
schema and the ML team's models.  All feature engineering lives here so that
model code stays schema-agnostic.

Design principles
-----------------
1. Fixed-length output: every record produces a vector of the same size regardless
   of which fields are populated, using a mask to flag missing values.
2. SI-unit normalization: raw SI values are divided by characteristic scales to
   keep features in a numerically well-conditioned range (~O(1)).
3. Registry-driven: features are defined as a flat list of ``FeatureSpec`` entries.
   Adding a new feature = adding one entry to FEATURE_REGISTRY.
4. Stateless extraction + stateful normalization: extraction is pure; normalization
   parameters (mean/std) are computed from the dataset and stored in a Normalizer.

Usage
-----
    extractor = FeatureExtractor()
    features, mask = extractor.extract(record)   # numpy arrays
    # or in bulk:
    dataset_features = extractor.extract_batch(records)
    normalizer = Normalizer.fit(dataset_features)
    normed = normalizer.transform(dataset_features)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from src.data.schemas.record import UnifiedCAERecord

# ── Feature specification ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class FeatureSpec:
    """Specification of a single scalar feature extracted from a UnifiedCAERecord.

    Attributes
    ----------
    name:
        Unique feature name (used for logging and config serialisation).
    extractor:
        Callable that receives a ``UnifiedCAERecord`` and returns ``float | None``.
        Return ``None`` to indicate the field is absent for this record; the
        feature vector will get 0.0 and the mask will be set to False.
    scale:
        Characteristic SI-unit scale factor.  The raw value is divided by this
        before being stored in the tensor.  Choose so that typical values ≈ 1.
    """

    name: str
    extractor: Callable[[UnifiedCAERecord], float | None]
    scale: float = 1.0


# ── Helper shorthands ─────────────────────────────────────────────────────────


def _pp(record: UnifiedCAERecord):
    """Shorthand for process_parameters."""
    return record.metadata.process_parameters


def _mat(record: UnifiedCAERecord):
    """Shorthand for material_properties."""
    return record.input_fields.material_properties


def _el(record: UnifiedCAERecord):
    """Shorthand for elastic properties."""
    return record.input_fields.material_properties.elastic


def _th(record: UnifiedCAERecord):
    """Shorthand for thermal properties."""
    return record.input_fields.material_properties.thermal


def _fib(record: UnifiedCAERecord):
    """Shorthand for fiber properties."""
    return record.input_fields.material_properties.fiber


def _lc(record: UnifiedCAERecord):
    """Shorthand for loading conditions."""
    return record.input_fields.loading_conditions


def _proc(record: UnifiedCAERecord):
    """Shorthand for process conditions."""
    return record.input_fields.process_conditions


# ── Feature registry ──────────────────────────────────────────────────────────
# Order is stable and defines the feature vector layout.
# Do NOT re-order entries — it would break existing checkpoints.
# Append new features at the end.

FEATURE_REGISTRY: list[FeatureSpec] = [
    # ── Process parameters (from metadata) ────────────────────────────────────
    FeatureSpec("mold_temperature_K", lambda r: _pp(r).mold_temperature_K, scale=300.0),
    FeatureSpec("cure_temperature_K", lambda r: _pp(r).cure_temperature_K, scale=450.0),
    FeatureSpec("ambient_temperature_K", lambda r: _pp(r).ambient_temperature_K, scale=300.0),
    FeatureSpec(
        "injection_pressure_MPa",
        lambda r: _pp(r).injection_pressure_Pa / 1e6 if _pp(r).injection_pressure_Pa else None,
        scale=10.0,
    ),
    FeatureSpec(
        "compaction_pressure_MPa",
        lambda r: _pp(r).compaction_pressure_Pa / 1e6 if _pp(r).compaction_pressure_Pa else None,
        scale=0.7,
    ),
    FeatureSpec(
        "blank_holder_force_kN",
        lambda r: _pp(r).blank_holder_force_N / 1e3 if _pp(r).blank_holder_force_N else None,
        scale=100.0,
    ),
    FeatureSpec("fill_time_s", lambda r: _pp(r).fill_time_s, scale=60.0),
    FeatureSpec("cure_time_s", lambda r: _pp(r).cure_time_s, scale=3600.0),
    FeatureSpec("cycle_time_s", lambda r: _pp(r).cycle_time_s, scale=7200.0),
    FeatureSpec("fiber_volume_fraction", lambda r: _pp(r).fiber_volume_fraction, scale=0.6),
    FeatureSpec("fiber_weight_fraction", lambda r: _pp(r).fiber_weight_fraction, scale=0.6),
    FeatureSpec("winding_angle_deg", lambda r: _pp(r).winding_angle_deg, scale=90.0),
    FeatureSpec(
        "band_width_mm",
        lambda r: _pp(r).band_width_m * 1e3 if _pp(r).band_width_m else None,
        scale=10.0,
    ),
    FeatureSpec(
        "num_plies", lambda r: float(_pp(r).num_plies) if _pp(r).num_plies else None, scale=20.0
    ),
    # ── Material: density ─────────────────────────────────────────────────────
    FeatureSpec("density_kg_per_m3", lambda r: _mat(r).density_kg_per_m3, scale=1600.0),
    # ── Material: elastic (isotropic) ─────────────────────────────────────────
    FeatureSpec(
        "youngs_modulus_GPa",
        lambda r: _el(r).youngs_modulus_Pa / 1e9 if _el(r).youngs_modulus_Pa else None,
        scale=70.0,
    ),
    FeatureSpec("poisson_ratio", lambda r: _el(r).poisson_ratio, scale=0.3),
    FeatureSpec(
        "shear_modulus_GPa",
        lambda r: _el(r).shear_modulus_Pa / 1e9 if _el(r).shear_modulus_Pa else None,
        scale=30.0,
    ),
    # ── Material: elastic (transversely isotropic) ────────────────────────────
    FeatureSpec("E1_GPa", lambda r: _el(r).E1_Pa / 1e9 if _el(r).E1_Pa else None, scale=150.0),
    FeatureSpec("E2_GPa", lambda r: _el(r).E2_Pa / 1e9 if _el(r).E2_Pa else None, scale=10.0),
    FeatureSpec("G12_GPa", lambda r: _el(r).G12_Pa / 1e9 if _el(r).G12_Pa else None, scale=5.0),
    FeatureSpec("G23_GPa", lambda r: _el(r).G23_Pa / 1e9 if _el(r).G23_Pa else None, scale=4.0),
    FeatureSpec("nu12", lambda r: _el(r).nu12, scale=0.3),
    FeatureSpec("nu23", lambda r: _el(r).nu23, scale=0.4),
    # ── Material: thermal ─────────────────────────────────────────────────────
    FeatureSpec(
        "thermal_conductivity_W_mK",
        lambda r: (
            _th(r).thermal_conductivity_W_per_mK
            if isinstance(_th(r).thermal_conductivity_W_per_mK, float)
            else None
        ),
        scale=5.0,
    ),
    FeatureSpec("specific_heat_J_kgK", lambda r: _th(r).specific_heat_J_per_kgK, scale=1000.0),
    FeatureSpec(
        "cte_per_K_1e6",
        lambda r: (
            _th(r).cte_per_K * 1e6
            if isinstance(_th(r).cte_per_K, float) and _th(r).cte_per_K is not None
            else None
        ),
        scale=30.0,
    ),
    FeatureSpec("glass_transition_K", lambda r: _th(r).glass_transition_K, scale=450.0),
    # ── Material: fiber ───────────────────────────────────────────────────────
    FeatureSpec(
        "fiber_diameter_um",
        lambda r: _fib(r).fiber_diameter_m * 1e6 if _fib(r).fiber_diameter_m else None,
        scale=7.0,
    ),
    FeatureSpec("fiber_density_kg_m3", lambda r: _fib(r).fiber_density_kg_per_m3, scale=1800.0),
    FeatureSpec(
        "fiber_modulus_GPa",
        lambda r: _fib(r).fiber_modulus_Pa / 1e9 if _fib(r).fiber_modulus_Pa else None,
        scale=230.0,
    ),
    FeatureSpec(
        "fiber_strength_GPa",
        lambda r: _fib(r).fiber_strength_Pa / 1e9 if _fib(r).fiber_strength_Pa else None,
        scale=4.0,
    ),
    FeatureSpec("fiber_aspect_ratio", lambda r: _fib(r).fiber_aspect_ratio, scale=100.0),
    # ── Loading conditions ────────────────────────────────────────────────────
    FeatureSpec(
        "applied_force_x_N",
        lambda r: _lc(r).applied_force_N[0] if _lc(r).applied_force_N else None,
        scale=10000.0,
    ),
    FeatureSpec(
        "applied_force_y_N",
        lambda r: _lc(r).applied_force_N[1] if _lc(r).applied_force_N else None,
        scale=10000.0,
    ),
    FeatureSpec(
        "applied_force_z_N",
        lambda r: _lc(r).applied_force_N[2] if _lc(r).applied_force_N else None,
        scale=10000.0,
    ),
    FeatureSpec(
        "applied_pressure_MPa",
        lambda r: _lc(r).applied_pressure_Pa / 1e6 if _lc(r).applied_pressure_Pa else None,
        scale=10.0,
    ),
    FeatureSpec("applied_temperature_K", lambda r: _lc(r).applied_temperature_K, scale=400.0),
    # ── Process conditions ────────────────────────────────────────────────────
    FeatureSpec("friction_coefficient", lambda r: _proc(r).friction_coefficient, scale=0.3),
    FeatureSpec(
        "forming_speed_mm_s",
        lambda r: _proc(r).forming_speed_m_per_s * 1000 if _proc(r).forming_speed_m_per_s else None,
        scale=10.0,
    ),
    FeatureSpec("winding_tension_N", lambda r: _proc(r).winding_tension_N, scale=50.0),
    # ── Geometry summary statistics ───────────────────────────────────────────
    FeatureSpec(
        "num_nodes_log10",
        lambda r: float(np.log10(r.geometry.num_nodes)) if r.geometry.num_nodes > 0 else None,
        scale=5.0,
    ),
    FeatureSpec(
        "num_elements_log10",
        lambda r: (
            float(np.log10(r.geometry.num_elements))
            if r.geometry.num_elements and r.geometry.num_elements > 0
            else None
        ),
        scale=5.0,
    ),
    # ── Tool / simulation type one-hot encoding ───────────────────────────────
    # These are split out as individual binary features so the model learns
    # tool-specific offsets without needing an embedding table.
    FeatureSpec(
        "tool_moldex3d",
        lambda r: 1.0 if r.metadata.source_tool.value == "moldex3d" else 0.0,
        scale=1.0,
    ),
    FeatureSpec(
        "tool_aniform",
        lambda r: 1.0 if r.metadata.source_tool.value == "aniform" else 0.0,
        scale=1.0,
    ),
    FeatureSpec(
        "tool_digimat",
        lambda r: 1.0 if r.metadata.source_tool.value == "digimat" else 0.0,
        scale=1.0,
    ),
    FeatureSpec(
        "tool_abaqus", lambda r: 1.0 if r.metadata.source_tool.value == "abaqus" else 0.0, scale=1.0
    ),
    FeatureSpec(
        "tool_simutence",
        lambda r: 1.0 if r.metadata.source_tool.value == "simutence" else 0.0,
        scale=1.0,
    ),
    FeatureSpec(
        "tool_cadfil", lambda r: 1.0 if r.metadata.source_tool.value == "cadfil" else 0.0, scale=1.0
    ),
    # ── Simulation type one-hot ───────────────────────────────────────────────
    FeatureSpec(
        "simtype_structural",
        lambda r: 1.0 if r.metadata.simulation_type.value == "structural" else 0.0,
        scale=1.0,
    ),
    FeatureSpec(
        "simtype_flow",
        lambda r: 1.0 if r.metadata.simulation_type.value == "flow" else 0.0,
        scale=1.0,
    ),
    FeatureSpec(
        "simtype_thermal",
        lambda r: 1.0 if r.metadata.simulation_type.value == "thermal" else 0.0,
        scale=1.0,
    ),
    FeatureSpec(
        "simtype_forming",
        lambda r: 1.0 if r.metadata.simulation_type.value == "forming" else 0.0,
        scale=1.0,
    ),
    FeatureSpec(
        "simtype_curing",
        lambda r: 1.0 if r.metadata.simulation_type.value == "curing" else 0.0,
        scale=1.0,
    ),
    FeatureSpec(
        "simtype_winding",
        lambda r: 1.0 if r.metadata.simulation_type.value == "winding" else 0.0,
        scale=1.0,
    ),
    FeatureSpec(
        "simtype_micromechanics",
        lambda r: 1.0 if r.metadata.simulation_type.value == "micromechanics" else 0.0,
        scale=1.0,
    ),
]

FEATURE_DIM: int = len(FEATURE_REGISTRY)
FEATURE_NAMES: list[str] = [f.name for f in FEATURE_REGISTRY]


# ── Core extractor ────────────────────────────────────────────────────────────


class FeatureExtractor:
    """Converts a UnifiedCAERecord into a fixed-size numpy feature vector.

    Thread-safe and stateless — safe to use in DataLoader workers.

    Attributes
    ----------
    feature_dim:
        Length of the feature vector produced for each record.
    feature_names:
        Ordered list of feature names (aligns with vector positions).
    """

    def __init__(self, registry: list[FeatureSpec] | None = None) -> None:
        self._registry = registry or FEATURE_REGISTRY
        self.feature_dim = len(self._registry)
        self.feature_names = [f.name for f in self._registry]
        # Precompute scale array for vectorised division
        self._scales = np.array([f.scale for f in self._registry], dtype=np.float32)

    def extract(self, record: UnifiedCAERecord) -> tuple[np.ndarray, np.ndarray]:
        """Extract features from a single record.

        Returns
        -------
        features:
            Float32 array of shape (D,) with scaled feature values.
            Missing values are 0.0.
        mask:
            Bool array of shape (D,): True where the feature is present.
        """
        values = np.zeros(self.feature_dim, dtype=np.float32)
        mask = np.zeros(self.feature_dim, dtype=bool)

        for i, spec in enumerate(self._registry):
            try:
                val = spec.extractor(record)
            except Exception:
                val = None

            if val is not None and np.isfinite(val):
                values[i] = float(val) / spec.scale
                mask[i] = True

        return values, mask

    def extract_batch(self, records: list[UnifiedCAERecord]) -> tuple[np.ndarray, np.ndarray]:
        """Extract features from a list of records.

        Returns
        -------
        features: (N, D) float32
        masks: (N, D) bool
        """
        feats = np.zeros((len(records), self.feature_dim), dtype=np.float32)
        masks = np.zeros((len(records), self.feature_dim), dtype=bool)
        for i, rec in enumerate(records):
            feats[i], masks[i] = self.extract(rec)
        return feats, masks

    def to_tensor(self, record: UnifiedCAERecord, device: Any = "cpu") -> tuple[Any, Any]:
        """Extract and return as PyTorch tensors (unsqueezed to include batch dim)."""
        import torch  # lazy import — keeps this module torch-free at import time

        feats, mask = self.extract(record)
        return (
            torch.from_numpy(feats).unsqueeze(0).to(device),
            torch.from_numpy(mask).unsqueeze(0).to(device),
        )


# ── Normalizer ────────────────────────────────────────────────────────────────


class Normalizer:
    """Fit mean/std on training features and apply z-score normalisation.

    Only normalises features where the mask is True across enough samples.
    Features that are always missing are left at 0.0.

    Serialises to / from a plain numpy .npz file so it can be saved alongside
    model checkpoints without pickle dependencies.
    """

    def __init__(self, mean: np.ndarray, std: np.ndarray) -> None:
        self.mean = mean.astype(np.float32)
        self.std = std.astype(np.float32)

    @classmethod
    def fit(
        cls, features: np.ndarray, masks: np.ndarray, min_present_fraction: float = 0.01
    ) -> Normalizer:
        """Compute mean/std from (N, D) training features.

        Parameters
        ----------
        features:
            Pre-scaled feature matrix of shape (N, D).
        masks:
            Boolean mask matrix of shape (N, D).
        min_present_fraction:
            Features present in fewer than this fraction of records are left
            un-normalised (mean=0, std=1).
        """
        _N, D = features.shape
        mean = np.zeros(D, dtype=np.float32)
        std = np.ones(D, dtype=np.float32)

        for d in range(D):
            present = masks[:, d]
            if present.mean() >= min_present_fraction:
                vals = features[present, d]
                mean[d] = vals.mean()
                s = vals.std()
                std[d] = s if s > 1e-8 else 1.0

        return cls(mean, std)

    def transform(self, features: np.ndarray) -> np.ndarray:
        return (features - self.mean) / self.std

    def inverse_transform(self, features: np.ndarray) -> np.ndarray:
        return features * self.std + self.mean

    def save(self, path: Path | str) -> None:
        np.savez(path, mean=self.mean, std=self.std)

    @classmethod
    def load(cls, path: Path | str) -> Normalizer:
        data = np.load(path)
        return cls(mean=data["mean"], std=data["std"])

    def to_tensors(self, device: Any = "cpu") -> tuple[Any, Any]:
        """Return (mean, std) as tensors for in-model normalisation if desired."""
        import torch  # lazy import

        return (
            torch.from_numpy(self.mean).to(device),
            torch.from_numpy(self.std).to(device),
        )
