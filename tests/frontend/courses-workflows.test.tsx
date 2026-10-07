import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import { createInstance } from 'i18next';
import { I18nextProvider, initReactI18next } from 'react-i18next';
import { createQueryClient } from '@/lib/query';
import { locales } from '@/features/courses/locales';
import { routes } from '@/features/courses/routes';
import { ApiError } from '@/lib/api';
import { DraftAdapter, DRAFT_TTL } from '@/lib/drafts';
const auth = vi.hoisted(() => ({ user: {id: 7, username: 'synthetic_teacher', role: 'teacher', first_name: 'Teacher', last_name: 'Synthetic', email: 'teacher@example.test'}, scope: 'account:7', status: 'authenticated', api: {get: vi.fn(), post: vi.fn(), put: vi.fn()}, registerResource: () => () => undefined, getSnapshot: () => ({scope: 'account:7', status: 'authenticated'}) }));
vi.mock('@/app/AuthProvider', () => ({useAuth: () => auth}));
vi.mock('@/app/DirtyGuard', () => ({useDirtyGuard: vi.fn(), useDirtyState: () => false}));
const summary = {id: 12, creator_id: 7, title: 'Synthetic physics', description: 'Small demonstration', is_public: false, created_at: '2026-10-07T10:00:00Z'};
const material = {id: 2, title: 'Motion lesson', content_type: 'lesson', difficulty: 1, is_personal: false, creator_id: 7, can_edit: true};
const tree = {...summary, phases: [{name: 'Motion', content_ids: [2]}], contents: [{...material, phase_index: 0, order_index: 0, created_at: summary.created_at}], content_count: 1};
let workflow: {status: string; version: number; read_only: boolean};
let data: Record<string, unknown>;
async function mount(path: string) {
  const i18n = createInstance(); await i18n.use(initReactI18next).init({lng: 'en', fallbackLng: 'en', resources: {en: {courses: locales.en, translation: {loading: 'Loading', cancel: 'Cancel', saved: 'Saved', dirty: 'Unsaved changes', 'errors.uncertain': 'Unknown result', 'errors.failed': 'Could not complete', 'errors.unavailable': 'Unavailable'}}}});
  const router = createMemoryRouter([...routes, {path: 'materiales/:id', element: <p>Material reader</p>}], {initialEntries: [path]});
  const result = render(<I18nextProvider i18n={i18n}><QueryClientProvider client={createQueryClient()}><RouterProvider router={router} /></QueryClientProvider></I18nextProvider>);
  return {...result, router, user: userEvent.setup()};
}
beforeEach(() => {
  vi.clearAllMocks(); auth.user.role = 'teacher'; workflow = {status: 'draft', version: 0, read_only: false};
  data = {'/api/learning/active': null, '/api/study-plans/': [summary], '/api/study-plans/12/tree': tree, '/api/content/': [material, {...material, id: 3, title: 'Reusable practice', content_type: 'exercise'}], '/api/students/': [{id: 8, username: 'learner_a', first_name: 'Alex', last_name: 'Synthetic', teacher_id: 7}, {id: 9, username: 'learner_b', first_name: 'Alex', last_name: 'Synthetic', teacher_id: 7}], '/api/study-plans/12/my-progress': {study_plan_id: 12, completed_content_ids: [], last_content_id: null, completion_percentage: 0}};
  auth.api.get.mockImplementation(async (path: string) => path === '/api/study-plans/12/workflow' ? {...workflow} : data[path]);
  auth.api.put.mockImplementation(async (_path: string, payload: Record<string,unknown>) => ({...summary, ...payload}));
  auth.api.post.mockImplementation(async (path: string, payload: Record<string,unknown>) => {
    if (path.endsWith('/workflow')) {workflow = {...workflow, status: payload.action === 'review' ? 'reviewed' : 'published', version: payload.action === 'review' ? 0 : 1}; return {status: workflow.status, version: workflow.version, snapshot: []};}
    if (path.endsWith('/assign')) {workflow.read_only = true; return {study_plan_id: 12, assigned_student_ids: payload.student_ids, already_assigned_student_ids: []};}
    if (path === '/api/content/') return {...material, id: 15, title: payload.title, difficulty: payload.difficulty};
    return {...summary, ...payload};
  });
});

describe('manual course journeys', () => {
  it('shows assigned courses to students without author controls', async () => {auth.user.role = 'student'; await mount('/cursos'); expect(await screen.findByRole('link', {name: 'Synthetic physics'})).toHaveAttribute('href','/cursos/12'); expect(screen.queryByRole('link', {name: 'Create course'})).not.toBeInTheDocument();});
  it('keeps student course context and never starts a session during reads', async () => {auth.user.role = 'student'; await mount('/cursos/12'); expect(await screen.findByRole('link', {name: 'Continue learning: Motion lesson'})).toHaveAttribute('href', '/materiales/2?plan_id=12'); expect(auth.api.post).not.toHaveBeenCalled(); expect(screen.queryByRole('button', {name: 'Mark reviewed'})).not.toBeInTheDocument();});
  it('continues the matching paused session before an earlier unfinished lesson or marker', async () => {
    auth.user.role = 'student'; data['/api/study-plans/12/tree'] = {...tree, contents: [...tree.contents, {...tree.contents[0], id: 3, title: 'Second lesson', order_index: 1}], content_count: 2};
    data['/api/learning/active'] = {id: 42, content_id: 3, status: 'active', start_time: '2026-10-07T10:00:00Z', notes: 'Paused here', duration_minutes: null, duration_known: true, timestamp_provenance: 'utc', content_snapshot: null, context_revision: {study_plan_id: 12}};
    new DraftAdapter(7).write('learning-location', 'current', 0, {planId: 12, contentId: 2});
    await mount('/cursos/12'); expect(await screen.findByRole('link', {name: 'Continue learning: Second lesson'})).toHaveAttribute('href', '/estudio/42?content_id=3&plan_id=12'); expect(auth.api.post).not.toHaveBeenCalled();
  });
  it('uses an account-scoped saved location when the active session belongs to another course', async () => {
    auth.user.role = 'student'; data['/api/study-plans/12/tree'] = {...tree, contents: [...tree.contents, {...tree.contents[0], id: 3, title: 'Second lesson', order_index: 1}], content_count: 2};
    data['/api/learning/active'] = {id: 42, content_id: 2, status: 'active', start_time: '2026-10-07T10:00:00Z', notes: null, duration_minutes: null, duration_known: true, timestamp_provenance: 'utc', content_snapshot: null, context_revision: {study_plan_id: 99}};
    new DraftAdapter(7).write('learning-location', 'current', 0, {planId: 12, contentId: 3});
    const {router} = await mount('/cursos/12'); expect(await screen.findByRole('link', {name: 'Continue learning: Second lesson'})).toHaveAttribute('href', '/materiales/3?plan_id=12'); expect(router.state.location.pathname).toBe('/cursos/12'); expect(auth.api.post).not.toHaveBeenCalled();
  });
  it.each(['other-account', 'other-course', 'expired', 'missing-material', 'invalid-id'] as const)('ignores an invalid saved learning location: %s', async reason => {
    auth.user.role = 'student'; data['/api/study-plans/12/tree'] = {...tree, contents: [...tree.contents, {...tree.contents[0], id: 3, title: 'Second lesson', order_index: 1}], content_count: 2};
    const now = Date.now(), clock = vi.spyOn(Date, 'now'); if (reason === 'expired') clock.mockReturnValue(now - DRAFT_TTL - 1);
    new DraftAdapter(reason === 'other-account' ? 8 : 7).write('learning-location', 'current', 0, {planId: reason === 'other-course' ? 99 : 12, contentId: reason === 'missing-material' ? 999 : reason === 'invalid-id' ? '3' : 3}); clock.mockRestore();
    await mount('/cursos/12'); expect(await screen.findByRole('link', {name: 'Continue learning: Motion lesson'})).toHaveAttribute('href', '/materiales/2?plan_id=12'); expect(auth.api.post).not.toHaveBeenCalled();
  });
  it('ignores an active session whose material is no longer in the authorized course tree', async () => {
    auth.user.role = 'student'; data['/api/learning/active'] = {id: 42, content_id: 999, status: 'active', start_time: '2026-10-07T10:00:00Z', notes: null, duration_minutes: null, duration_known: true, timestamp_provenance: 'utc', content_snapshot: null, context_revision: {study_plan_id: 12}};
    await mount('/cursos/12'); expect(await screen.findByRole('link', {name: 'Continue learning: Motion lesson'})).toHaveAttribute('href', '/materiales/2?plan_id=12');
  });
  it.each(['network', 'invalid-response'])('shows active-session %s failures rather than claiming no active work', async reason => {
    auth.user.role = 'student'; if (reason === 'invalid-response') data['/api/learning/active'] = {id: 42}; else auth.api.get.mockImplementation(async (path: string) => {if (path === '/api/learning/active') throw new ApiError(0, 'network', false, 'network'); return path.endsWith('/workflow') ? {...workflow} : data[path];});
    await mount('/cursos/12'); expect(await screen.findByRole('alert')).toBeInTheDocument(); expect(screen.queryByRole('link', {name: /Continue learning:/})).not.toBeInTheDocument(); expect(screen.getByRole('link', {name: 'Motion lesson'})).toBeInTheDocument(); expect(auth.api.post).not.toHaveBeenCalled();
  });
  it('rejects malformed route IDs without any private API read', async () => {await mount('/cursos/not-an-id/editar'); expect(screen.getByText('This course is unavailable.')).toBeInTheDocument(); expect(auth.api.get).not.toHaveBeenCalled();});
  it('denies management of another teacher public course before fetching its editor resources', async () => {data['/api/study-plans/'] = []; await mount('/cursos/12/editar'); expect(await screen.findByText(/only its author/)).toBeInTheDocument(); expect(auth.api.get.mock.calls.map(call => call[0])).toEqual(['/api/study-plans/']);});
  it('saves explicit structure and keyboard order without reviewing or publishing', async () => {
    const {user} = await mount('/cursos/12/editar'); await screen.findByLabelText('Course title');
    await user.selectOptions(screen.getByLabelText('Choose existing material'), '3'); await user.click(screen.getByRole('button', {name: 'Add selected material'}));
    await user.click(screen.getByRole('button', {name: 'Move up: Reusable practice'})); await user.click(screen.getByRole('button', {name: 'Save draft'}));
    await waitFor(() => expect(auth.api.put).toHaveBeenCalledWith('/api/study-plans/12', {title: summary.title, description: summary.description, is_public: false, phases: [{name: 'Motion', content_ids: [3,2]}]}));
    expect(auth.api.post).not.toHaveBeenCalled(); expect(await screen.findByText('Draft saved. Review is required before publishing.')).toBeInTheDocument();
  });
  it('excludes shared personal material and already-attached duplicate options', async () => {data['/api/content/'] = [material, {...material, id: 8, title: 'Private student answer', is_personal: true, creator_id: 8}]; await mount('/cursos/12/editar'); const select = await screen.findByLabelText('Choose existing material'); expect(within(select).queryByRole('option', {name: 'Private student answer'})).not.toBeInTheDocument(); expect(within(select).queryByRole('option', {name: 'Motion lesson'})).not.toBeInTheDocument();});
  it('filters cross-author private material and offers an owned revision to admins', async () => {
    auth.user.role = 'admin'; data['/api/study-plans/12/tree'] = {...tree, creator_id: 9}; data['/api/content/'] = [{...material, creator_id: 9}, {...material, id: 3, title: 'Private admin lesson', public_reuse: false}, {...material, id: 4, title: 'Public original lesson', public_reuse: true}];
    const {user} = await mount('/cursos/12/editar'); const select = await screen.findByLabelText('Choose existing material');
    expect(within(select).queryByRole('option', {name: 'Private admin lesson'})).not.toBeInTheDocument(); expect(within(select).getByRole('option', {name: 'Public original lesson'})).toBeInTheDocument(); expect(screen.getByRole('button', {name: 'Create lesson'})).toBeDisabled(); expect(screen.getByRole('button', {name: 'Create revision'})).toBeEnabled(); expect(screen.getByText(/create a revision owned by you/)).toBeInTheDocument();
    await user.selectOptions(select, '4'); await user.click(screen.getByRole('button', {name: 'Add selected material'})); await user.click(screen.getByRole('button', {name: 'Save draft'}));
    await waitFor(() => expect(auth.api.put).toHaveBeenCalledWith('/api/study-plans/12', {title: summary.title, description: summary.description, is_public: false, phases: [{name: 'Motion', content_ids: [2,4]}]})); expect(auth.api.post).not.toHaveBeenCalled();
  });
  it('rejects recovery that would attach private material from a different course author', async () => {
    auth.user.role = 'admin'; data['/api/study-plans/12/tree'] = {...tree, creator_id: 9}; new DraftAdapter(7).write('course',12,'structure',{title:'Unsafe recovered attachment',description:'',phases:[{name:'Motion',content_ids:[2,3]}]});
    const {user} = await mount('/cursos/12/editar'); await user.click(await screen.findByRole('button',{name:'Restore draft'})); expect(await screen.findByRole('alert')).toBeInTheDocument(); expect(screen.getByLabelText('Course title')).toHaveValue(summary.title); expect(auth.api.put).not.toHaveBeenCalled();
  });
  it('treats denied browser storage as no recovery location', async () => {
    auth.user.role = 'student'; const storage = vi.spyOn(window, 'localStorage', 'get').mockImplementation(() => {throw new DOMException('Storage denied', 'SecurityError');});
    try {await mount('/cursos/12'); expect(await screen.findByRole('link',{name:'Continue learning: Motion lesson'})).toHaveAttribute('href','/materiales/2?plan_id=12');} finally {storage.mockRestore();}
  });
  it('protects assigned structure and allows a separate explicit revision', async () => {workflow = {status: 'published', version: 1, read_only: true}; await mount('/cursos/12/editar'); expect(await screen.findByLabelText('Course title')).toBeDisabled(); expect(screen.getByRole('button', {name: 'Save draft'})).toBeDisabled(); expect(screen.getByRole('button', {name: 'Mark reviewed'})).toBeDisabled(); expect(screen.getByRole('button', {name: 'Create revision'})).toBeEnabled(); expect(auth.api.post).not.toHaveBeenCalled();});
  it('creates a real lesson separately and leaves course attachment unsaved', async () => {
    const {user} = await mount('/cursos/12/editar'); await screen.findByLabelText('Course title'); await user.click(screen.getByRole('button', {name: 'Create lesson'}));
    await user.type(screen.getByLabelText('Lesson title'), 'Energy'); await user.type(screen.getByLabelText('Lesson text'), 'Energy is conserved.'); await user.click(screen.getByRole('button', {name: 'Save lesson and add to unit'}));
    await waitFor(() => expect(auth.api.post).toHaveBeenCalledWith('/api/content/', {title: 'Energy', content_type: 'lesson', content_data: {content: 'Energy is conserved.'}, difficulty: 1, is_personal: false}));
    expect(await screen.findByRole('link', {name: 'Energy'})).toBeInTheDocument(); expect(auth.api.put).not.toHaveBeenCalled(); expect(screen.getByRole('button', {name: 'Mark reviewed'})).toBeDisabled();
  });
  it('keeps review, public publication, and exact student assignment separate', async () => {
    const {user} = await mount('/cursos/12'); await user.click(await screen.findByRole('button', {name: 'Mark reviewed'}));
    await waitFor(() => expect(auth.api.post).toHaveBeenCalledWith('/api/study-plans/12/workflow', {action: 'review', is_public: false}));
    const publish = screen.getByRole('button', {name: 'Publish course'}); await waitFor(() => expect(publish).toBeEnabled()); await user.click(publish);
    const publishDialog = screen.getByRole('dialog'); await user.click(within(publishDialog).getByRole('checkbox')); await user.click(within(publishDialog).getByRole('button', {name: 'Publish course'}));
    await waitFor(() => expect(auth.api.post).toHaveBeenCalledWith('/api/study-plans/12/workflow', {action: 'publish', is_public: true}));
    await user.click(await screen.findByRole('checkbox', {name: 'Alex Synthetic (@learner_b) · ID 9'})); await user.click(screen.getByRole('button', {name: 'Assign course'}));
    const assignDialog = screen.getByRole('dialog'); expect(within(assignDialog).getByText('Selected student IDs: 9')).toBeInTheDocument(); await user.click(within(assignDialog).getByRole('button', {name: 'Assign course'}));
    await waitFor(() => expect(auth.api.post).toHaveBeenCalledWith('/api/study-plans/12/assign', {student_ids: [9]})); expect(await screen.findByText('Assigned: 1. Already assigned: 0.')).toBeInTheDocument();
  });
  it('does not discard a dirty form or claim save on malformed success', async () => {auth.api.put.mockResolvedValue({id: 12}); const {user} = await mount('/cursos/12/editar'); await user.type(await screen.findByLabelText('Course title'), ' edited'); await user.click(screen.getByRole('button', {name: 'Save draft'})); await screen.findByText(/result could not be confirmed/); expect(screen.getByLabelText('Course title')).toHaveValue('Synthetic physics edited'); expect(screen.getByRole('button', {name: 'Save draft'})).toBeDisabled(); expect(screen.queryByText('Draft saved. Review is required before publishing.')).not.toBeInTheDocument();});
  it('prevents automatic replay after an unknown mutation outcome', async () => {auth.api.put.mockRejectedValue(new ApiError(0,'network',true,'uncertain')); const {user} = await mount('/cursos/12/editar'); await user.type(await screen.findByLabelText('Course title'), ' updated'); await user.dblClick(screen.getByRole('button', {name: 'Save draft'})); await screen.findByText(/result could not be confirmed/); expect(auth.api.put).toHaveBeenCalledTimes(1);});
  it('requires explicit restore and refuses a course assigned since the draft was saved', async () => {new DraftAdapter(7).write('course',12,'structure',{title: 'Recovered',description: '',phases: [{name:'Unit',content_ids:[2]}]}); const {user} = await mount('/cursos/12/editar'); expect(await screen.findByLabelText('Course title')).toHaveValue('Synthetic physics'); workflow.read_only = true; await user.click(screen.getByRole('button', {name: 'Restore draft'})); await screen.findByRole('alert'); expect(screen.getByLabelText('Course title')).toHaveValue('Synthetic physics');});
  it('preserves a pending recovery draft until an explicit choice', async () => {const adapter = new DraftAdapter(7), recovery = {title: 'Recovered', description: '', phases: [{name: 'Unit', content_ids: [2]}]}; adapter.write('course', 12, 'structure', recovery); const {user} = await mount('/cursos/12/editar'); const title = await screen.findByLabelText('Course title'); expect(title).toBeDisabled(); await user.click(screen.getByRole('button', {name: 'Restore draft'})); await waitFor(() => expect(title).toHaveValue('Recovered')); expect(title).toBeEnabled(); expect(auth.api.put).not.toHaveBeenCalled();});
  it('rejects malformed assignment receipts instead of displaying success', async () => {workflow.status = 'published'; auth.api.post.mockResolvedValue({study_plan_id:12,assigned_student_ids:[999],already_assigned_student_ids:[]}); const {user} = await mount('/cursos/12'); await user.click(await screen.findByRole('checkbox', {name:'Alex Synthetic (@learner_a) · ID 8'})); await user.click(screen.getByRole('button',{name:'Assign course'})); await user.click(within(screen.getByRole('dialog')).getByRole('button',{name:'Assign course'})); await screen.findByText(/result could not be confirmed/); expect(screen.queryByText(/Assigned: 1/)).not.toBeInTheDocument();});
});
