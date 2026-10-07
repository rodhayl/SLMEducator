import { StrictMode, type ReactNode } from 'react';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PracticeBlock } from '../../src/frontend/src/features/learning/PracticeBlock';
import { AnnotationsPanel } from '../../src/frontend/src/features/learning/AnnotationsPanel';
import { toolLocales } from '../../src/frontend/src/features/learning/tool-locales';
import { createQueryClient } from '../../src/frontend/src/lib/query';
import { ApiError } from '../../src/frontend/src/lib/api';
import { DraftAdapter, DRAFT_TTL } from '../../src/frontend/src/lib/drafts';

const state = vi.hoisted(() => ({ auth: { user: { id: 1, role: 'student' }, scope: '1:1', status: 'authenticated', api: { get: vi.fn(), post: vi.fn(), delete: vi.fn() }, registerResource: vi.fn(() => () => undefined) } }));
vi.mock('../../src/frontend/src/app/AuthProvider', () => ({ useAuth: () => ({ ...state.auth, getSnapshot: () => state.auth }), usePrivacyStatus: () => state.auth.status }));
const raw = { question: 'Choose two', options: { first: 'One', second: 'Two' }, correct_answer: 'second', hints: ['First clue', 'Second clue'], explanation: 'Two is the second option.' };
const note = (overrides = {}) => ({ id: 20, content_id: 3, user_id: 1, user_name: 'Synthetic learner', annotation_text: 'Saved note', annotation_type: 'comment', is_public: false, text_selection_start: null, text_selection_end: null, created_at: '2026-10-07T12:00:00+00:00', ...overrides });
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(yes => { resolve = yes; }); return { promise, resolve }; }
function setup(element: ReactNode, language = 'en') {
  const i18n = createInstance();
  void i18n.init({ lng: language, fallbackLng: 'en', initImmediate: false, interpolation: { escapeValue: false }, resources: { en: { learning: toolLocales.en, translation: { loading: 'Loading', idle: 'No unsaved changes', dirty: 'Unsaved changes', saving: 'Saving', saved: 'Saved', uncertain: 'Outcome uncertain', cancel: 'Cancel', retry: 'Retry', errors: { uncertain: 'Outcome uncertain', failed: 'Request failed', invalidResponse: 'Invalid response', conflict: 'Conflict', network: 'Network unavailable', reauth: 'Sign in again' } } }, es: { learning: toolLocales.es } } });
  const client = createQueryClient();
  const wrapper = ({ children }: { children: ReactNode }) => <StrictMode><I18nextProvider i18n={i18n}><QueryClientProvider client={client}>{children}</QueryClientProvider></I18nextProvider></StrictMode>;
  return { ...render(element, { wrapper }), client, i18n };
}
beforeEach(() => {
  vi.restoreAllMocks(); state.auth.user = { id: 1, role: 'student' }; state.auth.scope = '1:1'; state.auth.status = 'authenticated';
  state.auth.api.get.mockReset().mockImplementation(async (path: string) => path.startsWith('/api/content/') ? { id: 3, content_data: raw } : []);
  state.auth.api.post.mockReset(); state.auth.api.delete.mockReset();
});

describe('practice component', () => {
  it('does not mutate on render, gates self-check on own answer and reveals incremental hints', async () => {
    const writes = vi.spyOn(Storage.prototype, 'setItem'); const user = userEvent.setup();
    setup(<PracticeBlock raw={raw} contentId={3} sessionId={8} />);
    expect(writes).not.toHaveBeenCalled(); expect(state.auth.api.get).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: 'Self-check' }));
    expect(screen.getByText('Write or choose your own answer first.')).toBeVisible();
    expect(screen.queryByText('Suggested answer: Two')).not.toBeInTheDocument(); expect(screen.getByLabelText('Choose two')).toHaveFocus();
    await user.click(screen.getByRole('button', { name: 'Show next hint' }));
    expect(screen.getByText('First clue')).toBeVisible(); expect(screen.queryByText('Second clue')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Show next hint' })); expect(screen.getByText('Second clue')).toBeVisible(); expect(screen.getByRole('button', { name: 'Show next hint' })).toBeDisabled();
    await user.selectOptions(screen.getByLabelText('Choose two'), 'Two'); await user.click(screen.getByRole('button', { name: 'Self-check' }));
    expect(screen.getByText('Your choice matches the answer key.')).toBeVisible(); expect(screen.getByText('This is a practice self-check, not a final grade.')).toBeVisible();
    expect(state.auth.api.post).not.toHaveBeenCalled(); expect(state.auth.api.delete).not.toHaveBeenCalled();
    expect(new DraftAdapter(1).read('practice', 3, 8, (value): value is { answers: string[] } => !!value)).toMatchObject({ answers: ['Two'], hints: [2] });
  });
  it.each([['One', 'Compare your response with the answer key.'], ['Two', 'Your choice matches the answer key.']])('checks the %s choice without grades', async (answer, feedback) => {
    const user = userEvent.setup(); setup(<PracticeBlock raw={raw} contentId={3} sessionId={8} />);
    await user.selectOptions(screen.getByLabelText('Choose two'), answer); await user.click(screen.getByRole('button', { name: 'Self-check' })); expect(screen.getByText(feedback)).toBeVisible();
  });
  it.each([['array', ['One', 'Two'], 'B'], ['wrapped array', { choices: ['One', 'Two'] }, 'b'], ['wrapped map', { choices: { first: 'One', second: 'Two' } }, 'second']])('keeps the canonical %s option mapping in the rendered self-check', async (_, options, correct_answer) => {
    const user = userEvent.setup(); setup(<PracticeBlock raw={{ question: 'Choose two', options, correct_answer }} contentId={3} sessionId={8} />);
    await user.selectOptions(screen.getByLabelText('Choose two'), 'Two'); await user.click(screen.getByRole('button', { name: 'Self-check' })); expect(screen.getByText('Your choice matches the answer key.')).toBeVisible();
  });
  it('freezes answers and hints during completion without unmounting the buffer', async () => {
    const user = userEvent.setup(), view = setup(<PracticeBlock raw={raw} contentId={3} sessionId={8} />); await user.selectOptions(screen.getByLabelText('Choose two'), 'Two');
    view.rerender(<PracticeBlock raw={raw} contentId={3} sessionId={8} readOnly />); expect(screen.getByLabelText('Choose two')).toHaveValue('Two'); expect(screen.getByLabelText('Choose two')).toBeDisabled(); expect(screen.getByRole('button', { name: 'Show next hint' })).toBeDisabled(); expect(screen.getByRole('button', { name: 'Self-check' })).toBeDisabled();
  });
  it('keeps free text ungraded and reports absent answer keys honestly', async () => {
    const user = userEvent.setup(); setup(<PracticeBlock raw={{ questions: [{ question: 'Explain it', answer: 'Reference explanation' }, { question: 'No key' }] }} contentId={3} sessionId={8} />);
    await user.type(screen.getByLabelText('Explain it'), 'My independent explanation'); await user.click(screen.getAllByRole('button', { name: 'Self-check' })[0]); expect(screen.getByText('Compare your response with the answer key.')).toBeVisible();
    await user.type(screen.getByLabelText('No key'), 'My answer'); await user.click(screen.getAllByRole('button', { name: 'Self-check' })[1]); expect(screen.getByText('No answer key is available. Ask your teacher to review your response.')).toBeVisible();
  });
  it('offers explicit restoration and revalidates the resource before showing answers', async () => {
    new DraftAdapter(1).write('practice', 3, 8, { answers: ['Two'], hints: [1] });
    const pending = deferred<unknown>(); state.auth.api.get.mockReturnValue(pending.promise);
    const user = userEvent.setup(); setup(<PracticeBlock raw={raw} contentId={3} sessionId={8} />);
    expect(screen.getByLabelText('Choose two')).toHaveValue(''); expect(screen.getByLabelText('Choose two')).toBeDisabled(); expect(state.auth.api.get).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: 'Restore draft' })); expect(state.auth.api.get).toHaveBeenCalledWith('/api/content/3'); expect(screen.getByLabelText('Choose two')).toHaveValue('');
    await act(async () => pending.resolve({ id: 3, content_data: { ...raw, question: 'The current lesson was edited after this session started' } }));
    await waitFor(() => expect(screen.getByLabelText('Choose two')).toHaveValue('Two')); expect(screen.getByText('First clue')).toBeVisible(); expect(screen.queryByText('Second clue')).not.toBeInTheDocument();
  });
  it('rejects wrong resource receipts on restore and permits explicitly discarding the old draft', async () => {
    new DraftAdapter(1).write('practice', 3, 8, { answers: ['Two'], hints: [1] }); state.auth.api.get.mockResolvedValue({ id: 99, content_data: raw });
    const user = userEvent.setup(); setup(<PracticeBlock raw={raw} contentId={3} sessionId={8} />);
    await user.click(screen.getByRole('button', { name: 'Restore draft' })); await screen.findByText('Invalid response'); expect(screen.getByLabelText('Choose two')).toHaveValue('');
    await user.click(screen.getByRole('button', { name: 'Discard draft' })); expect(screen.getByLabelText('Choose two')).toBeEnabled(); expect(new DraftAdapter(1).hasDrafts()).toBe(false);
  });
  it('ignores another owner, session and expired drafts', () => {
    new DraftAdapter(2).write('practice', 3, 8, { answers: ['Two'], hints: [1] }); new DraftAdapter(1).write('practice', 3, 9, { answers: ['Two'], hints: [1] });
    localStorage.setItem('slm_draft_v1:1:practice:3:8', JSON.stringify({ owner: '1', expiresAt: Date.now() - DRAFT_TTL, value: { answers: ['Two'], hints: [1] } }));
    setup(<PracticeBlock raw={raw} contentId={3} sessionId={8} />); expect(screen.queryByRole('button', { name: 'Restore draft' })).not.toBeInTheDocument(); expect(screen.getByLabelText('Choose two')).toHaveValue('');
  });
  it('preserves answers through auxiliary visibility and equivalent props; resets for a new account', async () => {
    const user = userEvent.setup(), dirty = vi.fn(); const view = setup(<div><PracticeBlock raw={raw} contentId={3} sessionId={8} onDirtyChange={dirty} /></div>);
    await user.selectOptions(screen.getByLabelText('Choose two'), 'Two');
    view.rerender(<div hidden><PracticeBlock raw={{ ...raw }} contentId={3} sessionId={8} onDirtyChange={dirty} /></div>); view.rerender(<div><PracticeBlock raw={{ ...raw }} contentId={3} sessionId={8} onDirtyChange={dirty} /></div>);
    expect(screen.getByLabelText('Choose two')).toHaveValue('Two'); expect(screen.queryByRole('button', { name: 'Restore draft' })).not.toBeInTheDocument();
    state.auth.user = { id: 2, role: 'student' }; state.auth.scope = '2:2'; view.rerender(<div><PracticeBlock raw={raw} contentId={3} sessionId={8} onDirtyChange={dirty} /></div>); expect(screen.getByLabelText('Choose two')).toHaveValue('');
  });
  it('does not write a stale practice buffer after an account switch before rerender', () => {
    const writes = vi.spyOn(Storage.prototype, 'setItem'); setup(<PracticeBlock raw={{ question: 'Explain it' }} contentId={3} sessionId={8} />); state.auth.scope = '2:2'; state.auth.user = { id: 2, role: 'student' }; fireEvent.change(screen.getByLabelText('Explain it'), { target: { value: 'New account input' } }); expect(writes).not.toHaveBeenCalled();
  });
  it('retains input and marks dirty when browser draft writes fail', async () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('storage blocked'); }); const dirty = vi.fn(), user = userEvent.setup();
    setup(<PracticeBlock raw={raw} contentId={3} sessionId={8} onDirtyChange={dirty} />); await user.selectOptions(screen.getByLabelText('Choose two'), 'Two');
    expect(screen.getByLabelText('Choose two')).toHaveValue('Two'); expect(screen.getByText(/Browser draft storage is unavailable/)).toBeVisible(); expect(dirty).toHaveBeenLastCalledWith(true);
  });
  it('handles a denied localStorage getter without losing the practice page', async () => {
    const denied = vi.spyOn(window, 'localStorage', 'get').mockImplementation(() => { throw new Error('Denied'); });
    try { const user = userEvent.setup(); setup(<PracticeBlock raw={raw} contentId={3} sessionId={8} />); expect(screen.getByText(/Browser draft storage is unavailable/)).toBeVisible(); await user.selectOptions(screen.getByLabelText('Choose two'), 'Two'); expect(screen.getByLabelText('Choose two')).toHaveValue('Two'); } finally { denied.mockRestore(); }
  });
  it('does not restore answers after completion begins while access is being checked', async () => {
    new DraftAdapter(1).write('practice', 3, 8, { answers: ['Two'], hints: [1] }); const pending = deferred<unknown>(); state.auth.api.get.mockReturnValue(pending.promise);
    const user = userEvent.setup(), view = setup(<PracticeBlock raw={raw} contentId={3} sessionId={8} />); await user.click(screen.getByRole('button', { name: 'Restore draft' })); view.rerender(<PracticeBlock raw={raw} contentId={3} sessionId={8} readOnly />); await act(async () => pending.resolve({ id: 3, content_data: raw })); expect(screen.getByLabelText('Choose two')).toHaveValue(''); expect(screen.getByLabelText('Choose two')).toBeDisabled();
  });
  it('ignores late restoration after content changes', async () => {
    new DraftAdapter(1).write('practice', 3, 8, { answers: ['Two'], hints: [1] }); const pending = deferred<unknown>(); state.auth.api.get.mockReturnValue(pending.promise);
    const user = userEvent.setup(), view = setup(<PracticeBlock raw={raw} contentId={3} sessionId={8} />); await user.click(screen.getByRole('button', { name: 'Restore draft' }));
    view.rerender(<PracticeBlock raw={raw} contentId={4} sessionId={9} />); await act(async () => pending.resolve({ id: 3, content_data: raw })); expect(screen.getByLabelText('Choose two')).toHaveValue('');
  });
  it('renders localized true/false labels and safe user text', async () => {
    const user = userEvent.setup(); setup(<PracticeBlock raw={{ question: '<img onerror=alert(1)>', question_type: 'true_false', correct_answer: false }} contentId={3} sessionId={8} />, 'es');
    expect(document.querySelector('img')).toBeNull(); await user.selectOptions(screen.getByLabelText('<img onerror=alert(1)>'), 'False'); await user.click(screen.getByRole('button', { name: 'Comprobar mi respuesta' })); expect(screen.getByText('Respuesta sugerida: Falso')).toBeVisible();
  });
});

describe('annotations component', () => {
  it('loads without mutation, makes audience explicit and exposes deletion only for own entries', async () => {
    state.auth.user.role = 'teacher'; state.auth.api.get.mockResolvedValue([note(), note({ id: 21, user_id: 2, user_name: 'Another learner', is_public: true })]);
    setup(<AnnotationsPanel contentId={3} />); await screen.findByText('By Another learner'); expect(state.auth.api.get).toHaveBeenCalledWith('/api/annotations/?content_id=3', expect.any(Object));
    expect(screen.getAllByRole('button', { name: 'Delete annotation' })).toHaveLength(1); expect(screen.getByText('Sharing with your teacher and administrators does not share with classmates.')).toBeVisible(); expect(screen.getByLabelText('Audience')).toHaveValue('private'); expect(state.auth.api.post).not.toHaveBeenCalled(); expect(state.auth.api.delete).not.toHaveBeenCalled();
  });
  it('saves only on explicit submit and clears only after a matching receipt', async () => {
    const user = userEvent.setup(), dirty = vi.fn(), pending = deferred<unknown>(); state.auth.api.post.mockReturnValue(pending.promise);
    setup(<AnnotationsPanel contentId={3} onDirtyChange={dirty} />); await user.type(screen.getByLabelText('Your annotation'), 'My note'); await user.selectOptions(screen.getByLabelText('Audience'), 'shared'); expect(state.auth.api.post).not.toHaveBeenCalled(); expect(dirty).toHaveBeenLastCalledWith(true);
    await user.click(screen.getByRole('button', { name: 'Save annotation' })); expect(state.auth.api.post).toHaveBeenCalledWith('/api/annotations/', { content_id: 3, annotation_text: 'My note', annotation_type: 'comment', is_public: true, text_selection_start: null, text_selection_end: null }); expect(screen.getByLabelText('Your annotation')).toHaveValue('My note');
    await act(async () => pending.resolve(note({ annotation_text: 'My note', is_public: true })));
    await screen.findByText('Annotation saved.'); expect(screen.getByLabelText('Your annotation')).toHaveValue(''); expect(dirty).toHaveBeenLastCalledWith(false); expect(localStorage.length).toBe(0);
  });
  it('preserves newer edits made while a save is in flight', async () => {
    const user = userEvent.setup(), pending = deferred<unknown>(); state.auth.api.post.mockReturnValue(pending.promise); setup(<AnnotationsPanel contentId={3} />);
    await user.type(screen.getByLabelText('Your annotation'), 'First'); await user.click(screen.getByRole('button', { name: 'Save annotation' })); await user.type(screen.getByLabelText('Your annotation'), ' plus newer text');
    await act(async () => pending.resolve(note({ annotation_text: 'First' }))); expect(screen.getByLabelText('Your annotation')).toHaveValue('First plus newer text'); expect(screen.getByText('Unsaved changes')).toBeVisible();
  });
  it('preserves memory through failed saves and auxiliary hidden panels', async () => {
    state.auth.api.post.mockRejectedValue(new ApiError(422, 'http', false, 'failed')); const user = userEvent.setup(), view = setup(<div><AnnotationsPanel contentId={3} /></div>);
    await user.type(screen.getByLabelText('Your annotation'), 'Keep this question'); await user.selectOptions(screen.getByLabelText('Type'), 'question'); await user.click(screen.getByRole('button', { name: 'Save annotation' })); await screen.findByText('Request failed');
    view.rerender(<div hidden><AnnotationsPanel contentId={3} /></div>); view.rerender(<div><AnnotationsPanel contentId={3} /></div>); expect(screen.getByLabelText('Your annotation')).toHaveValue('Keep this question'); expect(screen.getByLabelText('Type')).toHaveValue('question'); expect(screen.getByRole('button', { name: 'Save annotation' })).toBeEnabled();
  });
  it('treats a wrong-context receipt as unknown, preserves text and does not replay automatically', async () => {
    state.auth.api.post.mockResolvedValue(note({ content_id: 99, annotation_text: 'Keep me' })); const user = userEvent.setup(); setup(<AnnotationsPanel contentId={3} />);
    await user.type(screen.getByLabelText('Your annotation'), 'Keep me'); await user.click(screen.getByRole('button', { name: 'Save annotation' })); await screen.findByText(/The outcome could not be confirmed/);
    expect(screen.getByLabelText('Your annotation')).toHaveValue('Keep me'); expect(screen.queryByText('Annotation saved.')).not.toBeInTheDocument(); expect(screen.getByRole('button', { name: 'Save annotation' })).toBeDisabled();
    await user.click(screen.getByRole('button', { name: 'Check saved annotations' })); await screen.findByText(/The latest saved annotations/); expect(state.auth.api.post).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole('button', { name: 'Try the action again' })); expect(screen.getByRole('dialog')).toBeVisible(); expect(state.auth.api.post).toHaveBeenCalledTimes(1); await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Cancel' })); expect(state.auth.api.post).toHaveBeenCalledTimes(1);
  });
  it('allows an explicitly confirmed retry after reviewing an unknown save', async () => {
    state.auth.api.post.mockRejectedValueOnce(new ApiError(0, 'network', true, 'uncertain')).mockResolvedValue(note({ annotation_text: 'Retry me' })); const user = userEvent.setup(); setup(<AnnotationsPanel contentId={3} />); await user.type(screen.getByLabelText('Your annotation'), 'Retry me'); await user.click(screen.getByRole('button', { name: 'Save annotation' })); await screen.findByText(/The outcome could not be confirmed/);
    await user.click(screen.getByRole('button', { name: 'Check saved annotations' })); await user.click(await screen.findByRole('button', { name: 'Try the action again' })); await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Try the action again' })); await screen.findByText('Annotation saved.'); expect(state.auth.api.post).toHaveBeenCalledTimes(2); expect(screen.getByLabelText('Your annotation')).toHaveValue('');
  });
  it('requires delete confirmation and validates the deletion receipt', async () => {
    state.auth.api.get.mockResolvedValue([note()]); state.auth.api.delete.mockResolvedValue({ status: 'ok' }); const user = userEvent.setup(); setup(<AnnotationsPanel contentId={3} />);
    await user.click(await screen.findByRole('button', { name: 'Delete annotation' })); expect(state.auth.api.delete).not.toHaveBeenCalled();
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete annotation' })); await screen.findByText(/The outcome could not be confirmed/); expect(state.auth.api.delete).toHaveBeenCalledWith('/api/annotations/20'); expect(screen.queryByText('Annotation deleted.')).not.toBeInTheDocument(); expect(screen.getByText('Saved note')).toBeVisible();
  });
  it('resolves an unknown deletion from the refreshed list without replaying it', async () => {
    state.auth.api.get.mockImplementation(async (path:string) => path.startsWith('/api/annotations/') ? state.auth.api.delete.mock.calls.length ? [] : [note()] : {timezone:'UTC'}); state.auth.api.delete.mockRejectedValue(new ApiError(0, 'network', true, 'uncertain')); const user = userEvent.setup(), dirty = vi.fn(); setup(<AnnotationsPanel contentId={3} onDirtyChange={dirty} />); await user.click(await screen.findByRole('button', { name: 'Delete annotation' })); await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete annotation' })); await screen.findByText(/The outcome could not be confirmed/); await user.click(screen.getByRole('button', { name: 'Check saved annotations' })); await screen.findByText('The latest list no longer contains this annotation.'); expect(state.auth.api.delete).toHaveBeenCalledTimes(1); expect(dirty).toHaveBeenLastCalledWith(false); expect(screen.queryByText('Annotation deleted.')).not.toBeInTheDocument();
  });
  it('confirms successful deletion without mutating another user’s entry', async () => {
    state.auth.api.get.mockImplementation(async (path:string) => path.startsWith('/api/annotations/') ? state.auth.api.delete.mock.calls.length ? [] : [note()] : {timezone:'UTC'}); state.auth.api.delete.mockResolvedValue({ status: 'ok', message: 'Annotation deleted' }); const user = userEvent.setup(); setup(<AnnotationsPanel contentId={3} />);
    await user.click(await screen.findByRole('button', { name: 'Delete annotation' })); await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete annotation' })); await screen.findByText('Annotation deleted.'); await screen.findByText('No annotations yet');
  });
  it('ignores late saves for old content and isolates account changes', async () => {
    const user = userEvent.setup(), pending = deferred<unknown>(); state.auth.api.post.mockReturnValue(pending.promise); const view = setup(<AnnotationsPanel contentId={3} />);
    await user.type(screen.getByLabelText('Your annotation'), 'Old context'); await user.click(screen.getByRole('button', { name: 'Save annotation' })); view.rerender(<AnnotationsPanel contentId={4} />); await user.type(screen.getByLabelText('Your annotation'), 'New context');
    await act(async () => pending.resolve(note({ annotation_text: 'Old context' }))); expect(screen.getByLabelText('Your annotation')).toHaveValue('New context'); expect(screen.queryByText('Annotation saved.')).not.toBeInTheDocument();
    state.auth.scope = '2:2'; state.auth.user.id = 2; view.rerender(<AnnotationsPanel contentId={4} />); expect(screen.getByLabelText('Your annotation')).toHaveValue('');
  });
  it('does not send a stale form after an account switch before rerender', async () => {
    const user = userEvent.setup(); setup(<AnnotationsPanel contentId={3} />); await user.type(screen.getByLabelText('Your annotation'), 'Old account input'); state.auth.scope = '2:2'; state.auth.user = { id: 2, role: 'student' }; await user.click(screen.getByRole('button', { name: 'Save annotation' })); expect(state.auth.api.post).not.toHaveBeenCalled();
  });
  it('hides private work during reauthentication without losing the same-account buffer', async () => {
    const user = userEvent.setup(), view = setup(<AnnotationsPanel contentId={3} />); await user.type(screen.getByLabelText('Your annotation'), 'Private buffer'); state.auth.status = 'locked'; view.rerender(<AnnotationsPanel contentId={3} />); expect(screen.queryByRole('textbox')).not.toBeInTheDocument(); expect(screen.getByLabelText('Your annotation')).not.toBeVisible();
    state.auth.status = 'authenticated'; view.rerender(<AnnotationsPanel contentId={3} />); expect(screen.getByLabelText('Your annotation')).toHaveValue('Private buffer');
  });
  it('hides private annotation dialogs as well as their panel during reauthentication', async () => {
    state.auth.api.get.mockResolvedValue([note()]); const user = userEvent.setup(), view = setup(<AnnotationsPanel contentId={3} />); await user.click(await screen.findByRole('button', { name: 'Delete annotation' })); expect(screen.getByRole('dialog')).toBeVisible(); state.auth.status = 'locked'; view.rerender(<AnnotationsPanel contentId={3} />); expect(screen.queryByRole('dialog')).not.toBeInTheDocument(); expect(state.auth.api.delete).not.toHaveBeenCalled();
    state.auth.status = 'authenticated'; view.rerender(<AnnotationsPanel contentId={3} />); await waitFor(() => expect(screen.getByRole('dialog')).toBeVisible()); expect(state.auth.api.delete).not.toHaveBeenCalled();
  });
  it('rejects foreign private entries and renders annotation text as plain text', async () => {
    state.auth.api.get.mockResolvedValue([note({ annotation_text: '<img onerror=alert(1)>' })]); const view = setup(<AnnotationsPanel contentId={3} />); await screen.findByText('<img onerror=alert(1)>'); expect(document.querySelector('img')).toBeNull();
    state.auth.api.get.mockResolvedValue([note({ id: 30, content_id: 4, user_id: 2 })]); view.rerender(<AnnotationsPanel contentId={4} />); await screen.findByText('Invalid response'); expect(screen.queryByText('Saved note')).not.toBeInTheDocument();
  });
  it('prevents empty submissions and duplicate in-flight sends', async () => {
    const pending = deferred<unknown>(); state.auth.api.post.mockReturnValue(pending.promise); const user = userEvent.setup(); setup(<AnnotationsPanel contentId={3} />); await user.click(screen.getByRole('button', { name: 'Save annotation' })); expect(state.auth.api.post).not.toHaveBeenCalled(); await screen.findByText('Write an annotation first.');
    fireEvent.change(screen.getByLabelText('Your annotation'), { target: { value: 'One save' } }); const button = screen.getByRole('button', { name: 'Save annotation' }); fireEvent.click(button); fireEvent.click(button); await waitFor(() => expect(state.auth.api.post).toHaveBeenCalledTimes(1)); await act(async () => pending.resolve(note({ annotation_text: 'One save' })));
  });
});

describe('annotation metadata provenance', () => {
  it('preserves the legacy note type and does not invent a timezone', async () => {
    state.auth.api.get.mockImplementation(async (path:string) => path.startsWith('/api/annotations/') ? [note({annotation_type:'note',created_at:'2020-04-01T09:30:00'})] : {timezone:'Europe/Madrid'});
    setup(<AnnotationsPanel contentId={3}/>);
    expect(await screen.findByText('2020-04-01T09:30:00 (timezone unknown)')).toBeVisible();expect(screen.getByText('Note')).toBeVisible();
  });
});
