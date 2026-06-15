# Nonlinear Information Fusion Algorithms for Data-Efficient Multi-Fidelity Modelling (NARGP)

**Authors:** Paris Perdikaris, Maziar Raissi, Andreas Damianou, Neil D. Lawrence, George Em Karniadakis  
**Venue:** Proceedings of the Royal Society A, 2017  
**DOI:** 10.1098/rspa.2016.0751  
**Domain:** Multi-Fidelity Learning / Sim-to-Real Data Fusion  

---

## Problem Formulation

Multi-fidelity modeling combines data from **multiple levels of accuracy and cost**:
- **Low-fidelity (LF):** fast, cheap, less accurate (coarse mesh FEA, simplified material models)
- **High-fidelity (HF):** slow, expensive, more accurate (fine mesh FEA, full multi-physics)
- **Experimental:** ground truth, extremely scarce and expensive

The classical approach (Kennedy & O'Hagan, 2000) uses a linear autoregressive model:
`f_HF(x) = ρ · f_LF(x) + δ(x)`

This fails when the relationship between fidelity levels is **nonlinear or space-dependent** (which is common in composites: LF and HF solvers may disagree differently across the design space).

The Nonlinear Autoregressive Gaussian Process (NARGP) replaces the linear scaling with a learned nonlinear mapping.

## Model Architecture

**NARGP — Nonlinear Autoregressive Gaussian Process:**

```
Level 1 (low-fidelity):
  f_1(x) ~ GP(m_1(x), k_1(x, x'))

Level 2 (medium-fidelity):
  f_2(x) ~ GP(m_2([x, f_1(x)]), k_2([x, f_1(x)], [x', f_1(x')]))
  Input = concatenation of [original input x, LF prediction f_1(x)]
  
Level L (high-fidelity or experimental):
  f_L(x) ~ GP(m_L([x, f_{L-1}(x)]), k_L(...))
```

Key insight: each higher-fidelity GP takes the lower-fidelity prediction as an **additional input feature** — enabling complex nonlinear, space-dependent cross-correlations to be captured automatically.

**Deep Multi-Fidelity GP (Cutajar et al., 2019) extension:** replaces GP levels with deep neural networks, allowing even richer nonlinear correlations and scalability to higher dimensions.

## Training Strategy

- Train level-by-level: fit GP_1 on LF data, then fit GP_2 on (HF data, LF predictions), etc.
- Maximum likelihood estimation of GP hyperparameters (length scales, signal variance, noise)
- Automatic relevance determination (ARD) kernels: learns which dimensions matter
- The propagation of uncertainty from lower to higher fidelity levels is automatic through the GP framework
- Can handle non-nested experimental designs (LF and HF evaluated at different x points)

## Dataset Characteristics

Demonstrated on:
- Borehole problem (8D engineering benchmark)
- Currin exponential function
- Multi-fidelity CFD: coarse mesh → fine mesh → experimental data

Typical data requirements:
- LF: 100–1,000 points
- HF: 10–100 points
- Experimental: 5–50 points

## Reported Metrics and Results

vs. Kennedy-O'Hagan (AR(1) linear):
- **NARGP achieves 2–5× lower RMSE** on nonlinear benchmark problems
- **Data efficiency:** NARGP with 10 HF points ≈ Kennedy-O'Hagan with 50 HF points
- **Uncertainty calibration:** NARGP provides well-calibrated predictive intervals
- Successfully captures space-dependent scaling relationships that linear AR(1) misses

## Limitations and Gaps

- **Scalability:** GP inference is O(N³) — struggles with more than ~1,000 training points per fidelity level
- Input dimensionality: standard GP kernels struggle in >20 dimensions
- Assumes smooth variations within each fidelity level (no discontinuities)
- Level-by-level training propagates errors: if LF GP is wrong, HF GP is misled
- Deep GP variants address scalability but lose closed-form uncertainty propagation

## Modern Extensions (2022–2025)

- **Multi-Fidelity GNN (2024):** extends NARGP to graph-structured data (coarse mesh → fine mesh → experiment)
- **Probabilistic Neural Data Fusion (2023):** arbitrary number of fidelity levels with neural network backbone
- **Multi-fidelity Bayesian neural networks (2024):** aerodynamic data fusion with heterogeneous uncertainties

## Relevance to KyulAI

**Very high — directly maps to the multi-CAE-tool hierarchy.**

KyulAI has a natural multi-fidelity hierarchy across CAE tools:

| Fidelity Level | Tool | Cost | Accuracy |
|---------------|------|------|---------|
| LF | Moldex3D (fast solve) | Minutes | Medium |
| MF | Digimat mean-field | Hours | Good |
| HF | Abaqus full FEA | Hours–days | High |
| Experimental | Coupon testing | Days–weeks | Ground truth |

NARGP (or its deep extension) can:
1. Train on abundant Moldex3D/fast-solve data
2. Incorporate fewer Abaqus runs as high-fidelity correction
3. Use very few experimental measurements as the final correction
4. Propagate uncertainty all the way through the chain

This is the **most direct algorithmic fit** for the multi-tool CAE → experiment pipeline, providing both accuracy and uncertainty quantification with very limited experimental data.

**Scalability concern:** for field-level predictions (full stress fields), standard GP is too slow. Combine with MeshGraphNets (Paper 04) or FNO (Paper 02) as the backbone, then use NARGP principles for the cross-fidelity fusion layer.
