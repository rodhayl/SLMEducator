/* Learner-owned submission reading never reserves a new attempt. */
const historyText = (key, fallback) => SLMClient.message(key, fallback);
const historyEscape = value => SLMRender.escape(value);
const historyId = value => /^\d+$/.test(String(value || '')) && Number.isSafeInteger(Number(value)) && Number(value) > 0 ? Number(value) : null;
let historyOwner = null;
let historySubmissions = [];
let historyListRevision = 0;
let historyDetailRevision = 0;
let selectedSubmissionId = historyId(new URLSearchParams(window.location.search).get('submission_id'));
let selectedAssessmentId = historyId(new URLSearchParams(window.location.search).get('assessment_id'));

function submissionStatus(status) {
    const messages = {
        draft: ['submission_draft', 'Attempt in progress'],
        submitted: ['pending_review', 'Pending teacher review. No final grade yet.'],
        ai_graded: ['pending_review', 'Pending teacher review. No final grade yet.'],
        graded: ['submission_final', 'Final grade'],
        abandoned: ['submission_abandoned', 'Attempt closed without submitting']
    };
    const message = messages[status];
    return message ? historyText(...message) : String(status || '');
}

async function initializeSubmissionHistory() {
    if (!window.AuthService?.isAuthenticated()) {
        window.location.href = '/login.html?redirect=' + encodeURIComponent(window.location.pathname + window.location.search);
        return;
    }
    if (AuthService.getRole() !== 'student') {
        document.getElementById('submission-history-status').textContent = historyText('submission_learner_only', 'This page shows learners their own submissions. Use Grading to review learner work.');
        return;
    }
    historyOwner = SLMClient.account();
    if (window.I18n?.init) await window.I18n.init();
    window.I18n?.translatePage?.();
    await SLMTime.load().catch(() => {});
    document.getElementById('refresh-submissions').onclick = refreshSubmissionHistory;
    await refreshSubmissionHistory();
}

function historyAccountMatches() { return historyOwner !== null && historyOwner === SLMClient.account(); }

async function refreshSubmissionHistory() {
    if (!historyAccountMatches()) return;
    await Promise.all([loadSubmissionHistory(), selectedSubmissionId ? loadLearnerSubmission(selectedSubmissionId, false) : Promise.resolve()]);
}

async function loadSubmissionHistory() {
    const revision = ++historyListRevision;
    const list = document.getElementById('learner-submission-list');
    list.textContent = historyText('loading', 'Loading…');
    try {
        const submissions = await SLMClient.request('/api/assessments/submissions');
        if (revision !== historyListRevision || !historyAccountMatches()) return;
        if (!Array.isArray(submissions)) throw new Error(historyText('submission_load_failed', 'Could not load submissions. Please refresh to retry.'));
        historySubmissions = submissions;
        renderSubmissionHistory();
    } catch (error) {
        if (revision === historyListRevision && historyAccountMatches()) list.textContent = error.message || historyText('submission_load_failed', 'Could not load submissions. Please refresh to retry.');
    }
}

function learnerSubmissionUrl(id) {
    const params = new URLSearchParams({ submission_id: String(id) });
    if (selectedAssessmentId) params.set('assessment_id', selectedAssessmentId);
    return 'assessment_history.html?' + params;
}

function renderSubmissionHistory() {
    const list = document.getElementById('learner-submission-list');
    const submissions = historySubmissions.filter(sub => !selectedAssessmentId || Number(sub.assessment_id) === selectedAssessmentId);
    list.replaceChildren();
    if (!submissions.length) { list.textContent = historyText('submission_empty', 'No submissions yet.'); return; }
    submissions.forEach(sub => {
        const link = document.createElement('a');
        link.className = 'list-group-item list-group-item-action';
        link.href = learnerSubmissionUrl(sub.id);
        if (Number(sub.id) === selectedSubmissionId) { link.classList.add('active'); link.setAttribute('aria-current', 'true'); }
        const heading = document.createElement('h3'); heading.className = 'h6'; heading.textContent = sub.assessment_title;
        const status = document.createElement('p'); status.className = 'mb-1'; status.textContent = submissionStatus(sub.status);
        const date = document.createElement('p'); date.className = 'small mb-1'; date.textContent = SLMTime.format(sub.submitted_at);
        const score = document.createElement('p'); score.className = 'small mb-0';
        score.textContent = sub.status === 'graded' && Number.isFinite(sub.score) ? `${historyText('final_score', 'Final score')}: ${sub.score} / ${sub.total_points ?? '—'}` : '';
        link.append(heading, status, date, score);
        link.onclick = event => {
            if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
            event.preventDefault(); loadLearnerSubmission(sub.id);
        };
        list.append(link);
    });
}

async function loadLearnerSubmission(id, changeUrl = true) {
    id = historyId(id);
    if (!id || !historyAccountMatches()) return;
    selectedSubmissionId = id;
    const revision = ++historyDetailRevision;
    const detail = document.getElementById('learner-submission-detail');
    const heading = document.getElementById('submission-detail-heading');
    heading.textContent = historyText('submission_detail', 'Submission and feedback');
    detail.textContent = historyText('loading', 'Loading…');
    if (changeUrl) window.history.pushState(null, '', learnerSubmissionUrl(id));
    renderSubmissionHistory();
    try {
        const sub = await SLMClient.request(`/api/assessments/submissions/${id}`);
        if (revision !== historyDetailRevision || !historyAccountMatches()) return;
        if (Number(sub?.id) !== id || !Array.isArray(sub.answers)) throw new Error(historyText('submission_detail_failed', 'Could not load this submission. Please retry.'));
        heading.textContent = sub.assessment_title;
        renderLearnerSubmission(sub, detail);
        if (changeUrl) heading.focus();
    } catch (error) {
        if (revision !== historyDetailRevision || !historyAccountMatches()) return;
        detail.textContent = error.message || historyText('submission_detail_failed', 'Could not load this submission. Please retry.');
        const retry = document.createElement('button');
        retry.type = 'button'; retry.className = 'btn btn-outline-primary d-block mt-2';
        retry.textContent = historyText('retry', 'Retry');
        retry.onclick = () => loadLearnerSubmission(id, false);
        detail.append(retry);
    }
}

function renderLearnerSubmission(sub, detail) {
    const final = sub.status === 'graded';
    const closed = sub.status === 'abandoned';
    const label = (key, fallback) => historyEscape(historyText(key, fallback));
    detail.innerHTML = `<p class="fw-bold">${historyEscape(submissionStatus(sub.status))}</p>
        <p>${label('submission_submitted_at', 'Submitted')}: ${historyEscape(SLMTime.format(sub.submitted_at))}</p>
        ${sub.graded_at ? `<p>${label('submission_graded_at', 'Graded')}: ${historyEscape(SLMTime.format(sub.graded_at))}</p>` : ''}
        ${final && Number.isFinite(sub.score) ? `<p class="h5">${label('final_score', 'Final score')}: ${sub.score} / ${historyEscape(sub.total_points ?? '—')}</p>` : ''}
        ${closed ? `<p>${label('attempt_closed_detail', 'This attempt still counts toward your limit. Your unsubmitted answers are saved with this closed attempt and can be read in your history.')}</p>` : `<h3 class="h6">${label('submission_teacher_feedback', 'Teacher feedback')}</h3><p>${historyEscape(sub.feedback || historyText('submission_no_feedback', 'No teacher feedback yet.'))}</p>`}
        ${sub.status === 'draft' ? `<a href="assessment_taker.html?id=${Number(sub.assessment_id)}" class="btn btn-primary mb-3">${label('submission_resume', 'Resume this attempt')}</a>` : ''}
        <h3 class="h5 mt-3">${label('submission_answers', 'Your answers')}</h3>
        ${sub.answers.length ? sub.answers.map((answer, index) => learnerAnswerMarkup(answer, index, final)).join('') : `<p>${label('submission_no_answers', 'No submitted answers.')}</p>`}`;
    if (closed && !sub.answers.length) renderClosedDraft(sub, detail);
}

function learnerAnswerMarkup(answer, index, final) {
    return `<section class="card mb-3"><div class="card-body"><h4 class="h6">${index + 1}. ${historyEscape(answer.question_text)}</h4>
        <p>${historyEscape(answer.given_answer || historyText('submission_unanswered', 'Not answered'))}</p>
        ${final && Number.isFinite(answer.points) ? `<p>${historyEscape(historyText('submission_answer_score', 'Question score'))}: ${answer.points} / ${historyEscape(answer.max_points)}</p>` : ''}
        ${answer.feedback ? `<p><strong>${historyEscape(historyText('submission_teacher_feedback', 'Teacher feedback'))}:</strong> ${historyEscape(answer.feedback)}</p>` : ''}
        ${!final && Number.isFinite(answer.ai_suggested_score) ? `<p>${historyEscape(historyText('submission_ai_provisional', 'AI suggestion, awaiting teacher review'))}: ${answer.ai_suggested_score} / ${historyEscape(answer.max_points)}</p><p>${historyEscape(answer.ai_suggested_feedback || '')}</p>` : ''}
        </div></section>`;
}

function renderClosedDraft(sub, detail) {
    const draft = SLMClient.drafts.read('assessment', sub.assessment_id, sub.id);
    if (!draft?.answers?.length) return;
    const section = document.createElement('section');
    section.className = 'card card-body mt-3';
    const heading = document.createElement('h3'); heading.className = 'h5';
    heading.textContent = historyText('submission_local_answers', 'Unsubmitted answers saved on this device');
    section.append(heading);
    draft.answers.forEach((answer, index) => {
        const paragraph = document.createElement('p');
        paragraph.textContent = `${index + 1}. ${answer.response_text || historyText('submission_unanswered', 'Not answered')}`;
        section.append(paragraph);
    });
    detail.append(section);
}

window.addEventListener('popstate', () => {
    const params = new URLSearchParams(window.location.search);
    selectedAssessmentId = historyId(params.get('assessment_id'));
    selectedSubmissionId = historyId(params.get('submission_id'));
    ++historyDetailRevision;
    renderSubmissionHistory();
    if (selectedSubmissionId) loadLearnerSubmission(selectedSubmissionId, false);
    else document.getElementById('learner-submission-detail').textContent = historyText('submission_select', 'Select a submission to read your answers and feedback.');
});
document.addEventListener('DOMContentLoaded', initializeSubmissionHistory);
