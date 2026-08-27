# Codex Prompt: Model Upgrade Without Curve CSV Classifier Work

You are working on the KyulAI / ImperialAX / ImperialAX composite CAE-AI project.

Repo:
- https://github.com/danhoonlee/KyulAI
- Branch: `codex/dd-laminate-ui-api`

## Current project context

The project already has productized surrogate-model workflows for:

1. Double-Double Laminate Forecast
2. u3 Forecast
3. Simple Injection Sprue/Filling Pressure Forecast
4. Physics feature packs based on CLT/ABD laminate descriptors
5. Physics XAI and live local XAI
6. Web/iOS/Android product surfaces
7. Unified module shell / account / entitlement MVP

The current model families already include:

- Tree / ExtraTrees / RandomForest-style classical models
- GointMLP-style neural models
- DeepONet for Simple Injection
- Physics-feature XAI models for Laminate Forecast and u3 Forecast

## Important new direction

We want to upgrade and compare model families beyond the current Tree and GointMLP models.

However, the Curve CSV Classifier is paused for now.

## Hard no-touch rule: Curve CSV Classifier

Do not work on the Curve CSV Classifier in this task.

Specifically, do NOT:

- retrain Curve CSV classifier models
- add MiniRocket, InceptionTime, TCN, CNN, GRU, or other curve-sequence models
- modify `/predict/curve`
- modify Curve CSV upload behavior
- modify `curve_classical` or `curve_goint` behavior
- modify Curve CSV UI tabs, preview logic, or result rendering
- change existing curve model registry entries unless required only for compatibility
- create new curve-classifier reports or curve-classifier model folders

You may inspect Curve CSV code only for context, but do not change it.

The first model-upgrade work should focus on:

1. Laminate Forecast
2. u3 Forecast
3. Simple Injection

not Curve CSV classification.

---

# Objective

Design and implement the next model-upgrade layer for the existing surrogate models, excluding Curve CSV classifier work.

The goal is to compare new model families against the current production/reference models while keeping the existing API and UI stable.

Do not change public defaults unless a new model clearly beats the current default and is documented.

---

# Priority 1: DD Laminate Forecast tabular challenger suite

Implement a model-comparison suite for the Laminate Forecast problem.

Current Laminate Forecast contract:

Inputs:

- `theta1`
- `theta2`
- `case`
- existing theta/case feature builders
- existing CLT/ABD physics feature builders

Outputs:

- predicted Type
- predicted Pt
- predicted max displacement
- predicted max force
- predicted force-displacement curve or curve basis/PCA reconstruction

Use existing feature builders where possible:

- `theta_physics_v2` for compact physics-feature models
- `theta_physics_nn_v2` only where neural-friendly features are relevant
- plain `theta` only as a baseline, not the main target

## Candidate models to evaluate

Start with a tabular challenger suite.

Include these if dependencies are already installed or can be added cleanly:

1. XGBoost
2. LightGBM
3. CatBoost

Also include sklearn fallback candidates that do not require optional dependencies:

1. ExtraTrees
2. RandomForest
3. HistGradientBoosting
4. Ridge/ElasticNet-style baseline for scalar heads if useful

Optional research-only candidate:

- TabPFN

But do not make TabPFN a required production dependency. If TabPFN is not installed, skip it gracefully and mention it in the report. If licensing or runtime is unclear, keep it research-only and do not add it to backend model registry.

## Evaluation

Use leakage-safe validation.

Preferred:

- GroupKFold by theta pair or equivalent grouping that prevents the same theta pair from leaking across train/test folds.

Report:

- Type accuracy
- Type macro F1
- Pt MAE
- Max displacement MAE
- Max force MAE
- Curve normalized RMSE
- Curve force RMSE
- training time
- inference time if easy
- model size if easy
- dependency notes

Compare explicitly against current reference models:

- `response_surrogate_physics_v2`
- `response_goint_physics_nn_v2`

## Deliverables

Create:

- `docs/design/dd_laminate_model_upgrade_no_curve_csv.md`
- `scripts/dd_response_tabular_challengers_train.py`
- `models/dd_laminate_response_tabular_challengers_v1/`
- `reports/dd_response_tabular_challengers_v1/model_comparison.md`
- `reports/dd_response_tabular_challengers_v1/model_comparison.json`

The report should recommend whether any challenger deserves a backend model key.

Do not add a new backend model key in the first pass unless the implementation is clean and the model clearly improves one of the main metrics.

---

# Priority 2: Type-gated Mixture-of-Experts design

After or alongside the tabular challenger suite, design a Type-gated Mixture-of-Experts model for Laminate Forecast.

Do not implement the full MoE unless the design is clear and the tabular challenger suite is already complete.

The design should be documented first.

Create or include in the design doc:

## Proposed model

Input:

- theta/case features
- compact CLT/ABD physics features

Gating model:

- predicts probabilities for Type 1, Type 2, Type 3

Expert models:

- Type 1 expert predicts Pt, max values, and curve basis
- Type 2 expert predicts Pt, max values, and curve basis
- Type 3 expert predicts Pt, max values, and curve basis

Final prediction options:

1. hard-gated: use the expert corresponding to predicted Type
2. soft-gated: probability-weighted sum of expert outputs

Compare both if implementation is simple.

## Why this model is relevant

The DD Laminate Type labels represent different response regimes:

- Type 1: clearer bilinear behavior
- Type 2: moderately curved post-transition behavior
- Type 3: heavily curved or force-fit-unreliable behavior

Because these regimes have different curve shapes, a Type-gated model may improve Pt and curve prediction compared with one global regressor.

## Deliverable

Add a section in:

- `docs/design/dd_laminate_model_upgrade_no_curve_csv.md`

with the proposed MoE architecture, data requirements, implementation steps, and evaluation plan.

If implemented later, the model key should likely be:

- `response_moe_physics_v1`

but do not expose it in the normal UI until validated.

---

# Priority 3: u3 Forecast challenger models

After Laminate Forecast challenger work, inspect the current u3 Forecast setup and propose challenger models.

Current u3 Forecast contract:

Inputs:

- `theta1`
- `theta2`
- `case`

Important:

- Do not reintroduce u3 bucket as a user input.
- u3 Type should be predicted as an output, not provided by the user.

Candidate directions:

1. XGBoost / LightGBM / CatBoost for Pt and Type
2. stacked ensemble of Tree + GointMLP
3. model blending:
   - Tree model for Type and curve shape
   - GointMLP model for Pt if it remains stronger
4. conformal or quantile interval around Pt

Deliverable:

- Add a u3 section to the model-upgrade design doc.
- Implement only if it is small and does not interfere with Laminate Forecast work.

---

# Priority 4: Simple Injection model upgrades

Do not start this before the DD Laminate tabular challenger suite is complete, unless the repo structure makes it much easier.

Candidate Simple Injection model upgrades:

## A. Filling softmax histogram head

Current Filling target includes histogram volume-ratio bins.

Implement or design a model where:

- raw logits go through softmax
- output volume-ratio bins sum structurally to 100%

This is better than only penalizing ratio-sum error through loss.

Candidate model key later:

- `filling_softmax_histogram_v1`

## B. Sprue Fourier-feature field model

Design a lightweight continuous curve model:

Input:

- geometry features
- process features
- normalized time `t`
- Fourier features of `t`

Output:

- sprue pressure at time `t`

This is a simpler alternative to DeepONet and may be easier to train on the current data size.

Candidate model key later:

- `sprue_fourier_field_v1`

## C. Multi-task shared Simple Injection model

Design a shared encoder:

Input:

- geometry + process features

Shared trunk:

- common process representation

Heads:

- Sprue pressure curve
- Filling pressure stats
- Filling histogram bins

Candidate model key later:

- `simple_injection_multitask_v1`

Deliverable:

- Add a Simple Injection section to the design doc.
- Do not implement all three in the first pass.
- Recommend the most promising first one based on current data and code structure.

---

# General constraints

Do not:

- remove existing models
- overwrite existing model folders
- change current API defaults
- break web/iOS/Android compatibility
- change public endpoint schemas unless backward-compatible
- touch Curve CSV classifier work
- start PINN implementation in this task

Do:

- keep changes small and reviewable
- add new model artifacts under new versioned folders
- add reports and metrics
- preserve current XAI behavior
- preserve current model registry behavior
- make optional dependencies optional
- skip unavailable model families gracefully
- document which models were skipped and why

---

# Suggested first implementation sequence

1. Inspect relevant files:
   - `src/backend/api/v1/dd_laminate.py`
   - `src/ml/dd_laminate/response_feature_sets.py`
   - `src/ml/dd_laminate/laminate_physics.py`
   - existing response training scripts
   - existing response prediction scripts
   - current model metrics JSON files

2. Create:
   - `docs/design/dd_laminate_model_upgrade_no_curve_csv.md`

3. Implement:
   - `scripts/dd_response_tabular_challengers_train.py`

4. Train/evaluate challengers:
   - ExtraTrees
   - RandomForest
   - HistGradientBoosting
   - XGBoost if available
   - LightGBM if available
   - CatBoost if available
   - TabPFN only if available and acceptable as research-only

5. Write:
   - `reports/dd_response_tabular_challengers_v1/model_comparison.md`
   - `reports/dd_response_tabular_challengers_v1/model_comparison.json`

6. Recommend:
   - best current challenger
   - whether it beats `response_surrogate_physics_v2`
   - whether it is worth adding to backend registry
   - whether MoE should be implemented next

---

# Acceptance criteria

The task is successful if:

1. Curve CSV classifier files and behavior are not modified.
2. A clear model-upgrade design document exists.
3. A Laminate Forecast tabular challenger suite exists.
4. The challenger suite runs with available dependencies.
5. Missing optional dependencies do not crash the full workflow.
6. Results are compared against the current Tree/GointMLP physics-XAI baselines.
7. The report gives a clear recommendation for the next model to implement.
8. Public API/UI defaults remain unchanged.
