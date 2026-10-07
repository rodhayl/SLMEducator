import {vi} from 'vitest';
import {render,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {createMemoryRouter,RouterProvider} from 'react-router';
import {QueryClientProvider} from '@tanstack/react-query';
import {createInstance} from 'i18next';
import {I18nextProvider,initReactI18next} from 'react-i18next';
import {AuthProvider} from '@/app/AuthProvider';
import {AuthController} from '@/app/auth-controller';
import {AppearanceProvider} from '@/app/AppearanceProvider';
import {ProtectedLayout} from '@/app/AppShell';
import {createQueryClient} from '@/lib/query';
import {routes as messageRoutes} from '@/features/messages/routes';
import {routes as helpRoutes} from '@/features/help/routes';
import {locales as messages} from '@/features/messages/locales';
import {locales as help} from '@/features/help/locales';
import type {Message} from '@/features/messages/contracts';
import type {HelpRequest} from '@/features/help/contracts';
import type {Role} from '@/lib/types';
import {en,es} from '@/i18n/common';
export const account={id:7,username:'synthetic_teacher',first_name:'Teacher',last_name:'Synthetic',email:'teacher@example.test',role:'teacher' as Role};
export const contacts=[{id:8,username:'alex_one',full_name:'Alex Synthetic',role:'student'},{id:9,username:'alex_two',full_name:'Alex Synthetic',role:'student'}];
export const message=(changes:Partial<Message>={}):Message=>({id:1,from_id:9,to_id:7,subject:'Synthetic question',content:'Synthetic body',read_at:null,sent_at:'2026-10-07T10:00:00Z',archived_at:null,sender_name:'Alex Synthetic',recipient_name:'Teacher Synthetic',...changes});
export const helpRequest=(changes:Partial<HelpRequest>={}):HelpRequest=>({id:21,student_id:9,student_name:'Alex Synthetic',subject:'Synthetic help',request_text:'Synthetic help: Explain the angle',status:'open',priority:2,created_at:'2026-10-07T10:00:00Z',content_id:null,content_title:null,content_type:null,study_plan_id:null,study_plan_title:null,question_id:null,question_text:null,...changes});
export const source={id:12,title:'Geometry',source_version:'v1',content_data:'Angles have measures.',truncated:false,references:['s1'],available_sections:[{id:'s1',title:'Angles',characters:21}]};
export const receipt=(id:string,status='completed')=>({request_id:id,status,elapsed_seconds:1,provider:'synthetic',model:'synthetic',tokens_used:10,max_output_tokens:1000,requests_used_today:1,requests_limit_daily:100,provider_may_continue:false,cost_known:false});
export const json=(value:unknown,status=200)=>new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}});
export type Call={path:string;method:string;body?:Record<string,unknown>};
export type Intercept=(call:Call)=>Response|Promise<Response>|undefined;
export async function mountClassroom(path:string,options:{role?:Role;language?:'en'|'es';intercept?:Intercept;messages?:Message[];requests?:HelpRequest[]}={}){
 vi.spyOn(window,'scrollTo').mockImplementation(()=>undefined);let current={...account,role:options.role || 'teacher'};let rows=options.messages || [message(),message({id:2,from_id:8,subject:'Another question'}),message({id:3,from_id:7,to_id:8,subject:'Saved response'})];let requests=options.requests || [helpRequest()];let intercept=options.intercept;const calls:Call[]=[];
 const transport=vi.fn(async(input:RequestInfo|URL,init?:RequestInit):Promise<Response>=>{
  const path=String(input),method=init?.method || 'GET',body=typeof init?.body==='string'?JSON.parse(init.body) as Record<string,unknown>:undefined;const call={path,method,body};calls.push(call);const result=intercept?.(call);if(result!==undefined)return result;
  if(path==='/api/auth/login')return json({access_token:'synthetic_token',user:current});if(path==='/api/classroom/messages/unread-count')return json({unread_count:rows.filter(item=>item.to_id===current.id&&!item.read_at&&!item.archived_at).length});if(path==='/api/auth/me')return json(current);
  if(path==='/api/settings/app')return json({theme:'auto',language:options.language || 'en',font_size:'medium',enable_animations:true});if(path==='/api/settings/timezone')return json({timezone:'UTC'});
  if(path.startsWith('/api/classroom/users?')){const search=new URL(path,'http://test').searchParams.get('search') || '';return json(contacts.filter(item=>!search || `${item.full_name} ${item.username}`.includes(search)));}
  if(path.startsWith('/api/classroom/messages?')){const folder=new URL(path,'http://test').searchParams.get('folder');return json(rows.filter(item=>folder==='archived'?!!item.archived_at && [item.from_id,item.to_id].includes(current.id):!item.archived_at && (folder==='sent'?item.from_id:item.to_id)===current.id));}
  if(path==='/api/classroom/messages' && method==='POST'){const item=message({id:100+rows.length,from_id:current.id,to_id:Number(body?.recipient_id),subject:String(body?.subject),content:String(body?.body)});rows=[item,...rows];return json(item);}
  const action=path.match(/^\/api\/classroom\/messages\/(\d+)(?:\/(read|unread|archive|unarchive))?$/);if(action){const item=rows.find(item=>item.id===Number(action[1]));if(!item)return json({},404);if(method==='DELETE'){rows=rows.filter(row=>row.id!==item.id);return json({status:'ok',deleted:true});}if(action[2]==='read'||action[2]==='unread'){item.read_at=action[2]==='read'?'2026-10-07T11:00:00Z':null;return json({status:'ok',read_at:item.read_at});}item.archived_at=action[2]==='archive'?'2026-10-07T11:00:00Z':null;return json({status:'ok',archived_at:item.archived_at});}
  if(path==='/api/classroom/help' && method==='GET')return json(current.role==='student'?requests.filter(item=>item.student_id===current.id):requests);
  if(path==='/api/classroom/help' && method==='POST'){const item=helpRequest({id:100+requests.length,student_id:current.id,subject:String(body?.subject),request_text:`${body?.subject}: ${body?.description}`,priority:Number(body?.urgency),content_id:body?.content_id as number|null,study_plan_id:body?.study_plan_id as number|null,question_id:body?.question_id as number|null,client_request_id:String(body?.client_request_id)});requests=[item,...requests];return json(item);}
  if(path.match(/^\/api\/classroom\/help\/\d+\/resolve$/)){requests=requests.map(item=>item.id===Number(path.split('/')[4])?{...item,status:'resolved'}:item);return json({status:'resolved',resolved_at:'2026-10-07T11:00:00Z'});}
  if(path==='/api/ai/usage')return json({active_request_id:null,requests_used_today:0,requests_limit_daily:100});if(path==='/api/ai/assistance-policy')return json({mode:'explanations'});if(path.startsWith('/api/ai/context?'))return json({source});
  if(path==='/api/ai/chat'||path==='/api/ai/answer-question')return json({receipt:receipt(String(body?.client_request_id)),response:'Synthetic draft suggestion',answer:'Synthetic draft suggestion',source,status:'suggestion',success:true,assistance_policy:{mode:'explanations'},effective_assistance:body?.assistance});
  if(path.endsWith('/cancel'))return json(receipt(path.split('/')[4],'cancelled'));
  return json({},404);
 });
 localStorage.setItem('token','synthetic_token');const queries=createQueryClient(),controller=new AuthController(queries,localStorage,transport);const i18n=createInstance();await i18n.use(initReactI18next).init({lng:options.language || 'en',fallbackLng:'en',defaultNS:'common',resources:{en:{common:en,messages:messages.en,help:help.en},es:{common:es,messages:messages.es,help:help.es}},interpolation:{escapeValue:false}});
 const router=createMemoryRouter([{element:<ProtectedLayout/>,children:[...messageRoutes,...helpRoutes,{path:'materiales/:contentId',element:<p>Material destination</p>},{path:'cursos/:courseId',element:<p>Course destination</p>},{path:'tutor',element:<p>Tutor destination</p>}]}],{initialEntries:[path]});
 const view=render(<I18nextProvider i18n={i18n}><QueryClientProvider client={queries}><AuthProvider controller={controller}><AppearanceProvider><RouterProvider router={router}/></AppearanceProvider></AuthProvider></QueryClientProvider></I18nextProvider>);await waitFor(()=>{if(controller.snapshot().status!=='authenticated')throw new Error('Waiting for synthetic account');});
 return {...view,user:userEvent.setup(),router,queries,controller,calls,transport,intercept:(value:Intercept)=>{intercept=value;},replaceAccount:(id:number,role:Role)=>{current={...current,id,role,username:`synthetic_${id}`};},dispose:()=>{view.unmount();router.dispose();queries.clear();}};
}
export function deferred<T>(){let resolve!:(value:T)=>void;let reject!:(reason:unknown)=>void;const promise=new Promise<T>((res,rej)=>{resolve=res;reject=rej;});return {promise,resolve,reject};}
