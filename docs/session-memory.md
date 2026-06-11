# KyulAI Session Memory

This file captures important conversation context and project decisions so a
future chat can resume work without losing direction.

## Project Summary

KyulAI is a CAE-AI platform for composite material analysis. Its goal is to use
simulation data from multiple CAE tools to predict real-world experimental
results, with a focus on sim-to-real transfer learning.

Supported CAE tools and domains currently described in the project:

- Moldex3D: SMC/RTM molding, flow, curing, fiber orientation
- AniForm: forming and draping
- Digimat: micromechanics and material modeling
- Abaqus: structural FEA
- Simutence: multi-process simulation
- cadfil: filament winding

The repository currently contains architecture and agent-team planning
documents, not a full implemented application. The planned implementation
includes `src/data`, `src/ml`, `src/validation`, `src/backend`, and
`src/frontend`.

## Current Repository State

Important existing files:

- `CLAUDE.md`: project overview, tech stack, conventions, directory layout
- `docs/architecture/agent-team-architecture.md`: full agent/team architecture
- `agents/*/team.md`: team role definitions
- `agents/orchestrator/agent.md`: routing and coordination rules
- `scripts/launch-teams.sh`: original Claude/tmux team launcher

Files added during this Codex session:

- `scripts/agent-bus.py`: local JSONL-based message and task bus for agents
- `scripts/telegram-bridge.py`: watches local agent-bus events and forwards
  new messages/tasks to Telegram
- `scripts/launch-codex-teams.sh`: tmux launcher for Codex-style agent teams
- `docs/architecture/agent-communication.md`: local and optional chat
  integration documentation
- `.gitignore`: now ignores `.agent-bus/`
- `CLAUDE.md`: now links to agent communication documentation

## Key Decisions

1. Codex can continue this project from the Claude-created planning state.
2. The recommended first implementation area is Data Engineering:
   unified CAE schema, parser base interface, quality validation, and tests.
3. Existing agent-team separation should be preserved:
   orchestrator, research, data engineering, AI/ML, domain validation,
   backend, frontend, MLOps, and QA.
4. Telegram, Discord, and Slack are not required for agent-to-agent
   communication. A shared coordination channel is enough.
5. The repository now uses a local append-only JSONL message/task bus as the
   default coordination channel.
6. Slack, Discord, and Telegram are optional notification integrations via
   environment variables.
7. From this point onward, important chat context and decisions should be
   recorded in this file so future sessions can resume cleanly.
8. Telegram integration should be used as a live observer bridge for agent-bus
   messages/tasks, not as the required source of truth for coordination.
9. The user completed the Telegram setup flow far enough to get past the
   `getUpdates` empty-result issue. Future work can assume Telegram bridge
   credentials are available in the user's shell when they export them.

## Agent Communication

Default local coordination uses:

```bash
python3 scripts/agent-bus.py
```

Common commands:

```bash
python3 scripts/agent-bus.py post \
  --from orchestrator \
  --to data-eng \
  --topic schema \
  --subject "Start unified schema" \
  --body "Design Pydantic schemas for UnifiedCAERecord first."
```

```bash
python3 scripts/agent-bus.py inbox --agent data-eng
```

```bash
python3 scripts/agent-bus.py task create \
  --from orchestrator \
  --to data-eng \
  --title "Implement unified CAE schema" \
  --body "Create src/data/schemas and tests for the first schema version."
```

```bash
python3 scripts/agent-bus.py task list --agent data-eng
```

Codex teams can be launched with:

```bash
scripts/launch-codex-teams.sh
```

Useful overrides:

```bash
AGENT_CMD=codex scripts/launch-codex-teams.sh
TEAMS="orchestrator data-eng qa" scripts/launch-codex-teams.sh
RESET_SESSION=1 scripts/launch-codex-teams.sh
```

Optional notification environment variables:

```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
export TELEGRAM_BOT_TOKEN="123456:..."
export TELEGRAM_CHAT_ID="123456789"
```

Telegram live bridge:

```bash
python3 scripts/telegram-bridge.py --send-test
python3 scripts/telegram-bridge.py
```

Local dry-run checks:

```bash
python3 scripts/telegram-bridge.py --send-test --dry-run
python3 scripts/telegram-bridge.py --once --since beginning --reset-state --dry-run
```

## Verified During Session

The following checks were run successfully:

- `python3 scripts/agent-bus.py --help`
- `bash -n scripts/launch-codex-teams.sh`
- `python3 -m py_compile scripts/agent-bus.py`
- `python3 -m py_compile scripts/telegram-bridge.py`
- `python3 scripts/telegram-bridge.py --send-test --dry-run`
- `python3 scripts/telegram-bridge.py --once --since beginning --reset-state --dry-run`
- Agent bus smoke test:
  - posted a message from `orchestrator` to `data-eng`
  - read `data-eng` inbox
  - created a task for `data-eng`
  - updated that task to `in_progress`

The `.agent-bus/` runtime directory was created during testing and is ignored by
git.

## Next Recommended Work

Start implementation with the Data Engineering foundation:

1. Create Python package scaffolding, likely with `pyproject.toml`.
2. Implement `src/data/schemas/` with Pydantic models for `UnifiedCAERecord`.
3. Implement `src/data/parsers/base.py` with the parser interface.
4. Implement `src/data/quality/` validation rules.
5. Add focused tests for schema validation and parser contracts.

After this, Backend and AI/ML can depend on stable data contracts.

## Current Code Status As Of Latest Review

The repository now contains the first product implementation slice for the Data
Engineering foundation. Frontend, backend, ML, validation, and infrastructure
apps still have not been implemented yet.

Implemented/available today:

- Architecture and planning docs
- Team definitions under `agents/`
- Original Claude tmux launcher
- Codex tmux launcher
- Local JSONL agent message/task bus
- Telegram bridge for observing agent-bus events
- Session memory document
- `pyproject.toml` Python package/test configuration
- `src/kyulai/data/schemas.py` with initial Pydantic unified CAE data models
- `src/kyulai/data/parsers/base.py` with parser contracts
- `src/kyulai/data/quality.py` with structured quality validation helpers
- `tests/unit/test_data_foundation_contract.py` with initial API/contract tests

Latest completed milestone:

- Orchestrator kicked off implementation through `scripts/agent-bus.py`.
- Data Engineering worker implemented the first data foundation.
- QA worker implemented contract tests.
- Orchestrator integrated compatibility fixes:
  - Python 3.10-friendly enum usage
  - public aliases `CAEMetadata` and `FieldCollection`
  - `input_fields`/`output_fields` compatibility on `UnifiedCAERecord`
  - simple list serialization for basic field collections
  - public parser exports from `kyulai.data`
  - pytest `unit` marker registration
- Full test suite passes: `pytest` -> 6 passed.

Additional autonomous milestones completed:

1. Parser foundation:
   - Added typed tool mappings for Abaqus, Moldex3D, AniForm, Digimat,
     Simutence, and cadfil.
   - Added `AbaqusExportParser` for conservative Abaqus JSON exports only.
   - Added Abaqus fixture tests.
   - Added `research/recommendations/initial-methodology-priorities.md`.
   - Full test suite passed: `pytest` -> 10 passed.
2. Domain Validation foundation:
   - Added `src/kyulai/validation/physics.py`.
   - Public APIs: `PhysicsSeverity`, `PhysicsIssue`,
     `PhysicsValidationResult`, `validate_physics`.
   - Checks include finite values, node field length consistency, positive
     stiffness/modulus-like material properties, tensor sanity, and basic fiber
     orientation tensor checks.
   - Added domain validation tests.
   - Full test suite passed: `pytest` -> 16 passed.
3. Ingestion pipeline:
   - Added `src/kyulai/data/pipelines/ingestion.py`.
   - Public APIs: `IngestionResult`, `default_parsers`, `select_parser`,
     `ingest_file`.
   - `ingest_file` now connects parser selection, parsing, data quality checks,
     and physics validation.
   - Added ingestion pipeline tests.
   - Full test suite passed: `pytest` -> 21 passed.
4. Moldex3D JSON export support:
   - Added `src/kyulai/data/parsers/moldex3d.py`.
   - Public APIs: `Moldex3DExportParser` from `kyulai`,
     `kyulai.data`, and `kyulai.data.parsers`.
   - `default_parsers()` now includes `Moldex3DExportParser` before
     `AbaqusExportParser`, so Moldex-identifying JSON files are routed before
     generic Abaqus JSON handling.
   - Added `tests/fixtures/data/moldex3d_export.json`.
   - Added Moldex3D parser and ingestion tests.
   - Scope is conservative Moldex3D JSON exports only. Proprietary XML/binary
     parsing remains future work.
   - Full test suite passed: `pytest` -> 27 passed.

Recommended agent assignment for the next phase:

1. Orchestrator: create the initial task graph and dependency order.
2. Data Engineering: add a CLI or batch ingestion interface, then expand parser
   coverage beyond Abaqus/Moldex3D as sample data becomes available.
3. QA: keep adding fixture-driven tests and negative-path validation cases.
4. Domain Validation: refine checks into tool/material-specific modules and add
   uncertainty validation later.
5. Backend: can now start a thin API around `ingest_file`, because there is a
   stable enough data/validation entrypoint.
6. AI/ML: should still wait for more realistic fixtures or paired experimental
   examples before training code becomes useful.
7. MLOps: can add lightweight CI/test automation once the current uncommitted
   scaffold is reviewed.

## DD Laminate AI And UI Work

In the full project checkout at `/Users/danlee/KyulAI_codex`, the active work shifted to DD laminate Type prediction.

Canonical case naming:

- Case 1: To be determined.
- Case 2: `[[±theta1]/[±theta2]]4`
- Case 3: `[[±theta1]/[±theta2]/[∓theta2]/[∓theta2]]2`
- Case 4: `[([±theta1]/[±theta2])2 / ([∓theta1]/[∓theta2])2]`

Current curated dataset:

- `/Users/danlee/KyulAI_codex/data/datasets/DD_curated_csv_v1`
- Total 400 samples from Case3 and Case4.
- Counts: Type1 126, Type2 234, Type3 40.

Current model families:

- Curve/CSV + metadata classifier:
  `/Users/danlee/KyulAI_codex/models/dd_laminate_csv_meta_v1`
- GointMLP-inspired deep sequence classifier:
  `/Users/danlee/KyulAI_codex/models/dd_laminate_deep_sequence_grouped_v1`
- Theta-only classical classifier:
  `/Users/danlee/KyulAI_codex/models/dd_laminate_theta_v1`
- Theta-only GointMLP-style classifier:
  `/Users/danlee/KyulAI_codex/models/dd_laminate_theta_goint_grouped_v1`

Unified DD summary:

- `/Users/danlee/KyulAI_codex/docs/DD_Laminate_AI_Current_Summary.md`

First local UI/API slice added:

- Backend router:
  `/Users/danlee/KyulAI_codex/src/backend/api/v1/dd_laminate.py`
- Standalone DB-free API app:
  `/Users/danlee/KyulAI_codex/src/backend/dd_laminate_app.py`
- Static frontend:
  `/Users/danlee/KyulAI_codex/src/frontend/dd-laminate`

Run commands:

```bash
cd /Users/danlee/KyulAI_codex
make dd-api
make dd-ui
```

Then open `http://localhost:3000`.

API endpoints:

- `GET /api/v1/dd-laminate/models`
- `POST /api/v1/dd-laminate/predict/theta`
- `POST /api/v1/dd-laminate/predict/curve`

Verification performed:

- `python3 -m py_compile src/backend/api/v1/dd_laminate.py src/backend/dd_laminate_app.py`
- `node --check src/frontend/dd-laminate/app.js`
- Basic HTML parse of `src/frontend/dd-laminate/index.html`

Limitation observed:

- The project `.venv` did not currently have FastAPI/Torch/scikit-learn installed in this Codex environment, so live model-serving verification still needs an API+ML dependency environment.

## External DD Laminate Dataset Review

User pointed to a separate working tree/data path:

- Dataset: `/Users/danlee/KyulAI_codex/data/datasets/DD`
- Extra context: `/Users/danlee/KyulAI_codex/extra/DD_Laminate_Research_Context.md`
- PPT: `/Users/danlee/Personal/Won/Presentation_G3MS_Dongwon.pptx`

Findings from inspection:

- The dataset path currently contains `Case3` and `Case4`, not folders named
  `Case2` and `Case3`.
- Each case has `Trial_1` and `Trial_2`, each sorted into `type1`, `type2`,
  and `type3`.
- There are 800 PNG graph images total:
  - Case3 Trial_1: type1 61, type2 114, type3 25
  - Case3 Trial_2: type1 61, type2 114, type3 25
  - Case4 Trial_1: type1 82, type2 98, type3 20
  - Case4 Trial_2: type1 82, type2 98, type3 20
- There are only two CSV files in this DD dataset:
  - `Case3/transition_load.csv`
  - `Case4/transition_load.csv`
- Each transition CSV has 200 rows with columns:
  `Test_ID, Theta1, Theta2, Pt, type`.
- These CSVs are mapping tables, not raw force-displacement curves.
- `Trial_1` images are `P1` plots and `Trial_2` images are `P2` plots. They
  are different views/series for the same test id, not byte-identical
  duplicates.
- Representative images show the graphs include title text with Test_ID, Pt,
  theta1, theta2, plotted force-displacement curve, fitted lines, kink marker,
  and transition point.
- The PPT has 21 slides. Extracted text confirms the mechanics problem,
  workflow, three DD cases, type definitions, transition-load discussion, and
  cost function context.
- `/Users/danlee/KyulAI_codex` already contains DD-specific ML code and models:
  - `src/ml/dd_laminate/data.py`
  - `src/ml/dd_laminate/classifier.py`
  - `src/ml/dd_laminate/train.py`
  - `src/ml/dd_laminate/optimize.py`
  - `models/dd_laminate/image_classifier.pt`
  - `models/dd_laminate/angle_predictor.pt`
  - `models/dd_laminate/pt_predictor.pt`
- Existing DD code appears to load Case3/Case4, store both P1/P2 image paths,
  but the current image classifier dataset uses only `image_path_p1`.

Open questions before modifying DD AI implementation:

1. Should `Case3` and `Case4` in the folder be treated as the user's described
   Case 2 and Case 3, or are they truly Case 3 and Case 4?
2. Should `Trial_1/P1` and `Trial_2/P2` both be used for classification, or is
   one of them the authoritative graph for type sorting?
3. Are raw force-displacement CSV files available elsewhere, or should the first
   production prototype use graph PNG image classification plus the
   `transition_load.csv` mapping tables?
4. Should labels be corrected using
   `classification_review_report.md` recommendations before training, or should
   the current folder labels remain the ground truth?
5. Should code changes target `/Users/danlee/KyulAI_codex` directly, or should
   the current Codex worktree remain the implementation target and ingest the
   external dataset as read-only input?

## DD Laminate CSV-Based Reclassification

User clarified the canonical case naming:

- Case 1: To be determined.
- Case 2: `[[±θ1]/[±θ2]]4`
- Case 3: `[[±θ1]/[±θ2]/[∓θ2]/[∓θ2]]2`
- Case 4: `[([±θ1]/[±θ2])2 / ([∓θ1]/[∓θ2])2]`
- Current usable data is only Case 3 and Case 4, stored as folders
  `/Users/danlee/KyulAI_codex/data/datasets/DD/Case3` and `Case4`.

New raw force-displacement CSV curves were found:

- `/Users/danlee/KyulAI_codex/data/datasets/DD/Case3/csv_load`
- `/Users/danlee/KyulAI_codex/data/datasets/DD/Case4/csv_load`
- 200 files per case, named `force_disp_Test_###.csv`.
- Each file is a two-column displacement/load curve with no header.

The advisor paper `/Users/danlee/KyulAI_codex/extra/CS_DDpaper.pdf` was
extracted with `pdftotext`. Key criterion:

- For unsymmetric DD laminates, classical bifurcation buckling load is not the
  main quantity.
- A geometrically nonlinear load-displacement response is used.
- Transition load is approximated by the intersection of the two stable path
  slopes.
- Therefore, type classification should focus on post-transition behavior:
  linear branch, moderate curvature, or strong/tail curvature.

Created new code and curated dataset in the external project:

- Script:
  `/Users/danlee/KyulAI_codex/scripts/dd_reclassify_from_csv.py`
- New dataset:
  `/Users/danlee/KyulAI_codex/data/datasets/DD_curated_csv_v1`
- Reports/metadata:
  - `DD_curated_csv_v1/README.md`
  - `DD_curated_csv_v1/classification_audit.csv`
  - `DD_curated_csv_v1/classification_review_report_csv.md`

Original dataset was not modified. The new dataset copies P1/P2 images and raw
CSV curves into final type folders. It remains compatible with the existing
loader `src.ml.dd_laminate.data.load_dd_dataset()`.

CSV-validated final label counts:

- Original Case3: Type1 61, Type2 114, Type3 25.
- Curated Case3: Type1 62, Type2 118, Type3 20.
- Original Case4: Type1 82, Type2 98, Type3 20.
- Curated Case4: Type1 64, Type2 116, Type3 20.
- Total changed labels: 24.
- Needs-review rows: 2.

Important label decisions:

- Case3 `Test_085`, `Test_162`, `Test_166`, `Test_180`, `Test_197` changed
  Type3 -> Type2. CSV supports moderate curvature, not heavy Type3 tail
  curvature.
- Case3 `Test_008` changed Type2 -> Type1. CSV metrics place it with
  clean/borderline Type1 curves, updating the previous report's "keep as-is"
  stance.
- Case4 report-recommended Type1 -> Type2 changes were accepted except
  `Test_078` and `Test_152`; their raw CSV curves are strongly Type1-linear.
- Case3 `Test_078` and `Test_152` were kept as Type2 but flagged
  `needs_review` because the raw CSV tail after Pt is missing or too short for
  reliable post-transition classification.

Verification:

- File counts in curated dataset:
  - Case3 Trial_1 images: 200
  - Case4 Trial_1 images: 200
  - Case3 csv_load files: 200
  - Case4 csv_load files: 200
- Existing loader check:
  - `load_dd_dataset("data/datasets/DD")` -> 400 samples.
  - `load_dd_dataset("data/datasets/DD_curated_csv_v1")` -> 400 samples with
    Case3 62/118/20 and Case4 64/116/20.

## DD CSV Curve Classifier Training

User asked to train a classifier using the corrected classification standard.
Decision:

- Use CSV curves as the primary model input because the new labels are defined
  from force-displacement curve behavior, while graph PNGs are a rendered
  secondary representation.
- Do not overwrite Claude's previous image-only models.
- Train a separate sklearn classifier from normalized curve-shape features.
- Use grouped cross-validation by `Test_ID` so matching Case3/Case4 samples do
  not leak between train and validation folds.

New files in `/Users/danlee/KyulAI_codex/src/ml/dd_laminate`:

- `curve_features.py`
  - Loads `transition_load.csv` + `csv_load/force_disp_Test_###.csv`.
  - Extracts 13 shape features including post-transition R2, normalized RMSE,
    slope ratio/drop, tail R2, quadratic curvature, transition location/load
    ratios, post fraction, and data-quality code.
- `train_curve_classifier.py`
  - Compares ExtraTrees, RandomForest, HistGradientBoosting, and RBF-SVC.
  - Saves model bundle, feature table, metrics JSON, feature importances, and
    markdown report.
- `predict_curve_classifier.py`
  - CLI/API helper for predicting one new force-displacement CSV when `Pt` is
    known.

Training command used:

```bash
cd /Users/danlee/KyulAI_codex
python3 -m src.ml.dd_laminate.train_curve_classifier \
  --data-dir data/datasets/DD_curated_csv_v1 \
  --output-dir models/dd_laminate_csv_v1
```

Outputs:

- `/Users/danlee/KyulAI_codex/models/dd_laminate_csv_v1/curve_classifier.joblib`
- `/Users/danlee/KyulAI_codex/models/dd_laminate_csv_v1/curve_features.csv`
- `/Users/danlee/KyulAI_codex/models/dd_laminate_csv_v1/feature_importances.csv`
- `/Users/danlee/KyulAI_codex/models/dd_laminate_csv_v1/curve_classifier_metrics.json`
- `/Users/danlee/KyulAI_codex/models/dd_laminate_csv_v1/curve_classifier_report.md`

Grouped 5-fold CV result:

- Best model: RandomForest.
- Accuracy: 0.9675 ± 0.0367.
- Macro F1: 0.9738 ± 0.0264.
- Confusion matrix, rows true and columns predicted `[Type1, Type2, Type3]`:

```text
[[120   6   0]
 [  6 228   0]
 [  0   1  39]]
```

Most important features:

- `tail_r2`
- `transition_x_ratio`
- `transition_load_ratio`
- `abs_quad_a`
- `post_nrmse`
- `post_r2`

Single-sample prediction test:

```bash
python3 -m src.ml.dd_laminate.predict_curve_classifier \
  data/datasets/DD_curated_csv_v1/Case3/csv_load/force_disp_Test_008.csv \
  --pt 13801.0 --case Case3 --test-id Test_008 --theta1 -43 --theta2 77
```

Result:

- Predicted Type: 1.
- Probabilities: Type1 0.9995, Type2 0.0005, Type3 0.0000.

## DD Combined Metadata + Curve Classifier

User clarified the next desired model:

- `Case3` and `Case4` files with the same `force_disp_Test_###.csv` name are
  not identical data.
- All 200 matching Test_ID pairs share the same theta1/theta2 values.
- Zero CSV pairs are byte-identical.
- 193/200 pairs have the same array shape; 7 pairs have different row counts:
  `Test_060`, `Test_078`, `Test_079`, `Test_140`, `Test_143`, `Test_152`,
  `Test_185`.

User wanted filenames to avoid collisions and wanted training/validation to mix
more freely instead of being forced apart by shared names. Implemented:

- Flat unique CSV view:
  `/Users/danlee/KyulAI_codex/data/datasets/DD_curated_csv_v1/flat_csv`
- Manifest:
  `/Users/danlee/KyulAI_codex/data/datasets/DD_curated_csv_v1/flat_csv/manifest.csv`
- 400 copied CSV files plus manifest.
- Filename pattern:
  `Case3_type2_force_disp_Test_001.csv`,
  `Case4_type1_force_disp_Test_006.csv`, etc.
- Script:
  `/Users/danlee/KyulAI_codex/scripts/dd_flatten_curated_csv.py`

Updated classifier code:

- `curve_features.py`
  - Added `case_id`.
  - Added feature sets:
    - `curve`: curve-only features.
    - `metadata`: `theta1`, `theta2`, `pt`, `case_id`.
    - `combined`: metadata + curve features.
- `train_curve_classifier.py`
  - Added `--feature-set curve|metadata|combined`.
  - Added `--cv-mode sample|grouped`.
  - Default for new combined model uses sample-level shuffled StratifiedKFold.
  - Still writes a secondary grouped CV check for conservative comparison.
- `predict_curve_classifier.py`
  - Works with combined model if `--pt`, `--case`, `--theta1`, `--theta2` are
    supplied.

Training command:

```bash
cd /Users/danlee/KyulAI_codex
python3 -m src.ml.dd_laminate.train_curve_classifier \
  --data-dir data/datasets/DD_curated_csv_v1 \
  --output-dir models/dd_laminate_csv_meta_v1 \
  --feature-set combined \
  --cv-mode sample
```

Combined model outputs:

- `/Users/danlee/KyulAI_codex/models/dd_laminate_csv_meta_v1/curve_classifier.joblib`
- `/Users/danlee/KyulAI_codex/models/dd_laminate_csv_meta_v1/curve_features.csv`
- `/Users/danlee/KyulAI_codex/models/dd_laminate_csv_meta_v1/permutation_importances.csv`
- `/Users/danlee/KyulAI_codex/models/dd_laminate_csv_meta_v1/curve_classifier_metrics.json`
- `/Users/danlee/KyulAI_codex/models/dd_laminate_csv_meta_v1/curve_classifier_report.md`

Combined model result:

- Selected model: HistGradientBoosting.
- Primary sample CV:
  - Accuracy: 0.9950 ± 0.0100.
  - Macro F1: 0.9958 ± 0.0083.
  - Confusion matrix:

```text
[[124   2   0]
 [  0 234   0]
 [  0   0  40]]
```

- Secondary conservative grouped CV:
  - Best grouped model: RandomForest.
  - Accuracy: 0.9675 ± 0.0367.
  - Macro F1: 0.9738 ± 0.0264.

Top permutation-importance features for the selected combined model:

- `transition_x_ratio`
- `post_slope_ratio`
- `theta1`
- `theta2`
- `pt` and `case_id` had zero permutation importance in this trained model,
  likely because the curve-shape features already explain almost all current
  label variance.

Single prediction smoke test:

```bash
python3 -m src.ml.dd_laminate.predict_curve_classifier \
  data/datasets/DD_curated_csv_v1/Case4/csv_load/force_disp_Test_194.csv \
  --model models/dd_laminate_csv_meta_v1/curve_classifier.joblib \
  --pt 13037.617786195782 --case Case4 --test-id Test_194 \
  --theta1 -29 --theta2 74
```

Result:

- Predicted Type: 2.
- Probabilities: Type1 0.0000, Type2 1.0000, Type3 0.0000.

Important future note:

- For a future Case5, if a raw force-displacement CSV and Pt are available,
  this combined model can still make a shape-based Type prediction. However,
  the current `case_id` encoding only knows Case3/Case4, so Case5 structural
  generalization should eventually use a richer case/layup descriptor rather
  than a simple integer ID.

## DD Neural-Net Candidate Comparison

User asked to try NN-family models and show them together with all existing
models. Updated:

- `/Users/danlee/KyulAI_codex/src/ml/dd_laminate/train_curve_classifier.py`
  now includes two sklearn MLPClassifier candidates:
  - `neural_net_mlp_adam`: `(64, 32)` hidden layers, Adam, early stopping.
  - `neural_net_mlp_lbfgs`: `(48, 24)` hidden layers, LBFGS solver, better for
    small tabular datasets.
- Reports now list tree/SVC/HGB/NN candidates in the same table.
- Final full-data candidate bundles are saved for every model:
  `/Users/danlee/KyulAI_codex/models/dd_laminate_csv_meta_v1/candidate_models/`
  - `extra_trees.joblib`
  - `random_forest.joblib`
  - `hist_gradient_boosting.joblib`
  - `svc_rbf.joblib`
  - `neural_net_mlp_adam.joblib`
  - `neural_net_mlp_lbfgs.joblib`

Primary sample CV results:

| Model | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| hist_gradient_boosting | 0.9950 ± 0.0100 | 0.9958 ± 0.0083 | 0.9949 |
| random_forest | 0.9925 ± 0.0100 | 0.9938 ± 0.0083 | 0.9924 |
| extra_trees | 0.9800 ± 0.0061 | 0.9838 ± 0.0050 | 0.9801 |
| neural_net_mlp_lbfgs | 0.9550 ± 0.0257 | 0.9576 ± 0.0226 | 0.9547 |
| svc_rbf | 0.9575 ± 0.0127 | 0.9515 ± 0.0221 | 0.9582 |
| neural_net_mlp_adam | 0.9425 ± 0.0232 | 0.9222 ± 0.0395 | 0.9411 |

Secondary conservative grouped CV results:

| Model | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| random_forest | 0.9675 ± 0.0367 | 0.9738 ± 0.0264 | 0.9674 |
| hist_gradient_boosting | 0.9650 ± 0.0464 | 0.9710 ± 0.0328 | 0.9645 |
| extra_trees | 0.9575 ± 0.0232 | 0.9640 ± 0.0151 | 0.9574 |
| neural_net_mlp_lbfgs | 0.9475 ± 0.0200 | 0.9491 ± 0.0209 | 0.9481 |
| svc_rbf | 0.9600 ± 0.0348 | 0.9448 ± 0.0614 | 0.9610 |
| neural_net_mlp_adam | 0.9350 ± 0.0561 | 0.9228 ± 0.0683 | 0.9339 |

Conclusion:

- NN-family models work, especially `neural_net_mlp_lbfgs`, but they do not
  beat HGB/RandomForest on this small tabular feature dataset.
- Keep `hist_gradient_boosting` as the default production model for now.
- Use `neural_net_mlp_lbfgs.joblib` as the best NN baseline if the user wants
  to compare NN-specific behavior.

NN prediction smoke test:

```bash
python3 -m src.ml.dd_laminate.predict_curve_classifier \
  data/datasets/DD_curated_csv_v1/Case4/csv_load/force_disp_Test_194.csv \
  --model models/dd_laminate_csv_meta_v1/candidate_models/neural_net_mlp_lbfgs.joblib \
  --pt 13037.617786195782 --case Case4 --test-id Test_194 \
  --theta1 -29 --theta2 74
```

Result: Predicted Type 2 with Type2 probability 1.0000.

## Review of User's Old GointMLP Code

User pointed to old deep-learning code:

- `/Users/danlee/KyulAI_codex/extra/GointMLP-master`

Important structure:

- `Model/GointMLP.py`
  - PyTorch Lightning module.
  - Architecture: GRU over input sequence, then JointMLP output head.
  - Multi-task output: regression value + CORAL ordinal classification logits.
- `Model/JointmLP.py`
  - `JointmLP` is an ensemble-like set of `SimpleMLP` branches.
  - Uses Sparsemax inside branches.
  - Uses `CoralLayer` for ordinal classification.
- `Dataloader/data.py`
  - Hard-coded for TDM medical columns:
    `gender`, `age`, `Ht`, `Wt`, `interval`, `tdm_value`, `range`, etc.
  - Not directly compatible with DD without a new adapter.
- `Dataloader/dataModule.py`
  - Variable-length sequence dataset with padding and mask.
  - Good conceptual fit for force-displacement curves.
- `Utils/losses.py`
  - Regression losses plus CORAL ordinal classification loss.

Dependency check in current environment:

- `torch` installed: 2.2.2.
- Missing: `pytorch_lightning`, `coral_pytorch`, `sparsemax`, `torchmetrics`.

Assessment for DD laminate:

- This is not a drop-in model for DD because the dataloader/schema is tied to
  TDM data.
- Conceptually it is a strong fit:
  - Force-displacement CSV is naturally a sequence.
  - GRU can learn curve evolution directly.
  - Type 1 < Type 2 < Type 3 is ordinal, so CORAL is appropriate.
  - Regression head could predict Pt or normalized transition/load if desired.
- Recommended next implementation:
  - Build a DD-specific GointMLP-inspired model in the main project rather than
  trying to run the old repo as-is.
  - Avoid extra dependencies at first by implementing a lightweight PyTorch
    version: GRU encoder + MLP head + optional ordinal/CORAL-style loss.
  - Inputs per timestep can include normalized displacement, normalized load,
    theta1, theta2, Pt, case_id, and maybe step index.
  - Output initially: Type 1/2/3 classification.
  - Optional later: multi-task Type + Pt/transition regression.

## DD GointMLP-Inspired Deep Sequence Model

User approved adapting the old GointMLP idea to DD instead of running the old
TDM code directly. Implemented a pure PyTorch version, avoiding missing
dependencies (`pytorch_lightning`, `coral_pytorch`, `sparsemax`,
`torchmetrics`):

- `/Users/danlee/KyulAI_codex/src/ml/dd_laminate/deep_sequence.py`
  - Loads DD samples from `transition_load.csv` + raw `csv_load` curves.
  - Resamples each force-displacement curve to a fixed sequence.
  - Per-timestep features:
    `displacement_norm`, `load_norm`, `step_norm`, `theta1/90`, `theta2/90`,
    `pt/pt_scale`, `case_id`, `load/pt`.
  - Model: bidirectional GRU encoder + JointMLP-style multi-branch MLP head.
  - Outputs class logits plus auxiliary ordinal logits.
  - Loss: cross entropy + CORAL-style ordinal BCE auxiliary loss.
- `/Users/danlee/KyulAI_codex/src/ml/dd_laminate/train_deep_sequence_classifier.py`
  - Trains/evaluates the DD Goint sequence classifier.
  - Supports sample/grouped CV, CPU/MPS/CUDA selection.
  - MPS GRU was very slow in this environment; CPU was used.
- `/Users/danlee/KyulAI_codex/src/ml/dd_laminate/predict_deep_sequence_classifier.py`
  - Single raw CSV prediction helper.

Primary sample-CV training command:

```bash
cd /Users/danlee/KyulAI_codex
python3 -m src.ml.dd_laminate.train_deep_sequence_classifier \
  --data-dir data/datasets/DD_curated_csv_v1 \
  --output-dir models/dd_laminate_deep_sequence_v1 \
  --cv-mode sample \
  --seq-len 128 \
  --device cpu
```

Sample-CV outputs:

- `/Users/danlee/KyulAI_codex/models/dd_laminate_deep_sequence_v1/dd_goint_sequence.pt`
- `/Users/danlee/KyulAI_codex/models/dd_laminate_deep_sequence_v1/deep_sequence_report.md`
- `/Users/danlee/KyulAI_codex/models/dd_laminate_deep_sequence_v1/deep_sequence_metrics.json`
- `/Users/danlee/KyulAI_codex/models/dd_laminate_deep_sequence_v1/oof_predictions.csv`

Sample-CV result:

- Accuracy: 0.9775 ± 0.0094.
- Macro F1: 0.9819 ± 0.0075.
- Confusion matrix rows true / columns predicted `[Type1, Type2, Type3]`:

```text
[[125   1   0]
 [  8 226   0]
 [  0   0  40]]
```

Grouped-CV command:

```bash
python3 -m src.ml.dd_laminate.train_deep_sequence_classifier \
  --data-dir data/datasets/DD_curated_csv_v1 \
  --output-dir models/dd_laminate_deep_sequence_grouped_v1 \
  --cv-mode grouped \
  --seq-len 128 \
  --device cpu
```

Grouped-CV outputs:

- `/Users/danlee/KyulAI_codex/models/dd_laminate_deep_sequence_grouped_v1/dd_goint_sequence.pt`
- `/Users/danlee/KyulAI_codex/models/dd_laminate_deep_sequence_grouped_v1/deep_sequence_report.md`
- `/Users/danlee/KyulAI_codex/models/dd_laminate_deep_sequence_grouped_v1/deep_sequence_metrics.json`
- `/Users/danlee/KyulAI_codex/models/dd_laminate_deep_sequence_grouped_v1/oof_predictions.csv`

Grouped-CV result:

- Accuracy: 0.9800.
- Macro F1: 0.9840.
- Confusion matrix:

```text
[[126   0   0]
 [  8 226   0]
 [  0   0  40]]
```

Single deep prediction smoke test:

```bash
python3 -m src.ml.dd_laminate.predict_deep_sequence_classifier \
  data/datasets/DD_curated_csv_v1/Case4/csv_load/force_disp_Test_194.csv \
  --model models/dd_laminate_deep_sequence_v1/dd_goint_sequence.pt \
  --pt 13037.617786195782 \
  --case Case4 \
  --test-id Test_194 \
  --theta1 -29 \
  --theta2 74 \
  --device cpu
```

Result:

- Predicted Type: 2.
- Softmax probabilities: Type1 0.0012, Type2 0.9985, Type3 0.0003.
- Ordinal probabilities:
  - `P(type > 1)`: 0.9963.
  - `P(type > 2)`: 0.0021.

Comparison note:

- HGB remains the strongest feature-engineered production model:
  sample macro F1 0.9958.
- The DD Goint sequence model is the strongest true deep-learning curve model so
  far and clearly beats the sklearn MLP baselines:
  sample macro F1 0.9819, grouped macro F1 0.9840.
- This is now a credible "deep learning" approach because it reads the raw
  curve sequence directly rather than only engineered curve statistics.

## DD Theta-Only Type Predictor

User asked for a much harder pre-Abaqus model that predicts Type using only
`theta1` and `theta2`, without Pt or force-displacement curves.

Important data issue:

- Case3 and Case4 share 200 identical theta pairs.
- There are 2 theta pairs with conflicting curated labels:
  - `(73, -45)`: Case3/Test_078 Type2, Case4/Test_078 Type1.
  - `(-52, 62)`: Case3/Test_152 Type2, Case4/Test_152 Type1.
- Therefore, theta-only prediction is intrinsically ambiguous for these pairs.

Implemented:

- `/Users/danlee/KyulAI_codex/src/ml/dd_laminate/train_theta_classifier.py`
- `/Users/danlee/KyulAI_codex/src/ml/dd_laminate/predict_theta_classifier.py`

Training command:

```bash
cd /Users/danlee/KyulAI_codex
python3 -m src.ml.dd_laminate.train_theta_classifier \
  --data-dir data/datasets/DD_curated_csv_v1 \
  --output-dir models/dd_laminate_theta_v1
```

Outputs:

- `/Users/danlee/KyulAI_codex/models/dd_laminate_theta_v1/theta_classifier.joblib`
- `/Users/danlee/KyulAI_codex/models/dd_laminate_theta_v1/theta_classifier_report.md`
- `/Users/danlee/KyulAI_codex/models/dd_laminate_theta_v1/theta_classifier_metrics.json`
- `/Users/danlee/KyulAI_codex/models/dd_laminate_theta_v1/theta_training_rows.csv`
- `/Users/danlee/KyulAI_codex/models/dd_laminate_theta_v1/theta_label_conflicts.csv`
- Candidate model bundles:
  `/Users/danlee/KyulAI_codex/models/dd_laminate_theta_v1/candidate_models/`

Primary sample CV results:

| Model | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| extra_trees | 0.9600 ± 0.0184 | 0.9675 ± 0.0151 | 0.9600 |
| neural_net_mlp_lbfgs | 0.9600 ± 0.0200 | 0.9667 ± 0.0172 | 0.9596 |
| hist_gradient_boosting | 0.9650 ± 0.0122 | 0.9644 ± 0.0213 | 0.9646 |
| random_forest | 0.9575 ± 0.0170 | 0.9626 ± 0.0179 | 0.9574 |
| neural_net_mlp_adam | 0.9225 ± 0.0527 | 0.9198 ± 0.0534 | 0.9217 |
| svc_rbf | 0.8850 ± 0.0483 | 0.8758 ± 0.0587 | 0.8866 |

Secondary grouped CV results, better for unseen theta pairs:

| Model | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| neural_net_mlp_adam | 0.9150 ± 0.0496 | 0.9188 ± 0.0522 | 0.9141 |
| neural_net_mlp_lbfgs | 0.8900 ± 0.0215 | 0.8807 ± 0.0507 | 0.8892 |
| random_forest | 0.9100 ± 0.0457 | 0.8730 ± 0.0731 | 0.9091 |
| extra_trees | 0.8900 ± 0.0184 | 0.8705 ± 0.0449 | 0.8874 |
| svc_rbf | 0.8800 ± 0.0615 | 0.8570 ± 0.0908 | 0.8824 |
| hist_gradient_boosting | 0.8900 ± 0.0629 | 0.8313 ± 0.0793 | 0.8879 |

Default saved model:

- `theta_classifier.joblib` uses `extra_trees`, selected from primary sample CV.
- For unseen theta generalization, also consider:
  `candidate_models/neural_net_mlp_adam.joblib`, which had the best grouped CV.

Smoke tests:

```bash
python3 -m src.ml.dd_laminate.predict_theta_classifier \
  --theta1 -29 --theta2 74 \
  --model models/dd_laminate_theta_v1/theta_classifier.joblib
```

Result: Predicted Type2 with probability 1.0000.

```bash
python3 -m src.ml.dd_laminate.predict_theta_classifier \
  --theta1 73 --theta2 -45 \
  --model models/dd_laminate_theta_v1/theta_classifier.joblib
```

Result: Predicted Type1 with probabilities Type1 0.6500, Type2 0.3500,
showing useful uncertainty for an intrinsically conflicting theta pair.

Interpretation:

- Theta-only is feasible and surprisingly strong, but it is less reliable than
  models that see Pt/curve data.
- Use it as a pre-Abaqus screening surrogate, not final classification.
- For top candidates, run Abaqus and then use the curve/deep-sequence model for
  final Type classification.

## DD Theta-Only GointMLP-Inspired Model

User asked whether the GointMLP idea can also be applied to theta-only
prediction. Since theta-only input has no sequence, a GRU is not meaningful
there. Implemented a GointMLP-inspired theta model using the JointMLP part:

- Multi-branch MLP head.
- Auxiliary ordinal loss, mirroring the CORAL idea.
- Input only: `theta1/90`, `theta2/90`.
- No case, Pt, or force-displacement curve data.

Implemented:

- `/Users/danlee/KyulAI_codex/src/ml/dd_laminate/theta_deep.py`
- `/Users/danlee/KyulAI_codex/src/ml/dd_laminate/train_theta_deep_classifier.py`
- `/Users/danlee/KyulAI_codex/src/ml/dd_laminate/predict_theta_deep_classifier.py`

Sample CV command:

```bash
cd /Users/danlee/KyulAI_codex
python3 -m src.ml.dd_laminate.train_theta_deep_classifier \
  --data-dir data/datasets/DD_curated_csv_v1 \
  --output-dir models/dd_laminate_theta_goint_v1 \
  --cv-mode sample \
  --device cpu
```

Sample CV result:

- Accuracy: 0.9450 ± 0.0257.
- Macro F1: 0.9512 ± 0.0241.
- Confusion matrix:

```text
[[123   3   0]
 [ 17 215   2]
 [  0   0  40]]
```

Grouped CV command:

```bash
python3 -m src.ml.dd_laminate.train_theta_deep_classifier \
  --data-dir data/datasets/DD_curated_csv_v1 \
  --output-dir models/dd_laminate_theta_goint_grouped_v1 \
  --cv-mode grouped \
  --device cpu
```

Grouped CV result:

- Accuracy: 0.9050 ± 0.0595.
- Macro F1: 0.8989 ± 0.0758.
- Confusion matrix:

```text
[[118   8   0]
 [ 24 204   6]
 [  0   0  40]]
```

Outputs:

- `/Users/danlee/KyulAI_codex/models/dd_laminate_theta_goint_v1/theta_goint.pt`
- `/Users/danlee/KyulAI_codex/models/dd_laminate_theta_goint_v1/theta_goint_report.md`
- `/Users/danlee/KyulAI_codex/models/dd_laminate_theta_goint_grouped_v1/theta_goint.pt`
- `/Users/danlee/KyulAI_codex/models/dd_laminate_theta_goint_grouped_v1/theta_goint_report.md`

Prediction examples:

```bash
python3 -m src.ml.dd_laminate.predict_theta_deep_classifier \
  --theta1 -29 --theta2 74 \
  --model models/dd_laminate_theta_goint_v1/theta_goint.pt \
  --device cpu
```

Result: Type2 with probabilities Type1 0.0555, Type2 0.9444, Type3 0.0000.

```bash
python3 -m src.ml.dd_laminate.predict_theta_deep_classifier \
  --theta1 73 --theta2 -45 \
  --model models/dd_laminate_theta_goint_v1/theta_goint.pt \
  --device cpu
```

Result: Type1 with probabilities Type1 0.9352, Type2 0.0648, Type3 0.0000.

Interpretation:

- Goint-style theta-only works, but it does not beat the best classical
  theta-only model on sample CV.
- It is comparable to theta-only sklearn MLP baselines.
- The full curve-sequence Goint model is the better place to use the GointMLP
  idea because it can exploit the actual force-displacement sequence.

## Unified DD Summary Document

User asked for one consolidated summary because many model results had
accumulated. Created:

- `/Users/danlee/KyulAI_codex/docs/DD_Laminate_AI_Current_Summary.md`

The document summarizes:

- Current DD research goal and case definitions.
- Curated dataset and label counts.
- CSV/curve HGB classifier.
- GointMLP-inspired deep sequence classifier.
- Theta-only predictor.
- Theta-only GointMLP-style deep predictor.
- Which model to use in each situation.
- Key caveats and important file paths.

## DD UI/API Live Test Update

In `/Users/danlee/KyulAI_codex`, a first local DD predictor UI/API slice was
added and then live-tested.

Backend files:

- `/Users/danlee/KyulAI_codex/src/backend/api/v1/dd_laminate.py`
- `/Users/danlee/KyulAI_codex/src/backend/dd_laminate_app.py`

Frontend folder:

- `/Users/danlee/KyulAI_codex/src/frontend/dd-laminate`

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

## 2026-04-30 Cloudflare Tunnel Access

User asked to make the DD Laminate app accessible from outside the local
network through Cloudflare.

Implemented:

- Updated `src/backend/dd_laminate_app.py` so the standalone FastAPI app serves
  the static DD frontend at `/` while keeping API routes under `/api/v1`.
- Updated `src/frontend/dd-laminate/app.js`:
  - If running from local dev server port `3000`, keep using
    `http://<host>:8000/api/v1/dd-laminate`.
  - Otherwise use same-origin API:
    `${window.location.origin}/api/v1/dd-laminate`.
- Updated `src/frontend/dd-laminate/index.html` cache-bust query to
  `v=20260430-cloudflare`.

Runtime state:

- Uvicorn is running at `http://127.0.0.1:8000`.
- Cloudflare quick tunnel is running to that local server.
- Current public test URL:
  `https://command-newbie-scholarship-sofa.trycloudflare.com`

Verification:

- `PYTHONPYCACHEPREFIX=/tmp/kyulai_pycache python3 -m py_compile` passed for
  DD backend files.
- `node --check src/frontend/dd-laminate/app.js` passed.
- Local checks passed:
  - `http://127.0.0.1:8000/health`
  - `http://127.0.0.1:8000/`
  - `http://127.0.0.1:8000/api/v1/dd-laminate/models`
- Cloudflare checks passed:
  - Public URL returns the DD UI HTML.
  - Public `/api/v1/dd-laminate/models` returns model metadata.
  - Public theta prediction smoke:
    `theta1=-29`, `theta2=74`, `Case4`, `theta_classical`
    -> Type 2, confidence `0.999863`.

Notes:

- This is an account-less Cloudflare quick tunnel. It is temporary and only
  works while both the local Uvicorn process and `cloudflared` process are
  running.
- For a stable URL, set up a named Cloudflare Tunnel under a Cloudflare account
  and route a custom domain/subdomain.

## 2026-04-30 Named Cloudflare Tunnel Attempt

User asked whether DD and Injection can be exposed simultaneously through a
stable Cloudflare setup and requested the stable approach.

Findings:

- Both apps can be exposed at the same time.
- Best stable approach:
  - One Cloudflare named tunnel.
  - One public hostname, with paths such as `/dd` and `/injection`, or separate
    hostnames such as `dd.example.com` and `injection.example.com`.
  - Local routing can be one unified FastAPI app or Cloudflare ingress rules
    pointing to multiple local services.
- Current checked-out branch has DD app files, but Simple Injection app files
  are not present in this branch because the branch contains the revert commit
  `2cc9e1f Revert "Add Simple Injection predictor app"`.
- Simple Injection still exists in another local worktree:
  `/private/tmp/kyulai-simple-injection`

Cloudflare status:

- `cloudflared` is installed at `/opt/homebrew/bin/cloudflared`.
- `cloudflared tunnel list` failed because no Cloudflare origin certificate
  exists locally.
- Ran `cloudflared tunnel login`; it opened/printed the Cloudflare login URL and
  waited for account/domain login.
- Login was not completed during the turn, so the waiting process was stopped.

Code prepared before the login blocker:

- `src/backend/dd_laminate_app.py` now serves the DD static UI at `/`, while
  keeping DD API under `/api/v1`.
- `src/frontend/dd-laminate/app.js` now uses same-origin API unless it is being
  served by the legacy local dev server on port `3000`.
- `src/frontend/dd-laminate/index.html` cache-bust query updated to
  `v=20260430-cloudflare`.

Verified:

- Local unified DD server:
  - `http://127.0.0.1:8000/health`
  - `http://127.0.0.1:8000/`
  - `http://127.0.0.1:8000/api/v1/dd-laminate/models`
- Existing quick tunnel also verified:
  `https://command-newbie-scholarship-sofa.trycloudflare.com`

Blocker to finish stable named tunnel:

- User must log in to Cloudflare and select a Cloudflare-managed domain/zone.
- Need target hostname choice, for example:
  - `dd.<domain>` only for DD, or
  - `apps.<domain>/dd` and `apps.<domain>/injection`, or
  - `dd.<domain>` + `injection.<domain>`.

## 2026-04-30 Domain Choice for Cloudflare

User decided not to use `kcompositelab.com` for the first Cloudflare setup
because it already has email-related DNS records and changing nameservers feels
risky.

Current direction:

- Use `cafedecafe.co.kr` instead as the Cloudflare-connected domain.
- Once Cloudflare shows `cafedecafe.co.kr` as active, continue named tunnel
  setup from the existing DD unified server on port `8000`.
- Suggested first hostname remains:
  `dd.cafedecafe.co.kr`
- If Injection is restored later, suggested second hostname:
  `injection.cafedecafe.co.kr`

Important DNS reminder:

- If `cafedecafe.co.kr` also has email, preserve MX/TXT/SPF/DKIM/DMARC records
  when moving DNS to Cloudflare.
- If it is only for testing, the setup is much simpler: point the domain's
  nameservers to Cloudflare, wait until active, then create a named tunnel and
  route `dd.cafedecafe.co.kr`.

## 2026-04-30 `dd.cafedecafe.co.kr` Named Tunnel Live

Cloudflare DNS delegation for `cafedecafe.co.kr` was verified locally:

- `perla.ns.cloudflare.com`
- `sterling.ns.cloudflare.com`

Cloudflare tunnel login completed successfully. Origin certificate saved by
Cloudflare to:

- `/Users/danlee/.cloudflared/cert.pem`

Created named tunnel:

- Name: `kclab-composite-ai`
- ID: `02b4b689-84ef-4459-91cd-48c81ea549ae`
- Credentials file:
  `/Users/danlee/.cloudflared/02b4b689-84ef-4459-91cd-48c81ea549ae.json`

Created DNS route:

- `dd.cafedecafe.co.kr` -> `kclab-composite-ai`

Local config file created:

- `infrastructure/cloudflare/kclab-composite-ai.yml`

Runtime state:

- DD FastAPI server running from `/Users/danlee/KyulAI_codex` on
  `127.0.0.1:8000`.
- Named Cloudflare Tunnel running with the config above.

Verified public URL:

- `https://dd.cafedecafe.co.kr/` returns the DD UI.
- `https://dd.cafedecafe.co.kr/api/v1/dd-laminate/models` returns model
  metadata.
- Public theta prediction smoke passed:
  `theta1=-29`, `theta2=74`, `case=Case4`, `model=theta_classical`
  -> Type 2, confidence `0.999863`.

## 2026-04-30 `injection.cafedecafe.co.kr` Added

User requested exposing the Simple Injection app the same way as DD.

Simple Injection source/runtime location:

- `/private/tmp/kyulai-simple-injection`

Started Simple Injection FastAPI server:

- App: `src.backend.simple_injection_app:app`
- Host/port: `127.0.0.1:8010`
- Command:
  `/Users/danlee/KyulAI_codex/.venv/bin/uvicorn src.backend.simple_injection_app:app --host 127.0.0.1 --port 8010`

Cloudflare route added:

- `injection.cafedecafe.co.kr` -> existing tunnel `kclab-composite-ai`

Cloudflare config updated:

- `infrastructure/cloudflare/kclab-composite-ai.yml`
- Ingress now routes:
  - `dd.cafedecafe.co.kr` -> `http://127.0.0.1:8000`
  - `injection.cafedecafe.co.kr` -> `http://127.0.0.1:8010`

Restarted named tunnel with updated config:

- `/opt/homebrew/bin/cloudflared --config /Users/danlee/KyulAI_codex/infrastructure/cloudflare/kclab-composite-ai.yml tunnel run kclab-composite-ai`

Verification:

- Local Injection health and model metadata passed:
  - `http://127.0.0.1:8010/health`
  - `http://127.0.0.1:8010/api/v1/simple-injection/models`
- Public routing was verified by forcing a Cloudflare IP with curl because local
  DNS cache had not yet caught up:
  - `https://injection.cafedecafe.co.kr/` returns the Korean Injection UI.
  - `https://injection.cafedecafe.co.kr/api/v1/simple-injection/models`
    returns model metadata.
  - Public sprue-pressure prediction smoke passed for `G01` + `P01` using
    `sprue_classical`, returning max pressure about `69 MPa`.

Note:

- Normal browser DNS may need a few minutes after route creation.

## 2026-04-30 DD Korean Page Added

User requested that DD have a Korean page like Simple Injection.

Implemented in `/Users/danlee/KyulAI_codex`:

- Added `src/frontend/dd-laminate/index.ko.html`.
- Kept `src/frontend/dd-laminate/index.html` as the English page.
- Added language switch links:
  - Korean page links to `index.html` as `English`.
  - English page links to `index.ko.html` as `한국어`.
- Updated `src/backend/dd_laminate_app.py` so root `/` serves
  `index.ko.html`.
- Added convenience routes:
  - `/dd-laminate-ko`
  - `/dd-laminate-en`
- Updated `src/frontend/dd-laminate/app.js` so dynamic UI text follows
  `document.documentElement.lang`:
  - API status
  - loading text
  - model labels
  - notes
  - CSV preview errors
  - empty chart labels
- Added `.top-actions` and `.language-link` styles to
  `src/frontend/dd-laminate/styles.css`.

Verification:

- `node --check src/frontend/dd-laminate/app.js` passed.
- `PYTHONPYCACHEPREFIX=/tmp/kyulai_pycache python3 -m py_compile
  src/backend/dd_laminate_app.py` passed.
- Restarted DD server on `127.0.0.1:8000`.
- Local `/` returns Korean DD page.
- Public `https://dd.cafedecafe.co.kr/` returned Korean DD page after restart.

## 2026-04-30 Default Language Policy Updated

User requested that both DD and Injection should default to English when the
base URL is typed directly. Korean pages should be reached through the language
button on the right side. Follow this convention for future UI work.

Implemented:

- DD:
  - `/` now serves `src/frontend/dd-laminate/index.html` (English).
  - Korean page remains at `index.ko.html` and via the `한국어` button.
  - `/dd-laminate-ko` and `/dd-laminate-en` remain available.
- Injection:
  - `/` now serves `src/frontend/simple-injection/index.html` (English).
  - Removed the root redirect to `/simple-injection/index.ko.html`.
  - Added root static serving so `/styles.css`, `/app.js`, and
    `/index.ko.html` work when the app is opened at
    `https://injection.cafedecafe.co.kr/`.
  - Legacy `/simple-injection` path still works, but it is no longer the URL
    users need to type.

Verification:

- DD local `/` returns English page.
- DD local `/index.ko.html` returns Korean page.
- Injection local `/` returns English page with no redirect.
- Injection local `/styles.css` returns CSS successfully.
- Cloudflare routing verified with direct Cloudflare IP resolution:
  - `https://dd.cafedecafe.co.kr/` returns English page.
  - `https://dd.cafedecafe.co.kr/index.ko.html` returns Korean page.
  - `https://injection.cafedecafe.co.kr/` returns English page.
  - `https://injection.cafedecafe.co.kr/styles.css` returns CSS.

Note:

- Local DNS lookup was intermittently stale/NXDOMAIN for
  `dd.cafedecafe.co.kr`, but `cloudflared tunnel route dns --overwrite-dns`
  confirmed the DD hostname is already routed to the named tunnel.

## 2026-04-30 Public App Connection Recheck

User reported the public connection seemed disconnected and asked to reconnect.

Checked runtime state:

- DD server still listening on `127.0.0.1:8000`.
- Injection server still listening on `127.0.0.1:8010`.
- Cloudflare tunnel still listening on metrics port `127.0.0.1:20241`.

Health checks:

- `http://127.0.0.1:8000/health` -> `{"status":"ok"}`
- `http://127.0.0.1:8010/health` -> `{"status":"ok"}`

Public checks:

- `https://dd.cafedecafe.co.kr/` -> HTTP 200.
- `https://injection.cafedecafe.co.kr/` -> HTTP 200.

Conclusion:

- No restart was needed. Public tunnel and both local apps were still connected.

## 2026-04-30 DD Laminate Reference Image Added

User requested adding a DD laminate structure image like the Simple Injection
shape reference, based on an attached Abaqus ply stack screenshot.

Implemented:

- Added DD image asset:
  `src/frontend/dd-laminate/assets/dd-ply-stack.svg`
- Added a reference panel to both DD pages:
  - English: `Laminate Reference` / `Double-Double ply stack`
  - Korean: `적층 구조 참고` / `Double-Double ply stack`
- Updated DD layout to show three panels by default:
  - input
  - laminate reference image
  - result
- Updated JS so the laminate reference panel hides in `Curve CSV` mode, where
  the CSV preview panel needs the middle column.

Verification:

- `node --check src/frontend/dd-laminate/app.js` passed.
- Local DD English and Korean pages include the new reference panel.
- Local asset `/assets/dd-ply-stack.svg` returns HTTP 200 as `image/svg+xml`.
- Public DD page includes the new reference image.
- Public asset `https://dd.cafedecafe.co.kr/assets/dd-ply-stack.svg` returns
  HTTP 200 as `image/svg+xml`.

## 2026-05-07 Telegram Control Question

User asked whether they can message the Telegram bot to talk to Codex or assign
work through Telegram.

Current implementation status:

- `scripts/agent-bus.py` supports local append-only agent messages/tasks.
- `scripts/telegram-bridge.py` is currently an observer bridge:
  - watches `.agent-bus/messages.jsonl` and `.agent-bus/tasks.jsonl`
  - forwards new events to Telegram with `sendMessage`
- The current bridge does not poll Telegram `getUpdates` for inbound user
  messages and does not convert Telegram messages into agent-bus tasks.

Answer:

- Agent-to-agent messages can be observed in Telegram.
- User-to-Codex or user-to-agent control from Telegram is not available yet.
- It can be implemented by adding an inbound Telegram listener that:
  - polls `getUpdates` or uses a webhook
  - only accepts allowlisted `TELEGRAM_CHAT_ID`
  - parses commands such as `/task`, `/msg`, `/status`
  - writes accepted commands into `.agent-bus/`
  - sends acknowledgements back to Telegram

Important caveat:

- Even with inbound Telegram commands, Codex itself will not automatically wake
  and execute arbitrary work unless a local runner/agent process is also
  running to read the bus and act on those tasks.

## 2026-05-07 Slack Outbound Bridge Setup

User asked to proceed step by step with Slack integration.

Implemented first phase: Slack outbound observer bridge.

Files added/restored in `/Users/danlee/KyulAI_codex`:

- `scripts/agent-bus.py`
  - Restored from the Codex worktree.
  - Supports local `.agent-bus/` messages/tasks and `--notify slack`.
- `scripts/slack-bridge.py`
  - New observer bridge.
  - Watches `.agent-bus/messages.jsonl` and `.agent-bus/tasks.jsonl`.
  - Sends new events to Slack through `SLACK_WEBHOOK_URL`.
  - Supports `--send-test`, `--dry-run`, `--once`, `--since beginning`, and
    `--reset-state`.
- `docs/architecture/agent-communication.md`
  - Documents local bus, Slack outbound bridge, and future inbound slash
    command plan.
- `.gitignore`
  - Added `.agent-bus/`.

Verification:

- `PYTHONPYCACHEPREFIX=/tmp/kyulai_pycache python3 -m py_compile
  scripts/agent-bus.py scripts/slack-bridge.py` passed.
- `python3 scripts/slack-bridge.py --send-test --dry-run` passed.
- Created a test bus message with `python3 scripts/agent-bus.py post ...`.
- `python3 scripts/slack-bridge.py --once --since beginning --reset-state
  --dry-run` printed the formatted Slack message.

Next user action:

- Create a Slack App.
- Enable Incoming Webhooks.
- Add webhook to the desired Slack channel.
- Export `SLACK_WEBHOOK_URL`.
- Then run:
  `python3 scripts/slack-bridge.py --send-test`
  and if successful:
  `python3 scripts/slack-bridge.py`.

Future phase:

- Add Slack inbound Slash Commands such as `/kyulai task`, `/kyulai msg`, and
  `/kyulai status` if the user wants Slack-to-agent control.

## 2026-05-07 Slack Webhook Connected

User provided a Slack Incoming Webhook URL and asked Codex to run the terminal
setup directly.

Actions:

- Ran `scripts/slack-bridge.py --send-test` with `SLACK_WEBHOOK_URL` set only
  in the process environment.
- Test message command exited successfully.
- Started live Slack bridge:
  `python3 scripts/slack-bridge.py`
- Live bridge is running in Codex exec session `13842`.
- Posted a live agent-bus test message:
  - from: `orchestrator`
  - to: `all`
  - topic: `slack`
  - subject: `Slack live bridge connected`

Security note:

- The Slack webhook URL was not written to project files or session memory.
- It was only used as a process environment variable for the test and live
  bridge command.

## 2026-05-07 Slack Inbound Slash Command Implemented

User asked to make Slack command control.

Implemented:

- Added `src/backend/api/v1/slack_commands.py`.
- Included the router in `src/backend/dd_laminate_app.py`.
- Public endpoint when DD server is restarted with the new code:
  `POST https://dd.cafedecafe.co.kr/slack/commands`
- Intended Slack Slash Command:
  `/kyulai`

Supported command text:

- `help`
- `status`
- `task <work request>`
- `msg <agent> <message>`

Security:

- Endpoint verifies Slack request signatures using `SLACK_SIGNING_SECRET`.
- Verifies timestamp freshness to reduce replay risk.
- Optional allowlist:
  `SLACK_ALLOWED_USER_IDS="U123,U456"`.
- Local-only bypass exists as `SLACK_ALLOW_UNSIGNED_COMMANDS=1`, but this
  should not be used for public operation.

Verification:

- `PYTHONPYCACHEPREFIX=/tmp/kyulai_pycache python3 -m py_compile
  src/backend/api/v1/slack_commands.py src/backend/dd_laminate_app.py` passed.
- FastAPI TestClient with `SLACK_ALLOW_UNSIGNED_COMMANDS=1` passed for:
  - `help`
  - `status`
  - `task Check Slack inbound command wiring`
- Test task created:
  `task_1778134243_e20b6ed6`

Next user action:

- In Slack App -> Basic Information, copy the Signing Secret.
- Configure Slash Command:
  - Command: `/kyulai`
  - Request URL: `https://dd.cafedecafe.co.kr/slack/commands`
  - Short description: `Send tasks and status requests to KyulAI`
  - Usage hint: `task <request> | status | msg <agent> <message>`
- Restart DD server with:
  `SLACK_SIGNING_SECRET` set in the process environment.

Follow-up:

- User provided the Slack Signing Secret.
- DD server was restarted with `SLACK_SIGNING_SECRET` set only as a process
  environment variable.
- New DD server process:
  - PID shown by uvicorn startup: `42221`
  - listening on `127.0.0.1:8000`
- Local signed Slack request test passed:
  - `POST http://127.0.0.1:8000/slack/commands`
  - text: `status`
  - response: HTTP 200 with KyulAI status.
- Public signed Slack request test passed:
  - `POST https://dd.cafedecafe.co.kr/slack/commands`
  - text: `help`
  - response: HTTP 200 with command help.

Operational note:

- The Signing Secret value is intentionally not recorded in this file.
- If DD server is restarted later, it must be started again with
  `SLACK_SIGNING_SECRET` in the environment or Slack Slash Commands will return
  service unavailable.

## 2026-05-07 Injection Public URL Restored

User reported `https://injection.cafedecafe.co.kr/` was not opening.

Diagnosis:

- Cloudflare tunnel was still running.
- Existing Injection server process was still listening on `127.0.0.1:8010`.
- Public URL initially returned HTTP 404, then local root showed
  `Internal Server Error`.
- Uvicorn logs showed the server was launched from the old temporary worktree:
  `/private/tmp/kyulai-simple-injection`.
- The referenced frontend file no longer existed:
  `/private/tmp/kyulai-simple-injection/src/frontend/simple-injection/index.html`.

Fix:

- Restored Simple Injection app files and models from branch
  `codex/simple-injection-predictor` into `/Users/danlee/KyulAI_codex`:
  - `src/backend/simple_injection_app.py`
  - `src/backend/api/v1/simple_injection.py`
  - `src/frontend/simple-injection`
  - `src/ml/simple_injection`
  - `models/simple_injection_sprue_pressure_v1`
  - `models/simple_injection_sprue_goint_v1`
- Reapplied root behavior:
  `/` serves English `index.html`; Korean remains at `index.ko.html`.
- Stopped old Injection server PID `36742`.
- Restarted Injection server from stable project directory:
  `/Users/danlee/KyulAI_codex`
- New Injection server PID shown by uvicorn: `56491`.

Verification:

- `PYTHONPYCACHEPREFIX=/tmp/kyulai_pycache python3 -m py_compile
  src/backend/simple_injection_app.py src/backend/api/v1/simple_injection.py`
  passed.
- Local `http://127.0.0.1:8010/` returns English Injection HTML.
- Local `http://127.0.0.1:8010/api/v1/simple-injection/models` returns both
  models as available.
- Public `https://injection.cafedecafe.co.kr/` returns HTTP 200 and English
  Injection HTML.
- Public `https://injection.cafedecafe.co.kr/api/v1/simple-injection/models`
  returns both models as available.

Note:

- These restored Injection files are currently local working-tree changes; they
  were intentionally not part of the prior DD-only git commit.

## 2026-05-07 Slack `/kyulai` Invalid Command Troubleshooting

User reported Slack says `/kyulai` is not a valid command.

Important interpretation:

- This error usually happens inside Slack before any request reaches the KyulAI
  server.
- It means the Slash Command has not been created, saved, installed, or
  reinstalled into the active Slack workspace.

Server check:

- Unsigned POST to `https://dd.cafedecafe.co.kr/slack/commands` returned:
  `{"detail":"Missing Slack signature headers."}`
- This confirms the public endpoint is reachable and the route exists; Slack
  still needs to register the command in the app configuration.

Recommended fix:

- Slack App -> `Slash Commands` -> `Create New Command`
- Command: `/kyulai`
- Request URL: `https://dd.cafedecafe.co.kr/slack/commands`
- Save
- Then go to `Install App` / `OAuth & Permissions` and reinstall the app to the
  workspace if Slack asks.
- Restart or refresh Slack if autocomplete does not show `/kyulai`.

## 2026-05-08 DD/Injection Service Restart

User asked whether both public app servers were down and requested restart if
needed.

Initial status:

- DD local server on `127.0.0.1:8000` was down.
- Injection local server on `:8010` was alive, but it was still an older
  process returning a redirect from `/` to `/simple-injection/index.ko.html`.
- Cloudflare tunnel metrics port `127.0.0.1:20241` was down, so both public
  hostnames returned Cloudflare 530 before restart.

Restart actions:

- Restarted DD API/UI on `127.0.0.1:8000` with Slack signing verification
  enabled through process environment only.
- Restarted named Cloudflare tunnel from
  `infrastructure/cloudflare/kclab-composite-ai.yml`.
- Stopped the stale Injection process on `:8010`.
- Restarted Injection API/UI from `/Users/danlee/KyulAI_codex` on
  `127.0.0.1:8010`.

Verification:

- `https://dd.cafedecafe.co.kr/health` returns `{"status":"ok"}`.
- `https://dd.cafedecafe.co.kr/` returns HTTP 200 through Cloudflare.
- `https://injection.cafedecafe.co.kr/` now returns HTTP 200 and serves the
  English Simple Injection page by default.
- `https://injection.cafedecafe.co.kr/api/v1/simple-injection/models` returns
  both `sprue_classical` and `sprue_goint` as available.

Current expected local listeners:

- DD: `127.0.0.1:8000`
- Injection: `127.0.0.1:8010`
- Cloudflare tunnel metrics: `127.0.0.1:20241`

## 2026-05-12 DD Public Server Restart

User reported `dd.cafedecafe.co.kr` appeared to be stopped and asked to keep
both running apps online.

Diagnosis:

- DD local server on `127.0.0.1:8000` was down.
- Injection local server on `:8010` was still running.
- Cloudflare tunnel metrics on `127.0.0.1:20241` was still running.
- Public DD health initially returned Cloudflare HTTP 502 because the tunnel
  could not reach the local DD origin.
- Public Injection health returned HTTP 200.

Action:

- Restarted DD API/UI on `127.0.0.1:8000` with Slack signing verification
  enabled through process environment only.
- Left the existing Injection server and Cloudflare tunnel running.

Verification:

- Local DD `http://127.0.0.1:8000/health` returns `{"status":"ok"}`.
- Local Injection `http://127.0.0.1:8010/health` returns `{"status":"ok"}`.
- Public DD `https://dd.cafedecafe.co.kr/health` returns HTTP 200.
- Public Injection `https://injection.cafedecafe.co.kr/health` returns HTTP
  200.

Current listeners after restart:

- DD: PID `95653` on `127.0.0.1:8000`
- Injection: PID `85809` on `:8010`
- Cloudflare tunnel: PID `25540` on `127.0.0.1:20241`

## 2026-05-12 DD New Case3 Data 201-300

User provided 100 new DD samples at:

- `/Users/danlee/KyulAI_codex/data/datasets/DD_new/201-250`
- `/Users/danlee/KyulAI_codex/data/datasets/DD_new/251-300`

All samples are Case3:

`[[±theta1]/[±theta2]/[∓theta2]/[∓theta2]]2`

Work completed:

- Added `scripts/dd_ingest_case3_new_batches.py`.
- Checked sibling folder labels `1`, `2`, `3` against the current CSV
  metadata+curve classifier.
- Updated each new batch `transition_load.csv` with:
  `Global_Test_ID`, final `type`, `original_type`, model prediction,
  probabilities, confidence, data quality, and review note.
- Created the new active curated dataset:
  `/Users/danlee/KyulAI_codex/data/datasets/DD_curated_csv_v2`
- Preserved the previous 400-sample dataset:
  `/Users/danlee/KyulAI_codex/data/datasets/DD_curated_csv_v1`

New-data review result:

- Original sibling counts: Type1=40, Type2=51, Type3=9.
- Model prediction counts: Type1=34, Type2=57, Type3=9.
- Final curated counts: Type1=34, Type2=57, Type3=9.
- Six labels changed from Type1 to Type2:
  `Test_241`, `Test_266`, `Test_272`, `Test_291`, `Test_293`, `Test_295`.
- Review files:
  - `/Users/danlee/KyulAI_codex/data/datasets/DD_new/case3_201_300_classification_review.md`
  - `/Users/danlee/KyulAI_codex/data/datasets/DD_new/case3_201_300_classification_review.csv`

Current v2 label counts:

- Case3: Type1=96, Type2=175, Type3=29, total=300.
- Case4: Type1=64, Type2=116, Type3=20, total=200.
- Total: Type1=160, Type2=291, Type3=49, total=500.

Models retrained from scratch on `DD_curated_csv_v2`:

- `models/dd_laminate_csv_meta_v1`: best model `random_forest`,
  sample CV accuracy 0.9960, macro F1 0.9967.
- `models/dd_laminate_theta_v1`: best sample model
  `hist_gradient_boosting`, sample CV accuracy 0.9640, macro F1 0.9579.
- `models/dd_laminate_response_surrogate_v1`: grouped CV accuracy 0.9380,
  macro F1 0.9378, Pt MAE 261.26.
- `models/dd_laminate_theta_goint_grouped_v1`: grouped CV accuracy 0.8975,
  macro F1 0.8901.
- `models/dd_laminate_response_goint_v1`: grouped CV accuracy 0.9460,
  macro F1 0.9472, Pt MAE 533.09.
- `models/dd_laminate_deep_sequence_grouped_v1`: grouped CV accuracy 0.9739,
  macro F1 0.9703.

Practical policy for future new DD data:

- While the dataset is still in the hundreds or low thousands, prefer full
  retraining from the curated dataset instead of incremental learning.
- Current sklearn tree/boosting pipelines and torch models are being trained
  from scratch for reproducibility and to avoid reinforcing old model mistakes.
- Incremental/fine-tune workflows can become useful later when the dataset is
  much larger and we have a stable held-out test set.

Runtime verification after retraining:

- Restarted DD server so model labels and files are reflected in the API.
- Current DD listener after restart: PID `10943` on `127.0.0.1:8000`.
- Injection remains running: PID `85809` on `:8010`.
- Cloudflare tunnel remains running: PID `25540` on `127.0.0.1:20241`.
- `https://dd.cafedecafe.co.kr/health` and
  `https://injection.cafedecafe.co.kr/health` both returned `{"status":"ok"}`.
- Local theta and curve API smoke tests returned Type2 for new reviewed sample
  `Case3/Test_241`.

## 2026-05-12 DD UI Response-First Simplification

User observed that `Theta + case` and `Response estimate` use essentially the
same inputs (`theta1`, `theta2`, `case`), while `Response estimate` returns more
useful outputs. Decision: keep theta-only models as backend/research baselines,
but remove the standalone theta-only tab from the user-facing UI.

UI changes:

- English title changed to `DD Laminate Response Predictor`.
- Korean title changed to `DD 적층 응답 예측기`.
- Default visible tab is now `Response estimate` / `응답 예측`.
- Top-level tabs are now only:
  - `Response estimate`
  - `Curve CSV`
- Removed the `Theta + case` / `θ + Case` tab and visible theta-only form.
- Kept backend theta endpoints and model files unchanged for research use.
- Updated cache-busting asset version to `20260512-response-first`.

Runtime verification:

- Restarted DD server after UI changes; latest DD listener PID is `15368` on
  `127.0.0.1:8000`.
- Browser verification confirmed:
  - `Response estimate` is present.
  - `Curve CSV` is present.
  - `Theta + case` tab is absent.
  - `theta-form` is absent from the rendered page.
- `Curve CSV` tab click shows the post-simulation classification form and CSV
  preview area.

## 2026-05-12 DD UI Naming: Laminate Forecast

User wanted a more polished name than `Response estimate`. Adopted
`Laminate Forecast`.

UI/API label changes:

- English page title: `DD Laminate Forecast`.
- English main tab: `Laminate Forecast`.
- English form title: `Pre-Abaqus Laminate Forecast`.
- English submit button: `Run Forecast`.
- Response model labels now show:
  - `Laminate Forecast - ExtraTrees + PCA + CLT`
  - `Laminate Forecast - GointMLP NN + CLT`
- Korean page title/tab wording changed to `DD 적층 예측` / `적층 예측`.
- Cache-busting asset version updated to `20260512-laminate-forecast`.

Verification:

- `node --check src/frontend/dd-laminate/app.js` passed.
- `PYTHONPYCACHEPREFIX=/tmp/kyulai_pycache .venv/bin/python -m py_compile
  src/backend/api/v1/dd_laminate.py` passed.
- Restarted DD server; current DD listener PID is `19384` on
  `127.0.0.1:8000`.
- Browser verification confirmed `Laminate Forecast` is present and old
  `Response estimate` / `Estimated Response` wording is absent on the main
  English page.

## 2026-05-12 Tunnel/Injection Restart

User reported the server went down again.

Diagnosis:

- DD local server was still running:
  PID `19384` on `127.0.0.1:8000`.
- Injection local server on `8010` was down.
- Cloudflare tunnel metrics on `127.0.0.1:20241` was down.
- Public DD and Injection health endpoints returned Cloudflare 530 / 1033,
  indicating the named tunnel was unavailable.

Action:

- Restarted Injection server:
  PID `24749` on `127.0.0.1:8010`.
- Restarted named Cloudflare tunnel:
  PID `24751`, metrics on `127.0.0.1:20241`.
- Left DD server running because it was already healthy.

Verification:

- Local DD `http://127.0.0.1:8000/health` returned `{"status":"ok"}`.
- Local Injection `http://127.0.0.1:8010/health` returned `{"status":"ok"}`.
- Public DD `https://dd.cafedecafe.co.kr/health` returned HTTP 200.
- Public Injection `https://injection.cafedecafe.co.kr/health` returned HTTP
  200.

Operational note:

- Recent outages are mostly process-lifetime issues, not application-code
  errors. A durable macOS LaunchAgent or supervisor script would be the next
  sensible step if public access should stay up without manual restarts.

## 2026-05-12 Windows Server Migration Preparation

User wants to move the DD/Injection public serving setup from the Mac to a
Windows server PC because keeping the Mac open is inconvenient.

Prepared files:

- `docs/windows-server-migration.md`: step-by-step migration guide.
- `requirements-serving.txt`: minimal runtime dependencies for serving DD and
  Injection without the full research/training stack.
- `.env.windows.example`: local secret/env template for Windows; copy to
  `.env.local`.
- `infrastructure/cloudflare/kclab-composite-ai.windows.example.yml`: Windows
  Cloudflare Tunnel config template.
- `scripts/windows/Setup-WindowsServing.ps1`: creates `.venv`, installs serving
  deps, installs PyTorch CPU wheel, verifies imports.
- `scripts/windows/Start-DD.ps1`: starts DD on `127.0.0.1:8000`.
- `scripts/windows/Start-Injection.ps1`: starts Injection on `127.0.0.1:8010`.
- `scripts/windows/Start-CloudflareTunnel.ps1`: starts the named Cloudflare
  tunnel from a Windows config path.
- `scripts/windows/Start-All.ps1`: launches DD, Injection, and Cloudflare into
  separate PowerShell processes with logs under `logs/`.
- `scripts/windows/Check-Health.ps1`: checks local and public health endpoints.
- `scripts/windows/Install-LogonTasks.ps1`: optional Windows Scheduled Tasks
  setup for starting the three services at user logon.
- `scripts/package_windows_bundle.py`: creates a portable zip including runtime
  code, selected model artifacts, selected datasets, docs, and Windows scripts.

Important migration notes:

- A plain Git clone may miss `data/datasets` because the repo ignores large data
  folders. Safest handoff is the portable zip:
  `python3 scripts/package_windows_bundle.py --output ~/Desktop/KyulAI_windows_server_bundle.zip`.
- The Cloudflare tunnel credential JSON is secret. Current tunnel ID is
  `02b4b689-84ef-4459-91cd-48c81ea549ae`; copy the corresponding JSON from
  the Mac `.cloudflared` folder to the Windows user `.cloudflared` folder and
  point the Windows YAML `credentials-file` at it.
- The Mac and Windows connector can run the same named tunnel at the same time
  during migration. After Windows is confirmed stable, stop the Mac tunnel.
- For normal prediction, `.env.local` can stay mostly empty. For Slack slash
  commands, set `SLACK_SIGNING_SECRET` in `.env.local`.

Validation done:

- `node --check src/frontend/dd-laminate/app.js` previously passed after UI
  changes.
- `PYTHONPYCACHEPREFIX=/tmp/kyulai_pycache .venv/bin/python -m py_compile
  scripts/package_windows_bundle.py scripts/dd_ingest_case3_new_batches.py
  src/backend/api/v1/dd_laminate.py` passed.

## 2026-05-12 Portable Bundle Consolidation

User asked to merge the necessary DD and Injection work into one portable package for moving to another computer. Created a consolidated zip on the Desktop:

- `/Users/danlee/Desktop/KyulAI_portable_server_20260512.zip`
- Size after verification: about 599 MB.
- Includes DD and Simple Injection backend/frontend/ML source, trained DD and Injection model artifacts, DD datasets (`DD`, `DD_curated_csv_v1`, `DD_curated_csv_v2`, `DD_new`), Simple Injection dataset, docs including this session memory, Cloudflare example config, and Windows setup/start scripts.
- Excludes `.git`, `.venv`, local secret files such as `.env.local`, logs, caches, and Cloudflare credential JSON. The credential JSON must be copied separately if the Windows PC will run the named Cloudflare Tunnel.

The package is intended as the safest handoff artifact because Git alone does not include ignored large data/model artifacts.

## 2026-05-12 DD Laminate Forecast Pt Label UI

Adjusted the Surrogate curve Pt marker label in `src/frontend/dd-laminate/app.js`:

- Replaced the small one-line `Pt <value>` canvas label with a larger two-line label: `Predicted Pt` plus the numeric value.
- Added a light callout box with more padding and a thin leader line from the Pt marker so the text is easier to read without sitting directly on the curve.
- Restarted the local DD frontend static server on `127.0.0.1:3000`; DD API health on `127.0.0.1:8000` was OK.
- `node --check src/frontend/dd-laminate/app.js` passed.

## 2026-05-12 DD Pt Label Cache Update

After the Pt callout label UI change, updated DD frontend script cache keys in both English and Korean pages:

- `src/frontend/dd-laminate/index.html` now loads `app.js?v=20260512-pt-label`.
- `src/frontend/dd-laminate/index.ko.html` now loads `app.js?v=20260512-pt-label`.

This makes browsers/Cloudflare request the updated `app.js` with the larger two-line `Predicted Pt` callout. `node --check src/frontend/dd-laminate/app.js` passed and DD API health was OK.

## 2026-05-15 Simple Injection Model Expansion

Current code remains separated by application:

- DD frontend: `src/frontend/dd-laminate`
- DD backend/API: `src/backend/dd_laminate_app.py`, `src/backend/api/v1/dd_laminate.py`
- DD ML source: `src/ml/dd_laminate`
- DD models: `models/dd_laminate*`
- Simple Injection frontend: `src/frontend/simple-injection`
- Simple Injection backend/API: `src/backend/simple_injection_app.py`, `src/backend/api/v1/simple_injection.py`
- Simple Injection ML source: `src/ml/simple_injection`
- Simple Injection models: `models/simple_injection_*`

Simple Injection Sprue Pressure now has three selectable model families:

- `sprue_classical`: RandomForest + PCA model in `models/simple_injection_sprue_pressure_v1`
- `sprue_goint`: GointMLP-style neural model in `models/simple_injection_sprue_goint_v1`
- `sprue_deeponet`: DeepONet operator model in `models/simple_injection_sprue_deeponet_v1`

Additional Sprue curve evaluation metrics were added in `src/ml/simple_injection/metrics.py`:

- shape correlation
- normalized AUC MAE
- pressure-time AUC MAE
- peak-position MAE
- rise-slope MAE

Weak physics-informed neural loss terms were added in `src/ml/simple_injection/physics.py` and wired into the neural training scripts:

- nonnegative pressure penalty
- pressure-curve oscillation suppression
- peak-timing soft constraint
- filling histogram ratio-sum penalty
- filling histogram nonnegative and min/avg/max consistency penalties

After physics-informed retraining:

- Sprue GointMLP improved to pressure RMSE about `2.4152 MPa`.
- Sprue DeepONet remained a research baseline with pressure RMSE about `4.3760 MPa`.
- Filling GointMLP improved to ratio RMSE about `2.1302%` and stats MAE about `1.9005 MPa`.

Simple Injection Filling Pressure now also has three model families:

- `filling_classical`: ExtraTrees histogram model in `models/simple_injection_filling_pressure_v1`
- `filling_goint`: GointMLP-style histogram model in `models/simple_injection_filling_pressure_goint_v1`
- `filling_deeponet`: DeepONet histogram model in `models/simple_injection_filling_pressure_deeponet_v1`

Latest Filling Pressure validation on 120 histogram samples:

- ExtraTrees: ratio RMSE `2.1807%`, ratio MAE `1.4338%`, stats MAE `1.4318 MPa`
- GointMLP: ratio RMSE `2.1302%`, ratio MAE `1.4425%`, stats MAE `1.9005 MPa`
- DeepONet histogram: ratio RMSE `2.2118%`, ratio MAE `1.4918%`, stats MAE `1.8827 MPa`

Frontend/API integration:

- The Simple Injection UI now exposes two model selectors: one for Sprue Pressure and one for Filling Pressure.
- A single prediction request includes both `model` and `filling_model`.
- Prediction output is presented as combined Sprue & Filling Pressure prediction while keeping Sprue curve and Filling distribution sections separate.
- Validation comparison titles now include the selected Sprue/Filling model labels.

Validation performed:

- `python -m py_compile` passed for updated Simple Injection backend/ML modules.
- `node --check src/frontend/simple-injection/app.js` passed.
- API `/models` returned all three Sprue models and all three Filling models.
- Combined prediction with `sprue_goint` + `filling_deeponet` returned a valid response.

## 2026-05-15 Simple Injection Filling Pressure G13-G17 Update

User added Filling Pressure data for `G13` through `G17` under
`data/datasets/Simple_Injection/Filling_Pressure`. Normalized the new file names
from Moldex-style spaced names such as `G13_P01_Filling Pressure.csv` and
`G13_P01_Filling Pressure.png` to the project convention:

- `G##_P##_Filling_Pressure.csv`
- `G##_P##_Filling_Pressure_chart.png`

After normalization, the Filling Pressure loader sees:

- 170 histogram CSV samples
- Geometry range represented: `G01` through `G17`
- Process combinations represented: `P01` through `P10`
- Training matrix shape: `(170, 23)`
- Target matrix shape: `(170, 14)`

Retrained all three Simple Injection Filling Pressure model families on the
170-sample dataset:

- `filling_classical` in `models/simple_injection_filling_pressure_v1`
  - Best model: RandomForest
  - Ratio RMSE: `1.9880%`
  - Ratio MAE: `1.2632%`
  - Stats MAE: `1.4442 MPa`
- `filling_goint` in `models/simple_injection_filling_pressure_goint_v1`
  - Ratio RMSE: `2.0611%`
  - Ratio MAE: `1.3026%`
  - Stats MAE: `1.3811 MPa`
- `filling_deeponet` in `models/simple_injection_filling_pressure_deeponet_v1`
  - Ratio RMSE: `2.0662%`
  - Ratio MAE: `1.2826%`
  - Stats MAE: `1.2080 MPa`

Verification performed:

- Local prediction for `G13_P01` succeeded with all three filling models.
- Predicted histogram volume-ratio sums are normalized to `100%` for all three
  models.
- Simple Injection API service was restarted with launchd.
- API `/api/v1/simple-injection/models` returned all Sprue and Filling models as
  available.

## 2026-05-15 Simple Injection Filling Pressure G18-G23 Update

User added Filling Pressure data for `G18` through `G23` under
`data/datasets/Simple_Injection/Filling_Pressure`. Normalized 120 new spaced
Moldex export names to the project convention:

- `G##_P##_Filling_Pressure.csv`
- `G##_P##_Filling_Pressure_chart.png`

After normalization, the Filling Pressure loader sees:

- 230 histogram CSV samples
- Geometry range represented: `G01` through `G23`
- Process combinations represented: `P01` through `P10`
- Training matrix shape: `(230, 23)`
- Target matrix shape: `(230, 14)`

Retrained all three Simple Injection Filling Pressure model families on the
230-sample dataset:

- `filling_classical` in `models/simple_injection_filling_pressure_v1`
  - Best model: ExtraTrees
  - Ratio RMSE: `2.2550%`
  - Ratio MAE: `1.3512%`
  - Stats MAE: `0.8388 MPa`
- `filling_goint` in `models/simple_injection_filling_pressure_goint_v1`
  - Ratio RMSE: `2.3757%`
  - Ratio MAE: `1.3645%`
  - Stats MAE: `1.1649 MPa`
- `filling_deeponet` in `models/simple_injection_filling_pressure_deeponet_v1`
  - Ratio RMSE: `2.1876%`
  - Ratio MAE: `1.2488%`
  - Stats MAE: `0.8568 MPa`

Verification performed:

- Local prediction for `G23_P10` succeeded with all three filling models.
- Predicted histogram volume-ratio sums are normalized to `100%` for all three
  models.
- Simple Injection API service was restarted with launchd.
- API `/api/v1/simple-injection/models` returned all Sprue and Filling models as
  available.

## 2026-05-15 Simple Injection Filling Pressure G24-G26 Update

User added Filling Pressure data for `G24` through `G26` under
`data/datasets/Simple_Injection/Filling_Pressure`. Normalized 60 new spaced
Moldex export names to the project convention:

- `G##_P##_Filling_Pressure.csv`
- `G##_P##_Filling_Pressure_chart.png`

After normalization, the Filling Pressure loader sees:

- 260 histogram CSV samples
- Geometry range represented: `G01` through `G26`
- Process combinations represented: `P01` through `P10`
- Training matrix shape: `(260, 23)`
- Target matrix shape: `(260, 14)`

Retrained all three Simple Injection Filling Pressure model families on the
260-sample dataset:

- `filling_classical` in `models/simple_injection_filling_pressure_v1`
  - Best model: RandomForest
  - Ratio RMSE: `1.8874%`
  - Ratio MAE: `1.2434%`
  - Stats MAE: `0.9312 MPa`
- `filling_goint` in `models/simple_injection_filling_pressure_goint_v1`
  - Ratio RMSE: `2.0084%`
  - Ratio MAE: `1.2119%`
  - Stats MAE: `0.9572 MPa`
- `filling_deeponet` in `models/simple_injection_filling_pressure_deeponet_v1`
  - Ratio RMSE: `1.8568%`
  - Ratio MAE: `1.1411%`
  - Stats MAE: `0.8480 MPa`

Verification performed:

- Local prediction for `G26_P10` succeeded with all three filling models.
- Predicted histogram volume-ratio sums are normalized to `100%` for all three
  models.
- Simple Injection API service was restarted with launchd.
- API `/api/v1/simple-injection/models` returned all Sprue and Filling models as
  available.

## 2026-05-15 Simple Injection Filling Pressure G27-G30 Complete Dataset Update

User added the remaining Filling Pressure data for `G27` through `G30` under
`data/datasets/Simple_Injection/Filling_Pressure`. Normalized 80 new spaced
Moldex export names to the project convention:

- `G##_P##_Filling_Pressure.csv`
- `G##_P##_Filling_Pressure_chart.png`

After normalization, the Filling Pressure loader sees the complete planned DOE
set:

- 300 histogram CSV samples
- Geometry range represented: `G01` through `G30`
- Process combinations represented: `P01` through `P10`
- Training matrix shape: `(300, 23)`
- Target matrix shape: `(300, 14)`

Retrained all three Simple Injection Filling Pressure model families on the
300-sample complete dataset:

- `filling_classical` in `models/simple_injection_filling_pressure_v1`
  - Best model: HistGradientBoosting
  - Ratio RMSE: `1.9283%`
  - Ratio MAE: `1.2498%`
  - Stats MAE: `0.8487 MPa`
- `filling_goint` in `models/simple_injection_filling_pressure_goint_v1`
  - Ratio RMSE: `1.8865%`
  - Ratio MAE: `1.1528%`
  - Stats MAE: `0.9562 MPa`
- `filling_deeponet` in `models/simple_injection_filling_pressure_deeponet_v1`
  - Ratio RMSE: `1.7776%`
  - Ratio MAE: `1.0442%`
  - Stats MAE: `0.7426 MPa`

Verification performed:

- Local prediction for `G30_P10` succeeded with all three filling models.
- Predicted histogram volume-ratio sums are normalized to `100%` for all three
  models.
- Simple Injection API service was restarted with launchd.
- API `/api/v1/simple-injection/models` returned all Sprue and Filling models as
  available.

## 2026-05-15 Simple Injection Supplemental V02/V03 DOE Proposal

Created supplemental DOE proposal files under
`data/datasets/Simple_Injection/DOE` to improve the current validation weak
spots without contaminating validation#2/#3 hold-out conditions:

- `supplemental_v02_v03_geometry_doe.csv`
- `supplemental_v02_v03_process_doe.csv`
- `supplemental_v02_v03_case_matrix_60.csv`

Design:

- V02-like long/thin/high-pressure region: 4 new geometries (`G31`-`G34`) x 5
  new processes (`P11`-`P15`) = 20 cases.
- V03-like short/thick/low-pressure region: 8 new geometries (`G35`-`G42`) x 5
  new processes (`P16`-`P20`) = 40 cases.
- Total: 60 proposed supplemental CAE runs.

Validation performed:

- Geometry rows: 12
- Process rows: 10
- Case matrix rows: 60
- D/R consistency checks passed.
- Hole diameter is smaller than the controlling L/W dimension for every
  geometry.
- No exact duplicate of validation#2 or validation#3 was included.

## 2026-05-21 Simple Injection Validation_Set V02 Training Update

User added `data/datasets/Simple_Injection/Validation_Set/V02` with 20 CAE
results for the previously proposed V02 long-flow/thin-wall/high-pressure
supplemental DOE. Folder mapping is:

- `Validation_Set/V02/v02FAM_G01..G04` -> supplemental `G31..G34`
- `P01..P05` folders -> supplemental `P11..P15`

Updated `src/ml/simple_injection/data.py` so training loaders include
`Validation_Set` data without adding `Prediction/validation#2` itself into
training. The loader now maps raw validation-set folders to the supplemental
case matrix and reads both:

- `Packing-Sprue Pressure.csv`
- `Filling_Pressure.csv` or spaced Moldex export names

After parser update:

- Sprue records: 320
- Filling records: 320
- Added samples: `G31_P11` through `G34_P15`

Retrained all Simple Injection Sprue and Filling model families:

Sprue Pressure, 320 samples:

- `sprue_classical`: best ExtraTrees, pressure curve RMSE `2.2489 MPa`,
  max pressure MAE `0.0784 MPa`
- `sprue_goint`: pressure curve RMSE `3.2866 MPa`, max pressure MAE
  `0.8690 MPa`
- `sprue_deeponet`: pressure curve RMSE `5.1748 MPa`, max pressure MAE
  `0.9146 MPa`

Filling Pressure, 320 samples:

- `filling_classical`: best RandomForest, ratio RMSE `2.0982%`, ratio MAE
  `1.3432%`, stats MAE `1.1375 MPa`
- `filling_goint`: ratio RMSE `2.1756%`, ratio MAE `1.1575%`, stats MAE
  `1.2753 MPa`
- `filling_deeponet`: ratio RMSE `2.0930%`, ratio MAE `1.0910%`, stats MAE
  `0.8891 MPa`

Hold-out `Prediction/validation#2` after V02 supplemental training:

- Sprue max pressure:
  - Classical: `85.47 MPa` vs actual `85.00 MPa` (`+0.55%`)
  - GointMLP: `86.28 MPa` (`+1.51%`)
  - DeepONet: `87.78 MPa` (`+3.27%`)
- Sprue curve RMSE:
  - Classical: `6.60 MPa`
  - GointMLP: `7.02 MPa`
  - DeepONet: `4.67 MPa`
- Filling max pressure:
  - Classical: `48.13 MPa` vs actual `54.44 MPa` (`-11.59%`)
  - GointMLP: `49.10 MPa` (`-9.81%`)
  - DeepONet: `51.88 MPa` (`-4.71%`)
- Filling distribution ratio RMSE:
  - Classical: `0.98%`
  - GointMLP: `0.81%`
  - DeepONet: `0.51%`

Also updated API labels for classical models to generic names because the best
classical algorithm can change after each retraining:

- `Sprue pressure - Classical ML + PCA`
- `Filling pressure - Classical ML histogram`

Validation performed:

- `py_compile` passed for `src/ml/simple_injection/data.py` and
  `src/backend/api/v1/simple_injection.py`.
- Simple Injection API service was restarted with launchd.
- API `/api/v1/simple-injection/models` returned all Sprue and Filling models as
  available.

## 2026-05-21 Simple Injection Validation_Set V02 Sprue Exclusion Correction

User clarified that supplemental validation-set Sprue results should not be
used in training; only Filling Pressure histogram data should be added, which
matches the earlier workflow.

Corrections made:

- Normalized `Validation_Set/V02` Filling filenames to mapped supplemental IDs:
  - `G31_P11_Filling_Pressure.csv`
  - `G31_P11_Filling_Pressure_chart.png`
  - through `G34_P15_Filling_Pressure.csv/chart.png`
- `Packing-Sprue Pressure.csv` files remain in the raw data folders but are now
  ignored by the training loader.
- Updated `src/ml/simple_injection/data.py` so `load_records()` uses only the
  original `Result` Sprue data. `Validation_Set` is only included by the Filling
  loader.

Current intended training data split:

- Sprue Pressure: 300 records, `G01_P01` through `G30_P10`; no `G31+` samples.
- Filling Pressure: 320 records, original 300 plus V02 supplemental
  `G31_P11` through `G34_P15`.

Retrained Sprue models back on the original 300-result dataset:

- `sprue_classical`: RandomForest, pressure curve RMSE `1.9396 MPa`, max
  pressure MAE `0.0583 MPa`
- `sprue_goint`: pressure curve RMSE `2.7063 MPa`, max pressure MAE
  `0.6989 MPa`
- `sprue_deeponet`: pressure curve RMSE `4.6378 MPa`, max pressure MAE
  `0.5192 MPa`

Filling models remain the 320-sample histogram-only update:

- `filling_classical`: RandomForest, ratio RMSE `2.0982%`, stats MAE
  `1.1375 MPa`
- `filling_goint`: ratio RMSE `2.1756%`, stats MAE `1.2753 MPa`
- `filling_deeponet`: ratio RMSE `2.0930%`, stats MAE `0.8891 MPa`

Hold-out checks after correction:

- `validation#2` Sprue is back to the original 300-sample behavior; DeepONet max
  pressure is `84.86 MPa` vs actual `85.00 MPa` (`-0.16%`), curve RMSE
  `19.24 MPa`.
- `validation#2` Filling still benefits from the V02 histogram supplement;
  DeepONet max pressure is `51.88 MPa` vs actual `54.44 MPa` (`-4.71%`),
  distribution ratio RMSE `0.51%`.
- `validation#3` Filling remains weak until V03 histogram supplement arrives;
  best max-pressure error is still around `+27%` to `+32%`.

Validation performed:

- `py_compile` passed for `src/ml/simple_injection/data.py`.
- Simple Injection API service was restarted with launchd.
- API `/api/v1/simple-injection/models` returned all Sprue and Filling models as
  available.

## 2026-05-21 Simple Injection Validation_Set V02 Both-Target Update

User clarified that `Validation_Set/V02` Sprue results should be used for
Sprue-model training, while Filling results should be used for Filling-model
training. The concern was only about not mixing Sprue outputs into the Filling
target.

Applied intended state:

- Sprue Pressure uses original 300 Sprue runs plus V02 Sprue 20 runs:
  `G01_P01` through `G34_P15`, 320 records.
- Filling Pressure uses original 300 Filling histograms plus V02 Filling 20
  histograms: `G01_P01` through `G34_P15`, 320 records.
- No cross-target mixing: Sprue models use `Packing-Sprue Pressure.csv`; Filling
  models use `*_Filling_Pressure.csv` histogram exports.

Retrained Sprue models on 320 records:

- `sprue_classical`: ExtraTrees, pressure curve RMSE `2.2489 MPa`, max pressure
  MAE `0.0784 MPa`
- `sprue_goint`: pressure curve RMSE `3.2866 MPa`, max pressure MAE
  `0.8690 MPa`
- `sprue_deeponet`: pressure curve RMSE `5.1748 MPa`, max pressure MAE
  `0.9146 MPa`

Filling models remain the 320-histogram update:

- `filling_classical`: RandomForest, ratio RMSE `2.0982%`, stats MAE
  `1.1375 MPa`
- `filling_goint`: ratio RMSE `2.1756%`, stats MAE `1.2753 MPa`
- `filling_deeponet`: ratio RMSE `2.0930%`, stats MAE `0.8891 MPa`

Hold-out checks after applying both-target V02 update:

- `validation#2` Sprue:
  - Classical max `85.47 MPa` vs actual `85.00 MPa` (`+0.55%`), curve RMSE
    `6.60 MPa`
  - GointMLP max `86.28 MPa` (`+1.51%`), curve RMSE `7.02 MPa`
  - DeepONet max `87.78 MPa` (`+3.27%`), curve RMSE `4.67 MPa`
- `validation#2` Filling:
  - Classical max `48.13 MPa` vs actual `54.44 MPa` (`-11.59%`), ratio RMSE
    `0.98%`
  - GointMLP max `49.10 MPa` (`-9.81%`), ratio RMSE `0.81%`
  - DeepONet max `51.88 MPa` (`-4.71%`), ratio RMSE `0.51%`
- `validation#3` remains mostly unchanged and still needs the planned V03
  supplemental data, especially for Filling.

Validation performed:

- `py_compile` passed for `src/ml/simple_injection/data.py`.
- Simple Injection API service was restarted with launchd.
- API `/api/v1/simple-injection/models` returned all Sprue and Filling models as
  available.

## 2026-05-21 DD Laminate Page Wording Cleanup

User asked to remove the word `Abaqus` from the DD Laminate page and present it simply as a prediction program. Updated DD-facing text:

- `src/frontend/dd-laminate/index.html`: intro copy and response form title now say laminate prediction/program wording without tool-specific naming.
- `src/frontend/dd-laminate/index.ko.html`: Korean intro and response form title changed to general prediction-program wording.
- `src/frontend/dd-laminate/app.js`: result-note translation keys/messages changed from pre-tool wording to general surrogate prediction wording.
- `src/backend/api/v1/dd_laminate.py`: model descriptions and response notes changed to remove tool-specific wording.
- `src/frontend/dd-laminate/README.md` and `assets/dd-ply-stack.svg` also had DD-facing wording cleaned.
- Updated `app.js` cache key to `20260521-prediction-program` in both English and Korean pages.

Validation:

- `rg -n "Abaqus|ABAQUS|abaqus" src/frontend/dd-laminate src/backend/api/v1/dd_laminate.py` returned no matches.
- `node --check src/frontend/dd-laminate/app.js` passed.
- `PYTHONPYCACHEPREFIX=/tmp/kyulai_pycache python3 -m py_compile src/backend/api/v1/dd_laminate.py` passed.
- DD API health was OK; response prediction notes now say `Laminate Forecast is a surrogate prediction; validate promising candidates with simulation.`

## 2026-05-21 Remove KCLab Text From DD and Injection

User asked to remove `KCLAB/KCLab` text from both DD Laminate and Simple Injection pages. Updated front-end-facing files:

- `src/frontend/dd-laminate/index.html`: title changed to `DD Laminate Forecast`; eyebrow changed to `Composite AI`.
- `src/frontend/dd-laminate/index.ko.html`: title changed to `DD 적층 예측`; eyebrow changed to `Composite AI`.
- `src/frontend/simple-injection/index.html`: title changed to `Simple Injection Pressure Predictor`; eyebrow changed to `Injection AI`; app.js cache key updated to `20260521-brand-cleanup`.
- `src/frontend/simple-injection/index.ko.html`: title changed to `Simple Injection Pressure Predictor`; eyebrow changed to `Injection AI`; app.js cache key updated to `20260521-brand-cleanup-ko`.
- `src/frontend/simple-injection/app.js`: exported report canvas title changed from `KCLab Injection AI` to `Injection AI`.

Validation:

- `rg -n "KCLAB|KCLab|KcLab|kclab|KC Lab" src/frontend/dd-laminate src/frontend/simple-injection` returned no matches.
- `node --check src/frontend/dd-laminate/app.js` passed.
- `node --check src/frontend/simple-injection/app.js` passed.

## 2026-05-21 DD Title Expanded To Double-Double

User asked to change the DD Laminate page wording from the abbreviation `DD` to the fuller `Double-Double` wording. Updated:

- `src/frontend/dd-laminate/index.html`: title, H1, and intro copy now use `Double-Double Laminate Forecast` / `Double-Double laminate`.
- `src/frontend/dd-laminate/index.ko.html`: title, H1, and intro copy now use `Double-Double 적층 예측` / `Double-Double 적층`.

Verified the updated page text with `rg` and direct file inspection.

## 2026-05-21 Double-Double Report Export

User asked to add an Injection-style report feature to the Double-Double page. Implemented DD Laminate report export:

- `src/frontend/dd-laminate/index.html` and `index.ko.html`: added `PNG` and `PDF` report buttons to the prediction result header.
- `src/frontend/dd-laminate/styles.css`: added result action layout styling, including mobile stacking.
- `src/frontend/dd-laminate/app.js`: added report-canvas generation, PNG download, and PDF print-window export. The report includes title, created time, predicted Type, confidence, Predicted Pt, curve point count, theta/case/input summary, model, Type probabilities, surrogate curve image when available, max displacement/force, and notes.
- Updated DD HTML cache keys for `styles.css` and `app.js` to `20260521-report-export`.

Validation:

- `node --check src/frontend/dd-laminate/app.js` passed.
- Local DD frontend served the new buttons and cache key at `127.0.0.1:3000`.
- Local DD API health at `127.0.0.1:8000/health` returned OK.

## 2026-05-21 Double-Double Report Download Fix

User reported the Double-Double report download did not appear to work. Updated DD report export code:

- `src/frontend/dd-laminate/app.js`: changed PNG export from direct `canvas.toDataURL()` + detached link click to `canvas.toBlob()` + `URL.createObjectURL()` + temporary DOM-attached download link. This is more reliable across browsers/security settings for larger canvas images.
- Added export failure messages and try/catch handling for PNG and PDF export paths.
- `src/frontend/dd-laminate/index.html` and `index.ko.html`: bumped app.js cache key to `20260521-report-download-fix`.

Validation:

- `node --check src/frontend/dd-laminate/app.js` passed.
- Local DD frontend served `app.js?v=20260521-report-download-fix` and the updated `toBlob/createObjectURL` code.

## 2026-05-27 Simple Injection Training_1/Training_2 Consolidation

User reorganized Simple Injection data under `data/datasets/Simple_Injection`:

- `Training_1/Filling_Pressure`: original 300 filling histogram cases.
- `Training_1/Sprue_Pressure`: original 30 geometry files, each containing P01-P10 sprue curves.
- `Training_2/V02` and `Training_2/V03`: supplemental V02/V03 range training data with one folder per G/P case.

Cleanup and loader updates:

- Renamed `Training_2/Fiiilng_Pressure_V02_V03_Set/V02` and `V03` into canonical `Training_2/V02` and `Training_2/V03`.
- Renamed Training_2 folders/files to canonical ids:
  - V02: `G31-G34`, `P11-P15`.
  - V03: `G35-G42`, `P16-P20`.
  - Files now use `G##_P##_Filling_Pressure.csv`, `G##_P##_Filling_Pressure_chart.png`, and `G##_P##_Sprue_Pressure.csv`.
- Renamed Training_1 sprue files from `SPRUE PRESSURE` to `SPRUE_PRESSURE`.
- Updated `src/ml/simple_injection/data.py` so default training loads:
  - Sprue: `Training_1/Sprue_Pressure` plus `Training_2`.
  - Filling: `Training_1/Filling_Pressure` plus `Training_2`.
  - Old `Validation_Set` fallback is only used when `Training_2` is absent.
- Updated Simple Injection CLI prediction helpers so `--geometry-id G31-G42` and
  `--process-id P11-P20` resolve through supplemental DOE files as well.

Verification:

- Loader sees 360 Sprue records and 360 Filling records from `G01_P01` through `G42_P20`.
- `find Training_1 Training_2 -type f -name '* *'` returned 0 after cleanup.
- Simple Injection API was restarted and `/health` returned OK.

Retrained all Simple Injection models on the consolidated 360 cases:

- Sprue Classical: curve RMSE 2.555 MPa, max pressure MAE 0.065 MPa, shape corr mean 0.996.
- Sprue GointMLP: curve RMSE 2.917 MPa, max pressure MAE 0.714 MPa, shape corr mean 0.994.
- Sprue DeepONet: curve RMSE 5.421 MPa, max pressure MAE 0.901 MPa, shape corr mean 0.979.
- Filling Classical: stats MAE 0.757 MPa, volume-ratio RMSE 2.071 percentage points.
- Filling GointMLP: stats MAE 1.112 MPa, volume-ratio RMSE 2.147 percentage points.
- Filling DeepONet: stats MAE 0.807 MPa, volume-ratio RMSE 2.071 percentage points.

Validation_1 manual checks after retraining:

- V01 still shows Filling max overprediction for all models; DeepONet is least high among the three.
- V02 Filling Classical is strong on max and ratio, but Sprue max remains underpredicted.
- V03 improved materially after adding V03 Training_2 data; Sprue max error is best with DeepONet/GointMLP and Filling max is close for all models.

Follow-up cleanup on the same day:

- Collapsed the standard training dataset into one canonical folder:
  `data/datasets/Simple_Injection/Training`.
- `Training/Filling_Pressure` now contains all 360 filling cases.
- `Training/Sprue_Pressure` now contains all sprue data. G01-G30 remain in
  geometry-level P01-P10 combined Moldex3D CSV files; G31-G42 use case-level
  CSV files.
- Removed the now-empty `Training_1` and `Training_2` folders after moving the
  data.
- Updated `src/ml/simple_injection/data.py` to prefer `Training` and still
  parse both combined and one-case Sprue CSV formats.
- Added dataset documentation at both
  `data/datasets/Simple_Injection/DATASET.md` for local dataset browsing and
  `docs/simple-injection-dataset.md` for git-tracked project documentation,
  including original DOE history, why V02/V03 were added, naming rules,
  validation usage, and future data-add rules.
- Verified loader counts remain 360 Sprue records and 360 Filling records.

Additional normalization:

- Chose process-folder structure as the canonical dataset layout.
- Moved G01-G30 Filling files into `Training/Filling_Pressure/G##/P##/`.
- Split the original G01-G30 Sprue combined P01-P10 CSV files into 300
  case-level files under `Training/Sprue_Pressure/G##/P##/`.
- Moved the 30 original combined Sprue exports into
  `Training/Source_Exports/Sprue_Pressure_Combined` so the raw Moldex3D export
  remains available without being mixed into the active training folder.
- Updated dataset documentation to show that both Filling and Sprue now use
  `G##/P##/file` layout for active training files.

## 2026-05-27 Simple Injection Next DOE Proposal

User asked for concrete DOE combinations to run next, based on current weak
regions. Created 55 supplemental candidate cases:

- `V01_filling_refine`: `G43-G47` x `P21-P25` = 25 cases.
  Purpose: reduce V01 Filling Pressure max overprediction.
- `V02_sprue_refine`: `G48-G51` x `P26-P30` = 20 cases.
  Purpose: improve long-flow/thin/high-pressure Sprue Pressure prediction.
- `bridge_mid_range`: `G52-G53` x `P31-P35` = 10 cases.
  Purpose: connect original DOE and supplemental V02/V03 regions.

Created files:

- `data/datasets/Simple_Injection/DOE/supplemental_v01_v02_bridge_geometry_doe.csv`
- `data/datasets/Simple_Injection/DOE/supplemental_v01_v02_bridge_process_doe.csv`
- `data/datasets/Simple_Injection/DOE/supplemental_v01_v02_bridge_case_matrix_55.csv`
- `docs/simple-injection-next-doe-20260527.md`

Validation:

- DOE loader now sees 53 geometry IDs and 35 process IDs.
- Training result loader still sees 360 Sprue and 360 Filling records because
  the proposed G43-G53/P21-P35 result files have not been generated yet.

## 2026-05-29 New Double-Double Dataset Audit

User reported a major DD data update under `data/datasets/Double-Double` and asked to first inspect folders `2`, `3`, and `4` before creating new training. Audit results:

- New dataset is not the same as previous `DD_curated_csv_v2`: new Case3/Case4 share `Test_001`-`Test_300` IDs but theta pairs and CSV curves differ from the old curated training set. Unordered theta-pair overlap was only 4/300 for new folder 3 vs old Case3 and 2/300 for new folder 4 vs old Case4.
- New folders 2, 3, 4 all share the same 300 theta pairs.
- Use `transition load P1.csv` for P1 label training; `transition load.csv` has same theta values but different Pt values for every row.
- Case/folder 2: 300 transition rows, 300 curve CSV IDs, 300 P1 labels. Type counts: 1=108, 2=145, 3=47.
- Case/folder 3: 300 transition rows and 300 curve CSV IDs, but only 248 P1 labels. Type counts: 1=97, 2=111, 3=40. Missing labels for 52 tests: Test_170-193 except 194, Test_195, Test_196, Test_199-214 except 215, Test_216-224, and Test_286. Full list written to `docs/dd_double_double_data_audit_2026-05-29.md`.
- Case/folder 4: 300 transition rows, 300 curve CSV IDs, 300 P1 labels. Type counts: 1=96, 2=164, 3=40.
- Existing training/backend code assumes only Case3/Case4 in several places; Case2 requires a new curated dataset and code updates for 3-case encoding.

Created audit document: `docs/dd_double_double_data_audit_2026-05-29.md`. Recommended not to overwrite existing models. Next step is to either request/fill the 52 missing Case3 labels or train a temporary model on 848 labeled samples.

## 2026-05-29 Case 3 P1 Root Images Classified

User asked to re-check `data/datasets/Double-Double/3/p1` because `206` and `286` were left outside Type folders. Findings and actions:

- Most previously missing Case 3 labels had been added. Only two PNGs remained directly under `data/datasets/Double-Double/3/p1`: `plot_Test_206_P1.png` and `plot_Test_286_P1.png`.
- Visual + CSV/model check:
  - `Test_206`: clear Type 2. Same Test ID in Case2 and Case4 was Type 2; temporary model predictions were also Type 2 with high confidence. Moved to `data/datasets/Double-Double/3/p1/2/plot_Test_206_P1.png`.
  - `Test_286`: classified as Type 3. CSV tail metrics and nearest labeled samples strongly indicated Type 3; temporary models mostly predicted Type 3. Moved to `data/datasets/Double-Double/3/p1/3/plot_Test_286_P1.png`.
- The p1 directories were read-only (`dr-xr-xr-x`), so write permission was temporarily enabled for `p1`, `p1/2`, `p1/3`, the files were moved, and permissions were restored to read-only.
- Final check: Case 2, Case 3, and Case 4 each have 300 transition rows, 300 recursive curve CSV IDs, and 300 P1 image labels. Case 3 type counts are now Type1=117, Type2=136, Type3=47.
- Updated audit document: `docs/dd_double_double_data_audit_2026-05-29.md`.

## 2026-05-29 Double-Double Case2/3/4 New Training

After Case 3 P1 labels were completed, created a new curated dataset from `data/datasets/Double-Double/2`, `3`, and `4` without overwriting older DD curated datasets or existing production model folders.

Created dataset:

- `data/datasets/DD_cases_2_3_4_curated_v1`
- Layout: `Case2`, `Case3`, `Case4`, each with `transition_load.csv`, `csv_load/force_disp_Test_XXX.csv`, and copied P1 plot images under `Trial_1/type1..type3`.
- Total samples: 900. Type counts: Type1=321, Type2=445, Type3=134.

Created scripts:

- `scripts/dd_prepare_cases_2_3_4_dataset.py`: converts the new numeric folders 2/3/4 into the DD training layout.
- `src/ml/dd_laminate/train_cases_2_3_4_classical.py`: trains separate new Case2/3/4 classical baselines and a Laminate Forecast surrogate.

New model outputs, separate from existing DD model folders:

- `models/dd_laminate_cases_2_3_4_theta_v1/theta_classifier.joblib`
- `models/dd_laminate_cases_2_3_4_csv_v1/curve_classifier.joblib`
- `models/dd_laminate_cases_2_3_4_response_surrogate_v1/response_surrogate.joblib`
- Report: `models/dd_laminate_cases_2_3_4_response_surrogate_v1/cases_2_3_4_training_report.md`

Validation used GroupKFold by theta pair, so the same theta pair was not split across train and validation.

Results:

- Theta+Case Type classifier: best `random_forest`, accuracy 0.931 +/- 0.018, macro F1 0.928 +/- 0.020.
- Curve CSV + metadata Type classifier: best `extra_trees`, accuracy 0.953 +/- 0.016, macro F1 0.949 +/- 0.019.
- Laminate Forecast surrogate from theta+case: Type accuracy 0.924 +/- 0.011, macro F1 0.915 +/- 0.017, Pt MAE 496.22, Max. Displacement MAE 0.00051, Max. Force MAE 578.67, normalized curve RMSE 0.0096.

Important: existing frontend/backend still points to the older DD production model folders unless updated separately. Next integration step is to add Case2 support and switch or expose these new model bundles in `src/backend/api/v1/dd_laminate.py` and the DD UI.

## 2026-05-31 DD Case2/3/4 Model Connected to Web App

Connected the newly trained Case2/Case3/Case4 DD model set to the live DD backend and UI.

Code updates:

- `src/backend/api/v1/dd_laminate.py`
  - `CaseKey` now accepts `Case2`, `Case3`, `Case4`.
  - `theta_classical` now points to `models/dd_laminate_cases_2_3_4_theta_v1/theta_classifier.joblib`.
  - `curve_classical` now points to `models/dd_laminate_cases_2_3_4_csv_v1/curve_classifier.joblib`.
  - `response_surrogate` now points to `models/dd_laminate_cases_2_3_4_response_surrogate_v1/response_surrogate.joblib`.
- `src/ml/dd_laminate/predict_theta_classifier.py`, `predict_curve_classifier.py`, and `predict_response_surrogate.py` now detect the new one-hot Case2/3/4 feature schema.
- `src/frontend/dd-laminate/index.html` and `index.ko.html` now include Case2 options and the Case2 formula `[[±θ1]/[±θ2]]4`.
- `src/frontend/dd-laminate/app.js` includes Case2 display labels and Korean model labels for the new Case2/3/4 models.

Deployment/verification:

- Restarted DD server on `127.0.0.1:8000`; new PID from uvicorn output was `32633`.
- Public `https://dd.cafedecafe.co.kr/api/v1/dd-laminate/models` returns the new Case2/3/4 model paths.
- Public `POST https://dd.cafedecafe.co.kr/api/v1/dd-laminate/predict/response` with `theta1=-29`, `theta2=74`, `case=Case2`, `model=response_surrogate` returned Type 2, confidence 0.9525, Predicted Pt 17869.37, Max. Displacement 0.15000000596046448, Max. Force 31382.98.
- Browser check showed `API: connected`, Case options `Case 2`, `Case 3`, `Case 4`, and response model option `Laminate Forecast - Cases 2/3/4` on `dd.cafedecafe.co.kr`.

## 2026-06-05 DD Case2/3/4 GointMLP Models Trained and Connected

User noticed the new Case2/Case3/Case4 dataset had only Tree models trained and asked to train the GointMLP models on the same data and connect them like the Tree models.

Actions:

- Added `src/ml/dd_laminate/train_cases_2_3_4_goint.py` to train GointMLP-style theta and response models on `data/datasets/DD_cases_2_3_4_curated_v1`.
- Trained `models/dd_laminate_cases_2_3_4_theta_goint_v1/theta_goint.pt`.
- Trained `models/dd_laminate_cases_2_3_4_response_goint_v1/response_goint.pt`.
- Extended `src/ml/dd_laminate/predict_theta_deep_classifier.py` and `predict_response_deep_surrogate.py` so new checkpoints with `feature_columns`, `feature_mean`, and `feature_std` use the Case2/3/4 feature schema.
- Also updated the Curve CSV deep sequence path to match the Tree curve model state:
  - Extended `src/ml/dd_laminate/deep_sequence.py` and `train_deep_sequence_classifier.py` for new lowercase theta columns, `force_disp_Test_XXX.csv` filenames, and Case2/3/4 training.
  - Trained `models/dd_laminate_cases_2_3_4_deep_sequence_v1/dd_goint_sequence.pt`.
- Updated `src/backend/api/v1/dd_laminate.py` so:
  - `theta_goint` -> `models/dd_laminate_cases_2_3_4_theta_goint_v1/theta_goint.pt`
  - `curve_goint` -> `models/dd_laminate_cases_2_3_4_deep_sequence_v1/dd_goint_sequence.pt`
  - `response_goint` -> `models/dd_laminate_cases_2_3_4_response_goint_v1/response_goint.pt`

Metrics:

- Theta GointMLP: accuracy 0.9356 +/- 0.0163, macro F1 0.9314 +/- 0.0143.
- Response GointMLP: Type accuracy 0.9356 +/- 0.0134, macro F1 0.9338 +/- 0.0115, Pt MAE 893.28, Max. Displacement MAE 0.000376, Max. Force MAE 1651.29, normalized curve RMSE 0.02370.
- Curve CSV GRU+GointMLP: accuracy 0.9343 +/- 0.0131, macro F1 0.9342 +/- 0.0203.

Deployment/verification:

- Restarted DD API on `127.0.0.1:8000`; uvicorn PID shown as `19149`.
- Public `https://dd.cafedecafe.co.kr/api/v1/dd-laminate/models` shows all three new Case2/3/4 deep paths as available.
- Public API smoke tests passed:
  - `theta_goint` Case2 prediction for theta1=-29, theta2=74 returned Type2 confidence 0.999521.
  - `response_goint` Case2 prediction for theta1=-29, theta2=74 returned Type2 confidence 0.999972 and Pt 18854.95.
  - `curve_goint` Case2 CSV Test_001 returned Type2 confidence 0.981036.

Note: Tree/ExtraTrees models still remain the safer default for Pt and curve-shape regression because their scalar/curve errors are lower, but the app now has matched new-data deep-learning options for theta, curve CSV, and Laminate Forecast.

## 2026-06-06 to 2026-06-11 Laminate Mobile App Iteration Memory

User continued turning the DD Laminate mobile prototype into a more app-like
iOS/Android experience. Important product direction:

- App-facing name should remain user-friendly; backend/project naming may use
  C2ES where appropriate.
- iOS and Android should feel like the same product. Android UI should not be a
  plain text-only version of the iOS app.
- Default network flow should be quiet and app-like: users should not normally
  need to press an API connection button or see developer-style status unless
  there is a failure.
- Public API base URL for out-of-network phone use is
  `https://dd.cafedecafe.co.kr`.

Implemented/adjusted in the Laminate apps:

- iOS and Android model selection now exposes both Tree/ExtraTrees-style and
  GointMLP NN response models.
- Model display names were cleaned so UI shows algorithm names such as
  `ExtraTrees + PCA` and `GointMLP NN` rather than old surrogate/Response
  wording.
- iOS language switching was added in-app near API settings; localization
  supports Korean and English.
- Recent prediction history keeps up to 5 runs, shows ordering with latest
  first, supports applying old inputs, comparing recent runs, and selective
  deletion.
- Comparison curve UI shows two curves with distinct styling and Pt markers.
- Response curve interaction supports tap/drag coordinate tooltip; tapping
  again clears the selected coordinate.
- Keyboard dismissal was improved after theta input on iOS/Android.
- Rule-based interpretation cards were added for confidence, Pt position, and
  curve softening/stability.
- Share text and share-image reports were added and ordered as:
  MODEL, INPUTS, RESULTS, CHART, GRAPH.
- Share output includes input information, readable bullet formatting, and the
  result chart.
- Android result UI was redesigned to match iOS more closely:
  hero Type/Confidence card, 2x2 metric boxes, interpretation card, response
  curve card, share buttons, and class probability bars in `type1`, `type2`,
  `type3` order.
- Android model selector was redesigned into iOS-like selectable cards with
  badges/tags/descriptions; theta inputs gained better padding.
- Android APK is rebuilt to
  `artifacts/android/Laminate-C2ES-debug.apk` after Android changes and verified
  with `apksigner`.

Important graph/metric decisions:

- Double-Double response curve Pt visualization should match the web app idea:
  draw two fitted slope guide lines and mark their intersection/kink at Pt,
  instead of placing a simple dot directly on the raw curve.
- The main result metric previously labeled `Max Displacement` should instead
  show displacement at Predicted Pt. Since the API does not return this field
  directly, the app computes it from the response curve by linearly
  interpolating the displacement where force equals `predictedPt`; if outside
  the curve range, it falls back to the first/last curve point.
- This Pt displacement value is now shown in iOS latest/result/share/compare
  flows and Android result/share/recent-detail/compare flows.

Verification from the latest Laminate app changes:

- `swift test` in `ios/DDLaminateMVP` passed.
- `xcodebuild -project ios/DDLaminateMVPApp/DDLaminateMVPHost.xcodeproj -scheme DDLaminateMVPHost -destination generic/platform=iOS\ Simulator build` passed after adding the new `PtDisplacement.swift` helper to the host Xcode project.
- `JAVA_HOME=/opt/homebrew/opt/openjdk@17 gradle :app:assembleDebug` passed.
- `artifacts/android/Laminate-C2ES-debug.apk` was refreshed and verified with
  APK Signature Scheme v2.

Memory hygiene note:

- User previously asked that important conversation context be recorded
  continuously. This file is the intended long-term project/session memory, but
  recent mobile-app UI iterations were not appended immediately during every
  conversational turn. Keep updating this file after meaningful decisions,
  implementation milestones, deployment changes, and unresolved risks.

## 2026-06-11 Luvelox Domain Migration Started

User is preparing a new company/domain direction under `luvelox.com` and wants
to migrate public service URLs away from `cafedecafe.co.kr`.

Domain/DNS state:

- User bought `luvelox.com` at WHOIS and completed Cloudflare activation before
  asking Codex to continue.
- `luvelox.com` nameservers now resolve to Cloudflare:
  `weston.ns.cloudflare.com` and `tegan.ns.cloudflare.com`.
- Existing `cafedecafe.co.kr` remains on Cloudflare:
  `sterling.ns.cloudflare.com` and `perla.ns.cloudflare.com`.

Chosen public hostnames:

- `https://laminate.luvelox.com` for DD Laminate.
- `https://injection.luvelox.com` for Simple Injection.
- Legacy hostnames stay active during migration:
  `https://dd.cafedecafe.co.kr` and
  `https://injection.cafedecafe.co.kr`.

Cloudflare tunnel actions:

- Existing named tunnel remains `kclab-composite-ai`
  (`02b4b689-84ef-4459-91cd-48c81ea549ae`).
- `infrastructure/cloudflare/kclab-composite-ai.yml` was updated to add
  `laminate.luvelox.com` -> `http://127.0.0.1:8000` and
  `injection.luvelox.com` -> `http://127.0.0.1:8010`, keeping old cafedecafe
  ingress entries.
- The first `cloudflared tunnel route dns kclab-composite-ai
  laminate.luvelox.com` attempt used the old cafedecafe Cloudflare cert and
  incorrectly reported creating `laminate.luvelox.com.cafedecafe.co.kr`.
  If this appears in the Cloudflare cafedecafe DNS dashboard, delete it.
- Backed up the old Cloudflare cert from
  `/Users/danlee/.cloudflared/cert.pem` to
  `/Users/danlee/.cloudflared/cert.cafedecafe-20260611.pem`.
- Ran `cloudflared tunnel login`, selected/authorized the Cloudflare account for
  `luvelox.com`, and received a new `/Users/danlee/.cloudflared/cert.pem`.
- Successfully created DNS routes:
  - `laminate.luvelox.com`
  - `injection.luvelox.com`
- Restarted local `cloudflared` with:
  `/opt/homebrew/bin/cloudflared --config /Users/danlee/KyulAI_codex/infrastructure/cloudflare/kclab-composite-ai.yml tunnel run kclab-composite-ai`
  New PID observed: `79529`.

Code/config updates:

- Laminate app defaults now use `https://laminate.luvelox.com`.
- Injection app defaults now use `https://injection.luvelox.com`.
- iOS app localized external URL hints were updated for both apps.
- Android README/mobile docs were updated for the new domains.
- `scripts/windows/Check-Health.ps1` now checks new Luvelox public URLs and
  legacy cafedecafe URLs.
- `infrastructure/cloudflare/kclab-composite-ai.windows.example.yml` includes
  new Luvelox hostnames plus legacy hostnames.
- Slack command response links were changed to the Luvelox URLs.

Verification:

- Existing legacy endpoints still work:
  - `https://dd.cafedecafe.co.kr/health` -> HTTP 200
  - `https://injection.cafedecafe.co.kr/health` -> HTTP 200
- New Laminate endpoint works:
  - `https://laminate.luvelox.com/health` -> HTTP 200
- New Injection endpoint works through Cloudflare when resolving against
  Cloudflare IP directly:
  - `curl --resolve injection.luvelox.com:443:104.21.31.122
    https://injection.luvelox.com/health` -> HTTP 200
- Local default resolver briefly returned `Could not resolve host` for
  `injection.luvelox.com`; `dig @1.1.1.1 injection.luvelox.com` already
  returned Cloudflare IPs. Treat this as local DNS/negative-cache propagation
  unless it persists.
- `swift test` passed for `ios/DDLaminateMVP`.
- `swift test` passed for `ios/InjectionMVP`.
- `gradle :app:assembleDebug` passed for Android Laminate and Android
  Injection.
- Refreshed and verified APKs:
  - `artifacts/android/Laminate-C2ES-debug.apk`
  - `artifacts/android/Injection-C2ES-debug.apk`

Follow-up branding update:

- User asked to remove `C2ES` from the apps and use `Luvelox` instead.
- User-facing app titles now show:
  - `Luvelox Laminate Forecast` / `Luvelox 적층 예측`
  - `Luvelox Injection Forecast` / `Luvelox 사출 예측`
- Share text, share-image headers, generated image filenames, Android gallery
  folder names, iOS share file names, iOS local-network permission descriptions,
  and mobile README titles were updated from C2ES/KyulAI-facing app branding to
  Luvelox where user-visible.
- Internal module names, package names, and bundle IDs such as
  `com.kyulai...` were intentionally left unchanged to avoid app identity and
  signing churn.
- Android APKs were rebuilt and copied to both legacy artifact names and new
  Luvelox artifact names:
  - `artifacts/android/Luvelox-Laminate-debug.apk`
  - `artifacts/android/Luvelox-Injection-debug.apk`
  - `artifacts/android/Laminate-C2ES-debug.apk`
  - `artifacts/android/Injection-C2ES-debug.apk`
- Verification passed:
  - `swift test` in `ios/DDLaminateMVP`
  - `swift test` in `ios/InjectionMVP`
  - `gradle :app:assembleDebug` in `android/DDLaminateMVP`
  - `gradle :app:assembleDebug` in `android/InjectionMVP`
  - `apksigner verify` for the two Luvelox APK artifacts

## 2026-06-11 Product Direction: Unified Luvelox App

User raised a strategic concern that making a separate app/web surface for
every model will not scale as Luvelox adds more models. Proposed direction:

- Move toward one unified Luvelox app/web product where available models appear
  as modules.
- Module visibility should depend on what the user/account has purchased or
  been granted access to.
- Add login/account support so module entitlements can be associated with a
  user, organization, or license.
- Need to decide the commercial model carefully because in-app digital module
  purchases may trigger Apple/Google in-app purchase or Play Billing rules,
  while B2B/enterprise subscriptions can often be handled as account/license
  entitlements purchased outside the app if the app is positioned as a companion
  to a paid web/enterprise service.

Initial product recommendation to discuss:

- Build a unified "Luvelox" shell app with a module dashboard.
- Keep each model as a backend-declared module with its own schema, UI renderer,
  result renderer, and entitlement key.
- Start with login + server-side entitlements, not separate app binaries.
- Keep Laminate and Injection as modules inside the unified app once the shell
  exists.

Implementation started:

- Added `GET /api/v1/modules` and `GET /api/v1/modules/me`.
- Added `src.backend.luvelox_app:app` as a standalone unified Luvelox shell.
- Added `src/frontend/luvelox` as a module dashboard preview.
- Laminate and Injection are active/granted by default for the MVP.
- Future modules can be represented as locked/planned catalog entries.

Native shell MVP started:

- Added `ios/LuveloxMVP`, a SwiftUI Luvelox module dashboard that reads
  `/api/v1/modules/me` and falls back to local Laminate/Injection cards.
- Added `android/LuveloxMVP`, a Kotlin Android Luvelox module dashboard with
  the same module catalog behavior.
- Both native shells currently open the existing module web apps rather than
  embedding the full native Laminate/Injection screens.
- The current catalog source is
  `https://laminate.luvelox.com/api/v1/modules/me` until a dedicated
  `api.luvelox.com` route exists.
- Android debug artifact: `artifacts/android/Luvelox-debug.apk`.
- Verification passed:
  - `swift test` in `ios/LuveloxMVP`
  - `JAVA_HOME=/opt/homebrew/opt/openjdk@17 gradle :app:assembleDebug` in
    `android/LuveloxMVP`
  - `apksigner verify --verbose artifacts/android/Luvelox-debug.apk`

Native Laminate module integration:

- Luvelox iOS now depends on `ios/DDLaminateMVP`'s `KyulAIDDLaminateCore` and
  includes `LaminateForecastView`.
- Tapping the Laminate card in the Luvelox iOS shell opens the native Laminate
  forecast screen instead of the web module.
- Luvelox Android now includes `LaminateActivity`.
- Tapping the Laminate card in the Luvelox Android shell opens the native
  Laminate Activity instead of the browser.
- The native Laminate screens support case/theta/model selection and call
  `POST /api/v1/dd-laminate/predict/response`.
- Injection still opens the existing web module; native Injection migration is
  the next logical step.
- Verification passed after this step:
  - `swift test` and `swift build` in `ios/LuveloxMVP`
  - `JAVA_HOME=/opt/homebrew/opt/openjdk@17 gradle :app:assembleDebug` in
    `android/LuveloxMVP`
  - refreshed and verified `artifacts/android/Luvelox-debug.apk`

Native Injection module integration:

- Luvelox iOS now also depends on `ios/InjectionMVP`'s
  `KyulAIInjectionCore` and includes `InjectionForecastView`.
- Tapping the Injection card in the Luvelox iOS shell opens the native Injection
  forecast screen instead of the web module.
- Luvelox Android now includes `InjectionActivity`.
- Tapping the Injection card in the Luvelox Android shell opens the native
  Injection Activity instead of the browser.
- The native Injection screens support geometry/process selection, sprue model
  selection, filling model selection, DOE value preview, and
  `POST /api/v1/simple-injection/predict/sprue-pressure`.
- Verification passed after this step:
  - `swift test` and `swift build` in `ios/LuveloxMVP`
  - `JAVA_HOME=/opt/homebrew/opt/openjdk@17 gradle :app:assembleDebug` in
    `android/LuveloxMVP`
  - refreshed and verified `artifacts/android/Luvelox-debug.apk`

## 2026-06-11 Session Memory Reminder

User explicitly reconfirmed that conversation context should keep being
recorded. Continue treating `docs/session-memory.md` as the long-term running
memory for important project decisions, implementation changes, deployment
state, dataset/model status, and unresolved risks. Do not rely only on chat
history for important context.

Latest Simple Injection reminder:

- The web DOE dropdown issue was not just copy text. The API `/doe` endpoint
  previously exposed only the base DOE files, so Geometry stopped at `G30` and
  Process stopped at `P10`.
- The intended current web/API DOE exposure is Geometry `G01-G42` and Process
  `P01-P20`, filtered to IDs that have normalized training results.
- Proposed future DOE entries such as `G43+` and `P21+` should not appear in the
  web dropdown until corresponding training results exist.

## Luvelox Native App Integration Update

As of 2026-06-11, the Luvelox iOS host no longer opens reduced Laminate and
Injection screens.

- `ios/DDLaminateMVP` now exposes a `KyulAIDDLaminateApp` library product.
- `ios/InjectionMVP` now exposes a `KyulAIInjectionApp` library product.
- The old package `@main` files were moved into separate preview executable
  targets:
  - `KyulAIDDLaminatePreview`
  - `KyulAIInjectionPreview`
- Public wrapper views were added:
  - `DDLaminateModuleView`
  - `InjectionModuleView`
- `ios/LuveloxMVP` imports those app products and routes Laminate/Injection
  cards to the full existing native app UI, preserving richer charts, history,
  sharing, interpretation, comparison, localization, and module-specific
  settings from the standalone apps.
- `ios/LuveloxMVPApp/LuveloxMVPHost.xcodeproj` links both app products, not
  only the core products.

Verification passed after this integration:

- `swift test` in `ios/DDLaminateMVP`
- `swift test` in `ios/InjectionMVP`
- `swift test` in `ios/LuveloxMVP`
- `xcodebuild -project ios/LuveloxMVPApp/LuveloxMVPHost.xcodeproj -scheme LuveloxMVPHost -destination 'generic/platform=iOS Simulator' build`

Luvelox app icon update:

- Source brand board: `icons/luvelox/Luvelox_LOGO.png`.
- Cropped reusable source icon: `icons/luvelox/Luvelox_AppIcon_Source.png`.
- iOS AppIcon asset set added under
  `ios/LuveloxMVPApp/LuveloxMVPHost/Assets.xcassets/AppIcon.appiconset`.
- `LuveloxMVPHost.xcodeproj` now sets
  `ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon`.
- Android launcher icons were generated in the `mipmap-*` folders and
  connected through `android:icon` / `android:roundIcon`.
- Updated Android APK artifact: `artifacts/android/Luvelox-debug.apk`.
- Verification passed:
  - `xcodebuild -project ios/LuveloxMVPApp/LuveloxMVPHost.xcodeproj -scheme LuveloxMVPHost -destination 'generic/platform=iOS Simulator' build`
  - `JAVA_HOME=/opt/homebrew/opt/openjdk@17 gradle :app:assembleDebug`
  - `JAVA_HOME=/opt/homebrew/opt/openjdk@17 apksigner verify --verbose artifacts/android/Luvelox-debug.apk`
