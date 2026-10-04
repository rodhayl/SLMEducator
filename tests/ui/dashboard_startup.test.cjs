/* Startup controls must not appear actionable before async bindings are ready. */
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {JSDOM} = require('jsdom');
const root = path.resolve(__dirname, '../../src/web');
const html = fs.readFileSync(path.join(root, 'dashboard.html'), 'utf8');
const code = fs.readFileSync(path.join(root, 'static/js/dashboard.js'), 'utf8');

test('binding the settings selector never overwrites the already-applied saved theme', () => {
    const dom = new JSDOM(html, {url:'http://localhost/dashboard.html', runScripts:'outside-only'});
    const w = dom.window;
    w.localStorage.setItem('slm_theme_preference', 'dark');
    w.document.body.classList.add('theme-dark');
    const calls = [];
    w.applyTheme = value => { calls.push(value); w.document.body.className = 'theme-' + value; };
    w.eval(code.slice(code.indexOf('function setSettingsTab('), code.indexOf("document.addEventListener('DOMContentLoaded', () => {", code.indexOf('function initSettingsUI('))));
    w.initSettingsUI();
    assert.deepEqual(calls, []);
    assert.equal(w.document.getElementById('app-theme').value, 'dark');
    assert.ok(w.document.body.classList.contains('theme-dark'));
    w.document.getElementById('app-theme').value = 'light';
    w.document.getElementById('app-theme').dispatchEvent(new w.Event('change'));
    assert.deepEqual(calls, ['light']);
    dom.window.close();
});

test('dashboard exposes a retryable loading state until startup completes', () => {
    const dom = new JSDOM(html, {url:'http://localhost/dashboard.html', runScripts:'outside-only'});
    const w = dom.window;
    const version = html.match(/dashboard\.js\?v=(\d+)/)?.[1];
    assert.ok(version);
    assert.ok(html.includes('main.css?v=' + version));
    assert.ok(fs.readFileSync(path.join(root, 'sw.js'), 'utf8').includes('slm-educator-v' + version + '-'));
    const app = w.document.getElementById('dashboard-app');
    const loading = w.document.getElementById('dashboard-loading');
    assert.ok(app?.hasAttribute('inert'));
    assert.equal(app.getAttribute('aria-busy'), 'true');
    assert.equal(loading.hidden, false);
    assert.ok(loading.querySelector('button'));
    const start = code.indexOf('function finishDashboardStartup(');
    const end = code.indexOf('\nfinishDashboardStartup();', start);
    assert.ok(start > code.indexOf('// Navigation Handler'));
    w.eval(code.slice(start, end));
    w.finishDashboardStartup();
    assert.equal(app.hasAttribute('inert'), false);
    assert.equal(app.getAttribute('aria-busy'), 'false');
    assert.equal(loading.hidden, true);
    dom.window.close();
});
