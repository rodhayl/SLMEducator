# Registration validation feedback: D3 repair

## Scope and source

This focused repair is based on PR 3 head
`42dc3a8eb73f31dc7fefcce9e4c1b51de554aa47` on
`feature/windows-installer-inno-20261006`. It changes authentication error
presentation and adds regressions. It does not change the backend, EmailStr,
role authorization, registration or password-change policies, installer,
bootstrap, navigation hierarchy, layout, theme, or saved user data.

The historical report in `implementation_documents/manual_windows_20261007/`
remains unchanged. Its A.1–A.5 passes describe the previously tested native
artifact. B.1 recorded HTTP 422 and `[object Object]`; its original POST body was
not captured, so the specific historical rejected field is still unknown.
C–F and real inference were not run in that session. This repair neither
invalidates the reported A evidence nor certifies a new native artifact.

## Behavior

- Registration and login share guarded JSON parsing and bounded error messages.
- Structured validation identifies allowlisted body fields in English/Spanish.
  Validator `msg`, `input`, context and arbitrary object fields are not rendered,
  because even validator messages can contain submitted secrets.
- Only exact, fixed routine backend string messages are displayed (for example,
  duplicate accounts, password requirements, permissions and login lockouts).
  Unknown strings, server 5xx messages and raw or prefixed/escaped payload strings
  use a safe localized fallback; no credential inspection/redaction heuristic
  is required. HTTP error status remains available on the error object.
- Network errors and malformed success replies cannot report account success or
  replace the signed-in administrator. Registration feedback asks the operator
  to check the account list before retrying an uncertain request. No automatic
  retry is introduced.
- Existing in-flight/repeated-submit protection, retryable form values, selected
  role/teacher and creator session remain intact. Only successful creation clears
  the form password.
- The service-worker cache name changes to
  `slm-educator-v22-session-locale-auth-validation`. This invalidates stale static
  authentication code without changing the existing worker activation policy.
  The live-browser upgrade test's expected name follows that change.

## Synthetic fixture correction

Use `docente.demo@example.com` for a valid demonstration teacher. The documented
`docente.demo@example.invalid` and `.test` variants are intentionally invalid
reserved-domain negative cases under the pinned email validator. Keep EmailStr;
do not add a reserved-domain exception to make an invalid fixture pass.

## Executed verification

All data was disposable and synthetic. Dependencies were reused from the existing
prepared environment; no installer, GitHub Actions, user installation or live
provider was executed.

- New canonical `/api/auth/register` suite: 19 passed. It uses the real app,
  dependency graph, create-only admin seeder, login tokens and isolated SQLite.
  Valid example.com creation, reserved-domain rejection without a persisted
  account, corrected retry, creator token, privilege/ownership restrictions and
  the existing registration password boundaries are exercised.
- That suite plus existing auth role and core auth tests: 35 passed.
- Auth-page serving, administrator recovery and frontend source/style checks:
  24 passed.
- New JSDOM error regressions: 60 passed. The real translation files and handlers
  cover both languages, structured/object/string/non-JSON/network errors,
  malformed 2xx responses, secret-safe text rendering, repeated submits,
  corrected retries, role/teacher selection and creator session preservation.
- Full serial JSDOM suite, including the new cases: 257 passed.
- The two email-rendering cases fail against the unchanged baseline auth.js,
  showing literal `[object Object]`, and pass with the repair.
- JavaScript syntax checks, new Python test flake8/mypy, translation-key parity
  and unchanged pre-existing translation values pass.

These are API, source and DOM-emulation checks. They do not establish real
browser rendering, a new Windows binary or completed manual educational flows.
Full-source coverage, the entire Python suite, browser acceptance and native
Windows acceptance were not executed for this repair.

## Required manual retest on a new reviewed build

Record the new source revision, artifact hash and environment separately from
the historical report. Use a new isolated build/output location; do not overwrite
or reset the installed database, existing administrator or saved settings.

1. Reopen the reviewed candidate, confirm the updated authentication asset is in
   use, and sign in with the operator's existing administrator account. For an
   existing browser client, close all old application tabs so the waiting worker
   can activate, then reopen. Check ordinary login, an incorrect login, and EN/ES
   feedback. New binary launch/native-X smoke is still a separate required check.
2. While the administrator remains signed in, choose Teacher and use a unique
   synthetic username with `docente.demo@example.invalid`. Expect a readable
   email error and no new account. Preserve the selected role and entered values;
   do not put passwords or raw authentication request/response bodies in evidence.
3. Change only the email to an unused example.com address. Submit once, including
   a deliberate repeated click while pending. Expect exactly one account,
   teacher role, success feedback, cleared password and the original admin still
   signed in. Confirm the teacher appears in the intended account list.
4. Repeat the readable negative/retry case in the other supported language.
   Verify an administrator's selected teacher assignment for a student survives
   a rejected submission; verify teachers can create only their own students.
5. Continue the previously blocked manual B registration sequence and then the
   still-pending C–F journeys as a separate acceptance session. D1 navigation and
   D2 width/restyling remain outside this D3 patch. Keep historical outcomes and
   new observations distinct; synthetic checks are not live-inference results.
