# Small local pilot: evidence before expansion

This is a reproducible synthetic scenario and a proposed evaluation pack. It is
not a completed human pilot or a teacher-approved curriculum. The first external
pilot audience, deployment, subject/level and data/institution authorization must
be chosen separately. Keep real learner information out of evaluation files.

## Reproduce the local scenario

Install runtime dependencies explicitly, then create a new disposable database:

```sh
python scripts/seed_pilot.py --synthetic --database /absolute/new/synthetic.db
```

An existing destination is refused. This uses the same create-only admin seeder
and prints new random credentials once. Keep that terminal output private. The
course content is synthetic, but live installation passwords and keys are secrets.
Set `SLM_DB_PATH` to this path before launching on `127.0.0.1`; never change a real
installation's path accidentally. Matching encryption and JWT keys must be kept
private in the installation's supported environment/key store.

1. Teacher A inspects three lessons and checks the separate assessment's answer,
   explicitly publishes that assessment first, then reviews/publishes the course
   and assigns it to learner A. Linked draft assessments block course publication.
2. Learner A studies, saves notes, refreshes/resumes, practices independently,
   submits the assessment and receives teacher-reviewed feedback.
3. Teacher B and learner B must not read/relink that private course, grade its work
   or read learner A's notes. Keep their enrollment separate.
4. Repeat submit/end, fail a note save, expire a token and switch browser accounts.
   Work must remain recoverable without false success or duplicate rewards.
5. Generate a package with one failed item; retry only that item. Prior saved and
   teacher-edited items must remain. Generation is optional; manual work still works.
6. Export learner material, export/reimport the teacher package, then use a private
   backup to restore into a new path with the matching key. Never overwrite the
   previous installation. A wrong/missing key must fail clearly.

## Record observations

Copy `observation_template.json` outside the repository. Use participant codes,
never names/emails. Record each `evaluation_cases.json` case once with
`case_id`, `acceptable` (true/false), `correction_minutes`, and a concise reason.
Only set `teacher_reviewed` after an educator actually evaluates the outputs.
Use `evidence_mode=synthetic` for scripted data or mocked provider work;
`observed_human_pilot` is reserved for an authorized, actually observed pilot.

Task records require `completed_without_rescue` and may include
`authoring_minutes`, `correction_minutes`, `baseline_minutes`, latency, input
method/language/theme, and an abandonment reason. Keep independent attempts and
teacher-reviewed delayed retrieval separate from time-on-page, confidence or XP.
Record every incident, including zero counts only after observation.

```sh
python scripts/evaluate_pilot.py /path/to/observations.json
```

The proposed gate is all 12 cases observed and teacher reviewed, at least 90%
acceptable and zero critical privacy/grade/work-loss incidents. These thresholds
need educator agreement; a small percentage is not proof of learning efficacy.
The tool never runs a model, pays a provider, transmits records or claims human
acceptance. It reports `awaiting_human_evidence` for mock/incomplete results.

## Technical evidence and pending human observation

The [Windows report](../PRODUCTION_READINESS_WINDOWS_20261005.md) records actual
native builds, password preservation/restart, frozen restoration, Chromium
keyboard/zoom/cache journeys and real native LM Studio inference. Ordinary DOM
and browser fixtures remain explicitly synthetic; they do not certify AI quality.
The final strict real-model rubric accepts 34/36 (23/25 known, 11/11 new reserved).
The remaining cases are an omitted teacher clarification and an educational error
already written in a synthetic source. Previous failures/results remain preserved.
The human pilot is deferred at the user's request; do not ask the participant to
validate these unresolved cases or treat preparation as acceptance.

The configured synthetic pilot contains provider settings for all five accounts,
Spanish source/course/drafts and four separate source-backed courses preserving
historical outputs for review. No participant must configure or install libraries.
The agent opens each relevant screen and changes accounts during an interactive
pilot; this preparation does not constitute human approval or new inference for
the imported failure examples.

Still pending: educator source/definition/answer review and corrections, learner
comprehension/attempts/progressive hints/pause/reload, subjective grading and
feedback, final executable's native Tk X confirmation, assistive-technology and
institution/data-lifecycle review where applicable. An operator usability check
does not substitute for an educator or prove learning efficacy.

Continue, adjust or stop from observed evidence. Do not expand to hosted schools,
LMS integrations, additional providers or consequential automatic grading merely
because this synthetic path succeeds.
