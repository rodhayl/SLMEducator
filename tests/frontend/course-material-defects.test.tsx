import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { flushSync } from 'react-dom';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import { createInstance } from 'i18next';
import { I18nextProvider, initReactI18next } from 'react-i18next';
import { createQueryClient } from '@/lib/query';
import { en, es } from '@/i18n/common';
import { authoredSource } from '@/features/authoring/contracts';
import { MaterialLibraryPage } from '@/features/authoring/MaterialLibrary';
import { MaterialEditorPage } from '@/features/authoring/MaterialEditor';
import { SourcePage } from '@/features/authoring/SourcePage';
import { CourseListPage } from '@/features/courses/CoursePages';
import { LessonContent } from '@/features/learning/LessonContent';
import { locales as authoring } from '@/features/authoring/locales';
import { locales as courses } from '@/features/courses/locales';
import { locales as learning } from '@/features/learning/locales';

const auth = vi.hoisted(() => ({user:{id:7,role:'teacher'},scope:'account:7',credentialEpoch:1,status:'authenticated',api:{get:vi.fn(),post:vi.fn(),put:vi.fn()},registerResource:()=>()=>undefined,getSnapshot:()=>({scope:auth.scope,credentialEpoch:auth.credentialEpoch,status:auth.status})}));
vi.mock('@/app/AuthProvider',()=>({useAuth:()=>auth}));
vi.mock('@/app/DirtyGuard',()=>({useDirtyGuard:vi.fn()}));
const course = {id:12,creator_id:7,title:'Same title',description:'Same description',is_public:false,created_at:'2026-10-08T12:00:00Z'};
const material = {id:2,title:'Practice',creator_id:7,content_type:'exercise',difficulty:1,is_personal:false,can_edit:true,content_data:{question:'Which answer?',type:'multiple_choice',options:{a:'First',b:'Second'},correct_answer:'a'}};
const source = {document_id:'a'.repeat(64),filename:'saved.txt',extracted_text:'Saved source remains intact',sections:[],original_bytes_hash:null,parser:null,extraction_coverage:'unknown',truncated:false,unreadable_pages:[],total_pages:null,provenance:'authored_or_legacy_text',original_binary_included:false};
let data:Record<string,unknown>;
beforeEach(()=>{
 vi.clearAllMocks();auth.user.role='teacher';
 data={'/api/content/':[material],'/api/content/2':material,'/api/study-plans/':[course,{...course,id:13}],'/api/study-plans/12/source':{source},'/api/study-plans/12/workflow':{status:'draft',version:0,read_only:false}};
 auth.api.get.mockImplementation(async(path:string)=>data[path]);
 auth.api.put.mockImplementation(async(_path:string,payload:object)=>({...material,...payload}));
});
async function mount(path:string,language:'en'|'es'='en',element?:React.ReactNode) {
 const i18n=createInstance();await i18n.use(initReactI18next).init({lng:language,resources:{en:{translation:en,authoring:authoring.en,courses:courses.en,learning:learning.en},es:{translation:es,authoring:authoring.es,courses:courses.es,learning:learning.es}}});
 const router=createMemoryRouter([{path:'/materiales',Component:MaterialLibraryPage},{path:'/materiales/:contentId/editar',Component:MaterialEditorPage},{path:'/fuentes',Component:SourcePage},{path:'/cursos',Component:CourseListPage},{path:'/lectura',element}],{initialEntries:[path]});
 render(<I18nextProvider i18n={i18n}><QueryClientProvider client={createQueryClient()}><RouterProvider router={router} flushSync={callback=>{flushSync(callback);}}/></QueryClientProvider></I18nextProvider>);
 return {user:userEvent.setup({applyAccept:false}),router,i18n};
}

describe.each(['en','es'] as const)('returned course/material defects in %s',language=>{
 const labels=authoring[language];
 it('002 distinguishes an empty library and does not offer a no-op filter reset',async()=>{
  data['/api/content/']=[];await mount('/materiales',language);
  expect(await screen.findByRole('heading',{name:language==='en'?'No materials yet':'Todavía no hay materiales'})).toBeVisible();
  expect(screen.queryByRole('button',{name:labels.clearFilters})).not.toBeInTheDocument();
  expect(screen.getByRole('link',{name:labels.newMaterial})).toHaveAttribute('href','/materiales/nuevo');
 });
 it('002 keeps a useful reset when filters hide existing material',async()=>{
  const {user}=await mount('/materiales?q=missing',language);
  expect(await screen.findByRole('heading',{name:labels.noMaterials})).toBeVisible();
  await user.click(screen.getByRole('button',{name:labels.clearFilters}));
  expect(await screen.findByRole('link',{name:'Practice'})).toBeVisible();
 });
 it('003 associates duplicate-key errors with both fields, preserves input and allows a corrected save',async()=>{
  const {user}=await mount('/materiales/2/editar',language);
  const first=await screen.findByLabelText(labels.choiceKey.replace('{{number}}','1'));
  const second=screen.getByLabelText(labels.choiceKey.replace('{{number}}','2'));
  await user.clear(second);await user.type(second,'a');await user.click(screen.getByRole('button',{name:labels.saveDraft}));
  await waitFor(()=>expect(second).toHaveAttribute('aria-invalid','true'));
  expect(first).toHaveAttribute('aria-invalid','true');expect(first).toHaveFocus();
  expect(second).toHaveAccessibleDescription(language==='en'?'Each choice needs a different key.':'Cada opción necesita una clave diferente.');
  expect(auth.api.put).not.toHaveBeenCalled();expect(screen.getByLabelText(labels.question)).toHaveValue('Which answer?');
  await user.clear(second);await user.type(second,'b');await user.click(screen.getByRole('button',{name:labels.saveDraft}));
  await waitFor(()=>expect(auth.api.put).toHaveBeenCalledTimes(1));expect(second).toHaveAttribute('aria-invalid','false');
 });
 it('006 makes same-title course cards and options distinguishable',async()=>{
  const {router}=await mount('/cursos',language);
  const links=await screen.findAllByRole('link',{name:'Same title'});
  expect(links[0]).toHaveAccessibleDescription(language==='en'?'Course ID 12':'ID del curso 12');
  expect(links[1]).toHaveAccessibleDescription(language==='en'?'Course ID 13':'ID del curso 13');
  await act(async()=>router.navigate('/fuentes'));
  expect(await screen.findByRole('option',{name:'Same title · ID 12'})).toHaveValue('12');
  expect(screen.getByRole('option',{name:'Same title · ID 13'})).toHaveValue('13');
 });
 it('007 omits empty optional headings and empty sections while retaining filled material',async()=>{
  await mount('/lectura',language,<LessonContent content={{id:1,title:'Lesson',content_type:'lesson',content_data:{sections:[{title:'Written section',content:'Teacher text'},{title:'Empty section',content:' \n '}],summary:'',worked_example:' \t ',independent_attempt:'',feedback:'',delayed_review:'',prerequisite_check:'',objectives:[' '],vocabulary:[{term:'',definition:''}],key_concepts:[''],discussion_questions:[]}}}/>);
  expect(screen.getAllByRole('heading').map(heading=>heading.textContent)).toEqual(['Written section']);
  expect(screen.getByText('Teacher text')).toBeVisible();
 });
 it('013 renders a normalized untitled inline lesson without empty or English fallback headings',async()=>{
  await mount('/lectura',language,<LessonContent content={{id:1,title:'Título de docente',content_type:'lesson',content_data:{content:'Texto escrito',sections:[{title:'',content:'Texto escrito'}]}}}/>);
  expect(screen.queryByRole('heading')).not.toBeInTheDocument();expect(screen.getAllByText('Texto escrito')).toHaveLength(1);
 });
 it.each([
  ['empty','empty.txt',0,'This file is empty. Choose a file with text.','Este archivo está vacío. Elige un archivo con texto.'],
  ['type','unsupported.bin',28,'Choose a PDF, TXT or MD file.','Elige un archivo PDF, TXT o MD.'],
  ['size','large.txt',10*1024*1024+1,'The file exceeds 10 MB. Choose a smaller file.','El archivo supera los 10 MB. Elige uno más pequeño.'],
 ] as const)('012 identifies the %s rejection beside the file without changing the source',async(_kind,name,size,enText,esText)=>{
  const {user}=await mount('/fuentes?plan_id=12',language);const input=await screen.findByLabelText(labels.upload);
  const file=new File(['x'],name);Object.defineProperty(file,'size',{value:size});await user.upload(input,file);
  await waitFor(()=>expect(input).toHaveAttribute('aria-invalid','true'));
  expect(input).toHaveAccessibleDescription(`${labels.uploadHint} ${language==='en'?enText:esText}`);
  expect(screen.getByLabelText(labels.sourceText)).toHaveValue(source.extracted_text);
  expect(auth.api.post).not.toHaveBeenCalled();expect(auth.api.put).not.toHaveBeenCalled();
 });
});

 it('001 related: course search preserves a burst of input before the next render',async()=>{
  const {router}=await mount('/cursos');await screen.findAllByRole('link',{name:'Same title'});
  const input=screen.getByRole('searchbox') as HTMLInputElement;
  act(()=>{for(const character of 'Same title')fireEvent.change(input,{target:{value:input.value+character}});});
  expect(input).toHaveValue('Same title');expect(router.state.location.search).toBe('?q=Same+title');
 });

 it('001 related: material search preserves a burst of input before the next render',async()=>{
  const {router}=await mount('/materiales');await screen.findByRole('link',{name:'Practice'});
  const input=screen.getByRole('searchbox') as HTMLInputElement;
  act(()=>{for(const character of 'Practice')fireEvent.change(input,{target:{value:input.value+character}});});
  expect(input).toHaveValue('Practice');expect(router.state.location.search).toBe('?q=Practice');
 });

 it('012 clears a rejection when a valid uppercase extension at the size boundary is selected',async()=>{
  const {user}=await mount('/fuentes?plan_id=12');const input=await screen.findByLabelText(authoring.en.upload);
  await user.upload(input,new File([],'empty.txt'));await waitFor(()=>expect(input).toHaveAttribute('aria-invalid','true'));
  auth.api.post.mockResolvedValue(authoredSource('VALID.TXT','Extracted proposal'));
  const file=new File(['text'],'VALID.TXT');Object.defineProperty(file,'size',{value:10*1024*1024});await user.upload(input,file);
  await screen.findByRole('heading',{name:authoring.en.extractedProposal});expect(input).toHaveAttribute('aria-invalid','false');
  expect(auth.api.post).toHaveBeenCalledTimes(1);expect(auth.api.post.mock.calls[0][1]).toBeInstanceOf(FormData);
  expect(screen.getByLabelText(authoring.en.sourceText)).toHaveValue(source.extracted_text);expect(auth.api.put).not.toHaveBeenCalled();
 });
 it('002 gives learners an accurate empty state without authoring actions',async()=>{
  auth.user.role='student';data['/api/content/']=[];await mount('/materiales');
  expect(await screen.findByRole('heading',{name:'No materials yet'})).toBeVisible();
  expect(screen.getByText('Authorized course material will appear here when it is available.')).toBeVisible();
  expect(screen.queryByRole('link',{name:authoring.en.newMaterial})).not.toBeInTheDocument();
  expect(screen.queryByRole('button',{name:authoring.en.clearFilters})).not.toBeInTheDocument();
 });
 it('003 identifies empty option text and a missing answer key after a key is changed',async()=>{
  const {user}=await mount('/materiales/2/editar');const text=await screen.findByLabelText('Choice 2 text');
  await user.clear(text);await user.clear(screen.getByLabelText('Choice 1 key'));await user.type(screen.getByLabelText('Choice 1 key'),'changed');
  await user.click(screen.getByRole('button',{name:'Save draft'}));
  await waitFor(()=>expect(text).toHaveAttribute('aria-invalid','true'));
  expect(text).toHaveAccessibleDescription(authoring.en.required);expect(screen.getByLabelText('Correct answer')).toHaveAttribute('aria-invalid','true');
  expect(auth.api.put).not.toHaveBeenCalled();
 });
 it('003 explains when fewer than two options remain and allows correction',async()=>{
  const {user}=await mount('/materiales/2/editar');await screen.findByLabelText('Choice 1 key');
  await user.click(screen.getAllByRole('button',{name:'Remove choice'})[1]);await user.click(screen.getByRole('button',{name:'Save draft'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('Add at least two choices.');expect(auth.api.put).not.toHaveBeenCalled();
  await user.click(screen.getByRole('button',{name:'Add choice'}));await user.type(screen.getByLabelText('Choice 2 text'),'Replacement');
  await user.click(screen.getByRole('button',{name:'Save draft'}));await waitFor(()=>expect(auth.api.put).toHaveBeenCalledTimes(1));
 });
 it('007 hides empty middle sections without repeating the canonical flattened body',async()=>{
  const sections=[{title:'First',content:'First paragraph'},{title:'Empty',content:' \n '},{title:'Last',content:'Last paragraph'}];
  await mount('/lectura','en',<LessonContent content={{id:1,title:'Lesson',content_type:'lesson',content_data:{content:sections.map(section=>section.content).join('\n\n'),sections}}}/>);
  expect(screen.getAllByText('First paragraph')).toHaveLength(1);expect(screen.getAllByText('Last paragraph')).toHaveLength(1);
  expect(screen.queryByRole('heading',{name:'Empty'})).not.toBeInTheDocument();
 });

it.each(['en','es'] as const)('007 preserves legacy text fallback without repeating a flattened body in %s',async language=>{
 await mount('/lectura',language,<LessonContent content={{id:1,title:'Legacy lesson',content_type:'lesson',content_data:{content:'Legacy paragraph',sections:[{title:'Legacy section',content:'',text:'Legacy paragraph'}]}}}/>);
 expect(screen.getAllByText('Legacy paragraph')).toHaveLength(1);
});
it.each(['en','es'] as const)('007 preserves a populated side of a legacy vocabulary entry in %s',async language=>{
 await mount('/lectura',language,<LessonContent content={{id:1,title:'Legacy lesson',content_type:'lesson',content_data:{content:'Lesson paragraph',vocabulary:[{term:'',definition:'A process that converts sunlight into stored energy.'},{term:'Photosynthesis',definition:''},{term:' ',definition:' '}]}}}/>);
 expect(screen.getByText('A process that converts sunlight into stored energy.')).toBeVisible();
 expect(screen.getByText('Photosynthesis')).toBeVisible();
 expect(screen.getAllByRole('term')).toHaveLength(2);
});

it.each([null,'',' \n ',undefined])('007 legacy fallback plus a whitespace-only middle section does not duplicate: %s',async content=>{
 const sections=[{title:'First',content,text:'Legacy paragraph'},{title:'Empty',content:' \n '},{title:'Last',content:'Last paragraph'}];
 const flattened='Legacy paragraph\n\n \n \n\nLast paragraph';
 await mount('/lectura','en',<LessonContent content={{id:1,title:'Lesson',content_type:'lesson',content_data:{content:flattened,sections}}}/>);
 expect(screen.getAllByText('Legacy paragraph')).toHaveLength(1);expect(screen.getAllByText('Last paragraph')).toHaveLength(1);
 expect(screen.queryByRole('heading',{name:'Empty'})).not.toBeInTheDocument();
});

const bodyVariants = [null, undefined, '', ' \n ', 'Primary paragraph'];
const textVariants = [null, undefined, '', ' \n ', 'Legacy paragraph'];
it.each(['content','body','text'].flatMap(field=>bodyVariants.flatMap(content=>textVariants.map(text=>({field,content,text})))))('007 deduplicates the rendered projection for $field with content=$content text=$text',async({field,content,text})=>{
 const sections=[{title:'First',content,text},{title:'Empty',content:' \n '},{title:'Last',content:'Last paragraph'}];
 const selected=(section:Record<string,unknown>):string=>[section.content,section.text].find((value):value is string=>typeof value==='string'&&!!value.trim())??[section.content,section.text].find((value):value is string=>typeof value==='string')??'';
 const flattened=sections.map(selected).join('\n\n');
 await mount('/lectura','en',<LessonContent content={{id:1,title:'Lesson',content_type:'lesson',content_data:{[field]:flattened,sections}}}/>);
 expect(screen.getAllByText('Last paragraph')).toHaveLength(1);
 const first=selected(sections[0]);if(first.trim())expect(screen.getAllByText(first)).toHaveLength(1);
 expect(screen.queryByRole('heading',{name:'Empty'})).not.toBeInTheDocument();
});
