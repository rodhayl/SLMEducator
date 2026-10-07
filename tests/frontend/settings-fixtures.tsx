import { vi } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import { createInstance } from 'i18next';
import { I18nextProvider, initReactI18next } from 'react-i18next';
import { AuthProvider } from '@/app/AuthProvider';
import { AuthController } from '@/app/auth-controller';
import { AppearanceProvider } from '@/app/AppearanceProvider';
import { ProtectedLayout } from '@/app/AppShell';
import { createQueryClient } from '@/lib/query';
import { routes as settingsRoutes } from '@/features/settings/routes';
import { locales as settingsLocales } from '@/features/settings/locales';
import { routes as portabilityRoutes } from '@/features/portability/routes';
import { locales as portabilityLocales } from '@/features/portability/locales';
import { aiDefaults } from '@/features/settings/contracts';
import { en, es } from '@/i18n/common';
import type { Role } from '@/lib/types';
export const account = {id:2,username:'synthetic.teacher',first_name:'Taylor',last_name:'Example',email:'teacher@example.test',role:'teacher' as Role,grade_level:'8',created_at:'2025-01-01T10:00:00',last_login:'2026-10-07T10:00:00Z'};
export const coursePlans = [{id:4,title:'Synthetic geometry',creator_id:2},{id:5,title:'Visible other course',creator_id:99}];
export const preview = (audience = 'learner',format = 'html') => ({audience,package_version:2,compatible_versions:[1,2],counts:{contents:2,assessments:1,books:0,questions:3},includes:['course structure','assessment questions'],excludes:['accounts','notes and messages'],warnings:[audience === 'teacher' ? 'Contains answer keys' : 'Reading copy only'],import_effect:'Creates a new private draft',validation:{valid:true,content_graph:'checked',source:'reported'},selected_format:format,available_formats:audience === 'teacher' ? ['json'] : ['html','markdown','json']});
export const backupPreview = {audience:'private_backup',format:'slmeducator-private-backup',key_fingerprint:'a'.repeat(64),includes:['accounts','encrypted credential records'],excludes:['encryption key'],warnings:['Keep private']};
export const timezonePolicy = {timezone:'UTC',timezone_source:'default',local_date:'2026-10-07',timestamp_policy:'utc_offset_v1',legacy_timestamps:'unknown_until_explicit_migration',historical_dates:'preserved_as_recorded'};
export const json = (value:unknown,status=200) => new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}});
export type Call = {path:string;method:string;body?:Record<string,unknown>};
export type Intercept = (call:Call)=>Response|Promise<Response>|undefined;
export async function mountSettings(path:string,role:Role='teacher',language:'en'|'es'='en',initialIntercept?:Intercept) {
 let current = {...account,role}; let ai = {...aiDefaults}; let app = {theme:'auto',language:'en',font_size:'medium',enable_animations:true}; let zone = {...timezonePolicy}; let intercept = initialIntercept;
 const calls:Call[]=[];
 const transport = vi.fn(async (input:RequestInfo|URL,init?:RequestInit):Promise<Response> => {
  const path=String(input),method=init?.method || 'GET';
  if(path==='/api/auth/login') return json({access_token:'synthetic-token',user:current});
  const body=typeof init?.body==='string' ? JSON.parse(init.body) as Record<string,unknown> : undefined; const call={path,method,body}; calls.push(call); const intercepted=intercept?.(call); if(intercepted!==undefined) return intercepted;
  if(path==='/api/gamification/badges')return json([{id:1,name:'Synthetic participation badge',earned:true,earned_at:'2026-10-07T10:00:00Z'},{id:2,name:'Not earned',earned:false,earned_at:null}]);
  if(path==='/api/classroom/messages/unread-count')return json({unread_count:0});if(path==='/api/auth/me') return json(current);
  if(path==='/api/auth/profile') {current={...current,...body};return json(current);}
  if(path==='/api/auth/change-password') return json({success:true,reauthentication_required:true});
  if(path==='/api/settings/ai') {if(method==='POST') ai={...ai,...body,has_api_key:body?.clear_api_key ? false : !!body?.api_key || ai.has_api_key}; const safe={...ai} as Record<string,unknown>;delete safe.api_key;delete safe.clear_api_key;return json(safe);}
  if(path==='/api/settings/ai/test') return json({status:'connected',provider:body?.provider,model:body?.model,response_time_ms:4,test_response:'synthetic only'});
  if(path.startsWith('/api/settings/ai/models')) return json({provider:new URL(path,'http://test').searchParams.get('provider'),models:['synthetic-model','other-model']});
  if(path==='/api/settings/app') {if(body)app={...app,...body};return json(app);}
  if(path==='/api/settings/timezone') {if(body)zone={...zone,...body,timezone_source:'user'};return json(zone);}
  if(path==='/api/status')return json({status:'online',version:'2.0.0'});
  if(path==='/api/study-plans/')return json(coursePlans);
  const url=new URL(path,'http://test');
  if(url.pathname.match(/^\/api\/portability\/plans\/\d+\/preview$/))return json(preview(url.searchParams.get('audience')!,url.searchParams.get('format')!));
  if(url.pathname.match(/^\/api\/portability\/plans\/\d+\/export$/))return new Response('synthetic export',{headers:{'Content-Type':url.searchParams.get('format')==='html'?'text/html':url.searchParams.get('format')==='markdown'?'text/markdown':'application/json'}});
  if(path==='/api/portability/import/preview')return json(preview('teacher','json'));
  if(path==='/api/portability/import')return json({study_plan_id:41,status:'draft',counts:{}});
  if(path.match(/^\/api\/study-plans\/\d+\/copy$/))return json({id:42,status:'draft'});
  if(path==='/api/portability/backup/preview')return json(backupPreview);
  if(path==='/api/portability/backup')return new Response('synthetic encrypted backup',{headers:{'Content-Type':'application/vnd.slmeducator.backup+json'}});
  return json({detail:'Not found'},404);
 });
 const queries=createQueryClient();localStorage.setItem('token','synthetic-token');const controller=new AuthController(queries,localStorage,transport);
 const i18n=createInstance();await i18n.use(initReactI18next).init({lng:language,fallbackLng:language,defaultNS:'common',resources:{en:{common:en,settings:settingsLocales.en,portability:portabilityLocales.en},es:{common:es,settings:settingsLocales.es,portability:portabilityLocales.es}},interpolation:{escapeValue:false}});
 const router=createMemoryRouter([{element:<ProtectedLayout/>,children:[...settingsRoutes,...portabilityRoutes,{path:'cursos',element:<p>Course destination</p>},{path:'cursos/:id/editar',element:<p>Draft destination</p>}]}],{initialEntries:[path]});
 const view=render(<I18nextProvider i18n={i18n}><QueryClientProvider client={queries}><AuthProvider controller={controller}><AppearanceProvider><RouterProvider router={router}/></AppearanceProvider></AuthProvider></QueryClientProvider></I18nextProvider>);
 await waitFor(()=>{if(controller.snapshot().status!=='authenticated')throw new Error('waiting for synthetic auth');});
 return {...view,user:userEvent.setup(),router,queries,controller,calls,transport,intercept:(next:Intercept)=>{intercept=next;},changeAccount:(role:Role,id:number)=>{current={...current,id,role,username:`synthetic-${id}`};},dispose:()=>{view.unmount();router.dispose();queries.clear();}};
}
