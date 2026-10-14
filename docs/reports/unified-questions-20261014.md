# Saved questions and shared AI: source delivery, 2026-10-14

Base: `ea7f91bf2835c2cb07decbddda659404bedee8fb` on
`fix/react-functional-continuation-20261007`.

## Delivered behavior

- One persisted **Preguntar / Ask** question with clearly labelled AI and teacher
  replies. AI requests remain explicit, with the existing policy, source-access,
  quota, cancellation and receipt checks.
- Only administrators configure installation-wide AI. No configuration gives an
  explicit error. One legacy administrator configuration is unambiguous; multiple
  legacy administrator rows require an explicit administrator save. Old rows are
  retained, and clients never receive provider secrets.
- An unassigned student has AI only. Human help requires an explicit request to
  the currently assigned active teacher, checked again by the API. No admin
  fallback or background escalation is introduced.
- A definite sharing rejection opens the already-saved question with the error
  visible; AI remains available. Uncertain retries retain their request identity
  and do not create another question.
- Replaced conversation/editor/help forms and their obsolete tests were removed;
  useful coverage and browser journeys were migrated. General teacher messaging
  and unrelated personal-QA API/history remain available.

## Data and upgrade

The new Alembic revision is `20261014_unified_questions`. Existing installation
startup does not silently change its schema. Use the documented recovery upgrade
with an encrypted backup and a **new working copy**, retaining the matching key.
Pending legacy requests with an explicit active teacher are linked deterministically
into answerable threads. Orphan requests, old configurations and unrelated messages
are preserved; messages are never guessed to be answers. No existing user database
was opened, migrated or deleted during this work.

## Verified evidence and limits

All executed application tests used disposable synthetic accounts/data and inert
provider transport. No paid or real-provider inference was performed.

- Full `tests/trust tests/integration`: **1,010 passed**.
- The subsequent core/unit, frontend-delivery, first-run, packaging, seeder,
  unified-question and browser-harness run reported **330 passed, 1 failed**.
  That failure was a missing archived worker fixture in the isolated checkout,
  not an application assertion. Restoring its exact repository bytes and rerunning
  the complete harness produced **4 passed**. The other 327 checks in that run
  passed, including authenticated role journeys and copy-first migration recovery.
- Renewed review found and reproduced a saved-source access leak. List, detail
  and cached-answer routes now recheck current access to every historical source
  item, including items removed from a course. Revoked source text is withheld;
  stored receipts and answer history remain intact. Authorized older versions
  remain readable. The affected authenticated API/boundary suite: **120 passed**,
  including cancellation of a late provider reply. The earlier 1,010-test run
  preceded this narrow correction and is not relabelled as a final-tree run.
- Renewed review also reproduced and fixed two UI recovery defects: a rejected
  teacher confirmation retained an invalid retry identity, and refreshing the
  selected thread could drop its unsaved-reply guard. All **16 focused workspace
  tests passed**. Critical Python syntax/name lint exited **0**.
- Final complete frontend check: **891 passed across 54 files**, with typecheck,
  ESLint and production build all complete, exit **0**.
  Earlier full frontend results were 888 and then 889 passing tests across 54
  files. An execution-session repeat was cancelled; a later final gate stopped
  at typecheck on an unsupported test query option, which was corrected before
  restarting. A subsequent attempt was cancelled by the execution-review layer;
  the single authorized retry completed successfully. No incomplete attempt is
  claimed as a pass.
- Independent read-only review covered all changed production areas,
  authorization, migration, packaging, removed consumers and the renewed fixes;
  no unresolved source blocker was reported. The final delivery excludes generated
  build assets, runtime logs and local test configuration.
- Browser journeys were updated, but painted-browser acceptance was not executed:
  Python Playwright was absent from the existing test environment, and the
  available Chromium launch was blocked by its socket restriction. Browser-harness
  tests are not browser acceptance. Python mypy was unavailable.
- No Windows executable, installed user UI, live provider or educational answer
  quality is certified by these results. GitHub Actions must remain untriggered;
  the workflow files are unchanged and publication uses `[skip ci]`.

## Minimal remaining USER_QA

Perform these only in an approved local environment, using synthetic accounts and
an explicitly approved live-provider request where needed:

1. Verify the installed candidate identity and the backed-up, copy-first schema
   upgrade; confirm retained historical requests and answers.
2. As admin, confirm the shared configuration without exposing secrets. As a
   student with no teacher, submit one question to the real provider, verify the
   labelled answer after reload, and verify no teacher option is available.
3. Assign a teacher to that synthetic student, explicitly share the same question,
   reply as that teacher, and verify both answers after student reload. Revoke the
   assignment between opening and submitting the teacher confirmation: the saved
   question must remain accessible with AI available and no admin diversion.
