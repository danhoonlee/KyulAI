# Pre-Commit Snapshot - 2026-06-29

This snapshot records the current stabilization pass before committing the
combined DD Laminate, Injection, ImperialAX shell, Android, and RAG changes.

## Stabilized Scope

- DD Laminate web/API/iOS contract tests
- Injection web/API/iOS/Android surfaces
- ImperialAX workspace/login static routing
- Composite RAG unit and API behavior
- Android debug build environment

## Cleanup Fixes Applied

- Removed an invalid Android login-card click handler in
  `android/ImperialAXMVP/app/src/main/java/com/luvelox/app/MainActivity.kt`.
  The handler referenced a `module` value outside its scope and broke
  Kotlin compilation.
- Updated ImperialAX web fallback account copy from `ImperialAX Demo` to
  `Demo Account` in the login/workspace shell.
- Updated stale backend contract tests so they match the current product
  direction:
  root pages expose the current Forecast entry instead of the old Classic UI,
  and the shell expects `Demo Account`.
- Kept grounded fail-safe fallbacks in place:
  local browser/app history failures remain non-blocking, Android offline
  module fallback remains explicit, and RAG has a tested local fallback answer.

## Verified Commands

```bash
node --check src/frontend/dd-laminate/app-v2.js
node --check src/frontend/simple-injection/app-v2.js
node --check src/frontend/luvelox/app.js
node --check src/frontend/luvelox/login-v2.js
node --check src/frontend/luvelox/admin.js

python -m pytest \
  tests/backend/test_dd_laminate_ios_contract.py \
  tests/backend/test_luvelox_modules.py \
  tests/backend/test_rag_api.py \
  tests/unit/test_rag_answer.py \
  tests/unit/test_rag_knowledge_index.py \
  tests/unit/test_rag_online_collection.py

swift test # in ios/DDLaminateMVP
swift test # in ios/InjectionMVP
swift test # in ios/ImperialAXMVP

JAVA_HOME=/opt/homebrew/opt/openjdk@17 \
PATH="/opt/homebrew/opt/openjdk@17/bin:$PATH" \
gradle :app:assembleDebug --no-daemon # in android/ImperialAXMVP

git diff --check
```

## Verification Result

- Python backend/RAG tests: 71 passed
- DD Laminate Swift tests: 11 passed
- Injection Swift tests: 8 passed
- ImperialAX Swift tests: 6 passed
- Android debug build: successful
- JS syntax checks: passed
- Whitespace check: passed

## Environment Notes

- This local Python is 3.10.20, while `pyproject.toml` declares Python 3.11+.
  The tests above pass in the current local environment after installing
  `requirements-serving.txt`, but the Windows/server setup should use Python
  3.11 as planned.
- `requirements-serving.txt` pins `pydantic==2.6.4`, which can conflict with
  unrelated local packages that expect newer Pydantic. Prefer a project venv
  instead of installing into a shared base environment.
- Android requires JDK 17. On this Mac, Homebrew OpenJDK 17 exists but is not
  registered with `/usr/libexec/java_home`, so the build command sets
  `JAVA_HOME=/opt/homebrew/opt/openjdk@17` explicitly.
- Gradle reports deprecation warnings for future Gradle 10 compatibility, but
  the current debug build succeeds.
