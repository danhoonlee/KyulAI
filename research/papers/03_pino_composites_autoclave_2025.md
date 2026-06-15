# Accelerated Gradient-based Design Optimization via Differentiable Physics-Informed Neural Operator: A Composites Autoclave Processing Case Study

**Authors:** (Bostanabad group / composites processing lab)  
**Venue:** ArXiv preprint, February 2025  
**ArXiv:** [2502.11504](https://arxiv.org/abs/2502.11504)  
**Related:** Extended PINO for Composites Autoclave (ScienceDirect 2025, doi:10.1016/j.compositesb.2025...)  
**Domain:** Physics-Informed Neural Operators / Composites Manufacturing  

---

## Problem Formulation

Autoclave curing of carbon-fiber composites involves coupled **thermo-chemical PDEs** governing:
- Temperature field T(x,t) across the part and tooling
- Degree of cure α(x,t) (exothermic reaction kinetics)
- Residual stress buildup from differential thermal/chemical shrinkage

Traditional FEA simulation of a single cure cycle takes hours. Design optimization (over cure temperature ramp, dwell temperatures, dwell durations) requires hundreds of simulations → infeasible with FEA. The goal is a neural operator surrogate that maps **process parameter functions → field evolution** and is **differentiable** for gradient-based optimization.

## Model Architecture

**Physics-Informed DeepONet (PIDON)** — novel variant extending canonical DeepONet:

```
Branch Net: encodes process parameter function p(t) (temperature cycle)
  → embedding vector of size [p]

Trunk Net: encodes query coordinates (x, t)
  → basis function vector of size [p]

Output: T(x,t) = branch(p(t)) · trunk(x,t)  [dot product]
       α(x,t) = separate PIDON head
```

Key extensions over standard DeepONet:
- **Nonlinear decoder:** replaces the linear dot-product with an MLP decoder for high-nonlinearity systems
- **Curriculum learning:** training starts with simpler cure cycles, progressively increases complexity
- **Physics loss terms:** PDE residuals (heat equation, Arrhenius cure kinetics) added to MSE data loss
- **Differentiable inference:** full backpropagation through the surrogate enables gradient-based design optimization

## Training Strategy

1. Generate training pairs via FEA solver (Abaqus/commercial curing solver)
2. Train with combined loss: `L = L_data + λ · L_physics`
   - `L_data`: MSE between predicted and FEA fields
   - `L_physics`: PDE residual evaluated at collocation points
3. Curriculum: start with linear temperature ramps, add complexity
4. Differentiable optimization: after training, minimize design objective through surrogate using Adam/L-BFGS

## Dataset Characteristics

- Training: ~500–2,000 FEA runs covering diverse cure cycle designs
- Geometry: representative composite laminate cross-sections (2D)
- Process parameters: cure temperature profile (5–7 parameters: ramp rates, dwell temperatures/times)
- Multi-physics output: temperature field + degree of cure field at all spatial points over time

## Reported Metrics and Results

- **Prediction accuracy:** relative L² error < 2–5% on held-out FEA runs
- **Inference speed:** ~100–1,000× faster than FEA (milliseconds vs. minutes/hours)
- **Optimization:** gradient-based optimization using surrogate finds cycle designs that reduce max temperature gradient by ~30% and improve cure uniformity compared to baseline
- **Zero-shot generalization:** can predict for process parameter combinations not seen in training

## Limitations and Gaps

- **2D geometry only:** cross-sectional analysis; 3D parts with complex geometry not addressed
- **Fixed geometry:** operator is trained for a specific laminate stacking sequence and thickness
- Cure kinetics model (Arrhenius) is phenomenological — does not capture resin batch variability
- **No sim-to-real gap addressed:** all training/testing is within FEA simulation — no experimental validation
- Does not model fiber orientation effects (assumes 1D heat conduction through thickness)
- No uncertainty quantification on predictions

## Relevance to KyulAI

**Very high — directly applicable to Moldex3D/AniForm process modeling.**

This paper provides the exact architecture pattern for KyulAI's process simulation surrogates:
- **Moldex3D (SMC/RTM filling):** PINO can map (injection pressure/flow rate curves, mold geometry) → (fill pattern, fiber orientation tensor field)
- **AniForm (thermoforming):** map (tool geometry, blank holder force, temperature) → (fiber angle, thickness, spring-back fields)
- The differentiable optimization framework directly enables process parameter optimization
- The physics-loss approach reduces data requirements vs. pure data-driven operators

**Critical extension for KyulAI:** The sim-to-real gap. This paper validates only against FEA — not against measured warpage, cure state, or mechanical properties of real parts. KyulAI must add a fine-tuning layer on real experimental measurements.
