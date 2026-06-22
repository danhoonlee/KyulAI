# DD Laminate Model Upgrade Without Curve CSV

## Scope

This design covers the next Laminate Forecast model-upgrade layer for theta/case
surrogate models. It explicitly excludes Curve CSV classifier work.

In scope:

- Laminate Forecast response prediction from `theta1`, `theta2`, and `case`
- Compact CLT/ABD physics features
- Tabular challenger evaluation
- A Type-gated mixture-of-experts design for a later pass
- Follow-on notes for u3 Forecast and Simple Injection

Out of scope:

- Curve CSV classifier training or registry changes
- `/predict/curve`
- `curve_classical` or `curve_goint`
- Curve CSV upload, preview, tab, or rendering behavior
- PINN work
- Public API/UI default changes

## Current Baselines

The current production/reference Laminate Forecast models already use leakage
safe grouped validation by theta pair. The strongest current baseline is:

- `response_surrogate_physics_v2`
- Feature builder: `theta_physics_v2`
- Samples: 900
- Type accuracy: about 0.942
- Type macro F1: about 0.937
- Pt MAE: about 438
- Max force MAE: about 339
- Normalized curve RMSE: about 0.007
- Curve force RMSE: about 479

The neural reference is:

- `response_goint_physics_nn_v2`
- Feature builder: `theta_physics_nn_v2`
- Samples: 900
- Type accuracy: about 0.939
- Type macro F1: about 0.938
- Pt MAE: about 661
- Max force MAE: about 1160
- Normalized curve RMSE: about 0.021
- Curve force RMSE: about 1251

The practical bar for a new backend model key is therefore not only Type
classification. A challenger should improve Pt and curve metrics without a
meaningful Type macro F1 regression.

## Tabular Challenger Suite

The first upgrade layer should be a research/evaluation harness, not a backend
registry change. It should train and compare multiple model families under one
fixed validation contract:

- Dataset: `data/datasets/DD_cases_2_3_4_curated_v1`
- Inputs: `theta1`, `theta2`, `case`
- Primary feature set: `theta_physics_v2`
- Validation: `GroupKFold` by theta pair
- Curve target: normalized force curve on the existing 128-point grid
- Curve prediction: PCA scores plus tabular regressor
- Scalar targets: Pt, max displacement, max force
- Type target: Type 1/2/3

Required sklearn candidates:

- ExtraTrees
- RandomForest
- HistGradientBoosting
- Ridge/ElasticNet-style scalar baseline

Optional candidates:

- XGBoost
- LightGBM
- CatBoost
- TabPFN as research-only

Optional dependencies must be skipped gracefully when unavailable. They should
not be added to serving requirements. If they are added later, keep them in a
training/research install path unless a production promotion decision is made.

## Deep-Learning Challenger Suite

The second upgrade layer should test whether the current GointMLP-style neural
learner is the weak point, while keeping the same neural response contract:

- Dataset: `data/datasets/DD_cases_2_3_4_curated_v1`
- Primary feature set: `theta_physics_nn_v2`
- Validation: `GroupKFold` by theta pair
- Scalar targets: log-normalized Pt, max displacement, max force
- Curve target: direct normalized response curve on the existing 128-point grid
- Loss contract: class, ordinal, scalar, and curve losses as in the GointMLP
  trainer

Initial DL challengers:

- Plain shared MLP response surrogate
- Residual MLP response surrogate
- Gated MLP response surrogate
- Physics-guided MLP response surrogate with soft curve-shape penalties
- DeepONet-style branch/trunk response surrogate over the displacement grid
- PCA/POD curve-decoder MLP that predicts curve basis coefficients
- Stack LSTM response surrogate over the deterministic 16-ply laminate stack
- Stack GRU response surrogate over the deterministic 16-ply laminate stack
- Stack GNN response surrogate over a deterministic 16-node ply-adjacency graph
- Stack GAT response surrogate over a deterministic 16-node ply-adjacency graph

These models are research comparisons against `response_goint_physics_nn_v2`.
They should not be exposed through the backend registry until they also compare
cleanly against `response_surrogate_physics_v2` and have prediction API support.

The physics-guided MLP is a PINN-adjacent model, not a true PINN. It does not
solve or differentiate a governing equation. Instead it applies soft penalties
to the predicted curve so that the start point, peak normalization, monotonic
descent, and curvature are more physically plausible. This should be treated as
a research constraint ablation because overly simple curve-shape assumptions can
conflict with observed force-displacement responses.

The DeepONet-style candidate is also PINN-adjacent, but through the neural
operator family rather than through physics residuals. The branch network
encodes theta/case physics features, the trunk network encodes the normalized
displacement grid, and their factorized product generates the response curve.
It is useful for testing whether a function-generator head is better than a
direct 128-point curve head.

The PCA/POD curve-decoder MLP is a curve-focused hybrid. It fits the curve basis
only on the training fold, predicts basis coefficients with a neural model, and
reconstructs the full curve for evaluation. This is not a public model by
itself because Type classification can regress, but it is useful as a
curve/scalar expert in a future hybrid where Type gating is handled separately.

The stack LSTM/GRU/GNN/GAT variants may add a structured stack encoding derived
from the same pre-simulation inputs. The current stack node features are angle
normalization, sine/cosine bases, sign, through-thickness position, case index,
and theta1/theta2 membership flags. This preserves the no-Curve-CSV boundary:
the models do not consume uploaded force-displacement curves as inputs.

## Evaluation Metrics

Each candidate report should include:

- Type accuracy
- Type macro F1
- Pt MAE
- Max displacement MAE
- Max force MAE
- Curve normalized RMSE
- Curve force RMSE
- Training time
- Inference time per sample
- Model artifact size
- Dependency status

The comparison report should include the existing reference models:

- `response_surrogate_physics_v2`
- `response_goint_physics_nn_v2`

Recommendation logic:

- Do not promote a model that only improves Type classification.
- Prefer a challenger only when Pt and curve metrics improve or remain clearly
  competitive while Type macro F1 does not regress materially.
- Keep public defaults unchanged unless a model clearly beats the current
  baseline and the deployment surface is simple.

## Type-Gated Mixture Of Experts

A Type-gated MoE may be useful because DD response Types encode different curve
regimes. It should be designed after the tabular challenger suite exposes
whether residuals are Type-specific.

Splitting the internal predictors by target is acceptable for this project as
long as the served contract remains one Laminate Forecast model. Type is a
classification target, while Pt and the response curve are regression/function
targets. A hybrid can therefore use a Type expert and a Pt/curve expert without
exposing multiple user-facing models.

Current research hybrid:

- `hybrid_type_tree_pca_curve_mlp`
- Type expert:
  - ExtraTrees classifier
  - `theta_physics_v2`
  - compact CLT/ABD physics feature set
- Pt/curve expert:
  - PCA/POD curve-decoder MLP
  - `theta_physics_nn_v2`
  - predicts scalar response plus curve basis coefficients
- Validation:
  - grouped by theta pair
  - PCA/POD basis fit inside each training fold only

Pt/curve consistency rule:

- Predicted Pt should remain the authoritative transition-load scalar.
- The displayed transition marker should be placed by interpolating the
  predicted curve at force = predicted Pt, not by trusting an arbitrary curve
  index.
- The curve expert must also report or enforce consistency diagnostics:
  - whether predicted Pt is inside the predicted force range
  - the interpolated displacement where the curve crosses Pt
  - the gap between Pt and the nearest/inferred curve transition force
- If Pt falls outside the predicted curve range, prefer a small post-processing
  calibration of the curve force scale/max-force over silently moving Pt,
  because the current scalar Pt metric is better than the direct curve-knee
  estimate.
- A later training pass can add a Pt-consistency loss so the curve and scalar
  head are encouraged to agree before post-processing.
- This is supervised regularization, not active learning. Active learning would
  request new simulations/labels for uncertain theta/case samples. Pt-consistency
  loss only changes the objective on the existing labeled data.
- Initial loss ablation:
  - weight 0.10 was too strong and harmed curve RMSE.
  - weight 0.01 kept Type metrics and improved Pt over the no-consistency
    hybrid, but slightly worsened curve RMSE.
  - The serving path should therefore still include inference-time diagnostics
    and force-scale calibration instead of relying only on the training loss.
- Implemented inference-time consistency support:
  - `src/ml/dd_laminate/pt_curve_consistency.py`
  - existing tree and deep response predictors now add flat Pt/curve diagnostic
    metrics.
  - research hybrid predictor uses the same consistency layer.
  - calibration keeps Pt authoritative and only scales the curve force/max-force
    conservatively when Pt falls outside the predicted curve range.

Proposed architecture:

- Shared input: theta/case features plus compact CLT/ABD physics descriptors
- Gating model: predicts probabilities for Type 1, Type 2, and Type 3
- Expert models:
  - Type 1 expert predicts Pt, max values, and curve PCA scores
  - Type 2 expert predicts Pt, max values, and curve PCA scores
  - Type 3 expert predicts Pt, max values, and curve PCA scores

Prediction modes:

- Hard-gated: use the expert for the predicted Type
- Soft-gated: probability-weighted sum of expert outputs

Implementation requirements for a later pass:

- The gate must be evaluated with grouped validation.
- Expert folds must be trained only from the training split to avoid leakage.
- Hard-vs-soft gating should be compared on the same folds.
- Type 3 data scarcity should be checked before using a high-capacity expert.

Possible future model key:

- `response_moe_physics_v1`

Do not expose this key in the normal UI until it beats the global baseline on a
held-out grouped evaluation.

## u3 Forecast Follow-Up

u3 Forecast already has theta/case-only models and should not reintroduce u3
bucket as a user input. u3 Type should remain an output. The next u3 step should
reuse the same challenger harness pattern after Laminate Forecast is complete:

- Compare ExtraTrees, RandomForest, HistGradientBoosting, and optional boosted
  libraries on Pt and Type.
- Consider a stacked or blended model only if current Tree and GointMLP residual
  patterns are complementary.
- Quantile or conformal intervals around Pt are promising, but should be
  evaluated as uncertainty calibration rather than as a point-metric win.

## Simple Injection Follow-Up

Simple Injection should wait until the Laminate Forecast challenger harness is
complete. The most promising first design is likely a filling histogram model
with structural softmax bins:

- Raw histogram logits go through softmax.
- Volume-ratio bins sum structurally to 100%.
- Existing weak physics penalties can remain as secondary constraints.

The sprue Fourier-feature field model is also attractive because it is simpler
than DeepONet for the current data size, but it should be evaluated after the
filling histogram constraint fix unless sprue curve residuals become the higher
priority.

## First Implementation Deliverables

- `scripts/dd_response_tabular_challengers_train.py`
- `models/dd_laminate_response_tabular_challengers_v1/`
- `reports/dd_response_tabular_challengers_v1/model_comparison.md`
- `reports/dd_response_tabular_challengers_v1/model_comparison.json`
- `scripts/dd_response_dl_challengers_train.py`
- `models/dd_laminate_response_dl_challengers_v1/`
- `reports/dd_response_dl_challengers_v1/model_comparison.md`
- `reports/dd_response_dl_challengers_v1/model_comparison.json`

The first pass should not add a backend model key.
