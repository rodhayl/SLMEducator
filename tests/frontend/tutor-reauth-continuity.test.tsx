import { act, render, screen, waitFor } from '@testing-library/react';
import { it, expect, vi } from 'vitest';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { AuthController } from '@/app/auth-controller';
import { AuthProvider } from '@/app/AuthProvider';
import { createQueryClient } from '@/lib/query';
import { TutorPage } from '@/features/tutor/TutorPage';
import { locales } from '@/features/tutor/locales';
const account={id:7,role:'student',username:'synthetic',first_name:'Synthetic',last_name:'Learner',email:'synthetic@example.test'};
const question={id:51,owner_id:7,question:'Why?',teacher_status:'not_requested',teacher_available:false,teacher_name:null,can_request_teacher:false,can_reply:false,replies:[{id:1,kind:'ai',body:'Saved answer',author_name:'IA'}]};
const json=(value:unknown,status=200)=>new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}});
async function mount(){
 let revoked=false;
 const calls:{path:string;method:string}[]=[];
 const transport=vi.fn(async(input:RequestInfo|URL,init?:RequestInit)=>{
  const path=String(input);calls.push({path,method:init?.method||'GET'});
  if(path==='/api/auth/login')return json({access_token:'synthetic-token',user:account});
  if(path==='/api/auth/me')return json(account);
  if(path==='/api/questions')return json([question]);
  if(path==='/api/questions/51')return revoked?json({},403):json(question);
  if(path==='/api/ai/assistance-policy')return json({mode:'explanations'});
  if(path==='/api/ai/usage')return json({requests_used_today:0,requests_limit_daily:100,active_request_id:null});
  return json([]);
 });
 localStorage.setItem('token','synthetic-token');const queries=createQueryClient(),auth=new AuthController(queries,localStorage,transport);
 const i18n=createInstance();await i18n.init({lng:'en',resources:{en:{tutor:locales.en}},interpolation:{escapeValue:false}});
 const view=render(<QueryClientProvider client={queries}><AuthProvider controller={auth}><I18nextProvider i18n={i18n}><MemoryRouter initialEntries={['/tutor?thread_id=51']}><TutorPage/></MemoryRouter></I18nextProvider></AuthProvider></QueryClientProvider>);
 await screen.findByText('Saved answer');
 return {auth,calls,revoke:()=>{revoked=true;},dispose:()=>{view.unmount();queries.clear();}};
}
it.each([false,true])('retains a hidden existing buffer while reauth validates current access (revoked=%s)',async revoked=>{
 const h=await mount();
 try{
  await act(async()=>h.auth.lock());
  expect(screen.getByText('Saved answer')).not.toBeVisible();
  const readsBefore=h.calls.filter(call=>call.path==='/api/questions/51').length;
  if(revoked){h.revoke();await act(async()=>{await expect(h.auth.login('synthetic','synthetic-only')).rejects.toMatchObject({status:403});});expect(h.auth.snapshot().status).toBe('locked');expect(screen.getByText('Saved answer')).not.toBeVisible();}
  else{await act(async()=>h.auth.login('synthetic','synthetic-only'));await waitFor(()=>expect(screen.getByText('Saved answer')).toBeVisible());}
  expect(h.calls.filter(call=>call.path==='/api/questions/51').length).toBeGreaterThan(readsBefore);
  expect(h.calls.filter(call=>call.method!=='GET').map(call=>call.path)).toEqual(['/api/auth/login']);
 }finally{h.dispose();}
});
