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
let totalGenerationTasks = 0;
let completedTasks = 0;
let failedTasks = 0;  // Track failures for accurate status
let createdStudyPlanId = null;

// === Initialization ===
document.addEventListener('DOMContentLoaded', () => {
    // Check authentication
    if (!checkAuth()) {
        return;
    }
    if (!checkRole()) {
        return;
    }
    setupStage1();
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
                                data-unit="${uIndex}" data-lesson="${lIndex}">
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
}

// === Stage 3: Cascade Generation ===

async function proceedToGeneration() {
    // Count checked lessons
    const checkedLessons = document.querySelectorAll('.lesson-check:checked');
    if (checkedLessons.length === 0) {
        showError('Please select at least one lesson to generate.');
        return;
    }

    document.getElementById('stage-2').classList.add('hidden');
    document.getElementById('stage-3').classList.remove('hidden');
    document.getElementById('step-2-ind').classList.add('completed');
    document.getElementById('step-3-ind').classList.add('active');

    // Create Study Plan container first
    await createStudyPlanShell();

    // Start cascade generation
    await startCascade();
}

/**
 * Create a Study Plan to hold generated content
 */
async function createStudyPlanShell() {
    log("Creating Study Plan container...");

    try {
        const response = await fetch('/api/study-plans', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                title: generatedOutline.title || currentConfig.subject,
                description: generatedOutline.description || `AI-generated course for ${currentConfig.subject}`,
                is_public: false,
                phases: generatedOutline.units.map((unit, idx) => ({
                    name: unit.title,
                    content_ids: [] // Will be populated as content is created
                }))
            })
        });

        if (response.ok) {
            const plan = await response.json();
            createdStudyPlanId = plan.id;
            log(`✓ Study Plan created (ID: ${createdStudyPlanId})`);
        } else {
            const errData = await response.json().catch(() => ({}));
            log(`⚠ Study Plan creation failed: ${errData.detail || 'Unknown error'}`, "warn");
        }
    } catch (e) {
        log("⚠ Error creating Study Plan: " + e.message, "warn");
    }
}

/**
 * Start the cascading content generation process
 */
async function startCascade() {
    const checkedLessons = document.querySelectorAll('.lesson-check:checked');
    totalGenerationTasks = checkedLessons.length;
    completedTasks = 0;
    failedTasks = 0;  // Reset failure count

    updateProgress(0, `Starting generation of ${totalGenerationTasks} lessons...`);
    log(`Starting cascade generation for ${totalGenerationTasks} lessons`);

    // Process sequentially to avoid rate limiting and maintain order
    for (const checkbox of checkedLessons) {
        const uIndex = parseInt(checkbox.dataset.unit);
        const lIndex = parseInt(checkbox.dataset.lesson);
        const unit = generatedOutline.units[uIndex];
        const lesson = unit.lessons[lIndex];

        const success = await generateAndSaveLesson(lesson, unit.title);

        completedTasks++;
        if (!success) failedTasks++;

        const percent = Math.round((completedTasks / totalGenerationTasks) * 100);
        updateProgress(percent, `${success ? 'Generated' : 'Failed'}: ${escapeHtml(lesson.title)}`);
    }

    // Show accurate completion status
    const successCount = completedTasks - failedTasks;
    if (failedTasks === 0) {
        updateProgress(100, "All content generated successfully!");
        log("✓ Course generation complete!");
    } else if (successCount > 0) {
        updateProgress(100, `Completed with ${failedTasks} errors. ${successCount}/${completedTasks} lessons saved.`);
        log(`⚠ Completed with ${failedTasks} failures. Check AI service configuration.`, "warn");
    } else {
        updateProgress(100, `Generation failed: All ${failedTasks} lessons failed. Check AI service.`);
        log(`✗ All lessons failed to generate. Please check AI service configuration.`, "error");
    }

    finishGeneration(failedTasks === totalGenerationTasks);
}

/**
 * Generate and save content for a single lesson
 */
async function generateAndSaveLesson(lesson, unitTitle) {
    log(`Generating: ${lesson.title}...`);
    updatePreview(`<div class="text-center"><div class="spinner-border spinner-border-sm"></div><p class="mt-2">Generating ${lesson.title}...</p></div>`);

    try {
        // 1. Generate Content via AI
        const response = await fetch('/api/generate/topic-content', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                subject: currentConfig.subject,
                topic_name: lesson.title,
                grade_level: currentConfig.grade_level,
                learning_objectives: lesson.learning_objectives || [`Understand ${lesson.title}`],
                content_types: ['lesson', 'exercise'],
                source_material: sourceMaterialText
            })
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || 'AI Generation failed');
        }

        const data = await response.json();

        // 2. Save Lesson Content
        if (data.lesson) {
            const lessonSaved = await saveContentItem({
                title: data.lesson.title || lesson.title,
                type: 'lesson',
                content_data: data.lesson,
                study_plan_id: createdStudyPlanId
            });

            if (lessonSaved) {
                updatePreview(`
                    <div class="mb-2"><strong>${lesson.title}</strong></div>
                    <div class="small text-muted">${data.lesson.introduction?.substring(0, 150) || ''}...</div>
                `);
            }
        }

        // 3. Save Exercises
        if (data.exercises && data.exercises.length > 0) {
            await saveContentItem({
                title: `Exercises: ${lesson.title}`,
                type: 'exercise',
                content_data: { questions: data.exercises },
                study_plan_id: createdStudyPlanId
            });
        }

        log(`✓ Completed: ${lesson.title}`);
        return true;  // Success

    } catch (e) {
        log(`✗ Failed: ${lesson.title} - ${e.message}`, "error");
        return false;  // Failure
    }
}

/**
 * Save a content item to the database
 */
async function saveContentItem(itemData) {
    try {
        const response = await fetch('/api/content', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                title: itemData.title,
                type: itemData.type,           // Using 'type' alias
                data: itemData.content_data,   // Using 'data' alias  
                difficulty: 1,
                is_personal: false,
                study_plan_id: itemData.study_plan_id
            })
        });

        if (!response.ok) {
            console.warn("Failed to save content item:", itemData.title);
            return false;
        }
        return true;
    } catch (e) {
        console.error("Save error:", e);
        return false;
    }
}

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
        preview.innerHTML = html;
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
function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return String(unsafe)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

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

        if (allFailed) {
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
                <h4>✓ Complete!</h4>
                <p>All lessons have been generated and saved.</p>
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
