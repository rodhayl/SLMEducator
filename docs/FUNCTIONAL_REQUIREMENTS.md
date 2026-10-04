# Maintained functional contracts

Updated 2026-10-04. The maintained stack is FastAPI, SQLAlchemy/SQLite, HTTPX and
Bootstrap/vanilla JavaScript. Tkinter supplies the Windows launcher only. This
replaces an obsolete desktop-UI inventory; old module paths and configuration
flags are not supported just because historical documentation mentioned them.

The supported evaluation is one local process with synthetic adult accounts.
Implementation, regression evidence and real-world acceptance are separate. See
[the approved plan](../implementation_documents/PRODUCT_CLOSURE_PLAN.md) and
[the validation record](../implementation_documents/LEARNING_LOOP_VALIDATION.md).

## Accounts and private information

- Create-only bootstrap uses `scripts/seed_admin.py`; existing account security
  state is preserved. Account creation requires administration or a teacher.
  Teachers create their own learners; learners cannot self-create staff accounts.
- Administration manages explicit enrollment, account status and password recovery.
  Recovery revokes old sessions and preserves audit history. Self-deactivation
  and removal of the last active administrator are refused.
- Teachers access enrolled learners, authored assessments and authorized content.
  Administration has installation scope; learners access their own assigned work.
  Legacy assignment compatibility cannot override another explicit enrollment.
- Annotations are private by default. Sharing reaches the enrolled teacher and
  administration, not classmates. Drafts are account/attempt-scoped.

Sources: `src/api/policies.py`, `src/api/routes/auth.py`, `students.py`,
`annotations.py`, `src/core/services/auth.py`. These controls do not establish
security certification, child suitability or regulatory compliance.

## Prepare, review, publish and assign

- Teachers create/edit courses, lessons and practice with or without AI. Canonical
  sections, objectives, vocabulary, references and order are checked before writes.
- Assessment content points to executable assessments. Inline exams containing
  hidden grading assets are rejected; low-stakes practice self-checks are separate.
- Review includes linked assessment definitions. Publication/assignment requires
  usable published assessments. Changes invalidate the review identity.
- Assigned material is immutable. Revisions are separate draft copies with lineage;
  they never silently replace existing learner work.
- Generation persists per-item status. Partial failure, retry and cancellation
  preserve teacher edits rather than claim all items succeeded.

Sources: `src/core/services/content_schema.py`, `course_workflow.py`,
`generation_workflow.py`, and `src/api/routes/content.py`, `study_plans.py`,
`assessment.py`, `generation.py`. Authoring uses `src/web/course_designer.html`,
`study_plan_builder.html`, `assessment_builder.html` and their JavaScript modules.

## Study, attempts and feedback

- New sessions capture instructional revisions; session rendering and tutoring use
  the same snapshot. Legacy sessions are explicitly unpinned. Unreadable captured
  content causes a recovery error rather than substitution with newer material.
- Complete/Next use retry-safe completion; Previous/Pause preserve notes without
  completion. Continue selects pending content. Restart preserves history, closes
  only the selected course's prior session and grants no completion reward.
- Attempts are bounded and replay-safe. Explicit closure preserves answers and
  consumes the reserved attempt without producing a grade or reward.
- Objective scoring validates keys. Subjective AI grades remain provisional until
  teacher review. Provider failure never becomes a final zero.
- Teachers open submissions from a grading queue; learners read correction feedback
  without reserving new attempts. A real zero remains zero.
- Participation/XP, self-reported confidence and assessed evidence are distinct.
  Review heuristics are not validated measures of learning improvement.

Sources: `src/api/routes/learning.py`, `assessment.py`, `mastery.py`,
`src/core/services/assessed_review.py`, `learning_session_service.py`, and
`src/web/session_player.html`, `grading.html`, `assessment_history.html`,
`assessment_taker.html`. See the three-lesson and product-journey trust tests.

## Optional AI and source provenance

- Supported providers are Ollama, LM Studio, OpenAI and OpenRouter. Unsupported
  saved providers require explicit repair. Retired preprocessing settings have
  compatibility warnings. Saved keys are never returned to the browser.
- PDF/TXT/Markdown extraction uses one bounded text budget and records hash,
  parser, sections/pages, omissions and coverage. Original binaries, external
  media and OCR are excluded. Unknown historical provenance stays unknown.
- Encrypted course-owned manifests distinguish extraction coverage from the actual
  generation fragment/hash and usage coverage. Source replacement preserves prior
  material/provenance, invalidates review and marks obsolete generation work.
- Tutor/help panels expose lesson context and section selection. Authorization,
  source revision and the strictest open-attempt assistance policy apply before
  delivery. Context changes invalidate stale conversation work.
- Responses are unverified suggestions. Source references do not prove correctness.
  Lessons, notes and teacher help remain usable if AI is unavailable.
- Tutor/Q&A permits one active request per account, 100 starts per UTC day and a
  90-second local delivery deadline. Cancelled/timed-out providers may continue
  working and charging; a busy slot remains until the call returns. Receipts report
  known tokens; monetary cost stays unknown. This is single-process policy, not a
  distributed queue or configurable monetary budget.

Sources: `src/api/routes/ai.py`, `settings.py`, `upload.py`, and
`src/core/services/learning_context.py`, `source_documents.py`,
`ai_request_lifecycle.py`, `ai_service.py`. See [assistance policy](ASSISTANCE_POLICY.md)
and [operating limits](AI_REQUESTS_AND_OPERATIONS.md). Mocked tests do not validate
real-model correctness, educational value, latency or provider cancellation.

## Portability and recovery

- Preview precedes export/import. Learner HTML/Markdown/JSON retains readable
  sections and vocabulary, omitting hidden keys/rubrics and raw teacher source.
  HTML is inert escaped text without external assets.
- Teacher course JSON v2 contains a validated ordered graph and provenance. V1
  remains accepted as a new private draft; future versions fail before writes.
  IDs are remapped and publication authority is never imported.
- Learner reading formats do not restore teacher courses. Teacher packages contain
  grading assets and should be shared only with intended instructors.
- Private encrypted backup is separate. Restore uses a new destination and the
  matching separately held key. Keys, configuration and external uploads are not
  included. Additive upgrades are copy-first and preserve the original database.
- New times retain UTC offsets, using an explicit IANA setting or UTC default.
  Unknown historical times remain labelled; migration needs a known source zone,
  selected fields and a preserved backup.

Sources: `src/api/routes/portability.py`, `src/core/services/portability_service.py`,
`recovery_service.py`, `schema_migrations.py`, `temporal_migration.py`,
`temporal_service.py`. See [portability and recovery](PORTABILITY_RECOVERY.md).

## Setup, packaging and acceptance

- Installation is explicit; launch never installs/upgrades dependencies. Runtime
  and test requirements are separate. Browser assets are local, pinned and hashed.
- Packaging uses isolated staging and new output directories. Production creates
  a new database; test mode requires an explicit synthetic SQLite source. Working
  databases/configuration are never silently reset or included.
- Synthetic CI excludes manual, existing-server browser and real-provider suites.
  It disables provider discovery and fails closed on real HTTP transports, then
  runs API/service checks and serial DOM regressions. Dependency installation
  still requires package-registry access.
- Native Windows build/start/login/restart/recovery, live-browser keyboard/screen
  reader/zoom/bilingual journeys, model quality and human pilot remain separate
  acceptance gates. Linux freezer mocks and DOM emulation cannot close them.
- No shared-host deployment, multi-process quota guarantee or educational efficacy
  claim is part of this implementation.

Procedures: `scripts/build_package.py`, `.github/workflows/offline-tests.yml`,
`tests/ui/README.md`, [browser scenarios](BROWSER_TEST.md),
[pilot tooling](pilot/README.md).
