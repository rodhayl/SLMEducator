/* Explicit administrator account operations. Passwords never leave form/request scope. */
(function(root) {
    'use strict';
    const text = (key, fallback) => SLMClient.message(key, fallback);
    let selected = null, revision = 0, busy = false, owner = null;
    const el = id => document.getElementById(id);
    function allowed() { return AuthService.getRole() === 'admin' && owner === SLMClient.account(); }
    function status(message, failed = false) {
        const node = el('account-operation-status'); node.textContent = message;
        node.className = failed ? 'text-danger mt-2' : 'text-success mt-2';
    }
    function updateControls() {
        const editable = Boolean(selected) && allowed() && !busy;
        ['account-status-btn','account-reset-btn','account-new-password','account-confirm-password'].forEach(id => {el(id).disabled = !editable;});
        el('account-status-btn').dataset.i18n = 'recovery.' + (selected?.active ? 'deactivate_account' : 'activate_account');
        el('account-status-btn').textContent = selected?.active ? text('deactivate_account', 'Deactivate account') : text('activate_account', 'Activate account');
        el('account-current-status').textContent = selected ? text(selected.active ? 'account_active' : 'account_inactive', selected.active ? 'Active' : 'Inactive') : '';
    }
    function identity(user) { return `${user.first_name || ''} ${user.last_name || ''} (@${user.username}; ${user.email})`.trim(); }
    root.manageAccount = async (id, filterRole = null) => {
        if (AuthService.getRole() !== 'admin' || !Number.isInteger(Number(id)) || Number(id) <= 0) return;
        const request = ++revision; owner = SLMClient.account(); selected = null; busy = false;
        el('account-new-password').value = ''; el('account-confirm-password').value = '';
        el('account-identity').textContent = text('loading', 'Loading…'); status(''); updateControls();
        bootstrap.Modal.getOrCreateInstance(el('accountManagerModal')).show();
        try {
            const roleQuery = ['student','teacher','admin'].includes(filterRole) ? '&role=' + filterRole : '';
            const users = await SLMClient.request('/api/auth/users?include_inactive=true&limit=500' + roleQuery);
            if (request !== revision || !allowed()) return;
            selected = users.find(user => user.id === Number(id) && String(user.id) !== owner);
            if (!selected) throw new Error(text('account_missing', 'This account could not be found. Reload the account list.'));
            el('account-identity').textContent = identity(selected); updateControls();
        } catch (error) { if (request === revision) status(error.message, true); }
    };
    function requireTarget() { return selected && allowed() && !busy ? {id:selected.id, revision, label:identity(selected)} : null; }
    function sameTarget(target) { return allowed() && target.revision === revision && selected?.id === target.id; }
    function refreshList() {
        const fn = {student:'loadStudents',teacher:'loadTeachers',admin:'loadAdmins'}[selected?.role];
        if (fn && typeof root[fn] === 'function') root[fn]();
    }
    root.changeManagedAccountStatus = async () => {
        const target = requireTarget(); if (!target) return;
        const active = !selected.active; busy = true; updateControls();
        try {
            const action = active ? text('activate_account', 'Activate account') : text('deactivate_account', 'Deactivate account');
            if (!await showConfirm(`${action}: ${target.label}? ${text('account_revoke_notice', 'Existing sessions will be revoked. Previous learning work is preserved.')}`)) return;
            if (!sameTarget(target)) return;
            const result = await SLMClient.request(`/api/auth/users/${target.id}/status`, {method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({active,confirm:true})});
            if (!sameTarget(target)) return;
            if (result?.id !== target.id || result.active !== active || result.sessions_revoked !== true) throw new Error(text('account_action_unconfirmed', 'The server did not confirm this account change. Reload before retrying.'));
            selected.active = active; status(text('account_status_saved', 'Account status saved. Previous sessions were revoked.')); refreshList();
        } catch (error) { if (sameTarget(target)) status(error.message, true); }
        finally { if (sameTarget(target)) { busy = false; updateControls(); } }
    };
    root.resetManagedAccountPassword = async () => {
        const target = requireTarget(); if (!target) return;
        const password = el('account-new-password').value;
        if (password !== el('account-confirm-password').value) { status(text('password_mismatch', 'Passwords do not match.'), true); return; }
        if (Array.from(password).length < 12 || new TextEncoder().encode(password).length > 72) { status(text('admin_password_length', 'Use at least 12 characters and no more than 72 UTF-8 bytes.'), true); return; }
        busy = true; updateControls();
        try {
            if (!await showConfirm(`${text('reset_password', 'Reset password')}: ${target.label}? ${text('account_revoke_notice', 'Existing sessions will be revoked. Previous learning work is preserved.')}`)) return;
            if (!sameTarget(target)) return;
            const result = await SLMClient.request(`/api/auth/users/${target.id}/reset-password`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({new_password:password,confirm:true})});
            if (!sameTarget(target)) return;
            if (result?.id !== target.id || result.reset !== true || result.sessions_revoked !== true) throw new Error(text('account_action_unconfirmed', 'The server did not confirm this account change. Reload before retrying.'));
            el('account-new-password').value = ''; el('account-confirm-password').value = '';
            status(text('account_password_reset', 'Password reset. Previous sessions were revoked. No email was sent.'));
        } catch (error) { if (sameTarget(target)) status(error.message, true); }
        finally { if (sameTarget(target)) { busy = false; updateControls(); } }
    };
    root.toggleInactiveAccounts = checkbox => {
        root.includeInactiveAccounts = AuthService.getRole() === 'admin' && checkbox.checked;
        document.querySelectorAll('[data-inactive-accounts]').forEach(input => {input.checked = root.includeInactiveAccounts;});
        const view = document.querySelector('.nav-item.active')?.dataset.view;
        ({students:root.loadStudents,teachers:root.loadTeachers,admins:root.loadAdmins})[view]?.();
    };
    document.addEventListener('i18n-language-changed', updateControls);
    root.addEventListener('storage', event => {
        if (!['user','token'].includes(event.key)) return;
        revision++; selected=null; busy=false; owner=null;
        el('account-new-password').value='';el('account-confirm-password').value='';
        status(text('account_changed','The signed-in account changed. Reload before continuing.'),true);updateControls();
    });
    document.addEventListener('DOMContentLoaded', () => {
        el('accountManagerModal').addEventListener('hidden.bs.modal', () => {revision++;selected=null;busy=false;el('account-new-password').value='';el('account-confirm-password').value='';updateControls();});
    });
})(window);
