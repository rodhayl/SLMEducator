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
an obsolete repository referer and generalize a local test-model label. A small
compatibility fix adds ephemeral server-side Ollama Cloud authentication and
endpoint/model overrides; it does not import the current private implementation. The
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
Windows launchers, browser behavior, deployment and complete UI behavior have not
been certified. The UI references external CDNs, including an unpinned Marked
build. Do not deploy this historical sample or use real student information.

A focused local test command (no model or API key required):

```sh
python -m venv .venv
# Activate .venv using your platform's activation command.
python -m pip install -r requirements.txt
python -m pytest tests/core tests/unit/test_translation_service.py tests/unit/test_ollama_cloud_headers.py -q
```

Some retained tests outside this focused selection can contact model services.
Do not run the entire suite expecting it to be offline. A representative tutor request was successfully exercised through the real
application using Ollama Cloud `beam:cloud`. No training or model downloads were
performed. This does not establish every AI feature or model as functional.
See `VALIDATION.md` for the actual observed checks and limitations.

## Run the historical application locally

After installing dependencies in your venv:

```sh
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8080
```

Open `http://127.0.0.1:8080/register.html` and create a synthetic teacher account.
Keep this historical server on loopback, never a public interface. No default
admin password or database is supplied. Runtime settings/databases are local
artifacts, not part of the source sample.

For an optional Ollama Cloud evaluation, set `SLM_OLLAMA_URL=https://ollama.com`,
`SLM_OLLAMA_MODEL=beam:cloud`, and `OLLAMA_API_KEY` in the **server process's
environment** before starting it; leave the default provider as Ollama. Obtain
your own authorized provider access and check its usage limits first. Never put
keys in browser code, tracked files or screenshots. The environment key is sent
only to the official HTTPS Ollama host and is not saved by this compatibility
path. Existing per-user AI configurations take precedence over default overrides.
If your environment uses a SOCKS proxy, install the optional `httpx[socks]==0.28.1`
extra in the venv (the validation host used `socksio==1.0.0`).

## License

MIT — copyright (c) 2026 SLMEducator contributors. This sample does not change
or grant access to the private current implementation.
