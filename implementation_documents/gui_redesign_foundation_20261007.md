# GUI redesign: foundation and first vertical slice

Date: 2026-10-07. Base: `568beb7f522123de5a2cb8249cd633893ccbbf7f` on `work/gui-redesign-plan-20261007`.

## Scope and status

This is an implementation milestone within the approved complete GUI replacement, not a claim that the project is finished. The exact 474-blob base tree was materialized and verified before integration. Existing historical evidence remains intact.

Implemented:

- A new static React/TypeScript/Vite frontend with a pinned npm lockfile, React Router Data mode, one TanStack Query remote-data owner, React Hook Form, Base UI dialogs, Tailwind/token styles, i18next ES/EN, Lucide and a single Marked/DOMPurify rendering boundary.
- Role-aware desktop/mobile navigation, same-origin API requests, route ownership and lazy domain loading, accessible field associations, persistent safe errors, explicit saving states and navigation/unload guards.
- Auth verification before private rendering; account/role-owned cache and credential-epoch-bound request clients; hidden/inert same-account recovery; protected portal contents; current resource permission revalidation; no automatic mutation replay; cache/buffer reset on account or role replacement and cross-tab/BFCache checks.
- Safe D3 error translation, strict identity/ID and response checks, and distinct unknown mutation outcomes. Arbitrary backend text, validator `msg/input/ctx`, and JavaScript exception messages are never rendered as user errors.
- Established owner/resource/attempt browser draft formats, seven-day TTL, explicit recovery and owner-only deletion, no private Query persistence, and storage failure reporting. An unconfirmed persisted logout clears the current private memory and warns that saved sign-in data may remain.
- Common light/dark/system appearance and reading size; explicit timezone/provenance formatting that never assumes an offset-free historical date is UTC.
- People/account creation and explicit enrollment, admin account operations, exact-resource detail lookup, teacher-owned notes and progress; course/manual lesson authoring, structure/order, review/publication/assignment and revision; student material preview, pinned-session reading, notes, pause/continue/completion, practice, annotations and contextual help.

The real three-role API test seeds only a disposable synthetic administrator, registers a teacher and an explicitly enrolled student, creates and publishes/assigns a teacher-owned manual course, and checks the learner's snapshot/notes/pause/continue/progress and the teacher's authorized view. It also checks registration correction, creator-session preservation, negative permissions, immutable assigned material and duplicate-reward prevention.

## Build and dependency spike

The initial build used Node 24.19.0 and npm 11.9.0. The declared development floor is Node 22.22.0. Dependencies were installed once from the official npm registry with scripts disabled; no AAC dependency tree was copied or modified. Production dependencies are pinned in `src/frontend/package.json` and the complete lockfile. An npm production-dependency advisory check reported no known vulnerabilities at this checkpoint; this is not an assurance that no vulnerability exists.

`npm run build` emits only static output. It produces Vite's `.vite/manifest.json`, a SHA-256/size `build-manifest.json`, and a notice inventory from the locked installed runtime packages plus Tailwind, whose emitted CSS is shipped even though it is installed as a development dependency. Generated assets, dependency trees, test output and local logs are excluded from Git. The notice inventory's presence is not an independent license audit.

Useful official references checked for the implementation: [Vite backend integration](https://vite.dev/guide/backend-integration), [React Router Data mode](https://reactrouter.com/start/data/installation), and [Base UI Dialog](https://base-ui.com/react/components/dialog). Local installed type declarations and the real existing API code are the contract authority for this pinned candidate.

## Verification boundaries

Current maintained foundation checks pass: 133 tests in 11 files, full-project TypeScript at the checkpoint, and focused foundation/test ESLint. A post-cleanup download rerun passes 5/5. The independent focused review passed eight adversarial tests and rechecked its seven findings after repair. Its course/learning continuation and completion-expiry regressions now live under `tests/frontend/foundation-*`, not only in disposable review files. The latest clean combined frontend gate before the subsequent adapters and concurrently added domains passed 294 tests in 16 files plus build; a later aggregate was blocked by in-progress authoring/portability files, so it is not presented as a final whole-project pass. Re-run the complete gate after ongoing domains settle. Reproduce frontend checks with `cd src/frontend && npm run check`. The real API journey is `tests/integration/test_frontend_vertical_contract.py`; run it under the repository's documented offline configuration with a unique disposable `--basetemp`.

Selected computed token pairs meet their explicit thresholds: text 5.93–14.16:1; border/surface 3.37:1 in light and 5.02:1 in dark. Tests keep those specific pairs above 4.5:1 and 3:1 respectively. This is not full-state contrast, painted layout, zoom, screen-reader or WCAG acceptance.

## Work still owned by the complete migration

- Remaining assessment/authoring/generation/grading/messaging/settings/progress/portability screens and their exact parity assertions.
- Source/frozen static hosting, legacy link compatibility, safe service-worker retirement, launcher, package and installer integration.
- Actual browser interaction and painted layout/zoom, native Windows build/install/start/login and the separate historical manual acceptance gates. DOM and TestClient checks do not establish these results.
- Removal of the old executable GUI only after each domain's contract parity and tests. This milestone has not deleted it or installed a new package.
- Three independent whole-codebase final audits after all migration work is finished. The current count is zero; the milestone review is not one of those three final audits.

The reviewed admin/foreign-author attachment gap is constrained without changing backend permissions: read-only creator/provenance metadata drives the UI, foreign-private attachments and unsafe draft recovery are rejected, authorized public-source reuse remains available, and an owned revision is offered before adding new material to another author's course. The real first vertical uses consistent teacher ownership.

No real provider/model campaign, real account data, user database, Windows installation, GitHub Actions run or main-branch change was used for this milestone.

## Shared integration handoff

The foundation now also exposes multipart upload and MIME-checked, credential-bound Blob download adapters, bounded object-URL cleanup, verified profile refresh, explicit same-account reauthentication, and motion-preference application. The app requests updates only for an existing exact root `/sw.js` registration; it never registers a new worker, forces activation or reloads dirty pages. The `/inicio`-only dashboard bridge uses the historical hash → view → tab precedence, exact view allowlist, and validated context/filter parameters. This does not certify the real browser service-worker transition.

Assessment, authoring, settings and portability routes have been registered as their modules were delivered; their separate owners retain domain verification. Shared data settings use `/ajustes/datos`, with private admin backup at `/administracion/copias`. Messages/help still require root registration when delivered. Source/dist must be rebuilt together after those changes: the current manifest verifies asset bytes and the lockfile, not an independent digest of every source input.
