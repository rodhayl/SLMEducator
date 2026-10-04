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

## Checkpoint 2: connected journeys and captured curriculum

The learner now reaches correction feedback without reserving another attempt;
grading has a real queue-to-submission link. Complete/Next share retry-safe
completion, Previous/Pause preserve notes without completing, and Continue selects
pending IDs. Administration can assign/remove a responsible teacher explicitly,
with history and prior work preserved. Saved drafts can be edited; assigned
courses are copied to independently reviewed drafts with lineage. Explicit attempt
closure preserves draft answers, consumes the reserved attempt and releases active
assistance policy without a grade or reward. Zero scores remain zero.

Canonical sections preserve distinct legacy bodies and section text for render,
tutor and handouts. Tutor scope validates course membership and source revision,
supports explicit sections or bounded query selection including late text, and
rechecks current access before delivering an answer. New sessions capture encrypted
instructional revisions; resumed rendering and session-bound tutor use the same
snapshot. Old sessions remain explicitly unpinned. Additive copy-first upgrade
preserves historical rows and verifies the new ciphertext field.

Evidence: the affected backend gate had 177 passes and six failures, all traced to
one old empty-lesson fixture; it now supplies actual synthetic lesson text. The
73-case temporal/scoring/journey repair scope passes. Canonical/privacy/resource
checks pass separately. UI evidence: 70 DOM-emulation tests and 18 source/style
checks. This is not the final aggregate. Durable extraction provenance, in-class
tutor panel, request lifecycle, portability wizard and operational cleanup remain
active work; native/browser/model/human gates remain open.

## Checkpoint 3: durable sources and in-class help

Source extraction now obeys one character budget including reference labels.
Course-owned encrypted source manifests persist text, byte-hash reports, parser,
sections/pages, omitted pages and extraction coverage. They explicitly exclude the
original binary and distinguish reported extraction from legacy text with unknown
provenance. Teacher packages preserve this manifest; learner exports do not expose
the raw author source. Generation records the actual bounded fragment/hash and
usage coverage separately from extraction coverage; late relevant segments can
be selected. Explicit replacement preserves prior content/history, invalidates
review and marks old generation jobs obsolete; stale-source requests fail.

The session player now has an in-place tutor and teacher-help panel with current
authorization, captured-session binding, section selection, partial-source and
unverified-response disclosures. Dashboard context changes invalidate conversation
and late replies. Unsupported Anthropic options and inactive preprocessing UI/
runtime methods were removed; old saved provider records have actionable errors,
and deprecated settings are ignored with explicit compatibility warnings.

Independent review identified two additional snapshot boundaries. Both were
reproduced before fixing: present-but-unreadable ciphertext must not fall back to
current content, and a session from one course must not masquerade as another
course sharing the same content. The fixed paths return a recovery error or select
the correct course-bound session; restart captures a revision too and closes only
the selected course's prior session without a completion reward.

Evidence: 28 source/generation/session cases pass; 24 settings/session cases pass;
two new restart/unsupported-provider edges pass. The UI worker reports 115 pinned
DOM cases and 18 source/style checks before later bounded refinements. Exact frozen
UI validation is recorded at publication. Limits/receipts/cancellation remain
the next active slice; no remote-provider stop or known-cost claim is made yet.

The frozen serial DOM check exposed an unbounded test fixture: a delayed context
resolver was accidentally replaced by a concurrent usage request. The fixture now
defers only context and has a five-second timeout. The corrected panel and all
remaining role/receipt modules pass **66 tests** in 3.45 seconds. Earlier modules
had passed before the fixture stalled; this record does not invent a completed
aggregate result. Secret scan and critical lint/type checks pass.
