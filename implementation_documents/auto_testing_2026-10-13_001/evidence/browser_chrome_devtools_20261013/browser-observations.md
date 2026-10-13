# Chrome DevTools synthetic browser observations

- Date: 2026-10-13.
- Browser: existing Chrome instance managed by the Chrome DevTools connection; page isolated context `slm-browser-acceptance-20261013`.
- Origin: `http://127.0.0.1:56134` only. No non-loopback app/API origins were used.
- App: current checkout React dist served by `tests/browser/local_server.py`; independent synthetic SQLite database and config under `%TEMP%\slm-chrome-devtools-run-20261013-01\state`; deterministic AI stub disables provider transport.
- Fixture scenario: `synthetic-adult-fractions-v1`; only seeded synthetic accounts/content. Account credentials were retrieved privately from the fixture using a loopback-only helper and are intentionally not retained here.
- Chrome DevTools direct observations: login as `teacher_a` succeeded; authenticated dashboard showed synthetic teacher identity; roster contained `learner_a` and did not contain `learner_b`; appearance page saved dark theme and English, returned “Appearance and language saved.”, set `data-theme=dark`, `lang=en`, and dark body background `rgb(17, 39, 37)`.
- A dashboard screenshot was captured in the browser response for in-session viewing. The DevTools screenshot file API rejected repository paths as outside configured roots, so no screenshot file is claimed by this note.
- This is source-checkout/manual DevTools evidence only, not Playwright acceptance-suite output, native OS keyboard/Narrator, installed-app acceptance, or a grade/submission outcome.
- Initial server startup via detached `Start-Process` exited with its parent shell; that empty fixture was stopped and removed after verifying process/listener exit. The persistent foreground-backed fixture now serves successfully on loopback; status endpoint returned 200. A loopback-only, credential-redacted helper runs separately to fill login credentials without printing secrets.

## Learner and teacher help-request loop (second DevTools pass, same session)

All steps performed through the same isolated browser context against `http://127.0.0.1:56134` only.

- Sign-out from `teacher_a` presented a confirmation dialog ("Sign out of this account?") with options to delete or keep drafts; "Sign out and keep my drafts here" returned the app to `/entrar` cleanly.
- Sign-in as `learner_a` (Student) succeeded via the credential helper; the account appearance form showed learner_a's own defaults (Follow device appearance / Spanish), confirming per-account preference isolation from `teacher_a`'s saved dark/English values.
- Learner home rendered correct empty states: "No courses available" (no course assigned to learner_a in this fixture state) and "No open assessments", with the explanatory copy "Home never starts an attempt; timed attempts keep their original deadline."
- Tutor flow (learner, no source selected): submitting "How do I add fractions with different denominators?" returned the deterministic stub hint ("Synthetic browser-test hint: compare equal parts. This is not a real model answer.") with the disclaimer "AI suggestion, not verified. Check it against the material and your own work." The conversation log stated the conversation is not saved as learning records.
- Help request creation (learner): form offered subject, description, and priority 1-5. Submission succeeded: "Request #1 is saved and open. A reply is not guaranteed immediately." The list showed the request as Open, Priority 1, attributed to "Synthetic learner_a".
- Teacher side: sign-in as `teacher_a` showed the same request under "Help requests" with matching subject, status Open, priority 1, and learner attribution. The detail page showed the full learner text, learning context ("No course or material is attached."), a reply form, "Draft with AI", and resolution notes.
- Teacher reply: sending a response returned "Response message sent. The request is still open until you resolve it separately." (correct semantics: reply does not auto-resolve).
- Learner delivery: after signing back in as `learner_a`, the nav showed "Messages 1 unread messages"; the inbox contained "Re: Stuck on fraction addition", Unread, From "Synthetic teacher_a", with batch actions (Mark read/unread, Archive, Delete permanently) disabled until selection, and the shared-archiving/deletion notice rendered.
- Console: no new errors observed during this pass (the earlier single 404 resource error from the first pass was not reproduced; it matched a one-time SPA asset fetch).
- Boundaries: all interactions were manual DevTools steps against the disposable synthetic fixture. This documents manual cross-check evidence only; the equivalent automated Playwright journeys (live journeys, best-effort tutor, help requests) remain the authoritative suite results. No answer-write or course-completion endpoints were exercised.