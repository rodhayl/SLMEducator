/* DOM/contract regressions. These use jsdom, not a live browser or live API. */
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM } = require('jsdom');
const root = path.resolve(__dirname, '../../src/web');
const read = file => fs.readFileSync(path.join(root, file), 'utf8');
async function fixture(page = 'assessment_taker.html') {
    const dom = new JSDOM(read(page), { url: 'http://localhost/' + page + '?id=4&content_id=8', runScripts: 'outside-only', pretendToBeVisual: true });
    const window = dom.window;
    await new Promise(resolve => setImmediate(resolve)); // Let initial DOMContentLoaded finish before explicit loading.
    window.owner = 7;
    window.AuthService = { getUser: () => ({ id: window.owner }), getToken: () => 'synthetic-test-token', isAuthenticated: () => true, getRole: () => 'teacher' };
    window.I18n = { t: key => key };
    window.toasts = [];
    window.showToast = (...args) => window.toasts.push(args);
    window.eval(read('static/vendor/dompurify@3.4.16/purify.min.js'));
    window.eval(read('static/vendor/marked@15.0.12/marked.min.js'));
    window.eval(read('static/js/safe-render.js'));
    window.eval(read('static/js/learning-client.js'));
    return { dom, window };
}
const reply = (status, data) => ({ ok: status >= 200 && status < 300, status, json: async () => data });
const assessment = { id: 4, title: '<script>unsafe()</script>', description: 'Synthetic', time_limit_minutes: 30, questions: [
    { id: 10, question_text: '<img src=x onerror=unsafe()>', question_type: 'multiple_choice', points: 10, options: { choices: ['a" onclick="unsafe()', 'b'] } },
    { id: 11, question_text: 'Explain <svg/onload=unsafe()>', question_type: 'short_answer', points: 20 }
] };
async function loadedAssessment(status, result) {
    const context = await fixture();
    const w = context.window;
    w.requests = [];
    w.fetch = async (url, options) => {
        w.requests.push({ url, options });
        if (url.endsWith('/start')) return reply(200, { submission_id: 21, expires_at: new Date(Date.now() + 60000).toISOString() });
        if (url.endsWith('/submit')) return reply(status, result);
        return reply(200, assessment);
    };
    w.eval(read('static/js/assessment_taker.js'));
    await w.loadAssessment();
    return context;
}

test('maintained sanitizer blocks executable author/import/model markup and unsafe links', async () => {
    const { dom, window: w } = await fixture();
    const target = w.document.createElement('div');
    const attacks = [
        '<img src=x onerror="window.pwned=1">', '<script>window.pwned=1</script>',
        '<svg><g onload="window.pwned=1"></g></svg>', '<a href="javascript:alert(1)">bad</a>',
        '<a href="data:text/html,unsafe">bad</a>', '<iframe srcdoc="<script>unsafe()</script>"></iframe>',
        '<form id=AuthService><input name=getToken></form>', '<div style="background:url(https://tracker)">text</div>'
    ];
    for (const attack of attacks) {
        w.SLMRender.setMarkdown(target, attack);
        assert.equal(target.querySelector('script,img,svg,iframe,form,input,[style],[onerror],[onload]'), null);
        assert.equal(target.querySelector('[href^="javascript:"],[href^="data:"]'), null);
    }
    w.SLMRender.setMarkdown(target, '## Heading\n\n**Strong** and [source](https://example.org)');
    assert.equal(target.querySelector('h2').textContent, 'Heading');
    assert.equal(target.querySelector('strong').textContent, 'Strong');
    assert.equal(target.querySelector('a').rel, 'noopener noreferrer');
    delete w.DOMPurify;
    assert.equal(w.SLMRender.html('<script>x</script>'), '&lt;script&gt;x&lt;/script&gt;');
    dom.window.close();
});

test('checked API rejects every failed HTTP even with valid JSON', async () => {
    const { dom, window: w } = await fixture();
    for (const status of [401, 403, 422, 500]) {
        w.fetch = async () => reply(status, { detail: 'Synthetic rejected save' });
        await assert.rejects(w.SLMClient.request('/api/test'), error => error.status === status);
    }
    dom.window.close();
});

test('draft namespace separates accounts, resources and attempts; expired and legacy drafts are purged', async () => {
    const { dom, window: w } = await fixture();
    const drafts = w.SLMClient.drafts;
    assert.equal(drafts.write('assessment', 4, 21, { notes: 'private synthetic' }), true);
    assert.equal(drafts.read('assessment', 4, 22), null);
    w.owner = 8; assert.equal(drafts.read('assessment', 4, 21), null);
    w.owner = 7; assert.equal(drafts.read('assessment', 4, 21).notes, 'private synthetic');
    const key = w.localStorage.key(0); const expired = JSON.parse(w.localStorage.getItem(key));
    expired.expiresAt = Date.now() - 1; w.localStorage.setItem(key, JSON.stringify(expired));
    w.localStorage.setItem('assessment_progress_4', 'legacy'); drafts.prune();
    assert.equal(w.localStorage.length, 0);
    const original = w.Storage.prototype.setItem;
    w.Storage.prototype.setItem = () => { throw new Error('quota'); };
    assert.equal(drafts.write('notes', 8, 1, { notes: 'draft' }), false);
    w.Storage.prototype.setItem = original;
    dom.window.close();
});

test('assessment options/questions render literally with semantic labels and no injected elements', async () => {
    const { dom, window: w } = await loadedAssessment(200, {});
    assert.equal(w.document.querySelector('#questions-container img'), null);
    assert.equal(w.document.querySelector('#questions-container svg'), null);
    assert.equal(w.document.querySelector('input[name=q_10]').value, 'a" onclick="unsafe()');
    assert.equal(w.document.querySelector('input[name=q_10]').getAttribute('onclick'), null);
    assert.equal(w.document.querySelector('label').htmlFor, 'q_10_0');
    assert.equal(w.document.querySelector('textarea').getAttribute('aria-labelledby'), 'question-text-11');
    assert.match(w.document.getElementById('assessment-timer').textContent, /^00:|^01:/);
    dom.window.close();
});

for (const status of [401, 403, 422, 500]) test(`assessment HTTP ${status} keeps answers/draft and never reports success`, async () => {
    const { dom, window: w } = await loadedAssessment(status, { detail: 'Submission failed' });
    w.document.querySelector('textarea').value = 'Retain this answer';
    await w.submitAssessment();
    assert.equal(w.SLMClient.drafts.read('assessment', 4, 21).answers[1].response_text, 'Retain this answer');
    assert.equal(w.document.getElementById('results').classList.contains('d-none'), true);
    assert.equal(w.document.getElementById('submit-btn').disabled, false);
    assert.equal(w.requests.filter(request => request.url.includes('award-xp')).length, 0);
    w.owner = 8;
    await w.submitAssessment();
    assert.equal(w.SLMClient.drafts.read('assessment', 4, 21), null);
    assert.equal(w.requests.filter(request => request.url.endsWith('/submit')).length, 1);
    dom.window.close();
});

test('successful pending submission clears only its draft and does not invent final grade', async () => {
    const { dom, window: w } = await loadedAssessment(200, { submission_id: 21, status: 'ai_graded', score: null });
    await w.submitAssessment(); await w.submitAssessment();
    assert.equal(w.SLMClient.drafts.read('assessment', 4, 21), null);
    assert.match(w.document.getElementById('results').textContent, /Pending teacher review/);
    assert.doesNotMatch(w.document.getElementById('results').textContent, /Final score/);
    assert.equal(w.requests.filter(request => request.url.endsWith('/submit')).length, 1);
    assert.equal(w.document.activeElement.id, 'results');
    dom.window.close();
});

test('notes HTTP failure is not synced and restore takes returned server notes', async () => {
    const { dom, window: w } = await fixture('session_player.html');
    w.eval(read('static/js/session.js'));
    w.fetch = async url => {
        if (url === '/api/content/8') return reply(200, {title:'Synthetic lesson',content_data:'Hello'});
        if (url === '/api/learning/start') return reply(200, {id:30,notes:'Server source of truth'});
        return reply(200, []);
    };
    await w.initSession();
    assert.equal(w.document.getElementById('session-notes').value, 'Server source of truth');
    w.fetch = async () => reply(500, { detail: 'Synthetic error' });
    w.document.getElementById('session-notes').value = 'Unsynced draft';
    assert.equal(await w.saveNotesToLocal('Unsynced draft'), false);
    assert.match(w.document.getElementById('notes-save-status').textContent, /Server save failed/);
    assert.equal(w.SLMClient.drafts.read('notes', 8, 30).notes, 'Unsynced draft');
    w.fetch = async () => reply(200, {});
    assert.equal(await w.saveNotesToLocal('Unsynced draft'), true);
    assert.match(w.document.getElementById('notes-save-status').textContent, /saved to server/);
    assert.equal(w.SLMClient.drafts.read('notes', 8, 30), null);
    dom.window.close();
});

test('session choice Escape/backdrop dismissal resolves instead of hanging', async () => {
    const { dom, window: w } = await fixture('session_player.html');
    w.bootstrap = { Modal: { getOrCreateInstance: () => ({ show() {}, hide() {} }) } };
    w.eval(read('static/js/session.js'));
    const choice = w.showSessionChoiceModal({ notes: '<script>unsafe</script>', start_time: '2026-01-01' });
    w.document.getElementById('sessionChoiceModal').dispatchEvent(new w.Event('hidden.bs.modal'));
    assert.equal(await choice, 'cancel');
    assert.equal(w.document.querySelector('#prev-session-notes-preview script'), null);
    dom.window.close();
});

test('course generator reports partial durable-save failure and never creates duplicate success claims', async () => {
    const { dom, window: w } = await fixture('course_designer.html');
    w.eval(read('static/js/course_designer.js'));
    w.eval('currentConfig={subject:"Synthetic",grade_level:"adult"}; createdStudyPlanId=4;');
    w.fetch = async () => reply(200, { success: false, saved_content_ids: [1] });
    assert.equal(await w.generateAndSaveLesson({ title: '<img src=x onerror=unsafe()>' }, 0), false);
    assert.match(w.document.getElementById('gen-log').textContent, /Failed:/);
    assert.equal(w.document.querySelector('#gen-log img'), null);
    w.fetch = async () => reply(500, { detail: 'Shell not saved' });
    await assert.rejects(w.createStudyPlanShell());
    dom.window.close();
});

test('non-drag plan controls add and reorder literal content, retaining focus', async () => {
    const { dom, window: w } = await fixture('study_plan_builder.html');
    w.history.replaceState(null, '', '/study_plan_builder.html');
    w.fetch = async () => reply(200, [{ id: 1, title: '<img src=x onerror=unsafe()>', content_type: 'lesson' }, { id: 2, title: 'Second lesson', content_type: 'lesson' }]);
    w.eval(read('static/js/study_plan_builder.js').replace("import { AuthService } from './auth.js';", ''));
    await w.loadContent(); w.addPhase();
    const card = w.document.querySelector('.phase-card');
    const picker = card.querySelector('select');
    card.querySelector('button.btn-outline-primary').click();
    picker.value = '2'; card.querySelector('button.btn-outline-primary').click();
    assert.equal(card.querySelector('img'), null);
    const rows = card.querySelectorAll('[data-content-id]');
    rows[1].querySelector('button[aria-label="Move up"]').click();
    assert.equal(card.querySelector('[data-content-id]').dataset.contentId, '2');
    assert.equal(w.document.activeElement.getAttribute('aria-label'), 'Move up');
    w.addPhase();
    const second = w.document.querySelectorAll('.phase-card')[1];
    second.querySelector('button[aria-label="Move phase up"]').click();
    assert.equal(w.document.querySelector('.phase-card'), second);
    dom.window.close();
});

test('question authoring safely previews text and explicitly saves before publish', async () => {
    const { dom, window: w } = await fixture('assessment_builder.html');
    let preview = null;
    w.showInfoModal = (title, content) => { preview = content; };
    w.eval(read('static/js/assessment_builder.js'));
    w.addQuestionUI();
    w.document.getElementById('quiz-title').value = '<svg/onload=unsafe()>';
    w.document.querySelector('.question-text').value = '<img src=x onerror=unsafe()>';
    w.previewAssessment();
    assert.ok(preview.includes('&lt;img'));
    const requests = [];
    w.fetch = async (url, options) => { requests.push({url, options}); return reply(200, {id: 2}); };
    await w.saveAssessmentDraft();
    assert.equal(requests.length, 1);
    assert.equal(requests[0].url, '/api/assessments/');
    assert.equal(JSON.parse(requests[0].options.body).time_limit_minutes, null);
    assert.equal(JSON.parse(requests[0].options.body).max_attempts, 1);
    assert.equal(w.document.getElementById('publish-btn').disabled, false);
    assert.ok(!requests.some(request => request.url.endsWith('/publish')));
    dom.window.close();
});

test('practice requires independent answer and never treats text as executable or awards grades', async () => {
    const { dom, window: w } = await fixture('session_player.html');
    w.eval(read('static/js/practice.js'));
    const container = w.document.getElementById('session-content-body');
    w.SLMPractice.render(container, { question: '<img src=x onerror=unsafe()>', options: { A: 'One', B: '<svg/onload=unsafe()>' }, correct_answer: 'B', explanation: '<script>unsafe()</script>' });
    assert.equal(container.querySelector('img,svg,script'), null);
    const buttons = container.querySelectorAll('button');
    buttons[1].click();
    assert.match(container.querySelector('[role=status]').textContent, /own answer first/);
    container.querySelector('select').value = '<svg/onload=unsafe()>';
    buttons[1].click();
    assert.match(container.querySelector('[role=status]').textContent, /matches the answer key/);
    assert.match(container.querySelector('[role=status]').textContent, /not a final grade/);
    assert.equal(container.querySelector('img,svg,script'), null);
    dom.window.close();
});

test('source coverage preview exposes partial extraction without injecting source labels', async () => {
    const { dom, window: w } = await fixture('course_designer.html');
    w.eval(read('static/js/course_designer.js') + '\nsourceCoverage={coverage:"partial",truncated:true,char_count:12,unreadable_pages:[2],sections:[{reference:"<img src=x onerror=unsafe()>"}]}; renderSourceCoverage();');
    const preview = w.document.getElementById('source-coverage');
    assert.match(preview.textContent, /Partial source/);
    assert.match(preview.textContent, /Unreadable pages: 2/);
    assert.equal(preview.querySelector('img'), null);
    dom.window.close();
});

test('portability preview safely renders server values and failed download never creates a link', async () => {
    const { dom, window: w } = await fixture('portability.html');
    w.eval(read('static/js/portability.js'));
    w.showPortabilityPreview('export-preview', { audience: '<img src=x onerror=unsafe()>', includes: ['<svg/onload=unsafe()>'], excludes: ['private records'] });
    assert.equal(w.document.querySelector('#export-preview img,#export-preview svg'), null);
    w.fetch = async () => reply(403, { detail: 'Not allowed' });
    await assert.rejects(w.downloadPortable('/api/portability/backup', 'file.slmbackup'));
    assert.equal(w.document.querySelector('a[download]'), null);
    assert.equal(w.document.getElementById('download-export').disabled, true);
    assert.equal(w.document.getElementById('confirm-import').disabled, true);
    dom.window.close();
});


test('malformed successful HTTP response never clears the assessment draft', async () => {
    for (const response of [null, {}, {submission_id:99,status:'graded',score:10}, {submission_id:21,status:'draft'}]) {
        const { dom, window: w } = await loadedAssessment(200, response);
        w.document.querySelector('textarea').value = 'Keep on ambiguous server result';
        await w.submitAssessment();
        assert.equal(w.SLMClient.drafts.read('assessment', 4, 21).answers[1].response_text, 'Keep on ambiguous server result');
        assert.equal(w.document.getElementById('results').classList.contains('d-none'), true);
        assert.equal(w.document.getElementById('submit-btn').disabled, false);
        dom.window.close();
    }
});
