# KyulAI Session Memory

This file captures important project context and decisions so a future chat can resume work without losing direction.

## Current Focus

The active work is DD laminate Type prediction for composite laminate research.

Canonical case naming:

- Case 1: To be determined.
- Case 2: `[[±theta1]/[±theta2]]4`
- Case 3: `[[±theta1]/[±theta2]/[∓theta2]/[∓theta2]]2`
- Case 4: `[([±theta1]/[±theta2])2 / ([∓theta1]/[∓theta2])2]`

Current usable data contains Case3 and Case4 only.

## DD Dataset

Original data is preserved under:

`/Users/danlee/KyulAI_codex/data/datasets/DD`

Curated CSV-validated dataset:

`/Users/danlee/KyulAI_codex/data/datasets/DD_curated_csv_v1`

Curated counts:

- Case3: Type1 62, Type2 118, Type3 20
- Case4: Type1 64, Type2 116, Type3 20
- Total: Type1 126, Type2 234, Type3 40

Main curation script:

`/Users/danlee/KyulAI_codex/scripts/dd_reclassify_from_csv.py`

## DD Models

Curve/CSV + metadata classifier:

- Folder: `/Users/danlee/KyulAI_codex/models/dd_laminate_csv_meta_v1`
- Best model: HistGradientBoosting
- Use after Abaqus CSV + Pt are available.

GointMLP-inspired deep sequence classifier:

- Folder: `/Users/danlee/KyulAI_codex/models/dd_laminate_deep_sequence_grouped_v1`
- Model file: `dd_goint_sequence.pt`
- Uses raw force-displacement sequence plus theta/Pt/case metadata.

Theta-only classifier:

- Folder: `/Users/danlee/KyulAI_codex/models/dd_laminate_theta_v1`
- Model file: `theta_classifier.joblib`
- Use as pre-Abaqus screening from `theta1`, `theta2`.

Theta-only GointMLP-style model:

- Folder: `/Users/danlee/KyulAI_codex/models/dd_laminate_theta_goint_grouped_v1`
- Model file: `theta_goint.pt`
- Neural theta-only baseline.

Unified summary:

`/Users/danlee/KyulAI_codex/docs/DD_Laminate_AI_Current_Summary.md`

## UI/API Work

A first local DD predictor interface was added.

Backend files:

- `/Users/danlee/KyulAI_codex/src/backend/api/v1/dd_laminate.py`
- `/Users/danlee/KyulAI_codex/src/backend/dd_laminate_app.py`

Frontend files:

- `/Users/danlee/KyulAI_codex/src/frontend/dd-laminate/index.html`
- `/Users/danlee/KyulAI_codex/src/frontend/dd-laminate/styles.css`
- `/Users/danlee/KyulAI_codex/src/frontend/dd-laminate/app.js`
- `/Users/danlee/KyulAI_codex/src/frontend/dd-laminate/README.md`

Makefile commands:

```bash
cd /Users/danlee/KyulAI_codex
make dd-api
make dd-ui
```

Then open:

```text
http://localhost:3000
```

API endpoints:

- `GET /api/v1/dd-laminate/models`
- `POST /api/v1/dd-laminate/predict/theta`
- `POST /api/v1/dd-laminate/predict/curve`

Implementation note:

- The standalone DD API avoids the main FastAPI app database startup.
- Current local `.venv` did not have FastAPI/Torch/scikit-learn installed during Codex verification.
- Python syntax compile passed for the new backend files.
- Frontend JavaScript syntax check and HTML parse passed.

## Live Test Update

Minimal runtime packages were installed into `/Users/danlee/KyulAI_codex/.venv`
for classical API testing:

- FastAPI, Uvicorn, pydantic-settings, python-multipart
- numpy, scipy, joblib, scikit-learn

scikit-learn was updated to `1.7.2` to match the saved joblib model version.

Live API checks succeeded:

- `theta1=-29`, `theta2=74`, theta-classical -> Type 2, confidence 1.0.
- Case4 `force_disp_Test_194.csv` with `Pt=13037.617786195782`,
  curve-classical -> Type 2, confidence 0.999996.

Local servers were started:

- API: `http://127.0.0.1:8000`
- UI: `http://127.0.0.1:3000`

Torch `2.2.0` was installed into the current `.venv` and the API server was
restarted. All four model options are now available from the API/UI:

- `theta_classical`
- `theta_goint`
- `curve_classical`
- `curve_goint`

Torch-model live checks succeeded:

- `theta1=-29`, `theta2=74`, theta-goint -> Type 2, confidence 0.976462.
- `theta1=73`, `theta2=-45`, theta-goint -> Type 1, confidence 0.961763.
- Case4 `force_disp_Test_194.csv` with `Pt=13037.617786195782`,
  curve-goint -> Type 2, confidence 0.997607.

## Next Good Steps

1. Test theta-only predictions from the browser.
2. Test CSV upload with a known Case3/Case4 sample and Pt.
3. Install Torch if Goint/deep models should be testable from the UI now.
4. Later, migrate the static UI into the documented Next.js frontend stack if the project needs a full web app.
