# Can the P1 transition load be rebuilt from the raw curves?

`transition load P1.csv` is the Pt label the 6x4 rows train on. Nothing in this
repository records how those numbers were produced, and
`docs/session-memory.md` already conceded the point: *"that upstream Pt may have
been manually or experimentally marked before the data reached us."*

This check tried to settle it, because the answer decides what can be done about
the target: if P1 is defined by a rule we can run, the same rule can be pointed
at any geometry that has a u3 curve. If it is not, that option does not exist.

## What was tried

`docs/DD_Laminate_PPT_Basis.md` states the rule:

| Type | Transition load |
|---|---|
| 1 | force-plot intersection |
| 2 | mean of the force-plot and u3-plot intersections |
| 3 | u3-plot intersection |

`dd_recompute_kink_pt.py` already reproduces the force-plot intersection —
`transition load.csv` — to within 1e-9, so the force half is settled. The u3 half
was attempted four ways:

1. **The same bilinear fitter applied to force-vs-u3.** Gives ~3,100 where the
   rule needs ~27,400 for Case2/Test_001. The u3 curve starts near-vertical, so
   the "slope dropped to 0.65x initial" test fires almost immediately.
2. **Tangent extrapolation back to u3 = 0**, the standard buckling construction.
   Intercepts over every post-buckling window land between 142 and 8,335 — never
   near the required value.
3. **u3 against applied displacement**, joined by row index since both files
   carry the same 1001 rows and an identical force column. The initial u3 slope
   (1.145) is steeper than every later window, so the intersection goes negative.
   These runs seed an imperfection, so u3 grows from the first increment; there
   is no flat pre-buckling branch to intersect.
4. **A statistical search** for any tight relationship. The closest are
   `u3(P1)/max(u3)` at 0.51 for both types and `P1/max(force)` at 0.557 for
   Type 2, but their coefficients of variation are 0.09-0.15. A definition would
   be exact; these are descriptions.

## Result

```
group          n   median rel   mean rel     <1%     <5%
Type 1        77      0.02475    0.02616   24.7%   88.3%
Type 2       154      0.61197    0.59515    0.0%    0.0%
Type 3        18      0.88599    0.89100    0.0%    0.0%
```

**The rebuild fails, and it fails in the most informative place.** Type 1 needs
no u3 curve at all — the rule is just the force-plot intersection, which is
reproduced to 1e-9 elsewhere. Yet stored P1 sits above it on **13 of 13** sampled
rows, median +2.18%, never below. A fitting difference would scatter around zero.
A one-sided offset means the stored number was built by a different construction,
not by the one the PPT describes.

Types 2 and 3 are not close by any reading tried here.

## What follows

P1 cannot be regenerated from what is in this repository. That removes the option
of rebuilding 6x8 and 8x8 under the P1 definition — not only because those
geometries have no u3 export, but because the rule itself is not recoverable.

The remaining honest choices for a single Pt definition are the force-plot kink,
which is reproducible to 1e-9 for all three geometries today, or new u3 exports
plus a documented construction agreed with whoever produced the original labels.

## Files

- `p1_definition_check.csv` — per test: the force-plot fit, the u3-plot fit, the
  rebuilt P1, the stored P1, and the error.
- `summary.json` — the table above.
- `scripts/dd_verify_p1_definition.py` — rerun with `--limit 0` for the full set.
