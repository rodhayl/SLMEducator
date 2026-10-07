import { beforeEach, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, Outlet, RouterProvider } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import { createInstance } from 'i18next';
import { I18nextProvider, initReactI18next } from 'react-i18next';
import { createQueryClient } from '@/lib/query';
import { DirtyProvider, NavigationGuard } from '@/app/DirtyGuard';
import { locales } from '@/features/courses/locales';
import { routes } from '@/features/courses/routes';
const auth = vi.hoisted(() => ({user: {id:7, role:'teacher', username:'teacher', first_name:'Synthetic', last_name:'Teacher', email:'teacher@example.test'}, scope:'account:7',status:'authenticated',api:{get:vi.fn(),post:vi.fn()},registerResource:() => () => undefined,getSnapshot:() => ({scope:'account:7',status:'authenticated'})}));
vi.mock('@/app/AuthProvider', () => ({useAuth:() => auth}));
function Layout() {return <DirtyProvider><NavigationGuard/><Outlet/></DirtyProvider>;}
let saved: {id:number;creator_id:number;title:string;description:string;is_public:boolean;created_at:string;phases:{name:string;content_ids:number[]}[]};
beforeEach(() => {
  vi.clearAllMocks(); saved = {id:31,creator_id:7,title:'Draft',description:'',is_public:false,created_at:'2026-10-07T10:00:00Z',phases:[]};
  auth.api.get.mockImplementation(async (path:string) => path === '/api/content/' ? [] : path === '/api/study-plans/' ? [saved] : path.endsWith('/workflow') ? {status:'draft',version:0,read_only:false} : {...saved,contents:[],content_count:0});
  auth.api.post.mockImplementation(async (_path:string,value:Partial<typeof saved>) => {saved = {...saved,...value};return saved;});
});
async function setup() {
  const i18n=createInstance(); await i18n.use(initReactI18next).init({lng:'en',resources:{en:{courses:locales.en,translation:{loading:'Loading',cancel:'Cancel',unsavedTitle:'Unsaved changes',unsavedDescription:'Stay to keep editing',leave:'Leave',saved:'Saved',dirty:'Dirty'}}}});
  const router=createMemoryRouter([{Component:Layout,children:routes}],{initialEntries:['/cursos/nuevo']});
  render(<I18nextProvider i18n={i18n}><QueryClientProvider client={createQueryClient()}><RouterProvider router={router}/></QueryClientProvider></I18nextProvider>);
  return {router,user:userEvent.setup()};
}
it('redirects a confirmed new save only after the shared dirty registry clears',async () => {
  const {router,user}=await setup(); await user.type(await screen.findByLabelText('Course title'),'New confirmed course');
  await user.click(screen.getByRole('button',{name:'Save draft'})); await waitFor(() => expect(router.state.location.pathname).toBe('/cursos/31/editar'));
  expect(auth.api.post).toHaveBeenCalledTimes(1); expect(screen.queryByRole('dialog')).not.toBeInTheDocument(); expect(await screen.findByLabelText('Course title')).toHaveValue('New confirmed course');
});
it('retains a dirty manual course when navigation is cancelled',async () => {
  const {router,user}=await setup(); await user.type(await screen.findByLabelText('Course title'),'Keep my work'); await user.click(screen.getByRole('link',{name:'All courses'}));
  expect(await screen.findByRole('dialog')).toBeInTheDocument(); await user.click(screen.getByRole('button',{name:'Cancel'}));
  expect(router.state.location.pathname).toBe('/cursos/nuevo'); expect(screen.getByLabelText('Course title')).toHaveValue('Keep my work'); expect(auth.api.post).not.toHaveBeenCalled();
});
