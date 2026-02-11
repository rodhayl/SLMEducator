let currentAssessment = null;

/**
 * Award XP to the current user for completing an activity
 */
async function awardXP(amount, reason = 'activity') {
    try {
        const token = AuthService.getToken();
        if (!token) return;

        // API expects query parameters, not JSON body
        const response = await fetch(`/api/gamification/award-xp?amount=${amount}&reason=${encodeURIComponent(reason)}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const result = await response.json();
            console.log(`🎮 XP awarded: +${amount} (${reason}). Total: ${result.total_xp}`);
        }
    } catch (e) {
        console.warn('Failed to award XP:', e);
    }
}

async function loadAssessment() {
    const urlParams = new URLSearchParams(window.location.search);
    const id = urlParams.get('id');

    if (!id) {
        showErrorState("No Assessment ID Provided", "Please look for this assessment in your Library or ask your instructor for the correct link.");
        return;
    }

    try {
        const response = await fetch(`/api/assessments/${id}`, {
            headers: {
                'Authorization': `Bearer ${AuthService.getToken()}`
            }
        });

        if (!response.ok) {
            if (response.status === 404) {
                showErrorState("Assessment Not Found", "This assessment ID is invalid or has been deleted.");
            } else if (response.status === 403) {
                showErrorState("Access Denied", "You do not have permission to view this assessment.");
            } else {
                loadingError();
            }
            return;
        }

        currentAssessment = await response.json();
        renderAssessment(currentAssessment);

    } catch (e) {
        console.error(e);
        loadingError();
    }
}

function showErrorState(title, message) {
    const overlay = document.getElementById('error-overlay');
    const container = document.getElementById('question-container');

    if (overlay) {
        overlay.querySelector('.error-title').textContent = title;
        overlay.querySelector('.error-text').textContent = message;
        overlay.classList.remove('d-none');
    }

    if (container) {
        container.classList.add('d-none');
    }
}

function loadingError() {
    showErrorState("Error Loading Assessment", "There was a problem communicating with the server. Please try again later.");
}


let timerInterval = null;
let timeRemaining = 0;

function renderAssessment(assessment) {
    document.getElementById('assessment-title').textContent = assessment.title;
    document.getElementById('assessment-desc').textContent = assessment.description || '';

    // Initialize Timer if time_limit exists (in minutes)
    if (assessment.time_limit) {
        startTimer(assessment.time_limit);
    } else {
        document.getElementById('assessment-timer').textContent = "No Limit";
    }

    const container = document.getElementById('questions-container');
    container.innerHTML = assessment.questions.map((q, index) => `
        <div class="question-card mb-4 p-3 border rounded">
            <h5>Question ${index + 1} <small class="text-muted">(${q.points} pts)</small></h5>
            <p class="lead">${q.question_text}</p>
            
            <div class="answer-input">
                ${renderInput(q)}
            </div>
        </div>
    `).join('');
}

function startTimer(minutes) {
    timeRemaining = minutes * 60;
    updateTimerDisplay();

    if (timerInterval) clearInterval(timerInterval);

    timerInterval = setInterval(() => {
        timeRemaining--;
        updateTimerDisplay();

        if (timeRemaining <= 300) { // 5 minutes warning
            document.getElementById('assessment-timer').classList.add('text-danger', 'fw-bold');
        }

        if (timeRemaining <= 0) {
            clearInterval(timerInterval);
            if (typeof showToast === 'function') {
                showToast("Time is up! Submitting your assessment.", "warning");
            }
            submitAssessment();
        }
    }, 1000);
}

function updateTimerDisplay() {
    const minutes = Math.floor(timeRemaining / 60);
    const seconds = timeRemaining % 60;
    document.getElementById('assessment-timer').textContent =
        `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

function renderInput(q) {
    if (q.question_type === 'multiple_choice' || q.question_type === 'true_false') {
        let choices = [];

        // Handle various option formats
        if (q.options) {
            if (q.options.choices && Array.isArray(q.options.choices)) {
                choices = q.options.choices;
            } else if (Array.isArray(q.options)) {
                choices = q.options;
            } else if (typeof q.options === 'object') {
                // Handle {A: "...", B: "..."} format
                choices = Object.values(q.options);
            }
        }

        // Default choices for true_false if none provided
        if (choices.length === 0 && q.question_type === 'true_false') {
            choices = ['True', 'False'];
        }

        // If still no choices, show warning
        if (choices.length === 0) {
            console.warn(`Question ${q.id} has no options:`, q.options);
            return `<div class="alert alert-warning">No answer options available for this question.</div>`;
        }

        return choices.map(opt => `
            <div class="form-check">
                <input class="form-check-input" type="radio" name="q_${q.id}" value="${opt}" id="q_${q.id}_${opt}">
                <label class="form-check-label" for="q_${q.id}_${opt}">
                    ${opt}
                </label>
            </div>
        `).join('');
    } else {
        return `<textarea class="form-control" name="q_${q.id}" rows="3"></textarea>`;
    }
}

window.submitAssessment = async () => {
    const answers = [];
    currentAssessment.questions.forEach(q => {
        let response = '';
        if (q.question_type === 'multiple_choice' || q.question_type === 'true_false') {
            const selected = document.querySelector(`input[name="q_${q.id}"]:checked`);
            response = selected ? selected.value : '';
        } else {
            response = document.querySelector(`textarea[name="q_${q.id}"]`).value;
        }

        answers.push({
            question_id: q.id,
            response_text: response
        });
    });

    try {
        const response = await fetch(`/api/assessments/${currentAssessment.id}/submit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${AuthService.getToken()}`
            },
            body: JSON.stringify({ answers })
        });

        const result = await response.json();

        // Award XP for completing the assessment
        await awardXP(25, 'assessment_complete');

        // Clear saved progress on successful submission
        clearProgress();

        const resultsDiv = document.getElementById('results');
        resultsDiv.classList.remove('d-none');
        resultsDiv.innerHTML = `
            <div class="alert alert-success">
                <h4>Submission Complete!</h4>
                <p>Score: ${result.score} points</p>
                <button class="btn btn-primary" onclick="window.location.href='dashboard.html'">Back to Dashboard</button>
            </div>
        `;

        // Hide all buttons
        document.getElementById('answer-buttons').classList.add('d-none');
        document.getElementById('review-buttons').classList.add('d-none');
        document.getElementById('autosave-indicator').classList.add('d-none');

    } catch (e) {
        if (typeof showToast === 'function') {
            showToast("Error submitting assessment", "danger");
        }
    }
}

// ============================================================================
// REVIEW MODE (25.2)
// ============================================================================
let isReviewMode = false;

window.showReviewMode = () => {
    isReviewMode = true;

    // Disable all inputs
    document.querySelectorAll('#questions-container input, #questions-container textarea').forEach(el => {
        el.disabled = true;
    });

    // Highlight answered vs unanswered questions
    currentAssessment.questions.forEach((q, index) => {
        const card = document.querySelectorAll('.question-card')[index];
        let hasAnswer = false;

        if (q.question_type === 'multiple_choice' || q.question_type === 'true_false') {
            hasAnswer = !!document.querySelector(`input[name="q_${q.id}"]:checked`);
        } else {
            const textarea = document.querySelector(`textarea[name="q_${q.id}"]`);
            hasAnswer = textarea && textarea.value.trim() !== '';
        }

        if (hasAnswer) {
            card.classList.add('border-success');
            card.classList.remove('border-warning');
        } else {
            card.classList.add('border-warning');
            card.classList.remove('border-success');
        }
    });

    // Toggle button visibility
    document.getElementById('answer-buttons').classList.add('d-none');
    document.getElementById('review-buttons').classList.remove('d-none');
}

window.exitReviewMode = () => {
    isReviewMode = false;

    // Re-enable all inputs
    document.querySelectorAll('#questions-container input, #questions-container textarea').forEach(el => {
        el.disabled = false;
    });

    // Remove highlights
    document.querySelectorAll('.question-card').forEach(card => {
        card.classList.remove('border-success', 'border-warning');
    });

    // Toggle button visibility
    document.getElementById('answer-buttons').classList.remove('d-none');
    document.getElementById('review-buttons').classList.add('d-none');
}

// ============================================================================
// AUTOSAVE / PARTIAL SAVE (25.3)
// ============================================================================
let autosaveTimer = null;

function getStorageKey() {
    const urlParams = new URLSearchParams(window.location.search);
    const id = urlParams.get('id');
    return `assessment_progress_${id}`;
}

function saveProgress() {
    if (!currentAssessment) return;

    const answers = {};
    currentAssessment.questions.forEach(q => {
        if (q.question_type === 'multiple_choice' || q.question_type === 'true_false') {
            const selected = document.querySelector(`input[name="q_${q.id}"]:checked`);
            answers[q.id] = selected ? selected.value : '';
        } else {
            const textarea = document.querySelector(`textarea[name="q_${q.id}"]`);
            answers[q.id] = textarea ? textarea.value : '';
        }
    });

    localStorage.setItem(getStorageKey(), JSON.stringify({
        assessmentId: currentAssessment.id,
        answers: answers,
        savedAt: new Date().toISOString()
    }));

    // Show save indicator
    const indicator = document.getElementById('autosave-indicator');
    const status = document.getElementById('autosave-status');
    if (indicator && status) {
        indicator.classList.remove('d-none');
        status.textContent = '💾 Progress saved';

        // Fade out after 2 seconds
        setTimeout(() => {
            indicator.classList.add('d-none');
        }, 2000);
    }
}

function loadProgress() {
    const saved = localStorage.getItem(getStorageKey());
    if (!saved) return;

    try {
        const data = JSON.parse(saved);
        if (data.assessmentId !== currentAssessment.id) return;

        // Restore answers
        Object.entries(data.answers).forEach(([questionId, value]) => {
            if (!value) return;

            // Try radio buttons first
            const radio = document.querySelector(`input[name="q_${questionId}"][value="${value}"]`);
            if (radio) {
                radio.checked = true;
                return;
            }

            // Try textarea
            const textarea = document.querySelector(`textarea[name="q_${questionId}"]`);
            if (textarea) {
                textarea.value = value;
            }
        });

        console.log('📥 Restored progress from', data.savedAt);
    } catch (e) {
        console.warn('Failed to restore progress:', e);
    }
}

function clearProgress() {
    localStorage.removeItem(getStorageKey());
}

function setupAutosave() {
    // Debounced save on any input change
    document.getElementById('questions-container').addEventListener('input', () => {
        clearTimeout(autosaveTimer);
        autosaveTimer = setTimeout(saveProgress, 3000); // Save 3s after last input
    });

    // Also save on radio button change
    document.getElementById('questions-container').addEventListener('change', () => {
        clearTimeout(autosaveTimer);
        autosaveTimer = setTimeout(saveProgress, 1000); // Save 1s after selection
    });
}

// ============================================================================
// INITIALIZATION
// ============================================================================
document.addEventListener('DOMContentLoaded', async () => {
    await loadAssessment();

    // After assessment loads, restore progress and setup autosave
    if (currentAssessment) {
        loadProgress();
        setupAutosave();
    }
});

