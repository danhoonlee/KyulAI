# Why the GointMLP loses to a lookup table on 6x4

On the fixed holdout the MLP's relative Pt error is 7.92% on 6x4 against a
nearest-neighbour lookup's 5.68%, while on 6x8 and 8x8 it beats that lookup by
a wide margin. The tree reaches 1.60% on the same rows, so the information is
in the features.

## What the split by type shows

```
panel  type    n    Pt mean    lookup     tree     goint
6x4    1      63     10,965    10.85%    2.52%     5.10%
6x4    2      98     19,687     4.37%    1.15%     8.11%
6x4    3      22     18,650     3.17%    2.19%    11.79%
6x8    1      47      6,948    43.19%    2.63%     5.46%
6x8    2     104      7,780   135.04%    0.97%     2.26%
6x8    3      32      6,769   181.48%    5.38%    15.74%
8x8    1      24      4,356   100.22%    1.75%     6.08%
8x8    2     107      5,483   201.94%    1.10%     3.62%
8x8    3      52      5,962   221.92%    8.75%    10.59%
```

## The discriminating comparison is Type 2

| Type 2 | 6x4 (P1 definition) | 6x8 (kink) | 8x8 (kink) |
|---|---:|---:|---:|
| Tree | 1.15% | 0.97% | 1.10% |
| GointMLP | **8.11%** | 2.26% | 3.62% |

The tree is flat across panels. The MLP is 3.6x worse on the one panel whose Pt
carries the PPT P1 definition.

Type 2 is exactly where P1 is a *blend*: the mean of the force-plot intersection
and the u3-plot intersection. On 6x8 and 8x8 the same response type carries the
force kink alone, with no rule to switch, and the MLP handles it at 2-4%. On 6x4
the target is the blend and its error triples.

As a function of (theta1, theta2), P1 is piecewise — it changes construction at
the type boundaries, with stored ratios to the kink of roughly 1.02, 1.68 and
2.46 for Types 1, 2 and 3. A smooth network has to approximate a jump; a tree
partitions across it and pays nothing.

## Type 3 does not discriminate

Every model is worst on Type 3 on every panel, including the two with no rule
switch (goint 15.74% on 6x8, 10.59% on 8x8). Type 3 is the heavily curved
response — intrinsically hard to fit, independent of how Pt was defined. It
cannot separate the two explanations, which is why Type 2 is the test.

## A second reading

The lookup's own profile is inverted on 6x4: 10.85% on Type 1 against 4.37% and
3.17% on Types 2 and 3, while on the other panels it is uniformly hopeless
(43-222%). So "the GointMLP loses to the lookup on 6x4" is partly the MLP
degrading and partly the lookup being unusually strong there. Both halves are
worth keeping in view before treating the comparison as a verdict on the model.

## What follows

This is evidence for unifying the Pt definition rather than for changing the
network. Any smooth model — the hybrid student sits between the two at 2.86%
overall — pays for a target that switches construction partway through the
design space. Until the definition is one thing, the MLP's 6x4 number measures
the label as much as the model.

Reproduce with `PYTHONPATH=. .venv/bin/python scripts/dd_diagnose_goint_6x4.py`.
