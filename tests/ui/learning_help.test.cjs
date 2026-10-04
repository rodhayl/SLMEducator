/* Inline help behavior with synthetic HTTP responses; not live provider/browser acceptance. */
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM } = require('jsdom');
const web = path.resolve(__dirname, '../../src/web');
const read = file => fs.readFileSync(path.join(web, file), 'utf8');
const reply = (status, data) => ({ ok: status >= 200 && status < 300, status, json: async () => data });
const settle = async () => { await new Promise(resolve => setImmediate(resolve)); await new Promise(resolve => setImmediate(resolve)); };
const policy = mode => ({ mode, active_assessment_ids: [], scope: 'active_attempt', reason: null });
const source = (id = 8, version = 'revision-A') => ({ id, title: 'Synthetic lesson', type: 'lesson', source_version: version,
    content_data: 'Bounded lesson text', available_sections: [{ id: `content:${id}/section-1`, title: '<img src=x onerror=unsafe()> First', characters: 120 },
        { id: `content:${id}/section-2`, title: 'Later section', characters: 7000 }],
    references: [`content:${id}/section-1`], truncated: true, included_characters: 140, total_characters: 7140 });
const answer = (overrides = {}) => ({ response: '**Try the next step.** <img src=x onerror=unsafe()><script>unsafe()</script>',
    status: 'suggestion', source: source(), source_verified: false, assistance_policy: policy('explanations'), effective_assistance: 'hint', ...overrides });
async function fixture(t, options = {}) {
    const dom = new JSDOM('<h1 id="lesson" tabindex="-1">Lesson</h1><div id="help"></div>', {
        url: 'http://localhost/session_player.html?content_id=8&plan_id=4', runScripts: 'outside-only', pretendToBeVisual: true
    });
    t.after(() => dom.window.close()); const w = dom.window; w.owner = 7; w.role = 'student';
    w.AuthService = { getUser: () => ({ id: w.owner }), getRole: () => w.role, getToken: () => 'synthetic-token' };
    w.I18n = { t: key => key }; w.requests = [];
    w.respond = async url => reply(200, url.endsWith('assistance-policy') ? policy('explanations') : url.startsWith('/api/ai/context') ? { source: source(), source_verified: false } : answer());
    w.fetch = async (url, options = {}) => { w.requests.push({ url, options }); return w.respond(url, options); };
    for (const file of ['static/vendor/dompurify@3.4.16/purify.min.js', 'static/vendor/marked@15.0.12/marked.min.js', 'static/js/safe-render.js', 'static/js/learning-client.js', 'static/js/learning-help.js']) w.eval(read(file));
    w.host = w.document.getElementById('help'); w.get = name => w.host.querySelector(`[name="${name}"]`);
    w.api = w.SLMHelp.mount(w.host, { contentId: 8, studyPlanId: 4, sessionId: 30, contentTitle: 'Synthetic lesson', returnFocus: w.document.getElementById('lesson'), ...options });
    w.submit = async name => { w.get(name).closest('form').dispatchEvent(new w.Event('submit', { bubbles: true, cancelable: true })); await settle(); };
    w.post = url => w.requests.filter(request => request.url === url && request.options.method === 'POST');
    w.choose = (index, checked = true) => { const input = w.host.querySelectorAll('[type=checkbox]')[index]; input.checked = checked; input.dispatchEvent(new w.Event('change', { bubbles: true })); return input; };
    w.sendTeacher = async () => { w.get('subject').value = 'A lesson question'; w.get('description').value = 'I tried the first step.'; await w.submit('subject'); };
    return w;
}
test('help opens inline with labelled native controls, scoped sections, partial and unverified source', async t => {
    const w = await fixture(t); assert.equal(w.requests.length, 0);
    const controls = [...w.host.firstElementChild.children];
    assert.deepEqual(controls.map(button => button.textContent), ['Tutor', 'Ask my teacher']);
    assert.equal(w.host.querySelector('section').hidden, true);
    await w.api.open('tutor');
    assert.equal(w.requests.find(request => request.url.startsWith('/api/ai/context')).url, '/api/ai/context?content_id=8&study_plan_id=4&session_id=30');
    assert.match(w.host.textContent, /revision-A/); assert.match(w.host.textContent, /Partial source/); assert.match(w.host.textContent, /unverified/);
    assert.equal(w.host.querySelectorAll('[type=checkbox]').length, 2);
    assert.equal(w.host.querySelector('img,script'), null);
    assert.equal(w.document.activeElement, w.get('question'));
    assert.equal(w.get('question').closest('form').querySelector('[type=submit]').disabled, false);
    assert.equal([...w.host.querySelectorAll('input,select,textarea')].every(input => input.labels.length), true);
    w.get('question').value = 'Keep this question'; w.host.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    assert.equal(w.host.querySelector('section').hidden, true); assert.equal(w.document.activeElement.id, 'lesson');
    await w.api.open('tutor'); assert.equal(w.get('question').value, 'Keep this question');
    assert.equal(w.location.pathname, '/session_player.html');
});
test('tutor binds exact source version, session, selected sections and bounded conversation', async t => {
    const w = await fixture(t); await w.api.open('tutor');
    w.choose(1); w.get('assistance').value = 'explanation'; w.get('question').value = 'Help with the later section';
    await w.submit('question');
    const payload = JSON.parse(w.post('/api/ai/chat')[0].options.body);
    assert.match(payload.client_request_id, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    delete payload.client_request_id;
    assert.deepEqual(payload, { message: 'Help with the later section', content_id: 8, study_plan_id: 4,
        session_id: 30, assistance: 'explanation', section_ids: ['content:8/section-2'], source_version: 'revision-A', conversation_history: [] });
    assert.equal(w.host.querySelector('img,script'), null); assert.match(w.host.querySelector('[role=log]').textContent, /Source sections used: content:8\/section-1/);
    assert.equal(w.get('question').value, '');
    for (let index = 0; index < 6; index++) { w.get('question').value = `Next ${index}`; await w.submit('question'); }
    const last = JSON.parse(w.post('/api/ai/chat').at(-1).options.body);
    assert.equal(last.conversation_history.length, 10);
    assert.equal(last.conversation_history[0].role, 'user');
    assert.equal(w.host.querySelectorAll('[role=log] article').length, 7);
});
test('policy fails closed, retries without losing input, and only hints can be sent under hints-only policy', async t => {
    const w = await fixture(t); let state = 'error';
    w.respond = async url => url.endsWith('assistance-policy') ? reply(state === 'error' ? 500 : 200, state === 'error' ? { detail: 'Unavailable' } : policy(state)) :
        reply(200, url.startsWith('/api/ai/context') ? { source: source() } : answer({ assistance_policy: policy('hints_only') }));
    await w.api.open('tutor'); w.get('question').value = 'My question'; await w.submit('question');
    assert.equal(w.post('/api/ai/chat').length, 0); assert.match(w.host.textContent, /Context or policy could not be loaded/);
    state = 'hints_only'; w.host.querySelector('[data-i18n="help_panel.refresh"]').click(); await settle();
    assert.equal(w.get('question').value, 'My question');
    assert.equal(w.get('assistance').querySelector('[value=explanation]').disabled, true);
    w.get('assistance').value = 'explanation'; await w.submit('question');
    assert.equal(JSON.parse(w.post('/api/ai/chat')[0].options.body).assistance, 'hint');
    state = 'disabled'; w.host.querySelector('[data-i18n="help_panel.refresh"]').click(); await settle();
    w.get('question').value = 'Another question'; await w.submit('question');
    assert.equal(w.post('/api/ai/chat').length, 1); assert.match(w.host.textContent, /disabled AI help/);
    await w.api.open('teacher'); assert.equal(w.get('subject').closest('form').querySelector('[type=submit]').disabled, false);
});
for (const status of [401, 403, 500]) test(`tutor HTTP ${status} keeps the question and allows checked retry`, async t => {
    const w = await fixture(t); await w.api.open('tutor'); let fail = true;
    w.respond = async url => reply(url === '/api/ai/chat' && fail ? status : 200,
        url.endsWith('assistance-policy') ? policy('explanations') : url.startsWith('/api/ai/context') ? { source: source() } : fail ? { detail: 'Synthetic failure' } : answer());
    w.get('question').value = 'Keep my question'; await w.submit('question');
    assert.equal(w.get('question').value, 'Keep my question'); assert.equal(w.host.querySelector('[role=log]').children.length, 0);
    fail = false;
    if (status === 403) { w.host.querySelector('[data-i18n="help_panel.refresh"]').click(); await settle(); }
    await w.submit('question'); assert.equal(w.post('/api/ai/chat').length, 2); assert.equal(w.get('question').value, '');
});
for (const status of ['unavailable', 'invalid_response']) test(`provider ${status} preserves input and does not add a trusted answer`, async t => {
    const w = await fixture(t); await w.api.open('tutor');
    w.respond = async () => reply(200, answer({ status, response: 'Provider details' }));
    w.get('question').value = 'Retry this'; await w.submit('question');
    assert.equal(w.get('question').value, 'Retry this'); assert.equal(w.host.querySelector('[role=log]').children.length, 0);
    assert.match(w.host.textContent, /could not provide a usable suggestion/);
});
for (const change of ['section', 'close', 'context', 'owner', 'teacher']) test(`late tutor response is discarded after ${change} changes`, async t => {
    const w = await fixture(t); await w.api.open('tutor'); let finish;
    w.respond = async url => url === '/api/ai/chat' ? new Promise(resolve => { finish = resolve; }) : reply(200,
        url.endsWith('assistance-policy') ? policy('explanations') : { source: source(9, 'revision-B') });
    w.get('question').value = 'An old question'; await w.submit('question');
    const pending = w.post('/api/ai/chat')[0];
    if (change === 'section') w.choose(1);
    if (change === 'close') w.api.close();
    if (change === 'context') await w.api.setContext({ contentId: 9, studyPlanId: 4, sessionId: 31, contentTitle: 'New lesson', contextRevision: 'new' });
    if (change === 'owner') w.owner = 99;
    if (change === 'teacher') await w.api.open('teacher');
    finish(reply(200, answer())); await settle();
    assert.equal(w.host.querySelector('[role=log]').children.length, 0);
    if (change !== 'owner') assert.equal(pending.options.signal.aborted, true);
    if (change === 'context') assert.equal(w.get('question').value, '');
    if (change === 'owner') { assert.equal(w.get('question').value, ''); assert.match(w.host.textContent, /account changed/); }
});
test('source revision conflicts never replace the preview silently and require explicit refresh', async t => {
    const w = await fixture(t); await w.api.open('tutor'); w.respond = async () => reply(200, answer({ source: source(8, 'revision-B') }));
    w.get('question').value = 'Original context'; await w.submit('question');
    assert.equal(w.get('question').value, 'Original context'); assert.match(w.host.textContent, /lesson source changed/);
    assert.equal(w.get('question').closest('form').querySelector('[type=submit]').disabled, true);
    assert.equal(w.host.querySelector('[role=log]').children.length, 0);
});
test('late context fetch cannot restore a closed panel or a different lesson', { timeout: 5000 }, async t => {
    const w = await fixture(t); let finish;
    w.respond = async url => url.startsWith('/api/ai/context') ? new Promise(resolve => { finish = resolve; }) :
        reply(200, url.endsWith('/usage') ? usage() : policy('explanations'));
    const pending = w.api.open('tutor'); await settle(); w.api.close();
    finish(reply(200, { source: source() })); await pending;
    assert.equal(w.host.querySelector('section').hidden, true);
    assert.equal(w.host.querySelectorAll('[type=checkbox]').length, 0);
    assert.equal(w.get('question').closest('form').querySelector('[type=submit]').disabled, true);
});
const receipt = (payload, overrides = {}) => ({ id: 55, student_id: 7, status: 'open', content_id: payload.content_id,
    study_plan_id: payload.study_plan_id, request_text: `${payload.subject}: ${payload.description}`, ...overrides });
test('teacher request captures context, suppresses repeated submits and shows only a matching receipt', async t => {
    const w = await fixture(t); await w.api.open('teacher'); let finish;
    w.respond = async () => new Promise(resolve => { finish = resolve; });
    await w.sendTeacher(); await w.submit('subject'); assert.equal(w.post('/api/classroom/help').length, 1);
    const payload = JSON.parse(w.post('/api/classroom/help')[0].options.body);
    assert.deepEqual(payload, { subject: 'A lesson question', description: 'I tried the first step.', urgency: 1, content_id: 8, study_plan_id: 4 });
    assert.doesNotMatch(w.host.textContent, /was received/);
    finish(reply(200, receipt(payload))); await settle();
    assert.match(w.host.textContent, /Help request #55 was received/);
    assert.equal(w.get('subject').closest('form').hidden, true);
    w.host.querySelector('[data-i18n="help_panel.new_request"]').click();
    assert.equal(w.get('subject').value, ''); assert.equal(w.get('subject').closest('form').hidden, false);
});
for (const status of [401, 403, 500]) test(`teacher HTTP ${status} preserves both inputs for retry`, async t => {
    const w = await fixture(t); await w.api.open('teacher'); w.respond = async () => reply(status, { detail: 'Synthetic failure' });
    await w.sendTeacher(); assert.equal(w.get('subject').value, 'A lesson question'); assert.equal(w.get('description').value, 'I tried the first step.');
    assert.doesNotMatch(w.host.textContent, /was received/);
    w.respond = async (url, options) => reply(200, receipt(JSON.parse(options.body)));
    await w.submit('subject'); assert.match(w.host.textContent, /Help request #55 was received/);
});
for (const mismatch of [{ id: null }, { student_id: 9 }, { content_id: 9 }, { study_plan_id: 5 }, { status: 'unknown' }, { request_text: 'Different request' }]) {
    test(`teacher ambiguous receipt ${JSON.stringify(mismatch)} keeps inputs and never claims success`, async t => {
        const w = await fixture(t); await w.api.open('teacher');
        w.respond = async (url, options) => reply(200, receipt(JSON.parse(options.body), mismatch)); await w.sendTeacher();
        assert.equal(w.get('description').value, 'I tried the first step.'); assert.doesNotMatch(w.host.textContent, /was received/);
        assert.match(w.host.textContent, /did not confirm/);
    });
}
test('closing pending teacher help ignores its late receipt and preserves input with delivery uncertainty', async t => {
    const w = await fixture(t); await w.api.open('teacher'); let finish;
    w.respond = async () => new Promise(resolve => { finish = resolve; }); await w.sendTeacher();
    const payload = JSON.parse(w.post('/api/classroom/help')[0].options.body); w.api.close(); finish(reply(200, receipt(payload))); await settle();
    await w.api.open('teacher'); assert.doesNotMatch(w.host.textContent, /was received/);
    assert.match(w.host.textContent, /Delivery of the previous request is unconfirmed/); assert.equal(w.get('description').value, 'I tried the first step.');
});
test('language changes preserve question, section selection and focus without new requests', async t => {
    const w = await fixture(t); await w.api.open('tutor'); const selected = w.choose(1); selected.focus(); w.get('question').value = 'My draft';
    const count = w.requests.length;
    w.I18n.t = key => ({ 'help_panel.teacher': 'Preguntar a mi docente', 'help_panel.close': 'Volver a la lección', 'help_panel.characters': 'caracteres' }[key] || key);
    w.document.dispatchEvent(new w.CustomEvent('i18n-language-changed'));
    assert.equal(w.host.firstElementChild.children[1].textContent, 'Preguntar a mi docente');
    assert.equal(w.get('question').value, 'My draft'); assert.equal(w.document.activeElement, selected); assert.equal(selected.checked, true);
    assert.match(selected.labels[0].textContent, /caracteres/); assert.equal(w.requests.length, count);
});
test('remount and destroy remove listeners and invalidate old in-flight work', async t => {
    const w = await fixture(t); await w.api.open('tutor'); let finish;
    w.respond = async url => url === '/api/ai/chat' ? new Promise(resolve => { finish = resolve; }) : reply(404, { detail: 'Unavailable' });
    w.get('question').value = 'Old mount'; await w.submit('question');
    const next = w.SLMHelp.mount(w.host, { contentId: 9, studyPlanId: 4, contentTitle: 'New mount' });
    finish(reply(200, answer())); await settle(); assert.equal(w.host.querySelector('[role=log]').children.length, 0);
    assert.match(w.host.textContent, /New mount/); next.destroy(); assert.equal(w.host.children.length, 0);
    w.document.dispatchEvent(new w.CustomEvent('i18n-loaded')); assert.equal(w.host.children.length, 0);
});
test('equivalent revision metadata does not reload, but a changed snapshot clears the old question', async t => {
    const w = await fixture(t, { contextRevision: { content_digest: 'A', course_version: '1' } }); await w.api.open('tutor');
    const count = w.requests.length; w.get('question').value = 'Old draft';
    await w.api.setContext({ contentId: 8, studyPlanId: 4, sessionId: 30, contentTitle: 'Synthetic lesson', contextRevision: { course_version: '1', content_digest: 'A' } });
    assert.equal(w.requests.length, count); assert.equal(w.get('question').value, 'Old draft');
    await w.api.setContext({ contentId: 8, studyPlanId: 4, sessionId: 30, contentTitle: 'Synthetic lesson', contextRevision: { course_version: '1', content_digest: 'B' } });
    assert.equal(w.requests.length, count + 3); assert.equal(w.get('question').value, '');
});
test('section selection keeps focus and never sends more than the server limit', async t => {
    const w = await fixture(t); const many = source();
    many.available_sections = Array.from({ length: 13 }, (_, index) => ({ id: `content:8/section-${index + 1}`, title: `Section ${index + 1}`, characters: 100 }));
    w.respond = async url => reply(200, url.endsWith('assistance-policy') ? policy('explanations') : url.startsWith('/api/ai/context') ? { source: many } : answer());
    await w.api.open('tutor');
    for (let index = 0; index < 12; index++) w.choose(index);
    const last = w.host.querySelectorAll('[type=checkbox]')[12]; last.focus(); w.choose(12);
    assert.equal(last.checked, false); assert.equal(w.document.activeElement, last); assert.match(w.host.textContent, /no more than 12/);
    w.get('question').value = 'A long lesson question'; await w.submit('question');
    assert.equal(JSON.parse(w.post('/api/ai/chat')[0].options.body).section_ids.length, 12);
});
test('repeated Tutor selection does not restart a pending request or refetch ready context', async t => {
    const w = await fixture(t); await w.api.open('tutor'); let finish;
    w.respond = async () => new Promise(resolve => { finish = resolve; }); w.get('question').value = 'Wait for this'; await w.submit('question');
    const count = w.requests.length; await w.api.open('tutor');
    assert.equal(w.requests.length, count); assert.equal(w.post('/api/ai/chat')[0].options.signal.aborted, false);
    finish(reply(200, answer())); await settle(); assert.equal(w.host.querySelectorAll('[role=log] article').length, 1);
});
const tutorReceipt = (requestId, overrides = {}) => ({ request_id: requestId, status: 'completed', elapsed_seconds: 1.25,
    provider: 'synthetic-provider', model: 'synthetic-model', tokens_used: null, max_output_tokens: 1200,
    requests_used_today: 3, requests_limit_daily: 100, provider_may_continue: false, cost_known: false, ...overrides });
const usage = (overrides = {}) => ({ active_request_id: null, requests_used_today: 2, requests_limit_daily: 100, concurrent_limit: 1, timeout_seconds: 90, ...overrides });
test('completed tutor receipt reports provider/model/time, zero tokens and unknown cost honestly', async t => {
    const w = await fixture(t); await w.api.open('tutor');
    w.respond = async (url, options) => reply(200, answer({ receipt: tutorReceipt(JSON.parse(options.body).client_request_id, { tokens_used: 0 }) }));
    w.get('question').value = 'Show request details'; await w.submit('question');
    assert.match(w.host.textContent, /Provider: synthetic-provider/); assert.match(w.host.textContent, /Model: synthetic-model/);
    assert.match(w.host.textContent, /Elapsed seconds: 1.25/); assert.match(w.host.textContent, /Tokens used: 0/);
    assert.match(w.host.textContent, /Tutor requests today: 3 \/ 100/); assert.match(w.host.textContent, /Provider cost is unknown/);
});
test('legacy response without receipt stays an unverified source-bound suggestion with usage explicitly unknown', async t => {
    const w = await fixture(t); await w.api.open('tutor'); w.get('question').value = 'Legacy response'; await w.submit('question');
    assert.equal(w.host.querySelectorAll('[role=log] article').length, 1);
    assert.match(w.host.textContent, /did not report a request receipt or token usage/);
    assert.match(w.host.textContent, /cost is unknown/);
});
test('a supplied mismatched receipt suppresses tutor output and retains the pending request', async t => {
    const w = await fixture(t); await w.api.open('tutor');
    w.respond = async () => reply(200, answer({ receipt: tutorReceipt('someone-elses-request') }));
    w.get('question').value = 'Keep this'; await w.submit('question');
    assert.equal(w.host.querySelectorAll('[role=log] article').length, 0); assert.equal(w.get('question').value, 'Keep this');
    assert.match(w.host.textContent, /did not confirm this tutor request/); assert.equal(w.host.querySelector('[data-i18n="help_panel.cancel"]').hidden, false);
});
test('unconfirmed retries reuse their client request ID; terminal failures start a new logical request', async t => {
    const w = await fixture(t); await w.api.open('tutor'); let attempt = 0;
    w.respond = async (url, options) => {
        const payload = JSON.parse(options.body); attempt++;
        if (attempt === 1) return reply(409, { detail: 'This request is running' });
        return reply(200, answer({ status: 'unavailable', receipt: tutorReceipt(payload.client_request_id, { status: 'failed' }) }));
    };
    w.get('question').value = 'Retry safely'; await w.submit('question'); await w.submit('question'); await w.submit('question');
    const ids = w.post('/api/ai/chat').map(request => JSON.parse(request.options.body).client_request_id);
    assert.equal(ids[0], ids[1]); assert.notEqual(ids[1], ids[2]); assert.equal(w.get('question').value, 'Retry safely');
});
test('cancel checks the exact server receipt, aborts delivery and retains input while provider may continue', async t => {
    const w = await fixture(t); await w.api.open('tutor'); let finish;
    w.respond = async (url) => url === '/api/ai/chat' ? new Promise(resolve => { finish = resolve; }) :
        reply(200, tutorReceipt(url.split('/')[4], { status: 'cancelled', provider_may_continue: true }));
    w.get('question').value = 'Keep the pending question'; await w.submit('question');
    const request = w.post('/api/ai/chat')[0], id = JSON.parse(request.options.body).client_request_id;
    w.host.querySelector('[data-i18n="help_panel.cancel"]').click(); await settle();
    assert.equal(request.options.signal.aborted, true); assert.equal(w.post(`/api/ai/requests/${id}/cancel`).length, 1);
    assert.match(w.host.textContent, /Answer delivery was cancelled/); assert.match(w.host.textContent, /Provider work may continue/);
    assert.equal(w.get('question').value, 'Keep the pending question');
    finish(reply(200, answer({ receipt: tutorReceipt(id) }))); await settle();
    assert.equal(w.host.querySelectorAll('[role=log] article').length, 0);
});
for (const result of ['error', 'wrong_id', 'already_completed']) test(`cancel ${result} never falsely claims confirmed cancellation`, async t => {
    const w = await fixture(t); await w.api.open('tutor'); let finish;
    w.respond = async url => url === '/api/ai/chat' ? new Promise(resolve => { finish = resolve; }) :
        result === 'error' ? reply(500, { detail: 'Unconfirmed' }) : reply(200, tutorReceipt(result === 'wrong_id' ? 'wrong-id' : url.split('/')[4], { status: result === 'already_completed' ? 'completed' : 'cancelled', provider_may_continue: true }));
    w.get('question').value = 'Cancel safely'; await w.submit('question'); w.host.querySelector('[data-i18n="help_panel.cancel"]').click(); await settle();
    assert.doesNotMatch(w.host.textContent, /Answer delivery was cancelled/);
    assert.match(w.host.textContent, result === 'already_completed' ? /already finished/ : /Cancellation is unconfirmed/);
    assert.equal(w.get('question').value, 'Cancel safely'); finish(reply(200, answer())); await settle();
    assert.equal(w.host.querySelectorAll('[role=log] article').length, 0);
});
test('timeout receipt preserves the question, reports unavailable tokens and warns provider work may continue', async t => {
    const w = await fixture(t); await w.api.open('tutor');
    w.respond = async (url, options) => reply(200, answer({ status: 'unavailable', receipt: tutorReceipt(JSON.parse(options.body).client_request_id,
        { status: 'timed_out', elapsed_seconds: 90, provider_may_continue: true }) }));
    w.get('question').value = 'Slow request'; await w.submit('question');
    assert.equal(w.get('question').value, 'Slow request'); assert.match(w.host.textContent, /Status: Timed out/);
    assert.match(w.host.textContent, /Tokens used: Unavailable/); assert.match(w.host.textContent, /Provider work may continue/);
});
for (const state of ['daily_limit', 'other_request']) test(`reported usage ${state} blocks a new tutor request while teacher help remains available`, async t => {
    const w = await fixture(t);
    w.respond = async url => reply(200, url.endsWith('/usage') ? usage(state === 'daily_limit' ? { requests_used_today: 100 } : { active_request_id: 'existing-request' }) :
        url.endsWith('assistance-policy') ? policy('explanations') : { source: source() });
    await w.api.open('tutor'); w.get('question').value = 'Wait'; await w.submit('question');
    assert.equal(w.post('/api/ai/chat').length, 0); assert.equal(w.get('question').closest('form').querySelector('[type=submit]').disabled, true);
    assert.match(w.host.textContent, state === 'daily_limit' ? /daily tutor request limit/ : /already active/);
    await w.api.open('teacher'); assert.equal(w.get('subject').closest('form').querySelector('[type=submit]').disabled, false);
});
test('cancellation after completion reuses the UUID to recover its cached answer without a new logical request', async t => {
    const w = await fixture(t); await w.api.open('tutor'); let finish, first = true;
    w.respond = async (url, options) => {
        if (url.endsWith('/cancel')) return reply(200, tutorReceipt(url.split('/')[4]));
        const payload = JSON.parse(options.body);
        if (first) { first = false; return new Promise(resolve => { finish = resolve; }); }
        return reply(200, answer({ receipt: tutorReceipt(payload.client_request_id) }));
    };
    w.get('question').value = 'Recover my completed answer'; await w.submit('question');
    const original = JSON.parse(w.post('/api/ai/chat')[0].options.body).client_request_id;
    w.host.querySelector('[data-i18n="help_panel.cancel"]').click(); await settle();
    assert.match(w.host.textContent, /already finished/); assert.equal(w.host.querySelector('[data-i18n="help_panel.cancel"]').hidden, true);
    await w.submit('question');
    assert.equal(JSON.parse(w.post('/api/ai/chat')[1].options.body).client_request_id, original);
    assert.equal(w.host.querySelectorAll('[role=log] article').length, 1);
    finish(reply(200, answer({ receipt: tutorReceipt(original) }))); await settle();
    assert.equal(w.host.querySelectorAll('[role=log] article').length, 1);
});
