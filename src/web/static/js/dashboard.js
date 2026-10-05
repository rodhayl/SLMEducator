import { AuthService } from './auth.js';

function setUserNameDisplay(name) {
    const primary = document.getElementById('user-name-display');
    const legacy = document.getElementById('user-name');
    if (primary) primary.textContent = name;
    if (legacy && legacy !== primary) legacy.textContent = name;
}

let dashboardStartupFailed = false;

function failDashboardStartup() {
    dashboardStartupFailed = true;
    const app = document.getElementById('dashboard-app');
    if (app) app.setAttribute('aria-busy', 'false');
    const loading = document.getElementById('dashboard-loading');
    if (!loading) return;
    loading.hidden = false;
    loading.setAttribute('role', 'alert');
    loading.classList.replace('alert-info', 'alert-danger');
    const message = loading.querySelector('[data-i18n]');
    if (message) {
        const key = 'recovery.dashboard_startup_failed';
        const translated = typeof I18n !== 'undefined' ? I18n.t(key) : key;
        message.dataset.i18n = key;
        message.textContent = translated && translated !== key ? translated :
            'The dashboard could not start. Check your connection and retry. Your saved work is unchanged.';
    }
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
    document.querySelectorAll('[data-role="student"]').forEach(item => item.classList.toggle('hidden', role !== 'student'));
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
        window.location.href = AuthService.loginUrl();
        throw new Error('Authentication is required');
    }

    // Canonical source of truth: API profile (fixes stale/missing localStorage user).
    const profile = await AuthService.refreshUser();
    if (!profile) throw new Error('Profile could not be verified');

    const { user } = refreshRoleState();
    const displayName = user ? `${user.first_name} ${user.last_name}`.trim() : I18n.t('common.roles.user');
    setUserNameDisplay(displayName || I18n.t('common.roles.user'));

    applyRoleUI();
}

// Keep a failed or stalled initialization closed until an explicit retry.
async function initializeDashboardStartup() {
    const watchdog = setTimeout(failDashboardStartup, 20000);
    try {
        await initAuthAndRoleUI();
        if (!dashboardStartupFailed) await SLMTime.load().catch(() => {});
    } catch {
        failDashboardStartup();
    } finally {
        clearTimeout(watchdog);
    }
}
await initializeDashboardStartup();

// Update on language load (and re-apply role UI)
document.addEventListener('i18n-loaded', () => {
    if (dashboardStartupFailed) return;
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

window.reloadAIConfiguration = () => loadSettings();
const supportedAIProviders = ['ollama', 'lm_studio', 'openai', 'openrouter'];
let savingAISettings = false;
let aiConfigLoadState = 'loading';
async function loadSettings() {
    aiConfigLoadState = 'loading'; onProviderChange();
    const token = AuthService.getToken();
    try {
        // Load AI Config
        const aiRes = await fetch('/api/settings/ai', { headers: { 'Authorization': `Bearer ${token}` } });
        if (aiRes.ok) {
            const aiData = await aiRes.json();
            // Populate Form
            if (!supportedAIProviders.includes(aiData.provider)) throw new Error(SLMClient.message('ai_config_repair', 'Choose a supported provider and save a replacement configuration. Your existing configuration has not changed.'));
            aiConfigLoadState = 'ready';
            document.getElementById('ai-config-status').textContent = '';
            document.getElementById('ai-provider').value = aiData.provider;
            document.getElementById('ai-model').value = aiData.model || '';
            document.getElementById('ai-endpoint').value = aiData.endpoint || '';
            // Key is likely masked or null if hidden
            document.getElementById('ai-key').value = '';
            document.getElementById('ai-key').dataset.hasKey = String(Boolean(aiData.has_api_key));

            // Advanced settings
            if (aiData.temperature !== undefined) {
                document.getElementById('ai-temperature').value = aiData.temperature;
                document.getElementById('temp-value').textContent = aiData.temperature;
            }
            if (aiData.max_tokens !== undefined) {
                document.getElementById('ai-max-tokens').value = aiData.max_tokens;
            }
            const reasoningSelect = document.getElementById('ai-reasoning-effort');
            if (reasoningSelect) reasoningSelect.value = aiData.reasoning_effort || '';
            // Update UI hints based on provider
            onProviderChange();
        } else {
            aiConfigLoadState = aiRes.status === 409 ? 'repair' : 'failed';
            document.getElementById('ai-provider').value = '';
            document.getElementById('ai-model').value = '';
            document.getElementById('ai-endpoint').value = '';
            document.getElementById('ai-key').value = '';
            document.getElementById('ai-key').dataset.hasKey = 'false';
            document.getElementById('ai-config-status').textContent = SLMClient.message(aiRes.status === 409 ? 'ai_config_repair' : 'ai_config_load_failed', aiRes.status === 409 ? 'Choose a supported provider and save a replacement configuration. Your existing configuration has not changed.' : 'AI configuration could not be loaded. Retry before changing it.');
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

    } catch (err) { aiConfigLoadState = 'failed'; onProviderChange(); document.getElementById('ai-config-status').textContent = SLMClient.message('ai_config_load_failed', 'AI configuration could not be loaded. Retry before changing it.'); }
}

function setSettingsTab(tabName) {
    const tabs = document.querySelectorAll('#settings-tabs .tab');
    const sections = document.querySelectorAll('.settings-tab-section');
    const targetId = `settings-tab-${tabName}`;

    tabs.forEach(tab => {
        tab.classList.toggle('active', tab.dataset.settingsTab === tabName);
        tab.setAttribute('aria-pressed', String(tab.dataset.settingsTab === tabName));
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
        // ThemeService already applied the saved setting. Binding a default
        // HTML selector must not briefly replace it while requests are pending.
        try {
            const saved = localStorage.getItem('slm_theme_preference');
            if (['auto', 'light', 'dark'].includes(saved)) themeSelect.value = saved;
        } catch { /* The current applied theme remains usable without storage. */ }
        themeSelect.addEventListener('change', () => applyTheme(themeSelect.value));
        settingsThemeBound = true;
    }

    initSettingsTabs();
    if (typeof window.loadProfileSettings === 'function') window.loadProfileSettings();
}

document.addEventListener('DOMContentLoaded', () => {
    if (dashboardStartupFailed) return;
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
        reasoning_effort: document.getElementById('ai-provider').value === 'lm_studio'
            ? (document.getElementById('ai-reasoning-effort')?.value || null) : null
    };
}

window.saveAISettings = async () => {
    if (savingAISettings || !['ready', 'repair'].includes(aiConfigLoadState)) return;
    const resultDiv = document.getElementById('ai-test-result');
    const data = buildAIConfigPayload();
    if (!supportedAIProviders.includes(data.provider)) {
        document.getElementById('ai-config-status').textContent = SLMClient.message('ai_config_repair', 'Choose a supported provider and save a replacement configuration. Your existing configuration has not changed.'); return;
    }
    const apiKeyValue = document.getElementById('ai-key').value;
    if (apiKeyValue) data.api_key = apiKeyValue;
    savingAISettings = true;
    const controls = [...document.querySelectorAll('#settings-ai-form input, #settings-ai-form select, #settings-ai-form button')];
    controls.forEach(control => { control.disabled = true; });
    resultDiv.className = 'mt-3 alert alert-info'; resultDiv.textContent = I18n.t('settings.save.saving');
    try {
        const saved = await SLMClient.request('/api/settings/ai', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
        if (saved?.provider !== data.provider || typeof saved.model !== 'string') throw new Error(SLMClient.message('ai_save_unconfirmed', 'The server did not confirm this configuration. Your entries are kept; retry.'));
        aiConfigLoadState = 'ready';
        document.getElementById('ai-key').value = '';
        document.getElementById('ai-key').dataset.hasKey = String(Boolean(saved.has_api_key));
        document.getElementById('ai-config-status').textContent = '';
        resultDiv.className = 'mt-3 alert alert-success'; resultDiv.textContent = I18n.t('settings.save.success');
    } catch (error) {
        resultDiv.className = 'mt-3 alert alert-danger'; resultDiv.textContent = error.message;
    } finally { savingAISettings = false; controls.forEach(control => { control.disabled = false; }); onProviderChange(); }
};
// --- AI SETTINGS HELPER FUNCTIONS ---

/**
 * Fetch available models from the current provider
 */
window.fetchModels = async function () {
    if (!['ready', 'repair'].includes(aiConfigLoadState) || !supportedAIProviders.includes(document.getElementById('ai-provider').value)) return;
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
                    data.models.map(m => `<option value="${escapeHtml(m)}">${escapeHtml(m)}</option>`).join('');
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
    const cloudProviders = ['openai', 'openrouter'];
    const valid = supportedAIProviders.includes(provider);
    const reasoningSelect = document.getElementById('ai-reasoning-effort');
    if (reasoningSelect) reasoningSelect.disabled = provider !== 'lm_studio' || savingAISettings;
    ['fetch-models-btn', 'save-ai-config', 'test-ai-config'].forEach(id => { const control = document.getElementById(id); if (control) control.disabled = !valid || savingAISettings || !['ready', 'repair'].includes(aiConfigLoadState); });

    if (cloudProviders.includes(provider)) {
        apiKeyGroup.classList.remove('d-none');
        document.getElementById('ai-key').placeholder = document.getElementById('ai-key').dataset.hasKey === 'true' ? I18n.t('settings.ai.api_key_set_placeholder') : I18n.t('settings.ai.api_key_required_for', { provider: provider });
    } else {
        // API key optional for local providers 
        document.getElementById('ai-key').placeholder = I18n.t('settings.ai.api_key_optional');
    }

    // Update endpoint placeholder
    const defaultEndpoints = {
        'ollama': 'http://localhost:11434',
        'lm_studio': 'http://localhost:1234',
        'openai': 'https://api.openai.com/v1',
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
    if (!['ready', 'repair'].includes(aiConfigLoadState) || !supportedAIProviders.includes(document.getElementById('ai-provider').value)) return;
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

        if (!res.ok) throw new Error(result.detail || I18n.t('settings.ai.error_connection_failed'));
        if (result.status === 'connected') {
            resultDiv.className = 'mt-3 alert alert-success';
            resultDiv.innerHTML = `
                <strong>${I18n.t('settings.ai.success_connected')}</strong><br>
                Provider: ${escapeHtml(result.provider)}<br>
                Model: ${escapeHtml(result.model)}<br>
                Response time: ${result.response_time_ms}ms
            `;
        } else {
            resultDiv.className = 'mt-3 alert alert-danger';
            resultDiv.innerHTML = `
                <strong>${I18n.t('settings.ai.error_connection_failed')}</strong><br>
                ${I18n.t('common.labels.error')}: ${escapeHtml(result.error)}
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
            <div class="toast-body">${escapeHtml(message)}</div>
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
    if (newPassword.length < 12) {
        if (feedbackEl) {
            feedbackEl.className = 'mt-3 alert alert-danger';
            feedbackEl.textContent = SLMClient.message('password_minimum', 'Password must be at least 12 characters');
        }
        return;
    }

    try {
        const token = AuthService.getToken();
        const response = await fetch('/api/auth/change-password', {
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
                feedbackEl.textContent = data.detail || 'Error changing password';
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
            profile.created_at ? SLMTime.format(profile.created_at, { dateOnly: true }) : 'N/A';
        document.getElementById('profile-last-login').textContent =
            profile.last_login ? SLMTime.format(profile.last_login) : 'N/A';

        // Populate form fields
        document.getElementById('profile-first-name').value = profile.first_name || '';
        document.getElementById('profile-last-name').value = profile.last_name || '';
        document.getElementById('profile-email').value = profile.email || '';
        document.getElementById('profile-grade-level').value = profile.grade_level || '';
        document.getElementById('profile-username-readonly').value = profile.username || '';

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
                    <small data-i18n="profile.badges.empty">${escapeHtml(I18n.t('profile.badges.empty'))}</small><br>
                    <small data-i18n="profile.badges.empty_hint">${escapeHtml(I18n.t('profile.badges.empty_hint'))}</small>
                </div>
            `;
            return;
        }

        // Render badges as a grid
        badgesList.innerHTML = badges.map(badge => `
            <div class="d-flex align-items-center mb-2 p-2 bg-elevated rounded">
                <div class="badge-icon me-2" style="font-size: 1.5rem;">
                    ${escapeHtml(badge.icon_path || '🎖️')}
                </div>
                <div class="flex-grow-1">
                    <div class="fw-bold small">${escapeHtml(badge.name)}</div>
                    <div class="text-muted" style="font-size: 0.75rem;">
                        ${badge.earned_at ? escapeHtml(SLMTime.format(badge.earned_at, { dateOnly: true })) : ''}
                    </div>
                </div>
            </div>
        `).join('');

    } catch (err) {
        console.error('Failed to load badges:', err);
        badgesList.innerHTML = `
            <div class="text-muted text-center">
                <small data-i18n="profile.badges.error_load">${escapeHtml(I18n.t('profile.badges.error_load'))}</small>
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
            const evidenceResponse = await fetch('/api/mastery/evidence', { headers: { Authorization: `Bearer ${token}` } });
            const evidence = evidenceResponse.ok ? await evidenceResponse.json() : { items: [] };
            const finalItems = (evidence.items || []).filter(item => item.evidence_type === 'final_assessment' && Number.isFinite(item.assessment_percent));
            document.getElementById('mastery-avg').textContent = finalItems.length ? `${Math.round(finalItems.reduce((sum,item) => sum + item.assessment_percent,0) / finalItems.length)}%` : '—';
            document.getElementById('mastery-mastered').textContent = finalItems.length;
            document.getElementById('mastery-progress').textContent = (evidence.items || []).filter(item => item.evidence_type !== 'final_assessment').length;
        }

    } catch (err) {
        console.error("Failed to load stats", err);
    }
}

// Inbox Logic
// Moved to modules/inbox.js



// Help requests keep one identity across transport retries.
let dashboardHelpBusy = false;
let dashboardHelpPending = null;
window.submitHelpRequest = async function submitHelpRequest() {
    if (dashboardHelpBusy) return;
    const owner = SLMClient.account();
    const learning = window.getLearningContext();
    const payload = {subject:document.getElementById('help-subject').value.trim(), description:document.getElementById('help-desc').value.trim(),
        urgency:Number(document.getElementById('help-urgency').value), content_id:Number(learning.contentId) || null,
        study_plan_id:Number(learning.studyPlanId) || null, question_id:Number(learning.questionId) || null};
    if (!payload.subject || !payload.description) return;
    const fingerprint = JSON.stringify(payload);
    if (!dashboardHelpPending || dashboardHelpPending.owner !== owner || dashboardHelpPending.fingerprint !== fingerprint) dashboardHelpPending = {owner,fingerprint,id:crypto.randomUUID()};
    payload.client_request_id = dashboardHelpPending.id;
    dashboardHelpBusy = true;
    const controls = [...document.querySelectorAll('#help-form input, #help-form textarea, #help-form select, #helpModal button[onclick="submitHelpRequest()"]')];
    controls.forEach(control => {control.disabled=true;});
    try {
        const result = await SLMClient.request('/api/classroom/help', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
        if (owner !== SLMClient.account()) return;
        if (!Number.isInteger(result?.id) || result.client_request_id !== payload.client_request_id || String(result.student_id) !== owner || !['open','resolved'].includes(result.status) || (result.content_id ?? null) !== payload.content_id || (result.study_plan_id ?? null) !== payload.study_plan_id || result.request_text !== `${payload.subject}: ${payload.description}`) throw new Error(SLMClient.message('help_delivery_unconfirmed', 'Help delivery is unconfirmed. Your text is kept; retrying the same text checks the same request.'));
        showToast(I18n.t('help_request.success_submit'), 'success');
        bootstrap.Modal.getInstance(document.getElementById('helpModal'))?.hide();
        document.getElementById('help-form').reset(); dashboardHelpPending=null;
        document.getElementById('help-context-display')?.replaceChildren();
    } catch (error) { if (owner === SLMClient.account()) showToast(error.message, 'danger'); }
    finally { dashboardHelpBusy=false;controls.forEach(control=>{control.disabled=false;}); }
};

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
                    contextParts.push(`<span class="badge bg-primary me-2">${icon} ${escapeHtml(context.contentTitle)}</span>`);
                }

                if (context.studyPlanTitle) {
                    contextParts.push(`<span class="badge bg-secondary me-2">📋 ${escapeHtml(context.studyPlanTitle)}</span>`);
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
                <div>${escapeHtml(a.id === 0 ? I18n.t('dashboard.recent_activity.no_activity') : a.text)}</div>
                <div class="activity-time">${escapeHtml(a.id === 0 ? I18n.t('dashboard.recent_activity.start_learning') : a.time)}</div>
            </div>
        `).join('');
    } catch (err) {
        console.error("Failed to load activity", err);
    }
}

// Navigation Handler
let restoringDashboardView = false;
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
        if (viewEl) { viewEl.classList.remove('hidden'); viewEl.tabIndex = -1; viewEl.focus({ preventScroll: true }); }
        if (!restoringDashboardView && window.location.hash !== `#${viewName}`) history.pushState(null, '', `#${viewName}`);

        document.body.classList.remove('sidebar-open');

        // Trigger data load
        if (viewName === 'overview') { loadStats(); loadActivity(); loadGamificationProfile(); }
        if (viewName === 'library') loadLibrary();
        if (viewName === 'settings') {
            initSettingsUI();
            loadSettings();
            loadProfile();
            loadTimezoneSettings();
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

function initializeResponsiveNavigation() {
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
}
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeResponsiveNavigation, {once: true});
} else {
    initializeResponsiveNavigation();
}

function restoreDashboardView() {
    if (dashboardStartupFailed) return;
    const params = new URLSearchParams(window.location.search);
    const requested = window.location.hash.slice(1) || params.get('view') || params.get('tab');
    const alias = requested === 'study-plans' ? 'library' : requested;
    const navigation = Array.from(document.querySelectorAll('.nav-item[data-view]')).find(item => item.dataset.view === alias);
    if (!navigation) return;
    restoringDashboardView = true;
    try { navigation.click(); } finally { restoringDashboardView = false; }
}
window.addEventListener('popstate', restoreDashboardView);
window.addEventListener('hashchange', restoreDashboardView);
document.addEventListener('DOMContentLoaded', restoreDashboardView);

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
            fetch('/api/mastery/evidence', { headers: { 'Authorization': `Bearer ${token}` } }).catch(() => null)
        ]);

        let items = await contentResponse.json();
        if (!contentResponse.ok) throw new Error('Content could not be loaded');
        let evidenceByContent = {};
        if (masteryResponse && masteryResponse.ok) {
            const evidence = await masteryResponse.json();
            evidenceByContent = Object.fromEntries((evidence.items || []).map(item => [item.content_id, item]));
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

            const evidence = evidenceByContent[item.id];
            const finalEvidence = evidence?.evidence_type === 'final_assessment' && Number.isFinite(evidence.assessment_percent);
            const evidenceLabel = finalEvidence ? `${SLMClient.message('final_assessment_score', 'Final assessment score')}: ${evidence.assessment_percent}%` :
                SLMClient.message('legacy_evidence', 'Legacy activity, not assessed mastery');
            const confidenceLabel = evidence?.self_confidence ? `${SLMClient.message('self_confidence', 'Self-rated confidence')}: ${evidence.self_confidence}/5` : '';

            return `
                <div class="col-md-4 col-lg-3">
                    <div class="card h-100" data-creator-id="${item.creator_id || ''}" data-can-edit="${item.can_edit === true}">
                        <div class="card-body">
                            <span class="badge ${typeColors[type] || 'bg-secondary'} mb-2">
                                ${typeIcons[type] || '📄'} ${escapeHtml(type.toUpperCase())}
                            </span>
                            <h5 class="card-title">${escapeHtml(item.title)}</h5>
                            ${(item.creator_id && currentUserId && item.creator_id !== currentUserId && (item.creator_name || item.creator_username)) ? `
                            <p class="text-muted small mb-2">
                                ${escapeHtml(I18n.t('content.library.from', { name: item.creator_name || 'Student' }))}${item.creator_username ? ` (@${escapeHtml(item.creator_username)})` : ''}
                            </p>` : ''}
                            <p class="text-muted small mb-2">
                                ${I18n.t('content.editor.errors.difficulty')} ${'⭐'.repeat(item.difficulty || 1)}
                            </p>
                            ${!isTeacherOrAdmin ? `
                            <div class="mb-2">
                                <small class="text-muted d-block">${escapeHtml(evidenceLabel)}</small>
                                <small class="text-muted d-block">${escapeHtml(confidenceLabel)}</small>
                            </div>` : ''}
                            <p class="text-muted small">
                                ${I18n.t('content.editor.errors.created_at')} ${escapeHtml(SLMTime.format(item.created_at, { dateOnly: true }))}
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
    container.querySelectorAll('[data-can-edit]').forEach(card => {
        const canEdit = card.dataset.canEdit === 'true';
        card.querySelectorAll('button[onclick^="editContent("], button[onclick^="deleteContent("]').forEach(button => button.classList.toggle('hidden', !canEdit));
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
                SLMRender.setMarkdown(answerContent, data.answer);
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
        document.getElementById('content-view-date').textContent = `Created: ${SLMTime.format(content.created_at, { dateOnly: true })}`;

        // Parse content body
        let bodyText = I18n.t('content.viewer.empty_content');
        if (content.content_data) {
            try {
                if (typeof content.content_data === 'string') {
                    const parsed = JSON.parse(content.content_data);
                    bodyText = type === 'lesson' ? SLMRender.lessonText(parsed) : parsed.content || parsed.body || parsed.text || JSON.stringify(parsed, null, 2);
                } else {
                    const parsed = content.content_data;
                    bodyText = type === 'lesson' ? SLMRender.lessonText(parsed) : parsed.content || parsed.body || JSON.stringify(parsed, null, 2);
                }
            } catch {
                bodyText = content.content_data;
            }
        }

        SLMRender.setMarkdown(document.getElementById('content-view-body'), bodyText);
        let receiptData = content.content_data;
        if (typeof receiptData === 'string') { try { receiptData = JSON.parse(receiptData); } catch { receiptData = null; } }
        SLMRender.generationNotice(document.getElementById('content-view-body'), {...receiptData, source_selection: content.source_selection});

        // Show modal
        new bootstrap.Modal(document.getElementById('contentViewModal')).show();
    } catch (err) {
        showToast(I18n.t('content.viewer.error_load_details', { error: err.message }), 'danger');
    }
};

// Edit content
let editingContentState = null;
let savingContentEdit = false;
let contentEditSequence = 0;
const editField = id => document.getElementById(id);
const editLines = id => editField(id).value.split('\n').map(line => line.trim()).filter(Boolean);
function editChoices(selected = '') {
    const select = editField('edit-exercise-correct-choice');
    select.replaceChildren(new Option(SLMClient.message('select_answer', 'Choose an answer'), ''));
    editLines('edit-exercise-options').forEach((value, index) => select.append(new Option(value, String(index))));
    select.value = selected;
}
window.editContent = async function editContent(id) {
    if (savingContentEdit) return;
    const sequence = ++contentEditSequence;
    const owner = SLMClient.account();
    editingContentState = null;
    bootstrap.Modal.getInstance(editField('contentViewModal'))?.hide();
    try {
        const res = await fetch(`/api/content/${id}`, {headers: {Authorization: `Bearer ${AuthService.getToken()}`}});
        if (!res.ok) throw new Error(I18n.t('content.viewer.error_load'));
        const content = await res.json();
        if (sequence !== contentEditSequence || owner !== SLMClient.account()) return;
        if (content.can_edit !== true) { showToast(SLMClient.message('content_read_only', 'This content cannot be edited. Open its course to create a draft copy.'), 'warning'); return; }
        const type = content.content_type?.value || content.content_type;
        let data = content.content_data;
        if (typeof data === 'string') { try { data = JSON.parse(data); } catch { data = {body: data}; } }
        if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error(I18n.t('content.viewer.error_load'));
        if (type === 'assessment') {
            if (!Number.isInteger(data.assessment_id) || data.assessment_id < 1) throw new Error(SLMClient.message('practice_unavailable', 'This item needs teacher review.'));
            window.location.href = `/assessment_builder.html?id=${data.assessment_id}`;
            return;
        }
        editingContentState = {id: content.id, type, data, owner};
        editField('edit-content-id').value = content.id;
        editField('edit-content-title').value = content.title;
        editField('edit-content-type').value = type;
        editField('edit-content-difficulty').value = content.difficulty || 1;
        editField('edit-lesson-fields').classList.toggle('d-none', type === 'exercise');
        editField('edit-exercise-fields').classList.toggle('d-none', type !== 'exercise');
        if (type === 'exercise') {
            const choices = SLMPractice.optionsFor(data);
            const multiple = (data.type || data.question_type) === 'multiple_choice';
            editField('edit-exercise-question').value = data.question || data.question_text || '';
            editField('edit-exercise-options-fields').classList.toggle('d-none', !multiple);
            editField('edit-exercise-answer-fields').classList.toggle('d-none', multiple);
            editField('edit-exercise-options').value = choices.map(choice => choice.value).join('\n');
            const answer = String(data.correct_answer ?? data.answer ?? '');
            const selected = choices.findIndex(choice => choice.key.toLowerCase() === answer.toLowerCase() || choice.value.toLowerCase() === answer.toLowerCase());
            editChoices(selected < 0 ? '' : String(selected));
            editField('edit-exercise-options').oninput = () => editChoices(editField('edit-exercise-correct-choice').value);
            editField('edit-exercise-answer').value = answer;
            editField('edit-exercise-explanation').value = data.explanation || '';
            editField('edit-exercise-hints').value = (Array.isArray(data.hints) ? data.hints : [data.hint]).filter(item => typeof item === 'string').join('\n');
        } else {
            editField('edit-content-body').value = type === 'lesson' ? SLMRender.lessonText(data) : data.content || data.body || data.answer || '';
        }
        new bootstrap.Modal(editField('contentEditModal')).show();
    } catch (err) {
        showToast(I18n.t('content.editor.error_load', {error: err.message}), 'danger');
    }
};

// Save corrections without discarding source receipts or practice structure.
window.saveContentEdit = async function saveContentEdit() {
    const state = editingContentState;
    if (savingContentEdit || !state || state.owner !== SLMClient.account() || String(state.id) !== editField('edit-content-id').value) return;
    const data = {...state.data};
    try {
        if (state.type === 'exercise') {
            data.question = editField('edit-exercise-question').value.trim();
            if (!data.question) throw new Error(SLMClient.message('editor_required', 'Complete the question and answer before saving.'));
            if ((data.type || data.question_type) === 'multiple_choice') {
                data.options = editLines('edit-exercise-options');
                const selected = editField('edit-exercise-correct-choice').value;
                if (data.options.length < 2 || selected === '' || !data.options[Number(selected)]) throw new Error(SLMClient.message('editor_required', 'Complete the choices and correct answer before saving.'));
                data.correct_answer = data.options[Number(selected)];
            } else {
                data.correct_answer = editField('edit-exercise-answer').value.trim();
                if (!data.correct_answer) throw new Error(SLMClient.message('editor_required', 'Complete the question and answer before saving.'));
            }
            data.hints = editLines('edit-exercise-hints');
            data.explanation = editField('edit-exercise-explanation').value;
            delete data.hint;
            delete data.answer;
            delete data.question_text;
        } else {
            const body = editField('edit-content-body').value;
            if (!body.trim()) throw new Error(SLMClient.message('editor_required', 'Complete the content before saving.'));
            if (state.type === 'lesson') {
                // All visible fields were included in the editable Markdown. Keeping
                // their old structured values would duplicate stale instructions.
                for (const key of ['sections', 'content', 'text', 'objectives', 'summary', 'vocabulary', 'key_concepts', 'discussion_questions', 'worked_example', 'independent_attempt', 'feedback', 'delayed_review', 'prerequisite_check']) delete data[key];
                data.body = body;
            } else data.content = body;
        }
        savingContentEdit = true;
        editField('save-content-edit').disabled = true;
        const res = await fetch(`/api/content/${state.id}`, {
            method: 'PUT', headers: {'Content-Type': 'application/json', Authorization: `Bearer ${AuthService.getToken()}`},
            body: JSON.stringify({title: editField('edit-content-title').value, difficulty: parseInt(editField('edit-content-difficulty').value), content_data: data})
        });
        if (state.owner !== SLMClient.account()) return;
        if (!res.ok) { const error = await res.json(); throw new Error(error.detail || I18n.t('common.errors.unknown')); }
        showToast(I18n.t('content.editor.success_update'), 'success');
        bootstrap.Modal.getInstance(editField('contentEditModal'))?.hide();
        editingContentState = null;
        await loadLibrary();
    } catch (err) {
        showToast(I18n.t('content.editor.error_save_generic', {error: err.message}), 'danger');
    } finally {
        savingContentEdit = false;
        editField('save-content-edit').disabled = false;
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
    const objectives = document.querySelector('#create-ai-content-form [name="learning_objectives"]');
    if (objectives) objectives.required = mode === 'topic';

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
                assessment_question_types: aiContentForm.assessment_question_type?.value && aiContentForm.assessment_question_type.value !== 'mixed'
                    ? [aiContentForm.assessment_question_type.value] : null,
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
        if (payload.auto_save) json._serverSaved = true;
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
            const options = SLMPractice.optionsFor(json);
            if (options.length) {
                html += '<p><strong>Options:</strong></p><ul class="mb-0">';
                options.forEach(option => { html += `<li>${escapeHtml(option.key)}: ${escapeHtml(option.value)}</li>`; });
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

        if (json.success === false) html += `<p>${escapeHtml(SLMClient.message('generation_partial', 'Some items failed. Saved items were kept; retry the same request to finish.'))}</p>`;
        if (itemsList) itemsList.innerHTML = SLMRender.html(html || '<p>Content generated!</p>');
        SLMRender.generationNotice(itemsList, json.lesson || json.exercises?.[0] || json);
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

let savingGeneratedContent = false;
window.saveAllGeneratedContent = async function () {
    if (!generatedAIContent || savingGeneratedContent) return;
    savingGeneratedContent = true;
    const generated = generatedAIContent;
    const mode = generated._mode || currentGenerationMode;
    if (generated._serverSaved) { savingGeneratedContent = false; showToast(SLMClient.message('saved_on_server', 'These results were already saved by the server. Retry generation to finish any failed items.'), 'info'); return; }
    const items = [];
    if (mode === 'study_plan') items.push({ key: 'plan', url: '/api/study-plans/', data: generated });
    else if (mode === 'exercise') items.push({ key: 'exercise', url: '/api/content', data: {
        title: generated.title || generated.question || 'Generated Exercise', content_type: 'exercise', content_data: generated
    }});
    else {
        if (generated.lesson) items.push({ key: 'lesson', url: '/api/content', data: {
            title: generated.lesson.title || 'Generated Lesson', content_type: 'lesson', content_data: generated.lesson
        }});
        (generated.exercises || []).forEach((exercise, index) => items.push({ key: `exercise-${index}`, url: '/api/content', data: {
            title: exercise.title || 'Generated Exercise', content_type: 'exercise', content_data: exercise
        }}));
        if (generated.assessment_questions?.length) items.push({ key: 'assessment', url: '/api/assessments/', data: {
            title: generated.topic_name || 'Generated Assessment', is_published: false, grading_mode: 'manual',
            questions: generated.assessment_questions.map(question => ({
                question_text: question.question_text || question.question,
                question_type: question.question_type || 'short_answer', points: question.points || 10,
                correct_answer: question.correct_answer || null,
                options: Array.isArray(question.options) ? { choices: question.options } : question.options
            }))
        }});
    }
    generated._savedKeys = generated._savedKeys || [];
    let failed = 0;
    try {
        for (const item of items) {
            if (generated._savedKeys.includes(item.key)) continue;
            try {
                await SLMClient.request(item.url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(item.data) });
                generated._savedKeys.push(item.key);
            } catch (error) { failed++; showToast(error.message, 'danger'); }
        }
        if (failed || !items.length) return; // Keep results and unsaved items available for retry.
        showToast(I18n.t('content.generator.success_save_items', { count: generated._savedKeys.length }), 'success');
        document.getElementById('ai-content-generation-result')?.classList.add('hidden');
        aiContentForm?.reset(); toggleGenerationMode(); generatedAIContent = null;
    } finally { savingGeneratedContent = false; }
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
            option.textContent = `📘 ${escapeHtml(plan.title)}`;
            select.appendChild(option);
        });
    } catch (err) {
        console.error('Failed to load tutor study plans:', err);
    }
};

// Load content items when study plan selected
let tutorContentRequest = 0;
window.resetTutorContext = function resetTutorContext() {
    cancelTutorRequest(true);
    tutorEpoch++; tutorConversation = []; tutorBusy = false;
    tutorOwner = SLMClient.account();
    const history = document.getElementById('chat-history');
    if (history) history.textContent = I18n.t('ai_tutor.start_conversation');
    const send = document.querySelector('#chat-form button[type=submit]');
    if (send) send.disabled = !tutorSourceReady || !tutorPolicy || tutorPolicy.mode === 'disabled';
    const selected = document.getElementById('tutor-content');
    window.setLearningContext({contentId: selected?.value || null, contentTitle: selected?.selectedOptions[0]?.textContent || null, studyPlanId: document.getElementById('tutor-study-plan')?.value || null, questionId: null});
    refreshTutorSource();
};
window.loadTutorContentItems = async function loadTutorContentItems() {
    const planId = document.getElementById('tutor-study-plan')?.value;
    const select = document.getElementById('tutor-content');
    if (!select) return;
    const version = ++tutorContentRequest;
    select.replaceChildren(new Option(I18n.t('ai.tutor.select_all_content'), ''));
    resetTutorContext(); select.disabled = true;
    try {
        const data = await SLMClient.request(planId ? `/api/study-plans/${planId}/tree` : '/api/content/');
        if (version !== tutorContentRequest) return;
        const contents = planId ? data.contents || [] : data;
        contents.forEach(content => select.append(new Option(content.title, content.id)));
    } catch (error) {
        if (version === tutorContentRequest) showToast(error.message, 'warning');
    } finally { if (version === tutorContentRequest) select.disabled = false; }
};
window.initTutorSelectors = async function initTutorSelectors() {
    await loadTutorStudyPlans();
    const params = new URLSearchParams(window.location.search);
    const planSelect = document.getElementById('tutor-study-plan');
    if (params.get('from_session') === '1') planSelect.value = params.get('plan_id') || '';
    await loadTutorContentItems();
    if (params.get('from_session') === '1') {
        const contentSelect = document.getElementById('tutor-content');
        contentSelect.value = params.get('content_id') || '';
        resetTutorContext();
    }
    await refreshTutorPolicy();
    await refreshTutorUsage();
};

// Clear AI Chat (30.3)
window.clearAIChat = async function clearAIChat() {
    const studyPlanSelect = document.getElementById('tutor-study-plan');
    if (studyPlanSelect) studyPlanSelect.value = '';
    const chatInput = document.getElementById('chat-input');
    if (chatInput) chatInput.value = '';
    await loadTutorContentItems();
    showToast(SLMClient.message('chat_cleared', 'Chat cleared. Choose a lesson or start a new conversation.'), 'info');
};


let tutorBusy = false;
let tutorEpoch = 0;
let tutorConversation = [];
let tutorPolicy = null;
let tutorPolicyRequest = 0;
let tutorSource = null;
let tutorSourceReady = true;
let tutorSourceRequest = 0;
let tutorOwner = SLMClient.account();
let tutorPending = null;

function applyTutorPolicy(policy) {
    if (!['hints_only', 'explanations', 'disabled'].includes(policy?.mode)) throw new Error('Invalid assistance policy');
    tutorPolicy = policy;
    const selector = document.getElementById('tutor-assistance');
    const status = document.getElementById('tutor-policy-status');
    const labels = {
        hints_only: SLMClient.message('policy_hints_only', 'Hints only'),
        explanations: SLMClient.message('policy_explanations', 'Hints and explanations'),
        disabled: SLMClient.message('policy_disabled', 'AI help disabled')
    };
    status.textContent = `${SLMClient.message('assistance_mode', 'Assistance mode')}: ${labels[policy.mode]}. ` +
        (policy.mode === 'disabled' ? SLMClient.message('policy_disabled_reason', 'Your teacher has disabled AI help while an assessment attempt is open. Complete the attempt, then refresh the policy.') :
            (policy.active_assessment_ids?.length ? SLMClient.message('policy_active_attempt', 'Teacher policy applies while an assessment attempt is open.') : SLMClient.message('policy_study_default', 'Independent study starts with hints.')));
    selector.querySelectorAll('option').forEach(option => {
        option.disabled = policy.mode !== 'explanations' && option.value !== 'hint';
    });
    if (policy.mode !== 'explanations') selector.value = 'hint';
    selector.disabled = policy.mode === 'disabled';
    chatForm.querySelector('button[type=submit]').disabled = tutorBusy || !tutorSourceReady || policy.mode === 'disabled';
}

window.refreshTutorPolicy = async function refreshTutorPolicy() {
    const version = ++tutorPolicyRequest;
    tutorPolicy = null;
    document.getElementById('tutor-assistance').disabled = true;
    chatForm.querySelector('button[type=submit]').disabled = true;
    document.getElementById('tutor-policy-status').textContent = SLMClient.message('policy_checking', 'Checking teacher assistance policy…');
    try {
        const policy = await SLMClient.request('/api/ai/assistance-policy');
        if (version === tutorPolicyRequest) applyTutorPolicy(policy);
    } catch (error) {
        if (version === tutorPolicyRequest) document.getElementById('tutor-policy-status').textContent = SLMClient.message('policy_check_failed', 'Could not check assistance policy. Refresh the policy to retry. Your message is kept.');
    }
};
window.refreshTutorSource = async function refreshTutorSource() {
    const revision = ++tutorSourceRequest;
    tutorSource = null;
    const box = document.getElementById('tutor-source-sections');
    const status = document.getElementById('tutor-source-status');
    const contentId = document.getElementById('tutor-content')?.value;
    const studyPlanId = document.getElementById('tutor-study-plan')?.value;
    box?.replaceChildren();
    const params = new URLSearchParams();
    if (contentId) params.set('content_id', contentId);
    if (studyPlanId) params.set('study_plan_id', studyPlanId);
    tutorSourceReady = !params.size;
    if (!params.size) { if (status) status.textContent = SLMClient.message('no_source', 'No source material selected.'); return; }
    if (status) status.textContent = SLMClient.message('source_loading', 'Loading available source sections…');
    chatForm.querySelector('button[type=submit]').disabled = true;
    try {
        const preview = await SLMClient.request('/api/ai/context?' + params);
        if (revision !== tutorSourceRequest || tutorOwner !== SLMClient.account()) return;
        const source = preview?.source;
        if (!source?.source_version || !Array.isArray(source.available_sections)) throw new Error(SLMClient.message('source_load_failed', 'Source could not be loaded. Reload before asking.'));
        tutorSource = source; tutorSourceReady = true;
        if (status) status.textContent = `${source.title}: ${source.included_characters}/${source.total_characters} ${SLMClient.message('characters', 'characters')}. ` + (source.truncated ? SLMClient.message('source_partial', 'Partial source: some material was not included.') : '') + ' ' + SLMClient.message('answer_unverified', 'Response not verified against the source.');
        source.available_sections.forEach(section => {
            const label = document.createElement('label'); label.className = 'form-check d-block';
            const input = document.createElement('input'); input.type = 'checkbox'; input.value = section.id; input.className = 'form-check-input';
            const caption = document.createElement('span'); caption.textContent = `${section.title} (${section.characters})`; caption.className = 'form-check-label';
            input.onchange = () => {
                if (box.querySelectorAll('input:checked').length > 12) { input.checked = false; showToast(SLMClient.message('source_section_limit', 'Select at most 12 sections.'), 'warning'); return; }
                cancelTutorRequest(true);
                tutorEpoch++; tutorConversation = []; tutorBusy = false; chatHistory.textContent = I18n.t('ai_tutor.start_conversation');
                chatForm.querySelector('button[type=submit]').disabled = !tutorPolicy || tutorPolicy.mode === 'disabled';
            };
            label.append(input, caption); box?.append(label);
        });
    } catch (error) { if (revision === tutorSourceRequest && status) status.textContent = error.message; }
    finally { if (revision === tutorSourceRequest) chatForm.querySelector('button[type=submit]').disabled = !tutorSourceReady || tutorBusy || !tutorPolicy || tutorPolicy.mode === 'disabled'; }
};

function tutorReceiptText(receipt) {
    const unknown = SLMClient.message('unknown', 'Unknown');
    return `${receipt.provider || unknown} / ${receipt.model || unknown}. ${receipt.elapsed_seconds ?? unknown}s. ` +
        `${SLMClient.message('ai_request_usage', 'Requests today')}: ${receipt.requests_used_today ?? unknown}/${receipt.requests_limit_daily ?? unknown}. ` +
        `${SLMClient.message('ai_tokens', 'Tokens used')}: ${receipt.tokens_used ?? unknown}. ` + SLMClient.message('ai_cost_unknown', 'Cost is unknown.') + ' ' +
        (receipt.provider_may_continue ? SLMClient.message('ai_provider_may_continue', 'The provider may continue working and may charge for this request.') : '');
}
window.refreshTutorUsage = async () => {
    try {
        const usage = await SLMClient.request('/api/ai/usage');
        const target = document.getElementById('tutor-usage-status');
        if (Number.isFinite(usage.requests_used_today) && Number.isFinite(usage.requests_limit_daily)) target.textContent = `${SLMClient.message('ai_request_usage', 'Requests today')}: ${usage.requests_used_today}/${usage.requests_limit_daily}.`;
    } catch { document.getElementById('tutor-usage-status').textContent = SLMClient.message('ai_usage_unavailable', 'Usage could not be loaded.'); }
};
window.prepareNewTutorRequest = async () => {
    const pending = tutorPending;
    if (!pending || tutorBusy || pending.cancelling || tutorOwner !== SLMClient.account()) return;
    if (!await showConfirm(SLMClient.message('new_tutor_confirm', 'Start a new request for this question? The previous outcome is unknown and provider work may still finish or incur charges. The new request counts separately.'))) return;
    if (pending !== tutorPending || tutorOwner !== SLMClient.account()) return;
    tutorPending = null;
    document.getElementById('tutor-new-request-btn').classList.add('d-none');
    document.getElementById('chat-input').focus();
};
window.cancelTutorRequest = async (contextChanged = false) => {
    const pending = tutorPending;
    if (!pending || pending.terminal || pending.cancelling) return;
    pending.cancelling = true;
    tutorEpoch++; tutorBusy = false; pending.controller?.abort();
    const input = document.getElementById('chat-input'); input.disabled = false;
    if (!input.value) input.value = pending.message;
    document.getElementById('typing-indicator')?.remove();
    document.getElementById('tutor-cancel-btn').disabled = true;
    const status = document.getElementById('tutor-request-status');
    status.textContent = SLMClient.message('ai_cancel_pending', 'Cancellation requested; waiting for the server.');
    try {
        const result = await SLMClient.request(`/api/ai/requests/${encodeURIComponent(pending.id)}/cancel`, {method:'POST'});
        const receipt = result;
        if (receipt?.request_id !== pending.id || !['cancelled', 'completed', 'failed', 'timed_out'].includes(receipt.status)) throw new Error('Unconfirmed cancellation');
        pending.terminal = receipt.status !== 'completed';
        if (tutorPending === pending) status.textContent = (receipt.status === 'cancelled' ? SLMClient.message('ai_cancel_confirmed', 'The server confirmed cancellation of delivery.') : SLMClient.message('ai_already_finished', 'This request had already finished. Retry the same question to retrieve its result.')) + ' ' + tutorReceiptText(receipt);
    } catch {
        if (tutorPending === pending) status.textContent = SLMClient.message('ai_cancel_unconfirmed', 'Server cancellation is unconfirmed. The provider may still run and charge. Your question is kept.');
    } finally {
        pending.cancelling = false;
        if (tutorPending === pending && !contextChanged) chatForm.querySelector('button[type=submit]').disabled = !tutorSourceReady || !tutorPolicy || tutorPolicy.mode === 'disabled';
    }
};

function appendTutorMessage(text, modelResponse, metadata = {}) {
    const row = document.createElement('div');
    row.className = 'chat-message ' + (modelResponse ? 'chat-message-ai' : 'chat-message-user');
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble';
    if (modelResponse) SLMRender.setMarkdown(bubble, text);
    else bubble.textContent = text;
    row.append(bubble);
    if (modelResponse) {
        const details = document.createElement('small');
        details.className = 'd-block text-secondary';
        let label = SLMClient.message('answer_unverified', 'Response not verified against the source.') + ' ';
        label += metadata.status && metadata.status !== 'suggestion' ?
            SLMClient.message('ai_unavailable', 'AI response unavailable. Try again or ask your teacher.') :
            SLMClient.message('ai_suggestion', 'AI suggestion; check it against your learning material.');
        if (metadata.effective_assistance === 'hint') label += ' ' + SLMClient.message('effective_hint', 'Requested help: hint under the current policy.');
        const source = metadata.source;
        details.textContent = label + (source ? ` ${SLMClient.message('source_context', 'Context')}: ${source.title}; ${(source.references || []).join(', ')}. ${source.included_characters}/${source.total_characters} ${SLMClient.message('characters', 'characters')}. ${source.truncated ? SLMClient.message('source_partial', 'Partial source: some material was not included.') : ''}` :
            ` ${SLMClient.message('no_source', 'No source material selected.')}`);
        row.append(details);
    }
    chatHistory.append(row);
}

if (chatForm) {
    chatForm.addEventListener('submit', async event => {
        event.preventDefault();
        const input = document.getElementById('chat-input');
        if (tutorOwner !== SLMClient.account()) { resetTutorContext(); showToast(SLMClient.message('account_changed', 'The signed-in account changed. Reload before continuing.'), 'warning'); return; }
        const message = input.value.trim();
        if (!message || tutorBusy || !tutorSourceReady || !tutorPolicy || tutorPolicy.mode === 'disabled' || tutorPending?.cancelling) return;
        const payload = {message, assistance: document.getElementById('tutor-assistance').value, conversation_history: tutorConversation.slice(-10)};
        const plan = document.getElementById('tutor-study-plan').value, content = document.getElementById('tutor-content').value;
        if (plan) payload.study_plan_id = Number(plan);
        if (content) payload.content_id = Number(content);
        if (tutorSource) { payload.source_version = tutorSource.source_version; payload.section_ids = [...document.querySelectorAll('#tutor-source-sections input:checked')].map(item => item.value); }
        const fingerprint = JSON.stringify(payload);
        if (!tutorPending || tutorPending.terminal || tutorPending.fingerprint !== fingerprint) tutorPending = {id: crypto.randomUUID(), fingerprint, message};
        const pending = tutorPending; pending.controller = new AbortController();
        document.getElementById('tutor-new-request-btn').classList.add('d-none');
        payload.client_request_id = pending.id;
        const epoch = tutorEpoch; tutorBusy = true; input.disabled = true;
        const send = chatForm.querySelector('button[type=submit]'); send.disabled = true;
        const cancel = document.getElementById('tutor-cancel-btn'); cancel.disabled = false;
        const status = document.getElementById('tutor-request-status'); status.textContent = I18n.t('ai.chat.status.thinking');
        try {
            const result = await SLMClient.request('/api/ai/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload), signal:pending.controller.signal});
            if (epoch !== tutorEpoch || tutorOwner !== SLMClient.account()) return;
            const receipt = result?.receipt;
            if (receipt && (receipt.request_id !== pending.id || !['completed','failed','cancelled','timed_out'].includes(receipt.status))) throw new Error(SLMClient.message('ai_receipt_unconfirmed', 'The server did not confirm this request. Your question is kept; retry.'));
            pending.terminal = true; status.textContent = receipt ? tutorReceiptText(receipt) : SLMClient.message('ai_usage_unreported', 'Request usage was not reported. Cost is unknown.');
            if ((receipt && receipt.status !== 'completed') || result.status !== 'suggestion') return;
            if (payload.source_version && result.source?.source_version !== payload.source_version) { tutorSourceReady = false; document.getElementById('tutor-source-status').textContent = SLMClient.message('source_changed', 'Source changed. Reload the source, review your sections, and retry.'); return; }
            if (result.assistance_policy) applyTutorPolicy(result.assistance_policy);
            appendTutorMessage(message, false); appendTutorMessage(result.response, true, result);
            tutorConversation.push({role:'user',content:message},{role:'assistant',content:result.response}); tutorConversation = tutorConversation.slice(-10);
            input.value = ''; chatHistory.scrollTop = chatHistory.scrollHeight;
        } catch (error) {
            if (epoch !== tutorEpoch || tutorOwner !== SLMClient.account()) return;
            if ([401,403,429].includes(error.status)) pending.terminal = true;
            if (error.status === 403) await refreshTutorPolicy();
            if (error.status === 409 && /source|revision/i.test(error.message)) { tutorSourceReady = false; document.getElementById('tutor-source-status').textContent = SLMClient.message('source_changed', 'Source changed. Reload the source, review your sections, and retry.'); }
            status.textContent = error.message || I18n.t('ai.chat.error_send');
            document.getElementById('tutor-new-request-btn').classList.toggle('d-none', pending.terminal === true);
        } finally {
            if (epoch === tutorEpoch) { tutorBusy = false; input.disabled = false; cancel.disabled = true; send.disabled = !tutorSourceReady || !tutorPolicy || tutorPolicy.mode === 'disabled'; }
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
        <div class="col-md-4 ${role}-card" data-name="${escapeHtml((u.first_name + ' ' + u.last_name).toLowerCase())}" data-username="${escapeHtml(u.username.toLowerCase())}">
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title">${escapeHtml(u.first_name)} ${escapeHtml(u.last_name)}</h5>
                    <p class="text-muted mb-1">@${escapeHtml(u.username)}</p>
                    <p class="mb-2">
                        <span class="badge bg-primary">Level ${u.level || 1}</span>
                        <span class="badge bg-success">${u.xp || 0} XP</span>
                    </p>
                    ${role === 'student' ? `<button class="btn btn-sm btn-outline-primary" onclick="viewStudentDetail(${u.id})">${SLMClient.message('view_details', 'View details')}</button>` : ''}
                    ${AuthService.getRole() === 'admin' ? `<button class="btn btn-sm btn-outline-secondary" onclick="manageAccount(${u.id}, '${role}')">${SLMClient.message('manage_account', 'Manage account')}</button><span class="badge bg-secondary ms-2">${SLMClient.message(u.active === false ? 'account_inactive' : 'account_active', u.active === false ? 'Inactive' : 'Active')}</span>` : ''}
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
        const res = await fetch(`/api/auth/users?role=${role}${AuthService.getRole() === 'admin' && window.includeInactiveAccounts ? '&include_inactive=true' : ''}`, {
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
                <td>${escapeHtml(e.username)}</td>
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
let currentGradingStatusFilter = new URLSearchParams(window.location.search).get('grading_filter') || 'all';
document.querySelectorAll('#grading-filter-tabs .tab').forEach(tab => {
    const active = tab.dataset.gradingFilter === currentGradingStatusFilter;
    tab.classList.toggle('active', active); tab.setAttribute('aria-pressed', String(active));
});

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
        const submittedAt = sub.submitted_at ? SLMTime.format(sub.submitted_at, { dateOnly: true }) : '';
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
                    <a class="btn btn-primary btn-sm mt-2" href="/grading.html?submission_id=${Number(sub.id)}&filter=${encodeURIComponent(currentGradingStatusFilter)}">${SLMClient.message('open_submission', 'Open submission')}</a>
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
    tabs.forEach(t => { t.classList.remove('active'); t.setAttribute('aria-pressed', 'false'); });
    if (tab) { tab.classList.add('active'); tab.setAttribute('aria-pressed', 'true'); }

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
            contextBadges += `<span class="badge bg-primary me-1" title="Content">${icon} ${escapeHtml(r.content_title)}</span>`;
        }
        if (r.study_plan_title) {
            contextBadges += `<span class="badge bg-secondary me-1" title="Study Plan">📋 ${escapeHtml(r.study_plan_title)}</span>`;
        }

        return `
            <a href="javascript:void(0)" class="list-group-item list-group-item-action" onclick="viewHelpRequest(${r.id})">
                <div class="d-flex w-100 justify-content-between">
                    <h5 class="mb-1">${escapeHtml(r.subject || 'Help Request')}</h5>
                    <span class="badge ${r.priority >= 3 ? 'bg-danger' : r.priority >= 2 ? 'bg-warning text-dark' : 'bg-secondary'}">${r.priority >= 3 ? 'Urgent' : r.priority >= 2 ? 'Important' : 'Normal'}</span>
                </div>
                <p class="mb-1">${escapeHtml(r.request_text || r.description)}</p>
                ${contextBadges ? `<div class="mb-1">${contextBadges}</div>` : ''}
                <small class="text-muted">From: ${escapeHtml(r.student_name || 'Student #' + r.student_id)} | ${escapeHtml(r.status)}</small>
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
        const res = await fetch(`/api/auth/users?role=student${AuthService.getRole() === 'admin' ? '&include_inactive=true' : ''}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!res.ok) {
            showToast('Could not load student details', 'danger');
            return;
        }

        const students = await res.json();
        if (id !== currentStudentId) return;
        const student = students.find(s => s.id === id);

        if (!student) {
            showToast('Student not found', 'warning');
            return;
        }

        await loadStudentTeacher(student);
        if (id !== currentStudentId) return;
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
                if (id !== currentStudentId) return;
                const earned = badges.filter(b => b.earned);
                if (earned.length > 0) {
                    badgesContainer.innerHTML = earned.slice(0, 5).map(b =>
                        `<span class="badge bg-warning text-dark">${escapeHtml(b.name)}</span>`
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
                if (id !== currentStudentId) return;
                const lessonsEl = document.getElementById('student-lessons-completed');
                const assessmentsEl = document.getElementById('student-assessments-taken');
                const avgScoreEl = document.getElementById('student-avg-score');
                const studyTimeEl = document.getElementById('student-study-time');
                if (lessonsEl) lessonsEl.textContent = progress.lessons_completed || 0;
                if (assessmentsEl) assessmentsEl.textContent = progress.assessments_taken || 0;
                if (avgScoreEl) avgScoreEl.textContent = progress.avg_score !== null && progress.avg_score !== undefined ? `${Math.round(progress.avg_score)}%` : '-';
                if (studyTimeEl) studyTimeEl.textContent = progress.study_time_hours ? `${Math.round(progress.study_time_hours)}h` : '0h';
            }
        } catch (e) {
            console.warn('Failed to load student progress:', e);
        }

        // Load teacher notes
        if (id !== currentStudentId) return;
        window.currentStudentId = id;
        try {
            const notesRes = await fetch(`/api/students/${id}/notes`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (notesRes.ok) {
                const notesData = await notesRes.json();
                if (id !== currentStudentId) return;
                const notesEl = document.getElementById('student-teacher-notes');
                if (notesEl) notesEl.value = notesData.notes || '';
            }
        } catch (e) {
            console.warn('Failed to load student notes:', e);
        }

        if (id !== currentStudentId) return;
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
                    if (id !== currentStudentId) return;
                    if (!plans || plans.length === 0) {
                        selectEl.innerHTML = '<option value="" disabled selected>No study plans available</option>';
                        selectEl.disabled = true;
                        btnEl.disabled = true;
                    } else {
                        const states = await Promise.all(plans.map(async plan => {
                            try { return { ...plan, workflow: await SLMClient.request(`/api/study-plans/${plan.id}/workflow`) }; }
                            catch { return { ...plan, workflow: { status: 'unavailable' } }; }
                        }));
                        if (id !== currentStudentId) return;
                        selectEl.replaceChildren();
                        states.forEach(plan => {
                            const option = new Option(`${plan.title} (${SLMClient.message('workflow_' + plan.workflow.status, plan.workflow.status)})`, plan.id);
                            option.disabled = plan.workflow.status !== 'published'; selectEl.append(option);
                        });
                        selectEl.value = states.find(plan => plan.workflow.status === 'published')?.id || '';
                        selectEl.disabled = !selectEl.value;
                        btnEl.disabled = !selectEl.value;
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
                contextParts.push(`<span class="badge bg-primary me-2">${icon} ${escapeHtml(request.content_title)}</span>`);
            }

            if (request.study_plan_title) {
                contextParts.push(`<span class="badge bg-secondary me-2">📋 ${escapeHtml(request.study_plan_title)}</span>`);
            }

            if (request.question_text) {
                contextParts.push(`<span class="badge bg-info text-dark me-2" title="${escapeHtml(request.question_text)}">❓ Question</span>`);
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
        const manageable = isTeacherOrAdmin ? new Set((await SLMClient.request('/api/study-plans')).map(plan => plan.id)) : new Set();
        if (studyPlans.length > 0) {
            html += '<h5 class="mb-3">📚 Study Plans</h5>';

            for (const plan of studyPlans) {
                const workflow = await SLMClient.request(`/api/study-plans/${plan.id}/workflow`).catch(() => ({read_only:true,status:'unavailable'}));
                const canManage = manageable.has(plan.id);
                const canEdit = canManage && !workflow.read_only;
                html += `
                    <div class="card mb-3 study-plan-tree" data-plan-id="${plan.id}">
                        <div class="card-header bg-primary bg-opacity-10 d-flex justify-content-between align-items-center">
                            <div class="d-flex align-items-center">
                                <button class="btn btn-sm btn-link text-decoration-none me-2 toggle-plan-btn" onclick="togglePlanContents(${plan.id})">
                                    <span class="toggle-icon">▶</span>
                                </button>
                                <strong>📘 ${escapeHtml(plan.title)}</strong>
                                <span class="badge bg-secondary ms-2">${plan.contents.length} ${SLMClient.message('items', 'items')}</span>
                                <span class="badge bg-secondary ms-2">${SLMClient.message('workflow_' + workflow.status, workflow.status)}</span>
                            </div>
                            <div class="btn-group btn-group-sm">
                                ${canManage ? `<a class="btn btn-outline-primary" href="/study_plan_builder.html?id=${plan.id}">${SLMClient.message('edit_or_copy', 'Review, edit or copy')}</a>` : ''}
                                ${canEdit ? `<button class="btn btn-outline-success" onclick="addTopicToPlan(${plan.id})" title="Add Topic">+ Topic</button>
                                <button class="btn btn-outline-primary" onclick="generateForPlan(${plan.id})" title="Generate Content">🤖 Generate</button>` : ''}
                                ${canManage ? `<button class="btn btn-outline-info" onclick="viewPlanGrades(${plan.id})" title="View Grades">📊 Grades</button>` : ''}
                            </div>
                        </div>
                        <div class="card-body plan-contents hidden" id="plan-contents-${plan.id}">
                            ${renderPlanContents(plan.id, plan.contents, canEdit)}
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
function renderPlanContents(planId, contents, canEdit = false) {
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
                            ${typeIcons[item.content_type] || '📄'} ${escapeHtml(item.content_type.toUpperCase())}
                        </span>
                        ${escapeHtml(item.title)}
                        <small class="text-muted ms-2">Difficulty: ${'⭐'.repeat(item.difficulty || 1)}</small>
                    </div>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary" onclick="viewContent(${item.id})">👁️</button>
                        <button class="btn btn-outline-success" onclick="startSession(${item.id}, ${planId})" title="Start with guided navigation">▶️</button>
                        ${canEdit && item.can_edit === true ? `<button class="btn btn-outline-warning" onclick="editContent(${item.id})" aria-label="${SLMClient.message('edit', 'Edit')}">✏️</button>
                        <button class="btn btn-outline-danger" onclick="deleteContent(${item.id})" aria-label="${SLMClient.message('delete', 'Delete')}">🗑️</button>` : ''}
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
            <div class="card h-100" data-creator-id="${item.creator_id || ''}" data-can-edit="${item.can_edit === true}">
                <div class="card-body">
                    <span class="badge ${typeColors[type] || 'bg-secondary'} mb-2">
                        ${typeIcons[type] || '📄'} ${escapeHtml(type.toUpperCase())}
                    </span>
                    <h5 class="card-title">${escapeHtml(item.title)}</h5>
                    ${(item.creator_id && currentUserId && item.creator_id !== currentUserId && (item.creator_name || item.creator_username)) ? `
                    <p class="text-muted small mb-2">
                        From: ${escapeHtml(item.creator_name || 'Student')}${item.creator_username ? ` (@${escapeHtml(item.creator_username)})` : ''}
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
        if (!result.success) throw new Error(SLMClient.message('generation_partial', 'Some items failed. Saved items were kept; retry the same request to finish.'));
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
        const summary = `📊 Total: ${grades.total_assessments} | Graded: ${grades.graded_submissions} | Avg: ${grades.average_score ?? 'N/A'}%`;
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
    activeContinuePlan = null; activeNextContentId = null;
    try {
        const plans = await SLMClient.request('/api/study-plans');
        const position = SLMClient.drafts.read('learning-location', 'current', 0);
        const orderedPlans = [...plans].sort((a, b) => Number(b.id === position?.planId) - Number(a.id === position?.planId));
        let completedCourse = null;
        for (const plan of orderedPlans) {
            const tree = await SLMClient.request(`/api/study-plans/${plan.id}/tree`);
            if (!tree.contents?.length) continue;
            const progress = await SLMClient.request(`/api/study-plans/${plan.id}/my-progress`);
            const contents = tree.contents.sort((a, b) => (a.phase_index || 0) - (b.phase_index || 0) || (a.order_index || 0) - (b.order_index || 0));
            const completed = new Set((progress.completed_content_ids || []).map(Number));
            let next = contents.findIndex(item => !completed.has(Number(item.id)));
            const resume = contents.findIndex(item => item.id === position?.contentId && !completed.has(Number(item.id)));
            if (position?.planId === plan.id && resume >= 0) next = resume;
            const data = { tree, contents, next, completedIds: contents.filter(item => completed.has(Number(item.id))).map(item => item.id) };
            if (next < 0) { completedCourse ||= data; continue; }
            showContinuePlan(data); return;
        }
        if (completedCourse) showContinuePlan(completedCourse);
        else card.style.display = 'none';
    } catch (error) {
        card.style.display = 'none';
        showToast(SLMClient.message('progress_unavailable', 'Progress could not be loaded. Retry when connected.'), 'warning');
    }
};
function showContinuePlan({tree, contents, next, completedIds}) {
    activeContinuePlan = tree; activePlanContents = contents;
    activeNextContentId = next >= 0 ? contents[next].id : null;
    document.getElementById('continue-plan-title').textContent = tree.title;
    document.getElementById('continue-next-title').textContent = next >= 0 ? contents[next].title : SLMClient.message('course_completed', 'Course completed');
    document.getElementById('continue-progress-text').textContent = `${completedIds.length}/${contents.length} ` + SLMClient.message('completed_items', 'items completed');
    document.getElementById('continue-btn').disabled = next < 0;
    renderProgressTimeline(contents, next, completedIds);
    document.getElementById('continue-learning-card').style.display = 'block';
}

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
        const node = document.createElement('button');
        node.type = 'button';
        node.setAttribute('aria-label', item.title);
        node.className = `timeline-node ${state}`;
        node.onclick = () => goToTimelineContent(item.id);

        // Icon based on content type and state
        let icon = '📖';
        if (item.content_type === 'exercise') icon = '🏋️';
        if (item.content_type === 'assessment') icon = '📝';
        if (state === 'completed') icon = '✓';

        node.innerHTML = `
            <div class="timeline-node-circle">${icon}</div>
            <div class="timeline-node-label" title="${escapeHtml(item.title)}">${escapeHtml(truncateText(item.title, 10))}</div>
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
                        <span>${escapeHtml(entry.display_name || entry.username || 'User')}</span>
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
    if (dashboardStartupFailed) return;
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

async function restoreSessionContext() {
    if (dashboardStartupFailed) return;
    const params = new URLSearchParams(window.location.search);
    if (params.get('from_session') !== '1' || !/^\d+$/.test(params.get('content_id') || '')) return;
    try {
        const content = await SLMClient.request(`/api/content/${Number(params.get('content_id'))}`);
        const planId = /^\d+$/.test(params.get('plan_id') || '') ? Number(params.get('plan_id')) : null;
        const plan = planId ? await SLMClient.request(`/api/study-plans/${planId}/tree`) : null;
        if (plan && !plan.contents.some(item => item.id === content.id)) return;
        window.setLearningContext({contentId: content.id, contentTitle: content.title, contentType: content.content_type, studyPlanId: planId, studyPlanTitle: plan?.title, questionId: null});
        const back = document.getElementById('session-context-return');
        back.href = `/session_player.html?content_id=${content.id}` + (planId ? `&plan_id=${planId}` : '');
        back.classList.remove('d-none');
        if (params.get('ask_help') === '1') bootstrap.Modal.getOrCreateInstance(document.getElementById('helpModal')).show();
    } catch (error) { showToast(error.message, 'warning'); }
}
document.addEventListener('DOMContentLoaded', restoreSessionContext);

let savingStudentTeacher = false;
async function loadStudentTeacher(student) {
    const container = document.getElementById('student-teacher-container');
    if (!container) return;
    container.classList.toggle('d-none', AuthService.getRole() !== 'admin');
    if (AuthService.getRole() !== 'admin') return;
    const select = document.getElementById('student-teacher-select');
    const button = document.getElementById('student-teacher-save');
    select.disabled = true; button.disabled = true;
    try {
        const teachers = await SLMClient.request('/api/auth/users?role=teacher');
        if (student.id !== currentStudentId) return;
        select.replaceChildren(new Option(SLMClient.message('unassigned_teacher', 'Unassigned'), ''));
        teachers.forEach(teacher => select.append(new Option(`${teacher.first_name} ${teacher.last_name} (${teacher.username})`, teacher.id)));
        select.value = student.teacher_id ?? '';
        select.disabled = false; button.disabled = false;
        document.getElementById('student-teacher-status').textContent = '';
    } catch (error) { document.getElementById('student-teacher-status').textContent = error.message; }
}
window.saveStudentTeacher = async () => {
    if (savingStudentTeacher || !currentStudentId || AuthService.getRole() !== 'admin') return;
    const studentId = currentStudentId;
    const teacher = document.getElementById('student-teacher-select').value;
    if (!await showConfirm(SLMClient.message('teacher_change_confirm', 'Change the responsible teacher? This changes who can manage this learner.'))) return;
    if (studentId !== currentStudentId) return;
    savingStudentTeacher = true;
    try {
        await SLMClient.request(`/api/students/${studentId}/teacher`, {method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify({teacher_id: teacher ? Number(teacher) : null})});
        document.getElementById('student-teacher-status').textContent = SLMClient.message('teacher_saved', 'Responsible teacher saved.');
    } catch (error) { document.getElementById('student-teacher-status').textContent = error.message; }
    finally { savingStudentTeacher = false; }
};

if (!dashboardStartupFailed && document.readyState !== 'loading') { initSettingsUI(); restoreDashboardView(); restoreSessionContext(); }

function finishDashboardStartup() {
    if (dashboardStartupFailed) return;
    const app = document.getElementById('dashboard-app');
    if (app) { app.removeAttribute('inert'); app.setAttribute('aria-busy', 'false'); }
    const loading = document.getElementById('dashboard-loading');
    if (loading) loading.hidden = true;
}
finishDashboardStartup();
