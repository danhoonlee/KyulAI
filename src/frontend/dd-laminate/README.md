# DD Laminate Predictor UI

Small local UI for trying the trained DD laminate Type predictors.

## Run

From the project root:

```bash
make dd-api
```

In another terminal:

```bash
make dd-ui
```

Open:

```text
http://localhost:3000
```

## Inputs

Theta-only mode:

- `theta1`
- `theta2`
- model selection between the classical theta model and the GointMLP-style theta model

Curve CSV mode:

- force-displacement CSV
- `theta1`
- `theta2`
- `Pt`
- `Case`
- `Test ID`
- model selection between the classical curve model and the Goint sequence model

The API runs at:

```text
http://localhost:8000/api/v1/dd-laminate
```

## Notes

- Theta-only prediction is a screening estimate from laminate inputs.
- Curve CSV prediction is the preferred classifier after simulation results exist.
- The standalone API uses `src.backend.dd_laminate_app:app` so it can run without the platform database.
