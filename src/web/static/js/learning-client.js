/* Shared checked requests and bounded, account/attempt-scoped local drafts. */
(function (root) {
    'use strict';
    const PREFIX = 'slm_draft_v1:';
    const TTL = 7 * 24 * 60 * 60 * 1000;
    function message(key, fallback) {
        const value = root.I18n?.t?.(`recovery.${key}`);
        return value && value !== `recovery.${key}` ? value : fallback;
    }
    class APIError extends Error {
        constructor(status, detail) {
            super(status === 401 ? message('reauth', 'Sign in again, then retry. Your draft is kept on this device.') :
                status === 403 ? message('forbidden', 'You do not have permission. Your draft is kept on this device.') :
                    (typeof detail === 'string' ? detail : message('failed', 'The server could not save your work. Please retry.')));
            this.status = status;
        }
    }
    async function request(url, options = {}) {
        const token = root.AuthService?.getToken();
        const response = await fetch(url, { ...options, headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers
        }});
        const data = response.status === 204 ? null : await response.json().catch(() => null);
        if (!response.ok) throw new APIError(response.status, data?.detail);
        return data;
    }
    function account() {
        const id = root.AuthService?.getUser()?.id;
        return id === undefined || id === null ? null : String(id);
    }
    function key(kind, resource, attempt) {
        const owner = account();
        if (!owner || resource == null || attempt == null) return null;
        return PREFIX + [owner, kind, resource, attempt].map(v => encodeURIComponent(String(v))).join(':');
    }
    function prune() {
        try {
            for (let i = localStorage.length - 1; i >= 0; i--) {
                const k = localStorage.key(i);
                // Legacy drafts have no owner: never restore/migrate them into an account.
                if (/^(session_notes_|notes_\d|assessment_progress_)/.test(k)) localStorage.removeItem(k);
                else if (k?.startsWith(PREFIX)) {
                    try {
                        const value = JSON.parse(localStorage.getItem(k));
                        if (!value.expiresAt || value.expiresAt <= Date.now()) localStorage.removeItem(k);
                    } catch { localStorage.removeItem(k); }
                }
            }
        } catch { /* Storage can be unavailable; server saves still work. */ }
    }
    function read(kind, resource, attempt) {
        const k = key(kind, resource, attempt);
        if (!k) return null;
        try {
            const entry = JSON.parse(localStorage.getItem(k));
            if (!entry || entry.owner !== account() || entry.expiresAt <= Date.now()) {
                localStorage.removeItem(k); return null;
            }
            return entry.value;
        } catch { return null; }
    }
    function write(kind, resource, attempt, value) {
        const k = key(kind, resource, attempt);
        if (!k) return false;
        try {
            localStorage.setItem(k, JSON.stringify({ owner: account(), expiresAt: Date.now() + TTL, value }));
            return true;
        } catch { return false; }
    }
    function remove(kind, resource, attempt) {
        try { const k = key(kind, resource, attempt); if (k) localStorage.removeItem(k); } catch { /* Already unavailable. */ }
    }
    function chooseDraft() {
        return new Promise(resolve => {
            const previousFocus = document.activeElement;
            const modal = document.createElement('div');
            modal.className = 'modal fade'; modal.tabIndex = -1;
            const titleId = 'draft-choice-' + Date.now();
            modal.setAttribute('aria-labelledby', titleId);
            modal.innerHTML = '<div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h2 class="modal-title h5"></h2></div><div class="modal-body"></div><div class="modal-footer"></div></div></div>';
            modal.querySelector('h2').id = titleId;
            modal.querySelector('h2').textContent = message('draft_found', 'Saved draft found');
            modal.querySelector('.modal-body').textContent = message('restore_answers', 'Restore the saved work for this attempt?');
            const controller = new bootstrap.Modal(modal);
            let result = 'keep';
            ['restore', 'discard', 'keep'].forEach(action => {
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'btn ' + (action === 'restore' ? 'btn-primary' : 'btn-outline-secondary');
                button.textContent = message(action, { restore: 'Restore', discard: 'Discard', keep: 'Leave and keep draft' }[action]);
                button.onclick = () => { result = action; controller.hide(); };
                modal.querySelector('.modal-footer').append(button);
            });
            modal.addEventListener('shown.bs.modal', () => modal.querySelector('button').focus(), { once: true });
            modal.addEventListener('hidden.bs.modal', () => {
                controller.dispose(); modal.remove(); previousFocus?.focus(); resolve(result);
            }, { once: true });
            document.body.append(modal); controller.show();
        });
    }
    // Other tabs may switch accounts while this page has unsaved account-specific state.
    root.addEventListener('storage', event => {
        if (['user', 'token'].includes(event.key) && event.oldValue !== event.newValue) root.location.reload();
    });
    prune();
    root.SLMClient = Object.freeze({ request, APIError, message, account, chooseDraft, drafts: { read, write, remove, prune }, draftTTL: TTL });
})(window);
