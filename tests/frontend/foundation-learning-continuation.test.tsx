import {it,expect,vi} from 'vitest';
import {act,render,screen,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {QueryClientProvider} from '@tanstack/react-query';
import {createMemoryRouter,RouterProvider} from 'react-router';
import {AuthController} from '@/app/auth-controller';
import {AuthProvider} from '@/app/AuthProvider';
import {ProtectedLayout} from '@/app/AppShell';
import {LoginPage} from '@/features/auth/LoginPage';
import {MaterialPreviewPage,LearningWorkspace} from '@/features/learning/routes';
import {locales} from '@/features/learning/locales';
import {createQueryClient} from '@/lib/query';
import i18n from '@/i18n';
const account={id:1,username:'a',role:'student',first_name:'A',last_name:'Test',email:'a@example.test'};
const content={id:4,title:'Pinned lesson',content_type:'lesson',content_data:{content:'Synthetic lesson'}};
const session={id:7,content_id:4,start_time:'2026-10-07T12:00:00Z',status:'active',notes:'Server note',duration_minutes:0,duration_known:true,timestamp_provenance:'utc',content_snapshot:content,context_revision:{study_plan_id:null,content_digest:'pinned'}};
const json=(value:unknown,status=200)=>new Response(JSON.stringify(value),{status});
it.each(['start','pause'] as const)('does not queue stale %s navigation when auth locks during invalidation',async operation=>{
 await i18n.changeLanguage('en');i18n.addResourceBundle('en','learning',locales.en);window.scrollTo=vi.fn();
 let changed=false,refreshStarted=false;
 const transport=vi.fn(async(path:RequestInfo|URL,init?:RequestInit)=>{
  const p=String(path);
  if(p==='/api/classroom/messages/unread-count')return json({unread_count:0});if(p==='/api/auth/me')return json(account);
  if(p==='/api/auth/login')return json({access_token:'A',user:account});
  if(init?.method!=='GET'){changed=true;return json(session);}
  if(p.startsWith('/api/learning/history/')){if(changed){refreshStarted=true;return new Promise<Response>(()=>{});}return json([session]);}
  if(p==='/api/content/4')return json(content);
  if(p==='/api/settings/timezone')return json({timezone:'UTC'});
  if(p.startsWith('/api/annotations'))return json([]);
  return json(null);
 });
 const queries=createQueryClient();const auth=new AuthController(queries,localStorage,transport);localStorage.setItem('token','A');
 const router=createMemoryRouter([{path:'/entrar',element:<LoginPage/>},{element:<ProtectedLayout/>,children:[{path:'/materiales/:contentId',element:<MaterialPreviewPage/>},{path:'/estudio/:sessionId',element:<LearningWorkspace/>},{path:'/cursos',element:<p>Course list</p>}]}],{initialEntries:[operation==='start'?'/materiales/4':'/estudio/7?content_id=4']});
 render(<QueryClientProvider client={queries}><AuthProvider controller={auth}><RouterProvider router={router}/></AuthProvider></QueryClientProvider>);
 if(operation==='start')await userEvent.click((await screen.findAllByRole('button',{name:'Continue session'}))[0]!);
 else await userEvent.click(await screen.findByRole('button',{name:'Save and pause'}));
 await waitFor(()=>expect(refreshStarted).toBe(true));
 act(()=>auth.lock());
 await act(async()=>{await new Promise(resolve=>setTimeout(resolve,50));});
 await act(async()=>{await new Promise(resolve=>setTimeout(resolve,0));});
 expect([...router.state.blockers.values()].map(blocker=>blocker.state)).not.toContain('blocked');
 expect(router.state.location.pathname).toBe(operation==='start'?'/materiales/4':'/estudio/7');
});
