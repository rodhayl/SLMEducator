import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import { createInstance } from 'i18next';
import { I18nextProvider, initReactI18next } from 'react-i18next';
import { AuthProvider } from '@/app/AuthProvider';
import { AuthController } from '@/app/auth-controller';
import { ProtectedLayout } from '@/app/AppShell';
import { createQueryClient } from '@/lib/query';
import { routes } from '@/features/assessments/routes';
import { Timestamp } from '@/features/assessments/shared';
import { locales } from '@/features/assessments/locales';
import { en, es } from '@/i18n/common';
import type { Role } from '@/lib/types';
import { assessment, submission } from './assessments-fixtures';

type Language = 'en' | 'es';
type ZoneResponse = (ownerId: number) => Response | Promise<Response>;
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } });
const policy = (timezone: string) => ({ timezone, timezone_source: 'user', local_date: '2026-10-07', timestamp_policy: 'utc_offset_v1', legacy_timestamps: 'unknown_until_explicit_migration', historical_dates: 'preserved_as_recorded' });
const submittedAt = '2026-10-07T11:00:00Z';
const gradedAt = '2026-10-07T12:00:00Z';
const routers: Array<ReturnType<typeof createMemoryRouter>> = [];
const pages: { name: string; path: string; role: Role; labelled: boolean }[] = [
 { name: 'history', path: '/evaluaciones/historial', role: 'student', labelled: false },
 { name: 'submission detail', path: '/envios/55', role: 'student', labelled: true },
 { name: 'grading workspace', path: '/correcciones/55', role: 'teacher', labelled: true },
 { name: 'grading queue', path: '/correcciones?filter=all', role: 'teacher', labelled: false },
];
beforeEach(() => { vi.spyOn(window, 'scrollTo').mockImplementation(() => undefined); });
afterEach(() => { routers.splice(0).forEach(router => router.dispose()); vi.restoreAllMocks(); });

async function mount(path: string, options: { language?: Language; role?: Role; submitted?: string; timezone?: ZoneResponse; timestamp?: { value: string | null; provenance?: string } } = {}) {
 const role = options.role || 'student'; const language = options.language || 'en';
 let actor = { id: role === 'student' ? 3 : 2, username: `${role}.example`, first_name: 'Sam', last_name: role, email: `${role}@example.test`, role };
 const data = structuredClone(assessment); const sub = structuredClone(submission);
 data.can_manage = role !== 'student'; sub.status = 'graded'; sub.submitted_at = options.submitted ?? submittedAt; sub.graded_at = gradedAt;
 if (role === 'student') sub.answers.forEach(answer => { answer.correct_answer = null; });
 let timezone = options.timezone || (() => json(policy('America/Bogota')));
 const calls: { path: string; method: string; ownerId: number }[] = [];
 const transport = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
  const path = String(input); const method = init?.method || 'GET'; calls.push({ path, method, ownerId: actor.id });
  if (path === '/api/auth/login') { actor = { ...actor, id: 44, username: 'other.example' }; sub.student_id = actor.id; return json({ access_token: 'synthetic-other', user: actor }); }
  if (path === '/api/auth/me') return json(actor);
  if (path === '/api/classroom/messages/unread-count') return json({ unread_count: 0 });
  if (path === '/api/settings/timezone') return timezone(actor.id);
  if (path === '/api/assessments/10') return json(data);
  if (path === '/api/assessments/submissions/55') return json(sub);
  if (path === '/api/assessments/submissions' || path.startsWith('/api/assessments/submissions?')) return json([sub]);
  return json({ detail: 'Not found' }, 404);
 });
 const queries = createQueryClient(); localStorage.setItem('token', 'synthetic-token');
 const controller = new AuthController(queries, localStorage, transport); const i18n = createInstance();
 await i18n.use(initReactI18next).init({ lng: language, fallbackLng: language, defaultNS: 'common', resources: { en: { common: en, assessments: locales.en }, es: { common: es, assessments: locales.es } }, interpolation: { escapeValue: false } });
 const children = options.timestamp ? [{ path: 'timestamp', element: <p><Timestamp {...options.timestamp}/></p> }] : routes;
 const router = createMemoryRouter([{ element: <ProtectedLayout/>, children }], { initialEntries: [path] }); routers.push(router);
 render(<I18nextProvider i18n={i18n}><QueryClientProvider client={queries}><AuthProvider controller={controller}><RouterProvider router={router}/></AuthProvider></QueryClientProvider></I18nextProvider>);
 await waitFor(() => expect(controller.snapshot().status).toBe('authenticated'));
 return { calls, queries, controller, setTimezone: (response: ZoneResponse) => { timezone = response; } };
}

function display(value: string, language: Language, timezone: string) {
 return new Intl.DateTimeFormat(language, { timeZone: timezone, year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(new Date(value)) + ` (${timezone})`;
}
function submittedText(value: string, language: Language, labelled: boolean) { return labelled ? `${locales[language].submittedAt}: ${value}` : value; }

describe.each(['en', 'es'] as const)('assessment account timezone in %s', language => {
 it.each(pages)('uses the saved zone in $name', async page => {
  const h = await mount(page.path, { role: page.role, language });
  const expected = display(submittedAt, language, 'America/Bogota');
  expect(expected).toContain('06:00:00');
  expect(await screen.findByText(submittedText(expected, language, page.labelled))).toBeInTheDocument();
  if (page.name === 'submission detail') expect(screen.getByText(`${locales[language].gradedAt}: ${display(gradedAt, language, 'America/Bogota')}`)).toBeInTheDocument();
  expect(h.calls.filter(call => call.path === '/api/settings/timezone')).toHaveLength(1);
  expect(h.calls.every(call => call.method === 'GET')).toBe(true);
 });

 it.each([
  { name: 'missing timezone', response: () => json({}) },
  { name: 'invalid timezone', response: () => json({ timezone: 'Not/A_Zone' }) },
  { name: 'failed timezone read', response: () => json({ detail: 'Unavailable' }, 503) },
  { name: 'explicit default policy', response: () => json({ ...policy('UTC'), timezone_source: 'default' }) },
 ])('labels the UTC fallback for $name', async ({ response }) => {
  const h = await mount('/envios/55', { language, timezone: response });
  await waitFor(() => expect(h.queries.getQueryState([h.controller.snapshot().scope, 'settings', 'timezone'])?.fetchStatus).toBe('idle'));
  expect(await screen.findByText(`${locales[language].submittedAt}: ${display(submittedAt, language, 'UTC')}`)).toBeInTheDocument();
  expect(screen.getByText(`${locales[language].gradedAt}: ${display(gradedAt, language, 'UTC')}`)).toBeInTheDocument();
  expect(document.body.textContent).not.toContain('America/Bogota');
 });

 it('shows UTC while the preference is pending, then updates both dates from one account-scoped read', async () => {
  let resolve!: (response: Response) => void;
  const pending = new Promise<Response>(done => { resolve = done; });
  const h = await mount('/envios/55', { language, timezone: () => pending });
  expect(await screen.findByText(`${locales[language].submittedAt}: ${display(submittedAt, language, 'UTC')}`)).toBeInTheDocument();
  await act(async () => { resolve(json(policy('America/Bogota'))); });
  expect(await screen.findByText(`${locales[language].submittedAt}: ${display(submittedAt, language, 'America/Bogota')}`)).toBeInTheDocument();
  expect(screen.getByText(`${locales[language].gradedAt}: ${display(gradedAt, language, 'America/Bogota')}`)).toBeInTheDocument();
  expect(h.calls.filter(call => call.path === '/api/settings/timezone')).toHaveLength(1);
  expect(h.queries.getQueryData([h.controller.snapshot().scope, 'settings', 'timezone'])).toEqual(policy('America/Bogota'));
 });

 it('falls back to labelled UTC if refreshing a saved preference fails', async () => {
  const h = await mount('/envios/55', { language });
  await screen.findByText(`${locales[language].submittedAt}: ${display(submittedAt, language, 'America/Bogota')}`);
  h.setTimezone(() => json({ detail: 'Unavailable' }, 503));
  await act(async () => { await h.queries.invalidateQueries({ queryKey: [h.controller.snapshot().scope, 'settings', 'timezone'] }); });
  expect(await screen.findByText(`${locales[language].submittedAt}: ${display(submittedAt, language, 'UTC')}`)).toBeInTheDocument();
  expect(document.body.textContent).not.toContain('America/Bogota');
 });

 it.each(pages)('preserves offset-free timestamps as unknown in $name', async page => {
  const original = '2026-10-07T11:00:00';
  const h = await mount(page.path, { role: page.role, language, submitted: original });
  await waitFor(() => expect(h.queries.getQueryData([h.controller.snapshot().scope, 'settings', 'timezone'])).toEqual(policy('America/Bogota')));
  expect(await screen.findByText(submittedText(`${original} (${locales[language].unknownTime})`, language, page.labelled))).toBeInTheDocument();
  expect(screen.queryByText(submittedText(display(submittedAt, language, 'America/Bogota'), language, page.labelled))).not.toBeInTheDocument();
 });

 it('preserves explicit legacy_unknown provenance even when an offset is present', async () => {
  const h = await mount('/timestamp', { language, timestamp: { value: submittedAt, provenance: 'legacy_unknown' } });
  await waitFor(() => expect(h.queries.getQueryData([h.controller.snapshot().scope, 'settings', 'timezone'])).toEqual(policy('America/Bogota')));
  expect(screen.getByText(`${submittedAt} (${locales[language].unknownTime})`)).toBeInTheDocument();
  expect(document.body.textContent).not.toContain('(America/Bogota)');
  expect(document.body.textContent).not.toContain('(UTC)');
 });
});

it('does not carry a previous account timezone into another account', async () => {
 const h = await mount('/envios/55', { timezone: ownerId => json(policy(ownerId === 3 ? 'America/Bogota' : 'Asia/Tokyo')) });
 await screen.findByText(`${locales.en.submittedAt}: ${display(submittedAt, 'en', 'America/Bogota')}`);
 const oldScope = h.controller.snapshot().scope;
 await act(async () => { h.controller.lock(); await h.controller.login('other.example', 'SyntheticFixture123!'); });
 expect(await screen.findByText(`${locales.en.submittedAt}: ${display(submittedAt, 'en', 'Asia/Tokyo')}`)).toBeInTheDocument();
 expect(document.body.textContent).not.toContain('America/Bogota');
 expect(h.queries.getQueryData([oldScope, 'settings', 'timezone'])).toBeUndefined();
 expect(h.queries.getQueryData([h.controller.snapshot().scope, 'settings', 'timezone'])).toEqual(policy('Asia/Tokyo'));
});
