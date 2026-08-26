# DD Phase 1 Immediate-Scope Preflight

- Status: **ready**
- Prepared experiment: `20260811-uq-mondrian-ood-tree-v2`
- Git branch: `codex/dd-aicomp2026-uq`
- Git commit: `06210e5f64cdc1766b94e987218c797dd1d82da0`
- Production endpoints changed: **No**

## Checks

- Frozen baseline quick verification: passed
- Case/theta group overlap: 0
- Feature matrix finite: True
- Holdout ledger status: `reused_fixed_benchmark_not_pristine_external_holdout`

## Prepared partitions

- Fit: 1725 rows / 575 groups
- Calibration: 429 rows / 143 groups
- Fixed benchmark: 546 rows / 182 groups

## Mondrian interval readiness

- Minimum required rows per geometry: 30
- 6x4: 143 calibration rows; eligible=true
- 6x8: 143 calibration rows; eligible=true
- 8x8: 143 calibration rows; eligible=true

## Next run contract

1. Generate grouped out-of-fold predictions only inside development data.
2. Select pooled or geometry-conditioned intervals from development evidence.
3. Freeze the selected method before reading fixed-benchmark targets.
4. Append the benchmark run to the usage ledger.
5. Keep the result as a challenger until review and explicit promotion.

A new untouched simulation set is still required for publication-grade external validation.
