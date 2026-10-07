import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AppearanceProvider } from '@/app/AppearanceProvider';
import { ApiError } from '@/lib/api';
import { DraftAdapter } from '@/lib/drafts';
import { createQueryClient } from '@/lib/query';
import { en, es } from '@/i18n/common';
import { locales } from '@/features/learning/locales';
import { routes } from '@/features/learning/routes';
import type { StudySession } from '@/features/learning/contracts';
const mocks = vi.hoisted(() => ({ api: {get: vi.fn(),post: vi.fn(),patch: vi.fn(),delete: vi.fn()}, scope:'account:1', status:'authenticated', user:{id:1,role:'student'}, guard: vi.fn(), register: vi.fn(() => () => {}) }));
vi.mock('@/app/AuthProvider', () => ({usePrivacyStatus:()=>mocks.status,useAuth: () => ({api:mocks.api,scope:mocks.scope,status:mocks.status,user:mocks.user,registerResource:mocks.register,getSnapshot:()=>({scope:mocks.scope,status:mocks.status,user:mocks.user})})}));
vi.mock('@/app/DirtyGuard', () => ({useDirtyGuard:(dirty:boolean)=>mocks.guard(dirty)}));
vi.mock('@/features/learning/LearningHelp', () => ({LearningHelp:()=> <div>Contextual help component</div>}));
const current = {id:4,title:'Current title',content_type:'lesson',content_data:{content:'Current material changed after the session'}};
const pinned = {id:4,title:'Pinned lesson',content_type:'lesson' as const,content_data:{content:'Snapshot text from session start'}};
function fixture(): StudySession {return {id:7,content_id:4,start_time:'2026-10-07T12:00:00Z',status:'active',notes:'Server note',duration_minutes:0,duration_known:true,timestamp_provenance:'utc',content_snapshot:pinned,context_revision:{study_plan_id:9,content_digest:'pinned'}};}
const plan = {id:9,title:'Assigned course',contents:[{id:3,title:'Earlier lesson',content_type:'lesson',phase_index:0,order_index:0},{id:4,title:'Pinned lesson',content_type:'lesson',phase_index:0,order_index:1}]};
let serverSession: StudySession;
let progress = {study_plan_id:9,completed_content_ids:[] as number[],last_content_id:null as number|null,total_contents:2,completion_percentage:0};
beforeEach(() => {
 vi.clearAllMocks(); mocks.scope='account:1'; mocks.user={id:1,role:'student'}; mocks.status='authenticated'; serverSession=fixture(); progress={study_plan_id:9,completed_content_ids:[],last_content_id:null,total_contents:2,completion_percentage:0};
 mocks.api.get.mockImplementation(async (path:string) => {
  if(path==='/api/settings/timezone') return {timezone:'UTC'};
  if(path==='/api/content/4') return current;
  if(path==='/api/content/3') return {...current,id:3,title:'Earlier lesson'};
  if(path==='/api/study-plans/9/tree') return plan;
  if(path==='/api/study-plans/9/my-progress') return progress;
  if(path.startsWith('/api/learning/history/4')) return [serverSession];
  if(path.startsWith('/api/learning/history/3')) return [];
  if(path==='/api/learning/active') return serverSession;
  if(path.startsWith('/api/annotations/')) return [];
  throw new Error(`Unexpected fixture GET ${path}`);
 });
 mocks.api.patch.mockImplementation(async (_path:string, body:{notes:string}) => {serverSession={...serverSession,notes:body.notes};return serverSession;});
 mocks.api.post.mockImplementation(async (path:string, body?:{notes?:string}) => {
  if(path==='/api/learning/start' || path==='/api/learning/7/restore') return serverSession;
  if(path==='/api/learning/7/end') {serverSession={...serverSession,status:'completed',notes:body?.notes || '',duration_minutes:5};return serverSession;}
  if(path==='/api/study-plans/9/progress') {progress={...progress,completed_content_ids:[4],last_content_id:4,completion_percentage:50};return progress;}
  throw new Error(`Unexpected fixture POST ${path}`);
 });
});
async function mount(path='/estudio/7?content_id=4&plan_id=9', language='en') {
 const i18n=createInstance(); await i18n.init({lng:language,fallbackLng:'en',defaultNS:'common',resources:{en:{common:en,learning:locales.en},es:{common:es,learning:locales.es}},interpolation:{escapeValue:false}});
 const router=createMemoryRouter([...routes,{path:'/cursos/:courseId',element:<p>Course destination</p>},{path:'/cursos',element:<p>Courses destination</p>}],{initialEntries:[path]});
 const query=createQueryClient(); const tree=<I18nextProvider i18n={i18n}><QueryClientProvider client={query}><AppearanceProvider><RouterProvider router={router}/></AppearanceProvider></QueryClientProvider></I18nextProvider>;
 const view=render(tree); return {router,query,view,i18n,tree};
}
async function openNotes() {await userEvent.click(await screen.findByRole('button',{name:'Notes and annotations'}));return screen.getByRole('textbox',{name:'My session notes'});}
async function complete() {await userEvent.click(await screen.findByRole('button',{name:'Complete and return'}));const dialog=await screen.findByRole('dialog');await userEvent.click(within(dialog).getByRole('button',{name:'Complete session'}));}

describe('student study session synthetic DOM contracts',()=>{
 it('opens a material read-only and starts/resumes only after explicit action',async()=>{
  const {router}=await mount('/materiales/4?plan_id=9');
  expect(await screen.findByText('Current material changed after the session')).toBeVisible();
  expect(mocks.api.post).not.toHaveBeenCalled(); expect(mocks.api.patch).not.toHaveBeenCalled();
  await userEvent.click(screen.getAllByRole('button',{name:'Continue session'})[0]);
  await waitFor(()=>expect(router.state.location.pathname).toBe('/estudio/7'));
  expect(mocks.api.post).toHaveBeenCalledWith('/api/learning/start',{content_id:4,study_plan_id:9});
  expect(await screen.findByText('Snapshot text from session start')).toBeVisible();
  expect(screen.queryByText('Current material changed after the session')).not.toBeInTheDocument();
 });
 it('changes the shared non-private reading-size preference without changing lesson content',async()=>{
  await mount();const size=await screen.findByRole('combobox',{name:'Reading text size'});await userEvent.selectOptions(size,'20');expect(size).toHaveValue('20');expect(await screen.findByText('Snapshot text from session start')).toBeVisible();expect(mocks.api.post).not.toHaveBeenCalled();
 });
 it('keeps note text while switching one visible auxiliary panel and returns focus',async()=>{
  await mount(); const input=await openNotes();fireEvent.change(input,{target:{value:'Local unsaved text'}});
  await userEvent.click(screen.getByRole('button',{name:'Course index'}));
  expect(input).not.toBeVisible(); expect(input).toHaveValue('Local unsaved text');
  expect(screen.getByRole('heading',{name:'Course index'})).toHaveFocus();
  await userEvent.click(screen.getByRole('button',{name:'Notes and annotations'}));expect(input).toBeVisible();expect(input).toHaveValue('Local unsaved text');
  await userEvent.keyboard('{Escape}');expect(screen.getByRole('heading',{name:'Pinned lesson',level:1})).toHaveFocus();
  expect(mocks.api.post).not.toHaveBeenCalled();
 });
 it('saves notes with a validated receipt before reporting server save',async()=>{
  await mount();const input=await openNotes();fireEvent.change(input,{target:{value:'My new notes'}});
  await userEvent.click(screen.getByRole('button',{name:'Save notes'}));
  expect(await screen.findByText('Notes saved to the server.')).toBeVisible();
  expect(mocks.api.patch).toHaveBeenCalledWith('/api/learning/7/notes',{notes:'My new notes'});
  expect(new DraftAdapter(1).read('notes',4,7,(value):value is {notes:string}=>!!value)).toBeNull();
 });
 it('does not mark an invalid notes receipt as saved and preserves the text',async()=>{
  mocks.api.patch.mockResolvedValue({status:'ok'});await mount();const input=await openNotes();fireEvent.change(input,{target:{value:'Keep until confirmed'}});
  await userEvent.click(screen.getByRole('button',{name:'Save notes'}));
  expect(await screen.findByText('The server save is unconfirmed. Your text is kept. Retry to check and save.')).toBeVisible();expect(input).toHaveValue('Keep until confirmed');
  expect(screen.queryByText('Notes saved to the server.')).not.toBeInTheDocument();
 });
 it('pauses only after a confirmed notes save and never completes progress',async()=>{
  const {router}=await mount();const input=await openNotes();fireEvent.change(input,{target:{value:'Pause here'}});
  await userEvent.click(screen.getByRole('button',{name:'Save and pause'}));
  await waitFor(()=>expect(router.state.location.pathname).toBe('/cursos/9'));
  expect(mocks.api.patch).toHaveBeenCalledWith('/api/learning/7/notes',{notes:'Pause here'});expect(mocks.api.post).not.toHaveBeenCalled();
 });
 it('previous material saves notes without completing this material',async()=>{
  const {router}=await mount();await screen.findByText('Snapshot text from session start');await userEvent.click(screen.getByRole('button',{name:'Previous material'}));
  await waitFor(()=>expect(router.state.location.pathname).toBe('/materiales/3'));expect(mocks.api.patch).toHaveBeenCalledTimes(1);expect(mocks.api.post).not.toHaveBeenCalled();
 });
 it('retries only course progress after the end receipt was confirmed',async()=>{
  let progressCalls=0;const ordinary=mocks.api.post.getMockImplementation()!;mocks.api.post.mockImplementation(async(path:string,body?:{notes?:string})=>{if(path.endsWith('/progress')&&progressCalls++===0) throw new ApiError(503,'http',true,'uncertain');return ordinary(path,body);});
  const {router}=await mount();await complete();
  expect(await screen.findByText('Session completion was confirmed. Course progress is still pending. Retry completion to finish saving it.')).toBeVisible();expect(router.state.location.pathname).toBe('/estudio/7');
  await userEvent.click(screen.getByRole('button',{name:'Complete and return'}));await waitFor(()=>expect(router.state.location.pathname).toBe('/cursos/9'));
  expect(mocks.api.post.mock.calls.filter(([path])=>path==='/api/learning/7/end')).toHaveLength(1);expect(mocks.api.post.mock.calls.filter(([path])=>path==='/api/study-plans/9/progress')).toHaveLength(2);
 });
 it('does not update progress after a malformed or mismatched end receipt',async()=>{
  mocks.api.post.mockResolvedValue({...fixture(),id:99,status:'completed'});await mount();await complete();
  expect(await screen.findByText('Completion is unconfirmed. Your original notes are kept for the retry. No progress is marked complete yet.')).toBeVisible();
  expect(mocks.api.post).toHaveBeenCalledTimes(1);expect(mocks.api.post.mock.calls[0][0]).toBe('/api/learning/7/end');
 });
 it('recovers missing plan progress from a persisted completed session without ending it again',async()=>{
  serverSession={...fixture(),status:'completed',duration_minutes:3};const {router}=await mount();await complete();await waitFor(()=>expect(router.state.location.pathname).toBe('/cursos/9'));
  expect(mocks.api.post).toHaveBeenCalledTimes(1);expect(mocks.api.post).toHaveBeenCalledWith('/api/study-plans/9/progress',{completed_content_id:4});
 });
 it('offers recovery only for the verified account/content/session draft',async()=>{
  new DraftAdapter(2).write('notes',4,7,{notes:'Other account secret'});new DraftAdapter(1).write('notes',4,7,{notes:'Recovery text'});await mount();
  const dialog=await screen.findByRole('dialog');expect(screen.queryByText('Other account secret')).not.toBeInTheDocument();
  await userEvent.click(within(dialog).getByRole('button',{name:'Restore draft'}));expect(await screen.findByRole('textbox',{name:'My session notes'})).toHaveValue('Recovery text');expect(mocks.api.patch).not.toHaveBeenCalled();
 });
 it('rechecks resource access before restoring a local note draft',async()=>{
  new DraftAdapter(1).write('notes',4,7,{notes:'Recovery after revalidation'});await mount();const dialog=await screen.findByRole('dialog');
  const get=mocks.api.get.getMockImplementation()!;mocks.api.get.mockImplementation(async(path:string)=>{if(path.startsWith('/api/learning/history/'))throw new ApiError(403,'http',false,'unavailable');return get(path);});
  await userEvent.click(within(dialog).getByRole('button',{name:'Restore draft'}));expect(await screen.findByRole('alert')).toHaveTextContent('You do not have access');expect(dialog).toBeVisible();expect(mocks.api.patch).not.toHaveBeenCalled();
 });
 it('honors the confirmed display timezone without guessing legacy provenance',async()=>{
  const get=mocks.api.get.getMockImplementation()!;mocks.api.get.mockImplementation(async(path:string)=>path==='/api/settings/timezone'?{timezone:'Europe/Madrid'}:get(path));await mount();expect(await screen.findByText(/\(Europe\/Madrid\)/)).toBeVisible();
 });
 it('canonicalizes a verified bare active-session link without starting another session',async()=>{
  const {router}=await mount('/estudio/7');await waitFor(()=>expect(router.state.location.search).toBe('?content_id=4&plan_id=9'));expect(await screen.findByText('Snapshot text from session start')).toBeVisible();expect(mocks.api.post).not.toHaveBeenCalled();
 });
 it('fails closed on invalid route IDs or a mismatched bare active-session link',async()=>{
  const {router}=await mount('/estudio/not-an-id');expect(await screen.findByText('This study session is unavailable')).toBeVisible();expect(mocks.api.get).not.toHaveBeenCalled();
  await act(()=>router.navigate('/estudio/8'));expect(await screen.findByText('This study session is unavailable')).toBeVisible();expect(mocks.api.post).not.toHaveBeenCalled();
 });
 it('does not substitute live content into an older unpinned session',async()=>{
  serverSession={...fixture(),content_snapshot:null,context_revision:{study_plan_id:9,provenance:'legacy_unpinned'},timestamp_provenance:'legacy_unknown',start_time:'2020-01-01T10:00:00',duration_known:false};await mount();
  expect(await screen.findByText(/This older session has no saved material version/)).toBeVisible();expect(screen.queryByText('Current material changed after the session')).not.toBeInTheDocument();expect(screen.getByText('2020-01-01T10:00:00 (timezone unknown)')).toBeVisible();
 });
 it('does not continue a two-phase completion after navigation to another material',async()=>{
  let resolveEnd!:(value:StudySession)=>void;mocks.api.post.mockImplementation((path:string)=>path.endsWith('/end')?new Promise<StudySession>(resolve=>{resolveEnd=resolve;}):Promise.resolve(progress));
  const {router}=await mount();await complete();await act(()=>router.navigate('/materiales/3?plan_id=9'));
  await act(async()=>{resolveEnd({...fixture(),status:'completed'});await Promise.resolve();});
  expect(mocks.api.post).toHaveBeenCalledTimes(1);expect(router.state.location.pathname).toBe('/materiales/3');
 });
 it('keeps notes and stays put when the server is unavailable on pause',async()=>{
  mocks.api.patch.mockRejectedValue(new ApiError(0,'network',true,'uncertain'));const {router}=await mount();const input=await openNotes();fireEvent.change(input,{target:{value:'Keep when server stops'}});
  await userEvent.click(screen.getByRole('button',{name:'Save and pause'}));await screen.findByText('The server save is unconfirmed. Your text is kept. Retry to check and save.');
  expect(input).toHaveValue('Keep when server stops');expect(router.state.location.pathname).toBe('/estudio/7');expect(mocks.api.post).not.toHaveBeenCalled();
 });
 it('retains editable memory when browser draft storage is unavailable',async()=>{
  const set=vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new Error('Storage denied');});
  try {await mount();const input=await openNotes();fireEvent.change(input,{target:{value:'Memory only note'}});expect(screen.getByText('A recovery draft could not be saved on this device. Keep this page open and save to the server.')).toBeVisible();expect(input).toHaveValue('Memory only note');expect(mocks.guard).toHaveBeenLastCalledWith(true);}
  finally {set.mockRestore();}
 });
 it('does not apply a late note receipt while authentication is locked',async()=>{
  let resolveSave!:(value:StudySession)=>void;mocks.api.patch.mockImplementation(()=>new Promise<StudySession>(resolve=>{resolveSave=resolve;}));
  const {router}=await mount();const input=await openNotes();fireEvent.change(input,{target:{value:'Hidden until same-account reauth'}});await userEvent.click(screen.getByRole('button',{name:'Save and pause'}));
  mocks.status='locked';await act(async()=>{resolveSave({...fixture(),notes:'Hidden until same-account reauth'});await Promise.resolve();});
  expect(router.state.location.pathname).toBe('/estudio/7');expect(new DraftAdapter(1).read('notes',4,7,(value):value is {notes:string}=>!!value)).toEqual({notes:'Hidden until same-account reauth'});
 });
 it('provides complete Spanish session controls without mutating on render',async()=>{
  await mount('/estudio/7?content_id=4&plan_id=9','es');expect(await screen.findByRole('button',{name:'Guardar y pausar'})).toBeVisible();expect(screen.getByRole('button',{name:'Completar y volver'})).toBeVisible();expect(mocks.api.post).not.toHaveBeenCalled();
 });
});
