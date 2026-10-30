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

// Init
document.addEventListener('DOMContentLoaded', async () => {
    await loadContent();
    addPhase(); // Add initial phase

    // Initialize Sortable for phase reordering (33.1)
    const phasesContainer = document.getElementById('phases-container');
    if (phasesContainer && typeof Sortable !== 'undefined') {
        new Sortable(phasesContainer, {
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
    container.innerHTML = items.map(item => {
        const estimate = Number.isFinite(item.estimated_time_min)
            ? `${item.estimated_time_min}m`
            : 'N/A';
        return `
        <div class="content-item-draggable" draggable="true" ondragstart="drag(event)" 
             data-id="${item.id}" data-title="${item.title}" data-type="${item.content_type}">
            <div class="d-flex justify-content-between">
                <strong>${item.title}</strong>
                <span class="badge bg-info text-dark">${item.content_type}</span>
            </div>
            <small class="text-muted">Est: ${estimate}</small>
        </div>
    `;
    }).join('');
}

// DRAG AND DROP HANDLING
window.allowDrop = (ev) => {
    ev.preventDefault();
}

window.drag = (ev) => {
    // Store data: ID, Title, Type
    ev.dataTransfer.setData("id", ev.target.dataset.id);
    ev.dataTransfer.setData("title", ev.target.dataset.title);
    ev.dataTransfer.setData("type", ev.target.dataset.type);
}

window.drop = (ev) => {
    ev.preventDefault();
    const id = ev.dataTransfer.getData("id");
    const title = ev.dataTransfer.getData("title");
    const type = ev.dataTransfer.getData("type");

    // Find closest phase-content-area
    let area = ev.target;
    if (!area.classList.contains('phase-content-area')) {
        area = area.closest('.phase-content-area');
    }

    if (area) {
        // Clear placeholder if present
        const placeholder = area.querySelector('small');
        if (placeholder) placeholder.remove();

        // Check if already exists in this phase to prevent dupes? 
        // Allowing dupes might be valid (review), but let's allow it.

        const div = document.createElement('div');
        div.className = 'content-item-draggable bg-light';
        div.dataset.contentId = id;
        div.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <span>[${type}] ${title}</span>
                <button class="btn btn-sm text-danger" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;
        area.appendChild(div);
    }
}

// PHASE MANAGEMENT
window.addPhase = () => {
    const template = document.getElementById('phase-template');
    const clone = template.content.cloneNode(true);
    document.getElementById('phases-container').appendChild(clone);
}

window.removePhase = (btn) => {
    btn.closest('.phase-card').remove();
}

// SAVE
window.saveStudyPlan = async () => {
    const title = document.getElementById('plan-title').value;
    const description = document.getElementById('plan-description').value;
    const isPublic = document.getElementById('plan-public').checked;

    if (!title) { showToast(t('study_plan.title_required'), 'warning'); return; }

    // Build Phases JSON
    // The backend expects `phases` list + `plan_contents` association.
    // Actually, StudyPlan model has `phases` (JSON) AND `plan_contents` (ManyToMany).
    // The `StudyPlanContent` association table has `phase_index`.
    // So we should structure the payload so the backend can create the associations.
    // If usage of `/api/study-plans` (POST) assumes just metadata, we might need a custom endpoint
    // or the endpoint handles the complexity.
    // Let's assume standard POST endpoint expects:
    // { title, description, is_public, phases: [ {name: "Week 1", items: [id1, id2]} ] }
    // AND the backend handles creating associations.

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

    try {
        const token = AuthService.getToken();
        const res = await fetch('/api/study-plans', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            showToast(t('study_plan.created'), 'success', 2000);
            setTimeout(() => {
                window.location.href = 'dashboard.html';
            }, 1500);
        } else {
            const err = await res.json();
            showToast(t('study_plan.error_save', { error: JSON.stringify(err) }), 'danger');
        }
    } catch (e) {
        showToast(t('study_plan.error_network'), 'danger');
    }
}
