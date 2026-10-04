/** Assessment listing and read-only author preview. */
import { AuthService } from './auth.js';

const assessmentText = (key, fallback) => SLMClient.message(key, fallback);
const assessmentEscape = value => SLMRender.escape(value);
const assessmentManager = () => ['teacher', 'admin'].includes(AuthService.getRole());
let assessmentListing = null;

export async function loadAssessments() {
    const list = document.getElementById('assessment-list');
    if (!list) return;
    try {
        const assessments = await SLMClient.request('/api/assessments/');
        if (!Array.isArray(assessments)) throw new Error(assessmentText('assessment_load_failed', 'Could not load assessments. Please retry.'));
        assessmentListing = assessments;
        renderAssessmentListing();
    } catch (error) {
        list.textContent = error.message || assessmentText('assessment_load_failed', 'Could not load assessments. Please retry.');
        list.classList.add('text-danger');
    }
}

function renderAssessmentListing() {
    const list = document.getElementById('assessment-list');
    if (!list || !assessmentListing) return;
    const manager = assessmentManager();
    list.classList.remove('text-danger');
    list.innerHTML = assessmentListing.length ? assessmentListing.map(a => assessmentCard(a, manager)).join('') :
        `<p class="text-muted">${assessmentEscape(assessmentText('assessment_empty', 'No assessments available.'))}</p>`;
    const navigation = document.createElement('a');
    navigation.className = 'btn btn-outline-primary mb-3';
    navigation.href = manager ? 'assessment_builder.html' : 'assessment_history.html';
    navigation.textContent = manager ? assessmentText('assessment_create', 'Create assessment') : assessmentText('submission_history', 'My submissions and feedback');
    list.prepend(navigation);
    list.querySelectorAll('[data-assessment-action]').forEach(button => {
        button.onclick = () => {
            const id = Number(button.dataset.assessmentId);
            const actions = { preview: window.previewAssessment, stats: window.loadAssessmentStats, delete: window.deleteAssessment };
            actions[button.dataset.assessmentAction]?.(id);
        };
    });
}

function assessmentCard(assessment, manager) {
    const id = Number(assessment.id);
    if (!Number.isSafeInteger(id) || id <= 0) return '';
    const button = (action, label, style) => `<button type="button" data-assessment-action="${action}" data-assessment-id="${id}" class="btn ${style} btn-sm">${assessmentEscape(label)}</button>`;
    const authorActions = button('preview', assessmentText('assessment_preview', 'Preview'), 'btn-primary') +
        button('stats', assessmentText('assessment_stats', 'Statistics'), 'btn-outline-info') +
        `<a href="assessment_builder.html?id=${id}" class="btn btn-outline-secondary btn-sm">${assessmentEscape(assessmentText('assessment_edit', 'Edit'))}</a>` +
        button('delete', assessmentText('assessment_delete', 'Delete'), 'btn-outline-danger');
    const learnerActions = (assessment.is_published ? `<a href="assessment_taker.html?id=${id}" class="btn btn-primary btn-sm">${assessmentEscape(assessmentText('assessment_start', 'Start or resume quiz'))}</a>` : '') +
        `<a href="assessment_history.html?assessment_id=${id}" class="btn btn-outline-secondary btn-sm">${assessmentEscape(assessmentText('assessment_feedback', 'View submissions and feedback'))}</a>`;
    return `<article class="card mb-3" data-assessment-id="${id}"><div class="card-body">
        <h3 class="h5 card-title">${assessmentEscape(assessment.title)}</h3>
        <p class="card-text">${assessmentEscape(assessment.description || '')}</p>
        <p class="text-muted">${assessmentEscape(assessment.question_count ?? 0)} ${assessmentEscape(assessmentText('assessment_questions', 'questions'))} · ${assessmentEscape(assessmentText(assessment.is_published ? 'published_label' : 'draft_label', assessment.is_published ? 'Published' : 'Draft: review required'))}</p>
        <div class="d-flex flex-wrap gap-2">${manager ? authorActions : learnerActions}</div>
        </div></article>`;
}

window.startAssessment = id => {
    if (assessmentManager()) return window.previewAssessment(id);
    if (AuthService.getRole() === 'student' && Number.isSafeInteger(Number(id)) && Number(id) > 0) {
        window.location.href = `assessment_taker.html?id=${Number(id)}`;
    }
};

window.previewAssessment = async id => {
    if (!assessmentManager() || !Number.isSafeInteger(Number(id)) || Number(id) <= 0) return;
    try {
        const assessment = await SLMClient.request(`/api/assessments/${Number(id)}`);
        const questions = (assessment.questions || []).map((question, index) => {
            let choices = question.options?.choices || question.options?.options || question.options || [];
            if (!Array.isArray(choices)) choices = Object.values(choices);
            if (!choices.length && question.question_type === 'true_false') choices = ['True', 'False'];
            return `<h3>${index + 1}. ${assessmentEscape(question.question_text)}</h3>
                <p>${assessmentEscape(question.points)} ${assessmentEscape(assessmentText('assessment_points', 'points'))}</p>
                ${Array.isArray(choices) && choices.length ? `<ul>${choices.map(choice => `<li>${assessmentEscape(choice)}</li>`).join('')}</ul>` : ''}`;
        }).join('');
        showInfoModal(assessment.title, `<p>${assessmentEscape(assessmentText('assessment_preview_notice', 'Teacher preview. Viewing this assessment does not start or use an attempt.'))}</p>
            <p>${assessmentEscape(assessment.description || '')}</p>${questions}`, assessmentText('close', 'Close'));
    } catch (error) {
        showToast(error.message || assessmentText('assessment_load_failed', 'Could not load assessments. Please retry.'), 'danger');
    }
};

window.loadAssessmentStats = async id => {
    if (!assessmentManager()) return;
    try {
        const stats = await SLMClient.request(`/api/assessments/${Number(id)}/stats`);
        const percent = value => Number.isFinite(value) ? `${value.toFixed(1)}%` : '—';
        const rows = [
            [assessmentText('assessment_final_submissions', 'Final graded submissions'), stats.total_submissions ?? 0],
            [assessmentText('assessment_average', 'Average score'), percent(stats.average_score)],
            [assessmentText('assessment_highest', 'Highest score'), percent(stats.highest_score)],
            [assessmentText('assessment_lowest', 'Lowest score'), percent(stats.lowest_score)],
            [assessmentText('assessment_pass_rate', 'Pass rate'), percent(stats.pass_rate)]
        ];
        showInfoModal(assessmentText('assessment_stats', 'Statistics'), rows.map(([label, value]) =>
            `<p><strong>${assessmentEscape(label)}:</strong> ${assessmentEscape(value)}</p>`).join(''), assessmentText('close', 'Close'));
    } catch (error) {
        showToast(error.message || assessmentText('assessment_stats_failed', 'Could not load assessment statistics. Please retry.'), 'danger');
    }
};
// Keep older callers working while all rendered controls use the implemented callback.
window.viewAssessmentStats = window.loadAssessmentStats;

window.deleteAssessment = async id => {
    if (!assessmentManager()) return;
    const confirmed = await showConfirm(
        assessmentText('assessment_delete_confirm', 'Delete this assessment? This cannot be undone.'),
        assessmentText('assessment_delete', 'Delete assessment'),
        assessmentText('delete', 'Delete'), assessmentText('cancel', 'Cancel'), true);
    if (!confirmed) return;
    try {
        await SLMClient.request(`/api/assessments/${Number(id)}`, { method: 'DELETE' });
        await loadAssessments();
        showToast(assessmentText('assessment_deleted', 'Assessment deleted.'), 'success');
    } catch (error) {
        showToast(error.message || assessmentText('assessment_delete_failed', 'Could not delete assessment. Please retry.'), 'danger');
    }
};

document.addEventListener('DOMContentLoaded', loadAssessments);

document.addEventListener('i18n-loaded', renderAssessmentListing);
document.addEventListener('i18n-language-changed', renderAssessmentListing);
