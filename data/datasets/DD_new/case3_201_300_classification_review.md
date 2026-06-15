# DD New Case3 201-300 Classification Review

Source: `data/datasets/DD_new`
Curated output: `data/datasets/DD_curated_csv_v2`
Reclassification threshold: `0.95`

## Counts

| Label Source | Type 1 | Type 2 | Type 3 | Total |
|---|---:|---:|---:|---:|
| Sibling original | 40 | 51 | 9 | 100 |
| Current model prediction | 34 | 57 | 9 | 100 |
| Final curated | 34 | 57 | 9 | 100 |

Changed labels: 6

## Changed Labels

| Global Test | Source | theta1 | theta2 | Pt | Original | Model | Confidence | post_r2 | post_nrmse | abs_quad_a | slope_drift |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Test_241 | 201-250/Test_041 | 40 | -77 | 13778.78 | 1 | 2 | 1.000 | 0.99658 | 0.01656 | 0.21571 | 0.39789 |
| Test_266 | 251-300/Test_016 | 38 | -75 | 13749.66 | 1 | 2 | 1.000 | 0.99654 | 0.01668 | 0.21795 | 0.39805 |
| Test_272 | 251-300/Test_022 | -65 | 36 | 13812.09 | 1 | 2 | 1.000 | 0.99655 | 0.01667 | 0.21792 | 0.39585 |
| Test_291 | 251-300/Test_041 | -52 | -35 | 13944.85 | 1 | 2 | 1.000 | 0.99678 | 0.01608 | 0.20924 | 0.38493 |
| Test_293 | 251-300/Test_043 | -58 | -40 | 14531.17 | 1 | 2 | 0.999 | 0.99746 | 0.01437 | 0.18801 | 0.33308 |
| Test_295 | 251-300/Test_045 | 34 | -45 | 13943.53 | 1 | 2 | 1.000 | 0.99655 | 0.01661 | 0.21524 | 0.40184 |

Notes:

- `type` in each updated batch `transition_load.csv` is the final curated label.
- `original_type` preserves the sibling folder label.
- `Global_Test_ID` maps local batch IDs to Case3 `Test_201` through `Test_300`.
- The original `DD_curated_csv_v1` dataset is preserved; the new 500-sample dataset is `DD_curated_csv_v2`.
