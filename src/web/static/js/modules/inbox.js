import { AuthService } from '../auth.js';

// I18n helper (fallback if I18n not available)
const t = (key, params = {}) => {
    if (typeof I18n !== 'undefined' && I18n.t) {
        return I18n.t(key, params);
    }
    return key;
};

// HTML escape helper
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Global UI Helper (assuming showToast and showConfirm are global or on window)
const showToast = window.showToast || ((msg, type) => console.log(`Toast [${type}]: ${msg}`));
const showConfirm = window.showConfirm || (() => Promise.resolve(true));

// --- INBOX & MESSAGING ---

// Store available recipients for filtering
let availableRecipients = [];
let currentRoleFilter = 'all';
let selectedMessageIds = new Set();
let currentInboxFolder = 'inbox';

// Exported for other modules if needed
export { availableRecipients };

/**
 * Load available recipients for the compose message dropdown
 */
window.loadRecipients = async function loadRecipients() {
    try {
        const token = AuthService.getToken();
        const res = await fetch('/api/classroom/users', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (res.ok) {
            availableRecipients = await res.json();
            renderRecipientList(availableRecipients);
        } else {
            console.error('Failed to load recipients');
            availableRecipients = [];
            renderRecipientList([]);
        }
    } catch (e) {
        console.error('Error loading recipients:', e);
        availableRecipients = [];
        renderRecipientList([]);
    }
};

/**
 * Render the recipient list in the dropdown
 */
function renderRecipientList(users) {
    const select = document.getElementById('compose-to');
    const countEl = document.getElementById('recipient-count');

    if (!select) return;

    select.innerHTML = '';

    if (users.length === 0) {
        select.innerHTML = `<option value="" disabled>${t('inbox.compose.no_users')}</option>`;
        if (countEl) countEl.textContent = t('inbox.compose.users_count_zero');
        return;
    }

    users.forEach(u => {
        const option = document.createElement('option');
        option.value = u.id;
        const roleIcon = u.role === 'student' ? '👨‍🎓' : u.role === 'teacher' ? '👩‍🏫' : '👤';
        option.textContent = `${roleIcon} ${u.full_name} (@${u.username})`;
        select.appendChild(option);
    });

    if (countEl) countEl.textContent = t('inbox.compose.users_count', { count: users.length });
}

/**
 * Filter recipients by search text
 */
window.filterRecipients = function filterRecipients() {
    const searchInput = document.getElementById('compose-search');
    const search = (searchInput?.value || '').toLowerCase();

    let filtered = availableRecipients;

    // Apply role filter
    if (currentRoleFilter !== 'all') {
        filtered = filtered.filter(u => u.role === currentRoleFilter);
    }

    // Apply text filter
    if (search) {
        filtered = filtered.filter(u =>
            u.full_name.toLowerCase().includes(search) ||
            u.username.toLowerCase().includes(search)
        );
    }

    renderRecipientList(filtered);
};

/**
 * Filter recipients by role
 */
window.filterByRole = function filterByRole(role, btn) {
    currentRoleFilter = role;

    // Update button states
    const btnGroup = btn?.parentElement;
    if (btnGroup) {
        btnGroup.querySelectorAll('.btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
    }

    if (typeof window.filterRecipients === 'function') window.filterRecipients();
};

/**
 * Send a message to the selected recipient
 */
window.sendMessage = async () => {
    const recipientSelect = document.getElementById('compose-to');
    const recipientId = recipientSelect?.value;
    const subject = document.getElementById('compose-subject').value;
    const content = document.getElementById('compose-content').value;

    if (!recipientId) {
        showToast(t('inbox.compose.select_recipient_error'), 'warning');
        return;
    }

    try {
        const token = AuthService.getToken();
        const res = await fetch('/api/classroom/messages', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({
                recipient_id: parseInt(recipientId),
                subject: subject,
                body: content
            })
        });

        if (res.ok) {
            showToast(t('inbox.compose.success_sent'), "success");
            const modalEl = document.getElementById('composeModal');
            if (modalEl) {
                const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
                modal.hide();
            }
            document.getElementById('compose-form').reset();
            document.getElementById('compose-search').value = '';
            currentRoleFilter = 'all';
            if (typeof window.loadInbox === 'function') window.loadInbox(); // Refresh
        } else {
            const err = await res.json();
            showToast(t('inbox.compose.error_send', { error: err.detail || 'Error' }), "danger");
        }
    } catch (e) {
        console.error('Send message error:', e);
        showToast(t('inbox.compose.error_network'), "danger");
    }
};

// Load recipients when compose modal is shown
document.addEventListener('DOMContentLoaded', () => {
    const composeModal = document.getElementById('composeModal');
    if (composeModal) {
        composeModal.addEventListener('show.bs.modal', () => {
            if (typeof window.loadRecipients === 'function') window.loadRecipients();
        });
    }
});


/**
 * Load messages for a specific folder
 */
window.loadInboxFolder = function (folder, tabElement) {
    currentInboxFolder = folder;

    // Update tab states
    const tabs = document.querySelectorAll('[data-inbox-folder]');
    tabs.forEach(t => t.classList.remove('active'));
    if (tabElement) tabElement.classList.add('active');

    if (typeof window.loadInbox === 'function') window.loadInbox();
};

window.loadInbox = async function loadInbox() {
    const list = document.getElementById('inbox-list');
    if (!list) return;

    list.innerHTML = '<div class="text-center p-3">Loading...</div>';

    try {
        const token = AuthService.getToken();
        const response = await fetch(`/api/classroom/messages?folder=${currentInboxFolder}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const messages = await response.json();

        list.innerHTML = '';
        if (messages.length === 0) {
            const emptyText = currentInboxFolder === 'inbox' ? t('inbox.empty_inbox') :
                currentInboxFolder === 'sent' ? t('inbox.empty_sent') :
                    t('inbox.empty_archived');
            list.innerHTML = `<div class="text-center text-muted p-3">${emptyText}</div>`;
            return;
        }

        const user = AuthService.getUser();
        const userId = user?.id;

        messages.forEach(msg => {
            const item = document.createElement('div');
            const isUnread = !msg.read_at && currentInboxFolder === 'inbox';
            item.className = 'list-group-item list-group-item-action' + (isUnread ? ' fw-bold bg-light' : '');
            item.style.cursor = 'pointer';

            // Determine display name based on folder
            let displayName = '';
            if (currentInboxFolder === 'inbox') {
                displayName = t('inbox.message.from', { name: msg.sender_name || 'Unknown' });
            } else if (currentInboxFolder === 'sent') {
                displayName = t('inbox.message.to', { name: msg.recipient_name || 'Unknown' });
            } else {
                // Archived - show direction
                if (msg.from_id === userId) {
                    displayName = t('inbox.message.to', { name: msg.recipient_name || 'Unknown' });
                } else {
                    displayName = t('inbox.message.from', { name: msg.sender_name || 'Unknown' });
                }
            }

            // Build action buttons
            let actions = '';
            if (currentInboxFolder === 'inbox') {
                // Reply button for inbox messages
                actions += `<button class="btn btn-sm btn-outline-success me-1" onclick="event.stopPropagation(); replyToMessage(${msg.id}, '${escapeHtml(msg.sender_name)}', '${escapeHtml(msg.subject)}')" title="${t('inbox.message.reply') || 'Reply'}">↩️</button>`;
                if (msg.read_at) {
                    actions += `<button class="btn btn-sm btn-outline-secondary me-1" onclick="event.stopPropagation(); markMessageUnread(${msg.id})" title="${t('inbox.message.mark_unread')}">📩</button>`;
                } else {
                    actions += `<button class="btn btn-sm btn-outline-primary me-1" onclick="event.stopPropagation(); markMessageRead(${msg.id})" title="${t('inbox.message.mark_read')}">✅</button>`;
                }
                actions += `<button class="btn btn-sm btn-outline-secondary me-1" onclick="event.stopPropagation(); archiveMessage(${msg.id})" title="${t('inbox.message.archive')}">📁</button>`;
                actions += `<button class="btn btn-sm btn-outline-danger" onclick="event.stopPropagation(); deleteMessage(${msg.id})" title="${t('inbox.message.delete')}">🗑️</button>`;
            } else if (currentInboxFolder === 'sent') {
                actions += `<button class="btn btn-sm btn-outline-secondary me-1" onclick="event.stopPropagation(); archiveMessage(${msg.id})" title="${t('inbox.message.archive')}">📁</button>`;
                actions += `<button class="btn btn-sm btn-outline-danger" onclick="event.stopPropagation(); deleteMessage(${msg.id})" title="${t('inbox.message.delete')}">🗑️</button>`;
            } else {
                // Archived
                actions += `<button class="btn btn-sm btn-outline-primary me-1" onclick="event.stopPropagation(); unarchiveMessage(${msg.id})" title="${t('inbox.message.unarchive')}">↩️</button>`;
                actions += `<button class="btn btn-sm btn-outline-danger" onclick="event.stopPropagation(); deleteMessage(${msg.id})" title="${t('inbox.message.delete')}">🗑️</button>`;
            }

            // Status indicators
            let statusBadge = '';
            if (currentInboxFolder === 'inbox' && !msg.read_at) {
                statusBadge = `<span class="badge bg-primary ms-2">${t('inbox.message.badge_new')}</span>`;
            }
            if (msg.read_at && currentInboxFolder === 'inbox') {
                statusBadge = `<span class="badge bg-secondary ms-2">${t('inbox.message.badge_read')}</span>`;
            }

            item.innerHTML = `
                <div class="d-flex w-100 justify-content-between align-items-start">
                    <div class="form-check me-2 d-flex align-items-center" style="min-height: 40px;">
                        <input class="form-check-input message-checkbox" type="checkbox" 
                               data-message-id="${msg.id}" 
                               onclick="event.stopPropagation(); toggleMessageSelection(this, ${msg.id})">
                    </div>
                    <div class="flex-grow-1">
                        <div class="d-flex align-items-center mb-1">
                            <h6 class="mb-0">${escapeHtml(msg.subject)}${statusBadge}</h6>
                        </div>
                        <p class="mb-1 text-truncate message-preview" style="max-width: 500px;">${escapeHtml(msg.content)}</p>
                        <small class="text-muted">${displayName} • ${new Date(msg.sent_at).toLocaleString()}</small>
                        <div class="message-full-content d-none mt-2 p-2 bg-light rounded">
                            <p class="mb-0">${escapeHtml(msg.content)}</p>
                        </div>
                    </div>
                    <div class="ms-2 text-nowrap">
                        ${actions}
                    </div>
                </div>
            `;

            // Add click handler to expand/collapse message
            item.addEventListener('click', function (e) {
                // Don't expand if clicking on buttons
                if (e.target.tagName === 'BUTTON') return;

                const preview = this.querySelector('.message-preview');
                const fullContent = this.querySelector('.message-full-content');

                if (fullContent.classList.contains('d-none')) {
                    preview.classList.add('d-none');
                    fullContent.classList.remove('d-none');
                    // Mark as read when expanded (for inbox)
                    if (currentInboxFolder === 'inbox' && !msg.read_at) {
                        if (typeof window.markMessageRead === 'function') window.markMessageRead(msg.id);
                    }
                } else {
                    preview.classList.remove('d-none');
                    fullContent.classList.add('d-none');
                }
            });

            list.appendChild(item);
        });
    } catch (e) {
        console.error("Inbox load failed", e);
        list.innerHTML = '<div class="text-center text-danger">Failed to load messages.</div>';
    }
};

/**
 * Reply to a message - opens compose modal pre-filled
 */
window.replyToMessage = function (messageId, senderName, originalSubject) {
    // Open compose modal
    const composeModal = document.getElementById('composeModal');
    if (composeModal) {
        const modal = bootstrap.Modal.getOrCreateInstance(composeModal);
        modal.show();

        // Pre-fill subject with "Re:" prefix
        const subjectInput = document.getElementById('compose-subject');
        if (subjectInput) {
            const subject = originalSubject || '';
            subjectInput.value = subject.startsWith('Re:') ? subject : `Re: ${subject}`;
        }

        // Set search to find the original sender and auto-select
        const searchInput = document.getElementById('compose-search');
        if (searchInput && senderName) {
            searchInput.value = senderName;
            if (typeof window.filterRecipients === 'function') window.filterRecipients();
            // Auto-select first matching recipient after short delay for DOM update
            setTimeout(() => {
                const recipientList = document.getElementById('recipient-list');
                if (recipientList) {
                    const firstMatch = recipientList.querySelector('.list-group-item:not(.d-none)');
                    if (firstMatch) firstMatch.click();
                }
            }, 100);
        }
    }
};

/**
 * Mark a message as read
 */
window.markMessageRead = async function (messageId) {
    try {
        const token = AuthService.getToken();
        const res = await fetch(`/api/classroom/messages/${messageId}/read`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            if (typeof window.loadInbox === 'function') window.loadInbox();
            if (typeof window.updateUnreadBadge === 'function') window.updateUnreadBadge();
        }
    } catch (e) {
        console.error('Mark read failed:', e);
    }
};

/**
 * Mark a message as unread
 */
window.markMessageUnread = async function (messageId) {
    try {
        const token = AuthService.getToken();
        const res = await fetch(`/api/classroom/messages/${messageId}/unread`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            if (typeof window.loadInbox === 'function') window.loadInbox();
            if (typeof window.updateUnreadBadge === 'function') window.updateUnreadBadge();
        }
    } catch (e) {
        console.error('Mark unread failed:', e);
    }
};

/**
 * Archive a message
 */
window.archiveMessage = async function (messageId) {
    try {
        const token = AuthService.getToken();
        const res = await fetch(`/api/classroom/messages/${messageId}/archive`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            if (typeof window.loadInbox === 'function') window.loadInbox();
        }
    } catch (e) {
        console.error('Archive failed:', e);
    }
};

/**
 * Unarchive a message
 */
window.unarchiveMessage = async function (messageId) {
    try {
        const token = AuthService.getToken();
        const res = await fetch(`/api/classroom/messages/${messageId}/unarchive`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            if (typeof window.loadInbox === 'function') window.loadInbox();
        }
    } catch (e) {
        console.error('Unarchive failed:', e);
    }
};

/**
 * Delete a message permanently
 */
window.deleteMessage = async function (messageId) {
    const confirmed = await showConfirm(
        t('inbox.message.delete_confirm') || 'Delete this message?',
        t('inbox.message.delete_title') || 'Confirm Delete',
        t('common.buttons.delete') || 'Delete',
        t('common.buttons.cancel') || 'Cancel',
        true
    );
    if (!confirmed) return;

    try {
        const token = AuthService.getToken();
        const res = await fetch(`/api/classroom/messages/${messageId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            if (typeof window.loadInbox === 'function') window.loadInbox();
            if (typeof window.updateUnreadBadge === 'function') window.updateUnreadBadge();
        }
    } catch (e) {
        console.error('Delete failed:', e);
    }
};

/**
 * Update the unread count badge in the sidebar
 */
window.updateUnreadBadge = async function updateUnreadBadge() {
    try {
        const token = AuthService.getToken();
        const res = await fetch('/api/classroom/messages/unread-count', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (res.ok) {
            const data = await res.json();
            const badge = document.getElementById('inbox-unread-badge');
            if (badge) {
                if (data.unread_count > 0) {
                    badge.textContent = data.unread_count;
                    badge.style.display = 'inline-block';
                } else {
                    badge.style.display = 'none';
                }
            }
        }
    } catch (e) {
        console.error('Failed to update unread badge:', e);
    }
};

/**
 * Toggle checkbox for a message
 */
window.toggleMessageSelection = function (checkbox, messageId) {
    if (checkbox.checked) {
        selectedMessageIds.add(messageId);
    } else {
        selectedMessageIds.delete(messageId);
    }
    updateBulkActionBar();
};

/**
 * Toggle select all messages
 */
window.toggleSelectAllMessages = function (checkbox) {
    const messageCheckboxes = document.querySelectorAll('.message-checkbox');
    messageCheckboxes.forEach(cb => {
        cb.checked = checkbox.checked;
        const messageId = parseInt(cb.dataset.messageId);
        if (checkbox.checked) {
            selectedMessageIds.add(messageId);
        } else {
            selectedMessageIds.delete(messageId);
        }
    });
    updateBulkActionBar();
};

/**
 * Filter inbox messages by search query
 */
window.filterInboxMessages = function (query) {
    const searchQuery = query ? query.toLowerCase().trim() : '';
    const inboxList = document.getElementById('inbox-list');
    if (!inboxList) return;

    const items = inboxList.querySelectorAll('.list-group-item');
    let visibleCount = 0;

    items.forEach(item => {
        const sender = item.querySelector('.fw-bold, .sender-name')?.textContent.toLowerCase() || '';
        const subject = item.querySelector('.text-body, .subject')?.textContent.toLowerCase() || '';
        const preview = item.querySelector('.text-muted, .preview')?.textContent.toLowerCase() || '';

        const matches = searchQuery === '' ||
            sender.includes(searchQuery) ||
            subject.includes(searchQuery) ||
            preview.includes(searchQuery);

        item.style.display = matches ? '' : 'none';
        if (matches) visibleCount++;
    });

    // Show empty state if no results
    if (visibleCount === 0 && searchQuery !== '') {
        const existing = inboxList.querySelector('.search-empty-state');
        if (!existing) {
            const empty = document.createElement('div');
            empty.className = 'text-center text-muted py-4 search-empty-state';
            empty.textContent = t('inbox.search_no_results') || 'No messages match your search';
            inboxList.appendChild(empty);
        }
    } else {
        const existing = inboxList.querySelector('.search-empty-state');
        if (existing) existing.remove();
    }
};

/**
 * Update bulk action bar visibility and count
 */
function updateBulkActionBar() {
    const countSpan = document.getElementById('inbox-selected-count');
    const archiveBtn = document.getElementById('bulk-archive-btn');
    const deleteBtn = document.getElementById('bulk-delete-btn');
    const count = selectedMessageIds.size;

    if (countSpan) {
        countSpan.textContent = `${count} ${t('inbox.bulk.selected') || 'selected'}`;
    }
    // Enable/disable bulk action buttons based on selection
    if (archiveBtn) archiveBtn.disabled = count === 0;
    if (deleteBtn) deleteBtn.disabled = count === 0;
}

/**
 * Bulk archive selected messages
 */
window.bulkArchiveMessages = async function () {
    if (selectedMessageIds.size === 0) return;

    const token = AuthService.getToken();
    const promises = Array.from(selectedMessageIds).map(id =>
        fetch(`/api/classroom/messages/${id}/archive`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        })
    );

    try {
        await Promise.all(promises);
        showToast(t('inbox.bulk.archived_success') || 'Messages archived', 'success');
        selectedMessageIds.clear();
        updateBulkActionBar();
        if (typeof window.loadInbox === 'function') window.loadInbox();
    } catch (e) {
        console.error('Bulk archive failed:', e);
        showToast(t('inbox.bulk.error') || 'Error archiving messages', 'danger');
    }
};

/**
 * Bulk delete selected messages
 */
window.bulkDeleteMessages = async function () {
    if (selectedMessageIds.size === 0) return;

    const confirmed = await showConfirm(
        t('inbox.bulk.delete_confirm') || 'Delete selected messages?',
        t('inbox.bulk.delete_title') || 'Confirm Bulk Delete',
        t('common.buttons.delete') || 'Delete',
        t('common.buttons.cancel') || 'Cancel',
        true
    );
    if (!confirmed) return;

    const token = AuthService.getToken();
    const promises = Array.from(selectedMessageIds).map(id =>
        fetch(`/api/classroom/messages/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        })
    );

    try {
        await Promise.all(promises);
        showToast(t('inbox.bulk.deleted_success') || 'Messages deleted', 'success');
        selectedMessageIds.clear();
        updateBulkActionBar();
        if (typeof window.loadInbox === 'function') window.loadInbox();
        if (typeof window.updateUnreadBadge === 'function') window.updateUnreadBadge();
    } catch (e) {
        console.error('Bulk delete failed:', e);
        showToast(t('inbox.bulk.error') || 'Error deleting messages', 'danger');
    }
};

// Auto-initialize unread badge when DOM is ready
// This ensures the badge is updated even when loaded as ES module
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        if (typeof window.updateUnreadBadge === 'function') window.updateUnreadBadge();
    });
} else {
    // DOM already loaded
    if (typeof window.updateUnreadBadge === 'function') window.updateUnreadBadge();
}
