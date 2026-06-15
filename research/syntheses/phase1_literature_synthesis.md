# Phase 1 Literature Synthesis: AI Methods for Composite Sim-to-Real Transfer

**Prepared by:** Research & Paper Analysis Team  
**Date:** 2026-04-08  
**Covers:** 9 key papers across 7 research domains  
**For:** AI/ML Team (model architecture decisions) and Domain Validation Team (UQ approach)

---

## Executive Summary

The field has converged on a clear paradigm for sim-to-real transfer in engineering: **pretrain on abundant simulation data, then fine-tune on scarce experimental data**. The principal challenge is not the availability of methods — many strong approaches exist — but the **architectural choices** for handling (a) unstructured mesh data, (b) multi-physics coupling across process chain stages, and (c) provable uncertainty quantification at deployment.

For KyulAI's specific problem (6 CAE tools, composites, multi-scale), the recommended stack is:
1. **FNO/GNN-based neural operators** as the primary simulation surrogate backbone
2. **NARGP-inspired multi-fidelity fusion** across the CAE tool hierarchy
3. **Fine-tuning (not adversarial DA)** as the sim-to-real adaptation method
4. **Conformal Prediction** as the UQ wrapper for all deployed models

---

## Domain-by-Domain Synthesis

### 1. Sim-to-Real Transfer Learning

**Convergent finding:** The power-law scaling (Minami et al., 2025) provides concrete guidance: prediction error decays as N_sim^{-α} when fine-tuning on real data. This has two actionable implications:

- **Data strategy:** generate as much simulation data as computationally feasible before collecting experimental data. The returns are significant until ~10⁴–10⁵ simulation samples.
- **Fine-tuning approach:** pretraining + fine-tuning decisively outperforms training from scratch on experimental data. Even 10–50 experimental samples post-fine-tuning give large gains.

**Critical gap:** Minami et al. studied molecular properties with molecular graph inputs. KyulAI's inputs are CAE field solutions (stress fields, fiber orientation tensors, filling patterns) — the modality is fundamentally different, requiring mesh-aware architectures rather than molecular GNNs.

**Open question:** Does the power-law hold for field-level predictions (not just scalar properties)? No study has answered this for composite structural simulations.

---

### 2. Physics-Informed Neural Networks (PINNs)

**Convergent finding:** PINNs are valuable as physics regularizers but have significant practical limitations as standalone architectures:
- Training is slow (hours per configuration) — worse than FEA for single solves
- Convergence is unstable for high-contrast composite materials (stiffness ratio ~100:1 between fiber and matrix)
- However, PINN loss terms as regularizers on top of data-driven networks (the PINO paradigm) combine the best of both

**Composite-specific advance (2025):** Extended PINO for autoclave curing (Paper 03) shows that physics-informed neural operators can handle complex coupled PDEs (heat + cure kinetics) with <5% error and 100–1,000× speedup. The differentiable inference capability enables gradient-based process optimization.

**Synthesis:** Use PINN *principles* (PDE residual loss terms), not PINN *architecture* (pure MLP with collocation). Integrate physics loss into FNO or DeepONet training.

---

### 3. Neural Operators (FNO, DeepONet, PINO)

**Convergent finding:** Neural operators are the strongest candidate for KyulAI's simulation surrogates. Key advantages over both classical PINNs and naive deep learning:
- **Discretization invariance:** train on coarse CAE meshes, infer on fine meshes
- **Operator learning:** learn the mapping (process params) → (full solution field), not just point values
- **Speed:** 100–1,000× faster than FEA at inference
- **Physics integration:** PINO variant combines data efficiency with physics constraints

**Performance comparison across architectures:**

| Architecture | Irregular Meshes | Physics Integration | Data Efficiency | Speed |
|-------------|-----------------|--------------------|-----------------|----|
| FNO | No (regular grids only) | Via PINO variant | Medium | 1000× |
| Geo-FNO / GNOT | Yes | Via PINO | Medium | 500× |
| DeepONet | Limited | Via PIDON | High | 500× |
| MeshGraphNets | Yes (native) | No (data-driven) | Low (needs more data) | 100× |

**Recommendation for KyulAI:** 
- For **regular-grid CAE outputs** (Moldex3D fill patterns, Digimat homogenization): FNO/PINO
- For **unstructured mesh FEA** (Abaqus stress fields): MeshGraphNets or Geo-FNO

---

### 4. Domain Adaptation for Scarce Experimental Data

**Convergent finding (MaterialDA, 2023):** Most sophisticated domain adaptation methods (DANN, MMD, CORAL) do NOT reliably improve OOD performance in materials science. The methods that work are:

1. **Fine-tuning** on labeled target domain samples (best, even with 10 samples)
2. **Importance weighting** (BW, RULSIF) when unlabeled target distribution is available

This is a surprising and practically critical finding — it argues *against* investing engineering effort into elaborate adversarial domain adaptation. The simplest approach (fine-tune on experimental data) is the most effective.

**Implication for KyulAI:** prioritize building a large, diverse simulation dataset, then fine-tune on experimental coupon data. Do not invest in adversarial DA methods as the primary strategy. Reserve importance weighting as a secondary tool for distribution shift correction.

---

### 5. Graph Neural Networks for Mesh-Based Simulation

**Convergent finding:** MeshGraphNets (Pfaff et al., 2021) established the GNN-as-surrogate paradigm. Key advances since 2021:
- **X-MeshGraphNets (2024):** scales to million-node meshes via graph partitioning
- **Edge-augmented GNN (2024):** outperforms base MeshGraphNets on solid mechanics
- **Noise injection during training** is critical for rollout stability (confirmed by multiple follow-up works)
- The multi-graph approach (mesh-space + world-space) handles contact and long-range effects

**Composite-specific challenge:** KyulAI's composites have **anisotropic, heterogeneous** material properties that vary node-by-node (fiber orientation, ply index, local manufacturing defects). This must be encoded in node/edge features, requiring careful feature engineering:
- Node features: fiber orientation tensor (6 independent components for 3D), ply angle, local resin content
- Edge features: material mismatch indicator, interface type (lamina-lamina vs. lamina-core)

---

### 6. Multi-Fidelity Learning

**Convergent finding:** The NARGP framework (Perdikaris et al., 2017) and its extensions provide the right abstraction for KyulAI's multi-CAE-tool pipeline. Key insight: nonlinear relationships between fidelity levels are the norm in composites (a fast Moldex3D solve and a full Abaqus FEA can disagree *differently* across the design space).

**Modern extensions are directly applicable:**
- Multi-fidelity GNN (2024): handles field-level predictions across mesh refinements
- Probabilistic Neural Data Fusion (2023): arbitrary N fidelity levels — directly maps to KyulAI's 6-tool chain

**Practical guide for KyulAI fidelity hierarchy:**

```
Level 1: Moldex3D fast mode (minutes) → fiber orientation tensor field
Level 2: Digimat mean-field homogenization (hours) → effective ply stiffness
Level 3: Abaqus linear FEA (hours) → stress/strain field under service load
Level 4: Abaqus nonlinear FEA (days) → progressive failure analysis
Level 5: Experimental coupon test (days) → measured stiffness, strength, failure load
```

A multi-fidelity model trained on levels 1–4 needs only ~5–20 level-5 experiments to produce well-calibrated real-world predictions.

---

### 7. Uncertainty Quantification

**Convergent finding:** Conformal Prediction (Paper 07) is the practical UQ solution for KyulAI:
- Works post-hoc on any trained surrogate (no architecture changes)
- Provides distribution-free coverage guarantees (unlike Bayesian methods)
- Calibration requires ~50–200 simulation runs (negligible vs. training cost)
- OOD inputs naturally produce wide intervals (built-in alarm system)

Bayesian neural networks and Monte Carlo dropout provide UQ but:
- Are computationally expensive (10–100 forward passes per prediction)
- Can be systematically miscalibrated for OOD inputs
- Add architectural complexity

**Recommendation:** implement CP as the UQ layer on all deployed KyulAI models. Use CQR (Conformalized Quantile Regression) for heteroscedastic data (uncertainty that varies with process parameters).

---

## Cross-Cutting Themes

### Theme 1: The Two-Stage Paradigm is Universal

Every successful sim-to-real approach follows the same template:
1. **Pretraining** on large simulation dataset → learns physics/structure
2. **Fine-tuning** on small experimental dataset → closes the sim-to-real gap

This is not controversial. The architectural choices determine *what* is pretrained and *how* fine-tuning happens, but the two-stage structure is consistent across all domains.

### Theme 2: Field-Level Predictions Require Geometry-Aware Architectures

Scalar property prediction (thermal conductivity, stiffness modulus as single numbers) is a solved problem. The open frontier is **field-level prediction**: predicting the full spatial distribution of stress, strain, temperature, fiber orientation, or damage. This requires:
- Mesh-aware GNNs or Geo-FNO (not standard MLP or regular-grid FNO)
- Multi-scale architectures that handle both fine-grained local features and global structural response

### Theme 3: Physics Constraints Reduce Data Requirements

PINN and PINO approaches consistently require fewer training pairs than purely data-driven methods. For KyulAI's setting where simulation runs are expensive (Abaqus takes hours), physics-informed training is essential:
- PINO reduces required training pairs by ~5–10×
- Physics constraints prevent non-physical predictions at extrapolation

### Theme 4: Evaluation Must Use Realistic (OOD) Splits

MaterialDA's key finding applies broadly: random train/test splits systematically overestimate performance. KyulAI must evaluate using:
- **Process parameter OOD:** train on one manufacturing condition range, test on unseen range
- **Geometry OOD:** train on flat laminates, test on curved parts
- **Material OOD:** train on CFRP, test on GFRP
- **Experimental OOD:** train on simulation, evaluate on real coupon measurements

---

## Identified Research Gaps (Opportunities for KyulAI to Advance the Field)

1. **Multi-physics, multi-tool process chain surrogates:** No paper addresses surrogate learning across a full manufacturing process chain (injection → forming → curing → structural). This is KyulAI's unique problem.

2. **Sim-to-real scaling laws for field predictions:** Minami et al. showed power-law scaling for scalar properties. Whether this holds for field-level predictions (stress fields, fiber orientation fields) is unknown.

3. **Composite-specific GNN features:** No published GNN surrogate paper explicitly handles ply-level anisotropy encoding, delamination interface physics, or manufacturing variability (void content, fiber volume fraction variation).

4. **Hybrid multi-fidelity + conformal UQ:** No paper combines multi-fidelity modeling with conformal UQ calibration — the uncertainty propagation across fidelity levels + experimental calibration is an open problem.

5. **Active learning for experimental data collection:** Which experiments provide the most information for fine-tuning the surrogate? Active learning strategies for composite characterization are underdeveloped.
