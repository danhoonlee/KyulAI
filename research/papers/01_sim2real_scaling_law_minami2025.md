# Scaling Law of Sim2Real Transfer Learning in Expanding Computational Materials Databases

**Authors:** Minami, Hayashi, Wu, Fukumizu, Sugisawa, Ishii, Kuwajima, Shiratori, Yoshida  
**Venue:** npj Computational Materials, Vol. 11, Article 146, 2025  
**ArXiv:** [2408.04042](https://arxiv.org/abs/2408.04042)  
**Domain:** Sim-to-Real Transfer Learning  

---

## Problem Formulation

Real-world experimental data for materials property prediction is scarce and expensive to acquire. High-throughput computational simulations (e.g., molecular dynamics) can generate abundant synthetic data, but a distributional gap exists between simulated and experimental observations. The core question: **how much computational data is needed to achieve a target real-world prediction accuracy via fine-tuning?**

## Model Architecture

- **Pretraining backbone:** Graph Neural Network (GNN) / message-passing architecture (compatible with atomic/molecular fingerprints) pretrained on large-scale MD simulation databases
- **Downstream adaptation:** Standard fine-tuning on small experimental datasets (linear probe or full fine-tune)
- **Data generation:** ~7 × 10⁴ amorphous polymers computed via RadonPy library (automated MD property calculations), covering 20 polymer classes (polyimides, polyesters, polystyrenes, etc.)
- **Predicted properties:** density, specific heat capacity (Cp), refractive index, thermal conductivity

## Training Strategy

1. **Phase 1 — Pretraining on simulation data:** Train neural model on large MD-derived database
2. **Phase 2 — Fine-tuning on real data:** Adapt pretrained model to small experimental dataset
3. **Scaling experiment:** Vary the size of the simulation pretraining dataset N_sim = {10², 10³, 10⁴, 10⁵} and measure downstream real-world test error
4. **Baseline:** Training from scratch on experimental data only

## Dataset Characteristics

| Split | Size | Source |
|-------|------|--------|
| Simulation (pretraining) | ~70,000 amorphous polymers | MD via RadonPy |
| Experimental (fine-tune) | Hundreds to ~1,000 | Published literature |
| Test | Out-of-distribution real samples | Published literature |

## Reported Metrics and Results

- **Key finding:** Real-world prediction error follows a **power-law** with respect to N_sim:
  `error ∝ N_sim^{-α}` where α depends on the property
- Fine-tuned Sim2Real models **outperform scratch-trained models** even with 10× fewer real data points
- Scaling curve enables **sample-efficiency planning**: can predict N_sim needed to hit a target RMSE
- Demonstrated equivalence: 1 experimental data point ≈ ~100 simulation data points for certain properties

## Limitations and Gaps

- Studied only polymers and simple inorganic materials — not fiber-reinforced composites or anisotropic multi-phase materials
- MD simulations capture molecular-level physics; does not directly transfer to macro-scale structural properties (stiffness, failure strength) from Abaqus/Digimat
- The power-law relationship holds within each property independently; multi-output/multi-physics coupling not studied
- Fine-tuning assumes the same input feature space (molecular descriptors) — CAE simulation inputs (mesh fields, process parameters) require a different modality

## Relevance to KyulAI

**High relevance.** This paper provides the *theoretical foundation* and *practical framework* for KyulAI's core sim-to-real challenge:
- Validates the pretraining-then-fine-tuning paradigm for sim-to-real
- Provides a methodology for quantifying how much CAE simulation data is needed before experimental fine-tuning becomes effective
- Suggests building a large simulation database first, then fine-tuning on scarce experimental coupons/laminates
- The power-law scaling can guide data acquisition cost/benefit decisions

**Adaptation needed:** The CAE setting involves mesh-structured fields (not molecular graphs), multi-physics process chains (Moldex3D → AniForm → Digimat → Abaqus), and anisotropic composites — modality transfer from molecular GNN to mesh GNN is the key extension.
