# KyulAI Model Interface — Phase 1

**For: Domain Validation Team, QA Team**
**Produced by: AI/ML Team**

This document describes the interface that all Phase 1 surrogate models expose.
It is the contract you should test against.  Model internals may change; this
interface will not change without notice.

---

## Core Data Structures

### `ModelBatch` (`src/ml/models/base.py`)

The standard input passed to every model's `forward()` call.

| Field | Type | Shape | Description |
|---|---|---|---|
| `process_features` | `torch.Tensor` | `(B, D_in)` | Scaled, masked feature vector extracted from `UnifiedCAERecord.input_fields` + `metadata.process_parameters`. `D_in = 56` in Phase 1 (see Feature Registry below). |
| `feature_mask` | `torch.Tensor` (bool) | `(B, D_in)` | `True` where feature was present in the record. Models zero-out positions where mask is `False`. |
| `grid_input` | `torch.Tensor \| None` | `(B, C, *spatial)` | Structured spatial grid for CNN path only. `None` for MLP. |
| `target_scalars` | `dict[str, Tensor]` | `{field: (B, N)}` | Ground truth scalar field values. Absent at inference time. |
| `target_vectors` | `dict[str, Tensor]` | `{field: (B, N, 3)}` | Ground truth vector field values. Absent at inference time. |
| `target_tensors` | `dict[str, Tensor]` | `{field: (B, N, ...)}` | Ground truth tensor field values. Absent at inference time. |
| `source_tools` | `list[str]` | `len = B` | CAE tool that generated each record. One of: `moldex3d`, `aniform`, `digimat`, `abaqus`, `simutence`, `cadfil`. |
| `record_ids` | `list[str]` | `len = B` | UUID string of each `UnifiedCAERecord`. |

### `ModelOutput` (`src/ml/models/base.py`)

The standard output from every model's `forward()` call.

| Field | Type | Description |
|---|---|---|
| `pred_scalars` | `dict[str, Tensor]` | Predicted scalar fields `{field_name: (B, N)}`. |
| `pred_vectors` | `dict[str, Tensor]` | Predicted vector fields `{field_name: (B, N, 3)}`. |
| `pred_tensors` | `dict[str, Tensor]` | Predicted tensor fields `{field_name: (B, N, ...)}`. |
| `uncertainty` | `dict[str, Tensor] \| None` | Epistemic uncertainty. **Always `None` in Phase 1**. Will be populated in Phase 3. |
| `aux` | `dict[str, Any]` | Model-specific extras. **Do not depend on these outside the model.** |

**Invariants:**
- `output.predicted_field_names` == the `output_field_names` property of the model.
- If field `f` is in `batch.target_scalars`, `output.pred_scalars[f]` has the **same shape** as `batch.target_scalars[f]`.
- `uncertainty` is `None` in all Phase 1 models (no UQ yet).

---

## Model Classes

### `MLPSurrogate` (`src/ml/models/surrogates/mlp.py`)

Maps flat process features to output field predictions.

**When to use:** Process parameter → field prediction for any CAE tool.
Particularly useful when geometry is fixed (same mesh across all simulations).

**Forward pass contract:**
```python
batch = ModelBatch(
    process_features=torch.randn(B, 56),   # B samples, 56 features
    feature_mask=torch.ones(B, 56, dtype=torch.bool),
    # target_* populated during training, absent at inference
)
output = model(batch)
# output.pred_scalars["temperature"].shape == (B, N_nodes)
```

**Key invariants for QA:**
- `batch.process_features` and `feature_mask` are the **only required fields**.
- `batch.grid_input` is **ignored**.
- Output shape matches `output_heads` config: `{field: (B, n_values)}`.

### `CNNSurrogate` (`src/ml/models/surrogates/cnn.py`)

U-Net encoder-decoder for structured spatial grids.

**When to use:** RVE microstructure (Digimat), structured mesh slices (Moldex3D).

**Forward pass contract:**
```python
batch = ModelBatch(
    process_features=torch.randn(B, 56),     # used for FiLM conditioning
    feature_mask=torch.ones(B, 56, dtype=torch.bool),
    grid_input=torch.randn(B, C_in, H, W),  # 2D grid; (B, C, D, H, W) for 3D
)
output = model(batch)
# output.pred_scalars["stress_vm"].shape == (B, H*W) for 2D
```

**Key invariants for QA:**
- `batch.grid_input` **must not be None** — raises `ValueError` otherwise.
- Output spatial shape matches input spatial shape (U-Net preserves resolution).
- FiLM conditioning is applied **only** when `config.process_feature_dim > 0`.

---

## Shared Interface (`KyulBaseModel`)

Every model exposes these methods.  QA and Domain Validation should call
**only** these:

```python
# Forward pass (with gradient)
output: ModelOutput = model(batch)

# Inference (no gradient, model.eval() set automatically)
output: ModelOutput = model.predict(batch)

# Which fields does this model predict?
names: list[str] = model.output_field_names

# Parameter count (for logging)
n: int = model.count_parameters()

# Save / load checkpoint
model.save("checkpoints/best.pt")
KyulBaseModel.load_state("checkpoints/best.pt", model)
```

---

## Feature Registry

The feature extractor produces a `D_in = 56` float32 vector from each
`UnifiedCAERecord`.  Features are ordered as below.  All values are
scaled to O(1) range; missing values are 0.0 with mask=False.

| Index | Feature Name | Scale | Source |
|---|---|---|---|
| 0 | `mold_temperature_K` | 300 K | `metadata.process_parameters` |
| 1 | `cure_temperature_K` | 450 K | `metadata.process_parameters` |
| 2 | `ambient_temperature_K` | 300 K | `metadata.process_parameters` |
| 3 | `injection_pressure_MPa` | 10 MPa | `metadata.process_parameters` |
| 4 | `compaction_pressure_MPa` | 0.7 MPa | `metadata.process_parameters` |
| 5 | `blank_holder_force_kN` | 100 kN | `metadata.process_parameters` |
| 6 | `fill_time_s` | 60 s | `metadata.process_parameters` |
| 7 | `cure_time_s` | 3600 s | `metadata.process_parameters` |
| 8 | `cycle_time_s` | 7200 s | `metadata.process_parameters` |
| 9 | `fiber_volume_fraction` | 0.6 | `metadata.process_parameters` |
| 10 | `fiber_weight_fraction` | 0.6 | `metadata.process_parameters` |
| 11 | `winding_angle_deg` | 90° | `metadata.process_parameters` |
| 12 | `band_width_mm` | 10 mm | `metadata.process_parameters` |
| 13 | `num_plies` | 20 | `metadata.process_parameters` |
| 14 | `density_kg_per_m3` | 1600 kg/m³ | `input_fields.material_properties` |
| 15 | `youngs_modulus_GPa` | 70 GPa | isotropic elastic |
| 16 | `poisson_ratio` | 0.3 | isotropic elastic |
| 17 | `shear_modulus_GPa` | 30 GPa | isotropic elastic |
| 18 | `E1_GPa` | 150 GPa | transversely isotropic |
| 19 | `E2_GPa` | 10 GPa | transversely isotropic |
| 20 | `G12_GPa` | 5 GPa | transversely isotropic |
| 21 | `G23_GPa` | 4 GPa | transversely isotropic |
| 22 | `nu12` | 0.3 | transversely isotropic |
| 23 | `nu23` | 0.4 | transversely isotropic |
| 24 | `thermal_conductivity_W_mK` | 5 W/mK | thermal |
| 25 | `specific_heat_J_kgK` | 1000 J/kgK | thermal |
| 26 | `cte_per_K_1e6` | 30 µ/K | thermal |
| 27 | `glass_transition_K` | 450 K | thermal |
| 28 | `fiber_diameter_um` | 7 µm | fiber |
| 29 | `fiber_density_kg_m3` | 1800 kg/m³ | fiber |
| 30 | `fiber_modulus_GPa` | 230 GPa | fiber |
| 31 | `fiber_strength_GPa` | 4 GPa | fiber |
| 32 | `fiber_aspect_ratio` | 100 | fiber |
| 33–35 | `applied_force_[xyz]_N` | 10,000 N | loading conditions |
| 36 | `applied_pressure_MPa` | 10 MPa | loading conditions |
| 37 | `applied_temperature_K` | 400 K | loading conditions |
| 38 | `friction_coefficient` | 0.3 | process conditions |
| 39 | `forming_speed_mm_s` | 10 mm/s | process conditions |
| 40 | `winding_tension_N` | 50 N | process conditions |
| 41 | `num_nodes_log10` | 5 | geometry (log₁₀) |
| 42 | `num_elements_log10` | 5 | geometry (log₁₀) |
| 43–48 | `tool_*` (one-hot) | 1 | source tool indicator |
| 49–55 | `simtype_*` (one-hot) | 1 | simulation type indicator |

To get the authoritative list at runtime:
```python
from src.ml.training import FEATURE_NAMES, FEATURE_DIM
print(FEATURE_DIM)    # 56 (or updated count)
print(FEATURE_NAMES)  # ordered list of all feature names
```

---

## Evaluation Interface

```python
from src.ml.evaluation import ModelEvaluator, EvaluationReport

evaluator = ModelEvaluator(model, device="cuda", split="val")
report: EvaluationReport = evaluator.evaluate(val_loader)

# Key attributes
report.overall           # dict[str, float]: aggregate MSE, RMSE, MAE, R², RelL2
report.per_field         # dict[str, FieldMetrics]: one entry per predicted field
report.per_tool          # dict[tool, dict[field, FieldMetrics]]: per CAE tool

# Save for artifact logging
report.save_json("outputs/eval_report.json")
print(report.summary_table())
```

**Metrics in `FieldMetrics`:** `mse`, `rmse`, `mae`, `r2`, `relative_l2`,
`max_abs_error`, `normalised_mae`.

---

## Phase 1 Acceptance Criteria

These thresholds are the AI/ML team's targets.  Domain Validation should verify
that models meeting these criteria also satisfy physics plausibility checks.

| Criterion | Threshold |
|---|---|
| Val R² per scalar field | ≥ 0.85 (stretch goal: 0.90) |
| Relative L2 error | ≤ 0.10 (10%) |
| Max absolute error | Within ±3σ of field range |
| Training must not diverge | train_loss monotonically non-increasing over last 20 epochs |

---

## What Phase 2 Will Add

- `physics_loss(batch, output) -> Tensor | None` — already stubbed in
  `KyulBaseModel`, returns `None` in all Phase 1 models.
- GNN surrogate for unstructured meshes (via `torch_geometric`).
- Neural operator (FNO/PINO) for resolution-invariant field prediction.
- None of these change the `ModelBatch` / `ModelOutput` interface.

---

## Questions?

Contact the AI/ML team lead or open an issue tagged `ai-ml`.
