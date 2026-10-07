# People, accounts and enrollment: React milestone

Date: 2026-10-07. Working source: `slm-react-redesign-20261007`, provided base
`568beb7f522123de5a2cb8249cd633893ccbbf7f`. This is the People domain of the
approved redesign, not a claim that the whole replacement GUI is finished.

## Implemented

- `/personas`: administrator role/status filters, bounded-list search, identity
  links, active/inactive state, and a teacher-specific “My students” view.
- `/personas/nueva`: fluid identity/access form with explicit administrator role
  selection, all three real API roles, and teacher-only owned-student creation.
  Successful creation leaves the creator session intact and offers a useful next
  destination or another creation. Administrator enrollment is a separate action.
- `/personas/:personId` and `/estudiantes/:studentId`: verified direct-link account
  read, profile, responsible teacher, progress, current-author private notes and,
  for administrators, confirmed account status/recovery actions.
- Enrollment explicitly preserves previous assignments and assessment authorship.
  The confirmation identifies both the learner and teacher by name/username.
  Administrators get their own notes, never notes written by another teacher.
- Passwords remain in the active form/transient request only. Register and recovery
  use void mutation variables; no password enters Query variables, query keys,
  local draft storage or confirmation text. Registration and recovery retain their
  distinct 8/12-character minimums and 72-byte UTF-8 bound. The server remains
  authoritative for password and email validation.
- D3 allowlisted field errors, local ES/EN text and safe shared errors are retained.
  Rejected creation preserves input and role. Unknown creation/recovery results
  do not become success and cannot be automatically replayed.
- Unknown notes, enrollment and status writes can be followed by an explicit read
  of the current server state. This does not repeat the write. Notes preserve edits
  made during a save and show a changed server version for explicit reconciliation.
- Dirty navigation uses the shared guard. Same-account reauthentication preserves
  hidden in-memory forms and revalidates the exact account/notes/progress resources.
  Replacing the account/role remounts the domain; late results cannot populate it.
- Positive safe frontend IDs and validated response shapes precede rendering or
  claims of successful mutation. Backend authorization remains authoritative.

## Narrow backend integration gap

Added `GET /api/auth/users/{user_id}` to `src/api/routes/auth.py` under the parent's
explicit integration authorization. It returns the existing `UserListResponse`,
with no new PII fields or write capabilities. Positive signed-SQLite-range IDs are
required. Administrators can resolve active/inactive accounts, including their own.
Teachers can resolve only active students within existing `can_manage_student`
scope. Students are denied. Missing and inaccessible records use the same 404.

This fixes direct links beyond the directory's 500-account limit without adding
pagination or changing account mutation, enrollment, authentication, bootstrap or
last-administrator policy. The directory/teacher selector limit is disclosed.

## Owned source and tests

- `src/frontend/src/features/people/routes.tsx`
- `src/frontend/src/features/people/model.ts`
- `src/frontend/src/features/people/locales.ts`
- `src/api/routes/auth.py`: imports and new read-only detail endpoint only
- `tests/frontend/people-flows.test.tsx`
- `tests/frontend/people-model.test.ts`
- `tests/integration/test_auth_user_detail.py`

The foundation owns global router/locale registration, shared primitives, auth,
query/operation adapters, styles and dependency installation. No legacy GUI was
removed in this milestone.

## Verification

All API fixtures were synthetic and disposable. No real provider, user database,
installer, Actions workflow, remote publication or global setting was used.

- 35 focused frontend/model tests pass, using the real shared AuthController,
  ProtectedLayout, API/query/operation and dirty-guard components with a synthetic
  transport. Coverage includes ES/EN D3 rejection/correction, all create roles,
  creator session retention, separate enrollment followed by teacher login/list,
  direct links and role denial, unknown results/no replay, no password in Query,
  status/recovery confirmations, private notes, conflict reconciliation, keyboard
  dialog dismissal, dirty navigation, same/different account reauth and late writes.
- 32 real-token API/regression tests pass: the new detail suite, existing canonical
  registration suite and existing administrator-recovery suite. These exercise
  real application dependencies and SQLite, including reassignment/private-note
  separation, active/inactive access, malformed IDs and a record beyond 500 rows.
- Frontend typecheck passes for the current combined frontend source.
- Focused frontend ESLint and Python flake8 pass.
- Focused mypy passes for `src/api/routes/auth.py` and the new API test module.

Commands (from repository root unless shown otherwise):

```sh
cd src/frontend
npm run typecheck
npx vitest run ../../tests/frontend/people-model.test.ts ../../tests/frontend/people-flows.test.tsx
cd ../..
./src/frontend/node_modules/.bin/eslint --config src/frontend/eslint.config.js src/frontend/src/features/people tests/frontend/people-model.test.ts tests/frontend/people-flows.test.tsx

# PY is the existing prepared SLM Python environment, not a new installation.
SLM_OFFLINE_TESTS=1 USE_REAL_AI=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD "$PY" -m pytest tests/integration/test_auth_user_detail.py tests/integration/test_auth_registration_contract.py tests/trust/test_admin_account_recovery.py -q -ra --strict-markers -p no:cacheprovider --basetemp=/tmp/slm-people-api-final-20261007
"$PY" -m flake8 --config=.flake8 src/api/routes/auth.py tests/integration/test_auth_user_detail.py
"$PY" -m mypy --config-file mypy.ini --follow-imports=silent --cache-dir /tmp/slm-people-mypy-20261007 src/api/routes/auth.py tests/integration/test_auth_user_detail.py
```

Raw command output and owned-source hashes are retained outside the source tree at
`/tmp/slm-people-evidence-20261007/`. The API run reports one existing Starlette
`BlockingPortal` deprecation warning. The frontend commands report npm environment
configuration/update notices; these are not test failures.

## Remaining acceptance and limits

- Actual browser paint, responsive/zoom visual inspection, assistive-technology
  review and native Windows validation have not been run. DOM tests do not certify
  those outcomes. The parent reported the browser-paint route blocked.
- This is focused domain evidence, not the entire project test/coverage gate or
  approval to retire the legacy GUI. Final integration and independent review are
  owned by the parent.
- The existing list and teacher selector remain capped at 500; their search is
  explicitly local to loaded records. The new detail endpoint has no such list
  dependency. Pagination is outside the authorized narrow backend correction.
- There is no invented role change, impersonation, account deletion, transfer of
  another author's notes, or client-only authorization. Existing self/last-active-
  administrator protections remain in the backend.
- A lost password-reset receipt cannot be safely confirmed by reading a password;
  the UI directs the operator to have the account holder try it before another
  reset. It does not sign in as that person or replace the creator session.
- Notes reconciliation detects observed conflicts; it does not claim server-side
  compare-and-swap where the existing API provides none.
