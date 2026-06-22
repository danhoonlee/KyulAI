# Model Upgrade No-Curve CSV Review Summary - 2026-06-17

## Context

User provided `codex_model_upgrade_no_curve_csv_prompt.md` and asked for a critical but productive review before proceeding.

## Key Findings

- The proposed no-touch rule for Curve CSV classifier work is well aligned with the current risk surface. `/predict/curve`, `curve_classical`, and `curve_goint` are separate from Laminate Forecast response models and should stay untouched.
- The strongest current Laminate Forecast baseline is `response_surrogate_physics_v2`, with 900 samples, compact physics features, GroupKFold validation, Type accuracy around 0.942, macro F1 around 0.937, Pt MAE around 438, and normalized curve RMSE around 0.007.
- The GointMLP physics variants are not clearly better than the tree baseline on scalar and curve metrics. Their Type metrics are close, but Pt, max force, and curve force RMSE are weaker.
- XGBoost, LightGBM, CatBoost, and TabPFN are not installed in the current environment. A challenger script should skip those gracefully unless the project intentionally adds optional research dependencies.
- The current code already has most of the needed evaluation machinery: grouped validation, compact physics feature builders, PCA curve reconstruction, scalar/curve metrics, and stable prediction APIs.
- A first implementation pass should prioritize a reusable evaluator/reporting layer over adding backend model keys or changing UI/API defaults.

## Recommended Direction

1. Create the design document first under `docs/design/dd_laminate_model_upgrade_no_curve_csv.md`.
2. Implement `scripts/dd_response_tabular_challengers_train.py` as a research/evaluation script, not a production registry change.
3. Start with sklearn challengers that are already available: ExtraTrees, RandomForest, HistGradientBoosting, and a regularized linear baseline for scalar heads.
4. Add optional dependency hooks for XGBoost, LightGBM, CatBoost, and TabPFN, but record skipped status in JSON/Markdown reports.
5. Compare every challenger directly against `response_surrogate_physics_v2` and `response_goint_physics_nn_v2` using the same dataset, groups, feature set, curve grid, PCA component policy, and metrics.
6. Treat Type-gated MoE as a second-stage design unless a challenger report shows Type-specific residual patterns that justify it.
7. Defer u3 and Simple Injection implementation until the Laminate Forecast evaluation harness is complete.

## Cautions

- Do not promote a challenger by a single metric. Require meaningful improvement on at least Pt and curve metrics without sacrificing Type macro F1.
- Avoid adding heavy dependencies to serving requirements. Optional research dependencies belong in training-only flows if used at all.
- Do not overwrite existing model folders or defaults.
- Keep Curve CSV classifier files and behavior unchanged.
