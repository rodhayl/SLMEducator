/* Preview-first portability UI. All permissions and import validation are server-owned. */
let exportSelection = null;
let importPackage = null;
let backupPreviewed = false;
let revisionSelection = null;
let portableOwner = null;
const portableFormats = {json:{type:'application/json',extension:'json'},html:{type:'text/html',extension:'html'},markdown:{type:'text/markdown',extension:'md'}};
const portableText = (key, fallback) => SLMClient.message(key, fallback);
function portabilityStatus(message, failed = false) {
    const status = document.getElementById('portability-status');
    status.textContent = message;
    status.className = 'alert ' + (failed ? 'alert-danger' : 'alert-info');
}
function showPortabilityPreview(id, preview) {
    const container = document.getElementById(id);
    container.replaceChildren();
    for (const key of ['audience', 'format', 'package_version', 'compatible_versions', 'counts', 'includes', 'excludes', 'warnings', 'import_effect', 'validation']) {
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
async function downloadPortable(url, filename, options = {}, expectedType = null) {
    const response = await fetch(url, { ...options, headers: {
        Authorization: `Bearer ${AuthService.getToken()}`, ...options.headers
    }});
    if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new SLMClient.APIError(response.status, body?.detail);
    }
    if (portableOwner && portableOwner !== SLMClient.account()) throw new Error(portableText('account_changed', 'The signed-in account changed. Reload before continuing.'));
    const contentType = response.headers?.get('content-type')?.split(';')[0];
    if (expectedType && contentType !== expectedType) throw new Error(portableText('export_format_unavailable', 'The server did not return the selected format. Choose JSON or retry after updating the server.'));
    const blob = await response.blob();
    if (portableOwner && portableOwner !== SLMClient.account()) throw new Error(portableText('account_changed', 'The signed-in account changed. Reload before continuing.'));
    const objectURL = URL.createObjectURL(blob);
    const link = document.createElement('a'); link.href = objectURL; link.download = filename;
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(objectURL), 1000);
    portabilityStatus(portableText('download_started', 'Download prepared. Store it securely.'));
}
function bindPortableAction(id, action) {
    const button = document.getElementById(id);
    button.addEventListener('click', async () => {
        if (button.disabled || portableOwner !== SLMClient.account()) return;
        button.disabled = true;
        try { await action(); } catch (error) { portabilityStatus(error.message, true); }
        finally { button.disabled = id === 'confirm-import' ? !importPackage : id === 'download-export' ? !exportSelection : id === 'download-backup' ? !backupPreviewed : id === 'confirm-revision' ? !revisionSelection : false; }
    });
}
async function initializePortability() {
    if (!AuthService.isAuthenticated()) { window.location.href = AuthService.loginUrl(); return; }
    portableOwner = SLMClient.account();
    const role = AuthService.getRole();
    document.querySelectorAll('[data-portability-purpose]').forEach(button => {
        const purpose = button.dataset.portabilityPurpose;
        button.hidden = role === 'student' ? purpose !== 'handout' : purpose === 'backup' && role !== 'admin';
        button.onclick = () => choosePortabilityPurpose(purpose);
    });
    if (role === 'student') {
        document.querySelector('#export-audience option[value=teacher]').remove();
        document.getElementById('import-section').classList.add('d-none');
    }
    if (role === 'admin') document.getElementById('backup-section').classList.remove('d-none');
    try {
        const plans = await SLMClient.request('/api/study-plans/');
        if (portableOwner !== SLMClient.account()) return;
        for (const id of ['export-plan','revision-plan']) { const select=document.getElementById(id);select.replaceChildren();plans.forEach(plan => select.append(new Option(plan.title, plan.id))); }
    } catch (error) { portabilityStatus(error.message, true); }
    for (const id of ['export-plan', 'export-audience', 'export-format']) document.getElementById(id).addEventListener('change', () => {
        exportSelection = null; document.getElementById('download-export').disabled = true;
        document.getElementById('export-preview').replaceChildren();
        updateExportFormats();
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
        const format = document.getElementById('export-format').value;
        const preview = await SLMClient.request(`/api/portability/plans/${id}/preview?audience=${audience}&format=${format}`);
        if (portableOwner !== SLMClient.account() || id !== document.getElementById('export-plan').value || audience !== document.getElementById('export-audience').value || format !== document.getElementById('export-format').value) return;
        showPortabilityPreview('export-preview', preview); exportSelection = { id, audience, format };
        portabilityStep('portable_step_confirm', 'Preview checked. Confirm the action when you are ready.');
        document.getElementById('download-export').disabled = false;
    });
    bindPortableAction('download-export', async () => {
        if (!exportSelection) return;
        const { id, audience, format } = exportSelection;
        await downloadPortable(`/api/portability/plans/${id}/export?audience=${audience}&format=${format}`, `course-${id}-${audience}.${portableFormats[format].extension}`, {}, portableFormats[format].type);
    });
    bindPortableAction('preview-import', async () => {
        importPackage = null; document.getElementById('confirm-import').disabled = true;
        const file = document.getElementById('import-file').files[0];
        if (!file || file.size > 10 * 1024 * 1024) throw new Error(portableText('import_limit', 'Choose a JSON course file smaller than 10 MB.'));
        let candidate;
        try { candidate = JSON.parse(await file.text()); } catch { throw new Error(portableText('invalid_course_json', 'The selected file is not valid course JSON.')); }
        const preview = await SLMClient.request('/api/portability/import/preview', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ package: candidate })
        });
        if (portableOwner !== SLMClient.account() || file !== document.getElementById('import-file').files[0]) return;
        showPortabilityPreview('import-preview', preview); importPackage = candidate;
        document.getElementById('confirm-import').disabled = false;
    });
    bindPortableAction('confirm-import', async () => {
        if (!importPackage) return;
        const result = await SLMClient.request('/api/portability/import', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ package: importPackage, confirm: true })
        });
        if (!Number.isInteger(result?.study_plan_id) || result.status !== 'draft') throw new Error(portableText('import_unconfirmed', 'The server did not confirm the new draft. Check your library before retrying.'));
        importPackage = null;
        const link = document.createElement('a');link.href = `/study_plan_builder.html?id=${result.study_plan_id}`;link.textContent = portableText('review_import', 'Open imported draft for review');document.getElementById('import-result').replaceChildren(link);
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
    document.getElementById('revision-plan').onchange = () => { revisionSelection = null; document.getElementById('confirm-revision').disabled = true; document.getElementById('revision-preview').replaceChildren(); };
    bindPortableAction('preview-revision', async () => {
        revisionSelection = null; document.getElementById('confirm-revision').disabled = true;
        const id = document.getElementById('revision-plan').value;
        if (!id) throw new Error(portableText('choose_course', 'Choose a course first.'));
        const plan = await SLMClient.request(`/api/study-plans/${id}/tree`);
        if (id !== document.getElementById('revision-plan').value || portableOwner !== SLMClient.account()) return;
        showPortabilityPreview('revision-preview', {counts:{contents:plan.contents?.length || 0},includes:[plan.title],warnings:[portableText('revision_explanation', 'A separate private draft is created. Review it before publishing.')]});
        revisionSelection = id; document.getElementById('confirm-revision').disabled = false;
    });
    bindPortableAction('confirm-revision', async () => {
        if (!revisionSelection) return;
        const result = await SLMClient.request(`/api/study-plans/${revisionSelection}/copy`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reason:'revision'})});
        if (!Number.isInteger(result?.id) || result.status !== 'draft') throw new Error(portableText('import_unconfirmed', 'The server did not confirm the new draft. Check your library before retrying.'));
        revisionSelection = null;
        const link=document.createElement('a');link.href=`/study_plan_builder.html?id=${result.id}`;link.textContent=portableText('review_import', 'Open imported draft for review');document.getElementById('revision-preview').append(link);
        portabilityStatus(portableText('imported', 'Created a new draft. Review before publishing.'));
    });
    choosePortabilityPurpose('handout');
}
function portabilityStep(key, fallback) { const step = document.getElementById('portability-step');step.dataset.i18n = 'recovery.' + key;step.textContent = portableText(key, fallback); }
function updateExportFormats() {
    const teacher = document.getElementById('export-audience').value === 'teacher';
    const select = document.getElementById('export-format');
    select.querySelectorAll('option').forEach(option => { option.disabled = teacher && option.value !== 'json'; });
    if (teacher) select.value = 'json';
    document.getElementById('export-purpose-warning').textContent = teacher ? portableText('teacher_package_warning', 'Teacher JSON contains answer keys. Share only with the intended teacher; never with learners.') : portableText('handout_warning', 'A learner handout is a reading copy. It cannot restore an editable teacher course; media and external files are excluded.');
}
window.choosePortabilityPurpose = function choosePortabilityPurpose(purpose) {
    const role = AuthService.getRole();
    if (!['handout','teacher','import','revision','backup'].includes(purpose) || (role==='student' && purpose!=='handout') || (purpose==='backup' && role!=='admin')) return;
    document.querySelectorAll('[data-portability-purpose]').forEach(button => { const active=button.dataset.portabilityPurpose===purpose;button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active)); });
    const target=['handout','teacher'].includes(purpose)?'export':purpose;
    for(const section of ['export','import','revision','backup']) document.getElementById(section+'-section').classList.toggle('d-none',section!==target);
    document.getElementById('export-audience').value=purpose==='teacher'?'teacher':'learner';
    document.getElementById('export-format').value=purpose==='teacher'?'json':'html';
    exportSelection=null;importPackage=null;revisionSelection=null;backupPreviewed=false;
    ['download-export','confirm-import','confirm-revision','download-backup'].forEach(id=>{document.getElementById(id).disabled=true;});
    ['export-preview','import-preview','revision-preview','backup-preview'].forEach(id=>document.getElementById(id).replaceChildren());
    updateExportFormats();portabilityStep('portable_step_choose','1. Choose a purpose and course. 2. Review the preview. 3. Confirm the action.');
};
document.addEventListener('DOMContentLoaded', initializePortability);
