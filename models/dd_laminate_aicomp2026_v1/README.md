# AIComp 2026 DD Laminate Model Artifacts

New challenger artifacts belong in one immutable experiment directory:

```text
<experiment-id>/
  metadata.json
  artifacts/
    model.joblib | model.pt | model.onnx
```

Do not copy or overwrite the frozen production baseline artifacts here. Model
binaries under `artifacts/` are handled by Git LFS; metadata stays regular Git.

The experiment configuration and evaluation evidence must be stored under
`research/dd_aicomp2026/` and `reports/dd_aicomp2026_v1/` with the same
experiment ID.
