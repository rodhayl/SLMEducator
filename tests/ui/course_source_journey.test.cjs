/* Synthetic DOM/API contracts for source preservation. No provider calls. */
const {test}=require('node:test');const assert=require('node:assert/strict');
const fs=require('node:fs');const path=require('node:path');const {JSDOM,VirtualConsole}=require('jsdom');
const root=path.resolve(__dirname,'../../src/web');const read=p=>fs.readFileSync(path.join(root,p),'utf8');
const manifest={filename:'synthetic.md',extracted_text:'[section-1]\nEarlier paragraph.\n\n[section-2]\nLater important section.',source_version:'a'.repeat(64),sections:[{reference:'section-1',text:'Earlier paragraph.'},{reference:'section-2',text:'Later important section.'}],coverage:'partial',truncated:true,unreadable_pages:[3],total_pages:3,parser:'synthetic',char_count:45};
const reply=(data,status=200)=>({ok:status>=200&&status<300,status,json:async()=>data});
async function fixture(){
 const dom=new JSDOM(read('course_designer.html'),{url:'http://localhost/course_designer.html',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:new VirtualConsole()});await new Promise(r=>setImmediate(r));const w=dom.window;
 w.AuthService={getUser:()=>({id:7,role:'teacher'}),getRole:()=> 'teacher',getToken:()=> 'synthetic',isAuthenticated:()=>true};w.I18n={t:k=>k};w.showToast=()=>{};w.showConfirm=async()=>true;
 for(const p of ['static/vendor/dompurify@3.4.16/purify.min.js','static/vendor/marked@15.0.12/marked.min.js','static/js/safe-render.js','static/js/learning-client.js'])w.eval(read(p));
 w.syntheticManifest=manifest;w.eval(read('static/js/course_designer.js') + "\ncourseOwner=SLMClient.account();createdStudyPlanId=5;currentConfig={subject:'Synthetic',grade_level:'beginner'};generatedOutline={title:'Synthetic course',units:[{title:'One',lessons:[{title:'A'}]}]};sourceCoverage=syntheticManifest;sourceMaterialText=syntheticManifest.extracted_text;generationTasks=[{unit:0,lesson:0,status:'saved'}]; window.sourceState=()=>({sourceCoverage,sourceDocumentId,generationTasks});");
 return {dom,w};
}
test('full extracted manifest is saved before generation and document identity survives retry',async()=>{
 const {dom,w}=await fixture();const calls=[];w.fetch=async(url,options={})=>{calls.push({url,options});return reply(url.endsWith('/source')?{document_id:'c'.repeat(64),source:manifest,review_required:true}:{success:true,saved_content_ids:[10]});};
 assert.equal(await w.generateAndSaveLesson({title:'A'},0),true);assert.equal(await w.generateAndSaveLesson({title:'B'},0),true);
 assert.equal(calls[0].url,'/api/study-plans/5/source');assert.equal(calls.filter(c=>c.url.endsWith('/source')).length,1);assert.deepEqual(JSON.parse(calls[0].options.body),manifest);
 for(const call of calls.filter(c=>c.url.includes('full-topic-package'))){const body=JSON.parse(call.options.body);assert.equal(body.source_document_id,'c'.repeat(64));assert.equal(body.source_material,manifest.extracted_text);}
 assert.equal(w.SLMClient.drafts.read('course','designer','active').sourceCoverage.sections[1].text,'Later important section.');dom.window.close();
});
for(const status of [401,500])test('source persistence HTTP '+status+' blocks provider generation without losing manifest',async()=>{
 const {dom,w}=await fixture();const calls=[];w.fetch=async(url)=>{calls.push(url);return reply({detail:'Save failed'},status);};assert.equal(await w.generateAndSaveLesson({title:'A'},0),false);assert.equal(calls.length,1);assert.ok(calls[0].endsWith('/source'));assert.equal(w.sourceState().sourceCoverage.sections[1].text,'Later important section.');dom.window.close();
});
for(const confirmed of [false,true])test('source replacement is explicit and never starts generation: '+confirmed,async()=>{
 const {dom,w}=await fixture();w.showConfirm=async()=>confirmed;const calls=[];const updated={...manifest,source_version:'b'.repeat(64),extracted_text:'[section-new]\nNew source',sections:[{reference:'section-new',text:'New source'}]};
 Object.defineProperty(w.document.getElementById('replace-source-file'),'files',{value:[new w.File(['Synthetic'],'new.md',{type:'text/markdown'})]});
 w.fetch=async(url,options={})=>{calls.push({url,options});return reply(url.endsWith('/workflow')?{read_only:false,status:'draft'}:url.includes('/upload/')?updated:{document_id:'d'.repeat(64),source:updated,review_required:true});};
 await w.replaceCourseSource();assert.equal(calls.some(c=>c.url.includes('full-topic-package')),false);
 if(confirmed){assert.equal(w.sourceState().generationTasks[0].status,'pending');assert.equal(w.sourceState().sourceDocumentId,'d'.repeat(64));assert.match(w.document.getElementById('source-replacement-status').textContent,/Previous content is preserved/);assert.equal(w.document.getElementById('retry-generation').textContent,'Generate new version');}
 else{assert.equal(calls.length,1);assert.equal(w.sourceState().generationTasks[0].status,'saved');assert.equal(w.sourceState().sourceCoverage.source_version,'a'.repeat(64));}dom.window.close();
});
test('assigned source replacement stops before upload and keeps completed task identities',async()=>{
 const {dom,w}=await fixture();Object.defineProperty(w.document.getElementById('replace-source-file'),'files',{value:[new w.File(['Synthetic'],'new.md')]});const calls=[];w.fetch=async url=>{calls.push(url);return reply({read_only:true,status:'published'});};await w.replaceCourseSource();assert.equal(calls.length,1);assert.equal(w.sourceState().generationTasks[0].status,'saved');assert.match(w.document.getElementById('source-replacement-status').textContent,/Assigned courses are fixed/);dom.window.close();
});
