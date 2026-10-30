/**
 * Assessment listing and management
 */
import { AuthService } from './auth.js';

export async function loadAssessments() {
    const list = document.getElementById('assessment-list');
    if (!list) return;

    try {
        const token = AuthService.getToken();
        const response = await fetch('/api/assessments/', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) throw new Error('Failed to load assessments');

        const assessments = await response.json();
        const role = AuthService.getRole();
        const isTeacher = role === 'teacher' || role === 'admin';

        if (assessments.length === 0) {
            list.innerHTML = `
                <div class="text-center text-muted p-4">
                    <p>No assessments available.</p>
                    ${isTeacher ? '<a href="assessment_builder.html" class="btn btn-primary">Create Assessment</a>' : ''}
                </div>
            `;
            return;
        }

        list.innerHTML = assessments.map(a => `
            <div class="card mb-3" data-assessment-id="${a.id}">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <h5 class="card-title">${escapeHtml(a.title)}</h5>
                            <p class="card-text">${escapeHtml(a.description) || 'No description'}</p>
                            <p class="text-muted"><small>${a.question_count || 0} Questions</small></p>
                        </div>
                        ${isTeacher ? `
                        <div class="dropdown">
                            <button class="btn btn-link text-muted" type="button" data-bs-toggle="dropdown">
                                ⋮
                            </button>
                            <ul class="dropdown-menu dropdown-menu-end">
                                <li><a class="dropdown-item" href="assessment_builder.html?id=${a.id}">✏️ Edit</a></li>
                                <li><a class="dropdown-item" href="#" onclick="viewAssessmentStats(${a.id}); return false;">📊 View Stats</a></li>
                                <li><hr class="dropdown-divider"></li>
                                <li><a class="dropdown-item text-danger" href="#" onclick="deleteAssessment(${a.id}); return false;">🗑️ Delete</a></li>
                            </ul>
                        </div>
                        ` : ''}
                    </div>
                    <div class="mt-2">
                        <button onclick="startAssessment(${a.id})" class="btn btn-primary btn-sm">▶️ Start Quiz</button>
                        ${isTeacher ? `
                        <button onclick="viewAssessmentStats(${a.id})" class="btn btn-outline-info btn-sm ms-2">📊 Stats</button>
                        <a href="assessment_builder.html?id=${a.id}" class="btn btn-outline-secondary btn-sm ms-2">✏️ Edit</a>
                        ` : ''}
                    </div>
                </div>
            </div>
        `).join('');

    } catch (e) {
        console.error(e);
        list.innerHTML = '<div class="alert alert-danger">Error loading assessments</div>';
    }
}

/**
 * Helper to escape HTML
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Start an assessment
 */
window.startAssessment = async (id) => {
    window.location.href = `assessment_taker.html?id=${id}`;
};

/**
 * View assessment statistics
 */
// I18n helper wrapper with fallback
function t(key, defaultMsg) {
    if (typeof I18n !== 'undefined' && I18n.t) {
        return I18n.t(key) || defaultMsg;
    }
    return defaultMsg;
}

window.loadAssessmentStats = async (id) => {
    try {
        const token = AuthService.getToken();
        const response = await fetch(`/api/assessments/${id}/stats`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            const errorData = await response.json();
            if (typeof showToast === 'function') {
                showToast(errorData.detail || 'Failed to load stats', 'danger');
            } else {
                console.error("Failed to load stats: " + errorData.detail);
            }
            return;
        }

        const stats = await response.json();

        // Show stats in a modal or alert
        const statsHtml = `
            <strong>Assessment Statistics</strong><br><br>
            Total Submissions: ${stats.total_submissions || 0}<br>
            Average Score: ${stats.average_score ? stats.average_score.toFixed(1) + '%' : 'N/A'}<br>
            Highest Score: ${stats.highest_score ? stats.highest_score + '%' : 'N/A'}<br>
            Lowest Score: ${stats.lowest_score ? stats.lowest_score + '%' : 'N/A'}<br>
            Pass Rate: ${stats.pass_rate ? stats.pass_rate.toFixed(1) + '%' : 'N/A'}
        `;

        // Try to use a modal if available, otherwise use alert
        const modalBody = document.getElementById('assessment-stats-body');
        const modal = document.getElementById('assessmentStatsModal');

        if (modal && modalBody) {
            modalBody.innerHTML = statsHtml;
            new bootstrap.Modal(modal).show();
        } else {
            // Fallback to simple modal
            if (typeof showInfoModal === 'function') {
                showInfoModal('Assessment Statistics', statsHtml);
            }
        }
    } catch (e) {
        console.error('Error loading stats:', e);
        if (typeof showToast === 'function') {
            showToast('Error loading assessment statistics', 'danger');
        }
    }
};

/**
 * Delete an assessment
 */
window.deleteAssessment = async (id) => {
    const confirmed = await showConfirm(
        'Are you sure you want to delete this assessment? This cannot be undone.',
        'Confirm Delete',
        'Delete',
        'Cancel',
        true
    );
    if (!confirmed) return;

    try {
        const token = AuthService.getToken();
        const response = await fetch(`/api/assessments/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            const errorData = await response.json();
            if (typeof showToast === 'function') {
                showToast(errorData.detail || 'Failed to delete assessment', 'danger');
            }
            return;
        }

        // Reload the list
        loadAssessments();

        if (typeof showToast === 'function') {
            showToast('Assessment deleted successfully', 'success');
        }
    } catch (e) {
        console.error('Error deleting assessment:', e);
        if (typeof showToast === 'function') {
            showToast('Error deleting assessment', 'danger');
        }
    }
};

// Initial Load
document.addEventListener('DOMContentLoaded', loadAssessments);
