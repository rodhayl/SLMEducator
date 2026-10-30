import { AuthService } from './auth.js';

function setUserNameDisplay(name) {
    const primary = document.getElementById('user-name-display');
    const legacy = document.getElementById('user-name');
    if (primary) primary.textContent = name;
    if (legacy && legacy !== primary) legacy.textContent = name;
}

let currentUserId = null;
let isTeacherOrAdmin = false;

function refreshRoleState() {
    const role = AuthService.getRole();
    isTeacherOrAdmin = role === 'teacher' || role === 'admin';
    const u = AuthService.getUser();
    currentUserId = u?.id ?? null;
    return { role, user: u };
}

function applyRoleUI() {
    const { role } = refreshRoleState();

    const teacherNavItems = document.querySelectorAll('[data-role="teacher"]');
    const adminNavItems = document.querySelectorAll('[data-role="admin"]');
    const libraryCreateBtn = document.getElementById('library-create-btn');
    const sharedQaOpt = document.getElementById('library-filter-qa-shared');
    const studentQaBtn = document.getElementById('student-qa-btn');

    // Only hide teacher links for explicit student role.
    teacherNavItems.forEach(item => {
        item.classList.toggle('hidden', role === 'student');
    });
    adminNavItems.forEach(item => {
        item.classList.toggle('hidden', role !== 'admin');
    });

    if (isTeacherOrAdmin) {
        libraryCreateBtn?.classList.remove('hidden');
        sharedQaOpt?.classList.remove('hidden');
        studentQaBtn?.classList.add('hidden');

        // Teacher/admin should see teacher-specific stats cards in Overview
        const teacherStats = ['stat-active-students', 'stat-assessments-created'];
        teacherStats.forEach(statId => {
            const statCard = document.getElementById(statId)?.closest('.col-md-3');
            statCard?.classList.remove('hidden');
        });
    } else {
        libraryCreateBtn?.classList.add('hidden');
        sharedQaOpt?.classList.add('hidden');

        // Hide teacher-only actions embedded in student-visible views
        document
            .querySelectorAll('a[href="/assessment_builder.html"], a[href="assessment_builder.html"]')
            .forEach(el => el.classList.add('hidden'));

        // Replace teacher-only empty-state prompts in the Library
        const libraryEmpty = document.getElementById('library-empty');
        if (libraryEmpty) {
            const emptyText = libraryEmpty.querySelector('p');
            if (emptyText) {
                emptyText.textContent = I18n.t('content.library.student_empty_state.text');
            }
            const createBtn = libraryEmpty.querySelector('button');
            if (createBtn) createBtn.classList.add('hidden');
        }

        // Hide teacher-specific stats cards in Overview
        const teacherStats = ['stat-active-students', 'stat-assessments-created'];
        teacherStats.forEach(statId => {
            const statCard = document.getElementById(statId)?.closest('.col-md-3');
            statCard?.classList.add('hidden');
        });
    }

    return role;
}

async function initAuthAndRoleUI() {
    if (!AuthService.isAuthenticated()) {
        window.location.href = '/login.html';
        return;
    }

    // Canonical source of truth: API profile (fixes stale/missing localStorage user).
    await AuthService.refreshUser();

    const { user } = refreshRoleState();
    const displayName = user ? `${user.first_name} ${user.last_name}`.trim() : I18n.t('common.roles.user');
    setUserNameDisplay(displayName || I18n.t('common.roles.user'));

    applyRoleUI();
}

// Initial auth + role UI
await initAuthAndRoleUI();

// Update on language load (and re-apply role UI)
document.addEventListener('i18n-loaded', () => {
    const { user } = refreshRoleState();
    const d = user ? `${user.first_name} ${user.last_name}`.trim() : I18n.t('common.roles.user');
    setUserNameDisplay(d || I18n.t('common.roles.user'));
    applyRoleUI();
});

// --- Learning Context Tracking ---
// Tracks what the student is currently studying for help request context
let currentLearningContext = {
    contentId: null,
    contentTitle: null,
    contentType: null,
    studyPlanId: null,
    studyPlanTitle: null,
    questionId: null
};

// Update learning context (called when student views content)
window.setLearningContext = function setLearningContext(context) {
    if (context.contentId !== undefined) {
        currentLearningContext.contentId = context.contentId;
        currentLearningContext.contentTitle = context.contentTitle || null;
        currentLearningContext.contentType = context.contentType || null;
    }
    if (context.studyPlanId !== undefined) {
        currentLearningContext.studyPlanId = context.studyPlanId;
        currentLearningContext.studyPlanTitle = context.studyPlanTitle || null;
    }
    if (context.questionId !== undefined) {
        currentLearningContext.questionId = context.questionId;
    }
    console.log('Learning context updated:', currentLearningContext);
};

// Clear learning context (called when leaving content view)
window.clearLearningContext = function clearLearningContext() {
    currentLearningContext = {
        contentId: null,
        contentTitle: null,
        contentType: null,
        studyPlanId: null,
        studyPlanTitle: null,
        questionId: null
    };
};

// Get current learning context (for help requests)
window.getLearningContext = function getLearningContext() {
    return { ...currentLearningContext };
};

// Role based UI is centralized in applyRoleUI/initAuthAndRoleUI

// ... existing code ...

// --- INBOX & MESSAGING ---
// Moved to modules/inbox.js



// --- SETTINGS ---
function applyTheme(theme) {
    const body = document.body;
    if (!body) return;

    body.classList.remove('theme-dark', 'theme-light');

    if (theme === 'dark') {
        body.classList.add('theme-dark');
    } else if (theme === 'light') {
        body.classList.add('theme-light');
    } else {
        const prefersDark = window.matchMedia &&
            window.matchMedia('(prefers-color-scheme: dark)').matches;
        body.classList.add(prefersDark ? 'theme-dark' : 'theme-light');
    }
}

window.loadProfileSettings = function () {
    const user = AuthService.getUser();
    if (user) {
        const fName = document.getElementById('profile-first-name');
        if (fName) fName.value = user.first_name || '';

        const lName = document.getElementById('profile-last-name');
        if (lName) lName.value = user.last_name || '';

        const email = document.getElementById('profile-email');
        if (email) email.value = user.email || '';

        const grade = document.getElementById('profile-grade-level');
        if (grade) grade.value = user.grade_level || 'Not specified';
    }
};

async function loadSettings() {
    const token = AuthService.getToken();
    try {
        // Load AI Config
        const aiRes = await fetch('/api/settings/ai', { headers: { 'Authorization': `Bearer ${token}` } });
        if (aiRes.ok) {
            const aiData = await aiRes.json();
            // Populate Form
            document.getElementById('ai-provider').value = aiData.provider || 'ollama';
            document.getElementById('ai-model').value = aiData.model || '';
            document.getElementById('ai-endpoint').value = aiData.endpoint || '';
            // Key is likely masked or null if hidden
            if (aiData.api_key) document.getElementById('ai-key').placeholder = I18n.t('settings.ai.api_key_set_placeholder');

            // Advanced settings
            if (aiData.temperature !== undefined) {
                document.getElementById('ai-temperature').value = aiData.temperature;
                document.getElementById('temp-value').textContent = aiData.temperature;
            }
            if (aiData.max_tokens !== undefined) {
                document.getElementById('ai-max-tokens').value = aiData.max_tokens;
            }
            if (aiData.enable_preprocessing) {
                document.getElementById('ai-preprocessing').checked = true;
                document.getElementById('preprocessing-model-group').classList.remove('d-none');
            }
            if (aiData.preprocessing_model) {
                document.getElementById('ai-preprocessing-model').value = aiData.preprocessing_model;
            }

            // Update UI hints based on provider
            onProviderChange();
        }

        // Load App Config
        const appRes = await fetch('/api/settings/app', { headers: { 'Authorization': `Bearer ${token}` } });
        if (appRes.ok) {
            const appData = await appRes.json();
            document.getElementById('app-theme').value = appData.theme || 'auto';
            document.getElementById('app-lang').value = appData.language || 'en';
            applyTheme(appData.theme || 'auto');
        }

    } catch (err) { console.error("Settings load error", err); }
}

function setSettingsTab(tabName) {
    const tabs = document.querySelectorAll('#settings-tabs .tab');
    const sections = document.querySelectorAll('.settings-tab-section');
    const targetId = `settings-tab-${tabName}`;

    tabs.forEach(tab => {
        tab.classList.toggle('active', tab.dataset.settingsTab === tabName);
    });

    sections.forEach(section => {
        section.classList.toggle('hidden', section.id !== targetId);
    });

    if (tabName === 'profile') {
        if (typeof window.loadProfileSettings === 'function') window.loadProfileSettings();
    }
}

let settingsTabsBound = false;
let settingsThemeBound = false;

function initSettingsTabs() {
    if (settingsTabsBound) return;

    const settingsTabs = document.querySelectorAll('#settings-tabs .tab');
    if (!settingsTabs.length) return;

    settingsTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.settingsTab || 'profile';
            setSettingsTab(tabName);
        });
    });

    settingsTabsBound = true;
    setSettingsTab('profile');
}

function initSettingsUI() {
    const themeSelect = document.getElementById('app-theme');
    if (themeSelect && !settingsThemeBound) {
        applyTheme(themeSelect.value || 'auto');
        themeSelect.addEventListener('change', () => applyTheme(themeSelect.value));
        settingsThemeBound = true;
    }

    initSettingsTabs();
    if (typeof window.loadProfileSettings === 'function') window.loadProfileSettings();
}

document.addEventListener('DOMContentLoaded', () => {
    initSettingsUI();

    // FIX: Trigger initial load for the active view (default is Overview)
    const activeNav = document.querySelector('.nav-item.active');
    if (activeNav) {
        const viewName = activeNav.dataset.view;
        if (viewName === 'overview') {
            if (typeof loadStats === 'function') loadStats();
            if (typeof loadActivity === 'function') loadActivity();
            if (typeof loadGamificationProfile === 'function') loadGamificationProfile();
        }
    }
});


function buildAIConfigPayload() {
    const endpointValue = document.getElementById('ai-endpoint').value.trim();

    return {
        provider: document.getElementById('ai-provider').value,
        model: document.getElementById('ai-model').value,
        endpoint: endpointValue || null,
        // Advanced settings
        temperature: parseFloat(document.getElementById('ai-temperature').value),
        max_tokens: parseInt(document.getElementById('ai-max-tokens').value),
        enable_preprocessing: document.getElementById('ai-preprocessing').checked,
        preprocessing_model: document.getElementById('ai-preprocessing-model').value || null
    };
}

window.saveAISettings = async () => {
    const token = AuthService.getToken();
    const resultDiv = document.getElementById('ai-test-result');
    const data = buildAIConfigPayload();
    const apiKeyValue = document.getElementById('ai-key').value;
    if (apiKeyValue) {
        data.api_key = apiKeyValue;
    }

    // Show saving state
    resultDiv.classList.remove('d-none');
    resultDiv.className = 'mt-3 alert alert-info';
    resultDiv.innerHTML = I18n.t('settings.save.saving');

    try {
        const res = await fetch('/api/settings/ai', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify(data)
        });
        if (res.ok) {
            resultDiv.className = 'mt-3 alert alert-success';
            resultDiv.innerHTML = `
                <strong>${I18n.t('settings.save.success')}</strong><br>
                Provider: ${data.provider}<br>
                Model: ${data.model || '(default)'}
            `;
            // Auto-hide after 5 seconds
            setTimeout(() => { resultDiv.classList.add('d-none'); }, 5000);
        } else {
            const err = await res.json();
            resultDiv.className = 'mt-3 alert alert-danger';
            resultDiv.innerHTML = `<strong>${I18n.t('settings.save.failed')}</strong><br>${err.detail || 'Unknown error'}`;
        }
    } catch (e) {
        resultDiv.className = 'mt-3 alert alert-danger';
        resultDiv.innerHTML = `<strong>${I18n.t('settings.save.network_error')}</strong><br>${I18n.t('settings.save.failed_msg')}`;
    }
};
// --- AI SETTINGS HELPER FUNCTIONS ---

/**
 * Fetch available models from the current provider
 */
window.fetchModels = async function () {
    const token = AuthService.getToken();
    const provider = document.getElementById('ai-provider').value;
    const btn = document.getElementById('fetch-models-btn');

    try {
        btn.disabled = true;
        btn.innerHTML = I18n.t('settings.ai.fetch_models_loading');

        const res = await fetch(`/api/settings/ai/models?provider=${provider}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (res.ok) {
            const data = await res.json();
            const select = document.getElementById('ai-model-select');

            if (data.models && data.models.length > 0) {
                select.innerHTML = `<option value="">${I18n.t('settings.ai.select_model_placeholder')}</option>` +
                    data.models.map(m => `<option value="${m}">${m}</option>`).join('');
                select.classList.remove('d-none');
                document.getElementById('model-hint').textContent =
                    I18n.t('settings.ai.info.loaded', { count: data.models.length });
            } else {
                select.classList.add('d-none');
                document.getElementById('model-hint').textContent =
                    I18n.t('settings.ai.errors.no_models_message');
            }
        } else {
            const err = await res.json();
            document.getElementById('model-hint').textContent =
                `${I18n.t('common.labels.error')}: ` + (err.detail || I18n.t('settings.ai.errors.fetch_failed'));
        }
    } catch (e) {
        document.getElementById('model-hint').textContent = I18n.t('settings.ai.errors.fetch_error', { error: e.message });
    } finally {
        btn.disabled = false;
        btn.innerHTML = I18n.t('settings.ai.fetch_models_button');
    }
};

/**
 * Select a model from the dropdown
 */
window.selectModel = function () {
    const select = document.getElementById('ai-model-select');
    document.getElementById('ai-model').value = select.value;
};

/**
 * Handle provider change to update UI hints
 */
window.onProviderChange = function () {
    const provider = document.getElementById('ai-provider').value;
    const apiKeyGroup = document.getElementById('api-key-group');
    const endpointInput = document.getElementById('ai-endpoint');
    const modelSelect = document.getElementById('ai-model-select');

    // Hide model select when provider changes
    modelSelect.classList.add('d-none');

    // Cloud providers need API key
    const cloudProviders = ['openai', 'anthropic', 'openrouter'];
    const localProviders = ['ollama', 'lm_studio'];

    if (cloudProviders.includes(provider)) {
        apiKeyGroup.classList.remove('d-none');
        document.getElementById('ai-key').placeholder = I18n.t('settings.ai.api_key_required_for', { provider: provider });
    } else {
        // API key optional for local providers 
        document.getElementById('ai-key').placeholder = I18n.t('settings.ai.api_key_optional');
    }

    // Update endpoint placeholder
    const defaultEndpoints = {
        'ollama': 'http://localhost:11434',
        'lm_studio': 'http://localhost:1234',
        'openai': 'https://api.openai.com/v1',
        'anthropic': 'https://api.anthropic.com',
        'openrouter': 'https://openrouter.ai/api/v1'
    };
    endpointInput.placeholder = `${I18n.t('settings.ai.endpoint_placeholder_default')} ${defaultEndpoints[provider] || I18n.t('settings.ai.endpoint_required')}`;

    // Update model hint
    const modelHint = document.getElementById('model-hint');
    if (modelHint) {
        modelHint.textContent =
            I18n.t('settings.ai.info.fetch_prompt_provider', { provider: provider });
    }
};

/**
 * Test AI connection
 */
window.testAIConnection = async function () {
    const token = AuthService.getToken();
    const resultDiv = document.getElementById('ai-test-result');
    const data = buildAIConfigPayload();
    const apiKeyValue = document.getElementById('ai-key').value;
    if (apiKeyValue) {
        data.api_key = apiKeyValue;
    }

    resultDiv.classList.remove('d-none');
    resultDiv.className = 'mt-3 alert alert-info';
    resultDiv.innerHTML = I18n.t('settings.ai.testing_connection');

    try {
        const res = await fetch('/api/settings/ai/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify(data)
        });

        const result = await res.json();

        if (result.status === 'connected') {
            resultDiv.className = 'mt-3 alert alert-success';
            resultDiv.innerHTML = `
                <strong>${I18n.t('settings.ai.success_connected')}</strong><br>
                Provider: ${result.provider}<br>
                Model: ${result.model}<br>
                Response time: ${result.response_time_ms}ms
            `;
        } else {
            resultDiv.className = 'mt-3 alert alert-danger';
            resultDiv.innerHTML = `
                <strong>${I18n.t('settings.ai.error_connection_failed')}</strong><br>
                ${I18n.t('common.labels.error')}: ${result.error}
            `;
        }
    } catch (e) {
        resultDiv.className = 'mt-3 alert alert-danger';
        resultDiv.innerHTML = I18n.t('settings.ai.error_network_test');
    }
};

/**
 * Update temperature display value
 */
window.updateTempDisplay = function () {
    const temp = document.getElementById('ai-temperature').value;
    document.getElementById('temp-value').textContent = temp;
};

/**
 * Toggle preprocessing model input visibility
 */
document.addEventListener('DOMContentLoaded', () => {
    const preprocessingCheckbox = document.getElementById('ai-preprocessing');
    if (preprocessingCheckbox) {
        preprocessingCheckbox.addEventListener('change', function () {
            const group = document.getElementById('preprocessing-model-group');
            if (this.checked) {
                group.classList.remove('d-none');
            } else {
                group.classList.add('d-none');
            }
        });
    }
});

/**
 * Show toast notification (helper function if not exists)
 */
function showToast(message, type = 'info') {
    const containerId = 'toast-container';
    let container = document.getElementById(containerId);
    if (!container) {
        container = document.createElement('div');
        container.id = containerId;
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '1080';
        document.body.appendChild(container);
    }

    const bgMap = {
        success: 'text-bg-success',
        danger: 'text-bg-danger',
        warning: 'text-bg-warning',
        info: 'text-bg-info'
    };
    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center ${bgMap[type] || 'text-bg-secondary'} border-0`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;

    container.appendChild(toastEl);
    const toast = bootstrap.Toast.getOrCreateInstance(toastEl, { delay: 3000 });
    toast.show();
    toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove(), { once: true });
}

// --- PASSWORD CHANGE ---
window.changePassword = async function () {
    const currentPassword = document.getElementById('current-password')?.value;
    const newPassword = document.getElementById('new-password')?.value;
    const confirmPassword = document.getElementById('confirm-password')?.value;
    const feedbackEl = document.getElementById('password-feedback');

    // Clear previous feedback
    if (feedbackEl) {
        feedbackEl.className = 'mt-3 d-none';
        feedbackEl.innerHTML = '';
    }

    // Validation
    if (!currentPassword || !newPassword || !confirmPassword) {
        if (feedbackEl) {
            feedbackEl.className = 'mt-3 alert alert-danger';
            feedbackEl.innerHTML = I18n.t('settings.security.password_required') || 'All password fields are required';
        }
        return;
    }

    if (newPassword !== confirmPassword) {
        if (feedbackEl) {
            feedbackEl.className = 'mt-3 alert alert-danger';
            feedbackEl.innerHTML = I18n.t('settings.security.password_mismatch') || 'New passwords do not match';
        }
        return;
    }

    // Password must meet minimum requirements
    if (newPassword.length < 8) {
        if (feedbackEl) {
            feedbackEl.className = 'mt-3 alert alert-danger';
            feedbackEl.innerHTML = 'Password must be at least 8 characters';
        }
        return;
    }

    try {
        const token = AuthService.getToken();
        const response = await fetch('/api/users/change-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword
            })
        });

        const data = await response.json();

        if (response.ok) {
            if (feedbackEl) {
                feedbackEl.className = 'mt-3 alert alert-success';
                feedbackEl.innerHTML = I18n.t('settings.security.password_changed') || 'Password changed successfully!';
            }
            // Clear the form
            document.getElementById('current-password').value = '';
            document.getElementById('new-password').value = '';
            document.getElementById('confirm-password').value = '';
            showToast(I18n.t('settings.security.password_changed') || 'Password changed successfully!', 'success');
        } else {
            if (feedbackEl) {
                feedbackEl.className = 'mt-3 alert alert-danger';
                feedbackEl.innerHTML = data.detail || 'Error changing password';
            }
        }
    } catch (error) {
        console.error('Error changing password:', error);
        if (feedbackEl) {
            feedbackEl.className = 'mt-3 alert alert-danger';
            feedbackEl.innerHTML = 'Network error. Please try again.';
        }
    }
};

// Save App Settings (Theme/Language)
window.saveAppSettings = async function () {
    const theme = document.getElementById('app-theme').value;
    const lang = document.getElementById('app-lang').value;

    try {
        const token = AuthService.getToken();
        const res = await fetch('/api/settings/app', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ theme, language: lang })
        });

        if (res.ok) {
            // Update LocalStorage immediately for persistence
            localStorage.setItem('slm_theme_preference', theme);
            localStorage.setItem('slm_language_preference', lang);

            // Apply theme immediately
            if (window.ThemeService) {
                window.ThemeService.apply(theme);
            }

            // Reload to apply language changes
            const confirmed = await showConfirm(
                I18n.t('settings.appearance.reload_confirm') || 'Settings saved. Reload now to apply changes?',
                I18n.t('settings.appearance.reload_title') || 'Reload Page',
                I18n.t('common.buttons.reload') || 'Reload',
                I18n.t('common.buttons.cancel') || 'Cancel'
            );
            if (confirmed) {
                window.location.reload();
            }
        } else {
            showToast(I18n.t('settings.error_save'), 'danger');
        }
    } catch (err) {
        console.error("Settings save error", err);
        showToast(I18n.t('settings.error_save'), 'danger');
    }
};


// --- PROFILE ---

/**
 * Load and display user profile data
 */
window.loadProfile = async function () {
    const token = AuthService.getToken();
    const user = AuthService.getUser();

    try {
        // Fetch fresh data from API
        const res = await fetch('/api/auth/me', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!res.ok) throw new Error('Failed to load profile');

        const profile = await res.json();

        // Update avatar with initials
        const initials = getInitials(profile.first_name, profile.last_name);
        document.getElementById('profile-avatar').textContent = initials;

        // Update info card
        document.getElementById('profile-full-name').textContent =
            `${profile.first_name} ${profile.last_name}`;
        document.getElementById('profile-username').textContent = `@${profile.username}`;
        document.getElementById('profile-role').textContent =
            profile.role.charAt(0).toUpperCase() + profile.role.slice(1);

        // Update account info
        document.getElementById('profile-created-at').textContent =
            profile.created_at ? new Date(profile.created_at).toLocaleDateString() : 'N/A';
        document.getElementById('profile-last-login').textContent =
            profile.last_login ? new Date(profile.last_login).toLocaleString() : 'N/A';

        // Populate form fields
        document.getElementById('profile-first-name').value = profile.first_name || '';
        document.getElementById('profile-last-name').value = profile.last_name || '';
        document.getElementById('profile-email').value = profile.email || '';
        document.getElementById('profile-grade-level').value = profile.grade_level || '';
        document.getElementById('profile-username-readonly').value = profile.username || '';

        // Hide grade level for teachers (optional for them)
        const gradeLevelGroup = document.getElementById('profile-grade-level-group');
        if (profile.role === 'teacher') {
            gradeLevelGroup.querySelector('label').textContent = I18n.t('profile.grade_optional');
        }

        // Clear feedback
        const feedback = document.getElementById('profile-feedback');
        feedback.classList.add('d-none');

        // Load user's badges
        loadProfileBadges();

    } catch (err) {
        console.error('Failed to load profile:', err);
        showProfileFeedback(I18n.t('profile.error_load'), 'danger');
    }
}

/**
 * Save profile changes
 */
window.saveProfile = async function () {
    const token = AuthService.getToken();
    const feedback = document.getElementById('profile-feedback');

    // Get form values
    const firstName = document.getElementById('profile-first-name').value.trim();
    const lastName = document.getElementById('profile-last-name').value.trim();
    const email = document.getElementById('profile-email').value.trim();
    const gradeLevel = document.getElementById('profile-grade-level').value;

    // Client-side validation
    if (!firstName) {
        showProfileFeedback(I18n.t('profile.error_firstname'), 'danger');
        return;
    }
    if (!lastName) {
        showProfileFeedback(I18n.t('profile.error_lastname'), 'danger');
        return;
    }
    if (!email || !email.includes('@')) {
        showProfileFeedback(I18n.t('profile.error_email'), 'danger');
        return;
    }

    feedback.classList.remove('d-none');
    feedback.className = 'mt-3 alert alert-info';
    feedback.textContent = I18n.t('profile.saving');

    try {
        const res = await fetch('/api/auth/profile', {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                first_name: firstName,
                last_name: lastName,
                email: email,
                grade_level: gradeLevel || null
            })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || I18n.t('profile.error_save'));
        }

        const updatedProfile = await res.json();

        // Update session storage with new user data
        AuthService.setUser(updatedProfile);

        // Update sidebar user name
        setUserNameDisplay(`${updatedProfile.first_name} ${updatedProfile.last_name}`);

        // Update avatar
        const initials = getInitials(updatedProfile.first_name, updatedProfile.last_name);
        document.getElementById('profile-avatar').textContent = initials;
        document.getElementById('profile-full-name').textContent =
            `${updatedProfile.first_name} ${updatedProfile.last_name}`;

        showProfileFeedback(I18n.t('profile.success_save'), 'success');

        // Hide success after 3 seconds
        setTimeout(() => {
            feedback.classList.add('d-none');
        }, 3000);

    } catch (err) {
        console.error('Failed to save profile:', err);
        showProfileFeedback(`❌ ${err.message}`, 'danger');
    }
};

/**
 * Get initials from first and last name
 */
function getInitials(firstName, lastName) {
    const first = (firstName || '').charAt(0).toUpperCase();
    const last = (lastName || '').charAt(0).toUpperCase();
    return first + last || '?';
}

/**
 * Show feedback message in profile form
 */
function showProfileFeedback(message, type) {
    const feedback = document.getElementById('profile-feedback');
    feedback.classList.remove('d-none', 'alert-info', 'alert-success', 'alert-danger');
    feedback.classList.add(`alert-${type}`);
    feedback.textContent = message;
}

/**
 * Load and display user's badges in the profile section
 */
window.loadProfileBadges = async function () {
    const badgesList = document.getElementById('profile-badges-list');
    const badgesCount = document.getElementById('profile-badges-count');

    if (!badgesList) return;

    try {
        const token = AuthService.getToken();
        const res = await fetch('/api/gamification/badges', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!res.ok) {
            throw new Error('Failed to load badges');
        }

        const allBadges = await res.json();
        // Filter to only show earned badges
        const badges = allBadges.filter(b => b.earned);

        // Update count
        if (badgesCount) {
            badgesCount.textContent = badges.length;
        }

        if (badges.length === 0) {
            badgesList.innerHTML = `
                <div class="text-muted text-center py-3">
                    <div class="mb-2">🎯</div>
                    <small>${I18n.t('profile.badges.empty')}</small><br>
                    <small>${I18n.t('profile.badges.empty_hint')}</small>
                </div>
            `;
            return;
        }

        // Render badges as a grid
        badgesList.innerHTML = badges.map(badge => `
            <div class="d-flex align-items-center mb-2 p-2 bg-elevated rounded">
                <div class="badge-icon me-2" style="font-size: 1.5rem;">
                    ${badge.icon_path || '🎖️'}
                </div>
                <div class="flex-grow-1">
                    <div class="fw-bold small">${badge.name}</div>
                    <div class="text-muted" style="font-size: 0.75rem;">
                        ${badge.earned_at ? new Date(badge.earned_at).toLocaleDateString() : ''}
                    </div>
                </div>
            </div>
        `).join('');

    } catch (err) {
        console.error('Failed to load badges:', err);
        badgesList.innerHTML = `
            <div class="text-muted text-center">
                <small>${I18n.t('profile.badges.error_load')}</small>
            </div>
        `;
    }
}


// --- STATS LOADER ---

async function loadStats() {
    try {
        const token = AuthService.getToken();

        // Load General Stats and populate static HTML elements
        const response = await fetch('/api/dashboard/stats', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            const stats = await response.json();

            // Populate static card elements by ID
            if (stats.active_students !== undefined) {
                document.getElementById('stat-active-students').textContent = stats.active_students;
            }
            if (stats.assessments_created !== undefined) {
                document.getElementById('stat-assessments-created').textContent = stats.assessments_created;
            }
            if (stats.average_score !== undefined) {
                document.getElementById('stat-average-score').textContent = stats.average_score + '%';
            }
            if (stats.total_content !== undefined) {
                document.getElementById('stat-total-content').textContent = stats.total_content;
            }
            const studyTime = stats.total_study_time_minutes ?? stats.total_study_time;
            if (studyTime !== undefined) {
                document.getElementById('stat-total-study-time').textContent = Math.round(studyTime);
            }
            if (stats.completed_lessons !== undefined) {
                document.getElementById('stat-completed-lessons').textContent = stats.completed_lessons;
            }
        }

        // Load Mastery Stats
        const masteryResp = await fetch('/api/mastery/overview', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (masteryResp.ok) {
            const m = await masteryResp.json();
            document.getElementById('mastery-due-count').textContent = m.items_due_review;
            document.getElementById('mastery-avg').textContent = m.average_mastery + '%';
            document.getElementById('mastery-mastered').textContent = m.items_mastered;
            document.getElementById('mastery-progress').textContent = m.items_in_progress;
        }

    } catch (err) {
        console.error("Failed to load stats", err);
    }
}

// Inbox Logic
// Moved to modules/inbox.js



// Help Request Logic
window.submitHelpRequest = async function submitHelpRequest() {
    const subject = document.getElementById('help-subject').value;
    const desc = document.getElementById('help-desc').value;
    const urgency = document.getElementById('help-urgency').value;

    // Get current learning context
    const context = window.getLearningContext();

    try {
        const token = AuthService.getToken();
        const response = await fetch('/api/classroom/help', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                subject: subject,
                description: desc,
                urgency: parseInt(urgency),
                // Include learning context
                content_id: context.contentId,
                study_plan_id: context.studyPlanId,
                question_id: context.questionId
            })
        });

        if (response.ok) {
            showToast(I18n.t('help_request.success_submit'), "success");
            const modal = bootstrap.Modal.getInstance(document.getElementById('helpModal'));
            modal.hide();
            // Clear form
            document.getElementById('help-form').reset();
            // Clear context display
            const contextDisplay = document.getElementById('help-context-display');
            if (contextDisplay) contextDisplay.innerHTML = '';
        } else {
            showToast(I18n.t('help_request.error_submit'), "danger");
        }
    } catch (e) {
        showToast(I18n.t('help_request.error_network'), "danger");
    }
}

// Initialize Help Modal - populate context display when opened
document.addEventListener('DOMContentLoaded', function () {
    const helpModal = document.getElementById('helpModal');
    if (helpModal) {
        helpModal.addEventListener('show.bs.modal', function () {
            const context = window.getLearningContext();
            const contextDisplay = document.getElementById('help-context-display');

            if (contextDisplay) {
                // Build context display HTML
                const contextParts = [];

                if (context.contentTitle) {
                    const icon = context.contentType === 'lesson' ? '📖' :
                        context.contentType === 'exercise' ? '🏋️' :
                            context.contentType === 'assessment' ? '📝' : '📄';
                    contextParts.push(`<span class="badge bg-primary me-2">${icon} ${context.contentTitle}</span>`);
                }

                if (context.studyPlanTitle) {
                    contextParts.push(`<span class="badge bg-secondary me-2">📋 ${context.studyPlanTitle}</span>`);
                }

                if (contextParts.length > 0) {
                    contextDisplay.innerHTML = `
                        <div class="alert alert-info mb-3">
                            <small class="text-muted d-block mb-1">${I18n.t('help_request.context_label')}</small>
                            <div>${contextParts.join('')}</div>
                        </div>
                    `;
                } else {
                    contextDisplay.innerHTML = `
                        <div class="alert alert-light mb-3">
                            <small class="text-muted">${I18n.t('help_request.context_tip')}</small>
                        </div>
                    `;
                }
            }
        });
    }
});


window.startReviewSession = async () => {
    // Navigate to first due item or a dedicated review page
    // For now, let's just find due items and pick one.
    try {
        const token = AuthService.getToken();
        const resp = await fetch('/api/mastery/due', { headers: { 'Authorization': `Bearer ${token}` } });
        const items = await resp.json();

        if (items.length > 0) {
            // Start review for the first item
            const item = items[0];
            window.location.href = `session_player.html?content_id=${item.content_id}&mode=review`;
        } else {
            showToast(I18n.t('review.no_items'), 'info');
        }
    } catch (err) {
        showToast(I18n.t('review.error_start', { error: err.message }), 'danger');
    }
};

// Activity Loader
async function loadActivity() {
    try {
        const token = AuthService.getToken();
        const response = await fetch('/api/dashboard/activity', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const activities = await response.json();

        const list = document.getElementById('activity-list');
        list.innerHTML = activities.map(a => `
            <div class="activity-item">
                <div>${a.text}</div>
                <div class="activity-time">${a.time}</div>
            </div>
        `).join('');
    } catch (err) {
        console.error("Failed to load activity", err);
    }
}

// Navigation Handler
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();

        // UI toggle
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        item.classList.add('active');

        const viewName = item.dataset.view;
        const { role } = refreshRoleState();

        // Guard teacher-only views (students can access help-queue to submit requests)
        if (!isTeacherOrAdmin && (viewName === 'create' || viewName === 'students' || viewName === 'grading')) {
            // Send user back to library (or overview) without throwing
            const libraryNav = document.querySelector('.nav-item[data-view=\"library\"]');
            if (libraryNav) libraryNav.click();
            return;
        }
        if ((viewName === 'teachers' || viewName === 'admins') && role !== 'admin') {
            const libraryNav = document.querySelector('.nav-item[data-view=\"library\"]');
            if (libraryNav) libraryNav.click();
            return;
        }

        // Hide all views
        document.querySelectorAll('.view-section').forEach(el => el.classList.add('hidden'));

        // Show selected view
        const viewEl = document.getElementById(`view-${viewName}`);
        if (viewEl) viewEl.classList.remove('hidden');

        document.body.classList.remove('sidebar-open');

        // Trigger data load
        if (viewName === 'overview') { loadStats(); loadActivity(); loadGamificationProfile(); }
        if (viewName === 'library') loadLibrary();
        if (viewName === 'settings') {
            initSettingsUI();
            loadSettings();
            loadProfile();
            setSettingsTab(item.dataset.settingsTab || 'profile');
        }
        if (viewName === 'inbox') loadInbox();
        if (viewName === 'students') loadStudents();
        if (viewName === 'teachers') loadTeachers();
        if (viewName === 'admins') loadAdmins();
        if (viewName === 'leaderboard') loadLeaderboard();
        if (viewName === 'grading') loadGradingQueue();
        if (viewName === 'help-queue') loadHelpQueue();
        if (viewName === 'tutor') initTutorSelectors();
    });
});

document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('sidebar-toggle');
    const backdrop = document.getElementById('sidebar-backdrop');

    if (toggle) {
        toggle.addEventListener('click', () => {
            document.body.classList.toggle('sidebar-open');
        });
    }

    if (backdrop) {
        backdrop.addEventListener('click', () => {
            document.body.classList.remove('sidebar-open');
        });
    }
});

// --- LIBRARY & CONTENT ---
let libraryCache = [];

window.loadLibrary = async function loadLibrary() {
    const grid = document.getElementById('library-content-list');
    const emptyState = document.getElementById('library-empty');

    if (!grid) {
        console.error("Library grid element 'library-content-list' not found! Check HTML structure.");
        return;
    }

    grid.innerHTML = '<div class="text-center p-3">Loading...</div>';

    try {
        const token = AuthService.getToken();
        const filterType = document.getElementById('library-filter-type')?.value || '';

        let url = '/api/content';
        if (filterType && filterType !== 'qa_shared') {
            url += `?content_type=${filterType}`;
        } else if (filterType === 'qa_shared') {
            url += `?content_type=qa`;
        }

        // Fetch content and mastery levels in parallel
        const [contentResponse, masteryResponse] = await Promise.all([
            fetch(url, { headers: { 'Authorization': `Bearer ${token}` } }),
            fetch('/api/mastery/levels', { headers: { 'Authorization': `Bearer ${token}` } }).catch(() => null)
        ]);

        let items = await contentResponse.json();
        let masteryLevels = {};
        if (masteryResponse && masteryResponse.ok) {
            masteryLevels = await masteryResponse.json();
        }

        // Teacher-only: show only student-shared Q&A
        if (filterType === 'qa_shared') {
            items = items.filter(i =>
                (i.content_type === 'qa' || i.content_type?.value === 'qa') &&
                i.is_personal === true &&
                i.shared_with_teacher === true &&
                i.creator_id !== currentUserId
            );
        }

        // Cache for later use
        libraryCache = items;

        // Update stats
        const allItems = items;
        document.getElementById('lib-total').textContent = allItems.length;
        document.getElementById('lib-lessons').textContent = allItems.filter(i =>
            (i.content_type === 'lesson' || i.content_type?.value === 'lesson')).length;
        document.getElementById('lib-exercises').textContent = allItems.filter(i =>
            (i.content_type === 'exercise' || i.content_type?.value === 'exercise')).length;
        document.getElementById('lib-assessments').textContent = allItems.filter(i =>
            (i.content_type === 'assessment' || i.content_type?.value === 'assessment')).length;

        if (items.length === 0) {
            grid.innerHTML = '';
            if (emptyState) {
                emptyState.classList.remove('hidden');
                grid.appendChild(emptyState);
            } else {
                grid.innerHTML = '<div class="text-center p-5"><h4>No content yet</h4></div>';
            }
            return;
        }

        if (emptyState) emptyState.classList.add('hidden');

        grid.innerHTML = items.map(item => {
            const type = item.content_type?.value || item.content_type || 'lesson';
            const typeColors = {
                lesson: 'bg-primary',
                exercise: 'bg-success',
                assessment: 'bg-warning text-dark',
                qa: 'bg-info'
            };
            const typeIcons = {
                lesson: '📖',
                exercise: '✏️',
                assessment: '📝',
                qa: '❓'
            };

            // Get mastery level for this content (0-100)
            const masteryLevel = masteryLevels[item.id] || 0;
            const masteryColor = masteryLevel >= 80 ? 'bg-success' : masteryLevel >= 40 ? 'bg-warning' : 'bg-secondary';
            const masteryLabel = masteryLevel >= 80 ? I18n.t('content.mastery.mastered') : masteryLevel >= 40 ? I18n.t('content.mastery.learning') : I18n.t('content.mastery.new');

            return `
                <div class="col-md-4 col-lg-3">
                    <div class="card h-100" data-creator-id="${item.creator_id || ''}">
                        <div class="card-body">
                            <span class="badge ${typeColors[type] || 'bg-secondary'} mb-2">
                                ${typeIcons[type] || '📄'} ${type.toUpperCase()}
                            </span>
                            <h5 class="card-title">${item.title}</h5>
                            ${(item.creator_id && currentUserId && item.creator_id !== currentUserId && (item.creator_name || item.creator_username)) ? `
                            <p class="text-muted small mb-2">
                                ${I18n.t('content.library.from', { name: item.creator_name || 'Student' })}${item.creator_username ? ` (@${item.creator_username})` : ''}
                            </p>` : ''}
                            <p class="text-muted small mb-2">
                                ${I18n.t('content.editor.errors.difficulty')} ${'⭐'.repeat(item.difficulty || 1)}
                            </p>
                            ${!isTeacherOrAdmin ? `
                            <div class="mb-2">
                                <small class="text-muted d-flex justify-content-between">
                                    <span>${I18n.t('content.mastery.label')}</span>
                                    <span class="badge ${masteryColor} badge-sm">${masteryLabel}</span>
                                </small>
                                <div class="progress" style="height: 6px;">
                                    <div class="progress-bar ${masteryColor}" role="progressbar" 
                                         style="width: ${masteryLevel}%;" 
                                         aria-valuenow="${masteryLevel}" aria-valuemin="0" aria-valuemax="100"></div>
                                </div>
                            </div>` : ''}
                            <p class="text-muted small">
                                ${I18n.t('content.editor.errors.created_at')} ${new Date(item.created_at).toLocaleDateString()}
                            </p>
                        </div>
                        <div class="card-footer bg-transparent border-0">
                            <div class="btn-group w-100" role="group">
                                <button class="btn btn-sm btn-outline-primary" onclick="viewContent(${item.id})" title="View">
                                    👁️
                                </button>
                                <button class="btn btn-sm btn-outline-success" onclick="startSession(${item.id})" title="Start Session">
                                    ▶️
                                </button>
                                <button class="btn btn-sm btn-outline-warning" onclick="editContent(${item.id})" title="Edit">
                                    ✏️
                                </button>
                                <button class="btn btn-sm btn-outline-danger" onclick="deleteContent(${item.id})" title="Delete">
                                    🗑️
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        applyLibraryPermissionUI(grid);
    } catch (err) {
        console.error(err);
        grid.innerHTML = '<div class="text-danger text-center p-3">Failed to load content</div>';
    }
};

function applyLibraryPermissionUI(container) {
    if (!container) return;
    const buttons = container.querySelectorAll('button[onclick^="editContent("],button[onclick^="deleteContent("]');

    // Students should not see manage actions on assigned content.
    if (!isTeacherOrAdmin) {
        buttons.forEach(b => b.classList.add('hidden'));
    }

    if (!currentUserId) return;

    // Allow managing own content (cards only).
    container.querySelectorAll('.card[data-creator-id]').forEach(card => {
        const creatorId = Number(card.getAttribute('data-creator-id') || 0);
        const canManage = creatorId === Number(currentUserId);
        if (canManage) {
            card.querySelectorAll('button[onclick^="editContent("],button[onclick^="deleteContent("]').forEach(b => b.classList.remove('hidden'));
        } else {
            card.querySelectorAll('button[onclick^="editContent("],button[onclick^="deleteContent("]').forEach(b => b.classList.add('hidden'));
        }
    });
}

// --- STUDENT Q&A ---

window.openStudentQAModal = function openStudentQAModal() {
    if (isTeacherOrAdmin) return;
    const modalEl = document.getElementById('qaCreateModal');
    if (!modalEl) return;
    const titleEl = document.getElementById('qa-title');
    const questionEl = document.getElementById('qa-question');
    const shareEl = document.getElementById('qa-share');
    const aiAnswerSection = document.getElementById('qa-ai-answer');
    if (titleEl) titleEl.value = '';
    if (questionEl) questionEl.value = '';
    if (shareEl) shareEl.checked = true;
    if (aiAnswerSection) aiAnswerSection.classList.add('hidden');
    bootstrap.Modal.getOrCreateInstance(modalEl).show();
};

window.saveStudentQA = async function saveStudentQA() {
    if (isTeacherOrAdmin) return;
    const title = (document.getElementById('qa-title')?.value || '').trim();
    const question = (document.getElementById('qa-question')?.value || '').trim();
    const share = !!document.getElementById('qa-share')?.checked;

    if (!title || !question) {
        showToast(I18n.t('content.qa_section.error_title_question'), 'warning');
        return;
    }

    try {
        const token = AuthService.getToken();
        const res = await fetch('/api/content', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({
                title,
                content_type: 'qa',
                content_data: { question },
                shared_with_teacher: share
            })
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            showToast(err.detail || I18n.t('content.qa_section.error_save'), 'danger');
            return;
        }

        showToast(I18n.t('content.qa_section.success_save'), 'success');
        const modalEl = document.getElementById('qaCreateModal');
        if (modalEl) bootstrap.Modal.getOrCreateInstance(modalEl).hide();
        loadLibrary();
    } catch (e) {
        console.error(e);
        showToast(I18n.t('content.qa_section.error_network'), 'danger');
    }
};

/**
 * Ask AI for an answer to the student's question
 */
window.askAIForAnswer = async function askAIForAnswer() {
    const question = (document.getElementById('qa-question')?.value || '').trim();

    if (!question) {
        showToast(I18n.t('content.qa_section.error_no_question'), 'warning');
        return;
    }

    const answerSection = document.getElementById('qa-ai-answer');
    const answerContent = document.getElementById('qa-ai-answer-content');
    const askBtn = document.getElementById('qa-ask-ai-btn');

    // Show loading state
    if (askBtn) {
        askBtn.disabled = true;
        askBtn.innerHTML = I18n.t('ai.chat.status.thinking');
    }

    try {
        const token = AuthService.getToken();
        const res = await fetch('/api/ai/answer-question', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ question })
        });

        const data = await res.json();

        if (res.ok && data.success) {
            // Show the answer
            if (answerContent) {
                // Use marked.parse if available for markdown support
                if (typeof marked !== 'undefined') {
                    answerContent.innerHTML = marked.parse(data.answer);
                } else {
                    answerContent.textContent = data.answer;
                }
            }
            if (answerSection) answerSection.classList.remove('hidden');
            showToast(I18n.t('content.qa_section.success_answer'), 'success');
        } else {
            showToast(data.answer || I18n.t('content.qa_section.error_answer'), 'warning');
            if (answerContent) answerContent.textContent = data.answer || I18n.t('content.qa_section.error_no_answer');
            if (answerSection) answerSection.classList.remove('hidden');
        }
    } catch (e) {
        console.error('AI Answer error:', e);
        showToast(I18n.t('content.qa_section.error_network'), 'danger');
    } finally {
        // Reset button
        if (askBtn) {
            askBtn.disabled = false;
            askBtn.innerHTML = I18n.t('content.qa_section.button_ask');
        }
    }
};

// View content details
window.viewContent = async function viewContent(id) {
    window.currentContentId = id;

    try {
        const token = AuthService.getToken();
        const res = await fetch(`/api/content/${id}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!res.ok) throw new Error(I18n.t('content.viewer.error_load'));

        const content = await res.json();

        // Set learning context for help requests
        const type = content.content_type?.value || content.content_type || 'lesson';
        window.setLearningContext({
            contentId: content.id,
            contentTitle: content.title,
            contentType: type
        });

        // Populate modal
        document.getElementById('content-view-title').textContent = content.title;
        document.getElementById('content-view-type').textContent = type.toUpperCase();
        document.getElementById('content-view-difficulty').textContent = `Difficulty: ${content.difficulty || 1}`;
        document.getElementById('content-view-date').textContent = `Created: ${new Date(content.created_at).toLocaleDateString()}`;

        // Parse content body
        let bodyText = I18n.t('content.viewer.empty_content');
        if (content.content_data) {
            try {
                if (typeof content.content_data === 'string') {
                    const parsed = JSON.parse(content.content_data);
                    bodyText = parsed.body || parsed.content || parsed.text || JSON.stringify(parsed, null, 2);
                } else {
                    bodyText = content.content_data.body || content.content_data.content || JSON.stringify(content.content_data, null, 2);
                }
            } catch {
                bodyText = content.content_data;
            }
        }

        document.getElementById('content-view-body').innerHTML = typeof marked !== 'undefined'
            ? marked.parse(bodyText)
            : `<pre>${bodyText}</pre>`;

        // Show modal
        new bootstrap.Modal(document.getElementById('contentViewModal')).show();
    } catch (err) {
        showToast(I18n.t('content.viewer.error_load_details', { error: err.message }), 'danger');
    }
};

// Edit content
window.editContent = async function editContent(id) {
    // Close view modal if open
    const viewModal = bootstrap.Modal.getInstance(document.getElementById('contentViewModal'));
    if (viewModal) viewModal.hide();

    try {
        const token = AuthService.getToken();
        const res = await fetch(`/api/content/${id}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!res.ok) throw new Error(I18n.t('content.viewer.error_load'));

        const content = await res.json();

        // Populate edit form
        document.getElementById('edit-content-id').value = content.id;
        document.getElementById('edit-content-title').value = content.title;
        const type = content.content_type?.value || content.content_type || 'lesson';
        document.getElementById('edit-content-type').value = type;
        document.getElementById('edit-content-difficulty').value = content.difficulty || 1;

        // Parse body
        let bodyText = '';
        if (content.content_data) {
            try {
                if (typeof content.content_data === 'string') {
                    const parsed = JSON.parse(content.content_data);
                    bodyText = parsed.body || parsed.content || parsed.text || JSON.stringify(parsed, null, 2);
                } else {
                    bodyText = content.content_data.body || content.content_data.content || JSON.stringify(content.content_data, null, 2);
                }
            } catch {
                bodyText = content.content_data;
            }
        }
        document.getElementById('edit-content-body').value = bodyText;

        // Show modal
        new bootstrap.Modal(document.getElementById('contentEditModal')).show();
    } catch (err) {
        showToast(I18n.t('content.editor.error_load', { error: err.message }), 'danger');
    }
};

// Save content edit
window.saveContentEdit = async function saveContentEdit() {
    const id = document.getElementById('edit-content-id').value;
    const title = document.getElementById('edit-content-title').value;
    const difficulty = document.getElementById('edit-content-difficulty').value;
    const body = document.getElementById('edit-content-body').value;

    try {
        const token = AuthService.getToken();

        // Note: Backend needs PATCH/PUT endpoint for content update
        // For now, we'll try PUT if it exists
        const res = await fetch(`/api/content/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                title: title,
                difficulty: parseInt(difficulty),
                content_data: { body: body }
            })
        });

        if (res.ok) {
            showToast(I18n.t('content.editor.success_update'), 'success');
            bootstrap.Modal.getInstance(document.getElementById('contentEditModal')).hide();
            // Clear existing grid immediately and reload to ensure fresh data
            const grid = document.getElementById('library-content-list');
            if (grid) grid.innerHTML = '<div class="text-center p-4">Refreshing...</div>';
            await loadLibrary(); // Refresh with await
        } else {
            const err = await res.json();
            showToast(I18n.t('content.editor.error_update', { error: err.detail || I18n.t('common.errors.unknown') }), 'danger');
        }
    } catch (err) {
        showToast(I18n.t('content.editor.error_save_generic', { error: err.message }), 'danger');
    }
};

// Delete content
window.deleteContent = async function deleteContent(id) {
    const confirmed = await showConfirm(
        I18n.t('content.editor.delete_confirm') || 'Delete this content?',
        I18n.t('content.editor.delete_title') || 'Confirm Delete',
        I18n.t('common.buttons.delete') || 'Delete',
        I18n.t('common.buttons.cancel') || 'Cancel',
        true
    );
    if (!confirmed) return;

    // Close modals
    const viewModal = bootstrap.Modal.getInstance(document.getElementById('contentViewModal'));
    if (viewModal) viewModal.hide();

    try {
        const token = AuthService.getToken();
        const res = await fetch(`/api/content/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (res.ok) {
            showToast(I18n.t('content.editor.success_delete'), 'success');
            // Clear existing grid immediately and reload to ensure fresh data
            const grid = document.getElementById('library-content-list');
            if (grid) grid.innerHTML = '<div class="text-center p-4">Refreshing...</div>';
            await loadLibrary(); // Refresh with await
        } else {
            const err = await res.json();
            showToast(I18n.t('content.editor.error_delete', { error: err.detail || I18n.t('common.errors.unknown') }), 'danger');
        }
    } catch (err) {
        showToast(I18n.t('content.editor.error_delete_generic', { error: err.message }), 'danger');
    }
};

// Start learning session for content (optionally within a study plan context)
window.startSession = function startSession(contentId, planId = null) {
    // Close any modals
    const viewModal = bootstrap.Modal.getInstance(document.getElementById('contentViewModal'));
    if (viewModal) viewModal.hide();

    let url = `session_player.html?content_id=${contentId}`;
    if (planId) {
        url += `&plan_id=${planId}`;
    }
    window.location.href = url;
};

// --- TABS & CREATE CONTENT ---

// Tab Switching (Create Content)
const createTabs = document.querySelectorAll('.tab[data-tab]');
createTabs.forEach(tab => {
    tab.addEventListener('click', () => {
        // Toggle active tab
        createTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        // Toggle form visibility
        const tabId = tab.dataset.tab; // manual, ai-content
        document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));

        // Map tab ID to form ID
        if (tabId === 'manual') document.getElementById('create-manual-form').classList.remove('hidden');
        if (tabId === 'ai-content') document.getElementById('create-ai-content-form').classList.remove('hidden');

        // Hide result areas on switch
        document.getElementById('ai-content-generation-result')?.classList.add('hidden');
        document.getElementById('manual-entry-feedback')?.classList.add('d-none');
    });
});


// Manual Form Handler
const manualForm = document.getElementById('create-manual-form');
if (manualForm) {
    manualForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = {
            title: manualForm.title.value,
            content_type: manualForm.content_type.value,
            content_data: { body: manualForm.content_body.value }
        };
        await createContent(data, manualForm);
    });
}

// --- AI CONTENT GENERATOR ---

// Toggle generation mode (Study Plan vs Topic vs Exercise)
window.toggleGenerationMode = function () {
    const mode = document.querySelector('input[name="generation_mode"]:checked')?.value || 'topic';

    // Hide all mode fields
    document.getElementById('study-plan-mode-fields')?.classList.add('hidden');
    document.getElementById('topic-mode-fields')?.classList.add('hidden');
    document.getElementById('exercise-mode-fields')?.classList.add('hidden');

    // Update button text
    const btn = document.getElementById('generate-btn');

    // Show appropriate fields based on mode
    if (mode === 'study_plan') {
        document.getElementById('study-plan-mode-fields')?.classList.remove('hidden');
        document.getElementById('save-options-section')?.classList.add('hidden');
        if (btn) btn.textContent = I18n.t('content.generator.buttons.study_plan');
    } else if (mode === 'topic') {
        document.getElementById('topic-mode-fields')?.classList.remove('hidden');
        document.getElementById('save-options-section')?.classList.remove('hidden');
        document.getElementById('link-to-plan-check')?.classList.remove('hidden');
        if (btn) btn.textContent = I18n.t('content.generator.buttons.topic_package');
    } else if (mode === 'exercise') {
        document.getElementById('exercise-mode-fields')?.classList.remove('hidden');
        document.getElementById('save-options-section')?.classList.remove('hidden');
        document.getElementById('link-to-plan-check')?.classList.add('hidden');
        if (btn) btn.textContent = I18n.t('content.generator.buttons.exercise');
    }
};

// Toggle functions for conditional options
window.toggleExerciseOptions = function () {
    const checkbox = document.getElementById('include-exercises');
    const options = document.getElementById('exercise-options');
    if (checkbox?.checked) {
        options?.classList.remove('hidden');
    } else {
        options?.classList.add('hidden');
    }
};

window.toggleAssessmentOptions = function () {
    const checkbox = document.getElementById('include-assessment');
    const options = document.getElementById('assessment-options');
    if (checkbox?.checked) {
        options?.classList.remove('hidden');
    } else {
        options?.classList.add('hidden');
    }
};

window.toggleStudyPlanSelector = function () {
    const checkbox = document.getElementById('add-to-study-plan');
    const selector = document.getElementById('study-plan-selector');
    if (checkbox?.checked) {
        selector?.classList.remove('hidden');
        loadStudyPlansForSelector();
    } else {
        selector?.classList.add('hidden');
    }
};

// Load study plans for the dropdown selector
async function loadStudyPlansForSelector() {
    try {
        const token = AuthService.getToken();
        const res = await fetch('/api/study-plans/', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) return;

        const plans = await res.json();
        const select = document.getElementById('study-plan-select');
        if (!select) return;

        // Keep the first option and add plans
        select.innerHTML = `<option value="">${I18n.t('common.forms.select_placeholder_study_plan')}</option>`;
        plans.forEach(plan => {
            const option = document.createElement('option');
            option.value = plan.id;
            option.textContent = plan.title;
            select.appendChild(option);
        });
    } catch (err) {
        console.error('Failed to load study plans:', err);
    }
}

// AI Content Generator Form Handler
const aiContentForm = document.getElementById('create-ai-content-form');
if (aiContentForm) {
    aiContentForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Get selected generation mode
        const mode = document.querySelector('input[name="generation_mode"]:checked')?.value || 'topic';

        let endpoint, payload;

        if (mode === 'study_plan') {
            // Study Plan mode
            const objectives = (aiContentForm.plan_objectives?.value || '')
                .split('\n')
                .map(line => line.replace(/^[\s-•*]+/, '').trim())
                .filter(line => line !== '');

            endpoint = '/api/generate/study-plan';
            payload = {
                subject: aiContentForm.plan_subject?.value || '',
                grade_level: aiContentForm.plan_grade_level?.value || '10',
                duration_weeks: parseInt(aiContentForm.plan_duration?.value) || 4,
                objectives: objectives
            };
        } else if (mode === 'exercise') {
            // Single Exercise mode
            endpoint = '/api/generate/exercise';
            payload = {
                topic: aiContentForm.exercise_topic?.value || '',
                difficulty: aiContentForm.single_exercise_difficulty?.value || 'medium',
                exercise_type: aiContentForm.single_exercise_type?.value || 'multiple_choice'
            };
        } else {
            // Topic Package mode (default)
            const objectives = (aiContentForm.learning_objectives?.value || '')
                .split('\n')
                .map(line => line.replace(/^[\s-•*]+/, '').trim())
                .filter(line => line !== '');

            endpoint = '/api/generate/full-topic-package';
            payload = {
                subject: aiContentForm.subject?.value || '',
                topic_name: aiContentForm.topic_name?.value || '',
                grade_level: aiContentForm.grade_level?.value || '10',
                learning_objectives: objectives,
                include_lesson: document.getElementById('include-lesson')?.checked ?? true,
                include_exercises: document.getElementById('include-exercises')?.checked ?? true,
                include_assessment: document.getElementById('include-assessment')?.checked ?? false,
                num_exercises: parseInt(aiContentForm.num_exercises?.value) || 4,
                exercise_difficulty: aiContentForm.exercise_difficulty?.value || 'medium',
                num_assessment_questions: parseInt(aiContentForm.num_assessment_questions?.value) || 5,
                assessment_difficulty: aiContentForm.assessment_difficulty?.value || 'medium',
                auto_save: document.getElementById('auto-save')?.checked ?? false
            };

            // Add study plan ID if selected
            const addToStudyPlan = document.getElementById('add-to-study-plan');
            if (addToStudyPlan?.checked) {
                const studyPlanId = document.getElementById('study-plan-select')?.value;
                const phaseIndex = document.getElementById('phase-select')?.value;
                if (studyPlanId) {
                    payload.study_plan_id = parseInt(studyPlanId);
                    payload.phase_index = parseInt(phaseIndex) || 0;
                }
            }
        }

        await generateAIContent(endpoint, payload, mode);
    });
}

// Generate AI Content - calls mode-appropriate endpoint
let generatedAIContent = null;
let currentGenerationMode = 'topic';

async function generateAIContent(endpoint, payload, mode) {
    currentGenerationMode = mode;
    const resultDiv = document.getElementById('ai-content-generation-result');
    const itemsList = document.getElementById('generated-items-list');
    const submitBtn = aiContentForm?.querySelector('button[type="submit"]');

    resultDiv?.classList.add('hidden');
    if (submitBtn) { submitBtn.textContent = I18n.t('content.generator.status.generating'); submitBtn.disabled = true; }

    try {
        const token = AuthService.getToken();
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || I18n.t('content.generator.error_failed'));
        }

        const json = await res.json();
        generatedAIContent = json;
        generatedAIContent._mode = mode; // Store mode for saving

        // Build preview based on mode
        let html = '';
        const topicNameBadge = document.getElementById('generated-topic-name');

        if (mode === 'study_plan') {
            // Study Plan preview
            if (topicNameBadge) topicNameBadge.textContent = json.title || I18n.t('content.generator.results.default_plan_title');

            html += `<div class="card mb-2"><div class="card-header bg-primary text-white">📋 Study Plan: ${json.title || 'Generated'}</div>
            <div class="card-body">
                <p><strong>Subject:</strong> ${json.subject || payload.subject}</p>
                <p><strong>Duration:</strong> ${json.duration_weeks || payload.duration_weeks} weeks</p>
                <p><strong>Phases:</strong> ${json.phases?.length || 0} phase(s)</p>`;
            if (json.phases?.length) {
                html += '<ul class="mb-0">';
                json.phases.slice(0, 5).forEach((phase, i) => {
                    html += `<li>Phase ${i + 1}: ${phase.title || phase.name || 'Unnamed'}</li>`;
                });
                if (json.phases.length > 5) html += `<li>... and ${json.phases.length - 5} more</li>`;
                html += '</ul>';
            }
            html += '</div></div>';
        } else if (mode === 'exercise') {
            // Single Exercise preview
            if (topicNameBadge) topicNameBadge.textContent = I18n.t('content.generator.results.default_exercise_title');

            html += `<div class="card mb-2"><div class="card-header bg-success text-white">🏋️ Exercise</div>
            <div class="card-body">
                <p><strong>Question:</strong> ${json.question || json.title || 'Generated'}</p>`;
            if (json.options?.length) {
                html += '<p><strong>Options:</strong></p><ul class="mb-0">';
                json.options.forEach(opt => { html += `<li>${opt}</li>`; });
                html += '</ul>';
            }
            html += '</div></div>';
        } else {
            // Topic Package preview (default)
            if (topicNameBadge) topicNameBadge.textContent = payload.topic_name || I18n.t('content.generator.results.default_content_title');

            if (json.lesson) {
                html += `<div class="card mb-2"><div class="card-header bg-primary text-white">📖 Lesson: ${json.lesson.title || 'Generated'}</div>
                <div class="card-body"><p>${json.lesson.summary || 'Lesson generated successfully'}</p></div></div>`;
            }
            if (json.exercises?.length) {
                html += `<div class="card mb-2"><div class="card-header bg-success text-white">🏋️ ${json.exercises.length} Exercise(s)</div>
                <div class="card-body">${json.exercises.slice(0, 3).map((e, i) => `<p>${i + 1}. ${e.title || e.question || 'Exercise'}</p>`).join('')}</div></div>`;
            }
            if (json.assessment_questions?.length) {
                html += `<div class="card mb-2"><div class="card-header bg-info text-white">📝 ${json.assessment_questions.length} Assessment Question(s)</div>
                <div class="card-body">${json.assessment_questions.slice(0, 3).map((q, i) => `<p>${i + 1}. ${q.question || q.question_text || 'Question'}</p>`).join('')}</div></div>`;
            }

            // Show auto-save status if applicable
            if (payload.auto_save && json.saved_content_ids?.length) {
                html += `<div class="alert alert-success mt-2">✅ Auto-saved ${json.saved_content_ids.length} item(s) to your library!</div>`;
            }
        }

        if (itemsList) itemsList.innerHTML = html || '<p>Content generated!</p>';
        resultDiv?.classList.remove('hidden');
    } catch (err) {
        showToast('Generation failed: ' + err.message, 'danger');
    } finally {
        // Reset button text based on mode
        if (submitBtn) {
            submitBtn.disabled = false;
            if (mode === 'study_plan') submitBtn.textContent = I18n.t('content.generator.buttons.study_plan');
            else if (mode === 'exercise') submitBtn.textContent = I18n.t('content.generator.buttons.exercise');
            else submitBtn.textContent = I18n.t('content.generator.buttons.topic_package');
        }
    }
}

window.saveAllGeneratedContent = async function () {
    if (!generatedAIContent) { showToast(I18n.t('content.generator.error_no_content'), 'warning'); return; }
    const token = AuthService.getToken();
    let saved = 0;
    const mode = generatedAIContent._mode || currentGenerationMode;

    if (mode === 'study_plan') {
        // Save study plan via /api/study-plans
        const r = await fetch('/api/study-plans/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify(generatedAIContent)
        });
        if (r.ok) {
            saved++;
            showToast(I18n.t('content.generator.success_save_plan'), 'success');
        } else {
            showToast(I18n.t('content.generator.error_save_plan'), 'danger');
        }
    } else if (mode === 'exercise') {
        // Save single exercise
        const r = await fetch('/api/content', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({
                title: generatedAIContent.title || generatedAIContent.question || 'Generated Exercise',
                content_type: 'exercise',
                content_data: generatedAIContent
            })
        });
        if (r.ok) saved++;
        showToast(I18n.t('content.generator.success_save_exercise'), 'success');
    } else {
        // Topic Package mode - save each item
        if (generatedAIContent.lesson) {
            const r = await fetch('/api/content', {
                method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ title: generatedAIContent.lesson.title || 'Generated Lesson', content_type: 'lesson', content_data: generatedAIContent.lesson })
            });
            if (r.ok) saved++;
        }
        for (const ex of (generatedAIContent.exercises || [])) {
            const r = await fetch('/api/content', {
                method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ title: ex.title || 'Generated Exercise', content_type: 'exercise', content_data: ex })
            });
            if (r.ok) saved++;
        }
        for (const q of (generatedAIContent.assessment_questions || [])) {
            const r = await fetch('/api/content', {
                method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ title: q.question || q.question_text || 'Generated Assessment', content_type: 'assessment', content_data: q })
            });
            if (r.ok) saved++;
        }
        showToast(I18n.t('content.generator.success_save_items', { count: saved }), 'success');
    }

    document.getElementById('ai-content-generation-result')?.classList.add('hidden');
    aiContentForm?.reset();
    toggleGenerationMode(); // Reset form to show correct fields
    generatedAIContent = null;
};

window.regenerateContent = function () { aiContentForm?.dispatchEvent(new Event('submit')); };
window.clearAIContentForm = function () {
    aiContentForm?.reset();
    document.getElementById('ai-content-generation-result')?.classList.add('hidden');
    document.getElementById('assessment-options')?.classList.add('hidden');
    document.getElementById('study-plan-selector')?.classList.add('hidden');
    toggleGenerationMode(); // Reset form to show correct fields
    generatedAIContent = null;
};

function setManualEntryFeedback(message, type = 'info') {
    const feedback = document.getElementById('manual-entry-feedback');
    if (!feedback) {
        showToast(message, type === 'danger' ? 'danger' : type === 'success' ? 'success' : 'info');
        return;
    }
    feedback.className = `alert alert-${type} mt-3`;
    feedback.textContent = message;
    feedback.classList.remove('d-none');
}



// Helper: Create Content API Call
async function createContent(data, formToReset) {
    try {
        const token = AuthService.getToken();
        const res = await fetch('/api/content', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify(data)
        });
        if (res.ok) {
            setManualEntryFeedback(I18n.t('content.creator.success'), 'success');
            if (formToReset) formToReset.reset();
            const libraryView = document.getElementById('view-library');
            if (libraryView && !libraryView.classList.contains('hidden')) {
                loadLibrary();
            }
        } else {
            const err = await res.json().catch(() => ({}));
            setManualEntryFeedback(err.detail || I18n.t('content.creator.error_save'), 'danger');
        }
    } catch (err) {
        setManualEntryFeedback(I18n.t('content.creator.error_generic', { error: err.message }), 'danger');
    }
}

// --- AI TUTOR ---
const chatForm = document.getElementById('chat-form');
const chatHistory = document.getElementById('chat-history');

// Load study plans for tutor context selector
window.loadTutorStudyPlans = async function loadTutorStudyPlans() {
    const select = document.getElementById('tutor-study-plan');
    if (!select) return;

    try {
        const token = AuthService.getToken();
        const res = await fetch('/api/study-plans/', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) return;

        const plans = await res.json();
        select.innerHTML = `<option value="">${I18n.t('ai.tutor.select_all_plans')}</option>`;
        plans.forEach(plan => {
            const option = document.createElement('option');
            option.value = plan.id;
            option.textContent = `📘 ${plan.title}`;
            select.appendChild(option);
        });
    } catch (err) {
        console.error('Failed to load tutor study plans:', err);
    }
};

// Load content items when study plan selected
window.loadTutorContentItems = async function loadTutorContentItems() {
    const planSelect = document.getElementById('tutor-study-plan');
    const contentSelect = document.getElementById('tutor-content');
    if (!contentSelect) return;

    const planId = planSelect?.value;

    if (!planId) {
        // Load all user content when no plan selected
        contentSelect.innerHTML = `<option value="">${I18n.t('ai.tutor.select_all_content')}</option>`;
        try {
            const token = AuthService.getToken();
            const res = await fetch('/api/content/', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const contents = await res.json();
                contents.slice(0, 50).forEach(c => {
                    const icon = c.content_type === 'lesson' ? '📖' :
                        c.content_type === 'exercise' ? '🏋️' :
                            c.content_type === 'assessment' ? '📝' : '📄';
                    const option = document.createElement('option');
                    option.value = c.id;
                    option.textContent = `${icon} ${c.title}`;
                    contentSelect.appendChild(option);
                });
            }
        } catch (e) { console.error('Failed to load content:', e); }
        return;
    }

    // Load content for specific study plan
    try {
        const token = AuthService.getToken();
        const res = await fetch(`/api/study-plans/${planId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) {
            contentSelect.innerHTML = `<option value="">${I18n.t('ai.tutor.select_all_content')}</option>`;
            return;
        }

        const plan = await res.json();
        contentSelect.innerHTML = `<option value="">${I18n.t('ai.tutor.select_all_plan_content')}</option>`;

        // Add plan's content items
        const contents = plan.contents || [];
        contents.forEach(c => {
            const icon = c.content_type === 'lesson' ? '📖' :
                c.content_type === 'exercise' ? '🏋️' :
                    c.content_type === 'assessment' ? '📝' : '📄';
            const option = document.createElement('option');
            option.value = c.content_id || c.id;
            option.textContent = `${icon} ${c.title}`;
            contentSelect.appendChild(option);
        });
    } catch (err) {
        console.error('Failed to load plan content:', err);
        contentSelect.innerHTML = `<option value="">${I18n.t('ai.tutor.select_all_content')}</option>`;
    }
};

// Initialize tutor selectors when tutor view is shown
window.initTutorSelectors = function initTutorSelectors() {
    loadTutorStudyPlans();
    loadTutorContentItems();
};

// Clear AI Chat (30.3)
window.clearAIChat = function clearAIChat() {
    const chatHistory = document.getElementById('chat-history');
    if (chatHistory) {
        chatHistory.innerHTML = '<div class="text-muted text-center">Start a conversation with your AI Tutor</div>';
    }

    // Reset context selectors
    const studyPlanSelect = document.getElementById('tutor-study-plan');
    const contentSelect = document.getElementById('tutor-content');
    if (studyPlanSelect) studyPlanSelect.value = '';
    if (contentSelect) contentSelect.value = '';

    // Clear input
    const chatInput = document.getElementById('chat-input');
    if (chatInput) chatInput.value = '';

    showToast('Chat cleared. Start a new conversation!', 'info');
};


if (chatForm) {
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const input = document.getElementById('chat-input');
        const msg = input.value;
        if (!msg) return;

        // Get selected context
        const studyPlanId = document.getElementById('tutor-study-plan')?.value || null;
        const contentId = document.getElementById('tutor-content')?.value || null;

        // Append User Message
        chatHistory.innerHTML += `<div class="chat-message chat-message-user"><span class="chat-bubble">${msg}</span></div>`;
        input.value = '';
        chatHistory.scrollTop = chatHistory.scrollHeight;

        // Show typing indicator
        chatHistory.innerHTML += `<div class="chat-message chat-message-ai" id="typing-indicator"><span class="chat-bubble text-muted">${I18n.t('ai.chat.status.thinking')}</span></div>`;
        chatHistory.scrollTop = chatHistory.scrollHeight;

        try {
            const token = AuthService.getToken();
            const payload = { message: msg };
            if (studyPlanId) payload.study_plan_id = parseInt(studyPlanId);
            if (contentId) payload.content_id = parseInt(contentId);

            const res = await fetch('/api/ai/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify(payload)
            });
            const data = await res.json();

            // Remove typing indicator
            document.getElementById('typing-indicator')?.remove();

            // Append AI Response
            chatHistory.innerHTML += `<div class="chat-message chat-message-ai"><span class="chat-bubble">${data.response}</span></div>`;
            chatHistory.scrollTop = chatHistory.scrollHeight;
        } catch (err) {
            document.getElementById('typing-indicator')?.remove();
            chatHistory.innerHTML += `<div class="text-danger text-sm">${I18n.t('ai.chat.error_send')}</div>`;
        }
    });
}

// Old settings logic removed.

// --- NEW LOADER FUNCTIONS (for additional views) ---

// Gamification Profile Loader
async function loadGamificationProfile() {
    // Check if I18n is ready before proceeding
    if (typeof I18n === 'undefined' || !I18n.isReady) {
        console.log('[Gamification] Waiting for I18n to be ready...');
        setTimeout(loadGamificationProfile, 100);
        return;
    }
    
    try {
        const token = AuthService.getToken();
        const res = await fetch('/api/gamification/profile', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            const profile = await res.json();
            // Update gamification card elements
            const xpEl = document.getElementById('gam-xp');
            if (xpEl) xpEl.textContent = profile.xp || 0;
            const levelBadge = document.getElementById('gam-level-badge');
            if (levelBadge) {
                const levelText = I18n.t('dashboard.gamification.level', { level: profile.level || 1 });
                levelBadge.textContent = levelText;
            }
            const streakEl = document.getElementById('gam-streak');
            if (streakEl) streakEl.textContent = profile.current_streak || 0;
            const longestStreakEl = document.getElementById('gam-longest-streak');
            if (longestStreakEl) longestStreakEl.textContent = profile.longest_streak || 0;
            const badgesEl = document.getElementById('gam-badges');
            if (badgesEl) badgesEl.textContent = profile.badges_earned || 0;
        }
    } catch (e) { console.error("Failed to load gamification profile", e); }

    // Also load daily goal
    loadDailyGoal();
}

// Daily Goal Loader
// Daily Goal Loader
async function loadDailyGoal() {
    try {
        const token = AuthService.getToken();
        const res = await fetch('/api/gamification/daily-goal', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            const goal = await res.json();
            console.log("Loaded Daily Goal:", goal); // Debug log

            const progressBar = document.getElementById('daily-goal-progress');
            const progressText = document.getElementById('daily-goal-text');

            if (goal.id) {
                // Reset classes to default success state
                progressBar.classList.remove('bg-secondary', 'bg-warning');
                progressBar.classList.add('bg-success');

                const percent = Math.min(100, Math.round((goal.current_value / goal.target_value) * 100));
                progressBar.style.width = `${percent}%`;
                progressBar.setAttribute('aria-valuenow', percent);

                const goalTypeLabel = goal.goal_type === 'lessons' ? '📖 Lessons' :
                    goal.goal_type === 'exercises' ? '✏️ Exercises' : '⏱️ Minutes';
                progressText.textContent = `${goal.current_value}/${goal.target_value} ${goalTypeLabel}`;

                if (goal.completed) {
                    progressBar.classList.remove('bg-success');
                    progressBar.classList.add('bg-warning');
                    progressText.textContent += ' ✅ Complete!';
                }
            } else {
                progressBar.style.width = '100%';
                progressBar.classList.remove('bg-success', 'bg-warning');
                progressBar.classList.add('bg-secondary');
                progressText.textContent = I18n.t('dashboard.gamification.no_goal_set');
            }
        }
    } catch (e) { console.error("Failed to load daily goal", e); }
}

// Open Daily Goal Modal
window.openDailyGoalModal = function () {
    const modal = new bootstrap.Modal(document.getElementById('dailyGoalModal'));
    modal.show();
};

// Save Daily Goal
window.saveDailyGoal = async function () {
    const goalType = document.getElementById('daily-goal-type').value;
    const targetValue = parseInt(document.getElementById('daily-goal-target').value) || 3;
    const saveAsDefault = document.getElementById('daily-goal-default').checked;

    try {
        const token = AuthService.getToken();
        const res = await fetch('/api/gamification/daily-goal', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                goal_type: goalType,
                target_value: targetValue,
                save_as_default: saveAsDefault
            })
        });

        if (res.ok) {
            showToast('Daily goal set!', 'success');
            bootstrap.Modal.getInstance(document.getElementById('dailyGoalModal')).hide();
            loadDailyGoal();
        } else {
            showToast('Failed to set goal', 'danger');
        }
    } catch (e) {
        console.error("Failed to save daily goal", e);
        showToast('Error saving goal', 'danger');
    }
};

// Users List Loader (Students/Teachers) - shared implementation
const usersByRole = {
    student: [],
    teacher: [],
    admin: []
};

function renderUserList(role, users) {
    const containerId = role === 'teacher' ? 'teacher-list' : role === 'admin' ? 'admin-list' : 'student-list';
    const label = role === 'teacher' ? 'teachers' : role === 'admin' ? 'admins' : 'students';
    const container = document.getElementById(containerId);
    if (!container) return;

    if (users.length === 0) {
        container.innerHTML = `<div class="text-muted p-4">No ${label} match your search.</div>`;
        return;
    }

    container.innerHTML = users.map(u => `
        <div class="col-md-4 ${role}-card" data-name="${(u.first_name + ' ' + u.last_name).toLowerCase()}" data-username="${u.username.toLowerCase()}">
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title">${escapeHtml(u.first_name)} ${escapeHtml(u.last_name)}</h5>
                    <p class="text-muted mb-1">@${escapeHtml(u.username)}</p>
                    <p class="mb-2">
                        <span class="badge bg-primary">Level ${u.level || 1}</span>
                        <span class="badge bg-success">${u.xp || 0} XP</span>
                    </p>
                    <button class="btn btn-sm btn-outline-primary" onclick="viewStudentDetail(${u.id})">View Details</button>
                </div>
            </div>
        </div>
    `).join('');
}

async function loadUsersByRole(role) {
    const containerId = role === 'teacher' ? 'teacher-list' : role === 'admin' ? 'admin-list' : 'student-list';
    const label = role === 'teacher' ? 'teachers' : role === 'admin' ? 'admins' : 'students';
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = `<div class="text-center text-muted p-4">Loading ${label}...</div>`;

    try {
        const token = AuthService.getToken();
        const res = await fetch(`/api/auth/users?role=${role}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!res.ok) {
            container.innerHTML = `<div class="text-muted p-4">No ${label} found or API not available.</div>`;
            return;
        }

        const users = await res.json();
        usersByRole[role] = users;

        if (users.length === 0) {
            container.innerHTML = `<div class="text-muted p-4">No ${label} found yet.</div>`;
            return;
        }

        renderUserList(role, users);
    } catch (e) {
        container.innerHTML = `<div class="text-danger p-4">Failed to load ${label}.</div>`;
        console.error("User load error", e);
    }
}

function filterUsersList(role, inputId) {
    const searchInput = document.getElementById(inputId);
    if (!searchInput) return;

    const query = searchInput.value.toLowerCase().trim();

    if (!query) {
        renderUserList(role, usersByRole[role]);
        return;
    }

    const filtered = usersByRole[role].filter(u => {
        const fullName = (u.first_name + ' ' + u.last_name).toLowerCase();
        const username = u.username.toLowerCase();
        return fullName.includes(query) || username.includes(query);
    });

    renderUserList(role, filtered);
}

// Students List Loader (Teacher Only)
window.loadStudents = function loadStudents() {
    return loadUsersByRole('student');
};

window.filterStudentsList = function filterStudentsList() {
    return filterUsersList('student', 'students-search');
};

// Teachers List Loader (Admin Only)
window.loadTeachers = function loadTeachers() {
    return loadUsersByRole('teacher');
};

window.filterTeachersList = function filterTeachersList() {
    return filterUsersList('teacher', 'teachers-search');
};

// Admins List Loader (Admin Only)
window.loadAdmins = function loadAdmins() {
    return loadUsersByRole('admin');
};

window.filterAdminsList = function filterAdminsList() {
    return filterUsersList('admin', 'admins-search');
};


// Leaderboard Loader
window.loadLeaderboard = async function loadLeaderboard() {
    const tbody = document.getElementById('leaderboard-body');
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">Loading...</td></tr>';

    try {
        const token = AuthService.getToken();
        const period = document.getElementById('leaderboard-period')?.value || 'weekly';

        const res = await fetch(`/api/gamification/leaderboard?period=${period}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!res.ok) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">Leaderboard not available.</td></tr>';
            return;
        }

        const entries = await res.json();

        if (entries.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No rankings yet.</td></tr>';
            return;
        }

        tbody.innerHTML = entries.map(e => `
            <tr>
                <td><span class="badge ${e.rank <= 3 ? 'bg-warning text-dark' : 'bg-secondary'}">#${e.rank}</span></td>
                <td>${e.username}</td>
                <td><strong>${e.xp}</strong> XP</td>
                <td>Level ${e.level}</td>
            </tr>
        `).join('');
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger">Failed to load leaderboard.</td></tr>';
        console.error("Leaderboard load error", e);
    }
};

let gradingQueueCache = [];
let currentGradingStatusFilter = 'all';

function getGradingStatusLabel(status) {
    const keyByStatus = {
        submitted: 'grading.status.submitted',
        ai_graded: 'grading.status.ai_graded',
        graded: 'grading.status.graded',
        pending: 'grading.status.pending'
    };
    const key = keyByStatus[status];
    if (key && typeof I18n !== 'undefined' && I18n.t) {
        return I18n.t(key);
    }
    return status;
}

function getGradingStatusBadgeClass(status) {
    const classes = {
        submitted: 'bg-warning text-dark',
        ai_graded: 'bg-info text-dark',
        graded: 'bg-success',
        returned: 'bg-secondary'
    };
    return classes[status] || 'bg-secondary';
}

function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

function renderGradingQueue(submissions) {
    const container = document.getElementById('grading-list');
    if (!container) return;

    if (!submissions.length) {
        const emptyText = (typeof I18n !== 'undefined' && I18n.t)
            ? I18n.t('grading.empty_state')
            : 'No pending submissions.';
        container.innerHTML = `<p class="text-muted">${emptyText}</p>`;
        return;
    }

    container.innerHTML = submissions.map(sub => {
        const studentName = sub.student_name || `Student #${sub.student_id}`;
        const assessmentTitle = sub.assessment_title || `Assessment #${sub.assessment_id}`;
        const submittedAt = sub.submitted_at ? new Date(sub.submitted_at).toLocaleDateString() : '';
        const statusLabel = getGradingStatusLabel(sub.status);
        const statusClass = getGradingStatusBadgeClass(sub.status);

        return `
            <div class="card">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <div>
                            <h5 class="mb-1">${escapeHtml(studentName)}</h5>
                            <div class="text-muted small">${escapeHtml(assessmentTitle)}</div>
                        </div>
                        <span class="badge ${statusClass}">${escapeHtml(statusLabel)}</span>
                    </div>
                    <div class="text-muted small">${escapeHtml(submittedAt)}</div>
                </div>
            </div>
        `;
    }).join('');
}

function applyGradingFilter() {
    let filtered = gradingQueueCache;

    if (currentGradingStatusFilter === 'pending') {
        filtered = gradingQueueCache.filter(s =>
            s.status === 'submitted' || s.status === 'ai_graded'
        );
    } else if (currentGradingStatusFilter === 'graded') {
        filtered = gradingQueueCache.filter(s => s.status === 'graded');
    }

    renderGradingQueue(filtered);
}

window.filterGradingQueue = function filterGradingQueue(status, tab) {
    currentGradingStatusFilter = status;

    const tabs = document.querySelectorAll('#grading-filter-tabs .tab');
    tabs.forEach(t => t.classList.remove('active'));
    if (tab) tab.classList.add('active');

    applyGradingFilter();
};

window.loadGradingQueue = async function loadGradingQueue() {
    const container = document.getElementById('grading-list');
    if (!container) return;

    container.innerHTML = '<p class="text-muted">Loading...</p>';

    const activeTab = document.querySelector('#grading-filter-tabs .tab.active');
    if (activeTab?.dataset?.gradingFilter) {
        currentGradingStatusFilter = activeTab.dataset.gradingFilter;
    }

    try {
        const token = AuthService.getToken();
        const res = await fetch('/api/assessments/submissions?status=submitted&status=graded&status=ai_graded', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!res.ok) {
            const fallback = (typeof I18n !== 'undefined' && I18n.t)
                ? I18n.t('grading.messages.error_loading_submissions', { error: res.status })
                : 'Failed to load submissions.';
            container.innerHTML = `<p class="text-danger">${fallback}</p>`;
            return;
        }

        gradingQueueCache = await res.json();
        applyGradingFilter();
    } catch (e) {
        const fallback = (typeof I18n !== 'undefined' && I18n.t)
            ? I18n.t('grading.messages.error_loading_submissions', { error: e.message })
            : 'Failed to load submissions.';
        container.innerHTML = `<p class="text-danger">${fallback}</p>`;
    }
};

// Help Queue Loader (Teacher Only)
let allHelpRequests = []; // Store globally for filtering
let currentHelpPriorityFilter = 'all';

window.loadHelpQueue = async function loadHelpQueue() {
    const container = document.getElementById('help-queue-list');
    if (!container) return;

    container.innerHTML = '<div class="text-center text-muted p-4">Loading help requests...</div>';

    try {
        const token = AuthService.getToken();
        const res = await fetch('/api/classroom/help', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!res.ok) {
            container.innerHTML = '<div class="text-muted p-4">No help requests or API not available.</div>';
            return;
        }

        allHelpRequests = await res.json();
        renderHelpQueue(allHelpRequests);
    } catch (e) {
        container.innerHTML = '<div class="text-danger p-4">Failed to load help requests.</div>';
        console.error("Help queue load error", e);
    }
};

// Filter help requests by priority (28.1)
window.filterHelpRequestsByPriority = function filterHelpRequestsByPriority(priority, btn) {
    currentHelpPriorityFilter = priority;

    // Update active button
    const tabs = document.querySelectorAll('#help-priority-filter-tabs button');
    tabs.forEach(t => t.classList.remove('active'));
    if (btn) btn.classList.add('active');

    // Filter and render
    let filtered = allHelpRequests;
    if (priority === 'high') {
        filtered = allHelpRequests.filter(r => r.priority >= 3);
    } else if (priority === 'medium') {
        filtered = allHelpRequests.filter(r => r.priority === 2);
    } else if (priority === 'low') {
        filtered = allHelpRequests.filter(r => r.priority <= 1 || !r.priority);
    }

    renderHelpQueue(filtered);
};

function renderHelpQueue(requests) {
    const container = document.getElementById('help-queue-list');
    if (!container) return;

    if (requests.length === 0) {
        container.innerHTML = '<div class="text-muted p-4 text-center">🎉 No help requests matching filter!</div>';
        return;
    }

    container.innerHTML = requests.map(r => {
        // Build context badges
        let contextBadges = '';
        if (r.content_title) {
            const icon = r.content_type === 'lesson' ? '📖' :
                r.content_type === 'exercise' ? '🏋️' :
                    r.content_type === 'assessment' ? '📝' : '📄';
            contextBadges += `<span class="badge bg-primary me-1" title="Content">${icon} ${r.content_title}</span>`;
        }
        if (r.study_plan_title) {
            contextBadges += `<span class="badge bg-secondary me-1" title="Study Plan">📋 ${r.study_plan_title}</span>`;
        }

        return `
            <a href="javascript:void(0)" class="list-group-item list-group-item-action" onclick="viewHelpRequest(${r.id})">
                <div class="d-flex w-100 justify-content-between">
                    <h5 class="mb-1">${r.subject || 'Help Request'}</h5>
                    <span class="badge ${r.priority >= 3 ? 'bg-danger' : r.priority >= 2 ? 'bg-warning text-dark' : 'bg-secondary'}">${r.priority >= 3 ? 'Urgent' : r.priority >= 2 ? 'Important' : 'Normal'}</span>
                </div>
                <p class="mb-1">${r.request_text || r.description}</p>
                ${contextBadges ? `<div class="mb-1">${contextBadges}</div>` : ''}
                <small class="text-muted">From: ${r.student_name || 'Student #' + r.student_id} | ${r.status}</small>
            </a>
        `}).join('');
}


// --- STUDENT DETAIL & HELP REQUEST IMPLEMENTATIONS ---
let currentStudentId = null;
let currentHelpRequestId = null;

async function loadTeacherPlansForAssignment() {
    const token = AuthService.getToken();
    const res = await fetch('/api/study-plans/', {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!res.ok) return [];
    return await res.json();
}

window.viewStudentDetail = async function viewStudentDetail(id) {
    currentStudentId = id;

    try {
        const token = AuthService.getToken();

        // Try to get student info from the users endpoint
        const res = await fetch(`/api/auth/users?role=student`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!res.ok) {
            showToast('Could not load student details', 'danger');
            return;
        }

        const students = await res.json();
        const student = students.find(s => s.id === id);

        if (!student) {
            showToast('Student not found', 'warning');
            return;
        }

        // Populate modal
        document.getElementById('student-detail-name').textContent = `${student.first_name} ${student.last_name}`;
        document.getElementById('student-detail-username').textContent = `@${student.username}`;
        document.getElementById('student-detail-xp').textContent = student.xp || 0;
        document.getElementById('student-detail-level').textContent = student.level || 1;
        document.getElementById('student-detail-streak').textContent = student.current_streak || 0;

        // Try to load badges
        const badgesContainer = document.getElementById('student-detail-badges');
        try {
            const badgeRes = await fetch(`/api/gamification/badges?user_id=${id}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (badgeRes.ok) {
                const badges = await badgeRes.json();
                const earned = badges.filter(b => b.earned);
                if (earned.length > 0) {
                    badgesContainer.innerHTML = earned.slice(0, 5).map(b =>
                        `<span class="badge bg-warning text-dark">${b.name}</span>`
                    ).join('');
                } else {
                    badgesContainer.innerHTML = '<span class="text-muted">No badges earned yet</span>';
                }
            }
        } catch (e) {
            badgesContainer.innerHTML = '<span class="text-muted">No badges earned yet</span>';
        }

        // Load student progress stats
        try {
            const progressRes = await fetch(`/api/students/${id}/progress`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (progressRes.ok) {
                const progress = await progressRes.json();
                const lessonsEl = document.getElementById('student-lessons-completed');
                const assessmentsEl = document.getElementById('student-assessments-taken');
                const avgScoreEl = document.getElementById('student-avg-score');
                const studyTimeEl = document.getElementById('student-study-time');
                if (lessonsEl) lessonsEl.textContent = progress.lessons_completed || 0;
                if (assessmentsEl) assessmentsEl.textContent = progress.assessments_taken || 0;
                if (avgScoreEl) avgScoreEl.textContent = progress.avg_score ? `${Math.round(progress.avg_score)}%` : '-';
                if (studyTimeEl) studyTimeEl.textContent = progress.study_time_hours ? `${Math.round(progress.study_time_hours)}h` : '0h';
            }
        } catch (e) {
            console.warn('Failed to load student progress:', e);
        }

        // Load teacher notes
        window.currentStudentId = id;
        try {
            const notesRes = await fetch(`/api/students/${id}/notes`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (notesRes.ok) {
                const notesData = await notesRes.json();
                const notesEl = document.getElementById('student-teacher-notes');
                if (notesEl) notesEl.value = notesData.notes || '';
            }
        } catch (e) {
            console.warn('Failed to load student notes:', e);
        }

        // Show modal
        new bootstrap.Modal(document.getElementById('studentDetailModal')).show();

        // Assignment UI (teacher/admin only)
        const assignContainer = document.getElementById('student-assign-plan-container');
        if (assignContainer) {
            if (!isTeacherOrAdmin) {
                assignContainer.classList.add('d-none');
            } else {
                assignContainer.classList.remove('d-none');
                const selectEl = document.getElementById('student-assign-plan-select');
                const btnEl = document.getElementById('student-assign-plan-btn');

                if (selectEl && btnEl) {
                    selectEl.disabled = true;
                    btnEl.disabled = true;
                    selectEl.innerHTML = '<option value="" disabled selected>Loading study plans...</option>';

                    const plans = await loadStudyPlans();
                    if (!plans || plans.length === 0) {
                        selectEl.innerHTML = '<option value="" disabled selected>No study plans available</option>';
                        selectEl.disabled = true;
                        btnEl.disabled = true;
                    } else {
                        selectEl.innerHTML = plans
                            .map(p => `<option value="${p.id}">${p.title}</option>`)
                            .join('');
                        selectEl.disabled = false;
                        btnEl.disabled = false;
                    }
                }
            }
        }
    } catch (err) {
        console.error('Failed to load student details:', err);
        showToast('Failed to load student details', 'danger');
    }
};

window.assignStudyPlanToStudent = async function assignStudyPlanToStudent() {
    if (!currentStudentId) return;
    const selectEl = document.getElementById('student-assign-plan-select');
    if (!selectEl || !selectEl.value) {
        showToast('Select a study plan first', 'warning');
        return;
    }

    try {
        const token = AuthService.getToken();
        const planId = parseInt(selectEl.value, 10);
        const res = await fetch(`/api/study-plans/${planId}/assign`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ student_ids: [currentStudentId] })
        });

        if (!res.ok) {
            let err = null;
            try { err = await res.json(); } catch { }
            showToast(err?.detail || 'Failed to assign study plan', 'danger');
            return;
        }

        showToast('Study plan assigned', 'success');
    } catch (e) {
        console.error('Assign plan error:', e);
        showToast('Network error assigning study plan', 'danger');
    }
};

window.sendMessageToStudent = function sendMessageToStudent() {
    if (!currentStudentId) return;

    // Close student detail modal
    const studentModal = bootstrap.Modal.getInstance(document.getElementById('studentDetailModal'));
    if (studentModal) studentModal.hide();

    // Pre-select the student in compose modal and open it
    const composeModal = new bootstrap.Modal(document.getElementById('composeModal'));
    composeModal.show();

    // After modal opens, select the student
    setTimeout(() => {
        const selectEl = document.getElementById('compose-to');
        if (selectEl) {
            selectEl.value = currentStudentId.toString();
        }
    }, 300);
};

window.viewHelpRequest = async function viewHelpRequest(id) {
    currentHelpRequestId = id;

    try {
        const token = AuthService.getToken();

        // Get all help requests and find the one we need
        const res = await fetch('/api/classroom/help', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!res.ok) {
            showToast('Could not load help request', 'danger');
            return;
        }

        const requests = await res.json();
        const request = requests.find(r => r.id === id);

        if (!request) {
            showToast('Help request not found', 'warning');
            return;
        }

        // Populate modal
        document.getElementById('help-request-subject').textContent = request.subject || 'Help Request';
        document.getElementById('help-request-content').textContent = request.request_text || request.description || 'No details provided';
        document.getElementById('help-request-student').textContent = `From: ${request.student_name || 'Student #' + request.student_id}`;

        // Populate learning context
        const contextEl = document.getElementById('help-request-context');
        if (contextEl) {
            const contextParts = [];

            if (request.content_title) {
                const icon = request.content_type === 'lesson' ? '📖' :
                    request.content_type === 'exercise' ? '🏋️' :
                        request.content_type === 'assessment' ? '📝' : '📄';
                contextParts.push(`<span class="badge bg-primary me-2">${icon} ${request.content_title}</span>`);
            }

            if (request.study_plan_title) {
                contextParts.push(`<span class="badge bg-secondary me-2">📋 ${request.study_plan_title}</span>`);
            }

            if (request.question_text) {
                contextParts.push(`<span class="badge bg-info text-dark me-2" title="${request.question_text}">❓ Question</span>`);
            }

            if (contextParts.length > 0) {
                contextEl.innerHTML = `
                    <div class="alert alert-light border mb-3">
                        <small class="text-muted d-block mb-1">📍 Student was studying:</small>
                        <div class="mb-2">${contextParts.join('')}</div>
                        ${request.content_id ? `<button class="btn btn-sm btn-outline-primary" onclick="viewContent(${request.content_id})">👁️ View Content</button>` : ''}
                    </div>
                `;
            } else {
                contextEl.innerHTML = `
                    <div class="alert alert-warning border mb-3">
                        <small class="text-muted">⚠️ No learning context captured (student wasn't viewing specific content)</small>
                    </div>
                `;
            }
        }

        // Store request for AI drafting
        window.currentHelpRequest = request;

        // Status badge
        const statusEl = document.getElementById('help-request-status');
        statusEl.textContent = request.status || 'Pending';
        statusEl.className = `badge ${request.status === 'resolved' ? 'bg-success' : 'bg-warning text-dark'}`;

        // Priority badge
        const priorityEl = document.getElementById('help-request-priority');
        const priority = request.priority || request.urgency || 1;
        priorityEl.textContent = priority >= 3 ? 'Urgent' : priority >= 2 ? 'Important' : 'Normal';
        priorityEl.className = `badge ${priority >= 3 ? 'bg-danger' : priority >= 2 ? 'bg-warning text-dark' : 'bg-secondary'}`;

        // Show/hide resolve button based on status
        const resolveBtn = document.getElementById('resolve-help-btn');
        const notesContainer = document.getElementById('help-request-notes-container');
        if (request.status === 'resolved') {
            resolveBtn.classList.add('hidden');
            notesContainer.classList.add('hidden');
        } else {
            resolveBtn.classList.remove('hidden');
            notesContainer.classList.remove('hidden');
        }

        // Clear notes
        document.getElementById('help-request-notes').value = '';

        // Reset response section
        document.getElementById('help-response-text').value = '';
        document.getElementById('ai-draft-area').classList.add('hidden');

        // Show/hide response section based on status
        const responseSection = document.getElementById('help-response-section');
        if (request.status === 'resolved') {
            responseSection.classList.add('hidden');
        } else {
            responseSection.classList.remove('hidden');
        }

        // Show modal
        new bootstrap.Modal(document.getElementById('helpRequestModal')).show();
    } catch (err) {
        console.error('Failed to load help request:', err);
        showToast('Failed to load help request', 'danger');
    }
};

window.resolveHelpRequest = async function resolveHelpRequest() {
    if (!currentHelpRequestId) return;

    const notes = document.getElementById('help-request-notes').value;

    try {
        const token = AuthService.getToken();

        const res = await fetch(`/api/classroom/help/${currentHelpRequestId}/resolve`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ notes: notes || null })
        });

        if (res.ok) {
            showToast('Help request resolved!', 'success');

            // Close modal
            const helpModal = bootstrap.Modal.getInstance(document.getElementById('helpRequestModal'));
            if (helpModal) helpModal.hide();

            // Refresh help queue
            loadHelpQueue();
        } else {
            const err = await res.json();
            showToast('Failed to resolve: ' + (err.detail || 'Unknown error'), 'danger');
        }
    } catch (err) {
        console.error('Failed to resolve help request:', err);
        showToast('Failed to resolve help request', 'danger');
    }
};

/**
 * Draft a response using AI based on the student's question
 * Now includes learning context for more relevant responses
 */
window.draftAIResponse = async function draftAIResponse() {
    const subject = document.getElementById('help-request-subject').textContent;
    const content = document.getElementById('help-request-content').textContent;
    const student = document.getElementById('help-request-student').textContent;

    // Get learning context from stored request
    const request = window.currentHelpRequest || {};

    const aiDraftArea = document.getElementById('ai-draft-area');
    const aiDraftLoading = document.getElementById('ai-draft-loading');
    const aiDraftResult = document.getElementById('ai-draft-result');
    const aiDraftContent = document.getElementById('ai-draft-content');
    const aiDraftBtn = document.getElementById('ai-draft-btn');

    // Show loading
    aiDraftArea.classList.remove('hidden');
    aiDraftLoading.classList.remove('hidden');
    aiDraftResult.classList.add('hidden');
    aiDraftBtn.disabled = true;
    aiDraftBtn.innerHTML = '⏳ Drafting...';

    try {
        const token = AuthService.getToken();

        // Build context for AI with learning context
        let contextInfo = '';
        if (request.content_title) {
            contextInfo += `\n\nLEARNING CONTEXT:
- The student was studying: "${request.content_title}" (${request.content_type || 'content'})`;
        }
        if (request.study_plan_title) {
            contextInfo += `\n- Part of study plan: "${request.study_plan_title}"`;
        }
        if (request.question_text) {
            contextInfo += `\n- Specific question they were on: "${request.question_text}"`;
        }

        const prompt = `A student needs help with the following:

Subject: ${subject}
Question: ${content}${contextInfo}

Please draft a helpful, educational response that:
1. Addresses their specific question
2. Provides clear explanations referencing the content they were studying
3. Suggests next steps or resources if applicable
4. Is encouraging and supportive

Keep the response concise but thorough (2-4 paragraphs).`;

        // Use the chat endpoint if we have content_id for richer context
        const endpoint = request.content_id ? '/api/ai/chat' : '/api/ai/answer-question';
        const body = request.content_id
            ? {
                message: prompt,
                content_id: request.content_id,
                study_plan_id: request.study_plan_id
            }
            : {
                question: prompt,
                context: `Teacher drafting response for help request. ${contextInfo}`
            };

        const res = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(body)
        });

        const data = await res.json();

        // Handle both endpoint response formats
        const answer = data.answer || data.response || data.message;
        const success = data.success !== false && res.ok;

        if (success && answer) {
            aiDraftContent.textContent = answer;
            aiDraftLoading.classList.add('hidden');
            aiDraftResult.classList.remove('hidden');
            showToast('AI draft generated with learning context!', 'success');
        } else if (!res.ok) {
            // API error
            const errorMsg = data.detail || data.error || `API Error (${res.status})`;
            showToast(`AI Draft failed: ${errorMsg}`, 'danger');
            aiDraftLoading.classList.add('hidden');
            aiDraftArea.classList.add('hidden');
        } else {
            // No content returned
            showToast('AI service returned empty response. Check AI settings.', 'warning');
            aiDraftLoading.classList.add('hidden');
            aiDraftArea.classList.add('hidden');
        }
    } catch (e) {
        console.error('AI Draft error:', e);
        showToast('Network error generating AI draft. Is AI service running?', 'danger');
        aiDraftLoading.classList.add('hidden');
        aiDraftArea.classList.add('hidden');
    } finally {
        aiDraftBtn.disabled = false;
        aiDraftBtn.innerHTML = '🤖 AI Draft Response';
    }
};


/**
 * Use the AI draft as the response
 */
window.useAIDraft = function useAIDraft() {
    const aiDraftContent = document.getElementById('ai-draft-content').textContent;
    const responseTextarea = document.getElementById('help-response-text');
    responseTextarea.value = aiDraftContent;

    // Hide the AI draft area
    document.getElementById('ai-draft-area').classList.add('hidden');
    showToast('AI draft applied! Edit if needed and click Send.', 'info');
};

/**
 * Send response to student via messaging system
 */
window.sendHelpResponse = async function sendHelpResponse() {
    if (!currentHelpRequestId) {
        showToast('No help request selected', 'warning');
        return;
    }

    const responseText = document.getElementById('help-response-text').value.trim();

    if (!responseText) {
        showToast('Please enter a response message', 'warning');
        return;
    }

    const subject = document.getElementById('help-request-subject').textContent;
    const sendBtn = document.getElementById('send-response-btn');

    sendBtn.disabled = true;
    sendBtn.innerHTML = '⏳ Sending...';

    try {
        const token = AuthService.getToken();

        // First, get the student ID from the help request
        const helpRes = await fetch('/api/classroom/help', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!helpRes.ok) throw new Error('Could not fetch help request details');

        const requests = await helpRes.json();
        const request = requests.find(r => r.id === currentHelpRequestId);

        if (!request || !request.student_id) {
            throw new Error('Could not find student for this request');
        }

        // Send message to student via messaging API
        const msgRes = await fetch('/api/classroom/messages', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                recipient_id: request.student_id,
                subject: `Re: ${subject}`,
                body: responseText
            })
        });

        if (!msgRes.ok) {
            const err = await msgRes.json();
            throw new Error(err.detail || 'Failed to send message');
        }

        showToast('Response sent to student!', 'success');

        // Clear the response textarea
        document.getElementById('help-response-text').value = '';
        document.getElementById('ai-draft-area').classList.add('hidden');

        // Optionally auto-resolve the help request
        const notesField = document.getElementById('help-request-notes');
        if (!notesField.value) {
            notesField.value = 'Responded to student via message.';
        }

    } catch (e) {
        console.error('Send response error:', e);
        showToast('Failed to send response: ' + e.message, 'danger');
    } finally {
        sendBtn.disabled = false;
        sendBtn.innerHTML = '📧 Send Reply to Student';
    }
};

// --- HIERARCHICAL CONTENT MANAGEMENT ---

// Store for hierarchical content tree
let libraryTreeCache = null;
let studyPlansCache = [];

/**
 * Load content organized by study plan hierarchy (tree view)
 */
window.loadLibraryTree = async function loadLibraryTree() {
    const grid = document.getElementById('content-list');
    grid.innerHTML = '<div class="text-center p-3">Loading hierarchical view...</div>';

    try {
        const token = AuthService.getToken();

        // Fetch hierarchical content tree
        const res = await fetch('/api/content/tree', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!res.ok) throw new Error('Failed to load content tree');

        const tree = await res.json();
        libraryTreeCache = tree;

        let html = '';

        // Render study plans with nested content
        const studyPlans = Object.values(tree.by_study_plan || {});
        if (studyPlans.length > 0) {
            html += '<h5 class="mb-3">📚 Study Plans</h5>';

            for (const plan of studyPlans) {
                html += `
                    <div class="card mb-3 study-plan-tree" data-plan-id="${plan.id}">
                        <div class="card-header bg-primary bg-opacity-10 d-flex justify-content-between align-items-center">
                            <div class="d-flex align-items-center">
                                <button class="btn btn-sm btn-link text-decoration-none me-2 toggle-plan-btn" onclick="togglePlanContents(${plan.id})">
                                    <span class="toggle-icon">▶</span>
                                </button>
                                <strong>📘 ${plan.title}</strong>
                                <span class="badge bg-secondary ms-2">${plan.contents.length} items</span>
                            </div>
                            <div class="btn-group btn-group-sm">
                                <button class="btn btn-outline-success" onclick="addTopicToPlan(${plan.id})" title="Add Topic">+ Topic</button>
                                <button class="btn btn-outline-primary" onclick="generateForPlan(${plan.id})" title="Generate Content">🤖 Generate</button>
                                <button class="btn btn-outline-info" onclick="viewPlanGrades(${plan.id})" title="View Grades">📊 Grades</button>
                            </div>
                        </div>
                        <div class="card-body plan-contents hidden" id="plan-contents-${plan.id}">
                            ${renderPlanContents(plan.id, plan.contents)}
                        </div>
                    </div>
                `;
            }
        }

        // Render standalone content
        if (tree.standalone && tree.standalone.length > 0) {
            html += '<h5 class="mb-3 mt-4">📄 Standalone Content</h5>';
            html += '<div class="row">';
            for (const item of tree.standalone) {
                html += renderContentCard(item);
            }
            html += '</div>';
        }

        if (!studyPlans.length && (!tree.standalone || !tree.standalone.length)) {
            const emptyHint = isTeacherOrAdmin
                ? 'Create your first study plan or content using the Create tab.'
                : 'No content has been assigned to you yet. Check back later or contact your teacher.';
            html = `
                <div class="text-center p-5">
                    <h4>No content yet</h4>
                    <p class="text-muted">${emptyHint}</p>
                </div>
            `;
        }

        grid.innerHTML = html;
        applyLibraryPermissionUI(grid);

        // Update stats
        const totalItems = (tree.standalone?.length || 0) +
            Object.values(tree.by_study_plan || {}).reduce((sum, p) => sum + p.contents.length, 0);
        document.getElementById('lib-total').textContent = totalItems;

    } catch (err) {
        console.error('Failed to load library tree:', err);
        grid.innerHTML = '<div class="text-danger text-center p-3">Failed to load content tree</div>';
    }
};

/**
 * Render contents within a study plan
 */
function renderPlanContents(planId, contents) {
    if (!contents || contents.length === 0) {
        return '<p class="text-muted">No content in this plan yet.</p>';
    }

    const typeIcons = {
        lesson: '📖', exercise: '✏️', assessment: '📝', qa: '❓'
    };
    const typeColors = {
        lesson: 'primary', exercise: 'success', assessment: 'warning', qa: 'info'
    };

    return `
        <div class="list-group list-group-flush">
            ${contents.map(item => `
                <div class="list-group-item d-flex justify-content-between align-items-center">
                    <div>
                        <span class="badge bg-${typeColors[item.content_type] || 'secondary'} me-2">
                            ${typeIcons[item.content_type] || '📄'} ${item.content_type.toUpperCase()}
                        </span>
                        ${item.title}
                        <small class="text-muted ms-2">Difficulty: ${'⭐'.repeat(item.difficulty || 1)}</small>
                    </div>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary" onclick="viewContent(${item.id})">👁️</button>
                        <button class="btn btn-outline-success" onclick="startSession(${item.id}, ${planId})" title="Start with guided navigation">▶️</button>
                        <button class="btn btn-outline-warning" onclick="editContent(${item.id})">✏️</button>
                        <button class="btn btn-outline-danger" onclick="deleteContent(${item.id})">🗑️</button>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

/**
 * Render a content card for grid view
 */
function renderContentCard(item) {
    const type = item.content_type || 'lesson';
    const typeColors = {
        lesson: 'bg-primary', exercise: 'bg-success', assessment: 'bg-warning text-dark', qa: 'bg-info'
    };
    const typeIcons = {
        lesson: '📖', exercise: '✏️', assessment: '📝', qa: '❓'
    };

    return `
        <div class="col-md-4 col-lg-3">
            <div class="card h-100" data-creator-id="${item.creator_id || ''}">
                <div class="card-body">
                    <span class="badge ${typeColors[type] || 'bg-secondary'} mb-2">
                        ${typeIcons[type] || '📄'} ${type.toUpperCase()}
                    </span>
                    <h5 class="card-title">${item.title}</h5>
                    ${(item.creator_id && currentUserId && item.creator_id !== currentUserId && (item.creator_name || item.creator_username)) ? `
                    <p class="text-muted small mb-2">
                        From: ${item.creator_name || 'Student'}${item.creator_username ? ` (@${item.creator_username})` : ''}
                    </p>` : ''}
                    <p class="text-muted small mb-2">
                        Difficulty: ${'⭐'.repeat(item.difficulty || 1)}
                    </p>
                </div>
                <div class="card-footer bg-transparent border-0">
                    <div class="btn-group w-100" role="group">
                        <button class="btn btn-sm btn-outline-primary" onclick="viewContent(${item.id})">👁️</button>
                        <button class="btn btn-sm btn-outline-success" onclick="startSession(${item.id})">▶️</button>
                        <button class="btn btn-sm btn-outline-warning" onclick="editContent(${item.id})">✏️</button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteContent(${item.id})">🗑️</button>
                    </div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Toggle plan contents visibility
 */
window.togglePlanContents = function (planId) {
    const contentsDiv = document.getElementById(`plan-contents-${planId}`);
    const toggleIcon = document.querySelector(`[data-plan-id="${planId}"] .toggle-icon`);

    if (contentsDiv.classList.contains('hidden')) {
        contentsDiv.classList.remove('hidden');
        if (toggleIcon) toggleIcon.textContent = '▼';
    } else {
        contentsDiv.classList.add('hidden');
        if (toggleIcon) toggleIcon.textContent = '▶';
    }
};

/**
 * Generate full topic package for a study plan
 */
window.generateForPlan = async function (planId) {
    const topic = await showPrompt('Enter topic name to generate content for:', '', 'Generate Content');
    if (!topic) return;

    const objectives = await showPrompt(
        'Enter learning objectives (one per line):',
        'Understand key concepts\nApply knowledge in practice',
        'Learning Objectives',
        true
    );
    if (!objectives) return;

    const token = AuthService.getToken();

    try {
        const res = await fetch('/api/generate/full-topic-package', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                subject: topic,
                topic_name: topic,
                grade_level: 'High School',
                learning_objectives: objectives.split('\n').filter(l => l.trim()),
                include_lesson: true,
                include_exercises: true,
                include_assessment: true,
                num_exercises: 4,
                auto_save: true,
                study_plan_id: planId,
                phase_index: 0
            })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Generation failed');
        }

        const result = await res.json();
        showToast(`Generated and saved: ${result.saved_content_ids?.length || 0} items!`, 'success');

        // Refresh library view
        loadLibraryTree();

    } catch (err) {
        showToast('Generation failed: ' + err.message, 'danger');
    }
};

/**
 * Add a new topic to a study plan
 */
window.addTopicToPlan = async function (planId) {
    const title = await showPrompt('Enter topic title:', '', 'New Topic');
    if (!title) return;

    const token = AuthService.getToken();

    try {
        const res = await fetch(`/api/study-plans/${planId}/topics`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                title: title,
                content_type: 'lesson',
                difficulty: 1
            })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Failed to add topic');
        }

        showToast('Topic added successfully!', 'success');
        loadLibraryTree();

    } catch (err) {
        showToast('Failed to add topic: ' + err.message, 'danger');
    }
};

/**
 * View aggregate grades for a study plan
 */
window.viewPlanGrades = async function (planId) {
    const token = AuthService.getToken();

    try {
        const res = await fetch(`/api/study-plans/${planId}/grades`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Failed to load grades');
        }

        const grades = await res.json();

        // Show grades summary using toast (for quick info)
        const summary = `📊 Total: ${grades.total_assessments} | Graded: ${grades.graded_submissions} | Avg: ${grades.average_score || 'N/A'}%`;
        showToast(summary, 'info', 5000);

    } catch (err) {
        showToast('Failed to load grades: ' + err.message, 'danger');
    }
};

/**
 * Load list of study plans for dropdown selectors
 */
window.loadStudyPlans = async function () {
    const token = AuthService.getToken();

    try {
        const res = await fetch('/api/study-plans', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (res.ok) {
            studyPlansCache = await res.json();
            return studyPlansCache;
        }
    } catch (err) {
        console.error('Failed to load study plans:', err);
    }

    return [];
};

/**
 * Switch between flat and tree view in library
 */
window.toggleLibraryView = function (viewType) {
    const flatBtn = document.getElementById('view-flat-btn');
    const treeBtn = document.getElementById('view-tree-btn');

    if (viewType === 'tree') {
        flatBtn?.classList.remove('active');
        treeBtn?.classList.add('active');
        loadLibraryTree();
    } else {
        treeBtn?.classList.remove('active');
        flatBtn?.classList.add('active');
        loadLibrary();
    }
};

// Initial Load (moved to end of file to ensure all functions are defined)

// ===============================
// Library Content Search
// ===============================

/**
 * Debounce utility function for input handlers.
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Filter library content based on search query.
 * Works with both flat and tree views.
 * @param {string} query - Search query string
 */
function filterLibraryContent(query) {
    const searchQuery = query.toLowerCase().trim();
    const contentList = document.getElementById('library-content-list');
    const treeView = document.getElementById('library-tree');

    if (!contentList) return;

    // Determine if tree view is active
    const isTreeView = treeView && treeView.style.display !== 'none';

    if (isTreeView) {
        // Filter tree view items
        const planCards = document.querySelectorAll('.study-plan-tree');
        const standaloneCards = contentList.querySelectorAll('.col-md-4, .col-lg-3, .col-6');
        let visibleCount = 0;

        // Filter study plan contents
        planCards.forEach(planCard => {
            const planTitle = planCard.querySelector('strong')?.textContent.toLowerCase() || '';
            const contentItems = planCard.querySelectorAll('.list-group-item');
            let planHasMatch = searchQuery === '' || planTitle.includes(searchQuery);
            let visibleItems = 0;

            contentItems.forEach(item => {
                const title = item.textContent.toLowerCase();
                const matches = searchQuery === '' || title.includes(searchQuery);
                item.style.display = matches ? '' : 'none';
                if (matches) {
                    visibleItems++;
                    planHasMatch = true;
                }
            });

            // Show plan if it matches or has matching items
            planCard.style.display = planHasMatch ? '' : 'none';
            if (planHasMatch) visibleCount++;
        });

        // Filter standalone content
        standaloneCards.forEach(card => {
            const title = card.querySelector('.card-title, h5, h6')?.textContent.toLowerCase() || '';
            const body = card.querySelector('.card-text, p')?.textContent.toLowerCase() || '';
            const type = card.querySelector('.badge')?.textContent.toLowerCase() || '';

            const matches = searchQuery === '' ||
                title.includes(searchQuery) ||
                body.includes(searchQuery) ||
                type.includes(searchQuery);

            card.style.display = matches ? '' : 'none';
            if (matches) visibleCount++;
        });

        // Show/hide empty state
        const emptyState = document.getElementById('library-empty');
        if (emptyState) {
            emptyState.style.display = visibleCount === 0 && searchQuery !== '' ? 'block' : 'none';
        }
    } else {
        // Filter flat view items (original logic)
        const cards = contentList.querySelectorAll('.col-md-4, .col-lg-3, .col-6');
        let visibleCount = 0;

        cards.forEach(card => {
            const title = card.querySelector('.card-title, h5, h6')?.textContent.toLowerCase() || '';
            const body = card.querySelector('.card-text, p')?.textContent.toLowerCase() || '';
            const type = card.querySelector('.badge')?.textContent.toLowerCase() || '';

            const matches = searchQuery === '' ||
                title.includes(searchQuery) ||
                body.includes(searchQuery) ||
                type.includes(searchQuery);

            card.style.display = matches ? '' : 'none';
            if (matches) visibleCount++;
        });

        // Show/hide empty state
        const emptyState = document.getElementById('library-empty');
        if (emptyState) {
            emptyState.style.display = visibleCount === 0 && searchQuery !== '' ? 'block' : 'none';
        }
    }
}

// Initialize content search handler
const contentSearch = document.getElementById('content-search');
if (contentSearch) {
    contentSearch.addEventListener('input', debounce((e) => {
        filterLibraryContent(e.target.value);
    }, 300));

    // Clear search when switching views
    contentSearch.addEventListener('focus', () => {
        if (contentSearch.value === '') {
            filterLibraryContent('');
        }
    });
}

// ===============================
// Continue Learning Functions
// ===============================

// Store the active plan for continue learning
let activeContinuePlan = null;
let activePlanContents = [];
let activeNextContentId = null;

/**
 * Load active study plans and display Continue Learning card if applicable
 */
window.loadContinueLearning = async function loadContinueLearning() {
    if (isTeacherOrAdmin) return;

    const card = document.getElementById('continue-learning-card');
    if (!card) return;

    try {
        const token = AuthService.getToken();
        // Get user's study plans
        const resp = await fetch('/api/study-plans', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!resp.ok) {
            card.style.display = 'none';
            return;
        }

        const plans = await resp.json();
        if (!plans || plans.length === 0) {
            card.style.display = 'none';
            return;
        }

        // Get the first plan with content (could enhance to track last active)
        for (const plan of plans) {
            const treeResp = await fetch(`/api/study-plans/${plan.id}/tree`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (treeResp.ok) {
                const tree = await treeResp.json();
                if (tree.contents && tree.contents.length > 0) {
                    activeContinuePlan = tree;
                    activePlanContents = tree.contents;

                    // Fetch actual progress from backend
                    let completedIds = [];
                    let currentIndex = 0;
                    try {
                        const progressResp = await fetch(`/api/study-plans/${plan.id}/my-progress`, {
                            headers: { 'Authorization': `Bearer ${token}` }
                        });
                        if (progressResp.ok) {
                            const progress = await progressResp.json();
                            completedIds = progress.completed_content_ids || [];
                            // Current index is first uncompleted item
                            currentIndex = completedIds.length;
                            if (currentIndex >= tree.contents.length) {
                                currentIndex = tree.contents.length - 1; // All complete
                            }
                        }
                    } catch (e) {
                        console.warn('Could not load progress:', e);
                    }

                    // Set next content based on progress
                    activeNextContentId = tree.contents[currentIndex]?.id || tree.contents[0].id;

                    // Update UI with real progress
                    document.getElementById('continue-plan-title').textContent = tree.title;
                    document.getElementById('continue-next-title').textContent =
                        tree.contents[currentIndex]?.title || tree.contents[0].title;
                    document.getElementById('continue-progress-text').textContent =
                        `${completedIds.length} of ${tree.contents.length} completed`;

                    // Render timeline with real progress
                    renderProgressTimeline(tree.contents, currentIndex, completedIds);

                    card.style.display = 'block';
                    return;
                }
            }
        }

        // No plans with content found
        card.style.display = 'none';

    } catch (e) {
        console.error('Failed to load continue learning:', e);
        card.style.display = 'none';
    }
};

/**
 * Render the progress timeline with nodes
 * @param {Array} contents - Array of content items
 * @param {number} currentIndex - Index of current item
 * @param {Array} completedIds - Array of completed content IDs
 */
function renderProgressTimeline(contents, currentIndex, completedIds = []) {
    const timeline = document.getElementById('progress-timeline');
    if (!timeline) return;

    timeline.className = 'progress-timeline';
    timeline.innerHTML = '';

    contents.forEach((item, index) => {
        // Determine node state based on actual completion
        let state = 'upcoming';
        if (completedIds.includes(item.id)) {
            state = 'completed';
        } else if (index === currentIndex) {
            state = 'current';
        }

        // Add connector before node (except first)
        if (index > 0) {
            const connector = document.createElement('div');
            const prevCompleted = completedIds.includes(contents[index - 1]?.id);
            connector.className = `timeline-connector ${prevCompleted ? 'completed' : ''}`;
            timeline.appendChild(connector);
        }

        // Create node
        const node = document.createElement('div');
        node.className = `timeline-node ${state}`;
        node.onclick = () => goToTimelineContent(item.id);

        // Icon based on content type and state
        let icon = '📖';
        if (item.content_type === 'exercise') icon = '🏋️';
        if (item.content_type === 'assessment') icon = '📝';
        if (state === 'completed') icon = '✓';

        node.innerHTML = `
            <div class="timeline-node-circle">${icon}</div>
            <div class="timeline-node-label" title="${item.title}">${truncateText(item.title, 10)}</div>
        `;

        timeline.appendChild(node);
    });
}

/**
 * Navigate to content from timeline
 */
function goToTimelineContent(contentId) {
    if (activeContinuePlan) {
        window.location.href = `session_player.html?content_id=${contentId}&plan_id=${activeContinuePlan.id}`;
    }
}

/**
 * Truncate text with ellipsis
 */
function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

/**
 * Continue to next item in study plan
 */
window.continueStudyPlan = function continueStudyPlan() {
    if (activeContinuePlan && activeNextContentId) {
        window.location.href = `session_player.html?content_id=${activeNextContentId}&plan_id=${activeContinuePlan.id}`;
    }
};

/**
 * View study plan in tree view
 */
window.viewStudyPlanTree = function viewStudyPlanTree() {
    // Switch to library view and toggle to tree
    document.querySelector('[data-view="library"]')?.click();
    setTimeout(() => {
        toggleLibraryView('tree');
    }, 100);
};

// Grading functions removed (moved to grading.js / used via grading.html)

// ===============================
// Leaderboard Functions
// ===============================

/**
 * Load leaderboard data based on selected period filter
 */
/**
 * Load leaderboard data based on selected period filter
 */
window.loadLeaderboard = async function loadLeaderboard() {
    // Determine which element we are using (list or table body) - prefer table
    let container = document.getElementById('leaderboard-body');
    const periodSelect = document.getElementById('leaderboard-period');

    // Fallback if table not found (should be present based on HTML)
    if (!container) {
        console.error("Leaderboard container not found");
        return;
    }

    const period = periodSelect?.value || 'weekly';

    // Show loading state (colspan 4 because table has 4 columns)
    container.innerHTML = '<tr><td colspan="4" class="text-center text-muted" data-i18n="common.labels.loading">Loading...</td></tr>';

    try {
        const token = AuthService.getToken();
        const res = await fetch(`/api/gamification/leaderboard?period=${period}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!res.ok) throw new Error('Failed to load leaderboard');

        const data = await res.json();
        renderLeaderboard(data);
    } catch (e) {
        console.error('Failed to load leaderboard:', e);
        container.innerHTML = '<tr><td colspan="4" class="text-muted text-center">Unable to load leaderboard</td></tr>';
    }
};

/**
 * Render leaderboard list
 */
function renderLeaderboard(entries) {
    const container = document.getElementById('leaderboard-body');
    if (!entries || entries.length === 0) {
        container.innerHTML = '<tr><td colspan="4" class="text-muted text-center">No leaderboard data available</td></tr>';
        return;
    }

    container.innerHTML = entries.map((entry, index) => {
        const rank = index + 1;
        // Medals for top 3
        let rankingDisplay;
        if (rank === 1) rankingDisplay = '🥇 1';
        else if (rank === 2) rankingDisplay = '🥈 2';
        else if (rank === 3) rankingDisplay = '🥉 3';
        else rankingDisplay = `#${rank}`;

        const isCurrentUser = entry.user_id === currentUserId;

        return `
            <tr class="${isCurrentUser ? 'table-primary' : ''}">
                <td>
                    <span class="fw-bold">${rankingDisplay}</span>
                </td>
                <td>
                    <div class="d-flex align-items-center gap-2">
                        <span>${entry.display_name || entry.username || 'User'}</span>
                        ${isCurrentUser ? '<span class="badge bg-primary">You</span>' : ''}
                    </div>
                </td>
                <td>
                    <span class="fw-bold">${entry.xp || 0} XP</span>
                </td>
                <td>
                     <span class="badge bg-secondary">Level ${entry.level || 1}</span>
                </td>
            </tr>
        `;
    }).join('');
}


// ===============================
// Inbox Bulk Actions Logic
// Moved to modules/inbox.js


/**
 * Save teacher notes for a student
 */
window.saveStudentNotes = async function () {
    const notesEl = document.getElementById('student-teacher-notes');
    const statusEl = document.getElementById('notes-save-status');
    if (!notesEl || !window.currentStudentId) return;

    const notes = notesEl.value;
    const token = AuthService.getToken();

    try {
        if (statusEl) statusEl.textContent = 'Saving...';
        const res = await fetch(`/api/students/${window.currentStudentId}/notes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ notes })
        });

        if (res.ok) {
            if (statusEl) statusEl.textContent = '✓ Notes saved';
            setTimeout(() => {
                if (statusEl) statusEl.textContent = 'Notes auto-saved';
            }, 2000);
        } else {
            if (statusEl) statusEl.textContent = '✗ Failed to save';
        }
    } catch (e) {
        console.error('Failed to save notes:', e);
        if (statusEl) statusEl.textContent = '✗ Error saving';
    }
};

// ===============================
// Initial Load (at end of file to ensure all functions are defined)
// ===============================
function initializeDashboard() {
    // Only initialize if I18n is ready
    if (typeof I18n === 'undefined' || !I18n.isReady) {
        console.log('[Dashboard] Waiting for I18n to be ready...');
        setTimeout(initializeDashboard, 100);
        return;
    }
    
    console.log('[Dashboard] Initializing dashboard...');
    loadStats();
    loadActivity();
    loadGamificationProfile();
    loadContinueLearning();
    
    // Note: updateUnreadBadge is handled by inbox.js when it loads
    console.log('[Dashboard] Dashboard initialized');
}

// Wait for DOM to be ready before initializing
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeDashboard);
} else {
    initializeDashboard();
}

// Wire up Library Search
const librarySearchInput = document.getElementById('content-search');
if (librarySearchInput) {
    librarySearchInput.addEventListener('input', (e) => {
        window.filterLibrary(e.target.value);
    });
}

// --- USER PROFILE ---

