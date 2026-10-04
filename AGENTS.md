# Repository working rules

- Read `README.md` and `docs/CONTRIBUTING.md` before changing behavior.
- Use disposable synthetic databases for tests. Never inspect, overwrite, reset,
  or package a user's database or private configuration as part of development.
- Bootstrap is create-only: an existing `admin` username keeps all account and
  authentication state. Reuse `scripts/seed_admin.py` rather than a second seeder.
- Packaging writes only isolated staging and a new output directory. Test-data
  packages require an explicit SQLite source; production never reads that source.
- Run affected tests and focused lint/type checks after changes. For packaging
  and bootstrap: `python -m pytest tests/test_build_package.py tests/test_seed_admin.py -q`.
  Mocked freezing on Linux is not evidence of a working Windows executable.
- Keep credentials, runtime data, generated builds, and local logs out of Git.
