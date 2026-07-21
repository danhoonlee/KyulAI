# Worktree Cleanup Snapshot - 2026-07-15

This note classifies the current uncommitted work so the next commit, bundle,
or handoff can be done without mixing unrelated changes by accident.

## Cleanup Actions Already Done

- Added `.gitignore` rules for local runtime state:
  - `runtime/`
  - `**/*.xcodeproj/project.xcworkspace/`
- No user data, model artifact, source file, or generated product asset was
  deleted.
- Local-only files now hidden from `git status`:
  - server/cloudflared logs
  - wedding runtime submissions/admin token
  - Xcode user workspace state

## Keep As Functional Changes

These files represent product or code behavior and should be kept unless the
feature is intentionally rolled back.

- Laminate Forecast Distillation v1
  - `scripts/dd_response_distillation_train.py`
  - `models/dd_laminate_response_distilled_v1/`
  - `reports/dd_response_xai_distilled_v1/`
  - `src/backend/api/v1/dd_laminate.py`
  - `src/backend/api/v1/optimization.py`
  - `src/frontend/dd-laminate/app-v2.js`
  - `src/frontend/dd-laminate/app.js`
  - iOS/Android model label/key updates
- Existing Laminate EXE/login packaging
  - `src/frontend/dd-laminate/auth-gate.js`
  - `scripts/windows/exe/`
  - `docs/LAMINATE_EXISTING_EXE_PACKAGE.md`
  - `src/backend/dd_laminate_app.py`
  - `src/backend/api/v1/modules.py`
- Laminate RAG / TAC-vs-DD basis
  - `data/PPT/TAC vs DD.pptx`
  - `docs/DD_Laminate_TAC_vs_DD_PPT_Basis.md`
  - `data/rag/knowledge_index.json`
  - `src/data/rag/answer.py`
  - `tests/unit/test_rag_answer.py`
- ABD-normalized active models and XAI
  - `models/dd_laminate_response_physics_abd_v1/`
  - `models/dd_laminate_response_goint_physics_nn_abd_v1/`
  - `models/dd_laminate_u3_forecast_physics_abd_v1/`
  - `reports/dd_response_xai_physics_abd_v1/`
  - `reports/dd_response_xai_goint_physics_nn_abd_v1/`
  - `reports/dd_u3_xai_physics_abd_v1/`
  - `reports/dd_u3_xai_goint_physics_abd_v1/`
  - `src/ml/dd_laminate/laminate_physics.py`
- Product page / marketing assets
  - `docs/C2ES_Laminate_Product_Page_*`
  - `docs/product-assets/`
- ImperialAX branding assets
  - `icons/imperialAX/`
  - `icons/reference_logos/`
- Wedding frontend/runtime-adjacent feature
  - `src/frontend/wedding/`
  - Do not include `runtime/wedding/`; that is local runtime state.

## Large Artifacts To Confirm Before Commit

These are probably required for a portable handoff, but they are large enough
that they should be committed or bundled intentionally.

- `models/dd_laminate_response_physics_abd_v1/` - about 453 MB
- `models/dd_laminate_u3_forecast_physics_abd_v1/` - about 324 MB
- `icons/imperialAX/` - about 66 MB

## Recommended Commit Groups

1. Runtime hygiene
   - `.gitignore`
2. Laminate ABD + Distillation model stack
   - backend/frontend/app model registry updates
   - ABD model folders and XAI reports
   - Distillation v1 script/model/report
   - `scripts/package_windows_bundle.py`
3. Laminate EXE auth packaging
   - auth gate frontend
   - backend auth env switches
   - Windows EXE scripts and docs
4. RAG and TAC-vs-DD knowledge update
   - PPT, RAG index, answer code, tests, docs
5. Web/app UI parity changes
   - Laminate and Injection frontend/app UI files
6. Product page / branding assets
   - C2ES product HTML/source/assets
   - ImperialAX icons/reference assets
7. Cloudflare/server config updates
   - infrastructure files

## Fallback / Slop Review

- `except Exception` and frontend `catch` blocks exist in API/model loading and
  browser UI paths.
- Current classification:
  - model loading, optional XAI, and browser fetch catches are grounded
    compatibility/fail-safe fallbacks because they preserve API/UI availability
    when optional artifacts or network calls fail.
  - no masking fallback was removed in this cleanup pass because changing those
    paths could alter runtime behavior without a dedicated test pass.

## Verification Targets

- Python compile:
  - `src/backend/api/v1/dd_laminate.py`
  - `src/backend/api/v1/optimization.py`
  - `src/backend/dd_laminate_app.py`
  - `scripts/dd_response_distillation_train.py`
- Web syntax:
  - `src/frontend/dd-laminate/app-v2.js`
  - `src/frontend/dd-laminate/app.js`
  - `src/frontend/simple-injection/app-v2.js`
- API smoke:
  - `/api/v1/dd-laminate/models`
  - `/api/v1/dd-laminate/predict/response`
  - `/api/v1/dd-laminate/xai/local`
- RAG tests:
  - `tests/unit/test_rag_answer.py`

## Verification Run - 2026-07-15

- PASS: Python compile for backend, optimization, app launcher, distillation
  training script, and Windows EXE launcher scripts.
- PASS: JavaScript syntax checks for Laminate v2, Laminate legacy,
  Laminate auth gate, and Simple Injection v2.
- PASS: RAG unit tests:
  `14 passed in 0.06s`.
- PASS: Laminate API smoke with FastAPI TestClient:
  - `/api/v1/dd-laminate/models` returned Machine Learning, Deep Learning,
    and Distilled NN.
  - `/predict/response` returned 200 for all three Laminate Forecast models.
  - `/xai/local` returned 200 for all three Laminate Forecast models.
- PASS: iOS Swift package tests in `ios/DDLaminateMVP`:
  `11 tests, 0 failures`.
- BLOCKED: Android `gradle -p android/LuveloxMVP :app:assembleDebug`
  did not reach Kotlin/Java compilation because this Mac has no Java 17
  toolchain configured:
  `Cannot find a Java installation ... matching languageVersion=17`.
  Re-run on a machine with JDK 17 or configure Gradle toolchain download
  repositories.
