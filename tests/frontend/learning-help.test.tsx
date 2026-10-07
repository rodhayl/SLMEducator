import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClientProvider } from '@tanstack/react-query';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { createQueryClient } from '@/lib/query';
import { ApiError } from '@/lib/api';
import { LearningHelp } from '@/features/learning/LearningHelp';
import type { LearningHelpProps } from '@/features/learning/LearningHelp';
import { helpLocales } from '@/features/learning/help-locales';
import { helpFingerprint, validHelpReceipt, validHelpSource, validTeacherReceipt } from '@/features/learning/help-contracts';

const auth = vi.hoisted(() => ({
  status: 'authenticated' as 'authenticated' | 'locked', scope: '7:1',
  user: { id: 7, role: 'student', username: 'synthetic-learner', first_name: '', last_name: '', email: '', grade_level: null },
  api: { get: vi.fn(), post: vi.fn() }, registerResource: vi.fn(() => () => undefined),
}));
vi.mock('@/app/AuthProvider', () => ({ useAuth: () => ({ ...auth, getSnapshot: () => auth }), usePrivacyStatus: () => auth.status }));
const props: LearningHelpProps = { contentId: 11, planId: 21, sessionId: 31, contextRevision: { version: 'snapshot-a', study_plan_id: 21 }, active: true };
const source = { id: 11, title: 'Synthetic lesson', content_data: 'Source **text**', source_version: 'version-a', truncated: false, references: ['s1'], available_sections: Array.from({ length: 13 }, (_, i) => ({ id: `s${i + 1}`, title: `Section ${i + 1}`, characters: 10 })) };
const usage = { active_request_id: null, requests_used_today: 0, requests_limit_daily: 100 };
function receipt(id: string, extra = {}) { return { request_id: id, status: 'completed', elapsed_seconds: 1, provider: 'synthetic', model: 'no-provider', tokens_used: null, max_output_tokens: 800, requests_used_today: 1, requests_limit_daily: 100, provider_may_continue: false, cost_known: false, ...extra }; }
function suggestion(payload: Record<string, unknown>, extra = {}) { return { receipt: receipt(String(payload.client_request_id)), source, assistance_policy: { mode: 'explanations' }, effective_assistance: payload.assistance, status: 'suggestion', response: 'Synthetic suggestion', ...extra }; }
function teacherResult(payload: Record<string, unknown>, extra = {}) { return { id: 51, student_id: 7, status: 'open', client_request_id: payload.client_request_id, content_id: payload.content_id, study_plan_id: payload.study_plan_id, request_text: `${payload.subject}: ${payload.description}`, priority: payload.urgency, context_revision: props.contextRevision, ...extra }; }
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(done => { resolve = done; }); return { promise, resolve }; }
async function mount(overrides: Partial<LearningHelpProps> = {}, language = 'en') {
  const i18n = createInstance();
  await i18n.init({ lng: language, fallbackLng: 'en', resources: { en: { learning: helpLocales.en, translation: { cancel: 'Cancel', errors: { failed: 'Safe failure', uncertain: 'Outcome unconfirmed' } } }, es: { learning: helpLocales.es } }, interpolation: { escapeValue: false } });
  const client = createQueryClient();
  const tree = (next: Partial<LearningHelpProps> = {}) => <QueryClientProvider client={client}><I18nextProvider i18n={i18n}><LearningHelp {...props} {...overrides} {...next} /></I18nextProvider></QueryClientProvider>;
  const view = render(tree());
  return { ...view, rerenderHelp: (next: Partial<LearningHelpProps> = {}) => view.rerender(tree(next)), client };
}
async function ready() { await waitFor(() => expect(screen.getByRole('button', { name: 'Ask tutor' })).toBeEnabled()); }
async function ask(text = 'A synthetic question') {
  fireEvent.change(screen.getByLabelText('What would you like help with?'), { target: { value: text } });
  fireEvent.click(screen.getByRole('button', { name: 'Ask tutor' }));
  await waitFor(() => expect(auth.api.post).toHaveBeenCalled());
}
async function teacher(text = 'Synthetic details') {
  fireEvent.click(screen.getByRole('button', { name: 'Ask my teacher' }));
  fireEvent.change(screen.getByLabelText('Subject'), { target: { value: 'Synthetic subject' } });
  fireEvent.change(screen.getByLabelText('What have you tried, and where are you stuck?'), { target: { value: text } });
  fireEvent.click(screen.getByRole('button', { name: 'Send help request' }));
  await waitFor(() => expect(auth.api.post).toHaveBeenCalled());
}
beforeEach(() => {
  vi.clearAllMocks(); auth.status = 'authenticated'; auth.scope = '7:1'; auth.user.id = 7; auth.user.role = 'student';
  auth.api.get.mockImplementation(async (path: string) => path.startsWith('/api/ai/context?') ? { source } : path.endsWith('/usage') ? usage : { mode: 'explanations' });
  auth.api.post.mockImplementation(async (path: string, payload: Record<string, unknown>) => path === '/api/ai/chat' ? suggestion(payload) : teacherResult(payload));
});

describe('Learning help synthetic DOM contract (no live providers)', () => {
  it('loads only read-only context, policy, and usage while active', async () => {
    const view = await mount({ active: false }); expect(auth.api.get).not.toHaveBeenCalled();
    view.rerenderHelp({ active: true }); await ready();
    expect(auth.api.get.mock.calls.map(([path]) => path).sort()).toEqual(['/api/ai/assistance-policy', '/api/ai/context?content_id=11&session_id=31&study_plan_id=21', '/api/ai/usage']);
    expect(auth.api.post).not.toHaveBeenCalled();
    expect(screen.getByText(helpLocales.en.help.unverified)).toBeVisible();
  });
  it('retains unsent fields while hidden or same-account locked and clears on identity/context replacement', async () => {
    const dirty = vi.fn(); const view = await mount({ onDirtyChange: dirty }); await ready();
    fireEvent.change(screen.getByLabelText('What would you like help with?'), { target: { value: 'Private draft' } });
    expect(dirty).toHaveBeenLastCalledWith(true);
    view.rerenderHelp({ active: false }); expect(screen.queryByRole('heading', { name: 'Help with this lesson' })).not.toBeInTheDocument();
    view.rerenderHelp(); await ready(); expect(screen.getByLabelText('What would you like help with?')).toHaveValue('Private draft');
    auth.status = 'locked'; view.rerenderHelp(); expect(screen.queryByRole('textbox', { name: 'What would you like help with?' })).not.toBeInTheDocument();
    auth.status = 'authenticated'; view.rerenderHelp(); await ready(); expect(screen.getByLabelText('What would you like help with?')).toHaveValue('Private draft');
    auth.scope = '8:2'; auth.user.id = 8; view.rerenderHelp(); await ready(); expect(screen.getByLabelText('What would you like help with?')).toHaveValue('');
    fireEvent.change(screen.getByLabelText('What would you like help with?'), { target: { value: 'New account draft' } });
    view.rerenderHelp({ contextRevision: { version: 'b' } }); await ready(); expect(screen.getByLabelText('What would you like help with?')).toHaveValue('');
    expect(localStorage.length).toBe(0);
  });
  it('enforces the 12-section limit and sends the captured session/source with unverified output', async () => {
    await mount(); await ready();
    for (const checkbox of screen.getAllByRole('checkbox')) fireEvent.click(checkbox);
    expect(screen.getAllByRole('checkbox').filter(input => (input as HTMLInputElement).checked)).toHaveLength(12);
    expect(screen.getByText(helpLocales.en.help.sectionLimit)).toBeVisible();
    await ask(); await screen.findByText('Synthetic suggestion');
    expect(auth.api.post.mock.calls[0][1]).toMatchObject({ content_id: 11, study_plan_id: 21, session_id: 31, source_version: 'version-a', section_ids: Array.from({ length: 12 }, (_, i) => `s${i + 1}`), assistance: 'hint', conversation_history: [] });
    expect(screen.getByLabelText('What would you like help with?')).toHaveValue('');
    expect(screen.getByText(helpLocales.en.help.costUnknown)).toBeVisible();
    expect(within(screen.getByRole('log')).getByText(helpLocales.en.help.unverified)).toBeVisible();
  });
  it('enforces hints only without changing the server policy', async () => {
    auth.api.get.mockImplementation(async (path: string) => path.includes('/context?') ? { source } : path.endsWith('/usage') ? usage : { mode: 'hints_only' });
    await mount(); await ready(); expect(screen.getByLabelText('Kind of help')).toBeDisabled(); await ask();
    expect(auth.api.post.mock.calls[0][1]).toMatchObject({ assistance: 'hint' });
    expect(auth.api.post.mock.calls.every(([path]) => path === '/api/ai/chat')).toBe(true);
  });
  it('keeps human help available when AI assistance is disabled', async () => {
    auth.api.get.mockImplementation(async (path: string) => path.includes('/context?') ? { source } : path.endsWith('/usage') ? usage : { mode: 'disabled' });
    await mount(); await screen.findByText(helpLocales.en.help.disabled);
    expect(screen.getByRole('button', { name: 'Ask tutor' })).toBeDisabled(); await teacher();
    await screen.findByText('Help request #51 was received and is open for your teacher.');
    expect(auth.api.post.mock.calls[0][0]).toBe('/api/classroom/help');
  });
  it.each(['missing', 'wrong-id', 'wrong-source', 'stricter-policy'])('suppresses %s tutor evidence and keeps the question', async failure => {
    auth.api.post.mockImplementation(async (_path, payload) => suggestion(payload, failure === 'missing' ? { receipt: undefined } : failure === 'wrong-id' ? { receipt: receipt('wrong') } : failure === 'wrong-source' ? { source: { ...source, source_version: 'changed' } } : { assistance_policy: { mode: 'disabled' } }));
    await mount(); await ready(); await ask();
    await waitFor(() => expect(screen.getByRole('button', { name: 'Ask tutor' })).not.toHaveAttribute('aria-busy', 'true'));
    expect(screen.getByLabelText('What would you like help with?')).toHaveValue('A synthetic question');
    expect(screen.queryByText('Synthetic suggestion')).not.toBeInTheDocument();
  });
  it('retries only identical tutor payloads with the same ID and single-flights double clicks', async () => {
    const result = deferred<unknown>(); auth.api.post.mockReturnValueOnce(result.promise);
    await mount(); await ready(); await ask(); fireEvent.click(screen.getByRole('button', { name: 'Ask tutor' })); expect(auth.api.post).toHaveBeenCalledTimes(1);
    await act(async () => result.resolve({})); await screen.findByText(helpLocales.en.help.receiptUnconfirmed);
    await ask('Changed input'); expect(auth.api.post).toHaveBeenCalledTimes(1); await screen.findByText(helpLocales.en.help.requestPending);
    await ask('A synthetic question'); await screen.findByText('Synthetic suggestion');
    expect(auth.api.post.mock.calls[1][1]).toEqual(auth.api.post.mock.calls[0][1]);
  });
  it('keeps same-context tutor delivery running while hidden and shows its result on reopening', async () => {
    const result = deferred<unknown>(); auth.api.post.mockReturnValueOnce(result.promise);
    const view = await mount(); await ready(); await ask(); const payload = auth.api.post.mock.calls[0][1];
    const signal = auth.api.post.mock.calls[0][2]?.signal as AbortSignal;
    view.rerenderHelp({ active: false }); expect(signal.aborted).toBe(false);
    await act(async () => result.resolve(suggestion(payload)));
    expect(screen.getByText('Synthetic suggestion')).not.toBeVisible();
    view.rerenderHelp(); await ready(); expect(screen.getByText('Synthetic suggestion')).toBeVisible();
    expect(auth.api.post).toHaveBeenCalledTimes(1);
    expect(screen.queryByText(helpLocales.en.help.interrupted)).not.toBeInTheDocument();
  });
  it('suppresses the old session response after context changes', async () => {
    const result = deferred<unknown>(); auth.api.post.mockReturnValueOnce(result.promise);
    const view = await mount(); await ready(); await ask(); const payload = auth.api.post.mock.calls[0][1];
    view.rerenderHelp({ sessionId: 32 }); await ready(); await act(async () => result.resolve(suggestion(payload)));
    expect(screen.queryByText('Synthetic suggestion')).not.toBeInTheDocument(); expect(screen.getByLabelText('What would you like help with?')).toHaveValue('');
  });
  it('cancels delivery explicitly, rejects late output, and never promises provider termination or zero cost', async () => {
    const result = deferred<unknown>(); auth.api.post.mockImplementation((path) => path === '/api/ai/chat' ? result.promise : Promise.resolve(receipt(path.split('/')[4], { status: 'cancelled', provider_may_continue: true })));
    await mount(); await ready(); await ask(); const payload = auth.api.post.mock.calls[0][1];
    fireEvent.click(screen.getByRole('button', { name: 'Cancel tutor delivery' })); await screen.findByText(helpLocales.en.help.cancelDone);
    expect(screen.getByText(helpLocales.en.help.providerContinue)).toBeVisible();
    expect(auth.api.post.mock.calls[1][0]).toBe(`/api/ai/requests/${payload.client_request_id}/cancel`);
    await act(async () => result.resolve(suggestion(payload))); expect(screen.queryByText('Synthetic suggestion')).not.toBeInTheDocument();
    expect(screen.getByLabelText('What would you like help with?')).toHaveValue('A synthetic question');
  });
  it.each([{ requests_used_today: 100 }, { active_request_id: 'other-request' }])('respects account usage blocking: %j', async extra => {
    auth.api.get.mockImplementation(async (path: string) => path.includes('/context?') ? { source } : path.endsWith('/usage') ? { ...usage, ...extra } : { mode: 'explanations' });
    await mount(); await screen.findByText('Lesson: Synthetic lesson');
    expect(screen.getByRole('button', { name: 'Ask tutor' })).toBeDisabled(); expect(auth.api.post).not.toHaveBeenCalled();
  });
  it.each(['owner', 'revision', 'request-id', 'priority'])('validates the teacher %s receipt and reuses identical retries', async failure => {
    const mismatch = failure === 'owner' ? { student_id: 8 } : failure === 'revision' ? { context_revision: { version: 'other' } } : failure === 'request-id' ? { client_request_id: 'other' } : { priority: 3 };
    auth.api.post.mockImplementationOnce(async (_path, payload) => teacherResult(payload, mismatch));
    await mount(); await ready(); await teacher(); await screen.findByText(helpLocales.en.help.teacherUnconfirmed);
    expect(screen.getByLabelText('Subject')).toHaveValue('Synthetic subject');
    fireEvent.click(screen.getByRole('button', { name: 'Send help request' })); await screen.findByText('Help request #51 was received and is open for your teacher.');
    expect(auth.api.post.mock.calls[1][1]).toEqual(auth.api.post.mock.calls[0][1]);
  });
  it('blocks changed unconfirmed teacher requests until explicit confirmation', async () => {
    auth.api.post.mockRejectedValueOnce(new ApiError(0, 'network', true, 'uncertain'));
    await mount(); await ready(); await teacher(); await screen.findByText(helpLocales.en.help.teacherUnconfirmed);
    fireEvent.change(screen.getByLabelText('Subject'), { target: { value: 'Changed subject' } }); fireEvent.click(screen.getByRole('button', { name: 'Send help request' }));
    await waitFor(() => expect(auth.api.post).toHaveBeenCalledTimes(1));
    fireEvent.click(screen.getByRole('button', { name: 'Write another help request' })); expect(await screen.findByRole('dialog')).toHaveTextContent(helpLocales.en.help.newTeacherConfirm);
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Cancel' }));
    expect(screen.getByLabelText('Subject')).toHaveValue('Changed subject'); expect(auth.api.post).toHaveBeenCalledTimes(1);
  });
  it('does not render raw error details and keeps failed input', async () => {
    auth.api.post.mockRejectedValueOnce(new Error('<script>secret provider trace</script>'));
    await mount(); await ready(); await ask(); await screen.findByText(helpLocales.en.help.interrupted);
    expect(screen.queryByText(/secret provider trace/)).not.toBeInTheDocument(); expect(screen.getByLabelText('What would you like help with?')).toHaveValue('A synthetic question');
  });
  it('uses the shared sanitized content renderer for responses', async () => {
    auth.api.post.mockImplementation(async (_path, payload) => suggestion(payload, { response: '<img src=x onerror="alert(1)"><script>unsafe()</script>**Safe suggestion**' }));
    const view = await mount(); await ready(); await ask(); await screen.findByText('Safe suggestion');
    expect(view.container.querySelector('script')).toBeNull(); expect(view.container.querySelector('[onerror]')).toBeNull();
  });
  it('retains selected source sections across an unchanged refresh and retries exactly', async () => {
    auth.api.post.mockResolvedValueOnce({});
    await mount(); await ready(); fireEvent.click(screen.getAllByRole('checkbox')[0]); await ask();
    await screen.findByText(helpLocales.en.help.receiptUnconfirmed);
    fireEvent.click(screen.getByRole('button', { name: 'Refresh context and policy' })); await ready();
    expect(screen.getAllByRole('checkbox')[0]).toBeChecked();
    fireEvent.click(screen.getByRole('button', { name: 'Ask tutor' })); await screen.findByText('Synthetic suggestion');
    expect(auth.api.post.mock.calls[1][1]).toEqual(auth.api.post.mock.calls[0][1]);
  });
  it('creates a new tutor ID only after explicit confirmation of an unknown outcome', async () => {
    auth.api.post.mockResolvedValueOnce({}); await mount(); await ready(); await ask(); await screen.findByText(helpLocales.en.help.receiptUnconfirmed);
    const original = auth.api.post.mock.calls[0][1].client_request_id;
    fireEvent.click(screen.getByRole('button', { name: 'Prepare a new request' }));
    const dialog = await screen.findByRole('dialog'); expect(dialog).toHaveTextContent(helpLocales.en.help.newTutorConfirm);
    fireEvent.click(within(dialog).getByRole('button', { name: 'Prepare a new request' }));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument()); await ready();
    expect(auth.api.post).toHaveBeenCalledTimes(1); fireEvent.click(screen.getByRole('button', { name: 'Ask tutor' }));
    await screen.findByText('Synthetic suggestion'); expect(auth.api.post.mock.calls[1][1].client_request_id).not.toBe(original);
  });
  it('keeps a same-account in-flight teacher request unconfirmed after a lock and reuses its ID', async () => {
    const result = deferred<unknown>(); auth.api.post.mockReturnValueOnce(result.promise);
    const view = await mount(); await ready(); await teacher(); const payload = auth.api.post.mock.calls[0][1];
    auth.status = 'locked'; view.rerenderHelp(); await act(async () => result.resolve(teacherResult(payload)));
    auth.status = 'authenticated'; view.rerenderHelp();
    expect(screen.queryByText('Help request #51 was received and is open for your teacher.')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Subject')).toHaveValue('Synthetic subject');
    fireEvent.click(screen.getByRole('button', { name: 'Send help request' })); await screen.findByText('Help request #51 was received and is open for your teacher.');
    expect(auth.api.post.mock.calls[1][1]).toEqual(payload);
  });
  it('does not interrupt a teacher submission when cancelling concurrent tutor delivery', async () => {
    const tutorResult = deferred<unknown>(), humanResult = deferred<unknown>();
    auth.api.post.mockImplementation((path: string) => path === '/api/ai/chat' ? tutorResult.promise : path === '/api/classroom/help' ? humanResult.promise : Promise.resolve(receipt(path.split('/')[4], { status: 'cancelled' })));
    await mount(); await ready(); await ask(); const tutorPayload = auth.api.post.mock.calls[0][1];
    await teacher(); await waitFor(() => expect(auth.api.post).toHaveBeenCalledTimes(2)); const humanPayload = auth.api.post.mock.calls[1][1];
    fireEvent.click(screen.getByRole('button', { name: 'Tutor' })); fireEvent.click(screen.getByRole('button', { name: 'Cancel tutor delivery' }));
    await screen.findByText(helpLocales.en.help.cancelDone); await act(async () => humanResult.resolve(teacherResult(humanPayload)));
    fireEvent.click(screen.getByRole('button', { name: 'Ask my teacher' }));
    expect(screen.getByText('Help request #51 was received and is open for your teacher.')).toBeVisible();
    await act(async () => tutorResult.resolve(suggestion(tutorPayload))); expect(screen.queryByText('Synthetic suggestion')).not.toBeInTheDocument();
  });
  it('reports unknown cancellation without claiming delivery was cancelled', async () => {
    auth.api.post.mockResolvedValueOnce({}); await mount(); await ready(); await ask(); await screen.findByText(helpLocales.en.help.receiptUnconfirmed);
    auth.api.post.mockRejectedValueOnce(new ApiError(0, 'network', true, 'uncertain'));
    fireEvent.click(screen.getByRole('button', { name: 'Cancel tutor delivery' })); await screen.findByText(helpLocales.en.help.cancelUnconfirmed);
    expect(screen.queryByText(helpLocales.en.help.cancelDone)).not.toBeInTheDocument();
    expect(screen.getByLabelText('What would you like help with?')).toHaveValue('A synthetic question');
  });
  it('prevents sending with malformed context and offers read-only refresh', async () => {
    auth.api.get.mockImplementation(async (path: string) => path.includes('/context?') ? { source: { ...source, id: 12 } } : path.endsWith('/usage') ? usage : { mode: 'explanations' });
    await mount(); await screen.findByText(helpLocales.en.help.loadFailed);
    expect(screen.getByRole('button', { name: 'Ask tutor' })).toBeDisabled(); expect(auth.api.post).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Refresh context and policy' })).toBeEnabled();
  });
  it('does not expose learner teacher-send controls to staff', async () => {
    auth.user.role = 'teacher'; await mount(); await ready(); fireEvent.click(screen.getByRole('button', { name: 'Ask my teacher' }));
    expect(screen.getByText(helpLocales.en.help.teacherStudent)).toBeVisible(); expect(screen.queryByRole('button', { name: 'Send help request' })).not.toBeInTheDocument();
  });
  it('provides complete Spanish help labels', async () => {
    await mount({}, 'es'); expect(await screen.findByRole('heading', { name: 'Ayuda con esta lección' })).toBeVisible();
    expect(screen.getByLabelText('¿Con qué necesitas ayuda?')).toBeVisible();
    expect(Object.keys(helpLocales.es.help).sort()).toEqual(Object.keys(helpLocales.en.help).sort());
    expect(helpLocales.es.help.interrupted).toContain('El proveedor puede seguir trabajando y generar cargos.');
  });
});

describe('Learning help synthetic contract validators', () => {
  it('compares nested revisions canonically and rejects malformed/foreign source and cost receipts', () => {
    expect(helpFingerprint({ b: 1, nested: { y: 2, x: 1 } })).toBe(helpFingerprint({ nested: { x: 1, y: 2 }, b: 1 }));
    expect(validHelpSource(source, 11)).toBe(true); expect(validHelpSource(source, 12)).toBe(false);
    expect(validHelpSource({ ...source, available_sections: [source.available_sections[0], source.available_sections[0]] }, 11)).toBe(false);
    expect(validHelpReceipt(receipt('id'), 'id')).toBe(true); expect(validHelpReceipt(receipt('id', { cost_known: true }), 'id')).toBe(false);
    expect(validHelpReceipt(receipt('id', { tokens_used: -1 }), 'id')).toBe(false);
    const payload = { subject: 'a', description: 'b', urgency: 1, content_id: 11, study_plan_id: 21, session_id: 31 };
    expect(validTeacherReceipt(teacherResult({ ...payload, client_request_id: 'id' }), payload, 'id', 7, props.contextRevision)).toBe(true);
  });
});
