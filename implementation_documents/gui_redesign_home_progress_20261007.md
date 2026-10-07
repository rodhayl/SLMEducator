# Role home and progress migration

Date: 2026-10-07. Implementation in the shared React redesign candidate. No backend, legacy GUI, installation, provider, user database or external service was changed by this domain work.

## Delivered

- Student home presents separate named course/session and existing-assessment-attempt actions simultaneously. Reading home uses only GET calls, never starts/restores/reserves a session or attempt. Existing active sessions use their pinned snapshot title and exact session/content/plan identifiers. Without an active session, the owner-scoped location marker is revalidated against current course structure/progress before use; otherwise the next incomplete item is chosen in canonical phase/order. Completed or empty courses are skipped until an incomplete course is found, with explicit course selection retained.
- Teacher home shows pending manageable assessment submissions and open help requests, with a short preview and complete-queue links. Assessment authorship, rather than the current student-enrollment roster, determines the correction queue. Help priority/order does not infer unread replies.
- Administrator home prioritizes people, real application-server/version status and private backup navigation. It does not display the administrator’s personal activity as installation-wide learning metrics or impersonate a learner.
- `/progreso` has query-selected overview, review/evidence, recent activity, daily goal, and participation/ranking sections. Student, teacher and administrator direct access always describes the signed-in account’s own data; no `student_id` query changes the actor. Teacher-only dashboard measures are separately labeled as authored assessments/materials and current active assigned students.
- Session count is labeled as completed learning sessions, not unique lessons; known elapsed minutes and unknown-duration sessions remain distinct. Zero final scores remain zero; missing evidence is not converted to zero. Course/session and assessment history link to their existing exact resource views.
- Review suggestions are labeled heuristic. Final assessment evidence, self-confidence and legacy activity remain separate. No legacy mastery average, XP, streak or badge is presented as demonstrated learning.
- Own participation profile and badges retain historical civil-day/timestamp uncertainty. Badge images/remote icon paths are not loaded. Rankings describe their actual authorization scope and server period-cache/lifetime fallback, never an invented global or verified weekly ranking.
- Daily-goal forms use RHF and the shared dirty/unload guard, validated mutation receipts, single flight, and explicit reconciliation after an unknown result. Pending intent survives same-account reauthentication; old-account or old-epoch callbacks do not publish a receipt. No mutation is automatically replayed. A confirmed save remains confirmed when its subsequent refresh fails, and reconciliation read failures do not destroy the draft.
- All frontend labels, states, accessible names and explanatory caveats have EN/ES parity. Shared styles/components/auth/query/API/time adapters are reused; no graph library or dependency was added.

## Exact integration

- Existing `features/home/HomePage.tsx` export remains `HomePage`. `features/home/routes.tsx` additionally exports `routes` containing `inicio`. The foundation already directly imports HomePage: do not also register an overlapping lazy `inicio` route unless replacing that direct ownership.
- `features/progress/routes.tsx` exports `routes = [{ path: 'progreso', Component: ProgressPage }]`. Add `progress: ['progreso']` to the foundation’s lightweight route map.
- `features/home/locales.ts` and `features/progress/locales.ts` export `{ en, es }` and are discovered by the existing locale glob. Namespace names are `home` and `progress`.
- Progress query keys all begin with `['progress', ...]`, except shared timezone `['settings','timezone']`. Home reuses existing `['courses']`, `['courses', id, 'tree'/'progress']`, `['learning','active']`, `['submissions']`, `['assessments']`, `['grading-queue']`, `['help-requests']`, and `['settings','status']` ownership.
- Learning completion should invalidate `['progress']` after a confirmed completion. Grade finalization should also invalidate it for current-actor views. Preserve existing shared identity/credential continuation rules and never reinterpret a confirmed write as failed because refresh failed. This cross-domain request was sent to the root owner; it is not implemented by editing another worker’s files here.
- People detail already provides exact authorized `/api/students/{id}/progress` and private notes. It should keep those actor-specific data; do not point another learner’s detail at these current-account gamification endpoints. People list URL filters were absent at inspection, so admin home does not claim an inactive-filter deep link exists.

## Backend limits deliberately preserved

1. `GET /api/gamification/daily-goal` can create a database row from defaults. The new page uses the nonmutating `/daily-goal/progress` read instead. That read cannot distinguish a displayed default from an existing current-day row; the UI discloses this and allows explicit Save even without field edits. It does not claim viewing the page activates counting.
2. Goal updates retain `current_value` and `completed`, even when type/target changes. Completed rows stop accruing in the current learning API. UI explains that edits do not recalculate activity or reopen a completed goal and warns if a completed flag conflicts with an increased target. There is no fabricated reset action.
3. The progress read does not expose the saved future default. After an uncertain write involving `save_as_default`, matching current-day values cannot verify the future default. The UI says so and lets the user explicitly discard edits in favor of the current server goal; this is not a claimed successful write.
4. `/api/dashboard/activity` returns opaque original English descriptions and relative labels, without raw timestamps or resource-type identifiers. The original server content is safely rendered as text beneath a localized scope/provenance explanation. It is not parsed into invented instants, identities or translated user content. The server limits it to recent known-time activity and up to ten entries.
5. There is no combined all-learning-session history API. Course → material history and the existing assessment-history route preserve the supported resource-scoped history instead.
6. `/api/mastery/overview` mixes heuristic/legacy measures; final evidence comes from `/api/mastery/evidence` instead. Due-review suggestions are labeled heuristic and do not claim assessed mastery merely because a schedule exists.
7. Rankings may use period-cache values or lifetime XP without a response field identifying which branch was used. The requested period remains selectable with that uncertainty visible; the client does not claim period-specific totals.
8. The due-review service catches SQLAlchemy read errors and returns an empty list, so the HTTP response cannot distinguish that backend failure from no suggestions. The frontend distinguishes HTTP/validation failures from valid empty responses and does not fabricate missing error metadata.
9. The existing student-progress API is separate from current-account participation APIs. No cross-student badges, invented all-user progress endpoint or global analytics were added.

## Verification

Focused synthetic DOM/contract suite: **35/35 passed across three files** (`home-flows.test.tsx`, `progress-flows.test.tsx`, and `progress-contracts.test.ts`). Final full-project TypeScript and focused domain/test ESLint both passed after these changes. Synthetic fixtures are in `progress-fixtures.tsx`.

Coverage includes role homes; simultaneous resume actions; actual pinned resource identity; GET-only reading; completed-course skipping; explicit course selection; owner-marker validation; failed versus empty state; assessment ownership; account replacement; zero versus absent scores; evidence provenance; safe original activity text; own badge/ranking scope; unknown historical time; period selection; locale/placeholder parity; validated goal receipts; duplicate-click protection; uncertain-write reconciliation; dirty section navigation; refresh failure preserving draft and confirmed receipt; credential-epoch reauthentication without replay; old-account late writes; and completed-goal counter semantics.

Commands:

```
cd src/frontend
npm run typecheck
npm test -- --run tests/frontend/home-flows.test.tsx tests/frontend/progress-contracts.test.ts tests/frontend/progress-flows.test.tsx
cd ../..
src/frontend/node_modules/.bin/eslint --config src/frontend/eslint.config.js src/frontend/src/features/home src/frontend/src/features/progress tests/frontend/home* tests/frontend/progress*
```

These are source/DOM checks. They do not establish painted layout, browser interaction, native Windows installation or a complete aggregate migration pass. No legacy files were removed and no push, main-branch update, Actions run or real-provider call was made.
