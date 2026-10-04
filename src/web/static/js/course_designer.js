/**
 * Course Designer Logic - SLM Educator
 * 
 * Implements a 3-stage wizard for AI-powered course generation:
 * Stage 1: Configuration & File Upload
 * Stage 2: Outline Review & Editing
 * Stage 3: Cascading Content Generation
 */

// === Constants ===
const MAX_FILE_SIZE_MB = 10;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

// === State Variables ===
let currentConfig = {};
let generatedOutline = null;
let sourceMaterialText = null;
let sourceCoverage = null;
let totalGenerationTasks = 0;
let completedTasks = 0;
let failedTasks = 0;  // Track failures for accurate status
let createdStudyPlanId = null;
let generationRunning = false;
let generationTasks = [];
let courseOwner = null;
function persistCourse() {
    if (courseOwner !== SLMClient.account()) return;
    SLMClient.drafts.write('course', 'designer', 'active', { currentConfig, generatedOutline, sourceMaterialText, sourceCoverage, createdStudyPlanId, generationTasks });
}
async function restoreCourse() {
    courseOwner = SLMClient.account();
    const draft = SLMClient.drafts.read('course', 'designer', 'active');
    if (!draft) return;
    const choice = await SLMClient.chooseDraft();
    if (choice === 'discard') { SLMClient.drafts.remove('course', 'designer', 'active'); return; }
    if (choice !== 'restore') { window.location.href = '/dashboard.html'; return; }
    ({ currentConfig, generatedOutline, sourceMaterialText, sourceCoverage, createdStudyPlanId, generationTasks } = draft);
    if (generatedOutline) {
        renderOutline(generatedOutline);
        document.getElementById('stage-1').classList.add('hidden');
        document.getElementById('stage-2').classList.remove('hidden');
    }
    renderSourceCoverage();
    if (createdStudyPlanId) document.getElementById('course-workflow').classList.remove('d-none');
}

// === Initialization ===
document.addEventListener('DOMContentLoaded', async () => {
    // Check authentication
    if (!checkAuth()) {
        return;
    }
    if (!checkRole()) {
        return;
    }
    setupStage1();
    await restoreCourse();
});

/**
 * Check if user is authenticated
 */
function checkAuth() {
    if (!window.AuthService || !AuthService.isAuthenticated()) {
        window.location.href = '/login.html?redirect=' + encodeURIComponent(window.location.pathname);
        return false;
    }
    return true;
}

function checkRole() {
    try {
        const role = AuthService.getRole();
        if (role && role !== 'teacher' && role !== 'admin') {
            window.location.href = '/dashboard.html';
            return false;
        }
    } catch {
        // If user is missing/corrupt, let auth guard handle redirect elsewhere
    }
    return true;
}

// === Stage 1: Configuration & Upload ===

function setupStage1() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const form = document.getElementById('config-form');
    const removeBtn = document.getElementById('remove-file');

    // Drag & Drop handlers
    dropZone.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); fileInput.click(); } });
    fileInput.addEventListener('change', handleFileSelect);

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('active');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('active');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('active');
        if (e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            handleFileSelect();
        }
    });

    // Remove file handler
    if (removeBtn) {
        removeBtn.addEventListener('click', handleRemoveFile);
    }

    // Form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Validate required fields
        const formData = new FormData(form);
        const subject = formData.get('subject')?.trim();

        if (!subject) {
            showError('Please enter a subject or topic.');
            return;
        }

        currentConfig = {
            subject: subject,
            grade_level: formData.get('grade_level'),
            duration: parseInt(formData.get('duration')) || 4
        };

        transitionToStage2();
    });
}

/**
 * Handle file selection and upload
 */
async function handleFileSelect() {
    const fileInput = document.getElementById('file-input');
    const file = fileInput.files[0];
    if (!file) return;

    // Validate file type
    const validTypes = ['.pdf', '.txt', '.md'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!validTypes.includes(ext)) {
        showError('Please upload a PDF, TXT, or MD file.');
        return;
    }

    // Validate file size
    if (file.size > MAX_FILE_SIZE_BYTES) {
        showError(`File size exceeds ${MAX_FILE_SIZE_MB}MB limit. Please upload a smaller file.`);
        return;
    }

    // Show preview UI
    document.getElementById('filename').textContent = file.name;
    document.getElementById('file-preview').classList.remove('hidden');
    document.getElementById('drop-zone').classList.add('hidden');

    // Upload immediately
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/upload/source-material', {
            method: 'POST',
            headers: getAuthHeaders(true),
            body: formData
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || 'Upload failed');
        }

        const data = await response.json();
        sourceMaterialText = data.extracted_text;
        sourceCoverage = { coverage: data.coverage, truncated: data.truncated,
            char_count: data.char_count, unreadable_pages: data.unreadable_pages,
            source_version: data.source_version, sections: (data.sections || []).map(section => ({ reference: section.reference })) };
        renderSourceCoverage();
        persistCourse();
        console.log("Source material processed:", data.char_count, "chars");

    } catch (e) {
        console.error(e);
        showError("Failed to process file: " + e.message);
        handleRemoveFile();
    }
}

/**
 * Remove uploaded file and reset UI
 */
function handleRemoveFile() {
    document.getElementById('file-preview').classList.add('hidden');
    document.getElementById('drop-zone').classList.remove('hidden');
    document.getElementById('file-input').value = '';
    sourceMaterialText = null;
    sourceCoverage = null;
    renderSourceCoverage();
    persistCourse();
}

// === Stage 2: Outline Generation ===

async function transitionToStage2() {
    const submitBtn = document.querySelector('#config-form button[type="submit"]');

    // Show loading state
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Generating...';
    }

    // Show loading indicator in Stage 1 (don't transition yet)
    const loadingIndicator = document.createElement('div');
    loadingIndicator.id = 'loading-overlay';
    loadingIndicator.className = 'text-center p-4';
    loadingIndicator.innerHTML = `
        <div class="spinner-border text-primary" role="status"></div>
        <p class="mt-2">Analyzing material & generating outline...</p>
        <small class="text-muted">This may take 30-60 seconds</small>
    `;
    document.getElementById('stage-1').appendChild(loadingIndicator);

    try {
        const response = await fetch('/api/generate/course-outline', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                subject: currentConfig.subject,
                grade_level: currentConfig.grade_level,
                duration_weeks: currentConfig.duration,
                source_material: sourceMaterialText
            })
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || 'Generation failed');
        }

        generatedOutline = await response.json();

        // Validate outline structure
        if (!generatedOutline.units || generatedOutline.units.length === 0) {
            throw new Error('AI returned empty outline. Please try again with more context.');
        }

        // SUCCESS: Now transition to Stage 2
        document.getElementById('stage-1').classList.add('hidden');
        document.getElementById('stage-2').classList.remove('hidden');
        document.getElementById('step-1-ind').classList.add('completed');
        document.getElementById('step-2-ind').classList.add('active');
        document.getElementById('course-designer-error')?.classList.add('d-none');

        renderOutline(generatedOutline);
        persistCourse();

    } catch (e) {
        console.error(e);
        // Remove loading indicator
        const overlay = document.getElementById('loading-overlay');
        if (overlay) overlay.remove();

        // Transition to Stage 2 so users can continue manually.
        generatedOutline = { title: currentConfig.subject || 'New Course', units: [] };
        document.getElementById('stage-1').classList.add('hidden');
        document.getElementById('stage-2').classList.remove('hidden');
        document.getElementById('step-1-ind').classList.add('completed');
        document.getElementById('step-2-ind').classList.add('active');
        renderOutline(generatedOutline);
        showOutlineError(`AI outline generation failed: ${e.message}. You can build the outline manually below.`);
        persistCourse();
    } finally {
        // Reset button and remove loading
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = 'Next: Generate Outline ➡️';
        }
        const overlay = document.getElementById('loading-overlay');
        if (overlay) overlay.remove();
    }
}

/**
     * Render the outline tree with checkboxes and edit controls
     */
function renderOutline(outline) {
    const container = document.getElementById('outline-container');
    const outlineError = document.getElementById('outline-error');
    if (outlineError) {
        outlineError.classList.add('d-none');
    }
    container.innerHTML = '';

    // Course Title Header (escape user-provided content)
    const courseTitle = escapeHtml(outline.title || currentConfig.subject);
    const titleDiv = document.createElement('div');
    titleDiv.className = "d-flex align-items-center mb-3";
    titleDiv.innerHTML = `
        <h5 class="mb-0 fw-bold flex-grow-1">${courseTitle}</h5>
        <span class="badge bg-info">${outline.units?.length || 0} Units</span>
    `;
    container.appendChild(titleDiv);

    // Description if available (use textContent for safety)
    if (outline.description) {
        const descP = document.createElement('p');
        descP.className = "text-muted mb-3";
        descP.textContent = outline.description;
        container.appendChild(descP);
    }

    // Units
    if (!outline.units) outline.units = [];

    outline.units.forEach((unit, uIndex) => {
        const unitDiv = document.createElement('div');
        unitDiv.className = 'unit-item';
        unitDiv.id = `unit-${uIndex}`;

        let lessonsHtml = '';
        if (unit.lessons && unit.lessons.length > 0) {
            unit.lessons.forEach((lesson, lIndex) => {
                // Escape all user-provided content
                const lessonTitle = escapeHtml(lesson.title);
                const lessonDuration = escapeHtml(lesson.duration || '30m');
                const objectives = lesson.learning_objectives?.map(obj => escapeHtml(obj)).join(', ') || '';

                lessonsHtml += `
                    <div class="lesson-item" id="lesson-${uIndex}-${lIndex}">
                        <div class="d-flex align-items-center flex-grow-1">
                            <input type="checkbox" checked class="form-check-input me-2 lesson-check" 
                                data-unit="${uIndex}" data-lesson="${lIndex}" aria-label="${lessonTitle}">
                            <div>
                                <span class="fw-medium">${lessonTitle}</span>
                                <small class="text-muted ms-2">(${lessonDuration})</small>
                                ${objectives ? `<br><small class="text-secondary">${objectives}</small>` : ''}
                            </div>
                        </div>
                        <span class="badge bg-light text-dark border">Lesson</span>
                    </div>
                `;
            });
        } else {
            lessonsHtml = '<div class="text-muted p-2"><em>No lessons in this unit</em></div>';
        }

        // Escape unit title
        const unitTitle = escapeHtml(unit.title);
        unitDiv.innerHTML = `
            <div class="unit-header">
                <div class="d-flex align-items-center">
                    <strong>${unitTitle}</strong>
                </div>
                <div class="d-flex align-items-center gap-2">
                    <span class="badge bg-secondary">${unit.lessons ? unit.lessons.length : 0} Lessons</span>
                    <button class="btn btn-sm btn-outline-secondary" onclick="addLessonToUnit(${uIndex})" title="Add Lesson">
                        + Lesson
                    </button>
                </div>
            </div>
            <div class="lesson-list">
                ${lessonsHtml}
            </div>
        `;
        container.appendChild(unitDiv);
    });
}


/**
 * Add a custom unit to the outline
 */
async function addCustomUnit() {
    // Ensure outline exists before adding units
    if (!generatedOutline) {
        generatedOutline = { title: currentConfig.subject || 'New Course', units: [] };
    }

    const unitTitle = await showPrompt('Enter unit title:', '', 'Add Unit');
    if (!unitTitle || !unitTitle.trim()) return;

    if (!generatedOutline.units) {
        generatedOutline.units = [];
    }

    generatedOutline.units.push({
        title: unitTitle.trim(),
        lessons: []
    });

    renderOutline(generatedOutline);
    persistCourse();
}

/**
 * Add a lesson to a specific unit
 */
async function addLessonToUnit(unitIndex) {
    const lessonTitle = await showPrompt('Enter lesson title:', '', 'Add Lesson');
    if (!lessonTitle || !lessonTitle.trim()) return;

    if (!generatedOutline.units[unitIndex].lessons) {
        generatedOutline.units[unitIndex].lessons = [];
    }

    generatedOutline.units[unitIndex].lessons.push({
        title: lessonTitle.trim(),
        duration: '30m',
        learning_objectives: []
    });

    renderOutline(generatedOutline);
    persistCourse();
}

// === Stage 3: Cascade Generation ===

async function proceedToGeneration() {
    if (generationRunning || courseOwner !== SLMClient.account()) return;
    const checked = Array.from(document.querySelectorAll('.lesson-check:checked'));
    if (!checked.length) { showError('Please select at least one lesson.'); return; }
    if (!generationTasks.length) generationTasks = checked.map(box => ({
        unit: Number(box.dataset.unit), lesson: Number(box.dataset.lesson), status: 'pending'
    }));
    generationRunning = true;
    try {
        if (!createdStudyPlanId) await createStudyPlanShell();
        document.getElementById('stage-2').classList.add('hidden');
        document.getElementById('stage-3').classList.remove('hidden');
        document.getElementById('course-workflow').classList.remove('d-none');
        await startCascade();
    } catch (error) { showError(error.message); }
    finally { generationRunning = false; persistCourse(); }
}

/**
 * Create a Study Plan to hold generated content
 */
async function createStudyPlanShell() {
    const plan = await SLMClient.request('/api/study-plans/', {
        method: 'POST', headers: getAuthHeaders(), body: JSON.stringify({
            title: generatedOutline.title || currentConfig.subject,
            description: generatedOutline.description || '', is_public: false,
            phases: generatedOutline.units.map(unit => ({ name: unit.title, content_ids: [] }))
        })
    });
    if (!plan?.id) throw new Error('The study plan was not saved. Please retry.');
    createdStudyPlanId = plan.id;
    persistCourse();
    log(`Study plan draft saved (${createdStudyPlanId}).`);
}

/**
 * Start the cascading content generation process
 */
async function startCascade() {
    totalGenerationTasks = generationTasks.length;
    completedTasks = generationTasks.filter(task => task.status === 'saved').length;
    failedTasks = 0;
    for (const task of generationTasks) {
        if (task.status === 'saved') continue;
        const unit = generatedOutline.units[task.unit];
        const lesson = unit.lessons[task.lesson];
        task.status = 'running'; persistCourse();
        const success = await generateAndSaveLesson(lesson, task.unit);
        task.status = success ? 'saved' : 'failed';
        if (success) completedTasks++; else failedTasks++;
        persistCourse();
        updateProgress(Math.round(completedTasks / totalGenerationTasks * 100), `${completedTasks}/${totalGenerationTasks} saved; ${failedTasks} failed.`);
    }
    finishGeneration(completedTasks === 0);
    document.getElementById('retry-generation').classList.toggle('d-none', failedTasks === 0);
}

async function generateAndSaveLesson(lesson, phaseIndex) {
    log(`Generating: ${lesson.title}`);
    try {
        const data = await SLMClient.request('/api/generate/full-topic-package', {
            method: 'POST', headers: getAuthHeaders(), body: JSON.stringify({
                subject: currentConfig.subject, topic_name: lesson.title,
                grade_level: currentConfig.grade_level,
                learning_objectives: lesson.learning_objectives || [`Understand ${lesson.title}`],
                include_lesson: true, include_exercises: true, include_assessment: false,
                source_material: sourceMaterialText, auto_save: true,
                study_plan_id: createdStudyPlanId, phase_index: phaseIndex
            })
        });
        if (!data?.success || !data.saved_content_ids?.length) {
            throw new Error('Some items could not be generated or saved. Retry keeps the saved items.');
        }
        log(`Saved: ${lesson.title}`);
        return true;
    } catch (error) {
        log(`Failed: ${lesson.title}. ${error.message}`, 'error');
        return false;
    }
}
window.retryCourseGeneration = async () => {
    if (generationRunning || courseOwner !== SLMClient.account()) return;
    generationRunning = true;
    try { await startCascade(); } finally { generationRunning = false; }
};
window.courseWorkflow = async action => {
    if (!createdStudyPlanId || generationRunning) return;
    try {
        if (action === 'publish' && !await showConfirm(SLMClient.message('publish_course_confirm', 'Publish this reviewed course for authorized learners?'))) return;
        await SLMClient.request(`/api/study-plans/${createdStudyPlanId}/workflow`, {
            method: 'POST', headers: getAuthHeaders(), body: JSON.stringify({ action })
        });
        showToast(SLMClient.message(action === 'publish' ? 'published' : 'reviewed', action === 'publish' ? 'Published successfully.' : 'Review recorded. You can publish when ready.'), 'success');
        if (action === 'publish') SLMClient.drafts.remove('course', 'designer', 'active');
    } catch (error) { showError(error.message); }
};

// === Helper Functions ===

/**
 * Update progress bar and status text
 */
function updateProgress(percent, status) {
    const bar = document.getElementById('gen-progress-bar');
    if (bar) {
        bar.style.width = `${percent}%`;
        bar.textContent = `${percent}%`;
        bar.setAttribute('aria-valuenow', percent);
    }

    const statusText = document.getElementById('gen-status-text');
    if (statusText) {
        statusText.textContent = status;
    }
}

/**
 * Update the live preview panel
 */
function updatePreview(html) {
    const preview = document.getElementById('live-preview');
    if (preview) {
        preview.innerHTML = SLMRender.html(html);
    }
}

/**
 * Log message to the generation log panel
 */
function log(msg, type = 'info') {
    const logDiv = document.getElementById('gen-log');
    if (!logDiv) return;

    const entry = document.createElement('div');
    const timestamp = new Date().toLocaleTimeString();
    entry.textContent = `[${timestamp}] ${msg}`;

    if (type === 'error') entry.style.color = '#ff6b6b';
    if (type === 'warn') entry.style.color = '#fcc419';
    if (type === 'success') entry.style.color = '#51cf66';

    logDiv.appendChild(entry);
    logDiv.scrollTop = logDiv.scrollHeight;
}

/**
 * Escape HTML to prevent XSS attacks
 */
function escapeHtml(unsafe) { return SLMRender.escape(unsafe); }

/**
 * Show error message to user
 */
function showError(message) {
    const errorEl = document.getElementById('course-designer-error');
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.classList.remove('d-none');
        return;
    }
    if (typeof showToast === 'function') {
        showToast(message, 'danger');
    } else {
        console.error(message);
    }
}

function showOutlineError(message) {
    const outlineError = document.getElementById('outline-error');
    if (outlineError) {
        outlineError.textContent = message;
        outlineError.classList.remove('d-none');
        return;
    }
    showError(message);
}

/**
 * Mark generation as complete and enable finish button
 */
function finishGeneration(allFailed = false) {
    const btn = document.getElementById('finish-btn');
    if (btn) {
        btn.classList.remove('disabled');

        if (allFailed || failedTasks > 0) {
            btn.classList.add('btn-warning');
            btn.textContent = "⚠️ Return to Dashboard";
        } else {
            btn.classList.remove('btn-primary');
            btn.classList.add('btn-success');
            btn.textContent = "🎉 View Course in Library";
        }

        // Update link to go to study plans
        if (createdStudyPlanId) {
            btn.href = `/dashboard.html#study-plans`;
        }
    }

    if (allFailed) {
        updatePreview(`
            <div class="text-center text-danger">
                <h4>⚠️ Generation Failed</h4>
                <p>Unable to generate content. Please check your AI service configuration.</p>
            </div>
        `);
    } else {
        updatePreview(`
            <div class="text-center text-success">
                <h4>Draft generation finished</h4>
                <p>${completedTasks}/${totalGenerationTasks} lessons saved. Review each item in the library before publishing.</p>
            </div>
        `);
    }
}

/**
 * Get authentication headers for API requests
 */
function getAuthHeaders(isMultipart = false) {
    const token = AuthService.getToken();
    const headers = {
        'Authorization': `Bearer ${token}`
    };
    if (!isMultipart) {
        headers['Content-Type'] = 'application/json';
    }
    return headers;
}

/**
 * Restart the designer wizard
 */
async function restartDesigner() {
    if (completedTasks > 0) {
        const confirmed = await showConfirm(
            'You have generated content. Are you sure you want to start over?',
            'Confirm Restart',
            'Start Over',
            'Cancel',
            true
        );
        if (!confirmed) return;
    }
    window.location.reload();
}

function renderSourceCoverage() {
    const status = document.getElementById('source-coverage');
    if (!status) return;
    status.classList.toggle('d-none', !sourceCoverage);
    if (!sourceCoverage) return;
    const partial = sourceCoverage.coverage === 'partial' || sourceCoverage.truncated || sourceCoverage.unreadable_pages?.length;
    status.className = 'alert ' + (partial ? 'alert-warning' : 'alert-info');
    const prefix = SLMClient.message(partial ? 'source_partial' : 'source_extracted', partial ? 'Partial source: some material was not included.' : 'Source text extracted; review it before generation.');
    const references = (sourceCoverage.sections || []).map(section => section.reference).join(', ');
    status.textContent = `${prefix} ${sourceCoverage.char_count || 0} ${SLMClient.message('characters', 'characters')}. ${references}`;
    if (sourceCoverage.unreadable_pages?.length) status.textContent += ` ${SLMClient.message('unreadable_pages', 'Unreadable pages')}: ${sourceCoverage.unreadable_pages.join(', ')}.`;
}
