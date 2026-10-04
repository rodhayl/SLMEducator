# Create-only administrator bootstrap

Historical bootstrap-only validation. The subsequent packaging repair is
documented in [PACKAGING_SAFETY_REPORT.md](PACKAGING_SAFETY_REPORT.md).

Validated on 4 October 2026 against base
`20776835356856953e07a2777cce7b10059e977a`.
Code and test candidate: `06d0c26` (following `1bd3911`).

## Scope

- `scripts/seed_admin.py`: an existing username `admin` returns before resolving
  bootstrap credentials. No password, email, role, activity, lockout or
  authentication-attempt state is changed.
- `start.bat`: removes the shared bootstrap password. A new account still accepts
  an explicit initial password or receives a one-time generated password.
- `README.md`: documents create-only provisioning, removes implicit reset
  instructions and preserves the unresolved packaging warnings.
- `tests/test_seed_admin.py`: adds 27 regression cases using disposable real
  SQLite databases and one consistent ORM namespace. Snapshot connections close
  explicitly, including on failure.

## Evidence

Environment: Linux, Python 3.12.14, isolated virtual environment installed from
the existing requirements. All account data and credentials used were synthetic.
No deployed application or external AI provider was used.

- Final affected regression run: **27 passed**, with `ResourceWarning` promoted
  to an error. No warnings were reported.
- Seeder statement coverage: **100%**, using the repository coverage
  configuration. This is coverage of this script, not the whole application.
- The preceding combined run passed **56 tests**: the 27 new regressions plus
  29 authentication, database and authentication-API tests. Its one warning was
  a third-party Starlette/AnyIO deprecation. The only subsequent test-code change
  explicitly closes snapshot connections; application code did not change.
- Before the handle-cleanup change, the new regression file was also run against
  an isolated archive of the exact base: **23 failed, 4 passed**, confirming that
  it detects the original bootstrap behavior.
- Black, Flake8, targeted Mypy, dependency consistency and `git diff --check`
  passed. Mypy uses explicit package bases to avoid interpreting the script under
  two module names.

Preservation tests compare every persisted column in `users` and
`auth_attempts`, including nondefault settings and relationships, all three
roles, disabled/locked accounts and linked/unlinked login attempts. They cover
missing, blank, short, valid and changed password overrides and repeated calls.
Password helpers and write commits are forbidden on the existing-account path.
Fresh-account tests cover validation boundaries, rollback, one-time generation
and secret-output behavior.

Reproduce the final focused check in an isolated test environment:

```text
python -m pytest tests/test_seed_admin.py -q --tb=short -W error::ResourceWarning --cov=scripts.seed_admin --cov-report=term-missing
```

The affected integration set is:

```text
tests/core/test_auth.py
tests/core/test_database.py
tests/integration/test_auth_pages.py
tests/integration/test_auth_role_contract.py
```

## Limits and remaining work

The full repository suite was not run. Real-AI, manual and browser suites are
outside this bounded repair. Native Windows launcher execution was not verified;
the launcher regression is a static contract check.

`build_package.bat` is unchanged. Its production mode still deletes the root
database and WAL/SHM files, and it still supplies a shared default password when
an override is absent. Do not run that mode against valuable data or distribute
its output before a separate packaging-safety repair and isolated acceptance.

This change does not recover lost access, reset existing credentials, certify
packaging safety or establish production readiness.
