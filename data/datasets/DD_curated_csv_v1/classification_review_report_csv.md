# CSV-Based DD Classification Review

This report updates the previous image/model review using raw force-displacement CSV curves.

## Paper-Derived Criterion

For unsymmetric DD laminates, a classical bifurcation load is not the key response quantity. The relevant quantity is the transition load from nonlinear load-displacement response, estimated at the intersection of the two stable path slopes. Therefore, Type classification should be driven by whether the post-transition branch is linear, moderately curved, or strongly/continuously curved.

## Final Label Changes

| Case | Test_ID | Original | Final | Confidence | Reason | r2_post | abs_quad_a | slope_drift | data_quality |
|---|---|---:|---:|---|---|---:|---:|---:|---|
| Case3 | Test_008 | 2 | 1 | high | csv_post_transition_is_type1_linear; overrides_report_borderline_keep | 0.99946 | 0.0896 | 0.1180 | ok |
| Case3 | Test_085 | 3 | 2 | high | report_change_supported_by_csv_moderate_curvature | 0.98316 | 0.4831 | 0.8216 | ok |
| Case3 | Test_162 | 3 | 2 | high | report_change_supported_by_csv_moderate_curvature | 0.98860 | 0.3963 | 0.6912 | ok |
| Case3 | Test_166 | 3 | 2 | high | report_change_supported_by_csv_moderate_curvature | 0.98256 | 0.4928 | 0.8345 | ok |
| Case3 | Test_180 | 3 | 2 | high | report_change_supported_by_csv_moderate_curvature | 0.98565 | 0.4490 | 0.7546 | ok |
| Case3 | Test_197 | 3 | 2 | high | report_change_supported_by_csv_moderate_curvature | 0.98698 | 0.4222 | 0.7378 | ok |
| Case4 | Test_017 | 1 | 2 | high | report_change_supported_by_csv_curvature | 0.99674 | 0.2109 | 0.3852 | ok |
| Case4 | Test_023 | 1 | 2 | high | report_change_supported_by_csv_curvature | 0.99564 | 0.2434 | 0.4511 | ok |
| Case4 | Test_042 | 1 | 2 | high | report_change_supported_by_csv_curvature | 0.99619 | 0.2293 | 0.4168 | ok |
| Case4 | Test_047 | 1 | 2 | high | report_change_supported_by_csv_curvature | 0.99623 | 0.2280 | 0.4161 | ok |
| Case4 | Test_054 | 1 | 2 | high | report_change_supported_by_csv_curvature | 0.99615 | 0.2308 | 0.4197 | ok |
| Case4 | Test_063 | 1 | 2 | high | report_change_supported_by_csv_curvature | 0.99674 | 0.2117 | 0.3856 | ok |
| Case4 | Test_064 | 1 | 2 | high | report_change_supported_by_csv_curvature | 0.99595 | 0.2367 | 0.4299 | ok |
| Case4 | Test_069 | 1 | 2 | high | report_change_supported_by_csv_curvature | 0.99609 | 0.2298 | 0.4270 | ok |
| Case4 | Test_102 | 1 | 2 | high | report_change_supported_by_csv_curvature | 0.99745 | 0.1855 | 0.3428 | ok |
| Case4 | Test_114 | 1 | 2 | high | report_change_supported_by_csv_curvature | 0.99744 | 0.1885 | 0.3321 | ok |
| Case4 | Test_115 | 1 | 2 | high | report_change_supported_by_csv_curvature | 0.99664 | 0.2147 | 0.3920 | ok |
| Case4 | Test_138 | 1 | 2 | high | report_change_supported_by_csv_curvature | 0.99604 | 0.2327 | 0.4258 | ok |
| Case4 | Test_157 | 1 | 2 | high | report_change_supported_by_csv_curvature | 0.99689 | 0.2069 | 0.3752 | ok |
| Case4 | Test_179 | 1 | 2 | high | report_change_supported_by_csv_curvature | 0.99626 | 0.2276 | 0.4138 | ok |
| Case4 | Test_190 | 1 | 2 | high | report_change_supported_by_csv_curvature | 0.99580 | 0.2382 | 0.4436 | ok |
| Case4 | Test_192 | 1 | 2 | high | report_change_supported_by_csv_curvature | 0.99633 | 0.2248 | 0.4101 | ok |
| Case4 | Test_194 | 1 | 2 | high | report_change_supported_by_csv_curvature | 0.99521 | 0.2591 | 0.4594 | ok |
| Case4 | Test_200 | 1 | 2 | high | report_change_supported_by_csv_curvature | 0.99614 | 0.2314 | 0.4186 | ok |

## Needs Manual/Data Review

| Case | Test_ID | Kept Label | Reason | post_points | pt | r2_post | data_quality |
|---|---|---:|---|---:|---:|---:|---|
| Case3 | Test_078 | 2 | csv_tail_insufficient; kept_original_label | 33 | 14002.89 | 0.99138 | short_curve_but_usable |
| Case3 | Test_152 | 2 | csv_tail_insufficient; kept_original_label | 3 | 13831.04 | 0.27483 | insufficient_post_transition_tail |

## Counts

| Case | Type 1 | Type 2 | Type 3 |
|---|---:|---:|---:|
| Case3 | 62 | 118 | 20 |
| Case4 | 64 | 116 | 20 |
