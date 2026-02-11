/**
 * Toast Notification Utility
 * 
 * Provides non-blocking toast notifications as a replacement for blocking alert() dialogs.
 * Uses Bootstrap toast components for consistent styling.
 * 
 * @module toast
 */

/**
 * Display a toast notification message.
 * 
 * @param {string} message - The message to display in the toast.
 * @param {string} [type='info'] - The type of toast: 'success', 'danger', 'warning', or 'info'.
 * @param {number} [delay=3000] - Auto-dismiss delay in milliseconds.
 * 
 * @example
 * showToast('Settings saved successfully!', 'success');
 * showToast('Network error occurred', 'danger');
 * showToast('Please fill all required fields', 'warning');
 */
function showToast(message, type = 'info', delay = 3000) {
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

    const toast = bootstrap.Toast.getOrCreateInstance(toastEl, { delay: delay });
    toast.show();

    toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove(), { once: true });
}

/**
 * Display a confirmation modal dialog.
 * 
 * @param {string} message - The confirmation message to display.
 * @param {string} [title='Confirm'] - The modal title.
 * @param {string} [confirmText='Confirm'] - Text for the confirm button.
 * @param {string} [cancelText='Cancel'] - Text for the cancel button.
 * @param {boolean} [isDanger=false] - If true, uses danger styling for confirm button.
 * @returns {Promise<boolean>} - Resolves to true if confirmed, false if cancelled.
 * 
 * @example
 * const confirmed = await showConfirm('Delete this item?', 'Confirm Delete', 'Delete', 'Cancel', true);
 * if (confirmed) {
 *     deleteItem();
 * }
 */
function showConfirm(message, title = 'Confirm', confirmText = 'Confirm', cancelText = 'Cancel', isDanger = false) {
    return new Promise((resolve) => {
        // Create modal element
        const modalId = 'confirm-modal-' + Date.now();
        const modalEl = document.createElement('div');
        modalEl.className = 'modal fade';
        modalEl.id = modalId;
        modalEl.tabIndex = -1;
        modalEl.setAttribute('aria-labelledby', modalId + '-label');
        modalEl.setAttribute('aria-hidden', 'true');

        const confirmBtnClass = isDanger ? 'btn-danger' : 'btn-primary';

        modalEl.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="${modalId}-label">${title}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        ${message}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">${cancelText}</button>
                        <button type="button" class="btn ${confirmBtnClass}" id="${modalId}-confirm">${confirmText}</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modalEl);

        const modal = new bootstrap.Modal(modalEl);
        const confirmBtn = modalEl.querySelector(`#${modalId}-confirm`);

        // Handle confirm
        confirmBtn.addEventListener('click', () => {
            modal.hide();
            resolve(true);
        });

        // Handle cancel/dismiss
        modalEl.addEventListener('hidden.bs.modal', () => {
            modalEl.remove();
            resolve(false);
        }, { once: true });

        modal.show();
    });
}

// Make available globally
window.showToast = showToast;
window.showConfirm = showConfirm;

/**
 * Display an input prompt modal dialog.
 * 
 * @param {string} message - The message/label to display.
 * @param {string} [defaultValue=''] - Default value for the input.
 * @param {string} [title='Input Required'] - The modal title.
 * @param {boolean} [isMultiline=false] - If true, renders a textarea instead of input.
 * @returns {Promise<string|null>} - Resolves to the input value if submitted, or null if cancelled.
 * 
 * @example
 * const name = await showPrompt('Enter your name:', 'Guest', 'Welcome');
 * if (name) console.log(name);
 */
function showPrompt(message, defaultValue = '', title = 'Input Required', isMultiline = false) {
    return new Promise((resolve) => {
        // Create modal element
        const modalId = 'prompt-modal-' + Date.now();
        const modalEl = document.createElement('div');
        modalEl.className = 'modal fade';
        modalEl.id = modalId;
        modalEl.tabIndex = -1;
        modalEl.setAttribute('aria-labelledby', modalId + '-label');
        modalEl.setAttribute('aria-hidden', 'true');

        const inputHtml = isMultiline
            ? `<textarea class="form-control" id="${modalId}-input" rows="4">${defaultValue}</textarea>`
            : `<input type="text" class="form-control" id="${modalId}-input" value="${defaultValue}">`;

        modalEl.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="${modalId}-label">${title}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <label for="${modalId}-input" class="form-label">${message}</label>
                        ${inputHtml}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" id="${modalId}-submit">Submit</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modalEl);

        const modal = new bootstrap.Modal(modalEl);
        const submitBtn = modalEl.querySelector(`#${modalId}-submit`);
        const inputEl = modalEl.querySelector(`#${modalId}-input`);

        // Handle submit
        const submitHandler = () => {
            const val = inputEl.value;
            modal.hide();
            resolve(val);
        };

        submitBtn.addEventListener('click', submitHandler);

        // Handle enter key (only for single line inputs)
        if (!isMultiline) {
            inputEl.addEventListener('keyup', (e) => {
                if (e.key === 'Enter') submitHandler();
            });
        }

        // Auto-focus input
        modalEl.addEventListener('shown.bs.modal', () => {
            inputEl.focus();
            if (!isMultiline) inputEl.select();
        });

        // Handle cancel/dismiss
        modalEl.addEventListener('hidden.bs.modal', () => {
            modalEl.remove();
            resolve(null);
        }, { once: true });

        modal.show();
    });
}

window.showPrompt = showPrompt;

/**
 * Display a simple information modal with HTML content.
 * 
 * @param {string} title - The modal title.
 * @param {string} content - The HTML content to display.
 * @param {string} [btnText='Close'] - Text for the close button.
 * 
 * @example
 * showInfoModal('Statistics', '<strong>Score:</strong> 95%');
 */
function showInfoModal(title, content, btnText = 'Close') {
    // Create modal element
    const modalId = 'info-modal-' + Date.now();
    const modalEl = document.createElement('div');
    modalEl.className = 'modal fade';
    modalEl.id = modalId;
    modalEl.tabIndex = -1;
    modalEl.setAttribute('aria-labelledby', modalId + '-label');
    modalEl.setAttribute('aria-hidden', 'true');

    modalEl.innerHTML = `
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="${modalId}-label">${title}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    ${content}
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">${btnText}</button>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(modalEl);

    const modal = new bootstrap.Modal(modalEl);

    // thorough cleanup
    modalEl.addEventListener('hidden.bs.modal', () => {
        modalEl.remove();
    }, { once: true });

    modal.show();
}

window.showInfoModal = showInfoModal;
