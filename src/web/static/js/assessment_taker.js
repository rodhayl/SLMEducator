let currentAssessment = null;
let currentAttempt = null;
let assessmentOwner = null;
let timerInterval = null;
let isReviewMode = false;
let submitting = false;
let submitted = false;
const assessmentMessage = (key, fallback) => SLMClient.message(key, fallback);

function showErrorState(title, message) {
    const overlay = document.getElementById('error-overlay');
    overlay.querySelector('.error-title').textContent = title;
    overlay.querySelector('.error-text').textContent = message;
    overlay.classList.remove('d-none');
    document.getElementById('question-container').classList.add('d-none');
}

async function loadAssessment() {
    const id = new URLSearchParams(window.location.search).get('id');
    if (!id || !/^\d+$/.test(id)) {
        showErrorState('Assessment unavailable', 'Open this assessment from your library.');
        return;
    }
    assessmentOwner = SLMClient.account();
    if (!assessmentOwner || !AuthService.isAuthenticated()) {
        window.location.href = '/login.html?redirect=' + encodeURIComponent(window.location.pathname + window.location.search);
        return;
    }
    try {
        currentAssessment = await SLMClient.request(`/api/assessments/${id}`);
        currentAttempt = await SLMClient.request(`/api/assessments/${id}/start`, { method: 'POST' });
        if (!currentAttempt?.submission_id) throw new Error('The server did not provide an assessment attempt. Please retry.');
        renderAssessment(currentAssessment);
        if (!await loadProgress()) return;
        setupAutosave();
        startTimer();
    } catch (error) {
        showErrorState('Assessment unavailable', error.message);
    }
}

function renderAssessment(assessment) {
    document.getElementById('assessment-title').textContent = assessment.title;
    document.getElementById('assessment-desc').textContent = assessment.description || '';
    const container = document.getElementById('questions-container');
    container.replaceChildren();
    assessment.questions.forEach((question, index) => {
        const card = document.createElement('fieldset');
        card.className = 'question-card mb-4 p-3 border rounded';
        const legend = document.createElement('legend');
        legend.className = 'h5';
        legend.textContent = `${assessmentMessage('question', 'Question')} ${index + 1} (${question.points} pts)`;
        const text = document.createElement('p');
        text.className = 'lead';
        text.id = `question-text-${question.id}`;
        text.textContent = question.question_text;
        card.append(legend, text, renderInput(question));
        container.append(card);
    });
}

function renderInput(question) {
    const container = document.createElement('div');
    container.className = 'answer-input';
    if (['multiple_choice', 'true_false'].includes(question.question_type)) {
        let choices = question.options?.choices || question.options || [];
        if (!Array.isArray(choices)) choices = Object.values(choices);
        if (!choices.length && question.question_type === 'true_false') choices = ['True', 'False'];
        choices.forEach((choice, index) => {
            const row = document.createElement('div');
            row.className = 'form-check';
            const input = document.createElement('input');
            input.className = 'form-check-input';
            input.type = 'radio';
            input.name = `q_${question.id}`;
            input.id = `q_${question.id}_${index}`;
            input.value = String(choice);
            const label = document.createElement('label');
            label.className = 'form-check-label';
            label.htmlFor = input.id;
            label.textContent = String(choice);
            row.append(input, label);
            container.append(row);
        });
    } else {
        const input = document.createElement('textarea');
        input.className = 'form-control';
        input.name = `q_${question.id}`;
        input.rows = 3;
        input.setAttribute('aria-labelledby', `question-text-${question.id}`);
        container.append(input);
    }
    return container;
}

function startTimer() {
    if (timerInterval) clearInterval(timerInterval);
    const timer = document.getElementById('assessment-timer');
    // The server owns the deadline; refresh never grants another time limit.
    if (currentAssessment.time_limit_minutes && currentAttempt.timing_provenance === 'legacy_unknown') {
        timer.textContent = assessmentMessage('timer_unknown', 'Timer timezone unknown; teacher review required.');
        return;
    }
    if (!currentAssessment.time_limit_minutes || !currentAttempt.expires_at) {
        timer.textContent = assessmentMessage('no_limit', 'No time limit');
        return;
    }
    const rawDeadline = currentAttempt.expires_at;
    const deadline = SLMTime.epoch(rawDeadline, currentAttempt.timing_provenance);
    if (deadline === null) {
        timer.textContent = assessmentMessage('timer_unknown', 'Timer timezone unknown; teacher review required.');
        return;
    }
    const tick = () => {
        const remaining = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
        timer.textContent = `${Math.floor(remaining / 60).toString().padStart(2, '0')}:${(remaining % 60).toString().padStart(2, '0')}`;
        timer.classList.toggle('text-danger', remaining <= 300);
        if (remaining === 0) {
            clearInterval(timerInterval);
            window.submitAssessment();
        }
    };
    timerInterval = setInterval(tick, 1000);
    tick();
}

function collectAnswers() {
    return currentAssessment.questions.map(question => {
        const inputs = document.getElementsByName(`q_${question.id}`);
        const selected = Array.from(inputs).find(input => input.type !== 'radio' || input.checked);
        return { question_id: question.id, response_text: selected?.value || '' };
    });
}

function showDraftStatus(message, failed = false) {
    const indicator = document.getElementById('autosave-indicator');
    indicator.classList.remove('d-none');
    indicator.classList.toggle('text-danger', failed);
    document.getElementById('autosave-status').textContent = message;
}

function saveProgress() {
    if (!currentAssessment || !currentAttempt || submitted || assessmentOwner !== SLMClient.account()) return false;
    const saved = SLMClient.drafts.write('assessment', currentAssessment.id, currentAttempt.submission_id,
        { answers: collectAnswers(), savedAt: new Date().toISOString() });
    showDraftStatus(saved ? assessmentMessage('local_draft', 'Draft saved on this device; not submitted.') :
        assessmentMessage('storage_failed', 'Could not save a local draft. Keep this page open and retry.'), !saved);
    return saved;
}

async function loadProgress() {
    const draft = SLMClient.drafts.read('assessment', currentAssessment.id, currentAttempt.submission_id);
    if (!draft?.answers?.length) return true;
    const choice = await SLMClient.chooseDraft();
    if (choice === 'discard') { clearProgress(); return true; }
    if (choice !== 'restore') { window.location.href = '/dashboard.html'; return false; }
    draft.answers.forEach(answer => {
        Array.from(document.getElementsByName(`q_${answer.question_id}`)).forEach(input => {
            if (input.type === 'radio') input.checked = input.value === answer.response_text;
            else input.value = answer.response_text;
        });
    });
    showDraftStatus(assessmentMessage('restored', 'Draft restored on this device.'));
    return true;
}

function clearProgress() {
    if (assessmentOwner === SLMClient.account()) SLMClient.drafts.remove('assessment', currentAssessment.id, currentAttempt.submission_id);
}

function setupAutosave() {
    const container = document.getElementById('questions-container');
    container.addEventListener('input', saveProgress);
    container.addEventListener('change', saveProgress);
    window.addEventListener('pagehide', saveProgress);
}

window.submitAssessment = async () => {
    if (!currentAssessment || !currentAttempt || submitting || submitted) return;
    if (assessmentOwner !== SLMClient.account()) {
        showDraftStatus(assessmentMessage('account_changed', 'The signed-in account changed. Reload before continuing.'), true);
        return;
    }
    saveProgress();
    submitting = true;
    const buttons = document.querySelectorAll('#answer-buttons button, #review-buttons button');
    buttons.forEach(button => { button.disabled = true; });
    try {
        const result = await SLMClient.request(`/api/assessments/${currentAssessment.id}/submit`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ submission_id: currentAttempt.submission_id, answers: collectAnswers() })
        });
        if (!result || Number(result.submission_id) !== Number(currentAttempt.submission_id) ||
            !['submitted', 'ai_graded', 'graded'].includes(result.status)) {
            throw new Error(assessmentMessage('failed', 'The server could not confirm your submission. Your draft is kept. Please retry.'));
        }
        submitted = true;
        clearInterval(timerInterval);
        clearProgress();
        document.querySelectorAll('#questions-container input, #questions-container textarea').forEach(input => { input.disabled = true; });
        const results = document.getElementById('results');
        results.replaceChildren();
        const heading = document.createElement('h3');
        heading.textContent = assessmentMessage('submitted', 'Submission received');
        const feedback = document.createElement('p');
        feedback.textContent = result.status === 'graded' && result.score !== null ?
            `${assessmentMessage('final_score', 'Final score')}: ${result.score} / ${result.total_points ?? currentAssessment.questions.reduce((sum, q) => sum + q.points, 0)}` :
            assessmentMessage('pending_review', 'Pending teacher review. No final grade yet.');
        const link = document.createElement('a');
        link.className = 'btn btn-primary'; link.href = '/dashboard.html';
        link.textContent = assessmentMessage('dashboard', 'Back to Dashboard');
        results.append(heading, feedback, link);
        results.classList.remove('d-none');
        results.tabIndex = -1;
        results.focus();
        ['answer-buttons', 'review-buttons', 'autosave-indicator'].forEach(id => document.getElementById(id).classList.add('d-none'));
    } catch (error) {
        showDraftStatus(error.message, true);
        showToast(error.message, 'danger');
    } finally {
        submitting = false;
        if (!submitted) buttons.forEach(button => { button.disabled = false; });
    }
};

window.showReviewMode = () => {
    if (!currentAssessment || submitted) return;
    isReviewMode = true;
    document.querySelectorAll('#questions-container input, #questions-container textarea').forEach(input => { input.disabled = true; });
    const answers = collectAnswers();
    document.querySelectorAll('.question-card').forEach((card, index) => {
        let status = card.querySelector('.answer-status');
        if (!status) { status = document.createElement('p'); status.className = 'answer-status small'; card.append(status); }
        status.textContent = answers[index].response_text.trim() ? assessmentMessage('answered', 'Answered') : assessmentMessage('unanswered', 'Not answered');
    });
    document.getElementById('answer-buttons').classList.add('d-none');
    document.getElementById('review-buttons').classList.remove('d-none');
    document.querySelector('#review-buttons button').focus();
};
window.exitReviewMode = () => {
    isReviewMode = false;
    document.querySelectorAll('#questions-container input, #questions-container textarea').forEach(input => { input.disabled = false; });
    document.querySelectorAll('.answer-status').forEach(status => status.remove());
    document.getElementById('answer-buttons').classList.remove('d-none');
    document.getElementById('review-buttons').classList.add('d-none');
    document.getElementById('review-btn').focus();
};
document.addEventListener('DOMContentLoaded', loadAssessment);
