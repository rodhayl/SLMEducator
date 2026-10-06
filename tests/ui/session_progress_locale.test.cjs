/* Exercise the real session counters with the existing ES/EN dictionaries. */
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {JSDOM, VirtualConsole} = require('jsdom');
const root = path.resolve(__dirname, '../..');
const read = file => fs.readFileSync(path.join(root, file), 'utf8');

for (const [language, progress, position] of [
    ['es', '1/2 completados', '1 de 2'],
    ['en', '1/2 completed', '1 of 2'],
]) {
    test(`session progress and position follow ${language} after navigation`, async () => {
        const dom = new JSDOM(read('src/web/session_player.html'), {
            url: 'http://localhost/session_player.html', runScripts: 'outside-only',
            virtualConsole: new VirtualConsole(),
        });
        await new Promise(resolve => setImmediate(resolve));
        const w = dom.window;
        for (const file of ['static/vendor/dompurify@3.4.16/purify.min.js',
            'static/vendor/marked@15.0.12/marked.min.js', 'static/js/safe-render.js']) {
            w.eval(read('src/web/' + file));
        }
        w.eval(read('src/web/static/js/i18n.js'));
        w.I18n.translations = JSON.parse(read(`translations/${language}.json`));
        w.SLMClient = {message: (_, fallback) => fallback};
        w.eval(read('src/web/static/js/session.js') + '\n' +
            'planContents=[{id:1,title:"First"},{id:2,title:"Second"}]; completedContentIds=[1]; currentContentIndex=0;' +
            'window.advanceCounters=()=>{currentContentIndex=1; updateNavigationButtons();};' +
            'window.emptyCounters=()=>{planContents=[]; completedContentIds=[]; updateNavigationButtons();};');
        w.renderPlanSidebar();
        w.updateNavigationButtons();
        assert.equal(w.document.getElementById('completed-count').textContent, progress);
        assert.equal(w.document.getElementById('content-position').textContent, position);
        w.advanceCounters();
        assert.equal(w.document.getElementById('content-position').textContent,
            language === 'es' ? '2 de 2' : '2 of 2');
        const focused = w.document.querySelector('.plan-content-item');
        focused.focus();
        w.I18n.translations = {};
        w.updatePlanCounterText();
        assert.equal(w.document.getElementById('completed-count').textContent, '1/2');
        const otherLanguage = language === 'es' ? 'en' : 'es';
        w.I18n.translations = JSON.parse(read(`translations/${otherLanguage}.json`));
        w.document.dispatchEvent(new w.CustomEvent('i18n-loaded'));
        w.document.dispatchEvent(new w.CustomEvent('i18n-language-changed'));
        assert.equal(w.document.getElementById('completed-count').textContent,
            otherLanguage === 'es' ? '1/2 completados' : '1/2 completed');
        assert.equal(w.document.getElementById('content-position').textContent,
            otherLanguage === 'es' ? '2 de 2' : '2 of 2');
        assert.equal(w.document.activeElement, focused);
        w.emptyCounters();
        assert.equal(w.document.getElementById('content-position').textContent,
            otherLanguage === 'es' ? '0 de 0' : '0 of 0');
        dom.window.close();
    });
}
