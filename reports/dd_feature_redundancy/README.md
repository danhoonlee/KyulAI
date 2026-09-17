# Finding 4: the features are redundant, and the DD coordinates do not fix it

Two separate claims. The first is proven. The second was tested and is false.

## The redundancy is real, and now explained

Five column pairs are numerically identical across all 2,700 rows:

```
a11           == d11          max relative difference 7.2e-16
a22           == d22
a12           == d12
a66           == d66
a11_a22_ratio == d11_d22_ratio
```

That is Kappel's result: for a valid Double-Double block the thickness-normalised
bending stiffness `D*` equals the membrane stiffness `A*`. Passing `d11` to a
model is passing `a11` twice.

Two exact identities hold on top of that:

```
a11 + a22 + 2*a66 = 24.0136301     (spread 1.8e-14 over the corpus)
a12 - a66         = -0.1638085     (spread 4.4e-15)
```

These are not coincidences of this dataset. Writing `A*` in Tsai-Pagano form,

```
A*11 = U1 + U2*xiA1 + U3*xiA2        A*12 = U4 - U3*xiA2
A*22 = U1 - U2*xiA1 + U3*xiA2        A*66 = U5 - U3*xiA2
```

gives `A*11 + A*22 + 2*A*66 = 2*(U1 + U5)` and `A*12 - A*66 = U4 - U5`, both
functions of the material alone. `tests/unit/ml/test_dd_lamination_parameters.py`
pins this. So `{a11, a22, a12, a66}` spends four columns on two degrees of
freedom, and those two are exactly the lamination parameters xiA1 and xiA2.

Within one case and one panel, 11 of the 40 columns are constant and the only
varying inputs are theta1 and theta2. Across the full corpus nothing is constant
and the linear rank is 22.

## The features still earn their place

Redundant is not the same as useless. Same tree, same fixed holdout:

| feature set | cols | Pt MAE | Pt MAE, Type 1 | Type acc |
|---|---:|---:|---:|---:|
| theta + case + panel | 5 | 467.17 | 643.12 | 0.8962 |
| canonical geometry | 40 | 200.79 | 176.93 | 0.9581 |

A nonlinear CLT re-encoding of two variables is worth 2.3x on Pt and 3.6x on the
Type 1 rows. Intrinsic dimension 2 does not mean the columns carry nothing.

Dropping the five duplicates and two derivable columns is close to free:

| feature set | cols | Pt MAE | Pt MAE, Type 1 | Type acc |
|---|---:|---:|---:|---:|
| all 40 | 40 | 200.79 | 176.93 | 0.9581 |
| minus 5 duplicates + 2 derivable | 33 | 209.12 | 193.86 | 0.9617 |

Information loss is zero by construction; the small movement is the random
feature selection in the forest, where duplicating a quantity doubles its chance
of being offered at a split and acts as an implicit weight.

## The remedy hypothesis was wrong

`theta_physics_geometry_dd_v3` adds 20 columns to the canonical 40: the
Tsai-Pagano trace, xiA1..4, xiD1..4, trace-normalised stiffnesses, and terms that
couple a bending stiffness to a panel dimension (`d11/b^2`, `d22/a^2`,
`2(d12+2d66)/ab`, the orthotropic buckling group). None of that existed before --
every geometry column in the old set is pure geometry, with no material in it.

Evaluated on the window where the target is not contaminated: 6x8 and 8x8 share
the force-plot kink definition, and only the Type 1 rows, which is where an answer
gets used. 1,434 training rows, 366 held out, 71 of them Type 1.

ExtraTrees, 10 seeds:

| feature set | cols | Pt MAE, Type 1 | rel | Type acc |
|---|---:|---:|---:|---:|
| bare theta + case + panel | 7 | 522.68 ± 13.97 | 8.61% | 0.8940 |
| canonical geometry (current) | 40 | **117.64 ± 4.64** | 1.94% | 0.9634 |
| DD coordinates only | 27 | 129.45 ± 3.66 | 2.13% | 0.9574 |
| canonical + DD (superset) | 60 | 124.60 ± 4.50 | 2.05% | 0.9612 |

A tree is largely indifferent to coordinates, so the same test with a network,
5 seeds, MLP (132, 50, 50, 50, 50), tanh:

| feature set | cols | Pt MAE, Type 1 | rel |
|---|---:|---:|---:|
| canonical geometry (current) | 40 | **159.18 ± 4.83** | 2.62% |
| DD coordinates only | 27 | 171.65 ± 15.07 | 2.83% |
| canonical + DD (superset) | 60 | 162.06 ± 13.60 | 2.67% |

Both model families agree. The current set wins, adding the DD coordinates makes
it slightly worse, and using them alone is worse still. The differences are one
to three standard deviations -- small, but consistently in the same direction.

## What this means

The DD literature's coordinates are the right way to *state* a layup, and they
explain the redundancy above exactly. They are not extra information: xiA1 and
xiA2 and `{a11, a22, a12, a66}` determine each other. Restating the same content
in more columns dilutes rather than informs.

Finding 4 is therefore closed as a modelling lead. The diagnosis stands, the
proposed remedy does not.

## Limits

71 Type 1 rows in the clean window is thin, and everything here is about Pt --
curve shape was not tested. The negative result is about predictive value for
this target, not about the theory. The 20 columns and `lamination_parameters()`
are kept, tested, and available; they are the right vocabulary for explaining a
layup even though they do not improve a prediction.
