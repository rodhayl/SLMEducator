import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { createQueryClient } from '@/lib/query';
import { ApiError } from '@/lib/api';
import { TutorPage } from '@/features/tutor/TutorPage';
import { locales } from '@/features/tutor/locales';
const auth=vi.hoisted(()=>({status:'authenticated' as 'authenticated'|'locked',scope:'7:1',credentialEpoch:1,user:{id:7,role:'student',username:'synthetic',first_name:'',last_name:'',email:'',grade_level:null},api:{get:vi.fn(),post:vi.fn(),put:vi.fn(),delete:vi.fn()},registerResource:vi.fn(()=>()=>undefined)}));
vi.mock('@/app/AuthProvider',()=>({useAuth:()=>({...auth,getSnapshot:()=>auth})}));
const source={id:11,title:'Synthetic lesson',type:'lesson',source_version:'a'.repeat(64),fragment_hash:'b'.repeat(64),content_data:'Bounded source',included_characters:14,total_characters:14,truncated:false,selection:'bounded_default',references:['content:11/section-1'],available_sections:Array.from({length:13},(_,i)=>({id:`content:11/section-${i+1}`,title:`Section ${i+1}`,characters:14}))};
const question={id:51,title:'Existing question',content_type:'qa',creator_id:7,is_personal:true,shared_with_teacher:false,can_edit:true,difficulty:1,content_data:{question:'Why?',answer:'Saved answer'}};
function receipt(id:string,extra={}){return{request_id:id,status:'completed',elapsed_seconds:1,provider:'synthetic',model:'fixture',tokens_used:null,max_output_tokens:800,requests_used_today:1,requests_limit_daily:100,provider_may_continue:false,cost_known:false,...extra};}
function result(payload:Record<string,unknown>,extra={}){return{receipt:receipt(String(payload.client_request_id)),source:payload.content_id?source:null,assistance_policy:{mode:'explanations'},effective_assistance:payload.assistance,status:'suggestion',response:'Synthetic suggestion',...extra};}
function deferred<T>(){let resolve!:(value:T)=>void;const promise=new Promise<T>(done=>{resolve=done;});return{promise,resolve};}
async function mount(path='/tutor',language='en'){
 const i18n=createInstance();await i18n.init({lng:language,fallbackLng:'en',resources:{en:{tutor:locales.en,translation:{cancel:'Cancel',errors:{failed:'Safe error',uncertain:'Outcome unconfirmed',invalidResponse:'Invalid response'}}},es:{tutor:locales.es}},interpolation:{escapeValue:false}});
 const client=createQueryClient(),tree=()=> <QueryClientProvider client={client}><I18nextProvider i18n={i18n}><MemoryRouter initialEntries={[path]}><TutorPage/></MemoryRouter></I18nextProvider></QueryClientProvider>;
 const view=render(tree());return{...view,rerenderApp:()=>view.rerender(tree()),client};
}
async function ready(){await waitFor(()=>expect(screen.getByRole('button',{name:'Ask tutor'})).toBeEnabled());}
async function ask(text='Original question'){fireEvent.change(screen.getByLabelText('What would you like help with?'),{target:{value:text}});fireEvent.click(screen.getByRole('button',{name:'Ask tutor'}));await waitFor(()=>expect(auth.api.post).toHaveBeenCalled());}
async function questions(){fireEvent.click(screen.getByRole('button',{name:'My questions'}));await waitFor(()=>expect(screen.getByRole('button',{name:'Save question'})).toBeEnabled());}
function draft(){fireEvent.change(screen.getByLabelText('Question title'),{target:{value:'New question title'}});fireEvent.change(screen.getByLabelText('My question'),{target:{value:'New question text'}});}
beforeEach(()=>{
 vi.clearAllMocks();auth.status='authenticated';auth.scope='7:1';auth.credentialEpoch=1;auth.user.id=7;auth.user.role='student';
 auth.api.get.mockImplementation(async(path:string)=>path==='/api/ai/assistance-policy'?{mode:'explanations'}:path==='/api/ai/usage'?{requests_used_today:0,requests_limit_daily:100,active_request_id:null}:path.startsWith('/api/ai/context?')?{source}:path==='/api/content/51'?question:[]);
 auth.api.delete.mockImplementation(async()=>({id:51,message:'Content deleted successfully'}));
 auth.api.put.mockImplementation(async(_path:string,payload:Record<string,unknown>)=>({...question,...payload}));
 auth.api.post.mockImplementation(async(path:string,payload:Record<string,unknown>)=>path==='/api/ai/chat'?result(payload):path==='/api/ai/answer-question'?{...result(payload),success:true,answer:'Suggested answer'}:{...question,id:52,title:payload.title,shared_with_teacher:payload.shared_with_teacher});
});
describe('Standalone tutor and student questions (synthetic, no providers)',()=>{
 it('supports free tutor with no course and only sends on an explicit action',async()=>{
  await mount();await ready();expect(auth.api.post).not.toHaveBeenCalled();expect(auth.api.get.mock.calls.some(([path])=>String(path).startsWith('/api/ai/context'))).toBe(false);
  await ask();await screen.findByText('Synthetic suggestion');expect(auth.api.post.mock.calls[0][1]).toMatchObject({message:'Original question',content_id:null,study_plan_id:null,section_ids:[],source_version:null,assistance:'hint',conversation_history:[]});
  expect(auth.api.post.mock.calls[0][1].client_request_id).toMatch(/^[\w-]+$/);expect(screen.getByLabelText('What would you like help with?')).toHaveValue('');expect(screen.getByText(locales.en.memoryOnly)).toBeVisible();
 });
 it('preserves manual question edits while an answer is pending',async()=>{
  const job=deferred<unknown>();auth.api.post.mockReturnValue(job.promise);await mount();await ready();await ask();const payload=auth.api.post.mock.calls[0][1];
  fireEvent.change(screen.getByLabelText('What would you like help with?'),{target:{value:'Later manual edit'}});await act(async()=>job.resolve(result(payload)));expect(await screen.findByText('Synthetic suggestion')).toBeVisible();expect(screen.getByLabelText('What would you like help with?')).toHaveValue('Later manual edit');
 });
 it('preserves dirty text through reauth, suppresses late response, and clears it on account switch',async()=>{
  const job=deferred<unknown>();auth.api.post.mockReturnValue(job.promise);const view=await mount();await ready();await ask('Private draft');const payload=auth.api.post.mock.calls[0][1];
  auth.status='locked';auth.credentialEpoch++;view.rerenderApp();expect(screen.queryByRole('textbox',{name:'What would you like help with?'})).not.toBeInTheDocument();await act(async()=>job.resolve(result(payload)));auth.status='authenticated';view.rerenderApp();expect(screen.getByLabelText('What would you like help with?')).toHaveValue('Private draft');expect(screen.queryByText('Synthetic suggestion')).not.toBeInTheDocument();expect(auth.api.post).toHaveBeenCalledTimes(1);
  auth.scope='8:2';auth.user.id=8;view.rerenderApp();await ready();expect(screen.getByLabelText('What would you like help with?')).toHaveValue('');
 });
 it('hiding tutor keeps an in-flight request and never automatically retries',async()=>{
  const job=deferred<unknown>();auth.api.post.mockReturnValue(job.promise);await mount();await ready();await ask();const payload=auth.api.post.mock.calls[0][1];fireEvent.click(screen.getByRole('button',{name:'My questions'}));await act(async()=>job.resolve(result(payload)));fireEvent.click(screen.getByRole('button',{name:'Tutor conversation'}));expect(await screen.findByText('Synthetic suggestion')).toBeVisible();expect(auth.api.post).toHaveBeenCalledTimes(1);expect(screen.getByLabelText('What would you like help with?')).toHaveValue('');
 });
 it('cancels local delivery truthfully and fences a provider response that arrives afterward',async()=>{
  const job=deferred<unknown>();auth.api.post.mockImplementation((path:string)=>path==='/api/ai/chat'?job.promise:Promise.resolve(receipt(path.split('/')[4],{status:'cancelled',provider_may_continue:true})));
  await mount();await ready();await ask();const payload=auth.api.post.mock.calls[0][1];fireEvent.click(screen.getByRole('button',{name:'Cancel AI request'}));expect(await screen.findByText(locales.en.cancelledMessage)).toBeVisible();await act(async()=>job.resolve(result(payload)));expect(screen.queryByText('Synthetic suggestion')).not.toBeInTheDocument();expect(screen.getByLabelText('What would you like help with?')).toHaveValue('Original question');
 });
 it('retries only the identical explicit request after an unknown receipt',async()=>{
  auth.api.post.mockImplementation(async(_path:string,payload:Record<string,unknown>)=>result(payload,{receipt:receipt('wrong-id')}));await mount();await ready();await ask();await screen.findByText(locales.en.receiptUnknown);const original=auth.api.post.mock.calls[0][1];fireEvent.change(screen.getByLabelText('What would you like help with?'),{target:{value:'New local words'}});expect(screen.getByRole('button',{name:'Ask tutor'})).toBeDisabled();fireEvent.click(screen.getByRole('button',{name:'Retry same request'}));await waitFor(()=>expect(auth.api.post).toHaveBeenCalledTimes(2));expect(auth.api.post.mock.calls[1][1]).toEqual(original);expect(screen.getByLabelText('What would you like help with?')).toHaveValue('New local words');
 });
 it('sends actual selected sections and rejects mismatched source delivery',async()=>{
  auth.api.get.mockImplementation(async(path:string)=>path==='/api/content/'?[{id:11,title:'Synthetic lesson',content_type:'lesson',difficulty:1,is_personal:false,creator_id:9}]:path.startsWith('/api/ai/context?')?{source}:path==='/api/ai/assistance-policy'?{mode:'explanations'}:path==='/api/ai/usage'?{requests_used_today:0,requests_limit_daily:100,active_request_id:null}:[]);
  await mount('/tutor?content_id=11');await ready();fireEvent.click(screen.getByText('Optional course and source material'));for(let i=1;i<=12;i++)fireEvent.click(screen.getByLabelText(`Section ${i}`,{exact:true}));expect(screen.getByLabelText('Section 13',{exact:true})).toBeDisabled();
  auth.api.post.mockImplementation(async(_path:string,payload:Record<string,unknown>)=>result(payload,{source:{...source,source_version:'c'.repeat(64)}}));await ask();expect(auth.api.post.mock.calls[0][1]).toMatchObject({content_id:11,source_version:source.source_version,section_ids:source.available_sections.slice(0,12).map(item=>item.id)});await screen.findByText(locales.en.changed);expect(screen.queryByText('Synthetic suggestion')).not.toBeInTheDocument();
 });
 it('retains a typed question but excludes old replies when the context changes',async()=>{
  await mount();await ready();await ask();await screen.findByText('Synthetic suggestion');fireEvent.change(screen.getByLabelText('What would you like help with?'),{target:{value:'Keep my words'}});fireEvent.click(screen.getByText('Optional course and source material'));fireEvent.change(screen.getByLabelText('Material'),{target:{value:''}});expect(screen.queryByText('Synthetic suggestion')).not.toBeInTheDocument();expect(screen.getByLabelText('What would you like help with?')).toHaveValue('Keep my words');
 });
 it('saves only student authored question fields and confirms the detail before reporting success',async()=>{
  auth.api.get.mockImplementation(async(path:string)=>path==='/api/content/52'?{...question,id:52,title:'New question title',content_data:{question:'New question text',answer:''}}:path==='/api/ai/assistance-policy'?{mode:'explanations'}:path==='/api/ai/usage'?{requests_used_today:0,requests_limit_daily:100,active_request_id:null}:[]);
  await mount();await questions();draft();fireEvent.click(screen.getByRole('button',{name:'Save question'}));await screen.findByText(locales.en.saved);expect(auth.api.post).toHaveBeenCalledWith('/api/content/',{title:'New question title',content_type:'qa',is_personal:true,shared_with_teacher:false,content_data:{question:'New question text',answer:''}},expect.objectContaining({signal:expect.any(AbortSignal)}));expect(auth.api.get).toHaveBeenCalledWith('/api/content/52',expect.anything());
 });
 it('keeps an AI suggestion separate from manual answer and saves it only after explicit use',async()=>{
  await mount();await questions();draft();fireEvent.change(screen.getByLabelText('Answer to save (optional)'),{target:{value:'My own answer'}});await waitFor(()=>expect(screen.getByRole('button',{name:'Ask AI for a suggestion'})).toBeEnabled());fireEvent.click(screen.getByRole('button',{name:'Ask AI for a suggestion'}));await screen.findByText('Suggested answer');expect(screen.getByLabelText('Answer to save (optional)')).toHaveValue('My own answer');expect(auth.api.post).toHaveBeenCalledTimes(1);expect(auth.api.post.mock.calls[0][0]).toBe('/api/ai/answer-question');fireEvent.click(screen.getByRole('button',{name:'Use suggestion in answer'}));const dialog=screen.getByRole('dialog');fireEvent.click(within(dialog).getByRole('button',{name:'Use suggestion in answer'}));expect(screen.getByLabelText('Answer to save (optional)')).toHaveValue('Suggested answer');expect(auth.api.post).toHaveBeenCalledTimes(1);
 });
 it('keeps unknown creates blocked and reconciles matching new own entries without posting again',async()=>{
  let created=false;auth.api.post.mockImplementation(async()=>{created=true;throw new ApiError(0,'network',true,'uncertain');});auth.api.get.mockImplementation(async(path:string)=>path==='/api/content/?content_type=qa'?(created?[{...question,id:52,title:'New question title'}]:[]):path==='/api/content/52'?{...question,id:52,title:'New question title',content_data:{question:'New question text',answer:''}}:path==='/api/ai/assistance-policy'?{mode:'explanations'}:path==='/api/ai/usage'?{requests_used_today:0,requests_limit_daily:100,active_request_id:null}:[]);
  await mount();await questions();draft();fireEvent.click(screen.getByRole('button',{name:'Save question'}));await screen.findByText(locales.en.saveUnknown);expect(screen.getByRole('button',{name:'Save question'})).toBeDisabled();fireEvent.click(screen.getByRole('button',{name:'Check saved content'}));await screen.findByText(locales.en.reviewMatches);fireEvent.click(screen.getByRole('button',{name:'Use this saved entry'}));await screen.findByText(locales.en.saved);expect(auth.api.post).toHaveBeenCalledTimes(1);
 });
 it('requires ownership, treats teacher-shared Q&A as read-only and never grants edits',async()=>{
  auth.user.role='teacher';auth.user.id=9;auth.api.get.mockImplementation(async(path:string)=>path==='/api/content/?content_type=qa'?[{...question,shared_with_teacher:true}]:path==='/api/content/51'?{...question,shared_with_teacher:true,can_edit:false}:path==='/api/ai/assistance-policy'?{mode:'explanations'}:[]);
  await mount('/tutor?tab=questions&question_id=51');await screen.findByText(locales.en.readOnly);expect(screen.queryByRole('button',{name:'Save question'})).not.toBeInTheDocument();expect(screen.queryByRole('textbox',{name:'My question'})).not.toBeInTheDocument();expect(auth.api.post).not.toHaveBeenCalled();expect(screen.getByText('Saved answer')).toBeVisible();
 });
 it('shows Spanish states and does not depend on a model selection gate',async()=>{await mount('/tutor','es');await waitFor(()=>expect(screen.getByRole('button',{name:'Preguntar al tutor'})).toBeEnabled());expect(screen.getByText(locales.es.freeHint)).toBeVisible();});

 it('restricts AI to hints during an attempt and blocks disabled assistance',async()=>{
  const normal=auth.api.get.getMockImplementation()!;
  auth.api.get.mockImplementation((path:string)=>path==='/api/ai/assistance-policy'?Promise.resolve({mode:'hints_only'}):normal(path));
  const view=await mount();await ready();expect(screen.getByLabelText('Type of support')).toBeDisabled();await ask();expect(auth.api.post.mock.calls[0][1].assistance).toBe('hint');await screen.findByText('Synthetic suggestion');
  auth.api.get.mockImplementation((path:string)=>path==='/api/ai/assistance-policy'?Promise.resolve({mode:'disabled'}):normal(path));await act(async()=>view.client.invalidateQueries({queryKey:[auth.scope,'tutor','policy']}));await waitFor(()=>expect(screen.getByRole('button',{name:'Ask tutor'})).toBeDisabled());expect(screen.getByText(locales.en.policy_disabled,{selector:'p[role="alert"]'})).toBeVisible();
 });
 it('bounds conversation history to the last five exchanges',async()=>{
  await mount();await ready();for(let i=0;i<7;i++){await ask(`Question ${i}`);await waitFor(()=>expect(screen.getByLabelText('What would you like help with?')).toHaveValue(''));}
  const last=auth.api.post.mock.calls.at(-1)![1];expect(last.conversation_history).toHaveLength(10);expect(last.conversation_history[0].content).toBe('Question 1');expect(last.conversation_history.at(-2).content).toBe('Question 5');
 });
 it('fences a late old-source result when the learner explicitly selects no source',async()=>{
  const job=deferred<unknown>();auth.api.post.mockReturnValue(job.promise);await mount('/tutor?content_id=11');await ready();await ask();const payload=auth.api.post.mock.calls[0][1];fireEvent.click(screen.getByText('Optional course and source material'));fireEvent.change(screen.getByLabelText('Material'),{target:{value:''}});await act(async()=>job.resolve(result(payload)));expect(screen.queryByText('Synthetic suggestion')).not.toBeInTheDocument();expect(screen.getByLabelText('What would you like help with?')).toHaveValue('Original question');expect(screen.getByRole('button',{name:'Retry same request'})).toBeDisabled();
 });
 it('rejects oversized context metadata and sends no provider request',async()=>{
  const normal=auth.api.get.getMockImplementation()!;auth.api.get.mockImplementation((path:string)=>path.startsWith('/api/ai/context?')?Promise.resolve({source:{...source,content_data:'x'.repeat(6001),included_characters:6001,total_characters:6001}}):normal(path));await mount('/tutor?content_id=11');await screen.findByText(locales.en.contextUnavailable);expect(screen.getByRole('button',{name:'Ask tutor'})).toBeDisabled();expect(auth.api.post).not.toHaveBeenCalled();
 });
 it('preserves all question fields while locked and drops them on account replacement',async()=>{
  const view=await mount();await questions();draft();fireEvent.change(screen.getByLabelText('Answer to save (optional)'),{target:{value:'Private answer'}});fireEvent.click(screen.getByLabelText('Share this question with my teacher'));auth.status='locked';auth.credentialEpoch++;view.rerenderApp();expect(screen.queryByRole('textbox',{name:'My question'})).not.toBeInTheDocument();auth.status='authenticated';view.rerenderApp();expect(screen.getByLabelText('My question')).toHaveValue('New question text');expect(screen.getByLabelText('Answer to save (optional)')).toHaveValue('Private answer');expect(screen.getByLabelText('Share this question with my teacher')).toBeChecked();auth.scope='8:2';auth.user.id=8;view.rerenderApp();await questions();expect(screen.getByLabelText('My question')).toHaveValue('');expect(screen.getByLabelText('Share this question with my teacher')).not.toBeChecked();
 });
 it('does not overwrite a manually changed question with a late AI result',async()=>{
  const job=deferred<unknown>();auth.api.post.mockReturnValue(job.promise);await mount('/tutor?tab=questions');await waitFor(()=>expect(screen.getByRole('button',{name:'Ask AI for a suggestion'})).toBeEnabled());draft();fireEvent.click(screen.getByRole('button',{name:'Ask AI for a suggestion'}));await waitFor(()=>expect(auth.api.post).toHaveBeenCalled());const payload=auth.api.post.mock.calls[0][1];fireEvent.change(screen.getByLabelText('My question'),{target:{value:'Different question'}});await act(async()=>job.resolve({...result(payload),success:true,answer:'Obsolete suggestion'}));expect(screen.queryByText('Obsolete suggestion')).not.toBeInTheDocument();expect(screen.getByLabelText('My question')).toHaveValue('Different question');expect(screen.getByRole('button',{name:'Retry same request'})).toBeDisabled();
 });
 it('updates only an owned personal QA and does not send the forbidden visibility field',async()=>{
  const normal=auth.api.get.getMockImplementation()!;let updated=false;auth.api.get.mockImplementation((path:string)=>path==='/api/content/?content_type=qa'?Promise.resolve([question]):path==='/api/content/51'?Promise.resolve({...question,shared_with_teacher:updated,content_data:{question:'Why?',answer:updated?'Edited answer':'Saved answer'}}):normal(path));auth.api.put.mockImplementation(async(_path:string,payload:Record<string,unknown>)=>{updated=true;return{...question,...payload};});await mount('/tutor?question_id=51');await screen.findByDisplayValue('Saved answer');fireEvent.change(screen.getByLabelText('Answer to save (optional)'),{target:{value:'Edited answer'}});fireEvent.click(screen.getByLabelText('Share this question with my teacher'));fireEvent.click(screen.getByRole('button',{name:'Save question'}));await screen.findByText(locales.en.saved);expect(auth.api.put.mock.calls[0][1]).toEqual({title:'Existing question',content_data:{question:'Why?',answer:'Edited answer'},shared_with_teacher:true});expect(auth.api.post).not.toHaveBeenCalled();
 });
 it('preserves newer manual text when save confirmation arrives',async()=>{
  const detail=deferred<unknown>();const normal=auth.api.get.getMockImplementation()!;auth.api.get.mockImplementation((path:string)=>path==='/api/content/52'?detail.promise:normal(path));await mount('/tutor?tab=questions');await waitFor(()=>expect(screen.getByRole('button',{name:'Save question'})).toBeEnabled());draft();fireEvent.click(screen.getByRole('button',{name:'Save question'}));await waitFor(()=>expect(auth.api.get).toHaveBeenCalledWith('/api/content/52',expect.anything()));fireEvent.change(screen.getByLabelText('My question'),{target:{value:'Newer unsaved edit'}});await act(async()=>detail.resolve({...question,id:52,title:'New question title',content_data:{question:'New question text',answer:''}}));await screen.findByText(locales.en.saved);expect(screen.getByLabelText('My question')).toHaveValue('Newer unsaved edit');
 });
 it('fences confirmed save continuation if the account changes during its readback',async()=>{
  const detail=deferred<unknown>();const normal=auth.api.get.getMockImplementation()!;auth.api.get.mockImplementation((path:string)=>path==='/api/content/52'?detail.promise:normal(path));const view=await mount('/tutor?tab=questions');await waitFor(()=>expect(screen.getByRole('button',{name:'Save question'})).toBeEnabled());draft();fireEvent.click(screen.getByRole('button',{name:'Save question'}));await waitFor(()=>expect(auth.api.get).toHaveBeenCalledWith('/api/content/52',expect.anything()));auth.scope='8:2';auth.user.id=8;view.rerenderApp();await act(async()=>detail.resolve({...question,id:52,title:'New question title',content_data:{question:'New question text',answer:''}}));expect(screen.queryByText(locales.en.saved)).not.toBeInTheDocument();expect(screen.getByLabelText('My question')).toHaveValue('');
 });
 it('does not mistake an old identical entry or another owner’s entry for an unknown new save',async()=>{
  const old={...question,title:'New question title',content_data:{question:'New question text',answer:''}};let created=false;const normal=auth.api.get.getMockImplementation()!;auth.api.get.mockImplementation((path:string)=>path==='/api/content/?content_type=qa'?Promise.resolve(created?[old,{...old,id:52,creator_id:8}]:[old]):normal(path));auth.api.post.mockImplementation(async()=>{created=true;throw new ApiError(0,'network',true,'uncertain');});await mount('/tutor?tab=questions');await waitFor(()=>expect(screen.getByRole('button',{name:'Save question'})).toBeEnabled());draft();fireEvent.click(screen.getByRole('button',{name:'Save question'}));await screen.findByText(locales.en.saveUnknown);fireEvent.click(screen.getByRole('button',{name:'Check saved content'}));await screen.findByText(locales.en.noMatch);expect(screen.queryByRole('button',{name:'Use this saved entry'})).not.toBeInTheDocument();expect(auth.api.post).toHaveBeenCalledTimes(1);
 });
 it('treats malformed save ownership as unconfirmed without fetching another owner’s receipt',async()=>{
  auth.api.post.mockResolvedValue({...question,id:52,title:'New question title',creator_id:8});await mount('/tutor?tab=questions');await waitFor(()=>expect(screen.getByRole('button',{name:'Save question'})).toBeEnabled());draft();fireEvent.click(screen.getByRole('button',{name:'Save question'}));await screen.findByText(locales.en.saveUnknown);expect(auth.api.get.mock.calls.some(([path])=>path==='/api/content/52')).toBe(false);expect(screen.getByRole('button',{name:'Save question'})).toBeDisabled();
 });
 it('keeps normal rejected validation editable without misclassifying it as an unknown save',async()=>{
  auth.api.post.mockRejectedValue(new ApiError(422,'http',false,'validation'));await mount('/tutor?tab=questions');await waitFor(()=>expect(screen.getByRole('button',{name:'Save question'})).toBeEnabled());draft();fireEvent.click(screen.getByRole('button',{name:'Save question'}));await waitFor(()=>expect(auth.api.post).toHaveBeenCalledTimes(1));await waitFor(()=>expect(screen.getByRole('button',{name:'Save question'})).toBeEnabled());expect(screen.queryByRole('button',{name:'Check saved content'})).not.toBeInTheDocument();expect(screen.getByLabelText('My question')).toHaveValue('New question text');
 });
 it('deletes an owned question only after confirmation and verifies the exact receipt',async()=>{
  const normal=auth.api.get.getMockImplementation()!;auth.api.get.mockImplementation((path:string)=>path==='/api/content/?content_type=qa'?Promise.resolve([question]):normal(path));await mount('/tutor?question_id=51');await screen.findByDisplayValue('Saved answer');fireEvent.click(screen.getByRole('button',{name:'Delete question'}));expect(auth.api.delete).not.toHaveBeenCalled();fireEvent.click(within(screen.getByRole('dialog')).getByRole('button',{name:'Delete question'}));await screen.findByText(locales.en.deletedQuestion);expect(auth.api.delete).toHaveBeenCalledWith('/api/content/51');
 });
 it('reconciles an uncertain deletion through a read without repeating DELETE',async()=>{
  const normal=auth.api.get.getMockImplementation()!;let deleted=false;auth.api.delete.mockImplementation(async()=>{deleted=true;throw new ApiError(0,'network',true,'uncertain');});auth.api.get.mockImplementation((path:string)=>path==='/api/content/?content_type=qa'?Promise.resolve(deleted?[]:[question]):path==='/api/content/51'&&deleted?Promise.reject(new ApiError(404,'http',false,'unavailable')):normal(path));await mount('/tutor?question_id=51');await screen.findByDisplayValue('Saved answer');fireEvent.click(screen.getByRole('button',{name:'Delete question'}));fireEvent.click(within(screen.getByRole('dialog')).getByRole('button',{name:'Delete question'}));await screen.findByText(locales.en.deleteUnknown);fireEvent.click(screen.getByRole('button',{name:'Check deletion outcome'}));await screen.findByText(locales.en.deletedQuestion);expect(auth.api.delete).toHaveBeenCalledTimes(1);
 });

 it('links saved QA as content context when asking the teacher',async()=>{
  const normal=auth.api.get.getMockImplementation()!;auth.api.get.mockImplementation((path:string)=>path==='/api/content/?content_type=qa'?Promise.resolve([question]):normal(path));await mount('/tutor?question_id=51');await screen.findByDisplayValue('Saved answer');expect(screen.getByRole('link',{name:'Ask my teacher about this question'})).toHaveAttribute('href','/ayuda?content_id=51');
 });
 it('supports a whole authorized course as optional source without requiring a material',async()=>{
  const normal=auth.api.get.getMockImplementation()!;auth.api.get.mockImplementation((path:string)=>path.startsWith('/api/ai/context?')?Promise.resolve({source:{...source,id:21,type:'course'}}):normal(path));auth.api.post.mockImplementation(async(_path:string,payload:Record<string,unknown>)=>result(payload,{source:{...source,id:21,type:'course'}}));await mount('/tutor?plan_id=21');await ready();await ask();await screen.findByText('Synthetic suggestion');expect(auth.api.post.mock.calls[0][1]).toMatchObject({study_plan_id:21,content_id:null,source_version:source.source_version});
 });
 it('keeps free tutor available when optional material choices cannot be read',async()=>{
  const normal=auth.api.get.getMockImplementation()!;auth.api.get.mockImplementation((path:string)=>path==='/api/study-plans/'||path==='/api/content/'?Promise.reject(new ApiError(503,'http',false,'failed')):normal(path));await mount();await ready();await ask();await screen.findByText('Synthetic suggestion');
 });
 it('fences delivery when the read assistance policy becomes stricter in flight',async()=>{
  const job=deferred<unknown>();auth.api.post.mockReturnValue(job.promise);const normal=auth.api.get.getMockImplementation()!,view=await mount();await ready();fireEvent.change(screen.getByLabelText('Type of support'),{target:{value:'explanation'}});await ask();const payload=auth.api.post.mock.calls[0][1];auth.api.get.mockImplementation((path:string)=>path==='/api/ai/assistance-policy'?Promise.resolve({mode:'hints_only'}):normal(path));await act(async()=>view.client.invalidateQueries({queryKey:[auth.scope,'tutor','policy']}));await waitFor(()=>expect(screen.getByLabelText('Type of support')).toBeDisabled());await act(async()=>job.resolve(result(payload)));expect(screen.queryByText('Synthetic suggestion')).not.toBeInTheDocument();expect(screen.getByRole('button',{name:'Retry same request'})).toBeDisabled();
 });
 it('keeps a continuing-provider receipt authoritative when the usage refresh fails',async()=>{
  let ended=false;const normal=auth.api.get.getMockImplementation()!;auth.api.get.mockImplementation((path:string)=>path==='/api/ai/usage'&&ended?Promise.reject(new ApiError(503,'http',false,'failed')):normal(path));auth.api.post.mockImplementation(async(_path:string,payload:Record<string,unknown>)=>{ended=true;return result(payload,{receipt:receipt(String(payload.client_request_id),{status:'timed_out',provider_may_continue:true}),status:'unavailable'});});await mount();await ready();await ask();await screen.findByText(locales.en.unavailable);expect(screen.getByRole('button',{name:'Ask tutor'})).toBeDisabled();expect(screen.getByRole('button',{name:'Cancel AI request'})).toBeEnabled();
 });
});

describe('confirmed question detail cache', () => {
 it('reopens the saved question from a fresh detail rather than its cached pre-edit value', async () => {
  let server = structuredClone(question);
  const normal = auth.api.get.getMockImplementation()!;
  auth.api.get.mockImplementation((path: string) => path === '/api/content/?content_type=qa' ? Promise.resolve([server]) : path === '/api/content/51' ? Promise.resolve(structuredClone(server)) : normal(path));
  auth.api.put.mockImplementation(async (_path: string, payload: Record<string, unknown>) => { server = {...server, ...payload}; return server; });
  await mount('/tutor?tab=questions&question_id=51');
  await waitFor(() => expect(screen.getByLabelText('My question')).toHaveValue('Why?'));
  fireEvent.change(screen.getByLabelText('My question'), {target: {value: 'A revised question?'}});
  fireEvent.click(screen.getByRole('button', {name: 'Save question'})); await screen.findByText(locales.en.saved);
  fireEvent.click(screen.getByRole('button', {name: 'New question'}));
  fireEvent.click(screen.getByRole('button', {name: 'Existing question'}));
  await waitFor(() => expect(screen.getByLabelText('My question')).toHaveValue('A revised question?'));
  expect(auth.api.put).toHaveBeenCalledTimes(1); expect(auth.api.post).not.toHaveBeenCalled();
 });
 it('invalidates a deleted detail without replaying the delete or preserving a live cached record', async () => {
  let deleted = false; const normal = auth.api.get.getMockImplementation()!;
  auth.api.get.mockImplementation((path: string) => path === '/api/content/?content_type=qa' ? Promise.resolve(deleted ? [] : [question]) : path === '/api/content/51' ? deleted ? Promise.reject(new ApiError(404)) : Promise.resolve(question) : normal(path));
  auth.api.delete.mockImplementation(async () => {deleted = true; return {id: 51, message: 'Content deleted successfully'};});
  const h = await mount('/tutor?tab=questions&question_id=51'); await screen.findByLabelText('My question');
  fireEvent.click(screen.getByRole('button', {name: 'Delete question'}));
  fireEvent.click(within(await screen.findByRole('dialog')).getByRole('button', {name: 'Delete question'}));
  await screen.findByText(locales.en.deletedQuestion);
  expect(h.client.getQueryState([auth.scope, 'tutor', 'question', 51])?.isInvalidated).toBe(true);
  expect(auth.api.delete).toHaveBeenCalledTimes(1);
 });
});

it('marks a receipt-confirmed question stale after failed detail verification, preserving typed text and retrying only GET', async () => {
 let server = structuredClone(question); let saved = false; let failed = true; const normal = auth.api.get.getMockImplementation()!;
 auth.api.get.mockImplementation((path: string) => path === '/api/content/?content_type=qa' ? Promise.resolve([server]) : path === '/api/content/51' ? saved && failed ? Promise.reject(new ApiError(503)) : Promise.resolve(structuredClone(server)) : normal(path));
 auth.api.put.mockImplementation(async (_path: string, payload: Record<string, unknown>) => {saved = true; server = {...server, ...payload}; return server;});
 const h = await mount('/tutor?tab=questions&question_id=51'); await screen.findByLabelText('My question');
 fireEvent.change(screen.getByLabelText('My question'), {target: {value: 'Preserved revised question'}});
 fireEvent.click(screen.getByRole('button', {name: 'Save question'})); await screen.findByText(locales.en.saveUnknown);
 expect(screen.getByLabelText('My question')).toHaveValue('Preserved revised question'); expect(screen.getByRole('button', {name: 'Save question'})).toBeDisabled();
 expect(h.client.getQueryState([auth.scope, 'tutor', 'question', 51])?.isInvalidated).toBe(true);
 failed = false; fireEvent.click(screen.getByRole('button', {name: 'Check saved content'})); await screen.findByText(locales.en.saved);
 expect(h.client.getQueryData([auth.scope, 'tutor', 'question', 51])).toEqual(server); expect(auth.api.put).toHaveBeenCalledTimes(1); expect(auth.api.post).not.toHaveBeenCalled();
});

it.each(['save', 'delete'])('invalidates a confirmed question %s receipt after same-account unmount', async action => {
 const pending = deferred<unknown>(); const normal = auth.api.get.getMockImplementation()!;
 auth.api.get.mockImplementation((path: string) => path === '/api/content/?content_type=qa' ? Promise.resolve([question]) : normal(path));
 if (action === 'save') auth.api.put.mockReturnValue(pending.promise); else auth.api.delete.mockReturnValue(pending.promise);
 const h = await mount('/tutor?tab=questions&question_id=51'); await screen.findByLabelText('My question');
 if (action === 'save') {fireEvent.change(screen.getByLabelText('My question'), {target: {value: 'New persisted question'}}); fireEvent.click(screen.getByRole('button', {name: 'Save question'})); await waitFor(() => expect(auth.api.put).toHaveBeenCalledTimes(1));}
 else {fireEvent.click(screen.getByRole('button', {name: 'Delete question'})); fireEvent.click(within(await screen.findByRole('dialog')).getByRole('button', {name: 'Delete question'})); await waitFor(() => expect(auth.api.delete).toHaveBeenCalledTimes(1));}
 h.unmount(); await act(async () => pending.resolve(action === 'save' ? {...question, content_data: {...question.content_data, question: 'New persisted question'}} : {id: 51, message: 'Content deleted successfully'}));
 expect(h.client.getQueryState([auth.scope, 'tutor', 'question', 51])?.isInvalidated).toBe(true);
 expect(auth.api.put.mock.calls.length + auth.api.delete.mock.calls.length).toBe(1);
});

it.each(['different', 'same', 'tab'])('waits for new detail before reopening a receipt-confirmed question after failed verification (%s selection)', async selection => {
 let server = structuredClone(question); let saved = false; let mode: 'fail' | 'wait' = 'fail'; const pending = deferred<unknown>(); const normal = auth.api.get.getMockImplementation()!;
 auth.api.get.mockImplementation((path: string) => path === '/api/content/?content_type=qa' ? Promise.resolve([server]) : path === '/api/content/51' ? saved ? mode === 'fail' ? Promise.reject(new ApiError(503)) : pending.promise : Promise.resolve(structuredClone(server)) : normal(path));
 auth.api.put.mockImplementation(async (_path: string, payload: Record<string, unknown>) => {saved = true; server = {...server, ...payload}; return server;});
 await mount('/tutor?tab=questions&question_id=51'); await screen.findByLabelText('My question');
 fireEvent.change(screen.getByLabelText('My question'), {target: {value: 'Persisted new question'}}); fireEvent.click(screen.getByRole('button', {name: 'Save question'})); await screen.findByText(locales.en.saveUnknown);
 mode = 'wait';
 if (selection === 'tab') {fireEvent.click(screen.getByRole('button', {name: 'Tutor conversation'})); fireEvent.click(screen.getByRole('button', {name: 'My questions'}));}
 else {fireEvent.click(screen.getByRole('button', {name: selection === 'different' ? 'New question' : 'Existing question'})); fireEvent.click(within(await screen.findByRole('dialog')).getByRole('button', {name: 'Continue'})); if (selection === 'different') fireEvent.click(screen.getByRole('button', {name: 'Existing question'}));}
 if (selection === 'tab') {
  // Hiding preserves the uncertain buffer. Readback remains an explicit action.
  expect(screen.getByLabelText('My question')).toHaveValue('Persisted new question');
  expect(screen.getByRole('button',{name:'Save question'})).toBeDisabled();
  fireEvent.click(screen.getByRole('button',{name:'Check saved content'}));
 } else expect(screen.queryByRole('textbox', {name: 'My question'})).not.toBeInTheDocument();
 await act(async () => pending.resolve(server)); expect(await screen.findByLabelText('My question')).toHaveValue('Persisted new question'); expect(auth.api.put).toHaveBeenCalledTimes(1);
});


describe('same-workspace tab continuity', () => {
 it.each(['/tutor', '/tutor?content_id=11'])('retains completed history through tabs in %s', async path => {
  await mount(path); await ready(); await ask(); await screen.findByText('Synthetic suggestion');
  fireEvent.click(screen.getByRole('button', {name: 'My questions'}));
  expect(screen.getByText('Synthetic suggestion')).not.toBeVisible();
  fireEvent.click(screen.getByRole('button', {name: 'Tutor conversation'})); await ready();
  expect(screen.getByText('Synthetic suggestion')).toBeVisible();
  await ask('Next question');
  expect(auth.api.post.mock.calls[1][1].conversation_history).toEqual([{role:'user',content:'Original question'},{role:'assistant',content:'Synthetic suggestion'}]);
  expect(auth.api.post).toHaveBeenCalledTimes(2);
 });
 it.each([null,51])('retains every unsaved field for question %s without mutations', async id => {
  const normal=auth.api.get.getMockImplementation()!;
  auth.api.get.mockImplementation((path:string)=>path==='/api/content/?content_type=qa'?Promise.resolve([question]):normal(path));
  await mount('/tutor?tab=questions'+(id?'&question_id='+id:'')); await screen.findByLabelText('My question');
  fireEvent.change(screen.getByLabelText('Question title'),{target:{value:'Unsaved title'}});
  fireEvent.change(screen.getByLabelText('My question'),{target:{value:'Unsaved question'}});
  fireEvent.change(screen.getByLabelText('Answer to save (optional)'),{target:{value:'Unsaved answer'}});
  fireEvent.click(screen.getByLabelText('Share this question with my teacher'));
  fireEvent.click(screen.getByRole('button',{name:'Tutor conversation'}));
  fireEvent.click(screen.getByRole('button',{name:'My questions'}));
  expect(await screen.findByLabelText('My question')).toHaveValue('Unsaved question');
  expect(screen.getByLabelText('Question title')).toHaveValue('Unsaved title');
  expect(screen.getByLabelText('Answer to save (optional)')).toHaveValue('Unsaved answer');
  expect(screen.getByLabelText('Share this question with my teacher')).toBeChecked();
  expect(auth.api.post).not.toHaveBeenCalled(); expect(auth.api.put).not.toHaveBeenCalled();
 });
 it('keeps an existing edit hidden during same-account reauth and clears it for another account', async () => {
  const normal=auth.api.get.getMockImplementation()!;
  auth.api.get.mockImplementation((path:string)=>path==='/api/content/?content_type=qa'?Promise.resolve([question]):normal(path));
  const view=await mount('/tutor?question_id=51'); await screen.findByLabelText('My question');
  fireEvent.change(screen.getByLabelText('My question'),{target:{value:'Private edited question'}});
  auth.status='locked'; auth.credentialEpoch++; view.rerenderApp();
  expect(screen.queryByRole('textbox',{name:'My question'})).not.toBeInTheDocument();
  auth.status='authenticated'; view.rerenderApp();
  expect(await screen.findByLabelText('My question')).toHaveValue('Private edited question');
  auth.scope='8:2'; auth.user.id=8; view.rerenderApp();
  await waitFor(()=>expect(screen.queryByDisplayValue('Private edited question')).not.toBeInTheDocument());
  expect(auth.api.put).not.toHaveBeenCalled();
 });
 it('retains contextual pending delivery while hidden but rejects a source change there', async () => {
  const job=deferred<unknown>(); auth.api.post.mockReturnValue(job.promise);
  const normal=auth.api.get.getMockImplementation()!, view=await mount('/tutor?content_id=11'); await ready(); await ask();
  const payload=auth.api.post.mock.calls[0][1];
  fireEvent.click(screen.getByRole('button',{name:'My questions'}));
  auth.api.get.mockImplementation((path:string)=>path.startsWith('/api/ai/context?')?Promise.resolve({source:{...source,source_version:'c'.repeat(64)}}):normal(path));
  await act(async()=>view.client.invalidateQueries({queryKey:[auth.scope,'tutor','source']}));
  await waitFor(()=>expect(screen.getByText(/Source version: c{64}/)).toBeInTheDocument());
  await act(async()=>job.resolve(result(payload)));
  fireEvent.click(screen.getByRole('button',{name:'Tutor conversation'}));
  expect(screen.queryByText('Synthetic suggestion')).not.toBeInTheDocument();
  expect(screen.getByRole('button',{name:'Retry same request'})).toBeDisabled();
  expect(auth.api.post).toHaveBeenCalledTimes(1);
 });
});

it('finishes the same Q&A save while its panel is hidden, without replay',async()=>{
 const job=deferred<unknown>(),normal=auth.api.get.getMockImplementation()!;
 let server=structuredClone(question);
 auth.api.get.mockImplementation((path:string)=>path==='/api/content/?content_type=qa'?Promise.resolve([server]):path==='/api/content/51'?Promise.resolve(server):normal(path));
 auth.api.put.mockReturnValue(job.promise);
 await mount('/tutor?question_id=51');await screen.findByLabelText('My question');
 fireEvent.change(screen.getByLabelText('My question'),{target:{value:'Saved while hidden'}});
 fireEvent.click(screen.getByRole('button',{name:'Save question'}));await waitFor(()=>expect(auth.api.put).toHaveBeenCalledTimes(1));
 fireEvent.click(screen.getByRole('button',{name:'Tutor conversation'}));
 server={...question,content_data:{...question.content_data,question:'Saved while hidden'}};
 await act(async()=>job.resolve(server));
 expect(await screen.findByText(locales.en.saved)).not.toBeVisible();
 fireEvent.click(screen.getByRole('button',{name:'My questions'}));
 expect(screen.getByLabelText('My question')).toHaveValue('Saved while hidden');
 expect(screen.getByRole('button',{name:'Save question'})).toBeEnabled();
 expect(auth.api.put).toHaveBeenCalledTimes(1);expect(auth.api.post).not.toHaveBeenCalled();
});
it('keeps a Q&A suggestion pending across tabs and requires explicit application',async()=>{
 const job=deferred<unknown>();auth.api.post.mockReturnValue(job.promise);
 await mount('/tutor?tab=questions');await waitFor(()=>expect(screen.getByRole('button',{name:'Ask AI for a suggestion'})).toBeEnabled());draft();
 fireEvent.click(screen.getByRole('button',{name:'Ask AI for a suggestion'}));await waitFor(()=>expect(auth.api.post).toHaveBeenCalledTimes(1));const payload=auth.api.post.mock.calls[0][1];
 fireEvent.click(screen.getByRole('button',{name:'Tutor conversation'}));
 await act(async()=>job.resolve({...result(payload),success:true,answer:'Hidden answer suggestion'}));
 fireEvent.click(screen.getByRole('button',{name:'My questions'}));
 expect(await screen.findByText('Hidden answer suggestion')).toBeVisible();
 expect(screen.getByLabelText('Answer to save (optional)')).toHaveValue('');
 expect(auth.api.post).toHaveBeenCalledTimes(1);expect(auth.api.put).not.toHaveBeenCalled();
});


it('fences pending delivery when policy is revoked while the conversation is hidden',async()=>{
 const job=deferred<unknown>();auth.api.post.mockReturnValue(job.promise);
 const normal=auth.api.get.getMockImplementation()!,view=await mount();await ready();await ask();const payload=auth.api.post.mock.calls[0][1];
 fireEvent.click(screen.getByRole('button',{name:'My questions'}));
 auth.api.get.mockImplementation((path:string)=>path==='/api/ai/assistance-policy'?Promise.resolve({mode:'disabled'}):normal(path));
 await act(async()=>view.client.invalidateQueries({queryKey:[auth.scope,'tutor','policy']}));
 await waitFor(()=>expect(screen.getAllByText(locales.en.policy_disabled).length).toBeGreaterThan(0));
 await act(async()=>job.resolve(result(payload)));
 fireEvent.click(screen.getByRole('button',{name:'Tutor conversation'}));
 expect(screen.queryByText('Synthetic suggestion')).not.toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Ask tutor'})).toBeDisabled();
 expect(screen.getByRole('button',{name:'Retry same request'})).toBeDisabled();
 expect(auth.api.post).toHaveBeenCalledTimes(1);
});
it.each(['discard','delete','answer'])('hides the question %s portal when its panel is hidden',async kind=>{
 const normal=auth.api.get.getMockImplementation()!;
 auth.api.get.mockImplementation((path:string)=>path==='/api/content/?content_type=qa'?Promise.resolve([question]):normal(path));
 await mount('/tutor?question_id=51');await screen.findByLabelText('My question');
 if(kind==='discard'){fireEvent.change(screen.getByLabelText('My question'),{target:{value:'Private unsaved'}});fireEvent.click(screen.getByRole('button',{name:'New question'}));}
 else if(kind==='delete')fireEvent.click(screen.getByRole('button',{name:'Delete question'}));
 else{await waitFor(()=>expect(screen.getByRole('button',{name:'Ask AI for a suggestion'})).toBeEnabled());fireEvent.click(screen.getByRole('button',{name:'Ask AI for a suggestion'}));await screen.findByText('Suggested answer');fireEvent.click(screen.getByRole('button',{name:locales.en.useAnswer}));}
 expect(await screen.findByRole('dialog')).toBeVisible();
 // Programmatic tab change exercises portal isolation independently of modal focus trapping.
 fireEvent.click(screen.getByText('Tutor conversation',{selector:'button'}));
 await waitFor(()=>expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
 expect(auth.api.delete).not.toHaveBeenCalled();expect(auth.api.put).not.toHaveBeenCalled();
});
it('hides the new-request confirmation portal with the conversation panel',async()=>{
 auth.api.post.mockRejectedValue(new ApiError(0,'network',true,'uncertain'));
 await mount();await ready();await ask();
 fireEvent.click(await screen.findByRole('button',{name:locales.en.newRequest}));expect(await screen.findByRole('dialog')).toBeVisible();
 fireEvent.click(screen.getByText('My questions',{selector:'button'}));
 await waitFor(()=>expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
 expect(auth.api.post).toHaveBeenCalledTimes(1);
});
