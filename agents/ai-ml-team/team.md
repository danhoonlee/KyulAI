# AI/ML Development Team

## Mission
Design, implement, train, and evaluate AI models for sim-to-real prediction in composite analysis.

## Agents & Model Assignments
- **ML Architect** (Opus): Designs model architectures and training strategies — highest-stakes decisions
- **Model Developer** (Sonnet): Implements models in PyTorch
- **Hyperparameter Engineer** (Haiku): Manages training sweeps and logs results
- **Evaluation Scientist** (Sonnet): Benchmarks, compares models, validates against experimental data

## Phased Strategy
1. **Baseline**: MLP/CNN surrogates + basic transfer learning
2. **Physics-Informed**: PINNs, Neural Operators (FNO/PINO), MeshGraphNets
3. **Sim-to-Real**: Fine-tuning + importance weighting (BW/RULSIF) — NOT DANN/MMD/CORAL
   - Research Team finding (MaterialDA, arXiv 2308.02937): adversarial domain adaptation
     (DANN, MMD, CORAL) consistently fails or shows marginal gains in materials science OOD.
   - Use: pretraining on simulation → fine-tuning on experimental data (10–50 samples).
   - Supplementary: importance weighting (RULSIF) for distribution shift correction.
4. **Novel Methods**: Multi-fidelity NARGP fusion, PINO process chain surrogates

## Key Dependencies
- Requires unified data from Data Engineering Team
- Receives methodology recommendations from Research Team
- Outputs validated through Domain Validation Team
- Infrastructure provided by MLOps Team

## Code Location
- `src/ml/models/` — Model architectures
- `src/ml/training/` — Training infrastructure
- `src/ml/evaluation/` — Metrics and benchmarks
- `src/ml/configs/` — Experiment configurations

## Constraints
- All experiments must be tracked in MLflow/W&B
- Models must accept unified schema input (no tool-specific code in models)
- Physics constraints must be incorporated where applicable
