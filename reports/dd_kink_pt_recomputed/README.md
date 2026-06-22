# DD Kink-Based Pt Recalculation

Generated from `/Users/danlee/KyulAI_codex/data/datasets/Double-Double`
with `scripts/dd_recompute_kink_pt.py`.

## Method

The script recomputes Pt directly from each force-displacement CSV instead of
trusting existing `transition load.csv` values.

Algorithm:

1. Estimate the initial slope from the first 3 to 5 points.
2. Detect the kink using a centered 7-point sliding slope.
3. Mark kink start when 3 consecutive local slopes drop below 65% of the
   initial slope.
4. Fit the first line on the best 3 to 7 point window before kink.
5. Fit the second line on a 5 point window after kink, starting at least
   `kink_idx + 2`.
6. Compute Pt as the intersection of the two fitted lines.
7. If the intersection is after kink, clamp Pt to just before kink.

## Outputs

- `recomputed_kink_pt.csv`: Pt recomputation summary for all scanned CSV files.
- `overlay_plots/`: sample plots showing force-displacement, kink, fitted
  lines, and recomputed Pt.

## Verification Summary

- Processed CSV files: 1,480
- Failures: 0
- Double-Double base case records: 900
- u3 records: 580
- Existing `transition load.csv` comparison was applied only to the 900 base
  Double-Double records.
- The recomputed base Double-Double Pt values matched existing transition
  values within floating-point noise.
