# ImperialAX Codebase Audit

Date: 2026-07-22
Branch: `codex/dd-laminate-ui-api`
Scope: backend, Laminate/Injection models and APIs, web, iOS, Android, CI, Windows serving scripts

## Executive Summary

The current product-serving path is operational: the unified API loads the core Laminate and
Injection models, the Python test suite passes, and the web/iOS/Android clients compile. This pass
also removed several unsafe development fallbacks and restored static-analysis enforcement.

The repository is not yet production-complete. The most important remaining work is to define one
consistent authentication boundary for every API and client. Application composition, secure mobile
token storage, and removal or migration of old internal `KyulAI` identifiers should follow after that.

## Changes Completed in This Pass

### Security and public serving

- Removed the broad `/data` static mount that could expose runtime files such as the authentication
  SQLite database. Only the two required Simple Injection public datasets remain mounted.
- Removed fixed `demo-token` and `danlee-token` client/server fallbacks. Demo sessions now use the
  regular random session-token path.
- Made demo login, public signup, self-service password reset, and client-supplied entitlement
  overrides default-closed. They require explicit `IMPERIALAX_ENABLE_*` environment flags.
- Removed the implicit admin email default. Admin accounts now require `IMPERIALAX_ADMIN_EMAILS`.
- Added shared multipart upload limits:
  - Per CSV: 16 MiB by default (`IMPERIALAX_MAX_CSV_UPLOAD_BYTES`).
  - Cumulative batch: 256 MiB by default (`IMPERIALAX_MAX_CSV_BATCH_BYTES`).
  - Oversized uploads return HTTP 413 before parsing or model inference.
- Confirmed `.env.local` is ignored and not tracked. It currently contains an OpenAI API key; rotate
  that key because it was visible during local review, even though it is not in Git.

### Model and API correctness

- Added one canonical `is_deep_response_model()` registry and reused it from response prediction and
  optimization. This prevents a PyTorch model from being routed through the joblib loader.
- Added regression coverage for every response-model key and the intended optimal model lists.
- Kept the verified geometry-aware deployment defaults: Geometry Tree for the main forecast,
  Geometry GointMLP for DL comparison, and Hybrid Student as a challenger/agreement check.
- Removed the duplicate public `create_dataloaders` definition by retaining the sample helper under
  the explicit `create_sample_dataloaders` name.

### Type safety and maintenance

- Reduced `mypy src` from roughly 350 errors across 32 files to zero.
- Brought Ruff lint and Ruff formatting to a clean state across `src` and `tests`.
- Replaced the nonstandard editable-install backend with `setuptools.build_meta`; `pip install -e .`
  now works in the Python 3.11 environment.
- Fixed SQLAlchemy collection return types, queue-training annotations, NumPy scalar conversions,
  Pydantic namespace warnings, RAG typing, and shared training/evaluation typing.
- CI now enforces mypy instead of allowing it to fail, installs the serving dependencies and CPU
  PyTorch needed by the actual tests, and uses Python 3.11 consistently.
- Added missing Gradle 8.9 wrappers to all three Android projects so a new machine can run builds
  without a separately installed Gradle executable.

## Fresh Verification Evidence

| Surface | Result |
|---|---|
| Python non-slow/non-GPU suite | 211 passed after upload-limit and 301-file batch tests were added |
| Targeted security/model/upload regressions | 41 passed before final full run |
| mypy | 0 errors |
| Ruff lint | passed |
| Ruff format | 190 files formatted after final additions |
| JavaScript syntax | all non-vendor frontend JavaScript passed `node --check` |
| iOS DD Laminate package | 11 tests passed |
| iOS Injection package | 8 tests passed |
| iOS ImperialAX package | 6 tests passed after cleaning a stale Swift module cache |
| Android DD Laminate | Gradle test/compile passed |
| Android Injection | Gradle test/compile passed |
| Android ImperialAX | Gradle test/compile passed |
| Unified API smoke | `/health` OK; `/ready` loaded all 5 core DD/u3 and 6 Injection artifacts |

The two remaining Python warnings are SciPy precision-loss warnings in synthetic tests whose values
are nearly identical. They do not currently fail a test, but the statistical fixtures should be made
less degenerate when that validation module is revisited.

## Remaining Findings

### P1: Authentication is not one enforceable system boundary

The unified app mounts Laminate and Injection prediction routers directly and only has redirect/CORS
middleware (`src/backend/imperialax_app.py`). The standalone Laminate app protects its API only when
`LAMINATE_REQUIRE_AUTH` is enabled (`src/backend/dd_laminate_app.py:241`), while the standalone
Injection app has no equivalent authentication middleware (`src/backend/simple_injection_app.py:46`).

The native clients also pass a session token in an admin web URL query string
(`ios/ImperialAXMVP/Sources/ImperialAXApp/ContentView.swift:966` and
`android/ImperialAXMVP/app/src/main/java/com/imperialax/app/MainActivity.kt:437`). Query tokens can
leak through browser history, logs, screenshots, and referrer headers. iOS persists the session in
`UserDefaults` and Android uses plain `SharedPreferences` rather than Keychain/Keystore-backed storage.

Recommended repair:

1. Put bearer-token/entitlement middleware or dependencies on every protected API router.
2. Replace query-token handoff with a short-lived one-time exchange that creates a Secure, HttpOnly,
   SameSite cookie scoped to the intended ImperialAX domain.
3. Store native refresh/session credentials in iOS Keychain and Android encrypted storage.
4. Add explicit public-route and protected-route policy tests before enabling production auth.

### P2: Application composition has four competing roots

`imperialax_app.py`, `dd_laminate_app.py`, `simple_injection_app.py`, and `main.py` mount different
router, middleware, static-file, RAG, and operational combinations. A feature can therefore work on
one hostname and silently be absent on another. Adopt the unified app as the only production
composition root, with standalone apps retained strictly as documented development entry points.

### P2: Laminate serving still owns an unrelated wedding application

`dd_laminate_app.py` contains wedding hosts, file storage, RSVP/guestbook/admin APIs, and static routes
starting around line 443. This widens the Laminate server's security and regression surface. Extract
the wedding application into its own module and process before the Laminate service is treated as a
stable production boundary.

### P2: Optimization is not geometry-aware yet

`src/backend/api/v1/optimization.py:254` forces every candidate to a 6 x 4 inch panel even though the
forecast API accepts panel dimensions. Either expose geometry in the optimization request or clearly
label optimization as 6 x 4 only. Silent fixed geometry can make otherwise valid recommendations
misleading for 6 x 8 and future panel sizes.

### P2: Generic platform APIs contain intentional scaffolds

The database-oriented training and dataset APIs return HTTP 501 and worker tasks raise
`NotImplementedError` (`src/backend/api/v1/models.py:81`, `src/backend/api/v1/data.py:130`, and
`src/backend/workers/tasks.py:61`). These are not on the current forecast-serving path, but they should
be hidden from production OpenAPI or implemented before being presented as usable platform features.

### P2: The ImperialAX rename is incomplete internally

There are still about 92 active files containing `KyulAI`, `kyulai`, or older compatibility names.
Examples include the Python package name, backend exception names, Celery queues, Windows task names,
remote GPU scripts, Slack command text, and Swift package products. Most public UI branding is already
ImperialAX, but an internal rename now requires a deliberate migration plan for environment variables,
queue names, bundle/module imports, stored task definitions, and deployment scripts.

### P3: Platform test depth is uneven

Android compilation succeeds, but the Android modules currently contain no meaningful JVM/UI test
suite. Full slow/GPU model training and validation were not rerun on this Mac. Those checks should run
on the RTX/WSL worker and publish artifacts to a reproducible model-validation report.

## Worktree and Preservation Notes

- This was intentionally not committed. The branch already contains a broad pre-existing worktree,
  and the cleanup includes many mechanical format/type changes.
- Existing untracked research inputs and reports were preserved without modification:
  `data/New_data/8x8_Case3/`, `data/New_data/8x8_Case4/`, and
  `reports/dd_response_geometry_fixed_holdout_smoke/`.
- Existing running public/local servers were not stopped. Verification used separate test/build
  processes and a temporary unified API smoke process.

## Recommended Next Sequence

1. Implement the unified authentication boundary and secure token handoff/storage.
2. Make optimization geometry-aware and add fixed-holdout tests for 6 x 4 versus 6 x 8 search results.
3. Split wedding and standalone development apps from the production composition root.
4. Decide and execute the internal ImperialAX naming migration with compatibility aliases.
5. Add Android UI/contract tests and run slow/GPU validation in WSL/RTX CI.
6. Only then create a reviewed snapshot commit; separate security/correctness changes from broad
   formatter-only changes where practical.
