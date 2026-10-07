import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import { createInstance } from 'i18next';
import { I18nextProvider, initReactI18next } from 'react-i18next';
import { AuthProvider } from '@/app/AuthProvider';
import { AuthController } from '@/app/auth-controller';
import { ProtectedLayout } from '@/app/AppShell';
import { createQueryClient } from '@/lib/query';
import { routes } from '@/features/people/routes';
import { locales } from '@/features/people/locales';
import { en, es } from '@/i18n/common';
import type { Person } from '@/features/people/model';
import type { Role } from '@/lib/types';

const admin: Person = { id: 1, username: 'admin.example', first_name: 'Alex', last_name: 'Admin', email: 'admin@example.com', role: 'admin', active: true, teacher_id: null };
const teacher: Person = { ...admin, id: 2, username: 'teacher.example', first_name: 'Taylor', last_name: 'Teacher', role: 'teacher', email: 'teacher@example.com' };
const student: Person = { ...admin, id: 3, username: 'student.example', first_name: 'Sam', last_name: 'Student', role: 'student', teacher_id: 2, email: 'student@example.com' };
const passphrase = 'SyntheticFixture123!';
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } });
type Intercept = (path: string, method: string, body: Record<string, unknown> | undefined) => Response | Promise<Response> | undefined;
const mounted: Array<ReturnType<typeof createMemoryRouter>> = [];
beforeEach(() => { vi.spyOn(window, 'scrollTo').mockImplementation(() => undefined); });
afterEach(() => { mounted.splice(0).forEach(router => router.dispose()); vi.restoreAllMocks(); });

async function mount(path = '/personas', role: Role = 'admin', language: 'en' | 'es' = 'en') {
  const records = [structuredClone(admin), structuredClone(teacher), structuredClone(student)];
  let current = records.find(person => person.role === role)!;
  let intercept: Intercept | undefined;
  const notes = new Map<string, string>();
  const calls: Array<{ path: string; method: string; body?: Record<string, unknown> }> = [];
  const transport = vi.fn(async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const path = String(input); const method = init?.method || 'GET';
    if (path === '/api/auth/login') {
      const name = (init?.body as URLSearchParams).get('username');
      current = records.find(person => person.username === name)!;
      return json({ access_token: `synthetic-token-${current.id}`, user: current });
    }
    const body = typeof init?.body === 'string' ? JSON.parse(init.body) as Record<string, unknown> : undefined;
    calls.push({ path, method, body });
    const intercepted = intercept?.(path, method, body); if (intercepted !== undefined) return intercepted;
    if (path === '/api/classroom/messages/unread-count') return json({ unread_count: 0 });
  if (path === '/api/auth/me') return json(current);
    if (path === '/api/settings/app') return json({theme:'auto',language:'en',font_size:'medium',enable_animations:true});
    const url = new URL(path, 'http://local');
    if (url.pathname === '/api/auth/users') return json(records.filter(person => person.id !== current.id && (!url.searchParams.get('role') || person.role === url.searchParams.get('role')) && (url.searchParams.get('include_inactive') === 'true' || person.active) && (current.role === 'admin' || person.role === 'student' && person.teacher_id === current.id)).slice(0, 500));
    if (path === '/api/auth/register' && body) {
      const created: Person = { id: Math.max(...records.map(person => person.id)) + 1, username: String(body.username), email: String(body.email), first_name: String(body.first_name), last_name: String(body.last_name), role: body.role as Role, active: true, teacher_id: typeof body.teacher_id === 'number' ? body.teacher_id : null };
      records.push(created); return json(created);
    }
    const detail = path.match(/^\/api\/auth\/users\/(\d+)$/);
    if (detail) {
      const person = records.find(person => person.id === Number(detail[1]));
      return person && (current.role === 'admin' || person.active && person.role === 'student' && person.teacher_id === current.id) ? json(person) : json({ detail: 'Account not available' }, 404);
    }
    const enrollment = path.match(/^\/api\/students\/(\d+)\/teacher$/);
    if (enrollment && body) {
      const person = records.find(person => person.id === Number(enrollment[1]))!;
      person.teacher_id = body.teacher_id as number | null;
      return json({ student_id: person.id, teacher_id: person.teacher_id, previous_teacher_id: null, existing_assignments_preserved: true });
    }
    const note = path.match(/^\/api\/students\/(\d+)\/notes$/);
    if (note) {
      const key = `${current.id}:${note[1]}`;
      if (method === 'POST') { notes.set(key, String(body?.notes)); return json({ success: true }); }
      return json({ notes: notes.get(key) || '' });
    }
    if (/\/progress$/.test(path)) return json({ lessons_completed: 2, assessments_taken: 1, avg_score: null, study_time_hours: 1.5, time_measure: 'elapsed_completed_session_time' });
    const status = path.match(/^\/api\/auth\/users\/(\d+)\/status$/);
    if (status && body) {
      const person = records.find(person => person.id === Number(status[1]))!; person.active = body.active as boolean;
      return json({ id: person.id, active: person.active, sessions_revoked: true });
    }
    const recovery = path.match(/^\/api\/auth\/users\/(\d+)\/reset-password$/);
    if (recovery) return json({ id: Number(recovery[1]), reset: true, sessions_revoked: true });
    return json({ detail: 'Not found' }, 404);
  });
  const queries = createQueryClient(); localStorage.setItem('token', `synthetic-token-${current.id}`);
  const controller = new AuthController(queries, localStorage, transport);
  const i18n = createInstance();
  await i18n.use(initReactI18next).init({ lng: language, fallbackLng: language, defaultNS: 'common', resources: { en: { common: en, people: locales.en }, es: { common: es, people: locales.es } }, interpolation: { escapeValue: false } });
  const router = createMemoryRouter([{ element: <ProtectedLayout />, children: routes }], { initialEntries: [path] }); mounted.push(router);
  const rendered = render(<I18nextProvider i18n={i18n}><QueryClientProvider client={queries}><AuthProvider controller={controller}><RouterProvider router={router} /></AuthProvider></QueryClientProvider></I18nextProvider>);
  await waitFor(() => expect(controller.snapshot().status).toBe('authenticated'));
  return { ...rendered, router, controller, queries, calls, records, notes, transport, user: userEvent.setup(), intercept: (next: Intercept) => { intercept = next; } };
}
async function completeCreate(user: ReturnType<typeof userEvent.setup>, language: 'en' | 'es' = 'en', role: Role | null = 'student') {
  const labels = locales[language];
  await user.type(await screen.findByLabelText(labels.firstName), 'Jamie');
  await user.type(screen.getByLabelText(labels.lastName), 'Example');
  await user.type(screen.getByLabelText(labels.email), 'jamie@example.com');
  await user.type(screen.getByLabelText(labels.username), 'jamie.example');
  await user.type(screen.getByLabelText(labels.password), passphrase);
  if (role) await user.selectOptions(screen.getByLabelText(labels.role), role);
}

 describe('People staff journeys', () => {
  it('addresses student messages by verified ID', async () => {
    await mount('/personas/3');
    expect(await screen.findByRole('link', { name: 'Send message' })).toHaveAttribute('href', '/mensajes?recipient_id=3&compose=1');
  });
  it('honors role bookmarks and restores filter state through browser history', async () => {
    const h = await mount('/personas?role=teacher');
    expect(await screen.findByRole('link', { name: 'Open Taylor Teacher' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Open Sam Student' })).not.toBeInTheDocument();
    await h.user.selectOptions(screen.getByLabelText('Filter by role'), 'student');
    expect(await screen.findByRole('link', { name: 'Open Sam Student' })).toBeInTheDocument();
    expect(h.router.state.location.search).toContain('role=student');
    await act(() => h.router.navigate(-1));
    expect(await screen.findByRole('link', { name: 'Open Taylor Teacher' })).toBeInTheDocument();
    expect(screen.getByLabelText('Filter by role')).toHaveValue('teacher');
  });
  it('does not broaden teacher scope through admin query filters', async () => {
    const h = await mount('/personas?role=admin&state=all', 'teacher');
    expect(await screen.findByRole('link', { name: 'Open Sam Student' })).toBeInTheDocument();
    const requests = h.calls.filter(call => call.path.startsWith('/api/auth/users?'));
    expect(requests.length).toBeGreaterThan(0);
    for (const request of requests) {
      const query = new URL(request.path, 'http://local').searchParams;
      expect(query.get('role')).toBe('student');
      expect(query.get('include_inactive')).not.toBe('true');
    }
  });

  it('filters real roles and inactive accounts while searching only loaded accounts', async () => {
    const h = await mount();
    expect(await screen.findByRole('link', { name: 'Open Sam Student' })).toHaveAttribute('href', '/personas/3');
    await h.user.selectOptions(screen.getByLabelText('Filter by role'), 'teacher');
    expect(await screen.findByRole('link', { name: 'Open Taylor Teacher' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Open Sam Student' })).not.toBeInTheDocument();
    h.records[1].active = false;
    await h.user.selectOptions(screen.getByLabelText('Account status'), 'inactive');
    expect(await screen.findByText('Inactive')).toBeInTheDocument();
    expect(h.calls.some(call => call.path === '/api/auth/users?limit=500&role=teacher&include_inactive=true')).toBe(true);
    await h.user.type(screen.getByLabelText('Find in this list'), 'not-present');
    expect(await screen.findByText('No accounts to show')).toBeInTheDocument();
  });
  it.each(['en', 'es'] as const)('keeps D3 safe fields, role and creator session through corrected retry in %s', async language => {
    const h = await mount('/personas/nueva', 'admin', language); const labels = locales[language];
    let rejected = false;
    h.intercept((path, method) => {
      if (path === '/api/auth/register' && method === 'POST' && !rejected) {
        rejected = true; return json({ detail: [{ loc: ['body', 'email'], type: 'value_error', msg: 'ARBITRARY SECRET MESSAGE', input: 'ARBITRARY INPUT', ctx: { reason: 'SECRET CONTEXT' } }] }, 422);
      }
    });
    await completeCreate(h.user, language, 'teacher');
    await h.user.click(screen.getByRole('button', { name: labels.create }));
    const email = screen.getByLabelText(labels.email);
    await waitFor(() => expect(email).toHaveAttribute('aria-invalid', 'true'));
    expect(email).toHaveFocus();
    expect(screen.getByLabelText(labels.username)).toHaveValue('jamie.example');
    expect(screen.getByLabelText(labels.role)).toHaveValue('teacher');
    expect(screen.getByLabelText(labels.password)).toHaveValue(passphrase);
    expect(document.body.textContent).not.toMatch(/ARBITRARY|SECRET|\[object Object\]/);
    await h.user.clear(email); await h.user.type(email, 'jamie.corrected@example.com');
    await h.user.click(screen.getByRole('button', { name: labels.create }));
    expect(await screen.findByRole('heading', { name: labels.created })).toBeInTheDocument();
    expect(h.controller.snapshot().user?.id).toBe(admin.id);
    expect(localStorage.getItem('token')).toBe('synthetic-token-1');
    expect(JSON.stringify(h.queries.getMutationCache().getAll().map(mutation => mutation.state))).not.toContain(passphrase);
    expect(JSON.stringify(h.queries.getQueryCache().getAll().map(query => query.state.data))).not.toContain(passphrase);
    expect(Object.keys(localStorage).some(key => key.includes('draft'))).toBe(false);
    expect(h.calls.filter(call => call.path === '/api/auth/register')).toHaveLength(2);
  });
  it('makes teacher-created student ownership explicit without showing elevated role controls', async () => {
    const h = await mount('/personas/nueva', 'teacher'); await completeCreate(h.user, 'en', null);
    expect(screen.queryByLabelText('Role')).not.toBeInTheDocument();
    await h.user.click(screen.getByRole('button', { name: 'Create account' }));
    expect(await screen.findByRole('heading', { name: 'Account created' })).toBeInTheDocument();
    expect(h.calls.find(call => call.path === '/api/auth/register')?.body).toMatchObject({ role: 'student', teacher_id: 2 });
    expect(h.controller.snapshot().user?.id).toBe(teacher.id);
    expect(screen.getByRole('link', { name: 'Open account' })).toHaveAttribute('href', '/estudiantes/4');
  });
  it('creates an admin student without silent enrollment, then confirms enrollment separately', async () => {
    const h = await mount('/personas/nueva'); await completeCreate(h.user);
    await h.user.click(screen.getByRole('button', { name: 'Create account' }));
    const next = await screen.findByRole('link', { name: 'Choose responsible teacher' });
    expect(h.calls.find(call => call.path === '/api/auth/register')?.body).not.toHaveProperty('teacher_id');
    await h.user.click(next);
    const selector = await screen.findByLabelText('Choose an active teacher'); await h.user.selectOptions(selector, '2');
    await h.user.click(screen.getByRole('button', { name: 'Save enrollment' }));
    expect(h.calls.filter(call => call.method === 'PUT')).toHaveLength(0);
    const dialog = await screen.findByRole('dialog'); expect(within(dialog).getByText(/Private notes are not transferred/)).toBeInTheDocument();
    await h.user.click(within(dialog).getByRole('button', { name: 'Save enrollment' }));
    expect(await screen.findByText('Enrollment saved. Previous assignments are preserved.')).toBeInTheDocument();
    expect(h.calls.find(call => call.method === 'PUT')).toMatchObject({ path: '/api/students/4/teacher', body: { teacher_id: 2 } });
    expect(h.records.find(person => person.id === 4)?.teacher_id).toBe(2);
    await act(async () => { await h.controller.login(teacher.username, passphrase); await h.router.navigate('/personas'); });
    expect(await screen.findByRole('link', { name: 'Open Jamie Example' })).toHaveAttribute('href', '/estudiantes/4');
    expect(h.calls.some(call => call.path === '/api/auth/users?limit=500&role=student')).toBe(true);
  });
  it('requires an explicit administrator role choice and supports creating another administrator', async () => {
    const h = await mount('/personas/nueva'); await completeCreate(h.user, 'en', null);
    await h.user.click(screen.getByRole('button', { name: 'Create account' }));
    await waitFor(() => expect(screen.getByLabelText('Role')).toHaveAttribute('aria-invalid', 'true'));
    expect(h.calls.some(call => call.path === '/api/auth/register')).toBe(false);
    await h.user.selectOptions(screen.getByLabelText('Role'), 'admin');
    await h.user.click(screen.getByRole('button', { name: 'Create account' }));
    expect(await screen.findByRole('heading', { name: 'Account created' })).toBeInTheDocument();
    expect(h.records.find(person => person.id === 4)?.role).toBe('admin');
    await h.user.click(screen.getByRole('button', { name: 'Create another' }));
    expect(screen.getByLabelText('Password')).toHaveValue('');
    expect(screen.getByLabelText('Role')).toHaveValue('');
  });
  it('ignores a late creation response after another account replaces the creator', async () => {
    const h = await mount('/personas/nueva', 'teacher'); let finish!: (response: Response) => void;
    h.intercept(path => path === '/api/auth/register' ? new Promise<Response>(resolve => { finish = resolve; }) : undefined);
    await completeCreate(h.user, 'en', null); await h.user.click(screen.getByRole('button', { name: 'Create account' }));
    await waitFor(() => expect(h.calls.some(call => call.path === '/api/auth/register')).toBe(true));
    await act(async () => { h.controller.lock(); await h.controller.login(admin.username, passphrase); });
    await act(async () => { finish(json({ ...student, id: 4, username: 'jamie.example', first_name: 'Jamie' })); });
    expect(screen.getByLabelText('First name')).toHaveValue('');
    expect(screen.getByLabelText('Role')).toHaveValue('');
    expect(screen.getByLabelText('Password')).toHaveValue('');
    expect(screen.queryByRole('heading', { name: 'Account created' })).not.toBeInTheDocument();
    expect(h.controller.snapshot().user?.id).toBe(admin.id);
  });
  it('supports keyboard dismissal of enrollment confirmation without a write', async () => {
    const h = await mount('/personas/3');
    await h.user.selectOptions(await screen.findByLabelText('Choose an active teacher'), '');
    const save = screen.getByRole('button', { name: 'Save enrollment' }); save.focus();
    await h.user.keyboard('{Enter}');
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    await h.user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(screen.getByLabelText('Choose an active teacher')).toHaveValue('');
    expect(h.calls.filter(call => call.method === 'PUT')).toHaveLength(0);
  });
  it('does not duplicate a pending create or automatically retry unknown outcomes', async () => {
    const h = await mount('/personas/nueva'); let reject!: (error: Error) => void;
    h.intercept(path => path === '/api/auth/register' ? new Promise<Response>((_, fail) => { reject = fail; }) : undefined);
    await completeCreate(h.user);
    const button = screen.getByRole('button', { name: 'Create account' });
    fireEvent.submit(button.closest('form')!); fireEvent.submit(button.closest('form')!);
    await waitFor(() => expect(h.calls.filter(call => call.path === '/api/auth/register')).toHaveLength(1));
    await act(async () => { reject(new TypeError('unsafe network body')); });
    expect(await screen.findByText(/account may have been created/)).toBeInTheDocument();
    expect(button).toBeDisabled(); expect(screen.getByLabelText('Username')).toHaveValue('jamie.example');
    expect(h.calls.filter(call => call.path === '/api/auth/register')).toHaveLength(1);
    expect(document.body.textContent).not.toContain('unsafe network body');
  });
  it('rejects malformed success without clearing input or claiming creation', async () => {
    const h = await mount('/personas/nueva'); h.intercept(path => path === '/api/auth/register' ? json({ id: 4 }) : undefined);
    await completeCreate(h.user); await h.user.click(screen.getByRole('button', { name: 'Create account' }));
    expect(await screen.findByText(/account may have been created/)).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toHaveValue(passphrase);
    expect(screen.queryByRole('heading', { name: 'Account created' })).not.toBeInTheDocument();
  });
  it('loads a deep link directly and does not derive existence from the capped directory', async () => {
    const h = await mount('/personas/3');
    expect(await screen.findByRole('heading', { name: 'Sam Student' })).toBeInTheDocument();
    expect(h.calls.some(call => call.path === '/api/auth/users/3')).toBe(true);
    expect(h.calls.some(call => call.path === '/api/auth/users?limit=500&include_inactive=true')).toBe(false);
    expect(await screen.findByText('No graded score yet')).toBeInTheDocument();
  });
  it.each(['/personas/0', '/personas/-1', '/estudiantes/not-an-id'])('rejects invalid direct-link ID %s without protected data requests', async path => {
    const h = await mount(path);
    expect(await screen.findByRole('alert')).toHaveTextContent('You do not have access');
    expect(h.calls.filter(call => !['/api/auth/me','/api/classroom/messages/unread-count','/api/settings/app'].includes(call.path))).toHaveLength(0);
  });
  it('denies students before issuing account or enrollment reads', async () => {
    const h = await mount('/personas/nueva', 'student');
    expect(await screen.findByText('This resource is not available')).toBeInTheDocument();
    expect(h.calls.filter(call => !['/api/auth/me','/api/classroom/messages/unread-count','/api/settings/app'].includes(call.path))).toHaveLength(0);
  });
  it('shows teachers only their student and no account or enrollment mutations', async () => {
    const h = await mount('/personas', 'teacher');
    await h.user.click(await screen.findByRole('link', { name: 'Open Sam Student' }));
    expect(await screen.findByText('Assigned to you')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Deactivate account' })).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Choose an active teacher')).not.toBeInTheDocument();
    expect(h.calls.some(call => call.path.includes('role=teacher'))).toBe(false);
  });
  it('requires confirmation for status and recovery and never puts reset credentials in Query', async () => {
    const h = await mount('/personas/2');
    await h.user.click(await screen.findByRole('button', { name: 'Deactivate account' }));
    expect(h.calls.some(call => call.method === 'PATCH')).toBe(false);
    await h.user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Deactivate account' }));
    expect(await screen.findByText('Account status updated. Existing sessions were revoked.')).toBeInTheDocument();
    expect(h.calls.find(call => call.method === 'PATCH')?.body).toEqual({ active: false, confirm: true });
    await h.user.click(screen.getByText('Recover account access'));
    await h.user.type(screen.getByLabelText('New password'), passphrase);
    await h.user.type(screen.getByLabelText('Repeat new password'), passphrase);
    await h.user.click(screen.getByRole('button', { name: 'Reset password' }));
    expect(h.calls.some(call => call.path.endsWith('reset-password'))).toBe(false);
    const dialog = screen.getByRole('dialog'); expect(dialog.textContent).not.toContain(passphrase);
    await h.user.click(within(dialog).getByRole('button', { name: 'Reset password' }));
    expect(await screen.findByText('Password reset. Existing sessions were revoked.')).toBeInTheDocument();
    expect(screen.getByLabelText('New password')).toHaveValue('');
    expect(JSON.stringify(h.queries.getMutationCache().getAll().map(mutation => mutation.state))).not.toContain(passphrase);
  });
  it('suppresses own-account recovery and deactivation', async () => {
    await mount('/personas/1'); await screen.findByRole('heading', { name: 'Alex Admin' });
    expect(screen.queryByRole('button', { name: 'Deactivate account' })).not.toBeInTheDocument();
    expect(screen.queryByText('Recover account access')).not.toBeInTheDocument();
    expect(screen.getByText(/cannot deactivate yourself or the last/)).toBeInTheDocument();
  });
  it('saves only the author’s private notes and retains text edited during a save', async () => {
    const h = await mount('/estudiantes/3', 'teacher'); let finish!: (response: Response) => void;
    const notes = await screen.findByLabelText('Notes');
    h.intercept((path, method) => path.endsWith('/notes') && method === 'POST' ? new Promise<Response>(resolve => { finish = resolve; }) : undefined);
    await h.user.type(notes, 'First snapshot'); await h.user.click(screen.getByRole('button', { name: 'Save notes' }));
    await h.user.type(notes, ' plus later edit');
    await act(async () => { finish(json({ success: true })); });
    await waitFor(() => expect(screen.getByRole('button', { name: 'Save notes' })).toBeEnabled());
    expect(notes).toHaveValue('First snapshot plus later edit');
    expect(screen.queryByText('Notes saved to the server.')).not.toBeInTheDocument();
    expect(h.calls.find(call => call.method === 'POST')?.body).toEqual({ notes: 'First snapshot' });
  });
  it('keeps dirty note text through same-account reauth and verifies the specific account', async () => {
    const h = await mount('/estudiantes/3', 'teacher');
    await h.user.type(await screen.findByLabelText('Notes'), 'Private unfinished teacher text');
    await act(async () => { h.controller.lock(); });
    expect(screen.queryByLabelText('Notes')).not.toBeVisible();
    await act(async () => { await h.controller.login(teacher.username, passphrase); });
    expect(await screen.findByLabelText('Notes')).toHaveValue('Private unfinished teacher text');
    expect(h.calls.filter(call => call.path === '/api/auth/users/3').length).toBeGreaterThan(1);
    expect(h.calls.filter(call => call.method !== 'GET')).toHaveLength(0);
  });
  it('does not reopen hidden text when same-account resource permission is revoked', async () => {
    const h = await mount('/estudiantes/3', 'teacher');
    await h.user.type(await screen.findByLabelText('Notes'), 'Private revoked text');
    h.intercept(path => path === '/api/auth/users/3' ? json({ detail: 'private owner' }, 404) : undefined);
    await act(async () => { h.controller.lock(); });
    await act(async () => { await expect(h.controller.login(teacher.username, passphrase)).rejects.toMatchObject({ status: 404 }); });
    expect(h.controller.snapshot().status).toBe('locked');
    expect(screen.queryByLabelText('Notes')).not.toBeVisible();
  });
  it('discards private note text when another account signs in', async () => {
    const h = await mount('/estudiantes/3', 'teacher');
    await h.user.type(await screen.findByLabelText('Notes'), 'Old account private text');
    await act(async () => { h.controller.lock(); await h.controller.login(admin.username, passphrase); });
    const notes = await screen.findByLabelText('Notes');
    expect(notes).toHaveValue('');
    expect(document.body.textContent).not.toContain('Old account private text');
    expect(h.queries.getQueryCache().getAll().every(query => String(query.queryKey[0]).startsWith('1:'))).toBe(true);
  });
  it('does not render a mismatched account returned for a valid deep link', async () => {
    const h = await mount('/personas/nueva');
    h.intercept(path => path === '/api/auth/users/3' ? json(teacher) : undefined);
    await act(async () => { await h.router.navigate('/personas/3'); });
    expect(await screen.findByRole('alert')).toHaveTextContent('could not be read safely');
    expect(screen.queryByRole('heading', { name: 'Taylor Teacher' })).not.toBeInTheDocument();
    expect(h.calls.some(call => call.path.endsWith('/notes'))).toBe(false);
  });
  it('checks uncertain notes without replaying and recognizes a matching server copy', async () => {
    const h = await mount('/estudiantes/3', 'teacher');
    const notes = await screen.findByLabelText('Notes');
    h.intercept((path, method, body) => {
      if (path.endsWith('/notes') && method === 'POST') {
        h.notes.set('2:3', String(body?.notes)); return Promise.reject(new TypeError('lost response'));
      }
    });
    await h.user.type(notes, 'May already be saved');
    await h.user.click(screen.getByRole('button', { name: 'Save notes' }));
    await h.user.click(await screen.findByRole('button', { name: 'Check saved notes' }));
    expect(await screen.findByText('The current server notes match your text. Nothing was sent again.')).toBeInTheDocument();
    expect(notes).toHaveValue('May already be saved');
    expect(screen.getByRole('button', { name: 'Save notes' })).toBeDisabled();
    expect(h.calls.filter(call => call.method === 'POST')).toHaveLength(1);
  });
  it('retains different local notes after an explicit server check without an automatic overwrite', async () => {
    const h = await mount('/estudiantes/3', 'teacher'); const notes = await screen.findByLabelText('Notes');
    h.intercept((path, method) => path.endsWith('/notes') && method === 'POST' ? Promise.reject(new TypeError('offline')) : undefined);
    await h.user.type(notes, 'Local text'); await h.user.click(screen.getByRole('button', { name: 'Save notes' }));
    await h.user.click(await screen.findByRole('button', { name: 'Check saved notes' }));
    expect(await screen.findByText(/The server has different notes/)).toBeInTheDocument();
    expect(notes).toHaveValue('Local text'); expect(screen.getByLabelText('Current server notes')).toHaveValue('');
    expect(screen.getByRole('button', { name: 'Save notes' })).toBeEnabled();
    expect(h.calls.filter(call => call.method === 'POST')).toHaveLength(1);
  });
  it('keeps local text when current server notes change and requires explicit replacement', async () => {
    const h = await mount('/estudiantes/3', 'teacher');
    const notes = await screen.findByLabelText('Notes'); await h.user.type(notes, 'Local draft');
    h.notes.set('2:3', 'New server version');
    await act(async () => { await h.queries.invalidateQueries(); });
    expect(notes).toHaveValue('Local draft');
    expect(await screen.findByLabelText('Current server notes')).toHaveValue('New server version');
    await h.user.click(screen.getByRole('button', { name: 'Use current server notes' }));
    await h.user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Cancel' }));
    expect(notes).toHaveValue('Local draft');
    await h.user.click(screen.getByRole('button', { name: 'Use current server notes' }));
    await h.user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Use current server notes' }));
    expect(notes).toHaveValue('New server version');
    expect(h.calls.filter(call => call.method === 'POST')).toHaveLength(0);
  });
  it('checks uncertain status without repeating it and requires another confirmation for a new change', async () => {
    const h = await mount('/personas/2');
    h.intercept((path, method) => {
      if (path.endsWith('/status') && method === 'PATCH') { h.records[1].active = false; return Promise.reject(new TypeError('lost receipt')); }
    });
    await h.user.click(await screen.findByRole('button', { name: 'Deactivate account' }));
    await h.user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Deactivate account' }));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    await h.user.click(screen.getByRole('button', { name: 'Reload current data' }));
    expect(await screen.findByText('Current account status checked.')).toBeInTheDocument();
    expect(h.calls.filter(call => call.method === 'PATCH')).toHaveLength(1);
    await h.user.click(screen.getByRole('button', { name: 'Activate account' }));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(h.calls.filter(call => call.method === 'PATCH')).toHaveLength(1);
  });
  it('preserves the last-admin refusal and does not reinterpret it as a successful account change', async () => {
    const h = await mount('/personas/2');
    h.intercept((path, method) => path.endsWith('/status') && method === 'PATCH' ? json({ detail: 'Cannot deactivate yourself or the last active administrator' }, 409) : undefined);
    await h.user.click(await screen.findByRole('button', { name: 'Deactivate account' }));
    await h.user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Deactivate account' }));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.queryByText('Account status updated. Existing sessions were revoked.')).not.toBeInTheDocument();
    expect(h.records[1].active).toBe(true);
  });
  it('keeps a dirty form when Cancel dismisses navigation and leaves only after explicit discard', async () => {
    const h = await mount('/personas/nueva');
    await h.user.type(await screen.findByLabelText('First name'), 'Unsaved');
    await h.user.click(screen.getAllByRole('link', { name: 'Back to list' })[0]);
    await h.user.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Cancel' }));
    expect(h.router.state.location.pathname).toBe('/personas/nueva');
    expect(screen.getByLabelText('First name')).toHaveValue('Unsaved');
    await h.user.click(screen.getAllByRole('link', { name: 'Back to list' })[0]);
    await h.user.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Discard changes and leave' }));
    await waitFor(() => expect(h.router.state.location.pathname).toBe('/personas'));
  });
});


describe('legacy registration role context', () => {
 it.each(['teacher','admin','student'])('prefills an allowed administrator-selected %s role without submitting', async role => { const h = await mount(`/personas/nueva?role=${role}`); expect(await screen.findByLabelText('Role')).toHaveValue(role); expect(h.calls.filter(call => call.method !== 'GET')).toHaveLength(0); });
 it('never elevates a teacher through an admin URL prefill', async () => { const h = await mount('/personas/nueva?role=admin','teacher'); await completeCreate(h.user,'en',null);expect(screen.queryByLabelText('Role')).not.toBeInTheDocument();await h.user.click(screen.getByRole('button',{name:'Create account'}));await screen.findByRole('heading',{name:'Account created'});expect(h.calls.find(call=>call.path==='/api/auth/register')?.body).toMatchObject({role:'student',teacher_id:2}); });
 it('ignores invalid roles without inventing account privileges', async () => { await mount('/personas/nueva?role=superuser'); expect(await screen.findByLabelText('Role')).toHaveValue(''); });
});


it.each(['admin','teacher'] as const)('returns to the filtered People origin for %s', async role => {
 const h=await mount('/personas?role=student&state=all&q=Sam',role);
 await h.user.click(await screen.findByRole('link',{name:'Open Sam Student'}));
 const back=await screen.findByRole('link',{name:locales.en.back});
 expect(back.getAttribute('href')).toContain('q=Sam');
 await h.user.click(back);
 expect(await screen.findByRole('searchbox')).toHaveValue('Sam');
 expect(h.router.state.location.hash).toBe('#person-3');
 if(role==='admin'){expect(screen.getByLabelText('Filter by role')).toHaveValue('student');expect(screen.getByLabelText('Account status')).toHaveValue('all');}
});


it.each(['browser','link'])('restores list scroll with %s return under the same account', async kind => {
 const h=await mount('/personas?q=Sam&role=student');
 await screen.findByRole('link',{name:'Open Sam Student'});
 vi.spyOn(window,'scrollY','get').mockReturnValue(430);
 await h.user.click(screen.getByRole('link',{name:'Open Sam Student'}));
 await screen.findByRole('link',{name:locales.en.back});
 vi.mocked(window.scrollTo).mockClear();
 if(kind==='browser')await act(async()=>h.router.navigate(-1));
 else await h.user.click(screen.getByRole('link',{name:locales.en.back}));
 expect(await screen.findByRole('searchbox')).toHaveValue('Sam');
 expect(window.scrollTo).toHaveBeenCalledWith(0,430);
});
it('direct People links have a fixed local return with no external destination', async () => {
 await mount('/personas/3?return=https://example.test&extra=unknown');
 expect(await screen.findByRole('link',{name:locales.en.back})).toHaveAttribute('href','/personas');
});


it('carries the directory origin through contextual creation and the created account', async () => {
 const h=await mount('/personas?role=student&state=all&q=Sam');
 await h.user.click(await screen.findByRole('link',{name:'Create account'}));
 expect(await screen.findByLabelText(locales.en.role)).toHaveValue('student');
 await completeCreate(h.user);await h.user.click(screen.getByRole('button',{name:'Create account'}));
 await h.user.click(await screen.findByRole('link',{name:locales.en.enrollNext}));
 await h.user.click(await screen.findByRole('link',{name:locales.en.back}));
 expect(await screen.findByRole('searchbox')).toHaveValue('Sam');
 expect(screen.getByLabelText('Filter by role')).toHaveValue('student');
 expect(screen.getByLabelText('Account status')).toHaveValue('all');
});
