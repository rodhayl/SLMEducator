# Coverage and route reconciliation

This note records evidence review and an isolated synthetic browser run. It is
not native installed-app GUI acceptance.

## Routes, roles, and test families

Reviewed `route-contracts.ts`, `feature-routes.ts`, route modules, the matching
coverage rows, and the repository test inventory. The feature route families
are home, people, courses, authoring, learning, assessments, tutor, help,
messages, progress, portability, and settings. Role guards distinguish common
authenticated routes from student progress/help and teacher/administrator
authoring, people, assessment, and administration functions. Action routes
outside the top-level menu (materials, generation/source selection, new
courses/evaluations, student details, attempts/submissions, data portability,
and backups) map to existing course, authoring, learning, assessment, people,
portability, and admin case families. No additional top-level route family was
found missing from the matrix.

This code/route inventory is not a claim that every path was clicked in the
current installed build. The 2026-10-12 Vitest evidence remains
`53 test files, 967 passed`; historical Python r2 remains
`1794 passed, 29 skipped, 5 failed`. The post-fix offline suite and the
synthetic browser run are recorded separately below.

## 2026-10-13 synthetic browser run

The selected Playwright journeys ran against the source checkout's verified
React dist and a disposable loopback-only application/database. A deterministic
provider stub blocked real provider transports. Playwright launched the
existing system Chrome 154.0.8037.98 headlessly with a fresh automated profile;
no existing Chrome session was attached or modified. The managed Playwright
Chromium was missing, so no browser was installed or downloaded.

The final selected set finished with **14 passed, 2 deselected, 0 failed**.
The deselections were the scripted-keyboard case and the fixture-only case;
the fixture-only case had already passed without a browser. Native zoom and
installed-app GUI acceptance were not included. The source-clarification
journey covered author editing/save, learner view/reload, and export/import
with synthetic content.

A separate narrow-login keyboard-event test then passed (**1 passed in 7.77 s**):
at 390px viewport width, Tab moved focus from username to password without
horizontal overflow. This is Playwright keyboard input, not native OS keyboard
or screen-reader evidence.

That journey initially exposed two timing gaps in the test itself: an immediate
DOM read before the editor query resolved, and an immediate reload before the
SPA reader URL changed. Replacing those with retrying value and URL assertions
made the complete journey pass. The frontend source did not change; this was
not recorded as a product defect.

The complete offline Python suite separately finished with **1777 passed,
54 skipped, 0 failed, 1 warning**. The skipped tests include opt-in AI,
browser, and installer/package cases. This does not resolve real-model
SLM-AUTO-018 failures or native GUI requirements.

## `AUTO-LEARN-03.practicas`

The inherited screenshot
`../auto_testing_2026-10-09_002/evidence/shot-learn-03-practica.png` shows the
student view titled “Práctica: Identificar un cuarto,” a “Empezar a estudiar”
button, and no prior sessions for that material/course. It does not show a
started session, selected option, submitted response, feedback, or persisted
attempt. The 2026-10-12 continuation also reported that no exercise was assigned.
Therefore the old PASS is downgraded to PARTIAL.

The repository contains `tests/frontend/learning-tools-components.test.tsx`
with synthetic `PracticeBlock` checks for self-check feedback, hints, answer
drafts, and honest handling of missing answer keys. Component-level coverage is
not evidence of teacher assignment plus a learner's real session and answer.

## `AUTO-VIS-04.zoom`

The inherited evidence explicitly says the native zoom menu did not work in the
headless browser and substitutes a smaller CSS viewport plus DPR. That can
exercise responsive layout, reflow, and focus, but it cannot establish browser
zoom at 100/200/400%. The old PASS is downgraded to PARTIAL pending the visible
native-menu interaction.

An additional attempt ran the browser's actual tab-zoom test in system Chrome
154 with a fresh persistent profile and generated extension. Both 200% and 400%
cases timed out waiting for the extension service worker before reaching any
zoom assertion. A retry after removing the Playwright service-worker block had
the same result. The managed Playwright Chromium is absent and was not
downloaded. The attempt is recorded as a technical BLOCKED row, not a
product failure. `AUTO-VIS-04.zoom` remains PARTIAL pending a successful
visible-menu/native zoom pass.

## `AUTO-TUT-01.libre_contextual` and `AUTO-AI-04.formatos_cancelar`

The owner report describes a useful free-tutor answer, a contextual 200 after
the 4000-token change, two 90-second `ReadError`s, and a later successful
response. The linked `shot-1012-tut-02-contextual.png` and
`shot-1012-tut-02-contextual-honest-reject.png` are both pre-submit views of the
same form. The file named `shot-1012-tut-02-contextual-fixed4000.png` in the
modified coverage row is not present in the campaign evidence directory.
Therefore these two rows are PARTIAL until the response/receipt and the complete
cancel/unavailable/recovery behavior are durably tied to the candidate and
actually served model. The inherited candidate field named the old installed
29df build, but the screenshots do not identify the running executable or
server. The new matrix marks the candidate unverified instead of assigning the
report to the currently installed cc0c build.

## Evidence boundaries

- Current owner-reported Setup and first-account actions remain attributed to
  the owner; registry and EXE identity were independently checked, but no GUI
  flow was repeated.
- The current installed application was not launched. No user database,
  runtime config, saved credential, or browser session was inspected.
- Native zoom, Narrator audio, and the assigned learner exercise require an
  authorized visible-GUI turn. The current run did not use CDP, viewport
  simulation, accessibility-tree output, or API/database shortcuts as
  substitutes for those interactions.
