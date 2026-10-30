# SLMEducator — historical engineering sample

AI-assisted education application with teacher/student workflows, study plans,
assessments, progress tracking, a FastAPI API and a browser interface.

## Scope and provenance

This is a curated **historical source sample from 11 February 2026**, based on
source revision `eac47a42acdc9b482e8c12f40bb7f3b7e9b43522`. It predates the
September–October refactoring work. It is not a September snapshot, the current
implementation, or a production-ready release.

Current development remains private. Technical access to the current version
can be discussed on request for an interview or a technical review.

The sample preserves the historical application code and selected tests. It
excludes the private repository's history, operational documentation, packaging
and installation scripts, deterministic admin-seeding scripts, manual and
real-provider test suites, databases, user data, credentials and generated
artifacts. Minor export edits remove unrelated-project path handling, replace
an obsolete repository referer and generalize a local test-model label. The
historical MIT license is preserved. See `THIRD_PARTY_NOTICES.md`.

## What to inspect

- `src/api/`: API routes and role-based access dependencies.
- `src/core/models/`: relational learning-domain models.
- `src/core/services/`: authentication, content, study plans, assessments,
  progress, spaced repetition, translation and AI-provider integration.
- `src/web/` and `translations/`: historical browser interface and EN/ES strings.
- `tests/`: examples of unit, integration and workflow checks; inclusion does
  not mean every test has been executed or passes.

## Local evaluation only

Python 3.10+ is required by the historical project. Use an isolated virtual
environment and synthetic data only. `requirements.txt` preserves the direct
historical pins; transitive dependencies are not locked. Dependency security,
Windows launchers, browser behavior, provider calls and deployment have not
been certified. The UI references external CDNs, including an unpinned Marked
build. Do not deploy this historical sample or use real student information.

A focused local test command (no model or API key required):

```sh
python -m venv .venv
# Activate .venv using your platform's activation command.
python -m pip install -r requirements.txt
python -m pytest tests/core tests/unit/test_translation_service.py -q
```

Some retained tests outside this focused selection can contact model services.
Do not run the entire suite expecting it to be offline. No AI provider calls,
training, model downloads or paid services were used for the sample validation.
See `VALIDATION.md` for the actual observed checks and limitations.

## License

MIT — copyright (c) 2026 SLMEducator contributors. This sample does not change
or grant access to the private current implementation.
