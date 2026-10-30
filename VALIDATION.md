# Local validation of the historical sample

Validated on 30 October 2026 in an isolated Linux environment with Python 3.12.
The source version is 11 February 2026, not the current private application.

- Direct historical requirements installed successfully in a disposable venv.
- `python -m pytest tests/core tests/unit/test_translation_service.py -q --disable-warnings`:
  **78 passed, 1 warning**, 34.97 seconds.
- The original 106 included Python files parsed successfully with `ast.parse`.
- Both translation JSON files parsed successfully.
- Original files were checked against their historical Git blob IDs before
  export edits. The MIT license was retained unchanged.
- Export review checked secret-token patterns, private paths, endpoint hosts,
  fixtures, binary/data artifacts and attribution. No real credentials or
  private deployment endpoints were identified. This is a review result, not
  a guarantee that the historical implementation is secure.

## Representative real-application checks

- Real loopback HTTP server: 18 checks passed, covering teacher/student
  registration and login, content creation, study-plan creation and assignment,
  student access, completion progress, assessment creation and 401/403 guards.
- Ollama Cloud: the application `/api/ai/chat` route with an authenticated
  synthetic student and assigned lesson context returned a useful Spanish
  explanation of `1/2 + 1/2 = 1`, using `beam:cloud`, in 8.4 seconds (HTTP 200).
  This required the documented minimal server-side cloud-auth compatibility fix.
  The key was transient process input, not saved in the source or database.
- Ten focused regression tests passed for sending the ephemeral key only to
  the official HTTPS host, never localhost/HTTP/lookalike hosts or custom ports.
- Browser GUI: **NOT RUN**. Chromium failed at startup because the isolated host
  did not permit its required socket; the approved environment retry also failed
  before execution. No successful browser walkthrough or screenshot is claimed.

No Windows executable, complete test-suite, performance, production, or current
  dependency-vulnerability validation was performed. Only the stated tutor path,
not every AI workflow, has real-provider evidence.
No models, real user data, private Git history or generated test artifacts are
included. The browser CDN dependencies and unpinned transitive requirements
remain historical limitations. Inspect the sample; do not deploy it.
