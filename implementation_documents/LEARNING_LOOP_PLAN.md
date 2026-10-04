# Trustworthy learning loop: implementation contract

## Supported scenario

One local installation, two synthetic teachers and two synthetic adult learners,
with a three-lesson fractions course: equal parts, comparing common denominators,
and independent retrieval. Teacher A owns the course and learner A; teacher B and
learner B are negative authorization fixtures. No real learner data, paid/model
inference, network exposure, automated consequential grades, or deployment.

The loop is prepare → review → publish → assign → study/resume → attempt →
teacher-reviewed feedback. Participation/XP and self-reported confidence are not
learning-outcome measures. Invalid AI output is a review state, never a final zero.

## Resource policy

| Resource/action | Administrator | Teacher | Learner |
| --- | --- | --- | --- |
| Create accounts | Approved roles | Own learners only | Denied |
| Private course/material | Installation-wide | Author | Assigned authorized content |
| Reuse material | Allowed | Own or author-public nonpersonal material | Denied |
| Roster/progress/help | Installation-wide | Explicit enrollment; legacy unclaimed assignment compatibility | Own |
| Submission/grade | Installation-wide | Assessment author | Own submission; no grading |
| Contacts | Installation-wide | Enrolled learners and admin | Enrolled teacher and admin |
| Notes/drafts | Account-scoped | Account-scoped | Account-scoped |

A foreign private link, including an old unsafe association, cannot grant content
access. Enrollment is User.teacher_id. Existing assignments provide compatibility
only for learners without a teacher_id; they do not override another enrollment.
The create-only bootstrap remains the only unauthenticated account provisioning
path; the public registration API cannot create unapproved staff.

## Phases and evidence

0. Reproducible synthetic fixture and this explicit boundary.
1. Authorization, prompt grounding, validated scoring/retries, password/settings,
   safe rendering, truthful HTTP feedback and account-separated recovery.
2. Canonical learning content, draft/review/publication, immutable assigned material,
   resumable per-item generation and maintained accessible screens.
3. Source references/coverage, typed provider failures, usable non-AI path and
   a teacher-scored evaluation pack. Mocked responses do not establish model quality.
4. Audience-specific portability, recoverable copy/restore and upgrade preflight;
   explicit setup and pinned local assets. Preserve isolated packaging safety.
5. Pilot/evaluation recording and evidence-based continuation gate, not invented
   participant results or educational efficacy.

## Verification boundary

Run individual/affected tests while working; every pytest call has a unique
project-scoped --basetemp. Run one applicable full gate after the implementation
stabilizes. Native Windows, live model quality, screen-reader/keyboard acceptance,
real human pilot and any institution/minors review remain separate evidence.
No person/environment is claimed to have accepted these gates without observation.
