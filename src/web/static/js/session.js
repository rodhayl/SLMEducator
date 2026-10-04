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

// Notes belong to a server session and the signed-in account, never just content.
let notesAutoSaveTimeout = null;
let sessionOwner = null;
let notesSyncQueue = Promise.resolve();
let endingSession = false;
const t = (key) => window.I18n?.t?.(key) || key;
const sessionMessage = (key, fallback) => SLMClient.message(key, fallback);

function saveNotesDraft(notes) {
    if (!sessionId || sessionOwner !== SLMClient.account()) return false;
    return SLMClient.drafts.write('notes', contentId, sessionId, { notes });
}

async function initNotesAutoSave(serverNotes = '') {
    const area = document.getElementById('session-notes');
    if (!area || !sessionId) return;
    area.value = serverNotes || '';
    const draft = SLMClient.drafts.read('notes', contentId, sessionId);
    if (draft && draft.notes !== area.value) {
        const choice = await SLMClient.chooseDraft();
        if (choice === 'restore') area.value = draft.notes;
        else if (choice === 'discard') SLMClient.drafts.remove('notes', contentId, sessionId);
        else { window.location.href = '/dashboard.html'; return; }
    }
    area.disabled = false;
    await window.SLMPractice?.bindAttempt(sessionOwner, contentId, sessionId);
    area.oninput = () => {
        updateNotesStatus(saveNotesDraft(area.value) ? 'local' : 'storage-error');
        clearTimeout(notesAutoSaveTimeout);
        notesAutoSaveTimeout = setTimeout(() => saveNotesToLocal(area.value), 1500);
    };
    window.addEventListener('pagehide', () => saveNotesDraft(area.value));
}

function saveNotesToLocal(notes) {
    if (!sessionId || sessionOwner !== SLMClient.account()) return Promise.resolve(false);
    const localSaved = saveNotesDraft(notes);
    const targetSession = sessionId;
    notesSyncQueue = notesSyncQueue.catch(() => false).then(async () => {
        try {
            await SLMClient.request(`/api/learning/${targetSession}/notes`, {
                method: 'PATCH', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ notes })
            });
            if (document.getElementById('session-notes').value === notes) {
                SLMClient.drafts.remove('notes', contentId, targetSession);
                updateNotesStatus('synced');
            }
            return true;
        } catch (error) {
            updateNotesStatus(localSaved ? 'sync-error' : 'storage-error');
            return false;
        }
    });
    return notesSyncQueue;
}

function updateNotesStatus(status) {
    const node = document.getElementById('notes-save-status');
    if (!node) return;
    const labels = {
        local: sessionMessage('local_notes', 'Draft saved on this device; waiting for server.'),
        synced: sessionMessage('server_saved', 'Notes saved to server.'),
        'sync-error': sessionMessage('sync_failed', 'Server save failed. Your draft is kept on this device. Sign in again if needed, then retry.'),
        'storage-error': sessionMessage('storage_failed', 'Could not save a local draft. Keep this page open and retry.')
    };
    node.textContent = labels[status] || '';
    node.className = status.endsWith('error') ? 'text-danger' : 'text-secondary';
    if (status === 'synced') {
        const time = document.getElementById('notes-last-saved');
        if (time) time.textContent = new Date().toLocaleTimeString();
    }
}
window.retryNotesSave = () => saveNotesToLocal(document.getElementById('session-notes').value);

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
    const currentUserId = AuthService.getUser()?.id;

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
    const instant = SLMTime.epoch(timestamp);
    if (instant === null) return escapeHtml(SLMTime.format(timestamp));
    const diffMs = Date.now() - instant;
    const diffMin = Math.floor(diffMs / 60000);
    const diffHour = Math.floor(diffMs / 3600000);
    const diffDay = Math.floor(diffMs / 86400000);

    if (diffMin < 1) return 'just now';
    if (diffMin < 60) return `${diffMin} min ago`;
    if (diffHour < 24) return `${diffHour} hr ago`;
    if (diffDay < 7) return `${diffDay} day${diffDay > 1 ? 's' : ''} ago`;
    return escapeHtml(SLMTime.format(timestamp, { dateOnly: true }));
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
    return SLMRender.escape(text);
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
            modal.setAttribute('aria-labelledby', 'session-choice-title');
            modal.innerHTML = `
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="session-choice-title">📚 Previous Session Found</h5>
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
            dateEl.textContent = SLMTime.format(previousSession.start_time, { provenance: previousSession.timestamp_provenance });
        }
        if (notesEl && previousSession.notes) {
            notesEl.textContent = previousSession.notes.substring(0, 200) + (previousSession.notes.length > 200 ? '...' : '');
        }

        // Set up button handlers
        const restoreBtn = document.getElementById('restore-btn');
        const restartBtn = document.getElementById('restart-btn');
        const bsModal = bootstrap.Modal.getOrCreateInstance(modal);
        modal.addEventListener('hidden.bs.modal', () => resolve('cancel'), { once: true });
        modal.addEventListener('shown.bs.modal', () => restoreBtn.focus(), { once: true });

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
        const session = await SLMClient.request(`/api/learning/${previousSessionId}/restore`, { method: 'POST' });
        sessionId = session.id;
        startTimer();
        await initNotesAutoSave(session.notes);
        loadAnnotations();
    } catch (error) {
        showErrorState('Session unavailable', error.message);
    }
}

async function initSession() {
    await SLMTime.load().catch(() => {});
    const urlParams = new URLSearchParams(window.location.search);
    contentId = urlParams.get('content_id');
    planId = urlParams.get('plan_id');

    authToken = AuthService.getToken();
    sessionOwner = SLMClient.account();
    document.getElementById('session-notes').disabled = true;
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
        let structured = content.content_data;
        if (typeof structured === 'string') { try { structured = JSON.parse(structured); } catch { structured = null; } }
        const body = document.getElementById('session-content-body');
        const isPractice = content.content_type === 'exercise' && structured && typeof structured === 'object';
        const isAssessment = content.content_type === 'assessment';
        if (isPractice) SLMPractice.render(body, structured);
        if (isAssessment) {
            body.replaceChildren();
            if (Number.isInteger(structured?.assessment_id) && structured.assessment_id > 0) {
                const link = document.createElement('a'); link.className = 'btn btn-primary';
                link.href = `/assessment_taker.html?id=${structured.assessment_id}`;
                link.textContent = sessionMessage('open_assessment', 'Open assessment'); body.append(link);
            } else body.textContent = sessionMessage('practice_unavailable', 'This item needs teacher review before it can be answered.');
        }
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
        if (!isPractice && !isAssessment) SLMRender.setMarkdown(body, bodyText);
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
        if (choice === 'cancel') { window.location.href = '/dashboard.html'; return; }
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
            await initNotesAutoSave(session.notes);
        } else {
            showToast(sessionMessage('session_start_failed', 'Session tracking could not start. Reload to retry; notes are disabled until then.'), 'danger');
        }
    } catch (e) {
        showToast(sessionMessage('session_start_failed', 'Session tracking could not start. Reload to retry; notes are disabled until then.'), 'danger');
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
            <button type="button" class="plan-content-item p-2 mb-1 rounded w-100 text-start border-0 ${isCurrent ? 'bg-primary text-white' : 'bg-light'}"
                 style="cursor: pointer;" onclick="goToContent(${item.id})">
                <span class="me-2">${statusIcon}</span>
                <span class="me-1">${icon}</span>
                <span class="text-truncate" style="max-width: 150px; display: inline-block;">${escapeHtml(item.title)}</span>
            </button>
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
    nextBtn.disabled = planContents.length === 0;

    // Update button text for last item
    if (currentContentIndex >= planContents.length - 1) {
        nextBtn.textContent = '✅ Complete Plan';
    } else {
        nextBtn.textContent = 'Next →';
    }

    positionText.textContent = `${currentContentIndex + 1} of ${planContents.length}`;
}

// Navigation changes progress only after the server accepts the transition.
async function completeCurrentContent() {
    if (!sessionId || sessionOwner !== SLMClient.account()) return false;
    const notes = document.getElementById('session-notes').value;
    saveNotesDraft(notes);
    clearTimeout(notesAutoSaveTimeout);
    await notesSyncQueue;
    await SLMClient.request(`/api/learning/${sessionId}/end`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notes })
    });
    if (planId) await SLMClient.request(`/api/study-plans/${planId}/progress`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ completed_content_id: Number(contentId) })
    });
    SLMClient.drafts.remove('notes', contentId, sessionId);
    clearInterval(timerInterval);
    return true;
}

window.navigatePlanContent = async function (direction) {
    if (endingSession) return;
    const newIndex = currentContentIndex + direction;
    if (newIndex < 0) return;
    endingSession = true;
    try {
        if (!await completeCurrentContent()) return;
        window.location.href = newIndex < planContents.length ?
            `session_player.html?content_id=${planContents[newIndex].id}&plan_id=${encodeURIComponent(planId)}` : '/dashboard.html';
    } catch (error) { showToast(error.message, 'danger'); }
    finally { endingSession = false; }
};
window.goToContent = async function (targetContentId) {
    if (targetContentId === Number(contentId) || endingSession) return;
    if (!await saveNotesToLocal(document.getElementById('session-notes').value)) return;
    window.location.href = `session_player.html?content_id=${Number(targetContentId)}&plan_id=${encodeURIComponent(planId)}`;
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
    if (timerInterval) clearInterval(timerInterval);
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
    if (!sessionId || endingSession || sessionOwner !== SLMClient.account()) return;
    endingSession = true;
    const notes = document.getElementById('session-notes').value;
    saveNotesDraft(notes);
    clearTimeout(notesAutoSaveTimeout);
    try {
        await notesSyncQueue;
        await SLMClient.request(`/api/learning/${sessionId}/end`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notes, difficulty_rating: Number(document.getElementById('difficulty-rating').value) })
        });
        SLMClient.drafts.remove('notes', contentId, sessionId);
        clearInterval(timerInterval);
        window.location.href = '/dashboard.html';
    } catch (error) { showToast(error.message, 'danger'); }
    finally { endingSession = false; }
};

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
