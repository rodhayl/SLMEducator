# Teacher-controlled assistance during assessments

Each assessment has a teacher-owned assistance setting:

- `hints_only` (default): the server selects hint mode and instructs the provider
  not to solve the assessment. The learner UI disables explanation/example modes.
- `explanations`: normal hint, explanation, example and understanding-check modes.
- `disabled`: no tutor or Q&A provider call is made while the attempt is open.

The scope is an **open assessment attempt** (`draft` submission), not all study
activity. When more than one attempt is open, the most restrictive rule wins.
Submitting an attempt releases that active-attempt restriction; teacher feedback
and final/provisional grades are a separate workflow. This does not control other
websites, copying material before an attempt, or what a model independently knows.

Only the assessment author or an administrator can change the setting. Learners
cannot override it through request fields or by omitting content/course context.
The server checks the current policy before a provider call and again before
returning its answer. A stricter teacher change can therefore prevent delivery
of an in-flight response. The already-running provider call may still finish;
this cannot retract input already sent under the prior policy.

Hint mode is a requested model behavior, not a guarantee of semantic compliance.
No hidden assessment answer keys are placed in the tutor's lesson context. Model
output remains an unverified suggestion, and consequential grades still require
teacher review. Real-model/educator evaluation is required before claiming that
hints reliably satisfy the chosen teaching policy.

## UI and persistence

The assessment builder loads/saves the policy separately from immutable assigned
assessment definitions. Policy load/save failure blocks publication and preserves
the selection for retry; a retry reuses the saved assessment ID. The learner tutor
shows the effective mode and offers refresh when an attempt was completed in a
different tab. A disabled request retains the learner's unsent question.

Settings use the existing author's per-user settings record. Only the mode is
included in a course package; no account records or credentials are exported.
Teacher package import maps the mode to the newly created assessment under the
new author, still as an unpublished draft.

## API

- `GET /api/assessments/{id}/assistance-policy`: authorized learner or owner
- `PUT /api/assessments/{id}/assistance-policy`, body `{"mode":"hints_only"}`:
  assessment author/administrator only
- `GET /api/ai/assistance-policy`: effective mode for the signed-in user

Responses identify `scope=active_attempt`. Tutor responses include the effective
policy object and selected assistance mode; source references/coverage remain
separate and never imply the generated answer has been verified.

Deterministic tests cover ownership, multiple routes, omitted context, teacher
policy changes on a separate database session, mode coercion, preserved settings
and export/import. UI behavior tests use DOM emulation; live-browser and real-model
acceptance remain separate.
