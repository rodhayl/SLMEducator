import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import { createInstance } from 'i18next';
import { I18nextProvider, initReactI18next } from 'react-i18next';
import { createQueryClient } from '@/lib/query';
import { ApiError } from '@/lib/api';
import { en, es } from '@/i18n/common';
import { authoredSource } from '@/features/authoring/contracts';
import { SourcePage } from '@/features/authoring/SourcePage';
import { locales as authoring } from '@/features/authoring/locales';
import { locales as courses } from '@/features/courses/locales';

const auth = vi.hoisted(() => ({
 user: {id:7,role:'teacher'}, scope:'account:7', credentialEpoch:1, status:'authenticated',
 api:{get:vi.fn(),post:vi.fn(),put:vi.fn()}, registerResource:()=>()=>undefined,
 getSnapshot:()=>({scope:auth.scope,credentialEpoch:auth.credentialEpoch,status:auth.status}),
}));
vi.mock('@/app/AuthProvider',()=>({useAuth:()=>auth}));
vi.mock('@/app/DirtyGuard',()=>({useDirtyGuard:vi.fn()}));

// Keep the saved source/course shapes aligned with course-material-defects.test.tsx.
const course = {id:12,creator_id:7,title:'Same title',description:'Same description',is_public:false,created_at:'2026-10-08T12:00:00Z'};
const source = {document_id:'a'.repeat(64),filename:'saved.txt',extracted_text:'Saved source remains intact',sections:[],original_bytes_hash:null,parser:null,extraction_coverage:'unknown',truncated:false,unreadable_pages:[],total_pages:null,provenance:'authored_or_legacy_text',original_binary_included:false};
const olderProposal = authoredSource('older.txt','Earlier extracted proposal');
const newerProposal = authoredSource('newer.txt','Newer extracted proposal');
let data:Record<string,unknown>;

function deferred<T>() {
 let resolve!:(value:T)=>void, reject!:(reason:unknown)=>void;
 const promise=new Promise<T>((yes,no)=>{resolve=yes;reject=no;});
 return {promise,resolve,reject};
}
function sourceReads() {return auth.api.get.mock.calls.filter(([path])=>path==='/api/study-plans/12/source');}

beforeEach(()=>{
 vi.resetAllMocks();auth.scope='account:7';auth.credentialEpoch=1;auth.status='authenticated';
 data={
  '/api/study-plans/':[course,{...course,id:13,title:'Second course'}],
  '/api/study-plans/12/source':{source},
  '/api/study-plans/12/workflow':{status:'draft',version:0,read_only:false},
  '/api/study-plans/13/source':{source:{...source,filename:'second.txt',extracted_text:'Second course source'}},
  '/api/study-plans/13/workflow':{status:'draft',version:0,read_only:false},
 };
 auth.api.get.mockImplementation(async(path:string)=>data[path]);
});

async function mount(language:'en'|'es'='en') {
 const i18n=createInstance();
 await i18n.use(initReactI18next).init({lng:language,resources:{en:{translation:en,authoring:authoring.en,courses:courses.en},es:{translation:es,authoring:authoring.es,courses:courses.es}}});
 const router=createMemoryRouter([{path:'/fuentes',Component:SourcePage}],{initialEntries:['/fuentes?plan_id=12']});
 render(<I18nextProvider i18n={i18n}><QueryClientProvider client={createQueryClient()}><RouterProvider router={router}/></QueryClientProvider></I18nextProvider>);
 await screen.findByLabelText(authoring[language].sourceText);
 return {user:userEvent.setup({applyAccept:false}),router};
}

describe.each(['en','es'] as const)('source operation continuity in %s',language=>{
 const labels=authoring[language],common=language==='en'?en:es;

 it('blocks reload during extraction, permits local edits, and clears the proposal only after a later explicit reload',async()=>{
  const pending=deferred<unknown>();auth.api.post.mockReturnValue(pending.promise);
  const {user}=await mount(language);
  const text=screen.getByLabelText(labels.sourceText),filename=screen.getByLabelText(labels.filename);
  await user.upload(screen.getByLabelText(labels.upload),new File(['text'],'newer.txt'));
  await waitFor(()=>expect(auth.api.post).toHaveBeenCalledTimes(1));
  const reload=screen.getByRole('button',{name:labels.reloadSaved});
  expect(reload).toBeDisabled();expect(screen.getByRole('button',{name:labels.saveSource})).toBeDisabled();
  expect(text).toBeEnabled();expect(filename).toBeEnabled();expect(screen.queryByText(common.saving)).not.toBeInTheDocument();
  await user.click(reload);
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();expect(sourceReads()).toHaveLength(1);
  await user.type(text,' plus a local draft');await user.clear(filename);await user.type(filename,'local.txt');
  expect(screen.getByText(common.dirty)).toBeVisible();
  await act(async()=>pending.resolve(newerProposal));
  await screen.findByRole('heading',{name:labels.extractedProposal});
  expect(text).toHaveValue(`${source.extracted_text} plus a local draft`);expect(filename).toHaveValue('local.txt');
  expect(reload).toBeEnabled();expect(auth.api.put).not.toHaveBeenCalled();expect(sourceReads()).toHaveLength(1);

  const reloading=deferred<unknown>();
  auth.api.get.mockImplementation((path:string)=>path==='/api/study-plans/12/source'?reloading.promise:Promise.resolve(data[path]));
  await user.click(reload);
  const dialog=await screen.findByRole('dialog');
  expect(sourceReads()).toHaveLength(1);expect(screen.getByText(newerProposal.filename)).toBeInTheDocument();
  await user.click(within(dialog).getByRole('button',{name:labels.reloadSaved}));
  await waitFor(()=>expect(sourceReads()).toHaveLength(2));
  expect(screen.getByLabelText(labels.upload)).toBeDisabled();
  await act(async()=>reloading.resolve({source}));
  await waitFor(()=>expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  expect(text).toHaveValue(source.extracted_text);expect(filename).toHaveValue(source.filename);
  expect(screen.queryByRole('heading',{name:labels.extractedProposal})).not.toBeInTheDocument();
  expect(auth.api.post).toHaveBeenCalledTimes(1);expect(auth.api.put).not.toHaveBeenCalled();
 });

 it('blocks adoption of an old proposal during replacement and preserves the draft and old proposal when replacement fails',async()=>{
  const pending=deferred<unknown>();
  auth.api.post.mockResolvedValueOnce(olderProposal).mockReturnValueOnce(pending.promise);
  const {user}=await mount(language);
  const text=screen.getByLabelText(labels.sourceText),input=screen.getByLabelText(labels.upload);
  await user.upload(input,new File(['old text'],'older.txt'));
  await screen.findByRole('heading',{name:labels.extractedProposal});
  await user.type(text,' local work');
  await user.upload(input,new File(['replacement'],'newer.txt'));
  await waitFor(()=>expect(auth.api.post).toHaveBeenCalledTimes(2));
  const adopt=screen.getByRole('button',{name:labels.useExtracted});
  expect(adopt).toBeDisabled();expect(screen.getByRole('button',{name:labels.reloadSaved})).toBeDisabled();
  await user.click(adopt);expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  await user.type(text,' while extracting');
  await act(async()=>pending.reject(new ApiError(503,'http',false,'failed')));
  expect(await screen.findByText(common.errors.failed)).toBeVisible();
  expect(adopt).toBeEnabled();expect(screen.getByRole('button',{name:labels.reloadSaved})).toBeEnabled();
  expect(text).toHaveValue(`${source.extracted_text} local work while extracting`);
  expect(screen.getByText(olderProposal.filename)).toBeInTheDocument();expect(screen.queryByText(newerProposal.filename)).not.toBeInTheDocument();
  expect(input).toBeEnabled();expect(auth.api.post).toHaveBeenCalledTimes(2);expect(auth.api.put).not.toHaveBeenCalled();

  await user.click(adopt);
  await user.click(within(await screen.findByRole('dialog')).getByRole('button',{name:common.cancel}));
  expect(text).toHaveValue(`${source.extracted_text} local work while extracting`);
  expect(screen.getByText(olderProposal.filename)).toBeInTheDocument();
  await user.click(adopt);
  await user.click(within(await screen.findByRole('dialog')).getByRole('button',{name:labels.useExtracted}));
  expect(text).toHaveValue(olderProposal.extracted_text);
  expect(screen.queryByRole('heading',{name:labels.extractedProposal})).not.toBeInTheDocument();
  expect(auth.api.put).not.toHaveBeenCalled();expect(sourceReads()).toHaveLength(1);
 });

 it('requires explicit adoption of the new proposal after successful replacement without saving either extraction',async()=>{
  const pending=deferred<unknown>();
  auth.api.post.mockResolvedValueOnce(olderProposal).mockReturnValueOnce(pending.promise);
  const {user}=await mount(language);
  const text=screen.getByLabelText(labels.sourceText),input=screen.getByLabelText(labels.upload);
  await user.upload(input,new File(['old text'],'older.txt'));
  await screen.findByRole('heading',{name:labels.extractedProposal});
  await user.upload(input,new File(['replacement'],'newer.txt'));
  await waitFor(()=>expect(screen.getByRole('button',{name:labels.useExtracted})).toBeDisabled());
  await act(async()=>pending.resolve(newerProposal));
  await waitFor(()=>expect(screen.getByRole('button',{name:labels.useExtracted})).toBeEnabled());
  expect(screen.queryByText(olderProposal.filename)).not.toBeInTheDocument();expect(screen.getByText(newerProposal.filename)).toBeInTheDocument();
  expect(text).toHaveValue(source.extracted_text);expect(auth.api.put).not.toHaveBeenCalled();
  await user.click(screen.getByRole('button',{name:labels.useExtracted}));
  await user.click(within(await screen.findByRole('dialog')).getByRole('button',{name:labels.useExtracted}));
  expect(text).toHaveValue(newerProposal.extracted_text);expect(screen.getByLabelText(labels.filename)).toHaveValue(newerProposal.filename);
  expect(auth.api.put).not.toHaveBeenCalled();expect(auth.api.post).toHaveBeenCalledTimes(2);
 });
});

describe('source operation interruption fences',()=>{
 it.each(['saveSource','useExtracted','reloadSaved'] as const)('guards an already-open %s confirmation if extraction begins before confirmation',async action=>{
  const pending=deferred<unknown>();
  auth.api.post.mockResolvedValueOnce(olderProposal).mockReturnValueOnce(pending.promise);
  const {user}=await mount();
  const input=screen.getByLabelText(authoring.en.upload),text=screen.getByLabelText(authoring.en.sourceText);
  await user.upload(input,new File(['old text'],'older.txt'));
  await screen.findByRole('heading',{name:authoring.en.extractedProposal});
  await user.click(screen.getByRole('button',{name:authoring.en[action]}));
  const dialog=await screen.findByRole('dialog');
  // A delayed native file-selection change can arrive after the dialog opened.
  fireEvent.change(input,{target:{files:[new File(['replacement'],'newer.txt')]}});
  await waitFor(()=>expect(auth.api.post).toHaveBeenCalledTimes(2));
  const confirm=within(dialog).getByRole('button',{name:authoring.en[action]});
  expect(confirm).toBeDisabled();
  fireEvent.click(confirm);
  expect(auth.api.put).not.toHaveBeenCalled();expect(sourceReads()).toHaveLength(1);
  expect(text).toHaveValue(source.extracted_text);expect(screen.getByText(olderProposal.filename)).toBeInTheDocument();
  await act(async()=>pending.reject(new ApiError(503,'http',false,'failed')));
  await waitFor(()=>expect(confirm).toBeEnabled());
  await user.click(within(dialog).getByRole('button',{name:en.cancel}));
  expect(text).toHaveValue(source.extracted_text);expect(auth.api.put).not.toHaveBeenCalled();expect(sourceReads()).toHaveLength(1);
 });

 it.each(['scope','credentialEpoch'] as const)('does not deliver a late extraction after the %s changes',async fence=>{
  const pending=deferred<unknown>();auth.api.post.mockReturnValue(pending.promise);
  const {user}=await mount();
  await user.upload(screen.getByLabelText(authoring.en.upload),new File(['text'],'newer.txt'));
  await waitFor(()=>expect(auth.api.post).toHaveBeenCalledTimes(1));
  if(fence==='scope')auth.scope='account:8';else auth.credentialEpoch++;
  await act(async()=>pending.resolve(newerProposal));
  await waitFor(()=>expect(screen.getByLabelText(authoring.en.upload)).toBeEnabled());
  expect(screen.queryByRole('heading',{name:authoring.en.extractedProposal})).not.toBeInTheDocument();
  expect(auth.api.put).not.toHaveBeenCalled();
 });

 it('does not put a departed course extraction into the next course or replay it on Back',async()=>{
  const pending=deferred<unknown>();auth.api.post.mockReturnValue(pending.promise);
  const {user,router}=await mount();
  await user.upload(screen.getByLabelText(authoring.en.upload),new File(['text'],'newer.txt'));
  await waitFor(()=>expect(auth.api.post).toHaveBeenCalledTimes(1));
  await act(async()=>router.navigate('/fuentes?plan_id=13'));
  await waitFor(()=>expect(screen.getByLabelText(authoring.en.sourceText)).toHaveValue('Second course source'));
  await act(async()=>pending.resolve(newerProposal));
  expect(screen.queryByRole('heading',{name:authoring.en.extractedProposal})).not.toBeInTheDocument();
  expect(screen.getByLabelText(authoring.en.sourceText)).toHaveValue('Second course source');
  await act(async()=>router.navigate(-1));
  await waitFor(()=>expect(screen.getByLabelText(authoring.en.sourceText)).toHaveValue(source.extracted_text));
  expect(screen.queryByRole('heading',{name:authoring.en.extractedProposal})).not.toBeInTheDocument();
  expect(auth.api.post).toHaveBeenCalledTimes(1);expect(auth.api.put).not.toHaveBeenCalled();
 });
});
