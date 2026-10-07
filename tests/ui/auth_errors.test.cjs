/* Synthetic auth responses in JSDOM; no database, provider or live-browser claims. */
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {JSDOM, VirtualConsole} = require('jsdom');
const root = path.resolve(__dirname, '../../src/web');
const read = file => fs.readFileSync(path.join(root, file), 'utf8');
const translations = Object.fromEntries(['en', 'es'].map(lang => [lang,
    JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../translations', lang + '.json'), 'utf8'))]));
const tick = () => new Promise(resolve => setImmediate(resolve));
const reply = (data, status = 200) => ({ok: status >= 200 && status < 300, status, json: async () => data});
const unreadable = status => ({ok: status >= 200 && status < 300, status,
    json: async () => { throw new SyntaxError('Synthetic private response contents'); }});
const password = 'Synthetic-Only-Secret12!';
const values = {first_name: 'Synthetic', last_name: 'Teacher', email: 'docente.demo@example.invalid',
    username: 'synthetic-teacher', password, role: 'teacher', teacher_id: ''};
const emailMessage = {
    en: 'Email: Enter a valid email address, such as name@example.com.',
    es: 'Correo electrónico: Introduce un correo válido, como nombre@example.com.'
};
const routineMessages = [
    'Username already exists',
    'Email already exists',
    'Password must be at least 8 characters and contain uppercase, lowercase, digit, and special character',
    'Choose an active teacher for a student account',
    'Invalid role',
    'Account creation requires an administrator or teacher',
    'Teachers can only create student accounts',
    'Teachers can only enroll their own learners',
    'Students cannot create user accounts',
    'Invalid username or password',
    'Too many login attempts. Please try again later.',
    'Account is locked due to too many failed attempts',
    'Account lock timestamp has an unknown timezone. Ask the administrator to review its provenance.',
    'Not authenticated',
    'Could not validate credentials',
    'Not authorized'
];

// Embedded shape from the actual UserRegister EmailStr schema reproduction.
// Reserved domains reach API validation even though input[type=email] accepts them.
const reservedEmail422 = {detail: [{
    type: 'value_error', loc: ['body', 'email'],
    msg: 'value is not a valid email address: The part after the @-sign is a special-use or reserved name that cannot be used with email.',
    input: 'docente.demo@example.invalid',
    ctx: {reason: 'The part after the @-sign is a special-use or reserved name that cannot be used with email.'}
}]};

async function fixture(t, lang = 'en', page = 'register.html') {
    const dom = new JSDOM(read(page), {url: 'http://localhost/' + page + '?role=teacher',
        runScripts: 'outside-only', pretendToBeVisual: true, virtualConsole: new VirtualConsole()});
    t.after(() => dom.window.close());
    await tick();
    const w = dom.window;
    const token = 'synthetic.' + Buffer.from(JSON.stringify({
        exp: Math.floor(Date.now() / 1000) + 3600, role: 'admin'
    })).toString('base64url') + '.synthetic';
    const creator = JSON.stringify({id: 7, role: 'admin', username: 'synthetic-creator'});
    w.localStorage.setItem('token', token);
    w.localStorage.setItem('user', creator);
    // Load the real translator after DOMContentLoaded; no translation network requests.
    w.eval(read('static/js/i18n.js'));
    w.I18n.currentLang = lang;
    w.I18n.translations = translations[lang];
    w.I18n.fallbackTranslations = translations.en;
    w.I18n.loaded = true;
    w.I18n.translatePage();
    w.eval(read('static/js/learning-client.js'));
    const calls = [];
    let response = async () => { throw new Error('Unconfigured synthetic auth response'); };
    w.fetch = async (url, options) => {
        if (url === '/api/auth/users?role=teacher') return reply([]);
        calls.push({url, options});
        return response(url, options);
    };
    const form = w.document.querySelector('form');
    const control = name => form.elements.namedItem(name);
    if (page === 'login.html') {
        // JSDOM lacks the HTMLFormElement named-control properties used by this handler.
        for (const name of ['username', 'password']) Object.defineProperty(form, name, {value: control(name)});
    }
    w.eval(read('static/js/auth.js').replace('export class AuthService', 'class AuthService'));
    for (const [name, value] of Object.entries(values)) if (control(name)) control(name).value = value;
    await tick();
    return {w, form, control, calls, token, creator,
        status: w.document.getElementById('error-msg'),
        respond: callback => { response = callback; },
        submit: () => form.dispatchEvent(new w.Event('submit', {cancelable: true})),
        message: key => {
            const text = w.I18n.t(key);
            assert.notEqual(text, key, 'translation must exist: ' + key);
            return text;
        }};
}

function unchangedSession(f) {
    assert.equal(f.w.localStorage.getItem('token'), f.token);
    assert.equal(f.w.localStorage.getItem('user'), f.creator);
}

function failedForm(f, expected, expectedValues = values) {
    assert.equal(f.status.textContent, expected);
    assert.equal(f.status.classList.contains('d-none'), false);
    assert.equal(f.status.style.display, 'block');
    assert.equal(f.status.classList.contains('alert-success'), false);
    assert.equal(f.status.childElementCount, 0);
    assert.equal(f.form.querySelector('[type=submit]').disabled, false);
    for (const [name, value] of Object.entries(expectedValues)) if (f.control(name)) assert.equal(f.control(name).value, value);
    const actions = f.w.document.getElementById('register-success-actions');
    if (actions) assert.equal(actions.classList.contains('d-none'), true);
    unchangedSession(f);
}

async function rejectedRequest(f, operation, expected, status) {
    const request = operation === 'login'
        ? f.w.AuthService.login(values.username, password)
        : f.w.AuthService.register({...values});
    await assert.rejects(request, error => {
        assert.equal(error.message, expected);
        assert.equal(error.status, status);
        assert.doesNotMatch(error.message, /\[object Object\]|Synthetic private|Synthetic-Only-Secret12!/);
        return true;
    });
    unchangedSession(f);
}

for (const lang of ['en', 'es']) {
    test(`registration ${lang}: schema 422 stays retryable; corrected email creates once without changing creator`, async t => {
        const f = await fixture(t, lang);
        let finish;
        f.respond(() => new Promise(resolve => { finish = resolve; }));
        assert.equal(f.control('email').checkValidity(), true);
        f.submit(); f.submit(); f.submit();
        assert.equal(f.calls.length, 1);
        assert.equal(f.form.querySelector('[type=submit]').disabled, true);
        finish(reply(reservedEmail422, 422));
        await tick();
        failedForm(f, emailMessage[lang]);
        assert.doesNotMatch(f.status.textContent, /reserved name|docente\.demo|value_error|ctx|input/);
        const corrected = 'docente.demo@example.com';
        f.control('email').value = corrected;
        f.submit(); f.submit();
        assert.equal(f.calls.length, 2);
        assert.equal(f.status.classList.contains('d-none'), true);
        assert.equal(f.control('password').value, password);
        finish(reply({id: 8, role: 'teacher'}));
        await tick();
        assert.equal(f.status.textContent, f.message('recovery.account_created'));
        assert.equal(f.status.classList.contains('alert-success'), true);
        assert.equal(f.w.document.getElementById('register-success-actions').classList.contains('d-none'), false);
        assert.equal(f.control('password').value, '');
        assert.equal(f.control('email').value, corrected);
        for (const name of ['first_name', 'last_name', 'username', 'role']) assert.equal(f.control(name).value, values[name]);
        assert.equal(f.form.querySelector('[type=submit]').disabled, true);
        assert.equal(f.w.document.getElementById('register-return').search, '?tab=teachers');
        unchangedSession(f);
        f.submit(); f.submit();
        await tick();
        assert.equal(f.calls.length, 2, 'a successful form cannot create another account');
        for (const [index, call] of f.calls.entries()) {
            assert.equal(call.url, '/api/auth/register');
            assert.equal(call.options.method, 'POST');
            assert.equal(call.options.headers.Authorization, 'Bearer ' + f.token);
            assert.equal(call.options.headers['Content-Type'], 'application/json');
            const expected = {...values, email: index ? corrected : values.email};
            delete expected.teacher_id;
            assert.deepEqual(JSON.parse(call.options.body), expected);
        }
    });

    const failures = [
        ['object detail', () => reply({detail: {message: 'Synthetic private object', input: password}}, 422), 'register_failed'],
        ['malformed detail', () => reply({detail: [null, 'Synthetic private entry', 42, {loc: 'email', type: 'missing'}]}, 422), 'register_failed'],
        ['missing detail', () => reply({}, 409), 'register_failed'],
        ['null detail', () => reply({detail: null}, 400), 'register_failed'],
        ['blank detail', () => reply({detail: '  '}, 400), 'register_failed'],
        ['non-JSON HTTP failure', () => unreadable(503), 'register_failed'],
        ['network rejection', () => Promise.reject(new Error('Synthetic private transport error')), 'register_network'],
        ['unreadable successful response', () => unreadable(200), 'register_invalid_response'],
        ['empty successful response', () => reply({}), 'register_invalid_response'],
        ['server detail', () => reply({detail: 'Synthetic private backend traceback'}, 500), 'register_failed']
    ];
    for (const [name, response, key] of failures) {
        test(`registration ${lang}: ${name} gives localized feedback and preserves form/session`, async t => {
            const f = await fixture(t, lang);
            f.respond(response);
            f.submit();
            await tick();
            assert.equal(f.calls.length, 1);
            failedForm(f, f.message('auth.errors.' + key));
        });
    }

    test(`structured 422 ${lang}: attacker values and unknown/nested locations are never rendered`, async t => {
        const f = await fixture(t, lang);
        const attack = '<img src=x onerror="window.authAttack=true">';
        const entry = {type: 'value_error', loc: ['body', 'email'],
            msg: attack + password, input: password, ctx: {reason: attack, password}};
        const detail = [entry, {...entry}, null, attack,
            {...entry, loc: ['body', attack]}, {...entry, loc: ['query', 'email']},
            {...entry, loc: ['body', 'email', password]}, {...entry, loc: ['body', '__proto__']},
            {...entry, loc: ['body', 'constructor']}, {...entry, loc: {field: 'email'}}];
        f.respond(() => reply({detail}, 422));
        f.submit();
        await tick();
        failedForm(f, emailMessage[lang]);
        assert.equal(f.w.authAttack, undefined);
        assert.equal(f.status.querySelector('img'), null);
        assert.doesNotMatch(f.w.document.body.textContent, /Synthetic-Only-Secret12!|onerror|authAttack|__proto__|value_error/);
    });

    test(`registration ${lang}: student role and reviewed teacher assignment survive validation failure`, async t => {
        const f = await fixture(t, lang);
        f.control('role').value = 'student';
        f.control('role').dispatchEvent(new f.w.Event('change'));
        f.control('teacher_id').add(new f.w.Option('Synthetic Teacher', '12'));
        f.control('teacher_id').value = '12';
        f.respond(() => reply(reservedEmail422, 422));
        f.submit();
        await tick();
        failedForm(f, emailMessage[lang], {...values, role: 'student', teacher_id: '12'});
        assert.equal(f.w.document.getElementById('register-teacher-field').classList.contains('d-none'), false);
        assert.equal(JSON.parse(f.calls[0].options.body).teacher_id, 12);
        assert.equal(JSON.parse(f.calls[0].options.body).role, 'student');
    });

    for (const page of ['register.html', 'login.html']) {
        test(`${page} ${lang}: HTML-looking server string receives localized fallback`, async t => {
            const f = await fixture(t, lang, page);
            const detail = '<img src=x onerror="window.authAttack=true"> Username already exists';
            f.respond(() => reply({detail}, 400));
            f.submit();
            await tick();
            failedForm(f, f.message('auth.errors.' + (page === 'login.html' ? 'login' : 'register') + '_failed'));
            assert.equal(f.w.authAttack, undefined);
            assert.equal(f.status.querySelector('img'), null);
            assert.doesNotMatch(f.status.textContent, /img|authAttack|Username already exists/);
        });

        test(`${page} ${lang}: trusted localization is rendered as inert text`, async t => {
            const f = await fixture(t, lang, page);
            const text = '<img src=x onerror="window.authAttack=true"> Localized feedback';
            const key = 'auth.errors.' + (page === 'login.html' ? 'login' : 'register') + '_failed';
            const translate = f.w.I18n.t.bind(f.w.I18n);
            f.w.I18n.t = candidate => candidate === key ? text : translate(candidate);
            f.respond(() => reply({detail: {message: 'Synthetic private response'}}, 400));
            f.submit();
            await tick();
            failedForm(f, text);
            assert.equal(f.w.authAttack, undefined);
            assert.equal(f.status.querySelector('img'), null);
            assert.match(f.status.innerHTML, /&lt;img/);
        });

        test(`${page} ${lang}: transformed secrets and arbitrary server text never reach the DOM`, async t => {
            const f = await fixture(t, lang, page);
            const fallback = f.message('auth.errors.' + (page === 'login.html' ? 'login' : 'register') + '_failed');
            const escapedPassword = 'Synthetic\\Password12!';
            const cases = [
                ['SyntheticPassword12! ', 'Rejected password: SyntheticPassword12! '],
                [escapedPassword, 'Invalid payload: ' + JSON.stringify({password: escapedPassword})],
                [password, 'Invalid payload: ' + JSON.stringify({input: password})],
                [password, 'Username already exists\nSynthetic private diagnostic'],
                [password, 'Synthetic private response '.repeat(100)],
                [password, 'Username already exists: additional arbitrary server detail'],
                [password, 'Diagnostic prefix: Username already exists']
            ];
            for (const [submittedPassword, detail] of cases) {
                f.control('password').value = submittedPassword;
                f.respond(() => reply({detail}, 400));
                f.submit();
                await tick();
                failedForm(f, fallback, {...values, password: submittedPassword});
                assert.doesNotMatch(f.w.document.body.textContent, /SyntheticPassword12|Synthetic\\+Password12|Synthetic-Only-Secret12|Invalid payload|Synthetic private diagnostic/);
            }
            assert.equal(f.calls.length, cases.length);
        });
    }

    for (const operation of ['register', 'login']) {
        test(`${operation} ${lang}: exact routine backend messages retain status and creator session`, async t => {
            const f = await fixture(t, lang, 'login.html');
            for (const [index, detail] of routineMessages.entries()) {
                const status = [400, 401, 403, 409, 422, 429][index % 6];
                f.respond(() => reply({detail}, status));
                await rejectedRequest(f, operation, detail, status);
            }
            f.respond(() => reply({detail: routineMessages[0]}, 500));
            await rejectedRequest(f, operation, f.message('auth.errors.' + operation + '_failed'), 500);
        });

        test(`${operation} ${lang}: structured field guidance preserves HTTP 422 and session`, async t => {
            const f = await fixture(t, lang, 'login.html');
            f.respond(() => reply(reservedEmail422, 422));
            await rejectedRequest(f, operation, emailMessage[lang], 422);
            const required = lang === 'en' ? 'This field is required.' : 'Este campo es obligatorio.';
            for (const field of ['username', 'password', 'email', 'first_name', 'last_name', 'role', 'teacher_id']) {
                f.respond(() => reply({detail: [{loc: ['body', field], type: 'missing', input: password, msg: password}]}, 422));
                const label = f.message(['role', 'teacher_id'].includes(field) ? 'auth.errors.' + field : 'common.labels.' + field);
                await rejectedRequest(f, operation, label + ': ' + required, 422);
                f.respond(() => reply({detail: [{loc: ['body', field], type: 'value_error', input: password, msg: password}]}, 422));
                const reason = f.message('auth.errors.' + (field === 'email' ? 'invalid_email' : 'invalid_field'));
                await rejectedRequest(f, operation, label + ': ' + reason, 422);
            }
        });

        test(`${operation} ${lang}: unsafe or malformed detail preserves HTTP status and uses localized fallback`, async t => {
            const f = await fixture(t, lang, 'login.html');
            const fallback = f.message('auth.errors.' + operation + '_failed');
            const cases = [
                [401, {detail: {reason: 'Synthetic private object'}}],
                [403, {detail: null}],
                [409, {detail: '[{"input":"Synthetic private array"}]'}],
                [422, {detail: '{"input":"Synthetic private object"}'}],
                [422, {detail: [{loc: ['query', 'email'], type: 'missing'}]}],
                [422, {detail: [{loc: ['body', 'email', password], type: 'missing'}]}],
                [400, {detail: 'Rejected password: ' + password}],
                [500, {detail: 'Synthetic private backend traceback'}],
                [502, {detail: reservedEmail422.detail}]
            ];
            for (const [status, data] of cases) {
                f.respond(() => reply(data, status));
                await rejectedRequest(f, operation, fallback, status);
            }
            f.respond(() => unreadable(503));
            await rejectedRequest(f, operation, fallback, 503);
            f.respond(() => Promise.reject(new Error('Synthetic private transport error')));
            const networkKey = operation === 'register' ? 'register_network' : 'network';
            await rejectedRequest(f, operation, f.message('auth.errors.' + networkKey), undefined);
        });

        test(`${operation} ${lang}: malformed 2xx never overwrites existing session`, async t => {
            const f = await fixture(t, lang, 'login.html');
            const invalidKey = operation === 'register' ? 'register_invalid_response' : 'invalid_response';
            const expected = f.message('auth.errors.' + invalidKey);
            const invalid = operation === 'register'
                ? [null, [], {}, {id: 0}, {id: -1}, {id: 1.5}, {id: '8'}, {id: true}]
                : [null, [], {}, {access_token: 'synthetic-new'},
                    {access_token: '', user: {id: 8}}, {access_token: 123, user: {id: 8}},
                    {access_token: 'synthetic-new', user: null}, {access_token: 'synthetic-new', user: []},
                    {access_token: 'synthetic-new', user: {}},
                    {access_token: 'synthetic-new', user: {id: '8'}},
                    {access_token: 'synthetic-new', user: {id: 0}},
                    {access_token: 'synthetic-new', user: {id: -1}},
                    {access_token: 'synthetic-new', user: {id: 1.5}}];
            for (const data of invalid) {
                f.respond(() => reply(data));
                await rejectedRequest(f, operation, expected, 200);
            }
            for (const status of [200, 201, 204]) {
                f.respond(() => unreadable(status));
                await rejectedRequest(f, operation, expected, status);
            }
        });
    }

    test(`login DOM ${lang}: shared validation and localized fallback do not navigate or clear credentials`, async t => {
        const f = await fixture(t, lang, 'login.html');
        f.respond(() => reply({detail: [{loc: ['body', 'username'], type: 'missing', msg: password}]}, 422));
        f.submit();
        await tick();
        failedForm(f, f.message('common.labels.username') + ': ' + f.message('auth.errors.required'));
        f.respond(() => reply({detail: {reason: 'Synthetic private object'}}, 401));
        f.submit();
        await tick();
        failedForm(f, f.message('auth.errors.login_failed'));
        assert.equal(f.w.location.pathname, '/login.html');
        assert.equal(f.calls.length, 2);
        assert.equal(f.calls[0].url, '/api/auth/login');
        assert.equal(f.calls[0].options.headers['Content-Type'], 'application/x-www-form-urlencoded');
        const body = new URLSearchParams(String(f.calls[0].options.body));
        assert.equal(body.get('username'), values.username);
        assert.equal(body.get('password'), password);
    });
}

test('successful login still normalizes legacy role and stores only validated response', async t => {
    const f = await fixture(t, 'en', 'login.html');
    const user = {id: 8, username: 'synthetic-new-user', role: {value: 'UserRole.TEACHER'}};
    f.respond(() => reply({access_token: 'synthetic-new-token', token_type: 'bearer', user}));
    const result = await f.w.AuthService.login(values.username, password);
    assert.equal(result.role, 'teacher');
    assert.equal(f.w.localStorage.getItem('token'), 'synthetic-new-token');
    assert.deepEqual(JSON.parse(f.w.localStorage.getItem('user')), {...user, role: 'teacher'});
});

test('auth errors remain bounded and deduplicate recognized structured fields', async t => {
    const f = await fixture(t, 'en', 'login.html');
    const text = 'Synthetic ordinary message '.repeat(100);
    f.respond(() => reply({detail: '  ' + text + '  '}, 400));
    await rejectedRequest(f, 'login', f.message('auth.errors.login_failed'), 400);
    const fields = ['username', 'password', 'email', 'first_name', 'last_name', 'role', 'teacher_id'];
    const entries = fields.flatMap(field => [{loc: ['body', field], type: 'missing'}, {loc: ['body', field], type: 'missing'}]);
    f.respond(() => reply({detail: entries}, 422));
    const expected = fields.slice(0, 4).map(field => f.message('common.labels.' + field) + ': This field is required.').join(' ');
    await rejectedRequest(f, 'register', expected, 422);
});

for (const i18nState of ['unavailable', 'missing keys']) {
    test(`auth has readable English fallback when translations are ${i18nState}`, async t => {
        const f = await fixture(t, 'en', 'login.html');
        f.w.I18n = i18nState === 'unavailable' ? undefined : {t: key => key};
        f.respond(() => reply(reservedEmail422, 422));
        await rejectedRequest(f, 'register', emailMessage.en, 422);
        f.respond(() => reply({detail: {message: 'Synthetic private object'}}, 401));
        await rejectedRequest(f, 'login', 'Sign-in failed. Please try again.', 401);
        f.respond(() => unreadable(500));
        await rejectedRequest(f, 'register', 'Account creation failed. Check the form and try again.', 500);
        f.respond(() => Promise.reject(new Error('Synthetic private transport error')));
        await rejectedRequest(f, 'login', 'Could not reach the server. Check the connection and try again.', undefined);
        f.respond(() => reply({}));
        await rejectedRequest(f, 'register', 'The server response could not be read. Before retrying account creation, check the account list.', 200);
    });
}
