/* Grading reuses the authorized submission APIs and preserves queue navigation. */
const gradingFallbacks = {
    'grading.access_denied': 'Grading is only available to teachers and administrators.',
    'grading.grade_saved': 'Grade saved.',
    'grading.labels.student_answer': 'Student answer',
    'grading.labels.correct_answer': 'Correct answer',
    'grading.labels.ai_suggestion': 'AI suggestion',
    'grading.labels.feedback': 'Feedback',
    'grading.labels.score': 'Score',
    'grading.labels.optional_feedback': 'Optional feedback',
    'grading.labels.pts': 'pts',
    'grading.buttons.accept': 'Accept',
    'grading.buttons.modify': 'Edit score',
    'grading.buttons.save': 'Save',
    'grading.messages.no_answer': 'No answer',
    'grading.messages.no_answer_data': 'No answers found.',
    'grading.messages.error_loading_details': 'Could not load this submission. Select it again to retry.',
    'grading.messages.error_loading_submissions': 'Could not load submissions. Please refresh to retry.',
    'grading.empty_state': 'No submissions match this filter.',
    'grading.status.submitted': 'Pending review',
    'grading.status.ai_graded': 'AI suggestions: pending teacher review',
    'grading.status.graded': 'Final grade',
    'common.labels.loading': 'Loading…'
};
const t = (key, params = {}) => {
    const translated = window.I18n?.t?.(key, params);
    return translated && translated !== key ? translated : gradingFallbacks[key] || key;
};
const gradingText = (key, fallback) => SLMClient.message(key, fallback);
const gradingEscape = value => SLMRender.escape(value);
const gradingId = value => /^\d+$/.test(String(value || '')) && Number.isSafeInteger(Number(value)) && Number(value) > 0 ? Number(value) : null;
const gradingFilter = value => ['all', 'pending', 'graded'].includes(value) ? value : 'all';
let currentSubmissionId = gradingId(new URLSearchParams(window.location.search).get('submission_id'));
let currentSubmissionData = null;
let allSubmissions = [];
let currentStatusFilter = gradingFilter(new URLSearchParams(window.location.search).get('filter'));
let gradingDetailRevision = 0;
let gradingListRevision = 0;
let gradingSaving = false;

function checkAuth() {
    if (!window.AuthService?.isAuthenticated()) {
        window.location.href = '/login.html?redirect=' + encodeURIComponent(window.location.pathname + window.location.search);
        return false;
    }
    if (!['teacher', 'admin'].includes(AuthService.getRole())) {
        document.getElementById('grading-placeholder').textContent = t('grading.access_denied');
        return false;
    }
    return true;
}

async function initializeGrading() {
    if (!checkAuth()) return;
    if (!window.I18n?.loaded) await window.I18n?.init?.();
    window.I18n?.translatePage?.();
    updateGradingNavigation();
    document.getElementById('grading-form').onsubmit = event => { event.preventDefault(); submitGrade(); };
    await SLMTime.load().catch(() => {});
    await Promise.all([loadSubmissions(), currentSubmissionId ? loadSubmissionDetails(currentSubmissionId) : Promise.resolve()]);
}

document.addEventListener('DOMContentLoaded', initializeGrading);
window.addEventListener('popstate', () => {
    const params = new URLSearchParams(window.location.search);
    currentStatusFilter = gradingFilter(params.get('filter'));
    const id = gradingId(params.get('submission_id'));
    currentSubmissionId = id;
    updateGradingNavigation();
    applyCurrentFilter();
    if (id) selectSubmission({ id }, false);
    else {
        ++gradingDetailRevision; currentSubmissionData = null;
        document.getElementById('grading-area').classList.add('hidden');
        document.getElementById('grading-placeholder').classList.remove('hidden');
    }
});

function updateGradingNavigation() {
    const back = document.getElementById('grading-dashboard-link');
    back.href = `dashboard.html?view=grading&grading_filter=${currentStatusFilter}`;
    document.querySelectorAll('#grading-filter-tabs button').forEach(button => {
        const active = button.dataset.filter === currentStatusFilter;
        button.classList.toggle('active', active);
        button.setAttribute('aria-pressed', String(active));
    });
}

function syncGradingUrl() {
    const url = new URL(window.location.href);
    url.searchParams.set('filter', currentStatusFilter);
    if (currentSubmissionId) url.searchParams.set('submission_id', currentSubmissionId);
    else url.searchParams.delete('submission_id');
    window.history.replaceState(null, '', url.pathname + url.search);
}

async function loadSubmissions() {
    if (!checkAuth()) return;
    const revision = ++gradingListRevision;
    const list = document.getElementById('submission-list');
    list.textContent = t('common.labels.loading');
    try {
        const submissions = await SLMClient.request('/api/assessments/submissions?status=submitted&status=graded&status=ai_graded');
        if (revision !== gradingListRevision) return;
        if (!Array.isArray(submissions)) throw new Error(t('grading.messages.error_loading_submissions'));
        allSubmissions = submissions;
        applyCurrentFilter();
    } catch (error) {
        if (revision === gradingListRevision) list.textContent = error.message || t('grading.messages.error_loading_submissions');
    }
}

function filterSubmissions(status) {
    currentStatusFilter = gradingFilter(status);
    updateGradingNavigation();
    syncGradingUrl();
    applyCurrentFilter();
}

function applyCurrentFilter() {
    const filtered = allSubmissions.filter(sub => currentStatusFilter === 'pending' ?
        ['submitted', 'ai_graded'].includes(sub.status) : currentStatusFilter === 'graded' ? sub.status === 'graded' : true);
    renderList(filtered);
}

function renderList(submissions) {
    const list = document.getElementById('submission-list');
    list.replaceChildren();
    if (!submissions.length) { list.textContent = t('grading.empty_state'); return; }
    const template = document.getElementById('submission-item-template');
    submissions.forEach(sub => {
        const clone = template.content.cloneNode(true);
        const link = clone.querySelector('a');
        link.href = `grading.html?submission_id=${Number(sub.id)}&filter=${currentStatusFilter}`;
        link.classList.toggle('active', Number(sub.id) === currentSubmissionId);
        if (Number(sub.id) === currentSubmissionId) link.setAttribute('aria-current', 'true');
        link.onclick = event => {
            if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
            event.preventDefault(); selectSubmission(sub);
        };
        clone.querySelector('.student-name').textContent = sub.student_name;
        clone.querySelector('.assessment-title').textContent = sub.assessment_title;
        clone.querySelector('.submission-date').textContent = SLMTime.format(sub.submitted_at, { dateOnly: true });
        const badge = clone.querySelector('.status-badge');
        badge.textContent = getStatusLabel(sub.status);
        badge.className = 'status-badge badge ' + getStatusBadgeClass(sub.status);
        list.append(clone);
    });
}

function getStatusLabel(status) { return t(`grading.status.${status}`); }
function getStatusBadgeClass(status) {
    return { submitted: 'bg-warning text-dark', ai_graded: 'bg-info text-dark', graded: 'bg-success' }[status] || 'bg-secondary';
}

async function selectSubmission(sub, syncUrl = true) {
    const id = gradingId(sub.id);
    if (!id || gradingSaving) return;
    currentSubmissionId = id;
    if (syncUrl) syncGradingUrl();
    applyCurrentFilter();
    await loadSubmissionDetails(id);
}

function setGradingControlsDisabled(disabled) {
    document.querySelectorAll('#grading-area button, #grading-area input, #grading-area textarea').forEach(control => { control.disabled = disabled; });
}

async function loadSubmissionDetails(id) {
    if (!checkAuth()) return;
    const revision = ++gradingDetailRevision;
    currentSubmissionId = Number(id);
    currentSubmissionData = null;
    document.getElementById('grading-placeholder').classList.add('hidden');
    document.getElementById('grading-area').classList.remove('hidden');
    document.getElementById('submission-title').textContent = t('common.labels.loading');
    document.getElementById('submission-status').textContent = '';
    document.getElementById('ai-actions').classList.add('hidden');
    document.getElementById('grade-score').value = '';
    document.getElementById('grade-feedback').value = '';
    const container = document.getElementById('answers-container');
    container.textContent = t('common.labels.loading');
    setGradingControlsDisabled(true);
    try {
        const sub = await SLMClient.request(`/api/assessments/submissions/${Number(id)}`);
        if (revision !== gradingDetailRevision) return;
        if (Number(sub?.id) !== Number(id) || !Array.isArray(sub.answers)) throw new Error(t('grading.messages.error_loading_details'));
        currentSubmissionData = sub;
        document.getElementById('submission-title').textContent = `${sub.student_name} · ${sub.assessment_title}`;
        const badge = document.getElementById('submission-status');
        badge.textContent = getStatusLabel(sub.status);
        badge.className = 'badge ' + getStatusBadgeClass(sub.status);
        renderAnswers(sub, container);
        document.getElementById('ai-actions').classList.toggle('hidden', sub.status !== 'ai_graded');
        document.getElementById('ai-summary').textContent = gradingText('grading_ai_provisional', 'AI scores are suggestions until you approve them.');
        document.getElementById('grade-score').value = sub.score ?? '';
        document.getElementById('grade-score').max = sub.total_points ?? 0;
        document.getElementById('grade-feedback').value = sub.feedback || '';
        setGradingControlsDisabled(!['submitted', 'ai_graded', 'graded'].includes(sub.status));
        document.getElementById('submission-title').focus();
    } catch (error) {
        if (revision === gradingDetailRevision) container.textContent = error.message || t('grading.messages.error_loading_details');
    }
}

function renderAnswers(sub, container) {
    if (!sub.answers.length) { container.textContent = t('grading.messages.no_answer_data'); return; }
    container.innerHTML = sub.answers.map((answer, index) => {
        const id = Number(answer.response_id);
        const ai = Number.isFinite(answer.ai_suggested_score);
        return `<section class="card mb-3" data-response-id="${id}"><div class="card-header">
            <h3 class="h6">${index + 1}. ${gradingEscape(answer.question_text)}</h3>
            <span>${gradingEscape(answer.points ?? '—')} / ${gradingEscape(answer.max_points)} ${gradingEscape(t('grading.labels.pts'))}</span></div>
            <div class="card-body"><p><strong>${gradingEscape(t('grading.labels.student_answer'))}:</strong> ${gradingEscape(answer.given_answer || t('grading.messages.no_answer'))}</p>
            ${answer.correct_answer ? `<p><strong>${gradingEscape(t('grading.labels.correct_answer'))}:</strong> ${gradingEscape(answer.correct_answer)}</p>` : ''}
            ${answer.feedback ? `<p><strong>${gradingEscape(t('grading.labels.feedback'))}:</strong> ${gradingEscape(answer.feedback)}</p>` : ''}
            ${ai ? `<div class="border rounded p-2 mb-2"><p>${gradingEscape(t('grading.labels.ai_suggestion'))}: ${gradingEscape(answer.ai_suggested_score)} / ${gradingEscape(answer.max_points)}</p><p>${gradingEscape(answer.ai_suggested_feedback || '')}</p><button type="button" class="btn btn-outline-success btn-sm" data-grade-action="accept" data-response-id="${id}">${gradingEscape(t('grading.buttons.accept'))}</button></div>` : ''}
            <button type="button" class="btn btn-outline-secondary btn-sm" data-grade-action="edit" data-response-id="${id}" aria-controls="manual-grade-${id}" aria-expanded="false">${gradingEscape(t('grading.buttons.modify'))}</button>
            <div class="manual-grade-input mt-3 hidden" id="manual-grade-${id}">
                <label for="score-${id}" class="form-label">${gradingEscape(t('grading.labels.score'))}</label>
                <input type="number" class="form-control" id="score-${id}" min="0" step="1" max="${Number(answer.max_points)}" value="${answer.points ?? ''}">
                <label for="feedback-${id}" class="form-label">${gradingEscape(t('grading.labels.optional_feedback'))}</label>
                <textarea class="form-control mb-2" id="feedback-${id}">${gradingEscape(answer.feedback || '')}</textarea>
                <button type="button" class="btn btn-primary btn-sm" data-grade-action="save" data-response-id="${id}">${gradingEscape(t('grading.buttons.save'))}</button>
            </div></div></section>`;
    }).join('');
    container.querySelectorAll('[data-grade-action]').forEach(button => {
        button.onclick = () => {
            const id = Number(button.dataset.responseId);
            if (button.dataset.gradeAction === 'edit') toggleManualGrade(id);
            else if (button.dataset.gradeAction === 'save') submitQuestionGrade(id);
            else acceptSingleAiGrade(id, sub.answers.find(answer => Number(answer.response_id) === id).ai_suggested_score);
        };
    });
}

function toggleManualGrade(responseId) {
    const input = document.getElementById(`manual-grade-${responseId}`);
    input.classList.toggle('hidden');
    const button = document.querySelector(`[data-grade-action="edit"][data-response-id="${responseId}"]`);
    button.setAttribute('aria-expanded', String(!input.classList.contains('hidden')));
    if (!input.classList.contains('hidden')) document.getElementById(`score-${responseId}`).focus();
}

async function saveGradingChange(path, body) {
    if (!currentSubmissionData || gradingSaving || !checkAuth()) return;
    gradingSaving = true;
    setGradingControlsDisabled(true);
    const id = currentSubmissionId;
    try {
        const result = await SLMClient.request(`/api/assessments/submissions/${id}${path}`, {
            method: 'POST', ...(body === undefined ? {} : { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
        });
        if (result?.status !== 'ok') throw new Error(gradingText('grading_save_unconfirmed', 'The server could not confirm the grade was saved. Review your inputs and retry.'));
        showToast(t('grading.grade_saved'), 'success');
        await Promise.all([loadSubmissionDetails(id), loadSubmissions()]);
    } catch (error) { showToast(error.message, 'danger'); }
    finally { gradingSaving = false; setGradingControlsDisabled(!currentSubmissionData || !['submitted', 'ai_graded', 'graded'].includes(currentSubmissionData.status)); }
}

function validGrade(input) {
    if (!input.value.trim() || !Number.isInteger(Number(input.value)) || !input.checkValidity()) {
        input.setCustomValidity(gradingText('grading_invalid_score', 'Enter a whole-number score within the allowed range.'));
        input.reportValidity(); input.setCustomValidity(''); input.focus(); return false;
    }
    return true;
}

function acceptSingleAiGrade(responseId, suggestedScore) {
    const answer = currentSubmissionData?.answers.find(item => Number(item.response_id) === Number(responseId));
    return saveGradingChange(`/responses/${responseId}/grade`, { score: suggestedScore, feedback: answer?.ai_suggested_feedback || null });
}
function submitQuestionGrade(responseId) {
    const score = document.getElementById(`score-${responseId}`);
    if (!validGrade(score)) return;
    return saveGradingChange(`/responses/${responseId}/grade`, { score: Number(score.value), feedback: document.getElementById(`feedback-${responseId}`).value || null });
}
function acceptAllAiGrades() { return saveGradingChange('/accept-ai'); }
function submitGrade() {
    const score = document.getElementById('grade-score');
    if (!validGrade(score)) return;
    return saveGradingChange('/grade', { score: Number(score.value), feedback: document.getElementById('grade-feedback').value });
}
