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
        w.fetch=async(url,options)=>{if (url.includes('role=teacher')) return reply([]);calls.push(JSON.parse(options.body));return reply(succeed?{id:8}:{detail:'Retry'},succeed?200:500);};
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
        assert.equal(w.document.querySelectorAll('#register-form input,#register-form select').length,7);
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
async function sessionFixture(query='?content_id=8&plan_id=4', withHelp=false) {
    const context=await fixture('session_player.html',query); const w=context.w;
    const calls=[];let progressFails=false;
    w.fetch=async(url,options={})=>{calls.push({url,method:options.method||'GET',body:options.body});
        if(url.endsWith('/tree'))return reply({id:4,title:'Course',contents:[{id:7,title:'Earlier',phase_index:0,order_index:0},{id:8,title:'Current',phase_index:0,order_index:1},{id:9,title:'Later',phase_index:0,order_index:2}]});
        if(url.endsWith('/my-progress'))return reply({completed_content_ids:[]});
        if(url==='/api/content/8')return reply({id:8,title:'Current',content_type:'lesson',content_data:{content:'Synthetic'}});
        if(url.includes('/history')||url.includes('/annotations'))return reply([]);
        if(url==='/api/learning/start')return reply({id:30,notes:''});
        if(url.endsWith('/progress')&&progressFails)return reply({detail:'Retry progress'},500);
        return reply({});};
    if(withHelp)w.eval(read('static/js/learning-help.js'));
    w.eval(read('static/js/session.js'));await w.initSession();calls.length=0;
    return {...context,calls,failProgress:value=>{progressFails=value;}};
}

test('learner sees partial selection without falsely certifying source support', async()=>{
    const {dom,w}=await sessionFixture();
    const data={objectives:['Explain the recorded amount'],sections:[{title:'Facts',content:'Valid saved explanation.'}]};
    const render=()=>w.renderSessionContent({title:'Current',content_type:'lesson',content_data:data,source_selection:{supplied_characters:100,source_characters:1000,use_coverage:'partial'}});
    render();render();
    const body=w.document.getElementById('session-content-body');
    assert.match(body.textContent,/Valid saved explanation/);
    assert.match(body.textContent,/100\/1000/);
    assert.match(body.textContent,/Partial source/);
    assert.match(body.textContent,/does not prove/);
    assert.match(body.textContent,/Explain the recorded amount/);
    assert.equal(body.querySelectorAll('[data-generation-notice]').length,1);
    w.renderSessionContent({title:'Manual',content_type:'lesson',content_data:{body:'Teacher-authored text'}});
    assert.equal(body.querySelector('[data-generation-notice]'),null);
    await new Promise(resolve=>setImmediate(resolve));
    dom.window.close();
});
test('Complete and next use the same completion and progress transition; repeat is idempotent',async()=>{
    const {dom,w,calls,failProgress}=await sessionFixture();
    failProgress(true);await w.confirmEndSession();
    assert.equal(calls.filter(c=>c.url.endsWith('/end')).length,1);
    assert.equal(w.toasts.at(-1)[1],'danger');
    assert.equal(w.document.getElementById('session-notes').disabled,true);
    assert.match(w.document.getElementById('session-transition-status').textContent,/retry Complete/);
    failProgress(false);await w.confirmEndSession();await w.confirmEndSession();
    assert.equal(calls.filter(c=>c.url.endsWith('/end')).length,1);
    assert.equal(calls.filter(c=>c.url.endsWith('/progress')).length,2);
    assert.equal(JSON.parse(calls.find(c=>c.url.endsWith('/progress')).body).completed_content_id,8);
    dom.window.close();
    const next=await sessionFixture();await next.w.navigatePlanContent(1);
    assert.equal(next.calls.filter(c=>c.url.endsWith('/end')).length,1);
    assert.equal(next.calls.filter(c=>c.url.endsWith('/progress')).length,1);next.dom.window.close();
});
test('Previous and pause preserve notes without marking a lesson complete',async()=>{
    for(const action of ['previous','pause']){
        const {dom,w,calls}=await sessionFixture();w.document.getElementById('session-notes').value='Keep my notes';
        if(action==='previous')await w.navigatePlanContent(-1);else await w.pauseSession();
        assert.equal(calls.filter(c=>c.url.endsWith('/end')||c.url.endsWith('/progress')).length,0);
        assert.equal(calls.find(c=>c.url.endsWith('/notes')).method,'PATCH');dom.window.close();
    }
});
test('Annotations are private by default and failed saves keep visible retryable text',async()=>{
    const {dom,w}=await sessionFixture();assert.equal(w.document.getElementById('annotation-public').checked,false);
    let payload;w.fetch=async(url,options)=>{payload=JSON.parse(options.body);return reply({detail:'Failed'},500);};
    w.document.getElementById('annotation-input').value='Private question';await w.addAnnotation();
    assert.equal(payload.is_public,false);assert.equal(w.document.getElementById('annotation-input').value,'Private question');
    assert.match(w.document.getElementById('annotation-status').textContent,/not saved/);dom.window.close();
});
for(const completed of [[3],[1,2,3]])test('Continue resolves pending identities and course completion: '+completed,async()=>{
    const {dom,w}=await fixture('dashboard.html');w.isTeacherOrAdmin=false;
    const source=read('static/js/dashboard.js');w.eval(source.slice(source.indexOf('let activeContinuePlan = null;'),source.indexOf('function renderProgressTimeline')));w.renderProgressTimeline=()=>{};
    w.fetch=async url=>reply(url.endsWith('/tree')?{id:4,title:'Course',contents:[{id:1,title:'First unfinished'},{id:2,title:'Second'},{id:3,title:'Third'}]}:url.endsWith('/my-progress')?{completed_content_ids:completed}:[{id:4}]);
    await w.loadContinueLearning();assert.equal(w.document.getElementById('continue-next-title').textContent,completed.length===3?'Course completed':'First unfinished');
    assert.equal(w.document.getElementById('continue-btn').disabled,completed.length===3);dom.window.close();
});
test('Dashboard grading cards link to submission and retain the current filter',async()=>{
    const {dom,w}=await fixture('dashboard.html');w.currentGradingStatusFilter='pending';w.escapeHtml=w.SLMRender.escape;w.getGradingStatusLabel=s=>s;w.getGradingStatusBadgeClass=()=>'';
    const source=read('static/js/dashboard.js');w.eval(source.slice(source.indexOf('function renderGradingQueue'),source.indexOf('function applyGradingFilter')));
    w.renderGradingQueue([{id:9,student_name:'Synthetic',assessment_title:'Essay',status:'submitted'}]);
    const link=w.document.querySelector('#grading-list a');assert.equal(link.pathname,'/grading.html');assert.equal(link.search,'?submission_id=9&filter=pending');
    assert.ok([...w.document.querySelectorAll('#settings-tabs .tab,#grading-filter-tabs .tab')].every(node=>node.tagName==='BUTTON'&&node.type==='button'));dom.window.close();
});
test('saved unassigned draft stays editable and updates the same plan before review',async()=>{
    const {dom,w}=await fixture('study_plan_builder.html','?id=5');w.AuthService.getRole=()=> 'teacher';
    const calls=[];w.fetch=async(url,options={})=>{calls.push({url,options});
        if(url.endsWith('/tree'))return reply({id:5,title:'Draft',description:'Before',is_public:false,phases:[{name:'One'}],contents:[{id:1,title:'First',content_type:'lesson',phase_index:0,order_index:0}]});
        if(url.endsWith('/workflow'))return reply({status:options.method?'reviewed':'draft',read_only:false});
        if(options.method==='PUT')return reply({id:5});
        return reply([{id:1,title:'First',content_type:'lesson'}]);};
    w.eval(read('static/js/study_plan_builder.js').replace("import { AuthService } from './auth.js';",''));
    w.document.dispatchEvent(new w.Event('DOMContentLoaded'));await new Promise(r=>setImmediate(r));
    const title=w.document.getElementById('plan-title');assert.equal(title.disabled,false);
    title.value='Revised';title.dispatchEvent(new w.Event('input',{bubbles:true}));
    await w.planWorkflow('review');
    const update=calls.find(call=>call.options.method==='PUT');assert.equal(update.url,'/api/study-plans/5');assert.equal(JSON.parse(update.options.body).title,'Revised');
    assert.ok(calls.indexOf(update)<calls.findIndex(call=>call.options.method==='POST'));
    assert.equal(w.document.getElementById('save-plan-btn').disabled,false);dom.window.close();
});
test('session renders canonical sections before legacy body and applies pinned session snapshot',async()=>{
    const {dom,w}=await sessionFixture();
    w.renderSessionContent({title:'Pinned lesson',content_type:'lesson',content_data:{content:'Obsolete flattened body',sections:[{title:'Step',content:'Canonical section'}],objectives:['Explain it']}});
    assert.match(w.document.getElementById('session-content-body').textContent,/Canonical section/);
    assert.match(w.document.getElementById('session-content-body').textContent,/Explain it/);
    assert.doesNotMatch(w.document.getElementById('session-content-body').textContent,/Obsolete/);
    w.fetch=async url=>url.includes('/annotations')?reply([]):reply({id:30,notes:'Pinned notes',content_snapshot:{title:'Saved version',content_type:'lesson',content_data:{sections:[{title:'Snapshot',content:'Original lesson'}]}}});
    await w.restoreSession(30);assert.equal(w.document.getElementById('session-content-title').textContent,'Saved version');assert.match(w.document.getElementById('session-content-body').textContent,/Original lesson/);await new Promise(r=>setImmediate(r));dom.window.close();
});
test('tutor uses the tree contract, clears old conversation and rejects late context replies',async()=>{
    const {dom,w}=await fixture('dashboard.html');w.escapeHtml=w.SLMRender.escape;w.setLearningContext=()=>{};
    const source=read('static/js/dashboard.js');w.eval(source.slice(source.indexOf('// --- AI TUTOR ---'),source.indexOf('// Old settings logic removed.')));
    const plan=w.document.getElementById('tutor-study-plan');plan.add(new w.Option('One',4));plan.add(new w.Option('Two',5));plan.value='4';
    let release;const calls=[];
    w.fetch=async(url,options)=>{calls.push({url,options});
        if(url.endsWith('/cancel'))return reply({request_id:url.split('/').at(-2),status:'cancelled',provider_may_continue:true});
        if(url==='/api/study-plans/4/tree')return reply({contents:[{id:8,title:'First'}]});
        if(url==='/api/study-plans/5/tree')return reply({contents:[{id:9,title:'Second'}]});
        if(url.endsWith('/assistance-policy'))return reply({mode:'hints_only',active_assessment_ids:[]});
        if(url.startsWith('/api/ai/context'))return reply({source:{source_version:'revision-v1',title:'Current',available_sections:[{id:'section-1',title:'One',characters:30}],included_characters:30,total_characters:30}});
        return await new Promise(resolve=>{release=()=>resolve(reply({response:'Outdated answer',status:'suggestion'}));});};
    await w.loadTutorContentItems();assert.equal(w.document.querySelector('#tutor-content option[value="8"]').textContent,'First');
    await w.refreshTutorPolicy();
    const section=w.document.querySelector('#tutor-source-sections input');assert.ok(section);section.checked=true;section.dispatchEvent(new w.Event('change'));
    w.document.getElementById('chat-input').value='Old lesson question';w.document.getElementById('chat-form').dispatchEvent(new w.Event('submit',{cancelable:true}));
    await new Promise(r=>setImmediate(r));plan.value='5';await w.loadTutorContentItems();release();await new Promise(r=>setImmediate(r));
    assert.equal(w.document.querySelector('#tutor-content option[value="8"]'),null);assert.ok(w.document.querySelector('#tutor-content option[value="9"]'));
    assert.doesNotMatch(w.document.getElementById('chat-history').textContent,/Outdated answer|Old lesson question/);
    assert.ok(calls.some(call=>call.url==='/api/study-plans/4/tree'));
    const sent=JSON.parse(calls.find(call=>call.url==='/api/ai/chat').options.body);assert.equal(sent.source_version,'revision-v1');assert.deepEqual(sent.section_ids,['section-1']);
    assert.match(w.document.getElementById('tutor-source-status').textContent,/not verified/);dom.window.close();
});
test('language changes update html lang and retain choice when browser storage fails',async()=>{
    const {dom,w}=await fixture('login.html');w.eval(read('static/js/i18n.js'));
    w.fetch=async()=>reply({recovery:{log_in:'Iniciar sesión'}});await w.I18n.setLanguage('es');w.I18n.translatePage();
    assert.equal(w.document.documentElement.lang,'es');assert.equal(w.localStorage.getItem('slm_language'),'es');
    w.Storage.prototype.setItem=()=>{throw new Error('blocked');};w.fetch=async()=>reply({recovery:{log_in:'Log in'}});await w.I18n.setLanguage('en');
    assert.equal(w.document.documentElement.lang,'en');assert.equal(w.document.querySelector('[data-i18n="recovery.log_in"]').textContent,'Log in');dom.window.close();
});
test('source preview failure blocks contextual requests and preserves the learner question',async()=>{
    const {dom,w}=await fixture('dashboard.html');w.escapeHtml=w.SLMRender.escape;w.setLearningContext=()=>{};
    const source=read('static/js/dashboard.js');w.eval(source.slice(source.indexOf('// --- AI TUTOR ---'),source.indexOf('// Old settings logic removed.')));
    const plan=w.document.getElementById('tutor-study-plan');plan.add(new w.Option('One',4));plan.value='4';
    let postCount=0;w.fetch=async(url,options={})=>{
        if(options.method==='POST')postCount++;
        if(url.endsWith('/assistance-policy'))return reply({mode:'hints_only',active_assessment_ids:[]});
        return reply({detail:'Source unavailable'},500);
    };
    await w.refreshTutorSource();await w.refreshTutorPolicy();
    const input=w.document.getElementById('chat-input');input.value='Keep my question';w.document.getElementById('chat-form').dispatchEvent(new w.Event('submit',{cancelable:true}));
    await new Promise(r=>setImmediate(r));assert.equal(postCount,0);assert.equal(input.value,'Keep my question');assert.equal(w.document.querySelector('#chat-form button').disabled,true);dom.window.close();
});
test('library editing follows the server can_edit decision, including admin-owned foreign content',async()=>{
    const {dom,w}=await fixture('dashboard.html');w.escapeHtml=w.SLMRender.escape;w.currentUserId=7;w.isTeacherOrAdmin=true;
    const source=read('static/js/dashboard.js');w.eval(source.slice(source.indexOf('function applyLibraryPermissionUI'),source.indexOf('// --- STUDENT Q&A ---')));
    const root=w.document.createElement('div');root.innerHTML='<div data-can-edit="false" data-creator-id="7"><button onclick="editContent(1)">Edit own assigned</button></div><div data-can-edit="true" data-creator-id="9"><button onclick="editContent(2)">Edit admin-permitted</button></div>';
    w.applyLibraryPermissionUI(root);assert.equal(root.querySelector('[data-can-edit=false] button').classList.contains('hidden'),true);assert.equal(root.querySelector('[data-can-edit=true] button').classList.contains('hidden'),false);dom.window.close();
});
test('lesson mounts contextual help with pinned session ID without navigation or losing notes',async()=>{
    const {dom,w}=await sessionFixture('?content_id=8&plan_id=4',true);const calls=[];
    w.fetch=async url=>{calls.push(url);return reply(url.includes('/context?')?{source:{id:8,title:'Current',source_version:'pinned-v1',available_sections:[{id:'s-1',title:'Pinned section',characters:20}],references:['s-1'],included_characters:20,total_characters:20,truncated:false}}:{mode:'hints_only',active_assessment_ids:[]});};
    const notes=w.document.getElementById('session-notes');notes.value='Continue my thinking';notes.dispatchEvent(new w.Event('input'));
    const host=w.document.getElementById('session-help-host');host.querySelector('[data-i18n="help_panel.tutor"]').click();await new Promise(r=>setImmediate(r));
    assert.equal(host.querySelector('section').hidden,false);assert.ok(calls.some(url=>url.includes('session_id=30')&&url.includes('content_id=8')&&url.includes('study_plan_id=4')));
    assert.equal(w.location.pathname,'/session_player.html');assert.equal(notes.value,'Continue my thinking');
    host.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
    assert.equal(host.querySelector('section').hidden,true);assert.equal(notes.value,'Continue my thinking');assert.equal(w.document.activeElement.id,'session-content-title');dom.window.close();
});
test('admin teacher assignment shows current owner, permits explicit removal and ignores stale confirmation',async()=>{
    const {dom,w}=await fixture('dashboard.html');w.AuthService.getRole=()=> 'admin';w.currentStudentId=8;let confirm;
    w.showConfirm=async()=>confirm;const calls=[];w.fetch=async(url,options={})=>{calls.push({url,options});return reply(options.method?{student_id:8,teacher_id:null}:[{id:9,first_name:'Synthetic',last_name:'Teacher',username:'teacher'}]);};
    const source=read('static/js/dashboard.js');w.eval(source.slice(source.indexOf('let savingStudentTeacher = false;'),source.indexOf("if (!dashboardStartupFailed && document.readyState !== 'loading')")));
    await w.loadStudentTeacher({id:8,teacher_id:9});assert.equal(w.document.getElementById('student-teacher-select').value,'9');
    confirm=true;w.document.getElementById('student-teacher-select').value='';await w.saveStudentTeacher();
    const request=calls.find(call=>call.options.method==='PUT');assert.equal(request.url,'/api/students/8/teacher');assert.equal(JSON.parse(request.options.body).teacher_id,null);
    w.showConfirm=async()=>{w.currentStudentId=10;return true;};await w.saveStudentTeacher();assert.equal(calls.filter(call=>call.options.method==='PUT').length,1);dom.window.close();
});

test('dashboard teacher help blocks duplicate clicks and retries the same request identity',async()=>{
 const {dom,w}=await fixture('dashboard.html');w.getLearningContext=()=>({contentId:8,studyPlanId:4});w.bootstrap={Modal:{getInstance:()=>({hide(){}})}};
 const source=read('static/js/dashboard.js');w.eval(source.slice(source.indexOf('// Help requests keep one identity'),source.indexOf('// Initialize Help Modal')));
 const calls=[];let failure=true;w.fetch=async(url,options)=>{const payload=JSON.parse(options.body);calls.push(payload);return failure?reply({detail:'Lost response'},500):reply({id:55,student_id:7,client_request_id:payload.client_request_id,status:'open',content_id:payload.content_id,study_plan_id:payload.study_plan_id,request_text:`${payload.subject}: ${payload.description}`});};
 w.document.getElementById('help-subject').value='Synthetic subject';w.document.getElementById('help-desc').value='Keep my question';const first=w.submitHelpRequest();await w.submitHelpRequest();await first;
 assert.equal(calls.length,1);assert.equal(w.document.getElementById('help-desc').value,'Keep my question');failure=false;await w.submitHelpRequest();assert.equal(calls.length,2);assert.equal(calls[0].client_request_id,calls[1].client_request_id);assert.equal(w.document.getElementById('help-desc').value,'');dom.window.close();
});
