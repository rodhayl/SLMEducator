import { AuthService } from './auth.js';

if (!AuthService.isAuthenticated()) {
    window.location.href = '/login.html';
}

const user = AuthService.getUser();
const role = AuthService.getRole();
if (role && role !== 'teacher' && role !== 'admin') {
    window.location.href = '/dashboard.html';
}

// I18n helper (fallback if I18n not available)
const t = (key, params = {}) => {
    if (typeof I18n !== 'undefined' && I18n.t) {
        return I18n.t(key, params);
    }
    // Fallback messages
    const fallbacks = {
        'study_plan.title_required': 'Title is required',
        'study_plan.created': 'Study Plan Created!',
        'study_plan.error_save': `Failed to save: ${params.error || ''}`,
        'study_plan.error_network': 'Network Error'
    };
    return fallbacks[key] || key;
};

let availableContent = [];
let phaseSortable = null;

// Init
document.addEventListener('DOMContentLoaded', async () => {
    await loadContent();
    if (!await loadSavedPlan()) addPhase(); // Add initial phase only for a new plan.

    // Initialize Sortable for phase reordering (33.1)
    const phasesContainer = document.getElementById('phases-container');
    if (!savedPlanId && phasesContainer && typeof Sortable !== 'undefined') {
        phaseSortable = new Sortable(phasesContainer, {
            animation: 150,
            handle: '.drag-handle',
            ghostClass: 'bg-warning-subtle',
            onEnd: function () {
                console.log('Phases reordered');
            }
        });
    }
});



async function loadContent() {
    try {
        const token = AuthService.getToken();
        const res = await fetch('/api/content/', { headers: { 'Authorization': `Bearer ${token}` } });
        if (!res.ok) throw new Error('Unable to load content');
        availableContent = await res.json();
        renderContentList(availableContent);
    } catch (e) {
        console.error("Failed to load content", e);
        renderContentList([]);
    }
}

function renderContentList(items) {
    const container = document.getElementById('source-content-list');
    if (items.length === 0) {
        container.innerHTML = `
            <div class="empty-state-visual p-3" style="min-height: 150px;">
                <div class="empty-state-icon" style="font-size: 1.5rem;">📭</div>
                <h6 class="empty-state-title" style="font-size: 1rem;">Library Empty</h6>
                <p class="empty-state-text" style="font-size: 0.8rem;">No content found to add.</p>
            </div>
        `;
        return;
    }
    container.replaceChildren();
    items.forEach(item => {
        const row = document.createElement('div');
        row.className = 'content-item-draggable'; row.draggable = true;
        row.dataset.id = item.id; row.dataset.title = item.title; row.dataset.type = item.content_type;
        row.ondragstart = window.drag;
        const title = document.createElement('strong'); title.textContent = item.title;
        const detail = document.createElement('small'); detail.className = 'd-block text-secondary';
        detail.textContent = item.content_type;
        row.append(title, detail); container.append(row);
    });
}

window.allowDrop = event => event.preventDefault();
window.drag = event => event.dataTransfer.setData('id', event.currentTarget.dataset.id);
window.drop = event => {
    event.preventDefault();
    if (savedPlanId) return;
    const area = event.target.closest('.phase-content-area');
    const item = availableContent.find(item => String(item.id) === event.dataTransfer.getData('id'));
    if (area && item) appendContent(area, item);
};
const builderMessage = (key, fallback) => SLMClient.message(key, fallback);
function moveElement(element, direction) {
    if (savedPlanId) return;
    const sibling = direction < 0 ? element.previousElementSibling : element.nextElementSibling;
    if (!sibling) return;
    if (direction < 0) element.parentNode.insertBefore(element, sibling);
    else element.parentNode.insertBefore(sibling, element);
}
function moveButton(element, direction, label) {
    const button = document.createElement('button'); button.type = 'button';
    button.className = 'btn btn-sm btn-outline-secondary';
    button.textContent = direction < 0 ? '↑' : '↓';
    button.setAttribute('aria-label', label);
    button.onclick = () => { moveElement(element, direction); button.focus(); };
    return button;
}
function appendContent(area, item) {
    area.querySelector('small')?.remove();
    const row = document.createElement('div');
    row.className = 'content-item-draggable bg-light'; row.dataset.contentId = item.id;
    const title = document.createElement('span'); title.textContent = `[${item.content_type}] ${item.title}`;
    const controls = document.createElement('div'); controls.className = 'btn-group ms-2';
    controls.append(moveButton(row, -1, builderMessage('move_up', 'Move up')),
        moveButton(row, 1, builderMessage('move_down', 'Move down')));
    const remove = document.createElement('button'); remove.type = 'button';
    remove.className = 'btn btn-sm btn-outline-danger'; remove.textContent = builderMessage('remove', 'Remove');
    remove.onclick = () => { const card = row.closest('.phase-card'); row.remove(); card.querySelector('select')?.focus(); };
    controls.append(remove); row.append(title, controls); area.append(row);
}

// PHASE MANAGEMENT
window.addPhase = () => {
    const clone = document.getElementById('phase-template').content.cloneNode(true);
    const card = clone.querySelector('.phase-card');
    card.querySelector('.phase-name-input').setAttribute('aria-label', builderMessage('phase_name', 'Phase name'));
    const moves = document.createElement('div'); moves.className = 'btn-group mb-2';
    moves.append(moveButton(card, -1, builderMessage('move_phase_up', 'Move phase up')),
        moveButton(card, 1, builderMessage('move_phase_down', 'Move phase down')));
    const picker = document.createElement('select'); picker.className = 'form-select mb-2';
    picker.setAttribute('aria-label', builderMessage('choose_content', 'Choose content for this phase'));
    availableContent.forEach(item => { const option = new Option(item.title, item.id); picker.append(option); });
    const add = document.createElement('button'); add.type = 'button';
    add.className = 'btn btn-sm btn-outline-primary mb-2';
    add.textContent = builderMessage('add_content', 'Add selected content');
    add.onclick = () => {
        const item = availableContent.find(item => String(item.id) === picker.value);
        if (item) appendContent(card.querySelector('.phase-content-area'), item);
    };
    card.append(moves, picker, add);
    document.getElementById('phases-container').append(clone);
};
window.removePhase = button => {
    button.closest('.phase-card').remove();
    document.getElementById('add-phase-btn')?.focus();
};
document.getElementById('content-search').addEventListener('input', event => {
    renderContentList(availableContent.filter(item => item.title.toLocaleLowerCase().includes(event.target.value.toLocaleLowerCase())));
});

// SAVE
let savingPlan = false;
let savedPlanId = null;
window.saveStudyPlan = async () => {
    if (savingPlan || savedPlanId) return;
    const title = document.getElementById('plan-title').value;
    const description = document.getElementById('plan-description').value;
    const isPublic = document.getElementById('plan-public').checked;

    if (!title) { showToast(t('study_plan.title_required'), 'warning'); return; }

    const phases = [];
    const phaseCards = document.querySelectorAll('.phase-card');

    phaseCards.forEach((card, index) => {
        const nameInput = card.querySelector('input[type="text"]');
        const contentIds = Array.from(card.querySelectorAll('[data-content-id]')).map(el => parseInt(el.dataset.contentId));

        phases.push({
            name: nameInput.value || `Phase ${index + 1}`,
            content_ids: contentIds
        });
    });

    const payload = {
        title,
        description,
        is_public: isPublic,
        phases: phases // Helper JSON
    };

    savingPlan = true;
    try {
        const token = AuthService.getToken();
        const res = await fetch('/api/study-plans', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            const plan = await res.json();
            savedPlanId = plan.id;
            history.replaceState(null, '', `study_plan_builder.html?id=${plan.id}`);
            document.getElementById('plan-workflow').classList.remove('d-none');
            lockSavedPlan();
            showToast(t('study_plan.created'), 'success', 2000);
        } else {
            const err = await res.json();
            showToast(t('study_plan.error_save', { error: JSON.stringify(err) }), 'danger');
        }
    } catch (e) {
        showToast(t('study_plan.error_network'), 'danger');
    } finally { savingPlan = false; }
}

window.planWorkflow = async action => {
    if (!savedPlanId) return;
    try {
        if (action === 'publish' && !await showConfirm(builderMessage('publish_course_confirm', 'Publish this reviewed course for authorized learners?'))) return;
        await SLMClient.request(`/api/study-plans/${savedPlanId}/workflow`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action, is_public: document.getElementById('plan-public').checked })
        });
        showToast(builderMessage(action === 'publish' ? 'published' : 'reviewed', action === 'publish' ? 'Published successfully.' : 'Review recorded. You can publish when ready.'), 'success');
    } catch (error) { showToast(error.message, 'danger'); }
};

async function loadSavedPlan() {
    const id = new URLSearchParams(window.location.search).get('id');
    if (!id || !/^\d+$/.test(id)) return false;
    try {
        const plan = await SLMClient.request(`/api/study-plans/${id}/tree`);
        savedPlanId = plan.id;
        document.getElementById('plan-title').value = plan.title;
        document.getElementById('plan-description').value = plan.description || '';
        document.getElementById('plan-public').checked = plan.is_public;
        (plan.phases?.length ? plan.phases : [{ name: 'Course' }]).forEach((phase, index) => {
            addPhase();
            const card = document.getElementById('phases-container').lastElementChild;
            card.querySelector('.phase-name-input').value = phase.name || phase.title || `Phase ${index + 1}`;
            (plan.contents || []).filter(item => item.phase_index === index).sort((a,b) => a.order_index - b.order_index).forEach(item => appendContent(card.querySelector('.phase-content-area'), item));
        });
        document.getElementById('plan-workflow').classList.remove('d-none');
        lockSavedPlan();
        return true;
    } catch (error) { showToast(error.message, 'danger'); return true; }
}

function lockSavedPlan() {
    document.querySelectorAll('#phases-container input, #phases-container select, #phases-container button, #plan-title, #plan-description, #plan-public, #save-plan-btn, #add-phase-btn').forEach(control => { control.disabled = true; });
    phaseSortable?.option('disabled', true);
    document.querySelectorAll('[draggable]').forEach(item => { item.draggable = false; });
    document.querySelectorAll('.drag-handle').forEach(handle => { handle.hidden = true; });
}
