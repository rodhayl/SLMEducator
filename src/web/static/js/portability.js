/* Preview-first portability UI. All permissions and import validation are server-owned. */
let exportSelection = null;
let importPackage = null;
let backupPreviewed = false;
const portableText = (key, fallback) => SLMClient.message(key, fallback);
function portabilityStatus(message, failed = false) {
    const status = document.getElementById('portability-status');
    status.textContent = message;
    status.className = 'alert ' + (failed ? 'alert-danger' : 'alert-info');
}
function showPortabilityPreview(id, preview) {
    const container = document.getElementById(id);
    container.replaceChildren();
    for (const key of ['audience', 'counts', 'includes', 'excludes', 'warnings']) {
        const value = preview[key];
        if (value === undefined) continue;
        const title = document.createElement('h3'); title.className = 'h6 mt-2';
        title.textContent = portableText(key, key);
        const detail = document.createElement('p');
        detail.textContent = Array.isArray(value) ? value.join('; ') : typeof value === 'object' ?
            Object.entries(value).map(([name, count]) => `${name}: ${count}`).join('; ') : String(value);
        container.append(title, detail);
    }
}
async function downloadPortable(url, filename, options = {}) {
    const response = await fetch(url, { ...options, headers: {
        Authorization: `Bearer ${AuthService.getToken()}`, ...options.headers
    }});
    if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new SLMClient.APIError(response.status, body?.detail);
    }
    const blob = await response.blob();
    const objectURL = URL.createObjectURL(blob);
    const link = document.createElement('a'); link.href = objectURL; link.download = filename;
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(objectURL), 1000);
    portabilityStatus(portableText('download_started', 'Download prepared. Store it securely.'));
}
function bindPortableAction(id, action) {
    const button = document.getElementById(id);
    button.addEventListener('click', async () => {
        if (button.disabled) return;
        button.disabled = true;
        try { await action(); } catch (error) { portabilityStatus(error.message, true); }
        finally { button.disabled = id === 'confirm-import' ? !importPackage : id === 'download-export' ? !exportSelection : id === 'download-backup' ? !backupPreviewed : false; }
    });
}
document.addEventListener('DOMContentLoaded', async () => {
    if (!AuthService.isAuthenticated()) { window.location.href = '/login.html'; return; }
    const role = AuthService.getRole();
    if (role === 'student') {
        document.querySelector('#export-audience option[value=teacher]').remove();
        document.getElementById('import-section').classList.add('d-none');
    }
    if (role === 'admin') document.getElementById('backup-section').classList.remove('d-none');
    try {
        const plans = await SLMClient.request('/api/study-plans/');
        plans.forEach(plan => document.getElementById('export-plan').append(new Option(plan.title, plan.id)));
    } catch (error) { portabilityStatus(error.message, true); }
    for (const id of ['export-plan', 'export-audience']) document.getElementById(id).addEventListener('change', () => {
        exportSelection = null; document.getElementById('download-export').disabled = true;
        document.getElementById('export-preview').replaceChildren();
    });
    document.getElementById('import-file').addEventListener('change', () => {
        importPackage = null; document.getElementById('confirm-import').disabled = true;
        document.getElementById('import-preview').replaceChildren();
    });
    bindPortableAction('preview-export', async () => {
        exportSelection = null;
        document.getElementById('download-export').disabled = true;
        const id = document.getElementById('export-plan').value;
        if (!id) throw new Error(portableText('choose_course', 'Choose a course first.'));
        const audience = document.getElementById('export-audience').value;
        const preview = await SLMClient.request(`/api/portability/plans/${id}/preview?audience=${audience}`);
        if (id !== document.getElementById('export-plan').value || audience !== document.getElementById('export-audience').value) return;
        showPortabilityPreview('export-preview', preview); exportSelection = { id, audience };
        document.getElementById('download-export').disabled = false;
    });
    bindPortableAction('download-export', async () => {
        if (!exportSelection) return;
        const { id, audience } = exportSelection;
        await downloadPortable(`/api/portability/plans/${id}/export?audience=${audience}`, `course-${id}-${audience}.json`);
    });
    bindPortableAction('preview-import', async () => {
        importPackage = null; document.getElementById('confirm-import').disabled = true;
        const file = document.getElementById('import-file').files[0];
        if (!file || file.size > 10 * 1024 * 1024) throw new Error(portableText('import_limit', 'Choose a JSON course file smaller than 10 MB.'));
        const candidate = JSON.parse(await file.text());
        const preview = await SLMClient.request('/api/portability/import/preview', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ package: candidate })
        });
        if (file !== document.getElementById('import-file').files[0]) return;
        showPortabilityPreview('import-preview', preview); importPackage = candidate;
        document.getElementById('confirm-import').disabled = false;
    });
    bindPortableAction('confirm-import', async () => {
        if (!importPackage) return;
        const result = await SLMClient.request('/api/portability/import', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ package: importPackage, confirm: true })
        });
        importPackage = null;
        portabilityStatus(portableText('imported', 'Imported as a new draft. Review before publishing.') + ` #${result.study_plan_id}`);
    });
    bindPortableAction('preview-backup', async () => {
        backupPreviewed = false; document.getElementById('download-backup').disabled = true;
        const preview = await SLMClient.request('/api/portability/backup/preview');
        showPortabilityPreview('backup-preview', preview); backupPreviewed = true;
        document.getElementById('download-backup').disabled = false;
    });
    bindPortableAction('download-backup', async () => {
        if (!backupPreviewed) return;
        await downloadPortable('/api/portability/backup', 'slmeducator-private-database.slmbackup', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ confirm: true })
        });
    });
});
