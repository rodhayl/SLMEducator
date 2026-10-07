# Test database isolation verification

Date: 2026-10-07

## Result

The reviewed synthetic test paths no longer create or reset root-relative databases. Collection, individual pytest cases, cache singleton tests and standalone feature runners all use disposable database paths. Existing database files and sidecars are refused rather than reset. No application code was changed.

Focused verification: **40 passed in 19.12 seconds**. Critical Ruff checks and Python compilation passed for all ten changed Python files. This result is a focused test-isolation gate, not a full-suite, browser or native Windows acceptance result.

## Findings and repairs

### Default AI cache database

The two global-instance tests in `tests/ai/test_ai_cache_service.py` called `get_cache_service()` without a URL. `src/core/services/ai_cache_service.py` defaults to `sqlite:///slm_educator.db` independently of `SLM_DB_PATH`. This is a direct path for a test to create the checkout-root database. The observed existing database was not opened, deleted or reset during this investigation.

Both tests now supply explicit `tmp_path` SQLite URLs. Their fixture isolates the singleton, closes the test instance and restores any previous instance. Singleton identity and custom TTL assertions remain.

A static search found no application, script or installer caller of this cache outside its defining module. It is therefore a candidate for the final dead-code audit, not a demonstrated runtime-path bug or an approved deletion target. Dynamic/reflection imports, documented or external callers, exports, packaging and configuration references still need checking before any removal decision.

### Collection and teardown

`tests/conftest.py` formerly installed the database path only in a function fixture and deleted it during teardown. Collection-time imports and between-test work could consequently use the default path.

`pytest_configure` now creates a unique temporary collection directory and installs DB/log defaults before test-module collection. Pytest cleanup restores the incoming environment and removes only that owned directory. Function fixtures still create a distinct database for each test. They use the shared `monkeypatch` fixture so later test-specific overrides unwind correctly and restore the collection-safe fallback.

The nested pytest regression exercises both collect-only and full execution, initially present and absent environment variables, distinct per-test paths, an extra test-specific override, between-test fallback, final environment restoration and owned-directory cleanup. Synthetic caller-owned sentinels remain unchanged.

### Standalone feature runners

The following files formerly used root-relative database names and pre-run deletion:

- `tests/core/test_content_ordering.py`
- `tests/features/test_comprehensive.py`
- `tests/features/test_workflows.py`
- `tests/features/test_phases_1_2.py`
- `tests/features/test_phase3_4.py`

Content-ordering now receives `tmp_path`. The four standalone runner classes require an explicit absolute database path; their direct command-line entry points allocate a `TemporaryDirectory`. Their cleanup closes database handles and leaves file removal to the temporary-directory owner. No global working-directory change is used by these runners.

`tests/fixtures/synthetic_database.py` implements create-only construction. It refuses an existing database or `-wal`, `-shm` or `-journal` sidecar, including a dangling destination symlink.

Executing the previously uncollected workflow helper exposed three stale test API assumptions. The helper now uses the existing `hash_password` function, verifies the boolean update receipt and reads back the changed plan, and checks the assignment's actual composite identity. Existing workflow assertions remain. The standalone wrapper now reports a nonzero exit status on failure instead of swallowing it.

## Verification

Run from a prepared test environment, using a fresh disposable base directory:

```sh
SLM_OFFLINE_TESTS=1 USE_REAL_AI=0 python -m pytest   tests/core/test_content_ordering.py   tests/trust/test_feature_database_isolation.py   tests/trust/test_pytest_database_isolation.py   tests/ai/test_ai_cache_service.py   -q --basetemp=/tmp/slm-test-isolation-final-20261007
```

Final result: **40 passed in 19.12 seconds**.

The focused set covers original ordering behavior, all four feature runner behaviors, all five direct script entry points, existing-file/sidecar refusal, absolute-path rejection, collection/per-test/teardown lifecycle and cache singleton isolation. The direct entry-point checks run in disposable working directories, preserve synthetic preexisting filenames and confirm their owned temporary directories are cleaned.

Critical Ruff selection `E9,F63,F7,F82` and `py_compile` passed on every file below. Full final audits must use these final files; an already-running pytest process retains fixtures loaded before changes.

## Changed Python files

- `tests/conftest.py`
- `tests/ai/test_ai_cache_service.py`
- `tests/trust/test_pytest_database_isolation.py`
- `tests/core/test_content_ordering.py`
- `tests/features/test_comprehensive.py`
- `tests/features/test_workflows.py`
- `tests/features/test_phases_1_2.py`
- `tests/features/test_phase3_4.py`
- `tests/fixtures/synthetic_database.py`
- `tests/trust/test_feature_database_isolation.py`

## Boundaries

No preexisting checkout database contents or private runtime configuration were inspected. No preexisting checkout database was deleted or reset. Tests used synthetic configuration and synthetic data; no provider or model calls were made. Native Windows filesystem, packaged application and browser acceptance remain separate gates.
