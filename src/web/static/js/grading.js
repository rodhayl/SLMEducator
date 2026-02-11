// grading.js - Calificaciones/Grading page functionality
// Loaded as regular script (not ES module) to support inline onclick handlers

// I18n helper (fallback if I18n not available)
const t = (key, params = {}) => {
    if (typeof I18n !== 'undefined' && I18n.t) {
        return I18n.t(key, params);
    }
    // Fallback messages
    const fallbacks = {
        'grading.access_denied': 'Access denied. Grading is only available to teachers and administrators.',
        'grading.grade_saved': 'Grade Saved!',
        'grading.ai_grades_accepted': `AI grades accepted! Final score: ${params.score || ''}`,
        'grading.error_accept_grade': 'Failed to accept grade',
        'grading.error_save_grade': 'Failed to save grade',
        'grading.error_network': 'Network Error',
        'grading.error_accept_ai': 'Failed to accept AI grades',
        'grading.labels.submissions': 'Submissions',
        'grading.labels.final_score': 'Final Score',
        'grading.labels.feedback': 'Feedback',
        'grading.labels.ai_suggestion': 'AI Suggestion',
        'grading.labels.student_answer': 'Student Answer',
        'grading.labels.correct_answer': 'Correct Answer',
        'grading.labels.modified': 'Modified',
        'grading.labels.score': 'Score',
        'grading.labels.optional_feedback': 'Optional feedback',
        'grading.labels.pts': 'pts',
        'grading.labels.confidence': `${params.percent || ''}% confidence`,
        'grading.buttons.accept_all_ai': '✓ Accept All AI Suggestions',
        'grading.buttons.accept': '✓ Accept',
        'grading.buttons.modify': '✏️ Modify',
        'grading.buttons.save': 'Save',
        'grading.buttons.submit_grade': 'Submit Grade',
        'grading.placeholders.select_submission': 'Select a submission to start grading',
        'grading.placeholders.grade_score': '0-100',
        'grading.placeholders.grade_feedback': 'Great job, but watch out for...',
        'grading.messages.error_loading_submissions': `Error loading submissions: ${params.error || ''}`,
        'grading.messages.not_authenticated': 'Error: Not authenticated',
        'grading.messages.error_loading_details': 'Error loading details',
        'grading.messages.no_answer': 'No answer',
        'grading.messages.no_answer_data': 'No answer data found.',
        'grading.ai.summary': `${params.count || ''} question(s) with AI suggestions`
    };
    return fallbacks[key] || key;
};

// Check authentication
function checkAuth() {
    // Wait for AuthService to be available (it's loaded as a module)
    if (typeof AuthService === 'undefined' || !AuthService) {
        console.log('[Grading] Waiting for AuthService...');
        setTimeout(checkAuth, 100);
        return false;
    }

    if (!AuthService.isAuthenticated()) {
        window.location.href = '/login.html';
        return false;
    }

    // Role-based access control: Only teachers and admins can access grading
    const userRole = AuthService.getRole();
    if (userRole !== 'teacher' && userRole !== 'admin') {
        // Show toast message then redirect
        if (typeof showToast === 'function') {
            showToast(t('grading.access_denied'), 'danger', 2000);
        }
        setTimeout(() => {
            window.location.href = '/dashboard.html';
        }, 1500);
        return false;
    }
    return true;
}

let currentSubmissionId = null;
let currentSubmissionData = null;
let allSubmissions = []; // Store globally for filtering
let currentStatusFilter = 'all';

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('[Grading] DOMContentLoaded fired');
    
    // Wait a brief moment for AuthService module to load
    setTimeout(() => {
        if (checkAuth()) {
            loadSubmissions();
        }
    }, 100);
});

function loadSubmissions() {
    console.log('[Grading] loadSubmissions called');
    const list = document.getElementById('submission-list');
    if (!list) {
        console.error('[Grading] submission-list element not found');
        return;
    }
    list.innerHTML = `<div class="text-center p-3 text-muted">${t('common.labels.loading')}</div>`;

    const token = AuthService.getToken();
    console.log('[Grading] Got token:', token ? 'Yes' : 'No');
    
    if (!token) {
        console.error('[Grading] No authentication token');
        list.innerHTML = `<div class="text-danger p-3">${t('grading.messages.not_authenticated')}</div>`;
        return;
    }

    // Include ai_graded status in filter for AI-assisted submissions needing review
    fetch('/api/assessments/submissions?status=submitted&status=graded&status=ai_graded', {
        headers: { 'Authorization': `Bearer ${token}` }
    })
    .then(res => {
        console.log('[Grading] API response status:', res.status);
        if (!res.ok) {
            throw new Error(`Failed to load: ${res.status}`);
        }
        return res.json();
    })
    .then(submissions => {
        console.log('[Grading] Got submissions:', submissions.length);
        allSubmissions = submissions;
        applyCurrentFilter();
    })
    .catch(e => {
        console.error('[Grading] Error in loadSubmissions:', e);
        list.innerHTML = `<div class="text-danger p-3">${t('grading.messages.error_loading_submissions', { error: e.message })}</div>`;
    });
}

/**
 * Filter submissions by status
 */
function filterSubmissions(status, btn) {
    currentStatusFilter = status;

    // Update active button
    const tabs = document.querySelectorAll('#grading-filter-tabs button');
    tabs.forEach(t => t.classList.remove('active'));
    if (btn) btn.classList.add('active');

    applyCurrentFilter();
}

/**
 * Apply current filter to submissions
 */
function applyCurrentFilter() {
    let filtered = allSubmissions;

    if (currentStatusFilter === 'pending') {
        filtered = allSubmissions.filter(s =>
            s.status === 'submitted' || s.status === 'ai_graded'
        );
    } else if (currentStatusFilter === 'graded') {
        filtered = allSubmissions.filter(s => s.status === 'graded');
    }

    renderList(filtered);
}

function renderList(submissions) {
    const list = document.getElementById('submission-list');
    list.innerHTML = '';

    if (submissions.length === 0) {
        list.innerHTML = `<div class="text-center p-3 text-muted">${t('grading.empty_state')}</div>`;
        return;
    }

    const template = document.getElementById('submission-item-template');

    submissions.forEach(sub => {
        const clone = template.content.cloneNode(true);
        const link = clone.querySelector('a');

        link.onclick = (e) => { e.preventDefault(); selectSubmission(sub); };
        clone.querySelector('.student-name').textContent = sub.student_name || `Student #${sub.student_id}`;
        clone.querySelector('.assessment-title').textContent = sub.assessment_title || `Assessment #${sub.assessment_id}`;
        clone.querySelector('.submission-date').textContent = new Date(sub.submitted_at).toLocaleDateString();

        const badge = clone.querySelector('.status-badge');
        badge.textContent = getStatusLabel(sub.status);
        badge.className = 'status-badge badge ' + getStatusBadgeClass(sub.status);

        list.appendChild(clone);
    });
}

function getStatusLabel(status) {
    const keyByStatus = {
        submitted: 'grading.status.submitted',
        ai_graded: 'grading.status.ai_graded',
        graded: 'grading.status.graded',
        pending: 'grading.status.pending'
    };
    const key = keyByStatus[status];
    return key ? t(key) : status;
}

function getStatusBadgeClass(status) {
    const classes = {
        'submitted': 'bg-warning text-dark',
        'ai_graded': 'bg-info text-dark',
        'graded': 'bg-success',
        'returned': 'bg-secondary'
    };
    return classes[status] || 'bg-secondary';
}

function selectSubmission(sub) {
    currentSubmissionId = sub.id;

    // UI Updates
    document.getElementById('grading-placeholder').classList.add('hidden');
    const area = document.getElementById('grading-area');
    area.classList.remove('hidden');

    document.getElementById('submission-title').textContent = `${sub.student_name} - ${sub.assessment_title}`;
    const statusBadge = document.getElementById('submission-status');
    statusBadge.textContent = getStatusLabel(sub.status);
    statusBadge.className = 'badge ' + getStatusBadgeClass(sub.status);

    // Load details
    loadSubmissionDetails(sub.id);
}

function loadSubmissionDetails(id) {
    const container = document.getElementById('answers-container');
    if (!container) return;
    container.innerHTML = t('common.labels.loading');

    const token = AuthService.getToken();
    
    fetch(`/api/assessments/submissions/${id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
    })
    .then(res => {
        if (!res.ok) throw new Error(`Failed to load: ${res.status}`);
        return res.json();
    })
    .then(fullSub => {
        currentSubmissionData = fullSub;
        renderAnswers(fullSub, container);

        // Show/hide AI actions based on status
        const aiActions = document.getElementById('ai-actions');
        const hasAiSuggestions = fullSub.answers?.some(a => a.ai_suggested_score !== null);

        if (fullSub.status === 'ai_graded' || hasAiSuggestions) {
            aiActions.classList.remove('hidden');
            const aiCount = fullSub.answers?.filter(a => a.ai_suggested_score !== null).length || 0;
            document.getElementById('ai-summary').textContent =
                t('grading.ai.summary', { count: aiCount });
        } else {
            aiActions.classList.add('hidden');
        }

        // Populate existing grade if any
        if (fullSub.score !== null) {
            document.getElementById('grade-score').value = fullSub.score;
        }
        if (fullSub.feedback) {
            document.getElementById('grade-feedback').value = fullSub.feedback;
        }
    })
    .catch(e => {
        container.innerHTML = t('grading.messages.error_loading_details');
        console.error(e);
    });
}

function renderAnswers(sub, container) {
    if (!sub.answers || !Array.isArray(sub.answers)) {
        container.innerHTML = t('grading.messages.no_answer_data');
        return;
    }

    container.innerHTML = sub.answers.map((ans, idx) => {
        const hasAiSuggestion = ans.ai_suggested_score !== null;
        const confidencePercent = ans.ai_confidence ? Math.round(ans.ai_confidence * 100) : null;
        const ptsLabel = t('grading.labels.pts');
        const studentAnswerLabel = t('grading.labels.student_answer');
        const correctAnswerLabel = t('grading.labels.correct_answer');
        const noAnswerLabel = t('grading.messages.no_answer');
        const aiSuggestionLabel = t('grading.labels.ai_suggestion');
        const modifiedLabel = t('grading.labels.modified');
        const acceptLabel = t('grading.buttons.accept');
        const modifyLabel = t('grading.buttons.modify');
        const scoreLabel = t('grading.labels.score');
        const optionalFeedbackLabel = t('grading.labels.optional_feedback');
        const saveLabel = t('grading.buttons.save');

        return `
        <div class="card mb-3" data-response-id="${ans.response_id}">
            <div class="card-header d-flex justify-content-between align-items-center">
                <div>
                    <strong>Q${idx + 1}:</strong> ${ans.question_text}
                </div>
                <span class="badge ${ans.points !== null ? 'bg-success' : 'bg-secondary'}">
                    ${ans.points ?? '?'} / ${ans.max_points || 1} ${ptsLabel}
                </span>
            </div>
            <div class="card-body">
                <p><strong>${studentAnswerLabel}:</strong> 
                    <span class="${ans.is_correct === true ? 'text-success' : ans.is_correct === false ? 'text-danger' : ''}">
                        ${ans.given_answer || `<em>${noAnswerLabel}</em>`}
                    </span>
                </p>
                ${ans.is_correct === false && ans.correct_answer ?
                `<p class="text-muted"><small>${correctAnswerLabel}: ${ans.correct_answer}</small></p>` : ''}
                
                ${hasAiSuggestion ? `
                <div class="ai-suggestion-panel mt-3 p-3 bg-light rounded border-start border-4 border-info">
                    <div class="d-flex justify-content-between align-items-start flex-wrap gap-2">
                        <div>
                            <span class="fw-bold text-info">🤖 ${aiSuggestionLabel}:</span>
                            <strong>${ans.ai_suggested_score}/${ans.max_points}</strong>
                            ${confidencePercent !== null ?
                    `<span class="badge ${confidencePercent >= 80 ? 'bg-success' : confidencePercent >= 50 ? 'bg-warning text-dark' : 'bg-danger'} ms-2">
                                    ${t('grading.labels.confidence', { percent: confidencePercent })}
                                </span>` : ''}
                            ${ans.teacher_override ? `<span class="badge bg-secondary ms-2">${modifiedLabel}</span>` : ''}
                        </div>
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-success btn-sm" onclick="acceptSingleAiGrade(${ans.response_id}, ${ans.ai_suggested_score})">
                                ${acceptLabel}
                            </button>
                            <button class="btn btn-outline-warning btn-sm" onclick="toggleManualGrade(${ans.response_id})">
                                ${modifyLabel}
                            </button>
                        </div>
                    </div>
                    ${ans.ai_suggested_feedback ?
                    `<div class="mt-2 text-muted small">${ans.ai_suggested_feedback}</div>` : ''}
                </div>
                ` : ''}
                
                <!-- Manual grade input (hidden by default) -->
                <div class="manual-grade-input mt-3 hidden" id="manual-grade-${ans.response_id}">
                    <div class="row g-2">
                        <div class="col-4">
                            <input type="number" class="form-control form-control-sm" 
                                   id="score-${ans.response_id}" 
                                   placeholder="${scoreLabel}" max="${ans.max_points}" value="${ans.points ?? ''}">
                        </div>
                        <div class="col-8">
                            <div class="input-group input-group-sm">
                                <input type="text" class="form-control" 
                                       id="feedback-${ans.response_id}" 
                                       placeholder="${optionalFeedbackLabel}">
                                <button class="btn btn-primary" onclick="submitQuestionGrade(${ans.response_id})">
                                    ${saveLabel}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    }).join('');
}

function toggleManualGrade(responseId) {
    const input = document.getElementById(`manual-grade-${responseId}`);
    input.classList.toggle('hidden');
}

function acceptSingleAiGrade(responseId, suggestedScore) {
    const token = AuthService.getToken();
    
    fetch(`/api/assessments/submissions/${currentSubmissionId}/responses/${responseId}/grade`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ score: suggestedScore, feedback: null })
    })
    .then(res => {
        if (res.ok) {
            loadSubmissionDetails(currentSubmissionId);
        } else {
            showToast(t('grading.error_accept_grade'), 'danger');
        }
    })
    .catch(e => {
        showToast(t('grading.error_network'), 'danger');
        console.error(e);
    });
}

function submitQuestionGrade(responseId) {
    const score = document.getElementById(`score-${responseId}`).value;
    const feedback = document.getElementById(`feedback-${responseId}`).value;
    const token = AuthService.getToken();

    fetch(`/api/assessments/submissions/${currentSubmissionId}/responses/${responseId}/grade`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ score: parseInt(score), feedback: feedback || null })
    })
    .then(res => {
        if (res.ok) {
            document.getElementById(`manual-grade-${responseId}`).classList.add('hidden');
            loadSubmissionDetails(currentSubmissionId);
        } else {
            showToast(t('grading.error_save_grade'), 'danger');
        }
    })
    .catch(e => {
        showToast(t('grading.error_network'), 'danger');
        console.error(e);
    });
}

function acceptAllAiGrades() {
    const token = AuthService.getToken();
    
    fetch(`/api/assessments/submissions/${currentSubmissionId}/accept-ai`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
    })
    .then(res => {
        if (res.ok) {
            return res.json();
        } else {
            return res.json().then(err => { throw err; });
        }
    })
    .then(result => {
        showToast(t('grading.ai_grades_accepted', { score: result.final_score }), 'success');
        loadSubmissionDetails(currentSubmissionId);
        loadSubmissions();
    })
    .catch(err => {
        showToast(err.detail || t('grading.error_accept_ai'), 'danger');
        console.error(err);
    });
}

function submitGrade() {
    if (!currentSubmissionId) return;

    const score = document.getElementById('grade-score').value;
    const feedback = document.getElementById('grade-feedback').value;
    const token = AuthService.getToken();

    fetch(`/api/assessments/submissions/${currentSubmissionId}/grade`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ score: parseFloat(score), feedback })
    })
    .then(res => {
        if (res.ok) {
            showToast(t('grading.grade_saved'), 'success');
            loadSubmissions();
        } else {
            showToast(t('grading.error_save_grade'), 'danger');
        }
    })
    .catch(e => {
        showToast(t('grading.error_network'), 'danger');
        console.error(e);
    });
}
