# Frontend safety regressions

These checks are deliberately separate from real-browser and real-provider tests.

- Python source/asset/semantic contracts: `python -m pytest tests/ui/test_style_standardization.py tests/ui/test_frontend_safety.py -q --basetemp=/tmp/slm-ui-source-UNIQUE`
- DOM behavior (Node 20+): from `tests/ui`, run `npm ci --ignore-scripts` then `npm test`.
- To keep dependencies outside the checkout: `npm ci --prefix /tmp/slm-ui-test-deps` after copying this package.json and package-lock.json there, then run `NODE_PATH=/tmp/slm-ui-test-deps/node_modules node --test --test-concurrency=1 tests/ui/*.test.cjs` from the project root.

The jsdom suite executes the real bundled sanitizer, renderer and UI handlers with
synthetic HTTP responses. It covers injected author/model/import strings, denied
and failed saves, account/attempt draft isolation, expiry and storage failures,
server deadlines, pending grades, restoration, dismissals, keyboard alternatives,
practice self-checks, partial generation and portability previews. It is not proof
of rendering, focus behavior or XSS resistance in a live browser engine.

The HTML-serving integration tests prove serving/auth contracts only. They do not
establish a completed learner journey. Browser, screen-reader, zoom/reflow and full
English/Spanish journey checks still require a supported browser environment.

Third-party browser assets are local, pinned, licensed and hashed in
`src/web/static/vendor/manifest.json`. Update each asset and its manifest together,
then run both suites. Do not silently restore unpinned CDN scripts.

Role journey regressions cover selected registration roles and creator sessions, completed versus paused navigation, pending lesson IDs, teacher grading deep links, read-only learner feedback, editable drafts, assigned-plan immutability, teacher-only assessment preview, closed attempt persistence, context changes and bilingual page language. Synthetic DOM tests do not establish live browser acceptance.

The default Node script runs files serially to keep jsdom resource use bounded. The additional suites exercise in-lesson source-bound help and request receipts, explicit provider repair, durable source manifests, portability formats, and confirmed administrator account operations with synthetic inputs only.
