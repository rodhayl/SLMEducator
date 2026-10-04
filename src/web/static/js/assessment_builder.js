// ============================================================================
// Authentication Check - Redirect to login if not authenticated
// ============================================================================
document.addEventListener('DOMContentLoaded', () => {
    if (!AuthService.isAuthenticated()) window.location.href = AuthService.loginUrl();
    else if (!['teacher', 'admin'].includes(AuthService.getRole())) window.location.href = '/dashboard.html';
});

function setAssessmentFeedback(message, type = 'info', assessmentId = null) {
    const feedback = document.getElementById('assessment-feedback');
    if (!feedback) {
        if (typeof showToast === 'function') {
            showToast(message, type);
        } else {
            console.error(message);
        }
        return;
    }

    feedback.className = `alert alert-${type} mt-3`;

    if (assessmentId) {
        feedback.innerHTML = `
            <div>${SLMRender.escape(message)}</div>
            <div class="mt-2 d-flex gap-2 flex-wrap">
                <a href="/dashboard.html?view=assessments" class="btn btn-sm btn-primary" data-i18n="recovery.open_assessments">Open assessments</a>
                <a href="dashboard.html" class="btn btn-sm btn-outline-secondary">Back to Dashboard</a>
            </div>
        `;
    } else {
        feedback.textContent = message;
    }
}

function addQuestionUI() {
    const template = document.getElementById('question-template');
    const clone = template.content.cloneNode(true);

    clone.querySelector('.remove-q').onclick = function () {
        this.closest('.question-item').remove();
        assessmentDirty = true;
        document.getElementById('save-draft-btn').focus();
    };

    addQuestionOrdering(clone.querySelector('.question-item'));
    document.getElementById('questions-container').appendChild(clone);
}

function toggleOptions(select) {
    const container = select.closest('.question-item')?.querySelector('.mc-options');
    if (!container) return;
    if (select.value === 'short_answer') {
        container.classList.add('hidden');
    } else {
        container.classList.remove('hidden');
    }
}

function openRubricModal() {
    const modal = new bootstrap.Modal(document.getElementById('rubricModal'));
    modal.show();
    // Use existing criteria if any or add one default
    if (document.getElementById('rubric-section').children.length === 0) {
        addCriterionUI();
    }
}

function addCriterionUI() {
    const template = document.getElementById('criterion-template');
    const clone = template.content.cloneNode(true);
    const remove = clone.querySelector('.btn-close');
    remove.setAttribute('aria-label', SLMClient.message('remove', 'Remove'));
    remove.onclick = () => { remove.closest('.criterion-item').remove(); assessmentDirty = true; };
    assessmentDirty = true;
    clone.querySelectorAll('input, textarea').forEach(input => input.setAttribute('aria-label', input.placeholder || 'Maximum points'));
    document.getElementById('rubric-section').appendChild(clone);
}

let assessmentSaving = false;
let assessmentDirty = false;
let assessmentPublished = false;
let assessmentPolicyReady = true;
let assessmentPolicyDirty = true;
const assessmentPolicyModes = ['hints_only', 'explanations', 'disabled'];

function updateAssessmentPublishButton() {
    document.getElementById('publish-btn').disabled = !window.editingAssessmentId ||
        assessmentSaving || !assessmentPolicyReady || assessmentDirty || assessmentPolicyDirty;
}

async function loadAssessmentAssistancePolicy() {
    if (!window.editingAssessmentId) return false;
    const selector = document.getElementById('assessment-assistance');
    const retry = document.getElementById('retry-assistance-policy');
    selector.disabled = true;
    assessmentPolicyReady = false;
    updateAssessmentPublishButton();
    try {
        const policy = await SLMClient.request(`/api/assessments/${window.editingAssessmentId}/assistance-policy`);
        if (!assessmentPolicyModes.includes(policy?.mode) || Number(policy.assessment_id) !== Number(window.editingAssessmentId)) throw new Error('Invalid assistance policy');
        selector.value = policy.mode;
        assessmentPolicyReady = true;
        assessmentPolicyDirty = false;
        retry.classList.add('d-none');
        setAssessmentFeedback(SLMClient.message('policy_loaded', 'Assistance policy loaded for review.'), 'info');
        return true;
    } catch (error) {
        retry.classList.remove('d-none');
        setAssessmentFeedback(SLMClient.message('policy_load_failed', 'The assistance policy could not be loaded. Retry before saving or publishing.'), 'danger');
        return false;
    } finally {
        selector.disabled = !assessmentPolicyReady;
        updateAssessmentPublishButton();
    }
}
function collectAssessment() {
    return {
        title: document.getElementById('quiz-title').value.trim(),
        description: document.getElementById('quiz-desc').value,
        passing_score: Number(document.getElementById('quiz-pass').value),
        time_limit_minutes: Number(document.getElementById('quiz-time').value) || null,
        max_attempts: Number(document.getElementById('quiz-attempts').value) || 1,
        grading_mode: document.getElementById('grading-mode').value,
        is_published: false,
        questions: Array.from(document.querySelectorAll('.question-item')).map(item => ({
            question_text: item.querySelector('.question-text').value,
            question_type: item.querySelector('.question-type').value,
            points: Number(item.querySelector('.points').value),
            correct_answer: item.querySelector('.correct-answer').value,
            options: item.querySelector('.question-type').value === 'multiple_choice' ?
                { choices: item.querySelector('.options-list').value.split(',').map(value => value.trim()) } : null
        }))
    };
}
function collectRubric() {
    const name = document.getElementById('rubric-name').value.trim();
    if (!name) return null;
    return { name, criteria: Array.from(document.querySelectorAll('.criterion-item')).map(item => ({
        name: item.querySelector('.criterion-name').value,
        description: item.querySelector('.criterion-desc').value,
        max_points: Number(item.querySelector('input[type="number"]').value)
    })) };
}
window.saveAssessmentDraft = async () => {
    if (assessmentSaving) return;
    if (!assessmentPolicyReady) { setAssessmentFeedback(SLMClient.message('policy_load_failed', 'The assistance policy could not be loaded. Retry before saving or publishing.'), 'danger'); return; }
    const payload = collectAssessment();
    if (!payload.title) { setAssessmentFeedback('Title is required', 'danger'); return; }
    assessmentSaving = true;
    updateAssessmentPublishButton();
    try {
        payload.rubric = collectRubric();
        if (!window.editingAssessmentId || assessmentDirty) {
            const saved = await SLMClient.request(window.editingAssessmentId ? `/api/assessments/${window.editingAssessmentId}` : '/api/assessments/', {
                method: window.editingAssessmentId ? 'PUT' : 'POST',
                headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
            });
            if (!Number.isInteger(saved?.id) || saved.id <= 0 || saved.is_published !== false) {
                throw new Error(SLMClient.message('failed', 'The server could not confirm a saved draft. Keep this page open and retry.'));
            }
            window.editingAssessmentId = saved.id;
            history.replaceState(null, '', `assessment_builder.html?id=${saved.id}`);
            assessmentPublished = false;
            assessmentDirty = JSON.stringify({ ...collectAssessment(), rubric: collectRubric() }) !== JSON.stringify(payload);
        }
        const mode = document.getElementById('assessment-assistance').value;
        assessmentPolicyDirty = true;
        const policy = await SLMClient.request(`/api/assessments/${window.editingAssessmentId}/assistance-policy`, {
            method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ mode })
        });
        if (policy?.mode !== mode || Number(policy.assessment_id) !== Number(window.editingAssessmentId)) throw new Error(SLMClient.message('policy_save_failed', 'The assistance policy was not confirmed saved. Keep this page open and retry; publishing is blocked.'));
        assessmentPolicyDirty = document.getElementById('assessment-assistance').value !== mode;
        const policyLabel = document.getElementById('assessment-assistance').selectedOptions[0].textContent;
        setAssessmentFeedback((assessmentDirty || assessmentPolicyDirty ? SLMClient.message('save_before_publish', 'Save your changes before publishing.') :
            assessmentPublished ? SLMClient.message('policy_saved', 'Assistance policy saved.') :
                SLMClient.message('draft_saved', 'Draft saved. Review the questions and answers, then publish when ready.')) + ` ${SLMClient.message('assistance_mode', 'Assistance mode')}: ${policyLabel}.`, 'info');
    } catch (error) { setAssessmentFeedback(error.message, 'danger'); }
    finally { assessmentSaving = false; updateAssessmentPublishButton(); }
};
window.publishAssessment = async () => {
    if (assessmentSaving || !window.editingAssessmentId) return;
    if (assessmentDirty || assessmentPolicyDirty || !assessmentPolicyReady) { setAssessmentFeedback(SLMClient.message('save_before_publish', 'Save your changes before publishing.'), 'warning'); return; }
    const approved = await showConfirm(SLMClient.message('publish_assessment_confirm', 'Have you reviewed every question, correct answer and grading rule? Publishing makes the assessment available to authorized learners.'),
        SLMClient.message('publish', 'Publish'));
    if (!approved) return;
    if (assessmentSaving || assessmentDirty || assessmentPolicyDirty || !assessmentPolicyReady) {
        setAssessmentFeedback(SLMClient.message('save_before_publish', 'Save your changes before publishing.'), 'warning');
        return;
    }
    assessmentSaving = true;
    try {
        await SLMClient.request(`/api/assessments/${window.editingAssessmentId}/publish`, { method: 'POST' });
        assessmentPublished = true;
        setAssessmentFeedback(SLMClient.message('published', 'Published successfully.'), 'success', window.editingAssessmentId);
    } catch (error) { setAssessmentFeedback(error.message, 'danger'); }
    finally { assessmentSaving = false; }
};

function addQuestionOrdering(card) {
    const controls = document.createElement('div'); controls.className = 'btn-group my-2';
    [-1, 1].forEach(direction => {
        const button = document.createElement('button'); button.type = 'button';
        button.className = 'btn btn-sm btn-outline-secondary';
        button.textContent = direction < 0 ? '↑' : '↓';
        button.setAttribute('aria-label', SLMClient.message(direction < 0 ? 'move_up' : 'move_down', direction < 0 ? 'Move question up' : 'Move question down'));
        button.onclick = () => {
            const sibling = direction < 0 ? card.previousElementSibling : card.nextElementSibling;
            if (sibling) card.parentNode.insertBefore(direction < 0 ? card : sibling, direction < 0 ? sibling : card);
            assessmentDirty = true; button.focus();
        };
        controls.append(button);
    });
    card.append(controls);
    card.querySelectorAll('input, select').forEach(input => {
        input.setAttribute('aria-label', input.placeholder || 'Question type');
        const label = input.previousElementSibling;
        if (label?.tagName === 'LABEL') {
            input.id = 'question-field-' + crypto.randomUUID(); label.htmlFor = input.id;
        }
    });
    assessmentDirty = true;
}

// Add one default question and initialize Sortable for reordering (32.2)
document.addEventListener('DOMContentLoaded', async () => {
    // Check if editing existing assessment
    const urlParams = new URLSearchParams(window.location.search);
    const assessmentId = urlParams.get('id');

    if (assessmentId) {
        await loadAssessmentForEdit(assessmentId);
        // Update page title
        document.querySelector('h2')?.replaceWith(Object.assign(document.createElement('h2'), {
            className: 'mb-4',
            textContent: '✏️ Edit Assessment'
        }));
        // Update button text
        updateAssessmentPublishButton();
    } else {
        addQuestionUI();
    }

    // Initialize Sortable for question reordering
    const questionsList = document.getElementById('questions-container');
    if (questionsList && typeof Sortable !== 'undefined') {
        new Sortable(questionsList, {
            animation: 150,
            handle: '.drag-handle',
            ghostClass: 'bg-primary-subtle',
            onEnd: function () {
                assessmentDirty = true;
            }
        });
    }
});

// Store assessment ID for edit mode
window.editingAssessmentId = null;

async function loadAssessmentForEdit(assessmentId) {
    assessmentPolicyReady = false;
    document.getElementById('assessment-assistance').disabled = true;
    updateAssessmentPublishButton();
    try {
        const response = await fetch(`/api/assessments/${assessmentId}`, {
            headers: {
                'Authorization': `Bearer ${AuthService.getToken()}`
            }
        });

        if (!response.ok) {
            setAssessmentFeedback('Failed to load assessment for editing', 'danger');
            return;
        }

        const assessment = await response.json();
        window.editingAssessmentId = assessmentId;
        assessmentPublished = assessment.is_published === true;

        // Populate form fields
        document.getElementById('quiz-title').value = assessment.title || '';
        document.getElementById('quiz-desc').value = assessment.description || '';
        document.getElementById('quiz-pass').value = assessment.passing_score ?? 70;
        if (document.getElementById('quiz-time')) {
            document.getElementById('quiz-time').value = assessment.time_limit_minutes || '';
        }
        if (document.getElementById('grading-mode')) {
            document.getElementById('grading-mode').value = assessment.grading_mode || 'ai_assisted';
        }

        // Load questions
        document.getElementById('questions-container').replaceChildren();
        if (assessment.questions && assessment.questions.length > 0) {
            for (const q of assessment.questions) {
                addQuestionUI();
                const items = document.querySelectorAll('.question-item');
                const lastItem = items[items.length - 1];

                lastItem.querySelector('.question-text').value = q.question_text || '';
                lastItem.querySelector('.question-type').value = q.question_type || 'multiple_choice';
                lastItem.querySelector('.points').value = q.points || 10;
                lastItem.querySelector('.correct-answer').value = q.correct_answer || '';

                const optionsList = lastItem.querySelector('.options-list');
                if (optionsList && q.options?.choices) {
                    optionsList.value = q.options.choices.join(', ');
                }

                toggleOptions(lastItem.querySelector('.question-type'));
            }
        } else {
            addQuestionUI();
        }

        document.getElementById('quiz-attempts').value = assessment.max_attempts || 1;
        document.getElementById('rubric-name').value = assessment.rubric?.name || '';
        document.getElementById('rubric-section').replaceChildren();
        (assessment.rubric?.criteria || []).forEach(criterion => {
            addCriterionUI();
            const item = document.getElementById('rubric-section').lastElementChild;
            item.querySelector('.criterion-name').value = criterion.name;
            item.querySelector('.criterion-desc').value = criterion.description || '';
            item.querySelector('input[type="number"]').value = criterion.max_points;
        });
        assessmentDirty = false;
        await loadAssessmentAssistancePolicy();
    } catch (e) {
        console.error('Failed to load assessment:', e);
        setAssessmentFeedback('Error loading assessment', 'danger');
    }
}

// Preview uses the same safe content boundary as the learner view.
function previewAssessment() {
    const payload = collectAssessment();
    const html = '<h2>' + SLMRender.escape(payload.title || 'Preview') + '</h2>' + payload.questions.map((question, index) =>
        `<p><strong>${index + 1}.</strong> ${SLMRender.escape(question.question_text)} (${question.points} pts)</p>`).join('');
    showInfoModal(SLMClient.message('preview', 'Preview'), html);
}
function markAssessmentChange(event) {
    if (event.target.id === 'assessment-assistance') assessmentPolicyDirty = true;
    else assessmentDirty = true;
    updateAssessmentPublishButton();
}
document.addEventListener('input', markAssessmentChange);
document.addEventListener('change', markAssessmentChange);
