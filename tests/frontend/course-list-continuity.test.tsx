import { act, render, screen } from '@testing-library/react';
import { flushSync } from 'react-dom';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import { createInstance } from 'i18next';
import { I18nextProvider, initReactI18next } from 'react-i18next';
import { createQueryClient } from '@/lib/query';
import { routes } from '@/features/courses/routes';
import { routes as authoringRoutes } from '@/features/authoring/routes';
import { locales as coursesLocales } from '@/features/courses/locales';
import { MaterialPreviewPage } from '@/features/learning/routes';
import { locales as learningLocales } from '@/features/learning/locales';
import { locales } from '@/features/authoring/locales';
import { locales as assessmentLocales } from '@/features/assessments/locales';
const auth=vi.hoisted(()=>({user:{id:7,role:'teacher',username:'synthetic_teacher'},scope:'account:7',credentialEpoch:1,status:'authenticated',api:{get:vi.fn(),post:vi.fn(),put:vi.fn(),delete:vi.fn()},registerResource:()=>()=>undefined,getSnapshot:()=>({scope:auth.scope,credentialEpoch:auth.credentialEpoch,status:auth.status})}));
vi.mock('@/app/AuthProvider',()=>({useAuth:()=>auth}));
vi.mock('@/app/DirtyGuard',()=>({useDirtyGuard:vi.fn()}));
const summary={id:12,creator_id:7,title:'Synthetic course',description:'Demo',is_public:false,created_at:'2026-10-07T12:00:00Z'};
const material={id:2,title:'Motion',content_type:'lesson',difficulty:3,is_personal:false,creator_id:7,can_edit:true,content_data:{sections:[{title:'Introduction',content:'Original lesson'}],summary:'Summary',generation:{provider:'synthetic',source_document_id:'a'.repeat(64)}}};
let data:Record<string,unknown>;
async function mount(path:string,language='en') {const i18n=createInstance();await i18n.use(initReactI18next).init({lng:language,resources:{en:{courses:coursesLocales.en,authoring:locales.en,learning:learningLocales.en,assessments:assessmentLocales.en,translation:{loading:'Loading',cancel:'Cancel',saved:'Saved',dirty:'Unsaved changes',errors:{uncertain:'Unknown result',failed:'Could not complete',invalidResponse:'Invalid response',validation:'Check input',network:'Network unavailable'}}},es:{courses:coursesLocales.es,authoring:locales.es,learning:learningLocales.es,assessments:assessmentLocales.es,translation:{loading:'Cargando',cancel:'Cancelar'}}}});const router=createMemoryRouter([...routes,...authoringRoutes,{path:'cursos/:id/editar',element:<p>Course editor</p>},{path:'materiales/:contentId',Component:MaterialPreviewPage}],{initialEntries:[path]});const client=createQueryClient();const result=render(<I18nextProvider i18n={i18n}><QueryClientProvider client={client}><RouterProvider router={router} flushSync={callback=>{flushSync(callback);}}/></QueryClientProvider></I18nextProvider>);return{...result,router,client,user:userEvent.setup()};}
beforeEach(()=>{vi.clearAllMocks();auth.user.role='teacher';auth.scope='account:7';auth.credentialEpoch=1;auth.status='authenticated';data={'/api/content/':[material],'/api/content/2':structuredClone(material),'/api/study-plans/':[summary],'/api/study-plans/12/tree':{...summary,phases:[{name:'Unit'}],contents:[],content_count:0},'/api/study-plans/12/workflow':{status:'draft',version:0,read_only:false},'/api/study-plans/12/source':{source:null},'/api/generate/courses/12/jobs':{jobs:{}}};auth.api.get.mockImplementation(async(path:string)=>data[path]);auth.api.put.mockImplementation(async(path:string,payload:Record<string,unknown>)=>({...material,...payload,id:Number(path.split('/').at(-1))}));auth.api.post.mockImplementation(async(_path:string,payload:Record<string,unknown>)=>({...material,...payload,id:20}));auth.api.delete.mockResolvedValue({message:'Content deleted successfully',id:2});});


it('audit: course search survives detail and browser Back', async () => {
 data['/api/study-plans/']=[summary,{...summary,id:13,title:'Other course'}];
 const {user,router}=await mount('/cursos');
 await screen.findByRole('link',{name:'Synthetic course'});
 await user.type(screen.getByRole('searchbox'),'Synthetic');
 await user.click(screen.getByRole('link',{name:'Synthetic course'}));
 await screen.findByRole('heading',{name:'Synthetic course',level:1});
 await act(async()=>router.navigate(-1));
 expect(await screen.findByRole('searchbox')).toHaveValue('Synthetic');
 expect(screen.queryByRole('link',{name:'Other course'})).not.toBeInTheDocument();
});
it.each(['teacher','admin'])('audit: Courses and materials provides material-library access to %s', async role => {
 auth.user.role=role;
 await mount('/cursos');
 await screen.findByRole('link',{name:'Synthetic course'});
 expect(document.querySelector('a[href="/materiales"]')).not.toBeNull();
});

it('course return link preserves the query and selected course', async () => {
 const {user,router}=await mount('/cursos?q=Synthetic');
 await user.click(await screen.findByRole('link',{name:'Synthetic course'}));
 await user.click(await screen.findByRole('link',{name:'All courses'}));
 expect(await screen.findByRole('searchbox')).toHaveValue('Synthetic');
 expect(router.state.location.hash).toBe('#course-12');
 expect(document.getElementById('course-12')).not.toBeNull();
});
it('direct course return cannot follow an external destination', async () => {
 await mount('/cursos/12?return=https://example.test&extra=unknown');
 expect(await screen.findByRole('link',{name:'All courses'})).toHaveAttribute('href','/cursos');
});

it.each(['teacher','admin'])('empty catalog exposes standalone material creation and generation to %s',async role=>{
 auth.user.role=role;data['/api/study-plans/']=[];data['/api/content/']=[];
 const {user}=await mount('/cursos');
 await user.click(await screen.findByRole('link',{name:'Material library'}));
 expect(await screen.findByRole('link',{name:'Create material'})).toHaveAttribute('href','/materiales/nuevo');
 expect(screen.getByRole('link',{name:'Generate with AI'})).toHaveAttribute('href','/generar');
 expect(auth.api.post).not.toHaveBeenCalled();
});
it('students can discover authorized library reads without author controls',async()=>{
 auth.user.role='student';const {user}=await mount('/cursos');
 await user.click(await screen.findByRole('link',{name:'Material library'}));
 expect(await screen.findByRole('link',{name:'Motion'})).toHaveAttribute('href','/materiales/2');
 expect(screen.queryByRole('link',{name:'Create material'})).not.toBeInTheDocument();
 expect(screen.queryByRole('link',{name:'Generate with AI'})).not.toBeInTheDocument();
 expect(auth.api.post).not.toHaveBeenCalled();
});
