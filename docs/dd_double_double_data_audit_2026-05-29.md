# Double-Double New Dataset Audit - 2026-05-29

Source folder: `data/datasets/Double-Double`

Requested training scope: folders `2`, `3`, and `4`.

## Summary

The new dataset is not the same as the previous training dataset in `data/datasets/DD_curated_csv_v2`.

- New Case 3 and Case 4 use the same `Test_001` to `Test_300` IDs, but the theta pairs and force-displacement CSV curves do not match the previous curated Case3/Case4 training data.
- The new folders 2, 3, and 4 share the same 300 theta pairs with each other.
- Case 2, Case 3, and Case 4 are now complete for P1 supervised training.
- Case 3 initially had two unclassified images left in `p1/`; these were classified and moved on 2026-05-29.

## Dataset Structure Found

Each usable case folder contains:

- `transition load P1.csv`
- `transition load.csv`
- `csv/`
- `p1/1`, `p1/2`, `p1/3`

For training against P1 labels, `transition load P1.csv` should be used. `transition load.csv` has the same theta values but different Pt values for every row, so it appears to represent a different transition/load definition.

## Case-Level Counts

| New folder | Training case | Transition P1 rows | Curve CSV IDs | P1 image labels | Type 1 | Type 2 | Type 3 | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `2` | Case 2 | 300 | 300 | 300 | 108 | 145 | 47 | Complete |
| `3` | Case 3 | 300 | 300 | 300 | 117 | 136 | 47 | Complete |
| `4` | Case 4 | 300 | 300 | 300 | 96 | 164 | 40 | Complete |

## Case 3 Label Completion

Case 3 no longer has missing P1 labels.

Two images were found directly under `data/datasets/Double-Double/3/p1` and manually classified with visual inspection plus CSV-feature/model checks:

- `plot_Test_206_P1.png` -> Type 2, moved to `data/datasets/Double-Double/3/p1/2/plot_Test_206_P1.png`.
- `plot_Test_286_P1.png` -> Type 3, moved to `data/datasets/Double-Double/3/p1/3/plot_Test_286_P1.png`.

Final Case 3 check:

- Transition P1 rows: 300.
- Recursive curve CSV IDs: 300.
- P1 image labels: 300.
- Unclassified PNG files directly under `p1/`: 0.

## Compatibility With Existing Training Code

The existing DD Laminate training code expects a curated structure like:

- `Case3/transition_load.csv`
- `Case3/csv_load/force_disp_Test_001.csv`
- `Case4/transition_load.csv`
- `Case4/csv_load/force_disp_Test_001.csv`

Current code also assumes only Case3 and Case4 in several places:

- `src/backend/api/v1/dd_laminate.py`
- `src/ml/dd_laminate/train_theta_classifier.py`
- `src/ml/dd_laminate/train_response_surrogate.py`
- `src/ml/dd_laminate/deep_sequence.py`
- `src/ml/dd_laminate/laminate_physics.py`

To train on Case 2, 3, and 4, we need a new curated dataset plus code changes for a 3-case encoding.

## Recommended Next Step

Do not overwrite the existing trained models.

Recommended path:

1. Create a new curated dataset, for example `data/datasets/DD_cases_2_3_4_curated_v1`.
2. Convert folders `2`, `3`, `4` into normalized case names: `Case2`, `Case3`, `Case4`.
3. Use `transition load P1.csv` as the transition metadata.
4. Copy all curve CSVs into each case's `csv_load/` folder. Case 3 needs recursive CSV lookup because some CSVs live in nested `csv/1`, `csv/3`, and `csv/New folder`.
5. Add final Type labels from `p1/1`, `p1/2`, `p1/3`.
6. Update training code to support Case2/Case3/Case4 case encoding and save outputs under new model directories.
7. Train a new model family against the normalized 900-sample dataset.
