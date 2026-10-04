# Product closure: approved implementation, 2026-10-04

Baseline: local `2ad6e05`, published `302f5dd2`. This extends the earlier technical
learning-loop work after an independent product audit. Passing defect
characterizations are evidence of defects, never evidence of repaired behavior.

## Scope and evidence ledger

| Phase | Requirements and audit coverage | Status / acceptance evidence |
| --- | --- | --- |
| 0 | UX-01 role selection; UX-02 annotation audience; CUR-01 hidden inline assessment keys; CUR-02 usable linked assessments; CUR-07 content/reference/order validation; CUR-08 audience-complete exports; shared create/edit/import contracts | In progress; two teachers/two learners, malformed input rejected before writes, keys/rubrics confined to author endpoints |
| 1 | CUR-03/04/05/06/10/11: canonical content; durable extraction/usage provenance; coherent render/tutor/export/session revisions; late sections; consistent budgets; source changes invalidate dependent review | Pending; actual source selection and review snapshots, no inferred historical provenance |
| 2 | UX-03/04/05/06/07/08/11/12/13/14/16/17: correction and feedback; completion/navigation; roster enrollment; draft edits and copies; attempts; admin scope; truthful metrics | Pending; complete role journeys and failure/retry regressions using existing services |
| 3 | UX-10 and AI audit 1–7: contextual tutor/help; supported providers/settings; section selection/context invalidation; delivery permission recheck; bounded usage/concurrency/cancel and honest receipts | Pending; deterministic provider stubs only; real model semantics remain unverified |
| 4 | CUR-09/12 and full portability criteria: preview/validation/round-trip; vocabulary/objectives/references; explicit copies/revisions and version compatibility; separate private backup; explicit media/OCR exclusions | Pending; cross-installation synthetic keys and transactional failure cases |
| 5 | UX-09/15 and AI audit 3/7–12: keyboard/labels/i18n/navigation; verified unused-code cleanup; packaging imports/readiness; minimal offline CI; stable aggregate and requirement map | Pending; source/DOM checks are separate from native/browser/human acceptance |

## Contract decisions

- Keep FastAPI, Pydantic, SQLAlchemy/SQLite, HTTPX, Bootstrap and existing modules.
- Annotation sharing means the author's enrolled teacher and administration,
  never classmates; new annotations are private by default.
- Assessment content is an executable `assessment_id` reference. Reject inline
  exam definitions with an actionable import error; preserve legitimate low-stakes
  practice self-checks. Existing invalid records cannot disclose keys to learners.
- Course publication requires usable published linked assessments. Review
  fingerprints include assessment definitions; later changes require new review.
- Existing assigned-course immutability, teacher-final subjective grades,
  replay-safe rewards, safe rendering, backups/migrations and unknown-time guards
  remain constraints. Copies never silently replace assigned work.
- Use synthetic fixtures, fail-closed provider stubs and unique pytest basetemp.
  Run individual/affected checks while changing code, then one stable aggregate.
- No paid inference, real student data, external write-back, new deployment,
  main merge, extra roles, vector database, microservices or framework rewrite.

## External acceptance gates

Cloud browser previously returned `ERR_BLOCKED_BY_CLIENT` for localhost. Native
Windows, real-browser/accessibility, real-model quality and authorized human pilot
remain unverified until actually executed. Static/DOM/API success cannot close
these gates. Original binaries, external media and unknown historical source zones
must have explicit inclusion/provenance statements, never fabricated coverage.

## Checkpoint 1: privacy and import/publication contracts

The selected account role now survives submit and retry without replacing the
creator's session. Annotation API sharing reaches only the owner, enrolled teacher
and administration; private annotations remain owner-only. Inline exam definitions
are rejected before import writes, and existing invalid records cannot disclose
keys/rubrics through learner content reads. Canonical package validation rejects
bad content, references and positions and validates the same audience graph for
preview/download. Learner handouts preserve vocabulary and omit unavailable exam
pointers. Course review identities now include assessment questions/rubrics, and
publication/assignment requires published executable linked assessments.

Evidence: 58 affected API/service tests passed; after added phase/position bounds,
12 privacy/course tests passed. The four account-role DOM regressions passed.
Focused critical lint and two-module type checks pass. These are overlapping
bounded scopes, not an aggregate suite or browser acceptance. Remaining phases
and the annotation UI default/error polish are still in progress.
