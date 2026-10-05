/* Teacher corrections preserve instructional work; DOM HTTP is synthetic. */
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM,VirtualConsole}=require('jsdom');
const root=path.resolve(__dirname,'../../src/web');
const read=file=>fs.readFileSync(path.join(root,file),'utf8');
async function fixture(type,data){
 const dom=new JSDOM(read('dashboard.html'),{url:'http://localhost/dashboard.html',runScripts:'outside-only',virtualConsole:new VirtualConsole()});
 await new Promise(resolve=>setImmediate(resolve));
 const w=dom.window;w.AuthService={getToken:()=> 'synthetic',getUser:()=>({id:7})};w.I18n={t:key=>key};w.showToast=()=>{};
 for(const file of ['static/vendor/dompurify@3.4.16/purify.min.js','static/vendor/marked@15.0.12/marked.min.js','static/js/safe-render.js','static/js/learning-client.js','static/js/practice.js'])w.eval(read(file));
 w.bootstrap={Modal:class{constructor(element){this.element=element;}static getInstance(){return{hide(){}};}show(){}hide(){this.element.dispatchEvent(new w.Event('hidden.bs.modal'));}dispose(){}}};w.loadLibrary=async()=>{};
 const calls=[];w.fetch=async(url,options)=>{if(options?.method==='PUT')calls.push(JSON.parse(options.body));return{ok:true,json:async()=>({id:8,title:'Draft',content_type:type,content_data:data,can_edit:true,difficulty:1})};};
 const code=read('static/js/dashboard.js');w.eval(code.slice(code.indexOf('// Edit content'),code.indexOf('// Delete content')));
 await w.editContent(8);return{dom,w,calls};
}
test('lesson correction presents every visible field and keeps its source receipt',async()=>{
 const generation={source_usage:{source_document_id:'synthetic',source_characters:50,ranges:[{start:0,end:50}]}};
 const {dom,w,calls}=await fixture('lesson',{sections:[{title:'Facts',content:'Observed amount.'}],objectives:['Explain the observation'],summary:'Summary of facts',vocabulary:[{term:'Half',definition:'One of two equal parts.'}],generation});
 const editor=w.document.getElementById('edit-content-body');
 assert.match(editor.value,/Explain the observation/);assert.match(editor.value,/One of two equal parts/);assert.match(editor.value,/Summary of facts/);
 editor.value=editor.value.replace('Observed amount.','Corrected observed amount.');await w.saveContentEdit();
 assert.deepEqual(calls[0].content_data.generation,generation);
 assert.match(calls[0].content_data.body,/Corrected observed amount/);assert.match(calls[0].content_data.body,/One of two equal parts/);
 dom.window.close();
});
test('exercise correction preserves executable question, choices, key and hints',async()=>{
 const {dom,w,calls}=await fixture('exercise',{question:'Choose two',type:'multiple_choice',options:{first:'One',second:'Two'},correct_answer:'second',hints:['Count the groups','Add them'],explanation:'Two groups.'});
 await w.saveContentEdit();const saved=calls[0].content_data;
 assert.equal(saved.question,'Choose two');assert.deepEqual(saved.options,['One','Two']);assert.equal(saved.correct_answer,'Two');assert.deepEqual(saved.hints,['Count the groups','Add them']);
 dom.window.close();
});
test('practice uses progressive hints without revealing all hints at once',async()=>{
 const {dom,w}=await fixture('exercise',{question:'Count groups',type:'short_answer',correct_answer:'12'});
 const host=w.document.createElement('div');w.SLMPractice.render(host,{question:'Count groups',type:'short_answer',hints:['Start with one group','Count the groups','Multiply'],correct_answer:'12'});
 const hint=host.querySelector('button');hint.click();assert.match(host.textContent,/Start with one group/);assert.doesNotMatch(host.textContent,/Multiply|12/);
 hint.click();assert.match(host.textContent,/Count the groups/);hint.click();assert.match(host.textContent,/Multiply/);assert.equal(hint.disabled,true);dom.window.close();
});

test('failed correction keeps text and prevents overlapping saves',async()=>{
 const {dom,w,calls}=await fixture('lesson',{body:'Valid work'});
 let release;w.fetch=async()=>{calls.push('PUT');await new Promise(resolve=>{release=resolve;});return{ok:false,json:async()=>({detail:'Synthetic failure'})};};
 const editor=w.document.getElementById('edit-content-body');editor.value='Corrected work';
 const pending=w.saveContentEdit();await w.saveContentEdit();assert.equal(calls.length,1);
 assert.equal(w.document.getElementById('save-content-edit').disabled,true);release();await pending;
 assert.equal(editor.value,'Corrected work');assert.equal(w.document.getElementById('save-content-edit').disabled,false);
 w.fetch=async(url,options)=>{calls.push(JSON.parse(options.body));return{ok:true};};await w.saveContentEdit();assert.equal(calls[1].content_data.body,'Corrected work');dom.window.close();
});

test('progressive hints restore with independent answers after interruption',async()=>{
 const {dom,w}=await fixture('exercise',{question:'Count',correct_answer:'12'});
 const host=w.document.createElement('div');const exercise={question:'Count',type:'short_answer',hints:['Count one group','Multiply'],correct_answer:'12'};
 w.SLMPractice.render(host,exercise);await w.SLMPractice.bindAttempt('7',8,9);
 host.querySelector('textarea').value='My attempt';host.querySelector('textarea').dispatchEvent(new w.Event('input'));host.querySelector('button').click();
 w.SLMPractice.render(host,exercise);
 const restoration=w.SLMPractice.bindAttempt('7',8,9);
 w.document.querySelector('[aria-labelledby^="draft-choice-"] .modal-footer button.btn-primary').click();await restoration;
 assert.equal(host.querySelector('textarea').value,'My attempt');assert.match(host.textContent,/Count one group/);
 host.querySelector('button').click();assert.match(host.textContent,/Multiply/);assert.equal(host.querySelector('button').disabled,true);dom.window.close();
});
