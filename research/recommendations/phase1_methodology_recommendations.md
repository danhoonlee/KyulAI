# Phase 1 Methodology Recommendations for KyulAI

**From:** Research & Paper Analysis Team  
**To:** AI/ML Team, Domain Validation Team, Data Engineering Team  
**Date:** 2026-04-08  
**Status:** Final — Phase 1  

---

## Core Recommendation: The KyulAI Stack

Based on the Phase 1 literature survey (9 papers, 7 domains), we recommend the following architecture and methodology stack:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          KyulAI Core ML Stack                                │
├──────────────────┬──────────────────────────────────────────────────────────┤
│ Layer            │ Recommendation                                             │
├──────────────────┼──────────────────────────────────────────────────────────┤
│ Backbone         │ PINO (Physics-Informed Neural Operator) with Geo-FNO      │
│                  │ for regular/semi-regular domains + MeshGraphNets for      │
│                  │ unstructured Abaqus FEA meshes                            │
├──────────────────┼──────────────────────────────────────────────────────────┤
│ Multi-Fidelity   │ NARGP-inspired nonlinear autoregressive fusion across    │
│ Fusion           │ the 5-level CAE fidelity hierarchy                        │
├──────────────────┼──────────────────────────────────────────────────────────┤
│ Sim-to-Real      │ Pretraining on simulation data → fine-tuning on          │
│ Adaptation       │ experimental coupon data (10–100 samples)                 │
├──────────────────┼──────────────────────────────────────────────────────────┤
│ UQ Layer         │ Conformal Prediction (CQR variant) wrapped around        │
│                  │ all deployed models                                        │
├──────────────────┼──────────────────────────────────────────────────────────┤
│ Evaluation       │ OOD-split evaluation protocol (not random splits)         │
└──────────────────┴──────────────────────────────────────────────────────────┘
```

---

## Top 5 Prioritized Approaches

### Priority 1 — PINO (Physics-Informed Neural Operator) as Primary Backbone
**Evidence:** Papers 02, 03, 08 | **Confidence:** High

**Why:** FNO and its physics-informed variant (PINO) are the strongest operators for the structured simulation fields that KyulAI produces. PINO combines:
- The operator-learning framework (maps functions to functions — correct abstraction for CAE)
- Physics constraints (PDE residual loss) that reduce training data requirements by 5–10×
- Zero-shot super-resolution (train on coarse meshes, infer on fine)
- Differentiable inference enabling gradient-based process optimization

**Specific application mapping:**

| CAE Tool | Output Field | Recommended Architecture |
|----------|-------------|--------------------------|
| Moldex3D (RTM/SMC) | Fiber orientation tensor field, fill fraction | PINO / Geo-FNO |
| AniForm | Fiber angle redistribution, thickness | PINO / Geo-FNO |
| Digimat | Effective stiffness tensor (per ply) | FNO on regular homogenization grid |
| Abaqus (linear) | Stress field, strain field on FE mesh | MeshGraphNets + PINN loss |
| Abaqus (nonlinear) | Progressive damage field | Hybrid DNS-NO (Paper 08) |
| Simutence | Multi-process coupled fields | Multi-fidelity PINO chain |

**Implementation steps:**
1. Install `neuraloperator` library (PyTorch-based FNO/PINO implementation)
2. Build Moldex3D data parser → convert output to regular-grid fiber orientation tensors
3. Train first PINO surrogate on Moldex3D fiber orientation prediction
4. Validate: compare PINO predictions vs. held-out Moldex3D runs (target: <5% relative L² error)

---

### Priority 2 — MeshGraphNets for Abaqus Structural Surrogates
**Evidence:** Paper 04 | **Confidence:** High

**Why:** Abaqus FEA outputs live on unstructured tetrahedral/hexahedral meshes. FNO cannot natively handle irregular meshes. MeshGraphNets (or its X-MeshGraphNets extension) is the correct architecture:
- Native unstructured mesh handling via GNN message passing
- Node-level field prediction (stress, strain at each integration point)
- Generalizes across mesh topologies with the same trained model
- `torch-geometric` library already in KyulAI tech stack

**Critical composite-specific engineering:** encode anisotropy correctly in node features:
```python
# Node feature vector for each FE integration point
node_features = torch.cat([
    position,                    # (x, y, z) — 3D
    fiber_orientation_tensor,    # (a11, a12, a13, a22, a23, a33) — 6 components
    ply_angle,                   # scalar
    ply_index,                   # one-hot encoded
    local_fiber_volume_fraction, # scalar
    manufacturing_defect_flag,   # binary
], dim=-1)
```

**Implementation steps:**
1. Build Abaqus .odb parser (Data Engineering Team) → extract mesh, material orientations, BCs, loads
2. Convert to PyG (PyTorch Geometric) heterogeneous graph
3. Implement MeshGraphNets with noise injection training (critical for rollout stability)
4. Train on 500+ Abaqus structural simulation pairs
5. Fine-tune on DIC (Digital Image Correlation) experimental strain maps

---

### Priority 3 — Two-Stage Pretraining + Fine-Tuning (Sim-to-Real Adaptation)
**Evidence:** Papers 01, 05 | **Confidence:** Very high

**Why:** The strongest and most consistently validated finding in the literature. Both papers independently confirm that pretraining on simulation data + fine-tuning on experimental data outperforms all alternatives, including sophisticated domain adaptation methods.

**The KyulAI fine-tuning protocol:**

```
Stage 1 — Simulation Pretraining:
  Data: All available CAE simulation runs (target: 10,000+ runs per process)
  Model: PINO or MeshGraphNets backbone
  Loss: MSE on field predictions + physics residuals
  Duration: Until validation loss converges (typically 50–200 epochs)
  Output: Pretrained weights W_sim

Stage 2 — Experimental Fine-Tuning:
  Data: Experimental coupon tests (start with 10–50; scale to 200+)
  Init: Load W_sim (frozen backbone, trainable head layers)
  Loss: MSE on measured properties (modulus, strength, failure load)
  Learning rate: 10–100× lower than pretraining
  Output: Production model W_real

Stage 3 — Conformal Calibration:
  Data: Reserve 20% of experimental data as calibration set (separate from fine-tuning)
  Method: CQR conformal calibration on fine-tuned model
  Output: Prediction intervals with guaranteed 90% or 95% coverage
```

**What NOT to do** (MaterialDA finding): Do not implement DANN, MMD, or CORAL adversarial domain adaptation as the primary sim-to-real strategy. These consistently fail or show marginal gains in materials settings.

**Data acquisition guidance** (Sim2Real scaling law):
- The power-law N^{-0.3 to -0.5} means doubling simulation data reduces error by ~20–35%
- First 1,000 simulation runs provide the biggest bang per simulation
- Experimental data is ~100× more valuable than simulation data per sample
- Aim for: 10,000 simulation runs → 50–100 experimental coupons per material system

---

### Priority 4 — NARGP Multi-Fidelity Fusion Across CAE Tool Hierarchy
**Evidence:** Paper 06 | **Confidence:** High

**Why:** KyulAI's 6 CAE tools form a natural multi-fidelity hierarchy. Running full Abaqus nonlinear FEA for every design point is infeasible; but ignoring the wealth of cheaper simulation data (Moldex3D, Digimat fast mode) wastes information. NARGP-inspired fusion extracts maximum value from the full hierarchy.

**The KyulAI fidelity hierarchy:**

```python
FIDELITY_LEVELS = {
    1: {"tool": "Moldex3D_fast", "cost_min": 5,    "n_target": 5000},
    2: {"tool": "Digimat_MF",   "cost_min": 60,   "n_target": 500},
    3: {"tool": "Abaqus_linear","cost_min": 120,  "n_target": 200},
    4: {"tool": "Abaqus_NL",   "cost_min": 480,  "n_target": 50},
    5: {"tool": "Experiment",  "cost_days": 3,   "n_target": 20},
}
```

**Nonlinear multi-fidelity fusion architecture:**
- Train Level 1 surrogate (PINO) on 5,000 Moldex3D runs
- Train Level 2 surrogate taking (design params + Level 1 prediction) as input — on 500 Digimat runs
- Continue up the chain
- At Level 5 (experimental): 20 data points is sufficient to fit a calibration GP layer

**Key advantage:** this decoupled training allows incremental data collection — start with cheap simulations, add expensive simulations and experiments as project progresses.

---

### Priority 5 — Conformal Prediction for All Deployed Models
**Evidence:** Paper 07 | **Confidence:** Very high

**Why:** KyulAI's project requirements mandate physics validation before any model is considered "ready." Conformal Prediction provides the only approach with a provable coverage guarantee that works with any surrogate architecture.

**Non-negotiable UQ requirements for KyulAI:**
1. Every model prediction must ship with a calibrated prediction interval
2. Interval width must be logged and monitored (wide intervals = model needs more data or retraining)
3. Models must be flagged when deployed on inputs outside their calibration distribution

**Implementation (post-hoc, no architecture changes required):**

```python
from mapie.regression import MapieRegressor  # or: use custom CQR implementation

# After training the surrogate model:
calibration_predictions = surrogate.predict(X_calibration)
nonconformity_scores = np.abs(y_calibration - calibration_predictions)
quantile_90 = np.quantile(nonconformity_scores, 0.9 * (1 + 1/len(X_calibration)))

# At inference time:
prediction = surrogate.predict(x_new)
interval = (prediction - quantile_90, prediction + quantile_90)
relative_width = (2 * quantile_90) / abs(prediction)

if relative_width > 0.25:  # >25% interval width = flag for review
    flag_for_human_review(prediction, interval, x_new)
```

**Calibration data strategy:**
- Reserve 15% of all simulation runs as a CP calibration set (separate from training)
- Additionally reserve 20% of experimental measurements as calibration set for the fine-tuned model
- Recalibrate after every major data addition (quarterly or when >20% new data added)

---

## Implementation Roadmap

### Phase 2 (Months 1–3): Infrastructure + First Surrogate
1. [Data Eng] Build Moldex3D parser, output → fiber orientation tensor grid
2. [Data Eng] Build Abaqus .odb parser, output → PyG heterogeneous graph
3. [AI/ML] Implement FNO/PINO on Moldex3D fiber orientation task
4. [AI/ML] Implement MeshGraphNets on Abaqus linear FEA task
5. [Domain Val] Define OOD evaluation protocol (process parameter ranges for test)
6. [Domain Val] Implement conformal calibration wrapper (CQR)

### Phase 3 (Months 4–6): Multi-Fidelity + Sim-to-Real
1. [AI/ML] Implement multi-fidelity fusion layer (NARGP or deep GP)
2. [AI/ML] Collect initial experimental coupon data (target: 30–50 samples)
3. [AI/ML] Execute fine-tuning protocol on experimental data
4. [Domain Val] Validate predictions against test coupons (OOD split)
5. [AI/ML] Iterate: active learning to select most informative next experiments

### Phase 4 (Months 7–12): Production + Continuous Learning
1. [Backend] Deploy surrogate models as FastAPI endpoints with CP intervals
2. [MLOps] MLflow tracking: every prediction logged with inputs, outputs, interval width
3. [AI/ML] Implement online fine-tuning as new experimental data arrives
4. [Frontend] Build UI for design space exploration with uncertainty visualization

---

## Decision Log (For Future Reference)

| Decision | Choice | Rationale | Papers |
|----------|--------|-----------|--------|
| Primary backbone | PINO (not pure PINN, not pure data-driven) | Physics constraints + operator learning combine best properties | 02, 03 |
| Mesh handling | MeshGraphNets for Abaqus | Only viable approach for unstructured FE meshes | 04 |
| Sim-to-Real method | Fine-tuning (not adversarial DA) | Consistently strongest in materials domain | 01, 05 |
| Multi-fidelity | Nonlinear autoregressive fusion | Linear K&O fails for nonlinear cross-tool correlations | 06 |
| UQ method | Conformal Prediction | Only provable coverage guarantee, model-agnostic | 07 |
| Evaluation | OOD splits (not random) | Random splits overestimate performance by 2–5× | 05 |
| Hybrid simulation | DNS-NO hybrid for time-evolving processes | Prevents error accumulation in long rollouts | 08 |

---

## Papers Cited in This Report

1. Minami et al. (2025) — [Sim2Real Scaling Law, npj CM](https://arxiv.org/abs/2408.04042)
2. Li, Kovachki et al. (2021) — [FNO, ICLR](https://arxiv.org/abs/2010.08895)
3. Autoclave PINO team (2025) — [Composites PINO, arXiv 2502.11504](https://arxiv.org/abs/2502.11504)
4. Pfaff et al. (2021) — [MeshGraphNets, ICLR](https://arxiv.org/abs/2010.03409)
5. Hu et al. (2023) — [MaterialDA, arXiv 2308.02937](https://arxiv.org/abs/2308.02937)
6. Perdikaris et al. (2017) — [NARGP, Proc. Royal Society A](https://royalsocietypublishing.org/doi/10.1098/rspa.2016.0751)
7. Gopakumar et al. (2024) — [CP for Surrogates, arXiv 2408.09881](https://arxiv.org/abs/2408.09881)
8. Oommen et al. (2024) — [DNS+NO hybrid, npj CM](https://arxiv.org/abs/2312.05410)
9. Composite plates PINN (2025) — [ScienceDirect, Composite Structures](https://www.sciencedirect.com/science/article/pii/S0263823125001089)
