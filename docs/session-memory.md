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

## 2026-06-23 DD Native App Research Insight Update

The DD Laminate web v2 Research Insight work was extended into the native app
surface.

Implemented:

- Android ImperialAX/ImperialAX Laminate app now calls
  `/api/v1/dd-laminate/design-space` after a successful response forecast.
- Android result screen now shows a compact Research Insight card with:
  - Top candidate
  - recommendation score breakdown: Pt, Type, Distance, Total
  - Case behavior zones
- iOS shared `KyulAIDDLaminateCore` now includes `DesignSpaceRequest`,
  `DesignSpaceResponse`, `DesignSpaceRecommendation`,
  `DesignSpaceScoreBreakdown`, and `DesignSpaceCaseInsight`.
- iOS shared API client now supports the design-space endpoint.
- iOS `PredictionViewModel` lazily loads response design-space insight after
  successful Laminate Forecast prediction without blocking the prediction if
  insight loading fails.
- iOS ImperialAX Laminate forecast view shows compact Research Insight UI below
  class probabilities.

Verification:

- `swift test` in `ios/DDLaminateMVP` passed: 11 tests.
- `swift build` in `ios/ImperialAXMVP` passed.
- Initial Android build failed because system Java was not configured.
- Homebrew `openjdk@17` was available and used with:
  `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home`.
- Android build passed with `gradle :app:assembleDebug`.
- Latest debug APK:
  `android/ImperialAXMVP/app/build/outputs/apk/debug/app-debug.apk`.
- Convenience copy:
  `artifacts/android/ImperialAX-debug-design-space.apk`.

## 2026-06-24 Native Design-Space Map Follow-Up

The native DD Laminate result screens were updated so Research Insight maps are
inspectable like the web UI.

Implemented:

- iOS `DDLaminateMVP` result detail Research Insight map now supports tapping
  dots to select the nearest experiment point.
- iOS map now shows a selected-point panel with Case, Test ID, theta values,
  Pt, Type, and distance.
- iOS map now shows nearest experiment-point rows that can also be tapped to
  change the selected point.

## 2026-06-25 DD Laminate Web Report Export Fix

The DD Laminate web v2 report export was updated because PNG/PDF downloads were
still using an older fixed report canvas and did not include the full current
result surface.

Implemented:

- `src/frontend/dd-laminate/app-v2.js` now builds report exports from the
  current prediction result plus visible XAI and Research Insight sections.
- Report PNG now includes the response curve, design-space map, XAI feature
  explanations, current-vs-candidate comparison, Case behavior zones, Case risk,
  nearest simulations, recommended candidates, and notes when those panels are
  loaded.
- Report PDF now slices the tall report canvas into printable page images so
  long reports are not clipped into a single oversized image.
- Lazy XAI and design-space responses now merge into `latestPredictionData`
  even when the other async result has already updated that object.
- `index-v2.html` and `index-v2.ko.html` now use
  `app-v2.js?v=20260625-report-full` to avoid stale browser cache.

Verification:

- `node --check src/frontend/dd-laminate/app-v2.js` passed.
- Temporary local DD server on `127.0.0.1:3000` served the updated
  `index-v2.html` script tag.
- `/api/v1/dd-laminate/predict/response`, `/xai/local`, and `/design-space`
  returned valid data for a sample `theta1=30`, `theta2=-30`, `Case3` request.

## 2026-06-25 DD Laminate Current Input Tooltip

The web Laminate Design-space map now treats the purple `Current input` point
as an interactive map point instead of drawing it as a visual-only marker.

Implemented:

- Current input is added to the map hover target list with model-estimated Type,
  Pt, and confidence from `latestPredictionData`.
- Tooltip copy distinguishes current model estimates from dataset observation
  points.
- The current input marker receives hover priority when it overlaps nearby
  curated simulation points.
- `index-v2.html` and `index-v2.ko.html` now use
  `app-v2.js?v=20260625-current-input-tooltip`.

Verification:

- `node --check src/frontend/dd-laminate/app-v2.js` passed.
- `git diff --check` on touched DD web files passed.
- Temporary local server on `127.0.0.1:3000` served the updated script tag and
  JS containing `currentInputPoint`, `isCurrentInput`, and current-input hover
  priority logic.

## 2026-06-25 DD Laminate Workflow Grid Alignment

The DD Laminate web v2 workflow summary strip was aligned with the three actual
work columns below it.

Implemented:

- `styles-v2.css` now defines shared `--workspace-columns` variables for the
  Forecast setup, preview, and Prediction columns.
- The top `01 Set case / 02 Pick model / 03 Review` cards now use the same
  grid tracks as the lower workspace grid.
- Curve CSV and u3 modes keep their mode-specific column widths, and the
  summary strip receives matching `curve-active` / `u3-active` classes.
- At tablet widths where the lower workspace collapses to one column, the
  summary strip also collapses to one column.
- English and Korean pages now load `styles-v2.css?v=20260625-workflow-grid`
  and `app-v2.js?v=20260625-workflow-grid`.

Verification:

- `node --check src/frontend/dd-laminate/app-v2.js` passed.
- `git diff --check` on touched DD web files passed.
- Temporary local server on `127.0.0.1:3000` served the updated CSS/JS version
  tags for both English and Korean pages.

## 2026-06-24 Android Design-Space Map Follow-Up

Implemented:

- Android result screen design-space map now has explicit loading/error states,
  a map-point count label, a fixed measured map size, a visible field
  background, horizontal scrolling, selected-point details, and nearest-point
  buttons.
- The live design-space API was checked and returns `map_points`, so the
  remaining Android risk is stale APK/device install state or device-specific
  rendering, not missing server data.

Verification:

- `swift test` in `ios/DDLaminateMVP` passed: 11 tests.
- `swift test` in `ios/ImperialAXMVP` passed: 6 tests.
- Android debug build passed with:
  `JAVA_HOME=/Applications/PyCharm.app/Contents/jbr/Contents/Home gradle :app:assembleDebug`.
- Latest Android APK copies:
  `artifacts/android/ImperialAX-debug-design-space-map.apk` and
  `artifacts/android/ImperialAX-debug-design-space-map-v2.apk`.

## 2026-06-24 iOS Response Curve Zoom Update

The iOS DD Laminate response-curve chart was updated so overlapping curve,
linear-fit, kink-guide, and Pt markers can be inspected more clearly.

Implemented:

- `CurveChartView` now supports pinch zoom up to 500%.
- The chart can be panned while zoomed.
- Compact zoom controls were added: zoom out, current zoom percentage, zoom in,
  and reset.
- Chart axes, curve, two red linear-fit slopes, kink guide, selected point, and
  Pt marker now use the same viewport-aware coordinate system.
- Result-detail response curves were given more vertical space.
- Report/share image rendering keeps chart controls hidden.

Verification:

- `swift test` in `ios/DDLaminateMVP` passed: 11 tests.
- `swift test` in `ios/ImperialAXMVP` passed: 6 tests.
- XcodeBuildMCP built and launched `ImperialAXMVPHost` on the iPhone 17 simulator.

## 2026-06-24 DD Laminate Classic Removal And iOS History Cards

User asked to stop exposing the old Classic DD Laminate UI and to make the iOS
empty result area more useful.

Implemented:

- iOS `DDLaminateModuleView` now opens the current `ContentViewV2` screen
  directly instead of showing a `v2` / `Classic` design picker.
- iOS `ContentViewV2` navigation title no longer says `v2`; it is presented as
  the normal Laminate screen.
- When Laminate Forecast or u3 Forecast has no active result, the old
  `Ready for input` panel now shows compact prediction-history cards if recent
  runs exist.
- History cards are mode-specific and summarize Case, model, θ₁, θ₂, Type,
  confidence, and Pt; tapping a card restores that setup.
- Web DD Laminate v2 titles no longer include `v2`.
- Web v2 headers no longer link to Classic.
- Direct classic URLs (`index.html`, `index.ko.html`) now redirect to the
  current forecast pages so the old UI is hidden.

Verification:

- `swift test` in `ios/DDLaminateMVP` passed: 11 tests.
- `swift build` in `ios/ImperialAXMVP` passed.
- Repository search found no remaining visible `Classic`, `Wanted v2`,
  `Laminate v2`, or `적층 v2` strings in DD Laminate web/app surfaces.

## 2026-06-24 DD Laminate Web And Android Prediction History

User asked to add the same prediction-history idea to Android and web if it was
missing.

Implemented:

- Web DD Laminate v2 now stores recent Response Forecast and u3 Forecast runs in
  `localStorage`.
- Web empty result panel now shows mode-specific prediction-history cards when
  recent runs exist.
- Web history cards summarize Case, θ₁, θ₂, Type, confidence, Pt, and model.
- Tapping a web history card restores that setup into the active prediction
  form.
- Web mobile layout now keeps the result panel visible when history exists,
  instead of hiding it just because there is no active result.
- Android native Laminate screen now stores recent Response Forecast summaries
  in app preferences.
- Android Laminate screen now shows compact recent forecast cards below the
  input form.
- Tapping an Android history card restores Case, θ₁, θ₂, and model selection.
- New Android debug APK copied to:
  `artifacts/android/ImperialAX-debug-prediction-history.apk`.

Verification:

- `node --check src/frontend/dd-laminate/app-v2.js` passed.
- `JAVA_HOME=/Applications/PyCharm.app/Contents/jbr/Contents/Home gradle :app:assembleDebug`
  in `android/ImperialAXMVP` passed.
- `git diff --check` on touched web/Android files passed.

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

## 2026-06-15 - Git handoff preparation for Windows PC

User requested a Git upload containing the current work plus data, so the
project can be cloned on a Windows PC and continued there.

Preparation:

- Audited repository size and found `data` at about 1.3GB and `models` at about
  3.6GB before compression.
- Git LFS is not installed in the current Mac environment, so large `joblib`
  models were recompressed with stronger `joblib`/LZMA compression instead of
  relying on LFS.
- After compression, `models` was reduced to about 811MB.
- Confirmed no files larger than 95MB remained under `data`, `models`,
  `reports`, `extra`, or `artifacts`, which avoids the normal GitHub 100MB
  single-file push limit.
- Verified representative compressed model files still load with `joblib`.
- Added `docs/WINDOWS_GIT_QUICKSTART.md` with Git clone and PowerShell setup
  steps for a fresh Windows PC.
- Updated `docs/windows-server-migration.md` to include the Git-based handoff
  path before the older zip-bundle path.
- Added `.dvc/` and `.dvcignore` to `.gitignore`; current handoff commits data
  directly through Git and does not include local DVC config or credentials.

Important:

- Cloudflare tunnel JSON credentials and `.env.local` remain local-only and are
  not committed.
- The Windows user should clone the branch, run
  `scripts\windows\Setup-WindowsServing.ps1`, then start DD and Injection with
  the provided PowerShell scripts.
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
  ImperialAX where appropriate.
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
  `artifacts/android/Laminate-ImperialAX-debug.apk` after Android changes and verified
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
- `artifacts/android/Laminate-ImperialAX-debug.apk` was refreshed and verified with
  APK Signature Scheme v2.

Memory hygiene note:

- User previously asked that important conversation context be recorded
  continuously. This file is the intended long-term project/session memory, but
  recent mobile-app UI iterations were not appended immediately during every
  conversational turn. Keep updating this file after meaningful decisions,
  implementation milestones, deployment changes, and unresolved risks.

## 2026-06-11 ImperialAX Domain Migration Started

User is preparing a new company/domain direction under `imperialax.com` and wants
to migrate public service URLs away from `cafedecafe.co.kr`.

Domain/DNS state:

- User bought `imperialax.com` at WHOIS and completed Cloudflare activation before
  asking Codex to continue.
- `imperialax.com` nameservers now resolve to Cloudflare:
  `weston.ns.cloudflare.com` and `tegan.ns.cloudflare.com`.
- Existing `cafedecafe.co.kr` remains on Cloudflare:
  `sterling.ns.cloudflare.com` and `perla.ns.cloudflare.com`.

Chosen public hostnames:

- `https://laminate.imperialax.com` for DD Laminate.
- `https://injection.imperialax.com` for Simple Injection.
- Legacy hostnames stay active during migration:
  `https://dd.cafedecafe.co.kr` and
  `https://injection.cafedecafe.co.kr`.

Cloudflare tunnel actions:

- Existing named tunnel remains `kclab-composite-ai`
  (`02b4b689-84ef-4459-91cd-48c81ea549ae`).
- `infrastructure/cloudflare/kclab-composite-ai.yml` was updated to add
  `laminate.imperialax.com` -> `http://127.0.0.1:8000` and
  `injection.imperialax.com` -> `http://127.0.0.1:8010`, keeping old cafedecafe
  ingress entries.
- The first `cloudflared tunnel route dns kclab-composite-ai
  laminate.imperialax.com` attempt used the old cafedecafe Cloudflare cert and
  incorrectly reported creating `laminate.imperialax.com.cafedecafe.co.kr`.
  If this appears in the Cloudflare cafedecafe DNS dashboard, delete it.
- Backed up the old Cloudflare cert from
  `/Users/danlee/.cloudflared/cert.pem` to
  `/Users/danlee/.cloudflared/cert.cafedecafe-20260611.pem`.
- Ran `cloudflared tunnel login`, selected/authorized the Cloudflare account for
  `imperialax.com`, and received a new `/Users/danlee/.cloudflared/cert.pem`.
- Successfully created DNS routes:
  - `laminate.imperialax.com`
  - `injection.imperialax.com`
- Restarted local `cloudflared` with:
  `/opt/homebrew/bin/cloudflared --config /Users/danlee/KyulAI_codex/infrastructure/cloudflare/kclab-composite-ai.yml tunnel run kclab-composite-ai`
  New PID observed: `79529`.

Code/config updates:

- Laminate app defaults now use `https://laminate.imperialax.com`.
- Injection app defaults now use `https://injection.imperialax.com`.
- iOS app localized external URL hints were updated for both apps.
- Android README/mobile docs were updated for the new domains.
- `scripts/windows/Check-Health.ps1` now checks new ImperialAX public URLs and
  legacy cafedecafe URLs.
- `infrastructure/cloudflare/kclab-composite-ai.windows.example.yml` includes
  new ImperialAX hostnames plus legacy hostnames.
- Slack command response links were changed to the ImperialAX URLs.

Verification:

- Existing legacy endpoints still work:
  - `https://dd.cafedecafe.co.kr/health` -> HTTP 200
  - `https://injection.cafedecafe.co.kr/health` -> HTTP 200
- New Laminate endpoint works:
  - `https://laminate.imperialax.com/health` -> HTTP 200
- New Injection endpoint works through Cloudflare when resolving against
  Cloudflare IP directly:
  - `curl --resolve injection.imperialax.com:443:104.21.31.122
    https://injection.imperialax.com/health` -> HTTP 200
- Local default resolver briefly returned `Could not resolve host` for
  `injection.imperialax.com`; `dig @1.1.1.1 injection.imperialax.com` already
  returned Cloudflare IPs. Treat this as local DNS/negative-cache propagation
  unless it persists.
- `swift test` passed for `ios/DDLaminateMVP`.
- `swift test` passed for `ios/InjectionMVP`.
- `gradle :app:assembleDebug` passed for Android Laminate and Android
  Injection.
- Refreshed and verified APKs:
  - `artifacts/android/Laminate-ImperialAX-debug.apk`
  - `artifacts/android/Injection-ImperialAX-debug.apk`

Follow-up branding update:

- User asked to remove `ImperialAX` from the apps and use `ImperialAX` instead.
- User-facing app titles now show:
  - `ImperialAX Laminate Forecast` / `ImperialAX 적층 예측`
  - `ImperialAX Injection Forecast` / `ImperialAX 사출 예측`
- Share text, share-image headers, generated image filenames, Android gallery
  folder names, iOS share file names, iOS local-network permission descriptions,
  and mobile README titles were updated from ImperialAX/KyulAI-facing app branding to
  ImperialAX where user-visible.
- Internal module names, package names, and bundle IDs such as
  `com.kyulai...` were intentionally left unchanged to avoid app identity and
  signing churn.
- Android APKs were rebuilt and copied to both legacy artifact names and new
  ImperialAX artifact names:
  - `artifacts/android/ImperialAX-Laminate-debug.apk`
  - `artifacts/android/ImperialAX-Injection-debug.apk`
  - `artifacts/android/Laminate-ImperialAX-debug.apk`
  - `artifacts/android/Injection-ImperialAX-debug.apk`
- Verification passed:
  - `swift test` in `ios/DDLaminateMVP`
  - `swift test` in `ios/InjectionMVP`
  - `gradle :app:assembleDebug` in `android/DDLaminateMVP`
  - `gradle :app:assembleDebug` in `android/InjectionMVP`
  - `apksigner verify` for the two ImperialAX APK artifacts

## 2026-06-11 Product Direction: Unified ImperialAX App

User raised a strategic concern that making a separate app/web surface for
every model will not scale as ImperialAX adds more models. Proposed direction:

- Move toward one unified ImperialAX app/web product where available models appear
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

- Build a unified "ImperialAX" shell app with a module dashboard.
- Keep each model as a backend-declared module with its own schema, UI renderer,
  result renderer, and entitlement key.
- Start with login + server-side entitlements, not separate app binaries.
- Keep Laminate and Injection as modules inside the unified app once the shell
  exists.

Implementation started:

- Added `GET /api/v1/modules` and `GET /api/v1/modules/me`.
- Added `src.backend.imperialax_app:app` as a standalone unified ImperialAX shell.
- Added `src/frontend/imperialax` as a module dashboard preview.
- Laminate and Injection are active/granted by default for the MVP.
- Future modules can be represented as locked/planned catalog entries.

Native shell MVP started:

- Added `ios/ImperialAXMVP`, a SwiftUI ImperialAX module dashboard that reads
  `/api/v1/modules/me` and falls back to local Laminate/Injection cards.
- Added `android/ImperialAXMVP`, a Kotlin Android ImperialAX module dashboard with
  the same module catalog behavior.
- Both native shells currently open the existing module web apps rather than
  embedding the full native Laminate/Injection screens.
- The current catalog source is
  `https://laminate.imperialax.com/api/v1/modules/me` until a dedicated
  `api.imperialax.com` route exists.
- Android debug artifact: `artifacts/android/ImperialAX-debug.apk`.
- Verification passed:
  - `swift test` in `ios/ImperialAXMVP`
  - `JAVA_HOME=/opt/homebrew/opt/openjdk@17 gradle :app:assembleDebug` in
    `android/ImperialAXMVP`
  - `apksigner verify --verbose artifacts/android/ImperialAX-debug.apk`

Native Laminate module integration:

- ImperialAX iOS now depends on `ios/DDLaminateMVP`'s `KyulAIDDLaminateCore` and
  includes `LaminateForecastView`.
- Tapping the Laminate card in the ImperialAX iOS shell opens the native Laminate
  forecast screen instead of the web module.
- ImperialAX Android now includes `LaminateActivity`.
- Tapping the Laminate card in the ImperialAX Android shell opens the native
  Laminate Activity instead of the browser.
- The native Laminate screens support case/theta/model selection and call
  `POST /api/v1/dd-laminate/predict/response`.
- Injection still opens the existing web module; native Injection migration is
  the next logical step.
- Verification passed after this step:
  - `swift test` and `swift build` in `ios/ImperialAXMVP`
  - `JAVA_HOME=/opt/homebrew/opt/openjdk@17 gradle :app:assembleDebug` in
    `android/ImperialAXMVP`
  - refreshed and verified `artifacts/android/ImperialAX-debug.apk`

Native Injection module integration:

- ImperialAX iOS now also depends on `ios/InjectionMVP`'s
  `KyulAIInjectionCore` and includes `InjectionForecastView`.
- Tapping the Injection card in the ImperialAX iOS shell opens the native Injection
  forecast screen instead of the web module.
- ImperialAX Android now includes `InjectionActivity`.
- Tapping the Injection card in the ImperialAX Android shell opens the native
  Injection Activity instead of the browser.
- The native Injection screens support geometry/process selection, sprue model
  selection, filling model selection, DOE value preview, and
  `POST /api/v1/simple-injection/predict/sprue-pressure`.
- Verification passed after this step:
  - `swift test` and `swift build` in `ios/ImperialAXMVP`
  - `JAVA_HOME=/opt/homebrew/opt/openjdk@17 gradle :app:assembleDebug` in
    `android/ImperialAXMVP`
  - refreshed and verified `artifacts/android/ImperialAX-debug.apk`

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

## ImperialAX Native App Integration Update

As of 2026-06-11, the ImperialAX iOS host no longer opens reduced Laminate and
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
- `ios/ImperialAXMVP` imports those app products and routes Laminate/Injection
  cards to the full existing native app UI, preserving richer charts, history,
  sharing, interpretation, comparison, localization, and module-specific
  settings from the standalone apps.
- `ios/ImperialAXMVPApp/ImperialAXMVPHost.xcodeproj` links both app products, not
  only the core products.

Verification passed after this integration:

- `swift test` in `ios/DDLaminateMVP`
- `swift test` in `ios/InjectionMVP`
- `swift test` in `ios/ImperialAXMVP`
- `xcodebuild -project ios/ImperialAXMVPApp/ImperialAXMVPHost.xcodeproj -scheme ImperialAXMVPHost -destination 'generic/platform=iOS Simulator' build`

ImperialAX app icon update:

- Source brand board: `icons/imperialax/ImperialAX_LOGO.png`.
- Cropped reusable source icon: `icons/imperialax/ImperialAX_AppIcon_Source.png`.
- iOS AppIcon asset set added under
  `ios/ImperialAXMVPApp/ImperialAXMVPHost/Assets.xcassets/AppIcon.appiconset`.
- `ImperialAXMVPHost.xcodeproj` now sets
  `ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon`.
- Android launcher icons were generated in the `mipmap-*` folders and
  connected through `android:icon` / `android:roundIcon`.
- Updated Android APK artifact: `artifacts/android/ImperialAX-debug.apk`.
- Verification passed:
  - `xcodebuild -project ios/ImperialAXMVPApp/ImperialAXMVPHost.xcodeproj -scheme ImperialAXMVPHost -destination 'generic/platform=iOS Simulator' build`
  - `JAVA_HOME=/opt/homebrew/opt/openjdk@17 gradle :app:assembleDebug`
  - `JAVA_HOME=/opt/homebrew/opt/openjdk@17 apksigner verify --verbose artifacts/android/ImperialAX-debug.apk`

## 2026-06-12 ImperialAX Account MVP

ImperialAX now has a first login/account MVP, intentionally implemented as a
replaceable demo-auth layer before integrating Supabase/Firebase/Auth0 or a
production identity provider.

Backend:

- `src/backend/api/v1/modules.py` now exposes
  `POST /api/v1/modules/auth/demo-login`.
- Demo users:
  - `demo@imperialax.com` -> Laminate + Injection
  - `danlee@imperialax.com` -> Laminate + Injection + Optimization
- `GET /api/v1/modules/me` now accepts `Authorization: Bearer <token>` and
  includes a `user` object in the response when a demo token is present.

iOS:

- `ios/ImperialAXMVP` now has a sign-in screen before the module workspace.
- The auth session is stored in `UserDefaults` as `imperialax.auth.session.v1`.
- Module catalog calls now send the bearer token.
- The signed-in workspace shows an account band and a menu with refresh/sign
  out.
- If the demo login endpoint is offline, the app can still create the local
  demo session for MVP testing.

Android:

- `android/ImperialAXMVP` now has the same login-first flow.
- The auth session is stored in `SharedPreferences`.
- Module catalog calls send the bearer token.
- `artifacts/android/ImperialAX-debug.apk` was refreshed after the auth changes.

Verification passed:

- `.venv/bin/pytest tests/backend/test_imperialax_modules.py`
- `swift test` in `ios/ImperialAXMVP`
- `xcodebuild -project ios/ImperialAXMVPApp/ImperialAXMVPHost.xcodeproj -scheme ImperialAXMVPHost -destination 'generic/platform=iOS Simulator' build`
- `JAVA_HOME=/opt/homebrew/opt/openjdk@17 gradle :app:assembleDebug` in
  `android/ImperialAXMVP`
- `JAVA_HOME=/opt/homebrew/opt/openjdk@17 /opt/homebrew/share/android-commandlinetools/build-tools/35.0.0/apksigner verify --verbose artifacts/android/ImperialAX-debug.apk`

## 2026-06-12 ImperialAX Account/Access UX

Next account-layer step:

- Backend now exposes `POST /api/v1/modules/request-access` for module access
  requests. It validates the module id and returns a structured `received`
  response with the current demo user when a bearer token is present.
- iOS ImperialAX app now has:
  - Account details sheet from the account menu/account band.
  - Module access list with granted/locked status and access reasons.
  - Locked module detail sheet with entitlement key, capabilities, and a
    request-access action.
- Android ImperialAX app now mirrors the same account/access flow with native
  dialogs and clickable locked-module request buttons.
- Offline fallback catalog includes the planned Optimization module so the
  access UX can be tested without the module catalog server.

## 2026-06-12 DD u3 Pt Regression Dataset and Models

New Double-Double u3 data was inspected under
`data/datasets/Double-Double/u3`.

- Raw folders:
  - Case2: `2-2`, `2-3`
  - Case3: `3-2`, `3-3`
  - Case4: `4-2`, `4-3`
- Each folder contains two-column force/displacement CSVs plus plot PNGs.
- u3 Pt labels are not compatible with the older
  `Double-Double/{2,3,4}/transition load P1.csv` values. Example:
  Case2 Test001 old table Pt is about `19662`, while u3 plot title Pt is
  about `8697`.
- macOS Vision OCR was added in `scripts/dd_u3_ocr.swift` to read plot titles.
- `scripts/dd_prepare_u3_pt_dataset.py` builds the curated u3 Pt manifest by:
  - OCR-reading Pt from P1/transition plot titles.
  - Reusing theta1/theta2 from the old transition tables.
  - Copying labeled CSVs into the curated dataset.
- Final clean curated dataset is `data/datasets/DD_u3_pt_v2`.
  - Records: 566 labeled CSVs.
  - Missing labels: 14 CSVs with no usable plot label.
  - Case counts: Case2 190, Case3 174, Case4 202.
  - Pt range after OCR cleanup: about 3858 to 13258 kips.
- A first `DD_u3_pt_v1` dataset/model run was created, but OCR had three
  decimal-loss outliers (`913357`, `869442`, `869418`). Treat v1 as superseded
  by v2.
- `src/ml/dd_laminate/train_u3_pt_models.py` trains u3-specific Pt regressors.
  It uses Test ID group CV to reduce leakage across repeated angle/case
  variants.
- Final v2 model outputs:
  - Classical ML: `models/dd_laminate_u3_pt_ml_v2/u3_pt_regressor.joblib`
  - Deep Goint-style PyTorch: `models/dd_laminate_u3_pt_goint_v2/u3_pt_goint.pt`
  - Combined report: `reports/dd_u3_pt_v2/summary.json`
- v2 validation summary:
  - ExtraTrees best classical model: CV MAE about `164.90` kips, R2 about
    `0.937`.
  - PyTorch Goint-style model: CV MAE about `163.81` kips, R2 about `0.943`.
  - HistGradientBoosting CV MAE about `198.88` kips.
  - sklearn MLP CV MAE about `781.01` kips.
- Recommendation: use the v2 models as the current u3 Pt baseline. Prefer a
  fresh u3-specific model over fine-tuning the older DD response model because
  the Pt label definition and curve family differ from the previous P1 data.

## 2026-06-12 DD u3 Pt Finder Web/App Integration

The current u3 Pt baseline was connected to the Double-Double prediction
surfaces.

- Backend:
  - Added `src/ml/dd_laminate/predict_u3_pt.py`.
  - Added `POST /api/v1/dd-laminate/predict/u3-pt`.
  - Added `u3_pt_models` to `GET /api/v1/dd-laminate/models`.
  - Supported models:
    - `u3_pt_classical`: `models/dd_laminate_u3_pt_ml_v2/u3_pt_regressor.joblib`
    - `u3_pt_goint`: `models/dd_laminate_u3_pt_goint_v2/u3_pt_goint.pt`
  - Endpoint input is multipart form data with CSV file, `theta1`, `theta2`,
    `case`, `u3_bucket` (`2` or `3`), optional `test_id`, and model key.
  - CSV reading now tolerates header/non-numeric rows by using `genfromtxt`.
- Web:
  - Added a third DD web tab, `u3 Pt Finder`, in both English and Korean pages.
  - The tab uploads a force-displacement CSV, selects Case and u3 bucket, and
    renders predicted Pt on the uploaded curve using the existing curve panel.
  - Report export now tolerates u3 Pt results without a predicted Type.
- iOS DD app:
  - Added u3 model list decoding and `U3PtPredictionResult`.
  - Added multipart CSV upload API client support.
  - Added a `u3 Pt Finder` card with CSV file picker, Case/theta/u3-bucket
    controls, model selection, and a Pt result chart.
- Verification:
  - `node --check src/frontend/dd-laminate/app.js`
  - FastAPI TestClient: `/models` returns `u3_pt_models`, and
    `/predict/u3-pt` returns Pt for `force_disp_Test_001.csv`.
  - Direct sample predictions:
    - Classical: about `8697.15` kips for Case2/u3-2/Test001.
    - Goint: about `8438.75` kips for the same sample.
  - `swift test` in `ios/DDLaminateMVP`: 9 tests passed.

## 2026-06-12 ImperialAX App Icon Refresh

The ImperialAX app icon was regenerated from the new logo file
`icons/imperialax/ImperialAX_LOGO_Fin.jpeg`.

- Used the left-side ImperialAX symbol: dark `L`, diagonal crossing orbit shape,
  and the red star at the orbit tip.
- After review, regenerated the crop to keep the red star and mask only the
  leftover wordmark/tagline fragments at the right and bottom edges.
- Regenerated the reusable source icon:
  `icons/imperialax/ImperialAX_AppIcon_Source.png`.
- Updated iOS ImperialAX app icon assets under
  `ios/ImperialAXMVPApp/ImperialAXMVPHost/Assets.xcassets/AppIcon.appiconset`.
- Updated Android ImperialAX launcher icons under
  `android/ImperialAXMVP/app/src/main/res/mipmap-*`.
- Refreshed Android debug APK artifacts:
  - `artifacts/android/ImperialAX-debug.apk`
  - `artifacts/android/ImperialAX-Laminate-debug.apk`
- Verification:
  - `swift test` in `ios/ImperialAXMVP`: 4 tests passed.
  - `xcodebuild -project ios/ImperialAXMVPApp/ImperialAXMVPHost.xcodeproj -scheme ImperialAXMVPHost -destination generic/platform=iOS Simulator build`: succeeded.
  - `JAVA_HOME=/opt/homebrew/opt/openjdk@17 gradle :app:assembleDebug` in `android/ImperialAXMVP`: succeeded.

## 2026-06-12 DD u3 Forecast Without CSV

The u3 workflow was extended so it can predict before a force-displacement CSV
exists, similar to the Laminate Forecast tab.

- Added a CSV-free u3 forecast model trained from
  `data/datasets/DD_u3_pt_v2/manifest.csv`.
- Inputs: `theta1`, `theta2`, `Case2/3/4`, and `u3_bucket` (`2` or `3`).
- Outputs: predicted Pt, predicted max displacement, predicted max force, and
  an approximate 192-point force-displacement curve.
- New model artifact:
  `models/dd_laminate_u3_forecast_v1/u3_forecast.joblib`.
- New report:
  `reports/dd_u3_forecast_v1/u3_forecast_report.md`.
- Validation summary:
  - Best scalar model: `extra_trees`.
  - Pt MAE: about `219.31 +/- 28.80` kips.
  - Pt R2: about `0.896`.
  - Max. Displacement MAE: about `0.00568`.
  - Max. Force MAE: about `437.24` kips.
  - Normalized curve RMSE: about `0.0094`.
- Added backend endpoint `POST /api/v1/dd-laminate/predict/u3-forecast`.
- Added `u3_forecast` to DD model discovery before the CSV-based u3 Finder
  models.
- Updated the DD web u3 tab:
  - CSV upload is now optional.
  - `u3 Forecast - ExtraTrees + PCA` runs without CSV.
  - Existing `u3 Pt Finder` models still require CSV and remain available for
    post-simulation refinement.
- Updated the iOS DD module:
  - Default u3 model is now `u3_forecast`.
  - Added JSON client support for `/predict/u3-forecast`.
  - The u3 card can run without CSV when the Forecast model is selected.
  - CSV upload is still available for the u3 Finder models.
- Verification:
  - `node --check src/frontend/dd-laminate/app.js`.
  - `PYTHONPYCACHEPREFIX=/private/tmp/kyulai_pycache python -m py_compile ...`.
  - FastAPI router TestClient: `/models` returns `u3_forecast`; `/predict/u3-forecast`
    returns Pt and a 192-point curve.
  - `swift test` in `ios/DDLaminateMVP`: 9 tests passed.

## 2026-06-12 DD u3 Forecast Cache Fix

The web page could show the backend error `Use /predict/u3-forecast for
CSV-free u3 forecast predictions.` when selecting `u3 Forecast - ExtraTrees +
PCA`.

- Cause: `index.html` and `index.ko.html` still referenced the old
  `app.js?v=20260605-response-model-picker` cache key, so browsers could keep
  using stale JavaScript that submitted all u3 models to `/predict/u3-pt`.
- Fix: bumped both pages to `app.js?v=20260612-u3-forecast`.
- Verification:
  - `node --check src/frontend/dd-laminate/app.js`
  - `rg` confirmed both English and Korean pages reference the new cache key.

## 2026-06-12 DD u3 Forecast Only With ML/DL Options

The u3 page was simplified per user request: CSV-based `u3 Pt Finder` is hidden
from the DD web/app workflow for now, and only CSV-free `u3 Forecast` remains.

- Retrained `src/ml/dd_laminate/train_u3_forecast_models.py` and added a
  GointMLP-style deep forecast model for the same input/output contract as the
  existing ML forecast.
- Active u3 Forecast model options:
  - `u3_forecast`: ExtraTrees + PCA, stored at
    `models/dd_laminate_u3_forecast_v1/u3_forecast.joblib`.
  - `u3_forecast_goint`: GointMLP NN, stored at
    `models/dd_laminate_u3_forecast_v1/u3_forecast_goint.pt`.
- Training data: `data/datasets/DD_u3_pt_v2/manifest.csv`, `566` samples.
- Validation summary:
  - ML ExtraTrees + PCA: Pt MAE `219.31 +/- 28.80` kips, Pt R2 `0.896`,
    normalized curve RMSE `0.0094`.
  - DL GointMLP Forecast: Pt MAE `181.74 +/- 48.54` kips, Pt R2 `0.918`,
    normalized curve RMSE `0.0101`.
- Backend:
  - `/api/v1/dd-laminate/models` now exposes only `u3_forecast` and
    `u3_forecast_goint` under `u3_pt_models`.
  - `/api/v1/dd-laminate/predict/u3-forecast` supports both ML and DL forecast
    models.
  - Legacy CSV Finder endpoint remains internally available but is no longer
    advertised to the UI model list.
- Web:
  - English/Korean u3 tab renamed to `u3 Forecast`.
  - Removed u3 CSV upload and optional Test ID field from the page.
  - Bumped page cache key to `app.js?v=20260612-u3-forecast-only`.
- iOS:
  - Removed u3 CSV picker flow from the DD Laminate app card.
  - u3 prediction now always calls the forecast endpoint with the selected
    forecast model.
- Verification:
  - `node --check src/frontend/dd-laminate/app.js`.
  - `PYTHONPYCACHEPREFIX=/private/tmp/kyulai_pycache /Users/danlee/KyulAI_codex/.venv/bin/python -m py_compile ...`.
  - FastAPI router TestClient: model list returns
    `['u3_forecast', 'u3_forecast_goint']`; both forecast models return HTTP
    `200` and a `192`-point curve.
  - `swift test` in `ios/DDLaminateMVP`: 9 tests passed.

## 2026-06-12 DD Web u3 Result Layout Fix

The u3 Forecast result page looked broken because the middle laminate reference
panel remained visible after prediction, leaving the result/chart panel too
narrow.

- Added `.grid.u3-active` to make u3 mode use a two-column layout:
  input panel + wide result panel.
- Updated mode switching so u3 hides the reference panel and CSV preview panel.
- Bumped web cache keys to `20260612-u3-layout` for both English and Korean
  DD pages.
- Verification:
  - `node --check src/frontend/dd-laminate/app.js`.
  - Browser check at `http://127.0.0.1:3000/`: ML and DL u3 Forecast results
    render with a wide chart, clean legend, and readable notes.

## 2026-06-12 DD App Laminate/u3 UX Cleanup

The ImperialAX/DD app Laminate screen was reorganized so users choose between the
standard laminate forecast and u3 forecast instead of seeing both input cards
stacked vertically.

- Added a segmented input-mode picker:
  - `Forecast Inputs`
  - `u3 Forecast`
- The selected mode now shows only its corresponding input card.
- u3 forecast results now open a dedicated detail page, matching the standard
  forecast result flow.
- Added `U3PtResultDetailView` with Pt, max force, max displacement, curve
  chart, and notes.
- Removed the nested `NavigationStack` from the DD Laminate content view so
  ImperialAX navigation owns the stack. This keeps result-page back navigation
  returning to the Laminate screen instead of the Laminate/Injection module
  picker.
- Standalone DD preview app now wraps `DDLaminateModuleView` in its own
  `NavigationStack`.
- Verification:
  - `swift test` in `ios/DDLaminateMVP`: 9 tests passed.
  - `swift test` in `ios/ImperialAXMVP`: 4 tests passed.

## 2026-06-12 DD/u3 Bilinear Pt Marker Fix

The u3 forecast graph was corrected so the plotted Pt marker is based on the
intersection of the two fitted linear guide lines, not the point where the
predicted Pt force happens to cross the predicted response curve.

- Web:
  - `src/frontend/dd-laminate/app.js` now computes the raw first/second fit
    line intersection, validates it within the usable kink range, and uses that
    intersection force/displacement for the red Pt marker and purple guide.
  - The model's scalar `predicted_pt` is still shown in the metric card, while
    the graph marker represents the bilinear-fit intersection used visually.
  - Bumped English/Korean DD page script cache key to
    `app.js?v=20260612-u3-kink`.
- iOS:
  - `CurveChartView.swift` uses the same bilinear intersection rule for the
    app chart.
- Verification:
  - `node --check src/frontend/dd-laminate/app.js`.
  - `swift test` in `ios/DDLaminateMVP`: 9 tests passed.
  - Local API `POST /api/v1/dd-laminate/predict/u3-forecast` returned HTTP
    `200` with a 192-point curve and predicted Pt/max values.

## 2026-06-12 DD/u3 Row-Window Linear Fit Correction

The previous u3 graph correction still used an envelope/tail style right-side
fit, which did not match the fitted lines in the raw u3 plot images.

- Checked the raw u3 reference plot
  `data/datasets/Double-Double/u3/2-2/plot/plot_Test_001_P1.png`.
- The reference plot explicitly labels:
  - `P1 Initial fit (rows 1-3)`
  - `P1 Second fit (rows 125-128)`
- The raw CSV has 1001 points, so rows 125-128 correspond to about 12.4% of
  the curve length, not the far tail.
- Updated web u3 graph rendering:
  - Added `buildU3BilinearFit(points)` in
    `src/frontend/dd-laminate/app.js`.
  - u3 uses first 3 points for the initial line.
  - u3 uses the 12.4%-position 4-point window for the second line.
  - The Pt marker is the intersection of those two row-window fitted lines.
  - Standard Laminate Forecast keeps its existing standard fit logic.
  - Bumped web cache key to `app.js?v=20260612-u3-row-fit`.
- Updated iOS:
  - Added `CurveFitMode.standard` / `.u3` to `CurveChartView.swift`.
  - u3 cards/details pass `fitMode: .u3`; standard forecast charts remain
    unchanged.
- Numeric check with local u3 forecast sample
  `theta1=65`, `theta2=19`, `Case3`, `u3_bucket=2`:
  - predicted Pt: `8768.69`
  - u3 fit second window on the 192-point predicted curve: rows `25-28`
  - fitted-line intersection: displacement `0.01461`, force `8767.72`
- Verification:
  - `node --check src/frontend/dd-laminate/app.js`.
  - `swift test` in `ios/DDLaminateMVP`: 9 tests passed.
  - Local frontend `http://127.0.0.1:3000/` returned HTTP `200`.

## 2026-06-12 DD/u3 Forecast Type Clarification

The user clarified that the u3 source folders named `x-2` and `x-3`
(`x` = Case2/Case3/Case4) actually represent the previously separated
Type2/Type3 groups. They are not known inputs for a future prediction.

Decision:

- u3 Forecast should take only `theta1`, `theta2`, and `Case`.
- u3 Type2/Type3 should be predicted as an output when possible.
- Pt prediction remains the primary target; Type prediction is useful but
  secondary.
- The old UI selector for `u3-2` / `u3-3` was conceptually wrong because it
  asked the user to provide a label-like value before prediction.

Implementation:

- Trained new u3 forecast v2 models from `data/datasets/DD_u3_pt_v2/manifest.csv`
  without using `u3_bucket` as an input feature.
- Added an ExtraTrees Type2/Type3 classifier inside
  `models/dd_laminate_u3_forecast_v2/u3_forecast.joblib`.
- Updated the backend `/api/v1/dd-laminate/predict/u3-forecast` contract so
  `u3_bucket` is legacy/optional and not passed into the model.
- Updated web and iOS UI to remove the u3 Dataset selector and show predicted
  u3 Type plus Type confidence/probabilities.

Latest u3 forecast v2 metrics:

- Samples: 566
- ML ExtraTrees + PCA:
  - Pt MAE: `220.22 +/- 28.26` kips
  - Pt R2: `0.894`
  - Max displacement MAE: `0.00571`
  - Max force MAE: `439.09`
  - normalized curve RMSE: `0.0095`
  - Type accuracy: `0.972`
  - Type macro F1: `0.956`
- DL GointMLP:
  - Pt MAE: `180.05 +/- 39.44` kips
  - Pt R2: `0.913`
  - Max displacement MAE: `0.00263`
  - Max force MAE: `373.24`
  - normalized curve RMSE: `0.0106`

Verification:

- `python -m py_compile` for updated training, prediction, and backend files
  passed with `PYTHONPYCACHEPREFIX=/private/tmp/kyulai_pycache`.
- Direct CLI prediction with `theta1=65`, `theta2=19`, `Case3` returned
  predicted Type2, Pt `8768.69`, and a 192-point curve.
- FastAPI TestClient for `/predict/u3-forecast` returned HTTP `200`.
- Live local API `POST http://127.0.0.1:8000/api/v1/dd-laminate/predict/u3-forecast`
  returned HTTP `200` with predicted Type2, confidence `1.0`, Pt `8768.69`,
  and v2 model metrics.
- `node --check src/frontend/dd-laminate/app.js` passed.
- `swift test` in `ios/DDLaminateMVP`: 9 tests passed.

## 2026-06-15 ImperialAX Branding Pass

The user asked to change app-visible `ImperialAX` branding back to `ImperialAX`, while
keeping the option to return to `ImperialAX` later.

Implementation approach:

- Changed user-visible product/app text to `ImperialAX`.
- Kept internal package, folder, type, and route identifiers such as
  `ImperialAXMVP`, `ImperialAXModule`, `com.imperialax.app`, and `imperialax.com` URLs
  unchanged so the current builds, package IDs, and Cloudflare routes stay
  stable and the branding can be reversed later with a small text pass.
- Updated the unified module catalog API brand response from `ImperialAX` to
  `ImperialAX`.
- Updated iOS/Android app titles, login/workspace headers, access messages,
  share/report titles, and report image filenames where they were visible to
  users.
- Updated selected mobile docs that described the app name.

New Android debug APK artifacts:

- `artifacts/android/ImperialAX-debug.apk`
- `artifacts/android/ImperialAX-Laminate-debug.apk`
- `artifacts/android/ImperialAX-Injection-debug.apk`

Verification:

- `.venv/bin/pytest tests/backend/test_imperialax_modules.py`: 6 passed.
- `swift test` in `ios/ImperialAXMVP`: 4 passed.
- `swift test` in `ios/DDLaminateMVP`: 9 passed.
- `swift test` in `ios/InjectionMVP`: 8 passed.
- `gradle :app:assembleDebug` in `android/ImperialAXMVP`: build successful.
- `gradle :app:assembleDebug` in `android/DDLaminateMVP`: build successful.
- `gradle :app:assembleDebug` in `android/InjectionMVP`: build successful.
- `apksigner verify --verbose` passed for all three new `ImperialAX-*.apk`
  artifacts using APK Signature Scheme v2.

## 2026-06-15 ImperialAX App Icon Refresh

The user added ImperialAX logo files under `icons/ImperialAX` and asked to use only the
left atom-like symbol as the app icon, without the text.

Implementation:

- Used `icons/ImperialAX/ImperialAX Logo(ssy).png` as the source because it has the highest
  resolution.
- Cropped the left atom-like symbol and removed the text block.
- Flattened the icon to RGB/no-alpha PNG for iOS app icon compatibility.
- Saved reusable source icon:
  `icons/ImperialAX/ImperialAX_AppIcon_Source.png`.
- Updated the unified app icon assets:
  - iOS: `ios/ImperialAXMVPApp/ImperialAXMVPHost/Assets.xcassets/AppIcon.appiconset`
  - Android: `android/ImperialAXMVP/app/src/main/res/mipmap-*`
- Refreshed Android APK artifacts:
  - `artifacts/android/ImperialAX-debug.apk`
  - `artifacts/android/ImperialAX-debug.apk` kept as a compatibility filename
    with the same refreshed build.

Verification:

- `sips -g hasAlpha` confirmed the source, iOS 1024 icon, and Android xxxhdpi
  icon have no alpha channel.
- `gradle :app:assembleDebug` in `android/ImperialAXMVP`: build successful.
- `xcodebuild -project ios/ImperialAXMVPApp/ImperialAXMVPHost.xcodeproj -scheme
  ImperialAXMVPHost -destination 'generic/platform=iOS Simulator' build`:
  succeeded.
- `apksigner verify --verbose artifacts/android/ImperialAX-debug.apk`: passed using
  APK Signature Scheme v2.

## 2026-06-15 ImperialAX Demo Account Name Cleanup

The user noticed `ImperialAX Demo` still appearing inside the ImperialAX app.

Root cause:

- New code had already moved most visible branding to ImperialAX, but an installed
  app could still restore an older persisted auth session whose saved display
  name was `ImperialAX Demo`.

Implementation:

- Changed demo account display name from `ImperialAX Demo` to the neutral
  `Demo Account`.
- Updated backend demo-login response, iOS fallback session, Android fallback
  session, and iOS test fixtures.
- Added session-name normalization/migration:
  - iOS converts saved `ImperialAX Demo` or `ImperialAX Demo` to `Demo Account` when
    loading or saving sessions.
  - Android converts saved/server `ImperialAX Demo` or `ImperialAX Demo` to
    `Demo Account`.
- The only remaining `ImperialAX Demo` string is inside the migration mapping and
  should not be displayed.

Verification:

- `.venv/bin/pytest tests/backend/test_imperialax_modules.py`: 6 passed.
- `swift test` in `ios/ImperialAXMVP`: 4 passed.
- `gradle :app:assembleDebug` in `android/ImperialAXMVP`: build successful.
- Refreshed `artifacts/android/ImperialAX-debug.apk`.
- `apksigner verify --verbose artifacts/android/ImperialAX-debug.apk`: passed.
## 2026-06-15 DD u3 XAI First Pass

User asked whether XAI can be applied now and what information would help the
Physics Feature Pack.

Current conclusion:

- XAI is immediately possible for the current u3 forecast Tree model because
  `models/dd_laminate_u3_forecast_v2/u3_forecast.joblib` stores ExtraTrees
  scalar, curve, and type models plus feature names.
- First-pass XAI should explain the existing theta/case feature model; deeper
  physics explanations require retraining with CLT/ABD/lamination-parameter
  features.
- Existing `src/ml/dd_laminate/laminate_physics.py` already computes a base ABD
  feature vector for Case3/Case4, but Case2 and richer lamination descriptors
  still need to be added before retraining the Case2/3/4 u3 forecast models.

Implemented:

- Added `scripts/dd_u3_xai_report.py`.
- Generated `reports/dd_u3_xai_v1/u3_xai_report.md`.
- Generated `reports/dd_u3_xai_v1/u3_feature_importance.csv`.
- Generated `reports/dd_u3_xai_v1/u3_local_sensitivity.csv`.

First-pass finding from current model:

- Top global drivers are trigonometric/absolute angle features, especially
  `theta1_cos_2`, `theta2_cos_4`, `theta2_cos_2`, `abs_theta1`, and
  `abs_theta2`.
- Case one-hot features are currently low in native feature importance, which
  may mean the current learned response is dominated by angle descriptors, or
  that case effects are indirectly entangled with sampled angle/data
  distributions. This should be rechecked after adding physics features.

Information useful from the user/brother for Physics Feature Pack:

- Confirm exact stacking sequence expansion for Case2, Case3, Case4, and any
  future cases.
- Confirm material properties and units: E11, E22, G12, nu12, ply thickness,
  panel dimensions, boundary conditions, load direction, and whether values are
  constant across all simulations.
- Provide any Abaqus outputs beyond force-displacement if available: buckling
  modes, stress/strain fields, displacement fields, damage variables, element or
  nodal CSV/ODB exports, and whether Pt fitting line locations are saved.
- If only force-displacement CSV and transition_load.csv exist, that is still
  enough for the next physics-feature retraining pass.
## 2026-06-15 DD PPT Basis And Physics Feature Model

User pointed to `data/PPT/Final ver2.pptx` as the detailed Double-Double
Laminate basis used for the Abaqus simulations and asked to summarize/apply it.

PPT extraction summary:

- Problem setup: 6 in x 4 in flat rectangular panel, lateral simply-supported
  edges, x=0/a clamped, load from x=a.
- Material: Toray T800/3900S, ply thickness 0.0075 in, total 16 plies.
- Type rules:
  - Type 1: clear bilinear force-displacement curve; Pt from force-line
    intersection.
  - Type 2: force curve second region bends; Pt from average of force-plot and
    u3-plot intersections.
  - Type 3: force bilinear fit unreliable; Pt from u3-plot intersection.
- Cases 2/3/4 form PPT Pattern II: four-corner peak surface with a low center
  region, dominated by nonzero +/-45 degree angle families.
- Reported high-performing region is near theta1 ~= 44.13 deg and theta2 ~=
  -49.42 deg.
- Transition-load best among Case2/3/4: Case3, about 15,916.5 lbs.
- Weighted cost-function best among Case2/3/4: Case2, about 2.998788, using
  70% buckling / 30% flexural-rigidity proxy.

Implemented from PPT basis:

- Added `docs/DD_Laminate_PPT_Basis.md`.
- Updated `src/ml/dd_laminate/laminate_physics.py`:
  - Case2 stack support: `[[+t1/-t1/+t2/-t2]] x 4`.
  - Added `EXTENDED_PHYSICS_FEATURE_COLUMNS`.
  - Added `extended_physics_feature_vector()` with ABD terms, B-coupling,
    bending/membrane anisotropy, angle center/spread, balance/symmetry
    descriptors, and Case2/3/4 flags.
- Updated `src/ml/dd_laminate/train_u3_forecast_models.py`:
  - Existing `theta` feature set remains model-compatible.
  - New `theta_physics` feature set adds the extended physics pack.
  - Saved models now record `feature_builder`.
- Updated `src/ml/dd_laminate/predict_u3_forecast.py` so prediction chooses
  the saved feature builder automatically.
- Updated `scripts/dd_u3_xai_report.py` so XAI works for both `theta` and
  `theta_physics` model bundles.

New physics-feature model artifacts:

- `models/dd_laminate_u3_forecast_physics_v1/u3_forecast.joblib`
- `models/dd_laminate_u3_forecast_physics_v1/u3_forecast_goint.pt`
- `reports/dd_u3_forecast_physics_v1/u3_forecast_report.md`
- `reports/dd_u3_xai_physics_v1/u3_xai_report.md`
- `reports/dd_u3_xai_physics_v1/u3_feature_importance.csv`
- `reports/dd_u3_xai_physics_v1/u3_local_sensitivity.csv`

Validation/results:

- Python compile passed for laminate physics, u3 training, u3 prediction, and
  XAI script.
- Smoke check passed for Case2/Case3/Case4 physics feature vectors.
- Existing `theta` model prediction still works.
- `theta_physics` model trained on 566 u3 samples.
- Physics Tree model: Pt MAE 218.29 kips, Pt R2 0.913, Type accuracy 0.974,
  curve norm RMSE 0.0070.
- Physics GointMLP: Pt MAE 163.35 +/- 28.59 kips, Pt R2 0.926, max
  displacement MAE 0.00262, max force MAE 361.35, curve norm RMSE 0.0104.
- Physics XAI top global drivers now include interpretable laminate terms:
  `angle_min_abs`, `d11`, `a11_a22_ratio`, `a11`, `d12`, `d11_d22_ratio`,
  `d66`, and `bending_anisotropy`.

Important caveat:

- The physics model was trained as a separate artifact and does not yet replace
  the production DD web/app default model. Next UI/API step is to add the
  physics model as an optional or default model after checking visual behavior.

Follow-up:

- User approved installing `python-pptx`; installed `python-pptx==1.0.2` in the
  project venv and added it to `requirements-ml.txt`.
- Rechecked `data/PPT/Final ver2.pptx` with `python-pptx` to verify slide
  tables and grouped text. Main extracted results matched the earlier XML
  extraction.
- Updated `docs/DD_Laminate_PPT_Basis.md` with the extraction note and the
  slide-25 value caveat: table/repeated overview use Case2 cost best
  `2.998788`, while a nearby text object appears as `2.988788`.

## 2026-06-15 DD XAI Web/App Display

User asked to make the XAI content visible in the web and app so visitors can
understand why the laminate prediction behaves the way it does.

Implemented:

- Backend `src/backend/api/v1/dd_laminate.py`:
  - Added `XAIExplanation` / `XAIFeature` response models.
  - Added `u3_forecast_physics` to the u3 forecast model registry.
  - Added `/api/v1/dd-laminate/xai/u3/{model_key}`.
  - `POST /predict/u3-forecast` now includes `xai` for the original u3
    forecast and the new PPT/CLT physics-feature model when reports exist.
  - XAI reads `reports/dd_u3_xai_physics_v1/u3_feature_importance.csv` and
    maps key features like `angle_min_abs`, `d11`, `a11_a22_ratio`, `d12`,
    `d66`, and `bending_anisotropy` to readable explanations.
- Web DD page:
  - Added an XAI panel to both English and Korean pages.
  - u3 forecast results now show summary, method, feature set, top feature
    importance bars, and validation notes.
  - Bumped DD web asset query strings to `20260615-xai-panel` so browsers load
    the new CSS/JS instead of cached files.
- iOS DD app:
  - Added Codable XAI models.
  - u3 result detail screen now shows a "Why this prediction?" card with top
    feature drivers.
- Android unified app:
  - Added optional XAI decoding/rendering so future laminate responses with
    `xai` do not break and can show explanation cards.

Verification:

- `node --check src/frontend/dd-laminate/app.js` passed.
- Backend AST parse passed without writing `__pycache__`.
- Direct backend smoke for `u3_forecast_physics` returned Pt `10127.63`, Type
  `2`, and `xai=True`.
- Local server smoke passed:
  - `http://127.0.0.1:3000/` serves the new XAI panel markup and asset version.
  - `http://127.0.0.1:8000/api/v1/dd-laminate/xai/u3/u3_forecast_physics`
    returns the XAI report JSON.
- `swift test` in `ios/DDLaminateMVP` passed: 9 tests.
- Android `gradle :app:assembleDebug` did not run to code compilation because
  this Mac has no Java 17 runtime/toolchain configured.

Follow-up:

- User said XAI output was hard to read and asked for percent display.
- Updated web, iOS, and Android XAI feature rows so importance is displayed as
  percentage text, e.g. `Angle · 39.3%` instead of raw decimals like
  `0.393317`.
- Bumped DD web asset query strings to `20260615-xai-percent`.
- Verification:
  - `node --check src/frontend/dd-laminate/app.js` passed.
  - `swift test` in `ios/DDLaminateMVP` passed: 9 tests.
  - Local DD HTML serves `20260615-xai-percent`.

Clarification:

- User asked whether there is also a GointMLP XAI model.
- Current state: u3 GointMLP models exist, including
  `models/dd_laminate_u3_forecast_physics_v1/u3_forecast_goint.pt`, but the
  generated XAI artifacts and API display currently explain the Tree/joblib
  u3 forecast bundles only.
- To add GointMLP XAI later, use neural-network methods such as permutation
  importance, gradient saliency, integrated gradients, or occlusion sensitivity
  over the same theta/physics feature set.

## 2026-06-15 DD GointMLP XAI

User asked to create GointMLP XAI as well and rename the models so Tree XAI and
GointMLP XAI are not confused.

Implemented:

- Updated `scripts/dd_u3_xai_report.py`:
  - Existing Tree mode remains `--model-kind tree`.
  - Added `--model-kind goint`.
  - GointMLP XAI uses feature occlusion sensitivity: each normalized feature is
    masked to its training mean, then Pt/max-value and curve-head movement is
    measured.
  - Still writes `u3_feature_importance.csv`, `u3_local_sensitivity.csv`, and
    `u3_xai_report.md`.
- Generated GointMLP physics XAI artifacts:
  - `reports/dd_u3_xai_goint_physics_v1/u3_feature_importance.csv`
  - `reports/dd_u3_xai_goint_physics_v1/u3_local_sensitivity.csv`
  - `reports/dd_u3_xai_goint_physics_v1/u3_xai_report.md`
- Top GointMLP + Physics XAI global drivers:
  - `angle_min_abs` 8.54%
  - `angle_abs_std` 4.46%
  - `a66_geom_ratio` 3.89%
  - `theta2_cos_4` 3.49%
  - `theta1_cos_4` 2.99%
  - `bending_anisotropy` 2.69%
- Renamed/clarified u3 model labels in API/UI:
  - `u3 Forecast - Tree (Theta)`
  - `u3 Forecast - Tree + Physics XAI`
  - `u3 Forecast - GointMLP (Theta)`
  - `u3 Forecast - GointMLP + Physics XAI`
- Added backend model key:
  - `u3_forecast_goint_physics`
  - Path: `models/dd_laminate_u3_forecast_physics_v1/u3_forecast_goint.pt`
- `/predict/u3-forecast` now serves XAI for `u3_forecast_goint_physics`.
- `/xai/u3/u3_forecast_goint_physics` now returns the GointMLP XAI report.
- Updated web/iOS/Android display aliases and Korean text for the new labels.
- Bumped DD web asset query string to `20260615-goint-xai`.

Verification:

- AST parse passed for `src/backend/api/v1/dd_laminate.py` and
  `scripts/dd_u3_xai_report.py`.
- `node --check src/frontend/dd-laminate/app.js` passed.
- `swift test` in `ios/DDLaminateMVP` passed: 9 tests.
- Local API `/models` returns all four renamed u3 forecast models.
- Local API `/xai/u3/u3_forecast_goint_physics` returns XAI JSON.
- Local API prediction smoke:
  - Input: theta1 `30`, theta2 `-30`, Case3,
    model `u3_forecast_goint_physics`.
  - Result: Pt `10649.18`, label `u3 Forecast - GointMLP + Physics XAI`,
    `xai=True`.

## 2026-06-15 DD XAI Retraining v2

User noted that when XAI is applied, retraining may be needed and asked to
proceed if so. Decision: the XAI display itself is post-hoc, but the physics
feature model is the part that truly requires training. To make the lineage
clean, retrained the physics-feature u3 forecast models into v2 artifacts
without overwriting v1.

New model artifacts:

- `models/dd_laminate_u3_forecast_physics_v2/u3_forecast.joblib`
- `models/dd_laminate_u3_forecast_physics_v2/u3_forecast_goint.pt`
- `models/dd_laminate_u3_forecast_physics_v2/u3_forecast_metrics.json`
- `models/dd_laminate_u3_forecast_physics_v2/u3_forecast_goint_metrics.json`

New report/XAI artifacts:

- `reports/dd_u3_forecast_physics_v2/u3_forecast_report.md`
- `reports/dd_u3_xai_physics_v2/u3_feature_importance.csv`
- `reports/dd_u3_xai_physics_v2/u3_local_sensitivity.csv`
- `reports/dd_u3_xai_physics_v2/u3_xai_report.md`
- `reports/dd_u3_xai_goint_physics_v2/u3_feature_importance.csv`
- `reports/dd_u3_xai_goint_physics_v2/u3_local_sensitivity.csv`
- `reports/dd_u3_xai_goint_physics_v2/u3_xai_report.md`

Retraining results:

- Dataset: `data/datasets/DD_u3_pt_v2/manifest.csv`
- Samples: 566
- Feature set: `theta_physics`
- Tree/ExtraTrees:
  - Pt MAE: `218.29 +/- 5.08`
  - Pt R2: `0.913`
  - Type accuracy: `0.974`
  - Type macro F1: `0.960`
  - Curve normalized RMSE: `0.0070`
- GointMLP:
  - Pt MAE: `163.35 +/- 28.59`
  - Pt R2: `0.926`
  - Max. Displacement MAE: `0.00262`
  - Max. Force MAE: `361.35`
  - Curve normalized RMSE: `0.0104`

API switched to v2:

- `u3_forecast_physics` now uses
  `models/dd_laminate_u3_forecast_physics_v2/u3_forecast.joblib`
  and `reports/dd_u3_xai_physics_v2/u3_feature_importance.csv`.
- `u3_forecast_goint_physics` now uses
  `models/dd_laminate_u3_forecast_physics_v2/u3_forecast_goint.pt`
  and `reports/dd_u3_xai_goint_physics_v2/u3_feature_importance.csv`.

Verification:

- Backend syntax parse passed.
- Local function smoke:
  - Tree + Physics XAI first XAI importance: `0.393317`.
  - GointMLP + Physics XAI first XAI importance: `0.08538`.
  - GointMLP + Physics XAI prediction for theta1 `30`, theta2 `-30`,
    Case3: Pt `10649.18`, `xai=True`.
- Local API `/models` returns v2 paths for both physics XAI models.
- Local API prediction smoke:
  - `u3_forecast_physics`: Pt `10127.63`, label
    `u3 Forecast - Tree + Physics XAI`.
  - `u3_forecast_goint_physics`: Pt `10649.18`, label
    `u3 Forecast - GointMLP + Physics XAI`.

## 2026-06-15 DD XAI Compact UI

User said the XAI section was hard to read because each feature consumed too
much space.

Implemented:

- Web DD XAI feature rows are now compact:
  - Removed always-visible long per-feature explanation text.
  - Kept feature label, category/percentage badge, and compact importance bar.
  - Long explanation remains available as a hover tooltip via `title`.
  - Reduced XAI summary/method typography and spacing.
  - Added mobile fallback so feature rows stack cleanly on narrow screens.
- iOS DD app:
  - Removed always-visible feature explanation text from the XAI card.
  - Feature rows now show label, category/percentage, and progress bar only.
- Android app:
  - Removed per-feature explanation paragraph under each XAI metric box.
- Bumped DD web asset query string to `20260615-xai-compact`.

Verification:

- `node --check src/frontend/dd-laminate/app.js` passed.
- `swift test` in `ios/DDLaminateMVP` passed: 9 tests.
- Local DD HTML serves `20260615-xai-compact`.

## 2026-06-15 DD GointMLP Theta XAI + Korean XAI Text

User asked whether `Tree (Theta)` already had XAI and why
`GointMLP (Theta)` did not show explanations. They also asked for XAI
explanations to be translated when the Korean page is selected.

Findings:

- `Tree (Theta)` already had XAI through `u3_forecast`.
- `GointMLP (Theta)` did not have its own XAI report/loader.
- `GointMLP + Physics XAI` was separate and did not cover the plain
  theta/case GointMLP model.

Implemented:

- Generated a new GointMLP theta/case XAI report from
  `models/dd_laminate_u3_forecast_v2/u3_forecast_goint.pt`.
- New artifacts:
  - `reports/dd_u3_xai_goint_v2/u3_feature_importance.csv`
  - `reports/dd_u3_xai_goint_v2/u3_local_sensitivity.csv`
  - `reports/dd_u3_xai_goint_v2/u3_xai_report.md`
- Backend now loads XAI for `u3_forecast_goint`.
- Added feature explanations for theta periodic features such as
  `cos(2θ)`, `cos(4θ)`, `sin(4θ)`, `|θ|`, `|θ₁ - θ₂|`, and `θ₁ × θ₂`.
- Web Korean mode now localizes XAI summaries, method labels, feature-set
  names, feature labels, categories, notes, and common explanations.
- iOS result detail XAI card now localizes feature-set names, categories,
  and expanded XAI labels/explanations.
- Bumped DD web asset query string to `20260615-xai-ko-goint`.

GointMLP Theta XAI top drivers:

- `cos(4θ₂)`: `16.73%`
- `cos(4θ₁)`: `15.86%`
- `|θ₁|`: `8.37%`
- `cos(2θ₂)`: `8.24%`
- `|θ₂|`: `8.13%`
- `cos(2θ₁)`: `7.50%`

Verification:

- GointMLP theta/case XAI generation completed successfully.
- Backend AST parse passed.
- Web JS syntax check passed.
- Direct loader smoke:
  - `u3_forecast`: `tree True cos(2θ₁)`
  - `u3_forecast_goint`: `goint True cos(4θ₂) 0.167251`
- Local API `/api/v1/dd-laminate/xai/u3/u3_forecast` returns Tree Theta
  XAI.
- Local API `/api/v1/dd-laminate/xai/u3/u3_forecast_goint` returns
  GointMLP Theta XAI.
- Local API `/predict/u3-forecast` with model `u3_forecast_goint` includes
  the `xai` block in the prediction response.
- `swift test` in `ios/DDLaminateMVP` passed: 9 tests.
- Local Korean DD HTML serves `20260615-xai-ko-goint`.

Clarification for model naming:

- `Theta` models do not use raw `theta1` and `theta2` only. They use 19
  theta/case-derived features:
  `theta1`, `theta2`, absolute/sum/difference/product terms,
  sin/cos periodic descriptors, and Case2/Case3/Case4 one-hot flags.
- `Physics XAI` models are separate retrained models with a different input
  feature set. They use the same 19 theta/case features plus 47 PPT/CLT-based
  laminate physics descriptors, for 66 total features.
- Physics descriptors include ABD stiffness terms, A/D ratios, coupling norms,
  ply count, total thickness, panel aspect/slenderness, B-matrix terms,
  membrane/bending anisotropy, DD angle center/spread, stack symmetry/balance,
  and case flags.
- Therefore `Theta` vs `Physics XAI` is not only a different explanation layer;
  it is a different trained feature space. XAI explains the feature space used
  by each selected model.

## 2026-06-15 DD XAI Feature Description Restore

User clarified that the compact XAI UI went too far: each feature still needs
to show both its influence percentage and what the feature means. The previous
compact pass had hidden feature explanations behind hover/tooltips, which made
the XAI section much less useful.

Implemented:

- Web DD XAI feature cards now show:
  - feature label,
  - category + percentage,
  - percent bar,
  - concise feature meaning below the percent bar.
- Kept the card compact, but restored visible explanation text.
- Korean web mode uses the existing translated feature explanations.
- iOS DD XAI feature rows now also show the feature explanation below the
  progress bar.
- Added missing Korean iOS translations for the common theta and physics
  feature explanations.
- Bumped DD web asset query string to `20260615-xai-desc`.

Verification:

- `node --check src/frontend/dd-laminate/app.js` passed.
- Backend AST parse passed.
- `swift test` in `ios/DDLaminateMVP` passed: 9 tests.

## 2026-06-15 Laminate Forecast Physics XAI Models

User requested the same XAI direction used for u3 Forecast to be applied to
Laminate Forecast as well, for both ML and DL models. The old non-XAI models
must remain available separately, while web/app defaults should show the XAI
models.

Implemented:

- Added `src/ml/dd_laminate/response_feature_sets.py` for Laminate Forecast
  feature construction.
- Added PPT/CLT physics-augmented Laminate Forecast models:
  - `models/dd_laminate_response_physics_xai_v1/response_surrogate.joblib`
  - `models/dd_laminate_response_goint_physics_xai_v1/response_goint.pt`
- Added training/report scripts:
  - `scripts/dd_response_physics_xai_train.py`
  - `scripts/dd_response_xai_report.py`
- Added XAI reports:
  - `reports/dd_response_xai_physics_v1/response_feature_importance.csv`
  - `reports/dd_response_xai_physics_v1/response_local_sensitivity.csv`
  - `reports/dd_response_xai_physics_v1/response_xai_report.md`
  - `reports/dd_response_xai_goint_physics_v1/response_feature_importance.csv`
  - `reports/dd_response_xai_goint_physics_v1/response_local_sensitivity.csv`
  - `reports/dd_response_xai_goint_physics_v1/response_xai_report.md`
- Backend model list now keeps both model families:
  - XAI defaults:
    `response_surrogate_physics`, `response_goint_physics`
  - Old non-XAI models:
    `response_surrogate`, `response_goint`
- Web defaults and labels now show:
  - `Laminate Forecast - Tree + Physics XAI`
  - `Laminate Forecast - GointMLP + Physics XAI`
  - `Laminate Forecast - Tree (Theta)`
  - `Laminate Forecast - GointMLP (Theta)`
- iOS DD app now defaults to `response_surrogate_physics`, decodes XAI, and
  shows the same compact XAI card on Laminate Forecast and u3 result screens.
- Android DD MVP now parses the response XAI block and displays a compact XAI
  card with percent bars and feature explanations.
- Windows bundle packaging includes the new response XAI model and report
  directories.

Training results:

- Tree + Physics XAI:
  - Type accuracy: `0.9433 +/- 0.0181`
  - Type macro F1: `0.9364 +/- 0.0211`
  - Pt MAE: `434.98`
  - Curve normalized RMSE: `0.00714`
- GointMLP + Physics XAI:
  - Type accuracy: `0.9456 +/- 0.0181`
  - Type macro F1: `0.9438 +/- 0.0183`
  - Pt MAE: `663.09`
  - Curve normalized RMSE: `0.02386`

Default/runtime behavior verified:

- `/api/v1/dd-laminate/models` response order:
  - Response models:
    `response_surrogate_physics`, `response_goint_physics`,
    `response_surrogate`, `response_goint`
  - u3 models:
    `u3_forecast_physics`, `u3_forecast_goint_physics`,
    `u3_forecast`, `u3_forecast_goint`
- `/predict/response` with no model now defaults to
  `response_surrogate_physics` and returns an XAI block.
- `/predict/response` with old `response_surrogate` still works and returns
  `xai: null`, confirming the non-XAI model is preserved separately.

Verification:

- Python compile passed for the backend, response predictors, feature builder,
  and new training/XAI scripts.
- `node --check src/frontend/dd-laminate/app.js` passed.
- API smoke passed:
  `response_surrogate_physics`, label
  `Laminate Forecast - Tree + Physics XAI`, XAI returned with top feature
  `Minimum |θ|`.
- `swift test` in `ios/DDLaminateMVP` passed: 9 tests.
- Android DD MVP Gradle compile could not run on this Mac because no Java
  runtime/JDK 17 is installed:
  `Unable to locate a Java Runtime`.

## 2026-06-15 DD XAI Korean Feature Translation Coverage

User noticed that some XAI feature names/descriptions were still appearing in
English in Korean mode, especially `A12 membrane coupling`.

Implemented:

- Expanded backend `FEATURE_EXPLANATIONS` so more CLT/PPT physics features get
  readable labels instead of fallback raw names:
  - `A12 membrane coupling`
  - `A22 membrane stiffness`
  - `A66 shear stiffness`
  - `A16/A26 extension-shear coupling`
  - `B11/B22/B12/B66 membrane-bending coupling`
  - `B16/B26` and `D16/D26 bend-twist coupling`
  - `A/B/D-matrix coupling norm`
  - stack balance, symmetry mismatch, DD angle center, panel geometry, and
    Case flag features.
- Added Korean web translations for the expanded XAI labels and explanations.
- Added the same Korean iOS translations in `XAIExplanationCard`.

Verification:

- Backend Python compile passed.
- Web `node --check src/frontend/dd-laminate/app.js` passed.
- iOS `swift test` passed: 9 tests.

## 2026-06-15 ImperialAX Web Login

ImperialAX unified web workspace now has a browser login flow aligned with the
iOS/Android account MVP.

Implemented:

- `src/frontend/imperialax/index.html`
  - Login-first layout for ImperialAX.
  - Workspace is hidden until a session exists.
  - Account and module access dialogs were added.
- `src/frontend/imperialax/app.js`
  - Uses `POST /api/v1/modules/auth/demo-login`.
  - Stores the demo auth session in `localStorage` under
    `imperialax.auth.session.v1`.
  - Sends `Authorization: Bearer <token>` to `GET /api/v1/modules/me`.
  - Supports local fallback demo sessions for `demo@imperialax.com` and
    `danlee@imperialax.com`.
  - Adds request-access behavior through
    `POST /api/v1/modules/request-access`.
- `src/frontend/imperialax/styles.css`
  - Added responsive login, account band, modal, and access-list styling.
- `DESIGN.md`
  - Updated source-of-truth surface list to include the ImperialAX web workspace.
- Backend ImperialAX branding cleanup:
  - `src/backend/api/v1/modules.py` response brand, demo user display names,
    error messages, and access-request copy now say `ImperialAX`.
  - `src/backend/imperialax_app.py` FastAPI title/description now say
    `ImperialAX Platform API`.

Verification:

- `node --check src/frontend/imperialax/app.js` passed.
- `.venv/bin/pytest tests/backend/test_imperialax_modules.py` passed: 6 tests.
- Local server on `http://127.0.0.1:8011` returned ImperialAX-branded login,
  module, request-access, and health responses.

## 2026-06-15 - DD XAI list and tab-state cleanup

User requested two DD Laminate UI adjustments:

- XAI feature importance should not show every feature at once.
- Switching from Laminate Forecast results to the u3 Forecast tab should clear
  the previous result instead of leaving stale values visible.

Changes:

- DD web `renderXai()` now sorts features by importance, shows the top 10 by
  default, and places the remaining features inside a collapsible "more"
  section.
- The same shared XAI renderer is used for both Laminate Forecast and u3
  Forecast, so both views get the top-10/default behavior.
- DD web mode-tab clicks now reset the prediction/result panel when changing
  modes, preventing Laminate Forecast results from remaining visible after
  switching to u3 Forecast.
- Added compact styling for the XAI "more features" disclosure.
- Bumped DD web asset key to `20260615-xai-more-reset`.

Verification:

- `node --check src/frontend/dd-laminate/app.js` passed.

## 2026-06-15 Compact Physics Feature Pack v2

User noticed that the Physics XAI feature pack had duplicate/static features.

Implemented:

- Added `COMPACT_PHYSICS_FEATURE_COLUMNS` and
  `compact_physics_feature_vector()` in `src/ml/dd_laminate/laminate_physics.py`.
- Added `theta_physics_v2` support for Laminate Forecast response features.
- Added `theta_physics_v2` support for u3 Forecast features.
- Updated Laminate Forecast physics-XAI training script to accept
  `--feature-set theta_physics_v2`.
- Trained new compact models without overwriting v1:
  - `models/dd_laminate_response_physics_xai_v2`
  - `models/dd_laminate_response_goint_physics_xai_v2`
  - `models/dd_laminate_u3_forecast_physics_v3`
- Generated new XAI reports:
  - `reports/dd_response_xai_physics_v2`
  - `reports/dd_response_xai_goint_physics_v2`
  - `reports/dd_u3_xai_physics_v3`
  - `reports/dd_u3_xai_goint_physics_v3`
- Added the new compact models to the DD API model registry as selectable
  options rather than replacing the existing defaults.
- Added new model/report paths to the Windows bundle packaging script.

Feature count:

- Laminate Forecast Physics XAI: 58 -> 35 features.
- u3 Forecast Physics XAI: 66 -> 43 features.

Training results:

- Laminate Forecast Tree compact v2:
  - Type accuracy: 0.9422
  - Macro F1: 0.9372
  - Pt MAE: 438.15 kips
  - Curve normalized RMSE: 0.00701
- Laminate Forecast GointMLP compact v2:
  - Type accuracy: 0.9400
  - Macro F1: 0.9362
  - Pt MAE: 801.35 kips
  - Curve normalized RMSE: 0.03223
- u3 Forecast Tree compact v2:
  - Best scalar model: ExtraTrees
  - Pt MAE: 223.79 kips
  - Type accuracy: 0.9753
- u3 Forecast GointMLP compact v2:
  - Pt MAE: 168.65 kips
  - Pt R2: 0.9226
  - Curve normalized RMSE: 0.01018

Interpretation:

- Compact v2 is much cleaner for XAI.
- Laminate Forecast Tree performance is nearly unchanged from v1.
- Laminate Forecast GointMLP got worse than v1, so keep v1 available.
- u3 compact v2 remains strong; GointMLP is still better than Tree for Pt MAE.

Follow-up:

- User asked why Laminate Forecast GointMLP compact v2 got worse.
- Compared v1/v2 XAI and trained probe variants.
- Removed features with nonzero v1 GointMLP importance accounted for:
  - Combined importance: 27.88%
  - Scalar/Pt importance: 23.92%
  - Curve importance: 27.65%
  - Type importance: 32.07%
- Full 58-feature model reproduced v1 exactly, confirming the difference was
  feature-set driven, not random training drift.
- Built a GointMLP-specific `theta_physics_nn_v2` feature pack:
  - 47 features.
  - Keeps compact physics descriptors.
  - Restores selected neural basis terms:
    `a66_geom_ratio`, `b11`, `b22`, `b12`, `b66`,
    `b11_d11_ratio`, `b22_d22_ratio`, `dd_angle_center`,
    `dd_angle_spread`, `case2_flag`, `case3_flag`, `case4_flag`.
  - Still removes static/zero descriptors such as panel geometry constants,
    `a16`, `a26`, `a_coupling_norm`, `angle_mean`,
    `stack_balance_sin_sum`, and `case_pattern_ii`.
- Trained final hidden-96 NN-friendly GointMLP:
  - Model path: `models/dd_laminate_response_goint_physics_nn_v2`
  - XAI path: `reports/dd_response_xai_goint_physics_nn_v2`
  - Feature builder: `theta_physics_nn_v2`
  - Input dim: 47
  - Type accuracy: 0.9389
  - Macro F1: 0.9383
  - Pt MAE: 661.41 kips
  - Curve normalized RMSE: 0.02131
- This slightly improves Pt MAE over the original 58-feature GointMLP v1
  (663.09 kips), while using fewer and more explainable features.

UI cleanup:

- User said the Laminate Forecast model dropdown had too many models.
- Web DD now filters the Laminate Forecast model select to primary models only:
  - `response_surrogate_physics_v2`
  - `response_goint_physics_nn_v2`
- Legacy/experimental response models remain available in the backend/API for
  comparison, but they are hidden from the normal web dropdown.
- Display labels were shortened:
  - `Tree + Compact XAI`
  - `GointMLP + NN-Friendly XAI`
- Web asset cache key bumped to `20260615-model-cleanup`.

Third follow-up:

- User noticed that forcing both red slope guides through `Predicted Pt` made
  the slopes collapse visually into almost one line.
- Revised the chart definition:
  - The red dashed two-line guide is again a visual bilinear fit/intersection
    that explains the predicted curve shape.
  - The red `Predicted Pt` dot/label is now a separate marker placed on the
    predicted curve at the scalar `predicted_pt` force.
  - The guide kink and the predicted marker intentionally may have different
    coordinates; this avoids hiding the two-slope shape while keeping the Pt
    number consistent with the metric card.
- Applied the separation to:
  - Web DD chart: `buildBilinearFit()` returns both `kink` and
    `predictedPoint`; drawing uses `predictedPoint` for the dot/label.
  - iOS DD chart: `BilinearFit` now includes optional `predictedPoint`, and
    the dot uses it when available.
  - Android DD MVP chart: same `predictedPoint` separation.
- Bumped DD web asset key to `20260615-pt-separate`.
- Verification:
  - `node --check src/frontend/dd-laminate/app.js` passed.
  - `swift test` in `ios/DDLaminateMVP` passed: 9 tests.
  - Local static server serves `styles.css?v=20260615-pt-separate` and
    `app.js?v=20260615-pt-separate`.
  - `git diff --check` passed for the touched DD chart/cache/memory files.
  - Android compile was attempted with system Gradle, but this Mac has no Java
    17 toolchain configured for `android/DDLaminateMVP`.

Fourth follow-up:

- User asked whether the two-slope calculation can stay as-is, while moving
  the two guide lines as much as possible toward `Predicted Pt`.
- Updated the standard Laminate Forecast chart rule:
  - Left/right slope values are still computed from the visual bilinear
    fit/envelope method.
  - After the slopes are computed, the final two red dashed guide lines are
    translated so both pass through the predicted curve point at scalar
    `predicted_pt`.
  - This preserves two distinct slope angles while making the line crossing
    align with the displayed `Predicted Pt`.
- Applied to web, iOS DD chart, and Android DD MVP chart.
- Bumped DD web asset key to `20260615-pt-slope-anchor`.

Fifth follow-up:

- User rejected the slope-translation experiment because the slope guide itself
  should stay in its fitted position.
- Reverted the standard Laminate Forecast chart behavior back to the previous
  separated design:
  - Red dashed slope guides use the visual bilinear fit/intersection position.
  - `Predicted Pt` remains a separate red dot/label on the predicted curve.
  - The slopes are not translated to pass through the predicted point.
- Applied the rollback to web, iOS DD chart, and Android DD MVP chart.
- Bumped DD web asset key to `20260615-pt-separate-restore`.

Sixth follow-up:

- User noted that the two red slope lines visibly meet at one point, but that
  point differs from the red model `Predicted Pt` marker.
- Clarified the web chart by making both meanings visible:
  - Red circle/label remains `Predicted Pt`, the model scalar Pt placed on the
    predicted curve.
  - Purple diamond/label is now `Fit intersection`, the visual crossing point
    of the two linear fit guides.
  - The legend now names `Fit intersection` instead of the vague kink line.
- This keeps the slope fit intact while preventing viewers from assuming the
  two points are the same quantity.
- Bumped DD web asset key to `20260615-pt-fit-vs-predicted`.

Seventh follow-up:

- User asked to apply the same `Predicted Pt` vs `Fit intersection`
  distinction to u3.
- Updated u3 chart handling:
  - Web `buildU3BilinearFit()` now receives `predicted_pt` and returns
    `predictedPoint` from the predicted curve.
  - u3 web charts now show red `Predicted Pt` and purple `Fit intersection`
    separately when the points differ, using the same legend as Laminate
    Forecast.
  - iOS u3 `CurveChartView` now passes `predictedPt` into
    `buildU3BilinearFit()` so the red marker uses the model Pt instead of the
    fit intersection.
- Bumped DD web asset key to `20260615-u3-fit-vs-predicted`.

## 2026-06-15 XAI Feature Density Cleanup

User noted that the XAI feature explanations were shown as separate large
cards, making it hard to inspect all features at once.

Implemented:

- Web DD XAI panel:
  - Replaced per-feature cards with one compact feature list.
  - Removed the `top_features.slice(0, 6)` display cap; all API-provided
    features are rendered.
  - Each row now shows feature label, category pill, short explanation, a
    compact percentage value, and a thin importance bar.
  - Bumped DD web asset key to `20260615-xai-compact-list`.
- iOS DD app:
  - Reworked `XAIExplanationCard` from large feature cards into compact rows.
  - Removed the `.prefix(5)` cap so all provided features are visible.
- Android DD MVP and unified Android Laminate screen:
  - Replaced metric-box style XAI feature cards with compact rows.
  - Removed the `.take(5)` cap and kept the feature explanation visible.

Verification:

- `node --check src/frontend/dd-laminate/app.js` passed.
- Local static server serves `styles.css?v=20260615-xai-compact-list` and
  `app.js?v=20260615-xai-compact-list`.
- `swift test` in `ios/DDLaminateMVP` passed: 9 tests.
- `git diff --check` passed for the touched web/iOS/Android/memory files.
- Android Gradle compile was attempted, but this Mac still lacks the Java 17
  toolchain required by `android/DDLaminateMVP`.

## 2026-06-15 Live Local XAI Fix

User noticed that XAI percentages did not change between predictions. This was
correct: the API was returning static global importance CSV rows from
`reports/.../feature_importance.csv`, so the UI could not change when
theta/case inputs changed.

Implemented:

- Backend DD API now computes local XAI during prediction for Laminate Forecast
  and u3 Forecast XAI models.
- For the current theta/case input, the API builds the model feature vector,
  masks one feature at a time, re-evaluates the model output, and scores how
  much Type/scalar/curve outputs move.
- The local score is blended with a small global prior so known global drivers
  remain visible, but the displayed percentages now change by input.
- Applied to:
  - `response_surrogate_physics`
  - `response_goint_physics`
  - `u3_forecast_physics`
  - `u3_forecast_goint_physics`
  - the theta-only u3 XAI variants when selected.
- Backend still supports static global XAI through `/xai/u3/{model_key}` for
  model-level explanation, but prediction responses now use live local XAI.
- Added caching/one-time model setup inside local XAI so GointMLP models are
  not rebuilt once per feature.
- Added Korean UI translations for the new local XAI method/notes.
- Bumped DD web asset key to `20260615-local-xai`.
- Restarted the DD API server on port `8000`.

Verification:

- `PYTHONPYCACHEPREFIX=/private/tmp/kyulai_pycache .venv/bin/python -m py_compile src/backend/api/v1/dd_laminate.py` passed.
- `node --check src/frontend/dd-laminate/app.js` passed.
- `git diff --check` passed for the touched backend/frontend/memory files.
- FastAPI TestClient confirmed different XAI rankings/percentages for two
  different inputs on Tree and GointMLP, Laminate Forecast and u3 Forecast.
- Live API confirmed different XAI for:
  - `theta1=-29`, `theta2=74`, `Case4`
  - `theta1=65`, `theta2=19`, `Case3`
- Live server health check `/api/v1/dd-laminate/models` returned OK after
  restart.
- API smoke for `response_goint_physics` now returns:
  - `a12 => A12 membrane coupling`
  - explanation:
    `In-plane membrane coupling term from the laminate A matrix.`
- Static search confirmed Korean mappings:
  - `A12 membrane coupling` -> `A12 막 커플링`
  - `In-plane membrane coupling term...` ->
    `적층 A 행렬의 평면 내 막 커플링 항입니다.`

## 2026-06-15 Laminate Forecast Pt Chart Consistency

User noticed that the `Predicted Pt` metric in Laminate Forecast and the value
shown inside the predicted curve graph did not match.

Root cause:

- The metric card used the API/model scalar value `predicted_pt`.
- The graph label used `bilinearFit.kink.force`, a force value recomputed from
  the visual two-line fit/intersection.
- Because Laminate Forecast predicts Pt and the surrogate curve with separate
  model heads, the visual bilinear intersection can differ from the scalar Pt.
  The UI then mislabeled the visual-fit value as `Predicted Pt`.

Implemented:

- Web DD chart:
  - Standard Laminate Forecast `buildBilinearFit()` now anchors the visual
    kink force and both guide lines to `predicted_pt`.
  - The graph label and metric card therefore use the same Pt force value.
- iOS DD chart:
  - Standard `ChartLayout.buildBilinearFit()` now anchors `kinkForce` and both
    guide lines to `predictedPt`.
- u3-specific fit logic was not changed because it uses a separate early-kink
  definition.
- Android DD MVP already anchored the standard fit to `predictedPt`; no change
  was needed there.

Verification:

- `node --check src/frontend/dd-laminate/app.js` passed.
- `swift test` in `ios/DDLaminateMVP` passed: 9 tests.

Follow-up:

- User still saw a mismatch after the first fix:
  metric `17,964.27` vs graph label `17,309.57`.
- Tightened the web drawing code so the graph label explicitly formats
  `predictedPtValue`, not `bilinearFit.kink.force`.
- Bumped DD HTML asset query strings from `20260615-response-xai` to
  `20260615-pt-sync` so browsers stop using the cached chart code.
- Verified local static server now serves:
  - `styles.css?v=20260615-pt-sync`
  - `app.js?v=20260615-pt-sync`
- Verified served `app.js` includes:
  - `const displayPt = Number.isFinite(Number(predictedPtValue)) ...`
  - `const ptValue = formatMetric(displayPt, 2)`

Second follow-up:

- User clarified that the red point itself should be the predicted point on the
  predicted curve, and the two red slope guides should be adjusted to pass
  through that point.
- Updated standard Laminate Forecast chart logic:
  - Web: `buildBilinearFit()` now anchors `kinkX` to
    `pointAtForce(points, predictedPt).displacement` and `kinkForce` to
    `predictedPt`.
  - iOS: `ChartLayout.buildBilinearFit()` now uses the same curve-on-Pt anchor.
  - Android DD MVP: `CurveChartView.kt` now starts `kinkX` from
    `ptOnCurve.displacement` instead of solving it from the first fitted slope.
- The two red slope guide lines are recomputed to pass through the anchored
  predicted Pt point.
- Bumped DD web asset key to `20260615-pt-anchor`.

Verification:

- Web `node --check src/frontend/dd-laminate/app.js` passed.
- Local static server serves:
  - `styles.css?v=20260615-pt-anchor`
  - `app.js?v=20260615-pt-anchor`
- Served JS contains:
  - `const kinkX = clampNumber(ptOnCurve.displacement, minKinkX, maxKinkX)`
  - `const displayPt = Number.isFinite(Number(predictedPtValue)) ...`
  - `const ptValue = formatMetric(displayPt, 2)`
- iOS `swift test` passed: 9 tests.

## 2026-06-17 No-Curve CSV Model Upgrade Review

User provided `codex_model_upgrade_no_curve_csv_prompt.md` for critical review.
The detailed review summary was written separately because this session memory
file is already long:

- `docs/model-upgrade-no-curve-csv-review-summary-2026-06-17.md`

Key conclusions:

- Keep Curve CSV classifier work out of scope for this model-upgrade pass.
- Current strongest Laminate Forecast baseline is `response_surrogate_physics_v2`
  with 900 samples, compact physics features, Type accuracy around 0.942,
  macro F1 around 0.937, Pt MAE around 438, and normalized curve RMSE around
  0.007.
- GointMLP physics variants are not clearly better than the tree baseline on
  scalar and curve metrics, even though Type metrics are close.
- `xgboost`, `lightgbm`, `catboost`, and `tabpfn` are not installed in the
  current environment; challenger scripts should skip those gracefully unless
  optional research dependencies are intentionally added.
- Recommended next step is a research-only Laminate Forecast challenger
  evaluation harness before any backend registry or UI default changes.

## 2026-06-17 Laminate Forecast Tabular Challenger Suite v1

Implemented the first no-Curve-CSV model-upgrade pass:

- Added design doc:
  - `docs/design/dd_laminate_model_upgrade_no_curve_csv.md`
- Added evaluation script:
  - `scripts/dd_response_tabular_challengers_train.py`
- Generated research artifacts:
  - `models/dd_laminate_response_tabular_challengers_v1/`
  - `reports/dd_response_tabular_challengers_v1/model_comparison.md`
  - `reports/dd_response_tabular_challengers_v1/model_comparison.json`

Evaluation setup:

- Dataset: `data/datasets/DD_cases_2_3_4_curated_v1`
- Feature set: `theta_physics_v2`
- Samples: 900
- Validation: 5-fold `GroupKFold` by theta pair
- Reference models: `response_surrogate_physics_v2` and
  `response_goint_physics_nn_v2`

Key results:

- Best challenger was `extra_trees`: Type accuracy 0.9456, macro F1 0.9397,
  Pt MAE 441.40, curve norm RMSE 0.00702, curve force RMSE 484.95.
- Current `response_surrogate_physics_v2` remains stronger overall: Type
  accuracy 0.9422, macro F1 0.9372, Pt MAE 438.15, curve norm RMSE 0.00701,
  curve force RMSE 479.43.
- `random_forest`, `hist_gradient_boosting`, `ridge_linear`, and
  `elastic_net_linear` did not beat the current reference.
- `xgboost`, `lightgbm`, `catboost`, and `tabpfn` were skipped because modules
  are not installed.

Recommendation:

- Do not add a backend model key yet.
- Keep public API/UI defaults unchanged.
- Curve CSV classifier files and behavior were not modified.

Follow-up with optional dependencies installed:

- Installed in the active miniforge Python environment:
  - `xgboost` 3.2.0
  - `lightgbm` 4.6.0
  - `catboost` 1.2.10
  - `tabpfn` 8.0.8
  - `torch` was upgraded in that environment to 2.12.0 as a TabPFN dependency.
- Updated `scripts/dd_response_tabular_challengers_train.py` so
  `--include-optional` actually trains XGBoost, LightGBM, CatBoost, and attempts
  TabPFN.
- Re-ran:
  - `python scripts/dd_response_tabular_challengers_train.py --include-optional`

Additional results:

- `xgboost`: Type accuracy 0.9422, macro F1 0.9371, Pt MAE 472.34, curve norm
  RMSE 0.00774, curve force RMSE 530.79.
- `lightgbm`: Type accuracy 0.9367, macro F1 0.9320, Pt MAE 499.55, curve norm
  RMSE 0.00756, curve force RMSE 524.21.
- `catboost`: Type accuracy 0.9411, macro F1 0.9340, Pt MAE 466.33, curve norm
  RMSE 0.00751, curve force RMSE 502.09.
- `tabpfn`: package installed, but evaluation failed because Prior Labs requires
  one-time license acceptance and `TABPFN_TOKEN` for non-interactive model
  weight download.

Updated recommendation:

- `response_surrogate_physics_v2` remains the best overall reference.
- Installed boosted-tree challengers do not justify a backend key yet.
- `extra_trees` remains the closest challenger, but its Pt/curve metrics are
  still slightly worse than the current reference and its artifact is large
  (about 453 MB).

Fair-comparison follow-up:

- Confirmed and documented that all trained challenger models use the same
  comparison contract as the current ExtraTrees reference:
  - feature set fixed to `theta_physics_v2`
  - compact CLT/ABD physics features, 35 columns
  - scalar targets fixed to `pt`, `max_displacement`, and `max_force`
  - curve target fixed to the 128-point normalized response curve
  - PCA curve surrogate fixed to 18 components
  - learner family is the intended variable
- Updated `reports/dd_response_tabular_challengers_v1/model_comparison.md` with
  a "Fair Comparison Contract" section.
- Added `src/ml/dd_laminate/zero_based_classifier.py` and changed
  `scripts/dd_response_tabular_challengers_train.py` to import it so XGBoost
  challenger artifacts no longer pickle the adapter as `__main__`.
- Regenerated challenger artifacts with `--include-optional`.
- Verified every trained `.joblib` artifact loads successfully and reports
  `theta_physics_v2`, 35 feature columns, `PCA`, 18 components, and a curve
  model.
- Confirmed no Curve CSV classifier, DD Laminate frontend, `predict_curve`, or
  `deep_sequence` files changed in this pass.

Deep-learning note from the original prompt:

- The prompt mentions existing `GointMLP` neural models and `DeepONet` for
  Simple Injection as current project context.
- It explicitly forbids adding Curve CSV sequence/deep-learning classifiers
  such as MiniRocket, InceptionTime, TCN, CNN, or GRU in this task.
- For Laminate Forecast, the prompt asks to compare against
  `response_goint_physics_nn_v2` and optionally use `theta_physics_nn_v2` where
  neural-friendly features are relevant, but the first implementation priority
  is a tabular challenger suite.
- For u3, the prompt suggests a possible stacked/blended Tree + GointMLP
  direction after the Laminate Forecast challenger work.

## 2026-06-17 Laminate Forecast DL Challenger Suite v1

User asked to do the same kind of challenger comparison for the GointMLP neural
model that was done for tree/tabular models.

Implemented:

- Added `scripts/dd_response_dl_challengers_train.py`
- Updated `docs/design/dd_laminate_model_upgrade_no_curve_csv.md` with a
  Deep-Learning Challenger Suite section.
- Generated artifacts:
  - `models/dd_laminate_response_dl_challengers_v1/`
  - `reports/dd_response_dl_challengers_v1/model_comparison.md`
  - `reports/dd_response_dl_challengers_v1/model_comparison.json`

Fair comparison contract:

- Compare against `response_goint_physics_nn_v2`.
- Keep feature set fixed to `theta_physics_nn_v2`.
- Keep direct 128-point normalized response curve head, not the Tree/PCA curve
  surrogate.
- Keep class, ordinal, scalar, and curve loss structure aligned with the
  existing GointMLP trainer.
- Change only the neural architecture.

DL candidates trained:

- `plain_mlp`
- `residual_mlp`
- `gated_mlp`

Results:

- `plain_mlp`: macro F1 0.9380, Pt MAE 936.90, curve norm RMSE 0.02569.
- `residual_mlp`: macro F1 0.9374, Pt MAE 890.09, curve norm RMSE 0.03672.
- `gated_mlp`: macro F1 0.9396, Pt MAE 726.62, curve norm RMSE 0.02740.
- Current `response_goint_physics_nn_v2`: macro F1 0.9383, Pt MAE 661.41,
  curve norm RMSE 0.02131.
- Current `response_surrogate_physics_v2`: macro F1 0.9372, Pt MAE 438.15,
  curve norm RMSE 0.00701.

Conclusion:

- `gated_mlp` is the best new DL challenger on Type macro F1 and is closest on
  Pt, but it still does not beat `response_goint_physics_nn_v2` on Pt or curve
  RMSE.
- None of the DL challengers justify a backend model key or UI/API default
  change.
- Verified all new DL artifacts load and report `theta_physics_nn_v2`, 47 input
  features, and 128 curve points.
- Confirmed no Curve CSV classifier, DD Laminate frontend, `predict_curve`, or
  `deep_sequence` files changed.

## 2026-06-17 Laminate Forecast Stack LSTM/GNN Challenger Extension

User asked whether GNN/LSTM or other graph-related DL models could be added
instead of only MLP-style challengers.

Implemented in `scripts/dd_response_dl_challengers_train.py`:

- Added deterministic 16-ply stack feature construction from the same
  theta/case input.
- Added `stack_lstm`:
  - bidirectional LSTM over the 16-ply laminate sequence
  - fused with `theta_physics_nn_v2` global features
- Added `stack_gru`:
  - bidirectional GRU over the 16-ply laminate sequence
  - lighter recurrent alternative to LSTM
- Added `stack_gnn`:
  - lightweight PyTorch-only graph convolution over a 16-node ply-adjacency
    chain graph
  - no `torch_geometric` or `dgl` dependency required
- Added `stack_gat`:
  - lightweight PyTorch-only graph attention over the same 16-node
    ply-adjacency graph
- Updated `reports/dd_response_dl_challengers_v1/model_comparison.md` and JSON
  by rerunning all DL candidates.
- Updated `docs/design/dd_laminate_model_upgrade_no_curve_csv.md` with the
  stack LSTM/GRU/GNN/GAT direction.

Final DL challenger results:

- `plain_mlp`: macro F1 0.9380, Pt MAE 936.90, curve norm RMSE 0.02569.
- `residual_mlp`: macro F1 0.9374, Pt MAE 890.09, curve norm RMSE 0.03672.
- `gated_mlp`: macro F1 0.9396, Pt MAE 726.62, curve norm RMSE 0.02740.
- `stack_lstm`: macro F1 0.9345, Pt MAE 821.41, curve norm RMSE 0.02581.
- `stack_gru`: macro F1 0.9415, Pt MAE 956.10, curve norm RMSE 0.03173.
- `stack_gnn`: macro F1 0.9416, Pt MAE 973.38, curve norm RMSE 0.03121.
- `stack_gat`: macro F1 0.9391, Pt MAE 774.76, curve norm RMSE 0.02256.

Interpretation:

- `stack_gnn` has the best Type macro F1 among the new DL challengers, but its
  Pt and curve metrics are much worse than `response_goint_physics_nn_v2`.
- `stack_gru` has similarly strong Type macro F1, but Pt and curve metrics are
  unstable because one fold regressed heavily.
- `stack_gat` is the most promising graph-family candidate because curve RMSE
  is close to `response_goint_physics_nn_v2`, but Pt MAE still trails the
  current GointMLP reference.
- `stack_lstm` captures some useful stack-order signal but still underperforms
  GointMLP on Pt and curve.
- `gated_mlp` remains the best new DL challenger by the current recommendation
  rule because Pt and curve metrics are less bad than the other new DL
  candidates.
- None of the DL challengers justify a backend model key or UI/API default
  change.

Verification:

- `python -m py_compile scripts/dd_response_dl_challengers_train.py` passed.
- All seven DL `.pt` artifacts load and report `theta_physics_nn_v2`, 47 global
  features, 128 curve points, and 10 stack feature columns.
- Confirmed no Curve CSV classifier, DD Laminate frontend, `predict_curve`, or
  `deep_sequence` files changed.

## 2026-06-17 Laminate Forecast PINN-Adjacent Challenger Check

User asked for a model that is not a full PINN, but is close in spirit.

Candidate reasoning:

- A true PINN is premature because the current task has no explicit governing
  equation/residual surface for the DD laminate response curve.
- A lightweight physics-guided neural network is the closest immediate option:
  use the same supervised response targets, but add soft curve-shape penalties.
- A DeepONet-style neural operator is another PINN-adjacent option: it learns a
  response function over the displacement grid without needing PDE residuals.

Implemented in `scripts/dd_response_dl_challengers_train.py`:

- `physics_guided_mlp`
  - same target contract as `response_goint_physics_nn_v2`
  - adds soft penalties for curve start near zero, peak normalization near one,
    monotonic descent, and curvature smoothness
- `deeponet_response`
  - branch network encodes `theta_physics_nn_v2`
  - trunk network encodes normalized displacement grid
  - curve is generated as a branch/trunk factorized function

Generated separate research artifacts:

- `models/dd_laminate_response_physics_guided_challenger_v1/`
- `models/dd_laminate_response_physics_guided_challenger_w005_v1/`
- `models/dd_laminate_response_deeponet_challenger_v1/`
- `reports/dd_response_physics_guided_challenger_v1/`
- `reports/dd_response_physics_guided_challenger_w005_v1/`
- `reports/dd_response_deeponet_challenger_v1/`

Results:

- `physics_guided_mlp`, physics weight 0.20: macro F1 0.9424, Pt MAE 806.94,
  curve norm RMSE 0.04979.
- `physics_guided_mlp`, physics weight 0.05: macro F1 0.9398, Pt MAE 806.88,
  curve norm RMSE 0.04523.
- `deeponet_response`: macro F1 0.9370, Pt MAE 990.16, curve norm RMSE
  0.07994.
- Current `response_goint_physics_nn_v2`: macro F1 0.9383, Pt MAE 661.41,
  curve norm RMSE 0.02131.
- Current `response_surrogate_physics_v2`: macro F1 0.9372, Pt MAE 438.15,
  curve norm RMSE 0.00701.

Conclusion:

- The PINN-adjacent direction is feasible technically, but the first two
  candidates are not promotion-worthy.
- Soft physics penalties improved/kept Type metrics in some folds but hurt
  curve stability, especially on one held-out theta-pair group.
- DeepONet-style curve generation is conceptually aligned with neural operators,
  but underperformed the current GointMLP and tree baselines.
- This suggests the next useful research direction is not stronger generic
  curve-head architecture, but a Type-gated or residual hybrid that keeps the
  strong Tree/PCA curve surrogate and uses neural/physics modules only where
  they reduce residual error.

Verification:

- `python -m py_compile scripts/dd_response_dl_challengers_train.py` passed.
- All three new PINN-adjacent `.pt` artifacts load and report
  `theta_physics_nn_v2`, 47 input features, and 128 curve points.
- Confirmed no Curve CSV classifier, DD Laminate frontend, `predict_curve`, or
  `deep_sequence` files changed.

## 2026-06-17 Laminate Forecast PCA Curve Head Challenger

User noticed that some new DL models have acceptable Pt but poor curve metrics
and asked whether a model could improve the curve.

Implemented in `scripts/dd_response_dl_challengers_train.py`:

- Added `pca_curve_mlp`.
- The model fits a PCA/POD curve basis inside each training fold only.
- The neural network predicts basis coefficients and reconstructs the 128-point
  normalized response curve.
- Early stopping for this candidate is curve-focused instead of Type-F1-only.
- Removed the output `Softplus` from the PCA reconstruction after an initial
  ablation showed it distorted the basis reconstruction.

Artifacts:

- Initial ablation:
  - `models/dd_laminate_response_pca_curve_challenger_v1/`
  - `reports/dd_response_pca_curve_challenger_v1/`
- Corrected curve-focused run:
  - `models/dd_laminate_response_pca_curve_challenger_v2/`
  - `reports/dd_response_pca_curve_challenger_v2/`

Final v2 results:

- `pca_curve_mlp`: macro F1 0.9132, Pt MAE 558.50, curve norm RMSE 0.01176,
  curve force RMSE 837.49.
- Current `response_goint_physics_nn_v2`: macro F1 0.9383, Pt MAE 661.41,
  curve norm RMSE 0.02131, curve force RMSE 1250.71.
- Current `response_surrogate_physics_v2`: macro F1 0.9372, Pt MAE 438.15,
  curve norm RMSE 0.00701, curve force RMSE 479.43.

Conclusion:

- `pca_curve_mlp` beats the current GointMLP reference on Pt and curve metrics,
  but its Type macro F1 regresses too much for standalone promotion.
- It is a promising curve/scalar expert for a future hybrid:
  - keep Type prediction from the stronger current classifier/gate
  - use `pca_curve_mlp` or a similar PCA/POD neural decoder for Pt and curve
  - compare that hybrid against `response_surrogate_physics_v2`
- No backend model key or public UI/API default was changed.

Verification:

- `python -m py_compile scripts/dd_response_dl_challengers_train.py` passed.
- `models/dd_laminate_response_pca_curve_challenger_v2/pca_curve_mlp.pt`
  loads and reports `theta_physics_nn_v2`, 47 input features, 128 curve points,
  and 18 PCA components.
- Confirmed no Curve CSV classifier, DD Laminate frontend, `predict_curve`, or
  `deep_sequence` files changed.

## 2026-06-17 Laminate Forecast Hybrid Expert Bundle

User asked whether it is acceptable to split the model by prediction target
instead of forcing one monolithic model to predict Type, Pt, and curve.

Decision:

- It is acceptable and common to use different internal models/heads for
  different target types when the targets have different statistical structure.
- For this project, Type is classification, while Pt and curve are
  regression/function reconstruction.
- The important product boundary is that the served Laminate Forecast predictor
  can remain one model/bundle and one API response, even if internally it has a
  Type expert and a Pt/curve expert.

Implemented:

- Added `scripts/dd_response_hybrid_challenger_train.py`.
- Built research bundle `hybrid_type_tree_pca_curve_mlp`:
  - Type expert: ExtraTrees classifier with `theta_physics_v2`, 35 compact
    CLT/ABD physics features.
  - Pt/curve expert: PCA/POD curve-decoder MLP with `theta_physics_nn_v2`, 47
    neural-friendly physics features.
  - PCA/POD basis is fit inside each training fold only during validation.
- Generated artifacts:
  - `models/dd_laminate_response_hybrid_challenger_v1/hybrid_type_bundle.joblib`
  - `models/dd_laminate_response_hybrid_challenger_v1/pca_curve_mlp_expert.pt`
- Generated report:
  - `reports/dd_response_hybrid_challenger_v1/model_comparison.md`

Results:

- `hybrid_type_tree_pca_curve_mlp`: macro F1 0.9372, Pt MAE 585.37, curve norm
  RMSE 0.01164, curve force RMSE 883.84.
- Current `response_goint_physics_nn_v2`: macro F1 0.9383, Pt MAE 661.41,
  curve norm RMSE 0.02131, curve force RMSE 1250.71.
- Current `response_surrogate_physics_v2`: macro F1 0.9372, Pt MAE 438.15,
  curve norm RMSE 0.00701, curve force RMSE 479.43.

Conclusion:

- The hybrid is a credible GointMLP-replacement research candidate because it
  improves Pt and curve metrics over GointMLP while keeping Type metrics at the
  tree reference level.
- It still does not beat `response_surrogate_physics_v2`, so no backend model
  key or UI/API default was changed.
- Next best step, if continuing, is to build a serving-compatible prediction
  wrapper for the hybrid and compare local sample predictions against the
  current production reference before considering registry exposure.

Verification:

- `python -m py_compile scripts/dd_response_hybrid_challenger_train.py
  scripts/dd_response_dl_challengers_train.py` passed.
- Hybrid artifacts load:
  - type bundle reports `theta_physics_v2`, `theta_physics_nn_v2`, 35 Type
    features, and 47 curve features.
  - curve expert reports `theta_physics_nn_v2`, 47 input features, 128 curve
    points, and 18 PCA components.
- Confirmed no Curve CSV classifier, DD Laminate frontend, `predict_curve`, or
  `deep_sequence` files changed.

## 2026-06-17 Hybrid Pt/Curve Consistency Note

User asked whether splitting Pt and curve into separate experts is acceptable
when predicted Pt should lie on the predicted curve.

Decision:

- It is not enough to say the curve shape is good and Pt is independent.
- Keep scalar Pt authoritative because the scalar Pt metric is meaningful and
  currently stronger than deriving Pt from an arbitrary generated curve index.
- The curve should be made consistent with Pt through a thin consistency layer:
  - interpolate the predicted curve at force = predicted Pt for display
  - report whether Pt lies inside the predicted force range
  - report the interpolated Pt displacement
  - if Pt falls outside range, calibrate the curve force scale/max-force rather
    than silently moving Pt
- A future training pass can add Pt-consistency loss so the Pt scalar and curve
  head agree before post-processing.

Implementation context:

- Current DD frontend already draws the Pt marker by finding `predicted_pt` on
  the curve (`pointAtForce(points, predictedPt)`), so the visual marker can be
  placed on the curve.
- The missing piece for the hybrid is backend/model-level consistency
  diagnostics and, if needed, force-scale calibration.

Updated:

- `docs/design/dd_laminate_model_upgrade_no_curve_csv.md` now includes the
  Pt/curve consistency rule under the hybrid design.

## 2026-06-17 Pt-Consistency Loss Ablation

User asked whether adding Pt-consistency loss means active learning.

Clarification:

- It is not active learning.
- Active learning would choose new uncertain theta/case samples and request new
  simulations or labels.
- Pt-consistency loss is supervised regularization on the existing dataset:
  it changes the loss so the predicted curve is encouraged to pass near the
  predicted/true Pt force level.

Implemented:

- Added `pt_consistency_loss()` to `scripts/dd_response_dl_challengers_train.py`.
- The loss computes true normalized Pt level as `pt / max_force` from the
  normalized scalar targets, then penalizes the predicted curve if no point is
  near that level or if Pt falls outside the predicted normalized force range.
- Added `--pt-consistency-weight` to:
  - `scripts/dd_response_dl_challengers_train.py`
  - `scripts/dd_response_hybrid_challenger_train.py`

Hybrid ablation results:

- No consistency loss, previous hybrid:
  - macro F1 0.9372
  - Pt MAE 585.37
  - curve norm RMSE 0.01164
  - curve force RMSE 883.84
- Pt consistency weight 0.10:
  - macro F1 0.9372
  - Pt MAE 642.84
  - curve norm RMSE 0.03656
  - curve force RMSE 1518.48
  - conclusion: too strong; harms curve.
- Pt consistency weight 0.01:
  - macro F1 0.9372
  - Pt MAE 558.62
  - curve norm RMSE 0.01420
  - curve force RMSE 926.96
  - conclusion: acceptable regularizer but curve is still worse than the
    no-consistency hybrid.

Conclusion:

- Pt-consistency training is feasible, but the naive soft-min loss must be very
  weak.
- Best current tradeoff remains the no-consistency hybrid for curve RMSE, plus
  inference-time Pt/curve diagnostics and force-scale calibration.
- A future improved consistency loss should target the actual transition/knee
  displacement if that label can be derived reliably, rather than pulling the
  whole curve toward the Pt force level.

Verification:

- `python -m py_compile scripts/dd_response_dl_challengers_train.py
  scripts/dd_response_hybrid_challenger_train.py` passed.
- Generated research artifacts:
  - `models/dd_laminate_response_hybrid_pt_consistent_v1/`
  - `reports/dd_response_hybrid_pt_consistent_v1/`
  - `models/dd_laminate_response_hybrid_pt_consistent_w001_v1/`
  - `reports/dd_response_hybrid_pt_consistent_w001_v1/`

## 2026-06-18 Inference-Time Pt/Curve Consistency Layer

User asked to proceed with the previously recommended inference-time Pt/curve
diagnostics and calibration work.

Implemented:

- Added `src/ml/dd_laminate/pt_curve_consistency.py`.
  - Computes whether predicted Pt lies inside the predicted curve force range.
  - Computes interpolated displacement where the curve crosses predicted Pt.
  - Computes force gap if the curve does not cross Pt.
  - Applies conservative max-force/force-scale calibration when Pt is above the
    predicted curve range.
  - Keeps scalar Pt authoritative; Pt is not moved to fit the curve.
- Updated existing response predictors:
  - `src/ml/dd_laminate/predict_response_surrogate.py`
  - `src/ml/dd_laminate/predict_response_deep_surrogate.py`
- Added research hybrid predictor:
  - `src/ml/dd_laminate/predict_response_hybrid.py`
  - Loads `models/dd_laminate_response_hybrid_challenger_v1/`
  - Uses the same consistency layer.
- Added tests:
  - `tests/ml/test_pt_curve_consistency.py`
- Updated design notes:
  - `docs/design/dd_laminate_model_upgrade_no_curve_csv.md`

New flat metrics emitted by response predictors:

- `pt_curve_inside_range`
- `pt_curve_inside_range_before_calibration`
- `pt_curve_displacement`
- `pt_curve_force_gap`
- `pt_curve_force_scale_correction`

Verification:

- `python -m py_compile src/ml/dd_laminate/pt_curve_consistency.py
  src/ml/dd_laminate/predict_response_surrogate.py
  src/ml/dd_laminate/predict_response_deep_surrogate.py
  src/ml/dd_laminate/predict_response_hybrid.py` passed.
- `pytest -q tests/ml/test_pt_curve_consistency.py` passed: 3 tests.
- Hybrid smoke:
  - command: `python -m src.ml.dd_laminate.predict_response_hybrid --theta1 30
    --theta2 -45 --case Case2 --model-dir
    models/dd_laminate_response_hybrid_challenger_v1`
  - returned Type 2, Pt 17161.66, max force 28830.10,
    `pt_curve_inside_range=1`, `pt_curve_force_scale_correction=1.0`, 128
    curve points.
- Tree response smoke:
  - `response_surrogate_physics_v2` returned Pt 16413.40, max force 26761.90,
    `pt_curve_inside_range=1`, scale correction 1.0, 128 curve points.
- Deep response smoke:
  - `response_goint_physics_nn_v2` returned Pt 16386.14, max force 25712.24,
    `pt_curve_inside_range=1`, scale correction 1.0, 128 curve points.
- `pytest -q tests/backend/test_dd_laminate_ios_contract.py` with the shell
  Python failed because `fastapi` is not installed there.
- `.venv/bin/pytest -q tests/backend/test_dd_laminate_ios_contract.py` ran, and
  response prediction tests passed, but one pre-existing model-list assertion
  failed because the current `response_surrogate` label is
  `Laminate Forecast - Tree (Theta)` while the test expects `ExtraTrees + PCA`.
  This failure appears unrelated to the Pt/curve consistency layer.

## 2026-06-18 ImperialAX/ImperialAX iOS Simulator Launch

User asked to launch the current app with the Build iOS Apps plugin as
ImperialAX(ImperialAX) so they can inspect it.

Executed with XcodeBuildMCP:

- Discovered host project:
  - `ios/ImperialAXMVPApp/ImperialAXMVPHost.xcodeproj`
- Confirmed scheme:
  - `ImperialAXMVPHost`
- Set session defaults profile:
  - profile `imperialax-ios`
  - simulator `iPhone 17`
  - simulator id `94D2DC55-5EAF-4A51-9760-5DFABB3CABF2`
  - bundle id `com.imperialax.mvp`
- Ran `build_run_sim`.

Result:

- Build/install/launch succeeded.
- Running app process id: `19472`.
- App path:
  - `/Users/danlee/Library/Developer/XcodeBuildMCP/workspaces/KyulAI_codex-a12407ff8fad/DerivedData/ImperialAXMVPHost-1ec0a496d51d/Build/Products/Debug-iphonesimulator/ImperialAXMVPHost.app`
- Build log:
  - `/Users/danlee/Library/Developer/XcodeBuildMCP/workspaces/KyulAI_codex-a12407ff8fad/logs/build_run_sim_2026-06-18T00-53-33-478Z_pid10865_faf0f189.log`
- Runtime log:
  - `/Users/danlee/Library/Developer/XcodeBuildMCP/workspaces/KyulAI_codex-a12407ff8fad/logs/com.imperialax.mvp_2026-06-18T00-54-20-160Z_helperpid19400_ownerpid10865_6ece1b7b.log`
- Screenshot confirmed the ImperialAX sign-in screen is visible with
  `demo@imperialax.com` prefilled.

## 2026-06-18 ImperialAX/ImperialAX Simulator Browser Mirror

User asked to show the current iOS Simulator in the Codex sidebar via
`build-ios-apps:ios-simulator-browser`.

Simulator/browser details:

- Simulator: `iPhone 17`
- Simulator id: `94D2DC55-5EAF-4A51-9760-5DFABB3CABF2`
- App bundle id: `com.imperialax.mvp`
- `serve-sim` URL: `http://localhost:3200`
- Long-running `serve-sim` terminal session id in this Codex turn: `8443`

Result:

- Opened `http://localhost:3200` in the Codex in-app browser/sidebar.
- Browser screenshot showed a live iPhone 17 frame with the ImperialAX workspace
  screen visible.
- The mirrored app screen showed:
  - `ImperialAX`
  - `Demo Account`
  - `demo@imperialax.com`
  - `Laminate`
  - `Open Laminate`
- XcodeBuildMCP runtime snapshot also confirmed the same UI and exposed tap
  targets including `Open Laminate`.

Note:

- Keep terminal session `8443` alive while the user is inspecting the browser
  mirror. Stopping that terminal should run the scoped cleanup trap for this
  simulator.

## 2026-06-18 ImperialAX Laminate Forecast Model List Trim

User asked to leave only two optimal models in the ImperialAX Laminate Forecast
`Choose Model` list.

Implemented:

- Backend `/api/v1/dd-laminate/models` now exposes only these response models:
  - `response_surrogate_physics_v2`
    - label: `Laminate Forecast - Tree + Compact Physics XAI`
  - `response_goint_physics_nn_v2`
    - label: `Laminate Forecast - GointMLP + NN-Friendly Physics XAI`
- Backend default `ResponsePredictionRequest.model` is now
  `response_surrogate_physics_v2`.
- iOS DD Laminate core default model is now `response_surrogate_physics_v2`.
- iOS view model defensively filters any server response to the same two model
  keys, preserving the preferred order.
- Updated mobile fixtures and contract tests to the new default model.

Changed files:

- `src/backend/api/v1/dd_laminate.py`
- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateCore/DDLaminateModels.swift`
- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateCore/PredictionViewModel.swift`
- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateCore/Resources/predict_response_case2.json`
- `ios/DDLaminateMVP/Tests/KyulAIDDLaminateCoreTests/DDLaminateCoreTests.swift`
- `tests/backend/test_dd_laminate_ios_contract.py`
- `tests/fixtures/dd_laminate/predict_response_case2.json`

Verification:

- `.venv/bin/python -m py_compile src/backend/api/v1/dd_laminate.py` passed.
- `.venv/bin/pytest -q tests/backend/test_dd_laminate_ios_contract.py` passed:
  4 tests.
- `swift test --package-path ios/DDLaminateMVP` passed: 9 tests.
- Direct TestClient check returned exactly:
  - `response_surrogate_physics_v2`
  - `response_goint_physics_nn_v2`
- Rebuilt and relaunched ImperialAX host on iPhone 17 simulator:
  - process id `35568`
  - simulator id `94D2DC55-5EAF-4A51-9760-5DFABB3CABF2`
- Runtime UI snapshot of the model selection sheet confirmed exactly two model
  option buttons:
  - `Laminate Forecast - Tree + Compact Physics XAI`
  - `Laminate Forecast - GointMLP + NN-Friendly Physics XAI`
- Existing simulator browser mirror at `http://localhost:3200` remains live via
  `serve-sim` session `8443`.

## 2026-06-18 u3 Model Card Parity

User asked to make the u3 Forecast model selection card look like the Response
Forecast model selection card instead of showing only a simple model name.

Implemented:

- Updated `u3ModelMenu` in
  `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/ContentView.swift`.
- u3 model card now mirrors the Response Forecast model card:
  - model icon
  - model name
  - `Recommended` badge for the default u3 model
  - short model description
  - chevron affordance
  - same rounded field background and subtle border
- Updated `isRecommendedModel(_:)` so both default response and default u3
  models are recognized as recommended.

Verification:

- `swift test --package-path ios/DDLaminateMVP` passed: 10 tests.
- Rebuilt and relaunched ImperialAX host on iPhone 17 simulator:
  - process id `17784`
  - simulator id `94D2DC55-5EAF-4A51-9760-5DFABB3CABF2`
- Runtime UI snapshot confirmed u3 Forecast now shows:
  - `u3 Forecast - Machine Learning`
  - `Recommended`
  - `Fast machine-learning model recommended for routine laminate forecasts.`
- Existing simulator browser mirror at `http://localhost:3200` remains live via
  `serve-sim` session `8443`.

## 2026-06-18 Model Picker And Recent Delete Cleanup

User asked to simplify the model picker area and consolidate recent-result
deletion:

- Remove the small `Model` / `u3 Pt Model` text above the model-selection cards.
- Remove the extra recent/history control shown beside the forecast tab header.
- Keep deletion through the `Recent Results` trash button.
- Add a select-all action inside the delete sheet.

Implemented:

- Removed the `Model` label above the Response Forecast model card.
- Removed the `u3 Pt Model` label above the u3 Forecast model card.
- Removed the tab-header `Recent` menu from both Response Forecast and
  u3 Forecast.
- The remaining recent-result deletion path is the trash icon in the
  `Recent Results` card.
- Added a `Select All` / `모두 선택` button to the recent-delete sheet.
- Updated legacy display-label aliases so older saved results with old
  `Tree + Physics XAI` / `GointMLP + Physics XAI` labels render as the newer
  `Machine Learning` / `Deep Learning` names.

Changed files:

- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/ContentView.swift`
- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/Resources/en.lproj/Localizable.strings`
- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/Resources/ko.lproj/Localizable.strings`
- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateCore/DDLaminateModels.swift`

Verification:

- `swift test --package-path ios/DDLaminateMVP` passed: 10 tests.
- Rebuilt and relaunched ImperialAX host on iPhone 17 simulator:
  - process id `13053`
  - simulator id `94D2DC55-5EAF-4A51-9760-5DFABB3CABF2`
- Runtime UI snapshot confirmed the Response Forecast card no longer shows the
  small `Model` label above the model picker.
- Runtime UI snapshot confirmed the tab header no longer shows the extra
  recent/history icon.
- Runtime UI snapshot confirmed the recent-delete sheet shows `Select All`.
- Runtime UI snapshot confirmed older u3 recent results now display
  `u3 Forecast - Machine Learning` instead of the old technical label.
- Existing simulator browser mirror at `http://localhost:3200` remains live via
  `serve-sim` session `8443`.

## 2026-06-18 Forecast Screen Header Cleanup

User noted two UX issues in the ImperialAX Laminate Forecast screen:

- `u3 Pt Forecast` had an extra explanatory sentence under the tab header while
  `Response Forecast` did not.
- The API connection/checkmark card at the top of the main screen was visually
  distracting and should move near the web/API URL entry area instead.

Decision:

- Removed the extra u3 explanatory sentence rather than adding a matching
  sentence to Response Forecast. The selected model card already explains the
  model, so removing the sentence keeps both tabs balanced and reduces visual
  noise.
- Removed the large main-screen API connection card.
- Added a compact connection status row inside the Settings `Base URL` section,
  directly below the API URL text field.
- The Settings status row shows:
  - connection icon
  - `Connected`, `Checking API`, `Connection failed`, etc.
  - retry button when the connection is failed
- Added localized `api.connected` string:
  - English: `Connected`
  - Korean: `연결됨`
- Updated older recent-run display labels to pass through the display-label
  cleaner, so previously saved runs with old technical labels now display the
  simplified model names.

Changed files:

- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/ContentView.swift`
- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/Resources/en.lproj/Localizable.strings`
- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/Resources/ko.lproj/Localizable.strings`
- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateCore/PredictionViewModel.swift`

Verification:

- `swift test --package-path ios/DDLaminateMVP` passed: 10 tests.
- Rebuilt and relaunched ImperialAX host on iPhone 17 simulator:
  - process id `99555`
  - simulator id `94D2DC55-5EAF-4A51-9760-5DFABB3CABF2`
- Runtime UI snapshot confirmed the main Laminate screen no longer has the
  top API connection card and starts with the forecast tabs/input card.
- Runtime UI snapshot confirmed `u3 Pt Forecast` no longer shows the extra
  `Predict u3 Type, Pt...` sentence.
- Runtime UI snapshot confirmed Settings/Base URL now shows `Connected` near
  the API URL input.
- Existing simulator browser mirror at `http://localhost:3200` remains live via
  `serve-sim` session `8443`.

## 2026-06-18 User-Friendly Forecast Model Names

User asked to simplify model names such as `Tree + Compact Physics-feature` and
`GointMLP + Compact Physics-feature` so non-technical users can understand the
choices more easily.

Implemented:

- Backend model labels now use:
  - `Laminate Forecast - Machine Learning`
  - `Laminate Forecast - Deep Learning`
  - `u3 Forecast - Machine Learning`
  - `u3 Forecast - Deep Learning`
- Backend model descriptions for the promoted response/u3 models were shortened
  to user-facing descriptions instead of technical feature-pack wording.
- iOS display-label aliases now map old server labels to the new names, so an
  older server response still appears with the simplified naming.
- Response and u3 model description cards now use the same simple description
  helper:
  - Machine Learning: fast recommended routine forecast
  - Deep Learning: comparison/experimental forecast
- English and Korean localized descriptions were updated to remove technical
  phrasing such as tree/PCA/compact physics from the primary UI.
- XAI summary text for the promoted models now refers to Machine Learning or
  Deep Learning first, while keeping concise physics-feature context.
- Contract fixtures and tests were updated to expect the new names.

Changed files:

- `src/backend/api/v1/dd_laminate.py`
- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateCore/DDLaminateModels.swift`
- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/ContentView.swift`
- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/ResultDetailView.swift`
- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/Resources/en.lproj/Localizable.strings`
- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/Resources/ko.lproj/Localizable.strings`
- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateCore/Resources/predict_response_case2.json`
- `ios/DDLaminateMVP/Tests/KyulAIDDLaminateCoreTests/DDLaminateCoreTests.swift`
- `tests/backend/test_dd_laminate_ios_contract.py`
- `tests/fixtures/dd_laminate/predict_response_case2.json`

Verification:

- `.venv/bin/python -m py_compile src/backend/api/v1/dd_laminate.py` passed.
- `.venv/bin/pytest -q tests/backend/test_dd_laminate_ios_contract.py` passed:
  4 tests.
- `swift test --package-path ios/DDLaminateMVP` passed: 10 tests.
- Direct FastAPI TestClient check returned:
  - response models: `Laminate Forecast - Machine Learning`,
    `Laminate Forecast - Deep Learning`
  - u3 models: `u3 Forecast - Machine Learning`,
    `u3 Forecast - Deep Learning`
- Rebuilt and relaunched ImperialAX host on iPhone 17 simulator:
  - process id `86266`
  - simulator id `94D2DC55-5EAF-4A51-9760-5DFABB3CABF2`
- Runtime UI snapshot confirmed Response Forecast shows:
  - `Laminate Forecast - Machine Learning`
  - `Fast machine-learning model recommended for routine laminate forecasts.`
- Runtime UI snapshot confirmed Response model menu can show:
  - `Laminate Forecast - Deep Learning`
  - `Deep-learning model for comparison and experimental checks.`
- Runtime UI snapshot confirmed u3 Forecast shows:
  - `u3 Forecast - Machine Learning`
  - `Fast machine-learning model recommended for routine laminate forecasts.`
- Runtime UI snapshot of the u3 model chooser showed exactly:
  - `u3 Forecast - Machine Learning`
  - `u3 Forecast - Deep Learning`
- Existing simulator browser mirror at `http://localhost:3200` remains live via
  `serve-sim` session `8443`.

## 2026-06-18 u3 Forecast Optimal Model List Trim

User asked to leave only 2 optimal models for the `u3 Forecast` model chooser,
matching the earlier Response Forecast cleanup.

Implemented:

- Backend `/api/v1/dd-laminate/models` now returns only these `u3_pt_models`:
  - `u3_forecast_physics_v2`
  - `u3_forecast_goint_physics_v2`
- Backend default `U3ForecastPredictionRequest.model` is now
  `u3_forecast_physics_v2`.
- iOS default `DDLaminateDefaults.u3PtModelKey` is now
  `u3_forecast_physics_v2`.
- Added iOS optimal u3 model allowlist:
  - `DDLaminateDefaults.u3PtModelKeys`
- `PredictionViewModel.checkConnection` now defensively filters received u3
  models to the two optimal keys, so the UI stays clean even if an older server
  returns legacy candidates.
- `PredictionViewModel.predictU3Pt` now treats every optimal u3 forecast key as
  a Forecast model, so the second GointMLP compact model does not accidentally
  fall back to the legacy CSV-upload u3 Pt path.
- Added display label aliases for the compact u3 Tree and GointMLP model names.
- Updated backend contract test expectations, Swift test fixture labels, and
  ViewModel readiness coverage for filtering legacy u3 candidates.

Changed files:

- `src/backend/api/v1/dd_laminate.py`
- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateCore/DDLaminateModels.swift`
- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateCore/PredictionViewModel.swift`
- `ios/DDLaminateMVP/Tests/KyulAIDDLaminateCoreTests/DDLaminateCoreTests.swift`
- `tests/backend/test_dd_laminate_ios_contract.py`

Verification:

- `.venv/bin/python -m py_compile src/backend/api/v1/dd_laminate.py` passed.
- `.venv/bin/pytest -q tests/backend/test_dd_laminate_ios_contract.py` passed:
  4 tests.
- `swift test --package-path ios/DDLaminateMVP` passed: 10 tests.
- Direct FastAPI TestClient check returned exactly:
  - `u3_forecast_physics_v2`
  - `u3_forecast_goint_physics_v2`
- Rebuilt and relaunched ImperialAX host on iPhone 17 simulator:
  - process id `67782`
  - simulator id `94D2DC55-5EAF-4A51-9760-5DFABB3CABF2`
- Runtime UI snapshot confirmed the `u3 Forecast` tab defaults to
  `u3 Forecast - Tree + Compact Physics XAI`.
- Runtime UI snapshot of the opened u3 model chooser showed exactly two targets:
  - `u3 Forecast - Tree + Compact Physics XAI`
  - `u3 Forecast - GointMLP + Compact Physics XAI`
- Final rebuild after the internal u3 Forecast branch guard:
  - process id `71831`
  - simulator id `94D2DC55-5EAF-4A51-9760-5DFABB3CABF2`
- Existing simulator browser mirror at `http://localhost:3200` remains live via
  `serve-sim` session `8443`.

## 2026-06-18 Forecast Tab Rename And Scoped Recents

User asked to rename the `Forecast Inputs` tab so it matches the style of
`u3 Forecast`, and to show only previous results created on the currently
selected tab.

Implemented:

- Renamed the main response tab from `Forecast Inputs` to `Response Forecast`.
- Added localized strings:
  - English: `response.forecast = Response Forecast`
  - Korean: `response.forecast = 응답 예측`
- Added recent-run kind tracking:
  - `responseForecast`
  - `u3Forecast`
- Existing older recent-run records decode as `responseForecast` for backward
  compatibility.
- Response predictions are saved as response recent runs.
- u3 Forecast predictions are now also saved as u3 recent runs.
- The bottom `Recent Results` card, recent menu, compare sheet, and delete sheet
  now receive only the recent runs for the active tab.
- Switching between `Response Forecast` and `u3 Forecast` clears stale compare
  selections so cross-tab comparisons are not carried over.

Changed files:

- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/ContentView.swift`
- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateCore/PredictionViewModel.swift`
- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/Resources/en.lproj/Localizable.strings`
- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/Resources/ko.lproj/Localizable.strings`
- `ios/DDLaminateMVP/Tests/KyulAIDDLaminateCoreTests/DDLaminateCoreTests.swift`

Verification:

- `swift test --package-path ios/DDLaminateMVP` passed: 10 tests.
- Added test:
  - `testViewModelSeparatesRecentRunsByForecastTab`
  - verifies response and u3 predictions save into separate recent-run buckets.
- Rebuilt and relaunched ImperialAX host on iPhone 17 simulator:
  - process id `57636`
  - simulator id `94D2DC55-5EAF-4A51-9760-5DFABB3CABF2`
- Runtime UI snapshot confirmed segmented tabs now show:
  - `Response Forecast`
  - `u3 Forecast`
- Runtime UI snapshot confirmed switching to `u3 Forecast` hides the response
  tab's existing recent menu/results from the u3 tab.
- Existing simulator browser mirror at `http://localhost:3200` remains live via
  `serve-sim` session `8443`.

## 2026-06-18 u3 Forecast Model Picker Sheet

User pointed out that the u3 Forecast model selector still opened as a compact
popover menu, while it should match the Response Forecast `Choose Model` sheet
with full option cards.

Implemented:

- Updated `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/ContentView.swift`.
- Added a separate `isShowingU3ModelPicker` sheet state.
- Replaced the u3 model `Menu` with the same card-style button pattern used by
  Response Forecast.
- Added `u3ModelSelectionSheet`, using the shared model option card layout:
  - navigation title: `Choose Model`
  - `Done` button
  - model-selection hint text
  - full cards for the two u3 models
- Refactored `modelOptionCard` so it can be reused for both Response Forecast
  and u3 Forecast selections.
- Marked the default u3 Machine Learning model as `Recommended` and `Fast`
  instead of showing the old experimental-style compact menu behavior.

Verification:

- `swift test --package-path ios/DDLaminateMVP` passed: 10 tests.
- Rebuilt and relaunched ImperialAX host on iPhone 17 simulator:
  - process id `25316`
  - simulator id `94D2DC55-5EAF-4A51-9760-5DFABB3CABF2`
- Runtime UI snapshot confirmed the u3 model button now shows the Response-style
  card summary:
  - `u3 Forecast - Machine Learning`
  - `Recommended`
  - `Fast machine-learning model recommended for routine laminate forecasts.`
- Tapping the u3 model card opened the full sheet with:
  - `Done`
  - model-selection hint text
  - `u3 Forecast - Machine Learning`, `Recommended`, `Fast`
  - `u3 Forecast - Deep Learning`, `Deep learning`
- Simulator screenshot captured at:
  - `/var/folders/7p/c3j_sb0j539805ngspmnb34r0000gn/T/screenshot_optimized_60c1c4eb-481a-4c3b-9131-89ff0c537a32.jpg`
- Existing simulator browser mirror at `http://localhost:3200` remains live via
  `serve-sim` session `8443`.

## 2026-06-18 Wanted UI Kit Laminate v2

User added `design/Wanted Design System (Community).fig` and asked to create an
optimized v2 design for the current web/app while preserving the existing
Classic screens.

Design source:

- Inspected `design/Wanted Design System (Community).fig`.
- The `.fig` package is a ZIP containing:
  - `canvas.fig`
  - `thumbnail.png`
  - `meta.json`
  - extracted image assets
- `canvas.fig` is Figma's internal binary format, not directly readable as
  normal JSON in this environment.
- Used the extracted thumbnail and package metadata as the design evidence:
  white canvas, black command surfaces, strong blue accent, thin borders,
  grid-like technical background, and dashboard/document-system components.

Implemented web v2:

- Added `src/frontend/dd-laminate/index-v2.html`.
- Added `src/frontend/dd-laminate/styles-v2.css`.
- Added `src/frontend/dd-laminate/app-v2.js`.
- Existing web files remain unchanged:
  - `index.html`
  - `styles.css`
  - `app.js`
- v2 uses the existing DD Laminate API/forecast JS contract but has its own
  HTML/CSS and a copied v2 JS file.
- v2 preserves the same modes:
  - Response Forecast
  - u3 Forecast
  - Curve CSV
- v2 has a Classic link back to `index.html`.
- v2 XAI default visible feature limit is 5 in `app-v2.js`, while Classic keeps
  its current behavior.
- Added a standalone DD app alias:
  - `http://127.0.0.1:8000/dd-laminate-v2`
- Broadened standalone DD local CORS handling so alternate local static ports
  such as `3211` can call the API during design review.
- Added a ImperialAX unified-app static mount for the DD Laminate web surface:
  - `http://127.0.0.1:8000/dd-laminate/index-v2.html`

Implemented iOS app v2:

- Added `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/ContentViewV2.swift`.
- Updated
  `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/DDLaminateModuleView.swift`.
- `DDLaminateModuleView` now has a segmented design switch:
  - `Wanted v2`
  - `Classic`
- The switch is backed by `@AppStorage("kyulai.ddLaminate.designVersion")`.
- Default design version is `Wanted v2`.
- Classic still renders the existing `ContentView`.
- v2 uses the same `AppSettings` and `PredictionViewModel`, so API connection,
  model loading, Response Forecast, and u3 Forecast share the existing data
  flow.
- v2 includes:
  - Wanted UI Kit-inspired header
  - API readiness badge
  - workflow rows
  - Response/u3 segmented forecast mode
  - card-style model selector and model sheet
  - theta/case controls
  - forecast buttons
  - result preview, metrics, curve chart, probabilities, and top 5 XAI preview
  - full-result navigation to the existing detail pages

Design documentation:

- Updated `DESIGN.md`:
  - refreshed date to 2026-06-18
  - added the Wanted `.fig` file as reviewed evidence
  - recorded v2 as a reversible experiment
  - documented the v2 visual language and token ownership

Verification:

- `node --check src/frontend/dd-laminate/app-v2.js` passed.
- Parsed `index-v2.html` and verified all required `app-v2.js` DOM IDs are
  present and non-duplicated.
- Started a static server for the DD Laminate web v2:
  - `http://127.0.0.1:3211/index-v2.html`
  - session id `49877`
- `curl -I` confirmed 200 responses for:
  - `/index-v2.html`
  - `/styles-v2.css`
  - `/app-v2.js`
- Captured web v2 screenshot with headless Chrome:
  - `/tmp/dd-laminate-web-v2.png`
- Final web v2 screenshots after API/CORS and mobile overflow verification:
  - desktop: `/tmp/dd-laminate-web-v2-final.png`
  - mobile CDP 390px viewport: `/tmp/dd-laminate-web-v2-mobile-cdp.png`
- CDP mobile verification reported:
  - `innerWidth`: 390
  - `documentElement.scrollWidth`: 390
  - API status text: `API: connected`
- Standalone DD API CORS verification from origin `http://127.0.0.1:3211`
  returned `access-control-allow-origin: http://127.0.0.1:3211`.
- `.venv/bin/pytest tests/backend/test_imperialax_modules.py tests/backend/test_dd_laminate_ios_contract.py`
  passed: 10 tests, 1 existing pytest config warning.
- `swift test --package-path ios/DDLaminateMVP` passed: 10 tests.
- Rebuilt and relaunched ImperialAX host on iPhone 17 simulator:
  - final process id `59701`
  - simulator id `94D2DC55-5EAF-4A51-9760-5DFABB3CABF2`
- Runtime UI snapshot confirmed:
  - `Wanted v2` and `Classic` design switch are present.
  - `Wanted v2` is selected.
  - `ImperialAX Laminate Forecast` header renders without truncation in the semantic
    snapshot.
  - workflow rows show `Set case`, `Pick model`, and `Review`.
  - Response Forecast model card shows `Laminate Forecast - Machine Learning`.
- Captured final iOS v2 screenshot:
  - `/var/folders/7p/c3j_sb0j539805ngspmnb34r0000gn/T/screenshot_optimized_c74dee9a-5831-4b7a-838a-606b6546f58e.jpg`
- Existing simulator browser mirror at `http://localhost:3200` remains live via
  `serve-sim` session `8443`.

## 2026-06-18 Result XAI Feature List Collapse

User asked to change the Laminate Forecast result page explanation list so only
the top 5 feature impact scores are shown by default, with the rest hidden
behind a button that expands the list.

Implemented:

- Updated `XAIExplanationCard` in
  `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/ResultDetailView.swift`.
- Added local `@State` expansion state.
- Shows only the first 5 `xai.topFeatures` by default.
- Adds a button when more than 5 features exist:
  - collapsed: `Show N more features`
  - expanded: `Show top 5 only`
- Button uses a chevron icon and an animated expand/collapse.
- Extracted the feature row rendering into `featureImpactRow(_:)`.
- Removed the trailing divider after the final visible row.

Verification:

- `swift test --package-path ios/DDLaminateMVP` passed: 9 tests.
- Rebuilt and relaunched ImperialAX host on iPhone 17 simulator:
  - process id `44057`
  - simulator id `94D2DC55-5EAF-4A51-9760-5DFABB3CABF2`
- Navigated to the Laminate module and confirmed the app launches with the new
  build. Runtime automation reached the result detail XAI card header; the
  final scroll interaction bounced back to the main screen before capturing the
  expanded list button, so the visual proof is partial, but the Swift build and
  tests passed with the new UI code.
- Existing simulator browser mirror at `http://localhost:3200` remains live via
  `serve-sim` session `8443`.

## 2026-06-18 DD Laminate Greenfield Flow Storyboard

User asked for a from-scratch UI/UX sample flow with at least five screens for
team discussion, assuming the existing UI did not exist.

Implemented a separate discussion prototype without changing Classic or Wanted
v2:

- Added `src/frontend/dd-laminate/greenfield-flow.html`.
- Added `src/frontend/dd-laminate/greenfield-flow.css`.
- Added design note:
  - `docs/design/dd_laminate_greenfield_flow.md`

The storyboard has seven screens:

1. Run Setup
2. Laminate Builder
3. Model Strategy
4. Forecast Progress
5. Decision Result
6. Explain and Compare
7. Review Package

Design direction:

- Starts from the engineering decision rather than raw model/input fields.
- Makes theta/case setup visual through the laminate stack preview.
- Reframes model selection as strategy: Machine Learning, Deep Learning, or
  Dual run.
- Treats Pt-curve consistency as a visible result quality gate.
- Ends with share/export/simulation handoff actions for team review.

Verification:

- `http://127.0.0.1:8000/greenfield-flow.html` returned 200.
- `http://127.0.0.1:8000/greenfield-flow.css` returned 200.
- `http://127.0.0.1:3211/greenfield-flow.html` returned 200.
- Captured desktop storyboard screenshot:
  - `/tmp/dd-laminate-greenfield-flow-final.png`
- Captured mobile viewport screenshot:
  - `/tmp/dd-laminate-greenfield-flow-mobile.png`
- CDP mobile check reported:
  - `innerWidth`: 390
  - `documentElement.scrollWidth`: 390
  - `.screen-card` count: 7

## 2026-06-18 DD Laminate Greenfield Flow 3 Versions

User asked to expand the greenfield storyboard into about three different
versions for team discussion.

Updated the existing standalone prototype:

- `src/frontend/dd-laminate/greenfield-flow.html`
- `src/frontend/dd-laminate/greenfield-flow.css`
- `docs/design/dd_laminate_greenfield_flow.md`

The page now contains three distinct product directions:

1. Version A: Decision Studio
   - Mobile-first guided flow.
   - Preserves the original seven phone storyboard screens.

2. Version B: Research Workbench
   - Desktop-first comparison workspace.
   - Five screens: Workspace Overview, Design Space, Model Matrix, Compare
     Results, Simulation Queue.

3. Version C: Review Command
   - Decision-review and approval surface.
   - Six screens: Brief, Evidence Intake, Confidence Gate, Decision Card,
     Challenge View, Approval Handoff.

Verification:

- `http://127.0.0.1:8000/greenfield-flow.html` returned 200.
- `http://127.0.0.1:8000/greenfield-flow.css` returned 200.
- HTML parse check found no duplicate IDs.
- DOM count check:
  - concepts: 3
  - Version A screens: 7
  - Version B screens: 5
  - Version C screens: 6
- Desktop screenshot:
  - `/tmp/dd-laminate-greenfield-3versions-full.png`
- Mobile CDP check:
  - `innerWidth`: 390
  - `documentElement.scrollWidth`: 390
  - concepts: 3
  - A/B/C screen counts: 7/5/6
- Mobile screenshot:
  - `/tmp/dd-laminate-greenfield-3versions-mobile.png`

## 2026-06-18 Version A Desktop Direction Discussion

User said Version A seems strongest and asked how it could change from a
mobile-first concept into a desktop-centered product direction.

Recommended direction:

- Keep Version A's core identity as a guided single-candidate decision flow.
- Do not turn it into Version B's broad multi-candidate research workbench.
- Reframe it as a `Desktop Decision Studio`:
  - left rail: run goal, case/theta inputs, API/model readiness, step progress
  - center canvas: laminate stack, curve/result preview, Pt marker, primary
    decision state
  - right inspector: model strategy, confidence gate, XAI top drivers,
    warnings, export/handoff
- Convert the mobile wizard into desktop sections that stay visible together:
  Run Setup, Stack Builder, Model Strategy, Forecast Progress, Decision Result,
  Explain/Compare, Review Package.
- Primary benefit: preserve Version A's clarity while making better use of
  desktop space for context, preview, and evidence.

## 2026-06-18 Version A Mobile/Desktop Prototype

User asked to make two concrete variants: `Version A Mobile` and
`Version A Desktop`.

Updated files:

- `src/frontend/dd-laminate/greenfield-flow.html`
- `src/frontend/dd-laminate/greenfield-flow.css`
- `docs/design/dd_laminate_greenfield_flow.md`

Current prototype:

- `Version A Mobile`
  - Keeps the guided phone-first Decision Studio flow.
  - Seven screens: Run Setup, Laminate Builder, Model Strategy, Forecast
    Progress, Decision Result, Explain and Compare, Review Package.
- `Version A Desktop`
  - Recasts the same Version A sequence as a desktop decision cockpit.
  - Left rail: setup/progress/run metadata.
  - Center canvas: candidate stack, theta/case inputs, result preview, Pt marker,
    curve comparison.
  - Right inspector: model strategy, confidence gate, top drivers, review
    package actions.
  - Adds five desktop storyboard cards: Persistent Run Setup, Large Stack
    Canvas, Live Result Preview, Evidence Inspector, Handoff Actions.

Verification:

- `http://127.0.0.1:8000/greenfield-flow.html` returned 200 in the browser.
- HTML/DOM checks:
  - duplicate IDs: none
  - top variant cards: 2
  - Version A Mobile phone screens: 7
  - Version A Desktop cockpit: 1
  - Version A Desktop storyboard cards: 5
- Mobile viewport check:
  - width: 390
  - scroll width: 390
  - horizontal overflow: false
  - screenshot: `/tmp/dd-laminate-version-a-mobile-desktop-mobile.png`
- Desktop viewport check:
  - width: 1440
  - scroll width: 1440
  - horizontal overflow: false
  - cockpit grid columns: `230px 796px 320px`
  - screenshot: `/tmp/dd-laminate-version-a-desktop-viewport.png`

## 2026-06-18 Dynamic Ply Stack Visualization Note

User asked whether the ply stacking image can reflect the theta angles entered
by the user.

Assessment:

- Yes, this is feasible.
- Current UI uses a static SVG asset:
  `src/frontend/dd-laminate/assets/dd-ply-stack.svg`.
- The SVG already encodes alternating ply colors and diagonal angle patterns,
  so the product can replace the static `<img>` with a generated SVG or canvas
  component.
- Recommended direction:
  - derive the Double-Double stacking sequence from case, theta1, and theta2
  - render each ply as a small projected layer
  - rotate/hatch the fiber-direction lines according to the ply angle
  - label visible layers with `+theta1`, `-theta1`, `+theta2`, `-theta2`
  - update the diagram live when users edit theta/case
- Best first implementation target is the `index-v2.html` app, then reuse the
  same renderer in the greenfield prototype.

## 2026-06-18 Angle-Aware Ply Stack Demo

User asked to build the dynamic ply stack visualization as a separate prototype
first, before applying it to the actual web/app UI.

Added standalone demo files:

- `src/frontend/dd-laminate/ply-stack-angle-demo.html`
- `src/frontend/dd-laminate/ply-stack-angle-demo.css`
- `src/frontend/dd-laminate/ply-stack-angle-demo.js`

Demo URL:

- `http://127.0.0.1:8000/ply-stack-angle-demo.html`

Behavior:

- Case 2/3/4 buttons use the same Double-Double formulas shown in `index-v2`.
- `theta1` and `theta2` sliders/number inputs update the SVG immediately.
- The renderer expands each case into a 16-ply sequence.
- Each ply is drawn as a projected layer.
- Ply family is color-coded:
  - theta1 family: blue
  - theta2 family: tan
- Signed angle direction is represented by hatch pattern color and rotation:
  - positive angle: green
  - negative angle: red
- Right inspector shows the full top-to-bottom ply list.
- SVG callouts are intentionally limited to representative plies to avoid
  clutter; the complete sequence remains in the inspector.

Verification:

- `node --check src/frontend/dd-laminate/ply-stack-angle-demo.js` passed.
- `curl -I` returned 200 for HTML/CSS/JS assets.
- Browser checks:
  - SVG count: 1
  - SVG pattern count: 16
  - sequence list items: 16
  - Case 4 + theta1 45 + theta2 -60 updated readouts and sequence
  - desktop width 1440 had no horizontal overflow
  - mobile width 390 had no horizontal overflow
  - console errors: none
- Screenshots:
  - desktop: `/tmp/dd-laminate-ply-stack-angle-demo-refined.png`
  - mobile: `/tmp/dd-laminate-ply-stack-angle-demo-mobile.png`

## 2026-06-18 PPT Case Formula Verification

User asked whether the dynamic ply stack demo was made after checking the PPT.

Clarification:

- The first demo implementation used the existing app/documented Case guide,
  not a fresh direct PPT check.
- Directly rendered `data/PPT/Final ver2.pptx` Slide 6 to confirm the formulas:
  - rendered PDF: `/tmp/dd-ppt-render-check/Final ver2.pdf`
  - rendered slide image: `/tmp/dd-ppt-render-check/slide6-06.png`
  - cropped formula image: `/tmp/dd-ppt-render-check/slide6-cases-wide-crop.png`
- PPT Slide 6 confirms:
  - Case2: `[[±theta1]/[±theta2]]4`
  - Case3: `[[±theta1]/[±theta2]/[∓theta1]/[∓theta2]]2`
  - Case4: `[([±theta1]/[±theta2])2 / ([∓theta1]/[∓theta2])2]`
- The initial demo had Case3 following the older app guide:
  `[[±theta1]/[±theta2]/[∓theta2]/[∓theta2]]2`.
- Fixed the standalone demo to use the PPT-accurate Case3 sequence.
- Updated `docs/DD_Laminate_PPT_Basis.md` to reflect the direct Slide 6
  verification.
- Important follow-up: `index-v2.html` and `laminate_physics.py` still contain
  the older Case3 wording/expansion and should be reviewed before changing the
  production app or retraining/physics features.

## 2026-06-18 PPT-Like Live SVG Preview Refinement

User asked to make only the `LIVE SVG PREVIEW` area in the angle-aware ply stack
demo look closer to the PPT image because the earlier preview felt slightly
cropped.

Updated files:

- `src/frontend/dd-laminate/ply-stack-angle-demo.css`
- `src/frontend/dd-laminate/ply-stack-angle-demo.js`

Changes:

- Reworked the SVG camera/viewBox from `1040 x 650` to `1160 x 720`.
- Enlarged the dark viewport plane so the stack has more breathing room.
- Changed each ply from a compact card-like layer to a longer, thinner
  projected strip.
- Shifted the ply offsets so the stack reads more like the PPT's diagonal
  staircase.
- Removed white angle callout boxes from the stack image.
- Added small yellow `Ply-n` labels near the right edge of each ply, closer to
  the PPT reference.
- Removed the fixed `min-height: 560px` on `.stack-visual`, eliminating the
  empty grid area under the SVG.

Verification:

- `node --check src/frontend/dd-laminate/ply-stack-angle-demo.js` passed.
- HTML/CSS/JS still served from `http://127.0.0.1:8000/ply-stack-angle-demo.html`.
- Desktop browser check:
  - width: 1440
  - horizontal overflow: false
  - SVG count: 1
  - hatch pattern count: 16
  - ply label count: 16
  - labels within SVG bounds: true
  - console errors: none
  - screenshot: `/tmp/dd-laminate-ply-stack-ppt-like-preview.png`
- Mobile browser check:
  - width: 390
  - horizontal overflow: false
  - SVG count: 1
  - hatch pattern count: 16
  - ply label count: 16
  - console errors: none
  - screenshot: `/tmp/dd-laminate-ply-stack-ppt-like-preview-mobile.png`

## 2026-06-18 Left-Up Ply Stack Label Refinement

User asked to make labels like `Ply-16` easier to read and to make the
laminated ply stack feel more symmetric, with the stack building toward the
upper-left.

Updated file:

- `src/frontend/dd-laminate/ply-stack-angle-demo.js`

Changes:

- Reversed the ply offset direction so higher ply numbers move left and up.
- Increased the diagonal spacing between plies so the left-up stacking reads
  more clearly.
- Added larger dark label chips with bright yellow text, outline, and leader
  lines for each `Ply-n` label.
- Kept all labels inside the SVG bounds while preserving the PPT-like projected
  laminate plate.

Verification:

- `node --check src/frontend/dd-laminate/ply-stack-angle-demo.js` passed.
- `curl -I http://127.0.0.1:8000/ply-stack-angle-demo.js` returned 200.
- Desktop browser check at 1440px:
  - horizontal overflow: false
  - SVG count: 1
  - hatch pattern count: 16
  - ply label count: 16
  - label box count: 16
  - labels within SVG bounds: true
  - `Ply-16` is left/up of `Ply-1`: true
  - screenshot: `/tmp/dd-laminate-ply-stack-left-up-readable-labels-v2.png`
- Mobile browser check at 390px:
  - horizontal overflow: false
  - SVG count: 1
  - hatch pattern count: 16
  - ply label count: 16
  - label box count: 16
  - labels within SVG bounds: true
  - `Ply-16` is left/up of `Ply-1`: true
  - screenshot: `/tmp/dd-laminate-ply-stack-left-up-readable-labels-v2-mobile.png`

## 2026-06-18 Current Formula Theta Symbol

User asked to replace the spelled-out `theta` text in the standalone ply stack
demo's `Current Formula` display with the Greek theta character.

Updated files:

- `src/frontend/dd-laminate/ply-stack-angle-demo.js`
- `src/frontend/dd-laminate/ply-stack-angle-demo.html`

Changes:

- Replaced `theta1` and `theta2` in the visible formula strings with `θ1` and
  `θ2`.
- Kept internal state, control names, and CSS class names as ASCII
  `theta1/theta2` so the implementation remains stable.

Verification:

- `node --check src/frontend/dd-laminate/ply-stack-angle-demo.js` passed.
- `curl -I` returned 200 for the HTML and JS files.
- Browser check confirmed Case2, Case3, and Case4 formulas all contain `θ` and
  no visible `theta` text in `#case-formula`.
- Screenshot: `/tmp/dd-laminate-ply-stack-theta-symbol-formula.png`

## 2026-06-18 Non-Overlapping Ply Label Rail

User pointed out that after enlarging the `Ply-n` labels, the label boxes were
overlapping even though the left-up stacking direction was correct.

Updated file:

- `src/frontend/dd-laminate/ply-stack-angle-demo.js`

Changes:

- Kept the `Ply-1` to `Ply-16` visual direction climbing toward the upper-left.
- Changed label placement from a fixed local Y offset to a per-layer diagonal
  label rail.
- Preserved the larger readable label chips while spacing their bounding boxes
  so adjacent labels no longer overlap.

Verification:

- `node --check src/frontend/dd-laminate/ply-stack-angle-demo.js` passed.
- `curl -I http://127.0.0.1:8000/ply-stack-angle-demo.js` returned 200.
- Browser bounding-box checks:
  - desktop 1440px: 16 label boxes, overlap count 0, labels within SVG true,
    horizontal overflow false, `Ply-16` left/up of `Ply-1` true
  - mobile 390px: 16 label boxes, overlap count 0, labels within SVG true,
    horizontal overflow false, `Ply-16` left/up of `Ply-1` true
- Screenshots:
  - desktop: `/tmp/dd-laminate-ply-stack-nonoverlap-labels.png`
  - mobile: `/tmp/dd-laminate-ply-stack-nonoverlap-labels-mobile.png`

## 2026-06-18 Close Ply Label Placement Revert

User asked to revert the non-overlapping label rail because the labels felt too
far from the actual ply positions.

Updated file:

- `src/frontend/dd-laminate/ply-stack-angle-demo.js`

Changes:

- Kept the left-up stacking direction from `Ply-1` to `Ply-16`.
- Moved the enlarged `Ply-n` label chips back close to each ply by restoring a
  fixed local label offset.
- Accepted slight label-box overlap as a tradeoff for stronger visual
  connection between each label and its ply.

Verification:

- `node --check src/frontend/dd-laminate/ply-stack-angle-demo.js` passed.
- `curl -I http://127.0.0.1:8000/ply-stack-angle-demo.js` returned 200.
- Browser checks:
  - desktop 1440px: 16 label boxes, overlap count 15, labels within SVG true,
    horizontal overflow false, `Ply-16` left/up of `Ply-1` true
  - mobile 390px: 16 label boxes, overlap count 15, labels within SVG true,
    horizontal overflow false, `Ply-16` left/up of `Ply-1` true
- Screenshots:
  - desktop: `/tmp/dd-laminate-ply-stack-close-overlap-labels.png`
  - mobile: `/tmp/dd-laminate-ply-stack-close-overlap-labels-mobile.png`

## 2026-06-18 Ply Stack Demo Mobile State

User asked what the current mobile version looks like.

Current state:

- The standalone ply stack demo remains responsive at 390px width.
- Mobile layout stacks sections vertically:
  - header
  - input controls
  - live SVG preview
  - sequence inspector
- The SVG preview is scaled down inside the mobile card.
- `Ply-n` labels are close to their corresponding plies, with slight overlap by
  design after the latest revert.
- The left-up stacking direction is preserved: `Ply-16` sits left/up relative to
  `Ply-1`.
- Latest mobile verification showed no horizontal overflow, all 16 labels inside
  the SVG, and 16 label boxes present.
- Screenshot: `/tmp/dd-laminate-ply-stack-close-overlap-labels-mobile.png`

## 2026-06-18 Mobile Sequence Inspector Collapse

User said the mobile demo is too long and asked to shrink the `SEQUENCE
INSPECTOR` area for now.

Updated files:

- `src/frontend/dd-laminate/ply-stack-angle-demo.html`
- `src/frontend/dd-laminate/ply-stack-angle-demo.css`
- `src/frontend/dd-laminate/ply-stack-angle-demo.js`

Changes:

- Added a `Show list` / `Hide list` toggle to the Sequence Inspector header.
- Mobile view now starts with the sequence list collapsed by default.
- Desktop view still starts expanded by default.
- The full 16-ply list and help card are hidden while collapsed, but remain in
  the DOM and are restored when the user opens the list.
- Added `aria-expanded` and `aria-controls` to the toggle.

Verification:

- `node --check src/frontend/dd-laminate/ply-stack-angle-demo.js` passed.
- `curl -I` returned 200 for HTML, CSS, and JS.
- Browser mobile check at 390px:
  - collapsed by default: true
  - `aria-expanded`: false
  - sequence list display: none
  - help card display: none
  - horizontal overflow: false
  - collapsed page height: 1681px
  - expanded page height after toggle: 2775px
- Browser desktop check at 1440px:
  - starts expanded
  - horizontal overflow: false
- Screenshots:
  - collapsed mobile: `/tmp/dd-laminate-ply-stack-mobile-inspector-collapsed.png`
  - expanded mobile: `/tmp/dd-laminate-ply-stack-mobile-inspector-expanded.png`

## 2026-06-18 Dynamic Ply Stack Applied to Web and iOS v2

User asked to apply the standalone angle-aware ply stack demo to the actual web
and app surfaces.

Scope:

- Applied to the v2 / Wanted UI Kit surfaces.
- Preserved Classic web/app surfaces.
- Did not change backend prediction logic or model artifacts.

Updated web files:

- `src/frontend/dd-laminate/index-v2.html`
- `src/frontend/dd-laminate/styles-v2.css`
- `src/frontend/dd-laminate/app-v2.js`

Web changes:

- Replaced the static `dd-ply-stack.svg` image in the v2 Laminate Reference
  panel with a live generated SVG preview.
- Added `#dynamic-stack-visual`, `#dynamic-stack-formula`, and
  `#dynamic-stack-count`.
- Ported the standalone demo's 16-ply sequence builder and PPT-style projected
  stack SVG renderer into `app-v2.js`.
- The preview updates when Response Forecast or u3 Forecast theta/case inputs
  change.
- Response Forecast and u3 Forecast both show the live stack preview.
- Curve CSV hides the stack preview and keeps the CSV preview behavior.
- Updated visible Case3 formulas in `index-v2.html` to the PPT-checked sequence:
  `[[±θ₁]/[±θ₂]/[∓θ₁]/[∓θ₂]]₂`.

Updated iOS file:

- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/ContentViewV2.swift`

iOS changes:

- Added `DynamicPlyStackPreviewCard` to the Wanted v2 input panel.
- Added `PlyStackCanvas` SwiftUI `Canvas` renderer with the same left-up
  stacking direction, 16-ply sequence, θ1/θ2 family colors, positive/negative
  hatch cues, and close `Ply-n` labels.
- The preview reads `viewModel.selectedCase`, `viewModel.theta1`, and
  `viewModel.theta2`, so it updates with the user's input state.
- Updated the iOS v2 visible Case formula text to use `θ1/θ2` and the
  PPT-checked Case3 sequence.

Verification:

- `node --check src/frontend/dd-laminate/app-v2.js` passed.
- HTML parse check for `index-v2.html` found 43 ids, no duplicates, and
  `dynamic-stack-visual` present.
- Browser web v2 checks:
  - Response mode: live SVG count 1, hatch pattern count 16, label count 16,
    plies count 16, visual visible, horizontal overflow false
  - Case4 formula updated to `([+/-θ1]/[+/-θ2]) x 2 + ([-/+θ1]/[-/+θ2]) x 2`
  - u3 mode: live SVG visible, SVG count 1, no overflow
  - Curve CSV mode: live stack visual panel hidden
  - Mobile 390px: SVG count 1, label count 16, no horizontal overflow
- Web screenshots:
  - desktop Response + Case4: `/tmp/dd-laminate-web-v2-dynamic-stack-response.png`
  - mobile Response default: `/tmp/dd-laminate-web-v2-dynamic-stack-mobile.png`
- `swift test --package-path ios/DDLaminateMVP` passed: 10 tests.
- XcodeBuildMCP `build_run_sim` for ImperialAX iOS host succeeded:
  - project: `ios/ImperialAXMVPApp/ImperialAXMVPHost.xcodeproj`
  - scheme: `ImperialAXMVPHost`
  - simulator: iPhone 17
  - bundle id: `com.imperialax.mvp`
  - process id: `24952`
- iOS runtime snapshot confirmed the Wanted v2 Laminate screen contains:
  - `LIVE LAMINATE PREVIEW`
  - `Angle-aware ply stack`
  - `16 plies`
  - `θ1`, `θ2`, `+`, and `-` legend chips
  - updated Case formula text
- iOS screenshot:
  - `/var/folders/7p/c3j_sb0j539805ngspmnb34r0000gn/T/screenshot_optimized_fcda07c8-6e9c-426d-9c7c-55b192f5fbf0.jpg`

## 2026-06-18 Web v2 URL and ImperialAX iOS Mirror

User asked for the web page URL and to show the app in the side browser.

Web page:

- `http://127.0.0.1:8000/index-v2.html`

iOS app mirror:

- Started `serve-sim` for simulator `94D2DC55-5EAF-4A51-9760-5DFABB3CABF2`.
- Mirror URL: `http://localhost:3201/`
- XcodeBuildMCP active profile: `imperialax-ios`
  - project: `ios/ImperialAXMVPApp/ImperialAXMVPHost.xcodeproj`
  - scheme: `ImperialAXMVPHost`
  - simulator: `iPhone 17`
  - bundle id: `com.imperialax.mvp`
- Relaunched the app with `launch_app_sim`; process id `38382`.
- Opened the Laminate module via the `Open Laminate` button.

Verification:

- Browser mirror title: `Simulator - iPhone 17`.
- Browser mirror shows the iPhone 17 frame and the ImperialAX `Laminate v2`
  screen with the Wanted v2 / Classic switch and Response Forecast controls.

## 2026-06-18 iOS Live Laminate Preview Angle Fix

User reported that the angles looked wrong in the app's `LIVE LAMINATE PREVIEW`.

Updated file:

- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/ContentViewV2.swift`

Change:

- Replaced the previous approximate hatch slope calculation
  (`theta / 90 * shift`) with the same angle convention used by the web SVG:
  hatch direction now uses a true `-theta` rotation vector.
- Added clipping so the hatch lines stay inside each ply top surface while
  preserving the existing θ1/θ2 family colors and positive/negative sign colors.

Verification:

- `swift test --package-path ios/DDLaminateMVP` passed: 10 tests.
- XcodeBuildMCP `build_run_sim` succeeded for ImperialAX iOS host.
- Opened `ImperialAX > Laminate v2` in the simulator mirror and scrolled to
  `LIVE LAMINATE PREVIEW`.
- Visual check confirmed the default `θ1=30`, `θ2=-30` hatch lines now render as
  shallow angle-aware diagonals rather than near-vertical lines.
- iOS screenshot:
  - `/var/folders/7p/c3j_sb0j539805ngspmnb34r0000gn/T/screenshot_optimized_4a6a44fe-ebcc-46bd-8c1f-36d50c6a3690.jpg`

## 2026-06-18 Web v2 Angle Sliders

User asked to bring the prototype-style angle bars into the web first.

Updated files:

- `src/frontend/dd-laminate/index-v2.html`
- `src/frontend/dd-laminate/styles-v2.css`
- `src/frontend/dd-laminate/app-v2.js`

Change:

- Added range sliders to the `Response Forecast` and `u3 Forecast` theta input
  controls.
- Preserved numeric theta inputs and kept them as the submitted form values.
- Sliders and numeric inputs now sync both ways.
- Slider movement updates the readout and live laminate SVG preview immediately.
- Added filled slider track styling with responsive one-column stacking on mobile.
- Left `Curve CSV` unchanged because it is a post-simulation upload flow.

Verification:

- `node --check src/frontend/dd-laminate/app-v2.js` passed.
- HTML check found 43 ids, no duplicate ids, 4 theta range inputs, and 4 theta
  readouts.
- Browser check at `http://127.0.0.1:8000/index-v2.html`:
  - Response Forecast has 4 total theta sliders across Response/u3 forms.
  - Numeric `theta1=62.5` synced the Response slider/readout and produced SVG
    hatch transforms including `rotate(-62.5)`.
  - Dragging the Response `theta2` slider synced the number/readout and updated
    SVG hatch transforms.
  - u3 Forecast range value update synced the u3 number/readout and preview.
  - Mobile 390px check had no horizontal overflow and stacked angle controls in
    one column.

## 2026-06-18 iOS v2 Angle Sliders

User asked to apply the prototype-style angle bars to the app version too.

Updated file:

- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/ContentViewV2.swift`

Change:

- Replaced the Wanted v2 theta numeric field component with an angle control
  that keeps the numeric text field and adds a SwiftUI `Slider`.
- The shared Response/u3 input panel means both `Response Forecast` and
  `u3 Forecast` now get the slider controls.
- Slider changes write back into `viewModel.theta1/theta2`; numeric changes and
  slider changes therefore update the `LIVE LAMINATE PREVIEW` from the same
  state.
- Added `+/-` angle readouts above each field and accessibility identifiers:
  `v2-theta1-slider`, `v2-theta2-slider`.

Verification:

- `swift test --package-path ios/DDLaminateMVP` passed: 10 tests.
- XcodeBuildMCP `build_run_sim` succeeded for ImperialAX iOS host.
- Runtime snapshot confirmed `Theta 1`, `Theta 2`, `+30°/-30°`, and
  `LIVE LAMINATE PREVIEW` are visible after opening `ImperialAX > Laminate v2`.
- `wait_for_ui(identifier: "v2-theta1-slider")` found the slider with value
  `0.6666666865348816` at `+30°`.
- After setting the theta text field to `45`, runtime snapshot confirmed the
  readout changed to `+45°` and the slider accessibility value changed to
  `0.75`.
- XcodeBuildMCP simulator drag events cannot move sliders in this environment
  because `FBSimulatorHIDEvent` reports no touch-move support; visual and
  binding/accessibility verification passed.
- iOS screenshot:
  - `/var/folders/7p/c3j_sb0j539805ngspmnb34r0000gn/T/screenshot_optimized_b0067f35-1037-4675-a824-d0fa453f689b.jpg`

## 2026-06-18 ImperialAX App Icon Centering

User reported that the app icon looked shifted to one side and asked to center
it.

Updated files:

- `ios/ImperialAXMVPApp/ImperialAXMVPHost/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png`
- `ios/ImperialAXMVPApp/ImperialAXMVPHost/Assets.xcassets/AppIcon.appiconset/AppIcon-20@2x.png`
- `ios/ImperialAXMVPApp/ImperialAXMVPHost/Assets.xcassets/AppIcon.appiconset/AppIcon-20@3x.png`
- `ios/ImperialAXMVPApp/ImperialAXMVPHost/Assets.xcassets/AppIcon.appiconset/AppIcon-29@2x.png`
- `ios/ImperialAXMVPApp/ImperialAXMVPHost/Assets.xcassets/AppIcon.appiconset/AppIcon-29@3x.png`
- `ios/ImperialAXMVPApp/ImperialAXMVPHost/Assets.xcassets/AppIcon.appiconset/AppIcon-40@2x.png`
- `ios/ImperialAXMVPApp/ImperialAXMVPHost/Assets.xcassets/AppIcon.appiconset/AppIcon-40@3x.png`
- `ios/ImperialAXMVPApp/ImperialAXMVPHost/Assets.xcassets/AppIcon.appiconset/AppIcon-60@2x.png`
- `ios/ImperialAXMVPApp/ImperialAXMVPHost/Assets.xcassets/AppIcon.appiconset/AppIcon-60@3x.png`
- `ios/ImperialAXMVPApp/ImperialAXMVPHost/Assets.xcassets/AppIcon.appiconset/AppIcon-76@2x.png`
- `ios/ImperialAXMVPApp/ImperialAXMVPHost/Assets.xcassets/AppIcon.appiconset/AppIcon-83.5@2x.png`

Change:

- Recentered the 1024px ImperialAX app icon artwork on the white canvas by shifting
  the artwork about 61px left and 45px up.
- Regenerated every app icon size from the recentered 1024px source.

Verification:

- Pre-fix non-white artwork center was about `(577, 548-571)` depending on
  threshold, visibly right/down of the `(512, 512)` canvas center.
- Post-fix non-white artwork center is about `(516, 503-519)`, close to canvas
  center while preserving the icon scale and shadow.
- `sips` confirmed all app icon PNGs still have the expected dimensions.
- XcodeBuildMCP `build_run_sim` for ImperialAX iOS host succeeded.

## 2026-06-18 Public Domain Routing

User asked to connect the live sites so `cafedecafe.co.kr` keeps the existing
DD laminate UI and `imperialax.com` serves the new v2 UI.

Updated files:

- `src/backend/dd_laminate_app.py`
- `tests/backend/test_dd_laminate_ios_contract.py`
- `infrastructure/cloudflare/kclab-composite-ai.yml`
- `infrastructure/cloudflare/kclab-composite-ai.windows.example.yml`
- `scripts/windows/Check-Health.ps1`

Change:

- Added host-aware root routing in the standalone DD FastAPI app:
  - `imperialax.com` and `www.imperialax.com` return `index-v2.html`.
  - `cafedecafe.co.kr`, `www.cafedecafe.co.kr`, existing subdomains, and local
    default return the existing `index.html`.
- Added root/www ingress entries for both domains to the Cloudflare tunnel
  config.
- Added root/www public health checks for both domains to the Windows health
  script.
- Added backend tests that lock the host-to-UI routing behavior.

Production actions:

- Used `cloudflared tunnel route dns --overwrite-dns` to point these hostnames
  to tunnel `kclab-composite-ai`:
  - `cafedecafe.co.kr`
  - `www.cafedecafe.co.kr`
  - `imperialax.com`
  - `www.imperialax.com`
- Restarted local `cloudflared` with
  `infrastructure/cloudflare/kclab-composite-ai.yml`.
- Restarted DD FastAPI/Uvicorn on port `8000` so it loaded the new host-aware
  route code.

Verification:

- `.venv/bin/python -m pytest tests/backend/test_dd_laminate_ios_contract.py -q`
  passed: 7 tests.
- `cloudflared tunnel ingress validate` passed for
  `infrastructure/cloudflare/kclab-composite-ai.yml`.
- Local Host-header checks:
  - `cafedecafe.co.kr`, `www.cafedecafe.co.kr`, and `localhost`: legacy UI.
  - `imperialax.com`, `www.imperialax.com`: v2 UI.
- Public checks:
  - `https://cafedecafe.co.kr/` and `https://www.cafedecafe.co.kr/` return the
    legacy UI markers (`Double-Double Laminate Forecast`, `app.js`).
  - `https://imperialax.com/` and `https://www.imperialax.com/` return the v2 UI
    markers (`Wanted UI Kit Adaptation`, `app-v2.js`).
  - `/health` returns `200 {"status":"ok"}` for root/www plus existing
    `dd.cafedecafe.co.kr` and `laminate.imperialax.com`.

Note:

- An initial `cafedecafe` DNS route attempt was run without the cafedecafe
  origin cert and reported a relative imperialax-zone hostname. Public DNS lookup
  for that reported hostname returned no CNAME record, and it did not affect
  the intended public domain routes.

## 2026-06-18 Public Laminate URL Update

User changed the desired live URLs:

- v1 / existing UI: `https://laminate.cafedecafe.co.kr/`
- v2 / new UI: `https://laminate.imperialax.com/`

Updated files:

- `src/backend/dd_laminate_app.py`
- `tests/backend/test_dd_laminate_ios_contract.py`
- `infrastructure/cloudflare/kclab-composite-ai.yml`
- `infrastructure/cloudflare/kclab-composite-ai.windows.example.yml`
- `scripts/windows/Check-Health.ps1`

Change:

- Added `laminate.imperialax.com` to the FastAPI v2 root host set so the public
  imperialax laminate subdomain serves `index-v2.html`.
- Added `laminate.cafedecafe.co.kr` to Cloudflare tunnel ingress, mapped to the
  DD laminate service on port `8000`.
- Added the cafedecafe laminate URL to the public health-check list.
- Updated backend tests so the primary checked hosts are now:
  - `laminate.cafedecafe.co.kr`: legacy UI.
  - `laminate.imperialax.com`: v2 UI.

Production actions:

- Added the Cloudflare DNS tunnel route for
  `laminate.cafedecafe.co.kr` using the cafedecafe origin cert:
  `cloudflared --origincert ~/.cloudflared/cert.cafedecafe-20260611.pem tunnel route dns kclab-composite-ai laminate.cafedecafe.co.kr`.
- Restarted the local Cloudflare tunnel with the updated ingress config.
- Restarted the DD FastAPI/Uvicorn process on port `8000` so it loaded the
  updated host routing.

Verification:

- `.venv/bin/python -m pytest tests/backend/test_dd_laminate_ios_contract.py -q`
  passed: 7 tests.
- `cloudflared tunnel ingress validate` passed for
  `infrastructure/cloudflare/kclab-composite-ai.yml`.
- Local Host-header checks:
  - `laminate.cafedecafe.co.kr`: legacy UI.
  - `laminate.imperialax.com`: v2 UI.
- External browser fetch verified:
  - `https://laminate.cafedecafe.co.kr/` returns `Double-Double Laminate
    Forecast` / legacy UI.
  - `https://laminate.imperialax.com/` returns `Wanted UI Kit Adaptation` / v2 UI.
- `https://laminate.imperialax.com/health` returned `200 {"status":"ok"}`.
- Cloudflare IP `--resolve` checks for `https://laminate.cafedecafe.co.kr/`
  returned the legacy UI and `/health` returned `200 {"status":"ok"}`. The
  local macOS `curl` resolver still had a stale negative cache immediately
  after DNS creation, while `dig`, `host`, and the external browser fetch saw
  the new record.

## 2026-06-18 v2 Header Eyebrow Copy

User asked to remove the prototype label `Wanted UI Kit Adaptation` from the
top of the v2 screen and replace it with wording related to the laminate
product.

Updated files:

- `src/frontend/dd-laminate/index-v2.html`
- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/ContentViewV2.swift`
- `tests/backend/test_dd_laminate_ios_contract.py`

Change:

- Replaced the v2 header eyebrow text with `Composite Laminate AI` on both web
  and iOS v2.
- Updated backend HTML routing tests to use `Composite Laminate AI` as the v2
  marker and to ensure legacy UI does not show it.

Verification:

- `.venv/bin/python -m pytest tests/backend/test_dd_laminate_ios_contract.py -q`
  passed: 7 tests.
- `swift test --package-path ios/DDLaminateMVP` passed: 10 tests.
- XcodeBuildMCP `build_run_sim` for the ImperialAX iOS host succeeded.
- Runtime UI snapshot after opening Laminate showed `COMPOSITE LAMINATE AI`.
- `https://laminate.imperialax.com/` returned `Composite Laminate AI` and no
  longer returned `Wanted UI Kit Adaptation`.

## 2026-06-18 v2 Korean Version

User asked to add a Korean version of the current v2 state, focusing on
translation rather than changing functionality.

Updated files:

- `src/frontend/dd-laminate/index-v2.html`
- `src/frontend/dd-laminate/index-v2.ko.html`
- `src/frontend/dd-laminate/app-v2.js`
- `src/backend/dd_laminate_app.py`
- `tests/backend/test_dd_laminate_ios_contract.py`
- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/ContentViewV2.swift`
- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/DDLaminateModuleView.swift`

Change:

- Added `index-v2.ko.html`, a Korean static page that keeps the v2 layout,
  IDs, forms, scripts, and model behavior intact.
- Changed the English v2 `한국어` link to point to `index-v2.ko.html`; the Korean
  v2 page links back to `index-v2.html`.
- Added `/dd-laminate-v2-ko` to the standalone FastAPI app.
- Extended `app-v2.js` Korean dynamic text for chart/report labels and the
  current simplified model names.
- Localized the iOS v2 screen through the existing language toggle:
  - header, workflow strip, mode tabs, input panel, model card/sheet,
    connection status, empty/result panels, XAI preview title, and live ply
    preview text.
- Renamed the app design picker label from `Wanted v2` to `v2`.

Verification:

- Browser check at `http://127.0.0.1:8000/index-v2.ko.html` confirmed:
  - `lang="ko"`
  - header `복합재 적층 AI` / `ImperialAX 적층 예측`
  - mode buttons `응답 예측`, `u3 예측`, `곡선 CSV`
  - response button `예측 실행`
  - language links to `Classic` and `English`.
- Public checks:
  - `https://laminate.imperialax.com/index-v2.ko.html`
  - `https://laminate.imperialax.com/dd-laminate-v2-ko`
  both returned Korean v2 markers including `복합재 적층 AI`, `ImperialAX 적층 예측`,
  `응답 예측`, and `예측 실행`.
- `.venv/bin/python -m pytest tests/backend/test_dd_laminate_ios_contract.py -q`
  passed: 8 tests.
- `node --check src/frontend/dd-laminate/app-v2.js` passed.
- `swift test --package-path ios/DDLaminateMVP` passed: 10 tests.
- XcodeBuildMCP `build_run_sim` succeeded for the ImperialAX host app.
- Runtime UI snapshot after opening Laminate and tapping the language button
  showed Korean v2 text:
  - `복합재 적층 AI`
  - `API 준비됨`
  - `ImperialAX 적층 예측`
  - `응답 예측`
  - `적층 예측 프로그램`
  - `적층 예측 - Machine Learning`

## 2026-06-18 Integer Angle Inputs

User noted that laminate angles do not need decimal places.

Change:

- Updated DD laminate web inputs so theta fields use integer step size:
  - `index.html`
  - `index.ko.html`
  - `index-v2.html`
  - `index-v2.ko.html`
- Updated web submit/report behavior:
  - `app.js` and `app-v2.js` round theta values to whole degrees before
    submit.
  - Result input chips, generated report text, and export filenames now show
    theta values without decimal places.
  - v2 live slider/readout now moves by 1 degree and displays whole-degree
    labels only, e.g. `+30°`.
- Updated iOS behavior:
  - v2 angle sliders now use `step: 1`.
  - v2 angle readouts and live ply preview round to whole degrees.
  - `PredictionViewModel` normalizes theta values before prediction so typed
    decimal input such as `30.6` becomes `31`.
  - Recent-run displays and comparison/detail text use integer theta display
    values, including older saved runs that may contain decimals.
- Added Swift test coverage for theta rounding before prediction.

Verification:

- `node --check src/frontend/dd-laminate/app-v2.js` passed.
- `node --check src/frontend/dd-laminate/app.js` passed.
- `swift test --package-path ios/DDLaminateMVP` passed: 11 tests.
- `.venv/bin/python -m pytest tests/backend/test_dd_laminate_ios_contract.py -q`
  passed: 8 tests, 1 existing pytest config warning.
- Static scan confirmed no `step="0.1"` remains in the DD laminate HTML pages.
- XcodeBuildMCP `build_run_sim` succeeded for ImperialAX iOS host app.
- Runtime simulator snapshot after opening Laminate v2 and scrolling to inputs
  showed integer values/readouts:
  - text fields: `30`, `-30`
  - readouts: `+30°`, `-30°`

## 2026-06-18 v2 Model Title Single Line

User reported that the app v2 selected model card wrapped
`적층 예측 - Machine Learning` onto two lines while `Deep Learning` fit on one.

Change:

- Updated `ContentViewV2.swift` selected model button title styling:
  - one-line title
  - lower minimum scale factor
  - text tightening enabled
  - title stack given layout priority
  - chevron/check icons fixed so they do not steal unstable text width.
- Applied the same one-line behavior to model option titles in the model sheet.

Verification:

- `swift test --package-path ios/DDLaminateMVP` passed: 11 tests.
- XcodeBuildMCP `build_run_sim` succeeded for ImperialAX iOS host app.
- Runtime screenshot showed `적층 예측 - Machine Learning` on one line in the
  selected model card.

## 2026-06-18 Android Parity Status Check

User asked whether the Android version has also been kept updated.

Current status:

- Android projects exist:
  - `android/DDLaminateMVP`
  - `android/InjectionMVP`
  - `android/ImperialAXMVP`
- Earlier Android work was kept in sync for several major product areas:
  - unified ImperialAX/ImperialAX shell
  - Laminate and Injection Android activities
  - Korean resources
  - model label simplification
  - XAI/result/chart updates
  - debug APK artifact refreshes under `artifacts/android`.
- Recent v2-focused work has not been fully mirrored to Android:
  - Wanted/v2-style laminate UI
  - live angle-aware ply stack preview
  - latest Korean v2 page parity
  - integer-only theta input normalization
  - one-line selected model title treatment.

Recommendation:

- Treat Android as behind the current web/iOS v2 surface.
- Next Android parity pass should update `android/ImperialAXMVP` and/or
  `android/DDLaminateMVP` depending on whether the target is the unified ImperialAX
  shell or standalone Laminate MVP.

## 2026-06-18 Android Laminate Parity Pass

User asked to start maintaining/building the Android version because Android
users are important for future Korean deployment.

Scope implemented:

- Updated standalone Laminate app `android/DDLaminateMVP`:
  - default response model is now `response_surrogate_physics_v2`
  - model picker exposes only the two optimal response families:
    - `Laminate Forecast - Machine Learning`
    - `Laminate Forecast - Deep Learning`
  - legacy response keys still gracefully map to the same two families when an
    older API server is used.
  - theta inputs are integer-only in the keyboard and normalized to whole
    degrees before prediction.
  - recent-run detail, comparison labels, share text, and image report inputs
    display theta values without decimal places.
  - result XAI/feature-impact list shows the top 5 first and hides the rest
    behind an expandable button.
  - English and Korean model descriptions and XAI expand/collapse strings were
    updated.
- Updated unified ImperialAX Android app `android/ImperialAXMVP` Laminate activity:
  - default response model is now `response_surrogate_physics_v2`.
  - model selector is limited to the Machine Learning / Deep Learning response
    families with legacy fallback.
  - theta inputs are integer-only and normalized before API submission.
  - result XAI feature list shows top 5 first and hides the rest behind a
    show/hide button.
  - old technical model labels are cleaned into user-facing Machine Learning /
    Deep Learning names.
- Refreshed Android debug APK artifacts:
  - `artifacts/android/ImperialAX-Laminate-debug.apk`
  - `artifacts/android/Laminate-ImperialAX-debug.apk`
  - `artifacts/android/ImperialAX-debug.apk`
  - `artifacts/android/ImperialAX-debug.apk`

Verification:

- `JAVA_HOME=/opt/homebrew/opt/openjdk@17 gradle :app:assembleDebug` passed in
  `android/DDLaminateMVP`.
- `JAVA_HOME=/opt/homebrew/opt/openjdk@17 gradle :app:assembleDebug` passed in
  `android/ImperialAXMVP`.
- `git diff --check` passed for modified Android source/resource files.
- APK signature verification with
  `/opt/homebrew/share/android-commandlinetools/build-tools/35.0.0/apksigner`
  passed for:
  - `artifacts/android/ImperialAX-Laminate-debug.apk`
  - `artifacts/android/ImperialAX-debug.apk`

Remaining Android parity gap:

- Android still does not have the full web/iOS v2 visual redesign or the live
  angle-aware ply stack preview. The current pass brings the prediction/model
  behavior up to date first.

## 2026-06-18 Android Laminate UI Preview Pass

User asked whether the Android UI portion could also be applied.

Scope implemented:

- Added Android native `PlyStackPreviewView` Canvas components to:
  - `android/DDLaminateMVP`
  - `android/ImperialAXMVP`
- The preview follows the same v2 ply sequence logic as web/iOS:
  - Case2: `[[+/-theta1]/[+/-theta2]] x 4`
  - Case3: `[[+/-theta1]/[+/-theta2]/[-/+theta1]/[-/+theta2]] x 2`
  - Case4: `([+/-theta1]/[+/-theta2]) x 2 + ([-/+theta1]/[-/+theta2]) x 2`
- Added angle slider controls to both Android Laminate entry points:
  - numeric theta inputs remain available
  - sliders use integer degrees from `-90` to `90`
  - slider changes update text fields, readouts, and preview immediately
  - text-field changes update sliders and preview when valid
- Added live laminate preview cards:
  - title/subtitle
  - ply count badge
  - theta1/theta2/+/- legend
  - formula row
  - compact-physics note
- Updated `DESIGN.md` component inventory to include Android live laminate
  preview.
- Refreshed Android debug APK artifacts:
  - `artifacts/android/ImperialAX-Laminate-debug.apk`
  - `artifacts/android/Laminate-ImperialAX-debug.apk`
  - `artifacts/android/ImperialAX-debug.apk`
  - `artifacts/android/ImperialAX-debug.apk`

Verification:

- `JAVA_HOME=/opt/homebrew/opt/openjdk@17 gradle :app:assembleDebug` passed in
  `android/DDLaminateMVP`.
- `JAVA_HOME=/opt/homebrew/opt/openjdk@17 gradle :app:assembleDebug` passed in
  `android/ImperialAXMVP`.
- `git diff --check` passed for modified Android source/resource files.
- APK signature verification passed for:
  - `artifacts/android/ImperialAX-Laminate-debug.apk`
  - `artifacts/android/ImperialAX-debug.apk`
- Runtime visual smoke test was not run in this turn because `adb` is not
  available on the current PATH.

Remaining Android UI gap:

- Android now has the live angle-aware laminate preview and slider controls, but
  it still is not a full one-to-one recreation of the web/iOS v2 visual shell.
  The current Android pass intentionally keeps native Kotlin Views and existing
  screen structure.

## 2026-06-18 Android ImperialAX APK Clarification

User asked whether installing `ImperialAX-debug.apk` shows the same integrated version
as the iOS unified app.

Clarification:

- `artifacts/android/ImperialAX-debug.apk` is the unified Android ImperialAX/ImperialAX shell
  built from `android/ImperialAXMVP`.
- It should show the same product concept as the iOS unified app: a ImperialAX module
  workspace with access to the Laminate module and other module entries.
- It is not pixel-for-pixel identical to the iOS unified UI. Android uses native
  Kotlin Views, while iOS uses SwiftUI.
- The Laminate Android module now includes the latest core parity work:
  two-model selection, integer theta inputs, XAI top-5 expansion, angle sliders,
  and live angle-aware laminate preview.

## 2026-06-18 Android Unified App v2 Visual Pass

User pointed out that the Android build still felt like v1 even after the
functional parity updates.

Scope implemented:

- Restyled the unified Android ImperialAX/ImperialAX shell in `android/ImperialAXMVP` toward
  the v2 visual direction:
  - white canvas
  - larger ImperialAX hero treatment
  - blue action accents
  - black command-style primary buttons
  - light bordered module panels
  - step/status strips closer to the web/iOS v2 structure
- Restyled the Android Laminate screen in `android/ImperialAXMVP`:
  - `ImperialAX Laminate Forecast` hero
  - response-forecast framing
  - v2-style input/result cards
  - blue and green status pills
  - black `Predict Forecast` command button
  - v2-toned live laminate preview card
  - v2-toned XAI top-5 expansion controls
- Refreshed Android debug APK artifacts:
  - `artifacts/android/ImperialAX-debug.apk`
  - `artifacts/android/ImperialAX-debug.apk`

Verification:

- `JAVA_HOME=/opt/homebrew/opt/openjdk@17 gradle :app:assembleDebug` passed in
  `android/ImperialAXMVP`.
- `git diff --check` passed for the modified Android source files.
- APK signature verification passed for:
  - `artifacts/android/ImperialAX-debug.apk`
  - `artifacts/android/ImperialAX-debug.apk`
- Runtime emulator visual smoke test was not run because `adb` is unavailable on
  the current PATH.

Remaining note:

- This is now much closer to the v2 tone, but it is still a native Android
  Kotlin Views implementation rather than a pixel-perfect clone of the SwiftUI
  or web v2 screens.

## 2026-06-18 iOS Xcode Install Prep

User asked to open Xcode so they can install the iOS app on their physical
iPhone.

Action:

- Opened the unified iOS host project:
  - `ios/ImperialAXMVPApp/ImperialAXMVPHost.xcodeproj`

Install notes for the next step:

- In Xcode, select the connected iPhone from the top device selector.
- Select the ImperialAX/ImperialAX host scheme if Xcode does not choose it
  automatically.
- If signing fails, set the Apple Developer Team under the target's
  `Signing & Capabilities` tab.
- Then press Run to build and install on the iPhone.

## 2026-06-18 Android Result Navigation and Home Quick Actions

User asked for Android prediction results to open as a separate result page
instead of rendering below the input form. User also asked to move the Demo
Account card and module entry cards into small icons near the top ImperialAX header,
and to center the Android launcher icon.

Scope implemented in `android/ImperialAXMVP`:

- Added `LaminateResultActivity`.
- Registered `LaminateResultActivity` in `AndroidManifest.xml`.
- Changed successful Laminate response predictions so `Predict response` opens
  the result page with:
  - Type
  - confidence
  - Pt
  - Pt displacement
  - max force
  - curve point count
  - class probabilities
  - XAI top 5 with expandable remaining features
- Kept prediction errors on the input screen.
- Changed the signed-in ImperialAX Android home screen:
  - account access is now a compact `A` icon beside the ImperialAX header
  - Laminate opens from a compact `L` icon
  - Injection opens from a compact `I` icon
  - the large account/module cards are no longer rendered as the main home
    content
- Regenerated Android launcher PNGs from the iOS ImperialAX icon source with the
  foreground recentered for all density buckets:
  - mdpi
  - hdpi
  - xhdpi
  - xxhdpi
  - xxxhdpi
- Refreshed Android APK artifacts:
  - `artifacts/android/ImperialAX-debug.apk`
  - `artifacts/android/ImperialAX-debug.apk`

Verification:

- `JAVA_HOME=/opt/homebrew/opt/openjdk@17 gradle :app:assembleDebug` passed in
  `android/ImperialAXMVP`.
- `git diff --check` passed for modified Android source/manifest files and
  `docs/session-memory.md`.
- APK signature verification passed for:
  - `artifacts/android/ImperialAX-debug.apk`
  - `artifacts/android/ImperialAX-debug.apk`
- Runtime emulator visual smoke test was not run because `adb` is unavailable on
  the current PATH.

## 2026-06-18 Android Icon Recheck and Drive Upload Attempt

User again asked to center the Android launcher icon and upload the newly
modified APK to the Google Drive folder:

- `https://drive.google.com/drive/u/0/folders/1iwONaQdOAA0l1eVki5xdVgH6edAueZ9G`

Status:

- Rechecked Android launcher icon foreground centering for all ImperialAXMVP
  density buckets.
- Pixel bounding-box centers are within roughly `0.5px` of the canvas center
  across mdpi/hdpi/xhdpi/xxhdpi/xxxhdpi.
- Latest APK is available at:
  - `artifacts/android/ImperialAX-debug.apk`
  - `artifacts/android/ImperialAX-debug.apk`
- Also copied the latest ImperialAX APK to:
  - `/Users/danlee/Desktop/android/ImperialAX-debug.apk`

Drive upload attempt:

- Opened the Drive folder in the in-app browser.
- User logged in as `Danny Lee`; the folder `APP` became visible.
- Existing files visible in the folder:
  - `ImperialAX-debug.apk`
  - `Laminate-ImperialAX-debug.apk`
- Opened Drive's `신규` menu and selected `파일 업로드`.
- Automated file selection failed because macOS blocked `osascript` keystroke
  injection:
  - `osascript에서 키스트로크를 보내도록 허용되지 않습니다. (1002)`
- No Google Drive CLI, rclone config, gcloud auth, mounted Google Drive folder,
  or Google Drive Desktop sync path was found locally.

Current blocker:

- Upload is ready but not completed. User needs to manually select
  `ImperialAX-debug.apk` in the open macOS file picker, or grant the app/terminal
  Accessibility permission for automated file picker control.
- After the user selects the file, Codex can verify the Drive upload result from
  the Drive page.

## 2026-06-18 Android Home Quick Action Revision

User clarified that only the account icon should remain beside the top ImperialAX
header. Laminate and Injection should appear as module cards as before.

Scope implemented in `android/ImperialAXMVP`:

- Updated `MainActivity` signed-in home layout:
  - kept only the compact `A` account icon beside the ImperialAX header
  - removed compact `L` and `I` header shortcuts
  - restored the `MODULES` section below the workflow strip
  - restored the module card list so Laminate/Injection open from cards again
- Refreshed Android APK artifacts:
  - `artifacts/android/ImperialAX-debug.apk`
  - `artifacts/android/ImperialAX-debug.apk`
  - `/Users/danlee/Desktop/android/ImperialAX-debug.apk`

Verification:

- `JAVA_HOME=/opt/homebrew/opt/openjdk@17 gradle :app:assembleDebug` passed in
  `android/ImperialAXMVP`.
- APK signature verification passed for `artifacts/android/ImperialAX-debug.apk`.
- `git diff --check` passed for the modified Android source file and
  `docs/session-memory.md`.

Drive note:

- The Drive folder remains open and logged in, but automatic file picker control
  is still blocked by macOS Accessibility permissions. The latest APK is ready
  for manual selection from `/Users/danlee/Desktop/android/ImperialAX-debug.apk`.

## 2026-06-19 Android Font and iOS Header Wrapping

User asked to modernize the Android font and make long iOS titles avoid awkward
single-line wrapping.

Android ImperialAXMVP changes:

- Bundled Pretendard font files:
  - `android/ImperialAXMVP/app/src/main/res/font/pretendard_regular.otf`
  - `android/ImperialAXMVP/app/src/main/res/font/pretendard_semibold.otf`
  - `android/ImperialAXMVP/app/src/main/res/font/pretendard_bold.otf`
- Added `AppFonts.kt` to centralize app font loading.
- Updated the app theme to use Pretendard regular as the default font family.
- Updated key labels, buttons, quick-action icons, module cards, result pages,
  and laminate preview text to use the app font while preserving monospace
  numeric inputs.

iOS title treatment:

- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/ContentViewV2.swift`
  now renders the app headline as `ImperialAX` followed by `Laminate Forecast` on the
  next line, with two-line limits and scaling guards.
- `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/ContentView.swift`
  uses the same `ImperialAX` / `Laminate Forecast` title treatment.
- `ios/ImperialAXMVP/Sources/ImperialAXApp/LaminateForecastView.swift`
  uses `ImperialAX` / `Laminate Forecast`.
- `ios/ImperialAXMVP/Sources/ImperialAXApp/InjectionForecastView.swift`
  uses `ImperialAX` / `Injection Forecast`.

Verification:

- `git diff --check` passed.
- `JAVA_HOME=/opt/homebrew/opt/openjdk@17 gradle :app:assembleDebug` passed in
  `android/ImperialAXMVP`.
- APK signature verification passed for:
  - `artifacts/android/ImperialAX-debug.apk`
  - `artifacts/android/ImperialAX-debug.apk`
- Refreshed APK artifacts:
  - `artifacts/android/ImperialAX-debug.apk`
  - `artifacts/android/ImperialAX-debug.apk`
  - `/Users/danlee/Desktop/android/ImperialAX-debug.apk`
- XcodeBuildMCP simulator build passed for `ImperialAXMVPHost` on `iPhone 17`.
- XcodeBuildMCP simulator build passed for the `KyulAIDDLaminateApp` target.

Known note:

- `DDLaminateMVPHost` still has a target configuration problem unrelated to
  this title change: it references missing file
  `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/KyulAIDDLaminateApp.swift`.
  The changed SwiftUI package target itself compiles successfully through the
  `KyulAIDDLaminateApp` scheme.

## 2026-06-19 iOS Laminate Title Follow-Up

User reported that the iOS title change did not appear reflected.

Finding:

- The previous update changed the large v2 headline, but the actual visible
  input panel title still said `Laminate Prediction Program`.
- On simulator, the top headline also briefly showed `Laminate F...` because
  the API status badge shared the same horizontal row and constrained the title
  width.

Fix:

- Updated `ContentViewV2.swift` so the visible response input panel title is
  also `ImperialAX` / `Laminate Forecast`.
- Updated the u3 input panel title to `ImperialAX` / `u3 Pt Forecast`.
- Reworked the v2 header layout so the eyebrow/status badge occupy the first
  row and the large `ImperialAX` / `Laminate Forecast` title uses the full card width.
- Added two-line/scaling guards to panel titles.

Verification:

- Rebuilt and ran `ImperialAXMVPHost` on the `iPhone 17` simulator with
  XcodeBuildMCP.
- Runtime UI snapshot confirmed:
  - `ImperialAX Laminate Forecast`
  - `ImperialAX u3 Pt Forecast`
- Simulator screenshots confirmed that both the hero card and input panel show
  `ImperialAX` on the first line and `Laminate Forecast` fully on the second line,
  without ellipsis.
- `git diff --check` passed.

## 2026-06-19 iOS Title Hierarchy Discussion

User noticed that the top hero title and lower input panel title both repeat
`ImperialAX Laminate Forecast`, which feels redundant.

Recommendation captured for next UI pass:

- Keep the top hero as the product/app identity:
  - `ImperialAX`
  - `Laminate Forecast`
- Make the lower active panel title task-specific instead of repeating the app
  name:
  - Response tab: `Response Forecast`
  - u3 tab: `u3 Pt Forecast`
- Keep or remove the small blue eyebrow, but avoid showing `RESPONSE FORECAST`
  and `Response Forecast` directly together unless the title is changed to a
  more action-oriented phrase such as `Predict Response Curve`.
- Best default direction: remove the duplicated lower `ImperialAX Laminate Forecast`
  and use task labels so the screen hierarchy reads as product -> workflow ->
  active task.

## 2026-06-19 iOS Title Hierarchy Applied

User asked to apply and show the title hierarchy recommendation.

Applied in `ContentViewV2.swift`:

- Kept the top hero as the product/app identity:
  - `ImperialAX`
  - `Laminate Forecast`
- Changed the lower active panel eyebrow to:
  - `Forecast Setup`
- Changed the lower active panel title by tab:
  - Response tab: `Response Forecast`
  - u3 tab: `u3 Pt Forecast`
- Removed the lower duplicate `ImperialAX Laminate Forecast` wording from the input
  panel.

Verification:

- Rebuilt and ran `ImperialAXMVPHost` on the `iPhone 17` simulator with
  XcodeBuildMCP.
- Runtime UI snapshot confirmed:
  - `Forecast Setup`
  - `Response Forecast`
  - `u3 Pt Forecast`
- Simulator screenshot confirmed the Response panel hierarchy is now visually
  distinct from the top hero.
- `git diff --check` passed.

## 2026-06-19 Web/App UI Parity Rule and Alignment

User noted that the web and app started to look different and explicitly asked
to keep them moving together.

Standing product rule:

- Shared ImperialAX Laminate Forecast surfaces should be updated together across:
  - Web v2 English/Korean
  - iOS v2
  - Android ImperialAX native app
- When changing shared labels, hierarchy, model names, core layout, or primary
  forecast workflow UI, check the corresponding web and native app surfaces in
  the same pass.
- Web-only features can remain web-only, but their surrounding shared UI should
  still follow the same hierarchy and wording.

Applied alignment:

- Web v2 English:
  - hero title split into `ImperialAX` / `Laminate Forecast`
  - API badge changed to `API ready`
  - workflow step 03 changed to `Review` / `Pt, curve, XAI.`
  - response panel changed to `Forecast Setup` / `Response Forecast`
  - u3 panel changed to `Forecast Setup` / `u3 Pt Forecast`
- Web v2 Korean:
  - hero title split into `ImperialAX` / `적층 예측`
  - API badge changed to `API 준비됨`
  - response panel changed to `예측 설정` / `응답 예측`
  - u3 panel changed to `예측 설정` / `u3 Pt 예측`
- Android ImperialAX Laminate:
  - top title changed to `ImperialAX` / `Laminate Forecast`
  - input card changed to `FORECAST SETUP` / `Response Forecast`
  - workflow steps changed to `Set case`, `Pick model`, `Review`

Verification:

- `git diff --check` passed.
- Android `JAVA_HOME=/opt/homebrew/opt/openjdk@17 gradle :app:assembleDebug`
  passed for `android/ImperialAXMVP`.
- Android APK artifacts refreshed and signature verification passed for
  `artifacts/android/ImperialAX-debug.apk`.
- XcodeBuildMCP `build_run_sim` passed for `ImperialAXMVPHost`.
- Browser DOM checks passed for:
  - `http://127.0.0.1:8000/index-v2.html`
  - `http://127.0.0.1:8000/index-v2.ko.html`
- Browser screenshot confirmed the English web v2 now matches the app title
  hierarchy.

## 2026-06-19 ImperialAX Web Login v2 Prototype

User asked whether there was an existing web login page and requested a new
example using the recently added Figma/Wanted UI Kit direction.

Context found:

- Existing ImperialAX web login already lives in `src/frontend/imperialax/index.html`
  with `styles.css` and `app.js`.
- It signs into the same local/session key flow:
  `imperialax.auth.session.v1`.
- The uploaded `design/Wanted Design System (Community).fig` is a zipped Figma
  package; `canvas.fig` is binary, so direct layer extraction was not available.
  Usable evidence was the package metadata, thumbnail, and the existing
  `DESIGN.md` Wanted-inspired direction.

Applied:

- Added a separate reversible prototype instead of replacing the current login:
  - `src/frontend/imperialax/login-v2.html`
  - `src/frontend/imperialax/login-v2.css`
  - `src/frontend/imperialax/login-v2.js`
- The prototype uses a Wanted-inspired ImperialAX treatment:
  - white/light grid canvas
  - black command/forecast preview surface
  - blue primary accents
  - green readiness/access states
  - compact 8px-radius panels
- The login remains functional for MVP demo accounts:
  - `demo@imperialax.com`
  - `danlee@imperialax.com`
- `Continue demo` stores the compatible ImperialAX session and redirects to the
  existing workspace at `src/frontend/imperialax/index.html`.
- Mobile layout was adjusted so the sign-in panel appears before the larger
  workspace preview.
- Updated `DESIGN.md` to record the ImperialAX `login-v2` prototype.

Verification:

- `git diff --check` passed.
- In-app browser rendered:
  `http://127.0.0.1:8032/imperialax/login-v2.html`
- Desktop DOM check confirmed:
  - `ImperialAX Account Access`
  - `Sign in`
  - `Demo ready`
  - Laminate, Injection, Optimization module rows
  - no horizontal overflow at the current browser width
- Mobile viewport check at 390px confirmed:
  - no horizontal overflow
  - `.login-panel` appears before `.workspace-panel`
- Demo login flow check confirmed:
  - `Continue demo` navigates to `/imperialax/index.html`
  - workspace is visible
  - account label shows `ImperialAX Demo · 2 modules`

## 2026-06-19 ImperialAX Domain IA Update

User clarified the intended public domain split:

- `ai.imperialax.com`: ImperialAX App entry point, including first login and module
  selection for Laminate, Injection, and future Optimization.
- `laminate.imperialax.com`: Laminate Forecast module reached from the ImperialAX AI
  workspace.
- `injection.imperialax.com`: Injection module remains a standalone module domain.
- `imperialax.com`: reserved for the future official company/product homepage, not
  the current app.

Applied:

- Added `ai.imperialax.com` to Cloudflare tunnel ingress on port `8000`.
- Removed `imperialax.com` and `www.imperialax.com` from the app ingress config so
  the official homepage domain is no longer used as the app surface.
- Added the same ingress change to the Windows tunnel example.
- Updated public `dd_laminate_app` host routing because port `8000` is the
  current public entry process:
  - `ai.imperialax.com/` serves `src/frontend/imperialax/login-v2.html`.
  - `ai.imperialax.com/index.html`, `/app.js`, and `/styles.css` serve the ImperialAX
    module workspace files.
  - `laminate.imperialax.com/` continues to serve DD Laminate v2.
- Updated standalone `imperialax_app` root routing so `ai.imperialax.com` also serves
  the login v2 entry when run directly.
- Changed Optimization module URLs away from `https://imperialax.com` to
  `https://ai.imperialax.com`.
- Renamed the ImperialAX web workspace visible shell to `ImperialAX App` /
  `ImperialAX AI Workspace`.
- Updated migration docs to record that port `8000` is host-routed for both
  the ImperialAX AI workspace and Laminate.

Deployment actions:

- Ran:
  `cloudflared tunnel route dns --overwrite-dns kclab-composite-ai ai.imperialax.com`
- Restarted the port `8000` `dd_laminate_app` uvicorn process.
- Restarted `cloudflared` with
  `infrastructure/cloudflare/kclab-composite-ai.yml`.

Verification:

- `cloudflared tunnel --config infrastructure/cloudflare/kclab-composite-ai.yml
  ingress validate` returned `OK`.
- `.venv/bin/python -m pytest tests/backend/test_imperialax_modules.py
  tests/backend/test_dd_laminate_ios_contract.py -q` passed:
  `18 passed, 1 warning`.
- `git diff --check` passed.
- Public checks confirmed:
  - `https://ai.imperialax.com/` returns `ImperialAX Account Access`.
  - `https://ai.imperialax.com/index.html` returns `ImperialAX App` and
    `Prediction modules`.
  - `https://ai.imperialax.com/api/v1/modules` lists Laminate and Injection module
    URLs plus Optimization pointing to `https://ai.imperialax.com`.
  - `https://laminate.imperialax.com/` returns `ImperialAX Laminate Forecast v2`.
  - `https://imperialax.com/` returns HTTP `404`, leaving it free for the future
    official homepage.

## 2026-06-19 ImperialAX Login Module Icons

User noticed that the small logo/icon boxes beside Laminate, Injection, and
Optimization in the `SELECTED ACCOUNT` area looked empty.

Applied:

- Updated `src/frontend/imperialax/login-v2.html` so each module row uses an inline
  SVG icon instead of a placeholder letter:
  - Laminate: stacked ply/layer icon
  - Injection: injection/pressure icon
  - Optimization: target/search icon
- Updated `src/frontend/imperialax/login-v2.css` with distinct icon colors:
  - Laminate blue
  - Injection teal
  - Optimization gray when locked, amber when enabled
- Added `v=20260619-module-icons` cache-busting query strings for
  `login-v2.css` and `login-v2.js`.

Verification:

- `git diff --check` passed.
- `node --check src/frontend/imperialax/login-v2.js` passed.
- Public checks confirmed `https://ai.imperialax.com/` serves the updated SVG
  markup and CSS.
- In-app browser DOM check confirmed all three `.module-icon` elements contain
  one SVG each.
- Browser screenshot confirmed the Selected Account module icons render visibly.

## 2026-06-19 Web Laminate Title Spacing

User noticed the web Laminate v2 hero title read as `ImperialAXLaminate Forecast`
without a space.

Applied:

- Updated `src/frontend/dd-laminate/index-v2.html` from
  `<span>ImperialAX</span><span>Laminate Forecast</span>` to
  `<span>ImperialAX</span> <span>Laminate Forecast</span>`.
- Updated `src/frontend/dd-laminate/index-v2.ko.html` similarly so its DOM text
  reads `ImperialAX 적층 예측`.

Verification:

- `git diff --check` passed.
- Public HTML check confirmed `https://laminate.imperialax.com/` contains the
  inserted space.
- In-app browser DOM check confirmed `#app-title.textContent` is exactly
  `ImperialAX Laminate Forecast`.

## 2026-06-19 ImperialAX AI Workspace V2 Shell

User asked to remove the extra top navigation on `ai.imperialax.com` and leave
only the logo, then make `ai.imperialax.com/index.html` feel more like the newer
Laminate v2 / Figma-derived direction instead of the older MVP shell.

Applied:

- Updated `src/frontend/imperialax/login-v2.html` and
  `src/frontend/imperialax/login-v2.css` so the login page top area keeps only a
  compact `ImperialAX` wordmark and removes the `Module workspace` / `Laminate v2`
  links.
- Redesigned `src/frontend/imperialax/index.html` as a v2-style module workspace:
  large `ImperialAX App` hero, clearer workspace copy, account/readiness chip,
  three-step flow strip, selected account band, dark module-intro band, and
  stronger module cards.
- Rebuilt `src/frontend/imperialax/styles.css` around the newer v2 visual system:
  light technical grid, white panels, black action blocks, blue/green accent
  language, 8px card radii, responsive desktop/mobile spacing, and no floating
  marketing-style hero.
- Updated `src/frontend/imperialax/app.js` so Laminate, Injection, and
  Optimization module cards use inline SVG icons instead of placeholder
  letters.
- Updated `DESIGN.md` to record the ImperialAX login and workspace shell as part
  of the shared design source of truth.

Verification:

- `git diff --check` passed.
- `node --check src/frontend/imperialax/app.js` and
  `node --check src/frontend/imperialax/login-v2.js` passed.
- `.venv/bin/python -m pytest tests/backend/test_imperialax_modules.py
  tests/backend/test_dd_laminate_ios_contract.py -q` passed:
  `18 passed, 1 warning`.
- Public checks confirmed:
  - `https://ai.imperialax.com/` serves the logo-only top area with no
    `Module workspace` / `Laminate v2` links.
  - `https://ai.imperialax.com/index.html` serves the cache-busted v2 workspace
    CSS and JS.
  - The workspace JS contains SVG module icons.
- In-app browser checks confirmed:
  - Root login page title is `ImperialAX Account Access`.
  - Root login page has `brand = ImperialAX`, no topbar action links, and no
    `Module workspace` / `Laminate v2` body text.
  - Workspace page opens after demo login with three module cards, each module
    card has an SVG icon, and the visible UI matches the v2 workspace direction.

## 2026-06-19 ImperialAX Workspace Title, Korean Pages, And API Hiding

User pointed out that `ImperialAX App` on `ai.imperialax.com/index.html` felt too
placeholder-like, the subtitle wrapped awkwardly, module cards exposed API
paths, the font needed refinement, and Korean versions were missing for the
ImperialAX hub.

Applied:

- Renamed the ImperialAX workspace page from `ImperialAX App` to
  `ImperialAX Forecast Workspace`.
- Changed the Korean workspace title to `ImperialAX 예측 워크스페이스`.
- Rewrote the hero subtitle to a shorter, intentional line:
  `Choose Laminate or Injection, then continue to the dedicated prediction screen.`
- Added `src/frontend/imperialax/index.ko.html`.
- Added `src/frontend/imperialax/login-v2.ko.html`.
- Updated `src/frontend/imperialax/app.js` so Korean pages localize dynamic module
  card summaries, badges, action buttons, module counts, access-copy text, and
  capability labels.
- Updated `src/frontend/imperialax/login-v2.js` so Korean login status text and
  post-login redirect go to `index.ko.html`.
- Removed the module-card API path display by deleting the card-level
  `.route-text` element and no longer writing `module.route.api_prefix` into
  cards.
- Kept modal access copy user-facing instead of exposing raw entitlement keys.
- Updated `src/frontend/imperialax/styles.css` and
  `src/frontend/imperialax/login-v2.css` to use a Pretendard-first font stack with
  Korean-friendly fallbacks.
- Added `/index.ko.html` and `/login-v2.ko.html` host-routed entries to
  `src/backend/dd_laminate_app.py` so `ai.imperialax.com` can serve the ImperialAX
  Korean pages through the current public 8000 app.
- Updated `DESIGN.md` to record the workspace naming, Korean page coverage, and
  Pretendard-first web typography decision.

Translation coverage note:

- Main product surfaces now have Korean variants:
  - ImperialAX login: `login-v2.ko.html`
  - ImperialAX module workspace: `index.ko.html`
  - Laminate Classic: `index.ko.html`
  - Laminate v2: `index-v2.ko.html`
  - Simple Injection: `index.ko.html`
- Prototype/review artifacts such as `greenfield-flow.html` and
  `ply-stack-angle-demo.html` are still English-only unless promoted to product
  pages.

Deployment/verification:

- Restarted the public port `8000` `dd_laminate_app` uvicorn process so the new
  Korean routes are active.
- `node --check src/frontend/imperialax/app.js` and
  `node --check src/frontend/imperialax/login-v2.js` passed.
- `git diff --check` passed.
- `.venv/bin/python -m pytest tests/backend/test_imperialax_modules.py
  tests/backend/test_dd_laminate_ios_contract.py -q` passed:
  `19 passed, 1 warning`.
- Public checks confirmed:
  - `https://ai.imperialax.com/index.html` serves
    `ImperialAX Forecast Workspace` and no longer contains `ImperialAX App`.
  - `https://ai.imperialax.com/index.ko.html` serves `lang="ko"` and
    `ImperialAX 예측 워크스페이스`.
  - `https://ai.imperialax.com/login-v2.ko.html` serves the Korean login page.
- In-app browser checks confirmed:
  - Korean workspace renders 3 module cards.
  - Card-level `.route-text` count is `0`.
  - No `/api/v1/...` path is visible inside module cards.
  - Refresh button is no longer stuck disabled after module load.

Follow-up title adjustment:

- User preferred the ImperialAX workspace title on one line.
- Updated `src/frontend/imperialax/styles.css` and
  `src/frontend/imperialax/login-v2.css` so `h1` title spans render inline with
  `white-space: nowrap`.
- Replaced viewport-scaled title sizing with breakpoint-based fixed font sizes
  so `ImperialAX Forecast Workspace` and `ImperialAX 예측 워크스페이스` stay on one line
  without horizontal overflow.
- Bumped ImperialAX CSS cache keys to `20260619-workspace-title-line2`.

Verification:

- `git diff --check` passed.
- `node --check src/frontend/imperialax/app.js` and
  `node --check src/frontend/imperialax/login-v2.js` passed.
- Public CSS/HTML checks confirmed the new cache key and `white-space: nowrap`.
- In-app browser checks confirmed:
  - Desktop Korean workspace title has one text rect.
  - 390px mobile English title has one text rect and no horizontal overflow.
  - 390px mobile Korean title has one text rect and no horizontal overflow.

Follow-up hero copy adjustment:

- User clarified that the subtitle under the title must also stay on one line.
- Shortened English subtitle to
  `Choose a module to open its prediction screen.`
- Shortened Korean subtitle to `모듈을 선택해 예측 화면을 여세요.`
- Added `white-space: nowrap` to `.hero-copy`, reduced mobile hero-copy font
  size, and reduced `.workspace-hero` desktop height from `280px` to `240px`
  with tighter padding.
- Bumped ImperialAX workspace CSS cache key to `20260619-workspace-hero-line`.

Verification:

- `git diff --check` passed.
- `node --check src/frontend/imperialax/app.js` and
  `node --check src/frontend/imperialax/login-v2.js` passed.
- Public checks confirmed `index.html` and `index.ko.html` use the new subtitle
  copy and cache key.
- In-app browser checks confirmed:
  - Desktop Korean title and subtitle each have one text rect.
  - 390px mobile Korean title and subtitle each have one text rect, no overflow.
  - 390px mobile English title and subtitle each have one text rect, no overflow.

Follow-up full box alignment:

- User pointed out that only the hero had been adjusted while the other boxes
  still had mismatched heights/wrapping.
- Updated the entire ImperialAX workspace stack, not only the title:
  - summary/step boxes
  - account band
  - dark module intro band
  - module cards
  - card summary/capability text
- Shortened module intro copy:
  - EN: `Open prediction modules from one account.`
  - KO: `한 계정에서 예측 모듈을 엽니다.`
- Shortened card summaries for English and Korean so server-provided long copy
  cannot stretch the card layout.
- Added no-wrap and ellipsis behavior to summary rows, account text, intro
  text, module titles, module summaries, and capability chips.
- Added `min-width: 0` to flex/grid children so nowrap text cannot push cards or
  the page wider than the viewport.
- Reduced summary, intro, and module card vertical density; kept the mobile
  account band horizontal instead of stacking it vertically.
- Bumped ImperialAX workspace CSS/JS cache keys to
  `20260619-workspace-box-align2`.
- Updated `DESIGN.md` to record compact no-wrap workspace box rhythm.

Verification:

- `git diff --check` passed.
- `node --check src/frontend/imperialax/app.js` and
  `node --check src/frontend/imperialax/login-v2.js` passed.
- Public checks confirmed the new copy/cache keys are served from
  `https://ai.imperialax.com/index.html` and `index.ko.html`.
- In-app browser checks at 390px confirmed both English and Korean pages have:
  - `bodyScrollWidth == viewportWidth == 390`
  - title one-line/no overflow
  - hero copy one-line/no overflow
  - summary rows one-line/no overflow
  - account band text one-line/no overflow
  - intro band text one-line/no overflow
  - module card title/summary/capability text one-line/no overflow

Follow-up duplicate account card cleanup:

- User pointed out that the top-right `ImperialAX Demo · 2 modules` chip and the
  middle horizontal `ImperialAX Demo` account card were duplicate account surfaces.
- Removed the middle `account-band` section from both ImperialAX workspace pages:
  - `src/frontend/imperialax/index.html`
  - `src/frontend/imperialax/index.ko.html`
- Removed the now-unused `accountBand` render/click logic from
  `src/frontend/imperialax/app.js`.
- Removed the unused `.account-band` and `.account-avatar` CSS rules from
  `src/frontend/imperialax/styles.css`.
- Kept the top-right account chip as the single account access point; it still
  opens the account dialog.
- Bumped ImperialAX workspace CSS/JS cache keys to
  `20260619-workspace-no-account-band`.
- Checked native app parity:
  - iOS also had a toolbar account menu plus a middle `accountBand`; removed
    the middle account band from
    `ios/ImperialAXMVP/Sources/ImperialAXApp/ContentView.swift`.
  - Android already uses a top-right `A` quick-action icon for account details
    and does not add `accountBand()` to the visible home screen.

Verification:

- `git diff --check -- src/frontend/imperialax/index.html
  src/frontend/imperialax/index.ko.html src/frontend/imperialax/app.js
  src/frontend/imperialax/styles.css` passed.
- `node --check src/frontend/imperialax/app.js` and
  `node --check src/frontend/imperialax/login-v2.js` passed.
- Public checks confirmed `https://ai.imperialax.com/index.html` and
  `index.ko.html` serve the new cache key, and public `app.js` contains only
  `accountButton/accountLabel` with no `accountBand`.
- In-app browser check on `https://ai.imperialax.com/index.ko.html` confirmed:
  - `.account-band` count is `0`
  - `.account-chip` count is `1`
  - visible account text is only in the top-right chip
  - workspace order is `hero -> summary -> intro -> module grid`
  - no horizontal overflow
- iOS `swift test` in `ios/ImperialAXMVP` passed: 4 tests.
- Backend pytest was not rerun successfully in the current terminal Python
  because the active Python is 3.10 and lacks `fastapi`; the project declares
  Python `>=3.11`, so this is an environment gap rather than a frontend syntax
  failure.

Follow-up ImperialAX login polish:

- User pointed out that forcing one-line copy on `ai.imperialax.com` broke the
  left login panel: the title overflowed outside the box and the visual layout
  felt careless.
- Changed the ImperialAX login title strategy from forced nowrap to deliberate
  wrapping:
  - desktop shows `ImperialAX` and `Forecast Workspace` on two clean lines
  - mobile keeps the sign-in card first and prevents horizontal overflow
  - very small screens scale the title down instead of spilling outside the card
- Reworked the left login panel so it no longer looks empty or unbalanced:
  - matched the left copy panel height to the right sign-in panel on desktop
  - added a compact module preview strip for Laminate, Injection, and
    Optimization
  - added stable clipping/ellipsis behavior inside the module preview rows
- Fixed the module logo alignment issue on the right-side account/module cards:
  - `.module-row span` no longer overrides `.module-icon`
  - module icon containers explicitly use grid centering
  - inline SVGs are block-level so they center visually instead of drifting
    toward the top-left
- Applied the same polish to English and Korean ImperialAX login/workspace entry
  pages.
- Bumped public cache keys:
  - `styles.css?v=20260619-login-polish3` for the main ImperialAX entry pages
  - `login-v2.css?v=20260619-login-polish2` for the account/login v2 pages
- Updated `DESIGN.md` to clarify that long headings should wrap deliberately,
  while no-wrap is reserved for short labels and chips.

Verification:

- `git diff --check` passed for the changed ImperialAX HTML/CSS and `DESIGN.md`.
- `node --check src/frontend/imperialax/app.js` and
  `node --check src/frontend/imperialax/login-v2.js` passed.
- Public checks confirmed `https://ai.imperialax.com/index.html`,
  `index.ko.html`, `login-v2.html`, and the updated CSS cache keys are served.
- In-app browser checks confirmed:
  - desktop `index.html` has no horizontal overflow
  - left and right login panels align at the same height
  - the left title stays inside its card
  - mobile Korean login has no horizontal overflow
  - login-v2 module SVGs are centered within their logo boxes

Follow-up ImperialAX mobile web adaptation:

- User pointed out that the mobile web still felt like the desktop web version
  simply stacked vertically.
- Reworked `ai.imperialax.com` mobile breakpoints in `src/frontend/imperialax/styles.css`
  so the main ImperialAX entry/workspace page behaves like a phone-first surface:
  - mobile login now uses a compact brand/header panel, a 3-column module preview
    strip, and a tighter sign-in card instead of a tall stacked desktop pair
  - mobile workspace uses a compact hero, account/sign-out controls in one row,
    3 short workflow chips, a shorter module intro band, and vertical module
    list cards
  - module cards hide the full capability grid on mobile because the page's job
    is module selection; detailed capabilities remain available through the
    account/access surfaces
  - adjusted mobile title sizing upward from the previous cramped 25px fallback
    and removed mobile-only forced nowrap where wrapping is safer
- Bumped public ImperialAX CSS cache keys to
  `styles.css?v=20260619-mobile-adaptive2` in both English and Korean entry
  pages.
- Updated `DESIGN.md` responsive guidance to state that mobile web must not be a
  stacked desktop canvas, and should use compact phone-first headers, workflow
  chips, and vertical module list cards.

Verification:

- `git diff --check` passed for the changed ImperialAX HTML/CSS and `DESIGN.md`.
- `node --check src/frontend/imperialax/app.js` passed.
- Public checks confirmed `https://ai.imperialax.com/index.html` serves
  `20260619-mobile-adaptive2` and the updated CSS is available.
- In-app browser checks at 390px width confirmed:
  - English mobile login has no horizontal overflow; login copy height is about
    271px instead of the previous 557px
  - English mobile workspace has no horizontal overflow; module cards are about
    207px tall instead of the previous 297px
  - Korean mobile workspace has no horizontal overflow; hero, summary chips,
    intro band, and module cards all fit within the 390px viewport
  - Korean mobile login has no horizontal overflow and keeps the module preview
    as a 3-column mobile strip
- Browser viewport override was reset after verification.

## 2026-06-19 - Injection v2 web app from flow prototype

User asked to turn the Injection flow prototype into an actual v2 web UI while
keeping the existing Injection version available.

What changed:

- Added a standalone English Injection v2 app:
  `src/frontend/simple-injection/index-v2.html`
- Added a standalone Korean Injection v2 app:
  `src/frontend/simple-injection/index-v2.ko.html`
- Added dedicated v2 styling:
  `src/frontend/simple-injection/styles-v2.css`
- Added dedicated v2 API/UI logic:
  `src/frontend/simple-injection/app-v2.js`
- Updated the flow prototype:
  `src/frontend/simple-injection/injection-v2-flow.html`
  - added an `Open v2` link to the actual v2 app
- Left the existing classic Injection files untouched:
  `src/frontend/simple-injection/index.html`,
  `src/frontend/simple-injection/index.ko.html`,
  `src/frontend/simple-injection/styles.css`, and
  `src/frontend/simple-injection/app.js`
- Updated `DESIGN.md` to record Injection v2 as a real web app surface, not only
  a flow prototype.

Injection v2 behavior:

- Loads actual Simple Injection models from
  `/api/v1/simple-injection/models`.
- Loads actual DOE geometry/process options from
  `/api/v1/simple-injection/doe`.
- Defaults to `G18 / P07` when available.
- Uses simplified public model labels:
  - `Injection - Machine Learning`
  - `Injection - Deep Learning`
  - `Injection - Operator Learning`
  - corresponding Filling labels
- Keeps editable DOE-derived geometry/process fields in the v2 form.
- Renders a live SVG shape preview from selected geometry dimensions, gate size,
  and hole diameter.
- Runs the actual prediction endpoint:
  `/api/v1/simple-injection/predict/sprue-pressure`.
- Renders:
  - max sprue pressure
  - max time
  - curve point count
  - sprue pressure canvas
  - filling pressure histogram rows
  - prediction notes
- Includes a Moldex3D CSV comparison panel wired to
  `/api/v1/simple-injection/compare/moldex3d` after a prediction exists.

Public URLs:

- `https://injection.imperialax.com/index-v2.html`
- `https://injection.imperialax.com/index-v2.ko.html`
- Current cache key: `20260619-injection-v2-5`

Verification:

- `git diff --check` passed for Injection v2 HTML/CSS/JS and `DESIGN.md`.
- `node --check src/frontend/simple-injection/app-v2.js` passed.
- Public curl checks confirmed:
  - English v2 page serves the new cache key and v2 markup
  - Korean v2 page serves the new cache key and v2 markup
  - v2 CSS and JS are publicly available
  - the flow prototype now links to `index-v2.html`
- Direct public API prediction check for `G18 / P07` returned:
  - status 200
  - max pressure about 87.7 MPa
  - 128 sprue curve points
  - 10 filling pressure bins
- In-app browser checks confirmed:
  - API status reaches `API ready`
  - model and DOE selects populate
  - live shape SVG renders
  - desktop 1280x900 has no horizontal overflow and the primary prediction
    button fits inside the viewport after layout compaction
  - mobile 390x844 has no horizontal overflow, shape preview renders, and the
    primary prediction button is visible in the first viewport
  - clicking prediction renders result state with 87.7 MPa max pressure, 128
    curve points, 10 filling rows, `G18_P07` comparison sample, and no visible
    error
- Browser viewport override was reset after verification and the in-app browser
  was left on the Injection v2 page.

Follow-up Laminate mobile ply preview:

- User liked the one-page mobile layout, but asked to show the ply stack image
  again on `laminate.imperialax.com` mobile because visuals help users understand
  the theta changes.
- Added compact mobile-only live ply previews inside both active forecast forms:
  - Response Forecast form
  - u3 Forecast form
- Placement: between the model selector and theta controls, so changing theta
  immediately affects the visible ply stack before the user runs prediction.
- Kept the large desktop/right-side `Live laminate preview` panel hidden on the
  mobile first screen; only the compact visual strip is shown there.
- Updated `app-v2.js` so all stack preview targets render from the same active
  Case/theta state. SVG defs now use per-preview IDs to avoid duplicated
  gradient/pattern collisions.
- Added short-height mobile handling: standard mobile gets a 78px preview strip;
  small 375x667-style screens get a 58px strip so the prediction button still
  fits in one viewport.
- Bumped DD Laminate v2 public cache keys:
  - `styles-v2.css?v=20260619-mobile-ply2`
  - `app-v2.js?v=20260619-mobile-ply2`
- Updated `DESIGN.md` responsive guidance: DD Laminate v2 mobile should keep a
  compact angle-aware ply stack visual between model selection and theta
  controls while deferring larger preview/result-heavy surfaces.

Verification:

- `git diff --check` passed for DD Laminate v2 HTML/CSS/JS and `DESIGN.md`.
- `node --check src/frontend/dd-laminate/app-v2.js` passed.
- Public curl checks confirmed `https://laminate.imperialax.com/` serves the new
  cache keys, mobile preview markup, CSS, and multi-preview JS.
- In-app browser checks confirmed:
  - 390x844 Response tab: compact preview is visible, contains SVG, sits between
    model and theta controls, has no horizontal/vertical overflow, and the
    forecast button remains visible around y=663
  - theta input change from 30 to 45 updates the readout and the SVG hatch angle
  - 375x667 Response tab: compact 58px preview is visible, no
    horizontal/vertical overflow, and forecast button remains visible around
    y=643
  - 390x844 u3 tab: compact preview is visible with SVG and no
    horizontal/vertical overflow

## 2026-06-19 - Injection v2 greenfield flow prototype

User asked to start revising the Injection UI in the same spirit as Laminate v2,
while keeping the existing Injection version available. The immediate request
was to create at least five flow screens for team discussion, not to replace the
live Injection app yet.

What changed:

- Added a standalone Injection v2 flow prototype:
  `src/frontend/simple-injection/injection-v2-flow.html`
- Added its dedicated styling:
  `src/frontend/simple-injection/injection-v2-flow.css`
- Left the existing Injection pages untouched:
  `src/frontend/simple-injection/index.html` and
  `src/frontend/simple-injection/index.ko.html`
- Updated `DESIGN.md` to record the Injection v2 flow prototype as a product
  surface and capture responsive guidance.

Prototype flow screens:

1. Workspace
2. DOE Setup
3. Process & Model
4. 3D / Flow Preview
5. Prediction Result
6. Validation & Report

Verification:

- `git diff --check` passed for the new Injection v2 HTML/CSS before the memory
  update.
- Public curl check confirmed
  `https://injection.imperialax.com/injection-v2-flow.html` serves the new file
  and references `injection-v2-flow.css`.
- In-app browser checks confirmed:
  - 6 flow screens render
  - desktop 1280x900 uses a 3-column screen grid with no horizontal overflow
  - current in-app viewport around 943px uses a 2-column screen grid with no
    horizontal overflow
  - mobile 390x844 stacks to a single column with no page-level horizontal
    overflow
- Browser viewport override was reset after verification and the prototype was
  reopened in the in-app browser.

Current status:

- This is a static discussion prototype only.
- It is not yet connected to the Injection prediction API.
- Next sensible step is to pick the preferred flow direction, then turn it into
  a real v2 Injection route/page while keeping the current version available.

Follow-up Laminate one-screen mobile input:

- User asked for `laminate.imperialax.com` to fit on mobile without scrolling,
  similar to the `ai.imperialax.com` mobile adaptation.
- Confirmed that `laminate.imperialax.com` serves DD Laminate v2 from
  `src/frontend/dd-laminate/index-v2.html`.
- Measured the previous 390x844 mobile layout:
  - topbar: about 240px
  - workflow summary: about 300px
  - mode switch: about 142px
  - active Response form started around y=765
  - primary forecast button bottom was around y=1496, far below the viewport
  - total page scroll height was about 2550px
- Updated DD Laminate v2 mobile CSS so the initial input state fits in one
  phone viewport:
  - compact topbar and hidden mobile hero copy
  - one-line title treatment on mobile
  - 3 short workflow chips instead of stacked summary cards
  - 3-column compact mode switch instead of stacked mode buttons
  - compact form spacing, input heights, angle controls, and primary button
  - hidden mobile case formula guide to preserve the one-screen input flow
  - hidden live laminate preview on mobile first screen
  - hidden empty result panel until a prediction result exists
- Added a small `body.has-result` state in `app-v2.js` when predictions render,
  and removed it during prediction reset, so result panels can still appear
  after a run while the initial mobile input remains compact.
- Bumped public cache keys for DD Laminate v2:
  - `styles-v2.css?v=20260619-one-screen1`
  - `app-v2.js?v=20260619-one-screen1`
- Updated `DESIGN.md` responsive guidance to record that DD Laminate v2 mobile
  should keep the active forecast form and primary action inside one viewport.

Verification:

- `git diff --check` passed for DD Laminate v2 HTML/CSS/JS.
- `node --check src/frontend/dd-laminate/app-v2.js` passed.
- Public checks confirmed `https://laminate.imperialax.com/` serves the new CSS/JS
  cache keys.
- In-app browser checks confirmed:
  - English 390x844 Response tab: no horizontal or vertical scroll; forecast
    button visible at bottom around 584px
  - English 390x844 u3 tab: no vertical scroll; `Predict u3 Pt` visible around
    584px
  - Korean 390x844 Response tab: no horizontal or vertical scroll; forecast
    button visible around 584px
  - English 375x667 small mobile check: no horizontal or vertical scroll; button
    still visible inside the viewport
- Browser viewport override was reset after verification.

Follow-up Laminate mobile maximum ply preview:

- User said the earlier one-page mobile fit was good, but the live ply drawing
  should be as large as possible. User also asked to remove the mobile
  `01/02/03` workflow summary and the `Forecast Setup` / `예측 설정` card above
  the model section, and emphasized that changes in one language must apply to
  the other language as well.
- Updated DD Laminate v2 mobile CSS:
  - `.summary-strip` is hidden on mobile.
  - `.form-header` is hidden on mobile.
  - mobile live stack preview height is increased to 192px on normal phones.
  - short-height phones use a 168px preview.
  - the preview SVG transform was adjusted so the enlarged drawing stays framed
    between model selection and theta controls.
- Applied the same public cache key to English and Korean v2 pages:
  - `styles-v2.css?v=20260619-mobile-ply3`
  - `app-v2.js?v=20260619-mobile-ply3`
- Updated `DESIGN.md` responsive guidance so Laminate v2 mobile prioritizes a
  large angle-aware stack visual by suppressing secondary workflow/setup headers.

Verification:

- `git diff --check` passed for DD Laminate v2 HTML/CSS and `DESIGN.md` before
  this memory update.
- `node --check src/frontend/dd-laminate/app-v2.js` passed.
- Public checks confirmed both English and Korean Laminate v2 pages serve
  `20260619-mobile-ply3`.
- In-app browser checks confirmed:
  - English 390x844 Response and u3 tabs: workflow summary and form header are
    hidden, preview is visible at 192px, preview sits between model and theta
    controls, no horizontal or vertical overflow, and the primary button remains
    visible around y=657.
  - English 375x667 Response tab: preview is visible at 168px, no overflow, and
    the primary button remains visible around y=633.
  - Korean 375x667 Response and u3 tabs: same hidden headers, 168px preview, no
    overflow, and primary button visible around y=633.
- Browser viewport override was reset after verification and the browser was
  left on `https://laminate.imperialax.com/?v=mobile-ply3`.

Follow-up Laminate adaptive mobile ply preview:

- User asked whether the mobile ply image could adapt so tall/large phones
  such as Galaxy Fold, Flip, Ultra, and iPhone Pro Max can show the full stack
  better.
- Updated DD Laminate v2 mobile CSS:
  - `.mobile-stack-preview` now uses a responsive `clamp()` height driven by
    both viewport width and remaining viewport height.
  - The target visual ratio follows the generated SVG viewBox ratio
    `1160:760`, so large phones can show the full ply stack instead of using
    the old fixed crop.
  - The SVG now fills the preview viewport with `height: 100%` and no transform
    crop.
  - Short phones still clamp down so the prediction button stays in the first
    viewport.
- Updated English and Korean cache keys to:
  - `styles-v2.css?v=20260619-mobile-ply5`
  - `app-v2.js?v=20260619-mobile-ply5`
- Updated `DESIGN.md` responsive guidance to record that the Laminate mobile ply
  visual should adapt to tall/large phones while preserving first-viewport
  reachability on short phones.

Verification:

- `git diff --check` passed for DD Laminate v2 HTML/CSS and `DESIGN.md`.
- `node --check src/frontend/dd-laminate/app-v2.js` passed.
- Public checks confirmed both English and Korean Laminate pages serve
  `20260619-mobile-ply5`, and public CSS contains the `100svh - 490px`
  responsive height calculation.
- In-app browser checks confirmed:
  - 375x667 English Response: preview height 177px, no horizontal/vertical
    overflow, button visible around y=642.
  - 390x844 English Response: preview height 228px, no overflow, button visible
    around y=693.
  - 430x932 English Response: preview height 254px, no overflow, button visible
    around y=719.
  - 673x841 English Response: preview height 351px, no overflow, button visible
    around y=816.
  - 430x932 English and Korean u3 tabs: preview height 254px, no overflow, and
    button visible around y=719.
- Browser viewport override was reset after verification and the browser was
  left on `https://laminate.imperialax.com/?v=mobile-ply5`.

ImperialAX real account signup/login foundation:

- User asked to move from visual-only web/app login pages to real login with a
  database and signup page.
- Added a SQLite-backed ImperialAX auth store at
  `src/backend/services/imperialax_auth_store.py`.
  - Default DB path: `data/imperialax_auth.sqlite3`.
  - Override path for tests/deployment: `IMPERIALAX_AUTH_DB_PATH`.
  - Stores users, PBKDF2 password hashes, session tokens, module entitlements,
    and access requests.
  - Seeds legacy demo accounts/tokens so existing demo clients keep working.
- Updated `src/backend/api/v1/modules.py`:
  - Added `POST /api/v1/modules/auth/signup`.
  - Added `POST /api/v1/modules/auth/login`.
  - Kept `POST /api/v1/modules/auth/demo-login` for demo compatibility.
  - `GET /api/v1/modules/me` now resolves real bearer session tokens through
    the auth DB.
  - module access requests are now recorded in the auth DB.
- Updated ImperialAX web login/workspace pages:
  - English and Korean workspace login cards now support switching between
    sign-in and account creation.
  - `login-v2` English/Korean entry pages also support account creation.
  - Real accounts call `/auth/signup` and `/auth/login`; demo button still uses
    the demo endpoint/fallback.
- Updated ImperialAX iOS app:
  - Added signup payload/client call.
  - Login now calls the real `/auth/login` route.
  - Login screen can switch to create-account mode with name/company fields.
- Updated ImperialAX Android app:
  - Added `/auth/login`, `/auth/signup`, and demo-login URL handling.
  - Login card can switch to create-account mode with name/company fields.
  - Stored session format remains unchanged.

Verification:

- `.venv/bin/pytest tests/backend/test_imperialax_modules.py -q` passed:
  12 tests.
- `.venv/bin/ruff check` passed for the changed auth backend/test files.
- `node --check src/frontend/imperialax/app.js` passed.
- `node --check src/frontend/imperialax/login-v2.js` passed.
- `cd ios/ImperialAXMVP && swift test` passed: 4 tests.
- FastAPI smoke check confirmed signup, login, and bearer `/modules/me` using
  a temporary SQLite auth DB.
- Android Gradle build could not run on this machine because no Java Runtime /
  JDK 17 is installed; Gradle stopped before compiling project code.

ImperialAX auth field visibility tweak:

- User clarified that name/company should not appear during login; they are
  only needed for signup.
- Confirmed iOS/Android already gate name/company fields behind signup mode.
- Bumped ImperialAX web cache keys so browsers load the CSS/JS where signup fields
  are hidden in login mode:
  - `styles.css?v=20260619-auth-fields1`
  - `app.js?v=20260619-auth-fields1`
  - `login-v2.css?v=20260619-auth-fields1`
  - `login-v2.js?v=20260619-auth-fields1`

Verification:

- `node --check src/frontend/imperialax/app.js` passed.
- `node --check src/frontend/imperialax/login-v2.js` passed.
- `git diff --check` passed for the touched ImperialAX web auth files.

ImperialAX login Korean entry:

- User noted the login page did not expose Korean.
- Added visible language switches:
  - English login pages show `한국어`.
  - Korean login pages show `English`.
- Applied this to both the `login-v2` entry pages and the workspace login pages.
- Bumped ImperialAX web cache keys to `20260619-login-lang1`.

Verification:

- `node --check src/frontend/imperialax/app.js` passed.
- `node --check src/frontend/imperialax/login-v2.js` passed.
- `git diff --check` passed for the touched ImperialAX web language files.

ImperialAX login button sizing:

- User asked to make `Continue demo` smaller and ensure `Sign in` is fully
  visible.
- Updated ImperialAX web login pages:
  - `Sign in` / `로그인` now occupies the full primary row.
  - demo action is shortened to `Demo` / `데모` and styled as a smaller
    secondary button.
  - Applied to both `login-v2` and workspace login pages in English/Korean.
- Bumped ImperialAX web cache keys to `20260619-login-buttons1`.

Verification:

- `node --check src/frontend/imperialax/app.js` passed.
- `node --check src/frontend/imperialax/login-v2.js` passed.
- `git diff --check` passed for the touched ImperialAX login button files.

## 2026-06-19 - Injection v2 parametric preview and setup polish

User said Injection v2 still looked too close to v1, asked to switch Live
Preview back toward the previous Parametric mode, and asked for substantial
Forecast setup cleanup because text was overlapping.

What changed:

- Updated Injection v2 English and Korean pages:
  - `src/frontend/simple-injection/index-v2.html`
  - `src/frontend/simple-injection/index-v2.ko.html`
- Updated Injection v2 styling:
  `src/frontend/simple-injection/styles-v2.css`
- Updated Injection v2 UI logic:
  `src/frontend/simple-injection/app-v2.js`
- Replaced the static v2 SVG-only preview path with a Three.js-backed
  Parametric mold preview:
  - dynamically imports `vendor/three.module.r160.js`
  - renders the DOE plate, center hole, edge gate, and flow tubes from the
    selected geometry/process payload
  - supports drag rotation, zoom in/out, reset controls, and SVG fallback
- Reworked Forecast setup:
  - grouped model, DOE, prevention check, and process controls into compact
    setup blocks
  - shortened model labels to keep model selects readable
  - made process controls a compact two-column card layout with inline numeric
    inputs and bars
  - hid extra setup copy that was causing density/overlap issues
  - hid the secondary workflow summary on mobile so the prediction button stays
    in the first viewport
- Applied the same changes to English and Korean pages.
- Updated `DESIGN.md` so Injection v2 now explicitly uses compact setup blocks,
  a Three.js parametric mold preview, and mobile behavior that prioritizes the
  primary prediction action.
- Current public cache key:
  `20260619-injection-v2-12`

Verification:

- `node --check src/frontend/simple-injection/app-v2.js` passed.
- `git diff --check` passed for Injection v2 HTML/CSS/JS and `DESIGN.md`.
- Public checks confirmed English and Korean Injection v2 pages serve
  `20260619-injection-v2-12`, and public JS contains the Three.js dynamic
  import plus `renderParametricShape`.
- In-app browser check confirmed:
  - API status reaches `API ready`
  - selected model reads `Machine Learning (Recommended)`
  - Parametric preview renders as a canvas, not the SVG fallback
- Chrome/Playwright viewport checks confirmed:
  - desktop 1280x900: no horizontal overflow, meaningful UI overflow list is
    empty, Parametric canvas renders, and Predict button bottom is y=884
  - mobile English 390x844: no horizontal overflow, meaningful UI overflow list
    is empty, Parametric canvas renders, and Predict button bottom is y=795
  - mobile Korean 390x844: no horizontal overflow, meaningful UI overflow list
    is empty, Parametric canvas renders, and Predict button bottom is y=795
  - native select controls may report scrollWidth overflow in English because
    browser measurement includes all option strings, but the selected displayed
    value is the shortened model label
- Three.js visual checks:
  - desktop canvas screenshot: non-transparent ratio 1.0, luminance variance
    924.19 before drag, average pixel delta 14.05 after drag
  - mobile canvas screenshot: non-transparent ratio 1.0, luminance variance
    1132.84 before drag, average pixel delta 17.28 after drag
  - screenshots saved to:
    `/var/folders/7p/c3j_sb0j539805ngspmnb34r0000gn/T/injection-v2-desktop-viewer.png`
    and
    `/var/folders/7p/c3j_sb0j539805ngspmnb34r0000gn/T/injection-v2-mobile-viewer.png`

## 2026-06-19 - ImperialAX Native Workspace Parity With Web

User noted that the native app view for `ai.imperialax.com/index.html` did not
match the web page closely enough, and asked to use the web page as the source
of truth.

What changed:

- Updated the unified iOS ImperialAX app entry screen:
  - login hero now follows the web `ImperialAX AI Workspace` /
    `ImperialAX Forecast Workspace` hierarchy
  - login form title now matches the web `Sign in` state
  - removed the extra top toolbar account menu so account, refresh, and sign
    out live inside the page like the web version
  - workspace home now uses the same hero, account chip, summary strip,
    dark `Prediction modules` intro band, and module-card hierarchy
  - remote module catalog responses are normalized to the same short web copy
    for Laminate, Injection, and Optimization
- Updated the unified Android ImperialAX app entry screen:
  - replaced the older `CAE-AI` / `UNIFIED CAE-AI WORKSPACE` shell with the
    web-style `ImperialAX AI Workspace` / `ImperialAX Forecast Workspace` login and home
    cards
  - added the web-style Laminate / Injection / Optimization preview strip
  - changed the home summary strip to `Account`, `Choose module`, `Forecast`
  - restyled the dark `Prediction modules` intro band with an internal refresh
    action
  - removed the visible API prefix from module cards
  - gave module cards web-matched short summaries, accent colors, badges, and
    `L` / `I` / `O` icons
  - normalized remote module catalog responses so connected Android builds keep
    the same web copy
- Updated `DESIGN.md` to record that the ImperialAX native unified app entry must
  mirror `ai.imperialax.com/index.html` for login, account status, workspace
  summary, and module card hierarchy.

Verification:

- `cd ios/ImperialAXMVP && swift test` passed: 4 tests.
- `cd android/ImperialAXMVP && JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home gradle :app:assembleDebug` passed.
- `git diff --check` passed for the changed iOS, Android, and design files.
- Old workspace/app copy search found no remaining `CAE-AI WORKSPACE`,
  `UNIFIED CAE-AI`, `ImperialAX App`, `ImperialAX MVP workspace`, `ImperialAX server`, or
  long v1 module summaries in the touched native workspace files.

## 2026-06-19 - Injection v2 Predicted Flow Preview Restored

User noticed that Injection v2's Parametric Preview no longer reflected the
prediction result after running prediction, and asked to restore it even if the
preview gets heavier. After seeing the first pass, user correctly pointed out
that the visual looked too much like an actual injection-flow path.

What changed:

- Restored prediction-aware preview rendering in
  `src/frontend/simple-injection/app-v2.js`.
- The Parametric Preview now changes after `Predict Sprue & Filling`:
  - predicted filling pressure bins drive heat cells across the plate
  - predicted sprue peak and filling distribution drive a gate-based
    fill-front/pressure map
  - preview title/copy and active run chip update to the predicted result
- Removed the over-literal long animated stream tubes from the predicted result
  overlay; the preview now uses short gate-entry guides, progressive fill-front
  bands, and a pressure heat map instead.
- The SVG fallback also gets an animated predicted pressure-map overlay, so the
  result signal remains visible if Three.js cannot load.
- Input changes clear the previous prediction map by default so stale result
  overlays do not remain attached to new DOE values.
- English and Korean Injection v2 pages now load cache key
  `20260619-injection-v2-14`.
- Updated `DESIGN.md` so Injection v2's Three.js parametric preview explicitly
  includes the predicted filling-pressure/fill-front map and user-triggered
  result motion.

Verification:

- `node --check src/frontend/simple-injection/app-v2.js` passed.
- `git diff --check` passed for Injection v2 JS/HTML files before the memory
  update.
- Public HTML now serves `20260619-injection-v2-14` for CSS/JS.
- Public JS now contains `Predicted filling pressure preview`,
  `gate-based fill-front map`, `fillFrontSegments`, and
  `addPredictionFrontBand`.
- Direct public prediction API smoke check for `G18 / P07` returned:
  - max sprue pressure `87.7 MPa`
  - filling max `26.27 MPa`
  - 10 filling-pressure bins
- In-app browser click verification was blocked by a stale tab-handle issue, so
  this correction was verified through public HTML/JS fetches, syntax checks,
  patch checks, and the public prediction API response.

## 2026-06-19 - Injection v2 Parametric Preview 360 Rotation

User asked for Injection v2's Parametric Preview to rotate 360 degrees like v1.

What changed:

- Removed the v2 vertical rotation clamp in
  `src/frontend/simple-injection/app-v2.js`.
- Dragging the preview now updates:
  - horizontal movement -> `group.rotation.z`
  - vertical movement -> unrestricted `group.rotation.x`
- Added `pointercancel` handling so interrupted touch gestures do not leave the
  preview stuck in dragging state.
- Added `cursor: grab`, `cursor: grabbing`, `touch-action: none`, and
  `user-select: none` to the v2 viewer plate so desktop and mobile drag behavior
  feels like a direct 3D manipulation surface.
- English and Korean Injection v2 pages now load cache key
  `20260619-injection-v2-15`.
- Updated `DESIGN.md` to record that Injection v2 Parametric Preview should
  match v1's free 360-degree drag rotation.

Verification:

- `node --check src/frontend/simple-injection/app-v2.js` passed.
- `git diff --check` passed for Injection v2 JS/CSS/HTML files.
- Public English and Korean Injection v2 HTML both serve
  `20260619-injection-v2-15`.
- Public v15 JS contains unrestricted `rotation.x += dy * 0.006` and
  `pointercancel`.
- Public v15 CSS contains `touch-action: none`, `cursor: grab`, and
  `cursor: grabbing`.

## 2026-06-19 - Injection v2 Sprue Chart and Small-Window Result Review

User asked for the Injection v2 Sprue Pressure graph to look more like v1 and
noted that, on small windows, the Setup panel kept following the scroll and made
the result hard to review.

What changed:

- Updated `src/frontend/simple-injection/app-v2.js` Sprue Pressure canvas
  rendering to match the v1 chart style more closely:
  - pale chart background
  - left/bottom axes
  - horizontal grid lines
  - y-axis tick labels
  - x-axis tick labels
  - `Time (s)` and `Sprue pressure (MPa)` axis labels
  - v1-style blue/cyan/green gradient curve
  - removed the extra v2 peak marker from the graph itself
- Updated English and Korean v2 chart canvases from `760x320` to v1-like
  `760x360`.
- Disabled sticky Setup behavior for:
  - viewport widths at or below `1180px`
  - viewport heights at or below `760px`
  so result review is not obstructed by the input panel on smaller windows.
- English and Korean Injection v2 pages now load cache key
  `20260619-injection-v2-16`.
- Updated `DESIGN.md` to record the v1-like Sprue chart style and small-window
  non-sticky Setup rule.

Verification:

- `node --check src/frontend/simple-injection/app-v2.js` passed.
- `git diff --check` passed for Injection v2 JS/CSS/HTML files.
- Public English and Korean Injection v2 HTML both serve
  `20260619-injection-v2-16` and `pressure-canvas` size `760x360`.
- Public v16 JS contains `timeAxis`, `pressureAxis`, `createLinearGradient`,
  and v1-style gradient color stops.
- Public v16 CSS contains the sticky default plus `position: static` overrides
  for `max-width: 1180px`, `max-height: 760px`, and mobile widths.

## 2026-06-19 - Injection v2 DOE User Input State

User asked for Injection v2 to match v1 behavior where manually editing Geometry
or Process values changes the DOE selector to a User Input state.

What changed:

- Added v1-style `manual` DOE options to Injection v2:
  - `User input (geometry)` / `사용자 입력 (형상)`
  - `User input (process)` / `사용자 입력 (공정)`
- Geometry fields now switch Geometry DOE to User Input when edited:
  - `L_mm`, `W_mm`, `t_mm`, `D_mm`, `R_mm`, `gate_type`,
    `gate_size_width_mm`, `gate_size_height_mm`
- Process fields now switch Process DOE to User Input when edited:
  - `melt_temp_C`, `mold_temp_C`, `injection_time_s`,
    `packing_pressure_MPa`, `packing_time_s`
- Preset DOE application is guarded by `applyingDoeValues`, so choosing a preset
  does not immediately mark it as User Input.
- If prediction inputs include `manual`, the Moldex3D comparison sample id is
  no longer auto-filled as a preset pair.
- English and Korean Injection v2 pages now load cache key
  `20260619-injection-v2-17`.
- Updated `DESIGN.md` to record that v2 should match v1's DOE User Input
  behavior.

Verification:

- `node --check src/frontend/simple-injection/app-v2.js` passed.
- `git diff --check` passed for Injection v2 JS/HTML files.
- Public English and Korean Injection v2 HTML both serve
  `20260619-injection-v2-17`.
- Public v17 JS contains `User input (geometry)`, `사용자 입력 (형상)`,
  `CUSTOM_GEOMETRY_ID`, `markCustomGeometry`, and manual comparison sample
  handling.

## 2026-06-19 - ImperialAX Separate Account Creation Page

User asked to move `Create account` out of the login form into a separate page
and collect `Name`, `Company`, `Location`, `Mobile`, `Email`, and `Password`.

What changed:

- Added standalone English/Korean signup pages:
  - `src/frontend/imperialax/signup-v2.html`
  - `src/frontend/imperialax/signup-v2.ko.html`
  - `src/frontend/imperialax/signup-v2.js`
- Updated ImperialAX login/workspace login screens so `Create account` navigates
  to the new signup page instead of toggling inline fields.
- Kept login focused on only email/password plus demo access.
- Extended the ImperialAX auth store and API user DTO to persist and return
  `location` and `mobile` alongside name/company/email.
- Added SQLite migration logic so existing `users` tables get `location` and
  `mobile` columns automatically.
- Added public DD Laminate standalone routes for `/signup-v2.html`,
  `/signup-v2.ko.html`, and `/signup-v2.js` so `ai.imperialax.com` can serve the
  signup flow even when routed through the standalone app.
- Added tests for signup page serving and signup API persistence of location
  and mobile.

Verification:

- `node --check src/frontend/imperialax/app.js`
- `node --check src/frontend/imperialax/login-v2.js`
- `node --check src/frontend/imperialax/signup-v2.js`
- `.venv/bin/ruff check src/backend/api/v1/modules.py src/backend/services/imperialax_auth_store.py src/backend/dd_laminate_app.py tests/backend/test_imperialax_modules.py tests/backend/test_dd_laminate_ios_contract.py`
- `.venv/bin/pytest tests/backend/test_imperialax_modules.py tests/backend/test_dd_laminate_ios_contract.py -q`
  passed: 24 tests, with the existing `asyncio_mode` pytest config warning.
- `git diff --check` passed for the touched signup/login/auth files.

## 2026-06-19 - ImperialAX Email ID Hint And Forgot Password Flow

User asked to make it clear that email is used as the sign-in ID, and to add a
Forgot password flow authenticated by name and email.

What changed:

- Added sign-in ID helper text on ImperialAX login and signup screens:
  - English: `This email is used as your sign-in ID.`
  - Korean: `이 이메일이 로그인 ID로 사용됩니다.`
- Added Forgot password links on the English/Korean login pages and workspace
  login cards.
- Added standalone English/Korean password reset pages:
  - `src/frontend/imperialax/forgot-v2.html`
  - `src/frontend/imperialax/forgot-v2.ko.html`
  - `src/frontend/imperialax/forgot-v2.js`
- Added `POST /api/v1/modules/auth/forgot-password`.
- Implemented reset behavior in `imperialax_auth_store`:
  - verifies account by normalized email plus case-insensitive normalized name
  - requires the new password to be at least 8 characters
  - updates password hash/salt
  - invalidates existing sessions for that user
  - returns a fresh login session
- Added DD Laminate standalone static routes for `forgot-v2` pages/scripts so
  `ai.imperialax.com` can serve the flow through either ImperialAX or standalone app
  routing.
- Added backend tests for successful reset, old-password rejection, wrong-name
  rejection, and public static route coverage.

Verification:

- `node --check src/frontend/imperialax/app.js`
- `node --check src/frontend/imperialax/login-v2.js`
- `node --check src/frontend/imperialax/signup-v2.js`
- `node --check src/frontend/imperialax/forgot-v2.js`
- `.venv/bin/ruff check src/backend/api/v1/modules.py src/backend/services/imperialax_auth_store.py src/backend/dd_laminate_app.py tests/backend/test_imperialax_modules.py tests/backend/test_dd_laminate_ios_contract.py`
- `.venv/bin/pytest tests/backend/test_imperialax_modules.py tests/backend/test_dd_laminate_ios_contract.py -q`
  passed: 26 tests, with the existing `asyncio_mode` pytest config warning.

## 2026-06-19 - Public Account Links On ai.imperialax.com

User could not open the previously mentioned local signup URL and asked to use
`ai.imperialax.com/signup-v2.html` style URLs instead.

What changed:

- Restarted the public DD Laminate/ImperialAX server on port `8000`, which is the
  Cloudflare tunnel target for `ai.imperialax.com`.
- Confirmed the earlier 404 was from the stale server process, not from the
  route definitions.
- Updated ImperialAX account-flow links to use absolute public URLs:
  - `https://ai.imperialax.com/signup-v2.html`
  - `https://ai.imperialax.com/signup-v2.ko.html`
  - `https://ai.imperialax.com/forgot-v2.html`
  - `https://ai.imperialax.com/forgot-v2.ko.html`
  - `https://ai.imperialax.com/login-v2.html`
  - `https://ai.imperialax.com/login-v2.ko.html`
- Updated login/signup/forgot success redirects to return to
  `https://ai.imperialax.com/index.html` or `index.ko.html`.

Verification:

- Public GET checks confirmed:
  - `https://ai.imperialax.com/signup-v2.html` -> `200`
  - `https://ai.imperialax.com/signup-v2.ko.html` -> `200`
  - `https://ai.imperialax.com/forgot-v2.html` -> `200`
- Public login page now contains:
  - `href="https://ai.imperialax.com/signup-v2.html"`
  - `href="https://ai.imperialax.com/forgot-v2.html"`
- `node --check` passed for `login-v2.js`, `signup-v2.js`, and
  `forgot-v2.js`.
- `.venv/bin/pytest tests/backend/test_imperialax_modules.py tests/backend/test_dd_laminate_ios_contract.py -q`
  passed: 26 tests, with the existing `asyncio_mode` pytest config warning.
- `git diff --check` passed for the touched ImperialAX account-flow files.

## 2026-06-19 - Module Pages Link Back To User Page

User clarified that the module selection page is effectively the User Page and
asked for Laminate and Injection pages to include a button returning there.

What changed:

- Added a `Modules` button to English Laminate pages:
  - `src/frontend/dd-laminate/index-v2.html`
  - `src/frontend/dd-laminate/index.html`
- Added a `모듈 선택` button to Korean Laminate pages:
  - `src/frontend/dd-laminate/index-v2.ko.html`
  - `src/frontend/dd-laminate/index.ko.html`
- Added the same English/Korean User Page return buttons to Injection:
  - `src/frontend/simple-injection/index-v2.html`
  - `src/frontend/simple-injection/index-v2.ko.html`
  - `src/frontend/simple-injection/index.html`
  - `src/frontend/simple-injection/index.ko.html`
- Buttons point to:
  - `https://ai.imperialax.com/index.html`
  - `https://ai.imperialax.com/index.ko.html`
- Added backend/static HTML tests so both Laminate and Injection pages must keep
  the User Page return links.

Verification:

- `.venv/bin/pytest tests/backend/test_dd_laminate_ios_contract.py tests/backend/test_simple_injection_model_labels.py -q`
  passed: 14 tests, with the existing `asyncio_mode` pytest config warning.
- `git diff --check` passed for touched Laminate/Injection HTML and tests.
- Public GET checks confirmed:
  - `https://laminate.imperialax.com/` contains the `Modules` link
  - `https://laminate.imperialax.com/dd-laminate-v2-ko` contains `모듈 선택`
  - `https://injection.imperialax.com/index-v2.html` contains the `Modules` link
  - `https://injection.imperialax.com/index-v2.ko.html` contains `모듈 선택`

## 2026-06-19 - ImperialAX Admin User Management Page

User asked where registered user information can be checked and then asked to
create an admin page.

What changed:

- Added a ImperialAX admin users API:
  - `GET /api/v1/modules/admin/users`
  - Requires `X-ImperialAX-Admin-Token` or `Authorization: Bearer ...`
  - Uses `IMPERIALAX_ADMIN_TOKEN`
  - Returns user profile fields, entitlements, session count, and last session
    timestamp.
  - Does not return password hashes or reset credentials.
- Added admin pages:
  - `src/frontend/imperialax/admin.html`
  - `src/frontend/imperialax/admin.ko.html`
  - `src/frontend/imperialax/admin.js`
- Added admin table/card styling to `src/frontend/imperialax/styles.css`.
- Added public routes for `/admin.html`, `/admin.ko.html`, and `/admin.js` on
  the `dd_laminate_app.py` public server used by `ai.imperialax.com`.
- Created `scripts/run_public_ai_server.sh` so the public LaunchAgent reads the
  admin token from `.omx/state/imperialax-admin-token.txt` without storing the
  secret in the plist.
- Updated `/Users/danlee/Library/LaunchAgents/com.kyulai.dd-laminate-api.plist`
  to run `scripts/run_public_ai_server.sh`; this fixed the stale public server
  that was restarting without the admin token.

Admin URLs:

- `https://ai.imperialax.com/admin.html`
- `https://ai.imperialax.com/admin.ko.html`

Verification:

- `node --check src/frontend/imperialax/admin.js`
- `.venv/bin/ruff check src/backend/api/v1/modules.py src/backend/services/imperialax_auth_store.py src/backend/dd_laminate_app.py tests/backend/test_imperialax_modules.py tests/backend/test_dd_laminate_ios_contract.py`
- `.venv/bin/pytest tests/backend/test_imperialax_modules.py tests/backend/test_dd_laminate_ios_contract.py -q`
  passed: 31 tests, with the existing `asyncio_mode` pytest config warning.
- Local admin API with token returned `user_count: 4`.
- Public admin API via `https://ai.imperialax.com/api/v1/modules/admin/users` with
  token returned `user_count: 4`.
- Public admin pages returned `200 text/html` for both English and Korean
  pages.

## 2026-06-19 - Admin Password Reset

User asked for password reset inside the admin page.

What changed:

- Added `reset_password_by_user_id()` to the ImperialAX auth store.
  - Admin reset updates the password hash/salt.
  - Existing sessions for that user are revoked.
  - The function returns only non-sensitive user profile fields.
- Added admin API:
  - `POST /api/v1/modules/admin/users/{user_id}/password`
  - Requires the same `X-ImperialAX-Admin-Token` or bearer admin token as the
    admin user list API.
  - Accepts `{ "password": "..." }` with the existing 8-character minimum.
- Added a `Reset password` / `비밀번호 재설정` action button to each row in the
  admin users table.
- Bumped admin page asset versions to `20260619-admin2`.
- Restarted the public `com.kyulai.dd-laminate-api` LaunchAgent so
  `https://ai.imperialax.com/admin.html` serves the updated UI.

Verification:

- `node --check src/frontend/imperialax/admin.js`
- `.venv/bin/ruff check src/backend/api/v1/modules.py src/backend/services/imperialax_auth_store.py tests/backend/test_imperialax_modules.py`
- `.venv/bin/pytest tests/backend/test_imperialax_modules.py tests/backend/test_dd_laminate_ios_contract.py -q`
  passed: 33 tests, with the existing `asyncio_mode` pytest config warning.
- Public admin HTML contains `admin2` assets and the `Actions` column.
- Public admin JS contains the reset-password action.
- Public reset endpoint returns `401` for an invalid admin token, confirming the
  live route is protected.

## 2026-06-19 - Admin Module Entitlement Toggles

User confirmed that admin-side module access management is needed.

What changed:

- Added `set_user_entitlements()` to the ImperialAX auth store.
  - Replaces a user's module entitlement set in `user_entitlements`.
  - Rejects missing users via the existing credentials error path.
- Added admin entitlement API:
  - `PUT /api/v1/modules/admin/users/{user_id}/entitlements`
  - Requires the same admin token as the other admin endpoints.
  - Accepts `{ "entitlements": ["module.laminate", ...] }`.
  - Rejects unknown entitlement keys.
- Extended the admin users response with server-provided module options so the
  admin UI follows `MODULE_CATALOG` instead of hardcoding module names.
- Updated the admin table to show module-access toggles per user:
  - Laminate
  - Injection
  - Optimization
- Changed module-access policy:
  - Anonymous/demo workspace can still see default active modules.
  - Logged-in accounts now depend on stored entitlements, so removing a module
    in admin changes `/api/v1/modules/me` immediately.
- Bumped admin page asset versions to `20260619-admin3`.
- Restarted the public `com.kyulai.dd-laminate-api` LaunchAgent so
  `https://ai.imperialax.com/admin.html` serves the updated UI.

Verification:

- `node --check src/frontend/imperialax/admin.js`
- `.venv/bin/ruff check src/backend/api/v1/modules.py src/backend/services/imperialax_auth_store.py tests/backend/test_imperialax_modules.py`
- `.venv/bin/pytest tests/backend/test_imperialax_modules.py tests/backend/test_dd_laminate_ios_contract.py -q`
  passed: 35 tests, with the existing `asyncio_mode` pytest config warning.
- Public admin HTML contains `admin3`, `Module access`, and `Actions`.
- Public admin JS contains the entitlement update endpoint and success/error
  text.

## 2026-06-19 - Optimization MVP For Laminate Design Search

User asked whether design/optimization is possible in the current state and
said they wanted to try building it.

What changed:

- Added the first Optimization API:
  - `POST /api/v1/optimization/search`
  - Initial domain: `laminate`
  - Generates bounded Double-Double laminate candidate grids over `case`,
    `theta1`, and `theta2`.
  - Calls the existing DD Laminate response predictor for each candidate.
  - Ranks candidates by:
    - `balanced`
    - `maximize_pt`
    - `maximize_force`
    - `minimize_displacement`
    - `target_pt`
  - Supports constraints:
    - target Type
    - minimum confidence
    - min/max Pt
    - minimum force
    - maximum displacement
  - Limits search size with `max_candidates`.
- Added `src/backend/api/v1/optimization.py`.
- Included the optimization router in:
  - `src/backend/imperialax_app.py`
  - `src/backend/dd_laminate_app.py`
- Added a usable Optimization web screen:
  - `src/frontend/imperialax/optimization.html`
  - `src/frontend/imperialax/optimization.ko.html`
  - `src/frontend/imperialax/optimization.js`
- Added Optimization UI styling in `src/frontend/imperialax/styles.css`.
- Changed the Optimization catalog entry from planned to active, while keeping
  it entitlement-gated.
- Updated the module card route:
  - English: `https://ai.imperialax.com/optimization.html`
  - Korean workspace opens `https://ai.imperialax.com/optimization.ko.html`
- Added public routes for `/optimization.html`, `/optimization.ko.html`, and
  `/optimization.js` in the public DD/ImperialAX server.
- Restarted the public `com.kyulai.dd-laminate-api` LaunchAgent.

Verification:

- `node --check src/frontend/imperialax/app.js`
- `node --check src/frontend/imperialax/optimization.js`
- `.venv/bin/ruff check src/backend/api/v1/optimization.py src/backend/api/v1/modules.py src/backend/imperialax_app.py src/backend/dd_laminate_app.py tests/backend/test_imperialax_modules.py tests/backend/test_dd_laminate_ios_contract.py`
- `.venv/bin/pytest tests/backend/test_imperialax_modules.py tests/backend/test_dd_laminate_ios_contract.py -q`
  passed: 39 tests, with the existing `asyncio_mode` pytest config warning.
- Public API smoke test:
  - `POST https://ai.imperialax.com/api/v1/optimization/search`
  - one Case2 / theta1 30 / theta2 -30 candidate
  - returned one feasible candidate with `predicted_pt`, force, displacement,
    Type, and confidence.
- Public pages returned `200 text/html`:
  - `https://ai.imperialax.com/optimization.html`
  - `https://ai.imperialax.com/optimization.ko.html`
- Public `optimization.js` contains `/api/v1/optimization/search`.

## 2026-06-19 - Optimization Search Speed Fix

User reported that Optimization search did not seem to work.

Root cause:

- The web default search generated 75 candidates:
  - Case2/Case3/Case4
  - theta1 -60..60 step 30
  - theta2 -60..60 step 30
- The API was calling the full DD Laminate response endpoint for every
  candidate, which also computed XAI/detail data that is unnecessary for
  ranking.
- The classical response predictor loaded the joblib bundle inside each
  prediction call unless routed through the API cache.

What changed:

- Added `predict_response_from_bundle(...)` in
  `src/ml/dd_laminate/predict_response_surrogate.py`.
- Updated DD Laminate response prediction to use `_cached_joblib_model(...)`
  for classical response models.
- Added an Optimization fast path that bypasses per-candidate XAI and uses
  cached classical response bundles for ranking.
- Reduced the default Optimization search space to 9 candidates:
  - Case2 only by default
  - theta1 -30..30 step 30
  - theta2 -30..30 step 30
- Updated both English and Korean Optimization pages with the safer defaults.
- Restarted the public `com.kyulai.dd-laminate-api` LaunchAgent.

Verification:

- Local API smoke test:
  - before fast path: default 9-candidate search took about 52 seconds.
  - after fast path: first request about 5.4 seconds, cached request about
    1.9 seconds.
- Public API smoke test:
  - `POST https://ai.imperialax.com/api/v1/optimization/search`
  - default payload returned `200`, `searched_count=9`,
    `feasible_count=9`, `skipped_count=0`.
- Public Korean page confirmed updated defaults:
  - Case2 checked.
  - Case3/Case4 unchecked.
  - theta ranges set to -30..30.
- `node --check src/frontend/imperialax/optimization.js`
- `.venv/bin/ruff check src/backend/api/v1/optimization.py src/ml/dd_laminate/predict_response_surrogate.py`
- `.venv/bin/pytest tests/backend/test_imperialax_modules.py tests/backend/test_dd_laminate_ios_contract.py`
  passed: 39 tests, with the existing `asyncio_mode` pytest config warning.

## 2026-06-20 - Admin Module In ImperialAX Apps

User asked to make the admin page visible from the app while keeping it hidden
from other users.

Decision:

- Do not create a separate admin app yet.
- Add an admin-only module inside the unified ImperialAX app.
- Keep the admin module out of the public module catalog.
- Add it only to `/api/v1/modules/me` when the logged-in account is an admin.
- Treat these accounts as admin by default:
  - `danlee@imperialax.com`
  - `dannylee9295@gmail.com`
- Allow `IMPERIALAX_ADMIN_EMAILS` to override the admin email list.

What changed:

- Added a private `ADMIN_MODULE` definition in `src/backend/api/v1/modules.py`.
- Added `module.admin` as an effective entitlement for admin accounts.
- Updated admin API authorization so it accepts:
  - existing `IMPERIALAX_ADMIN_TOKEN`
  - admin account session tokens such as `danlee-token`
- Updated `/api/v1/modules/me`:
  - `danlee-token` gets Laminate, Injection, Optimization, and Admin.
  - `demo-token` does not receive Admin.
- Updated `src/frontend/imperialax/admin.js` so `?session_token=...` or
  `?admin_token=...` auto-fills the admin token and loads users.
- Updated iOS ImperialAX app:
  - Admin card appears only when the server returns it.
  - Admin opens inside the app via `WKWebView`.
  - Admin URL includes the current app session token.
- Updated Android ImperialAX app:
  - Added `AdminWebActivity`.
  - Admin opens inside the app via `WebView`.
  - Admin URL includes the current app session token.

Verification:

- `node --check src/frontend/imperialax/admin.js`
- `.venv/bin/ruff check src/backend/api/v1/modules.py tests/backend/test_imperialax_modules.py`
- `.venv/bin/pytest tests/backend/test_imperialax_modules.py tests/backend/test_dd_laminate_ios_contract.py`
  passed: 41 tests, with the existing `asyncio_mode` pytest config warning.
- `swift test` in `ios/ImperialAXMVP` passed.
- `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home gradle :app:assembleDebug`
  passed in `android/ImperialAXMVP`.
- Restarted the public `com.kyulai.dd-laminate-api` LaunchAgent.
- Public API checks:
  - `GET https://laminate.imperialax.com/api/v1/modules/me` with
    `Authorization: Bearer danlee-token` includes `admin`.
  - The same endpoint with `demo-token` does not include `admin`.
  - `GET /api/v1/modules/admin/users` with `X-ImperialAX-Admin-Token:
    danlee-token` returns `200`.
  - `GET https://ai.imperialax.com/api/v1/modules/admin/users` with
    `danlee-token` returns `200`, matching the in-app admin WebView origin.
  - The same admin endpoint with `demo-token` returns `401`.

## 2026-06-20 - Laminate Pt Label Source Check

User asked how the original Laminate Pt values were obtained, because the UI
now shows a red Predicted Pt and a purple Fit/Intersection Pt on the response
curve.

Findings:

- For the standard Laminate Case2/Case3/Case4 data, our pipeline did not
  re-detect Pt from the force-displacement curve. It reads Pt directly from
  tabular CSV columns such as `Pt`, `PT`, `P1`, `Transition_Load`, or
  `transition_load`, then writes the curated `transition_load.csv`.
- The curated Case2/Case3/Case4 files contain explicit rows like
  `Test_ID,theta1,theta2,Pt,type`; the force-displacement CSV is copied
  separately and is used for curve shape/modeling, not for deriving the Pt
  label in that preparation script.
- Response model targets use `[record.pt, max_displacement, max_force]`; the
  `record.pt` value comes from the curated transition table.
- For u3 Pt data, the source is different: the raw folders contain
  force-displacement CSVs plus plot images. The preparation script parses Pt
  from plot titles via OCR/regex (`p1_plot_title` preferred, fallback
  `transition_plot_title`) and stores that in `manifest.csv`.
- `DD_u3_pt_v2/dataset_summary.json` records 566 u3 samples, with Pt sources:
  505 from `p1_plot_title` and 61 from `transition_plot_title`.
- In the frontend, red `Predicted Pt` is the model's predicted scalar Pt placed
  on the predicted curve by interpolating where curve force equals that Pt.
- Purple `Fit intersection` is not an original label. It is computed only for
  visualization by fitting two local linear segments to the predicted curve and
  drawing their intersection/kink.

Remaining caveat:

- The repository shows how our training data consumed Pt labels, but it does
  not fully prove how the very first human/source process selected the Pt in
  the original CSV/plot. For Case2/3/4, that upstream Pt may have been manually
  or experimentally marked before the data reached us; our code treats it as an
  existing label.

Follow-up clarification:

- For standard Laminate Case2/Case3/Case4, Type 1, Type 2, and Type 3 all read
  Pt from the same row-level transition table source. The row's `type` column is
  used as the class label, and the same row's `Pt` column is used as the Pt
  target; there is no separate type-specific Pt extraction path.
- This clarification does not apply to the u3 Pt dataset, whose Pt values were
  prepared from plot-title OCR into `manifest.csv`.
- Current Case2/Case3/Case4 response-training scripts default to
  `data/datasets/DD_cases_2_3_4_curated_v1`, so the relevant transition tables
  are:
  - `data/datasets/DD_cases_2_3_4_curated_v1/Case2/transition_load.csv`
  - `data/datasets/DD_cases_2_3_4_curated_v1/Case3/transition_load.csv`
  - `data/datasets/DD_cases_2_3_4_curated_v1/Case4/transition_load.csv`
- Compared those curated transition tables against the raw
  `data/datasets/Double-Double/{2,3,4}/transition load P1.csv` and
  `transition load.csv` files:
  - Curated Case2/3/4 each have 300 rows, matching the raw P1 row count.
  - After normalizing `Test_001` -> `001` and header case, curated theta/Pt
    values are exactly identical to raw `transition load P1.csv` for all 900
    rows.
  - Curated files are not byte-identical to raw P1 files because curated files
    normalize headers/test IDs and add the `type` column.
  - Curated files are not the same as raw `transition load.csv`: theta values
    match, but Pt differs for all 300 rows in each case.

## 2026-06-20 - Laminate/u3 Curve Chart PPT Ratio

User felt the Laminate and u3 response graphs looked stretched too wide, and
asked to make them closer to the younger sibling's PPT examples.

Changes:

- Checked the local PPT references (`data/PPT/Final ver2.pptx` and
  `data/datasets/DD/Presentation_G3MS_Dongwon.pptx`). The relevant
  force-displacement plots are mostly 2000 x 1200, so their visual ratio is
  about 5:3.
- Updated the web response curve canvas from 720 x 300 to 720 x 432 in the
  Laminate frontend, including the v2 English/Korean pages.
- Added a fixed 5:3 `aspect-ratio` for `#response-curve-canvas` so the browser
  does not flatten the curve horizontally.
- Updated the web curve drawing logic to use a little more vertical padding,
  start the y-axis scale from zero, and draw subtle gridlines like the PPT
  charts.
- Updated the exported result report image so the embedded curve keeps the new
  taller chart proportion.
- Updated native iOS and Android Laminate chart views so the plot area is
  centered inside a 5:3 frame instead of filling every wide container.

Verification:

- `node --check src/frontend/dd-laminate/app.js`
- `node --check src/frontend/dd-laminate/app-v2.js`
- `swift build` in `ios/DDLaminateMVP`
- `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
  gradle :app:assembleDebug` in `android/DDLaminateMVP`
- `git diff --check` for the touched graph files

Browser note:

- The v2 page loaded in the in-app browser and confirmed the canvas attribute
  is now 720 x 432. A full live forecast render could not be reliably completed
  because local server/API access was inconsistent during the browser smoke
  check.

## 2026-06-20 - Laminate/u3 Curve Axis Tick Labels

User asked for numeric values to appear on both the x-axis and y-axis of the
Laminate/u3 graphs.

Changes:

- Added compact numeric tick labels to the web response curve canvas for both
  x-axis and y-axis. The tick formatter automatically reduces decimals for
  larger values and keeps enough precision for small displacement values.
- Applied the same tick-label rendering to the v2 web script, so Response
  Forecast and u3 Forecast share the same chart treatment.
- Increased chart padding slightly so axis numbers do not collide with the
  curve or get clipped.
- Added axis tick labels and subtle gridlines to the native iOS chart canvas.
- Added axis tick labels and subtle gridlines to the native Android chart view.
- Updated Android touch-position math to use the same centered 5:3 plot frame
  that is used for drawing, so point selection still lines up with the curve.

Verification:

- `node --check src/frontend/dd-laminate/app.js`
- `node --check src/frontend/dd-laminate/app-v2.js`
- `git diff --check` for the touched chart files
- `swift build` in `ios/DDLaminateMVP`
- `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
  gradle :app:assembleDebug` in `android/DDLaminateMVP`

## 2026-06-22 - Backend Curve-Fit Metadata for Laminate Graphs

User clarified that the web graph should show the backend kink-fit result
instead of recalculating the fit only in frontend JavaScript.

Changes:

- Added `kink_fit_details()` in `src/ml/dd_laminate/pt_curve_consistency.py`.
  It returns the same kink-fit result used by `kink_fit_transition()`, plus
  first/second fit line slope/intercept, display spans, detected kink, and
  window indices.
- Added `curve_fit` to Laminate Forecast ML/DL and u3 Forecast ML/DL prediction
  outputs.
- Added optional `curve_fit` to the DD Laminate FastAPI response schemas.
- Updated the v2 web frontend so `drawResponseCurve()` uses backend
  `curve_fit` first and only falls back to JavaScript fitting when older
  responses do not include it.
- Bumped v2 script cache version to `20260622-backend-fit`.
- Restarted the local/public DD server on port 8000.

Verification:

- `python -m py_compile` for the changed ML/backend modules.
- `node --check src/frontend/dd-laminate/app-v2.js`.
- Local API check for Case2, θ₁=30, θ₂=-30:
  `predicted_pt = 17163.21208`,
  `curve_fit.kink.force = 17163.21208`.
- u3 API check for Case2, θ₁=30, θ₂=-30:
  `predicted_pt = 10205.06331`,
  `curve_fit.kink.force = 10205.06331`.
- Public URL check confirmed
  `https://laminate.imperialax.com/index-v2.html` loads
  `app-v2.js?v=20260622-backend-fit`.
- Public API check confirmed `curve_fit` is present and matches Predicted Pt.

## 2026-06-22 - Show Backend Fit Intersection as Predicted Pt

User asked to hide the red curve-crossing Predicted Pt marker and leave only
the backend fit-intersection point, but label that point as Predicted Pt.

Changes:

- Updated `src/frontend/dd-laminate/app-v2.js` so the response curve marker is
  always `bilinearFit.kink` from backend `curve_fit`.
- Removed the separate red curve-crossing point from the rendered graph.
- Kept the fit-intersection diamond marker and label, but renamed the label to
  `Predicted Pt` / `예측 Pt`.
- Updated English/Korean v2 legends to remove `Fit intersection` and the
  separate red `Predicted Pt` item.
- Bumped the v2 frontend cache version to `20260622-fit-pt-label`.

Verification:

- `node --check src/frontend/dd-laminate/app-v2.js`.
- `rg` confirmed no v2 `Fit intersection`, `Fit 교차점`, or
  `legend-swatch pt` entries remain.
- Public page check confirmed
  `https://laminate.imperialax.com/index-v2.html` loads
  `app-v2.js?v=20260622-fit-pt-label`.

Follow-up color tweak:

- Changed the Predicted Pt marker, label connector, label card, and legend
  swatch from purple to amber so it is visually distinct from the purple kink
  guide line.
- Bumped v2 CSS/JS cache version to `20260622-pt-amber`.
- Verified `node --check src/frontend/dd-laminate/app-v2.js`.
- Public page check confirmed the amber cache version is served.

Follow-up revert:

- User preferred the original purple treatment, so Predicted Pt marker, label,
  and legend swatch were changed back to purple.
- Bumped v2 CSS/JS cache version to `20260622-pt-purple`.
- Verified `node --check src/frontend/dd-laminate/app-v2.js`.
- Public page check confirmed the purple cache version is served.

## 2026-06-22 - DD Forecast Model Loading and XAI Speed Optimization

User noticed model loading felt slow and asked whether it could be optimized.

Findings:

- Tree/ML forecast model files were partly cached already for Laminate Forecast,
  but u3 Tree forecast still loaded its joblib bundle per request.
- Deep Learning forecast endpoints loaded the Torch checkpoint and rebuilt the
  neural model per request.
- The largest remaining perceived delay for ML models was live Tree XAI feature
  masking, not only model file loading.

Changes:

- Added cached Deep Learning artifact builders for Laminate Forecast and u3
  Forecast so Torch checkpoints and instantiated model objects are reused.
- Added `predict_response_deep_from_artifacts()`,
  `predict_u3_forecast_from_bundle()`, and
  `predict_u3_forecast_deep_from_artifacts()` so API routes can call cached
  artifacts directly.
- Changed u3 Tree forecast route to use the existing joblib model cache.
- Changed live local XAI to mask the strongest 12 global feature candidates
  instead of every feature on every request.
- Added an LRU cache for local XAI explanations by `(model, theta1, theta2,
  case)`.
- Added server startup warm-up for the primary Laminate/u3 ML and DL forecast
  models.

Verification:

- `python -m py_compile` passed for changed backend/ML modules.
- `node --check src/frontend/dd-laminate/app-v2.js` still passed.
- TestClient benchmark after changes:
  - Laminate ML: first ~6.9s cold, repeated same input ~0.23s.
  - u3 ML: first ~4.7s cold, repeated same input ~0.17s.
  - Laminate DL: ~0.04-0.05s after artifact caching.
  - u3 DL: ~0.07s after artifact caching.
- Startup warm-up took about 7.1s and reduced first ML request after warm-up to
  about 2.3s.
- Local running server check:
  - first same Laminate ML request after server warm-up/XAI change: ~2.7s
  - repeated same input: ~0.25s
- Public API check returned HTTP 200 and confirmed the new XAI note:
  "strongest 12 global candidates"; cached public request measured about 0.64s.

## 2026-06-22 - DD Lazy XAI Loading

User chose optimization option 1: show the prediction immediately, then load XAI
separately after the result is visible.

Changes:

- Added `POST /api/v1/dd-laminate/xai/local` for local theta/case XAI
  explanations.
- Removed live XAI calculation from Laminate Forecast and u3 Forecast prediction
  responses. The responses still include `xai: null` for schema compatibility,
  but no feature masking is performed during prediction.
- Updated the v2 web UI so Forecast results render first, then an XAI loading
  panel appears and automatically fills once `/xai/local` returns.
- Added request-serial guarding so late XAI responses from a previous input/tab
  cannot overwrite the current result.
- Bumped v2 page cache version to `20260622-lazy-xai`.

Verification:

- `python -m py_compile src/backend/api/v1/dd_laminate.py
  src/backend/dd_laminate_app.py` passed.
- `node --check src/frontend/dd-laminate/app-v2.js` passed.
- FastAPI TestClient check:
  - Laminate Forecast prediction: HTTP 200, ~0.37s, `xai` is `null`.
  - u3 Forecast prediction: HTTP 200, ~0.17s, `xai` is `null`.
  - Separate local XAI request: HTTP 200, ~1.90s, returned 35 feature rows.

## 2026-06-22 - u3 Graph Marker Split

User said the u3 graph looked odd after the Pt/fit-consistency changes and asked
to restore the earlier graph style with separate `Predicted Pt` and
`Fit Intersection` markers.

Changes:

- For u3 forecast graph drawing only, the frontend now ignores backend
  `curve_fit` alignment and uses the earlier frontend kink-fit calculation.
- u3 graphs now draw:
  - red circle on the curve for `Predicted Pt`
  - purple diamond for `Fit Intersection`
- The curve legend switches dynamically:
  - Laminate Forecast keeps the simpler curve/linear-fit/Predicted Pt legend.
  - u3 Forecast shows both `Predicted Pt` and `Fit Intersection`.
- Bumped v2 page cache version to `20260622-u3-split-fit`.

Verification:

- `node --check src/frontend/dd-laminate/app-v2.js` passed.

Follow-up:

- User reported that u3 input `θ₁=-29`, `θ₂=74`, `Case4` still produced an odd
  graph and that label placement varied too much.
- Checked the live u3 prediction: predicted Pt about `9355.96`, max
  displacement about `0.48969`, max force about `57962.90`.
- Fixed u3 graph rendering so the second linear fit starts at the fit
  intersection instead of extending left across the early graph. This prevents a
  long dashed line from visually cutting through the plot on long-displacement
  u3 curves.
- Added fixed label-coordinate support to `drawPtLabel()`.
- For u3 graphs, `Fit Intersection` and `Predicted Pt` labels now use a stable
  stacked layout near the top of the plot, farther away from the points and
  curve.
- Bumped v2 page cache version to `20260622-u3-label-layout`.
- Verified `node --check src/frontend/dd-laminate/app-v2.js`.
- Public page check confirmed the new cache version is served.

Second follow-up:

- User clarified that u3 should receive the same fit-intersection correction as
  the earlier Laminate Forecast check, where:
  - `Predicted Pt`
  - `kink_fit_pt_force_after`
  - recalculated returned-curve kink Pt
  all match with `diff: 0.0`.
- Root cause: u3 frontend had been switched back to a local frontend kink-fit
  calculation, and the backend `curve_fit` metadata also had a mixed state where
  `kink.force` was corrected but the returned `first_line`/`second_line`
  intersection could still recompute to a different force.
- Changed `kink_fit_details()` to accept `target_force`. When supplied, the
  returned `first_line` and `second_line` intercepts are adjusted so their actual
  intersection force equals the target Predicted Pt.
- Passed `target_force=predicted_pt` from Laminate Forecast ML, Laminate
  Forecast DL, u3 Forecast ML, and u3 Forecast DL prediction paths.
- Changed u3 frontend rendering back to backend `curve_fit` first, while keeping
  the u3 display-range normalization so the second linear fit starts at the fit
  intersection for cleaner visuals.
- Bumped v2 page cache version to `20260622-u3-fit-target`.

Verification:

- `python -m py_compile` passed for the changed ML/API modules.
- `node --check src/frontend/dd-laminate/app-v2.js` passed.
- Local direct u3 check for `θ₁=-29`, `θ₂=74`, `Case4`:
  - `Predicted Pt: 9355.96274`
  - `kink_fit_pt_force_after: 9355.96274`
  - `returned curve 재계산 kink Pt: 9355.96274`
  - `diff: 0.00000000`
- Restarted the DD server on port 8000.
- Public API check for the same u3 input returned the same `diff: 0.00000000`.
- Public page check confirmed `20260622-u3-fit-target` is served.

Revert:

- User clarified that the immediately previous slope drawing was better and the
  desired fix is different.
- Reverted the `target_force` fit-intersection metadata change from
  `kink_fit_details()` and removed `target_force=...` calls from Laminate
  Forecast/u3 prediction modules.
- Reverted u3 frontend curve drawing to the previous frontend u3 bilinear fit
  path instead of prioritizing backend `curve_fit`.
- Kept the previous u3 label layout improvements from `20260622-u3-label-layout`.
- Restarted the DD server on port 8000.
- Verified:
  - `python -m py_compile` passed for changed ML/API modules.
  - `node --check src/frontend/dd-laminate/app-v2.js` passed.
  - Public page serves `20260622-u3-label-layout`.
  - Public u3 Forecast API returns HTTP 200 for `θ₁=-29`, `θ₂=74`, `Case4`.

Third follow-up:

- User clarified the intended behavior: `Fit Intersection` does not need to
  match `Predicted Pt`; it should simply sit at the actual intersection of the
  two drawn linear-fit slopes.
- Updated u3 graph rendering so the purple `Fit Intersection` marker and guide
  use `lineIntersection(firstLine, secondLine)` instead of the clamped
  `bilinearFit.kink` point.
- Kept the red `Predicted Pt` marker on the predicted curve point.
- Bumped v2 page cache version to `20260622-u3-true-intersection`.
- Verified `node --check src/frontend/dd-laminate/app-v2.js`.
- Public page check confirmed the new cache version is served.

## 2026-06-22 - u3 model recap

- User asked for a detailed recap of the u3 model data and configuration.
- Current u3 raw data root: `data/datasets/Double-Double/u3`.
- Current curated u3 dataset root: `data/datasets/DD_u3_pt_v2`.
- Curated manifest contains 566 labeled records:
  - Case2: 190
  - Case3: 174
  - Case4: 202
  - folders: `2-2`, `2-3`, `3-2`, `3-3`, `4-2`, `4-3`
- `x-2` / `x-3` folder suffixes are legacy Type 2 / Type 3 buckets, used as a secondary type label for u3 Forecast; main target is Pt.
- Main visible u3 Forecast models:
  - ML: `u3_forecast_physics_v2` -> `models/dd_laminate_u3_forecast_physics_v3/u3_forecast.joblib`
  - DL: `u3_forecast_goint_physics_v2` -> `models/dd_laminate_u3_forecast_physics_v3/u3_forecast_goint.pt`
- Current feature builder for both: `theta_physics_v2`, 43 features.
- Current output grid length: 192 curve points.
- ML metrics:
  - ExtraTrees Pt MAE: 223.79 kips
  - Pt R2: 0.9131
  - curve normalized RMSE: 0.00702
  - type accuracy: 97.53%
  - type macro F1: 96.24%
- DL/GointMLP metrics:
  - Pt MAE: 168.65 kips
  - Pt R2: 0.9226
  - curve normalized RMSE: 0.01018
- u3 Pt Finder CSV-based models still exist but are not the main UI path:
  - ML: `models/dd_laminate_u3_pt_ml_v2/u3_pt_regressor.joblib`
  - DL: `models/dd_laminate_u3_pt_goint_v2/u3_pt_goint.pt`
- Main API endpoint: `POST /api/v1/dd-laminate/predict/u3-forecast`.

## 2026-06-22 - Full debugging pass

- User asked for a broad debugging pass over the current codebase and to fix
  issues where safe.
- Persistent report written to `docs/debugging-audit-2026-06-22.md`.
- Verified current state first without reverting existing user/worktree changes.
- Tests and checks run:
  - Python: `.venv/bin/python -m pytest tests -q` -> 170 passed.
  - Python compile: `.venv/bin/python -m compileall -q src scripts tests` -> passed.
  - DD/API smoke via FastAPI TestClient:
    - `/health` -> 200.
    - Laminate response model `response_goint_physics_nn_v2` -> 200.
    - u3 ML model `u3_forecast_physics_v2` -> 200.
    - u3 DL model `u3_forecast_goint_physics_v2` -> 200.
  - JavaScript syntax checks for DD, ImperialAX, and Simple Injection frontend
    files -> passed.
  - iOS SwiftPM:
    - `ios/DDLaminateMVP swift test` -> 11 passed.
    - `ios/ImperialAXMVP swift test` -> 4 passed.
  - Android Gradle debug builds:
    - Initial runs failed because macOS Java discovery could not find JDK 17.
    - Re-ran with `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home`.
    - ImperialAXMVP, DDLaminateMVP, and InjectionMVP debug builds all passed.
- Fixes made:
  - Replaced deprecated DD standalone FastAPI `@app.on_event("startup")` with
    lifespan startup.
  - Hardened DD/u3 response prediction paths with strict curve/probability
    zipping so model artifact length mismatches fail loudly instead of silently
    truncating.
  - Added empty-curve guard in the deep Laminate Forecast smoothing helper.
  - Removed unused physics-feature temporary variable.
  - Added strict feature-name/value zipping for compact and neural-friendly
    physics feature vectors.
  - Cleaned an unused Pt curve consistency variable.
  - Added `.gitignore` protection for local ImperialAX auth SQLite files and Office
    lock files.
- Remaining known risks:
  - Current `.venv` does not include `pytest-asyncio`, so pytest reports
    `Unknown config option: asyncio_mode`; `Makefile install-dev` already
    installs `pytest-asyncio`, so this is an environment setup gap.
  - Full repo `ruff check src tests scripts` still reports many legacy style
    issues, mostly FastAPI dependency defaults, script import order, naming
    warnings, and old validation/unit-test style conventions. They are not
    failing runtime tests, but should be handled in a separate cleanup pass to
    avoid a noisy mega-diff.
  - Gradle builds require JDK 17 to be discoverable or `JAVA_HOME` set on the
    server/developer machine.

Follow-up in same debugging pass:

- User approved installing and running additional dev checks such as mypy.
- Installed/normalized local dev tools:
  - `pytest-asyncio`, removing the pytest `asyncio_mode` config warning.
  - `mypy==1.9.0`, matching the repo pre-commit mirror version.
- Updated type-check configuration:
  - `pyproject.toml` now uses `explicit_package_bases = true`.
  - `Makefile typecheck` now passes `--explicit-package-bases`.
- Fixed targeted typing/runtime-boundary issues in current serving paths:
  - DD/ImperialAX host parsing now handles a missing `Host` header safely.
  - DD API dynamic model bundle/checkpoint outputs are cast at the boundary
    before being passed into Pydantic responses.
  - u3 forecast/checkpoint loader uses `Any` at artifact boundaries and strict
    zipping for curve/probability outputs.
  - DD/u3 training scripts now type mixed metric dictionaries explicitly.
  - Simple Injection DOE and filling-pressure summaries now validate through
    the Pydantic response model.
  - Optimization default factories now return fully typed defaults.
- Targeted checks now passing:
  - `ruff check` on changed DD/Simple Injection/optimization/model helper files.
  - `mypy --explicit-package-bases` on DD app, ImperialAX app, DD API, Simple
    Injection API, optimization API, DD/u3 model helpers, and Simple Injection
    data loader.
  - `pytest tests -q` -> 170 passed, 2 scipy precision warnings.
  - `compileall -q src scripts tests` -> passed.
  - `node --check` for DD, ImperialAX, and Simple Injection frontend app files -> passed.
  - `swift test` for iOS DD and ImperialAX packages -> 11 passed / 4 passed.
  - Android `gradle :app:assembleDebug` for ImperialAXMVP, DDLaminateMVP, and
    InjectionMVP -> all passed with `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home`.
- Remaining known technical debt:
  - Full `mypy --explicit-package-bases src --ignore-missing-imports` still has
    332 errors in 26 files, mostly legacy `data/schemas/tool_mappings`, older
    Pydantic default-factory typing, generic training/evaluation typing, and
    experiment/dataset service annotations.
  - `pip check` still reports `nlopt 2.10.0` requiring `numpy>=2,<3` while the
    current ML environment uses `numpy 1.26.4`; do not upgrade numpy casually
    without validating sklearn/scipy/model artifacts.
  - Current local `.venv` is Python 3.10.20 even though `pyproject.toml` requires
    Python `>=3.11`; tests pass locally, but fresh Windows/server setup should
    use Python 3.11+.

## 2026-06-23 - Windows Serving Handoff Stabilization

- User said "ㄱㄱ" after the recommended next direction: stabilize the project
  for a Windows server handoff before adding more model/UI features.
- Implemented readiness probes:
  - DD standalone app now exposes `/ready`, returning warm status for the two
    exposed Laminate Forecast models and the two exposed u3 Forecast models.
  - Simple Injection standalone app now exposes `/ready`, returning model-file
    and dependency availability for sprue/filling ML, GointMLP, and DeepONet
    models.
  - ImperialAX unified app also exposes `/ready`, combining DD and Simple
    Injection readiness.
- Improved Windows scripts:
  - `Setup-WindowsServing.ps1` now checks the configured Python command,
    enforces Python 3.11+, runs `pip check`, and prints DD/Injection model
    readiness after installing dependencies.
  - `Start-All.ps1` now supports `-SkipCloudflare` for local-only startup and
    runs `Check-Health.ps1 -Ready -LocalOnly` after launching DD/Injection.
  - `Check-Health.ps1` now supports `-Ready`, `-LocalOnly`, `-PublicOnly`,
    `-Strict`, retry options, and configurable public base URLs.
  - `Start-CloudflareTunnel.ps1` now fails with a clear install command if
    `cloudflared.exe` is not on PATH.
- Updated portable bundle coverage:
  - `scripts/package_windows_bundle.py` now includes the ImperialAX/ImperialAX frontend,
    all currently API-referenced DD model directories, all currently
    API-referenced Simple Injection sprue/filling model directories, and the
    current Double-Double/u3 curated datasets needed for serving handoff.
- Updated Windows docs:
  - `docs/windows-server-migration.md` and `docs/WINDOWS_GIT_QUICKSTART.md`
    now recommend local-first startup with `Start-All.ps1 -SkipCloudflare`,
    then `/ready` validation, then Cloudflare config/startup.
- Added backend tests covering the new DD and Simple Injection readiness
  endpoints.

## 2026-06-23 - Windows Portable Bundle Created

- Created a Windows handoff zip at
  `dist/KyulAI_windows_server_bundle_2026-06-23.zip`.
- Bundle size/count:
  - Size: about 1.3 GB.
  - Entries: 9,867 files.
- Bundle includes:
  - DD Laminate, Simple Injection, and ImperialAX/ImperialAX backend/frontend runtime code.
  - Windows serving scripts under `scripts/windows`.
  - Serving requirements and `.env.windows.example`.
  - Current API-referenced DD and Simple Injection model directories.
  - Current DD/Double-Double/u3 and Simple Injection datasets selected by
    `scripts/package_windows_bundle.py`.
  - Windows/server migration docs.
- Verification performed:
  - `unzip -t dist/KyulAI_windows_server_bundle_2026-06-23.zip` passed with no
    compressed-data errors.
  - Zip file list check found no `.git`, `.venv`, `.env.local`,
    `.cloudflared`, `__pycache__`, `.pyc`, or `.DS_Store` entries.
  - Targeted secret-pattern scan over text files inside the zip found 0 hits
    for the prior Slack webhook/signing-secret values.
- Deliberately not included:
  - `models/dd_laminate_response_tabular_challengers_v1/extra_trees.joblib`
  - `models/dd_laminate_response_tabular_challengers_v1/random_forest.joblib`
  - These two remain untracked because they are 453 MB / 215 MB research-only
    challenger artifacts and are not active serving registry defaults.

## 2026-06-23 - Laminate Research Insight Panel

- User approved moving from XAI-only explanations toward a more
  research-oriented view explaining where a prediction sits in the design
  space.
- Added DD backend endpoint:
  - `POST /api/v1/dd-laminate/design-space`
  - Inputs: `theta1`, `theta2`, `case`, and `scope` (`response` or `u3`).
  - Response includes:
    - `map_points`: curated data points for plotting θ₁/θ₂ design-space
      position.
    - `nearest_points`: nearest existing simulations around the current input.
    - `case_summaries`: Case2/3/4 count, median/max Pt, Type rates, and
      compact risk label.
    - `recommendations`: simulation-backed candidate angle/case suggestions.
    - `notes`: interpretation caveats.
- Recommendation behavior:
  - Laminate Forecast recommendations now prioritize observed Type 1 candidates
    because Type 1 bilinear behavior is the research target.
  - u3 recommendations prioritize high observed u3 Pt while showing Type 2/3 as
    curve-family context.
- Updated DD v2 web UI:
  - Added a compact `Research Insight` panel below XAI.
  - Panel draws a θ₁/θ₂ map, highlights the current input, shows Case risk
    cards, nearest simulations, and recommended candidates.
  - Korean page receives the same panel structure and Korean labels.
- Verification:
  - `ruff check src/backend/api/v1/dd_laminate.py tests/backend/test_dd_laminate_ios_contract.py`
  - `mypy --explicit-package-bases src/backend/api/v1/dd_laminate.py --ignore-missing-imports`
  - `pytest tests/backend/test_dd_laminate_ios_contract.py -q` -> 16 passed.
  - `node --check src/frontend/dd-laminate/app-v2.js`

## 2026-06-23 - Research Insight Visibility Check

- User reported Research Insight was not visible for θ₁=-30, θ₂=30, Case2.
- Confirmed the backend design-space endpoint returns data for that input:
  - status 200
  - 509 map points
  - 8 nearest points
  - 8 recommendation candidates
- Clarified behavior:
  - Research Insight runs only on DD v2 `Laminate Forecast` and `u3 Forecast`
    results.
  - It does not run for Curve CSV preview/classification flows.
  - Local `/` may still serve the legacy page unless the host is
    `laminate.imperialax.com`; local v2 testing should use `/index-v2.html` or
    the v2 route exposed by the server.
- Updated DD v2 HTML asset query strings to
  `20260623-research-insight` so browsers/Cloudflare fetch the current
  `app-v2.js` and `styles-v2.css`.
- Follow-up:
  - User asked whether design-space map colors represent Type or Case.
  - Confirmed colors represent Type 1/2/3; the current input is purple and
    selected Case points are drawn with stronger opacity.
  - Added English/Korean map legends under the Research Insight canvas.
  - Bumped DD v2 asset query strings again to `20260623-research-legend`.

## 2026-06-23 - Research Insight Candidate Apply

- User chose the first next-step feature: make Research Insight recommended
  candidates actionable.
- Added click behavior to `Recommended candidates` cards:
  - Card is now a real button.
  - Clicking it applies candidate `θ₁`, `θ₂`, and `Case` to the active forecast
    form.
  - It then immediately submits the matching forecast mode:
    - `Laminate Forecast` -> `POST /predict/response`
    - `u3 Forecast` -> `POST /predict/u3-forecast`
  - Existing model selection is preserved.
- Added English/Korean compact CTA text:
  - English: `Apply and forecast`
  - Korean: `입력에 적용하고 예측`
- Updated button styling so recommendation cards read as clickable without
  changing the research card layout.
- Bumped DD v2 asset query strings to `20260623-recommendation-apply`.
- Verification:
  - `node --check src/frontend/dd-laminate/app-v2.js`
  - `git diff --check -- src/frontend/dd-laminate/app-v2.js src/frontend/dd-laminate/index-v2.html src/frontend/dd-laminate/index-v2.ko.html src/frontend/dd-laminate/styles-v2.css`
  - `python -m pytest tests/backend/test_dd_laminate_ios_contract.py::test_design_space_endpoint_returns_research_context -q`
  - Browser smoke test on `http://127.0.0.1:8000/index-v2.html`:
    - Ran default Response Forecast.
    - Confirmed 5 recommendation buttons render.
    - Clicked first candidate (`Case3`, `θ₁=32`, `θ₂=-60`).
    - Confirmed the Response Forecast form changed to `θ₁=32`, `θ₂=-60`,
      `Case3`.
    - Confirmed prediction refreshed with Pt `16,960.47` and Research Insight
      reloaded with 5 recommendation buttons.

## 2026-06-23 - Research Insight Candidate Comparison

- User asked to continue to the next Research Insight improvement.
- Implemented the second planned feature: `Current input vs top candidate`.
- Added a compact comparison block under the design-space map legend:
  - Current forecast card:
    - Case, θ₁, θ₂
    - model-predicted Pt
    - model-predicted Type
    - current Case risk
  - Top candidate card:
    - Case, θ₁, θ₂
    - observed dataset Pt
    - observed Type
    - candidate Case risk
  - Pt delta pill comparing candidate observed Pt against current model Pt.
  - Rationale line explaining why the candidate was recommended.
- UI wording explicitly distinguishes `Model estimate` from
  `Dataset observation` so the comparison is useful without pretending both
  numbers have the same provenance.
- Added Korean labels for the same comparison UI.
- Bumped DD v2 asset query strings to `20260623-research-comparison`.
- Verification:
  - `node --check src/frontend/dd-laminate/app-v2.js`
  - `git diff --check -- src/frontend/dd-laminate/app-v2.js src/frontend/dd-laminate/index-v2.html src/frontend/dd-laminate/index-v2.ko.html src/frontend/dd-laminate/styles-v2.css`
  - `python -m pytest tests/backend/test_dd_laminate_ios_contract.py::test_design_space_endpoint_returns_research_context -q`
  - Browser smoke test on `http://127.0.0.1:8000/index-v2.html`:
    - Ran default Response Forecast.
    - Confirmed comparison block shows `Current input vs top candidate`.
    - Confirmed current card for default `Case2`, `θ₁=30`, `θ₂=-30` and top
      candidate card for `Case3`, `θ₁=32`, `θ₂=-60`.
    - Confirmed recommendation click still applies the candidate and refreshes
      the comparison block to the applied `Case3`, `θ₁=32`, `θ₂=-60` input.

## 2026-06-23 - Research Insight Map Tooltip

- User asked to continue to the next Research Insight improvement.
- Implemented point detail tooltip for the design-space map:
  - Hover or click a point to see Case, Type, θ₁, θ₂, Pt, and Test ID.
  - Tooltip labels whether the point belongs to the selected Case or another
    Case.
  - Hit testing uses the same canvas coordinates as the rendered points.
  - When overlapping points are close, points from the selected Case are
    prioritized.
  - Tooltip closes when the pointer leaves the map area.
- Wrapped the map canvas in a positioned shell and added compact tooltip
  styling.
- Bumped DD v2 asset query strings to `20260623-research-tooltip`.
- Verification:
  - `node --check src/frontend/dd-laminate/app-v2.js`
  - `git diff --check -- src/frontend/dd-laminate/app-v2.js src/frontend/dd-laminate/index-v2.html src/frontend/dd-laminate/index-v2.ko.html src/frontend/dd-laminate/styles-v2.css`
  - `/Users/danlee/KyulAI_codex/.venv/bin/python -m pytest tests/backend/test_dd_laminate_ios_contract.py::test_design_space_endpoint_returns_research_context -q`
  - Browser smoke test on `http://127.0.0.1:8000/index-v2.html`:
    - Ran default Response Forecast.
    - Hovered the design-space map near `θ₁=32`, `θ₂=-60`.
    - Confirmed tooltip appears with `Case 2`, `Type 1`, `Pt 16,888.95`,
      and `Test 255`.
    - Confirmed tooltip is hidden again after moving outside the map.

## 2026-06-23 - Research Insight Case Behavior Zones

- User asked for the next Research Insight improvement.
- Added backend `case_insights` to `POST /api/v1/dd-laminate/design-space`.
- Response scope:
  - Each Case insight focuses on the high-Pt subset of Type 1 rows.
  - This intentionally avoids using every Type 1 row because the full Type 1
    range can span almost the entire theta design space and is less useful as a
    quick screening zone.
- u3 scope:
  - Each Case insight focuses on the high-Pt subset because u3 Type 2/3 is used
    as curve-family context while Pt is the primary target.
- Frontend v2 now shows compact `Case behavior zones` / `Case별 유리 영역`
  cards below the current-vs-candidate comparison:
  - focus zone label
  - theta window
  - best observed Pt/theta/type sample
  - zone sample count and rate
  - selected Case highlight
- Bumped DD v2 asset query strings to `20260623-case-insight`.
- Restarted local DD/ImperialAX server on port `8000`; new listener PID was
  `15345`.
- Verification:
  - `node --check src/frontend/dd-laminate/app-v2.js`
  - `git diff --check -- src/backend/api/v1/dd_laminate.py tests/backend/test_dd_laminate_ios_contract.py src/frontend/dd-laminate/app-v2.js src/frontend/dd-laminate/index-v2.html src/frontend/dd-laminate/index-v2.ko.html src/frontend/dd-laminate/styles-v2.css`
  - `/Users/danlee/KyulAI_codex/.venv/bin/python -m pytest tests/backend/test_dd_laminate_ios_contract.py::test_design_space_endpoint_returns_research_context tests/backend/test_dd_laminate_ios_contract.py::test_u3_design_space_endpoint_returns_curve_family_context -q`
  - `/Users/danlee/KyulAI_codex/.venv/bin/ruff check src/backend/api/v1/dd_laminate.py tests/backend/test_dd_laminate_ios_contract.py`
  - Live API check on `http://127.0.0.1:8000/api/v1/dd-laminate/design-space`
    returned 3 `case_insights`; default Case2 response focus was 27/300 samples.
  - Browser smoke check on `http://127.0.0.1:8000/index-v2.html` confirmed
    3 Case behavior cards render and the selected Case card is highlighted.
- Follow-up layout change:
  - User said the Case behavior cards would be easier to read as 3 horizontal
    rows rather than 3 cards in one row.
  - Changed `case-insight-list` to a single-column stack.
  - Changed each card to a horizontal row layout: Case/zone label on the left,
    theta window / best observed / sample count on the right.
  - Mobile still collapses cards and details to one column.
  - Bumped DD v2 asset query strings to `20260623-case-insight-rows`.
  - Browser smoke check confirmed:
    - 3 cards render.
    - `case-insight-list` has one grid column.
    - the first card uses two internal columns.
    - selected Case highlight remains.
- Follow-up comparison layout change:
  - User asked to make the `Current input vs top candidate` section horizontal
    as well.
  - Changed the comparison grid from two compact side-by-side cards into two
    full-width rows.
  - Each row now keeps the Case/theta identity on the left and Pt/Type/Risk
    metrics on the right.
  - Mobile still collapses the row internals into a single column.
  - Bumped DD v2 asset query strings to `20260623-comparison-rows`.
  - Browser smoke check confirmed:
    - 2 comparison cards render.
    - `.comparison-grid` has one grid column.
    - the first comparison row uses two internal columns.
- Follow-up score explanation:
  - User asked what condition determines `Top candidate`.
  - Next action was to make that condition visible in the UI.
  - Added backend `score_components` to each design-space recommendation:
    - weighted Pt contribution
    - weighted Type contribution
    - weighted proximity/distance contribution
    - raw normalized Pt/Type/proximity values
  - `score_components.pt + score_components.type + score_components.proximity`
    equals the recommendation `score`.
  - Frontend v2 now shows a compact `Recommendation score` row under
    `Current input vs top candidate`.
  - Default live API check for `θ₁=30`, `θ₂=-30`, `Case2`, response scope:
    - total score `0.5474`
    - Pt `0.2924`
    - Type `0.18`
    - Distance/proximity `0.075`
  - Bumped DD v2 asset query strings to `20260623-score-breakdown`.
  - Restarted local DD/ImperialAX server on port `8000`; new listener PID was
    `46131`.
  - Verification:
    - `node --check src/frontend/dd-laminate/app-v2.js`
    - `git diff --check -- src/backend/api/v1/dd_laminate.py tests/backend/test_dd_laminate_ios_contract.py src/frontend/dd-laminate/app-v2.js src/frontend/dd-laminate/index-v2.html src/frontend/dd-laminate/index-v2.ko.html src/frontend/dd-laminate/styles-v2.css`
    - `/Users/danlee/KyulAI_codex/.venv/bin/python -m pytest tests/backend/test_dd_laminate_ios_contract.py::test_design_space_endpoint_returns_research_context tests/backend/test_dd_laminate_ios_contract.py::test_u3_design_space_endpoint_returns_curve_family_context -q`
    - `/Users/danlee/KyulAI_codex/.venv/bin/ruff check src/backend/api/v1/dd_laminate.py tests/backend/test_dd_laminate_ios_contract.py`
    - Browser smoke check confirmed score chips render:
      `Pt 29.2%`, `Type 18%`, `Distance 7.5%`, `Total 54.7%`.

## 2026-06-23 - iOS DD Laminate graph/XAI parity pass
- User reported the iOS app was tangled and did not match the web content,
  starting with a mismatched DD Laminate graph.
- Root cause:
  - Web v2 renders response curves from backend `curve_fit` when available.
  - iOS decoded only `curve`/`predicted_pt` and recomputed bilinear fits locally,
    so slope/intersection placement could diverge from the web.
  - Web now loads XAI separately through `/api/v1/dd-laminate/xai/local`, but
    iOS only displayed XAI when it was embedded in the prediction response.
- Changes:
  - Added iOS Core models for `curve_fit`:
    `ResponseCurveFit`, fit lines, fit points, and fit windows.
  - Added optional `curveFit` decoding to `ResponsePredictionResult` and
    `U3PtPredictionResult`.
  - Updated all DD iOS graph callsites to pass `curveFit`.
  - Reworked `CurveChartView` so standard Laminate Forecast graphs prefer
    backend `curve_fit`, while u3 keeps its web-style u3 fit behavior.
  - Made the chart module public enough for the ImperialAX package to reuse.
  - Added `/xai/local` support to the iOS API client and ViewModel:
    if prediction responses do not include XAI, iOS now fetches local XAI with
    the same `theta1`, `theta2`, `Case`, and model key, then attaches it before
    presenting the result detail.
  - Added a compact graph + XAI block to the ImperialAX-specific
    `LaminateForecastView`; the actual app path currently opens
    `DDLaminateModuleView`, which also received the graph/XAI fixes.
- Verification:
  - `swift test` in `ios/DDLaminateMVP`: 11 tests passed.
  - `swift build` in `ios/ImperialAXMVP`: passed.
  - XcodeBuildMCP simulator run:
    - project: `ios/ImperialAXMVPApp/ImperialAXMVPHost.xcodeproj`
    - scheme: `ImperialAXMVPHost`
    - simulator: `iPhone 17`
    - build/install/launch succeeded.
  - Simulator smoke flow:
    - opened ImperialAX app
    - opened Laminate module
    - ran default `Case2`, `theta1=30`, `theta2=-30` forecast
    - result showed Type 2, Predicted Pt `17,163.21`, 128 curve points
    - graph showed Pt label/marker at `17,163.21`
    - XAI detail card appeared with `Why this prediction?` and feature
      importance rows, e.g. `D11 bending stiffness` at `23.4%`.
  - Useful simulator screenshots from this pass:
    - graph view:
      `/var/folders/7p/c3j_sb0j539805ngspmnb34r0000gn/T/screenshot_optimized_816dfc7a-7eee-49de-b290-0433d21e4862.jpg`
    - XAI view:
      `/var/folders/7p/c3j_sb0j539805ngspmnb34r0000gn/T/screenshot_optimized_bc89dc88-a5c0-428f-b74d-d1f84b72355b.jpg`

## 2026-06-23 - iOS DD Laminate Research Insight parity pass
- User asked to keep adding the next web features into the iOS app after the
  graph/XAI parity pass.
- Added iOS Research Insight support for both Laminate Forecast and u3 Forecast:
  - `PredictionViewModel` now loads design-space context for u3 as well as
    response forecasts.
  - iOS detail routes now carry the current `DesignSpaceResponse` into result
    detail pages.
  - Added a shared `ResearchInsightCard` to the DD iOS result detail screen.
  - The card mirrors the web feature hierarchy:
    `Current input vs top candidate`, `Recommendation score`, and
    `Case behavior zones`.
  - Recommendation score displays Pt, Type, Distance, and Total percentages.
  - Case behavior zones are shown as vertical rows for Case 2/3/4, matching the
    revised web layout direction.
- Verification:
  - `swift test` in `ios/DDLaminateMVP`: 11 tests passed.
  - `swift build` in `ios/ImperialAXMVP`: passed.
  - XcodeBuildMCP simulator run succeeded with:
    - project: `ios/ImperialAXMVPApp/ImperialAXMVPHost.xcodeproj`
    - scheme: `ImperialAXMVPHost`
    - simulator: `iPhone 17`
  - Laminate Forecast smoke check:
    - default `Case2`, `theta1=30`, `theta2=-30`
    - Research Insight appeared with top candidate:
      `Case 3 · theta1 +32 deg · theta2 -60 deg`
    - score chips appeared: Pt `29.2%`, Type `18.0%`,
      Distance `7.5%`, Total `54.7%`.
  - u3 Forecast smoke check:
    - default `Case2`, `theta1=30`, `theta2=-30`
    - result showed Predicted Pt `10,205.06` and graph label `Pt 10,205.06`
    - Research Insight appeared with top candidate:
      `Case 4 · theta1 -38 deg · theta2 -40 deg`
    - score chips appeared: Pt `72.0%`, Type `12.6%`,
      Distance `5.7%`, Total `90.3%`.
  - Useful simulator screenshots from this pass:
    - Laminate Research Insight:
      `/var/folders/7p/c3j_sb0j539805ngspmnb34r0000gn/T/screenshot_optimized_8bb48db7-3e9a-4f78-9b98-9cb12f0c67ed.jpg`
    - u3 Research Insight:
      `/var/folders/7p/c3j_sb0j539805ngspmnb34r0000gn/T/screenshot_optimized_d86f2a6a-5bbe-4c49-83da-1bfa3031142c.jpg`

## 2026-06-23 - iOS DD Laminate Design-space map polish
- User asked whether the theta range text such as `-56 to 67` could be made
  easier to read, and whether a design-space dot graph could be added to the
  app.
- Changes:
  - Replaced range wording with a compact angle format:
    `theta1 -56 deg to +67 deg` -> `theta1 -56° ~ +67°`.
  - Changed Research Insight angle labels from `deg` to `°`.
  - Added `DesignSpacePoint` and `mapPoints` decoding on iOS for backend
    `map_points`.
  - Added a compact SwiftUI `Canvas` design-space scatter map inside the iOS
    `ResearchInsightCard`.
  - Map rules match the web behavior:
    - Type 1/2/3 color coding.
    - Same-Case points are stronger, other Case points are faded.
    - Current input is a purple marker.
    - Top candidate is a highlighted diamond marker.
    - Axes are theta1 x theta2 from -90 to +90.
- Verification:
  - `swift test` in `ios/DDLaminateMVP`: 11 tests passed.
  - `swift build` in `ios/ImperialAXMVP`: passed.
  - XcodeBuildMCP build/run succeeded on `iPhone 17`.
  - Laminate Forecast simulator smoke check confirmed:
    - `Design-space map` appears in Research Insight.
    - Range labels render as e.g.
      `theta1 -56° ~ +67° · theta2 -66° ~ +65°`.
  - u3 Forecast simulator smoke check confirmed:
    - `Design-space map` appears in Research Insight.
    - Candidate/current angle labels use `°`.
  - Useful simulator screenshots from this pass:
    - Laminate map:
      `/var/folders/7p/c3j_sb0j539805ngspmnb34r0000gn/T/screenshot_optimized_0812630a-13b1-4d88-bf79-5dfd8aad96a6.jpg`
    - u3 map:
      `/var/folders/7p/c3j_sb0j539805ngspmnb34r0000gn/T/screenshot_optimized_62c3cd25-764a-4108-a10a-e237022cafa9.jpg`

## 2026-06-23 - iOS DD Laminate v2 result-detail refresh
- User reported that the iOS result page still looked like the old classic
  page even when entering from the v2 Laminate screen.
- Cause:
  - The v2 input screen and the classic input screen both route into the same
    shared `ResultDetailView` / `U3PtResultDetailView`.
  - The shared detail views still used the older classic-style result layout.
- Changes:
  - Refreshed the shared Laminate Forecast result detail into a v2-style page:
    dark gradient hero, compact confidence/model/points badges, stronger metric
    tiles, v2 section headers, and the existing curve/XAI/research cards below.
  - Refreshed the shared u3 Forecast result detail with the same v2 treatment.
  - Kept the backend curve-fit, Pt marker, XAI, and Research Insight behavior
    unchanged; this pass was visual/readability-focused.
- Verification:
  - `swift test` in `ios/DDLaminateMVP`: 11 tests passed.
  - `swift build` in `ios/ImperialAXMVP`: passed.
  - XcodeBuildMCP simulator smoke check on `iPhone 17` confirmed:
    - Laminate Forecast result detail shows the v2 hero and result cards.
    - u3 Forecast result detail shows the v2 hero and result cards.
  - Useful simulator screenshots from this pass:
    - Laminate v2 result detail:
      `/var/folders/7p/c3j_sb0j539805ngspmnb34r0000gn/T/screenshot_optimized_4ae91a4e-f7d5-43d8-8d31-c9643584b1e7.jpg`
    - u3 v2 result detail:
      `/var/folders/7p/c3j_sb0j539805ngspmnb34r0000gn/T/screenshot_optimized_bb18fa12-8b9f-4412-a739-73dff27d5cf9.jpg`

## 2026-06-23 - iOS Research Insight Case-zone readability polish
- User said the three `Case behavior zones` examples were hard to distinguish,
  especially the two theta ranges inside each row.
- Changes:
  - Updated the shared iOS `ResearchInsightCard` case-zone rows.
  - Each Case row now has a stronger Case-specific accent color:
    Case 2 blue, Case 3 cyan, Case 4 amber.
  - Added a colored Case badge, tinted background, and stronger border.
  - Split theta ranges into two separate chips:
    `theta1 range` and `theta2 range` are no longer combined into one dense
    sentence.
  - Separated Best Pt, Type, sample count, and focus-rate information into
    distinct visual positions.
- Verification:
  - `swift test` in `ios/DDLaminateMVP`: 11 tests passed.
  - `swift build` in `ios/ImperialAXMVP`: passed.
  - XcodeBuildMCP build/run succeeded on `iPhone 17`.
  - Laminate Forecast simulator smoke check confirmed the updated
    `Case behavior zones` layout.
  - Useful simulator screenshot:
    `/var/folders/7p/c3j_sb0j539805ngspmnb34r0000gn/T/screenshot_optimized_f81cb8c9-759e-48b2-a72b-0b499e41c744.jpg`

## 2026-06-23 - Web Research Insight Case-zone readability polish
- User asked to apply the same Case behavior zone readability improvement to
  the web DD Laminate v2 UI.
- Changes:
  - Updated `src/frontend/dd-laminate/app-v2.js` Case Insight rendering.
  - Case rows now receive stable classes for Case 2, Case 3, and Case 4.
  - Theta ranges now use a compact `~` range separator in all languages.
  - Split dense theta range text into separate theta1/theta2 range chips.
  - Split Best Pt, Best theta, Best Type, and sample coverage into separate
    metric cells.
  - Updated `src/frontend/dd-laminate/styles-v2.css` with Case-specific colors:
    Case 2 blue, Case 3 cyan, Case 4 amber.
  - Added stronger card backgrounds, colored badges, borders, and mobile metric
    grid behavior.
  - Updated `index-v2.html` and `index-v2.ko.html` cache-bust query strings to
    `v=20260623-case-zones` so browsers request the new JS/CSS.
- Verification:
  - `node --check src/frontend/dd-laminate/app-v2.js` passed.
  - `git diff --check` for the changed DD web v2 files passed.
  - `http://127.0.0.1:8000/index-v2.html` returned HTTP 200 while the local DD
    server was running.
  - A live design-space POST previously returned 3 `case_insights` for the
    default `Case2`, `theta1=30`, `theta2=-30` response request; later POST
    smoke attempts were intermittent in the sandbox, while the server process
    remained listening on port 8000.

## 2026-06-23 - ImperialAX app login-screen check
- User asked whether the mobile app was missing a login page.
- Findings:
  - iOS and Android both have a login page; the app skips it when a saved
    account/demo session exists.
  - iOS stores the session under `imperialax.auth.session.v1` in `UserDefaults`.
  - Android stores the session under the `imperialax_auth` SharedPreferences.
  - Both apps expose `Sign out`, which clears the saved session and re-renders
    the login page.
- Verification:
  - XcodeBuildMCP simulator check on `iPhone 17` first showed the app already
    inside the workspace as `Demo Account · 2 modules`.
  - Tapping `Sign out` immediately displayed the login page with email,
    password, `Sign in`, `Create a new account`, and
    `Continue with demo account`.

## 2026-06-23 - ImperialAX app session timeout
- User asked whether the app can automatically log out after staying logged in
  for some time.
- Decision:
  - Added a local 24-hour session lifetime to both iOS and Android apps.
  - Existing saved sessions without a timestamp are migrated by assigning the
    first app launch time after this update, so users are not logged out
    immediately on upgrade.
- iOS:
  - Stores `imperialax.auth.saved_at.v1` next to the existing
    `imperialax.auth.session.v1` session in `UserDefaults`.
  - Checks expiry on startup, refresh/request actions, and app active-state
    transitions.
  - Expired sessions are cleared and the login screen shows
    `Session expired. Please sign in again.`
  - Added tests for expired-session clearing and legacy-session timestamp
    migration.
- Android:
  - Stores `saved_at_ms` next to the existing `imperialax_auth` SharedPreferences
    values.
  - Checks expiry on startup, resume, and before opening a module.
  - Expired sessions are cleared and the login screen shows the same message.
- Verification:
  - `swift test` in `ios/ImperialAXMVP`: 6 tests passed.
  - `swift build` in `ios/ImperialAXMVP`: passed.
  - XcodeBuildMCP `build_run_sim` for `ImperialAXMVPHost` on `iPhone 17`: passed.
  - Runtime UI snapshot showed the login screen with email/password fields,
    `Sign in`, `Create a new account`, and `Continue with demo account`.
  - Android `gradle :app:assembleDebug` passed when run with
    `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home`.

## 2026-06-23 - ImperialAX app Optimization module routing
- User asked whether Optimization was reflected in the app.
- Findings:
  - Optimization backend/API and web page already existed:
    `/api/v1/optimization/search` and `src/frontend/imperialax/optimization.html`.
  - iOS/Android apps already listed the Optimization module, but the fallback
    copy still treated it as planned/coming soon and the app route pointed at
    the generic `https://ai.imperialax.com` module page.
- Changes:
  - Updated iOS and Android fallback module metadata to treat Optimization as
    an active, access-controlled module.
  - Updated Optimization module route to
    `https://ai.imperialax.com/optimization.html`.
  - Updated login preview copy from `Coming soon` to `Design search`.
  - iOS now opens granted Optimization access inside the existing in-app
    WebView with the session token attached.
  - Android now opens Optimization with the existing WebView activity and the
    session token attached.
- Verification:
  - `swift test` in `ios/ImperialAXMVP`: 6 tests passed.
  - `swift build` in `ios/ImperialAXMVP`: passed.
  - Android `gradle :app:assembleDebug` passed with Java 17 `JAVA_HOME`.
  - XcodeBuildMCP simulator smoke:
    - Login preview shows Optimization as `Design search`.
    - Dan Lee account shows `Optimization` as `Available`.
    - `Open Optimize` opens the in-app `Optimization` WebView.
  - Useful simulator screenshot:
    `/var/folders/7p/c3j_sb0j539805ngspmnb34r0000gn/T/screenshot_optimized_75752447-0c90-48df-9aba-8f02cacb38bc.jpg`

## 2026-06-23 - Admin account control inside the app
- User asked whether accounts can be controlled from the app Admin surface.
- Decision:
  - The mobile apps already open Admin through the shared in-app WebView with
    the `session_token`, so account management should be implemented in the
    Admin web/API layer and will be visible from both iOS and Android.
- Backend changes:
  - Added admin account creation:
    `POST /api/v1/modules/admin/users`.
  - Added admin profile update:
    `PUT /api/v1/modules/admin/users/{user_id}/profile`.
  - Account creation supports selected module entitlements. If entitlements are
    omitted, default Laminate/Injection access is used; if an empty list is
    sent, the account is created with no module access.
- Admin UI changes:
  - Added a `Create account` / `계정 생성` card to `admin.html` and
    `admin.ko.html`.
  - Added module entitlement checkboxes for new accounts.
  - Added per-user `Edit profile` / `정보 수정` action next to password reset.
  - Existing module access toggles and password reset remain available.
  - Bumped Admin asset cache version to `20260623-admin-account`.
- Verification:
  - `/Users/danlee/KyulAI_codex/.venv/bin/python -m pytest tests/backend/test_imperialax_modules.py`:
    29 passed.
  - `node --check src/frontend/imperialax/admin.js`: passed.
  - `git diff --check`: passed.

## 2026-06-24 - ImperialAX app interactive design-space map
- User asked for the in-app design-space map to show point details when dots
  are tapped, and to remain usable when the map does not fit the screen.
- iOS changes:
  - Added an interactive `InteractiveDesignSpaceMapView` inside
    `ios/ImperialAXMVP/Sources/ImperialAXApp/LaminateForecastView.swift`.
  - The map is wider than the card and wrapped in a horizontal `ScrollView`,
    so users can pan across the full theta1/theta2 design space.
  - Tapping a map dot selects the nearest simulation/design point and shows
    Case, Test ID, theta1, theta2, Pt, Type, and distance below the map.
  - Current input and top candidate markers remain visually distinct.
- Android changes:
  - Preserved backend `map_points` in
    `android/ImperialAXMVP/app/src/main/java/com/imperialax/app/LaminateActivity.kt`.
  - Added a custom `DesignSpaceMapView` in
    `android/ImperialAXMVP/app/src/main/java/com/imperialax/app/LaminateResultActivity.kt`.
  - The map is placed in a `HorizontalScrollView`; short taps select points,
    while drags continue to scroll the map.
  - Point details update in a compact info panel below the map.
- Artifact:
  - Copied the refreshed Android APK to
    `artifacts/android/ImperialAX-debug-design-space-map.apk`.
- Verification:
  - `swift test` in `ios/ImperialAXMVP`: 6 tests passed.
  - Android `gradle :app:assembleDebug` passed with Java 17 `JAVA_HOME`.
  - `git diff --check`: passed.

## 2026-06-24 - Android design-space map visibility cleanup
- User reported that the Android app still did not show the design-space map.
- Applied the `ai-slop-cleaner` workflow to the Android Laminate result path.
- Behavior lock:
  - The backend design-space endpoint was already known to return
    `map_points`; the Android path was treated as the display/failure-handling
    layer to lock.
  - Android `gradle :app:assembleDebug` passed after the fix.
- Fallback/slop findings:
  - The design-space API call used a silent `getOrNull()` path, so failures
    could be hidden from the result screen.
  - The map rendering was too tightly coupled to the recommendation/candidate
    block instead of being shown whenever `map_points` exist.
- Changes:
  - `LaminateActivity.kt` now carries either parsed design-space data or an
    explicit design-space error into `LaminateResultActivity`.
  - `LaminateResultActivity.kt` now renders the design-space map whenever
    `mapPoints` is non-empty, independent of whether a top candidate exists.
  - If the design-space request fails, the result page shows a visible
    unavailable card instead of silently omitting Research Insight.
  - Refreshed Android APK artifact:
    `artifacts/android/ImperialAX-debug-design-space-map.apk`.
- Verification:
  - Android `gradle :app:assembleDebug` passed with Java 17 `JAVA_HOME`.
  - Android `gradle :app:lintDebug` passed with Java 17 `JAVA_HOME`.
  - `git diff --check` passed.

## 2026-06-24 - Workspace refresh and password visibility UX
- User reported that the Android Workspace `Prediction modules` Refresh button
  did not visibly react, and that the login email/password fields were too
  cramped with password text visible.
- Product rule captured:
  - When a login/password UX issue is fixed on one platform, check and align
    Android, iOS, and web instead of leaving platform-specific drift.
- Android unified app:
  - Enlarged login input vertical padding/min-height.
  - Password field now uses password masking by default.
  - Added a side `Show` / `Hide` button for password visibility.
  - Refresh now disables itself while loading, changes to `Refreshing...`, and
    shows status text such as `Modules refreshed` or `Offline fallback shown`.
- iOS unified app:
  - Replaced the plain `SecureField` with a password entry row that supports
    show/hide via an eye icon while staying masked by default.
  - Increased login field height to reduce cramped input appearance.
  - Workspace Refresh now shows text plus progress/refresh state instead of an
    icon-only button.
- Web workspace/login:
  - Added show/hide password controls to `index.html`, `index.ko.html`,
    `login-v2.html`, and `login-v2.ko.html`.
  - Added visible Refresh status in the web workspace with loading, updated,
    and offline-fallback states.
  - Bumped web asset query versions to `20260624-auth-refresh1`.
- Artifact:
  - Refreshed Android APK:
    `artifacts/android/ImperialAX-debug-design-space-map.apk`.
- Verification:
  - `node --check src/frontend/imperialax/app.js`: passed.
  - `node --check src/frontend/imperialax/login-v2.js`: passed.
  - `swift test` in `ios/ImperialAXMVP`: 6 tests passed.
  - Android `gradle :app:assembleDebug` passed with Java 17 `JAVA_HOME`.
  - Android `gradle :app:lintDebug` passed with Java 17 `JAVA_HOME`.
  - `git diff --check` passed.

## 2026-06-24 - Demo email placeholder cleanup
- User asked that `demo@imperialax.com` should not be pre-filled as actual text in
  the login ID field. It should appear like an example/placeholder and
  disappear automatically when the user taps and types.
- Platform alignment:
  - Android already used `demo@imperialax.com` as an `EditText` hint rather than a
    direct input value, so no Android source change was needed.
  - iOS now starts with an empty email state and uses `demo@imperialax.com` as the
    `TextField` placeholder.
  - iOS blank Sign in still resolves to the demo email internally, preserving
    the demo-account convenience without forcing users to erase text.
  - Web `index`, `index.ko`, `login-v2`, and `login-v2.ko` now use
    `placeholder="demo@imperialax.com"` instead of a `value`.
  - Web demo buttons clear the email field instead of filling it with the demo
    address, while the existing blank-email demo fallback remains active.
  - Web asset query versions bumped to `20260624-auth-placeholder1`.
- Verification:
  - Search confirmed no remaining `value="demo@imperialax.com"` or prefilled iOS
    email state in the login inputs.
  - `node --check src/frontend/imperialax/app.js`: passed.
  - `node --check src/frontend/imperialax/login-v2.js`: passed.
  - `swift test` in `ios/ImperialAXMVP`: 6 tests passed.

## 2026-06-24 - App design-space point selection fix
- User reported that tapping the design-space control/points inside the app did
  not show point information reliably.
- Root cause:
  - Android renders the map as a custom `View` inside a horizontal scroll
    container, so small taps could be swallowed or treated like scroll gestures.
  - iOS renders the map as a `Canvas` inside a horizontal `ScrollView`, where
    dot-only tap targets were too fragile for touch use.
- Android unified app:
  - Preselects the nearest experiment point so the info panel is populated as
    soon as the result screen opens.
  - Adds `Nearest experiment points` buttons under the map; tapping a row
    updates both the info panel and the map selection ring.
  - Increases map tap tolerance and improves touch-parent coordination so dot
    taps work more reliably while preserving horizontal scrolling.
- iOS unified app:
  - Adds the same nearest-point row buttons under the design-space map.
  - Preselects the nearest experiment point on first render.
  - Uses a higher-priority map tap gesture and a larger nearest-point radius.
- Artifact:
  - Refreshed Android APK:
    `artifacts/android/ImperialAX-debug-design-space-map.apk`.
- Verification:
  - `swift test` in `ios/ImperialAXMVP`: 6 tests passed.
  - Android `gradle :app:assembleDebug` passed with JetBrains JBR Java 17.
  - Android `gradle :app:lintDebug` passed with JetBrains JBR Java 17.
  - `git diff --check` passed.

## 2026-06-24 - Codex phone/watch notification helper
- User asked whether permission-request and completion notifications can be
  received on a phone or watch because they may miss Codex while doing other
  work.
- Added `scripts/codex-notify.py`, a direct notification helper independent of
  the local agent bus.
- Supported events:
  - `approval`: use before a Codex approval prompt or other user attention
    requirement.
  - `complete`: use when a task/build/test pass is done.
  - `failed`: use when a task fails and needs user attention.
  - `info` and `test`: general updates and setup verification.
- Supported channels:
  - Telegram via `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
  - Slack via `SLACK_WEBHOOK_URL`.
  - `--channel auto` sends to whichever channel environment variables are
    configured.
- Added usage documentation to `docs/architecture/agent-communication.md`,
  including private `~/.codex/notify.env` setup, test notification examples,
  approval notification examples, and completion notification examples.
- Important limitation:
  - The Codex app approval button itself still must be pressed in Codex. The
    notification helper is a phone/watch nudge that tells the user to return to
    the app.
- Verification:
  - `PYTHONPYCACHEPREFIX=/private/tmp/codex-pycache python3 -m py_compile
    scripts/codex-notify.py` passed.
  - `python3 scripts/codex-notify.py --status` passed.
  - `python3 scripts/codex-notify.py approval --dry-run ...` printed Telegram
    and Slack dry-run payloads.
  - `python3 scripts/codex-notify.py complete --channel telegram --dry-run ...`
    printed a Telegram dry-run payload.
  - `git diff --check -- scripts/codex-notify.py
    docs/architecture/agent-communication.md` passed.

## 2026-06-24 - Android design-space visibility and theta symbol fix
- User reported that Android still did not show the design-space section, and
  that the Live Laminate Preview formula still displayed `theta1` / `theta2`
  instead of Greek symbols.
- Root correction:
  - The previous Android change improved point selection only after a
    design-space map was already rendered. It did not make the design-space
    section impossible to miss when the data was delayed, missing, or hidden
    below the larger result/XAI card.
- Android Laminate result screen:
  - Moved the Research Insight / design-space section directly under the input
    summary and before the large result/XAI card.
  - Result screen now fetches design-space data itself instead of relying on a
    large serializable Intent payload from the input screen.
  - Added an always-visible loading card: `Loading design-space map`.
  - Added an always-visible unavailable card if the design-space request fails,
    including the server/network error text.
  - Kept nearest-point row buttons and map selection behavior from the previous
    interaction fix.
- Android Live Laminate Preview:
  - Formula strings now use `θ₁`, `θ₂`, `±`, `∓`, and `×`.
  - Preview legend and angle input labels now use `θ₁` / `θ₂`.
  - Result summary and design-space point/candidate labels now use `θ₁` /
    `θ₂`, with degrees displayed as `°`.
- Artifact:
  - Refreshed Android APK:
    `artifacts/android/ImperialAX-debug-design-space-map.apk`.
- Verification:
  - Android `gradle :app:assembleDebug` passed with JetBrains JBR Java 17.
  - Android `gradle :app:lintDebug` passed with JetBrains JBR Java 17.
  - `git diff --check` for the touched Android files and session memory passed.

## 2026-06-24 - iOS Response Curve chart legend and fit-line polish
- User asked to refine the iOS Response Curve graph so it matches the web
  presentation more closely, including visible legend items and two clear red
  slope/linear-fit lines.
- Updated the shared SwiftUI `CurveChartView` used by both DD Laminate iOS and
  the ImperialAX/ImperialAX iOS host:
  - Added a responsive legend for predicted curve, linear fit, kink guide, and
    Predicted Pt.
  - Added English/Korean localized legend strings.
  - Changed draw order so the predicted curve is drawn first, then the red
    dashed linear-fit segments are drawn above it for better visibility.
  - Increased the red dashed line weight/opacity so both fit segments are easier
    to distinguish on phone screens.
  - Kept backend `curve_fit` usage for standard forecasts and u3 fit behavior.
- Increased chart frame heights in DD result panels, detail views, share image,
  and the ImperialAX Laminate forecast result so adding the legend does not shrink
  the graph too aggressively.
- Verification:
  - `swift test` in `ios/DDLaminateMVP`: 11 tests passed.
  - `swift test` in `ios/ImperialAXMVP`: 6 tests passed.
  - `git diff --check` passed.
  - XcodeBuildMCP built and launched `ImperialAXMVPHost` on the iPhone 17
    simulator successfully.
  - Simulator smoke test ran a Laminate forecast and confirmed the Response
    Curve result screen renders the new legend.

## 2026-06-24 - Android Response Curve zoom and fit-line parity
- User asked whether the same Response Curve zoom/polish work was applied to
  Android.
- Finding:
  - Android already had the Laminate result page and design-space map, but the
    Response Curve chart itself was not rendered in the result card.
- Android unified app updates:
  - Added parsing for backend `curve_fit` data in `LaminateActivity.kt`.
  - Added a custom Android `ResponseCurveChartView` in
    `LaminateResultActivity.kt`.
  - The chart renders the predicted force-displacement curve, red dashed
    two-segment linear fit, purple kink/Pt guide, axis labels, and compact
    legend.
  - Added pinch zoom, pan while zoomed, and `- / + / reset` controls.
  - Uses backend fit details when available and falls back to a curve-derived
    fit only when the API does not provide `curve_fit`.
- Artifact:
  - Refreshed Android APK:
    `artifacts/android/ImperialAX-debug-response-curve-zoom.apk`.
  - Also refreshed the usual install path:
    `artifacts/android/ImperialAX-debug-design-space-map.apk`.
- Verification:
  - Android `gradle :app:assembleDebug` passed with JetBrains JBR Java 17.
  - Android `gradle :app:lintDebug` passed with JetBrains JBR Java 17.

## 2026-06-24 - Android result order and chart pan polish
- User reported that the Android Laminate result page order still did not match
  the iOS/web flow, and that Response Curve zoom worked but one-finger graph
  movement was difficult.
- Android result page order:
  - Changed the page sequence to `input summary -> result card -> Research
    Insight / design-space -> back button`.
  - This matches the iOS result-card flow where metrics, curve, probabilities,
    and XAI come before research/design-space context.
- Android Response Curve interaction:
  - Button zoom and pinch zoom now keep the visible chart area centered instead
    of anchoring at the lower-left edge.
  - One-finger panning while zoomed now follows the same direction convention
    as iOS, including vertical movement.
  - The chart now asks parent scroll containers to stay out of the gesture while
    zooming or panning, so the page scroll should no longer steal the graph
    drag.
- Artifact:
  - Refreshed Android APK:
    `artifacts/android/ImperialAX-debug-result-order-zoom.apk`.
  - Also refreshed:
    `artifacts/android/ImperialAX-debug-design-space-map.apk`.
- Verification:
  - Android `gradle :app:assembleDebug` passed with JetBrains JBR Java 17.
  - Android `gradle :app:lintDebug` passed with JetBrains JBR Java 17.

## 2026-06-24 - Android Response Curve point selection
- User asked whether tapping the Android Response Curve still selects curve
  points like iOS.
- Finding:
  - The Android chart had zoom/pan and fit-line rendering, but tap-to-select
    curve point callouts were not yet implemented.
- Android Response Curve update:
  - Added tap selection to `ResponseCurveChartView`.
  - A tap inside the plot selects the closest curve point by displacement.
  - Selected points show a dashed crosshair, a highlighted marker, and an
    `x/y` value callout.
  - Panning while zoomed clears the selected point so chart movement stays
    uncluttered.
- Artifact:
  - Refreshed Android APK:
    `artifacts/android/ImperialAX-debug-curve-tap.apk`.
  - Also refreshed:
    `artifacts/android/ImperialAX-debug-design-space-map.apk`.
- Verification:
  - Android `gradle :app:assembleDebug` passed with JetBrains JBR Java 17.
  - Android `gradle :app:lintDebug` passed with JetBrains JBR Java 17.

## 2026-06-24 - Android Response Curve point scrubbing
- User asked whether a selected chart point can move along the graph while the
  finger moves on screen.
- Android Response Curve update:
  - Added curve scrubbing to `ResponseCurveChartView`.
  - In normal zoom, dragging inside the plot now moves the selected point along
    the predicted curve by nearest displacement.
  - In zoomed view, starting near the curve enters scrub mode; starting away
    from the curve keeps the existing one-finger pan behavior.
  - The selected point keeps the same dashed crosshair and `x/y` callout while
    scrubbing.
  - Edge clamping keeps the selected point stable when the finger approaches the
    plot boundaries.
- Artifact:
  - Refreshed Android APK:
    `artifacts/android/ImperialAX-debug-curve-scrub.apk`.
  - Also refreshed:
    `artifacts/android/ImperialAX-debug-design-space-map.apk`.
- Verification:
  - Android `gradle :app:assembleDebug` passed with JetBrains JBR Java 17.
  - Android `gradle :app:lintDebug` passed with JetBrains JBR Java 17.

## 2026-06-24 - Android iOS-style visual polish
- User asked to make the Android UI closer to the cleaner iOS look, especially
  font/color feel.
- Android visual update:
  - Kept the existing Pretendard font setup and aligned the Android palette to
    the iOS `WantedV2Theme` tone: softer page background, calmer field surfaces,
    lighter strokes, stronger blue accent, and darker ink text.
  - Applied the refreshed palette to the Android workspace, Laminate Forecast,
    Laminate Result, and Injection screens.
  - Updated primary command buttons to use an ink-to-blue/cyan gradient similar
    to the iOS button treatment.
  - Added subtle card elevation and softened chart plot/grid colors so the
    Response Curve and Design-space map feel less harsh.
- Artifact:
  - Created Android APK: `artifacts/android/ImperialAX-debug-ios-style.apk`.
  - Refreshed shared Android APK path:
    `artifacts/android/ImperialAX-debug-design-space-map.apk`.
- Verification:
  - Android `gradle :app:assembleDebug` passed with JetBrains JBR Java 17.
  - Android `gradle :app:lintDebug` passed with JetBrains JBR Java 17.

## 2026-06-24 - iOS/Android Research Insight parity pass
- User pointed out that Android still missed iOS parity in specific Research
  Insight details, and that iOS curve point scrubbing worked only at normal zoom.
- Android Research Insight update:
  - Added missing Design-space map legend entries for `Current` and `Candidate`
    so Android now shows `Type 1`, `Type 2`, `Type 3`, `Current`, and
    `Candidate` like iOS.
  - Restyled Case behavior zones with Case-specific tint cards:
    Case 2 blue, Case 3 cyan, Case 4 amber.
  - Reworked the zone content into clearer theta range chips and compact
    `Best Pt` / Type / count rows, matching the iOS layout intent.
  - Changed theta ranges from `to` to `~` with signed degree symbols.
- iOS Response Curve update:
  - Changed zoomed drag behavior so starting near the predicted curve scrubs
    the selected point along the curve, while starting away from the curve keeps
    the zoomed pan behavior.
  - This matches the Android curve interaction model more closely.
- Artifact:
  - Created Android APK: `artifacts/android/ImperialAX-debug-ios-android-parity.apk`.
  - Refreshed shared Android APK path:
    `artifacts/android/ImperialAX-debug-design-space-map.apk`.
- Verification:
  - Android `gradle :app:assembleDebug` passed with JetBrains JBR Java 17.
  - Android `gradle :app:lintDebug` passed with JetBrains JBR Java 17.
  - iOS `swift build` passed in `ios/DDLaminateMVP`.
  - iOS `swift test` passed in `ios/DDLaminateMVP` with 11 tests.

## 2026-06-24 - Android Forecast setup section clarity
- User reported that Android Forecast setup did not clearly separate Case,
  angle, and Model inputs.
- Android Laminate Forecast update:
  - Split Forecast setup into numbered sections:
    `01 Case`, `02 Angles`, and `03 Model`.
  - Added short helper subtitles for each setup section.
  - Wrapped Case and Model controls in their own section cards instead of
    leaving raw spinners directly in the setup card.
  - Added a Case formula readout under the Case picker and update it when the
    selected Case changes.
  - Kept θ₁ and θ₂ angle controls grouped inside a dedicated Angles section.
  - Increased Case/Model spinner touch height for clearer mobile input.
- Artifact:
  - Created Android APK:
    `artifacts/android/ImperialAX-debug-forecast-setup-sections.apk`.
  - Refreshed shared Android APK path:
    `artifacts/android/ImperialAX-debug-design-space-map.apk`.
- Verification:
  - Android `gradle :app:assembleDebug` passed with JetBrains JBR Java 17.
  - Android `gradle :app:lintDebug` passed with JetBrains JBR Java 17.

## 2026-06-24 - DD Laminate Prediction History deletion
- User asked to restore a history deletion screen with individual selection and
  a select-all option, and to apply it to web, iOS, and Android.
- Web DD Laminate v2:
  - Added a `Manage` mode to the Prediction history panel.
  - Users can select individual history cards, use `Select all`, clear the
    selection, cancel management mode, or delete selected records.
  - Deletion is scoped to the visible Response Forecast/u3 Forecast history and
    removes matching records from `localStorage`.
  - Mode switches and result resets clear stale delete-selection state.
- iOS DD Laminate v2:
  - Added a `Manage History` sheet from the Prediction history panel.
  - The sheet supports per-record checkmarks, `Select all`, `Clear`, and
    `Delete Selected`.
  - Deletion reuses `PredictionViewModel.deleteRecentRuns(ids:)`, so Response
    Forecast and u3 Forecast history remain separated by the existing model
    layer.
- Android Laminate Forecast:
  - Added a `Manage` button to the native Prediction history card.
  - Added a checkbox-based `Manage history` dialog with `Select all`, `Clear`,
    and `Delete selected`.
  - Added a shared recent-history writer plus selected-record deletion by
    history signature.
- Artifact:
  - Created Android APK: `artifacts/android/ImperialAX-debug-history-delete.apk`.
- Verification:
  - Web `node --check src/frontend/dd-laminate/app-v2.js` passed.
  - iOS `swift test` passed in `ios/DDLaminateMVP` with 11 tests.
  - iOS `swift build` passed in `ios/ImperialAXMVP`.
  - Android `gradle :app:assembleDebug` passed with JetBrains JBR Java 17.

## 2026-06-24 - Android u3 Forecast restoration
- User noticed that Android no longer exposed u3 Forecast after the native
  Laminate history work.
- Root cause:
  - Android `LaminateActivity` still only loaded `response_models` and only
    called `/api/v1/dd-laminate/predict/response`.
  - Web and iOS had separate Response Forecast/u3 Forecast modes, but Android
    did not yet have a native mode switch.
- Android Laminate Forecast update:
  - Added a Response Forecast / u3 Forecast mode picker above the Forecast
    setup card.
  - Added u3 model constants:
    `u3_forecast_physics_v2` and `u3_forecast_goint_physics_v2`.
  - Updated model loading to parse both `response_models` and `u3_pt_models`
    from `/api/v1/dd-laminate/models`.
  - The model spinner now swaps between Response ML/DL models and u3 ML/DL
    models based on the selected mode.
  - Predict button now calls `/predict/response` for Response mode and
    `/predict/u3-forecast` for u3 mode.
  - Prediction history now stores a `kind` field and keeps Response/u3 histories
    separated. Legacy history without `kind` defaults to Response.
  - Result screen receives `EXTRA_LAMINATE_MODE`; u3 runs show `u3 Forecast`
    as the result title and request Research Insight with `scope = "u3"`.
- Artifact:
  - Created Android APK: `artifacts/android/ImperialAX-debug-u3-restored.apk`.
- Verification:
  - Android `gradle :app:assembleDebug` passed with JetBrains JBR Java 17.
  - Android `gradle :app:lintDebug` passed with JetBrains JBR Java 17.
  - `git diff --check` passed for the Android Laminate files.

## 2026-06-24 - Injection v2 workflow strip alignment
- User reported that the Injection Forecast top workflow strip
  (`01 Set DOE`, `02 Preview`, `03 Review`) looked like tabs but did not align
  with the actual input, preview, and result columns below.
- Web Injection v2 update:
  - Added shared CSS variables for the workspace column template and gap.
  - Updated `.summary-strip` and `.grid` to use the same
    `--workspace-columns` / `--workspace-gap` values.
  - Desktop now uses the same `0.95fr / 0.9fr / 1.15fr` proportions for both
    the workflow strip and the working panels.
  - Tablet layout now mirrors the lower workspace layout: first two workflow
    cards align to the first two columns and `03 Review` spans the full width,
    matching the result panel.
  - Mobile remains single-column with the workflow strip hidden.
  - Updated the CSS cache-busting query on English and Korean Injection v2
    pages.

## 2026-06-24 - Injection v2 Parametric preview restoration
- User preferred the older Injection Parametric view and asked to replace the
  current preview with that style while keeping geometry-driven updates.
- Web Injection v2 update:
  - Restored the visual-panel wording/structure to the older
    `Shape Preview` / `DOE-driven 3D preview` / `Parametric` flow.
  - Replaced the dark v2 preview card with a light `shape-preview` canvas area,
    top-right circular zoom/reset controls, and a compact DOE dimension caption.
  - Kept the current v2 element ids (`shape-visual`, `metric-*`,
    `preview-title`, `preview-copy`) so the existing app logic remains wired.
  - Updated the Three.js preview scene to use the older light background,
    orthographic camera angle, grid helper, stronger lights, and default
    oblique rotation.
  - Initially added a v2-only geometry color approximation, but the user noted
    the color direction did not match the older preview.
  - Replaced that approximation with the v1 parametric rendering approach:
    blue default plate, red gate, v1 bevel geometry, v1 gate placement, and
    v1 filling-pressure vertex coloring only when prediction/filling summary
    data is available.
  - Removed the v2-only animated flow tubes/overlay from the base parametric
    preview so the geometry preview behaves like the older version.
  - Updated English and Korean v2 pages and bumped the CSS cache key.
  - Bumped the JS cache key after restoring the v1 parametric renderer.
- Verification:
  - `node --check src/frontend/simple-injection/app-v2.js` passed.
  - `git diff --check` passed for the Injection v2 files.
  - Temporarily served `src.backend.simple_injection_app` on
    `127.0.0.1:8011` and confirmed `index-v2.html`, `index-v2.ko.html`, and
    the cache-busted `app-v2.js` were served.
  - Captured a Chrome headless screenshot. Headless Chrome fell back from
    WebGL to SVG, and the SVG fallback was fixed so the preview no longer
    appears blank when WebGL initialization fails.

## 2026-06-24 - Injection v2 DOE detail panel cleanup
- User asked to clean up the Injection DOE input area:
  - Rename `03 Process controls` to `03 Controls`.
  - Add `Process details` similar to `Geometry details`.
  - Keep `Geometry details` always open instead of a dropdown.
- Web Injection v2 update:
  - Updated English and Korean v2 pages.
  - Replaced the collapsed `<details>` Geometry section with a permanently
    visible detail card.
  - Added a permanently visible Process details card with mirror inputs for
    melt temperature, mold temperature, packing pressure, injection time, and
    packing time.
  - Kept the original compact process controls as the canonical form fields.
    Process detail mirror inputs sync into those canonical fields so prediction
    payloads remain unambiguous.
  - Bumped CSS and JS cache keys to `20260624-injection-doe-details-1`.
- Verification:
  - `node --check src/frontend/simple-injection/app-v2.js` passed.
  - `git diff --check` passed for the Injection v2 files.

## 2026-06-24 - Injection v2 detail card consolidation
- User clarified that the duplicated Process input area felt wrong and preferred
  the compact photo-style process cards shown in the screenshot.
- Web Injection v2 update:
  - Removed the separate Process mirror-input approach from the active UI flow.
  - Kept one canonical Process details card inside `03 Controls`, using the
    compact card style with label, blue readout, mini gradient bar, and right
    aligned input.
  - Converted Geometry details to the same compact card style for L, W,
    thickness, hole diameter, hole radius, gate type, gate width, and gate
    height.
  - Removed stale `data-process-detail-input` synchronization logic from
    `app-v2.js` so prediction payloads are driven by a single input per field.
  - Added geometry readout and mini-bar updates alongside the existing process
    readout updates.
  - Bumped English and Korean Injection v2 CSS/JS cache keys to
    `20260624-injection-detail-cards-2`.
- Verification:
  - `node --check src/frontend/simple-injection/app-v2.js` passed.
  - `git diff --check` passed for the Injection v2 files.
  - `rg` confirmed no `data-process-detail-input` references remain.

## 2026-06-24 - Injection v2 default DOE selection
- User asked for the Injection Forecast page to start from `G01` and `P01`.
- Web Injection v2 update:
  - Changed the bootstrap DOE defaults from `G18 / P07` to `G01 / P01`.
  - Updated the comparison Sample ID placeholder to `G01_P01`.
  - Bumped the English and Korean v2 JS cache key to
    `20260624-injection-default-g01-p01-1`.
- Verification:
  - `node --check src/frontend/simple-injection/app-v2.js` passed.
  - `git diff --check` passed for the Injection v2 files.

## 2026-06-24 - Injection app detail card parity
- User said the web Injection page looked organized and asked to apply the same
  cleanup to the apps.
- iOS Injection app update:
  - Replaced the separated Geometry/Gate/Process input blocks with two compact
    detail cards: `Process details` and `Geometry details`.
  - Kept the existing editable SwiftUI bindings and prediction payload contract.
  - Added the same card pattern as web: label, blue readout, mini range bar,
    and right-side input field.
  - Added English and Korean localizations for the new section titles.
  - Existing defaults already start from `G01 / P01`; this remains unchanged.
- Android ImperialAX/ImperialAX Injection app update:
  - Explicitly selects `G01` and `P01` after DOE catalog loading when available.
  - Replaced the flat value grid with `Process details` and `Geometry details`
    sections using compact cards, blue readouts, mini bars, and value pills.
  - Built and copied the updated debug APK to
    `artifacts/android/ImperialAX-debug-injection-detail-cards.apk`.
- Verification:
  - `swift test` in `ios/InjectionMVP` passed: 8 tests.
  - `swift build` in `ios/ImperialAXMVP` passed.
  - `JAVA_HOME=/Applications/PyCharm.app/Contents/jbr/Contents/Home gradle :app:assembleDebug`
    in `android/ImperialAXMVP` passed.
  - `git diff --check` passed for the touched app files.

## 2026-06-24 - Injection app prediction model label parity
- User pointed out that Prediction models names still differed between web and
  app.
- Canonical Injection v2 web labels are now treated as the source of truth:
  - `sprue_classical` / `filling_classical`: `Machine Learning`
  - `sprue_goint` / `filling_goint`: `Deep Learning`
  - `sprue_deeponet` / `filling_deeponet`: `Operator Learning`
- iOS Injection core now displays model names by model key first, falling back
  to cleaned labels only for unknown keys.
- Android Injection screen now does the same for both spinner labels and result
  labels, and parses `model_key` / `filling_model_key` from prediction
  responses.
- Tests were updated so old technical names such as `ExtraTrees + PCA`,
  `GointMLP NN`, and `DeepONet NN` cannot silently reappear in app display
  paths.
- Built and copied the updated Android debug APK to
  `artifacts/android/ImperialAX-debug-injection-model-label-parity.apk`.
- Verification:
  - `swift test` in `ios/InjectionMVP` passed: 8 tests.
  - `swift build` in `ios/ImperialAXMVP` passed.
  - `JAVA_HOME=/Applications/PyCharm.app/Contents/jbr/Contents/Home gradle :app:assembleDebug`
    in `android/ImperialAXMVP` passed.
  - `git diff --check` passed for the model-label app files and session memory.

## 2026-06-24 - Laminate predict flow restored to history/result page
- User clarified that the immediate result-page loading experiment should be
  cancelled and that both Android and iOS should keep the previous
  history/result-page behavior.
- Android restore:
  - The attempted Android autorun/result-page loading change was removed.
  - Android again predicts in `LaminateActivity`, saves recent-run history
    there, then opens `LaminateResultActivity` after success.
  - No replacement Android APK was kept from the cancelled autorun experiment.
- iOS restore:
  - Removed the pending `responsePending` / `u3Pending` navigation routes.
  - Removed the temporary `PredictionPendingDetailView`.
  - Removed the temporary `prepareForResponsePrediction` /
    `prepareForU3Prediction` methods.
  - iOS again waits for prediction completion, updates the existing
    latest-result/history state, and opens the normal result detail page only
    when a result exists.
- Verification:
  - `swift test` in `ios/DDLaminateMVP` passed: 11 tests.
  - `swift build` in `ios/ImperialAXMVP` passed.
  - `JAVA_HOME=/Applications/PyCharm.app/Contents/jbr/Contents/Home gradle :app:assembleDebug`
    in `android/ImperialAXMVP` passed.
  - `git diff --check` passed for the touched Laminate app files and session
    memory.

## 2026-06-24 - iOS Laminate Forecast page keeps history panel
- User clarified the intended iOS Laminate flow:
  - `Run Forecast` should still open the separate result detail page.
  - The Laminate Forecast page itself should not keep showing the latest result
    summary/curve after prediction.
  - The Forecast page result area should remain a history/empty-state panel.
- Actual iOS app entry is `DDLaminateModuleView -> ContentViewV2()`, so the
  fix was applied there.
- `ContentViewV2.resultPanel` now always renders the history/empty panel:
  - no history: `Ready for input`
  - history exists: mode-specific prediction-history cards
- Result detail navigation remains in `predict()` / `predictU3Pt()` after a
  successful prediction, using the saved `selectedDetail` route.
- Note: the previous removed code was the temporary pending/loading result
  route experiment, not the history panel itself.
- Verification:
  - `swift test` in `ios/DDLaminateMVP` passed: 11 tests.
  - `swift build` in `ios/ImperialAXMVP` passed.
  - `git diff --check` passed for `ContentViewV2.swift` and session memory.

## 2026-06-24 - iOS Injection UI aligned with Laminate
- User asked for the iOS Injection module to visually match the Laminate module
  without needing to spell out every UI detail.
- Injection app changes:
  - Added Injection language state to `AppSettings` with the same English/Korean
    toggle pattern used by Laminate.
  - Updated Injection `L10n` to load the selected language bundle from
    `kyulai.injection.languageCode`.
  - Moved language and API actions to the top-right toolbar:
    globe language toggle plus link/API settings button.
  - Reworked the Injection header into a Laminate-style card with a compact API
    connection badge.
  - Added a compact three-step workflow strip: Set DOE, Preview, Review.
  - Replaced the always-visible API connection card with a warning card only
    when the connection/model state needs attention.
  - Adjusted Injection theme colors, card border, shadow, and typography toward
    the Laminate V2 style.
  - Fixed the Injection SwiftUI preview to inject required environment objects.
- Verification:
  - `swift test` in `ios/InjectionMVP` passed: 8 tests.
  - `swift build` in `ios/ImperialAXMVP` passed.
  - XcodeBuildMCP built and launched `ImperialAXMVPHost` on the iPhone 17
    simulator.
  - Simulator screenshot reached the ImperialAX workspace/login flow; direct
    Injection screen navigation was limited by the current UI automation
    scroll gesture failing in this simulator environment.

## 2026-06-26 - DD Laminate research-purpose brief added
- User pointed to `data/PPT/Final ver2.pptx` and asked to expose the Laminate/u3
  research motivation in the web/app so an external URL can explain the model.
- PPT context captured for UI copy:
  - Double-Double laminates are being explored as lighter, angle-driven
    alternatives to quasi-isotropic layups for impact and post-impact
    compression behavior.
  - The model screens are meant to screen Case and theta candidates before
    deeper analysis by estimating Type, transition load Pt, response curve, and
    u3 behavior.
  - Current study signals from the PPT: best DD candidates improved Pt by
    28.93% and u3 metric by 31.31% versus quasi-isotropic baselines.
- Web changes:
  - Added a compact `Research purpose` section to
    `src/frontend/dd-laminate/index-v2.html` and Korean equivalent in
    `index-v2.ko.html`.
  - Added responsive `.research-brief` styling in `styles-v2.css`; desktop uses
    a two-column brief, mobile keeps the three purpose points in a horizontal
    scroll row to avoid taking too much vertical space.
  - Bumped the CSS cache query to `20260626-research-brief`.
- App changes:
  - Added the same research-purpose card to the active iOS DD module
    `ContentViewV2`.
  - Added the same research-purpose card to Android
    `android/ImperialAXMVP/.../LaminateActivity.kt`.
- Design note:
  - Refreshed `DESIGN.md` to record the DD Laminate research-purpose brief as a
    supported top-of-screen context component.
- Verification:
  - `git diff --check` passed for the touched web/app/design files.
  - `swift test` in `ios/DDLaminateMVP` passed: 11 tests.
  - `JAVA_HOME=/Applications/PyCharm.app/Contents/jbr/Contents/Home gradle :app:assembleDebug`
    in `android/ImperialAXMVP` passed.
  - Local web render check passed for English and Korean pages; mobile width
    390px showed no page-level horizontal overflow.

## 2026-06-26 - Korean line-breaking cleanup for DD Laminate
- User asked to prevent awkward Korean word/syllable clipping after adding the
  research-purpose content.
- Web changes:
  - Korean DD Laminate page now applies `word-break: keep-all`,
    `overflow-wrap: break-word`, `line-break: strict`, and disables hyphenation
    for normal Korean text.
  - Korean one-line ellipsis areas for prediction history model names and XAI
    feature labels now allow wrapping instead of clipping mid-word.
  - CSS cache query was bumped to `20260626-ko-wrap`.
- Android change:
  - Base `label()` TextView helper now uses high-quality line breaking and
    disables hyphenation on supported Android versions.
- Verification:
  - `git diff --check` passed for the touched files.
  - Android `gradle :app:assembleDebug` passed.
  - Korean web page at 390px viewport showed `word-break: keep-all` on the
    research text and no page-level horizontal overflow.

## 2026-06-26 - DD Laminate top title kept on one line
- User asked for the very top Laminate name to fit on one line in both English
  and Korean.
- Web changes:
  - `ImperialAX Laminate Forecast` and `ImperialAX 적층 예측` now render as one-line `h1`
    text by removing the block-style span behavior.
  - Web title sizing now uses a smaller responsive clamp and `white-space:
    nowrap`.
  - CSS cache query was bumped to `20260626-title-nowrap`.
- App changes:
  - iOS DD active screen `ContentViewV2` and legacy `ContentView` now use
    `ImperialAX Laminate Forecast` / `ImperialAX 적층 예측` without embedded newlines.
  - Legacy ImperialAX Laminate SwiftUI screen also uses a one-line title.
  - Android ImperialAX Laminate screen now uses `ImperialAX Laminate Forecast` without
    embedded newline and a smaller one-line title size.
- Verification:
  - `git diff --check` passed for the touched files.
  - `swift test` in `ios/DDLaminateMVP` passed: 11 tests.
  - `swift build` in `ios/ImperialAXMVP` passed.
  - Android `gradle :app:assembleDebug` passed.
  - Web English/Korean pages at 320px and 390px rendered the top title as one
    line with no page-level horizontal overflow.

## 2026-06-26 - Composite RAG online source collection pipeline
- User asked to start applying RAG and asked whether online composite-material
  references can be added beyond internal PPT/PDF/model documents.
- Decision:
  - Start with a conservative online source collection pipeline before adding
    an LLM endpoint.
  - Use an allowlist and source metadata so RAG content remains traceable and
    rights-aware.
  - Keep paywalled/rights-managed journal pages as metadata-only unless access
    rights are confirmed.
- Added:
  - `data/rag/online_sources.seed.json`: curated seed list for Double-Double,
    laminate mechanics, NASA/FAA/CMH-17, and university publication pages.
  - `data/rag/README.md`: run instructions and policy notes.
  - `src/data/rag/sources.py`: `RagSource`, allowed-domain validation, catalog
    loading.
  - `src/data/rag/collector.py`: online fetch, HTML/PDF text extraction,
    chunking, raw/text/chunk artifact writing, collection manifest writing.
  - `scripts/rag_collect_online_sources.py`: CLI collector with
    `--metadata-only`, `--limit`, `--allow-domain`, and `--fail-on-error`.
  - `tests/unit/test_rag_online_collection.py`: allowlist, metadata-only,
    fake HTML collection, blocked-domain, and chunking tests.
- Collection result from `python scripts/rag_collect_online_sources.py`:
  - 9 seed sources evaluated.
  - 6 collected with text/chunks.
  - 1 metadata-only: AIAA Tsai Double-Double DOI/landing page.
  - 2 fetch errors: FAA PDF URLs returned HTTP 403 and should be handled by
    alternate URLs or manual source attachment if needed.
  - Generated artifacts under `data/rag/online_corpus/`, including raw files,
    extracted text, JSONL chunks, and `collection_manifest.json`.
- Verification:
  - `python -m pytest tests/unit/test_rag_online_collection.py` passed: 5 tests.
  - `python scripts/rag_collect_online_sources.py --metadata-only --limit 4`
    wrote a manifest successfully.
  - `python scripts/rag_collect_online_sources.py` wrote a full manifest and
    collected 6 downloadable sources.

## 2026-06-26 - Composite RAG local knowledge index and API
- User asked to proceed to the next RAG step.
- Added:
  - `src/data/rag/indexer.py`: merges online JSONL chunks with internal
    DD/Composite materials, extracts PPT/PDF/Markdown text, chunks content, and
    builds a deterministic local TF-IDF style sparse-vector index.
  - `scripts/rag_build_knowledge_index.py`: builds
    `data/rag/knowledge_index.json`.
  - `scripts/rag_query_index.py`: command-line retrieval smoke-test tool.
  - `src/backend/api/v1/rag.py`: `GET /api/v1/rag/search`.
  - Registered the RAG router in both the aggregate API router and the
    standalone DD Laminate app.
  - `tests/unit/test_rag_knowledge_index.py` and `tests/backend/test_rag_api.py`.
- Built index result:
  - `python scripts/rag_build_knowledge_index.py`
  - Output: `data/rag/knowledge_index.json`
  - 229 chunks from 54 sources.
  - Index size was about 1.3 MB.
- Retrieval smoke tests:
  - `Double-Double laminate purpose theta Pt` returned internal DD Laminate
    summary / paper chunks.
  - `A12 membrane coupling physics XAI feature` returned Laminate Forecast
    Physics XAI reports.
  - `u3 forecast Pt model` returned u3 forecast training reports.
- Verification:
  - `.venv/bin/python -m pytest tests/unit/test_rag_online_collection.py
    tests/unit/test_rag_knowledge_index.py tests/backend/test_rag_api.py`
    passed: 10 tests.
  - `.venv/bin/python` TestClient call to `/api/v1/rag/search` returned HTTP
    200 and ranked RAG results.
  - `python -m compileall src/data/rag src/backend/api/v1/rag.py
    scripts/rag_build_knowledge_index.py scripts/rag_query_index.py` passed.

## 2026-06-26 - Composite RAG answer endpoint and web panel
- User asked to try the LLM/RAG assistant.
- Added:
  - `src/data/rag/answer.py`: grounded answer layer over the local RAG index.
    It retrieves top chunks, builds citations, and either calls OpenAI
    Responses API or falls back to a local extractive answer.
  - `scripts/rag_answer.py`: CLI for asking the Composite RAG assistant.
  - `POST /api/v1/rag/answer` in `src/backend/api/v1/rag.py`.
  - Web panel in `src/frontend/dd-laminate/index-v2.html` and Korean version:
    `Composite AI Assistant` / `복합재 AI Assistant`.
  - `app-v2.js` now posts to `/api/v1/rag/answer` and renders the grounded
    answer plus citations using safe DOM text nodes.
  - `styles-v2.css` now styles the assistant card, answer body, provider badge,
    and citation cards.
  - Tests: `tests/unit/test_rag_answer.py`; backend RAG API test now covers
    `/rag/answer`.
- Runtime behavior:
  - If `OPENAI_API_KEY` is set, `answer_query()` calls
    `https://api.openai.com/v1/responses` with `store: false`.
  - `OPENAI_RAG_MODEL` can override the default model; default is
    `gpt-5.4-mini`.
  - If no key is set or the OpenAI call fails, the endpoint returns a local
    citation-backed extractive answer.
- Verification:
  - `.venv/bin/python -m pytest tests/unit/test_rag_online_collection.py
    tests/unit/test_rag_knowledge_index.py tests/unit/test_rag_answer.py
    tests/backend/test_rag_api.py` passed: 15 tests.
  - `node --check src/frontend/dd-laminate/app-v2.js` passed.
  - `python -m compileall src/data/rag src/backend/api/v1/rag.py
    scripts/rag_answer.py scripts/rag_build_knowledge_index.py
    scripts/rag_query_index.py` passed.
  - Restarted DD server on port 8000; `/ready` returned ready and
    `POST /api/v1/rag/answer` returned HTTP 200 with citations.
  - HTML checks confirmed the English and Korean assistant panels are served.

## 2026-06-26 - RAG assistant default question UX
- User wanted one basic Composite AI question to be shown by default, while
  clearing automatically when the user starts typing.
- Updated DD Laminate English/Korean RAG panels:
  - The question textarea now contains a real default question, so pressing
    submit immediately asks it.
  - The default text is stored as `data-default-query`.
  - `app-v2.js` clears the default question on first focus or first input only
    when the current value still matches the default.
  - Bumped web asset query strings to `20260626-rag-default-question`.

## 2026-06-26 - RAG local answer feature explanations
- User reported that asking `D11 굽힘 강성이 왜 중요한가요?` showed only
  citation/source-like content without a useful answer.
- Root cause:
  - The RAG API returned a valid response, but the local fallback answer only
    summarized retrieved evidence and did not synthesize domain explanations.
  - OpenAI LLM synthesis is optional and depends on `OPENAI_API_KEY`, so the
    local fallback needs to be useful by itself.
- Fix:
  - Added a small physics-feature glossary to `src/data/rag/answer.py` for
    CLT/ABD terms such as `D11`, `D22`, `D12`, `D66`, `A11`, `A22`, `A12`,
    `A66`, and B-matrix coupling terms.
  - `build_extractive_answer()` now detects feature names in the user query and
    places a concise explanation before the citation list.
  - Added unit tests for Korean `D11` explanation and English `A12 membrane
    coupling` detection.
- Verification:
  - `.venv/bin/python -m pytest tests/unit/test_rag_answer.py
    tests/backend/test_rag_api.py` passed: 8 tests.
  - `python -m compileall src/data/rag/answer.py src/backend/api/v1/rag.py`
    passed.
  - Restarted DD server on port 8000.
  - Public `https://laminate.imperialax.com/api/v1/rag/answer` now returns a
    Korean D11 explanation before citations.

## 2026-06-26 - RAG citation toggle and LLM setup note
- User reported that RAG citations take too much space and asked to make them
  accessible from a compact top-right control, similar to the language toggle.
- Updated DD Laminate RAG UI:
  - `renderRagAnswer()` now renders a `근거 보기` / `Show citations` button in
    the answer header.
  - Citation cards are hidden by default and can be toggled with the button.
  - Added matching styles for the compact citation toggle.
  - Bumped DD v2 asset query strings to `20260626-rag-citation-toggle`.
- Updated local fallback answer text:
  - It now keeps the answer body focused on the explanation.
  - Citation snippets are no longer duplicated inside the answer body; they stay
    in the API `citations` array and UI citation panel.
- Added `data/rag/README.md` note for enabling LLM synthesis:
  - Set `OPENAI_API_KEY`.
  - Optionally set `OPENAI_RAG_MODEL`.
  - Start the DD server with those environment variables.

## 2026-06-26 - OpenAI RAG key local env setup
- User asked where to enter the OpenAI API key and asked Codex to prepare the
  setup.
- Implemented:
  - `scripts/run_public_ai_server.sh` now loads `.env.local` before starting
    `src.backend.dd_laminate_app:app`.
  - The script reports whether `OPENAI_API_KEY` is configured by length only,
    never by printing the key value.
  - `.env.windows.example` now documents optional `OPENAI_API_KEY` and
    `OPENAI_RAG_MODEL` for Windows/server migration.
  - Created local-only `.env.local` template with `OPENAI_RAG_MODEL=gpt-5.4-mini`
    and a commented `OPENAI_API_KEY` placeholder.
- Safety:
  - `.env.local` is already ignored by `.gitignore`.
  - Verified with `git check-ignore -v .env.local`.
  - Did not paste or expose any actual OpenAI API key in chat or command output.
- User action remaining:
  - Create an API key from `https://platform.openai.com/api-keys`.
  - Put it in `.env.local` as `OPENAI_API_KEY=...`.
  - Restart the DD server using `scripts/run_public_ai_server.sh`.

## 2026-06-26 - OpenAI RAG enabled on public DD server
- User added `OPENAI_API_KEY` to `.env.local`.
- Verified without printing the secret:
  - `OPENAI_API_KEY configured`.
  - `.env.local` remains ignored by git.
- Restarted the DD public server with:
  - `scripts/run_public_ai_server.sh`
  - This loads `.env.local` before starting uvicorn.
- Verification:
  - `GET http://127.0.0.1:8000/ready` returned ready.
  - Local `POST /api/v1/rag/answer` with `use_llm: true` returned:
    - `provider: openai`
    - `model: gpt-5.4-mini`
    - `used_llm: true`
  - Public `https://laminate.imperialax.com/api/v1/rag/answer` returned the same
    OpenAI provider fields.
- Safety:
  - Did not print or store the actual key in logs, docs, or git-tracked files.

## 2026-06-26 - RAG answer style cleanup
- User reported that OpenAI RAG answers still looked too machine-written:
  - LaTeX-like terms such as `\(A_{12}\)`.
  - Markdown markers such as `**bold**`.
  - Sentences not flowing naturally enough.
- Updated:
  - `src/data/rag/answer.py`
    - OpenAI instructions now request natural connected prose, no Markdown,
      no LaTeX notation, and plain engineering terms like `A12` and `D11`.
    - Added `clean_answer_text()` to normalize returned answers:
      - removes inline LaTeX wrappers,
      - converts subscript notation such as `A_{12}` and `D_{11}` to `A12`
        and `D11`,
      - removes Markdown bold markers, headings, and list prefixes,
      - replaces internal phrasing like `Retrieved context` with more natural
        wording.
  - `src/backend/api/v1/rag.py`
    - Applies `clean_answer_text()` right before API response serialization as
      a final guard.
  - `tests/unit/test_rag_answer.py`
    - Added coverage for Markdown/LaTeX cleanup and internal phrase removal.
- Verification:
  - `.venv/bin/python -m pytest tests/unit/test_rag_answer.py
    tests/backend/test_rag_api.py` passed: 9 tests.
  - `python -m compileall src/data/rag/answer.py src/backend/api/v1/rag.py`
    passed.
  - Restarted DD public server.
  - Public OpenAI RAG check for `A12 membrane coupling이 왜 중요한가요?`
    returned:
    - `provider: openai`
    - no `**`
    - no `\(` / `\)`
    - no subscript notation like `_12`
    - no `Retrieved context`

## 2026-06-26 - DD XAI local occlusion sensitivity
- User asked whether SHAP/occlusion results and value-change sensitivity
  analysis can be added for each feature.
- Decision:
  - Do not add a new SHAP dependency yet.
  - First expose a robust SHAP-like local occlusion sensitivity already
    compatible with the current Tree and GointMLP-style DD models.
  - Keep global feature importance, but recompute the strongest global feature
    candidates for the current `theta1`, `theta2`, and `case` input by masking
    one feature at a time.
- Backend update:
  - `src/backend/api/v1/dd_laminate.py`
    - Added `local_sensitivity`, `local_value`, and `perturbation` fields to
      `XAIFeature`.
    - Added `_local_xai_analysis()` to return normalized local score, raw
      output-change sensitivity, current feature value, and masked value.
    - `/api/v1/dd-laminate/xai/local` now returns the new fields for local XAI
      explanations for both Laminate Forecast and u3 Forecast models.
    - Method text now reports `live local feature masking` once.
- Frontend update:
  - `src/frontend/dd-laminate/app-v2.js`
    - XAI feature rows now show compact `Current`, `Sensitivity`, and
      `Perturbation` details when available.
    - Korean UI labels use `현재값`, `민감도`, and `변화 조건`.
    - Korean perturbation text changes `masked to ...` into `마스킹 값 ...`.
  - `src/frontend/dd-laminate/styles-v2.css`
    - Added compact styling for the local sensitivity line.
  - `index-v2.html` and `index-v2.ko.html`
    - Cache-busted JS/CSS to `20260626-xai-sensitivity`.
- Verification:
  - `.venv/bin/python -m compileall src/backend/api/v1/dd_laminate.py` passed.
  - `node --check src/frontend/dd-laminate/app-v2.js` passed.
  - `.venv/bin/python -m pytest tests/unit/test_rag_answer.py
    tests/backend/test_rag_api.py -q` passed: 9 tests.
  - Restarted DD public server and `GET /ready` returned all DD models ready.
  - Public HTML includes `20260626-xai-sensitivity`.
  - Public XAI API returned local fields:
    - Laminate example top feature `d11` with `local_sensitivity`,
      `local_value`, and `perturbation`.
    - u3 example top feature `angle_min_abs` with `local_sensitivity`,
      `local_value`, and `perturbation`.
- Known note:
  - Earlier broad iOS contract tests still have unrelated legacy page
    expectation failures around `index.html` redirect behavior. This XAI
    change did not edit that legacy contract.

## 2026-06-26 - DD XAI perturbation label cleanup
- User asked what `마스킹 값 0` means and requested clearer wording.
- Updated `src/frontend/dd-laminate/app-v2.js`:
  - Korean label changed from `변화 조건: 마스킹 값 0` to
    `가상 제거: 0으로 대체`.
  - English label changed from `Perturbation: masked to 0` to
    `Virtual removal: replaced with 0`.
- Updated DD v2 HTML cache busting to `20260626-xai-sensitivity-label`.
- Verification:
  - `node --check src/frontend/dd-laminate/app-v2.js` passed.
  - `git diff --check` passed for the edited DD frontend files.
  - Public Korean and English DD v2 pages include the new cache-busted asset
    version.

## 2026-06-26 - DD RAG Assistant linked to active prediction context
- User asked whether the AI Assistant can read the current prediction result
  and explain quantitative feature contribution, rather than only answering
  from static RAG documents.
- Finding:
  - Before this change, the Assistant only sent `query`, `top_k`, `use_llm`,
    and `language` to `/api/v1/rag/answer`.
  - The frontend already stored the latest prediction in `latestPredictionData`,
    but it was not included in the RAG request.
  - Therefore questions like `A12 membrane coupling이 정량적으로 얼마나
    기여했나요?` correctly received cautious answers saying the quantitative
    contribution was hard to judge.
- Backend update:
  - `src/backend/api/v1/rag.py`
    - `RagAnswerRequest` now accepts optional `prediction_context`.
  - `src/data/rag/answer.py`
    - `answer_query()` and `call_openai_responses()` now accept the active
      prediction context.
    - Added `compact_prediction_context()` to pass only concise app-result
      fields to the LLM: mode, inputs, model, Type/confidence, Pt/max values,
      XAI method, feature set, and top local XAI features.
    - Prompt now instructs the assistant to use this as the active app result,
      and to distinguish current-model XAI numbers from general laminate
      theory.
    - Cleanup normalizes joined terms such as `localsensitivity` and
      `virtualremoval`.
- Frontend update:
  - `src/frontend/dd-laminate/app-v2.js`
    - Added `ensurePredictionXaiForAssistant()` to fetch `/xai/local` before
      asking RAG if the current prediction does not yet have XAI attached.
    - Added `buildAssistantPredictionContext()` to send a compact version of
      `latestPredictionData` and top XAI features with Assistant questions.
  - DD v2 asset cache bumped to `20260626-rag-prediction-context`.
- Behavior:
  - If the user asks before running a prediction, Assistant still answers from
    references and should say quantitative contribution needs a prediction/XAI
    result.
  - If the user asks after Laminate Forecast or u3 Forecast, Assistant receives
    the current prediction and can mention supplied importance/local
    sensitivity values.
- Verification:
  - `.venv/bin/python -m pytest tests/unit/test_rag_answer.py
    tests/backend/test_rag_api.py -q` passed: 9 tests.
  - `python -m compileall src/backend/api/v1/rag.py src/data/rag/answer.py`
    passed.
  - `node --check src/frontend/dd-laminate/app-v2.js` passed.
  - Restarted DD public server and `/ready` returned all DD models ready.
  - Public Korean DD page includes `20260626-rag-prediction-context`.
  - Manual RAG API check with a supplied prediction context returned an OpenAI
    answer that referenced the current A12 importance/local sensitivity values.

## 2026-06-26 - RAG Assistant enriched with current laminate physics context
- User reported that after `theta1=30`, `theta2=-30`, `Case2`, the Assistant
  correctly identified D11 as influential but still ended by saying the D11
  formula, stacking sequence, and actual response data were needed.
- Investigation:
  - D11 formula and CLT calculation already exist in
    `src/ml/dd_laminate/laminate_physics.py`.
  - Case stack expansion already exists:
    - Case2 = `[[±theta1]/[±theta2]]4`.
    - For `theta1=30`, `theta2=-30`, Case2 expands to
      `[30, -30, -30, 30]` repeated four times, 16 plies total.
  - Material constants already exist in code:
    - `E11=21.5 Msi`, `E22=1.23 Msi`, `nu12=0.329`, `G12=0.571 Msi`,
      `ply_thickness=0.0075 in`.
  - For the exact input, there is no exact matching Abaqus CSV in the curated
    Case2 dataset; the app result is a surrogate forecast unless a source CSV
    is explicitly attached.
- Backend update:
  - `src/data/rag/answer.py`
    - `compact_prediction_context()` now appends current laminate physics
      context when `theta1`, `theta2`, and `case` are present.
    - It includes stack formula, expanded stack, D11 calculation basis,
      material/thickness constants, computed raw D11, normalized d11,
      d22, d11/d22, and bending anisotropy.
    - It explicitly tells the Assistant that the current app result is a
      surrogate forecast, not an exact Abaqus result, unless source CSV/test
      metadata is attached.
    - Answer cleanup now normalizes `currentvalue` and `masked to 0`.
- Current computed values for `theta1=30`, `theta2=-30`, `Case2`:
  - total thickness = `0.12 in`
  - raw D11 = `0.00184715`
  - normalized d11 = `1.06895`
  - d22 = `0.219105`
  - d11/d22 = `4.87872`
  - bending anisotropy = `0.65979`
- Verification:
  - Added unit coverage in `tests/unit/test_rag_answer.py`.
  - `.venv/bin/python -m pytest tests/unit/test_rag_answer.py
    tests/backend/test_rag_api.py -q` passed: 10 tests.
  - `python -m compileall src/data/rag/answer.py` passed.
  - Restarted DD public server and `/ready` returned all DD models ready.
  - Manual RAG API check with the D11 question now returns an answer that
    includes D11 formula context, expanded interpretation, and current computed
    D11/d11 values.

## 2026-06-26 - DD Case formula notation synced across UI and Assistant
- User reported that Assistant sometimes writes Case formulas with `theta1`
  and `theta2`, while the app UI uses Greek symbols and subscripts.
- Updated:
  - `src/data/rag/answer.py`
    - Assistant prediction context now uses the same formula notation as the
      app:
      - Case2: `[[±θ₁]/[±θ₂]]₄`
      - Case3: `[[±θ₁]/[±θ₂]/[∓θ₁]/[∓θ₂]]₂`
      - Case4: `[([±θ₁]/[±θ₂])₂ / ([∓θ₁]/[∓θ₂])₂]`
    - OpenAI instruction now allows app-style `θ₁` and `θ₂` in laminate case
      formulas while still avoiding LaTeX notation.
  - `src/frontend/dd-laminate/app-v2.js`
    - Dynamic stack preview formulas now use the same symbols.
  - `src/frontend/dd-laminate/index-v2.html` and `index-v2.ko.html`
    - Dynamic preview default text now uses `[[±θ₁]/[±θ₂]]₄`.
    - Asset cache bumped to `20260626-case-formula-symbols`.
- Verification:
  - `.venv/bin/python -m pytest tests/unit/test_rag_answer.py
    tests/backend/test_rag_api.py -q` passed: 10 tests.
  - `python -m compileall src/data/rag/answer.py src/backend/api/v1/rag.py`
    passed.
  - `node --check src/frontend/dd-laminate/app-v2.js` passed.
  - Restarted public DD server; `/ready` returned all DD models ready.
  - Public Korean page contains the new asset version and formula text.
  - `compact_prediction_context()` now emits
    `Laminate stack formula: Case2 = [[±θ₁]/[±θ₂]]₄.`

## 2026-06-26 - RAG Assistant enriched with Type definitions and Pt distribution
- User reported that Assistant still ended XAI explanations with
  `타입 정의와 타깃 분포 정보가 추가로 있어야 더 정확히 설명할 수 있습니다`,
  even though this project already has those definitions/data.
- Investigation:
  - Type definitions are in `docs/DD_Laminate_PPT_Basis.md`.
  - The curated Case2/3/4 response manifest is
    `data/datasets/DD_cases_2_3_4_curated_v1/label_manifest.csv`.
  - For the current example `theta1=30`, `theta2=-30`, `Case2`,
    predicted Pt 17163.21 sits around the Case2 median region.
- Backend update:
  - `src/data/rag/answer.py`
    - Added project Type definitions to the prediction context:
      - Type 1: clean bilinear response; Pt from two fitted line intersection.
      - Type 2: initial branch linear, post-transition branch curved; u3 helps
        define Pt.
      - Type 3: heavy post-transition curvature; force bilinear fitting is
        unreliable, Pt mainly from u3.
    - Added cached target-distribution summary from the curated manifest:
      - Case2: 300 samples; Type1=108, Type2=145, Type3=47.
      - Case3/Case4 are also available from the same manifest.
    - Added Case-specific Pt min/median/max and current predicted Pt percentile.
    - Prompt now says if Type definitions/target distributions are present,
      use them and do not claim they are missing.
    - Cleanup normalizes feature names such as `bendinganisotropy` and
      `d11_d22_ratio`.
- Current example context now includes:
  - Case2 Type distribution: Type1=36.0%, Type2=48.3%, Type3=15.7%.
  - Case2 Pt distribution: min=4911.51, median=17391.04, max=34578.32.
  - Current predicted Pt percentile within Case2: 48.3%.
  - Current predicted Type meaning: Type 2 post-transition curved response.
- Verification:
  - Added/updated unit coverage in `tests/unit/test_rag_answer.py`.
  - `.venv/bin/python -m pytest tests/unit/test_rag_answer.py
    tests/backend/test_rag_api.py -q` passed: 10 tests.
  - `python -m compileall src/data/rag/answer.py` passed.
  - Restarted DD public server and `/ready` returned all DD models ready.
  - Manual RAG API check no longer contains the missing-info phrase and now
    explains Type 2 plus Case2 Pt percentile.

## 2026-06-26 - Simple Injection XAI added
- User asked whether Injection already had XAI like DD Laminate, then requested
  the XAI pattern be ported while keeping Injection-specific feature meaning.
- Investigation:
  - Injection did not previously have an XAI API/response/UI.
  - Existing Simple Injection models share 23 input features:
    base geometry/process values, gate one-hot features, and derived flow
    descriptors such as area, net area, gate area, flow length/thickness, and
    process total time.
- Backend update:
  - `src/backend/api/v1/simple_injection.py`
    - Added `InjectionXAIFeature` and `InjectionXAIExplanation`.
    - `SpruePressurePredictionResponse` now includes optional `xai`.
    - Added local perturbation/occlusion sensitivity for selected Sprue and
      Filling models together.
    - Supports `sprue_classical`, `sprue_goint`, `sprue_deeponet`,
      `filling_classical`, `filling_goint`, and `filling_deeponet`.
    - XAI categories are Injection-specific: geometry, process, gate, derived,
      and other.
- Frontend update:
  - `src/frontend/simple-injection/index-v2.html`
  - `src/frontend/simple-injection/index-v2.ko.html`
  - `src/frontend/simple-injection/app-v2.js`
  - `src/frontend/simple-injection/styles-v2.css`
  - Added compact “Prediction Drivers” / “예측 영향 인자” card.
  - Displays top 10 local feature drivers as percentages with current value,
    local sensitivity, perturbation condition, category, and explanation.
- Verification:
  - `python -m compileall src/backend/api/v1/simple_injection.py` passed.
  - `node --check src/frontend/simple-injection/app-v2.js` passed.
  - `.venv/bin/python -m pytest tests/backend/test_simple_injection_model_labels.py -q`
    passed: 2 tests.
  - Direct G01/P01 prediction call returned `xai` with 23 features; top sample
    features included `melt_temp_C`, `process_total_time_s`, and
    `flow_length_to_thickness`.

## 2026-06-26 - Injection default route fixed to v2
- User noticed Injection opened as the old/classic UI after the XAI update.
- Root cause:
  - `src/backend/simple_injection_app.py` mounted the static frontend at `/`,
    so `/` and `/index.html` still served `src/frontend/simple-injection/index.html`
    in some paths.
  - `index-v2.html` existed and worked, but the default URL was not guaranteed
    to serve v2.
  - `styles-v2.css` cache query was also still on an older version string.
- Fix:
  - `src/backend/simple_injection_app.py`
    - `/`, `/index.html`, `/index.ko.html`, `/index-v2.html`,
      `/index-v2.ko.html`, `/styles-v2.css`, and `/app-v2.js` now serve v2
      assets with no-cache headers.
    - Legacy `/simple-injection*` redirects remain pointed to v2.
  - `src/frontend/simple-injection/index-v2.html` and `.ko.html`
    - CSS cache version bumped to `20260626-injection-xai-1`.
- Verification:
  - `python -m compileall src/backend/simple_injection_app.py` passed.
  - `node --check src/frontend/simple-injection/app-v2.js` passed.
  - Restarted the Injection server on port 8010.
  - `https://injection.imperialax.com/` now returns v2 markers and the updated
    `styles-v2.css?v=20260626-injection-xai-1`.

## 2026-06-26 - Injection Korean XAI copy and header cleanup
- User reported that the Korean Injection page still showed XAI interpretation
  text in English and asked to remove the top-right `Flow` and `Classic` links.
- Frontend update:
  - `src/frontend/simple-injection/app-v2.js`
    - Added Korean XAI feature label/explanation mapping for Injection-specific
      features such as melt temperature, mold temperature, gate area,
      flow-length/thickness, total process time, and gate type one-hot features.
    - Korean page now translates XAI summary, method label, perturbation text,
      feature labels, feature explanations, and method notes.
  - `src/frontend/simple-injection/index-v2.html`
  - `src/frontend/simple-injection/index-v2.ko.html`
    - Removed `Flow` and `Classic` links from the top-right action group.
    - Bumped JS/CSS cache keys to `20260626-injection-xai-ko-1`.
    - Korean workflow copy now says `게이트, 홀, 유동 경로`.
  - `src/frontend/simple-injection/styles-v2.css`
    - Adjusted mobile top-action grid for the reduced link count.
- Verification:
  - `node --check src/frontend/simple-injection/app-v2.js` passed.
  - Public Korean Injection HTML contains the new asset version and no
    top-right `Flow`/`Classic` links.
  - Public `app-v2.js` contains the Korean XAI mapping, including `수지 온도`
    and `형상 + 공정 + 게이트 + 파생 유동 descriptor`.

## 2026-06-26 - Injection RAG/LLM assistant added
- User asked to add the same kind of LLM assistant used in Laminate to the
  Injection app, adapted to Injection-specific inputs and XAI.
- Backend update:
  - `src/backend/simple_injection_app.py`
    - Mounted the shared RAG router under `/api/v1/rag` for Injection serving.
  - `src/data/rag/answer.py`
    - Extended prediction-context compaction for Injection geometry/process/gate
      fields and Sprue/Filling outputs.
    - Added Injection-aware fallback explanations so local RAG answers no longer
      mention DD Laminate when the current context is Injection.
    - Added safe `.env.local` loading for `OPENAI_API_KEY` and
      `OPENAI_RAG_MODEL` during direct uvicorn launches.
    - Updated the OpenAI prompt to handle both Double-Double laminate AI and
      Moldex3D Injection AI.
- Frontend update:
  - `src/frontend/simple-injection/index-v2.html`
  - `src/frontend/simple-injection/index-v2.ko.html`
  - `src/frontend/simple-injection/app-v2.js`
  - `src/frontend/simple-injection/styles-v2.css`
  - Added “Injection AI Assistant” / “Injection 지식베이스에 질문하기” card.
  - The assistant sends the latest prediction result, Injection inputs, Sprue
    and Filling outputs, and top XAI feature drivers into the RAG answer API.
  - Citations are hidden behind a compact toggle like the Laminate assistant.
- Tests and verification:
  - `python -m compileall src/backend/simple_injection_app.py src/data/rag/answer.py`
    passed.
  - `node --check src/frontend/simple-injection/app-v2.js` passed.
  - `.venv/bin/python -m pytest tests/unit/test_rag_answer.py tests/backend/test_rag_api.py tests/backend/test_simple_injection_model_labels.py -q`
    passed: 14 tests.
  - Restarted the Injection server on port 8010.
  - Local `/ready` reports all six Sprue/Filling models as `ok`.
  - Local RAG smoke with `use_llm=true` returned provider `openai`,
    model `gpt-5.4-mini`, and `used_llm=true`.
  - Public Injection page includes the new RAG asset version
    `20260626-injection-rag-1`.

## 2026-06-26 - Injection assistant uses XAI context even when retrieval is empty
- User found that asking “왜 수지 온도가 가장 큰 영향력을 주는 것 같아?”
  after an XAI result with melt temperature at 25.6% returned
  “관련 근거를 찾지 못했습니다.”
- Root cause:
  - `answer_query()` returned early when RAG retrieval had zero citations.
  - That early return happened before the assistant used the active prediction
    and XAI context sent from the Injection UI.
- Fix:
  - `src/data/rag/answer.py`
    - If retrieval is empty but current prediction context contains Injection
      XAI details, the API now returns a context-grounded local answer instead
      of the generic “no evidence” message.
    - Response model label for this path is `local-prediction-context`.
  - `tests/unit/test_rag_answer.py`
    - Added regression coverage for empty retrieval plus Injection XAI context.
- Verification:
  - `python -m compileall src/data/rag/answer.py` passed.
  - `.venv/bin/python -m pytest tests/unit/test_rag_answer.py tests/backend/test_rag_api.py -q`
    passed: 13 tests.
  - Restarted Injection server on port 8010.
  - Smoke test with the exact Korean question and XAI `importance=0.256`
    returned an answer containing `수지 온도` and `25.6%`, with no generic
    “관련 근거를 찾지 못했습니다” message.

## 2026-06-26 - Injection assistant follows the feature named in the question
- User noticed that asking about `보압 시간` still produced essentially the
  same answer as asking about `수지 온도`.
- Root cause:
  - Injection local fallback explanation always described the first XAI feature
    in `top_features`.
  - It did not inspect the user's question to find the requested feature name.
  - The frontend sent only the first 8 XAI features into the assistant context,
    so lower-ranked requested features could be unavailable.
- Fix:
  - `src/data/rag/answer.py`
    - Added Injection feature alias matching for Korean/English terms such as
      `수지 온도`, `보압`, `보압 시간`, `melt temperature`, and `packing time`.
    - Longer/more specific aliases win, so `보압 시간` no longer gets confused
      with `보압`.
    - If the requested feature appears in the XAI list, the assistant explains
      that feature's own rank, importance, local sensitivity, current value, and
      perturbation instead of repeating the strongest overall driver.
    - If the requested feature is missing, the assistant now says it is missing
      from the transmitted XAI list rather than pretending the top feature
      answers the question.
    - Increased compact prediction context XAI limit from 6 to 24 features.
  - `src/frontend/simple-injection/app-v2.js`
    - Assistant context now sends the full `xai.top_features` array instead of
      slicing to the first 8.
  - `src/frontend/simple-injection/index-v2.html`
  - `src/frontend/simple-injection/index-v2.ko.html`
    - Bumped asset cache version to `20260626-injection-rag-2`.
- Verification:
  - `node --check src/frontend/simple-injection/app-v2.js` passed.
  - `python -m compileall src/data/rag/answer.py` passed.
  - `.venv/bin/python -m pytest tests/unit/test_rag_answer.py tests/backend/test_rag_api.py -q`
    passed: 15 tests.
  - Restarted Injection server on port 8010.
  - Smoke test for `보압 시간이 왜 영향력을 주는 것 같아?` with `수지 온도`
    at 25.6% and `보압 시간` at 9.1% returned a `보압 시간`-specific answer
    and did not repeat the 25.6% melt-temperature explanation.
  - Public `https://injection.imperialax.com/` serves `20260626-injection-rag-2`,
    and public `app-v2.js` uses the full `data.xai.top_features.map(...)`.

## 2026-06-26 - Injection assistant causal explanation quality improved
- User said the assistant still did not explain the reason behind XAI effects
  well enough.
- Root cause:
  - The assistant mainly repeated XAI percentages, rank, and sensitivity.
  - The compact prediction context sent to OpenAI did not include enough
    Injection process-mechanism hints.
  - Feature fallback copy was too short to explain the process/physics chain.
- Fix:
  - `src/data/rag/answer.py`
    - Expanded Injection feature explanations for melt temperature, mold
      temperature, injection time, packing pressure, packing time, total process
      time, gate area, and flow-length/thickness.
    - Added prompt context fields for app feature explanation and process
      mechanism so LLM answers can connect XAI to pressure-curve behavior.
    - Added explicit OpenAI instruction to explain causal chains such as
      input -> viscosity/flow resistance/pressure loss/fill-pack timing ->
      model sensitivity.
    - Local fallback now explains why the feature can physically affect Sprue
      Pressure/Filling Pressure, not just that it has a certain percentage.
    - Added Korean particle cleanup so `수지 온도는` reads naturally.
- Verification:
  - `python -m compileall src/data/rag/answer.py` passed.
  - `.venv/bin/python -m pytest tests/unit/test_rag_answer.py tests/backend/test_rag_api.py -q`
    passed: 15 tests.
  - Restarted Injection server on port 8010.
  - Smoke test for `왜 수지 온도가 가장 큰 영향력을 주는 것 같아?`
    now explains viscosity, flow resistance, pressure curve height/slope, and
    local model sensitivity.

## 2026-06-26 - Injection RAG assistant added to native apps
- User asked whether the Injection RAG/XAI assistant improvements were also
  reflected in the apps.
- Status before this pass:
  - Backend and web were updated.
  - Native iOS/Android Injection apps did not yet expose the assistant UI or
    `/api/v1/rag/answer` call path.
- iOS changes:
  - `InjectionAPIClient` now supports POST `/api/v1/rag/answer`.
  - `PredictionViewModel` now keeps assistant question/answer/loading/error
    state and sends the latest prediction context, inputs, curve summary, and
    XAI top features to RAG.
  - Injection result UI now includes an `Injection AI Assistant` card below the
    forecast result.
  - Core tests updated for the added `xai` field and RAG API protocol method.
- Android changes:
  - Injection result UI now includes an `Injection AI Assistant` card.
  - Native client parses `xai.top_features`, filling pressure max, and backend
    inputs from the prediction response.
  - Native client sends question + prediction context to `/api/v1/rag/answer`.
  - Nullable JSON values are explicitly encoded with `JSONObject.NULL`.
- Verification:
  - `swift test` in `ios/InjectionMVP` passed: 8 tests.
  - Backend RAG regression test passed:
    `.venv/bin/python -m pytest tests/unit/test_rag_answer.py tests/backend/test_rag_api.py -q`
    passed: 15 tests.
  - Android compile check was attempted with
    `gradle :app:compileDebugKotlin`, but the local Mac has no Java 17 runtime,
    so Gradle stopped before Kotlin compilation:
    `Cannot find a Java installation ... matching languageVersion=17`.

## 2026-06-26 - iOS Injection performance pass
- User reported that the iOS app felt noticeably slow.
- Code-first performance audit findings:
  - Injection result detail rendered `FillingAnimationView` immediately after
    prediction. That view uses a Canvas and nested fill-grid drawing, so opening
    the result page could do expensive rendering before the user asked to see
    the filling preview.
  - Injection assistant question text was bound directly to
    `PredictionViewModel.assistantQuestion`, an `@Published` field on the shared
    observable object. Typing in the assistant could fan out updates through the
    larger screen.
- Fix:
  - `ios/InjectionMVP/Sources/KyulAIInjectionApp/ResultDetailView.swift`
    - Filling histogram still appears immediately.
    - Filling animation is now lazy-loaded behind a `Show Filling Preview`
      button.
  - `ios/InjectionMVP/Sources/KyulAIInjectionApp/ContentView.swift`
    - Assistant card moved into `InjectionAssistantCard` with local `@State`
      question text.
    - ViewModel receives the final question only when the user taps Ask.
  - `ios/InjectionMVP/Sources/KyulAIInjectionCore/PredictionViewModel.swift`
    - `askAssistant` now accepts an explicit question while preserving the old
      default behavior.
  - Injection localization resources added the `show.filling.preview` key.
- Verification:
  - `swift test` in `ios/InjectionMVP` passed: 8 tests.
  - `swift test` in `ios/DDLaminateMVP` passed: 11 tests.
  - `swift test` in `ios/ImperialAXMVP` passed: 6 tests.
  - XcodeBuildMCP build/run of
    `ios/ImperialAXMVPApp/ImperialAXMVPHost.xcodeproj` scheme `ImperialAXMVPHost`
    on booted iPhone 17 simulator succeeded.
  - Simulator screenshot succeeded and showed the ImperialAX Forecast Workspace login
    screen.
- Remaining performance candidates:
  - Laminate `DesignSpaceMapView` sorts nearby map points during view render.
  - Laminate curve chart/fitting path still performs point sorting and kink-fit
    calculations in the render path. These are good next targets if Laminate
    result pages still feel slow.

## 2026-06-26 - Fixed iOS Open Injection freeze in ImperialAX host
- User reported that tapping `Open Injection` froze the iOS app.
- Root cause:
  - `ImperialAXMVP` opens module cards inside an existing `NavigationStack`.
  - The Injection module destination used `InjectionModuleView()`, whose
    internal `ContentView` created another `NavigationStack`.
  - This nested NavigationStack path could freeze or heavily stall the
    navigation transition.
- Fix:
  - `ios/InjectionMVP/Sources/KyulAIInjectionApp/ContentView.swift`
    - Added `wrapsInNavigationStack` mode.
    - Standalone Injection still owns its own `NavigationStack`.
    - Embedded Injection can render inside the host's existing navigation stack.
  - `ios/InjectionMVP/Sources/KyulAIInjectionApp/InjectionModuleView.swift`
    - Added `embedInNavigationStack` initializer option.
  - `ios/ImperialAXMVP/Sources/ImperialAXApp/ContentView.swift`
    - `Open Injection` now uses
      `InjectionModuleView(embedInNavigationStack: false)`.
- Verification:
  - `swift test` in `ios/InjectionMVP` passed: 8 tests.
  - `swift test` in `ios/ImperialAXMVP` passed: 6 tests.
  - XcodeBuildMCP rebuilt and launched `ImperialAXMVPHost` on iPhone 17 simulator.
  - UI automation flow:
    - tapped `Continue with demo account`;
    - scrolled to `Open Injection`;
    - tapped `Open Injection`;
    - confirmed the Injection screen opened with `ImperialAX Injection Forecast` and
      `Connected` visible.

## 2026-06-26 - Injection XAI visible in native apps
- User asked to add Injection XAI to the app UI.
- Status before this pass:
  - Native apps already decoded or forwarded Injection XAI to the assistant
    context.
  - XAI was not visibly rendered as a result card section.
- Fix:
  - `ios/InjectionMVP/Sources/KyulAIInjectionApp/ContentView.swift`
    - Latest Injection result card now shows an `Injection XAI` section when
      `result.xai` is present.
    - Shows top 5 features with percent bars and short explanations.
  - `ios/InjectionMVP/Sources/KyulAIInjectionApp/ResultDetailView.swift`
    - Full result page now shows an `Injection XAI` card after the pressure
      curve.
    - Shows top 8 features with category, percent bar, and explanation.
  - `android/ImperialAXMVP/app/src/main/java/com/imperialax/app/InjectionActivity.kt`
    - Android Injection result card now shows an `Injection XAI` section when
      `xaiFeatures` are present.
    - Shows top 5 features with percent bars and explanations before the
      assistant card.
- Verification:
  - `swift test` in `ios/InjectionMVP` passed: 8 tests.
  - `swift test` in `ios/ImperialAXMVP` passed: 6 tests.
  - Android compile check was attempted with
    `gradle :app:compileDebugKotlin`, but the local Mac still has no Java 17
    runtime, so Gradle stopped before Kotlin compilation.

## 2026-06-26 - Added Laminate RAG assistant to native apps
- User noticed RAG was not reflected in the app.
- Status before this pass:
  - Web RAG endpoint existed at `/api/v1/rag/answer`.
  - Injection native app already had an assistant call path.
  - Laminate native result pages showed XAI and design-space insight, but no
    RAG assistant UI or RAG API request.
- Fix:
  - `ios/DDLaminateMVP/Sources/KyulAIDDLaminateCore/DDLaminateModels.swift`
    - Added `RagAnswerRequest` and `RagAnswerResponse`.
  - `ios/DDLaminateMVP/Sources/KyulAIDDLaminateCore/DDLaminateAPIClient.swift`
    - Added `answerRag` using `POST /api/v1/rag/answer`.
  - `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/ResultDetailView.swift`
    - Added `LaminateAssistantCard` to both Laminate Response and u3 result
      pages.
    - The card sends the current prediction context with the question:
      mode, model, inputs, predicted Type, Pt, max displacement/force, and
      top XAI features.
  - `android/ImperialAXMVP/app/src/main/java/com/imperialax/app/LaminateResultActivity.kt`
    - Added a Laminate AI Assistant card to the native Android result page.
    - It posts the current result and XAI context to the same RAG endpoint.
- Verification:
  - `swift test` in `ios/DDLaminateMVP` passed: 11 tests.
  - `swift test` in `ios/ImperialAXMVP` passed: 6 tests.
  - Public RAG endpoint smoke test passed with a D11 bending stiffness question
    and returned internal XAI report citations.
  - Android compile check was attempted with
    `gradle :app:compileDebugKotlin`, but Gradle still cannot start on this Mac
    because Java 17 is not installed/configured.

## 2026-06-26 - Added Injection Shape Preview to native app inputs
- User asked whether Shape Preview could be shown inside the app and whether it
  would be a large upgrade.
- Decision:
  - Implemented a lightweight native DOE-driven preview rather than a full CAD
    or 3D engine integration.
  - The preview uses the selected geometry values: L, W, thickness, hole
    diameter, gate width, and gate height.
- Fix:
  - `ios/InjectionMVP/Sources/KyulAIInjectionApp/ContentView.swift`
    - Added a `Shape Preview` section inside the Injection input card.
    - Added `InjectionShapePreviewView`, a SwiftUI Canvas 2.5D panel preview
      with hole, edge gate, flow guide, and dimension chips.
  - `android/ImperialAXMVP/app/src/main/java/com/imperialax/app/InjectionActivity.kt`
    - Added a `Shape Preview` section above process/geometry details.
    - Added `InjectionShapePreviewView`, a native Android custom View drawing
      the same DOE-driven panel/hole/gate preview.
- Verification:
  - `swift test` in `ios/InjectionMVP` passed: 8 tests.
  - `swift test` in `ios/ImperialAXMVP` passed: 6 tests.
  - `git diff --check` passed for the changed iOS/Android files.
  - Android compile check was attempted with
    `gradle :app:compileDebugKotlin`, but Gradle still cannot start on this Mac
    because Java 17 is not installed/configured.

## 2026-06-26 - Hardened iOS Injection Shape Preview after main-thread crash report
- User reported Xcode stopping at `Thread 1 Queue : com.apple.main-thread`.
- Reproduction attempt:
  - Built and launched `ImperialAXMVPHost` on the iPhone 17 simulator.
  - Opened the Injection module and scrolled to the new `Shape Preview`
    section.
  - The simulator did not reproduce a crash; the preview rendered normally.
- Defensive fix:
  - `ios/InjectionMVP/Sources/KyulAIInjectionApp/ContentView.swift`
    - Changed `InjectionShapePreviewView` from asynchronous Canvas rendering to
      normal Canvas rendering.
    - Added `safeDimension` clamping so malformed/empty/NaN geometry values
      cannot enter preview geometry calculations.
- Verification:
  - `swift test` in `ios/InjectionMVP` passed: 8 tests.
  - `swift test` in `ios/ImperialAXMVP` passed: 6 tests.
  - XcodeBuildMCP build/run of `ImperialAXMVPHost` succeeded.
  - UI automation opened Injection and confirmed the `Shape Preview` section
    with G01 dimensions visible.

## 2026-06-26 - Fixed iOS Laminate predict crash after RAG assistant addition
- User reported the app froze after pressing Predict in Laminate.
- Root cause:
  - Predict itself completed, but opening the result detail page crashed.
  - Runtime log showed:
    `No ObservableObject of type AppSettings found`.
  - The Laminate RAG assistant added `@EnvironmentObject AppSettings` to
    `ResultDetailView` and `U3PtResultDetailView`, but navigation destinations
    did not explicitly pass the environment object.
- Fix:
  - `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/ContentViewV2.swift`
    - Added `.environmentObject(settings)` to both response and u3 result
      destinations.
  - `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/ContentView.swift`
    - Added the same explicit environment object pass for the legacy content
      path.
- Verification:
  - `swift test` in `ios/DDLaminateMVP` passed: 11 tests.
  - `swift test` in `ios/ImperialAXMVP` passed: 6 tests.
  - XcodeBuildMCP build/run of `ImperialAXMVPHost` succeeded.
  - UI automation opened Laminate, tapped `Run Forecast`, and confirmed the
    result detail page opened with `Predicted Pt 17,163.21`.

## 2026-06-28 - Fixed Injection entry flow, geometry preview, and result RAG surface
- User reported that `Open Injection` froze, the Injection preview did not feel
  consistent with DOE geometry, and Injection needed RAG inside the app.
- Reproduction:
  - Built and launched `ImperialAXMVPHost` on the iPhone 17 simulator.
  - Demo-login state was active.
  - Tapped `Open Injection`; the current build entered the Injection module
    without freezing.
  - Ran `Predict Pressure`; the result detail page opened without crashing.
- Fixes:
  - `ios/InjectionMVP/Sources/KyulAIInjectionApp/ContentView.swift`
    - Passed `AppSettings` explicitly into `ResultDetailView` navigation.
    - Reworked `InjectionShapePreviewView` from decorative 2.5D geometry to a
      top-view DOE geometry preview with scaled panel, centered hole, edge gate,
      flow guide, grid, and dimension labels.
  - `ios/InjectionMVP/Sources/KyulAIInjectionApp/ResultDetailView.swift`
    - Added `Injection AI Assistant` to the full result page.
    - The assistant now sends prediction context, inputs, XAI features, pressure,
      filling, model labels, and curve metadata to `/api/v1/rag/answer`.
  - `android/ImperialAXMVP/app/src/main/java/com/imperialax/app/InjectionActivity.kt`
    - Reworked native Injection shape preview to the same top-view DOE geometry
      interpretation used by iOS.
- Verification:
  - `swift test` in `ios/InjectionMVP` passed: 8 tests.
  - `swift test` in `ios/ImperialAXMVP` passed: 6 tests.
  - `git diff --check` passed.
  - XcodeBuildMCP build/run of `ImperialAXMVPHost` succeeded.
  - UI automation opened Injection, confirmed the `Shape Preview` section with
    G01 dimensions visible, tapped `Predict Pressure`, and confirmed the result
    detail page opened.
  - Android compile check with `gradle :app:compileDebugKotlin` is still blocked
    by the Mac environment missing a Java 17 toolchain, not by a reported Kotlin
    compile error.

## 2026-06-29 - Fixed Injection Assistant HTTP 500 from RAG index query
- User reported `Assistant failed: HTTP 500: Internal Server Error` in the
  Injection assistant.
- Root cause:
  - The RAG index stores `token_counts` as TF-IDF weights.
  - `query_index` was recomputing document frequency by summing those stored
    weights as if they were raw document counts.
  - Common English assistant questions such as
    `Why is the top XAI feature important in this prediction?` produced negative
    pseudo document frequencies for tokens like `is`, `the`, and `in`, causing
    `ZeroDivisionError` in IDF calculation.
- Fix:
  - `src/data/rag/indexer.py`
    - Changed query-time document frequency to count whether a token appears in
      each chunk, not to sum TF-IDF weights.
  - `src/data/rag/answer.py`
    - Broadened OpenAI response fallback handling so unexpected LLM/client
      errors return local fallback text instead of surfacing as HTTP 500.
    - Prioritized current Injection prediction/XAI context over generic RAG
      retrieval when the request is explaining an active Injection prediction,
      avoiding unrelated DD Laminate citations for generic assistant questions.
  - `src/backend/api/v1/rag.py`
    - Added a route-level safety fallback so answer generation exceptions return
      a usable local explanation with `model=local-error-fallback` instead of
      crashing the API.
  - `tests/backend/test_rag_api.py`
    - Added regression coverage for route-level fallback on answer generation
      failure.
  - `tests/unit/test_rag_answer.py`
    - Added regression coverage for common English assistant questions against
      the production RAG index.
- Verification:
  - Direct local reproduction no longer raises `ZeroDivisionError`.
  - `.venv/bin/python -m pytest -q tests/backend/test_rag_api.py tests/unit/test_rag_answer.py`
    passed: 17 tests.
  - `git diff --check` passed.
  - Restarted both uvicorn servers on ports 8000 and 8010.
  - Public smoke checks against `https://injection.imperialax.com/api/v1/rag/answer`
    returned HTTP 200 for both Korean and English Injection assistant questions.

## 2026-06-29 - Improved Laminate Assistant keyboard dismissal on iOS
- User reported that after asking the Laminate AI Assistant, the iOS keyboard
  stayed open and did not dismiss when interacting outside the input field.
- Fix:
  - `ios/DDLaminateMVP/Sources/KyulAIDDLaminateApp/ResultDetailView.swift`
    - Added iOS keyboard dismissal helper using `UIResponder.resignFirstResponder`.
    - Added interactive scroll keyboard dismissal to both Laminate and u3 result
      detail scroll views.
    - Added `@FocusState` to the shared `LaminateAssistantCard`.
    - The assistant input now dismisses the keyboard on Done/submit.
    - The Ask button dismisses the keyboard before sending the RAG request.
    - Tapping assistant answer/error/background space also clears focus.
- Verification:
  - `swift test` in `ios/DDLaminateMVP` passed: 11 tests.

## 2026-06-29 - Applied the same Assistant keyboard dismissal to Injection iOS
- User pointed out that similar UX fixes should be checked across related
  modules without needing a separate reminder.
- Fix:
  - `ios/InjectionMVP/Sources/KyulAIInjectionApp/ResultDetailView.swift`
    - Added iOS keyboard dismissal support to the Injection result Assistant.
    - The result Assistant now dismisses the keyboard when asking, tapping
      response/error/background space, or scrolling interactively.
  - `ios/InjectionMVP/Sources/KyulAIInjectionApp/ContentView.swift`
    - Applied the same behavior to the Injection main-screen Assistant card.
- Verification:
  - `swift test` in `ios/InjectionMVP` passed: 8 tests.
  - `swift test` in `ios/ImperialAXMVP` passed: 6 tests.
  - `git diff --check` passed.

## 2026-06-29 - Made mobile module cards tappable, not only the Open button
- User reported that tapping Injection inside the app appeared to do nothing.
- Finding:
  - On iOS, the latest build could open Injection when tapping the explicit
    `Open Injection` button.
  - The module card itself was not a navigation target, so tapping the
    `Injection` card/title/body felt unresponsive.
- Fix:
  - `ios/ImperialAXMVP/Sources/ImperialAXApp/ContentView.swift`
    - Wrapped granted Laminate and Injection module cards in `NavigationLink`.
    - The whole card is now tappable while preserving the existing button-like
      visual label.
  - `android/ImperialAXMVP/app/src/main/java/com/imperialax/app/MainActivity.kt`
    - Added a card-level click listener so tapping the Android module card also
      opens the module or shows the access dialog.
- Verification:
  - `swift test` in `ios/ImperialAXMVP` passed: 6 tests.
  - `swift test` in `ios/InjectionMVP` passed: 8 tests.
  - XcodeBuildMCP build/run of `ImperialAXMVPHost` succeeded.
  - UI automation confirmed the Injection card is now one tap target and opens
    the `Injection Forecast AI` screen.
  - Android compile check is still blocked by missing Java 17 toolchain on the
    Mac environment.

## 2026-06-29 - Hardened Injection Shape Preview after Xcode stopped at ContentView line 327
- User reported Xcode stopped on the main thread at
  `ios/InjectionMVP/Sources/KyulAIInjectionApp/ContentView.swift:327`, which is
  the start of the Injection `Shape Preview` card body.
- Finding:
  - The visible `Thread 1 Queue : com.apple.main-thread (serial)` text is a
    thread/frame label, not the underlying exception message.
  - In the current simulator build, Injection opened successfully and the Shape
    Preview rendered.
- Fix:
  - Sanitized geometry strings before building the Shape Preview card so invalid
    or transient DOE text values cannot enter the preview body.
  - Added a Canvas size guard to skip drawing when SwiftUI gives a non-finite or
    too-small preview size during layout.
- Verification:
  - `swift test` in `ios/InjectionMVP` passed: 8 tests.
  - `swift test` in `ios/ImperialAXMVP` passed: 6 tests.
  - `git diff --check` passed.
  - XcodeBuildMCP build/run succeeded.
  - UI automation opened Injection and scrolled to `Shape Preview`; the card
    rendered with G01 dimensions visible.

## 2026-06-29 - Removed Canvas from Injection Shape Preview after EXC_BAD_ACCESS
- User reported a real crash:
  `Thread 1: EXC_BAD_ACCESS (code=2, address=...)` at
  `ios/InjectionMVP/Sources/KyulAIInjectionApp/ContentView.swift:333`.
- Fix:
  - Moved the Shape Preview content into a standalone `InjectionShapePreviewCard`
    so the main `ContentView` body no longer owns the complex preview hierarchy.
  - Replaced the `Canvas`-based preview renderer with pure SwiftUI
    `GeometryReader`, `Shape`, `RoundedRectangle`, `Circle`, and `Path` views.
  - Kept geometry value sanitization before rendering.
- Verification:
  - `swift test` in `ios/InjectionMVP` passed: 8 tests.
  - `swift test` in `ios/ImperialAXMVP` passed: 6 tests.
  - `git diff --check` passed.
  - XcodeBuildMCP build/run succeeded.
  - UI automation opened Injection and scrolled to `Shape Preview`; the preview
    rendered with L/W/T/D/Gate labels visible and no simulator crash.

## 2026-06-29 - Removed runtime content closure from Injection detail sections
- User reported another real crash:
  `Thread 1: EXC_BAD_ACCESS (code=2, address=...)` at
  `ios/InjectionMVP/Sources/KyulAIInjectionApp/ContentView.swift:511`.
- Root suspect:
  - Line 511 was the generic `detailSection` helper's `content()` call.
  - Multiple sections (`Shape Preview`, `Process details`, `Geometry details`)
    passed complex controls through that runtime ViewBuilder closure.
- Fix:
  - Replaced the `detailSection(title:content:)` helper with a standalone
    `InjectionDetailSection` view that stores its built content in `init`.
  - Updated Shape Preview, Process details, and Geometry details to use the new
    section view.
  - The old line 511 `content()` crash site no longer exists.
- Verification:
  - `swift test` in `ios/InjectionMVP` passed: 8 tests.
  - `swift test` in `ios/ImperialAXMVP` passed: 6 tests.
  - `git diff --check` passed.
  - XcodeBuildMCP build/run succeeded.
  - UI automation opened Injection, scrolled through Shape Preview, Process
    details, Geometry details, and reached `Predict Pressure` without simulator
    crash.

## 2026-06-29 - Improved Injection AI Assistant answer readability
- User said the Injection AI Assistant answer was difficult to read and asked
  for cleaner sentence organization.
- Backend changes:
  - `src/data/rag/answer.py`
    - Injection local fallback answers now use clearer paragraph structure:
      summary, current input/output, XAI mechanism, and caution/interpretation.
    - Requested-feature explanations now separate quantitative XAI details,
      physical mechanism, and interpretation into readable paragraphs.
    - OpenAI-backed Injection answers are post-processed through
      `format_answer_for_display()` so long single-paragraph responses are split
      into compact display paragraphs.
- Web changes:
  - `src/frontend/simple-injection/app-v2.js`
    - Renders Assistant answers as paragraph nodes instead of one large text
      block.
  - `src/frontend/simple-injection/styles-v2.css`
    - Adds spacing and softer weight/line-height for answer paragraphs.
- Native app changes:
  - `ios/InjectionMVP/Sources/KyulAIInjectionApp/ContentView.swift`
    - Added shared `InjectionAssistantAnswerBlock` to render answer provider and
      paragraphs with better line spacing.
  - `ios/InjectionMVP/Sources/KyulAIInjectionApp/ResultDetailView.swift`
    - Result Assistant now uses the same answer block.
  - `android/ImperialAXMVP/app/src/main/java/com/imperialax/app/InjectionActivity.kt`
    - Android Injection Assistant now renders answers as paragraph rows inside
      a bordered answer block.
- Verification:
  - `python -m pytest tests/unit/test_rag_answer.py` passed: 14 tests.
  - `swift test` in `ios/InjectionMVP` passed: 8 tests.
  - `swift test` in `ios/ImperialAXMVP` passed: 6 tests.
  - `git diff --check` passed.
  - Backend API test collection is blocked in this local Python by missing
    `fastapi`.
  - Android Kotlin compile is still blocked by missing Java 17 toolchain.

## 2026-06-29 - Pre-commit snapshot stabilization
- User asked to proceed with the next cleanup stage: pre-commit snapshot
  cleanup, web/app UI parity, Android build environment, and RAG/Assistant API
  test stabilization.
- Used the ai-slop-cleaner workflow:
  - Locked behavior with targeted tests before and after edits.
  - Classified fallback-like code before changing it.
  - Kept compatibility/fail-safe fallbacks that protect offline modules,
    local history, and local RAG answers.
- Fixes:
  - `android/ImperialAXMVP/app/src/main/java/com/imperialax/app/MainActivity.kt`
    - Removed an invalid login-card click handler that referenced `module`
      outside scope and broke Android Kotlin compilation.
  - `src/frontend/imperialax/login-v2.html`,
    `src/frontend/imperialax/login-v2.ko.html`,
    `src/frontend/imperialax/login-v2.js`, and
    `src/frontend/imperialax/app.js`
    - Replaced remaining visible web fallback `ImperialAX Demo` account copy with
      `Demo Account`.
  - `tests/backend/test_dd_laminate_ios_contract.py`
    - Updated stale route/static expectations to the current UX contract:
      roots expose the forecast entry/current v2 path instead of old Classic
      content, and workspace static JS now contains `Demo Account`.
  - Added `docs/precommit-snapshot-2026-06-29.md` with reproducible verification
    commands and environment notes.
- Android environment:
  - JDK 17 is installed at `/opt/homebrew/opt/openjdk@17`, but macOS
    `java_home` does not discover it.
  - Verified Android with explicit `JAVA_HOME=/opt/homebrew/opt/openjdk@17`.
- Verification:
  - JS syntax checks passed for DD Laminate, Simple Injection, ImperialAX app,
    ImperialAX login, and ImperialAX admin scripts.
  - Python backend/RAG suite passed: 71 tests.
  - `swift test` in `ios/DDLaminateMVP` passed: 11 tests.
  - `swift test` in `ios/InjectionMVP` passed: 8 tests.
  - `swift test` in `ios/ImperialAXMVP` passed: 6 tests.
  - Android `gradle :app:assembleDebug --no-daemon` passed with explicit JDK 17.
  - `git diff --check` passed.
- Remaining notes:
  - Current local Python is 3.10.20, while project metadata asks for Python
    3.11+. Use a project venv on the Windows/server PC.
  - Installing `requirements-serving.txt` into the shared local base
    environment downgraded some packages and produced unrelated local package
    compatibility warnings; this reinforces using an isolated venv.
  - Gradle reports future Gradle 10 deprecation warnings, but current debug
    build succeeds.

## 2026-06-29 - Injection cleanup/debug pass
- User asked to review the accumulated code, debug, and optimize.
- Cleanup scope followed the ai-slop-cleaner workflow:
  - Locked current behavior first with existing tests/checks.
  - Kept the edit small and reversible.
  - Focused on side-effect boundaries instead of broad refactoring.
- Web Injection cleanup:
  - `src/frontend/simple-injection/app-v2.js`
    - Separated result rendering from history persistence. `renderResult()`
      now only updates the UI, and successful prediction submission records
      history explicitly afterward.
    - Injection AI citation controls now appear only when citations are
      actually present, avoiding a dead `Show citations` button.
- Fallback/debug notes:
  - Browser history storage failures remain intentionally non-blocking because
    predictions should still work even if `localStorage` is unavailable.
  - iOS/Android history parsing similarly treats stored recent runs as
    recoverable local state rather than a prediction blocker.
- Verification:
  - `swift test` in `ios/InjectionMVP` passed after cleanup: 8 tests.
  - `node --check src/frontend/simple-injection/app-v2.js` passed after cleanup.
  - `git diff --check` passed after cleanup.
  - Android Gradle verification is still blocked by missing local Java Runtime.

## 2026-06-29 - Added Injection history and Korean XAI/Assistant UX
- User asked to make Injection match Laminate's bottom prediction history and
  fix remaining English-only Injection XAI/Assistant text in Korean mode.
- iOS Injection changes:
  - `ios/InjectionMVP/Sources/KyulAIInjectionApp/ContentView.swift`
    - Added a bottom `Prediction history` / `예측 기록` card using the existing
      `PredictionViewModel.recentRuns` store.
    - Tapping a history card reapplies the saved DOE/model setup; the card also
      exposes a clear-history action.
    - Localized the main Injection Assistant default question to Korean when the
      app language is Korean.
    - Added shared Korean XAI helpers for Injection feature labels,
      explanations, XAI summary/method, and runtime notes.
  - `ios/InjectionMVP/Sources/KyulAIInjectionApp/ResultDetailView.swift`
    - Reused the same Korean XAI helpers in the result detail page.
    - Localized the result-detail Assistant default question and XAI notes.
    - Sends translated XAI feature labels/explanations in the Assistant
      prediction context when Korean is selected.
- Web Injection changes:
  - `src/frontend/simple-injection/index-v2.html` and
    `src/frontend/simple-injection/index-v2.ko.html`
    - Added a result-panel prediction history section.
  - `src/frontend/simple-injection/app-v2.js`
    - Stores recent Injection predictions in `localStorage`.
    - Renders reusable history cards at the bottom of the result panel.
    - Localizes backend result notes in Korean mode.
  - `src/frontend/simple-injection/styles-v2.css`
    - Added compact history-card styles.
- Android ImperialAX app changes:
  - `android/ImperialAXMVP/app/src/main/java/com/imperialax/app/InjectionActivity.kt`
    - Added SharedPreferences-backed recent Injection history cards.
    - Added Korean XAI label/explanation copy when the device locale is Korean.
    - Added Korean Assistant default question/note text.
    - Sends `ko`/`en` language to the RAG endpoint instead of `auto`.
- Verification:
  - `swift test` in `ios/InjectionMVP` passed: 8 tests.
  - `node --check src/frontend/simple-injection/app-v2.js` passed.
  - `git diff --check` passed.
  - Android Gradle verification could not run because this Mac currently has no
    Java Runtime available.

## 2026-06-29 - Polished Injection AI Assistant answer presentation
- User asked for Injection AI Assistant answers to appear in the same organized
  style as Laminate instead of a loose text block.
- Web Injection:
  - `src/frontend/simple-injection/app-v2.js`
    - Renders Assistant answers as structured paragraph cards.
    - The first paragraph is labeled `Summary` / `요약`; later paragraphs are
      labeled `Reasoning` / `해석`.
  - `src/frontend/simple-injection/styles-v2.css`
    - Added a bordered answer container, provider/citation header treatment,
      highlighted summary card, and compact reasoning cards.
- iOS Injection:
  - `ios/InjectionMVP/Sources/KyulAIInjectionApp/ContentView.swift`
    - Reworked `InjectionAssistantAnswerBlock` into a polished answer panel
      with an `Injection AI` header, provider badge, summary/reasoning cards,
      and retrieved-source count.
  - `ios/InjectionMVP/Sources/KyulAIInjectionApp/ResultDetailView.swift`
    - Updated result-detail Assistant to use the same polished answer block.
- Android Injection:
  - `android/ImperialAXMVP/app/src/main/java/com/imperialax/app/InjectionActivity.kt`
    - Renders Assistant answers as a headed block with summary/reasoning cards.
- Verification:
  - `swift test` in `ios/InjectionMVP` passed: 8 tests.
  - `node --check src/frontend/simple-injection/app-v2.js` passed.
  - `git diff --check` passed.
  - Android Gradle verification is still blocked by missing local Java Runtime.

## 2026-06-29 - DD Laminate Prediction Reliability / Uncertainty First Pass
- User asked to start the next research/model enhancement direction:
  recommendation confidence/uncertainty, validation-loop support, and more
  research-style Type-cause analysis.
- Implemented the first step as a lightweight, no-retraining uncertainty layer
  for DD Laminate Forecast and u3 Forecast.
- Backend:
  - Added `PredictionUncertainty` to
    `src/backend/api/v1/dd_laminate.py`.
  - `POST /api/v1/dd-laminate/predict/response` and
    `POST /api/v1/dd-laminate/predict/u3-forecast` now return
    `uncertainty`.
  - The score combines model confidence, distance to nearby curated
    simulations in the same Case/design scope, and local Type agreement.
  - The Pt range is a screening band from nearby Pt scatter, not a formal
    statistical confidence interval.
- Web:
  - Added a compact Prediction reliability panel to
    `src/frontend/dd-laminate/index-v2.html` and Korean page.
  - `src/frontend/dd-laminate/app-v2.js` renders Reliability, Pt screening
    range, design-space coverage, Type agreement, and short notes.
  - PNG/PDF report export now includes a Prediction Reliability section.
- iOS:
  - Added `PredictionUncertainty` Codable model and result-detail card in
    `ios/DDLaminateMVP`.
- Android:
  - Added uncertainty parsing to the ImperialAX Laminate API result model and a
    compact result-detail section in `LaminateResultActivity`.
- Verification:
  - `.venv/bin/python` FastAPI TestClient checks returned uncertainty for
    response and u3 forecast examples.
  - `python3 -m py_compile src/backend/api/v1/dd_laminate.py` passed.
  - `node --check src/frontend/dd-laminate/app-v2.js` passed.
  - `swift test --package-path ios/DDLaminateMVP` passed 11 tests.
  - Android Gradle compile could not run because this Mac does not have a Java
    17 toolchain configured for the ImperialAX Android project.

## 2026-06-30 - DD Laminate Case5 / Explicit Ply-Sequence Preview
- User asked whether new laminate stacking patterns can be applied from the
  existing Case2/Case3/Case4 model family, then asked to start with Case5.
- Decision:
  - Do not inject Case5 directly into the trained forecast models yet because
    saved model feature schemas are trained on Case2/Case3/Case4 one-hot
    features and no Case5 simulation labels exist.
  - Add a safe preview path that expands or accepts an explicit ply sequence
    and computes CLT/ABD physics descriptors without changing model behavior.
- Backend:
  - Added explicit-stack physics utilities in
    `src/ml/dd_laminate/laminate_physics.py`:
    `abd_matrices_from_stack`, `stack_physics_summary`, and public
    `case_stack`.
  - Added `POST /api/v1/dd-laminate/stack/preview` in
    `src/backend/api/v1/dd_laminate.py`.
  - Built-in Case2/Case3/Case4 can be previewed from `theta1`, `theta2`, and
    `case`.
  - Case5/Custom requires `ply_sequence`, e.g. an already-expanded list of
    ply angles. The endpoint returns `low / extrapolation` reliability notes
    because Case5 has no direct training samples yet.
- Verification:
  - `python3 -m py_compile src/backend/api/v1/dd_laminate.py
    src/ml/dd_laminate/laminate_physics.py` passed.
  - FastAPI TestClient returned HTTP 200 for a sample explicit Case5
    16-ply sequence and reported CLT physics values plus extrapolation notes.
  - FastAPI TestClient returned HTTP 200 for built-in Case2 preview and
    expanded to 16 plies.

## 2026-06-30 - DD Laminate Stack Lab UI
- User asked whether a new stacking expression could be entered in real time,
  first in a separate tab, before integrating it into the Case2/Case3/Case4
  forecast flow.
- Implemented a web-first `Stack Lab` tab on the DD Laminate v2 page:
  - Added English and Korean forms for `Case5` / `Custom`.
  - Inputs: `theta1`, `theta2`, case selector, formula memo, and expanded
    ply sequence textarea.
  - The live ply-stack preview now reads the custom sequence immediately.
  - Submit calls `POST /api/v1/dd-laminate/stack/preview` and renders ply
    count, total thickness, reliability, design-space coverage,
    expanded sequence chips, and key CLT physics descriptors.
- Important boundary:
  - This is not yet a trained Case5 predictor. It is a physics/design-space
    preview for testing new formulas before generating simulation labels and
    retraining the forecast models.
- Verification:
  - `node --check src/frontend/dd-laminate/app-v2.js` passed.
  - Local backend curl to `/stack/preview` returned HTTP 200 for the sample
    16-ply Case5 sequence.
  - Public `https://laminate.imperialax.com/` serves
    `app-v2.js?v=20260630-stack-lab`.
  - Browser smoke test clicked `Stack Lab`, verified active mode and 16-ply
    live preview, then ran `Preview Stack Physics`; result showed 16 plies,
    0.12 in thickness, 49% reliability, extrapolation coverage, 10 physics
    rows, and 16 sequence chips with no visible error.

## 2026-07-02 - DD Stack Lab Formula Parser
- User asked whether entering `theta1`, `theta2`, and a stacking formula can
  automatically generate the ply sequence.
- Implemented frontend formula parsing in the DD Laminate `Stack Lab` tab:
  - Supports `±θ₁`, `±θ₂`, `∓θ₁`, `∓θ₂`.
  - Supports grouping with `[]`, `()`, `{}`.
  - Supports repeat counts written as subscript digits such as `₂`, normal
    digits like `4`, `_4`, `^4`, or `x4`.
  - If the formula can be parsed, the generated sequence textarea is updated
    automatically as theta values or formula text changes.
  - If the formula cannot be parsed, the manual sequence textarea remains the
    fallback.
- Updated English/Korean Stack Lab copy from "Formula memo" to actual
  stack-formula / generated-sequence wording.
- Verification:
  - `node --check src/frontend/dd-laminate/app-v2.js` passed.
  - Public `https://laminate.imperialax.com/` serves
    `app-v2.js?v=20260702-formula-parser`.
  - Browser smoke test:
    - Default `[[±θ₁]/[±θ₂]/[∓θ₂]/[∓θ₁]]₂` generated 16 plies.
    - With `θ1=45`, `θ2=-15`, sequence updated to
      `45,-45,-15,15,15,-15,-45,45,...`.
    - Preview API rendered 16 plies, 0.12 in thickness, 49% reliability,
      and no visible error.
    - Case2 formula `[[±θ₁]/[±θ₂]]₄` also generated a 16-ply sequence.

## 2026-07-02 - DD Stack Lab Formula Toolbar
- User wanted to know the Case5 equation on screen and needed a way to enter
  theta symbols without typing special Greek/subscript characters manually.
- Updated the web DD Laminate Stack Lab:
  - Added an on-form Case5 formula guide:
    `[[±θ₁]/[±θ₂]/[∓θ₂]/[∓θ₁]]₂`.
  - Added formula token buttons for `±θ₁`, `±θ₂`, `∓θ₁`, `∓θ₂`,
    `[`, `]`, `/`, `₂`, and `₄`.
  - Clicking a token inserts it at the current formula cursor position and
    dispatches the normal input event, so the generated ply sequence and
    live stack preview update immediately.
  - Korean page received the same Case5 guide and toolbar.
- Verification:
  - `node --check src/frontend/dd-laminate/app-v2.js` passed.
  - Public page serves `app-v2.js?v=20260702-formula-toolbar`.
  - Browser smoke test confirmed the toolbar has 9 buttons and Case5 guide is
    visible.
  - Browser clicked `[`, `±θ₁`, `/`, `±θ₂`, `]`, `₂`; formula became
    `[±θ₁/±θ₂]₂`, sequence became
    `30,-30,-60,60,30,-30,-60,60`, and live ply count became `8`.

## 2026-07-03 - Injection Shape Preview First Frame
- User noticed that the Injection Preview area briefly showed a different
  shape before the intended Shape Preview appeared.
- Root cause:
  - `app-v2.js` rendered an immediate SVG fallback while the Three.js module
    was still loading.
  - After Three.js finished importing, the fallback SVG was cleared and the
    actual parametric 3D preview was rendered.
  - This was technically a loading fallback, but it could look like a wrong
    geometry to viewers.
- Update:
  - During normal Three.js loading, the Preview area now stays in the loading
    state instead of showing the fallback SVG first.
  - The SVG fallback is still kept for the real failure path, if Three.js
    cannot be loaded.
  - Bumped the English/Korean Injection v2 script cache version to
    `20260703-shape-preview-loading`.
- Verification:
  - `node --check src/frontend/simple-injection/app-v2.js` passed.

## 2026-07-03 - ImperialAX App Latest Build
- User asked to update the app to the latest version.
- Android:
  - Built the unified Android app from `android/ImperialAXMVP`.
  - Used JDK 17 explicitly because the default macOS Java runtime was not
    registered.
  - Copied the latest debug APK to:
    - `artifacts/android/ImperialAX-debug-20260703-latest.apk`
    - `artifacts/android/ImperialAX-debug-latest.apk`
- iOS:
  - `swift test` passed for `ios/ImperialAXMVP`.
  - Simulator build succeeded for
    `ios/ImperialAXMVPApp/ImperialAXMVPHost.xcodeproj`, scheme
    `ImperialAXMVPHost`, with `CODE_SIGNING_ALLOWED=NO`.
- Verification:
  - Android `gradle assembleDebug` passed.
  - iOS Swift package tests passed: 6 tests, 0 failures.
  - iOS simulator host build passed.

## 2026-07-03 - Imperialax Cloudflare Server Routing
- User registered `imperialax.com` and asked to connect the current app/web
  servers.
- Updated DD/ImperialAX host routing:
  - `ai.imperialax.com` and `app.imperialax.com` serve the ImperialAX workspace
    login from the DD/ImperialAX server on port 8000.
  - `laminate.imperialax.com` and `dd.imperialax.com` serve the Laminate
    Forecast v2 page from port 8000.
  - `injection.imperialax.com` is routed in the Cloudflare Tunnel config to
    the Injection server on port 8010.
- Updated Cloudflare Tunnel config files:
  - `infrastructure/cloudflare/kclab-composite-ai.yml`
  - `infrastructure/cloudflare/kclab-composite-ai.windows.example.yml`
- Server state:
  - Restarted DD/Laminate server on port 8000.
  - Injection server on port 8010 was already running.
  - Restarted `cloudflared` with the updated ingress config.
- Verification:
  - `python3 -m py_compile src/backend/dd_laminate_app.py` passed.
  - Local `/ready` checks for ports 8000 and 8010 returned ready/ok models.
  - Local Host-header checks served the expected pages:
    - `ai.imperialax.com` / `app.imperialax.com`: ImperialAX Account Access.
    - `laminate.imperialax.com` / `dd.imperialax.com`: ImperialAX Laminate Forecast.
    - `injection.imperialax.com`: ImperialAX Injection Forecast v2.
- DNS caveat:
  - `imperialax.com` NS resolves to Cloudflare
    (`weston.ns.cloudflare.com`, `tegan.ns.cloudflare.com`).
  - The local `cloudflared tunnel route dns` authentication is currently tied
    to the existing `imperialax.com` zone, so CLI-created records landed under
    `*.imperialax.com.imperialax.com` instead of the `imperialax.com` zone.
  - Add the intended `imperialax.com` CNAME records manually in the Cloudflare
    dashboard, or re-run `cloudflared tunnel login` for the `imperialax.com`
    zone before using CLI DNS provisioning.

## 2026-07-03 - ImperialAX Root Domain Restored
- User asked to keep `imperialax.com` open and verify that it works.
- Root cause:
  - DD/ImperialAX and Injection servers were running and ready.
  - `laminate.imperialax.com` and `injection.imperialax.com` already returned HTTP 200.
  - `imperialax.com` and `www.imperialax.com` returned Cloudflare Tunnel HTTP 404 because they were missing from the active tunnel ingress list.
- Fix:
  - Added `imperialax.com` and `www.imperialax.com` to the active Cloudflare Tunnel config, routed to port 8000.
  - Mirrored the same entries into the Windows example tunnel config.
  - Restarted `cloudflared` with `/Users/danlee/KyulAI_codex/infrastructure/cloudflare/kclab-composite-ai.yml`.
- Verification:
  - `https://imperialax.com`, `https://www.imperialax.com`, `https://laminate.imperialax.com`, and `https://injection.imperialax.com` all returned HTTP 200 after restart.

## 2026-07-03 - ImperialAX Root Redirect to AI Workspace
- User asked to make `imperialax.com` connect to `ai.imperialax.com`.
- Updated `/Users/danlee/KyulAI_codex/src/backend/dd_laminate_app.py`:
  - Added `AI_REDIRECT_HOSTS = {"imperialax.com", "www.imperialax.com"}`.
  - Root requests for those hosts now return HTTP 308 to `https://ai.imperialax.com/`.
- Restarted the DD/ImperialAX uvicorn server on port 8000.
- Verification:
  - `python3 -m py_compile src/backend/dd_laminate_app.py` passed.
  - Local Host-header checks for `imperialax.com` and `www.imperialax.com` return `308 Location: https://ai.imperialax.com/`.
  - Public checks:
    - `https://imperialax.com` -> HTTP 308 to `https://ai.imperialax.com/`.
    - `https://www.imperialax.com` -> HTTP 308 to `https://ai.imperialax.com/`.
    - `https://ai.imperialax.com`, `https://laminate.imperialax.com`, and `https://injection.imperialax.com` return HTTP 200.

## 2026-07-03 - Imperialax Public DNS Connected
- User approved Cloudflare login for `imperialax.com`.
- `cloudflared tunnel login` saved a new `/Users/danlee/.cloudflared/cert.pem` for the active Cloudflare zone. The previous certificate was already backed up before login.
- Provisioned Cloudflare Tunnel DNS routes for:
  - `imperialax.com`
  - `www.imperialax.com`
  - `ai.imperialax.com`
  - `app.imperialax.com`
  - `laminate.imperialax.com`
  - `dd.imperialax.com`
  - `injection.imperialax.com`
- Updated tunnel ingress config files:
  - `/Users/danlee/KyulAI_codex/infrastructure/cloudflare/kclab-composite-ai.yml`
  - `/Users/danlee/KyulAI_codex/infrastructure/cloudflare/kclab-composite-ai.windows.example.yml`
- Updated `/Users/danlee/KyulAI_codex/src/backend/dd_laminate_app.py`:
  - `imperialax.com` and `www.imperialax.com` redirect to `https://ai.imperialax.com/`.
  - Existing `imperialax.com` and `www.imperialax.com` redirects to `https://ai.imperialax.com/` remain intact.
- Restarted DD/ImperialAX server on port 8000 and Cloudflare Tunnel.
- Verification:
  - DD `/ready` returned all models ok.
  - Injection `/ready` returned all models ok before the routing update.
  - Cloudflare DNS via `1.1.1.1` resolves all Imperialax hosts to Cloudflare edge A/AAAA records.
  - HTTPS checks through Cloudflare edge:
    - `https://imperialax.com` -> HTTP 308 to `https://ai.imperialax.com/`.
    - `https://www.imperialax.com` -> HTTP 308 to `https://ai.imperialax.com/`.
    - `https://ai.imperialax.com` and `https://app.imperialax.com` -> HTTP 200, ImperialAX workspace.
    - `https://laminate.imperialax.com` and `https://dd.imperialax.com` -> HTTP 200, Laminate Forecast.
    - `https://injection.imperialax.com` -> HTTP 200, Injection Forecast.
- Note:
  - The Mac's default ISP DNS resolver lagged behind temporarily, but Cloudflare/Google public DNS and direct Cloudflare edge checks were already correct.

## 2026-07-08 - Laminate XAI D11/D66 Feature Source
- User asked how Laminate XAI features such as D11 and D66 are computed.
- Answer basis:
  - The values are not read directly from Abaqus result files.
  - They are derived in `/Users/danlee/KyulAI_codex/src/ml/dd_laminate/laminate_physics.py` using Classical Laminate Theory.
  - The app expands `case + theta1 + theta2` into a ply stack, computes transformed lamina stiffness `Qbar` for each ply using T800/3900S material constants from the PPT, integrates through thickness to form ABD matrices, then uses normalized ABD terms in the XAI feature pack. As of the later ABD normalization update on 2026-07-08, those terms use `A* = A / h`, `B* = 2B / h^2`, and `D* = 12D / h^3`.
- Important wording:
  - In the UI/assistant, describe these as CLT-derived bending/twisting stiffness descriptors, not directly measured Abaqus outputs.

## 2026-07-08 - ABD Normalization Update and Full DD Retrain
- User requested ABD matrix normalization to follow:
  - `A* = A / h`
  - `B* = 2B / h^2`
  - `D* = 12D / h^3`
- Updated `/Users/danlee/KyulAI_codex/src/ml/dd_laminate/laminate_physics.py` so all stack/physics feature builders now use the requested normalized ABD definitions.
- Because B and D feature magnitudes changed, retrained the active DD Laminate Forecast and u3 Forecast models into new non-overwriting folders:
  - Laminate Forecast ML: `/Users/danlee/KyulAI_codex/models/dd_laminate_response_physics_abd_v1`
  - Laminate Forecast DL: `/Users/danlee/KyulAI_codex/models/dd_laminate_response_goint_physics_nn_abd_v1`
  - u3 Forecast ML/DL: `/Users/danlee/KyulAI_codex/models/dd_laminate_u3_forecast_physics_abd_v1`
- Generated matching XAI reports:
  - `/Users/danlee/KyulAI_codex/reports/dd_response_xai_physics_abd_v1`
  - `/Users/danlee/KyulAI_codex/reports/dd_response_xai_goint_physics_nn_abd_v1`
  - `/Users/danlee/KyulAI_codex/reports/dd_u3_xai_physics_abd_v1`
  - `/Users/danlee/KyulAI_codex/reports/dd_u3_xai_goint_physics_abd_v1`
- Updated the DD API registry so the existing user-facing model keys now point to the ABD-normalized models:
  - `response_surrogate_physics_v2`
  - `response_goint_physics_nn_v2`
  - `u3_forecast_physics_v2`
  - `u3_forecast_goint_physics_v2`
- Updated Windows bundle packaging list so the new model/report folders are included in future migration packages.
- Training results:
  - Laminate Forecast ML: Type accuracy `0.9422`, macro F1 `0.9372`, Pt MAE `438.11 kips`, curve normalized RMSE `0.00697`.
  - Laminate Forecast DL: Type accuracy `0.9389`, macro F1 `0.9383`, Pt MAE `661.41 kips`, curve normalized RMSE `0.02131`.
  - u3 Forecast ML: best scalar model `extra_trees`, Pt MAE `223.78 kips`, Type accuracy `0.9753`, curve normalized RMSE `0.00700`.
  - u3 Forecast DL: Pt MAE `168.65 kips`, Pt R2 `0.9226`, curve normalized RMSE `0.01018`.
- Verification:
  - `py_compile` passed for changed/training/API scripts.
  - Direct prediction smoke tests passed for Laminate ML/DL and u3 ML/DL model files.
  - Restarted DD server on port 8000.
  - `/ready` returned all active DD models as `ok`.
  - HTTP smoke tests passed for Laminate response prediction, u3 forecast prediction, and local XAI.
- Follow-up:
  - User asked to use the newly trained ABD-normalized models instead of the previous active models.
  - Verified local and public `/api/v1/dd-laminate/models` both expose the active keys with `*_abd_v1` model paths.
  - Removed previous active model/report folders from the Windows bundle include list so migration packages favor the current ABD-normalized model set.
  - Updated iOS DD Laminate test fixtures to expect `models/dd_laminate_u3_forecast_physics_abd_v1` for the active u3 ML/DL models.
  - Searched app/backend/frontend/package references and confirmed no stale previous active paths remain for:
    `dd_laminate_response_physics_xai_v2`, `dd_laminate_response_goint_physics_nn_v2`,
    `dd_laminate_u3_forecast_physics_v3`, and their previous XAI report folders.
  - Verification: backend/package `py_compile` passed, and `swift test --package-path ios/DDLaminateMVP` passed 11 tests.

## 2026-07-09 - Laminate RAG TAC vs DD PPT Added
- User added `/Users/danlee/KyulAI_codex/data/PPT/TAC vs DD.pptx` and asked to reflect it in Laminate RAG.
- Read the PPT and extracted 6 slides:
  - DD vs TAC stacking sequence comparison.
  - TAC has more angle-pair freedom and can intentionally create nonzero `B16*`/`B26*`.
  - DD Case 1 vs Case 2: same angle counts can have different `D*`; Case 1 is the more balanced DD baseline.
  - TAC Case 3 vs Case 4: Case 4 is the better balanced 8-ply TAC representative; Case 3 is a high-`D11*` specialized case.
  - TAC Case 5 vs Case 6: Case 6 is the better 6-ply TAC representative for weight-reduction/balance; Case 5 is specialized for maximum x-direction `D11*`.
  - Overall recommendation: Case 1 DD remains safest baseline; Case 4 is best 8-ply TAC alternative; Case 6 is best 6-ply TAC alternative when weight saving is prioritized.
- Added summary document:
  - `/Users/danlee/KyulAI_codex/docs/DD_Laminate_TAC_vs_DD_PPT_Basis.md`
- Rebuilt local RAG index:
  - `/Users/danlee/KyulAI_codex/data/rag/knowledge_index.json`
  - New count: 242 chunks, 62 sources.
- Improved local extractive fallback so TAC/DD comparison questions can include compact source takeaways without disturbing generic fallback behavior.
- Restarted DD/Laminate server on port 8000 so the RAG answer code update is live.
- App impact:
  - Web, iOS, and Android Laminate Assistant all call the server `/api/v1/rag/answer` endpoint, so the new TAC vs DD knowledge is available to apps through the shared backend without a new app build.
  - Android currently calls the Laminate RAG endpoint through `https://laminate.imperialax.com`; this is still live and backed by the same updated server/index.
- Verification:
  - `scripts/rag_query_index.py "TAC와 DD 차이 B16 B26 Case4 Case6"` returns `TAC vs DD.pptx` as top hits.
  - `scripts/rag_answer.py "TAC와 DD를 비교할 때 D11만 보면 안 되는 이유는?" --top-k 6 --language ko` returns a Korean answer grounded in `TAC vs DD.pptx` and the new basis doc.
  - Local `/api/v1/rag/answer` with `use_llm=false` returns citations from `DD Laminate TAC vs DD PPT Basis` and `TAC vs DD`.
  - `pytest tests/unit/test_rag_answer.py tests/unit/test_rag_knowledge_index.py tests/backend/test_rag_api.py -q` passed: 21 tests.

## 2026-07-09 - iOS ImperialAXMVPHost Xcode Priors Cache Fix
- User reported `SwiftDriver.ModuleDependencyGraph.ReadError error 14` while Xcode tried to read `KyulAIDDLaminateCore-primary.priors` under `DerivedData`.
- Treated this as stale/corrupt Xcode incremental build cache rather than a source-code error.
- Removed only the ImperialAX host build caches:
  - `/Users/danlee/Library/Developer/Xcode/DerivedData/ImperialAXMVPHost-*`
  - `/Users/danlee/KyulAI_codex/ios/ImperialAXMVPApp/.derived-data`
- Re-resolved Swift package dependencies for:
  - `/Users/danlee/KyulAI_codex/ios/ImperialAXMVPApp/ImperialAXMVPHost.xcodeproj`
  - Scheme: `ImperialAXMVPHost`
- Verification:
  - `xcodebuild -resolvePackageDependencies -project /Users/danlee/KyulAI_codex/ios/ImperialAXMVPApp/ImperialAXMVPHost.xcodeproj -scheme ImperialAXMVPHost` succeeded.
  - Simulator build with `CODE_SIGNING_ALLOWED=NO` succeeded.
- Recommendation:
  - Reopen Xcode if it was already open, run Clean Build Folder once, then build/run again on the device.
  - If a new device build failure appears after this cache reset, the next likely area is signing/provisioning rather than the `.priors` cache.

## 2026-07-09 - App Laminate XAI Korean Translation Fix
- User reported that the Laminate app section titled "Why this prediction?" still showed English content on the Korean page.
- Added Android shared XAI localization helper:
  - `/Users/danlee/KyulAI_codex/android/ImperialAXMVP/app/src/main/java/com/imperialax/app/LaminateXaiText.kt`
- Updated Android Laminate input/recent-result and result-detail XAI cards to localize:
  - Section title: "왜 이런 예측이 나왔나요?"
  - XAI summary text
  - Method / Feature set labels
  - Feature names, categories, explanations
  - "Show more / hide extra features" toggle text
- Updated iOS Laminate result XAI translation map to include newer normalized-CLT summary variants for Laminate Forecast and u3 Forecast.
- Verification:
  - Android `gradle -p android/ImperialAXMVP :app:compileDebugKotlin` succeeded using local JetBrains JBR as `JAVA_HOME`.
  - iOS `swift test --package-path ios/DDLaminateMVP` passed 11 tests.

## 2026-07-10 - ImperialAX Product Page Copy Draft for Laminate Forecast
- User wants to add the jointly built Laminate product to `imperialaxkorea.com > 제품소개`.
- Checked the public ImperialAX product page/search snippets and existing product tone: CAE/engineering software descriptions are organized around problem, functions, application fields, and expected value.
- Created a product-page draft document:
  - `/Users/danlee/KyulAI_codex/docs/ImperialAX_Laminate_Product_Page_Draft.md`
- Draft includes:
  - Product name candidates and recommended title.
  - Full Korean HTML-style product description for `ImperialAX Laminate Forecast`.
  - Short product-card copy and one-line intro.
  - Supported Case formulas.
  - Core functions: Type prediction, Pt prediction, response curve, u3 Forecast, Physics XAI, Design-space Insight, AI Assistant/RAG.
  - Application areas and expected benefits.
  - Technical composition and validation caution language.
  - 60-second video storyboard, required visual materials, and narration script.

## 2026-07-10 - Laminate Product Page Screenshots
- User asked whether Codex could capture screenshots/photos for the product page.
- Generated Korean Laminate Forecast web screenshots from `https://laminate.imperialax.com/index-v2.ko.html` into:
  - `/Users/danlee/KyulAI_codex/docs/product-assets/screenshots/`
- Captures:
  - `laminate-01-overview.png`
  - `laminate-02-input-panel.png`
  - `laminate-03-result-top.png`
  - `laminate-04-response-curve.png`
  - `laminate-05-xai.png`
  - `laminate-06-design-space.png`
  - `laminate-07-u3-result.png`
  - `laminate-08-u3-curve.png`
- During capture QA, noticed the Korean web XAI summary still had an English fallback for the new ABD-normalized Laminate Forecast summary.
- Patched `src/frontend/dd-laminate/app-v2.js` in both active workspace roots to localize:
  - `This explanation uses the Laminate Forecast Machine Learning model... with ABD terms normalized as A/h, 2B/h², and 12D/h³.`
- Re-captured the XAI screenshot after confirming the summary appears in Korean.
- Updated `/Users/danlee/KyulAI_codex/docs/ImperialAX_Laminate_Product_Page_Draft.md` with the screenshot list.

## 2026-07-10 - ImperialAX Laminate Product Page Zip Package
- User asked to package only the needed files for uploading from another PC.
- Created upload package folder:
  - `/Users/danlee/KyulAI_codex/dist/imperialax-laminate-product-page-20260710/`
- Included only:
  - `ImperialAX_Laminate_Product_Page_Draft.md`
  - `README.md`
  - 8 screenshot PNGs under `images/`
- Created zip:
  - `/Users/danlee/KyulAI_codex/dist/imperialax-laminate-product-page-20260710.zip`
- Zip size: about 1.8 MB.

## 2026-07-10 - AniForm-Style Laminate Product HTML
- User provided the current AniForm product page source code and asked to remake the Laminate product copy in the same style.
- Read the AniForm source:
  - `m3d` wrapper and 1100px layout.
  - Red-dot list style.
  - `details/summary` accordion sections.
  - 3-column feature cards with 16:9 images.
- Created AniForm-style Laminate HTML:
  - `/Users/danlee/KyulAI_codex/docs/ImperialAX_Laminate_Product_Page_AniFormStyle.html`
- Structure:
  - Intro / positioning.
  - AI-based laminate screening.
  - Response curve and transition load prediction.
  - Physics XAI.
  - Design-space insight and recommendation.
  - u3 Forecast.
  - AI Assistant and knowledge base.
- Uses the screenshot package image paths as `images/laminate-*.png`.
- Updated the upload package and regenerated:
  - `/Users/danlee/KyulAI_codex/dist/imperialax-laminate-product-page-20260710.zip`
- Updated package README to explain the new `ImperialAX_Laminate_Product_Page_AniFormStyle.html` file.

## 2026-07-10 - AniForm-Style Product HTML With Explicit Image Placement
- User clarified that the source code should include the screenshots already placed at appropriate locations, not only separate image assets.
- Created final recommended HTML:
  - `/Users/danlee/KyulAI_codex/docs/ImperialAX_Laminate_Product_Page_AniFormStyle_FINAL.html`
- Changes:
  - Added a top representative hero image using `images/laminate-01-overview.png`.
  - Kept function-specific card images for input, result, curve, XAI, design-space, and u3 sections.
  - Added captions and CSS for the hero image block.
  - Image placement now includes 9 `<img>` tags: one hero plus eight feature/card placements.
- Copied the final HTML into the upload package and regenerated:
  - `/Users/danlee/KyulAI_codex/dist/imperialax-laminate-product-page-20260710.zip`
- Updated package README to recommend using `ImperialAX_Laminate_Product_Page_AniFormStyle_FINAL.html` first.

## 2026-07-10 - Copy/Paste Source Text for ImperialAX Product Admin
- User clarified they want a source text file to paste into the product admin source editor, not just an `.html` artifact.
- Created:
  - `/Users/danlee/KyulAI_codex/docs/ImperialAX_Laminate_Product_Page_Source_For_Upload.txt`
- Content is identical to the final image-placed AniForm-style source.
- Copied it into the upload package and regenerated:
  - `/Users/danlee/KyulAI_codex/dist/imperialax-laminate-product-page-20260710.zip`
- Updated README to instruct using `ImperialAX_Laminate_Product_Page_Source_For_Upload.txt` for copy/paste.

## 2026-07-10 - ImperialAX Laminate Representative Image
- User asked to create a representative image for the Laminate product page.
- Generated screenshot-based 16:9 representative assets:
  - `/Users/danlee/KyulAI_codex/docs/product-assets/representative/imperialax-laminate-forecast-representative-1200x675.png`
  - `/Users/danlee/KyulAI_codex/docs/product-assets/representative/imperialax-laminate-forecast-representative-1200x675.jpg`
  - `/Users/danlee/KyulAI_codex/docs/product-assets/representative/imperialax-laminate-forecast-representative-1600x900.png`
  - `/Users/danlee/KyulAI_codex/docs/product-assets/representative/imperialax-laminate-forecast-representative-1600x900.jpg`
- Design uses ImperialAX palette, Laminate Forecast title, Korean summary, feature pills, and real web UI screenshots.
- Added the assets to the upload package under:
  - `/Users/danlee/KyulAI_codex/dist/imperialax-laminate-product-page-20260710/representative/`
- Updated package README with representative image recommendations.
- Regenerated:
  - `/Users/danlee/KyulAI_codex/dist/imperialax-laminate-product-page-20260710.zip`

## 2026-07-10 - ImperialAX Product-Page-Fit Laminate Assets and Modern Source
- User clarified the ImperialAX product page needs a square product photo matching the product list/detail style, not only a 16:9 representative banner.
- Checked the live ImperialAX product list/detail pages:
  - Product list uses 350x350 thumbnail-style product images.
  - Current Laminate page source had `object-fit: cover`, causing UI screenshots to be cropped inside cards.
- Generated square product-photo assets:
  - `/Users/danlee/KyulAI_codex/docs/product-assets/representative/imperialax-laminate-product-thumb-350x350.png`
  - `/Users/danlee/KyulAI_codex/docs/product-assets/representative/imperialax-laminate-product-thumb-350x350.jpg`
  - `/Users/danlee/KyulAI_codex/docs/product-assets/representative/imperialax-laminate-product-thumb-700x700.png`
  - `/Users/danlee/KyulAI_codex/docs/product-assets/representative/imperialax-laminate-product-thumb-700x700.jpg`
  - `/Users/danlee/KyulAI_codex/docs/product-assets/representative/imperialax-laminate-product-thumb-1000x1000.png`
  - `/Users/danlee/KyulAI_codex/docs/product-assets/representative/imperialax-laminate-product-thumb-1000x1000.jpg`
- Created a new Laminate-specific product detail source that does not inherit the AniForm card-crop structure:
  - `/Users/danlee/KyulAI_codex/docs/ImperialAX_Laminate_Product_Page_Source_Modern.txt`
  - `/Users/danlee/KyulAI_codex/docs/ImperialAX_Laminate_Product_Page_Modern.html`
- Modern source uses:
  - Screenshot-first sections.
  - `object-fit: contain`.
  - Wide feature rows instead of cropped image cards.
  - Case formulas, response curve, Physics XAI, Design-space, u3 Forecast, and AI Assistant sections.
- Copied modern source and square representative images into:
  - `/Users/danlee/KyulAI_codex/dist/imperialax-laminate-product-page-20260710/`
- Updated README to recommend:
  - `ImperialAX_Laminate_Product_Page_Source_Modern.txt` for product detail source.
  - `representative/imperialax-laminate-product-thumb-700x700.png` for product main/list image.
- Regenerated:
  - `/Users/danlee/KyulAI_codex/dist/imperialax-laminate-product-page-20260710.zip`
- Follow-up: User asked to make the square product image name appear on one line as `Laminate | Forecast AI`.
- Regenerated the 350x350, 700x700, and 1000x1000 square product thumbnail PNG/JPG files.
- Re-copied updated thumbnails into the upload package and regenerated the same zip.
- Follow-up: User asked to remove the `|`, remove the non-white/background area, and make the product-name font bolder.
- Updated square product thumbnails to use one-line `Laminate Forecast AI`, a heavier font, and transparent PNG background outside the white product card.
- Added explicit transparent files:
  - `imperialax-laminate-product-thumb-transparent-350x350.png`
  - `imperialax-laminate-product-thumb-transparent-700x700.png`
  - `imperialax-laminate-product-thumb-transparent-1000x1000.png`
- Verified alpha channel on the 700x700 transparent PNG; corner pixels are fully transparent.
- Updated README to recommend `representative/imperialax-laminate-product-thumb-transparent-700x700.png`.
- Regenerated the upload zip.
- Follow-up: User asked for the Design-space insight result image to be scrollable and for the product detail source fonts to be smaller.
- Updated `/Users/danlee/KyulAI_codex/docs/ImperialAX_Laminate_Product_Page_Source_Modern.txt`:
  - Reduced hero/title/body/card/list/table font sizes.
  - Added `.screenBox.scroll` with vertical scrolling.
  - Applied `class="screenBox tall scroll"` to the Design-space map figure.
- Synced the modern `.html` preview and upload package files, then regenerated the zip.
- Follow-up: User asked to show that SETUP reflects the input angles in the ply stack preview, and to simplify the Prediction Result section so it shows mainly the result image.
- Created a focused setup crop:
  - `/Users/danlee/KyulAI_codex/docs/product-assets/screenshots/laminate-09-setup-ply-stack.png`
  - Shows the forecast setup controls next to the live `각도 반영 ply stack` preview.
- Updated modern source:
  - SETUP section now uses `laminate-09-setup-ply-stack.png`.
  - SETUP copy now explicitly mentions real-time ply stack preview from θ input.
  - Prediction Result section now uses a result-only layout and makes the long result screenshot scrollable.
- Copied the new image into the upload package `images/` folder, updated README from 8 to 9 screenshots, and regenerated the zip.
- Follow-up: User said the FORECAST SETUP image was still too small/cropped.
- Regenerated `laminate-09-setup-ply-stack.png` at 1280x860 using the complete input panel and a larger ply stack preview crop.
- Updated the SETUP article to use the full-width `feature resultOnly` layout instead of the two-column layout.
- Added `.screenBox.setupFull img { max-height: none; }` so the setup image is not height-limited.
- Synced the source, preview HTML, package image, and regenerated the zip.
- Follow-up: User reported the `∓` character was not rendering on the homepage.
- Replaced `∓θ` in the supported-case formulas with `opposite ±θ` text for better CMS/font compatibility.
- Synced source/preview/package files and regenerated the zip.

## 2026-07-10 - ImperialAX Laminate product page formula entity fix
- User clarified that the `∓` symbol must appear in the supported-case formulas, even though the homepage/CMS may not read the literal character correctly.
- Updated the modern product-page upload source to use HTML numeric entity `&#8723;` instead of literal `∓` or the temporary `opposite ±θ` text.
- Current supported-case formulas in upload source:
  - Case 3: `[[±θ₁]/[±θ₂]/[&#8723;θ₂]/[&#8723;θ₂]]₂`
  - Case 4: `[([±θ₁]/[±θ₂])₂ / ([&#8723;θ₁]/[&#8723;θ₂])₂]`
- Added math/symbol-capable font fallbacks to `.formula`: `Cambria Math`, `STIX Two Math`, `DejaVu Sans`, `Segoe UI Symbol`, `Apple Symbols`.
- Synced `docs/ImperialAX_Laminate_Product_Page_Source_Modern.txt` to the preview HTML and the package copy.
- Regenerated `/Users/danlee/KyulAI_codex/dist/imperialax-laminate-product-page-20260710.zip`.

## 2026-07-10 - ImperialAX Laminate product page site link
- User asked whether the product page includes the demo/site URL at the bottom.
- Added a bottom CTA site link to the modern upload source:
  - `https://laminate.imperialax.com/`
- Added `.siteLink` styling so the URL appears as a clear white pill button inside the final CTA block, with mobile-safe line breaking.
- Synced the modern source to preview/package HTML and regenerated `/Users/danlee/KyulAI_codex/dist/imperialax-laminate-product-page-20260710.zip`.

## 2026-07-10 - ImperialAX Laminate product page accordion and spacing update
- User requested the modern product-page source to adopt the collapsible `details/summary` style seen in `ImperialAX_Laminate_Product_Page_AniFormStyle_FINAL.html`.
- Reworked the modern upload source into six collapsible accordion sections:
  - AI-based laminate screening / Why it matters
  - Workflow
  - Forecast setup and prediction result
  - Response curve and Pt prediction
  - Physics XAI and Design-space insight
  - u3 Forecast and AI Assistant
- Kept the content dense rather than reducing it; existing screenshots and explanatory copy remain included.
- Moved `Double-Double 적층 패턴` into the first accordion section below the three summary cards.
- Added `.casePanel` styling and `margin-top: 30px` to create clear spacing between the three summary cards and the supported-case formula block.
- Continued using `&#8723;` HTML entity for the required `∓` symbol in Case 3 and Case 4 formulas.
- Synced the modern source to preview/package HTML and regenerated `/Users/danlee/KyulAI_codex/dist/imperialax-laminate-product-page-20260710.zip`.

## 2026-07-15 - Laminate greenfield Codex rebuild package
- User asked for a package so his brother can rebuild only the Laminate portion from scratch on another PC using Codex.
- Created data-only/source-free rebuild package at:
  `/Users/danlee/KyulAI_codex/dist/laminate_greenfield_codex_20260715`
- Created zip:
  `/Users/danlee/KyulAI_codex/dist/laminate_greenfield_codex_20260715.zip`
- Zip size verified: about 460 MB. Unzipped package size: about 594 MB.
- Intentionally excluded existing app/server/trained-model code so a new Codex session can implement from scratch.
- Included data:
  - `data/datasets/Double-Double` raw source data, excluding redundant `p1.zip`, `u3.zip`, `.DS_Store`, and `desktop.ini`.
  - `data/datasets/DD_cases_2_3_4_curated_v1` 900-record curated Case2/3/4 Laminate Forecast dataset.
  - `data/datasets/DD_u3_pt_v2` 566-record u3 forecast dataset.
  - `data/PPT/Final ver2.pptx` and `data/PPT/TAC vs DD.pptx`.
- Included references:
  - `CS_DDpaper.pdf`
  - `DD_Laminate_PPT_Basis.md`
  - `DD_Laminate_TAC_vs_DD_PPT_Basis.md`
  - `DD_Laminate_AI_Current_Summary.md`
  - `dd_double_double_data_audit_2026-05-29.md`
  - `dd_laminate_greenfield_flow.md`
  - `DD_Laminate_Research_Context.md`
  - GointMLP reference source under `references/gointmlp/GointMLP-master`.
  - UI screenshots under `references/product-assets/screenshots`.
- Added new package docs:
  - `00_START_HERE.md`
  - `docs/01_RESEARCH_CONTEXT.md`
  - `docs/02_DATA_MANIFEST.md`
  - `docs/03_IMPLEMENTATION_SPEC.md`
  - `docs/04_MODELING_AND_XAI_SPEC.md`
  - `docs/05_CODEX_BOOTSTRAP_PROMPT.md`
  - `docs/06_ACCEPTANCE_TESTS.md`
  - `docs/07_NEW_PC_SETUP.md`
  - `docs/README_FOR_DATA_ONLY_REBUILD.md`
  - `PACKAGE_CONTENTS.txt`
- Verified zip contains key files:
  - `00_START_HERE.md`
  - `docs/05_CODEX_BOOTSTRAP_PROMPT.md`
  - `data/datasets/DD_cases_2_3_4_curated_v1/label_manifest.csv`
  - `data/datasets/DD_u3_pt_v2/manifest.csv`

## 2026-07-15 - Added Cloudflare/server deployment guide to Laminate greenfield package
- User asked whether Cloudflare/server setup instructions are included in the Laminate greenfield Codex rebuild package.
- They were not included initially because the package was intentionally data/spec focused and excluded deployment settings.
- Added `/Users/danlee/KyulAI_codex/dist/laminate_greenfield_codex_20260715/docs/08_DEPLOYMENT_CLOUDFLARE_SERVER.md`.
- The deployment guide covers:
  - local FastAPI/frontend server layout,
  - single-port vs split frontend/backend deployment,
  - Cloudflare Tunnel purpose,
  - dashboard token-based tunnel setup,
  - locally-managed named tunnel setup,
  - Windows `cloudflared` service registration,
  - Windows Task Scheduler/NSSM direction for keeping FastAPI alive,
  - `.env` example,
  - `/health` and `/ready`,
  - troubleshooting 502/1033/origin-down scenarios,
  - prompt for future Codex to create deployment scripts.
- Updated package `00_START_HERE.md` and `docs/05_CODEX_BOOTSTRAP_PROMPT.md` to reference the new deployment guide.
- Regenerated `/Users/danlee/KyulAI_codex/dist/laminate_greenfield_codex_20260715.zip` and verified the new MD is included.

## 2026-07-15 - Added Windows EXE packaging guide to Laminate greenfield package
- User asked whether Laminate Forecast can be made as a Windows `.exe` like most CAE software.
- Answer: yes, recommended route is desktop wrapper + bundled backend/model, not just a web URL shortcut.
- Added `/Users/danlee/KyulAI_codex/dist/laminate_greenfield_codex_20260715/docs/09_WINDOWS_EXE_PACKAGING.md`.
- The EXE guide covers:
  - Tauri/Electron desktop wrapper + Python/FastAPI backend option,
  - PyInstaller-only local server launcher option,
  - cloud server + EXE URL launcher option,
  - recommended build sequence,
  - backend PyInstaller example,
  - frontend build strategy,
  - model/data inclusion strategy,
  - offline vs server inference tradeoffs,
  - first target as portable folder before installer,
  - prompt for future Codex to create EXE packaging scripts.
- Updated package `00_START_HERE.md` and `docs/05_CODEX_BOOTSTRAP_PROMPT.md` to reference `09_WINDOWS_EXE_PACKAGING.md`.
- Regenerated `/Users/danlee/KyulAI_codex/dist/laminate_greenfield_codex_20260715.zip` and verified the new MD is included.

## 2026-07-15 - Prepared Windows EXE packaging scripts on Mac
- User asked to prepare `.exe` packaging code/scripts on the Mac before moving to Windows.
- Added Windows build kit under:
  `/Users/danlee/KyulAI_codex/dist/laminate_greenfield_codex_20260715/packaging/windows`
- Added files:
  - `README_WINDOWS_EXE_BUILD.md`
  - `Build-WindowsExe.ps1`
  - `Build-BackendExe.ps1`
  - `Build-Frontend.ps1`
  - `Make-PortableBundle.ps1`
  - `Check-PortableBundle.ps1`
  - `templates/laminate_backend_launcher.py`
  - `templates/laminate_desktop_launcher.py`
  - `templates/laminate_backend.spec.template`
- Build kit target: first portable Windows folder, not installer:
  `dist/windows/LaminateForecast-win-x64-portable/`
  with `LaminateForecast.exe`, `backend/laminate_backend.exe`, frontend assets, models, and `README_RUN.md`.
- Updated:
  - `00_START_HERE.md`
  - `docs/05_CODEX_BOOTSTRAP_PROMPT.md`
  - `docs/09_WINDOWS_EXE_PACKAGING.md`
  to reference `packaging/windows` scripts.
- Verified Python launcher templates with `python3 -m py_compile`.
- `pwsh` is not installed on this Mac, so PowerShell scripts were not executed locally; final validation must happen on Windows.
- Regenerated `/Users/danlee/KyulAI_codex/dist/laminate_greenfield_codex_20260715.zip` and verified packaging files are included.

## 2026-07-15 - Added license login gate for existing Laminate EXE packaging
- User clarified the previous greenfield package was for brother's Codex to rebuild from scratch; this pass targets the already-built Laminate app.
- Implemented a Laminate license/login gate using the existing ImperialAX auth system instead of inventing a separate license database.
- Added frontend gate:
  - `/Users/danlee/KyulAI_codex/src/frontend/dd-laminate/auth-gate.js`
  - Included from `index-v2.html` and `index-v2.ko.html` before `app-v2.js`.
  - Requires a real logged-in user with `module.laminate`; tokenless default-enabled catalog access no longer passes the gate.
  - Wraps `fetch` so Laminate/RAG/Optimization API calls receive the saved bearer token.
  - Adds a password visibility toggle and bilingual Korean/English copy.
- Added CSS for the license overlay in `styles-v2.css`.
- Added backend enforcement switch in `src/backend/dd_laminate_app.py`:
  - `LAMINATE_REQUIRE_AUTH=1` makes `/api/v1/dd-laminate/*` require a bearer token with `module.laminate`.
  - Path roots can now be supplied via `KYULAI_PROJECT_ROOT`, `LAMINATE_FRONTEND_DIR`, `IMPERIALAX_FRONTEND_DIR`, `WEDDING_FRONTEND_DIR`, and `WEDDING_DATA_DIR` for packaged execution.
- Added demo-login kill switch in `src/backend/api/v1/modules.py`:
  - `IMPERIALAX_DISABLE_DEMO_LOGIN=1` disables `/api/v1/modules/auth/demo-login`.
- Added existing-app Windows EXE packaging kit:
  - `scripts/windows/exe/Build-LaminateExe.ps1`
  - `scripts/windows/exe/Create-LaminateUser.ps1`
  - `scripts/windows/exe/laminate_backend_launcher.py`
  - `scripts/windows/exe/laminate_desktop_launcher.py`
  - `scripts/windows/exe/README_LAMINATE_EXISTING_EXE.md`
- Added package note:
  - `/Users/danlee/KyulAI_codex/docs/LAMINATE_EXISTING_EXE_PACKAGE.md`
- Intended Windows build behavior:
  - create licensed users with `Create-LaminateUser.ps1`, granting only `module.laminate`;
  - run `Build-LaminateExe.ps1` on Windows;
  - output portable bundle at `dist/windows/LaminateForecast-existing-win-x64-portable`;
  - `LaminateForecast.exe` starts the local backend with auth required and demo login disabled.
- Mac-side validation still needed: py_compile/import checks; PowerShell/PyInstaller build must be validated on Windows.
- Follow-up refinement in the same pass:
  - `auth-gate.js` now activates the login overlay only when the backend actually requires auth, detected by probing `/api/v1/dd-laminate/models` without a token and receiving 401/403.
  - This avoids accidentally locking the public web deployment unless the server is started with `LAMINATE_REQUIRE_AUTH=1`.
  - Expired/invalid local sessions are cleared and only block the UI in auth-required mode.
- Verification:
  - `python3 -m py_compile` passed for backend/app launcher files.
  - `node --check src/frontend/dd-laminate/auth-gate.js` passed.
  - FastAPI TestClient with `LAMINATE_REQUIRE_AUTH=1` verified: no token -> 401, password login -> 200, bearer token -> 200 for Laminate models, demo login -> 403.

## 2026-07-15 - Created existing Laminate EXE build kit ZIP
- User asked for a ZIP containing the organized files needed to move the existing Laminate EXE build work to a Windows PC.
- Created staging folder:
  `/Users/danlee/KyulAI_codex/dist/laminate_existing_exe_buildkit_20260715`
- Created ZIP:
  `/Users/danlee/KyulAI_codex/dist/laminate_existing_exe_buildkit_20260715.zip`
- ZIP size: about 492 MB; unzipped staging folder size: about 792 MB.
- Included:
  - `README_START_HERE.md`
  - `scripts/windows/exe/*` build and account scripts
  - `docs/LAMINATE_EXISTING_EXE_PACKAGE.md`
  - current Laminate backend/frontend/auth-gate source
  - ImperialAX login frontend source
  - current ABD-normalized active Laminate/u3 model folders
  - current XAI report folders
  - RAG knowledge index and minimal DD design-space manifests
  - `requirements-serving.txt`, `requirements-ml.txt`, `pyproject.toml`
- Verified ZIP contains key files including `Build-LaminateExe.ps1`, `Create-LaminateUser.ps1`, `auth-gate.js`, `dd_laminate_app.py`, active model folders, `knowledge_index.json`, and design-space manifests.

## 2026-07-15 - Built Laminate Forecast Distillation v1
- User asked to try the first Foundation Model / Distillation direction by creating "Distillation v1".
- Added training script:
  `/Users/danlee/KyulAI_codex/scripts/dd_response_distillation_train.py`
- Teacher:
  `models/dd_laminate_response_physics_abd_v1/response_surrogate.joblib`
  (`response_surrogate_physics_v2`, the active Laminate Forecast Machine Learning model).
- Student:
  `models/dd_laminate_response_distilled_v1/response_goint.pt`
  and compatibility copy `response_distilled.pt`.
- Student architecture:
  compact `DDResponseGointSurrogate`, 35 `theta_physics_v2` inputs, 128-point curve output, hidden dim 64, 6 branches, dropout 0.10.
- Distillation objective:
  hard true Type/scalar/curve losses plus soft teacher Type probabilities, teacher scalar targets, and teacher curve targets.
- Training dataset:
  `data/datasets/DD_cases_2_3_4_curated_v1`, 900 samples.
- Cross-validation result:
  - Type accuracy: 0.9378 +/- 0.0119
  - Macro F1: 0.9352 +/- 0.0156
  - Teacher Type agreement: 0.9378
  - Pt MAE: 739.90 kips
  - Max force MAE: 1271.80 kips
  - Curve normalized RMSE: 0.01864
- Interpretation:
  Distilled v1 is very small (~1 MB) and close to the tree teacher for Type classification, but still worse than the active Machine Learning teacher for Pt/curve accuracy. Keep it as an experimental compact deployment/comparison model, not the default production replacement yet.
- Added model registry key:
  `response_distilled_v1` with label `Laminate Forecast - Distilled NN`.
- Connected Distilled NN to:
  - backend Laminate model listing, prediction, warm preload, local XAI
  - optimization deep-model routing
  - web model dropdown order
  - iOS and Android model key/label normalization
  - Windows portable bundle include list
- Generated dedicated Distilled XAI prior:
  `/Users/danlee/KyulAI_codex/reports/dd_response_xai_distilled_v1/response_feature_importance.csv`
  from live local masking over all 900 training inputs.
- Distilled XAI top global features from the generated report:
  `angle_abs_std`, `angle_min_abs`, `b_coupling_norm`, `abs_theta1`, `d66`.
- Verification:
  - `python -m py_compile` passed for `dd_laminate.py`, `optimization.py`, and `dd_response_distillation_train.py`.
  - `node --check` passed for `src/frontend/dd-laminate/app-v2.js` and `app.js`.
  - FastAPI TestClient `/api/v1/dd-laminate/models` returns:
    `response_surrogate_physics_v2`, `response_goint_physics_nn_v2`, `response_distilled_v1`.
  - FastAPI TestClient `/predict/response` and `/xai/local` returned 200 for all three Laminate Forecast models.

## 2026-07-15 - Cleaned and classified mixed worktree
- User noted that the current worktree had many previous changes mixed with the new Distillation v1 work and asked to clean it up.
- Used the AI slop cleanup workflow:
  - locked behavior with targeted compile/syntax/unit/API checks before claiming cleanup;
  - avoided deleting user data or feature artifacts;
  - only hid confirmed local runtime/Xcode state via `.gitignore`.
- Added `.gitignore` entries:
  - `runtime/`
  - `**/*.xcodeproj/project.xcworkspace/`
- This removed local server logs, wedding runtime submissions/admin token, and Xcode user workspace state from `git status`.
- Added cleanup classification document:
  `/Users/danlee/KyulAI_codex/docs/WORKTREE_CLEANUP_20260715.md`
- Classification highlights:
  - Keep as functional work: Distillation v1, ABD-normalized active models, EXE auth packaging, Laminate RAG/TAC-vs-DD, app/web UI parity, product-page assets, ImperialAX branding assets, Cloudflare/server config.
  - Large artifacts needing intentional commit/bundle choice:
    `models/dd_laminate_response_physics_abd_v1` (~453 MB),
    `models/dd_laminate_u3_forecast_physics_abd_v1` (~324 MB),
    `icons/imperialAX` (~66 MB).
- Fallback review:
  - Existing broad `except Exception` / frontend `catch` paths were classified as grounded compatibility/fail-safe fallbacks for model loading, optional XAI, and UI/network availability.
  - No masking fallback was removed in this pass because changing those paths would need a dedicated behavior/test pass.
- Verification:
  - Python compile passed for Laminate backend, optimization, app launcher, distillation training script, and Windows EXE launcher scripts.
  - JS syntax checks passed for Laminate v2, Laminate legacy, Laminate auth gate, and Simple Injection v2.
  - RAG unit test passed: 14 tests.
  - FastAPI Laminate model/predict/XAI smoke passed for Machine Learning, Deep Learning, and Distilled NN.
  - iOS `swift test` passed in `ios/DDLaminateMVP`: 11 tests.
  - Android `gradle -p android/ImperialAXMVP :app:assembleDebug` was blocked by missing Java 17 toolchain on this Mac, before Kotlin/Java compilation.

## 2026-07-15 - Built Laminate Forecast synthetic theta/case grid distillation v2
- User asked to try `synthetic theta/case grid distillation`.
- Extended `/Users/danlee/KyulAI_codex/scripts/dd_response_distillation_train.py` so the compact student can train on:
  - the real 900 Case2/Case3/Case4 curated Laminate samples;
  - synthetic theta/case grid pseudo-labels generated by the active Machine Learning teacher.
- Synthetic grid settings used:
  - theta range: -90 to 90 degrees
  - grid step: 5 degrees
  - cases: Case2, Case3, Case4
  - pseudo-labeled samples: 4107
  - synthetic sample weight: 0.35
- Teacher:
  `models/dd_laminate_response_physics_abd_v1/response_surrogate.joblib`
  (`response_surrogate_physics_v2`).
- Student output:
  `/Users/danlee/KyulAI_codex/models/dd_laminate_response_distilled_grid_v1/response_goint.pt`
  and compatibility copy `response_distilled.pt`.
- Cross-validation result:
  - Type accuracy: 0.9767 +/- 0.0133
  - Macro F1: 0.9775 +/- 0.0139
  - Teacher Type agreement: 0.9767
  - Pt MAE: 490.16 kips
  - Max force MAE: 691.92 kips
  - Curve normalized RMSE: 0.01073
- Comparison against Distillation v1:
  - v1 Type accuracy: 0.9378 -> v2 0.9767
  - v1 Macro F1: 0.9352 -> v2 0.9775
  - v1 Pt MAE: 739.90 kips -> v2 490.16 kips
  - v1 curve normalized RMSE: 0.01864 -> v2 0.01073
- Added model registry key:
  `response_distilled_grid_v1` with label `Laminate Forecast - Distilled NN v2`.
- Updated default visible Laminate Forecast model lists on backend, web, iOS, Android, and Windows bundle packaging so the visible models are:
  `response_surrogate_physics_v2`, `response_goint_physics_nn_v2`, and `response_distilled_grid_v1`.
- Generated dedicated XAI prior:
  `/Users/danlee/KyulAI_codex/reports/dd_response_xai_distilled_grid_v1/response_feature_importance.csv`
  from live local masking over all 900 real training inputs.
- Distilled Grid v2 XAI top global features from the generated report:
  `angle_abs_std`, `angle_min_abs`, `b_coupling_norm`, `abs_theta1`, `d66`, `angle_abs_mean`, `angle_max_abs`, `d12`, `a12`, `a66`.
- Verification:
  - `python -m py_compile` passed for `dd_laminate.py`, `optimization.py`, and `dd_response_distillation_train.py`.
  - `node --check` passed for `src/frontend/dd-laminate/app-v2.js` and `app.js`.
  - FastAPI TestClient `/api/v1/dd-laminate/models` returns:
    `response_surrogate_physics_v2`, `response_goint_physics_nn_v2`, `response_distilled_grid_v1`.
  - FastAPI TestClient `/predict/response` and `/xai/local` returned 200 for all three visible Laminate Forecast models.
  - iOS `swift test` passed in `ios/DDLaminateMVP`: 11 tests.

## 2026-07-15 - Improved distillation with confidence-weighted synthetic grid v3
- User asked to develop the synthetic theta/case grid distillation further.
- Added confidence-weighted pseudo-sample support to:
  `/Users/danlee/KyulAI_codex/scripts/dd_response_distillation_train.py`
- New options:
  - `--synthetic-confidence-power`
  - `--synthetic-min-confidence-weight`
  - `--model-name`
- Rationale:
  v2 assigned every synthetic teacher-labeled grid point the same weight. v3 keeps the same teacher-student setup but gives higher influence to grid points where the teacher is confident and lower influence to uncertain boundary points.
- Tried a heavier 2.5-degree grid first:
  - 15,987 synthetic samples
  - confidence-weighted effective mean weight: 0.2522
  - early folds looked strong (`pt_mae` 358.83 and 459.51), but CPU runtime was too high for a routine local training pass, so the run was intentionally interrupted and not promoted.
- Promoted practical v3-lite run:
  - Output: `/Users/danlee/KyulAI_codex/models/dd_laminate_response_distilled_grid_conf_v1/`
  - Model key: `response_distilled_grid_conf_v1`
  - Label: `Laminate Forecast - Distilled NN v3`
  - Synthetic grid step: 3.75 degrees
  - Synthetic samples: 7203
  - Synthetic base weight: 0.30
  - Synthetic confidence power: 1.5
  - Synthetic minimum confidence multiplier: 0.45
  - Synthetic effective weight mean: 0.2702
  - Teacher confidence mean: 0.9273
  - Hidden dim: 80
  - Branches: 8
  - Dropout: 0.08
- Cross-validation result:
  - Type accuracy: 0.9789 +/- 0.0124
  - Macro F1: 0.9784 +/- 0.0150
  - Teacher Type agreement: 0.9789
  - Pt MAE: 469.74 kips
  - Max force MAE: 617.01 kips
  - Curve normalized RMSE: 0.00977
- Comparison:
  - Distilled v1 Pt MAE: 739.90 kips
  - Synthetic grid v2 Pt MAE: 490.16 kips
  - Confidence-weighted grid v3 Pt MAE: 469.74 kips
  - v3 also improved curve normalized RMSE from v2's 0.01073 to 0.00977.
- Generated dedicated XAI prior:
  `/Users/danlee/KyulAI_codex/reports/dd_response_xai_distilled_grid_conf_v1/response_feature_importance.csv`
  from live local masking over all 900 real training inputs.
- v3 XAI top global features:
  `angle_abs_std`, `angle_min_abs`, `b_coupling_norm`, `abs_theta1`, `d66`, `angle_max_abs`, `angle_abs_mean`, `a66`, `abs_theta2`, `d12`.
- Updated backend/web/iOS/Android/Windows bundle visible model configuration so the visible Laminate Forecast models are now:
  `response_surrogate_physics_v2`, `response_goint_physics_nn_v2`, and `response_distilled_grid_conf_v1`.
- Verification:
  - `python -m py_compile` passed for `dd_laminate.py`, `optimization.py`, and `dd_response_distillation_train.py`.
  - `node --check` passed for `src/frontend/dd-laminate/app-v2.js` and `app.js`.
  - FastAPI TestClient `/api/v1/dd-laminate/models` returns:
    `response_surrogate_physics_v2`, `response_goint_physics_nn_v2`, `response_distilled_grid_conf_v1`.
  - FastAPI TestClient `/predict/response` and `/xai/local` returned 200 for all three visible Laminate Forecast models.
  - iOS `swift test` passed in `ios/DDLaminateMVP`: 11 tests.

## 2026-07-15 - Added automatic GPU/MPS device selection for distillation training
- User asked whether a GPU PC would be detected automatically for the heavier 2.5-degree synthetic grid distillation run.
- Updated `/Users/danlee/KyulAI_codex/scripts/dd_response_distillation_train.py`:
  - `--device` now supports `auto`, `cpu`, `mps`, and `cuda`.
  - default device is now `auto`.
  - auto priority is CUDA first, then Apple MPS, then CPU.
  - script prints the actual selected device at startup, including CUDA GPU name and compute capability when available.
  - explicit `--device cuda` now fails early if PyTorch cannot see CUDA, instead of silently running wrong.
- Added Windows helper:
  `/Users/danlee/KyulAI_codex/scripts/windows/Train-LaminateDistillationGPU.ps1`
  - checks PyTorch CUDA visibility;
  - launches the heavy Laminate distillation training with `--device auto`;
  - defaults to the 2.5-degree confidence-weighted synthetic grid settings for a GPU PC.
- Updated Windows setup:
  `/Users/danlee/KyulAI_codex/scripts/windows/Setup-WindowsServing.ps1`
  - added `-TorchBackend cpu|cuda`;
  - CPU remains default for serving;
  - `-TorchBackend cuda` installs the CUDA PyTorch wheel and prints `cuda available` plus GPU name.
- Updated Windows docs:
  - `/Users/danlee/KyulAI_codex/docs/WINDOWS_GIT_QUICKSTART.md`
  - `/Users/danlee/KyulAI_codex/docs/windows-server-migration.md`
- Verification:
  - `python -m py_compile scripts/dd_response_distillation_train.py` passed.

## 2026-07-20 - Added batch Curve CSV classification and classified 900 New_Data curves
- User asked to classify all newly delivered `data/New_Data` force-displacement CSVs and make the Curve CSV web tab support multiple CSV files at once.
- Backend update:
  - Added `/api/v1/dd-laminate/predict/curve-batch` in
    `/Users/danlee/KyulAI_codex/src/backend/api/v1/dd_laminate.py`.
  - Batch endpoint accepts multiple `files` plus optional `metadata_file`.
  - Metadata CSV can provide per-file `filename`, `theta1`, `theta2`, `pt`, `case`, and `test_id`.
  - If metadata is omitted, the form's shared theta/Pt/case inputs are reused for every selected CSV.
- Frontend update:
  - Updated `/Users/danlee/KyulAI_codex/src/frontend/dd-laminate/index-v2.html`.
  - Updated `/Users/danlee/KyulAI_codex/src/frontend/dd-laminate/index-v2.ko.html`.
  - Updated `/Users/danlee/KyulAI_codex/src/frontend/dd-laminate/app-v2.js`.
  - Updated `/Users/danlee/KyulAI_codex/src/frontend/dd-laminate/styles-v2.css`.
  - Curve CSV file input now supports `multiple`.
  - Added optional Batch metadata CSV input.
  - Single CSV still renders the original prediction card.
  - Multiple CSVs render a compact batch table with a CSV download button.
- Added script:
  `/Users/danlee/KyulAI_codex/scripts/dd_classify_new_data_curves.py`
  - Uses `models/dd_laminate_cases_2_3_4_csv_v1/curve_classifier.joblib`.
  - Optimized for batch inference by loading the joblib model once.
  - Reads:
    - `data/New_Data/6x8_Case2/transition load.csv`
    - `data/New_Data/6x8_Case3/transition load.csv`
    - `data/New_Data/6x8_Case4/transition load.csv`
    - matching `csv_6x8_Case*` force-displacement CSVs
    - matching `Original/plot_Test_*_original.png` plots
- Generated classification outputs:
  - `/Users/danlee/KyulAI_codex/reports/new_data_6x8_curve_type_classification.csv`
  - `/Users/danlee/KyulAI_codex/reports/new_data_6x8_curve_type_classification.md`
  - `/Users/danlee/KyulAI_codex/data/New_Data/classified_curve_csv_v1/`
- Classification summary:
  - Total curves: `900`
  - Case2: Type1 `78`, Type2 `167`, Type3 `55`
  - Case3: Type1 `85`, Type2 `161`, Type3 `54`
  - Case4: Type1 `64`, Type2 `183`, Type3 `53`
  - Review priority by confidence:
    - low: `139`
    - medium: `343`
    - high: `418`
- Sorted dataset:
  - copied `900` CSV files and `900` plot images into Case/Type folders under
    `/Users/danlee/KyulAI_codex/data/New_Data/classified_curve_csv_v1/`.
  - Wrote a root `classification_manifest.csv` plus per-Case/per-Type manifest files.
- Verification:
  - `python -m py_compile src/backend/api/v1/dd_laminate.py scripts/dd_classify_new_data_curves.py` passed.
  - `node --check src/frontend/dd-laminate/app-v2.js` passed.
  - `scripts/dd_classify_new_data_curves.py --no-copy` smoke test classified all `900` curves.
  - Router check confirmed `/dd-laminate/predict/curve-batch` is registered.

## 2026-07-20 - Documented Curve CSV batch file format in Korean and English
- User asked for a clear explanation of how to prepare files for the `Curve CSV` tab.
- Added bilingual guide:
  `/Users/danlee/KyulAI_codex/docs/DD_CURVE_CSV_BATCH_GUIDE.md`
- Guide covers:
  - single CSV prediction inputs;
  - batch CSV selection;
  - recommended folder structure;
  - metadata CSV format;
  - required/recommended columns:
    `filename,test_id,theta1,theta2,pt,case`;
  - how `metadata_file` is matched to uploaded force-displacement CSV files;
  - what happens when metadata is omitted;
  - current `data/New_Data` example.
- Updated UI copy in:
  - `/Users/danlee/KyulAI_codex/src/frontend/dd-laminate/index-v2.html`
  - `/Users/danlee/KyulAI_codex/src/frontend/dd-laminate/index-v2.ko.html`
  so the Curve CSV tab states the batch metadata columns and filename matching rule.
- Updated:
  `/Users/danlee/KyulAI_codex/src/frontend/dd-laminate/README.md`
  with a pointer to the bilingual guide.
- Added helper script:
  `/Users/danlee/KyulAI_codex/scripts/dd_make_curve_batch_metadata.py`
- Generated ready-to-upload metadata files:
  - `/Users/danlee/KyulAI_codex/data/New_Data/batch_metadata/curve_batch_metadata_6x8_Case2.csv`
  - `/Users/danlee/KyulAI_codex/data/New_Data/batch_metadata/curve_batch_metadata_6x8_Case3.csv`
  - `/Users/danlee/KyulAI_codex/data/New_Data/batch_metadata/curve_batch_metadata_6x8_Case4.csv`
- Each generated metadata file has `300` rows and columns:
  `filename,test_id,theta1,theta2,pt,case`.
- Verification:
  - `python -m py_compile scripts/dd_make_curve_batch_metadata.py` passed.
  - `node --check src/frontend/dd-laminate/app-v2.js` passed.

## 2026-07-20 - Re-checked newly added Laminate New_Data files
- User added more files under:
  `/Users/danlee/KyulAI_codex/data/New_Data`
- Current folder structure now includes:
  - `6x8_Case2/Original`
  - `6x8_Case3/Original`
  - `6x8_Case4/Original`
  - `csv_6x8_Case2`
  - `csv_6x8_Case3`
  - `csv_6x8_Case4`
- Newly confirmed transition load files:
  - `/Users/danlee/KyulAI_codex/data/New_Data/6x8_Case2/transition load.csv`
  - `/Users/danlee/KyulAI_codex/data/New_Data/6x8_Case3/transition load.csv`
  - `/Users/danlee/KyulAI_codex/data/New_Data/6x8_Case4/transition load.csv`
- Integrity check:
  - Each case has `300` transition rows, Test IDs `001-300`, no missing IDs, no duplicate IDs.
  - Each case has `300` plot images under `Original`.
  - Each matching `csv_6x8_Case*` folder has `300` `force_disp_Test_*.csv` files.
  - Theta ranges are `-89` to `90` for both `Theta1` and `Theta2` in all three cases.
- Pt summary:
  - Case2 Pt min/max/mean: `3213.638 / 11751.285 / 7434.859`
  - Case3 Pt min/max/mean: `3214.143 / 11666.361 / 7445.659`
  - Case4 Pt min/max/mean: `3213.762 / 11665.921 / 7415.716`
- Important interpretation:
  - The earlier first inspection was correct at that time: actual Pt files were not present yet.
  - After the user's latest additions, actual Pt values are now available in the three `transition load.csv` files.
  - The new data is ready for a dataset-builder/training pass using Case2, Case3, and Case4 with actual Pt labels.

## 2026-07-20 - Inspected LaminateForecast share folder RTX results
- User asked to inspect `/Users/danlee/KyulAI_codex/dist/LaminateForecast(share)` because it should contain RTX-trained results and additional changes.
- Folder size:
  - about `1.6 GB`.
- Key new model artifact found:
  `/Users/danlee/KyulAI_codex/dist/LaminateForecast(share)/models/dd_laminate_response_hybrid_type_student_v1/`
- Hybrid student files:
  - `response_goint.pt`
  - `response_distilled.pt`
  - `response_distilled_metrics.json`
  - `distillation_report.md`
- Reported model metadata:
  - model name: `laminate_forecast_hybrid_type_student_v1`
  - teacher: `models/dd_laminate_response_physics_abd_v1/response_surrogate.joblib`
  - real samples: `900`
  - synthetic samples: `15987`
  - feature builder: `theta_physics_v2`
  - input features: `35`
  - sequence length: `128`
  - hidden dim: `96`
  - branches: `10`
  - dropout: `0.08`
  - synthetic grid step: `2.5`
  - synthetic weight: `0.28`
  - confidence power: `1.5`
- Reported optimistic/deployment-style CV metrics:
  - Type accuracy: `0.9922 +/- 0.0067`
  - Macro F1: `0.9928 +/- 0.0062`
  - Teacher Type agreement: `0.9922`
  - Pt MAE vs ground truth: `368.07 kips`
  - Max Force MAE: `426.66`
  - Curve normalized RMSE: `0.00633`
  - Curve force RMSE: `439.59`
- Interpretation:
  - This is better than current Distilled NN v3 optimistic metrics
    (`0.9789` accuracy, `469.74 kips` Pt MAE, `0.00977` curve normalized RMSE).
  - It is still not a strict independent CV result because it follows the full-data teacher/synthetic-grid distillation pattern.
  - Treat it as a strong deployment candidate, but use strict CV or external holdout before making research/generalization claims.
- Code differences vs current repo:
  - package `src/backend/api/v1/dd_laminate.py` registers new model key
    `response_hybrid_distilled_type_tree_response_v1`;
  - it exposes label `Laminate Forecast - Hybrid`;
  - it combines distilled neural Type prediction with the stable Tree response model for Pt and response curves;
  - visible Laminate models in package are Machine Learning, Deep Learning, and Hybrid;
  - package `src/frontend/dd-laminate/app-v2.js` changes the primary response model list to show Hybrid instead of Distilled NN v3;
  - package `src/data/rag/answer.py` is much simpler/older than the current repo RAG answer layer and should not be copied over blindly.
- Runtime log note:
  - package backend ran locally on port `8765`;
  - `/api/v1/dd-laminate/xai/local` returned `404` in the package log, suggesting the packaged EXE may have been serving an older compiled backend or route mismatch even though the source file contains the route.
- Current repo state:
  - `models/dd_laminate_response_hybrid_type_student_v1/` is not yet present in the main repo.
  - Hybrid integration from the share package has not yet been merged into the active source tree.

## 2026-07-20 - Ran strict CV check for RTX Hybrid distillation settings
- User asked to keep newer repo files such as current RAG `answer.py`, and then check whether the RTX Hybrid result is optimistic because it used full-data teacher + synthetic grid distillation.
- Important merge rule confirmed:
  - Do not copy package `dist/LaminateForecast(share)/src/data/rag/answer.py` into the repo because it is older/simpler than the current repo RAG/Assistant implementation.
  - Only candidate changes from the package are the RTX Hybrid model artifact and the targeted Hybrid model registration logic.
- Ran strict CV-only with settings matching the RTX Hybrid model as closely as practical on this Mac:
  - command used `.venv/bin/python scripts/dd_response_distillation_train.py`
  - `--strict-cv --strict-cv-only`
  - `--strict-synthetic-exclusion-radius 2.5`
  - `--synthetic-grid-step 2.5`
  - `--synthetic-weight 0.28`
  - `--synthetic-confidence-power 1.5`
  - `--synthetic-min-confidence-weight 0.45`
  - `--epochs 90`
  - `--patience 16`
  - `--batch-size 512`
  - `--hidden-dim 96`
  - `--branches 10`
  - `--dropout 0.08`
  - output:
    `/Users/danlee/KyulAI_codex/reports/dd_response_hybrid_type_student_strict_cv_mps/`
- Device:
  - selected `mps (Apple Metal Performance Shaders)`.
- Synthetic data:
  - `15,987` teacher-labeled samples;
  - after validation-near exclusion, each fold kept about `15,075` to `15,171` synthetic samples.
- Strict CV result:
  - Type accuracy: `0.9556 +/- 0.0161`
  - Macro F1: `0.9513 +/- 0.0173`
  - Teacher Type agreement: `0.9689`
  - Pt MAE vs ground truth: `501.14 kips`
  - Pt MAE vs fold-local teacher: `347.39 kips`
  - Max Force MAE: `667.28`
  - Curve normalized RMSE vs ground truth: `0.01271`
  - Curve normalized RMSE vs fold-local teacher: `0.01065`
  - Curve force RMSE: `725.17`
- Interpretation:
  - RTX/package optimistic metrics were `0.9922` Type accuracy, `368.07 kips` Pt MAE, and `0.00633` curve normalized RMSE.
  - Strict CV confirms those RTX/package metrics are optimistic and should not be used as independent generalization claims.
  - The strict result is still better than the earlier quick strict run
    (`0.9433` accuracy, `671.63 kips` Pt MAE, `0.02448` curve normalized RMSE),
    so the RTX Hybrid remains a credible deployment/research candidate.
  - For public/research reporting, cite the strict CV metrics; for product deployment,
    the full-data Hybrid student can still be used if app/EXE behavior and XAI routes are verified.

## 2026-07-20 - Inspected new sibling experiment data in data/New_Data
- User added `/Users/danlee/KyulAI_codex/data/New_Data` and asked to read the three new experiments.
- Folder size:
  - about `35 MB`.
- Structure:
  - `csv_6x6_Case2`
  - `csv_6x8_Case3`
  - `csv_6x8_Case4`
- File counts:
  - each experiment folder contains `300` `force_disp_Test_###.csv` files;
  - total force-displacement CSV files: `900`;
  - no missing Test IDs from `001` to `300` in any of the three folders;
  - `csv_6x8_Case3` also contains `desktop.ini`; top folder also contains `.DS_Store`.
- CSV format:
  - headerless 2-column data;
  - column 1 appears to be displacement;
  - column 2 appears to be force/load;
  - row counts are `1001` or `1003`;
  - maximum displacement is consistently `0.15000000596046448`.
- Data integrity:
  - all 900 CSVs parsed successfully;
  - each folder has 300 unique file hashes;
  - same Test number across the three new experiment folders is not byte-identical.
- Missing metadata:
  - `data/New_Data` currently does not include a `transition_load.csv`, `transition load.csv`, explicit Pt file, or Type label folders.
  - If Test IDs follow the existing DD ordering, theta mapping can likely be inherited from
    `/Users/danlee/KyulAI_codex/data/datasets/DD_cases_2_3_4_curated_v1/Case2/transition_load.csv`
    because existing Case2/3/4 transition files share the same `Test_001..300` theta order.
- Example inferred mapping from existing curated data:
  - Test 001: theta1 `65`, theta2 `19`
  - Test 002: theta1 `40`, theta2 `-51`
  - Test 003: theta1 `-44`, theta2 `65`
  - Test 300: theta1 `51`, theta2 `46`
- Existing curated CSV comparison:
  - no new CSV is byte-identical to the corresponding old curated CSV.
  - New max force compared with old `DD_cases_2_3_4_curated_v1` max force:
    - `csv_6x6_Case2` vs old Case2: mean ratio `0.9005`, median `0.8985`
    - `csv_6x8_Case3` vs old Case3: mean ratio `0.9020`, median `0.8989`
    - `csv_6x8_Case4` vs old Case4: mean ratio `0.9004`, median `0.8991`
- Interpretation:
  - These look like new force-displacement results for three experiment conditions:
    `6x6 Case2`, `6x8 Case3`, and `6x8 Case4`.
  - They are usable as new curve data, but Pt/type labels are not directly present in `New_Data`.
  - Next useful step is to run the existing kink/Pt extraction method on all 900 new CSVs, then compare extracted Pt/type-like curve behavior against current Laminate Forecast models.

## 2026-07-20 - Cleaned obsolete zip artifacts from dist
- User asked to remove unnecessary zip files created in `/Users/danlee/KyulAI_codex/dist` to reclaim disk space.
- Kept current/relevant deliverables:
  - `/Users/danlee/KyulAI_codex/dist/KyulAI_windows_gpu_handoff_20260715_122841.zip`
  - `/Users/danlee/KyulAI_codex/dist/KyulAI_windows_gpu_handoff_20260715_122841.sha256`
  - `/Users/danlee/KyulAI_codex/dist/LaminateForecast(share).zip`
  - `/Users/danlee/KyulAI_codex/dist/laminate_existing_exe_buildkit_20260715.zip`
  - `/Users/danlee/KyulAI_codex/dist/imperialax-laminate-product-page-20260710.zip`
- Removed obsolete/superseded zip artifacts:
  - `KyulAI_DD_Injection_windows_bundle_20260512_151719.zip`
  - `KyulAI_dd_laminate_current_20260514_090104.zip`
  - `KyulAI_separated_current_20260514_090104.zip`
  - `KyulAI_shared_runtime_20260514_090104.zip`
  - `KyulAI_simple_injection_current_20260514_090104.zip`
  - `KyulAI_windows_server_bundle_2026-06-23.zip`
  - `laminate_greenfield_codex_20260715.zip`
  - stale checksum `KyulAI_separated_current_20260514_090104_checksums.sha256`
- Result:
  - `dist` size after zip cleanup: about `8.6 GB`.
  - Remaining large cleanup candidates are extracted folders, not zip files:
    `LaminateForecast(share)`, `KyulAI_separated_current_20260514_090104`,
    `KyulAI_DD_Injection_windows_bundle_20260512_151457`,
    `KyulAI_DD_Injection_windows_bundle_20260512_151719`,
    `laminate_existing_exe_buildkit_20260715`, and
    `laminate_greenfield_codex_20260715`.
  - A 1-epoch smoke run with `--device auto` completed successfully on this Mac and selected `mps (Apple Metal Performance Shaders)`.
  - PowerShell parse check was skipped because `pwsh` is not installed on this Mac.

## 2026-07-15 - Prepared Windows GPU PC handoff bundle
- User asked to prepare the current project state for moving to a GPU Windows PC, similar to the earlier handoff package.
- Updated bundle packaging:
  `/Users/danlee/KyulAI_codex/scripts/package_windows_bundle.py`
  now includes the Laminate distillation training scripts:
  - `scripts/dd_response_distillation_train.py`
  - `scripts/dd_response_physics_xai_train.py`
- Added handoff guide:
  `/Users/danlee/KyulAI_codex/docs/WINDOWS_GPU_PC_HANDOFF_20260715.md`
  covering:
  - fresh Windows setup;
  - CUDA PyTorch install with `Setup-WindowsServing.ps1 -TorchBackend cuda`;
  - local server start;
  - health checks;
  - GPU distillation run with `Train-LaminateDistillationGPU.ps1`;
  - current active Distilled NN v3 model and metrics.
- Created package:
  `/Users/danlee/KyulAI_codex/dist/KyulAI_windows_gpu_handoff_20260715_122841.zip`
- Package size:
  about `1.6 GB`.
- SHA256:
  `cef857f595b09576e9573d07e1bd3719abbe850aed658e58d9bee95f1e93e701`
- Package verification:
  - zip contains 9927 entries;
  - required Windows setup/training scripts are included;
  - required Distilled NN v3 model and XAI report are included;
  - required backend files and serving requirements are included.

## 2026-07-16 - Added and ran strict distillation CV sanity check
- User reported an RTX5070 distillation run with accuracy near `0.99` and asked whether that might indicate a problem.
- Analysis found the optimistic distillation CV can be inflated because:
  - the teacher model used for pseudo-labeling is the final Tree teacher trained on all 900 samples;
  - synthetic grid pseudo-labels are generated globally and then added to each fold;
  - some validation case/theta points exactly overlap the synthetic grid, and many validation-near points are present.
- Added strict CV support to:
  `/Users/danlee/KyulAI_codex/scripts/dd_response_distillation_train.py`
- New options:
  - `--strict-cv`
  - `--strict-cv-only`
  - `--strict-synthetic-exclusion-radius`
  - `--teacher-n-components`
- Strict CV behavior:
  - trains a fold-local Tree teacher only on that fold's real training samples;
  - creates fold-local synthetic pseudo-labels from that fold-local teacher;
  - removes synthetic points near the current validation fold's case/theta inputs;
  - computes normalization statistics from fold training data only;
  - reports CV metrics without training or saving a final deployment model when `--strict-cv-only` is used.
- Smoke test:
  - `--strict-cv --strict-cv-only --synthetic-grid-step 15 --epochs 2`
  - selected `mps` on this Mac;
  - completed all 5 folds, proving the strict path works.
- More meaningful CPU/MPS quick strict run:
  - command used `--synthetic-grid-step 7.5`, `--strict-synthetic-exclusion-radius 2.5`, `--epochs 45`, `--patience 8`.
  - output directory:
    `/Users/danlee/KyulAI_codex/reports/dd_response_distillation_strict_cv_quick/`
  - Type accuracy: `0.9433 +/- 0.0119`
  - Macro F1: `0.9381 +/- 0.0165`
  - Teacher Type agreement: `0.9656`
  - Pt MAE vs ground truth: `671.63 kips`
  - Pt MAE vs fold-local teacher: `532.00 kips`
  - Curve normalized RMSE vs ground truth: `0.02448`
- Interpretation:
  - The RTX `0.99` accuracy should be treated as optimistic/deployment-style distillation, not strict independent CV.
  - The strict quick CV accuracy around `0.9433` aligns much more closely with the Tree teacher's conservative CV accuracy (`0.9422`).
  - For publication/research claims, report strict CV. For deployment, the full-data teacher + synthetic grid student can still be trained as the production model.
- Verification:
  - `python -m py_compile scripts/dd_response_distillation_train.py` passed.

## 2026-07-20 - Prepared ImperialAX to ImperialAX URL migration
- User said the company name is now ImperialAX and asked to forward ImperialAX-side URLs to ImperialAX.
- Updated host routing and public URLs:
  - `imperialax.com`, `www.imperialax.com`, and `ai.imperialax.com` now return HTTP `308` to `https://ai.imperialax.com/`.
  - `laminate.imperialax.com` now returns HTTP `308` to `https://laminate.imperialax.com/` while preserving path/query.
  - `injection.imperialax.com` now returns HTTP `308` to `https://injection.imperialax.com/` while preserving path/query.
- Updated the module catalog API to use `brand: "ImperialAX"` and ImperialAX module URLs:
  - Laminate: `https://laminate.imperialax.com`
  - Injection: `https://injection.imperialax.com`
  - Optimization/Admin: `https://ai.imperialax.com`
- Updated user-facing workspace/login/admin/optimization copy from ImperialAX to ImperialAX.
- Added demo email aliases so `demo@imperialax.com` and `danlee@imperialax.com` map to the existing demo sessions without breaking legacy accounts.
- Kept legacy `X-ImperialAX-*` headers and legacy demo account records for compatibility.
- Kept old ImperialAX hostnames in Cloudflare tunnel routing intentionally so the app can serve the redirects.
- Restarted local production servers:
  - DD/Laminate/ImperialAX app on port `8000`
  - Simple Injection app on port `8010`
- Verification:
  - `python -m py_compile src/backend/dd_laminate_app.py src/backend/simple_injection_app.py src/backend/api/v1/modules.py src/backend/imperialax_app.py` passed.
  - `node --check` passed for ImperialAX workspace JS files.
  - Public `/ready` checks returned `200` for `ai.imperialax.com`, `laminate.imperialax.com`, and `injection.imperialax.com`.
  - Public legacy redirect checks returned `308` to the expected ImperialAX targets.
  - `https://ai.imperialax.com/api/v1/modules` returns `brand: "ImperialAX"` and ImperialAX URLs.

## 2026-07-20 - Added Laminate Forecast Hybrid Student deployment candidate
- User asked whether the strict-CV-checked Hybrid Student could replace the optimistic Distilled NN path and whether it could be trained locally instead of on RTX.
- Added final-only deployment training support to:
  `/Users/danlee/KyulAI_codex/scripts/dd_response_distillation_train.py`
  - `--final-only`
  - `--reference-metrics`
- Trained a Mac/MPS deployment candidate:
  `/Users/danlee/KyulAI_codex/models/dd_laminate_response_hybrid_student_deploy_quick_v1/`
- Training setup:
  - real data: `900` Case2/Case3/Case4 samples;
  - synthetic theta/case grid: `15,987` teacher-labeled samples;
  - teacher: `/Users/danlee/KyulAI_codex/models/dd_laminate_response_physics_abd_v1/response_surrogate.joblib`;
  - feature builder: `theta_physics_v2`;
  - hidden dim: `96`;
  - branches: `10`;
  - dropout: `0.08`;
  - final epochs: `65`.
- Reference strict-CV metrics copied from:
  `/Users/danlee/KyulAI_codex/reports/dd_response_hybrid_type_student_strict_cv_mps/response_distilled_metrics.json`
  - Type accuracy: `0.9556`;
  - macro F1: `0.9513`;
  - Pt MAE: `501.14 kips`;
  - curve norm RMSE: `0.01271`;
  - teacher agreement: `0.9689`.
- Generated model-specific XAI report:
  `/Users/danlee/KyulAI_codex/reports/dd_response_xai_hybrid_student_deploy_quick_v1/`
- Connected API model key:
  `response_hybrid_student_deploy_quick_v1`
- Updated visible Laminate Forecast response model list to:
  - `response_surrogate_physics_v2` = `Laminate Forecast - Machine Learning`;
  - `response_goint_physics_nn_v2` = `Laminate Forecast - Deep Learning`;
  - `response_hybrid_student_deploy_quick_v1` = `Laminate Forecast - Hybrid Student`.
- Kept old Distilled NN v3 registry key for backward compatibility but removed it from the optimal visible list.
- Updated Windows bundle script so the Hybrid Student model and XAI report are included in future handoff packages.
- Restarted local Laminate server on port `8000`.
- Verification:
  - `python3 -m py_compile scripts/dd_response_distillation_train.py scripts/package_windows_bundle.py src/backend/api/v1/dd_laminate.py` passed.
  - Direct model smoke test for `theta1=30`, `theta2=-30`, `Case2` returned Type `2`, Pt `17299.25`, and `128` curve points.
  - FastAPI TestClient `/predict/response` and `/xai/local` returned `200`.
  - Live local server `/api/v1/dd-laminate/models` returns the three visible models including `response_hybrid_student_deploy_quick_v1`.

## 2026-07-20 - Added geometry-aware Laminate Forecast prototype
- User asked whether Laminate Forecast can still predict when the panel size changes.
- Confirmed the original mechanics setup is `6 in x 4 in` from the DD PPT and code defaults.
- Built a combined geometry-aware dataset:
  `/Users/danlee/KyulAI_codex/data/datasets/DD_cases_2_3_4_geometry_v1/`
  - total rows: `1800`;
  - `900` existing curated `6x4` samples;
  - `900` new `6x8` samples from `data/New_Data/classified_curve_csv_v1/classification_manifest.csv`;
  - Case2/Case3/Case4 each has `600` rows.
- Added response feature set `theta_physics_geometry_v1`:
  - θ/case descriptors;
  - compact CLT ABD features;
  - panel geometry descriptors: `panel_aspect`, `a_slenderness`, `b_slenderness`, `panel_a_in`, `panel_b_in`.
- Trained geometry-aware ML model:
  `/Users/danlee/KyulAI_codex/models/dd_laminate_response_geometry_tree_v1/response_surrogate.joblib`
- Training metrics from 5-fold CV:
  - Type accuracy: `0.9561`;
  - macro F1: `0.9511`;
  - Pt MAE: `316.31 kips`;
  - Max force MAE: `315.11 kips`;
  - normalized curve RMSE: `0.00572`.
- Generated XAI report:
  `/Users/danlee/KyulAI_codex/reports/dd_response_xai_geometry_tree_v1/`
- Connected API model key:
  `response_geometry_tree_v1`
- Updated visible Response Forecast model list so Geometry ML is first/default, followed by Deep Learning and Hybrid Student.
- Updated web UI Response Forecast with panel size inputs:
  - English: `Panel length a (in)`, `Panel width b (in)`;
  - Korean: `패널 길이 a (in)`, `패널 폭 b (in)`.
- Bumped DD web JS cache version to `20260720-geometry-panel`.
- Updated Windows bundle script to include the geometry dataset, model, and XAI report.
- Verification:
  - Python compile passed for changed backend/ML/scripts files.
  - `node --check src/frontend/dd-laminate/app-v2.js` passed.
  - Direct model smoke test for `θ₁=30`, `θ₂=-30`, `Case2`:
    - `6x4`: Type `2`, Pt `17151.49`, Max force `42629.76`;
    - `6x8`: Type `2`, Pt `8393.31`, Max force `27970.08`.
  - FastAPI TestClient `/predict/response`, `/predict/theta`, and `/xai/local` returned `200`.
  - Restarted local Laminate server on port `8000`.
  - Public `https://laminate.imperialax.com/api/v1/dd-laminate/models` returns `response_geometry_tree_v1` as the first Response model.
  - Public prediction with `panel_a_in=6`, `panel_b_in=8` returned model `response_geometry_tree_v1`, Pt `8393.31`, and panel inputs in the response.
  - Public DD HTML and `app-v2.js?v=20260720-geometry-panel` include the new panel-size controls and payload fields.
- Caveat:
  - The `6x8` Type labels are curve-classifier-generated labels, not manually reviewed labels. This is suitable for a prototype and internal screening, but research-grade claims should use human-reviewed labels or a geometry-held-out validation set.

## 2026-07-20 - Trained Geometry GointMLP/DL Laminate Forecast
- User asked to train `Geometry GointMLP/DL` using the same `6x4 + 6x8` geometry-aware dataset.
- Trained DL model:
  `/Users/danlee/KyulAI_codex/models/dd_laminate_response_geometry_goint_v1/response_goint.pt`
- Dataset:
  `/Users/danlee/KyulAI_codex/data/datasets/DD_cases_2_3_4_geometry_v1/`
  - `1800` samples;
  - `6x4` existing curated samples + `6x8` new classified samples;
  - feature set `theta_physics_geometry_v1`;
  - `40` input features.
- Training settings:
  - `5` GroupKFold splits;
  - quick Mac/MPS run with `epochs=70`, `patience=12`, `final_epochs=35`, `batch_size=128`.
- Geometry DL 5-fold metrics:
  - Type accuracy: `0.9494`;
  - macro F1: `0.9484`;
  - Pt MAE: `823.04 kips`;
  - Max force MAE: `1261.57 kips`;
  - normalized curve RMSE: `0.02100`.
- Comparison against Geometry ML / Tree:
  - Geometry ML remains stronger for deployment:
    - Type accuracy `0.9561`;
    - Pt MAE `316.31 kips`;
    - Max force MAE `315.11 kips`;
    - normalized curve RMSE `0.00572`.
  - Geometry DL is available as a neural comparison/research model, but not the recommended default yet.
- Generated matching XAI report:
  `/Users/danlee/KyulAI_codex/reports/dd_response_xai_geometry_goint_v1/`
- Fixed `/Users/danlee/KyulAI_codex/scripts/dd_response_xai_report.py` so Tree/Goint finite-difference XAI passes each record's `panel_a_in` and `panel_b_in` instead of silently using the old `6x4` defaults.
- Regenerated Geometry Tree XAI with the corrected panel-size-aware sensitivity logic:
  `/Users/danlee/KyulAI_codex/reports/dd_response_xai_geometry_tree_v1/`
- Added comparison report:
  `/Users/danlee/KyulAI_codex/reports/dd_response_geometry_v1/response_geometry_training_report.md`
- Connected API model key:
  `response_geometry_goint_v1`
- Updated visible Response Forecast model list to:
  - `response_geometry_tree_v1` = `Laminate Forecast - Geometry ML`;
  - `response_geometry_goint_v1` = `Laminate Forecast - Geometry DL`;
  - `response_hybrid_student_deploy_quick_v1` = `Laminate Forecast - Hybrid Student`.
- Updated Windows bundle script to include:
  - `models/dd_laminate_response_geometry_goint_v1`;
  - `reports/dd_response_xai_geometry_goint_v1`.
- Verification:
  - `python3 -m py_compile` passed for changed backend/XAI/package files.
  - `node --check src/frontend/dd-laminate/app-v2.js` passed.
  - FastAPI TestClient returned `200` for Geometry ML/DL predictions and local XAI.
  - Local smoke test for `θ₁=30`, `θ₂=-30`, `Case2`:
    - Geometry ML `6x4`: Type `2`, Pt `17151.49`;
    - Geometry ML `6x8`: Type `2`, Pt `8393.31`;
    - Geometry DL `6x4`: Type `2`, Pt `17874.86`;
    - Geometry DL `6x8`: Type `3`, Pt `7959.53`.
  - Restarted local Laminate server on port `8000`.
  - Public `https://laminate.imperialax.com/api/v1/dd-laminate/models` returns Geometry ML and Geometry DL as the first two response models.
  - Public Geometry DL prediction with `panel_a_in=6`, `panel_b_in=8` returned model `response_geometry_goint_v1`, Type `3`, Pt `7959.53`.

## 2026-07-20 - Updated Laminate Forecast public branding
- User asked to replace the remaining `ImperialAX Laminate Forecast` page title/header on `laminate.imperialax.com`.
- Updated DD Laminate web shell files:
  - `/Users/danlee/KyulAI_codex/src/frontend/dd-laminate/index-v2.html`
  - `/Users/danlee/KyulAI_codex/src/frontend/dd-laminate/index.html`
  - `/Users/danlee/KyulAI_codex/src/frontend/dd-laminate/index-v2.ko.html`
  - `/Users/danlee/KyulAI_codex/src/frontend/dd-laminate/index.ko.html`
- English public title/header now shows `ImperialAX Laminate Forecast`.
- Korean public title/header now shows `ImperialAX 적층 예측`.
- Verification:
  - `rg` confirms the updated Laminate shell files no longer contain `ImperialAX Laminate Forecast`.
  - `curl https://laminate.imperialax.com/` returns `<title>ImperialAX Laminate Forecast</title>` and the matching H1.

## 2026-07-20 - Fixed empty Laminate Forecast model dropdown
- User reported that `laminate.imperialax.com` showed no models in the model select bar.
- Root cause:
  - Backend `/api/v1/dd-laminate/models` was healthy and returned the new visible response model keys:
    `response_geometry_tree_v1`, `response_geometry_goint_v1`, and `response_hybrid_student_deploy_quick_v1`.
  - Frontend `PRIMARY_RESPONSE_MODEL_KEYS` still filtered for the previous keys:
    `response_surrogate_physics_v2`, `response_goint_physics_nn_v2`, and `response_distilled_grid_conf_v1`.
  - The filter therefore returned an empty list even though the API was working.
- Fixed:
  - `/Users/danlee/KyulAI_codex/src/frontend/dd-laminate/app-v2.js`
  - `/Users/danlee/KyulAI_codex/src/frontend/dd-laminate/app.js`
  - Updated `PRIMARY_RESPONSE_MODEL_KEYS` to:
    - `response_geometry_tree_v1`
    - `response_geometry_goint_v1`
    - `response_hybrid_student_deploy_quick_v1`
  - Bumped DD v2 JS cache version to `20260720-geometry-models` in English/Korean pages.
- Verification:
  - Public `/api/v1/dd-laminate/models` returns all three model keys as `available: true`.
  - Public HTML references `app-v2.js?v=20260720-geometry-models`.
  - Public JS contains the corrected `PRIMARY_RESPONSE_MODEL_KEYS`.
  - Node reproduction of the frontend filter returns all three models.

## 2026-07-20 - Moved panel-size controls to Response Forecast form
- User reported that there was no visible control for setting/changing panel size.
- Root cause:
  - The panel-size controls had been added to the `u3 Pt Forecast` form instead of the `Response Forecast` form.
- Fixed English/Korean DD Laminate pages:
  - Removed `panel_a_in` / `panel_b_in` controls from `u3-pt-form`.
  - Added them below `Case` in `response-form`.
- Verification:
  - Local HTML check: `u3_has_panel=False`, `response_has_panel=True`.
  - Public `https://laminate.imperialax.com/` check: `u3_has_panel=False`, `response_has_panel=True`.
  - Public response form contains `Panel length a (in)` and `Panel width b (in)` controls.

## 2026-07-20 - Added web Predicted Curve zoom controls
- User asked whether the DD Laminate `Predicted curve` section originally had a detailed graph view such as zoom in/out.
- Finding:
  - Web v2 used a static canvas for `#response-curve-canvas`.
  - Android and iOS already had interactive zoom/pan chart work, but web did not.
- Updated DD Laminate web v2:
  - Added a compact `Curve view` / `곡선 상세 보기` toolbar above the predicted curve canvas.
  - Added `−`, `+`, and `Reset` controls plus a percentage zoom label.
  - Added mouse-wheel zoom, double-click reset, and drag-to-pan when zoomed in.
  - Redraws chart axes/ticks against the zoomed visible domain instead of only bitmap-scaling the canvas.
  - Clips curve/fit lines to the plot area so zoomed curves do not spill outside the graph frame.
  - Bumped `index-v2.html` and `index-v2.ko.html` asset versions to `20260720-curve-zoom`.
- Verification:
  - `node --check src/frontend/dd-laminate/app-v2.js` passed.
  - Local HTML contains `curve-viewer-head` and the new `20260720-curve-zoom` assets.
  - Public `https://laminate.imperialax.com/index-v2.html` contains the new curve toolbar and cache-busted assets.
  - Public `app-v2.js?v=20260720-curve-zoom` contains `installResponseCurveZoomControls`, `setResponseCurveSource`, and the zoom constants.
  - Public response prediction smoke test for `θ₁=30`, `θ₂=-30`, `Case2`, `6x4`, `response_geometry_tree_v1` returned Type `2` and Pt `17151.49`.

## 2026-07-20 - Improved Predicted Curve readability
- User reported that text inside the `Predicted curve` graph, legend, and predicted Pt label looked too small.
- Updated DD Laminate web v2:
  - Increased `#response-curve-canvas` backing resolution from `720x432` to `1080x648` while keeping the displayed responsive size.
  - Increased canvas plot padding so larger axis labels and Pt labels fit without crowding.
  - Increased axis tick labels from `11px` to `16px`.
  - Increased axis labels from `12px` to `17px`.
  - Increased predicted Pt callout title/value fonts from `13/15px` to `17/22px`.
  - Enlarged Pt markers, predicted curve line width, fit-line width, and kink-guide width.
  - Increased web curve legend font size and swatch size.
  - Bumped English/Korean web assets to `20260720-curve-readable`.
- Verification:
  - `node --check src/frontend/dd-laminate/app-v2.js` passed.
  - Public `https://laminate.imperialax.com/index-v2.html` now references `20260720-curve-readable` assets and contains the `1080x648` response canvas.
  - Public JS contains the larger chart font/padding/line-width settings.
  - Public CSS contains the larger curve legend and swatch settings.

## 2026-07-20 - Fixed canvas readability scaling issue
- User reported that the graph text still did not look larger after the readability update.
- Root cause:
  - Increasing the canvas backing size from `720x432` to `1080x648` while displaying it at the same CSS width caused the browser to scale the whole bitmap down.
  - The larger font settings were therefore mostly canceled out by the canvas down-scaling.
- Fixed:
  - Added `prepareResponseCurveCanvas()` to draw the response curve in CSS/logical pixels while using device-pixel-ratio backing pixels for sharpness.
  - Updated pointer coordinate mapping to use the same logical pixel coordinate system, preserving zoom and pan behavior.
  - Added resize redraw handling so the curve remains readable when the panel width changes.
  - Bumped DD v2 assets to `20260720-curve-readable-v2`.
- Verification:
  - `node --check src/frontend/dd-laminate/app-v2.js` passed.
  - Public `https://laminate.imperialax.com/index-v2.html` references `20260720-curve-readable-v2`.
  - Public `app-v2.js?v=20260720-curve-readable-v2` contains `prepareResponseCurveCanvas`, logical pointer mapping, and the larger graph fonts.

## 2026-07-21 - Prepared latest Git snapshot for Windows/RTX handoff
- User asked to push the latest project state so the Windows RTX PC can start from `git clone`.
- Repository state:
  - Active branch: `codex/dd-laminate-ui-api`.
  - Remote: `origin https://github.com/danhoonlee/KyulAI.git`.
  - Latest state includes DD Laminate, Injection, web/app changes, Windows serving scripts, Cloudflare configs, RAG/Assistant updates, geometry-aware Laminate models, new 6x8 data, and product-page assets/docs.
- Large artifact handling:
  - Installed Git LFS locally because several deployment-critical model artifacts exceed GitHub's normal 100MB file limit.
  - Initially tested broad `*.joblib`/`*.pt` LFS tracking, but narrowed it before final commit to avoid converting every historical model artifact.
  - Final LFS tracking is limited to deployment-relevant oversized artifacts:
    - `models/dd_laminate_response_geometry_tree_v1/response_surrogate.joblib`
    - `models/dd_laminate_u3_forecast_physics_abd_v1/u3_forecast.joblib`
    - `models/dd_laminate_response_physics_abd_v1/response_surrogate.joblib`
  - Important new large model: `models/dd_laminate_response_geometry_tree_v1/response_surrogate.joblib` (~900MB).
  - Excluded untracked local challenger artifacts `random_forest.joblib` and `extra_trees.joblib` under `models/dd_laminate_response_tabular_challengers_v1/` from the portable Git handoff.
- Safety checks before staging:
  - `.env.local` remains ignored and was not staged.
  - `dist/`, `.venv/`, and Gradle cache folders remain ignored.
  - Secret scan found only placeholder/example Slack/OpenAI strings, not real credentials.
  - Syntax checks passed for DD Laminate web JS, Injection web JS, ImperialAX web JS, and key Python backend/training/RAG files.
- Git result:
  - Created commit `f555ab3` on `codex/dd-laminate-ui-api`.
  - Uploaded three LFS model objects separately, then pushed `codex/dd-laminate-ui-api` to GitHub.
  - Remote branch advanced from `a33c2a2` to `f555ab3`.

## 2026-07-21 - Added remaining portable handoff assets
- User clarified that non-Laminate parts also need to be available from Git.
- Checked repository state:
  - Injection web/app code and Simple Injection models/data were already tracked and pushed in the prior handoff snapshot.
  - Remaining ignored files were mostly local caches/build outputs (`dist/`, `.venv/`, Gradle/Xcode build folders), OS metadata, local auth DB, logs, and historical APK variants.
- Added the useful remaining portable assets:
  - `data/datasets/DD_cases_2_3_4_geometry_v1/` with geometry response manifest and Case2/Case3/Case4 transition-load CSV summaries.
  - `artifacts/android/ImperialAX-debug-latest.apk` as the current Android debug APK alias.
- Deliberately left out:
  - `dist/` bundles (~8.6GB), because they are generated copies and include old packaged artifacts.
  - `.env.local` and `data/imperialax_auth.sqlite3`, because they contain local secrets/runtime state.
  - Build caches and OS metadata.
  - Untracked `random_forest.joblib` / `extra_trees.joblib` challenger artifacts, because they are large local experiment outputs and not current deployment models.

## 2026-07-21 - Added WSL RTX GPU worker bridge
- User wants Codex on the Mac to be able to run heavy model training on the Windows RTX PC through WSL when GPU is needed.
- Verified remote worker:
  - Tailscale SSH target: `user@100.65.153.56`.
  - Remote project: `~/projects/KyulAI`.
  - Python `3.11.15`.
  - PyTorch `2.11.0+cu128`.
  - CUDA available through PyTorch.
  - GPU detected by PyTorch: `NVIDIA GeForce RTX 5070`.
  - `nvidia-smi` is not currently on WSL PATH, but PyTorch CUDA is working.
- Added:
  - `scripts/remote/Run-WSLGPU.sh` for one-line remote command execution from the Mac repo into WSL.
  - `docs/WINDOWS_WSL_GPU_WORKER.md` documenting worker address, runtime, command examples, and operational notes.
- Git/network notes:
  - Local Mac DNS could not resolve `github.com`, so normal `git push` initially failed before authentication.
  - WSL could resolve/reach GitHub, but WSL did not have GitHub push credentials configured.
  - GitHub connector had read access but not write access.
  - Final push succeeded from Mac by temporarily pinning `github.com:443` to the GitHub IP resolved by WSL with `git -c http.curloptResolve=github.com:443:20.200.245.247 push`.
  - Remote branch `codex/dd-laminate-ui-api` advanced to `cbd9006`.

## 2026-07-21 - Ran RTX Geometry-aware Laminate strict validation
- User asked to run the next Laminate research/model step: Geometry-aware strict CV and Hybrid/Student revalidation on the Windows RTX worker.
- Preparation:
  - Added `--synthetic-panel-sizes` to `scripts/dd_response_distillation_train.py`.
  - Default remains `6x4` for backward compatibility.
  - RTX run used `6x4,6x8`, so synthetic grid distillation reflects both panel sizes.
  - Added `scripts/remote/Run-LaminateGeometryStrictRTX.sh` to make the remote run reproducible.
  - Copied untracked-but-required `data/New_Data/csv_6x8_Case2`, `csv_6x8_Case3`, `csv_6x8_Case4`, and `classified_curve_csv_v1/classification_manifest.csv` to the WSL worker because those source CSVs are not all tracked in Git.
- RTX worker:
  - Host: `user@100.65.153.56`.
  - GPU visible to PyTorch: `NVIDIA GeForce RTX 5070`.
  - Run id: `20260721_geometry_strict_rtx_v1`.
  - Remote log: `reports/rtx_runs/20260721_geometry_strict_rtx_v1.log`.
- Geometry ML/DL strict grouped CV, 1800 samples, feature set `theta_physics_geometry_v1`:
  - Geometry ML / Tree: Type accuracy `0.9561 +/- 0.0106`, Macro F1 `0.9511 +/- 0.0149`, Pt MAE `313.91` kips, curve norm RMSE `0.00571`.
  - Geometry DL / GointMLP: Type accuracy `0.9500 +/- 0.0111`, Macro F1 `0.9473 +/- 0.0142`, Pt MAE `837.34` kips, curve norm RMSE `0.03257`.
- Geometry-aware Hybrid Student strict CV:
  - Teacher: `models/dd_laminate_response_geometry_tree_v1/response_surrogate.joblib`.
  - Samples: `1800`.
  - Synthetic samples: `31974`.
  - Synthetic grid step: `2.5`.
  - Synthetic panel sizes: `6x4,6x8`.
  - Type accuracy `0.9622 +/- 0.0132`, Macro F1 `0.9601 +/- 0.0169`.
  - Pt MAE vs ground truth `471.62` kips.
  - Curve norm RMSE vs ground truth `0.00943`.
- Interpretation:
  - Hybrid Student improves Type classification over Geometry ML in strict CV.
  - Geometry ML / Tree remains better for Pt and curve prediction.
  - Current deployment default should remain Geometry ML unless the product goal shifts toward Type-only screening.
  - Hybrid Student remains a strong research/deployment candidate for compact or Type-focused workflows, but not yet a better all-around replacement for Geometry ML.
- Local reports copied back:
  - `reports/dd_response_geometry_rtx_strict_20260721_geometry_strict_rtx_v1/response_geometry_training_report.md`.
  - `reports/dd_response_hybrid_geometry_strict_cv_20260721_geometry_strict_rtx_v1/distillation_report.md`.
  - `reports/dd_response_hybrid_geometry_strict_cv_20260721_geometry_strict_rtx_v1/response_distilled_metrics.json`.

## 2026-07-21 - Added RTX training resource controls
- User noticed the Windows RTX worker seemed to use CPU heavily and asked to continue with the next optimization step.
- Diagnosis:
  - PyTorch CUDA is available on the WSL worker and detects `NVIDIA GeForce RTX 5070`.
  - High CPU usage is expected during sklearn `ExtraTrees`, PCA, synthetic grid generation, and teacher pseudo-label prediction because those parts are CPU-only.
  - GPU is used by the GointMLP / PyTorch and Hybrid Student training sections.
- Added runtime controls:
  - `scripts/dd_response_physics_xai_train.py`
    - `--tree-n-jobs` to cap sklearn ExtraTrees CPU parallelism.
    - `--num-workers`, `--prefetch-factor`, and `--pin-memory` for PyTorch DataLoader tuning.
  - `scripts/dd_response_distillation_train.py`
    - Same DataLoader controls.
    - Same `--tree-n-jobs` control for fold-local teachers in strict CV.
    - Fixed final-only report generation when no `--reference-metrics` is provided.
  - `src/ml/dd_laminate/train_cases_2_3_4_goint.py`
    - Uses non-blocking tensor transfer when pinned memory is enabled.
  - `scripts/remote/Run-LaminateGeometryStrictRTX.sh`
    - Defaults now include `TREE_N_JOBS=8`, `NUM_WORKERS=2`, `PIN_MEMORY=auto`, and `PREFETCH_FACTOR=2`.
- Verification:
  - Local `py_compile` passed for the modified Python files.
  - WSL RTX venv `py_compile` passed.
  - WSL CUDA smoke passed for distillation final-only training with `--device cuda --num-workers 2 --pin-memory auto`.
  - WSL CUDA smoke passed for Geometry GointMLP training with `--device cuda --skip-tree --splits 2 --epochs 1 --final-epochs 1`.

## 2026-07-21 - Benchmarked RTX DataLoader worker settings
- Added `scripts/remote/Benchmark-LaminateRTXResources.sh` to compare short CUDA training runs across DataLoader worker settings.
- Ran benchmark on WSL RTX worker:
  - Run id: `20260721_resource_benchmark_v1`.
  - GPU: `NVIDIA GeForce RTX 5070`.
  - Batch size: `512`.
  - Epochs: `3`.
  - Goint smoke splits: `2`.
  - Configs: `0:auto,1:auto,2:auto,4:auto`.
- Results:
  - Distillation final-only: workers `0=5s`, `1=6s`, `2=5s`, `4=6s`.
  - Geometry GointMLP CV smoke: workers `0=3s`, `1=4s`, `2=4s`, `4=4s`.
- Recommendation:
  - Keep `NUM_WORKERS=2` as the default for stable longer RTX runs.
  - Use `NUM_WORKERS=0` when Windows desktop responsiveness matters more.
  - Avoid `NUM_WORKERS=4` for current dataset scale because worker overhead did not help.
  - Keep `TREE_N_JOBS=8` as a balanced default; lower to `4` if sklearn Tree/fold-local teacher stages make CPU too busy.
- Local artifacts:
  - `reports/rtx_resource_benchmarks/20260721_resource_benchmark_v1/resource_benchmark.csv`.
  - `reports/rtx_resource_benchmarks/20260721_resource_benchmark_v1/benchmark_summary.md`.

## 2026-07-21 - Matched Laminate panel-size inputs across Web/iOS/Android
- User clarified that the next panel-size step referred to the existing `Panel length a` and `Panel width b` inputs.
- Confirmed backend and ML feature layer already support geometry-aware response forecasts:
  - `/api/v1/dd-laminate/predict/response` accepts `panel_a_in` and `panel_b_in`.
  - XAI local requests also accept the same fields.
  - Feature pack uses panel aspect/slenderness and raw panel dimensions.
- Updated clients:
  - Web `app-v2.js` now saves panel dimensions in response forecast history, restores them when a history card is clicked, includes them in history signatures, and passes them to assistant lazy-XAI requests.
  - iOS `DDLaminateMVP` now has `panelAIn`/`panelBIn` ViewModel state, sends `panel_a_in`/`panel_b_in`, restores/saves them in recent runs, and shows panel chips in response history.
  - Android `ImperialAXMVP` now shows Panel size inputs, sends geometry values for Response Forecast, includes them in result summaries, assistant context, and recent-history signatures/cards.
  - Standalone Android `DDLaminateMVP` also sends and stores panel dimensions to avoid stale behavior in that older app surface.
- Scope note:
  - u3 Forecast remains theta/case-only for now because the current u3 model request/schema does not include panel geometry.
- Verification:
  - `node --check src/frontend/dd-laminate/app-v2.js` passed.
  - `git diff --check` passed.
  - `swift test` in `ios/DDLaminateMVP` passed: 11 tests.
  - Initial Android Gradle assemble was blocked because macOS could not locate Java 17.
  - Homebrew `openjdk@17` was already installed; using `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home` fixed the toolchain.
  - `gradle :app:assembleDebug` passed in `android/ImperialAXMVP`.
  - `gradle :app:assembleDebug` passed in `android/DDLaminateMVP`.

## 2026-07-21 - RTX Geometry-Aware Strict Leaderboard v2
- User asked to continue improving the model direction after panel-size support and Android build verification.
- Ran the latest geometry-aware Laminate Forecast leaderboard on the Windows WSL RTX worker.
- Remote worker:
  - Host: `user@100.65.153.56`.
  - GPU: `NVIDIA GeForce RTX 5070`.
  - PyTorch: `2.11.0+cu128`.
  - Run id: `20260721_geometry_strict_rtx_v2`.
  - Remote commit: `d789947`.
- Dataset:
  - Built `data/datasets/DD_cases_2_3_4_geometry_v1`.
  - Total rows: `1800`.
  - Case2/Case3/Case4 each have `600` rows.
  - Each case combines `300` existing `6x4` curated rows and `300` new `6x8` rows.
  - Feature set: `theta_physics_geometry_v1`.
- Strict grouped CV results:
  - Geometry Tree + Physics XAI:
    - Type accuracy `0.9561 +/- 0.0106`.
    - Macro F1 `0.9511 +/- 0.0149`.
    - Pt MAE `313.91 +/- 50.55` kips.
    - Curve normalized RMSE `0.00571 +/- 0.00086`.
    - Curve force RMSE `401.38 +/- 66.36` kips.
  - Geometry GointMLP + Physics XAI:
    - Type accuracy `0.9511 +/- 0.0080`.
    - Macro F1 `0.9480 +/- 0.0108`.
    - Pt MAE `738.04 +/- 116.19` kips.
    - Curve normalized RMSE `0.02698 +/- 0.01042`.
    - Curve force RMSE `1241.92 +/- 341.99` kips.
  - Geometry Hybrid Student:
    - Type accuracy `0.9622 +/- 0.0117`.
    - Macro F1 `0.9601 +/- 0.0143`.
    - Teacher Type agreement `0.9789`.
    - Pt MAE vs ground truth `423.02 +/- 47.02` kips.
    - Pt MAE vs teacher `333.96 +/- 51.24` kips.
    - Curve normalized RMSE vs ground truth `0.00951 +/- 0.00094`.
    - Curve force RMSE vs ground truth `648.20 +/- 29.84` kips.
- Interpretation:
  - Geometry Tree remains the best all-around deployment default because Pt and curve regression are strongest.
  - Geometry Hybrid Student is the best Type classifier and should remain a strong research/challenger model.
  - Geometry GointMLP remains a useful deep-learning baseline but is not competitive for Pt/curve regression yet.
- Local reports copied back:
  - `reports/dd_response_geometry_rtx_strict_20260721_geometry_strict_rtx_v2/response_geometry_training_report.md`.
  - `reports/dd_response_hybrid_geometry_strict_cv_20260721_geometry_strict_rtx_v2/distillation_report.md`.
  - `reports/dd_response_hybrid_geometry_strict_cv_20260721_geometry_strict_rtx_v2/response_distilled_metrics.json`.
  - `reports/dd_laminate_geometry_strict_leaderboard_20260721.md`.

## 2026-07-21 - Added Fixed Holdout Gate for Geometry-Aware Laminate Forecast
- User pointed out that the fixed external holdout should have been run together with the strict CV leaderboard.
- Added `scripts/dd_response_geometry_holdout_eval.py`.
- Split policy:
  - Deterministic seed `42`.
  - Holdout ratio `0.2`.
  - Group key: `Case + theta1 + theta2`.
  - No identical case/theta pair appears in both train and holdout.
  - Stratification target: `Case + Type`.
  - The resulting holdout also preserves panel/source coverage exactly: `182` rows from `6x4` and `182` rows from `6x8`.
- Local Tree-only smoke:
  - Confirmed split generation and report writing.
  - System `/usr/bin/python3` lacked numpy, so the project `.venv` was used for local smoke.
- RTX full holdout run:
  - Run id: `20260721_geometry_holdout_rtx_v1`.
  - Device: `NVIDIA GeForce RTX 5070`.
  - Train rows: `1436`.
  - Holdout rows: `364`.
  - Train groups: `718`.
  - Holdout groups: `182`.
- Fixed holdout results:
  - Geometry Tree + Physics XAI:
    - Type accuracy `0.9451`.
    - Macro F1 `0.9456`.
    - Pt MAE `247.39` kips.
    - Curve normalized RMSE `0.00293`.
    - Curve force RMSE `227.99` kips.
  - Geometry GointMLP + Physics XAI:
    - Type accuracy `0.9203`.
    - Macro F1 `0.9247`.
    - Pt MAE `675.61` kips.
    - Curve normalized RMSE `0.01838`.
    - Curve force RMSE `1035.00` kips.
  - Geometry Hybrid Student:
    - Type accuracy `0.9451`.
    - Macro F1 `0.9444`.
    - Teacher Type agreement `0.9863`.
    - Pt MAE `361.05` kips.
    - Curve normalized RMSE `0.00576`.
    - Curve force RMSE `425.69` kips.
- Interpretation:
  - Fixed holdout confirms the same product decision as strict grouped CV.
  - Geometry Tree remains the deployment default because Pt and curve errors are best.
  - Hybrid Student remains a strong Type/challenger model but is not yet the better all-around forecast model.
- Local artifacts:
  - `reports/dd_response_geometry_fixed_holdout_20260721_geometry_holdout_rtx_v1/fixed_holdout_report.md`.
  - `reports/dd_response_geometry_fixed_holdout_20260721_geometry_holdout_rtx_v1/fixed_holdout_metrics.json`.
  - `reports/dd_response_geometry_fixed_holdout_20260721_geometry_holdout_rtx_v1/fixed_holdout_manifest.csv`.
  - Updated `reports/dd_laminate_geometry_strict_leaderboard_20260721.md`.

## 2026-07-21 - Added Laminate Tree/Student Ensemble Consistency Check
- User preferred the `Teacher + Student Ensemble` direction over replacing the deployment model with the student.
- Product decision:
  - Keep `response_geometry_tree_v1` as the Laminate Forecast deployment/default prediction because strict CV and fixed holdout show the best Pt and curve regression.
  - Use `response_hybrid_student_deploy_quick_v1` as a challenger/student that runs alongside the Tree model for consistency checking.
- Backend changes:
  - Added `/api/v1/dd-laminate/predict/response-ensemble`.
  - The endpoint returns the normal Tree prediction plus a `teacher_student` block.
  - Agreement compares Type match, Pt delta, max-force delta, and normalized curve RMSE between Tree and Hybrid Student for the same θ/Case/panel input.
  - Agreement score weights: Type `45%`, Pt `35%`, curve shape `20%`.
  - Confidence labels: high `>= 0.78`, medium `>= 0.58`, otherwise low.
- Web changes:
  - When the Laminate Forecast ML model (`response_geometry_tree_v1`) is selected, the web UI calls the new ensemble endpoint.
  - The result page now shows a compact `Tree vs Student agreement` panel below prediction reliability.
  - The panel is hidden for u3 and non-ensemble single-model predictions.
- Smoke verification:
  - Sample `θ₁=30`, `θ₂=-30`, `Case2`, `6x4` panel:
    - Tree predicted Type `2`, Pt `17151.49`.
    - Student predicted Type `2`, Pt `17299.25`.
    - Agreement score `0.7623`, confidence label `medium`, Pt delta `147.76` kips.

## 2026-07-22 - Applied Tree/Student Agreement to iOS and Android Apps
- User asked to continue with app parity after the web ensemble panel.
- iOS changes:
  - Added `ResponseModelSnapshot` and `TeacherStudentAgreement` decoding to `DDLaminateModels.swift`.
  - Added `ResponseEnsemblePredictionRequest` and routed the default Laminate ML model (`response_geometry_tree_v1`) through `/predict/response-ensemble`.
  - Updated default Laminate model keys to geometry-aware models:
    - ML: `response_geometry_tree_v1`.
    - DL: `response_geometry_goint_v1`.
    - Student/challenger: `response_hybrid_student_deploy_quick_v1`.
  - Added `TeacherStudentAgreementCard` to result detail and Laminate result panels.
  - Exposed the shared agreement card for reuse and inserted it into the separate `ios/ImperialAXMVP` Laminate forecast result flow as well.
  - Korean/English labels and notes are included.
- Android changes:
  - Updated ImperialAX Android Laminate defaults to the same geometry-aware model keys.
  - Added `LaminateTeacherStudentAgreement` and snapshot parsing.
  - Default ML forecast now calls `/predict/response-ensemble`; other selected models still call `/predict/response`.
  - Added a `Tree vs Student agreement` section to the Android result detail page.
- Verification:
  - `swift build --package-path ios/DDLaminateMVP` passed.
  - `swift build --package-path ios/ImperialAXMVP` passed.
  - `xcodebuild` for `KyulAIDDLaminateCore` simulator scheme passed.
  - `xcodebuild` for `KyulAIDDLaminateApp` simulator scheme passed.
  - `xcodebuild` for `ImperialAXMVPHost` simulator scheme passed.
  - Android `:app:compileDebugKotlin` passed with `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home`.
- Note:
  - The Mac has Homebrew `openjdk@17`, but system `/usr/bin/java` is not linked. Use the explicit `JAVA_HOME` above for Android builds.

## 2026-07-22 - ImperialAX Public Rebrand Pass
- User requested removing user-facing legacy brand names and replacing the product
  identity with `ImperialAX`.
- Scope decision:
  - Updated visible product text, account text, URLs, test expectations, and app display names to `ImperialAX`.
  - At this point, internal package/file/type identifiers were still mostly kept
    for compatibility and to avoid unnecessary bundle/package churn.
- Backend compatibility:
  - Module catalog brand is now `ImperialAX`.
  - Admin API uses `X-ImperialAX-Admin-Token` / `IMPERIALAX_ADMIN_TOKEN`.
  - Entitlement override uses `X-ImperialAX-Entitlements`.
  - Demo/admin emails use `@imperialax.com`.

## 2026-07-22 - ImperialAX Internal Rename Pass
- User confirmed the project is still pre-release and asked to rename the
  remaining internal Luvelox/C2ES-era identifiers now, even if servers need a
  short restart.
- Completed broad internal rename:
  - Unified shell moved from `src/backend/luvelox_app.py` to
    `src/backend/imperialax_app.py`.
  - Account store moved from `src/backend/services/luvelox_auth_store.py` to
    `src/backend/services/imperialax_auth_store.py`.
  - Unified frontend moved from `src/frontend/luvelox/` to
    `src/frontend/imperialax/`.
  - iOS unified package/project moved from `ios/LuveloxMVP*` to
    `ios/ImperialAXMVP*`, with Swift target/type names changed to
    `ImperialAXApp` and bundle id changed to `com.imperialax.mvp`.
  - Android unified app moved from `android/LuveloxMVP` to
    `android/ImperialAXMVP`, package/application id changed to
    `com.imperialax.app`.
  - Tests, scripts, product docs, product images, and app icon/source asset
    paths were renamed to ImperialAX where they are active repo assets.
- Important migration note:
  - Because the iOS bundle id and Android application id changed, existing
    installed test builds with the old app id will not update in-place. Fresh
    install is expected until production identifiers are finalized.
  - iOS real-device installation now needs a provisioning profile for
    `com.imperialax.mvp`.
- Verification:
  - Backend targeted suite passed:
    `.venv/bin/pytest tests/backend/test_imperialax_modules.py tests/backend/test_simple_injection_model_labels.py -q`.
  - JS syntax checks passed for `src/frontend/imperialax/app.js`,
    `login-v2.js`, and `admin.js`.
  - Ruff passed for the touched backend rename surface.
  - `swift build --package-path ios/ImperialAXMVP --scratch-path ...` passed.
  - `xcodebuild -project ios/ImperialAXMVPApp/ImperialAXMVPHost.xcodeproj -scheme ImperialAXMVPHost -destination generic/platform=iOS\ Simulator -configuration Debug CODE_SIGNING_ALLOWED=NO build` passed.
  - `swift build` for `ios/DDLaminateMVP` and `ios/InjectionMVP` passed.
  - Android Gradle `:app:compileDebugKotlin` passed for
    `android/ImperialAXMVP`, `android/DDLaminateMVP`, and
    `android/InjectionMVP`.

## 2026-07-22 - Full Codebase Audit and Stabilization
- User requested a slow, detailed review and cleanup across the complete repository.
- Audit report:
  - `docs/reviews/2026-07-22-codebase-audit.md`.
- Security repairs:
  - Removed the broad `/data` static mount that could expose the auth SQLite database.
  - Removed fixed demo/admin session tokens from backend, web, iOS, and Android.
  - Made demo login, public signup, self-service password reset, and entitlement overrides
    default-closed behind explicit `IMPERIALAX_ENABLE_*` flags.
  - Removed implicit admin-email defaults.
  - Added shared CSV upload guards: 16 MiB per file and 256 MiB per batch by default, configurable
    with `IMPERIALAX_MAX_CSV_UPLOAD_BYTES` and `IMPERIALAX_MAX_CSV_BATCH_BYTES`.
- Correctness and maintenance repairs:
  - Centralized deep response-model detection and added registry regression tests.
  - Removed a duplicate public data-loader definition.
  - Reduced mypy from roughly 350 errors to zero and made CI enforce it.
  - Ruff lint/format and editable package installation now pass.
  - Added Gradle 8.9 wrappers for all Android apps.
- Verification:
  - Full non-slow/non-GPU Python suite: 210 passed; only two known SciPy precision warnings remain.
  - mypy: zero errors; Ruff lint/format: passed; frontend JavaScript syntax: passed.
  - iOS package tests: DD 11, Injection 8, ImperialAX 6, all passed.
  - Android DD/Injection/ImperialAX Gradle test/compile: passed.
  - Unified API `/health` and `/ready`: passed; all core DD/u3 and Injection artifacts loaded.
- Important unresolved items:
  - Authentication is not yet enforced consistently across unified/standalone APIs.
  - Native web handoff uses query-string session tokens; mobile storage is not Keychain/Keystore-backed.
  - Four app composition roots remain, and the DD server still contains wedding routes.
  - Optimization still hardcodes a 6 x 4 panel.
  - Generic dataset/training/worker APIs remain explicit HTTP 501/NotImplemented scaffolds.
  - Roughly 92 active files retain internal `KyulAI` compatibility identifiers; a dedicated migration
    is needed rather than a blind text replacement.
- Local ignored `.env.local` contains an OpenAI API key. It was not tracked, but rotate it as a
  precaution because it was visible during local review.
- No commit was created. Existing untracked 8 x 8 data and fixed-holdout smoke reports were preserved.

## 2026-07-22 - 8x8 Curve CSV Batch Capacity Check
- User added `data/New_data/8x8_Case3` and `data/New_data/8x8_Case4` and reported that
  only 230 files appeared selectable during Curve CSV sorting.
- Root cause:
  - Case3 contains only 230 force-displacement CSV files.
  - `force_disp_Test_031.csv` through `force_disp_Test_100.csv` are missing (70 files).
  - Case3 still has 300 plot PNGs and 300 transition-load rows.
  - Case4 contains all 300 force-displacement CSVs, plots, and transition-load rows.
- Batch-capacity changes:
  - Backend continues to allow up to 1,000 files per batch request.
  - Web now accepts up to 1,000 selected CSVs and automatically sends them in sequential chunks of 200.
  - Added selected file count, total size, and batch progress text in Korean and English.
  - Added a 256 MiB browser-side total limit, matching the backend cumulative limit; per-file limit is 16 MiB.
  - Cached the classical curve joblib bundle and deep sequence PyTorch model so batch prediction no
    longer reloads the same artifact for every CSV.
- Verification:
  - Added a regression test that submits 301 CSV files; all 301 are accepted.
  - Actual Case4 batch test classified all 300 real CSVs successfully in 18.767 seconds: 300 OK, 0 errors.
  - Full Python suite: 211 passed, 2 known SciPy warnings.
  - JS syntax, Ruff, mypy, and diff checks passed.
- Generated upload metadata under `data/New_data/batch_metadata/` using the corrected
  `scripts/dd_make_curve_batch_metadata.py` defaults.
- Restarted the DD/Laminate server on port 8000 so model caching and upload guards are live.
- Public Cloudflare-path verification at `https://laminate.imperialax.com`:
  - Sent the actual Case4 set in the same 200 + 100 chunks used by the browser.
  - 300 files classified successfully, 0 errors, total elapsed time 29.657 seconds.

## 2026-07-22 - Home WSL Connectivity and Internet Check
- Confirmed remote access from the Mac to the home Windows WSL2 host through Tailscale/SSH.
- Remote host:
  - Tailscale IP: `100.65.153.56`.
  - User: `user`.
  - Hostname: `DESKTOP-6MNJOKL`.
  - Kernel: WSL2 Linux `6.18.33.2-microsoft-standard-WSL2`.
- Mac-to-home Tailscale ping:
  - 0% packet loss.
  - Warm round trips were approximately 6.8-9.4 ms; the first packet took 146.8 ms.
- Home WSL internet test using Cloudflare endpoints:
  - External ping to `1.1.1.1`: 2.87 ms average, 0% loss.
  - 25 MB single-stream download: 9,545,518 bytes/s, approximately 76.4 Mbps.
  - Upload tests: approximately 91.1 Mbps at 10 MiB, 92.9 Mbps at 25 MiB, and 93.3 Mbps at 50 MiB.
- The Cloudflare endpoint returned a one-byte response for the 100 MB and 250 MB download probes,
  so those invalid samples were excluded. The download figure is a conservative single-stream result.
- `speedtest`/`speedtest-cli` is not installed in WSL; network checks were completed without installing software.

## 2026-07-22 - Double-Double Technical Overview Review
- Reviewed the newly added `data/PPT/double_double_composite_laminate_technical_overview.md`
  against primary DD literature, the current physics feature code, project UI/RAG formulas, and the
  6x4/6x8/8x8 dataset state.
- Added the detailed review at `docs/reviews/2026-07-22-double-double-technical-overview-review.md`.
- Overall finding:
  - The document is a strong and mostly accurate generic DD overview.
  - It should not yet be ingested as unquestioned RAG or training ground truth.
- Required corrections:
  - The Section 3 building-block definition and the 22.5/67.5 example use different ply-order families.
  - `unsymmetric -> B != 0` is stated too absolutely.
  - The 16-ply/four-block claim needs its 2% criterion and stacking-order scope directly attached.
  - Proposed schema fields such as `B_norm_percent` need reproducible mathematical definitions.
- Critical project inconsistency:
  - Physics feature code expands Case3 as `[[±theta1]/[±theta2]/[∓theta2]/[∓theta2]]2`.
  - Web, iOS, Android, and RAG display `[[±theta1]/[±theta2]/[∓theta1]/[∓theta2]]2`.
  - The user subsequently confirmed the UI/RAG formula is canonical. Centralize all formulas and
    expanded sequences in one registry, then retrain the physics-feature model family.
- Recommended model roadmap:
  - Physics Feature Pack v3 with full normalized ABD, Tsai trace, A*-D* and B* residuals, and
    lamination parameters.
  - A sequence-aware ply encoder for Case5/custom formulas instead of relying only on Case one-hot flags.
  - Store Force and U3 curves, Pt method/version, fit windows, R2, label source, and confidence.
  - Add imperfection/eigenmode/BC/load metadata to study why response Types occur.
  - Use curated 8x8 data first as a true external geometry holdout before adding it to training.

## 2026-07-22 - Canonical Case3 Confirmed and Retraining Impact
- User confirmed the canonical Case3 formula is
  `[[±theta1]/[±theta2]/[∓theta1]/[∓theta2]]2`.
- The UI, app, and RAG formula is correct, but `src/ml/dd_laminate/laminate_physics.py`
  currently expands Case3 as `(pm1 + pm2 + mp2 + mp2) * 2`, omitting `mp1` and duplicating `mp2`.
- The correct expansion is `(pm1 + pm2 + mp1 + mp2) * 2`.
- Active Laminate models requiring corrected-feature retraining:
  - Geometry ML (`theta_physics_geometry_v1`)
  - Geometry DL (`theta_physics_geometry_v1`)
  - Hybrid Student and its physics-feature teacher/distillation chain
  - Physics XAI artifacts and reports
- Physics-based u3 ML/DL models also require retraining.
- Theta/case-only classifiers and Curve CSV classifiers do not require retraining solely for this
  formula-code correction because they do not calculate ABD features from the generated stack.
- Do not change only the inference feature builder while serving the old artifacts. Feature names stay
  the same while their numerical meaning changes, which would create a silent train/serve mismatch.
- If the original Abaqus analyses used the confirmed canonical sequence, raw curves, Type labels, and
  Pt targets remain valid. Recompute derived features and retrain; no Abaqus rerun is required.

## 2026-07-22 - Canonical Case3 Retraining and Deployment Promotion Completed
- Added one canonical case registry at
  `src/ml/dd_laminate/case_definitions.json` and a typed Python access layer in
  `src/ml/dd_laminate/case_definitions.py`.
- Canonical Case3 is now expanded as
  `[[±theta1]/[±theta2]/[∓theta1]/[∓theta2]]2`, producing 16 balanced plies.
- Preserved historical artifacts through explicit `legacy_case3_v1` feature semantics. Old saved
  prediction records remain readable, but no old model is exposed as a deployment default.
- Added corrected feature families:
  - `theta_physics_canonical_v2`
  - `theta_physics_compact_canonical_v2`
  - `theta_physics_nn_canonical_v2`
  - `theta_physics_geometry_canonical_v2`
- Retrained on the home RTX 5070 WSL host:
  - Geometry Tree: `models/dd_laminate_response_geometry_tree_canonical_v2`
  - Geometry GointMLP: `models/dd_laminate_response_geometry_goint_canonical_v2`
  - Hybrid Student: `models/dd_laminate_response_hybrid_student_canonical_v2`
  - u3 Tree/GointMLP: `models/dd_laminate_u3_forecast_physics_canonical_v2`
  - model-specific response and u3 XAI reports under corresponding `reports/*canonical_v2` paths.
- Corrected five-fold grouped CV:
  - Tree: Type accuracy 0.9639, macro F1 0.9634, Pt MAE 267.79 kips,
    normalized curve RMSE 0.00570.
  - GointMLP: Type accuracy 0.9567, macro F1 0.9567, Pt MAE 706.01 kips,
    normalized curve RMSE 0.03069.
  - Hybrid: Type accuracy 0.9728, macro F1 0.9720, Pt MAE 393.28 kips,
    normalized curve RMSE 0.00777.
- Corrected deterministic grouped holdout:
  - Tree: Type accuracy 0.9451, Pt MAE 200.21 kips.
  - GointMLP: Type accuracy 0.9258, Pt MAE 717.14 kips.
  - Hybrid: Type accuracy 0.9451, Pt MAE 303.19 kips.
- u3 corrected grouped CV:
  - Tree: Pt MAE 227.88 kips, Type accuracy 0.979, normalized curve RMSE 0.0064.
  - GointMLP: Pt MAE 166.16 kips, normalized curve RMSE 0.0102.
- Deployment policy:
  - Geometry Tree remains the default because it has the best Pt and curve accuracy.
  - Hybrid remains the Type-screening challenger.
  - GointMLP remains the direct deep-learning comparison.
- Switched backend API defaults, web, iOS, and Android to the corrected canonical model keys.
  Historical registry entries remain for compatibility only.
- Verification completed:
  - canonical/unit tests: 5 passed;
  - backend DD contract tests: 16 passed;
  - iOS Swift package tests: 11 passed;
  - Android Gradle debug unit-test build: successful;
  - all five corrected prediction endpoints and local XAI endpoints returned HTTP 200.

## 2026-07-22 - Laminate Forecast Curve Label Readability
- The user reported that the web response curve looked visually broken because the vertical Force
  axis title overlapped long Y-axis tick labels, and the Predicted Pt callout was too large.
- Updated the v2 response-curve renderer to:
  - reserve more left-side space for five- and six-digit force tick labels;
  - use smaller responsive axis fonts and keep the Force title outside the tick-label column;
  - reduce the Predicted Pt callout title/value fonts, padding, height, and marker size;
  - retain a compact variant for narrow/mobile canvases.
- Updated English and Korean v2 asset cache keys so the deployed page does not reuse the previous
  chart-rendering script.

## 2026-07-22 - Completed 8x8 Case3 CSV Delivery and External Geometry Baseline
- The previously missing Case3 CSV files `force_disp_Test_031.csv` through
  `force_disp_Test_100.csv` were added under `data/New_data/8x8_Case3/csv`.
- Verified the full delivered 8x8 set before ingestion:
  - Case3: 300 transition rows, 300 force-displacement CSVs, and 300 plots.
  - Case4: 300 transition rows, 300 force-displacement CSVs, and 300 plots.
  - All 600 CSVs were readable, contained finite numeric pairs, and had monotonic displacement.
- Generalized `scripts/dd_classify_new_data_curves.py` and
  `scripts/dd_make_curve_batch_metadata.py` so they support both the historical 6x8 folder layout
  and the new case-local `8x8_Case*/csv` layout.
- Classified all 600 curves with the established Curve CSV ExtraTrees model:
  - Case3: Type1 43, Type2 175, Type3 82.
  - Case4: Type1 22, Type2 210, Type3 68.
  - 170 rows had confidence >= 0.70; 430 rows remain high-priority human-review candidates.
  - Outputs: `reports/new_data_8x8_curve_type_classification.csv` and `.md`.
- Generated browser batch metadata for both cases under `data/New_data/batch_metadata`.
- Preserved the 8x8 delivery as a quarantined external geometry holdout at
  `data/datasets/DD_8x8_external_holdout_v1` before using any 8x8 row for training.
  Type is explicitly stored as a confidence-bearing pseudo-label; provided Pt and curve CSVs are
  retained as direct evaluation targets.
- Evaluated all current canonical-v2 deployed models on the untouched 8x8 Case3/Case4 set:
  - Geometry Tree: Pt MAE 3502.40, normalized curve RMSE 0.02173.
  - Geometry GointMLP: Pt MAE 6788.33, normalized curve RMSE 0.02068.
  - Hybrid Student: Pt MAE 2106.87, normalized curve RMSE 0.01726.
  - Tree pseudo-Type agreement was 78.83% over all rows and 100% over the 170 rows whose Curve CSV
    pseudo-label confidence was at least 0.70.
- Interpretation: 8x8 is a material out-of-geometry shift from the 6x4/6x8 training domain. Keep an
  untouched 8x8 test partition, review ambiguous Type labels, then retrain geometry-aware models
  with the remaining 8x8 rows rather than contaminating the only external baseline.
- Detailed metrics: `reports/dd_response_8x8_external_holdout_canonical_v2`.

## 2026-07-22 - WSL Remote Connectivity Recheck
- Rechecked the home WSL host at `100.65.153.56` before discussing a server migration.
- Tailscale network connectivity is healthy: ICMP returned 0% loss with approximately 9-16 ms latency.
- A direct SSH probe using the Mac default identity failed because that command did not specify the
  project key. This was not a WSL outage.
- The configured remote runner `scripts/remote/Run-WSLGPU.sh`, which uses
  `~/.ssh/kyulai_wsl_gpu_codex`, connected successfully and returned host `DESKTOP-6MNJOKL`, user
  `user`.
- Current serving remains on the Mac; WSL is reachable and ready for a planned serving migration.

## 2026-07-22 - ImperialAX Production Serving Migrated to WSL
- Migrated ImperialAX Laminate and Injection production serving from the office Mac to the home
  Windows PC's Ubuntu WSL2 environment at `/home/user/projects/KyulAI`.
- Backed up the existing remote source and synchronized the current backend, web assets, model
  registries and artifacts, RAG data, reports, authentication database, environment configuration,
  and required runtime credentials over the dedicated SSH/Tailscale path.
- Added and enabled three WSL user systemd services:
  - `imperialax-laminate.service` on port 8000;
  - `imperialax-injection.service` on port 8010;
  - `imperialax-cloudflared.service` for the public tunnel.
- Created the dedicated Cloudflare Tunnel `imperialax-wsl-serving`, ID
  `e8928d27-7518-4ba9-ac36-108ca3a78718`, and moved all seven ImperialAX hostnames to it.
- Kept the former Mac tunnel running because it still serves unrelated `cafedecafe.co.kr` and
  other domains. ImperialAX DNS no longer routes through the Mac tunnel.
- Verified WSL-local `/health` and `/ready` for both APIs, all canonical Laminate/u3 and Injection
  model readiness checks, and real Laminate and Injection prediction requests.
- Verified all public ImperialAX routes, both external readiness endpoints, and real external
  predictions. The new tunnel registered four connectors, received production requests, and
  reported zero request errors during cutover validation.
- Added Windows login startup and health-check scripts plus the operations and rollback guide at
  `docs/IMPERIALAX_WSL_SERVING.md`.

## 2026-07-22 - CafeDeCafe and Nangman Production Serving Migrated to WSL
- Migrated all seven `cafedecafe.co.kr` hostnames from the office Mac to the home Windows WSL host.
- Reused the WSL Laminate and Injection origins for wedding, DD/Laminate, and Injection routes.
- Migrated `/Users/danlee/nangman-rag` to `/home/user/projects/nangman-rag`, including a consistent
  SQLite snapshot, private runtime configuration, source, and tests.
- Built an independent Python 3.11 environment on WSL; all 17 Nangman tests passed.
- Added `cafedecafe-nangman.service` on port 8020 and a persistent 15-minute
  `cafedecafe-nangman-sync.timer`. The first WSL sync completed with zero failures and added the
  latest selected DCInside documents and chunks.
- Created the dedicated Tunnel `cafedecafe-wsl-serving`, ID
  `68025491-2fa9-48a3-bc61-9caf6bd8e6d5`, using the CafeDeCafe zone certificate and routed all
  seven production hostnames to it.
- Used the former tunnel as a temporary WSL migration bridge, disabled the old Mac launch agent,
  then removed the bridge after the new tunnel began receiving traffic.
- Verified all public pages, Laminate and Injection readiness, Nangman authentication behavior,
  a real Nangman RAG answer with sources, and Cloudflare metrics with zero request errors.
- Updated the Windows login startup script to restore ImperialAX and CafeDeCafe services together.
- Added operations and emergency rollback instructions at `docs/CAFEDECAFE_WSL_SERVING.md`.

## 2026-07-22 - Wedding Runtime Restored and Samsung Internet Fonts Fixed
- Confirmed that the wedding migration had copied the UI but not its persistent runtime files.
  The original Mac data was still intact at `runtime/wedding/rsvp-submissions.jsonl` and
  `runtime/wedding/admin-token.txt`; no record had been deleted.
- Backed up the WSL wedding runtime, briefly stopped the Laminate service, and restored both files
  with owner-only permissions. Source and destination SHA-256 hashes match exactly.
- Verified the restored production state without exposing private content:
  - 2 total stored records;
  - 1 RSVP record;
  - 1 guestbook record;
  - the public guestbook and authenticated admin totals both return the restored data.
- Removed Google Fonts runtime requests from the main invitation, parents page, RSVP page, bus
  page, and share-test page.
- Added compact self-hosted subsets of Gowun Batang, Cormorant Garamond, and Pinyon Script under
  `src/frontend/wedding/assets/fonts`, with their SIL Open Font License files.
- Replaced the generic `cursive` fallback with readable Korean and Latin serif fallbacks, and added
  an extra narrow-screen rule so the scripted couple name does not clip on small Galaxy Flip views.
- Synchronized the complete wedding frontend directory to WSL. Mac and WSL directory digests match
  across all 23 files.
- Production verification used a Galaxy Flip/Samsung Internet user agent at 412 px:
  - all local CSS and WOFF resources returned HTTP 200;
  - both the script and Korean fonts loaded through the FontFace API;
  - no Google font links remained;
  - body width matched the viewport with no horizontal overflow;
  - the restored guestbook entry rendered in the page.

## 2026-07-22 - Wedding Signature Made Independent of Web Fonts
- The user reported that the scripted couple name still did not appear correctly on a physical
  Galaxy Flip Samsung Internet browser after the self-hosted font deployment.
- Confirmed production was already served from WSL, HTML responses used `no-store`, and Cloudflare
  was not serving stale invitation HTML.
- Replaced the first-cover scripted couple name with a transparent high-resolution PNG rendered
  from the same Pinyon Script font. The heading keeps meaningful alt text for accessibility.
- Deployed the asset to the main invitation, parents page, and share-test page with an explicit
  cache-busting URL and eager/high-priority loading.
- Verified production with the Samsung Internet user agent while forcibly blocking every web-font
  request: the signature image still loaded at its intended size, the page had no horizontal
  overflow, and the restored guestbook entry remained visible. Mac rollback was therefore not
  required for this rendering issue.

## 2026-07-22 - Wedding Root URL Asset Paths Corrected
- A physical Galaxy screenshot showed the couple-name image's alt text instead of the rendered
  signature. This proved that the issue was a failed image request, not Samsung Internet's font
  rendering.
- Identified the root cause: the invitation is also served at `https://cafedecafe.co.kr`, while its
  `./assets/...` references resolved to `/assets/...`; the files are mounted at
  `/wedding/assets/...`, so fonts, the signature, map icons, and calendar download returned 404 at
  the root URL.
- Changed all wedding asset references to absolute `/wedding/assets/...` paths and added cache
  versions to the font stylesheet and signature image URLs. The same fix covers the main,
  parents, share-test, RSVP, and bus pages.
- Deployed the corrected frontend to WSL and verified the public root route with a 412 px mobile
  viewport: the signature image loaded at its full natural width, no images failed, all local font
  families were available, there was no horizontal overflow or console error, and the preserved
  guestbook entry remained available. Both the application and CafeDeCafe tunnel services stayed
  active, so no rollback to the Mac was needed.

## 2026-07-22 - Wedding Typography Parity and Forced-Dark Opt-Out
- A second physical Galaxy screenshot showed that the signature image was fixed but the remaining
  Latin typography still fell back to a sans-serif face. Comparing the current files with the
  original committed invitation confirmed that the migration repair had replaced the original
  Google Fonts setup with a locally generated variable-font subset.
- Restored the original Google Fonts declarations and original font-family priority for Cormorant
  Garamond, Gowun Batang, and Pinyon Script. Kept self-hosting as a fallback, but replaced the
  Cormorant variable WOFF with static WOFF2 files for weights 400, 500, and 600; also added static
  WOFF2 fallbacks for Gowun Batang and Pinyon Script for broader Samsung Internet compatibility.
- Added `<meta name="color-scheme" content="only light">`, the legacy supported-color-schemes
  declaration, and `color-scheme: only light` to the main invitation, parents, RSVP, bus, share
  test, and admin pages. This explicitly opts the invitation out of Samsung/Chromium automatic
  dark-theme color overrides while retaining the original light palette.
- Audited every wedding page at 412 px after deployment. All pages returned HTTP 200, had no failed
  images, no horizontal overflow, no browser console errors, and computed `light only`. All six
  static WOFF2 assets and the Samsung-targeted Google Fonts stylesheet returned HTTP 200. The WSL
  frontend digest matched the Mac source digest, both services remained active, and the existing
  guestbook record was preserved.

## 2026-07-22 - Wedding Cover Protected from Samsung Device-Font Override
- The physical Galaxy screenshot still showed sans-serif Latin text even though the CSS fallback
  chain ended in Georgia/Times/serif and both Google-hosted and self-hosted fonts returned HTTP 200.
  This is consistent with Samsung Internet applying a device-font preference over the page's own
  `font-family`, rather than the handset simply lacking the requested fonts.
- Rendered the cover's remaining static Latin typography from the original Cormorant Garamond font
  into high-resolution transparent PNG assets: the invitation kicker, date/time/venue group, and
  three-line footer. Meaningful `alt` text remains in the markup.
- Applied the assets to the main invitation, parents page, and share-test page. The scripted names
  were already protected by the same raster approach, so the complete first cover is now immune to
  browser or accessibility settings that forcibly replace page fonts.
- Deployed the frontend to WSL after creating a remote rollback archive. Public verification used a
  Samsung Internet user agent plus a deliberately forced Arial override: all four cover typography
  images remained correct, loaded at their intended dimensions, had no failed requests, and caused
  no horizontal overflow. Both the application and CafeDeCafe tunnel services remained active.

## 2026-07-22 - Kakao Share Card Updated to the Current Wedding Cover
- The Kakao/Open Graph card still referenced `og-classic-v2.png`, whose cover used shortened names
  and an older venue treatment.
- Captured the current first screen as a dedicated 1200 x 630 social preview and added it as
  `src/frontend/wedding/assets/og-classic-v3.png`. The card now shows the full scripted names,
  current English date/time/venue typography, and the current footer treatment.
- Updated Open Graph, Twitter card, and Kakao SDK `imageUrl` references across the main invitation,
  parents, share-test, RSVP, and bus pages. The new filename also avoids reuse of the old cached
  image object.
- Deployed the updated frontend to WSL after creating a rollback archive. Both the root and
  `/wedding/` routes expose the v3 image to a Kakao crawler user agent; the public asset is 1200 x
  630 and its SHA-256 digest matches the local source. Both serving services remained active.

## 2026-07-22 - Parents Kakao Card Copy Restored
- Restored the parents-only Kakao card wording requested by the family.
- The card title is `저희 자녀의 결혼식에 초대합니다`; the description is
  `승찬·재효 장남 성용·순이 장녀 모바일 청첩장`.
- Updated both the parents page Open Graph metadata and the Kakao SDK feed payload while leaving
  the standard invitation card unchanged.
- Deployed the single parents page to WSL after saving a rollback copy. A Kakao crawler request and
  the live JavaScript payload both returned the requested wording, and both serving services stayed
  active.

## 2026-07-22 - Samsung Internet Body Typography Hardened
- The physical Samsung Internet browser preserved the rasterized first cover but continued to
  replace live HTML text in the remaining invitation sections with the device sans-serif font.
- Kept the body as accessible, selectable HTML rather than converting the entire invitation and
  forms into images. Strengthened every existing public-page font-family declaration with author
  priority and added a direct serif assignment to all descendant elements; more-specific Latin
  label rules continue to select Cormorant Garamond.
- Applied the compatibility rules to the main invitation, parents page, share-test page, RSVP form,
  and bus form. The admin UI was intentionally left unchanged.
- The restored Gowun Batang metrics exposed an existing RSVP radio input overflow. Reduced the
  visually hidden radio controls to 1 x 1 px so the RSVP page no longer extends beyond the viewport.
- Deployed the public wedding frontend to WSL after creating a rollback archive. Production tests
  used a Samsung Internet user agent, blocked Google Fonts, and injected a later forced Arial rule.
  The main, parents, RSVP, and bus pages still computed to the self-hosted Gowun Batang/Cormorant
  families, returned no failed requests, and matched the 412 px viewport without overflow. Both
  serving services remained active.
## 2026-07-22 - Samsung Internet Font Setting Guidance Corrected

- The previously mentioned Samsung Internet path `Settings > Labs > Apply device font settings to web pages` is historical guidance from Samsung Internet 14.0.1.62 (2021), not a reliable path for current Samsung Internet versions.
- Current Galaxy checks relevant to font rendering are `Settings > Display > Font size and style` and `Settings > Accessibility > Vision enhancements > High contrast fonts`.
- Do not rely on a Samsung Internet `Labs` toggle when diagnosing the wedding invitation typography on current devices.
## 2026-07-22 - Mac-to-WSL Serving Migration Audited

- Completed a checksum and runtime audit of the wedding, DD Laminate, Injection, ImperialAX auth,
  Laminate RAG, Nangman RAG, model artifacts, environment configuration, and public CafeDeCafe
  routes after the Mac-to-WSL migration.
- Found no missing production assets or persistent records. Wedding frontend/runtime, auth DB,
  deployed UI trees, RAG index, and deployed model directories match their Mac sources.
- Nangman WSL data is newer rather than incomplete: 310 documents and 1,628 chunks versus 284
  documents and 1,602 chunks on the former Mac database.
- All WSL serving services and the Nangman sync timer are active and enabled; public readiness
  checks report all Laminate and Injection models loaded.
- Recorded three operational follow-ups: add rotating WSL data backups, remove the Windows-login
  dependency caused by `Linger=no`, and decide whether to keep or stop the Mac rollback origins.
- Full evidence is recorded in `docs/reviews/2026-07-22-wsl-serving-migration-audit.md`.

## 2026-07-22 - WSL Serving Resilience Completed

- Added `scripts/backup_wsl_serving_state.sh` and a daily systemd user timer that back up wedding
  submissions/admin state, ImperialAX auth state, private environment files, Nangman SQLite data,
  Cloudflare credentials, and installed service definitions to the Windows disk.
- Backups are stored under `C:\Users\user\ImperialAX-Backups`, retain 14 generations, and include a
  SHA-256 sidecar. The first real archive was extracted and all three SQLite snapshots passed
  `PRAGMA integrity_check`; the wedding JSONL restored with both records intact.
- Enabled WSL user lingering (`Linger=yes`) and added the backup timer to the Windows login startup
  script.
- Prepared `Install-ImperialAX-WSL-BootTask.cmd` and its PowerShell installer on the Windows desktop.
  Registering an at-startup Windows task requires one interactive UAC approval and cannot be
  completed from the non-elevated remote WSL session.
- Disabled and stopped the former Mac DD, Injection, Nangman API, and Nangman sync launch agents.
  The Mac Cloudflare Tunnel was already disabled. All public ImperialAX and CafeDeCafe endpoints
  remained healthy after the Mac listeners on ports 8000, 8010, and 8020 stopped.

## 2026-07-23 - 8x8 Case 2 Curve Dataset Sorted

- Inspected the new `data/New_data/8x8_Case2` delivery. It contains 300 transition rows, 300
  force-displacement CSV files, and 300 plot images covering `Test_001` through `Test_300` with no
  missing or duplicate IDs. All curve files contain two numeric columns; curve lengths range from
  255 to 1,001 points.
- Extended `scripts/dd_classify_new_data_curves.py` to accept both the established `Original` plot
  folder and the new Case 2 delivery's `Ori` folder. Added a regression test for the `Ori` layout;
  all four ingestion tests pass.
- Generated `data/New_data/batch_metadata/curve_batch_metadata_8x8_Case2.csv` and reran the complete
  8x8 Case 2/3/4 sorting pipeline so the combined manifest remains coherent at 900 curves.
- Case 2 pseudo-label counts are Type 1: 41, Type 2: 177, Type 3: 82. The classifier is the existing
  `models/dd_laminate_cases_2_3_4_csv_v1/curve_classifier.joblib` ExtraTrees model using theta,
  Case, Pt, and force-displacement curve features. These are model-assisted pseudo-labels, not
  human-confirmed ground truth.
- Sorted Case 2 files are under `data/New_data/classified_8x8_curve_csv_v1/Case2`; the combined
  manifest and review report are `reports/new_data_8x8_curve_type_classification.csv` and `.md`.
  Case 2 confidence averages 0.622: 224 records are marked high review priority, 51 medium, and 25
  low, so the high-priority queue should be manually checked before using these labels for training.
- Verified that each Case 2 source ID appears exactly once in the manifest, each sorted CSV has a
  matching plot and type manifest entry, no copied file is empty, and the source checksum remained
  `595b6c5fd712ec040240fb10f15099d41633228eb460847a26e1adc3b5763010` before and after sorting.

## 2026-07-23 - Clarified 8x8 Training Inclusion

- None of the 900 delivered 8x8 curves are currently included in the deployed Laminate Forecast
  model training set.
- The earlier 600-row 8x8 set consists of Case3 and Case4, 300 rows each. It was classified and
  evaluated as `external_holdout_not_for_training`; it was not used to fit the models.
- The newly delivered 300-row 8x8 Case2 set has only been validated and sorted so far. It has not
  yet been added to either the preserved holdout dataset or a training dataset.
- Current geometry-aware Tree/GointMLP/Hybrid training uses 1,800 rows: 900 curated 6x4 rows plus
  900 6x8 rows. The phrase `600 rows per Case` in that dataset means 300 rows at 6x4 plus 300 rows
  at 6x8 for each of Case2, Case3, and Case4; it does not refer to the 8x8 delivery.
- Before 8x8 retraining, preserve a final untouched 8x8 test partition across all three Cases and
  review low-confidence pseudo-labels in the remaining training partition.

## 2026-07-23 - Clarified 6x4/6x8 Holdout Policy

- A deterministic 20% fixed evaluation split exists for the combined 6x4/6x8 dataset at
  `reports/dd_response_geometry_canonical_v2_fixed_holdout/fixed_holdout_manifest.csv`.
- The split contains 364 rows: 182 from 6x4 and 182 from 6x8. Its paired train side contains 1,436
  rows: 718 from each geometry. It is grouped by `Case + theta1 + theta2`, so identical angle/Case
  combinations do not cross between train and holdout during that evaluation.
- This fixed split was used to train temporary evaluation models and compare Tree, GointMLP, and
  Hybrid performance on stable rows. It is not a permanently untouched external holdout for the
  deployed models.
- The deployed final geometry-aware models were subsequently fit on all 1,800 available 6x4/6x8
  rows. Therefore no 6x4 or 6x8 row remains completely unseen by the current deployed final model.
- The quarantined 8x8 dataset is currently the only geometry-level external holdout that the
  deployed models have not used for fitting.

## 2026-07-23 - Recommended Final 8x8 Validation Policy

- Because future independent DD data is not guaranteed, do not retrain the validated deployment
  model on all 2,700 rows.
- Lock 180 of the 900 8x8 records as a permanent final test set: 60 records per Case, stratified by
  pseudo-Type and classifier-confidence band. Manually review the selected Type labels because the
  Type targets are pseudo-labels; Pt and force-displacement curves remain direct evaluation targets.
- Use the remaining 720 8x8 records together with all 1,800 existing 6x4/6x8 records. The resulting
  2,520-row development set can use grouped cross-validation for feature, model, and hyperparameter
  selection.
- After model selection, fit the validated deployment artifact on those same 2,520 development
  rows and evaluate the locked 180 rows exactly once for the release report. Keep the locked split
  manifest versioned and never use those rows for fitting, tuning, early stopping, or model choice.
- Prioritize Pt MAE and normalized curve RMSE on the final test set. Report Type agreement as a
  secondary metric until the selected 8x8 Type labels have been human-reviewed.
- An optional 2,700-row all-data model may be retained as an explicitly unvalidated challenger, but
  it should not replace the validated default unless a genuinely new external test set arrives.

## 2026-07-23 - Unified Permanent Holdout Across 6x4, 6x8, and 8x8

- Confirmed that all three panel geometries contain the exact same 900 unique
  `Case + theta1 + theta2` design groups. There are no design groups missing from or added to the
  8x8 delivery relative to the existing 6x4/6x8 dataset.
- The permanent split must therefore be assigned at the design-group level, not independently by
  row or geometry. Otherwise the same Case/angle design could appear in training at one panel size
  and in the final test set at another size, producing optimistic leakage.
- Reuse the existing deterministic fixed split: 718 design groups for development and 182 locked
  design groups for final testing. Apply each group assignment to all three panel sizes.
- Resulting row counts across the 2,700 available curves:
  - development: 718 rows per geometry, 2,154 rows total;
  - permanent final test: 182 rows per geometry, 546 rows total.
- Use grouped cross-validation only inside the 2,154-row development partition. After model and
  hyperparameters are frozen, train the release model on all 2,154 development rows and evaluate
  the 546 locked rows once. Do not retrain the validated release artifact on the locked rows.
- This split measures generalization to unseen Case/angle design groups within the three observed
  panel sizes. It does not prove extrapolation to a completely unseen fourth panel geometry; that
  would require future data at another size.

## 2026-07-23 - One Locked Holdout Plus Geometry Cross-Validation

- Do not create two disjoint permanent holdout datasets. Maintain one locked grouped final test set
  and use a separate evaluation protocol for geometry transfer.
- Permanent release gate: the 546-row grouped holdout containing the same 182 locked
  `Case + theta1 + theta2` groups at 6x4, 6x8, and 8x8. This tests unseen laminate designs within
  the three supported sizes.
- Geometry benchmark: run leave-one-panel-size-out evaluation only on the 2,154-row development
  partition. Train on two sizes and test on the third, rotating through 6x4, 6x8, and 8x8. This
  intentionally tests size transfer without consuming another permanent data partition.
- Model and hyperparameter selection may use grouped CV and leave-one-size-out results from the
  development partition. The 546 locked rows must remain outside both workflows and be evaluated
  only after the release configuration is frozen.
- The earlier Case3/Case4 8x8 external evaluation remains an archived historical baseline. The new
  strict protocol requires retraining from scratch on the 2,154-row development partition because
  current deployed models have already seen all 6x4/6x8 rows.

## 2026-07-23 - Three-Geometry Strict Validation And Retraining Completed

- Built `data/datasets/DD_cases_2_3_4_geometry_3size_v1` with 2,700 curves: 900 each at 6x4, 6x8,
  and 8x8. Case2, Case3, and Case4 each contribute 900 rows.
- Froze `data/datasets/DD_cases_2_3_4_geometry_grouped_v1/split_manifest.csv` using the shared
  `Case + theta1 + theta2` group key. It contains 718 development groups (2,154 rows) and 182
  locked groups (546 rows), with no group leakage. The split manifest SHA-256 is
  `af7b4b020abc943c2ff3b942f7b696c9691d7ca796b686c5fdfeba28d8151ed6`.
- Updated response training so grouped CV includes Case in the group key and GointMLP fold
  normalization is fitted on training folds only. GointMLP early stopping now considers Type F1,
  Pt MAE, and curve RMSE instead of Type F1 alone.
- Updated Hybrid distillation so all locked design groups are excluded from synthetic grids and
  validation-near synthetic samples are removed independently inside every strict CV fold.
- Retrained Tree, GointMLP, and Hybrid artifacts on the 2,154-row development partition using the
  RTX 5070 WSL training environment. Grouped CV Type accuracy / Pt MAE results were Tree
  `0.9461 / 176.51`, GointMLP `0.9536 / 641.09`, and Hybrid `0.9582 / 365.67`.
- Evaluated the saved artifacts on the 546 locked rows. Raw Type agreement / Pt MAE / curve-force
  RMSE were Tree `0.9377 / 190.12 / 291.36`, GointMLP `0.9048 / 532.84 / 1,017.90`, and Hybrid
  `0.9341 / 305.64 / 438.50`. Tree is the recommended release candidate for Pt and curve quality;
  Hybrid remains the stronger neural challenger for Type classification.
- Ran leave-one-geometry-out tests inside development. Pt MAE for Tree / GointMLP / Hybrid was
  `9,828.99 / 10,362.35 / 9,950.89` for held 6x4, `1,393.86 / 1,009.84 / 884.15` for held 6x8,
  and `3,643.59 / 7,569.93 / 3,821.11` for held 8x8. This demonstrates acceptable interpolation
  at 6x8 but weak extrapolation to a geometry outside the observed range.
- Separated raw model evaluation from web/app `Pt-curve consistency` post-processing. The current
  force-rescaling post-process preserves Pt but severely distorts max force and force-scale curve
  metrics. Do not use those post-processed force metrics as surrogate-model accuracy claims; replace
  the rescaling approach before release.
- Full results and artifact hashes are recorded in
  `reports/dd_response_geometry_3size_grouped_v1/validation_summary.md`.

## 2026-07-23 - Raw Model Response Restored In Web And Apps

- User chose to show the model prediction directly instead of forcing the curve-fit intersection
  to equal the separately predicted Pt scalar.
- Removed Pt-driven force scaling from the serving paths for Laminate Tree, GointMLP, Hybrid, and
  u3 Tree/GointMLP forecasts. `predicted_max_force` and every returned curve force now retain the
  model output scale.
- The previous `enforce_pt_curve_consistency()` helper remains available only for archived
  comparison and research diagnostics. Serving uses `measure_pt_curve_consistency()`, which records
  the Pt/curve gap without modifying the curve or Max. Force.
- Prediction metrics now identify `response_output_mode=raw_model_prediction` and
  `pt_curve_force_postprocessing_applied=0`.
- Web, iOS, and Android graph semantics were separated: the purple marker is the linear-fit
  intersection, while the red marker is the model-predicted Pt. A disagreement is shown rather than
  hidden by rescaling the force axis.

## 2026-07-23 - Isolated 3-Size Raw-Curve Preview Deployed

- Deployed a temporary research page at
  `https://laminate.imperialax.com/preview/3size` without adding the new models to the production
  Laminate model selector.
- The preview exposes exactly three grouped-holdout artifacts trained on the 2,154-row development
  split: `response_geometry_tree_3size_grouped_v1`,
  `response_geometry_goint_3size_grouped_v1`, and
  `response_hybrid_student_3size_grouped_v1`.
- Added a dedicated `/api/v1/dd-laminate/predict/response/3size-preview` endpoint. It accepts only
  the three preview model keys and returns `raw_model_prediction` with force scale correction
  fixed at `1.0`. The regular production response endpoint retains its existing Pt-aligned
  post-processing until the graph review is complete.
- The graph displays the raw predicted curve, two independently fitted slope segments, their
  purple fit-intersection marker, and the separately predicted red Pt marker. It also supports
  zoom, pan, hover readout, and explicit Pt-versus-fit gap diagnostics.
- Public checks confirmed HTTP 200 for both the main page and preview page, the production model
  registry remains the canonical three models, all preview artifacts are available, and all three
  preview models return 128-point raw curves without force rescaling.
- Verification: Ruff and JavaScript syntax checks passed; targeted backend/model tests completed
  with `23 passed`.
- Restored direct panel geometry entry on the preview page while retaining 6x4, 6x8, and 8x8
  quick presets. Length and width now post directly as `panel_a_in` and `panel_b_in`; changing a
  preset synchronizes the numeric fields, while a custom size clears the preset selection. The
  public page was verified with a 7x5-inch prediction and with 8x8 preset resynchronization.
- Dataset audit found no measured `Case2, theta1=30, theta2=-30` design group at 6x4 or either of
  the other two panel sizes. Predictions at this input are therefore unseen-design surrogate
  estimates, not retrieval of a training curve. The nearest 6x4 Case2 sample is `(30, -25)`
  (`Test_274`, Type 3, Pt 18,587.12 kips), followed by `(36, -31)` (`Test_028`, Type 2,
  Pt 16,320.79 kips).

## 2026-07-23 - Original P1 Plot Fitting Restored In 3-Size Preview

- Confirmed that the 3-size Tree prediction for measured design `Case2, theta1=30, theta2=-25,
  6x4` reproduces the Test 274 curve extremely closely: force RMSE is approximately `8.16 kips`,
  or `0.025%` of the measured peak force. The large visual mismatch came from fit-window selection,
  not the surrogate curve itself.
- Recovered the original P1 plotting method from the user-provided script. On the 1,001-point Test
  274 CSV it selects initial rows `38-44`, second rows `936-940`, and reproduces Pt
  `18,587.1203737 kips` exactly.
- Added `p1_transition_fit_details()` for the temporary preview. Full-resolution data follows the
  original maximum-R2 P1 selection. For reduced 128-point surrogate curves, the independently
  predicted Pt resolves near-tied high-R2 post-kink windows; this changes only the display fit and
  never rescales or edits the predicted curve or Max. Force.
- For the public Test 274 preview, the P1-style fit now uses curve windows `1-7` and `118-122`,
  producing `18,567.26 kips` versus model Pt `18,587.12 kips` (gap `19.86 kips`, `0.1%`). Max.
  Force remains `32,590.47 kips` and force scale correction remains `1.000`.
- Updated graph semantics on `https://laminate.imperialax.com/preview/3size`: red dashed lines are
  the initial/late P1 fits, the purple vertical line is detected kink start, the amber diamond is
  P1 fit Pt, and the red dot is the independent model Pt. Production model selection remains
  unchanged.
- Verification: `23 passed`, Ruff clean, JavaScript syntax clean, public API HTTP 200, and browser
  visual verification completed for the Korean preview page.

## 2026-07-23 - Negative Theta Entry Fixed Across Laminate Web UI

- Fixed the production Laminate Forecast, u3, stack preview, Curve CSV, and temporary 3-size
  preview angle controls so a leading minus sign is preserved while users type negative theta
  values. Previously the preview `input` handler converted the transient empty value produced by a
  lone `-` into `0`, while browser-native number-field behavior could also discard the sign.
- Angle fields use signed text entry with explicit integer validation because some browsers expose
  a lone minus in `type=number` as an empty value. They keep in-progress text untouched,
  synchronize sliders/readouts only after a finite angle exists, and normalize/clamp the completed
  value on change. Range-slider behavior is unchanged.

## 2026-07-23 - Pt-Consistent 3-Size Tree Challenger Deployed

- Added preview model `response_pt_consistent_tree_3size_grouped_v1` without replacing any of the
  three existing 3-size preview models or the production model registry. The artifact is stored at
  `models/dd_laminate_response_pt_consistent_tree_3size_grouped_v1/response_surrogate.joblib`.
- The scalar Tree head jointly predicts Pt, Max. Displacement, Max. Force, normalized Pt
  displacement, and both normalized P1 slopes. The two P1 intercepts are then solved analytically
  so their displayed intersection is exactly the predicted Pt. The PCA response curve remains the
  raw model output; neither the curve nor the force axis is rescaled to pass through Pt.
- Locked 546-row grouped Holdout results were: Type accuracy `0.9359`, macro F1 `0.9325`, Pt MAE
  `191.79 kips`, Max. Force MAE `155.28 kips`, normalized-curve RMSE `0.00603`, and force-curve RMSE
  `291.50 kips`. The displayed P1/Pt gap is `0.0`. Existing 3-size Tree references are Type accuracy
  `0.9377`, Pt MAE `190.12 kips`, Max. Force MAE `153.70 kips`, and force-curve RMSE `291.36 kips`.
  The challenger therefore improves display consistency without a material accuracy change, but it
  does not outperform the existing Tree on raw Holdout regression.
- A full data audit showed that the independent legacy P1 window selector reproduces almost all
  stored 6x4 Pt labels but not most 6x8/8x8 labels. The overall independent fit versus source-Pt
  median gap was `2,417.93 kips`; the geometry medians were approximately `0`, `6,763.75`, and
  `8,896.17 kips` for 6x4, 6x8, and 8x8. Therefore the independent fit remains a diagnostic and is
  not allowed to overwrite the supplied Pt training targets.
- Fixed `_best_p1_second_window()` so a target-guided fit with no candidate above the strict R2
  threshold falls back to the near-best R2 set instead of failing on an empty candidate list.
- The public research preview at `https://laminate.imperialax.com/preview/3size?lang=ko` now lists
  four models. For the Pt-consistent challenger it shows one purple P1 intersection as
  `Predicted Pt`, hides the redundant raw-curve force-crossing marker, and explicitly states that
  the raw response curve is not modified.
- Validation report:
  `reports/dd_response_pt_consistent_tree_3size_grouped_v1/validation_report.md`.
- Verification: targeted ML tests `11 passed`, backend/API contract tests `18 passed`, Ruff and
  Python/JavaScript syntax checks passed, WSL service is active, public API returns the challenger,
  and the public
  Test 274 input produced predicted Pt and displayed P1 Pt of `18,587.12 kips` with gap `0.0` and
  force scale correction `1.000`.

## 2026-07-23 - Pt-Consistent GointMLP And Hybrid Challengers Deployed

- Extended the 3-size Pt-consistent P1 contract to both GointMLP and the distilled Hybrid model.
  The new scalar head predicts Pt, Max. Displacement, Max. Force, normalized Pt displacement, and
  the two normalized P1 slopes. P1 intercepts are solved analytically so both displayed lines meet
  exactly at the predicted Pt; the 128-point neural response curve and Max. Force remain raw model
  outputs with no force-axis rescaling.
- Preserved backward compatibility: existing neural checkpoints still use the original three
  scalar outputs unless `scalar_dim: 6` and `curve_representation: pt_consistent_p1_head_v1` are
  present in the checkpoint.
- Trained both challengers on the WSL RTX 5070 using the fixed grouped protocol: 2,154 development
  rows and 546 locked-Holdout rows, split by Case + theta1 + theta2 across 6x4, 6x8, and 8x8.
  The Hybrid additionally used 45,300 holdout-excluded synthetic design rows distilled from the
  Pt-consistent Tree teacher.
- Locked-Holdout results:
  - Existing GointMLP: Type accuracy `0.9048`, Pt MAE `532.84`, Max. Force MAE `1011.54`,
    force-curve RMSE `1017.90` kips.
  - Pt-Consistent GointMLP: Type accuracy `0.9139`, Pt MAE `525.37`, Max. Force MAE `867.40`,
    force-curve RMSE `908.29` kips, displayed P1/Pt gap `0.0`.
  - Existing Hybrid: Type accuracy `0.9341`, Pt MAE `305.64`, Max. Force MAE `389.45`,
    force-curve RMSE `438.50` kips.
  - Pt-Consistent Hybrid: Type accuracy `0.9322`, Pt MAE `286.66`, Max. Force MAE `362.38`,
    force-curve RMSE `425.62` kips, displayed P1/Pt gap `0.0`.
- Added the two challengers to the isolated public 3-size preview only. The production registry is
  unchanged. `https://laminate.imperialax.com/preview/3size?lang=ko` now exposes six comparison
  models: original and Pt-consistent Tree, GointMLP, and Hybrid pairs.
- Public browser verification at Case 2, theta1 30, theta2 -30, 6x4 produced:
  - GointMLP: predicted Pt and displayed P1 Pt both `17,679.54 kips`.
  - Hybrid: predicted Pt and displayed P1 Pt both `17,319.65 kips`.
  Both returned `response_output_mode=pt_consistent_p1_head_v1`, 128 curve points, force
  post-processing disabled, and no browser console errors.
- Artifacts:
  `models/dd_laminate_response_pt_consistent_goint_3size_grouped_v1/response_goint.pt` and
  `models/dd_laminate_response_pt_consistent_hybrid_3size_grouped_v1/response_goint.pt`.
  Validation report:
  `reports/dd_response_pt_consistent_deep_3size_grouped_v1/validation_report.md`.
- Verification: Ruff clean; targeted ML/backend tests `25 passed`; WSL service active; public model
  registry and prediction requests returned HTTP 200.

## 2026-07-23 - Neural Upgrade Diagnosis And Recommended V2

- A locked-Holdout error breakdown showed that neural errors are concentrated rather than uniform.
  Pt-Consistent GointMLP Pt MAE was `1051.2 / 313.8 / 211.1 kips` for 6x4 / 6x8 / 8x8;
  Pt-Consistent Hybrid was `558.1 / 176.8 / 125.2 kips`. Type 3 remained the hardest response
  family: GointMLP Pt MAE `843.0` and force-curve RMSE `1367.6 kips`; Hybrid Pt MAE `603.0` and
  force-curve RMSE `655.0 kips`.
- The current model sends the same 40-feature vector through 8-10 parallel dense branches and
  directly predicts all 128 normalized curve points. Training uses fixed epochs and fixed loss
  weights without a grouped inner-validation early-stop loop. The Hybrid distillation applies a
  temperature to student logits while using unsoftened Tree probabilities as the teacher target;
  this is a concrete calibration target for v2.
- Recommended first upgrade is `Residual Hybrid v2`: keep the strong Tree prediction as a base and
  train a physics-structured neural network to predict out-of-fold residual corrections for Type,
  Pt, Max. Force, P1 parameters, and a compressed curve representation. This has a better chance of
  beating the Tree than replacing it with a larger standalone MLP.
- Recommended structured branches: theta/trigonometric features, actual ply-sequence encoder,
  normalized CLT ABD descriptors, and geometry/slenderness features. Fuse the branches with a
  gated residual trunk rather than duplicating the full input in every branch.
- Training protocol for v2: keep the 546-row Holdout locked; create grouped inner CV only from the
  2,154 development rows; use early stopping and learning-rate scheduling; correct distillation
  temperature handling; add 6x4 and Type-3-aware weighting; compare 3-5 random seeds. Curve output
  should use a small PCA/autoencoder coefficient head plus Pt/P1 consistency losses instead of an
  unconstrained 128-value head.
- Promotion targets for the neural challenger: Type accuracy at least `0.934`, Pt MAE below
  `250 kips`, Max. Force MAE below `330 kips`, force-curve RMSE below `390 kips`, and no panel-size
  subgroup regression above 10% relative to the current Hybrid.

## 2026-07-23 - Laminate Model Portfolio Decision

- Added the canonical model inventory and decision record at
  `docs/DD_LAMINATE_MODEL_CATALOG.md`.
- On the common 546-row three-size locked Holdout, the original 3-Size Tree remains the strict raw
  metric winner (`93.77%` Type accuracy, `190.12 kips` Pt MAE). The Pt-Consistent Tree is a near
  tie (`93.59%`, `191.79 kips`) and adds exact displayed P1/Pt agreement without altering the raw
  curve, so it is the recommended product-facing default rather than an unconditional numerical
  winner.
- Pt-Consistent GointMLP improves every main metric over its matching original GointMLP.
  Pt-Consistent Hybrid improves Pt, Max. Force, and curve regression over the original Hybrid while
  losing 0.18 percentage points of Type accuracy. It is the best current neural model.
- Recommended future visible set: Pt-Consistent Tree as default, Pt-Consistent Hybrid as the neural
  comparison, and Pt-Consistent GointMLP only when a standalone-DL option is useful. Preserve the
  original three-size models as hidden baselines and archive older generations after recording
  reproducibility metadata.
- The main production page still exposes the older `canonical_v2` Tree/GointMLP/Hybrid set trained
  on the different 1,800-row 6x4 + 6x8 protocol. Those scores are not directly comparable to the
  2,700-row three-size benchmark, and production has not yet been switched.

## 2026-07-23 - 3-Size Preview Predicted Pt Label Fix

- Fixed the canvas marker label in `app-3size-preview.js` by explicitly resetting `textAlign` and
  `textBaseline` inside `drawMarkerLabel`. The label had inherited the Y-axis tick alignment, which
  placed the purple `Predicted Pt` title and value to the left of their bordered box.
- Updated the preview script cache key and deployed the two frontend files to the WSL-hosted
  `imperialax-laminate.service`.
- Verified on `https://laminate.imperialax.com/preview/3size?lang=ko` using the Pt-Consistent Tree:
  both label lines render inside the purple box, the connector remains visible, and browser logs
  contain no errors. Local verification: `node --check` and 19 backend contract tests passed.

## 2026-07-23 - Production-UI 3-Size Preview Integration

- Replaced the isolated 3-size demo layout at `/preview/3size` with the existing production V2
  Laminate UI. The preview now keeps the complete result flow: Type probabilities, reliability,
  curve metrics, XAI, Research Insight, prediction history, report export, and RAG assistant.
- Preview mode remains isolated from production. It loads only the six 3-size comparison models
  from `/models/3size-preview` and predicts through `/predict/response/3size-preview`; the main
  `/` page still uses the existing canonical production registry.
- Pt-consistent preview models preserve the raw 128-point model curve and display two red P1 fit
  lines with their purple diamond intersection labeled `Predicted Pt`. The duplicate red Pt marker
  and purple vertical guide are omitted only for this fit mode.
- Added live local XAI fallback for all six 3-size models. Each explanation masks the 40 canonical
  angle, normalized CLT, Case, and panel-geometry features in the selected deployed model instead
  of borrowing an older global XAI report. Korean summary, method, notes, feature names, and feature
  set labels are localized in the existing UI.
- The preview reliability and Research Insight now use only the 900 simulations matching the
  selected panel size (6x4, 6x8, or 8x8). Production and u3 design-space contracts remain backward
  compatible.
- Added a compact validation banner for the locked protocol: 2,154 development rows / 718 design
  groups and 546 Holdout rows / 182 unseen groups. Both `/preview/3size` and the trailing-slash form
  resolve the production assets correctly and return `X-Robots-Tag: noindex, nofollow`.
- Verification: JavaScript and Python syntax clean, `git diff --check` clean, targeted backend tests
  `21 passed`, all six preview models returned HTTP 200 with 128 curve points and 40 local XAI
  features, WSL service active, and public browser QA at 8x8 completed with no console errors.
- Review URL: `https://laminate.imperialax.com/preview/3size?lang=ko`. Do not switch the main site
  until the user approves this preview.

## 2026-07-23 - 3-Size Preview Simplification And Language Parity

- Reduced the `/preview/3size` model selector to the three product-facing Pt-Consistent models:
  Tree, GointMLP, and Teacher-Student Hybrid. The original three-size models remain preserved as
  hidden benchmark artifacts and are not exposed by the preview API.
- Restored the compact hero description: Korean uses `Case와 theta 입력으로 적층 Type, Pt, 응답
  곡선을 예측합니다.` and English uses `Forecast laminate Type, Pt, and response curve from case
  and theta inputs.`
- Removed the development/Holdout count banner from the public preview UI. The validation protocol
  remains documented in project reports and session memory for research and review use.
- Added Korean display names for all three Pt-Consistent models and localized their result notes
  and XAI model references. Prediction history now stores a language-neutral model name and
  renders it in the active language, so switching between Korean and English no longer leaves the
  previous language in history cards.
- Verification: targeted backend contract tests `21 passed`, JavaScript/Python syntax checks and
  `git diff --check` passed, the public preview API returned exactly three available models, and
  browser QA confirmed both `?lang=ko` and `?lang=en` with no validation banner.
- The main production page remains unchanged pending explicit approval.

## 2026-07-23 - 3-Size Pt-Consistent Web Promotion

- Promoted the validated three-size Pt-Consistent model set to the main web Laminate Forecast at
  `https://laminate.imperialax.com/`: Tree, GointMLP, and Teacher-Student Hybrid.
- Kept the backend mobile model registry and the existing iOS/Android API contract unchanged. The
  web client now obtains only its Laminate response models from `/models/3size-preview` and sends
  those forecasts through `/predict/response/3size-preview`.
- Main-web response predictions therefore preserve the raw 128-point model curve and use the
  Pt-consistent P1 fit display. XAI uses the live local three-size explanation, while Research
  Insight requests the panel-matched three-size design space.
- Existing `u3 Forecast`, `Stack Lab`, and `Curve CSV` modes remain available. Previous canonical
  response-history cards are retained in browser storage but hidden from the promoted response
  history so unavailable legacy choices are not presented as current runs.
- Verified the public English and Korean pages. Both list exactly the three Pt-Consistent response
  models, preserve their respective translations, and keep the two existing u3 models. A live
  Case 2, theta 30/-30, 6x4 Tree prediction returned Type 2, Pt 17,190.1, visible XAI, P1 legend,
  and the 6x4-specific three-size design-space note without a UI error.
- Verification: JavaScript syntax clean, `git diff --check` clean, and targeted backend/mobile
  contract tests `22 passed`.

## 2026-07-24 - Reconfirmed 8x8 Curve Classification Lineage

- The `31-100` delivery was the previously missing 70 force-displacement CSV files for
  `data/New_data/8x8_Case3/csv`. Adding them completed Case 3 at 300 curves; Case 4 was already
  complete at 300 curves.
- Case 3 and Case 4 were then classified together with the established Curve CSV ExtraTrees model:
  Case 3 = Type 1/2/3 counts 43/175/82, Case 4 = 22/210/68.
- The last separate 300-file delivery was `data/New_data/8x8_Case2`. It was also fully classified:
  Type 1/2/3 counts 41/177/82.
- The combined 8x8 sorting manifest therefore contains 900 unique curves with no missing Test IDs:
  Type 1/2/3 totals 106/562/232. These Type values are model-assisted pseudo-labels produced from
  theta, Case, provided Pt, and force-displacement curve features, not human-confirmed labels.
- Canonical outputs remain at `data/New_data/classified_8x8_curve_csv_v1/classification_manifest.csv`
  and `reports/new_data_8x8_curve_type_classification.{csv,md}`. The 900 rows were later combined
  with 6x4 and 6x8 data to form the 2,700-row three-size dataset; the strict model protocol uses
  2,154 development rows and keeps 546 rows in the locked Holdout.

## 2026-07-24 - Predicted Pt Callout Moved Above The Curve

- Moved the purple `Predicted Pt` canvas callout out of the response-curve plotting rectangle and
  into a dedicated upper-left callout band. The data plot keeps its previous height; the canvas
  grows only by the added callout-band height.
- The callout remains fixed while zooming or panning. Its connector still points to the purple Pt
  diamond, or to the nearest plot boundary when the Pt is temporarily outside the zoomed viewport.
- Kept the existing u3 dual-marker layout unchanged; the new callout band applies only to the
  deployed Pt-consistent P1 fit mode.
- Deployed the updated `app-v2.js` to the WSL-hosted ImperialAX Laminate site. Public browser QA at
  100% and 182% zoom confirmed that the callout stays above the curve, remains inside its box, and
  produces no browser console errors.
- Verification: `node --check`, `git diff --check`, and the DD Laminate backend/web contract suite
  passed (`22 passed`).

## 2026-07-24 - Pt-Consistent First P1 Line Upper-Envelope Display

- Identified why the left red P1 line could begin below the green predicted curve: Pt-consistent
  models predict the raw curve, Pt displacement, and P1 slopes with separate heads. The two red
  lines meet exactly at predicted Pt, but small head-to-head differences can make the first slope
  slightly too steep near the origin.
- Added a shared display-only upper-envelope adjustment for the Pt-consistent Tree, GointMLP, and
  Teacher-Student Hybrid predictors. It preserves predicted Pt, the raw green curve, and the second
  P1 line, and only reduces the first P1 slope when required to keep it above the pre-Pt curve.
- The API preserves the model's original first line as `curve_fit.first_line_model` and records the
  applied method and slope ratio under `curve_fit.first_line_display_adjustment` for auditability.
- For the default Case 2, theta 30/-30, 6x4 input, the Tree display slope changed by about 10.4%,
  while predicted Pt remained 17,190.10 and the minimum pre-Pt line/curve gap became +112.48 kips.
  GointMLP and Hybrid also retained zero Pt-intersection gap and positive pre-Pt gaps.
- Deployed the shared predictor update to `laminate.imperialax.com` and restarted the WSL user
  service successfully. Public browser QA confirmed the left red line starts above the green curve,
  both P1 lines still meet at the purple Pt marker, and no browser errors were emitted.
- Verification: Python compilation, `git diff --check`, and targeted Pt-consistent plus DD web/API
  contract tests passed (`26 passed`).

## 2026-07-24 - Locked-Holdout Manual Smoke Samples

- Selected three reusable model/UI smoke inputs from the locked grouped Holdout, covering every
  panel geometry, Case 2/3/4, and Type 1/2/3:
  - `6x4_003`: Case 2, theta -44/65, panel 6x4, observed Type 1, Pt 15,283.10.
  - `6x8_216`: Case 3, theta -10/59, panel 6x8, pseudo-labeled Type 2, Pt 7,240.70.
  - `8x8_140`: Case 4, theta 1/-3, panel 8x8, pseudo-labeled Type 3, Pt 9,812.45.
- Current Pt-Consistent Tree predictions for those inputs were respectively Type 1 / 15,208.13,
  Type 2 / 7,084.15, and Type 3 / 5,840.35. The third sample is intentionally a difficult Pt case
  and is useful for detecting whether future model changes improve geometry generalization.
- `observed Pt` means the Pt derived from the stored simulation response. Only the 6x4 Type label is
  human-reviewed; the two newer geometry Type labels are curve-classifier pseudo-labels.

## 2026-08-11 - AIComp 2026 Relevance Review

- Reviewed the official AIComp 2026 agenda, speakers, workshops, and 99-page book of abstracts for
  directions applicable to the Double-Double Laminate project.
- The current project already aligns with the conference in forward surrogate modelling, CLT-based
  physics features, XAI, grouped Holdout validation, Teacher-Student modelling, Pt-consistent output,
  and composites-oriented RAG.
- The highest-priority gap is formal uncertainty quantification. The current UI reliability score blends
  model confidence, design-space distance, and local Type agreement, while its Pt band is explicitly a
  screening band rather than a calibrated statistical interval.
- Recommended immediate work: calibrated Type probabilities and Pt/Max. Force intervals, coverage
  and calibration metrics on the locked Holdout, subgroup analysis, and OOD/failure-case reporting.
- Recommended next work: an active-learning/Bayesian-optimization simulation planner that balances
  expected improvement, uncertainty reduction, design-space coverage, and feasibility.
- Recommended architectural research: encode the explicit ordered ply stack using a sequence model
  fused with CLT/ABD and panel-geometry branches. This is the most promising route for Case 5 and
  arbitrary custom stacking patterns beyond Case 2/3/4.
- RAG improvements suggested by the KPC-RAG presentation: retrieval similarity cutoff, evidence-aware
  abstention, source version/review metadata, and a reviewed DD QA benchmark measuring faithfulness
  and citation correctness.
- Full review saved at `docs/reviews/2026-08-11-aicomp-2026-dd-laminate-review.md`.

## 2026-08-11 - AIComp-Informed DD Upgrade Order

- Detailed implementation order was added to the AIComp review. The main dependency chain is:
  freeze reproducible baseline -> formal calibration and intervals -> separate OOD/coverage signals ->
  offline active-learning replay -> researcher-approved simulation loop -> explicit ply-sequence model ->
  constrained inverse design -> broader physics/geometry conditions -> RAG benchmark -> staged rollout.
- The 546-row locked Holdout must not be used for calibration or tuning. Calibration choices are made
  only inside grouped development folds and then evaluated once on the locked Holdout.
- The first implementation target is calibrated Type probability plus 80/90/95% Pt and Max. Force
  intervals. The current Reliability card remains a screening indicator until empirical coverage is
  available.
- Active learning must first be validated retrospectively against random selection using existing rows.
  Its first operational output is an approval-ready next-simulation CSV, not automatic solver execution.
- The ply-sequence model must be evaluated on unseen pattern families. Case 5 claims require at least a
  small independent Case 5 simulation set even if Case 2/3/4 are used for pretraining.

## 2026-08-11 - DD Model Baseline Freeze and Research Branch

- The current DD production reference was frozen as
  `dd-3size-pt-consistent-v1-20260811` in
  `research/dd_aicomp2026/baselines/dd_3size_pt_consistent_v1.json`.
- The baseline contains the 2,700-row 6x4/6x8/8x8 dataset, the grouped 2,154-row development and
  546-row Holdout protocol, and the deployed Pt-Consistent Tree, GointMLP, and Teacher-Student Hybrid
  artifacts with SHA-256 hashes and comparable metrics.
- Future AIComp-inspired work is isolated on Git branch `codex/dd-aicomp2026-uq` and model namespace
  `models/dd_laminate_aicomp2026_v1/<experiment-id>/`.
- New runs must never overwrite frozen model paths. Each run receives an immutable experiment ID with
  matching config, model, and report directories.
- The first challenger will add calibrated Type probabilities and conformal Pt/Max. Force intervals
  using only the development partition for calibration; the locked Holdout remains the final gate.
- Baseline integrity can be checked with `python scripts/dd_verify_model_baseline.py`.
