# Isolated Windows packaging safety

Validated on 4 October 2026 on top of the create-only bootstrap candidate
`00b925fbbfd303a7f6c239c979a381d1a8c521f1`; original upstream base remains
`20776835356856953e07a2777cce7b10059e977a`.

## Changes

- `build_package.bat` delegates to a Python builder from the checkout directory.
  It no longer kills app processes, removes build/install directories, assigns a
  shared password, deletes SQLite files or copies the working configuration.
- `scripts/build_package.py` builds in disposable staging with isolated work,
  spec, cache, database, configuration and home-key paths. It reuses runtime
  defaults and the existing create-only admin seeder. A seeding failure aborts.
- Production packages get a fresh seeded database. Missing password overrides
  retain the seeder's random one-time credential behavior; explicit valid
  overrides remain supported. Credentials are not written to a plaintext file.
- Test packages require `--test --database PATH`. SQLite's online backup API
  includes committed WAL records and produces a checked standalone database.
  Test snapshots do not seed, reset or promote accounts. SQLite itself may
  manage source WAL/SHM metadata while taking the explicit read-only snapshot.
- Existing output directories are refused. The builder writes only a new output
  directory and removes its own partial copy on failure. It never stops a
  running application to replace files.
- Runtime/configuration backups, logs, temporary files and key files are excluded
  from resource inputs. Symlinks and Windows reparse points are rejected for
  resource inputs, including the seeder and migration-config file inputs.
- Both frozen launchers anchor relative runtime paths beside the executable
  before application imports. This makes the staged admin database available
  when the package is launched from another working directory. Explicit runtime
  path overrides remain supported; source launch behavior is unchanged.
- `README.md` documents new CLI semantics, per-installation credentials,
  configuration, writable locations, data sensitivity and validation limits.
  `AGENTS.md` records the stable data-safety and focused-testing rules.

## Evidence

Environment: Linux, Python 3.12.14, existing isolated project virtual environment.
Only disposable synthetic data and credentials were used. PyInstaller was
simulated; configuration generation and seeding were real subprocesses, and
snapshot tests used real SQLite with a live WAL writer and an uncommitted row.

Final bounded regression run: **82 passed**, with `ResourceWarning` treated as an
error. It contains 26 packaging tests, 27 create-only bootstrap tests and 29
existing authentication/database/API tests. One existing Starlette/AnyIO
`DeprecationWarning` remains. The initial aggregate attempt lacked a synthetic
JWT environment value and hit the test host's read-only home directory; the
final run supplied the synthetic value explicitly and passed without source
changes for that environment issue.

Packaging checks cover:

- byte-identical production preservation of working SQLite, WAL and SHM files,
  including live-writer state and non-SQLite sentinels that must never be opened;
- clean configuration and private-home-key isolation despite inherited path
  overrides, plus explicit backup/log/key exclusion fixtures;
- separate builds producing different usable random admin passwords, explicit
  password use without plaintext output/bundling, and invalid-password failure;
- committed-WAL inclusion, uncommitted-row exclusion, standalone snapshot
  integrity, missing-source failure and no test-mode seeding;
- existing-output refusal, failed-freezer cleanup, explicit mode validation,
  symlink rejection and source-versus-frozen working-directory behavior.

Independent review reproduced and closed two input-boundary findings (backup/log
inclusion and unchecked file-input symlinks). Additional synthetic checks covered
publication-copy failure cleanup, nested symlinks and a simulated Windows
reparse-point attribute. No blocking finding remained in that reviewed scope.

`build_package.py` statement coverage is **81%**. This does not measure a native
freezer or full application. Black, Flake8, focused Mypy, dependency consistency
(70 compatible installed packages) and `git diff --check` passed. No dependency
was added.

Reproduce the bounded test set from a disposable checkout (set a synthetic
`JWT_SECRET` in the test process environment first):

```text
python -m pytest tests/test_build_package.py tests/test_seed_admin.py tests/core/test_auth.py tests/core/test_database.py tests/integration/test_auth_pages.py tests/integration/test_auth_role_contract.py -q --tb=short -W error::ResourceWarning --cov=scripts.build_package --cov-report=term-missing
python -m black --check scripts/build_package.py tests/test_build_package.py src/startup_utils.py src/starter.py src/starter_headless.py
python -m flake8 scripts/build_package.py tests/test_build_package.py src/startup_utils.py src/starter.py src/starter_headless.py
python -m mypy --explicit-package-bases --follow-imports=silent scripts/build_package.py tests/test_build_package.py src/startup_utils.py
```

## Remaining acceptance boundary

This is a reviewed source repair, not a certified Windows distribution. Native
batch execution, PyInstaller collection, actual Windows junction handling,
packaged GUI/server startup and browser login were not executed here. The full
repository suite and real AI/provider tests were not run.

Before distributing a package, use a disposable Windows checkout with synthetic
fixtures. Build into a new output directory, start the executable from another
working directory, verify the generated admin credential, rotate it, restart,
and confirm that the rotation persists. Check static assets and server shutdown.
Confirm the original synthetic working database and any previous package remain
untouched. Treat a seeded production package as installation-specific; copying
it reuses the same account. Test snapshots are private and encrypted records
require their original key in the test runtime; this builder does not export
that key.
