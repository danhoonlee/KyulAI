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

## DD UI Program-Style Redesign Reverted

User provided the GointMLP program appearance PDF:

- `/Users/danlee/KyulAI_codex/extra/모양 및 구조 - 외형_250206_rev1.pdf`

The PDF describes a program-style flow:

- login/home
- main list table
- selected subject information
- measured data/input area
- prediction action
- prediction value/class and graph result

The DD frontend was briefly redesigned to follow the same application shape:

- left specimen list with search and selectable rows
- center selected laminate details and prediction input workspace
- theta screening mode and curve classification mode
- CSV upload preview with force-displacement canvas chart
- right prediction result panel with Type, confidence, probabilities, and Type guide

User feedback: the redesigned UI looked worse for a web app and appeared less
stable. The three frontend files were restored to the previously committed
web-form UI:

- `/Users/danlee/KyulAI_codex/src/frontend/dd-laminate/index.html`
- `/Users/danlee/KyulAI_codex/src/frontend/dd-laminate/app.js`
- `/Users/danlee/KyulAI_codex/src/frontend/dd-laminate/styles.css`

Verification:

- `node --check src/frontend/dd-laminate/app.js`
- basic HTML parse
- UI server serves the restored page at `http://127.0.0.1:3000`
- API smoke test still succeeds for `theta_goint`

## DD UI CSV Preview

User asked to add the first small UI improvement: CSV graph preview.

Implemented on the restored web UI, without changing the overall theta-only page structure:

- `Curve CSV` tab now shows a separate `CSV Preview` panel outside the input form.
- Theta-only mode remains a clean two-column input/result layout.
- Curve CSV mode switches to input / preview / result columns on desktop.
- Reads two-column force-displacement CSV in the browser.
- Draws the curve on a canvas.
- Shows point count, max displacement, and max force.
- Includes a `Clear` button.

Updated files:

- `/Users/danlee/KyulAI_codex/src/frontend/dd-laminate/index.html`
- `/Users/danlee/KyulAI_codex/src/frontend/dd-laminate/app.js`
- `/Users/danlee/KyulAI_codex/src/frontend/dd-laminate/styles.css`

Verification:

- `node --check src/frontend/dd-laminate/app.js`
- basic HTML parse
- UI server confirmed serving `CSV Preview`
- sample CSV `Case4/csv_load/force_disp_Test_194.csv` has 1001 points,
  max displacement `0.15000000596046448`, max force `32118.02663421631`
- curve prediction API still succeeds with `curve_goint`

## DD Response Surrogate

User asked to estimate force-displacement graph and Pt from only `theta1`,
`theta2`, and selected case.

Implemented new curated-data surrogate:

- Training script: `/Users/danlee/KyulAI_codex/src/ml/dd_laminate/train_response_surrogate.py`
- Prediction script: `/Users/danlee/KyulAI_codex/src/ml/dd_laminate/predict_response_surrogate.py`
- Model folder: `/Users/danlee/KyulAI_codex/models/dd_laminate_response_surrogate_v1`
- Model file: `response_surrogate.joblib`

Model design:

- Input features: `theta1`, `theta2`, `case_id`, simple angle transforms.
- Type: `ExtraTreesClassifier`.
- Pt, max displacement, max force: `ExtraTreesRegressor`.
- Curve: normalize each CSV curve to 128 points, PCA to 16 components, then
  `ExtraTreesRegressor` predicts PCA scores.

Training command:

```bash
.venv/bin/python -m src.ml.dd_laminate.train_response_surrogate \
  --data-dir data/datasets/DD_curated_csv_v1 \
  --output-dir models/dd_laminate_response_surrogate_v1 \
  --seq-len 128 \
  --n-components 16
```

Grouped CV metrics:

- Accuracy: 0.9025 +/- 0.0583.
- Macro F1: 0.8966 +/- 0.0614.
- Pt MAE: 291.14 +/- 48.81.
- Max displacement MAE: 0.000622 +/- 0.000462.
- Max force MAE: 690.08 +/- 96.07.
- Curve normalized RMSE: 0.01143 +/- 0.00213.
- Curve force RMSE: 661.62 +/- 110.22.

API added:

- `POST /api/v1/dd-laminate/predict/response`

UI added:

- New tab: `Response estimate`.
- Inputs: model, `theta1`, `theta2`, `case`.
- Result panel displays Type, probabilities, predicted Pt, predicted max
  displacement, predicted max force, and estimated force-displacement curve.

Verification:

- Python compile passed for new backend/ML files.
- `node --check src/frontend/dd-laminate/app.js`.
- API `/models` shows `response_surrogate` available.
- API smoke:
  `theta1=-29`, `theta2=74`, `Case4` -> Type 2, Pt `13037.617786199913`,
  max displacement `0.15000000596046448`, max force `32118.02663421631`.
- Browser smoke at `http://127.0.0.1:3000/` passed:
  `Response estimate` tab renders, default inputs submit, and result shows Type 2
  with estimated response metrics and curve section.
- UI server was restarted with explicit IPv4 bind:
  `python3 -m http.server 3000 --bind 127.0.0.1 --directory src/frontend/dd-laminate`.
- Follow-up UI fix: Chrome could show no `Response estimate` inputs when old
  `app.js` was cached or the page was scrolled down to the result panel. Added
  cache-busting query strings to `index.html` for `styles.css`/`app.js`, disabled
  browser scroll restoration, and scroll the input panel into view on mode switch.
- Follow-up response graph fix: user wanted the critical Pt to appear on the
  predicted force-displacement graph and resemble the previous bilinear analysis.
  Updated `Response estimate` canvas to interpolate the displacement where the
  predicted curve reaches predicted Pt, draw a Pt marker/label, and overlay a
  dashed bilinear guide from origin -> Pt -> endpoint. Added a small legend and
  cache-busted assets with `v=20260430-pt-overlay`. Browser smoke passed.
- Follow-up correction: user showed `plot_Test_006_P1.png` and clarified that
  the linear graphs should be actual red dashed fit lines above/over the
  predicted curve, not a chord drawn through the predicted curve. Updated
  response canvas to estimate separate initial and tail slopes, force both fit
  lines to meet at predicted Pt, draw red dashed `Linear fits`, add a purple
  vertical `Kink line`, and keep the red Pt marker at that fit intersection.
  Cache-busted assets with `v=20260430-linear-fit`.
- Follow-up correction: user noticed the right-side linear fit could still sit
  below the predicted curve after Pt. Added envelope-aware slope correction in
  `app.js`: the right fit slope is raised enough to stay above Pt-right curve
  samples, and the left fit is lightly capped so it stays above the pre-Pt curve.
  Cache-busted assets with `v=20260430-linear-fit-envelope`; JS syntax check and
  browser DOM smoke passed.

## DD Response GointMLP-Style NN

User asked to add a deep-learning option to `Response estimate`, analogous to
the theta-only `GointMLP-style NN`.

Implemented:

- Model module: `/Users/danlee/KyulAI_codex/src/ml/dd_laminate/response_deep.py`
- Training script:
  `/Users/danlee/KyulAI_codex/src/ml/dd_laminate/train_response_deep_surrogate.py`
- Prediction script:
  `/Users/danlee/KyulAI_codex/src/ml/dd_laminate/predict_response_deep_surrogate.py`
- Model folder: `/Users/danlee/KyulAI_codex/models/dd_laminate_response_goint_v1`
- Model file: `response_goint.pt`

Model design:

- Input: same 8 theta/case features used by the ExtraTrees response surrogate.
- Architecture: GointMLP-style multi-branch MLP.
- Outputs: Type logits, ordinal auxiliary logits, normalized scalar outputs
  (`Pt`, max displacement, max force), and normalized 128-point curve.
- Inference post-processing forces the predicted curve to start at zero and
  smooths/monotonizes the curve for physical force-displacement display.

Training command:

```bash
.venv/bin/python -m src.ml.dd_laminate.train_response_deep_surrogate \
  --data-dir data/datasets/DD_curated_csv_v1 \
  --output-dir models/dd_laminate_response_goint_v1 \
  --seq-len 128 \
  --device cpu \
  --epochs 180 \
  --final-epochs 100 \
  --patience 28
```

Grouped CV metrics:

- Accuracy: 0.9300 +/- 0.0359.
- Macro F1: 0.9282 +/- 0.0327.
- Pt MAE: 802.29 +/- 234.60.
- Max displacement MAE: 0.000541 +/- 0.000575.
- Max force MAE: 2079.32 +/- 712.51.
- Curve normalized RMSE: 0.03589 +/- 0.00817.
- Curve force RMSE: 2002.11 +/- 629.82.

API/UI integration:

- Added response model key: `response_goint`.
- `/api/v1/dd-laminate/models` now returns both:
  `response_surrogate` and `response_goint`.
- `/api/v1/dd-laminate/predict/response` dispatches to the NN predictor when
  `model=response_goint`.
- UI `Response estimate` dropdown shows
  `Estimated response - GointMLP-style NN`.

Verification:

- Syntax compile via `.venv/bin/python -c compile(...)` passed.
- CLI smoke:
  `theta1=-29`, `theta2=74`, `Case4`, `response_goint` -> Type 2,
  Pt `12734.149632387063`, max displacement `0.15002038627923578`,
  max force `33659.37970066126`.
- API server restarted.
- Browser smoke passed: selected `Estimated response - GointMLP-style NN` in
  `Response estimate`; result rendered Type 2, 99.7% confidence, Pt `12734.15`,
  and no browser console errors.

Current recommendation:

- Keep `Estimated response - ExtraTrees + PCA` as the safer default for curve
  shape/force response on the current 400-sample dataset.
- Use `Estimated response - GointMLP-style NN` as the deep-learning baseline and
  for comparison/reporting.

## DD UI Polish

User asked to refine the UI.

Updated:

- `src/frontend/dd-laminate/index.html`
  - Cache-busted UI assets with `v=20260430-ui-polish`.
- `src/frontend/dd-laminate/app.js`
  - Adds `type-1`, `type-2`, or `type-3` class to the result panel after
    prediction.
- `src/frontend/dd-laminate/styles.css`
  - Softer app background and shadows.
  - Cleaner topbar/status styling.
  - More spacious mode tabs and form inputs.
  - Sticky input panel on desktop.
  - Form header divider.
  - Result header styled as a compact summary card.
  - Confidence and probability bars now change color by predicted Type.
  - Metric/meta blocks styled as quiet research-tool cells.
  - Mobile keeps single-column layout and disables sticky input panel.

Verification:

- `node --check src/frontend/dd-laminate/app.js` passed.
- Browser smoke passed for `Response estimate` using default inputs:
  result rendered Type 2, no console errors.

## DD UI Font Polish

User asked about trendy fonts for modern websites/apps.

Recommendation:

- For modern product UI, `Inter` is still a widely used screen-optimized
  standard for SaaS/dashboard/developer tools.
- For Korean/multilingual UI, `Pretendard` is a strong fit because it is based
  around Inter-like UI proportions with optimized Hangul support.

Implemented without external CDN dependency:

- `styles.css`
  - Added `--font-ui` and `--font-display` stacks:
    `Pretendard`, `Inter`, `SF Pro`, `Apple SD Gothic Neo`, `Noto Sans KR`,
    then system sans-serif fallbacks.
  - Applied display stack to headings and predicted Type.
  - Enabled tabular numeric rendering for metrics/confidence/result values.
  - Added `text-rendering: optimizeLegibility`.
- `index.html`
  - Cache-busted assets with `v=20260430-font-polish`.

Verification:

- `node --check src/frontend/dd-laminate/app.js` passed.
- Browser smoke passed; no console errors.

Note:

- Because no font files are bundled in the repo, `Pretendard` only activates if
  installed on the viewing machine. Otherwise the UI falls back to Inter/SF
  Pro/Apple system fonts. To guarantee the exact font on another machine, bundle
  local `.woff2` files or knowingly use a CDN.

## DD UI Greek Theta Labels

User asked to change displayed `theta1`, `theta2` labels to Greek letters.

Updated:

- `index.html`
  - Visible form labels now use `θ₁` and `θ₂` in Theta only, Response estimate,
    and Curve CSV modes.
  - Cache-busted assets with `v=20260430-greek-theta`.
- `app.js`
  - Result input summary maps API keys `theta1`/`theta2` to display labels
    `θ₁`/`θ₂`.
  - Internal form field names and API payload keys remain `theta1`/`theta2`, so
    backend/model compatibility is unchanged.

Verification:

- `node --check src/frontend/dd-laminate/app.js` passed.
- Browser smoke passed: labels show `θ₁`/`θ₂`, `theta1`/`theta2` text no longer
  appears visibly in the DOM snapshot, prediction still works, and input summary
  uses `θ₁: -29, θ₂: 74`.

## DD UI Input Summary Polish

User pointed out the `Input` summary was hard to read and asked to bold
`θ₁`, `θ₂`, `case`, plus capitalize `case` to `Case`.

Updated:

- `app.js`
  - Result summary now renders as inline HTML tokens:
    `<strong>θ₁</strong>: -29, <strong>θ₂</strong>: 74, <strong>Case</strong>: Case4`.
  - `case` display label changed to `Case`.
- `styles.css`
  - Added `.input-token` styling and bold label styling.
- `index.html`
  - Cache-busted assets with `v=20260430-input-summary-v2`.

Verification:

- `node --check src/frontend/dd-laminate/app.js` passed.
- Browser smoke passed: summary text is exactly
  `θ₁: -29, θ₂: 74, Case: Case4`; no console errors.

## DD UI Input Summary Chips

User said the Input summary was still not visually clean and asked for clearer
separation than commas plus wider spacing.

Updated:

- `app.js`
  - Input summary no longer uses comma-separated text.
  - Renders each input as a separate `.input-token` chip with a bold label and
    muted bold value.
- `styles.css`
  - `#input-summary` is now a wrapping flex row with `gap: 8px`.
  - `.input-token` has border, padding, white background, and label/value spacing.
- `index.html`
  - Cache-busted assets with `v=20260430-input-chips`.

Verification:

- `node --check src/frontend/dd-laminate/app.js` passed.
- Browser smoke passed: `.input-token` count is 3 and no console errors.

## DD Physics Features From Properties Image

User provided `/Users/danlee/KyulAI_codex/extra/Properties.png` and asked
whether the physical features discussed earlier can be reflected.

Image information captured:

- Panel: flat rectangular panel, `6 in x 4 in`.
- Boundary/load setup: simply supported lateral edges, clamped at `x=0,a`,
  load applied from `x=a`. Current Case3/Case4 simulations appear to share this
  setup, so these are mostly constants for the present dataset.
- Material: Toray T800/3900S.
- Lamina thickness: `0.0075 in`.
- Material constants used:
  - `E11 = 21.5 Msi`
  - `E22 = 1.23 Msi`
  - `nu12 = 0.329`
  - `G12 = 0.571 Msi`

Implemented:

- New module:
  `/Users/danlee/KyulAI_codex/src/ml/dd_laminate/laminate_physics.py`
- Adds CLT-derived laminate physics features:
  - Builds Case3/Case4 stacking sequences from current project definitions.
  - Computes transformed reduced stiffness `Qbar`.
  - Computes laminate `A`, `B`, `D` matrices using ply thickness.
  - Adds normalized extensional/bending/coupling features and ratios:
    `a11`, `a22`, `a12`, `a66`, `a16`, `a26`,
    `b16`, `b26`,
    `d11`, `d22`, `d12`, `d66`, `d16`, `d26`,
    stiffness ratios/coupling norms, ply count, total thickness, aspect ratio,
    and slenderness.
- Updated `train_response_surrogate.py`
  - Response feature vector is now 33 features:
    8 previous theta/case features + 25 CLT physics features.
- Retrained:
  - `models/dd_laminate_response_surrogate_v1/response_surrogate.joblib`
  - `models/dd_laminate_response_goint_v1/response_goint.pt`
- Updated API response model labels:
  - `Estimated response - ExtraTrees + PCA + CLT`
  - `Estimated response - GointMLP NN + CLT`

Metrics after physics feature retraining:

ExtraTrees + PCA + CLT:

- Accuracy: 0.9350 +/- 0.0398, previously 0.9025.
- Macro F1: 0.9315 +/- 0.0512, previously 0.8966.
- Pt MAE: 303.49 +/- 53.26, previously 291.14.
- Max force MAE: 682.54 +/- 47.96, previously 690.08.
- Curve normalized RMSE: 0.00996 +/- 0.00299, previously 0.01143.
- Curve force RMSE: 704.59 +/- 125.63, previously 661.62.

GointMLP NN + CLT:

- Accuracy: 0.9350 +/- 0.0515, previously 0.9300.
- Macro F1: 0.9384 +/- 0.0458, previously 0.9282.
- Pt MAE: 646.09 +/- 192.21, previously 802.29.
- Max force MAE: 2542.01 +/- 786.18, previously 2079.32.
- Curve normalized RMSE: 0.03892 +/- 0.00954, previously 0.03589.
- Curve force RMSE: 2571.57 +/- 767.29, previously 2002.11.

Interpretation:

- CLT physics features clearly help Type classification and the NN Pt estimate.
- ExtraTrees + PCA + CLT remains the safer default for curve/force response.
- NN + CLT is useful as a deep-learning baseline, but its curve/force output is
  still less stable on the current 400-sample dataset.

Verification:

- Syntax compile passed for backend and new/updated ML files.
- CLI smoke passed for both response models using `theta1=-29`, `theta2=74`,
  `Case4`.
- API server restarted.
- Browser smoke passed: Response estimate dropdown now shows both CLT model
  labels and no console errors.

## 2026-04-30 Phone LAN Access Setup

Goal:

- Let the DD Laminate UI running on the Mac be reachable from a smartphone on
  the same Wi-Fi network.

Implemented:

- Updated `src/frontend/dd-laminate/app.js` so `API_BASE` uses
  `window.location.hostname` instead of fixed `localhost`. This lets:
  - Desktop `http://127.0.0.1:3000` call `http://127.0.0.1:8000`.
  - Phone `http://172.30.1.7:3000` call `http://172.30.1.7:8000`.
- Updated `src/frontend/dd-laminate/index.html` cache-bust query strings to
  `v=20260430-lan-access`.
- Updated `src/backend/dd_laminate_app.py` CORS with a LAN-friendly regex for
  `http://<ip>:3000` origins.

Current LAN test address:

- Mac Wi-Fi IP detected as `172.30.1.7`.
- Smartphone URL: `http://172.30.1.7:3000`

Server state:

- API is running on `0.0.0.0:8000`.
- UI is running on `0.0.0.0:3000`.

Verification:

- `curl http://127.0.0.1:8000/health` returned `{"status":"ok"}`.
- Outside-sandbox LAN checks passed:
  - `http://172.30.1.7:3000/`
  - `http://172.30.1.7:8000/health`

Notes:

- Phone and Mac must be on the same Wi-Fi.
- If macOS shows a firewall prompt for Python, allow incoming connections.
- This is LAN-only. Outside the same Wi-Fi would require tunneling
  (Cloudflare Tunnel/ngrok) or deployment.

## 2026-04-30 Brand Color UI Pass

Goal:

- Apply the company logo color direction to the DD Laminate UI without making
  the app visually noisy.

Implemented:

- Updated `src/frontend/dd-laminate/styles.css` with a logo-derived palette:
  - Main action/accent: blue `#0076bd`
  - Secondary energy: cyan `#16aad8`
  - Positive/Type 1: green `#00ad5a`
  - Warning/note: yellow family from the logo
  - Type 3/error: red `#d40000`
  - Neutral support: gray `#868987`
- Added a thin multi-color top brand strip.
- Added subtle panel top accents using blue/cyan/green.
- Updated buttons, focus rings, active tabs, status pills, graph legend colors,
  Type probability colors, notes, shadows, and background wash.
- Updated `index.html` cache-bust query strings to
  `v=20260430-brand-colors`.

Design note:

- The full logo palette is intentionally not used everywhere. Blue/cyan remain
  dominant, while green/yellow/red are used as status and data accents.

Verification:

- `node --check src/frontend/dd-laminate/app.js` passed.
- API health check passed.
- LAN UI server is still listening on `0.0.0.0:3000`.
- LAN CSS fetch passed at
  `http://172.30.1.7:3000/styles.css?v=20260430-brand-colors`.

## 2026-04-30 UI Name Update

- Changed visible DD Laminate UI branding from `KyulAI` to
  `KCLab Composite AI`.
- Updated browser tab title to
  `KCLab Composite AI DD Laminate Predictor`.
- Verified no remaining `KyulAI` text exists under
  `src/frontend/dd-laminate`.
- LAN UI fetch confirmed the new title/eyebrow are served.
- Follow-up fix: removed forced uppercase from `.eyebrow`, so the brand now
  displays as mixed case `KCLab Composite AI`.
- Updated static cache-bust query to `v=20260430-brand-case`.
- Follow-up label fix: removed forced uppercase from `.preview-stats span` and
  `dt`, so labels such as `Predicted Pt`, `Max displacement`, `Max force`,
  `Model`, and `Input` display in mixed case.
- Updated static cache-bust query to `v=20260430-label-case`.
- Follow-up wording fix: changed `Max displacement` to `Max. Displacement`
  and `Max force` to `Max. Force`; updated cache-bust query to
  `v=20260430-max-labels`.
- Follow-up Case formula UI: changed Case select display labels to `Case 3`
  and `Case 4`, added formula guide boxes under Case inputs:
  - `Case 3` `[[±θ₁]/[±θ₂]/[∓θ₂]/[∓θ₂]]₂`
  - `Case 4` `[([±θ₁]/[±θ₂])₂ / ([∓θ₁]/[∓θ₂])₂]`
- API values still remain `Case3` / `Case4`; result input chips now display
  `Case 3` / `Case 4`.
- Updated static cache-bust query to `v=20260430-case-formulas`.

## 2026-04-30 Theta + Case Type Predictor

User noticed `Theta only` accepted θ₁/θ₂ but not Case, even though Case 3 and
Case 4 are different stacking equations. This was correct: the old theta
models truly used only two features and needed retraining for Case-aware Type
prediction.

Implemented:

- Updated classical theta model code to use three pre-Abaqus inputs:
  `theta1`, `theta2`, `case_is_case4`.
- Updated GointMLP-style theta model to use the same 3-feature input.
- Updated API `/predict/theta` request schema to require `case`.
- Updated API model labels:
  - `Theta + case - ExtraTrees`
  - `Theta + case - GointMLP-style NN`
- Updated UI:
  - Tab text changed from `Theta only` to `Theta + case`.
  - First panel title changed to `Pre-Abaqus Type Estimate`.
  - Added Case dropdown and Case formula guide to the theta form.
  - Theta prediction payload now sends `case`.
  - Static cache-bust query updated to `v=20260430-theta-case`.

Retrained models:

- `models/dd_laminate_theta_v1/theta_classifier.joblib`
- `models/dd_laminate_theta_goint_grouped_v1/theta_goint.pt`

New metrics:

- Classical theta+case:
  - Best sample-CV model: `hist_gradient_boosting`
  - Sample CV accuracy: `0.9625`
  - Sample CV macro F1: `0.9624`
  - Best grouped-CV model: `neural_net_mlp_adam`
  - Grouped CV accuracy: `0.9025`
  - Grouped CV macro F1: `0.9133`
- GointMLP-style theta+case:
  - Grouped CV accuracy: `0.9050`
  - Grouped CV macro F1: `0.8920`

Verification:

- Python compile passed with `PYTHONPYCACHEPREFIX=/tmp/kyulai_pycache`.
- `node --check src/frontend/dd-laminate/app.js` passed.
- API server restarted on `0.0.0.0:8000`.
- LAN UI fetch passed and shows `Theta + case`.
- LAN API smoke passed:
  - Classical `theta1=-29`, `theta2=74`, `Case4` -> Type 2, confidence
    `0.999863`.
  - Goint `theta1=-29`, `theta2=74`, `Case4` -> Type 2, confidence
    `0.958622`.

## 2026-04-30 Carbon Fiber Background UI Pass

Goal:

- Add a subtle carbon-fiber/composite visual feeling to the DD Laminate UI
  without making the research controls hard to read.

Implemented:

- Updated `src/frontend/dd-laminate/styles.css`:
  - Added brand-tinted radial background wash.
  - Added fixed `body::after` woven carbon-fiber-style texture using CSS
    layered gradients.
  - Kept the company color strip as `body::before`.
  - Raised `.shell` above the texture.
  - Added light translucency and blur to panels, status pill, and mode switch
    so the texture is visible but subdued.
- Updated `index.html` cache-bust query to `v=20260430-carbon-bg`.

Verification:

- `node --check src/frontend/dd-laminate/app.js` passed.
- API health check passed.
- LAN UI fetch passed and references `styles.css?v=20260430-carbon-bg`.
- LAN CSS fetch passed and includes the new texture/background rules.

## 2026-04-30 Darker Woven Composite Background

User wanted the background slightly darker and closer to a real carbon-fiber
composite weave reference image.

Implemented:

- Updated `src/frontend/dd-laminate/styles.css`:
  - Darkened the page background from very light blue-white to a deeper
    blue-gray.
  - Replaced the simple diagonal texture with layered repeating gradients that
    cross at two angles to resemble woven composite tow bundles.
  - Added subtle highlight bands and darker strands to make the pattern feel
    more image-like.
  - Increased panel/status/tab blur and opacity slightly to keep readability.
  - Added `-webkit-backdrop-filter` and `-webkit-mask-image` for Safari support.
- Updated `index.html` cache-bust query to `v=20260430-woven-bg`.

Verification:

- `node --check src/frontend/dd-laminate/app.js` passed.
- API health check passed.
- LAN UI fetch passed and references `styles.css?v=20260430-woven-bg`.
- LAN CSS fetch passed and includes the darker woven background rules.

Follow-up:

- User disliked the darker woven pattern because it read like a Burberry/check
  pattern rather than composite material.
- Reverted the background back to the previous subtle carbon-fiber CSS pattern.
- Updated `index.html` cache-bust query to `v=20260430-carbon-bg-return`.
- Confirmed LAN UI and CSS fetches reference the reverted version.

## 2026-04-30 Type Mechanism Angle Analysis

User asked whether the current analysis can explain why Type 1/2/3 graph shapes
occur and whether specific angles cause each Type.

Dataset analyzed:

- `data/datasets/DD_curated_csv_v1`
- 400 rows total: Case3 200 + Case4 200.
- Type counts:
  - Type 1: 126
  - Type 2: 234
  - Type 3: 40

Key findings:

- Case3/Case4 have nearly identical Type distributions:
  - Case3: Type1 62, Type2 118, Type3 20
  - Case4: Type1 64, Type2 116, Type3 20
- Same theta pair but different Case changed Type in only 2 of 200 paired
  theta combinations.
- Model permutation importance on theta+case production model:
  - `theta1`: ~0.497 macro-F1 decrease
  - `theta2`: ~0.484 macro-F1 decrease
  - `case_is_case4`: ~0.004 macro-F1 decrease
- In current data, angle magnitude dominates Type; Case is much less important
  for Type, though still useful for response/Pt prediction.

Simple explanatory rule:

- Let `a = min(|θ₁|, |θ₂|)` and `s = |θ₁| + |θ₂|`.
- A shallow decision tree using derived angle features fit the 400 rows with
  ~0.975 accuracy / ~0.980 macro F1:
  - If `a <= 38.5` and `s <= 39`, predict Type 3.
  - If `a <= 38.5` and `s > 39`, predict Type 2.
  - If `a > 38.5`, predict Type 1.

Empirical regions:

- `max(|θ₁|, |θ₂|) <= 22`: 22/22 were Type 3.
- `max(|θ₁|, |θ₂|) <= 30`: 38 Type 3, 6 Type 2.
- `min(|θ₁|, |θ₂|) > 45`: 89 Type 1, 1 Type 2.
- `min(|θ₁|, |θ₂|) >= 55`: 54/54 were Type 1.
- `min(|θ₁|, |θ₂|) <= 30 < max(|θ₁|, |θ₂|)`: 180 Type 2,
  2 Type 3.
- `abs(|θ₁| - |θ₂|) >= 45`: 100/100 were Type 2.

CLT physics interpretation:

- Top separating CLT features by Type were stiffness anisotropy ratios:
  - `a11_a22_ratio` means by Type 1/2/3:
    `0.3565`, `2.2184`, `13.4824`
  - `d11_d22_ratio` means by Type 1/2/3:
    `0.3530`, `2.1506`, `13.4366`
- Type 3 corresponds to low absolute angles near 0 degrees and very
  x-direction-dominated extensional/bending stiffness.
- Type 1 corresponds to both absolute angles being large, with stiffness
  shifted away from x-dominance.
- Type 2 is the transition/mixed region, especially when one angle is low and
  the other is much higher.

Caveat:

- This is correlation/explanatory analysis from Case3/Case4 labels, not a full
  mechanics proof. To prove mechanism, inspect Abaqus mode shapes, post-kink
  curvature, strain energy, and controlled angle sweeps.

## Next Good Steps

1. Test theta-only predictions from the browser.
2. Test CSV upload with a known Case3/Case4 sample and Pt.
3. Install Torch if Goint/deep models should be testable from the UI now.
4. Later, migrate the static UI into the documented Next.js frontend stack if the project needs a full web app.
