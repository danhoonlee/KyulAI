# Abaqus laminate to OpenRadioss

`scripts/inp2rad_laminate.py` is a strict converter for the laminate input-deck subset used by `Test_001 (1).inp`. It intentionally stops on unsupported Abaqus features instead of silently producing a different model.

## Supported conversion profile

- one untransformed part instance
- four-node `S4R` shell mesh
- one composite shell section covering the shell mesh
- orthotropic `*Elastic, type=ENGINEERING CONSTANTS`
- ply thickness, angle, material, and integration-point count
- assembly node sets
- zero displacement constraints and one or more imposed displacement components
- a nonlinear static step represented by a smooth explicit loading ramp

The generated Starter deck uses OpenRadioss 2026 `LAW25` (`/MAT/COMPSH`) with `/PROP/SH_SANDW` and the fully integrated QBAT shell formulation. The current profile assumes the source values use a consistent inch-lbf-second unit system. Numerical values are not rescaled; the `/BEGIN` unit scale factors describe that system to Radioss.

No material failure law is invented because the source deck does not define one. Consequently, the converter is suitable for elastic-response dataset generation, not damage or failure prediction.

## Run locally

```bash
.venv/bin/python scripts/inp2rad_laminate.py \
  'data/inp/Test_001 (1).inp' \
  --output-dir .tmp/openradioss/Test_001 \
  --run-name Test_001 \
  --run-time 0.005
```

This writes a Starter deck, an Engine deck, and a JSON conversion manifest.

## Convert and run on the WSL workstation

```bash
scripts/remote/Run-OpenRadiossLaminate.sh \
  'data/inp/Test_001 (1).inp' \
  Test_001
```

Useful environment overrides are `OPENRADIOSS_THREADS`, `OPENRADIOSS_RUN_TIME`, `OPENRADIOSS_OUTPUT_INTERVAL`, `OPENRADIOSS_RUN_ID`, `KYULAI_WSL_HOST`, and `KYULAI_WSL_KEY`.

## Validation boundary

A normal Starter and Engine termination proves that the translated model is syntactically and numerically runnable. It does not by itself prove equivalence to Abaqus. Before using generated cases in a shared training dataset, compare force-displacement response, deformed shape, and selected ply stress/strain fields against a retained Abaqus reference case. For a quasi-static explicit run, also keep kinetic energy small relative to internal energy by increasing the loading duration or using an appropriate quasi-static control method.

The `Test_001` validation run on `DESKTOP-6MNJOKL` used one SPMD domain and eight SMP threads. Starter completed with zero errors and zero warnings. Engine completed 26,351 cycles normally in 595 seconds for a 0.005-second smooth ramp. At the last printed state (0.004934 seconds), kinetic energy was 2.21% of internal energy with zero added mass. The final animation converted to VTK with 6,561 nodes, 6,400 shells, exact `-0.15` imposed X displacement on all 81 loaded-edge nodes, and 48 stress plus 48 strain tensors (16 plies × 3 integration points).
