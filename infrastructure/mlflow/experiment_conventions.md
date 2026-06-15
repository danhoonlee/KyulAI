# MLflow Experiment Naming Conventions

## Experiment Names

Format: `{team}/{model_family}/{objective}`

Examples:
- `kyulai/sim2real/abaqus-to-experiment`
- `kyulai/graph-net/fiber-orientation`
- `kyulai/pinn/residual-stress`
- `kyulai/neural-operator/fno-moldex3d`

## Run Tags (always set these)

| Tag | Example | Description |
|-----|---------|-------------|
| `cae_tool` | `abaqus`, `moldex3d` | Source CAE tool |
| `model_arch` | `gnn`, `fno`, `pinn` | Model architecture |
| `data_version` | `v1.2` | DVC data version |
| `git_commit` | `abc1234` | Git SHA |
| `env` | `dev`, `staging`, `prod` | Environment |

## Metric Naming

- Use dot notation: `train.loss`, `val.loss`, `val.r2_score`
- Physics metrics: `physics.energy_conservation_error`, `physics.stress_equilibrium`
- Sim-to-real gap: `s2r.mean_bias`, `s2r.rmse`

## Artifact Structure

```
mlflow-artifacts/
  {experiment_id}/
    {run_id}/
      artifacts/
        model/          — Saved model weights + config
        plots/          — Training curves, error maps
        predictions/    — Sample predictions vs. ground truth
        config.yaml     — Full Hydra config for reproducibility
```

## Lifecycle

- `Active`: Ongoing or recently completed runs
- `Deleted`: Runs with invalid data or aborted early (< 10 steps)
- Promote to model registry only after physics validation passes
