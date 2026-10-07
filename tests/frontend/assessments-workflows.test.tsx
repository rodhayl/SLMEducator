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
import { DraftAdapter } from '@/lib/drafts';
import { routes } from '@/features/assessments/routes';
import { locales } from '@/features/assessments/locales';
import { en, es } from '@/i18n/common';
import type { Role } from '@/lib/types';
import type { Submission } from '@/features/assessments/model';
import { assessment, submission } from './assessments-fixtures';
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } });
type Intercept = (path: string, method: string, body?: Record<string, unknown>) => Response | Promise<Response> | undefined;
const routers: Array<ReturnType<typeof createMemoryRouter>> = [];
beforeEach(() => { vi.spyOn(window, 'scrollTo').mockImplementation(() => undefined); });
afterEach(() => { routers.splice(0).forEach(router => router.dispose()); vi.restoreAllMocks(); });
async function mount(path: string, options: { role?: Role; status?: Submission['status']; language?: 'en' | 'es'; canManage?: boolean; intercept?: Intercept; noAttempts?: boolean } = {}) {
 const role = options.role || 'student'; const language = options.language || 'en'; let actor = { id: role === 'student' ? 3 : role === 'teacher' ? 2 : 1, username: `${role}.example`, first_name: 'Sam', last_name: role, email: `${role}@example.test`, role };
 const data = structuredClone(assessment); data.can_manage = role !== 'student' && options.canManage !== false; if (role === 'student') data.questions.forEach(question => { question.correct_answer = null; });
 const sub = structuredClone(submission); sub.status = options.status || 'draft'; if (role === 'student') sub.answers.forEach(answer => { answer.correct_answer = null; }); if (sub.status === 'draft') sub.answers = [];
 let mode = 'hints_only'; let intercept = options.intercept; const calls: { path: string; method: string; body?: Record<string, unknown> }[] = [];
 const transport = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
  const path = String(input); const method = init?.method || 'GET';
  if (path === '/api/auth/login') { const username = (init?.body as URLSearchParams).get('username'); if (username === 'other.example') actor = { ...actor, id: 44, username, first_name: 'Other' }; return json({ access_token: `synthetic-${actor.id}`, user: actor }); }
  const body = typeof init?.body === 'string' ? JSON.parse(init.body) as Record<string, unknown> : undefined; calls.push({ path, method, body }); const handled = intercept?.(path, method, body); if (handled !== undefined) return handled;
  if (path === '/api/classroom/messages/unread-count') return json({ unread_count: 0 });
  if (path === '/api/auth/me') return json(actor);
  if (path === '/api/settings/timezone') return json({timezone: 'UTC'});
  if (path === '/api/assessments/' && method === 'GET') return json([data]);
  if (path === '/api/assessments/' && method === 'POST') { Object.assign(data, body, { id: 20, can_manage: true, question_count: (body?.questions as unknown[]).length, created_at: assessment.created_at }); return json(data); }
  if (path === '/api/assessments/10' || path === '/api/assessments/20') { if (method === 'PUT') Object.assign(data, body, { is_published: false }); if (method === 'DELETE') return json({ success: true }); return json(data); }
  if (/\/assistance-policy$/.test(path)) { if (method === 'PUT') mode = String(body?.mode); return json({ assessment_id: path.includes('/20/') ? 20 : 10, mode, scope: 'active_attempt' }); }
  if (/\/publish$/.test(path)) { data.is_published = true; return json({ id: data.id, is_published: true }); }
  if (path === '/api/assessments/10/start') return json({ id: sub.id, submission_id: sub.id, status: 'draft' });
  if (path.startsWith('/api/assessments/submissions?') || path === '/api/assessments/submissions') return json(options.noAttempts ? [] : [sub]);
  if (path === '/api/assessments/submissions/55') return json(sub);
  if (path === '/api/assessments/10/submit') { sub.status = 'submitted'; return json({ id: 55, submission_id: 55, status: sub.status, score: null, total_points: 20 }); }
  if (path === '/api/assessments/submissions/55/close') { sub.status = 'abandoned'; return json({ id: 55, submission_id: 55, status: sub.status, score: null, total_points: 20 }); }
  const grade = path.match(/\/responses\/(\d+)\/grade$/); if (grade) { const answer = sub.answers.find(item => item.response_id === Number(grade[1]))!; answer.points = Number(body?.score); answer.feedback = String(body?.feedback || ''); if (sub.answers.every(item => item.points !== null)) { sub.status = 'graded'; sub.score = sub.answers.reduce((sum, item) => sum + item.points!, 0); } return json({ status: 'ok', score: answer.points }); }
  if (path.endsWith('/grade')) { sub.score = Number(body?.score); sub.status = 'graded'; return json({ status: 'ok' }); }
  if (path.endsWith('/accept-ai')) { sub.answers.forEach(item => { item.points ??= item.ai_suggested_score; }); sub.score = sub.answers.reduce((sum, item) => sum + (item.points ?? 0), 0); sub.status = 'graded'; return json({ status: 'ok', final_score: sub.score }); }
  if (path.endsWith('/stats')) return json({ assessment_id: 10, total_submissions: 1, average_score: 0, highest_score: 0, lowest_score: 0, pass_rate: 0 });
  return json({ detail: 'Not found' }, 404);
 });
 const queries = createQueryClient(); localStorage.setItem('token', 'synthetic-token'); const controller = new AuthController(queries, localStorage, transport); const i18n = createInstance();
 await i18n.use(initReactI18next).init({ lng: language, fallbackLng: language, defaultNS: 'common', resources: { en: { common: en, assessments: locales.en }, es: { common: es, assessments: locales.es } }, interpolation: { escapeValue: false } });
 const router = createMemoryRouter([{ element: <ProtectedLayout/>, children: routes }], { initialEntries: [path] }); routers.push(router);
 const result = render(<I18nextProvider i18n={i18n}><QueryClientProvider client={queries}><AuthProvider controller={controller}><RouterProvider router={router}/></AuthProvider></QueryClientProvider></I18nextProvider>);
 await waitFor(() => expect(controller.snapshot().status).toBe('authenticated'));
 return { ...result, user: userEvent.setup(), calls, router, controller, queries, data, sub, transport, intercept: (handler: Intercept) => { intercept = handler; } };
}
const mutations = <T extends { method: string }>(calls: T[]) => calls.filter(call => call.method !== 'GET');
describe('assessment learner journeys', () => {
 it('preflight uses GET only; starting requires explicit confirmation', async () => { const h = await mount('/evaluaciones/10', { noAttempts: true }); await h.user.click(await screen.findByRole('button', { name: 'Start assessment' })); expect(mutations(h.calls)).toHaveLength(0); await h.user.click(screen.getByRole('button', { name: 'Begin attempt' })); await screen.findByRole('timer'); expect(mutations(h.calls).map(call => call.path)).toEqual(['/api/assessments/10/start']); expect(h.router.state.location.pathname).toBe('/intentos/55'); });
 it('an active attempt resumes by GET without reserving or restarting a timer', async () => { const h = await mount('/evaluaciones/10'); await h.user.click(await screen.findByRole('link', { name: 'Resume attempt' })); await screen.findByRole('timer'); expect(mutations(h.calls)).toHaveLength(0); });
 it('restores exact-attempt draft only after explicit choice and submits canonical keys', async () => { new DraftAdapter(3).write('assessment', 10, 55, { answers: [{ question_id: 101, response_text: 'B' }, { question_id: 102, response_text: 'Saved explanation' }] }); const h = await mount('/intentos/55'); const restore = await screen.findByRole('button', { name: 'Restore local draft' }); expect(screen.getByLabelText('Answer to question 2')).toHaveValue(''); await h.user.click(restore); expect(screen.getByLabelText('Answer to question 2')).toHaveValue('Saved explanation'); expect(screen.getByLabelText('Two thirds')).toBeChecked(); await h.user.click(screen.getByRole('button', { name: 'Submit answers' })); const dialog = screen.getByRole('dialog'); expect(within(dialog).getByText(locales.en.submitDescription)).toBeInTheDocument(); await h.user.click(within(dialog).getByRole('button', { name: 'Submit answers' })); await screen.findByText('Submission received'); expect(mutations(h.calls)).toEqual([{ path: '/api/assessments/10/submit', method: 'POST', body: { submission_id: 55, answers: [{ question_id: 101, response_text: 'B' }, { question_id: 102, response_text: 'Saved explanation' }] } }]); expect(new DraftAdapter(3).hasDrafts()).toBe(false); });
 it('requires terminal close confirmation and preserves answers with no grade', async () => { const h = await mount('/intentos/55'); await h.user.type(await screen.findByLabelText('Answer to question 2'), 'Keep my work'); await h.user.click(screen.getByRole('button', { name: 'Close attempt without submitting' })); await h.user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Close attempt without submitting' })); await screen.findByText('Attempt closed'); expect(mutations(h.calls)[0]).toMatchObject({ path: '/api/assessments/submissions/55/close', body: { reason: 'abandoned', answers: [{ question_id: 101, response_text: '' }, { question_id: 102, response_text: 'Keep my work' }] } }); });
 it('history and zero-score feedback never call start and hide private keys', async () => { const h = await mount('/envios/55', { status: 'graded' }); h.sub.score = 0; await act(async () => { await h.queries.invalidateQueries(); }); expect(await screen.findByText('Final score: 0 / 20')).toBeInTheDocument(); expect(screen.queryByText(/Answer key:/)).not.toBeInTheDocument(); expect(mutations(h.calls)).toHaveLength(0); });
 it('keeps drafts on unknown submit outcome and requires GET reconciliation before retry', async () => { const h = await mount('/intentos/55'); await h.user.type(await screen.findByLabelText('Answer to question 2'), 'Keep through failure'); h.intercept((path, method) => { if (path.endsWith('/submit') && method === 'POST') throw new TypeError('PRIVATE SERVER ERROR'); return undefined; }); await h.user.click(screen.getByRole('button', { name: 'Submit answers' })); await h.user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Submit answers' })); expect(await screen.findByText(locales.en.mutationUncertain)).toBeInTheDocument(); expect(mutations(h.calls)).toHaveLength(1); expect(new DraftAdapter(3).hasDrafts()).toBe(true); expect(document.body.textContent).not.toContain('PRIVATE SERVER ERROR'); expect(screen.queryByRole('dialog')).not.toBeInTheDocument(); expect(screen.getByRole('button', { name: 'Submit answers' })).toBeDisabled(); await h.user.click(screen.getByRole('button', { name: 'Refresh server state' })); await waitFor(() => expect(screen.getByRole('button', { name: 'Submit answers' })).toBeEnabled()); expect(mutations(h.calls)).toHaveLength(1); });
 it('unknown-time attempts remain reviewable without synthetic deadlines or auto-submit', async () => { const h = await mount('/intentos/55', { intercept: path => path === '/api/assessments/submissions/55' ? json({ ...submission, status: 'draft', started_at: '2026-10-07T10:40:00', expires_at: null, timing_provenance: 'legacy_unknown', answers: [] }) : undefined }); expect(await screen.findByText(locales.en.timerUnknown)).toBeInTheDocument(); expect(screen.queryByRole('timer')).not.toBeInTheDocument(); expect(mutations(h.calls)).toHaveLength(0); });
 it('student cannot open authoring or staff attempt route', async () => { const h = await mount('/evaluaciones/nueva'); expect(h.calls.filter(call => call.path.startsWith('/api/assessments'))).toHaveLength(0); });
});
describe('assessment author and grading journeys', () => {
 it.each(['teacher', 'admin'] as const)('%s preview cannot reserve attempts or trigger rewards', async role => { const h = await mount('/evaluaciones/10', { role }); expect(await screen.findByText(locales.en.previewNotice)).toBeInTheDocument(); expect(screen.queryByRole('button', { name: 'Start assessment' })).not.toBeInTheDocument(); expect(mutations(h.calls)).toHaveLength(0); await h.user.click(screen.getByRole('button', { name: 'Final-grade statistics' })); expect(await screen.findAllByText('0.0%')).toHaveLength(4); });
 it('visibility never grants editing or grading permission', async () => { const h = await mount('/evaluaciones/10', { role: 'teacher', canManage: false }); expect(await screen.findByText(locales.en.manageOnly)).toBeInTheDocument(); expect(screen.queryByRole('link', { name: 'Edit assessment' })).not.toBeInTheDocument(); await act(async () => { await h.router.navigate('/correcciones/55'); }); await screen.findByRole('alert'); expect(screen.queryByRole('button', { name: 'Save question grade' })).not.toBeInTheDocument(); expect(mutations(h.calls)).toHaveLength(0); });
 it.each(['en', 'es'] as const)('saves a zero last-question score after explaining immediate finalization in %s', async language => { const h = await mount('/correcciones/55?filter=pending', { role: 'teacher', status: 'submitted', language }); const labels = locales[language]; const headings = await screen.findAllByRole('heading', { name: new RegExp(language === 'en' ? 'Grade question' : 'Calificar pregunta') }); const second = headings[1].closest('section')!; const score = within(second).getByLabelText(labels.score); expect(score).toHaveValue(null); await h.user.type(score, '0'); expect(within(second).getByText(labels.lastQuestionWarning)).toBeInTheDocument(); await h.user.click(within(second).getByRole('button', { name: labels.saveQuestion })); expect(mutations(h.calls)).toHaveLength(0); await h.user.click(within(screen.getByRole('dialog')).getByRole('button', { name: labels.save })); await waitFor(() => expect(h.sub.status).toBe('graded')); expect(h.sub.score).toBe(0); expect(mutations(h.calls)[0].body).toEqual({ score: 0, feedback: null }); expect(screen.getByRole('link', { name: labels.backQueue })).toHaveAttribute('href', '/correcciones?filter=pending'); });
 it('blank grade is rejected rather than coercing to zero', async () => { const h = await mount('/correcciones/55', { role: 'teacher', status: 'submitted' }); const headings = await screen.findAllByRole('heading', { name: /Grade question/ }); await h.user.click(within(headings[1].closest('section')!).getByRole('button', { name: 'Save question grade' })); expect(await screen.findByText(locales.en.wholeNumber)).toBeInTheDocument(); expect(mutations(h.calls)).toHaveLength(0); });
 it('AI suggestions populate a dirty draft, never silently accept or override teacher zero', async () => { const h = await mount('/correcciones/55', { role: 'teacher', status: 'ai_graded' }); const headings = await screen.findAllByRole('heading', { name: /Grade question/ }); const first = headings[0].closest('section')!; expect(within(first).getByLabelText('Score')).toHaveValue(0); await h.user.click(within(headings[1].closest('section')!).getByRole('button', { name: 'Use AI suggestion' })); expect(mutations(h.calls)).toHaveLength(0); expect(screen.getByRole('button', { name: 'Approve all AI suggestions' })).toBeDisabled(); });
 it('queue is author-scoped and does not depend on current enrollment reads', async () => { const h = await mount('/correcciones?filter=all', { role: 'teacher', status: 'submitted' }); expect(await screen.findByRole('link', { name: 'Fractions · Sam Student' })).toHaveAttribute('href', '/correcciones/55?filter=all'); expect(h.calls.some(call => /students|auth\/users/.test(call.path))).toBe(false); });
 it('editor saves draft and policy as separate confirmed steps before publication', async () => { const h = await mount('/evaluaciones/10/editar', { role: 'teacher', noAttempts: true }); await h.user.clear(await screen.findByLabelText('Title')); await h.user.type(screen.getByLabelText('Title'), 'Updated fractions'); await h.user.click(screen.getByRole('button', { name: 'Save draft' })); await screen.findByText(locales.en.savedDraft); await h.user.selectOptions(screen.getByLabelText('AI assistance during an active attempt'), 'disabled'); expect(screen.getByRole('button', { name: 'Publish assessment' })).toBeDisabled(); await h.user.click(screen.getByRole('button', { name: 'Save assistance policy' })); await screen.findByText(locales.en.policySaved); await h.user.click(screen.getByRole('button', { name: 'Publish assessment' })); expect(mutations(h.calls).map(call => call.path)).toEqual(['/api/assessments/10', '/api/assessments/10/assistance-policy']); await h.user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Publish assessment' })); await waitFor(() => expect(mutations(h.calls)).toHaveLength(3)); });
 it('existing attempts restrict saves to metadata without resending scoring assets', async () => { const h = await mount('/evaluaciones/10/editar', { role: 'teacher' }); await h.user.type(await screen.findByLabelText('Title'), ' revised'); expect(screen.getAllByLabelText('Question text')[0]).toBeDisabled(); await h.user.click(screen.getByRole('button', { name: 'Save draft' })); await waitFor(() => expect(mutations(h.calls)).toHaveLength(1)); expect(mutations(h.calls)[0].body).toEqual({ title: 'Fractions revised', description: 'Read carefully', max_attempts: 2 }); });
});
describe('assessment interruption and recovery', () => {
 it('hides a dirty attempt during same-account reauth and never replays submit', async () => {
  const h = await mount('/intentos/55'); await h.user.type(await screen.findByLabelText('Answer to question 2'), 'Private unfinished answer'); let denied = false;
  h.intercept((path, method) => { if (path.endsWith('/submit') && method === 'POST' && !denied) { denied = true; return json({ detail: 'Not authenticated' }, 401); } return undefined; });
  await h.user.click(screen.getByRole('button', { name: 'Submit answers' })); await h.user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Submit answers' }));
  await waitFor(() => expect(h.controller.snapshot().status).toBe('locked')); expect(screen.queryByLabelText('Answer to question 2')).not.toBeVisible();
  await act(async () => { await h.controller.login('student.example', 'SyntheticFixture123!'); });
  expect(await screen.findByLabelText('Answer to question 2')).toHaveValue('Private unfinished answer'); expect(mutations(h.calls)).toHaveLength(1);
  expect(h.calls.filter(call => call.path === '/api/assessments/submissions/55').length).toBeGreaterThan(1);
 });
 it('another account cannot restore a prior account draft or see its private answer', async () => {
  const h = await mount('/intentos/55'); await h.user.type(await screen.findByLabelText('Answer to question 2'), 'PRIVATE OLD ANSWER');
  await act(async () => { h.controller.lock(); await h.controller.login('other.example', 'SyntheticFixture123!'); });
  await screen.findByRole('alert'); expect(screen.queryByLabelText('Answer to question 2')).not.toBeInTheDocument(); expect(document.body.textContent).not.toContain('PRIVATE OLD ANSWER'); expect(new DraftAdapter(44).hasDrafts()).toBe(false); expect(new DraftAdapter(3).hasDrafts()).toBe(true);
 });
 it('dirty grading feedback survives reauth and saving a different question', async () => {
  const h = await mount('/correcciones/55', { role: 'teacher', status: 'submitted' }); const headings = await screen.findAllByRole('heading', { name: /Grade question/ });
  await h.user.type(within(headings[0].closest('section')!).getByLabelText('Feedback (optional)'), 'Keep first feedback');
  await act(async () => { h.controller.lock(); }); expect(screen.queryAllByLabelText('Feedback (optional)')[0]).not.toBeVisible();
  await act(async () => { await h.controller.login('teacher.example', 'SyntheticFixture123!'); });
  const next = screen.getAllByRole('heading', { name: /Grade question/ }); const second = next[1].closest('section')!; await h.user.type(within(second).getByLabelText('Score'), '0'); await h.user.click(within(second).getByRole('button', { name: 'Save question grade' })); await h.user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Save' })); await waitFor(() => expect(h.sub.status).toBe('graded'));
  expect(screen.getAllByLabelText('Feedback (optional)')[0]).toHaveValue('Keep first feedback'); expect(mutations(h.calls)).toHaveLength(1);
 });
 it('dirty answer navigation requires an explicit leave decision', async () => {
  const h = await mount('/intentos/55'); await h.user.type(await screen.findByLabelText('Answer to question 2'), 'Unsaved server answer'); await h.user.click(screen.getByRole('link', { name: 'Leave this attempt open' }));
  const dialog = screen.getByRole('dialog'); await h.user.click(within(dialog).getByRole('button', { name: 'Cancel' })); expect(h.router.state.location.pathname).toBe('/intentos/55'); expect(screen.getByLabelText('Answer to question 2')).toHaveValue('Unsaved server answer');
 });
 it('single-flight submission rejects repeated confirmation while response is pending', async () => {
  let complete!: (value: Response) => void; const h = await mount('/intentos/55'); await screen.findByLabelText('Answer to question 2'); h.intercept((path, method) => path.endsWith('/submit') && method === 'POST' ? new Promise(resolve => { complete = resolve; }) : undefined);
  await h.user.click(screen.getByRole('button', { name: 'Submit answers' })); await h.user.dblClick(within(screen.getByRole('dialog')).getByRole('button', { name: 'Submit answers' })); expect(mutations(h.calls)).toHaveLength(1); expect(screen.getByRole('button', { name: 'Submit answers' })).toBeDisabled();
  h.sub.status = 'submitted'; await act(async () => { complete(json({ id: 55, submission_id: 55, status: 'submitted', score: null })); }); await screen.findByText('Submission received'); expect(mutations(h.calls)).toHaveLength(1);
 });
 it('assistance-policy read failure blocks editor writes and publication', async () => {
  const h = await mount('/evaluaciones/10/editar', { role: 'teacher', intercept: path => path.endsWith('/assistance-policy') ? json({ detail: 'sensitive internal error' }, 500) : undefined }); await screen.findByRole('alert'); expect(screen.queryByRole('button', { name: 'Save draft' })).not.toBeInTheDocument(); expect(document.body.textContent).not.toContain('sensitive internal error'); expect(mutations(h.calls)).toHaveLength(0);
 });
 it('creates an editable draft once but cannot publish until its assistance policy is confirmed', async () => {
  const h = await mount('/evaluaciones/nueva', { role: 'teacher', noAttempts: true }); await h.user.type(await screen.findByLabelText('Title'), 'New assessment'); await h.user.selectOptions(screen.getByLabelText('Question type'), 'short_answer'); await h.user.type(screen.getByLabelText('Question text'), 'Explain this'); await h.user.click(screen.getByRole('button', { name: 'Save draft' })); await screen.findByText(locales.en.savedDraft); expect(screen.getByRole('button', { name: 'Publish assessment' })).toBeDisabled(); expect(mutations(h.calls).map(call => call.path)).toEqual(['/api/assessments/']); await h.user.click(screen.getByRole('button', { name: 'Save assistance policy' })); await screen.findByText(locales.en.policySaved); expect(screen.getByRole('button', { name: 'Publish assessment' })).toBeEnabled(); expect(mutations(h.calls).map(call => call.path)).toEqual(['/api/assessments/', '/api/assessments/20/assistance-policy']);
 });
 it('rejects malformed grade success and keeps score and feedback without replay', async () => {
  const h = await mount('/correcciones/55', { role: 'teacher', status: 'submitted' }); const headings = await screen.findAllByRole('heading', { name: /Grade question/ }); const second = headings[1].closest('section')!; await h.user.type(within(second).getByLabelText('Score'), '3'); await h.user.type(within(second).getByLabelText('Feedback (optional)'), 'Keep grading text'); h.intercept((path, method) => path.endsWith('/grade') && method === 'POST' ? json({ message: 'ok' }) : undefined); await h.user.click(within(second).getByRole('button', { name: 'Save question grade' })); await h.user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Save' })); await screen.findByText(locales.en.mutationUncertain); expect(within(second).getByLabelText('Score')).toHaveValue(3); expect(within(second).getByLabelText('Feedback (optional)')).toHaveValue('Keep grading text'); expect(within(second).getByRole('button', { name: 'Save question grade' })).toBeDisabled(); expect(mutations(h.calls)).toHaveLength(1);
 });
});
describe('assessment unsupported legacy definitions', () => {
 it.each(['/evaluaciones/10', '/intentos/55'])('blocks ambiguous stored key on %s without changing stored answers', async path => {
  const incompatible = structuredClone(assessment); incompatible.can_manage = false; incompatible.questions[0].options = { choices: ['one', 'two'] }; incompatible.questions[0].correct_answer = null; incompatible.questions[0].options_supported = false;
  const h = await mount(path, { noAttempts: true, intercept: request => request === '/api/assessments/10' ? json(incompatible) : undefined }); expect(await screen.findByText(locales.en.unsupportedOptions)).toBeInTheDocument(); expect(screen.getByRole('button', { name: path.includes('intentos') ? 'Submit answers' : 'Start assessment' })).toBeDisabled(); expect(mutations(h.calls)).toHaveLength(0);
 });
});


describe('closed assessment recovery evidence', () => {
 it.each(['/intentos/55','/envios/55'])('keeps unsubmitted local answers readable at %s after server closure', async path => {
  const drafts = new DraftAdapter(3); const saved = { answers: [{ question_id: 102, response_text: 'Recovered closed answer' }] }; drafts.write('assessment',10,55,saved);
  const before = localStorage.getItem('slm_draft_v1:3:assessment:10:55');
  const h = await mount(path,{status:'abandoned',intercept: route => route === '/api/assessments/submissions/55' ? json({...submission,status:'abandoned',answers:[]}) : undefined});
  await h.user.click(await screen.findByRole('button',{name:'Show local recovery answers'}));
  expect(screen.getByText('Recovered closed answer')).toBeInTheDocument(); expect(localStorage.getItem('slm_draft_v1:3:assessment:10:55')).toBe(before); expect(mutations(h.calls)).toHaveLength(0);
 });
 it('does not expose a different account or attempt recovery', async () => { new DraftAdapter(44).write('assessment',10,55,{answers:[{question_id:102,response_text:'Other account secret'}]});new DraftAdapter(3).write('assessment',10,56,{answers:[{question_id:102,response_text:'Other attempt'}]});await mount('/envios/55',{status:'abandoned'});await screen.findByRole('heading',{name:'Fractions'});expect(screen.queryByRole('button',{name:'Show local recovery answers'})).not.toBeInTheDocument(); });
});

describe('confirmed assessment detail cache', () => {
 it('refreshes preview and reopened editor after saving title, questions and draft state within staleTime', async () => {
  const server = structuredClone(assessment);
  const h = await mount('/evaluaciones/10', {role: 'teacher', noAttempts: true, intercept: (path, method, body) => {
   if (path !== '/api/assessments/10') return undefined;
   if (method === 'PUT') Object.assign(server, body, {is_published: false, questions: (body!.questions as Record<string, unknown>[]).map((question, index) => ({...question, id: 101 + index, options_supported: true}))});
   return json(server);
  }});
  await h.user.click(await screen.findByRole('link', {name: 'Edit assessment'}));
  await h.user.clear(await screen.findByLabelText('Title')); await h.user.type(screen.getByLabelText('Title'), 'Updated fractions');
  const first = screen.getAllByLabelText('Question text')[0]; await h.user.clear(first); await h.user.type(first, 'Choose a fraction');
  await h.user.click(screen.getByRole('button', {name: 'Save draft'})); await screen.findByText(locales.en.savedDraft);
  await h.user.click(screen.getByRole('link', {name: locales.en.preview}));
  await screen.findByRole('heading', {level: 1, name: 'Updated fractions'}); expect(screen.getByText('Choose a fraction')).toBeInTheDocument(); expect(screen.getByText('Draft', {selector: '.badge'})).toBeInTheDocument();
  await h.user.click(screen.getByRole('link', {name: 'Edit assessment'}));
  expect(await screen.findByLabelText('Title')).toHaveValue('Updated fractions'); expect(screen.getAllByLabelText('Question text')[0]).toHaveValue('Choose a fraction');
  expect(mutations(h.calls)).toHaveLength(1);
 });
 it('keeps a confirmed save and local draft intact when the next detail read fails, and retries only the read', async () => {
  const server = structuredClone(assessment); let saved = false; let unavailable = true;
  const h = await mount('/evaluaciones/10/editar', {role: 'teacher', noAttempts: true, intercept: (path, method, body) => {
   if (path !== '/api/assessments/10') return undefined;
   if (method === 'PUT') { saved = true; Object.assign(server, body, {is_published: false, questions: (body!.questions as Record<string, unknown>[]).map((question, index) => ({...question, id: 101 + index, options_supported: true}))}); return json(server); }
   return saved && unavailable ? json({detail: 'synthetic temporary failure'}, 503) : json(server);
  }});
  new DraftAdapter(2).write('assessment', 10, 99, {answers: [{question_id: 102, response_text: 'Preserved local recovery'}]});
  const before = localStorage.getItem('slm_draft_v1:2:assessment:10:99');
  await h.user.clear(await screen.findByLabelText('Title')); await h.user.type(screen.getByLabelText('Title'), 'Confirmed title');
  await h.user.click(screen.getByRole('button', {name: 'Save draft'})); await screen.findByText(locales.en.savedDraft);
  expect(screen.getByLabelText('Title')).toHaveValue('Confirmed title');
  await h.user.click(screen.getByRole('link', {name: locales.en.preview})); await screen.findByRole('alert');
  expect(mutations(h.calls)).toHaveLength(1); expect(localStorage.getItem('slm_draft_v1:2:assessment:10:99')).toBe(before);
  unavailable = false; await h.user.click(screen.getByRole('button', {name: 'Try again'}));
  await screen.findByRole('heading', {level: 1, name: 'Confirmed title'}); expect(mutations(h.calls)).toHaveLength(1);
 });
});

it('waits for invalidated assessment detail before hydrating a reopened editor', async () => {
 const server = structuredClone(assessment); let saved = false; let resolve!: (response: Response) => void;
 const read = new Promise<Response>(done => {resolve = done;});
 const h = await mount('/evaluaciones/10/editar', {role: 'teacher', noAttempts: true, intercept: (path, method, body) => {
  if (path !== '/api/assessments/10') return undefined;
  if (method === 'PUT') {saved = true; Object.assign(server, body, {is_published: false, questions: (body!.questions as Record<string, unknown>[]).map((question, index) => ({...question, id: 101 + index, options_supported: true}))}); return json(server);}
  return saved ? read : json(server);
 }});
 await h.user.clear(await screen.findByLabelText('Title')); await h.user.type(screen.getByLabelText('Title'), 'Reopened saved title');
 await h.user.click(screen.getByRole('button', {name: 'Save draft'})); await screen.findByText(locales.en.savedDraft);
 await h.user.click(screen.getByRole('link', {name: 'Back to assessments'}));
 await act(async () => {await h.router.navigate('/evaluaciones/10/editar');});
 expect(screen.queryByRole('textbox', {name: 'Title'})).not.toBeInTheDocument();
 await act(async () => {resolve(json(server));});
 expect(await screen.findByLabelText('Title')).toHaveValue('Reopened saved title'); expect(mutations(h.calls)).toHaveLength(1);
});
