/* Shared Python-checked output through the real vendored rendering boundary. */
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM } = require('jsdom');
const root = path.resolve(__dirname, '../../src/web');
const fixtures = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../fixtures/source_clarification_render.json'), 'utf8'));

for (const item of fixtures.cases) {
    test(item.name + ': clarification is visible literal text before untrusted markup', () => {
        const dom = new JSDOM('<main></main>', {url: 'http://localhost/', runScripts: 'outside-only'});
        const w = dom.window;
        for (const file of ['static/vendor/dompurify@3.4.16/purify.min.js', 'static/vendor/marked@15.0.12/marked.min.js', 'static/js/safe-render.js']) {
            w.eval(fs.readFileSync(path.join(root, file), 'utf8'));
        }
        const target = w.document.querySelector('main');
        const text = w.SLMRender.lessonText(item.learner_output);
        w.SLMRender.setMarkdown(target, text);
        assert.ok(target.textContent.includes(item.question), target.innerHTML);
        assert.equal(target.querySelector('script,img,svg,iframe,[onerror],[onload]'), null);
        // The existing editor flattens the displayed text to one Markdown body.
        w.SLMRender.setMarkdown(target, w.SLMRender.lessonText({body: text}));
        assert.ok(target.textContent.includes(item.question), target.innerHTML);
        assert.equal(target.querySelector('script,img,svg,iframe,[onerror],[onload]'), null);
        dom.window.close();
    });
}
