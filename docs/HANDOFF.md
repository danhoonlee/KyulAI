# Handoff — read this first

State as of 2026-09-10. Written so a session starting anywhere, with no prior
context, can pick the work up in a few minutes.

`docs/session-memory.md` is the full log and runs to 16,000 lines. Do not read
it front to back. Search it for a date or a heading when this file points you
there.

---

## Where things are

| | |
|---|---|
| Repo | `github.com/danhoonlee/KyulAI`, **public** |
| Working branch | `wsl-live-20260826` — the live server runs from this tree |
| Serving host | this WSL box, `~/projects/KyulAI` |
| Research checkout | `~/KyulAI-raw` — different branch, leave alone unless asked |
| Team channel | Slack `#imperialax-dev` (`C0BSZ03KK2A`), workspace `imperialax` |

**uvicorn loads the working tree directly.** Editing a file and restarting a
unit puts it in front of customers. There is no deploy step.

```bash
systemctl --user restart imperialax-laminate      # or imperialax-injection
curl https://ai.imperialax.com/health
```

Services: `imperialax-laminate` (:8000, ai/laminate/dd/app),
`imperialax-injection` (:8010), `imperialax-cloudflared`, `imperialax-redis`,
`cafedecafe-*`, `ds-wedding`. A five-minute health check watches all of them and
posts to `#imperialax-dev` on state change — see
`docs/SERVING_HEALTH_MONITORING.md`.

Never commit `data/imperialax_auth.sqlite3` (real accounts), `runs/` (24G) or
model artifacts. The repo is public.

---

## What the laminate model is for

**Pt, the transition load, is the target.** Where the material starts to deform
and the response changes regime. That is the research question.

**Max force is not an independent quantity.** The prescribed displacement is
fixed at 0.15 in, so max force is the load at the end of the stroke — verified
180 of 180 sampled curves have their maximum at the curve's end. Max
displacement is constant at 0.15 for 2,683 of 2,700 rows. Reporting `pt_mae` and
`max_force_mae` side by side is close to counting one result twice.

**The curve splits at Pt and both halves should read as linear.** Type 1 is the
ideal clean bilinear; Type 2 curves after the transition; Type 3 curves heavily.
The Type label is a grading of how well a bilinear description holds, not an
arbitrary three-class problem.

---

## The four findings, and where each stands

An audit on 2026-08-28 found four problems, all upstream of the models. None was
a modelling-technique failure.

### 1. Pt mixes two definitions — **OPEN, blocked on a person**

6x4 rows carry the PPT "P1" definition; 6x8 and 8x8 carry the force-plot kink.
The two source tables differ on all 300 rows per case and correlate at r ≈ 0.14.
At a fixed design point, Pt correlates +0.746 between 6x8 and 8x8 (same
definition) but +0.022 between 6x4 and 6x8.

This reinterprets an older conclusion: leave-one-geometry-out Pt MAE of 9,829
for 6x4 against 1,394 for 6x8 was read as weak extrapolation. It is not — the
target is a different physical quantity.

**P1 cannot be rebuilt from anything in this repository.** Four readings of the
u3 construction were tried and all fail (`reports/dd_p1_definition_check/`). The
decisive evidence is Type 1, which needs no u3 curve at all: stored P1 sits above
the recomputed force-plot intersection on **13 of 13** sampled rows, median
+2.18%, never below. A one-sided offset means a different construction. Slide 10
of `data/PPT/Final ver2.pptx` explains it — Stage 4 of the pipeline is
"Check if Pt is correct by looking at the xy plot", a human eyeball step.

**Waiting on:** the original author (the user's brother, at UW). Question sheet
prepared: https://claude.ai/code/artifact/17202040-e9a8-40fd-b2ec-90604ac97290

**If no answer comes:** unify on the force-plot kink, which
`scripts/dd_recompute_kink_pt.py` reproduces to 1e-9 for all three geometries
today. Cost: gives up the physical fidelity the PPT wanted for Types 2 and 3,
which is 76% of the corpus. Record the decision and the cost.

### 2. The holdout leaked — **FIXED** (`39c08cd`)

The split keyed on `case|theta1|theta2`, but Case2/3/4 of one design are the same
laminate to within what these targets depend on — the building-block permutation
moves only D16, D26 and B. Pt across cases at a fixed design varied by a median
0.14%. 537 of 546 held-out rows had a same-angle twin in training, and a lookup
table beat every trained model on Pt (132 against 190).

Now keyed on the angle pair alone, matching what the six challenger trainers
already did. A `Nearest-design lookup` baseline is a permanent row in the report:
**a model that does not clearly beat it has not been shown to generalise.**
`tests/unit/ml/test_dd_split_key.py` pins this.

### 3. Two thirds of type labels are unreviewed — **PARTLY ANSWERED**

Every 6x8 and 8x8 type label is `curve_classifier_v1` output, mean confidence
0.708 and 0.625, minimum 0.433 on a three-class problem. That classifier takes
`pt` as a feature and was trained on 6x4 P1-definition rows, so the feature is
out of distribution exactly where its confidence collapses.
`type_label_confidence` is in the manifest and read by no training script.

An independent measure using curve shape only and no `pt`, calibrated on the 900
human-reviewed 6x4 labels, settled the main question
(`reports/dd_type_label_audit/`): **the Type 1 collapse across panel sizes is
real physics, not labeller drift.** Independent Type 1 share is 35.6% on 6x4
against a stored 35.7%, and 24.0% against 25.2% on 6x8.

That measure detects Type 1 well (precision 94.4%) and **cannot separate Type 2
from Type 3 at all** (21 of 134 recovered) — do not use it there.

**Waiting on:** a person to review 56 curves, ~10 minutes.
https://claude.ai/code/artifact/723cb962-5300-4fca-879e-324bd0ae8d84
These are 8x8 rows labelled Type 1 that the measure rejects — 53% of that
panel's Type 1 rows against 6% and 8% elsewhere. Verdicts go in
`reports/dd_type_review_8x8/review_list.csv`, column `verdict_type1_yes_no`.

### 4. Features encode two degrees of freedom, not 24 — **NOT STARTED**

`A11+A22+2·A66` is constant (it is Tr(Q)) and `A12−A66` is constant, so
`{A11,A22,A12,A66}` has effective rank 2. `a11≡d11`, `a22≡d22`, `a12≡d12`,
`a66≡d66` to 1e-14 — Kappel proves `D*` equals `A*` for valid DD blocks. Eight
more columns are identically constant. Nothing computes the laminate trace
normalisation or the lamination parameters ξA1, ξA2 that the Double-Double
literature is built on, and no feature multiplies a stiffness by a panel
dimension.

Lower priority than 1–3: feature work cannot be measured while the target is
bimodal.

---

## What else was fixed

| Commit | |
|---|---|
| `b256099` | A month of serving-host work had never been committed — the host had no push credentials at all. Recovered to this branch. |
| `42a403e` | Merged the 2026-07-22 branding rename. Every conflict resolved to the serving side; taking origin would have put `demo-token` and `danlee-token` back into a public repo. |
| `e9319e1` | Backend tests realigned with hardened auth: 32 failures → 1, none of them code bugs. |
| `bba5ae4` | Removed retired demo credentials from the iOS **and** Android clients. **Neither was compiled — this host has no Swift or Android toolchain. Build both before any release.** |
| `89e6da2` | Panel dimensions bounded to 6–8 × 4–8 in. Outside that the tree answered from the nearest trained leaf: 100×4 returned 6×4's Pt to four decimal places. |
| `831c75c` | The reliability panel was blind to panel size — it reported "interpolation, high confidence, well-covered" for a 100×4 panel. |
| `e4398c4` | Health monitoring. An injection outage had run 10 hours unnoticed; it was a clean SIGTERM, so `OnFailure` would never have caught it. |
| `25586fd`, `bfa9668` | OpenRadioss starter and output converters built. Two upstream `-no-python` defects patched. See `infrastructure/openradioss/README.md`. |

---

## Current numbers

Honest as of the split fix. `reports/dd_response_geometry_split_v2_3size/`.

```
                                  Type acc     Pt MAE
lookup (no training)                0.7741   6,879.06
Geometry Tree                       0.9581     204.08
Geometry GointMLP                   0.9581     675.29
Geometry Hybrid Student             0.9563     327.87
```

**Compare the relative column, not the absolute one.** Pt differs by more than a
factor of two across panels, so a pooled Pt MAE lets a change in the geometry mix
read as a change in accuracy.

```
panel    lookup     Tree   GointMLP   Hybrid
6x4       5.68%    1.60%      7.92%    2.86%
6x8     120.30%    2.08%      5.19%    3.08%
8x8     197.50%    3.54%      6.04%    5.17%
```

Two things only visible split: the lookup is respectable on 6x4 (5.68%) where the
design grid is dense, and **the GointMLP is worse than the lookup there**. Traced
to finding 1 — `reports/dd_goint_6x4_diagnosis/`. The discriminating cell is
Type 2, where the tree is flat across panels (1.15 / 0.97 / 1.10%) while the MLP
is 3.6× worse on the P1-definition panel (8.11% against 2.26 / 3.62%). Type 2 is
where P1 is a *blend* of two intersections. A smooth network approximates the
rule switch; a tree partitions across it.

---

## Landmines

- **`docs/session-memory.md` must be appended to after every piece of work**,
  without being asked. Format: `## YYYY-MM-DD - Title In Title Case`, then `-`
  bullets in English wrapped near 100 chars, facts and numbers, usually ending
  with a `Verification:` bullet. Commit and push it.
- **Reported values are labelled `kips` and are actually `lbf`** — no `/1000`
  exists anywhere in the pipeline, Pt spans 2,345–34,578 lbf, and the PPT's own
  body text says `lbs` while only its plot axes say kips. The mislabel is
  inherited. Not yet fixed; it reaches the customer-facing UI.
- **`theta_physics_geometry_v1` builds a wrong Case3 stack** — `∓θ1` dropped and
  `±θ2` duplicated, 4 θ1 plies where the canonical block has 8. It is still the
  default in `dd_response_pt_consistent_tree_train.py` and
  `dd_response_pt_consistent_deep_train.py`. The holdout eval's default was
  corrected; those two were not.
- **An artifact without `feature_builder` is silently served with legacy
  physics.** `feature_set_from_columns` cannot distinguish legacy from canonical
  because the column names are identical.
- **Do not quote numbers from the `KyulAI_dl_v2`/`dl_v3`/`uq` worktrees** — they
  were removed, and their reports were a superseded version where Curve RMSE used
  a different aggregation.
- **The Slack MCP holds one workspace at a time.** Connecting `imperialax`
  replaced `nangmaninchq`.
- Memory files under `~/.claude/projects/<path>/memory/` are scoped to the
  directory Claude was started from. They do not follow you to another location.
  This file does, because it is in the repo.

---

## If you are picking this up cold

1. Read this file and `CLAUDE.md`.
2. Check the two human-blocked items above have not been answered while you were
   away — the review CSV and any reply from UW.
3. If the Pt definition arrived: encode the rule, regenerate the column for all
   three geometries, retrain, re-evaluate. That is the main line.
4. If it did not: everything except finding 1 is still workable. The nearest
   unblocked piece is finding 4, or writing the per-panel breakdown into the
   remaining trainers.

Detail for any of this is in `docs/session-memory.md` under its date.
