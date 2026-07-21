# TAC vs DD Laminate PPT Basis

Source: `data/PPT/TAC vs DD.pptx`

This note extracts the main technical points from the TAC vs DD comparison
presentation so the Laminate RAG assistant can answer comparison questions
without depending only on raw slide text extraction.

## Main Purpose

The presentation compares Double-Double (DD) laminate stacking and TAC-style
angle-pair laminate stacking. Both use positive and negative angle pairs, but
their design freedom and coupling behavior are different.

DD is treated as the safer baseline for general plate behavior because it can
keep membrane-bending coupling terms near zero while maintaining balanced
in-plane stiffness. TAC can be useful when weight reduction or targeted
directional stiffness is important, but its nonzero coupling terms must be
validated carefully.

## DD vs TAC Concept

DD uses two main angle families, generally written with `+theta` and `-theta`
pairs. TAC is not limited to two angle-pair families. It can use more angle
pairs and intentionally tailor coupling through antisymmetric relationships.

The important TAC feature in the slides is that `B16*` and `B26*` can become
nonzero. These membrane-bending coupling terms are not automatically bad, but
they mean the laminate response can be more coupled and less predictable unless
the coupling is part of the design target.

## DD Case Comparison

The PPT emphasizes that two DD stacks can contain the same angle counts but
still have different normalized bending stiffness because stacking order changes
the through-thickness distribution.

For the DD comparison:

| Case | A11*/A22* | D11*/D22* | B16*, B26* | Interpretation |
| --- | ---: | ---: | --- | --- |
| Case 1 | 1.00 | 1.28 | 0 | More balanced DD baseline |
| Case 2 | 1.00 | 2.96 | 0 | Larger D11*, but more directionally biased because D22* is lower |

The key conclusion is that the same `A*` does not imply the same `D*`. Buckling
and bending depend not only on ply angle counts, but also on where each angle
family is placed through the laminate thickness.

Case 1 is described as the more balanced DD baseline. Case 2 has larger
longitudinal bending stiffness, but the larger `D11*/D22*` ratio makes it more
directionally biased.

## TAC 8-Ply Case Comparison

The 8-ply TAC cases also show that identical angle counts can produce different
normalized bending stiffness because stacking order changes the laminate
through-thickness stiffness distribution.

| Case | A11*/A22* | D11*/D22* | B16*, B26* | Interpretation |
| --- | ---: | ---: | --- | --- |
| Case 3 | 1.76 | 6.27 | -2.6, -1.13 | Specialized high-D11* TAC case |
| Case 4 | 1.00 | 3.97 | -2.57, -1.46 | More balanced 8-ply TAC representative |

Case 3 gives higher `D11*`, so it is stronger in the x-direction bending sense.
However, it is also much more directionally biased. Case 4 gives
`A11*/A22* = 1.00`, so its in-plane stiffness is more balanced.

Both Case 3 and Case 4 have nonzero `B16*` and `B26*`, which is the key TAC
coupling feature. The presentation recommends Case 4 as the better 8-ply TAC
representative for main comparison, while Case 3 should be described as a
specialized high-`D11*` design.

## TAC 6-Ply Case Comparison

The 6-ply TAC cases are used to check whether TAC can provide an advantage with
fewer plies.

| Case | A11*/A22* | D11*/D22* | B16*, B26* | Interpretation |
| --- | ---: | ---: | --- | --- |
| Case 5 | 3.66 | 9.00 | -2.68, -0.78 | Largest D11*, but highly directional |
| Case 6 | 1.99 | 6.16 | -2.83, -1.12 | More balanced 6-ply TAC representative |

Case 5 has the largest `D11*` among the compared cases, but it is highly
directional because `D22*` is very low. Case 6 sacrifices some `D11*` but
improves `A22*` and `D22*`, making it the more balanced 6-ply TAC option.

The presentation therefore prefers Case 6 as the 6-ply TAC representative.
Case 5 is best only when the design objective is maximum x-direction bending
stiffness.

## Overall Selection Logic

For aerospace structures, the preferred laminate is not simply the one with the
largest `D11*`.

For DD baseline versus 8-ply TAC:

- Case 1 is the best DD baseline.
- Case 4 is the best 8-ply TAC representative because `A11*/A22* = 1.00`.
- Case 4 still has nonzero `B16*` and `B26*`, so its response is more coupled.
- Case 3 has higher `D11*`, but is too directionally biased for general plate
  design.

For DD baseline versus 6-ply TAC:

- Case 6 is the stronger TAC candidate when weight reduction is the primary
  objective.
- Case 6 uses fewer plies and is more balanced than Case 5.
- Case 5 has the largest `D11*`, but low `D22*` makes it a specialized
  x-direction design.
- For primary structure, Case 1 DD remains the safer baseline unless TAC
  coupling is fully validated.

The final recommendation in the PPT is:

- Overall structure selection: Case 1 DD.
- Best 8-ply TAC alternative: Case 4.
- Best 6-ply TAC alternative when weight saving is prioritized: Case 6.

## RAG Answer Guidance

When the assistant answers TAC vs DD questions, it should not say that the case
with the highest `D11*` is automatically best. It should explain the tradeoff:

- `D11*` indicates x-direction bending stiffness.
- `D22*` and ratios such as `D11*/D22*` indicate directional bias.
- `A11*/A22*` indicates in-plane balance.
- Nonzero `B16*` and `B26*` indicate membrane-bending coupling, which can be
  useful but requires validation.
- DD Case 1 is the safer general baseline because it has `B* = 0`, balanced
  in-plane stiffness, and more predictable bending/buckling response.
- TAC Case 4 and Case 6 are meaningful alternatives depending on the objective:
  balanced 8-ply comparison or 6-ply weight reduction.
