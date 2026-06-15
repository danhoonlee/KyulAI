# Uncertainty Quantification of Surrogate Models using Conformal Prediction

**Authors:** Vignesh Gopakumar, Ander Gray, Joel Oskarsson, Lorenzo Zanisi, Stanislas Pamela, Daniel Giles, Matt Kusner, Marc Peter Deisenroth  
**Venue:** ArXiv, August 2024  
**ArXiv:** [2408.09881](https://arxiv.org/abs/2408.09881)  
**Related:** ConfEviSurrogate (ArXiv 2504.02919, April 2025)  
**Domain:** Uncertainty Quantification / Surrogate Model Reliability  

---

## Problem Formulation

Surrogate models (neural operators, GNNs, PINNs) produce point predictions without native uncertainty estimates. For engineering decision-making, two failure modes are critical:
1. **Overconfident predictions:** model says "stress = 450 MPa" but true value is 520 MPa with no warning
2. **Miscalibrated Bayesian models:** Bayesian methods that claim calibrated uncertainty but fail on OOD inputs

**Conformal Prediction (CP)** provides a model-agnostic framework that:
- Takes any pre-trained surrogate as input
- Calibrates prediction intervals using a held-out calibration set
- Provides **distribution-free, finite-sample coverage guarantees**: `P(y ∈ Ĉ(x)) ≥ 1 - α`
- Requires only exchangeability (weak assumption), no distributional assumptions on residuals

## Method Architecture

Conformal Prediction workflow:

```
1. Train surrogate model f̂ on training data (any architecture: FNO, GNN, PINN, etc.)

2. Calibrate on held-out calibration set D_cal = {(x_i, y_i)}:
   - Compute nonconformity score s_i = score(x_i, y_i, f̂) for each calibration point
   - Common scores:
     a) Absolute residual: s_i = |y_i - f̂(x_i)|
     b) Normalized residual: s_i = |y_i - f̂(x_i)| / σ̂(x_i)  [requires uncertainty estimate]
     c) Conformalized Quantile Regression (CQR): uses quantile regressor estimates

3. Compute the (1-α)(1 + 1/|D_cal|) quantile q̂ of {s_i}

4. At test time: Ĉ(x_test) = {y : score(x_test, y, f̂) ≤ q̂}
   → For regression: interval [f̂(x) - q̂, f̂(x) + q̂]
```

For **field-level predictions** (spatially extended, e.g., stress fields):
- Apply CP per-node (element-wise) — guarantees joint coverage across the field
- Or use functional conformal prediction for correlated spatial outputs

## Training Strategy

No retraining required. CP is a post-hoc calibration method:
1. Train surrogate f̂ with any standard approach
2. Reserve 10–20% of simulation runs as calibration set (disjoint from training)
3. Compute nonconformity scores on calibration set
4. Deploy: surrogate prediction + calibrated interval

## Dataset Characteristics

Demonstrated on:
- Navier-Stokes surrogate (FNO backbone): 2D turbulent flow field prediction
- Weather forecasting (Pangu-Weather model)
- Plasma physics surrogate for fusion reactor simulations
- Time-series PDE surrogates

Key calibration requirement: calibration set must cover the deployment distribution (or use split conformal for distribution shift)

## Reported Metrics and Results

- **Coverage guarantee:** empirically achieves ≥ 1 - α coverage on held-out test sets across all tested models
- **Calibration time:** seconds to minutes on standard hardware (negligible overhead)
- **OOD robustness:** standard CP guarantees marginal coverage even for OOD inputs (though intervals may widen appropriately)
- **Interval width:** CP intervals are competitive with Bayesian approaches but without distributional assumptions

ConfEviSurrogate (2025 extension):
- Separates **aleatoric** (irreducible, from simulation noise) and **epistemic** (model, from limited data) uncertainty
- Provides higher-quality intervals than basic CP for structured engineering problems

## Limitations and Gaps

- CP provides **marginal** coverage guarantee — not conditional coverage (interval for a specific x may not be tight)
- Requires a calibration set that is representative of deployment distribution
- For spatial fields, naive element-wise CP is conservative (ignores spatial correlation → overly wide intervals)
- CP interval width depends on model quality — bad surrogate → wide intervals (but never overconfident)
- Does not improve model predictions — only quantifies uncertainty around them

## Relevance to KyulAI

**Critical for production deployment — non-negotiable UQ requirement.**

KyulAI's physics validation mandate ("Physics validation is mandatory before any model is considered 'ready'") requires uncertainty quantification. Conformal Prediction is the right tool because:

1. **Model-agnostic:** works with FNO, MeshGraphNets, DeepONet — no architecture changes needed
2. **Guaranteed coverage:** unlike Bayesian approaches, CP provides provable guarantees
3. **Data-efficient calibration:** 50–200 simulation runs sufficient for calibration
4. **Engineering decision support:** interval [150 MPa, 220 MPa] tells engineers when to trust the model
5. **OOD detection:** intervals widen automatically for out-of-distribution inputs (natural alarm system)

**Implementation plan for KyulAI:**
1. Train surrogate (FNO/GNN) on simulation data
2. Reserve 15% of simulation runs as conformal calibration set
3. Apply CQR (Conformalized Quantile Regression) — best for heteroscedastic engineering data
4. Threshold: reject any prediction where interval width exceeds 20% of predicted value
5. Log all predictions + intervals to MLflow for monitoring
