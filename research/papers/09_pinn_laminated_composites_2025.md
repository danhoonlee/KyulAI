# A Physics-Informed Neural Network Framework for Laminated Composite Plates under Bending

**Authors:** (ScienceDirect, Composite Structures, January 2025)  
**Venue:** Composite Structures, 2025  
**URL:** https://www.sciencedirect.com/science/article/pii/S0263823125001089  
**Domain:** Physics-Informed Neural Networks / Composite Structural Analysis  

---

## Problem Formulation

Predicting the deformation, stress, and strain fields in laminated composite plates under bending loads typically requires solving coupled 2D plate theories (Classical Lamination Theory, First-Order Shear Deformation Theory — FSDT, or higher-order theories). FEA is the standard tool, but:
- Repeated design iterations are expensive
- Mesh generation for complex ply configurations is laborious
- Parametric sweeps over ply angles, stacking sequences, and load distributions require many FEA runs

**PINNs for composite plates** encode the governing plate equations (equilibrium, constitutive relations, kinematics) directly as soft constraints in the neural network loss, enabling mesh-free parametric prediction.

## Model Architecture

Standard PINN architecture adapted for composite plate bending:

```
Input: (x, y) spatial coordinates + ply parameters (angles θ_k, thicknesses t_k, material E_k)
  ↓
Fully connected neural network (MLP):
  5–8 hidden layers × 50–100 neurons
  Activation: tanh (smooth, compatible with second-order derivatives via autograd)
  ↓
Output: [u(x,y), v(x,y), w(x,y)]  — in-plane and out-of-plane displacements
  ↓
Post-processing: strains via automatic differentiation
                 stresses via laminated constitutive law [A,B,D] matrices
```

Loss function:
```
L_total = L_PDE + λ_BC · L_BC + λ_data · L_data

L_PDE: residual of FSDT equilibrium equations at interior collocation points
L_BC: residual of boundary conditions (simply-supported, clamped, etc.)
L_data: (optional) MSE against sparse FEA data points
```

## Training Strategy

- **Collocation-based:** no simulation data required — only need PDE residuals and BCs
- Adam optimizer for initial training → L-BFGS for refinement
- ~10,000–50,000 collocation points distributed across the plate domain
- Multiple outputs (u, v, w) trained simultaneously
- Training time: hours on GPU (vs. minutes per FEA run — PINN is NOT faster at training, only at inference)

## Dataset Characteristics

Validation against analytical solutions (Navier series) and Abaqus FEA:
- Simply-supported plates: exact analytical solutions available
- Cross-ply and angle-ply laminates: [0/90]_s, [±45]_s, [0/45/90/-45]_s
- Load types: uniform pressure, sinusoidal load distribution
- Thickness ratios: a/h = 4 (thick) to 100 (thin)

## Reported Metrics and Results

- **Deflection (w):** < 1% error vs. Abaqus for thin plates (a/h ≥ 20)
- **In-plane stresses (σ_xx, σ_yy, τ_xy):** < 3% error
- **Transverse shear stresses (τ_xz, τ_yz):** < 5% error (inherently harder, recovered by integration)
- **Limitation on thick plates:** FSDT formulation breaks down for a/h < 10 — requires Higher-Order theory
- Inference time after training: milliseconds per new load/geometry combination

## Limitations and Gaps

- PINN training is **slow** (hours per configuration) vs. FEA (minutes) — only beneficial when many parametric queries needed after training
- Convergence can be unstable for high ply counts or extreme stiffness contrasts
- Limited to linear elastic behavior — no damage, progressive failure, or geometric nonlinearity
- Only validates bending — not buckling, vibration, or impact
- No sim-to-real validation against actual tested coupon data
- **Training from scratch** for each new stacking sequence (no transfer learning between laminate configurations)

## Relevance to KyulAI

**Moderate relevance — useful as a component but not the primary architecture.**

PINNs for composite plates are useful for KyulAI's Digimat/Abaqus structural analysis surrogates, but with significant caveats:
- **Strength:** physics-constrained — model cannot predict non-physical stress distributions
- **Weakness:** slow to train, does not natively handle the sim-to-real gap, and does not scale to 3D laminate assemblies

**Recommended role in KyulAI:** use PINN loss terms as **regularizers** on top of GNN/FNO surrogates (the PINO paradigm) rather than as the primary architecture. This gives the physics constraint benefits without the pure PINN convergence difficulties.

**Key insight for KyulAI:** the coupling between Digimat (material homogenization) and Abaqus (structural) is where composite-specific physics must be preserved. PINN-regularized operators that encode the classical lamination theory constitutive law [A,B,D] matrices are the right tool here.
