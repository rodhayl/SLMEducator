/* Supported practice option containers; synthetic DOM/API, no model calls. */
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {JSDOM, VirtualConsole} = require('jsdom');
const root = path.resolve(__dirname, '../../src/web');
const read = file => fs.readFileSync(path.join(root, file), 'utf8');
const shapes = [
    ['list', ['One', 'Two'], 'B'],
    ['mapping', {first: 'One', second: 'Two'}, 'second'],
    ['wrapped list', {choices: ['One', 'Two']}, 'B'],
    ['wrapped mapping', {choices: {first: 'One', second: 'Two'}}, 'second'],
];
async function fixture() {
    const dom = new JSDOM(read('dashboard.html'), {url: 'http://localhost/dashboard.html',
        runScripts: 'outside-only', virtualConsole: new VirtualConsole()});
    await new Promise(resolve => setImmediate(resolve));
    const w = dom.window;
    w.AuthService = {getToken: () => 'synthetic'};
    w.I18n = {t: key => key};
    w.toasts = []; w.showToast = (...args) => w.toasts.push(args);
    for (const file of ['static/vendor/dompurify@3.4.16/purify.min.js',
        'static/js/safe-render.js', 'static/js/learning-client.js', 'static/js/practice.js']) w.eval(read(file));
    const code = read('static/js/dashboard.js');
    w.eval('const aiContentForm = document.getElementById("create-ai-content-form"); const escapeHtml = SLMRender.escape;\n' +
        code.slice(code.indexOf('let generatedAIContent ='), code.indexOf('let savingGeneratedContent =')) +
        '\nwindow.latestGenerated = () => generatedAIContent;');
    return {dom, w};
}
for (const [name, options, correct_answer] of shapes) {
    test('dashboard preview preserves option labels and answer binding: ' + name, async () => {
        const {dom, w} = await fixture();
        w.fetch = async () => ({ok: true, json: async () => ({question: 'Choose two', type: 'multiple_choice', options, correct_answer})});
        await w.generateAIContent('/api/generate/exercise', {}, 'exercise');
        const labels = [...w.document.querySelectorAll('#generated-items-list li')].map(item => item.textContent);
        assert.equal(labels.length, 2); assert.match(labels[0], /One/); assert.match(labels[1], /Two/);
        assert.equal(w.document.getElementById('ai-content-generation-result').classList.contains('hidden'), false);
        assert.equal(w.toasts.length, 0);
        assert.deepEqual(w.latestGenerated().options, options);
        assert.equal(w.latestGenerated().correct_answer, correct_answer);
        dom.window.close();
    });
    test('learner self-check keeps original option keys: ' + name, async () => {
        const {dom, w} = await fixture(); const host = w.document.createElement('div');
        w.SLMPractice.render(host, {question: 'Choose two', type: 'multiple_choice', options, correct_answer});
        assert.equal(host.querySelectorAll('select').length, 1);
        host.querySelector('select').value = 'Two'; host.querySelectorAll('button')[1].click();
        assert.match(host.querySelector('[role=status]').textContent, /matches the answer key/);
        assert.match(host.querySelector('[role=status]').textContent, /not a final grade/);
        dom.window.close();
    });
}
test('dashboard loads the existing practice option helper before its module', () => {
    const html = read('dashboard.html');
    assert.ok(html.indexOf('/static/js/practice.js') > 0);
    assert.ok(html.indexOf('/static/js/practice.js') < html.indexOf('/static/js/dashboard.js'));
});
test('generation modes are siblings and hidden topic fields do not block other modes', async () => {
    const {dom, w} = await fixture();
    const code = read('static/js/dashboard.js');
    w.eval(code.slice(code.indexOf('window.toggleGenerationMode ='), code.indexOf('// Toggle functions for conditional options')));
    const form = w.document.getElementById('create-ai-content-form');
    for (const id of ['study-plan-mode-fields', 'topic-mode-fields', 'exercise-mode-fields', 'save-options-section']) {
        assert.equal(w.document.getElementById(id).parentElement, form);
    }
    assert.equal(w.document.getElementById('generate-btn').closest('#topic-mode-fields'), null);
    assert.equal(w.document.getElementById('create-manual-form').closest('#create-ai-content-form'), null);
    for (const mode of ['exercise', 'study_plan', 'topic', 'exercise']) {
        w.document.querySelector(`[name=generation_mode][value=${mode}]`).checked = true;
        w.toggleGenerationMode();
        assert.equal(form.querySelector('[name=learning_objectives]').required, mode === 'topic');
        if (mode !== 'topic') assert.equal(form.checkValidity(), true);
    }
    dom.window.close();
});
test('invalid option provider response leaves visible retryable failure and preserves form input', async () => {
    const {dom, w} = await fixture();
    const topic = w.document.querySelector('[name=exercise_topic]'); topic.value = 'Keep this topic';
    w.fetch = async () => ({ok: false, json: async () => ({detail: 'Multiple-choice practice needs options'})});
    await w.generateAIContent('/api/generate/exercise', {}, 'exercise');
    assert.equal(topic.value, 'Keep this topic');
    assert.equal(w.document.getElementById('ai-content-generation-result').classList.contains('hidden'), true);
    assert.equal(w.toasts.length, 1); assert.match(w.toasts[0][0], /Multiple-choice practice needs options/);
    assert.equal(w.document.querySelector('#create-ai-content-form button[type=submit]').disabled, false);
    dom.window.close();
});
