# KyulAI Model Interface

For Domain Validation and QA teams.

---

## 1. Loading a Trained Model

```python
from src.ml.models import MLPSurrogate, CNNSurrogate, MLPConfig, CNNConfig
from pathlib import Path

# Load from checkpoint (saves model_name + state_dict)
model = MLPSurrogate(config=cfg)
model = MLPSurrogate.load_state("checkpoints/best.pt", model)
model.eval()

# Or use the registry for dynamic loading
from src.ml.models import MODEL_REGISTRY
ModelClass = MODEL_REGISTRY["mlp"]  # or "cnn"
model = ModelClass(config=cfg)
ModelClass.load_state("checkpoints/best.pt", model)
```

---

## 2. Input/Output Tensor Shapes

### Input: `ModelBatch`

| Field | Shape | Dtype | Notes |
|-------|-------|-------|-------|
| `process_features` | `(B, D_in)` | float32 | D_in = 56 (FeatureExtractor.FEATURE_DIM) |
| `feature_mask` | `(B, D_in)` | bool | True where feature was present in source record |
| `grid_input` | `(B, C_in, H, W)` or `(B, C_in, D, H, W)` | float32 | CNN only; None for MLP |
| `target_scalars` | `{field: (B, N_nodes)}` | float32 | Ground truth; absent at inference |
| `target_vectors` | `{field: (B, N_nodes, 3)}` | float32 | Ground truth; absent at inference |
| `target_tensors` | `{field: (B, N_nodes, ...)}` | float32 | Ground truth; absent at inference |
| `source_tools` | `list[str]` len B | str | CAE tool identifier per sample |
| `record_ids` | `list[str]` len B | str | Unique record ID per sample |

### Output: `ModelOutput`

| Field | Shape | Notes |
|-------|-------|-------|
| `pred_scalars` | `{field: (B, N_nodes)}` | Scalar field predictions |
| `pred_vectors` | `{field: (B, N_nodes, 3)}` | Vector field predictions |
| `pred_tensors` | `{field: (B, N_nodes, ...)}` | Tensor field predictions |
| `uncertainty` | `{field: tensor}` or None | Populated by `predict_with_uncertainty` |
| `aux` | `dict` | Model-specific extras (latent codes, bottleneck maps) |

### Concrete model shapes

**MLPSurrogate**
- Input: `(B, 56)` process feature vector
- Output per head: `(B, N_output)` where N_output is configured per field

**CNNSurrogate**
- Input: `(B, C_in, H, W)` for 2D or `(B, C_in, D, H, W)` for 3D
- Output: same spatial resolution as input (U-Net architecture preserves spatial dims)
- FiLM conditioning: optionally uses `process_features` to modulate bottleneck

---

## 3. Getting Predictions with Uncertainty Intervals

### MC Dropout (MLPSurrogate, requires `dropout > 0`)

```python
from src.ml.models import ModelBatch
import torch

batch = ModelBatch(
    process_features=torch.randn(4, 56),
    feature_mask=torch.ones(4, 56, dtype=torch.bool),
)

# Point prediction (no uncertainty)
output = model.predict(batch)
pred = output.pred_scalars["temperature"]  # (4, N_nodes)

# MC Dropout uncertainty (30 forward passes with dropout enabled)
output, uncertainty = model.predict_with_uncertainty(batch, n_samples=30)
pred_mean = output.pred_scalars["temperature"]        # (4, N_nodes)
pred_std = uncertainty["temperature"]                  # (4, N_nodes)

# 90% prediction interval (Gaussian approximation, pre-conformal calibration)
z90 = 1.6449
lower_90 = pred_mean - z90 * pred_std
upper_90 = pred_mean + z90 * pred_std
```

### Conformal Prediction (CQR, post-hoc calibration — Phase 3)

```python
# After training, use the CP calibration set (15% of train, held out by CAEDataLoader)
from mapie.regression import MapieRegressor  # or: custom CQR

# Compute nonconformity scores on calibration set
cal_preds = model.predict(cal_batch).pred_scalars["temperature"]
nonconformity_scores = torch.abs(cal_targets - cal_preds).numpy()
quantile_90 = np.quantile(nonconformity_scores, 0.9 * (1 + 1/len(cal_preds)))

# At inference:
pred = model.predict(new_batch).pred_scalars["temperature"]
interval = (pred - quantile_90, pred + quantile_90)
relative_width = (2 * quantile_90) / (pred.abs() + 1e-8)

# Flag predictions with interval width > 25% for human review
wide_mask = relative_width > 0.25
```

---

## 4. OOD Evaluation

Per the Research Team's recommendation (MaterialDA, arXiv 2308.02937): random splits
overestimate performance by 2–5×. All final results must use OOD splits.

```python
from src.ml.evaluation import OODEvaluationProtocol

protocol = OODEvaluationProtocol(
    model=model,
    device="cuda",
    iid_threshold=0.20,   # 20% relative L2 = Phase 1 IID target
    ood_threshold=0.50,   # 50% relative L2 = Phase 1 OOD target
)

result = protocol.run(iid_loader, ood_loader)
print(result.summary())
result.save_json("outputs/ood_eval.json")

# Check acceptance
if result.all_fields_pass:
    print("Model passes Phase 1 acceptance criteria.")
```

### OOD split dimensions

| Axis | Description | ood_column |
|------|-------------|------------|
| Process parameter OOD | Unseen manufacturing condition range | `mold_temperature_K` |
| Geometry OOD | Curved parts vs. flat laminates | `geometry.part_type` |
| Material OOD | GFRP vs. CFRP | `metadata.material_system` |
| Cross-tool | Test on Abaqus, train on Moldex3D | `metadata.source_tool` |
| Experimental | Real coupon vs. simulation | `metadata.is_experimental` |

---

## 5. KyulAISample Data Schema

```python
from src.ml.training.data import KyulAISample
import torch

sample = KyulAISample(
    process_params=torch.tensor([...], dtype=torch.float32),  # shape (56,)
    simulation_fields={
        "fiber_orientation_a11": torch.tensor([...]),  # shape (N_nodes,)
    },
    experimental_targets=None,        # None for simulation records
    tool_name="moldex3d",             # one of 6 CAE tools or "experiment"
    fidelity_level=1,                 # 1–5 per NARGP hierarchy
    sample_id="moldex3d_run_00001",
)
```

**Fidelity hierarchy:**

| Level | Tool | Cost | Target N |
|-------|------|------|----------|
| 1 | Moldex3D fast | ~5 min | 5,000 runs |
| 2 | Digimat MF | ~60 min | 500 runs |
| 3 | Abaqus linear | ~120 min | 200 runs |
| 4 | Abaqus nonlinear | ~480 min | 50 runs |
| 5 | Experiment | ~3 days | 20 coupons |

---

## 6. Conformal Calibration Integration (Post-hoc)

Conformal Prediction (CQR) provides provable coverage guarantees with no architecture
changes. It wraps any trained surrogate:

**Protocol:**
1. Reserve 15% of simulation runs as CP calibration set (separate from training, done by `CAEDataLoader.build_loaders()`).
2. After training, compute nonconformity scores on calibration set.
3. Compute quantile at `0.9 * (1 + 1/n_cal)` for 90% coverage guarantee.
4. At inference: add/subtract quantile to point prediction.
5. Recalibrate quarterly or when >20% new data is added.

**CQR for heteroscedastic data** (uncertainty varies with process params):
Use quantile regression loss in training plus conformal calibration of quantile residuals.
This is planned for Phase 3 when sufficient experimental data is available.

---

## 7. Physics Validation Integration Points

The Domain Validation team hooks into the following model interface points:

| Hook | When | Purpose |
|------|------|---------|
| `model.physics_loss(batch, output)` | During training | PDE residual loss (Phase 2 PINO models) |
| `output.aux["latent"]` | Post-forward | Latent code for multi-fidelity NARGP chain |
| `output.aux["bottleneck"]` | Post-forward (CNN) | Spatial feature map for physics checks |
| `uncertainty` dict from `predict_with_uncertainty` | Inference | Wide intervals flag OOD inputs for review |
| `EvaluationReport.generate_report(...)` | Post-training | Markdown report with per-field metrics |

For Phase 2 PINO models: override `physics_loss()` in the model subclass to return
a PDE residual scalar. The trainer multiplies by `TrainingConfig.physics_loss_weight`
(set to 0 in Phase 1 baseline).

---

## 8. Quick-Reference: Metric Thresholds

| Phase | Split | Metric | Target |
|-------|-------|--------|--------|
| Phase 1 | IID val | Relative L2 | < 20% |
| Phase 1 | IID val | R² | > 0.90 |
| Phase 2 (PINO) | IID val | Relative L2 | < 5% |
| Phase 2 (PINO) | OOD | Relative L2 | < 15% |
| Phase 3 (fine-tuned) | Experimental OOD | Relative L2 | < 25% |

Conformal Prediction interval width > 25% on any input triggers human review flag.
