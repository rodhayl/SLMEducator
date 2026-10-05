const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const code = fs.readFileSync(path.resolve(__dirname, '../../src/web/sw.js'), 'utf8');

test('failed precache rejects installation and keeps the old worker active', async () => {
    const events = {};
    let activated = false;
    const scope = {console: {log() {}, warn() {}, error() {}},
        Request: class extends Request {constructor(url, options) {super(new URL(url, 'http://synthetic.invalid'), options);}}, Response, URL,
        fetch: async () => { throw new Error('Synthetic disconnected asset'); },
        caches: {open: async () => ({put: async () => {}}), delete: async () => true},
        self: {addEventListener: (name, handler) => { events[name] = handler; },
            skipWaiting: async () => { activated = true; }, clients: {claim: async () => {}}}};
    vm.runInNewContext(code, scope);
    let operation;
    events.install({waitUntil: task => { operation = task; }});
    await assert.rejects(operation);
    assert.equal(activated, false);
});

test('activation cleans only this application caches', async () => {
    const events = {}, deleted = [];
    vm.runInNewContext(code, {console, URL, Request, Response,
        caches: {keys: async () => ['slm-educator-v1-old', 'another-application'],
            delete: async name => { deleted.push(name); }},
        self: {addEventListener: (name, handler) => { events[name] = handler; },
            clients: {claim: async () => {}}}});
    let operation;
    events.activate({waitUntil: task => { operation = task; }});
    await operation;
    assert.deepEqual(deleted, ['slm-educator-v1-old']);
});
