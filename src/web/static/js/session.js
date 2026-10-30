let sessionId = null;
let timerInterval = null;
let startTime = Date.now();
let contentId = null;
let authToken = null;

// Plan-aware session variables
let planId = null;
let planContents = [];     // Array of content items in order
let currentContentIndex = 0;
let completedContentIds = [];

// Notes auto-save
let notesAutoSaveTimeout = null;
const NOTES_SAVE_KEY_PREFIX = 'session_notes_';

// I18n helper (fallback if I18n not available)
const t = (key, params = {}) => {
    if (typeof I18n !== 'undefined' && I18n.t) {
        return I18n.t(key, params);
    }
    // Fallback messages
    const fallbacks = {
        'session.plan_complete': '🎉 Congratulations! You have completed this study plan!',
        'session.review_submitted': 'Review submitted! Spaced repetition updated.',
        'session.error_review': 'Error submitting review',
        'session.error_session_save': 'Error saving session',
        'session.error_network': 'Network error ending session'
    };
    return fallbacks[key] || key;
};

/**
 * Initialize notes auto-save functionality
 */
function initNotesAutoSave() {
    const notesTextarea = document.getElementById('session-notes');
    if (!notesTextarea || !contentId) return;

    // Load saved notes from localStorage
    const savedNotes = localStorage.getItem(NOTES_SAVE_KEY_PREFIX + contentId);
    if (savedNotes) {
        notesTextarea.value = savedNotes;
        updateNotesStatus('loaded');
    }

    // Set up auto-save on input
    notesTextarea.addEventListener('input', () => {
        updateNotesStatus('typing');

        // Debounce save - wait 1.5 seconds after last keystroke
        clearTimeout(notesAutoSaveTimeout);
        notesAutoSaveTimeout = setTimeout(() => {
            saveNotesToLocal(notesTextarea.value);
        }, 1500);
    });
}

/**
 * Save notes to localStorage and sync to server
 */
async function saveNotesToLocal(notes) {
    if (!contentId) return;
    localStorage.setItem(NOTES_SAVE_KEY_PREFIX + contentId, notes);

    // Also sync to server if session is active
    if (sessionId && authToken) {
        try {
            await fetch(`/api/learning/${sessionId}/notes`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${authToken}`
                },
                body: JSON.stringify({ notes: notes })
            });
            updateNotesStatus('synced');
        } catch (e) {
            console.warn('Failed to sync notes to server:', e);
            updateNotesStatus('saved'); // Still show saved locally
        }
    } else {
        updateNotesStatus('saved');
    }
}


/**
 * Update the notes save status indicator
 */
function updateNotesStatus(status) {
    const statusEl = document.getElementById('notes-save-status');
    const lastSavedEl = document.getElementById('notes-last-saved');
    if (!statusEl) return;

    switch (status) {
        case 'typing':
            statusEl.innerHTML = '✍️ Typing...';
            statusEl.className = 'text-warning';
            break;
        case 'saved':
            statusEl.innerHTML = '✅ Saved';
            statusEl.className = 'text-success';
            if (lastSavedEl) {
                lastSavedEl.textContent = new Date().toLocaleTimeString();
            }
            // Reset to neutral after 3 seconds
            setTimeout(() => {
                statusEl.innerHTML = '📝 Notes auto-saved';
                statusEl.className = 'text-muted';
            }, 3000);
            break;
        case 'synced':
            statusEl.innerHTML = '☁️ Synced';
            statusEl.className = 'text-primary';
            if (lastSavedEl) {
                lastSavedEl.textContent = new Date().toLocaleTimeString();
            }
            setTimeout(() => {
                statusEl.innerHTML = '📝 Notes synced to server';
                statusEl.className = 'text-muted';
            }, 3000);
            break;
        case 'loaded':
            statusEl.innerHTML = '📥 Loaded from draft';
            statusEl.className = 'text-info';
            setTimeout(() => {
                statusEl.innerHTML = '📝 Notes auto-saved';
                statusEl.className = 'text-muted';
            }, 3000);
            break;
        default:
            statusEl.innerHTML = '📝 Notes auto-saved';
            statusEl.className = 'text-muted';
    }
}


/**
 * Award XP to the current user for completing an activity
 * @param {number} amount - XP amount to award
 * @param {string} reason - Reason for the award (e.g., 'lesson_complete', 'exercise_complete')
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
            console.log(`🎮 XP awarded: +${amount} (${reason}). Total: ${result.total_xp}, Level: ${result.level}`);
        }
    } catch (e) {
        console.warn('Failed to award XP:', e);
    }
}

// ===== ANNOTATIONS FUNCTIONS =====
let annotationsCache = [];

/**
 * Load annotations for the current content
 */
async function loadAnnotations() {
    if (!contentId || !authToken) return;

    try {
        const response = await fetch(`/api/annotations?content_id=${contentId}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (response.ok) {
            annotationsCache = await response.json();
            renderAnnotations();
            updateAnnotationCount();
        }
    } catch (e) {
        console.warn('Failed to load annotations:', e);
    }
}

/**
 * Add a new annotation for the current content
 */
async function addAnnotation() {
    const text = document.getElementById('annotation-input')?.value?.trim();
    const annotationType = document.getElementById('annotation-type')?.value || 'comment';
    const isPublic = document.getElementById('annotation-public')?.checked ?? true;

    if (!text) {
        return;
    }

    if (!contentId || !authToken) {
        console.error('Cannot add annotation: missing content ID or auth token');
        return;
    }

    try {
        const response = await fetch('/api/annotations', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                content_id: parseInt(contentId),
                annotation_text: text,
                annotation_type: annotationType,
                is_public: isPublic,
                text_selection_start: null,  // Could be populated if implementing text selection
                text_selection_end: null
            })
        });

        if (response.ok) {
            const newAnnotation = await response.json();
            annotationsCache.unshift(newAnnotation);
            renderAnnotations();
            updateAnnotationCount();

            // Clear input
            document.getElementById('annotation-input').value = '';
        } else {
            console.error('Failed to add annotation:', response.status);
        }
    } catch (e) {
        console.error('Error adding annotation:', e);
    }
}
window.addAnnotation = addAnnotation;

/**
 * Delete an annotation by ID
 * @param {number} annotationId - The annotation ID to delete
 */
async function deleteAnnotation(annotationId) {
    if (!authToken) return;

    try {
        const response = await fetch(`/api/annotations/${annotationId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (response.ok) {
            annotationsCache = annotationsCache.filter(a => a.id !== annotationId);
            renderAnnotations();
            updateAnnotationCount();
        }
    } catch (e) {
        console.error('Error deleting annotation:', e);
    }
}
window.deleteAnnotation = deleteAnnotation;

/**
 * Render annotations in the annotations panel
 */
function renderAnnotations() {
    const container = document.getElementById('annotations-list');
    if (!container) return;

    if (annotationsCache.length === 0) {
        container.innerHTML = `
            <div class="text-muted text-center py-3 small">
                <div>No annotations yet</div>
                <div class="mt-1">Add comments or questions about this content</div>
            </div>
        `;
        return;
    }

    // Get current user ID from localStorage to check ownership
    const currentUserData = localStorage.getItem('user_data');
    let currentUserId = null;
    if (currentUserData) {
        try {
            currentUserId = JSON.parse(currentUserData).id;
        } catch (e) { }
    }

    const typeIcons = {
        'comment': '💬',
        'question': '❓',
        'highlight': '🔖',
        'note': '📝'
    };

    container.innerHTML = annotationsCache.map(annotation => {
        const typeIcon = typeIcons[annotation.annotation_type] || '💬';
        const isOwner = annotation.user_id === currentUserId;
        const timeAgo = formatTimeAgo(annotation.created_at);

        return `
            <div class="annotation-item p-2 border-bottom" data-id="${annotation.id}">
                <div class="d-flex justify-content-between align-items-start">
                    <span class="badge bg-light text-dark me-1">${typeIcon}</span>
                    <small class="text-muted flex-grow-1">${timeAgo}</small>
                    ${isOwner ? `<button class="btn btn-sm btn-link text-danger p-0" onclick="deleteAnnotation(${annotation.id})" title="Delete">×</button>` : ''}
                </div>
                <div class="annotation-text mt-1 small">${escapeHtml(annotation.annotation_text)}</div>
                ${annotation.is_public === false ? '<small class="text-muted"><em>Private</em></small>' : ''}
            </div>
        `;
    }).join('');
}

/**
 * Update the annotation count badge
 */
function updateAnnotationCount() {
    const badge = document.getElementById('annotation-count');
    if (badge) {
        const count = annotationsCache.length;
        badge.textContent = count;
        badge.style.display = count > 0 ? 'inline' : 'none';
    }
}

/**
 * Format a timestamp to relative time (e.g., "5 min ago")
 * @param {string} timestamp - ISO timestamp
 * @returns {string} Formatted relative time
 */
function formatTimeAgo(timestamp) {
    if (!timestamp) return '';
    const now = new Date();
    const then = new Date(timestamp);
    const diffMs = now - then;
    const diffMin = Math.floor(diffMs / 60000);
    const diffHour = Math.floor(diffMs / 3600000);
    const diffDay = Math.floor(diffMs / 86400000);

    if (diffMin < 1) return 'just now';
    if (diffMin < 60) return `${diffMin} min ago`;
    if (diffHour < 24) return `${diffHour} hr ago`;
    if (diffDay < 7) return `${diffDay} day${diffDay > 1 ? 's' : ''} ago`;
    return then.toLocaleDateString();
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Check for previous sessions with notes for this content
 * @returns {Object|null} Most recent completed session with notes or null
 */
async function checkPreviousSession() {
    if (!contentId || !authToken) return null;

    try {
        const response = await fetch(`/api/learning/history/${contentId}?limit=1`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (response.ok) {
            const history = await response.json();
            // Return most recent completed session with notes
            const previous = history.find(s => s.status === 'completed' && s.notes);
            return previous || null;
        }
    } catch (e) {
        console.warn('Failed to check session history:', e);
    }
    return null;
}

/**
 * Show modal asking user to restore or restart session
 * @param {Object} previousSession - The previous session data
 * @returns {Promise<string>} 'restore' or 'restart'
 */
function showSessionChoiceModal(previousSession) {
    return new Promise((resolve) => {
        // Create modal HTML if it doesn't exist
        let modal = document.getElementById('sessionChoiceModal');
        if (!modal) {
            modal = document.createElement('div');
            modal.className = 'modal fade';
            modal.id = 'sessionChoiceModal';
            modal.tabIndex = -1;
            modal.innerHTML = `
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">📚 Previous Session Found</h5>
                        </div>
                        <div class="modal-body">
                            <p>You have a previous session with notes from <span id="prev-session-date"></span>:</p>
                            <div class="bg-light p-2 rounded mb-3 small" style="max-height: 100px; overflow-y: auto;">
                                <em id="prev-session-notes-preview"></em>
                            </div>
                            <p>Would you like to restore your previous notes or start fresh?</p>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-outline-secondary" id="restart-btn">
                                🔄 Start Fresh
                            </button>
                            <button type="button" class="btn btn-primary" id="restore-btn">
                                📥 Restore Notes
                            </button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        // Populate previous session info
        const dateEl = document.getElementById('prev-session-date');
        const notesEl = document.getElementById('prev-session-notes-preview');

        if (dateEl && previousSession.start_time) {
            dateEl.textContent = new Date(previousSession.start_time).toLocaleString();
        }
        if (notesEl && previousSession.notes) {
            notesEl.textContent = previousSession.notes.substring(0, 200) + (previousSession.notes.length > 200 ? '...' : '');
        }

        // Set up button handlers
        const restoreBtn = document.getElementById('restore-btn');
        const restartBtn = document.getElementById('restart-btn');
        const bsModal = new bootstrap.Modal(modal);

        restoreBtn.onclick = () => {
            bsModal.hide();
            resolve('restore');
        };
        restartBtn.onclick = () => {
            bsModal.hide();
            resolve('restart');
        };

        bsModal.show();
    });
}

/**
 * Restore a previous session and load its notes
 * @param {number} previousSessionId - ID of session to restore
 */
async function restoreSession(previousSessionId) {
    try {
        const response = await fetch(`/api/learning/${previousSessionId}/restore`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (response.ok) {
            const session = await response.json();
            sessionId = session.id;
            startTimer();

            // Auto-save notes logic
            const notesArea = document.getElementById('session-notes');
            if (notesArea) {
                notesArea.value = localStorage.getItem(`notes_${contentId}`) || '';
                notesArea.addEventListener('input', (e) => {
                    localStorage.setItem(`notes_${contentId}`, e.target.value);
                    const status = document.getElementById('notes-save-status');
                    if (status) {
                        status.textContent = 'Saving...';
                        setTimeout(() => status.textContent = 'Notes auto-saved', 1000);
                    }
                });
            }

            // Load annotations
            loadAnnotations();

            // Initialize notes auto-save (this call might be redundant if the above block handles it)
            // initNotesAutoSave(); // Keeping this commented out as the new block seems to replace its functionality
        } else {
            console.error('Failed to restore session');
            // Fall back to starting new session
            location.reload();
        }
    } catch (e) {
        console.error('Error restoring session:', e);
        location.reload();
    }
}

async function initSession() {
    const urlParams = new URLSearchParams(window.location.search);
    contentId = urlParams.get('content_id');
    planId = urlParams.get('plan_id');

    authToken = AuthService.getToken();
    if (!authToken || !AuthService.isAuthenticated()) {
        window.location.href = '/login.html';
        return;
    }

    if (!contentId) {
        showErrorState("Session Not Found", "The learning session you requested could not be loaded.");
        return;
    }

    // If plan_id provided, load plan context for guided navigation
    if (planId) {
        await loadPlanContext(planId, contentId);
    }

    // Load Content Details
    try {
        const contentResp = await fetch(`/api/content/${contentId}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!contentResp.ok) {
            showErrorState("Content Not Found", "The requested learning content could not be found.");
            return;
        }

        const content = await contentResp.json();
        document.getElementById('session-content-title').textContent = content.title;
        // Handle content_data which might be JSON object, JSON string, or plain text
        let bodyText = "No content data.";
        if (content.content_data) {
            // Helper function to extract readable text from parsed JSON
            const extractContent = (parsed) => {
                if (!parsed || typeof parsed !== 'object') return null;

                // Direct text fields (common patterns)
                if (parsed.content && typeof parsed.content === 'string') return parsed.content;
                if (parsed.text && typeof parsed.text === 'string') return parsed.text;
                if (parsed.body && typeof parsed.body === 'string') return parsed.body;
                if (parsed.lesson && typeof parsed.lesson === 'string') return parsed.lesson;
                if (parsed.description && typeof parsed.description === 'string') return parsed.description;

                // AI enhancement wrapper
                if (parsed.enhanced_content) {
                    const inner = extractContent(parsed.enhanced_content);
                    if (inner) return inner;
                }

                // Nested content object
                if (parsed.content && typeof parsed.content === 'object') {
                    const inner = extractContent(parsed.content);
                    if (inner) return inner;
                }

                // AI-generated format with sections array
                if (parsed.sections && Array.isArray(parsed.sections)) {
                    let markdown = '';
                    parsed.sections.forEach(section => {
                        if (section.title) markdown += `## ${section.title}\n\n`;
                        if (section.content) markdown += `${section.content}\n\n`;
                        if (section.text) markdown += `${section.text}\n\n`;
                    });
                    if (parsed.summary) markdown += `## Summary\n\n${parsed.summary}\n\n`;
                    if (parsed.vocabulary && Array.isArray(parsed.vocabulary)) {
                        markdown += `## Key Terms\n\n`;
                        parsed.vocabulary.forEach(term => {
                            markdown += `- **${term.term || term}**: ${term.definition || ''}\n`;
                        });
                    }
                    if (parsed.key_concepts && Array.isArray(parsed.key_concepts)) {
                        markdown += `## Key Concepts\n\n`;
                        parsed.key_concepts.forEach(concept => {
                            markdown += `- ${concept}\n`;
                        });
                    }
                    return markdown.trim() || null;
                }

                // Topics array format
                if (parsed.topics && Array.isArray(parsed.topics)) {
                    return parsed.topics.map(t => `## ${t.title || t}\n\n${t.content || t.description || ''}`).join('\n\n');
                }

                // Fallback to stringified JSON
                return null;
            };


            // Check if content_data is already an object (from some API responses)
            if (typeof content.content_data === 'object') {
                const extracted = extractContent(content.content_data);
                bodyText = extracted || JSON.stringify(content.content_data, null, 2);
            } else if (typeof content.content_data === 'string') {
                try {
                    const parsed = JSON.parse(content.content_data);
                    const extracted = extractContent(parsed);
                    bodyText = extracted || JSON.stringify(parsed, null, 2);
                } catch {
                    // Plain text
                    bodyText = content.content_data;
                }
            } else {
                // Fallback: stringify whatever it is
                bodyText = String(content.content_data);
            }
        }
        document.getElementById('session-content-body').innerHTML = marked.parse(bodyText);
        // Let's just use innerText for safety if marked isn't there, or pre
        if (typeof marked === 'undefined') {
            document.getElementById('session-content-body').innerHTML = `<pre>${bodyText}</pre>`;
        }
    } catch (e) {
        console.error("Failed to load content", e);
        showErrorState("Error Loading Content", "An unexpected error occurred while loading the content.");
        return;
    }

    // Check for previous sessions with notes (restore/restart logic)
    const previousSession = await checkPreviousSession();
    if (previousSession && previousSession.notes) {
        // Show restore/restart modal
        const choice = await showSessionChoiceModal(previousSession);
        if (choice === 'restore') {
            await restoreSession(previousSession.id);
            return; // restoreSession handles initialization
        }
        // Otherwise continue to start new session (restart)
    }

    // Start Session API
    try {
        const response = await fetch('/api/learning/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ content_id: parseInt(contentId) })
        });

        if (response.ok) {
            const session = await response.json();
            sessionId = session.id;
            startTimer();

            // Load annotations for this content
            loadAnnotations();

            // Initialize notes auto-save
            initNotesAutoSave();
        } else {
            console.error("Failed to start session tracking");
            // Non-blocking error, allow reading but warn
            // Still initialize notes auto-save even if session tracking fails
            initNotesAutoSave();
        }
    } catch (e) {
        console.error(e);
    }
}

function showErrorState(title, message) {
    const overlay = document.getElementById('error-overlay');
    const container = document.querySelector('.container-fluid');
    const nav = document.querySelector('.navbar-standalone');

    if (overlay) {
        overlay.querySelector('.error-title').textContent = title;
        overlay.querySelector('.error-text').textContent = message;
        overlay.classList.remove('d-none');
    }

    // Hide main UI
    if (container) container.classList.add('d-none');
    if (nav) nav.classList.add('d-none'); // Optional: hide nav on error or keep it
}

// Load study plan context for guided navigation
async function loadPlanContext(planId, currentContentId) {
    try {
        const response = await fetch(`/api/study-plans/${planId}/tree`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!response.ok) return;

        const plan = await response.json();
        document.getElementById('plan-title').textContent = plan.title;

        // Sort contents by phase_index then order_index
        planContents = (plan.contents || []).sort((a, b) => {
            if (a.phase_index !== b.phase_index) return a.phase_index - b.phase_index;
            return a.order_index - b.order_index;
        });

        // Load existing progress from backend
        try {
            const progressResp = await fetch(`/api/study-plans/${planId}/my-progress`, {
                headers: { 'Authorization': `Bearer ${authToken}` }
            });
            if (progressResp.ok) {
                const progress = await progressResp.json();
                completedContentIds = progress.completed_content_ids || [];
            }
        } catch (e) {
            console.warn('Could not load progress:', e);
        }

        // Find current content index
        currentContentIndex = planContents.findIndex(c => c.id === parseInt(currentContentId));
        if (currentContentIndex === -1) currentContentIndex = 0;

        // Render plan sidebar
        renderPlanSidebar();

        // Show plan UI elements
        document.getElementById('plan-sidebar-container').classList.remove('d-none');
        document.getElementById('plan-navigation').classList.remove('d-none');
        document.getElementById('main-content-col').classList.remove('col-md-9');
        document.getElementById('main-content-col').classList.add('col-md-6');
        document.getElementById('notes-sidebar-col').classList.remove('col-md-3');
        document.getElementById('notes-sidebar-col').classList.add('col-md-3');

        updateNavigationButtons();

    } catch (e) {
        console.error("Failed to load plan context", e);
    }
}

// Render the plan sidebar with content items
function renderPlanSidebar() {
    const container = document.getElementById('plan-contents-list');
    const typeIcons = { lesson: '📖', exercise: '✏️', assessment: '📝', qa: '❓' };

    container.innerHTML = planContents.map((item, idx) => {
        const isCurrent = idx === currentContentIndex;
        const isCompleted = completedContentIds.includes(item.id);
        const icon = typeIcons[item.content_type] || '📄';
        const statusIcon = isCompleted ? '✅' : (isCurrent ? '🔵' : '○');

        return `
            <div class="plan-content-item p-2 mb-1 rounded ${isCurrent ? 'bg-primary text-white' : 'bg-light'}"
                 style="cursor: pointer;" onclick="goToContent(${item.id})">
                <span class="me-2">${statusIcon}</span>
                <span class="me-1">${icon}</span>
                <span class="text-truncate" style="max-width: 150px; display: inline-block;">${item.title}</span>
            </div>
        `;
    }).join('');

    // Update progress text
    const completed = completedContentIds.length;
    document.getElementById('completed-count').textContent = `${completed}/${planContents.length} completed`;
}

// Update prev/next button states
function updateNavigationButtons() {
    const prevBtn = document.getElementById('prev-content-btn');
    const nextBtn = document.getElementById('next-content-btn');
    const positionText = document.getElementById('content-position');

    prevBtn.disabled = currentContentIndex <= 0;
    nextBtn.disabled = currentContentIndex >= planContents.length - 1;

    // Update button text for last item
    if (currentContentIndex >= planContents.length - 1) {
        nextBtn.textContent = '✅ Complete Plan';
    } else {
        nextBtn.textContent = 'Next →';
    }

    positionText.textContent = `${currentContentIndex + 1} of ${planContents.length}`;
}

// Save progress to backend
async function saveProgressToBackend(completedId) {
    if (!planId || !completedId) return;

    try {
        await fetch(`/api/study-plans/${planId}/progress`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                completed_content_id: parseInt(completedId)
            })
        });
    } catch (e) {
        console.error('Failed to save progress:', e);
    }
}

// Navigate to previous/next content in plan
window.navigatePlanContent = async function (direction) {
    const newIndex = currentContentIndex + direction;
    if (newIndex >= 0 && newIndex < planContents.length) {
        const nextContent = planContents[newIndex];
        // Mark current as completed before navigating
        if (!completedContentIds.includes(parseInt(contentId))) {
            completedContentIds.push(parseInt(contentId));
            // Save to backend for persistence
            await saveProgressToBackend(contentId);
            // Award XP for completing content
            await awardXP(10, 'content_complete');
        }
        // Navigate to new content
        window.location.href = `session_player.html?content_id=${nextContent.id}&plan_id=${planId}`;
    } else if (newIndex >= planContents.length) {
        // Plan complete!
        if (!completedContentIds.includes(parseInt(contentId))) {
            completedContentIds.push(parseInt(contentId));
            await saveProgressToBackend(contentId);
            // Award XP for plan completion (bonus)
            await awardXP(50, 'plan_complete');
        }
        showToast(t('session.plan_complete'), 'success', 2500);
        setTimeout(() => {
            window.location.href = 'dashboard.html';
        }, 2000);
    }
};

// Go to specific content in plan
window.goToContent = function (targetContentId) {
    if (targetContentId === parseInt(contentId)) return;
    window.location.href = `session_player.html?content_id=${targetContentId}&plan_id=${planId}`;
};

// Toggle plan sidebar visibility
window.togglePlanSidebar = function () {
    const sidebar = document.getElementById('plan-sidebar-container');
    const mainCol = document.getElementById('main-content-col');

    if (sidebar.classList.contains('d-none')) {
        sidebar.classList.remove('d-none');
        mainCol.classList.remove('col-md-9');
        mainCol.classList.add('col-md-6');
    } else {
        sidebar.classList.add('d-none');
        mainCol.classList.remove('col-md-6');
        mainCol.classList.add('col-md-9');
    }
};

function startTimer() {
    startTime = Date.now();
    timerInterval = setInterval(() => {
        const delta = Date.now() - startTime;
        const seconds = Math.floor(delta / 1000);
        const h = Math.floor(seconds / 3600).toString().padStart(2, '0');
        const m = Math.floor((seconds % 3600) / 60).toString().padStart(2, '0');
        const s = (seconds % 60).toString().padStart(2, '0');
        document.getElementById('session-timer').textContent = `${h}:${m}:${s}`;

        // Heartbeat every 30s
        if (seconds > 0 && seconds % 30 === 0) {
            sendHeartbeat();
        }
    }, 1000);
}

async function sendHeartbeat() {
    if (!sessionId) return;
    try {
        await fetch(`/api/learning/${sessionId}/heartbeat`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
    } catch (e) { console.warn("Heartbeat failed", e); }
}

window.endSessionUI = () => {
    const timerText = document.getElementById('session-timer').textContent;
    document.getElementById('final-time').textContent = timerText;
    new bootstrap.Modal(document.getElementById('endSessionModal')).show();
};

window.confirmEndSession = async () => {
    if (!contentId) return; // Need content ID for review

    const notes = document.getElementById('session-notes').value;
    const rating = document.getElementById('difficulty-rating').value;
    const urlParams = new URLSearchParams(window.location.search);
    const mode = urlParams.get('mode');

    try {
        if (mode === 'review') {
            // Submit Review to Mastery API
            const response = await fetch('/api/mastery/review', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${authToken}`
                },
                body: JSON.stringify({
                    content_id: parseInt(contentId),
                    rating: parseInt(rating),
                    actual_duration_min: Math.max(1, Math.floor((Date.now() - startTime) / 60000))
                })
            });

            if (response.ok) {
                showToast(t('session.review_submitted'), 'success', 2000);
                setTimeout(() => {
                    window.location.href = 'dashboard.html';
                }, 1500);
            } else {
                showToast(t('session.error_review'), 'danger');
            }
        } else {
            // Standard Session End
            if (!sessionId) return;
            const response = await fetch(`/api/learning/${sessionId}/end`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${authToken}`
                },
                body: JSON.stringify({
                    notes: notes,
                    difficulty_rating: parseInt(rating)
                })
            });

            if (response.ok) {
                // Award XP for session completion
                await awardXP(15, 'session_complete');
                window.location.href = 'dashboard.html';
            } else {
                showToast(t('session.error_session_save'), 'danger');
            }
        }
    } catch (e) {
        showToast(t('session.error_network'), 'danger');
    }
};

// Check for marked.js for markdown rendering
if (typeof marked === 'undefined') {
    // Dynamically load marked if not present (optional enhancement)
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/marked/marked.min.js';
    script.onload = () => {
        if (document.getElementById('session-content-body').textContent) {
            // re-render if content already loaded as pre
            // simplistic approach, really initSession should wait. 
        }
    };
    document.head.appendChild(script);
}

// --- Accessibility & Focus Mode ---

/**
 * Adjust the base font size for accessibility
 * @param {number} delta - Amount to change font size (+1 or -1)
 */
window.adjustFontSize = function (delta) {
    const contentBody = document.getElementById('session-content-body');
    if (!contentBody) return;

    const current = parseFloat(getComputedStyle(contentBody).fontSize);
    const newSize = Math.max(14, Math.min(24, current + (delta * 2))); // Limit between 14px and 24px
    contentBody.style.fontSize = newSize + 'px';

    // Store preference
    localStorage.setItem('session_font_size', newSize);
};

/**
 * Toggle Focus Mode - hides sidebars and centers content
 */
window.toggleFocusMode = function () {
    const body = document.body;
    const isFocusMode = body.classList.toggle('focus-mode');

    const planCol = document.getElementById('plan-sidebar-container');
    const noteCol = document.getElementById('notes-sidebar-col');
    const mainCol = document.getElementById('main-content-col');

    if (isFocusMode) {
        // Enter focus mode
        if (planCol) planCol.classList.add('d-none');
        if (noteCol) noteCol.classList.add('d-none');
        if (mainCol) {
            mainCol.classList.remove('col-md-9');
            mainCol.classList.add('col-12');
            mainCol.style.maxWidth = '800px';
            mainCol.style.margin = '0 auto';
        }
    } else {
        // Exit focus mode - restore layout
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('plan_id') && planCol) {
            planCol.classList.remove('d-none');
        }
        if (noteCol) noteCol.classList.remove('d-none');
        if (mainCol) {
            mainCol.classList.add('col-md-9');
            mainCol.classList.remove('col-12');
            mainCol.style.maxWidth = '';
            mainCol.style.margin = '';
        }
    }
};

// Restore font size preference on load
document.addEventListener('DOMContentLoaded', () => {
    const savedSize = localStorage.getItem('session_font_size');
    if (savedSize) {
        const contentBody = document.getElementById('session-content-body');
        if (contentBody) contentBody.style.fontSize = savedSize + 'px';
    }
});

document.addEventListener('DOMContentLoaded', initSession);
