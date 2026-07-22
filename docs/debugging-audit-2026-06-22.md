# Debugging Audit - 2026-06-22

## Scope

Broad pass over the current DD Laminate, u3 Forecast, ImperialAX, Simple Injection,
iOS, Android, and serving surfaces without reverting existing worktree changes.

## Fixes Applied

- Installed/normalized local dev checks:
  - `pytest-asyncio` so `asyncio_mode = "auto"` is recognized by pytest
  - `mypy==1.9.0`, matching the repo pre-commit mirror version
- Made mypy invocation explicit-package based to avoid duplicate `src.*` module
  discovery:
  - `pyproject.toml`
  - `Makefile`
- Replaced deprecated DD standalone FastAPI startup event with lifespan startup:
  - `src/backend/dd_laminate_app.py`
- Hardened DD/ImperialAX standalone host parsing against missing `Host` headers:
  - `src/backend/dd_laminate_app.py`
  - `src/backend/luvelox_app.py`
- Tightened type boundaries in current operational API/model paths:
  - DD Laminate/u3 API response assembly
  - u3 forecast model bundle/checkpoint loading
  - DD classical/u3 forecast training report metric dictionaries
  - Simple Injection DOE/filling-pressure response conversion
  - Laminate optimization default factories
- Hardened DD/u3 prediction code:
  - strict probability and curve-point zipping
  - empty-curve guard for the deep Laminate Forecast smoother
  - strict physics feature-name/value alignment
  - removed unused physics and Pt-consistency variables
- Protected local-only/generated files from accidental commits:
  - `data/luvelox_auth.sqlite3`
  - `data/luvelox_auth.sqlite3-*`
  - Office lock files matching `~$*`

## Verification

- Python tests:
  - `.venv/bin/python -m pytest tests -q`
  - Result: 170 passed
- Python compile:
  - `.venv/bin/python -m compileall -q src scripts tests`
  - Result: passed
- Targeted lint on changed Python files:
  - `ruff check src/backend/api/v1/dd_laminate.py src/backend/api/v1/simple_injection.py src/backend/api/v1/optimization.py src/ml/dd_laminate/predict_curve_classifier.py src/ml/dd_laminate/train_cases_2_3_4_classical.py src/ml/dd_laminate/train_u3_forecast_models.py src/ml/dd_laminate/train_u3_pt_models.py src/ml/simple_injection/data.py`
  - Result: passed
- Targeted type check on operational DD/ImperialAX/Simple Injection serving chain:
  - `mypy --explicit-package-bases` over DD app, ImperialAX app, DD API,
    Simple Injection API, optimization API, DD/u3 model helpers, and Simple
    Injection data loader
  - Result: passed
- Frontend JavaScript syntax:
  - DD, ImperialAX, and Simple Injection app files
  - Result: passed
- Backend/API smoke:
  - DD `/health`
  - Laminate Forecast response prediction
  - u3 Forecast ML prediction
  - u3 Forecast DL prediction
  - ImperialAX `/health`
  - ImperialAX modules endpoint
  - Result: all HTTP 200
- iOS SwiftPM:
  - `ios/DDLaminateMVP`: 11 tests passed
  - `ios/ImperialAXMVP`: 4 tests passed
- Android Gradle:
  - Initial build failed because macOS Java discovery could not find JDK 17.
  - Builds passed with:
    - `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home`
  - `android/ImperialAXMVP`: passed
  - `android/DDLaminateMVP`: passed
  - `android/InjectionMVP`: passed

## Remaining Risks

- Full-repo mypy still reports legacy type debt:
  - latest run: 332 errors across 26 files
  - major buckets: core `data/schemas/tool_mappings/*` missing `FieldMapping`
    defaults, older Pydantic default-factory typing, generic training/evaluation
    tensor/list typing, and old experiment/dataset service annotations.
  - The current DD/ImperialAX/Simple Injection serving chain checked in this audit
    passes targeted mypy.
- `pip check` still reports an environment dependency conflict:
  - `nlopt 2.10.0` requires `numpy>=2,<3`
  - current ML environment uses `numpy 1.26.4`
  - `nlopt` appears to be pulled in transitively, likely through CAD tooling; do
    not upgrade numpy casually because the trained sklearn/scipy/model stack was
    validated on the current numpy line.
- The active local `.venv` is Python 3.10.20 while `pyproject.toml` declares
  `requires-python = ">=3.11"`. Tests pass in this venv, but fresh Windows/server
  setup should use Python 3.11+ to match the project contract.
- Full-repo ruff may still be noisy outside the targeted files. This audit added
  narrow per-file ignores only where the warning reflected intentional FastAPI,
  Pydantic API-field, PyTorch, or UI math-symbol conventions.
- Android builds require JDK 17 to be discoverable. On macOS this currently needs
  `JAVA_HOME` unless OpenJDK is linked into the system Java discovery path.
- The worktree contains many existing modified and untracked files from earlier
  DD/injection/app work. This audit did not revert or normalize those changes.

## Recommended Follow-Up

- Add a lightweight `scripts/check_all.sh` or Make target that runs the exact
  passing checks from this audit.
- Tackle full-repo mypy in separate batches:
  1. `data/schemas` / `tool_mappings`
  2. generic training/evaluation framework
  3. experiment/dataset service annotations
  4. remaining research scripts
- Add Windows and macOS Java/JDK setup notes to the serving docs before relying
  on Android artifact generation on a fresh machine.
