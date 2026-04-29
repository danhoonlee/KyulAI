# DD Laminate AI Current Summary

_Last updated: 2026-04-29_

## 1. Current Goal

Double-Double laminate simulation results are being used to automate Type classification and eventually screen/optimize theta combinations before running Abaqus.

Current canonical cases:

| Case | Layup |
|---|---|
| Case 1 | To be determined |
| Case 2 | `[[±theta1]/[±theta2]]4` |
| Case 3 | `[[±theta1]/[±theta2]/[∓theta2]/[∓theta2]]2` |
| Case 4 | `[([±theta1]/[±theta2])2 / ([∓theta1]/[∓theta2])2]` |

Current usable dataset contains only Case3 and Case4.

## 2. Curated Dataset

Original data was preserved. A CSV-validated curated copy was created:

`/Users/danlee/KyulAI_codex/data/datasets/DD_curated_csv_v1`

Curated label counts:

| Case | Type 1 | Type 2 | Type 3 | Total |
|---|---:|---:|---:|---:|
| Case3 | 62 | 118 | 20 | 200 |
| Case4 | 64 | 116 | 20 | 200 |
| Total | 126 | 234 | 40 | 400 |

Key label decisions:

- Case3 `Test_085`, `Test_162`, `Test_166`, `Test_180`, `Test_197`: Type3 -> Type2.
- Case3 `Test_008`: Type2 -> Type1.
- Case4 report-suggested Type1 -> Type2 changes accepted except `Test_078`, `Test_152`.
- Case3 `Test_078`, `Test_152` kept as Type2 but marked needs-review because CSV tail after Pt is too short.

Relevant files:

- Curated dataset README: `/Users/danlee/KyulAI_codex/data/datasets/DD_curated_csv_v1/README.md`
- Audit table: `/Users/danlee/KyulAI_codex/data/datasets/DD_curated_csv_v1/classification_audit.csv`
- CSV review report: `/Users/danlee/KyulAI_codex/data/datasets/DD_curated_csv_v1/classification_review_report_csv.md`

A flat CSV view was also created to avoid duplicate filenames:

`/Users/danlee/KyulAI_codex/data/datasets/DD_curated_csv_v1/flat_csv`

Filename pattern:

`Case3_type2_force_disp_Test_001.csv`

## 3. Main Model Results

### A. Curve/CSV-Based Classifier

Input:

- raw force-displacement CSV
- Pt
- theta1, theta2
- case_id

This is the strongest practical classifier when Abaqus has already produced a curve.

Output folder:

`/Users/danlee/KyulAI_codex/models/dd_laminate_csv_meta_v1`

Best model: `HistGradientBoosting`

| Validation | Accuracy | Macro F1 | Notes |
|---|---:|---:|---|
| Sample CV | 0.9950 | 0.9958 | Best overall result |
| Grouped CV | 0.9650 | 0.9710 | More conservative unseen-theta check |

Report:

`/Users/danlee/KyulAI_codex/models/dd_laminate_csv_meta_v1/curve_classifier_report.md`

Use when:

- Abaqus result CSV is available.
- You want the most accurate automatic Type classification.

Prediction command example:

```bash
cd /Users/danlee/KyulAI_codex
python3 -m src.ml.dd_laminate.predict_curve_classifier   data/datasets/DD_curated_csv_v1/Case4/csv_load/force_disp_Test_194.csv   --model models/dd_laminate_csv_meta_v1/curve_classifier.joblib   --pt 13037.617786195782   --case Case4   --test-id Test_194   --theta1 -29   --theta2 74
```

### B. GointMLP-Inspired Deep Sequence Classifier

Input:

- raw force-displacement CSV sequence
- Pt
- theta1, theta2
- case_id

This is the best true deep-learning model because it reads the curve sequence directly.

Output folders:

- Sample CV: `/Users/danlee/KyulAI_codex/models/dd_laminate_deep_sequence_v1`
- Grouped CV: `/Users/danlee/KyulAI_codex/models/dd_laminate_deep_sequence_grouped_v1`

Architecture:

`resampled force-displacement sequence -> bidirectional GRU -> JointMLP-style multi-branch head -> class logits + ordinal auxiliary logits`

| Validation | Accuracy | Macro F1 | Confusion Summary |
|---|---:|---:|---|
| Sample CV | 0.9775 | 0.9819 | Type3 perfect; Type1/2 boundary errors |
| Grouped CV | 0.9800 | 0.9840 | Type3 perfect; Type2 sometimes predicted Type1 |

Reports:

- `/Users/danlee/KyulAI_codex/models/dd_laminate_deep_sequence_v1/deep_sequence_report.md`
- `/Users/danlee/KyulAI_codex/models/dd_laminate_deep_sequence_grouped_v1/deep_sequence_report.md`

Use when:

- You want a deep-learning story/model.
- You want the model to learn directly from raw curve shape, not only engineered features.

Prediction command example:

```bash
python3 -m src.ml.dd_laminate.predict_deep_sequence_classifier   data/datasets/DD_curated_csv_v1/Case4/csv_load/force_disp_Test_194.csv   --model models/dd_laminate_deep_sequence_v1/dd_goint_sequence.pt   --pt 13037.617786195782   --case Case4   --test-id Test_194   --theta1 -29   --theta2 74   --device cpu
```

### C. Theta-Only Predictor

Input:

- theta1
- theta2

No Pt, no Abaqus CSV, no case condition.

This is a pre-Abaqus screening model. It is useful but less reliable than curve-based models.

Output folder:

`/Users/danlee/KyulAI_codex/models/dd_laminate_theta_v1`

Best primary model: `ExtraTrees`

| Validation | Best Model | Accuracy | Macro F1 | Notes |
|---|---|---:|---:|---|
| Sample CV | ExtraTrees | 0.9600 | 0.9675 | Strong if theta pairs can mix |
| Grouped CV | MLP Adam | 0.9150 | 0.9188 | Better estimate for unseen theta pairs |

Important ambiguity:

Two theta pairs have conflicting labels between Case3 and Case4:

| theta1 | theta2 | Conflict |
|---:|---:|---|
| 73 | -45 | Case3 Type2, Case4 Type1 |
| -52 | 62 | Case3 Type2, Case4 Type1 |

Use when:

- You want to screen theta combinations before running Abaqus.
- You accept uncertainty and will validate promising candidates later.

Prediction command example:

```bash
python3 -m src.ml.dd_laminate.predict_theta_classifier   --theta1 -29   --theta2 74   --model models/dd_laminate_theta_v1/theta_classifier.joblib
```

### D. Theta-Only GointMLP-Style Deep Model

Input:

- theta1
- theta2

This applies the GointMLP idea to theta-only data using a multi-branch JointMLP-style head plus ordinal auxiliary loss. No GRU is used because there is no sequence.

Output folders:

- `/Users/danlee/KyulAI_codex/models/dd_laminate_theta_goint_v1`
- `/Users/danlee/KyulAI_codex/models/dd_laminate_theta_goint_grouped_v1`

| Validation | Accuracy | Macro F1 | Notes |
|---|---:|---:|---|
| Sample CV | 0.9450 | 0.9512 | Good deep theta-only baseline |
| Grouped CV | 0.9050 | 0.8989 | Slightly below best theta-only classical/MLP |

Use when:

- You specifically want a deep-learning theta-only surrogate.
- For pure performance, prefer `models/dd_laminate_theta_v1/theta_classifier.joblib`.

Prediction command example:

```bash
python3 -m src.ml.dd_laminate.predict_theta_deep_classifier   --theta1 -29   --theta2 74   --model models/dd_laminate_theta_goint_v1/theta_goint.pt   --device cpu
```

## 4. Which Model Should Be Used?

| Situation | Recommended Model | Why |
|---|---|---|
| Abaqus CSV curve is available | `dd_laminate_csv_meta_v1` HGB | Best accuracy and fastest inference |
| Need a deep-learning model from raw curve | `dd_laminate_deep_sequence_v1` | Reads curve sequence directly; good DL story |
| Before Abaqus, only theta1/theta2 available | `dd_laminate_theta_v1` | Best theta-only screening surrogate |
| Need theta-only deep learning | `dd_laminate_theta_goint_v1` | GointMLP-inspired theta-only baseline |

Recommended workflow:

1. Use theta-only model to screen many `(theta1, theta2)` candidates.
2. Run Abaqus for top candidates.
3. Use curve-based HGB or deep-sequence model for final Type classification.
4. Use Type1 probability plus Pt to rank candidates.

## 5. Model Ranking

Approximate ranking by practical usefulness:

1. `dd_laminate_csv_meta_v1` HistGradientBoosting: best final classifier.
2. `dd_laminate_deep_sequence_v1` DD Goint sequence: best deep-learning curve model.
3. `dd_laminate_theta_v1` theta-only ExtraTrees/MLP: best pre-Abaqus screening model.
4. `dd_laminate_theta_goint_v1` theta-only Goint-style deep model: useful DL baseline, not best performance.

## 6. Key Caveats

- Current data has only Case3 and Case4, 400 total samples.
- Case5 or new layup structures need careful validation.
- If Case5 has raw CSV + Pt, curve-based/deep-sequence models can still classify by shape.
- If Case5 prediction must happen before Abaqus from theta only, the model needs more case/layup descriptors and ideally Case5 training data.
- Theta-only results should be treated as screening, not final truth.

## 7. Most Important Files

Code:

- `/Users/danlee/KyulAI_codex/src/ml/dd_laminate/curve_features.py`
- `/Users/danlee/KyulAI_codex/src/ml/dd_laminate/train_curve_classifier.py`
- `/Users/danlee/KyulAI_codex/src/ml/dd_laminate/predict_curve_classifier.py`
- `/Users/danlee/KyulAI_codex/src/ml/dd_laminate/deep_sequence.py`
- `/Users/danlee/KyulAI_codex/src/ml/dd_laminate/train_deep_sequence_classifier.py`
- `/Users/danlee/KyulAI_codex/src/ml/dd_laminate/predict_deep_sequence_classifier.py`
- `/Users/danlee/KyulAI_codex/src/ml/dd_laminate/train_theta_classifier.py`
- `/Users/danlee/KyulAI_codex/src/ml/dd_laminate/predict_theta_classifier.py`
- `/Users/danlee/KyulAI_codex/src/ml/dd_laminate/theta_deep.py`
- `/Users/danlee/KyulAI_codex/src/ml/dd_laminate/train_theta_deep_classifier.py`
- `/Users/danlee/KyulAI_codex/src/ml/dd_laminate/predict_theta_deep_classifier.py`
- `/Users/danlee/KyulAI_codex/src/backend/api/v1/dd_laminate.py`
- `/Users/danlee/KyulAI_codex/src/backend/dd_laminate_app.py`
- `/Users/danlee/KyulAI_codex/src/frontend/dd-laminate`

Data and reports:

- `/Users/danlee/KyulAI_codex/data/datasets/DD_curated_csv_v1`
- `/Users/danlee/KyulAI_codex/models/dd_laminate_csv_meta_v1/curve_classifier_report.md`

## 8. Local UI/API Slice

A first usable local interface was added so theta values and CSV files can be entered without using command-line prediction scripts.

Backend:

- Standalone app: `/Users/danlee/KyulAI_codex/src/backend/dd_laminate_app.py`
- Router: `/Users/danlee/KyulAI_codex/src/backend/api/v1/dd_laminate.py`
- Existing v1 router also includes the DD route.

API endpoints:

- `GET /api/v1/dd-laminate/models`
- `POST /api/v1/dd-laminate/predict/theta`
- `POST /api/v1/dd-laminate/predict/curve`

Frontend:

- Static UI folder: `/Users/danlee/KyulAI_codex/src/frontend/dd-laminate`
- Supports `Theta only` and `Curve CSV` tabs.
- Shows predicted Type, confidence, probability bars, model name, input summary, and ambiguity notes.

Run commands:

```bash
cd /Users/danlee/KyulAI_codex
make dd-api
make dd-ui
```

Open:

```text
http://localhost:3000
```

Important environment note:

- The standalone DD API avoids the platform database startup path.
- The Python environment still needs both API and ML dependencies installed, for example `requirements-api.txt` and the relevant ML dependencies from `requirements-ml.txt`.
- `/Users/danlee/KyulAI_codex/models/dd_laminate_deep_sequence_v1/deep_sequence_report.md`
- `/Users/danlee/KyulAI_codex/models/dd_laminate_theta_v1/theta_classifier_report.md`
- `/Users/danlee/KyulAI_codex/models/dd_laminate_theta_goint_v1/theta_goint_report.md`
