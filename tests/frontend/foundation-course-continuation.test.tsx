import {it,expect,vi} from 'vitest';
import {act,render,screen,waitFor,within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {QueryClientProvider} from '@tanstack/react-query';
import {createMemoryRouter,RouterProvider} from 'react-router';
import {AuthController} from '@/app/auth-controller';
import {AuthProvider} from '@/app/AuthProvider';
import {ProtectedLayout} from '@/app/AppShell';
import {LoginPage} from '@/features/auth/LoginPage';
import {CourseWorkflowPanel} from '@/features/courses/CourseWorkflowPanel';
import {locales} from '@/features/courses/locales';
import {createQueryClient,useResource} from '@/lib/query';
import i18n from '@/i18n';
const account={id:1,username:'a',role:'teacher',first_name:'A',last_name:'Test',email:'a@example.test'};
const json=(value:unknown,status=200)=>new Response(JSON.stringify(value),{status});
it('does not navigate to an old-account revision after logout cancels onSuccess invalidation',async()=>{
 await i18n.changeLanguage('en');i18n.addResourceBundle('en','courses',locales.en);window.scrollTo=vi.fn();
 let copied=false,refreshStarted=false;
 const transport=vi.fn(async(path:RequestInfo|URL)=>{
  if(String(path)==='/api/classroom/messages/unread-count')return json({unread_count:0});if(String(path)==='/api/auth/me')return json(account);
  if(String(path).endsWith('/copy')){copied=true;return json({id:99,status:'draft'});}
  if(copied){refreshStarted=true;return new Promise<Response>(()=>{});}
  return json([]);
 });
 const queries=createQueryClient();const auth=new AuthController(queries,localStorage,transport);localStorage.setItem('token','A');
 function Page(){useResource(['courses'],'/api/study-plans/');return <CourseWorkflowPanel planId={12} workflow={{status:'published',version:1,read_only:true}} dirty={false} contentCount={1} isPublic={false}/>;}
 const router=createMemoryRouter([{path:'/entrar',element:<LoginPage/>},{element:<ProtectedLayout/>,children:[{path:'/cursos/12',element:<Page/>},{path:'/cursos/99/editar',element:<p>Old revision page</p>}]}],{initialEntries:['/cursos/12']});
 const visited:string[]=[];router.subscribe(state=>visited.push(state.location.pathname));
 render(<QueryClientProvider client={queries}><AuthProvider controller={auth}><RouterProvider router={router}/></AuthProvider></QueryClientProvider>);
 await userEvent.click(await screen.findByRole('button',{name:'Create revision'}));
 await userEvent.click(within(screen.getByRole('dialog')).getByRole('button',{name:/copy/i}));
 await waitFor(()=>expect(refreshStarted).toBe(true));
 await act(()=>auth.logout('keep'));
 expect(visited).not.toContain('/cursos/99/editar');
});
