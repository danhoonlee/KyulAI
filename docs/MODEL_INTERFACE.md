# KyulAI Model Interface Specification

**Audience:** Domain Validation Team, QA Team, Backend Team
**Maintained by:** AI/ML Team
**Version:** 1.0 (Phase 1 Baseline)
**Date:** 2026-04-08

---

## Overview

All KyulAI surrogate models implement the `KyulBaseModel` interface
(`src/ml/models/base.py`).  This document describes:

1. The input/output contract (what models accept and return)
2. What the Domain Validation Team should test
3. What the QA Team should assert
4. How the Backend Team should call models at inference time

---

## 1. Core Interface Contract

### 1.1 Input: `ModelBatch`

All models accept a single `ModelBatch` dataclass:

```python
@dataclass
class ModelBatch:
    process_features: torch.Tensor   # (B, D_in) — process/material features
    feature_mask: torch.Tensor        # (B, D_in) bool — True = value present
    grid_input: torch.Tensor | None   # (B, C, *spatial) — CNN models only
    target_scalars: dict[str, Tensor] # {field_name: (B, N_nodes)} — training only
    target_vectors: dict[str, Tensor] # {field_name: (B, N_nodes, 3)}
    target_tensors: dict[str, Tensor] # {field_name: (B, N_nodes, ...)}
    source_tools: list[str]           # length B — CAE tool identifier
    record_ids: list[str]             # length B — UnifiedCAERecord UUIDs
```

**Feature vector layout:** The `process_features` tensor is produced by
`FeatureExtractor` from `src/ml/training/feature_extractor.py`.  The feature
order is defined by `FEATURE_REGISTRY` (55 features, 55-dimensional vector as
of Phase 1).  The `feature_mask` is `True` where the original field was not
`None` — all masked positions are zeroed before the model sees them.

**At inference time:** `target_*` dicts are empty.  Only `process_features`,
`feature_mask`, and (for CNNs) `grid_input` are required.

### 1.2 Output: `ModelOutput`

All models return a `ModelOutput` dataclass:

```python
@dataclass
class ModelOutput:
    pred_scalars: dict[str, Tensor]   # {field_name: (B, N_nodes)}
    pred_vectors: dict[str, Tensor]   # {field_name: (B, N_nodes, 3)}
    pred_tensors: dict[str, Tensor]   # {field_name: (B, N_nodes, ...)}
    uncertainty: dict[str, Tensor] | None  # None in Phase 1; populated Phase 3
    aux: dict[str, Any]               # latent codes, bottleneck features, etc.
```

**Phase 1 note:** `uncertainty` is always `None` in Phase 1 models.  The
Domain Validation Team should NOT assert on uncertainty at this stage.  Phase 3
adds Conformal Prediction intervals (see Section 4).

### 1.3 Required Methods

Every model must implement:

| Method | Signature | Description |
|--------|-----------|-------------|
| `forward(batch)` | `ModelBatch → ModelOutput` | Full forward pass with gradient tracking |
| `predict(batch)` | `ModelBatch → ModelOutput` | No-grad inference (calls `forward` internally) |
| `output_field_names` | `property → list[str]` | Names of all predicted fields |
| `from_config(config)` | `classmethod → KyulBaseModel` | Construct from Pydantic config |
| `count_parameters()` | `() → int` | Trainable parameter count |
| `save(path)` | `Path → None` | Save checkpoint |
| `physics_loss(batch, output)` | `→ Tensor | None` | Physics residual (None in Phase 1) |

---

## 2. Phase 1 Model Catalogue

### 2.1 MLP Surrogate (`MLPSurrogate`)

| Property | Value |
|----------|-------|
| Architecture | Shared MLP backbone + per-field linear heads |
| Input | `process_features` (B, D_in) |
| Output | Per-field predictions (scalar, vector, or tensor) |
| Config class | `MLPConfig` |
| Config file | `src/ml/configs/model/mlp.yaml` |
| Feature masking | Yes — missing inputs zeroed before backbone |
| Residual connections | Optional (when hidden dims match) |
| Activation | Configurable (GELU default) |
| Normalisation | Configurable (LayerNorm default) |
| Physics loss | Returns `None` (Phase 1) |

**Primary use case:** Any CAE tool where outputs can be represented as
per-node scalar, vector, or tensor fields derived from global process parameters.

**Phase 2 extension path:** Replace the backbone with an FNO or PINO encoder.
The per-field head interface stays the same.

### 2.2 CNN Surrogate (`CNNSurrogate`)

| Property | Value |
|----------|-------|
| Architecture | U-Net with FiLM process-parameter conditioning |
| Input | `grid_input` (B, C, *spatial) + `process_features` (B, D_in) |
| Output | Per-field spatial predictions |
| Config class | `CNNConfig` |
| Config file | `src/ml/configs/model/cnn.yaml` |
| Spatial dims | 2D or 3D (configurable) |
| Skip connections | U-Net style (configurable) |
| FiLM conditioning | Enabled when `process_feature_dim > 0` |
| Physics loss | Returns `None` (Phase 1) |

**Primary use case:**
- Digimat RVE microstructure analysis (3D voxel grids)
- Moldex3D flow results on regular 2D/3D meshes

**Phase 2 extension path:** Replace the encoder with a Geo-FNO or PINO operator
that is discretisation-invariant.

---

## 3. Domain Validation Team: What to Test

### 3.1 Physics Plausibility Checks (per field)

The Domain Validation Team must verify predictions against known physical bounds
before any model is approved for production.

| Field | Physical constraint | Action if violated |
|-------|--------------------|--------------------|
| Temperature (K) | Must be > 0 K | Flag prediction; retrain |
| Cure degree (-) | Must be in [0, 1] | Apply sigmoid clamp or flag |
| Fiber orientation (A2 trace) | Trace = A11+A22+A33 must equal 1.0 | Flag records where |trace-1| > 0.05 |
| Stress tensor | Must be symmetric: S_ij = S_ji | Enforce symmetry in post-processing |
| Displacement | Must satisfy equilibrium (see force balance check) | Physics loss residual |
| Fill fraction | Must be in [0, 1] | Flag prediction |

### 3.2 OOD Performance Monitoring

Use `OODEvaluationProtocol` (`src/ml/evaluation/ood_protocol.py`):

```python
from src.ml.evaluation.ood_protocol import OODEvaluationProtocol

protocol = OODEvaluationProtocol(
    model=model,
    iid_threshold=0.20,   # Phase 1 baseline: <20% relative L2 on IID
    ood_threshold=0.50,   # Phase 1 baseline: <50% relative L2 on OOD
)
result = protocol.run(iid_test_loader, ood_test_loader)
result.save_json("domain_validation/ood_report.json")
```

**Key OOD splits to run** (per Research Team recommendations):
1. Process parameter OOD (train on T_mold=200°C, test on T_mold=250°C)
2. Material OOD (train on CFRP, test on GFRP)
3. Geometry OOD (train on flat laminates, test on curved panels)
4. Cross-tool OOD (train on Moldex3D, evaluate on Abaqus-linked records)

### 3.3 Uncertainty Quantification (Phase 3 — plan now)

In Phase 3, all models will be wrapped with Conformal Quantile Regression (CQR).
The Domain Validation Team should:
- Reserve 15% of simulation data as a CP calibration set (separate from training)
- Reserve 20% of experimental measurements as a CP calibration set
- Monitor that interval widths are reasonable: relative width < 25% = acceptable
- Flag predictions where relative interval width > 25% for human review

---

## 4. QA Team: Assertion Checklist

For each model checkpoint, the QA team must run:

### 4.1 Shape Tests
```python
# For MLPSurrogate with temperature head (1000 nodes)
batch = ModelBatch(
    process_features=torch.randn(4, 55),  # FEATURE_DIM = 55
    feature_mask=torch.ones(4, 55, dtype=torch.bool),
)
output = model.predict(batch)
assert output.pred_scalars["temperature"].shape == (4, 1000)
```

### 4.2 No NaN/Inf in Output
```python
for field_name, pred in output.pred_scalars.items():
    assert torch.isfinite(pred).all(), f"NaN/Inf in {field_name}"
```

### 4.3 Feature Mask Respected
```python
zero_mask = torch.zeros(1, 55, dtype=torch.bool)
batch_zero = ModelBatch(process_features=features, feature_mask=zero_mask)
batch_full = ModelBatch(process_features=features, feature_mask=ones_mask)
# Zeroed features → different predictions (model is sensitive to masking)
assert not torch.allclose(model.predict(batch_zero).pred_scalars["x"],
                           model.predict(batch_full).pred_scalars["x"])
```

### 4.4 Checkpoint Round-Trip
```python
model.save("test_checkpoint.pt")
model2 = MLPSurrogate.from_config(config)
KyulBaseModel.load_state("test_checkpoint.pt", model2)
assert torch.allclose(model.predict(batch).pred_scalars["x"],
                      model2.predict(batch).pred_scalars["x"], atol=1e-6)
```

### 4.5 Physics Loss Returns None (Phase 1)
```python
assert model.physics_loss(batch, output) is None
```

### 4.6 Performance Regression Test
After each training run, compare against the baseline:
```python
assert result.best_val_loss < BASELINE_VAL_LOSS * 1.05  # within 5% of baseline
```

---

## 5. Backend Team: Inference API

### 5.1 Calling a Model at Inference Time

```python
from src.ml.models import MLPSurrogate, MLPConfig, ModelBatch, KyulBaseModel
from src.ml.training.feature_extractor import FeatureExtractor, Normalizer
import torch

# Load model
model = MLPSurrogate.from_config(config)
KyulBaseModel.load_state("checkpoints/phase1_mlp_temperature/best.pt", model)
model.eval()

# Load normalizer (saved alongside checkpoint)
normalizer = Normalizer.load("checkpoints/phase1_mlp_temperature/normalizer.npz")
extractor = FeatureExtractor()

# Construct input from a UnifiedCAERecord
features, mask = extractor.extract(record)
features_normed = normalizer.transform(features)

batch = ModelBatch(
    process_features=torch.from_numpy(features_normed).unsqueeze(0),  # (1, D)
    feature_mask=torch.from_numpy(mask).unsqueeze(0),
)

# Run inference
with torch.no_grad():
    output = model.predict(batch)

# Extract prediction
temperature_field = output.pred_scalars["temperature"][0].numpy()  # (N_nodes,)
```

### 5.2 Response Schema (for FastAPI)

The Backend Team's FastAPI endpoint should return:

```json
{
  "record_id": "uuid-string",
  "model_name": "mlp_surrogate",
  "model_version": "phase1_mlp_temperature_v1",
  "predictions": {
    "temperature": [/* N_nodes float values */],
    "cure_degree": [/* N_nodes float values */]
  },
  "uncertainty": null,
  "prediction_interval_lower": null,
  "prediction_interval_upper": null,
  "relative_interval_width": null,
  "flags": []
}
```

When Phase 3 CP is active, `uncertainty` and `prediction_interval_*` are
populated.  `flags` contains human-review flags when `relative_interval_width
> 0.25`.

---

## 6. Feature Vector Reference

The feature vector produced by `FeatureExtractor` has `FEATURE_DIM = 55`
elements (Phase 1).  Key groups:

| Group | Features | Count |
|-------|----------|-------|
| Process parameters | mold_temperature, cure_temperature, injection_pressure, ... | 14 |
| Material: density | density_kg_per_m3 | 1 |
| Material: elastic (isotropic) | E, nu, G | 3 |
| Material: elastic (transversely isotropic) | E1, E2, G12, G23, nu12, nu23 | 6 |
| Material: thermal | k, Cp, CTE, Tg | 4 |
| Material: fiber | diameter, density, modulus, strength, aspect_ratio | 5 |
| Loading conditions | Fx, Fy, Fz, pressure, temperature | 5 |
| Process conditions | friction, forming_speed, winding_tension | 3 |
| Geometry statistics | log10(num_nodes), log10(num_elements) | 2 |
| Tool one-hot | moldex3d, aniform, digimat, abaqus, simutence, cadfil | 6 |
| Simulation type one-hot | structural, flow, thermal, forming, curing, winding, micromechanics | 7 |

Full feature names: `from src.ml.training.feature_extractor import FEATURE_NAMES`

---

## 7. Phase Roadmap for This Interface

| Phase | Change | Impact |
|-------|--------|--------|
| Phase 1 (current) | MLP + CNN baselines | This document |
| Phase 2 | Add FNO/PINO surrogates (same `forward` interface) | Extend `ModelConfig` union |
| Phase 2 | Add MeshGraphNets (graph inputs via `torch_geometric`) | New `graph_inputs` field in `ModelBatch` |
| Phase 3 | Conformal Prediction wrapper | `uncertainty` field in `ModelOutput` populated |
| Phase 3 | Fine-tuning protocol (frozen backbone) | No interface change |
| Phase 3 | Importance weighting (RULSIF/BW) | Training-only change |

---

*This document is maintained by the AI/ML Team.  Changes to the model
interface must be communicated to Domain Validation, QA, and Backend Teams
before merging.*
