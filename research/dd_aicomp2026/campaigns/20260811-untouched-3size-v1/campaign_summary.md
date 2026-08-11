# Untouched Validation Campaign: UV3S1

## Frozen design

- Theta pairs: 60
- Simulations: 540
- Pilot simulations: 180
- Confirmatory simulations: 360
- Existing theta-pair overlap: 0
- Predictions and targets are intentionally absent from the simulation manifest.

## Design strata

- `uniform_grid`: pre-registered random unseen integer-angle pairs.
- `maximin_gap`: unseen pairs farthest from the existing design set and each other.
- Every pair is repeated across Case 2/3/4 and 6x4/6x8/8x8 panels.
- The predeclared weak-subgroup diagnostic is `6x8 | Case2`.

## Handling rule

Run the pilot first, but do not retrain, recalibrate, or alter the frozen models after reading
pilot targets. Pilot results may stop the campaign for solver/data-quality failures only. Final
model metrics are computed after the confirmatory results are complete and the returned-data
audit passes.
