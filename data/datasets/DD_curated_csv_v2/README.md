# DD Curated CSV v1

This dataset preserves the original DD data and copies files into corrected type folders using raw force-displacement CSV validation.

## Canonical Case Names

- Case 1: To be determined.
- Case 2: [[+-theta1]/[+-theta2]]4 (not included in this curated dataset).
- Case 3: [[+-theta1]/[+-theta2]/[-+theta2]/[-+theta2]]2.
- Case 4: [([+-theta1]/[+-theta2])2 / ([-+theta1]/[-+theta2])2].

## Label Counts

| Case | Original T1 | Original T2 | Original T3 | Curated T1 | Curated T2 | Curated T3 |
|---|---:|---:|---:|---:|---:|---:|
| Case3 | 61 | 114 | 25 | 62 | 118 | 20 |
| Case4 | 82 | 98 | 20 | 64 | 116 | 20 |

## Method

- The advisor paper defines transition load for unsymmetric DD laminates from nonlinear load-displacement response, approximately at the intersection of two stable path slopes.
- This curation uses the raw `csv_load` force-displacement curves as the primary evidence for post-transition linearity/curvature.
- Metrics include post-transition linear-fit R2, normalized RMSE, quadratic curvature coefficient, slope drift, and tail slope ratio.
- Existing `classification_review_report.md` was treated as a candidate-change report, then checked against CSV evidence.

## Important Decisions

- Case3 Test_085, Test_162, Test_166, Test_180, Test_197: Type 3 -> Type 2; CSV confirms moderate curvature rather than heavy Type 3 tail curvature.
- Case3 Test_008: Type 2 -> Type 1; CSV metrics place it with clean/borderline Type 1 curves.
- Case4 report Type 1 -> Type 2 recommendations were accepted except Test_078 and Test_152, whose CSV curves are strongly Type 1-linear.
- Case3 Test_078 and Test_152 are retained as Type 2 but flagged `needs_review` because the raw CSV tail after Pt is missing or too short for a reliable post-transition decision.

Changed labels: 24 samples.
Needs-review labels: 2 samples.

See `classification_audit.csv` and `classification_review_report_csv.md` for row-level evidence.

## v2 Update: Case3 Test_201-Test_300

- Added 100 new Case3 samples from `data/datasets/DD_new/201-250` and `data/datasets/DD_new/251-300`.
- Original sibling labels were checked with the current CSV metadata+curve classifier.
- Changed labels after review: 6.
- Final new-sample counts: Type1=34, Type2=57, Type3=9.
- Review report: `data/datasets/DD_new/case3_201_300_classification_review.md`.
