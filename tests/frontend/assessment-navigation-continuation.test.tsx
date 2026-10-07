import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import { createInstance } from 'i18next';
import { I18nextProvider, initReactI18next } from 'react-i18next';
import { AuthProvider } from '@/app/AuthProvider';
import { AuthController } from '@/app/auth-controller';
import { ProtectedLayout } from '@/app/AppShell';
import { createQueryClient } from '@/lib/query';
import { AssessmentListPage, AssessmentPreviewPage } from '@/features/assessments/AssessmentPages';
import { locales } from '@/features/assessments/locales';
import { en } from '@/i18n/common';
import { assessment } from './assessments-fixtures';

const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } });
const deferred = <T,>() => { let resolve!: (value: T) => void; const promise = new Promise<T>(done => { resolve = done; }); return { promise, resolve }; };
const routers: Array<ReturnType<typeof createMemoryRouter>> = [];
beforeEach(() => { vi.spyOn(window, 'scrollTo').mockImplementation(() => undefined); });
afterEach(() => { routers.splice(0).forEach(router => router.dispose()); vi.restoreAllMocks(); });

async function mount(role: 'student' | 'teacher' = 'student', startResponse?: Promise<Response>, removeDeleted = false) {
 const actor = { id: role === 'student' ? 3 : 2, username: `${role}.example`, first_name: 'Sam', last_name: 'Example', email: `${role}@example.test`, role };
 const data = [10, 20].map(id => ({ ...structuredClone(assessment), id, title: id === 10 ? 'Fractions' : 'Decimals', can_manage: role === 'teacher' }));
 const calls: { path: string; method: string; signal?: AbortSignal | null }[] = [];
 const transport = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
  const path = String(input), method = init?.method || 'GET'; calls.push({ path, method, signal: init?.signal });
  if (path === '/api/auth/me') return json(actor);
  if (path === '/api/classroom/messages/unread-count') return json({ unread_count: 0 });
  if (path === '/api/assessments/') return json(data);
  if (path === '/api/assessments/submissions') return json([]);
  if (path === '/api/assessments/10/start') return startResponse || json({ id: 55, submission_id: 55, status: 'draft' });
  const match = path.match(/^\/api\/assessments\/(10|20)(\/assistance-policy)?$/);
  if (match?.[2]) return json({ assessment_id: Number(match[1]), mode: 'hints_only', scope: 'active_attempt' });
  if (match && method === 'DELETE') { if (removeDeleted) data.splice(data.findIndex(item => item.id === Number(match[1])), 1); return json({ success: true }); }
  if (match) { const item = data.find(item => item.id === Number(match[1])); return json(item || {}, item ? 200 : 404); }
  return json({}, 404);
 });
 const queries = createQueryClient(); localStorage.setItem('token', 'synthetic-token'); const controller = new AuthController(queries, localStorage, transport);
 const i18n = createInstance(); await i18n.use(initReactI18next).init({ lng: 'en', fallbackLng: 'en', defaultNS: 'common', resources: { en: { common: en, assessments: locales.en } }, interpolation: { escapeValue: false } });
 const router = createMemoryRouter([{ path: '/entrar', element: <p>Signed out</p> }, { element: <ProtectedLayout />, children: [
  { path: '/evaluaciones', Component: AssessmentListPage }, { path: '/evaluaciones/:assessmentId', Component: AssessmentPreviewPage }, { path: '/intentos/:submissionId', element: <p>Attempt page</p> },
 ] }], { initialEntries: ['/evaluaciones/10'] }); routers.push(router);
 render(<I18nextProvider i18n={i18n}><QueryClientProvider client={queries}><AuthProvider controller={controller}><RouterProvider router={router} /></AuthProvider></QueryClientProvider></I18nextProvider>);
 await screen.findByRole('heading', { name: 'Fractions' });
 return { router, queries, controller, calls, user: userEvent.setup() };
}
async function start(h: Awaited<ReturnType<typeof mount>>) {
 await h.user.click(await screen.findByRole('button', { name: 'Start assessment' }));
 await h.user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Begin attempt' }));
 await waitFor(() => expect(h.calls.filter(call => call.method === 'POST')).toHaveLength(1));
}
function delayInvalidation(h: Awaited<ReturnType<typeof mount>>) {
 const gate = deferred<void>(); const original = h.queries.invalidateQueries.bind(h.queries);
 const invalidate = vi.spyOn(h.queries, 'invalidateQueries').mockImplementation(async (...args) => { await original(...args); await gate.promise; });
 return { gate, invalidate };
}

// Real auth, API receipts and query invalidation; only transport/refresh timing is synthetic.
describe('assessment route continuations', () => {
 it.each(['list', 'different-assessment', 'leave-and-return'] as const)('does not deliver a delayed start to a later page: %s', async destination => {
  const response = deferred<Response>(); const h = await mount('student', response.promise), scope = h.controller.snapshot().scope;
  await start(h);
  await h.user.click(screen.getByRole('link', { name: 'Back to assessments' }));
  await screen.findByRole('link', { name: 'Decimals' });
  if (destination !== 'list') { await h.user.click(screen.getByRole('link', { name: destination === 'different-assessment' ? 'Decimals' : 'Fractions' })); await screen.findByRole('heading', { name: destination === 'different-assessment' ? 'Decimals' : 'Fractions' }); }
  const expected = h.router.state.location.pathname;
  const request = h.calls.find(call => call.method === 'POST')!;
  expect(request.signal?.aborted).toBe(false);
  await act(async () => { response.resolve(json({ id: 55, submission_id: 55, status: 'draft' })); await response.promise; });
  await waitFor(() => expect(h.queries.getMutationCache().getAll().every(item => item.state.status !== 'pending')).toBe(true));
  expect(h.router.state.location.pathname).toBe(expected);
  expect(h.calls.filter(call => call.method === 'POST')).toHaveLength(1);
  if (destination === 'list') expect(h.queries.getQueryState([scope, 'submissions'])?.isInvalidated).toBe(true);
 });

 it('navigates to the confirmed attempt when the original preview is still current', async () => {
  const h = await mount(); await start(h);
  await waitFor(() => expect(h.router.state.location.pathname).toBe('/intentos/55'));
  expect(h.calls.filter(call => call.method === 'POST')).toHaveLength(1);
 });

 it('does not delay a confirmed start behind a separate history refresh', async () => {
  const h = await mount(); const { gate, invalidate } = delayInvalidation(h);
  await start(h); await waitFor(() => expect(invalidate).toHaveBeenCalledOnce());
  try { expect(h.router.state.location.pathname).toBe('/intentos/55'); }
  finally { await act(async () => { gate.resolve(); await gate.promise; }); }
  expect(h.calls.filter(call => call.method === 'POST')).toHaveLength(1);
 });

 it('returns to the list after a confirmed delete makes its old detail unavailable', async () => {
  const h = await mount('teacher', undefined, true); const { gate, invalidate } = delayInvalidation(h);
  await h.user.click(screen.getByRole('button', { name: 'Delete assessment' }));
  await h.user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete assessment' }));
  await waitFor(() => expect(invalidate).toHaveBeenCalledOnce());
  await screen.findByRole('alert');
  await act(async () => { gate.resolve(); await gate.promise; });
  await waitFor(() => expect(h.router.state.location.pathname).toBe('/evaluaciones'));
  expect(screen.queryByRole('link', { name: 'Fractions' })).not.toBeInTheDocument();
  expect(await screen.findByRole('link', { name: 'Decimals' })).toBeInTheDocument();
  expect(h.calls.filter(call => call.method === 'DELETE')).toHaveLength(1);
 });

 it.each(['list', 'different-assessment', 'logout', 'lock'] as const)('does not navigate after delete refresh loses its page or credentials: %s', async destination => {
  const h = await mount('teacher'); const { gate, invalidate } = delayInvalidation(h);
  await h.user.click(screen.getByRole('button', { name: 'Delete assessment' }));
  await h.user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete assessment' }));
  await waitFor(() => expect(invalidate).toHaveBeenCalledOnce());
  const receipt = h.queries.getMutationCache().getAll()[0]; expect(receipt.state.status).toBe('success');
  if (destination === 'logout') await act(() => h.controller.logout('keep'));
  else if (destination === 'lock') act(() => h.controller.lock());
  else { await h.user.click(screen.getByRole('link', { name: 'Back to assessments' })); if (destination === 'different-assessment') await h.user.click(await screen.findByRole('link', { name: 'Decimals' })); }
  const expected = h.router.state.location.pathname, locationKey = h.router.state.location.key;
  await act(async () => { gate.resolve(); await gate.promise; });
  expect(h.router.state.location.pathname).toBe(expected);
  expect(h.router.state.location.key).toBe(locationKey);
  expect(receipt.state.status).toBe('success');
  expect(h.calls.filter(call => call.method === 'DELETE')).toHaveLength(1);
 });
});
