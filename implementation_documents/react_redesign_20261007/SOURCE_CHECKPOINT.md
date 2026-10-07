# Redesigned GUI: source checkpoint

2026-10-07. Base: `568beb7f522123de5a2cb8249cd633893ccbbf7f`.
This is a source checkpoint, not final acceptance, a release or an installer.

## Implemented scope

The React/TypeScript GUI replaces the retired educational HTML/JavaScript UI across student, teacher and administrator workflows. Shared routing, identity-bound data access, draft/navigation continuity, bilingual presentation and content rendering support the domain pages. FastAPI delivery requires a verified frontend build; legacy links and the narrow service-worker retirement endpoint remain compatibility boundaries. The native launcher presentation, packaging selection, test isolation and maintained browser harness have been adapted.

The checkpoint includes the first review's repairs and the later personal Q&A lifecycle correction. Course-linked personal questions can again follow their owner's edit/share/unshare/delete lifecycle while assigned teaching-material guards remain covered.

## Verified evidence

- Synthetic Python functional aggregate: **1,615 passed, 56 skipped, 5 deselected, zero failures/errors**, exit 0 in 1,354.85 seconds. It ran from 17:47:24 to 18:10:08 UTC. All 623 inventoried source/test/document/build files were unchanged during the run. This inventory includes generated build files that are excluded from this source publication.
- All 25 personal Q&A lifecycle cases passed in that aggregate. Earlier focused results overlap and are not added to the aggregate count.
- Frontend: TypeScript, ESLint and **759 tests across 49 files passed**. All 179 entries in its frozen source/test/tooling manifest still match this checkpoint's source bytes.
- Canonical production build passed, reporting **26 local assets and 29 dependency license records**. Python frontend-distribution validation also passed. Generated dist, dependency trees and build artifacts are not committed; a fresh checkout needs the explicit build described in the README.
- The Python skips remain explicit: 23 AI-provider, 17 browser, 13 Windows command-runner and 3 Windows package/installer cases. The run emitted one third-party Starlette/AnyIO deprecation warning.

After that aggregate, two metadata/documentation fixes were made: the hash-pinned `tests/browser/fixtures/service_worker_v22.js` received its own `-text` Git attribute, and [the installer guide](../../docs/WINDOWS_INSTALLER.md) gained the existing Node/build prerequisite. The fixture bytes and SHA-256 are unchanged. The two existing operational-documentation and offline-harness test files passed **15 cases** on the updated checkpoint. No implementation or test source changed after the aggregate. The 1,615-pass result remains evidence for its original snapshot, not a claim that the complete aggregate was rerun after these two edits.

## Review and acceptance status

**Exactly one whole-codebase review is completed.** [Review 1](AUDIT_1.md) and its repairs are recorded separately. Review 2 is **incomplete**: its worker stopped at a tool-reported security restriction. The restricted check was not retried through another route. Review 3 is **pending**. A preliminary Windows-specific translation-path concern from the incomplete review remains unverified and unresolved by this checkpoint. The separately reproduced personal Q&A issue was repaired and functionally tested.

This paragraph supersedes review counts and pending-run statements in earlier progress reports; those historical reports retain their original evidence. No second or third completed audit, complete security review, full coverage threshold, real-browser acceptance, service-worker lifecycle acceptance, native Windows GUI/zoom/installer acceptance, live AI/provider acceptance or learning-outcome validation is claimed.

## Source and retirement boundaries

Only the explicit source delta is proposed. All other baseline Git leaves and file modes are preserved, including historical screenshots, reports and evidence. The retirement set is exactly 76 paths: the [71 GUI/vendor and replaced-harness paths](LEGACY_RETIREMENT.json), plus the reviewed unused cache/scaffolding files below:

- `src/core/services/ai_cache_service.py`
- `tests/ai/test_ai_cache_service.py`
- `tests/core/test_settings_workflow.py`
- `tests/fixtures/gui_test_utils.py`
- `tests/utils/test_helpers.py`

The cache had no supported active in-repository runtime caller; its implementation-only tests retired with it. Production settings/progress coverage remains. Unknown external consumers were not assessed. Existing historical references were retained.

No user database, private runtime configuration, credential, model weight, local runtime log, dependency tree, generated dist, temporary patch or test output is added. No installer was built, no hosted Actions were run, and no merge or main-branch change is part of this checkpoint. Workflow definitions are source changes only; their hosted behavior and the 80% coverage gate remain unvalidated. A later authorized publication must use the real baseline ancestry and avoid hosted CI execution.
