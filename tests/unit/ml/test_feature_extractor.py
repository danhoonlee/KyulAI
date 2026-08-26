"""Unit tests for the FeatureExtractor and Normalizer.

These tests use stub UnifiedCAERecord objects to verify feature extraction
without requiring actual CAE data files.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.ml.training.feature_extractor import (
    FEATURE_DIM,
    FEATURE_NAMES,
    FEATURE_REGISTRY,
    FeatureExtractor,
    FeatureSpec,
    Normalizer,
)

# ---------------------------------------------------------------------------
# Minimal stub for UnifiedCAERecord
# ---------------------------------------------------------------------------


class _StubFiber:
    fiber_diameter_m = 7e-6
    fiber_density_kg_per_m3 = 1800.0
    fiber_modulus_Pa = 230e9
    fiber_strength_Pa = 4e9
    fiber_aspect_ratio = 100.0
    tow_count = 12000


class _StubElastic:
    youngs_modulus_Pa = 70e9
    poisson_ratio = 0.33
    shear_modulus_Pa = None
    E1_Pa = 150e9
    E2_Pa = 10e9
    G12_Pa = 5e9
    G23_Pa = 4e9
    nu12 = 0.3
    nu23 = 0.4


class _StubThermal:
    thermal_conductivity_W_per_mK = 5.0
    specific_heat_J_per_kgK = 1000.0
    cte_per_K = 3e-5
    glass_transition_K = 420.0


class _StubRheological:
    pass


class _StubMaterial:
    density_kg_per_m3 = 1600.0
    elastic = _StubElastic()
    thermal = _StubThermal()
    fiber = _StubFiber()
    rheological = _StubRheological()
    strength = None


class _StubLoading:
    applied_force_N = [1000.0, 0.0, 0.0]
    applied_pressure_Pa = 1e5
    applied_temperature_K = 300.0
    applied_displacement_m = None
    temperature_profile = None
    extra = {}


class _StubProcess:
    cure_cycle = None
    injection_locations = None
    vent_locations = None
    tool_geometry_ref = None
    forming_speed_m_per_s = 0.01
    friction_coefficient = 0.3
    mandrel_geometry_ref = None
    winding_pattern = None
    winding_tension_N = None
    extra = {}


class _StubInputFields:
    material_properties = _StubMaterial()
    loading_conditions = _StubLoading()
    process_conditions = _StubProcess()


class _StubGeometry:
    num_nodes = 1000
    num_elements = 800


class _StubProcessParams:
    mold_temperature_K = 200.0
    cure_temperature_K = 180.0
    ambient_temperature_K = 25.0
    injection_pressure_Pa = 5e6
    compaction_pressure_Pa = None
    blank_holder_force_N = None
    fill_time_s = 60.0
    cure_time_s = 3600.0
    cycle_time_s = 7200.0
    fiber_volume_fraction = 0.55
    fiber_weight_fraction = None
    winding_angle_deg = None
    band_width_m = None
    num_plies = 8


class _StubSourceTool:
    value = "moldex3d"


class _StubSimType:
    value = "flow"


class _StubMetadata:
    source_tool = _StubSourceTool()
    simulation_type = _StubSimType()
    process_parameters = _StubProcessParams()


class _StubRecord:
    metadata = _StubMetadata()
    input_fields = _StubInputFields()
    geometry = _StubGeometry()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFeatureRegistry:
    def test_feature_dim_matches_registry_length(self):
        assert FEATURE_DIM == len(FEATURE_REGISTRY)

    def test_feature_names_length(self):
        assert len(FEATURE_NAMES) == FEATURE_DIM

    def test_all_names_unique(self):
        assert len(set(FEATURE_NAMES)) == len(FEATURE_NAMES), "Feature names must be unique"

    def test_all_scales_positive(self):
        for spec in FEATURE_REGISTRY:
            assert spec.scale > 0, f"Scale for '{spec.name}' must be positive"


class TestFeatureExtractor:
    def setup_method(self):
        self.extractor = FeatureExtractor()
        self.record = _StubRecord()

    def test_extract_returns_correct_shape(self):
        features, mask = self.extractor.extract(self.record)
        assert features.shape == (FEATURE_DIM,)
        assert mask.shape == (FEATURE_DIM,)

    def test_extract_dtype(self):
        features, mask = self.extractor.extract(self.record)
        assert features.dtype == np.float32
        assert mask.dtype == bool

    def test_mask_true_for_present_features(self):
        _features, mask = self.extractor.extract(self.record)
        # At least some features should be present
        assert mask.sum() > 0

    def test_masked_values_are_zero(self):
        features, mask = self.extractor.extract(self.record)
        # Wherever mask is False, feature should be 0
        assert np.all(features[~mask] == 0.0)

    def test_tool_one_hot_correct(self):
        features, _mask = self.extractor.extract(self.record)
        names = self.extractor.feature_names
        # moldex3d one-hot should be 1.0, others 0.0
        moldex_idx = names.index("tool_moldex3d")
        abaqus_idx = names.index("tool_abaqus")
        assert features[moldex_idx] == pytest.approx(1.0)
        assert features[abaqus_idx] == pytest.approx(0.0)

    def test_extract_batch_shape(self):
        records = [self.record] * 5
        feats, masks = self.extractor.extract_batch(records)
        assert feats.shape == (5, FEATURE_DIM)
        assert masks.shape == (5, FEATURE_DIM)

    def test_exception_in_extractor_yields_none(self):
        """If an extractor function raises, it should be caught and return 0/False."""
        # Create a spec that always raises
        bad_spec = FeatureSpec("bad_feature", lambda r: 1 / 0, scale=1.0)
        extractor = FeatureExtractor(registry=[bad_spec])
        record = _StubRecord()
        features, mask = extractor.extract(record)
        assert features[0] == 0.0
        assert mask[0] is np.bool_(False)

    def test_mold_temperature_scaled(self):
        features, mask = self.extractor.extract(self.record)
        names = self.extractor.feature_names
        idx = names.index("mold_temperature_K")
        # mold_temperature_K = 200.0, scale = 300.0 → expected = 200/300 ≈ 0.667
        assert mask[idx] is np.bool_(True)
        assert features[idx] == pytest.approx(200.0 / 300.0, rel=1e-4)

    def test_custom_registry(self):
        """Custom registry overrides the default."""
        custom_spec = FeatureSpec("custom_feat", lambda r: 1.0, scale=2.0)
        extractor = FeatureExtractor(registry=[custom_spec])
        features, _mask = extractor.extract(self.record)
        assert extractor.feature_dim == 1
        assert features[0] == pytest.approx(0.5)  # 1.0 / 2.0


class TestNormalizer:
    def test_fit_produces_sensible_stats(self):
        n, d = 100, 10
        features = np.random.randn(n, d).astype(np.float32) * 5 + 2
        masks = np.ones((n, d), dtype=bool)
        norm = Normalizer.fit(features, masks)
        assert norm.mean.shape == (d,)
        assert norm.std.shape == (d,)
        assert np.all(norm.std > 0)

    def test_transform_gives_approx_zero_mean_unit_std(self):
        n, d = 1000, 5
        features = np.random.randn(n, d).astype(np.float32) * 3 + 10
        masks = np.ones((n, d), dtype=bool)
        norm = Normalizer.fit(features, masks)
        normed = norm.transform(features)
        assert normed.mean() == pytest.approx(0.0, abs=0.2)
        assert normed.std() == pytest.approx(1.0, abs=0.2)

    def test_inverse_transform_roundtrip(self):
        n, d = 50, 4
        features = np.random.randn(n, d).astype(np.float32)
        masks = np.ones((n, d), dtype=bool)
        norm = Normalizer.fit(features, masks)
        normed = norm.transform(features)
        recovered = norm.inverse_transform(normed)
        assert np.allclose(features, recovered, atol=1e-5)

    def test_save_load_roundtrip(self, tmp_path):
        n, d = 20, 6
        features = np.random.randn(n, d).astype(np.float32)
        masks = np.ones((n, d), dtype=bool)
        norm = Normalizer.fit(features, masks)
        path = tmp_path / "norm.npz"
        norm.save(path)
        loaded = Normalizer.load(path)
        assert np.allclose(norm.mean, loaded.mean)
        assert np.allclose(norm.std, loaded.std)

    def test_missing_features_excluded_from_stats(self):
        """Features present in < min_present_fraction of records → mean=0, std=1."""
        n, d = 100, 3
        features = np.random.randn(n, d).astype(np.float32)
        masks = np.ones((n, d), dtype=bool)
        # Make feature index 1 always missing
        masks[:, 1] = False
        norm = Normalizer.fit(features, masks, min_present_fraction=0.5)
        assert norm.mean[1] == pytest.approx(0.0)
        assert norm.std[1] == pytest.approx(1.0)
