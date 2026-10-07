import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, Link, RouterProvider, useParams } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import { createInstance } from 'i18next';
import { I18nextProvider, initReactI18next } from 'react-i18next';
import { AuthProvider } from '@/app/AuthProvider';
import { AuthController } from '@/app/auth-controller';
import { ProtectedLayout } from '@/app/AppShell';
import { CourseWorkflowPanel } from '@/features/courses/CourseWorkflowPanel';
import { locales } from '@/features/courses/locales';
import { createQueryClient, useResource } from '@/lib/query';
import { en } from '@/i18n/common';

const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } });
const deferred = <T,>() => { let resolve!: (value: T) => void; const promise = new Promise<T>(done => { resolve = done; }); return { promise, resolve }; };
const routers: Array<ReturnType<typeof createMemoryRouter>> = [];
beforeEach(() => { vi.spyOn(window, 'scrollTo').mockImplementation(() => undefined); });
afterEach(() => { routers.splice(0).forEach(router => router.dispose()); vi.restoreAllMocks(); });

function Page() {
 const { courseId } = useParams(); useResource(['courses'], '/api/study-plans/');
 return <><h1>Course {courseId}</h1><Link to="/cursos">Back to courses</Link><Link to="/cursos/20">Other course</Link><CourseWorkflowPanel planId={Number(courseId)} workflow={{ status: 'published', version: 1, read_only: true }} dirty={false} contentCount={1} isPublic={false} /></>;
}
async function mount(copyResponse?: Promise<Response>) {
 let actor = { id: 2, username: 'teacher.example', first_name: 'Sam', last_name: 'Example', email: 'teacher@example.test', role: 'teacher' };
 const calls: { path: string; method: string; signal?: AbortSignal | null }[] = [];
 const transport = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
  const path = String(input), method = init?.method || 'GET'; calls.push({ path, method, signal: init?.signal });
  if (path === '/api/auth/login') { actor = { ...actor, id: 44, username: 'other.example' }; return json({ access_token: 'synthetic-other', user: actor }); }
  if (path === '/api/auth/me') return json(actor);
  if (path === '/api/classroom/messages/unread-count') return json({ unread_count: 0 });
  if (path === '/api/study-plans/12/copy') return copyResponse || json({ id: 99, status: 'draft' });
  if (path === '/api/study-plans/' || path === '/api/students/') return json([]);
  return json({}, 404);
 });
 const queries = createQueryClient(); localStorage.setItem('token', 'synthetic-token'); const controller = new AuthController(queries, localStorage, transport);
 const i18n = createInstance(); await i18n.use(initReactI18next).init({ lng: 'en', fallbackLng: 'en', defaultNS: 'common', resources: { en: { common: en, courses: locales.en } }, interpolation: { escapeValue: false } });
 const router = createMemoryRouter([{ path: '/entrar', element: <p>Signed out</p> }, { element: <ProtectedLayout />, children: [
  { path: '/cursos', element: <><p>Course list</p><Link to="/cursos/12">Return to first course</Link></> }, { path: '/cursos/:courseId', Component: Page }, { path: '/cursos/99/editar', element: <p>New revision</p> },
 ] }], { initialEntries: ['/cursos/12'] }); routers.push(router);
 const visited: string[] = []; router.subscribe(state => visited.push(state.location.pathname));
 render(<I18nextProvider i18n={i18n}><QueryClientProvider client={queries}><AuthProvider controller={controller}><RouterProvider router={router} /></AuthProvider></QueryClientProvider></I18nextProvider>);
 await screen.findByRole('heading', { name: 'Course 12' });
 return { router, queries, controller, calls, visited, user: userEvent.setup() };
}
async function revise(h: Awaited<ReturnType<typeof mount>>) {
 await h.user.click(screen.getByRole('button', { name: 'Create revision' }));
 await h.user.click(within(screen.getByRole('dialog')).getByRole('button', { name: /copy/i }));
 await waitFor(() => expect(h.calls.filter(call => call.path.endsWith('/copy'))).toHaveLength(1));
}

// The route deliberately retains the panel across planId changes, like a cached detail page.
describe('course workflow route continuations', () => {
 it.each(['list', 'different-course', 'leave-and-return', 'logout', 'lock', 'other-account'] as const)('does not navigate after revision refresh loses its page or credentials: %s', async destination => {
  const h = await mount(), gate = deferred<void>(); const original = h.queries.invalidateQueries.bind(h.queries);
  const invalidate = vi.spyOn(h.queries, 'invalidateQueries').mockImplementation(async (...args) => { await original(...args); await gate.promise; });
  await revise(h); await waitFor(() => expect(invalidate).toHaveBeenCalledOnce());
  const receipt = h.queries.getMutationCache().getAll()[0]; expect(receipt.state.status).toBe('success');
  if (destination === 'logout') await act(() => h.controller.logout('keep'));
  else if (destination === 'lock') act(() => h.controller.lock());
  else if (destination === 'other-account') await act(() => h.controller.login('other.example', 'synthetic-password'));
  else if (destination === 'different-course') await h.user.click(screen.getByRole('link', { name: 'Other course' }));
  else { await h.user.click(screen.getByRole('link', { name: 'Back to courses' })); if (destination === 'leave-and-return') await h.user.click(screen.getByRole('link', { name: 'Return to first course' })); }
  const expected = h.router.state.location.pathname;
  await act(async () => { gate.resolve(); await gate.promise; });
  expect(h.router.state.location.pathname).toBe(expected);
  expect(h.visited).not.toContain('/cursos/99/editar');
  expect(receipt.state.status).toBe('success');
  expect(h.calls.filter(call => call.path.endsWith('/copy'))).toHaveLength(1);
 });

 it('invalidates confirmed courses without delivering a delayed revision after a resource change', async () => {
  const response = deferred<Response>(); const h = await mount(response.promise), scope = h.controller.snapshot().scope;
  const invalidate = vi.spyOn(h.queries, 'invalidateQueries');
  await revise(h);
  await act(() => h.router.navigate('/cursos/20'));
  await screen.findByRole('heading', { name: 'Course 20' });
  // A later course's dialog must also survive the old operation's completion.
  await h.user.click(screen.getByRole('button', { name: 'Create revision' }));
  expect(screen.getByRole('dialog')).toBeInTheDocument();
  const request = h.calls.find(call => call.path.endsWith('/copy'))!; expect(request.signal?.aborted).toBe(false);
  await act(async () => { response.resolve(json({ id: 99, status: 'draft' })); await response.promise; });
  await waitFor(() => expect(invalidate).toHaveBeenCalledWith({ queryKey: [scope, 'courses'] }));
  expect(h.router.state.location.pathname).toBe('/cursos/20');
  expect(screen.getByRole('dialog')).toBeInTheDocument();
  expect(h.calls.filter(call => call.path.endsWith('/copy'))).toHaveLength(1);
 });

 it('navigates to the new revision when the original course is still current', async () => {
  const h = await mount(); await revise(h);
  await waitFor(() => expect(h.router.state.location.pathname).toBe('/cursos/99/editar'));
  expect(h.calls.filter(call => call.path.endsWith('/copy'))).toHaveLength(1);
 });
});
