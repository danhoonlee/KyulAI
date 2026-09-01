# An independent second opinion on the response-type labels

Two thirds of the type labels — every 6x8 and 8x8 row — are unreviewed
predictions from `curve_classifier_v1`. The Type 1 share falls
35.7% → 25.2% → 11.8% as the panel grows, tracking that classifier's own
confidence collapse (1.00 → 0.71 → 0.63), and it was not possible to say
whether that was physics or labeller drift.

The classifier cannot settle this about itself. It takes `pt` as an input
feature and was trained on 6x4 rows carrying the PPT P1 definition, then
applied to rows carrying the force kink — the feature is out of distribution
exactly where its confidence falls.

So the curves were scored again by the rule the presentation states, from shape
alone and with no `pt`: fit two straight lines, and measure how much the
post-transition branch bends. Calibrated against the 900 human-reviewed 6x4
labels, then applied to the pseudo-labelled panels.

## What this measure can and cannot do

Against the human 6x4 labels:

```
             ->1    ->2    ->3    total
stored 1     302     19      0      321
stored 2      17    404     24      445
stored 3       1    112     21      134
```

**Type 1 detection is reliable**: precision 302/320 = 94.4%, recall
302/321 = 94.1%.

**Type 2 against Type 3 is not**: only 21 of 134 Type 3 rows are recovered. A
single curvature threshold does not separate "curves" from "curves heavily".
Every claim below is therefore restricted to Type 1 against the rest.

This also explains an apparent anomaly. Agreement with the pseudo-labels is not
monotone in classifier confidence — the 0.8-0.9 band scores worst (49.4% on
6x8, 17.7% on 8x8). All 172 disagreements in that band are `stored 3 -> mine 2`.
That is this measure failing, not the labels.

## The Type 1 collapse is real

```
geometry   stored T1   independent T1   stored T1 that this measure rejects
6x4            35.7%            35.6%                            19  (6%)
6x8            25.2%            24.0%                            19  (8%)
8x8            11.8%             6.0%                            56 (53%)
```

An independent, `pt`-free measure reproduces the stored Type 1 share almost
exactly on 6x4 (35.6 against 35.7) and closely on 6x8 (24.0 against 25.2). The
fall with panel size is **not an artefact of the pseudo-labeller**: larger
panels really do produce fewer clean bilinear responses.

If anything the stored labels *understate* it. On 8x8 this measure rejects 56 of
the 106 rows labelled Type 1 — 53%, against 6% and 8% on the other panels —
while its Type 1 precision on human data is 94%. The reasonable reading is that
the classifier over-calls Type 1 on 8x8, and the true share there is below
11.8%.

## Where human review is worth spending

The 56 rows on 8x8 labelled Type 1 that this measure rejects. They are few
enough to review by eye, they sit in the one place the two methods disagree
sharply, and the measure making the claim is 94% accurate on the class in
question. `type_label_audit.csv` has them: `geometry == 8x8`, `label == 1`,
`independent != 1`.

Reviewing the 3-versus-2 disagreements would not be worth the time — this
measure has no standing there.

## Files

- `type_label_audit.csv` — every row with its stored label, the independent
  call, the bilinear fit quality, the tail curvature and the break position.
- `summary.json` — thresholds and per-geometry shares.
- `scripts/dd_audit_type_labels.py` — rerun to reproduce.
