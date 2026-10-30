// ============================================================================
// Authentication Check - Redirect to login if not authenticated
// ============================================================================
(function () {
    if (!window.AuthService || !AuthService.isAuthenticated()) {
        window.location.href = 'login.html';
        return;
    }

    try {
        const role = AuthService.getRole();
        if (role && role !== 'teacher' && role !== 'admin') {
            window.location.href = 'dashboard.html';
            return;
        }
    } catch {
        // ignore
    }
})();

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
            <div>${message}</div>
            <div class="mt-2 d-flex gap-2 flex-wrap">
                <a href="assessment_taker.html?id=${assessmentId}" class="btn btn-sm btn-primary">Open Assessment</a>
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
    };

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
    document.getElementById('rubric-section').appendChild(clone);
}

async function publishAssessment() {
    const title = document.getElementById('quiz-title').value;
    if (!title) {
        setAssessmentFeedback('Title is required', 'danger');
        return;
    }

    // Gather Questions
    const questions = [];
    document.querySelectorAll('.question-item').forEach(item => {
        const text = item.querySelector('.question-text').value;
        const type = item.querySelector('.question-type').value;
        const points = parseInt(item.querySelector('.points').value) || 10;
        const correct = item.querySelector('.correct-answer').value;
        const optionsStr = item.querySelector('.options-list') ? item.querySelector('.options-list').value : '';

        const options = type === 'multiple_choice'
            ? { choices: optionsStr.split(',').map(s => s.trim()) }
            : null;

        questions.push({
            question_text: text,
            question_type: type,
            points: points,
            correct_answer: correct,
            options: options
        });
    });

    // Gather Rubric
    let rubric = null;
    const rubricName = document.getElementById('rubric-name').value;
    if (rubricName) {
        const criteria = [];
        document.querySelectorAll('.criterion-item').forEach(item => {
            criteria.push({
                name: item.querySelector('.criterion-name').value,
                max_points: parseInt(item.querySelector('input[type="number"]').value) || 10,
                description: item.querySelector('.criterion-desc').value
            });
        });
        if (criteria.length > 0) {
            rubric = {
                name: rubricName,
                description: "Attached to assessment",
                criteria: criteria
            };
        }
    }

    const payload = {
        title: title,
        description: document.getElementById('quiz-desc').value,
        passing_score: parseInt(document.getElementById('quiz-pass').value),
        grading_mode: document.getElementById('grading-mode')?.value || 'ai_assisted',
        questions: questions,
        rubric: rubric
    };

    try {
        const response = await fetch('/api/assessments/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${AuthService.getToken()}`
            },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            const created = await response.json();
            setAssessmentFeedback('Assessment published successfully.', 'success', created.id);
        } else {
            const err = await response.json();
            setAssessmentFeedback(err.detail || 'Failed to publish assessment.', 'danger');
        }
    } catch (e) {
        console.error(e);
        setAssessmentFeedback('Network error while publishing assessment.', 'danger');
    }
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
            innerHTML: '✏️ Edit Assessment'
        }));
        // Update button text
        const publishBtn = document.getElementById('publish-btn');
        if (publishBtn) {
            publishBtn.textContent = '💾 Save Changes';
        }
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
                console.log('Questions reordered');
            }
        });
    }
});

// Store assessment ID for edit mode
window.editingAssessmentId = null;

async function loadAssessmentForEdit(assessmentId) {
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

        // Populate form fields
        document.getElementById('quiz-title').value = assessment.title || '';
        document.getElementById('quiz-desc').value = assessment.description || '';
        document.getElementById('quiz-pass').value = assessment.passing_score || 70;
        if (document.getElementById('quiz-time')) {
            document.getElementById('quiz-time').value = assessment.time_limit_minutes || '';
        }
        if (document.getElementById('grading-mode')) {
            document.getElementById('grading-mode').value = assessment.grading_mode || 'ai_assisted';
        }

        // Load questions
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

        setAssessmentFeedback('Loaded assessment for editing', 'info');
    } catch (e) {
        console.error('Failed to load assessment:', e);
        setAssessmentFeedback('Error loading assessment', 'danger');
    }
}

// Modify publishAssessment to handle both create and update
const originalPublishAssessment = publishAssessment;
window.publishAssessment = async function () {
    if (window.editingAssessmentId) {
        await updateAssessment();
    } else {
        await originalPublishAssessment();
    }
};

async function updateAssessment() {
    const title = document.getElementById('quiz-title').value;
    if (!title) {
        setAssessmentFeedback('Title is required', 'danger');
        return;
    }

    // Gather Questions
    const questions = [];
    document.querySelectorAll('.question-item').forEach(item => {
        const text = item.querySelector('.question-text').value;
        const type = item.querySelector('.question-type').value;
        const points = parseInt(item.querySelector('.points').value) || 10;
        const correct = item.querySelector('.correct-answer').value;
        const optionsStr = item.querySelector('.options-list') ? item.querySelector('.options-list').value : '';

        const options = type === 'multiple_choice'
            ? { choices: optionsStr.split(',').map(s => s.trim()) }
            : null;

        questions.push({
            question_text: text,
            question_type: type,
            points: points,
            correct_answer: correct,
            options: options
        });
    });

    const payload = {
        title: title,
        description: document.getElementById('quiz-desc').value,
        passing_score: parseInt(document.getElementById('quiz-pass').value),
        grading_mode: document.getElementById('grading-mode')?.value || 'ai_assisted',
        questions: questions
    };

    try {
        const response = await fetch(`/api/assessments/${window.editingAssessmentId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${AuthService.getToken()}`
            },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            const updated = await response.json();
            setAssessmentFeedback('Assessment updated successfully.', 'success', updated.id);
        } else {
            const err = await response.json();
            setAssessmentFeedback(err.detail || 'Failed to update assessment.', 'danger');
        }
    } catch (e) {
        console.error(e);
        setAssessmentFeedback('Network error while updating assessment.', 'danger');
    }
}
// Preview Assessment Function
function previewAssessment() {
    const title = document.getElementById('quiz-title').value || 'Preview';
    const questions = [];
    document.querySelectorAll('.question-item').forEach((item, i) => {
        questions.push({
            text: item.querySelector('.question-text').value || 'Q' + (i + 1),
            type: item.querySelector('.question-type').value,
            points: item.querySelector('.points').value || 10
        });
    });
    let html = '<h2>' + title + '</h2><hr><p class="badge bg-info">Preview Mode</p>';
    questions.forEach((q, i) => {
        html += '<div class="card mb-3"><div class="card-body"><strong>Q' + (i + 1) + '</strong>: ' + q.text + ' (' + q.points + 'pts)</div></div>';
    });
    const w = window.open('', '_blank', 'width=600,height=500');
    w.document.write('<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"><div class="container p-4">' + html + '</div>');
}
