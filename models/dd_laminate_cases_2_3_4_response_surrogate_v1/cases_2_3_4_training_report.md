# DD Cases 2/3/4 Training Report

- Dataset: `data/datasets/DD_cases_2_3_4_curated_v1`
- Total samples: 900
- Validation: GroupKFold by theta pair, so the same theta pair is not split across train/validation.

## Type Counts
- Type 1: 321
- Type 2: 445
- Type 3: 134

## Best Models
- theta: `random_forest` / accuracy 0.931 +/- 0.018, macro F1 0.928 +/- 0.020
- curve: `extra_trees` / accuracy 0.953 +/- 0.016, macro F1 0.949 +/- 0.019

## Laminate Forecast Surrogate
- Type accuracy: 0.924 +/- 0.011
- Type macro F1: 0.915 +/- 0.017
- Pt MAE: 496.22
- Max. Displacement MAE: 0.00051
- Max. Force MAE: 578.67
- Normalized curve RMSE: 0.0096

## Note
- This is a separate new-model experiment. Existing DD production model folders are not overwritten.
