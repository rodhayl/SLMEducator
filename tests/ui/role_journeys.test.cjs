/* Behavior regressions for role journeys, using DOM emulation, not browser acceptance. */
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {JSDOM, VirtualConsole} = require('jsdom');
const root = path.resolve(__dirname, '../../src/web');
const read = file => fs.readFileSync(path.join(root, file), 'utf8');
async function fixture(page, query = '') {
    const dom = new JSDOM(read(page), {url: 'http://localhost/' + page + query, runScripts:'outside-only', pretendToBeVisual:true, virtualConsole:new VirtualConsole()});
    await new Promise(resolve => setImmediate(resolve));
    const w = dom.window;
    w.AuthService = {getUser:()=>({id:7,role:'student'}), getRole:()=> 'student', getToken:()=> 'synthetic', isAuthenticated:()=>true};
    w.I18n = {t:key=>key}; w.toasts=[]; w.showToast=(...args)=>w.toasts.push(args);
    for (const source of ['static/vendor/dompurify@3.4.16/purify.min.js','static/vendor/marked@15.0.12/marked.min.js','static/js/safe-render.js','static/js/learning-client.js','static/js/time-display.js']) w.eval(read(source));
    return {dom,w};
}
const reply = (data, status=200) => ({ok:status >= 200 && status < 300,status,json:async()=>data});
for (const [query,chosen] of [['','teacher'],['?role=teacher','student'],['?role=student','admin']]) {
    test('registration preserves the reviewed role and creator session: '+query, async()=>{
        const {dom,w}=await fixture('register.html',query);
        const token='synthetic.'+Buffer.from(JSON.stringify({exp:Math.floor(Date.now()/1000)+3600,role:'admin'})).toString('base64url')+'.synthetic';
        const creator=JSON.stringify({id:7,role:'admin'});
        w.localStorage.setItem('token',token); w.localStorage.setItem('user',creator);
        const calls=[]; let succeed=false;
        w.fetch=async(url,options)=>{calls.push(JSON.parse(options.body));return reply(succeed?{id:8}:{detail:'Retry'},succeed?200:500);};
        w.eval(read('static/js/auth.js').replace('export class AuthService','class AuthService'));
        const form=w.document.getElementById('register-form');
        form.elements.namedItem('role').value=chosen;
        for (const name of ['first_name','last_name','email','username','password']) form.elements.namedItem(name).value='synthetic';
        const submit=()=>form.dispatchEvent(new w.Event('submit',{cancelable:true}));
        submit(); await new Promise(resolve=>setImmediate(resolve));
        assert.equal(calls[0].role,chosen); assert.equal(form.elements.namedItem('role').value,chosen);
        succeed=true;submit();submit();await new Promise(resolve=>setImmediate(resolve));
        assert.equal(calls.length,2); assert.equal(calls[1].role,chosen);
        assert.equal(w.localStorage.getItem('token'),token); assert.equal(w.localStorage.getItem('user'),creator);
        assert.equal(w.document.getElementById('register-return').pathname,'/dashboard.html');
        assert.equal(w.document.getElementById('register-success-actions').classList.contains('d-none'),false);
        assert.equal(form.elements.namedItem('password').value,'');
        assert.equal(w.document.querySelectorAll('#register-form input,#register-form select').length,6);
        assert.ok([...form.querySelectorAll('input,select')].every(control=>control.labels.length));
        w.document.getElementById('create-another-account').click();
        assert.equal(form.elements.namedItem('role').value,chosen);
        assert.equal(form.querySelector('[type=submit]').disabled,false);
        dom.window.close();
    });
}
test('teacher creation rejects an injected administrator role without making a request',async()=>{
    const {dom,w}=await fixture('register.html');
    const token='synthetic.'+Buffer.from(JSON.stringify({exp:Math.floor(Date.now()/1000)+3600,role:'teacher'})).toString('base64url')+'.synthetic';
    w.localStorage.setItem('token',token);w.localStorage.setItem('user',JSON.stringify({id:7,role:'teacher'}));
    let requests=0;w.fetch=async()=>{requests++;return reply({});};
    w.eval(read('static/js/auth.js').replace('export class AuthService','class AuthService'));
    const f=w.document.getElementById('register-form');
    const role=f.elements.namedItem('role');assert.equal(role.value,'student');assert.equal(role.disabled,true);
    role.add(new w.Option('Admin','admin'));role.value='admin';
    f.dispatchEvent(new w.Event('submit',{cancelable:true}));await new Promise(r=>setImmediate(r));
    assert.equal(requests,0);assert.match(w.document.getElementById('error-msg').textContent,/create accounts/);
    assert.equal(w.AuthService.loginDestination('https://attacker.invalid/'),'/dashboard.html');
    assert.equal(w.AuthService.loginDestination('/session_player.html?content_id=8&plan_id=4'),'/session_player.html?content_id=8&plan_id=4');
    dom.window.close();
});
