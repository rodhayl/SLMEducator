import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AppearanceProvider } from '@/app/AppearanceProvider';
import { DraftAdapter } from '@/lib/drafts';
import { createQueryClient } from '@/lib/query';
import { en, es } from '@/i18n/common';
import { locales } from '@/features/learning/locales';
import { routes } from '@/features/learning/routes';
import type { StudySession } from '@/features/learning/contracts';

const mocks = vi.hoisted(() => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
  scope: 'account:1', status: 'authenticated', user: { id: 1, role: 'student' },
  guard: vi.fn(), register: vi.fn(() => () => {}),
}));
vi.mock('@/app/AuthProvider', () => ({ useAuth: () => ({
  api: mocks.api, scope: mocks.scope, status: mocks.status, user: mocks.user,
  registerResource: mocks.register,
  getSnapshot: () => ({ scope: mocks.scope, status: mocks.status, user: mocks.user }),
}) }));
vi.mock('@/app/DirtyGuard', () => ({ useDirtyGuard: (dirty: boolean) => mocks.guard(dirty) }));
vi.mock('@/features/learning/LearningHelp', () => ({ LearningHelp: () => null }));

type Language = 'en' | 'es';
const session: StudySession = {
  id: 7, content_id: 4, start_time: '2026-10-07T12:00:00Z', status: 'active', notes: 'Server note',
  duration_minutes: 0, duration_known: true, timestamp_provenance: 'utc',
  content_snapshot: { id: 4, title: 'Pinned lesson', content_type: 'lesson', content_data: { content: 'Pinned reading' } },
  context_revision: { study_plan_id: 9, content_digest: 'pinned' },
};
const plan = { id: 9, title: 'Assigned course', contents: [
  { id: 3, title: 'Earlier lesson', content_type: 'lesson', phase_index: 0, order_index: 0 },
  { id: 4, title: 'Pinned lesson', content_type: 'lesson', phase_index: 0, order_index: 1 },
] };
const progress = { study_plan_id: 9, completed_content_ids: [3], last_content_id: 3, total_contents: 2, completion_percentage: 50 };
const progressText = (language: Language, completed: number) => language === 'en'
  ? `${completed} of 2 materials completed` : `${completed} de 2 materiales completados`;

beforeEach(() => {
  vi.clearAllMocks();
  mocks.api.get.mockImplementation(async (path: string) => {
    if (path.startsWith('/api/learning/history/4')) return [session];
    if (path === '/api/study-plans/9/tree') return plan;
    if (path === '/api/study-plans/9/my-progress') return progress;
    if (path === '/api/settings/timezone') return { timezone: 'UTC' };
    if (path.startsWith('/api/annotations/')) return [];
    throw new Error(`Unexpected fixture GET ${path}`);
  });
});

async function mount(language: Language) {
  const i18n = createInstance();
  await i18n.init({ lng: language, fallbackLng: 'en', defaultNS: 'common', resources: {
    en: { common: en, learning: locales.en }, es: { common: es, learning: locales.es },
  }, interpolation: { escapeValue: false } });
  const router = createMemoryRouter(routes, { initialEntries: ['/estudio/7?content_id=4&plan_id=9'] });
  const query = createQueryClient();
  const view = render(<I18nextProvider i18n={i18n}><QueryClientProvider client={query}>
    <AppearanceProvider><RouterProvider router={router} /></AppearanceProvider>
  </QueryClientProvider></I18nextProvider>);
  await screen.findByText('Pinned reading');
  await waitFor(() => expect(query.isFetching()).toBe(0));
  return { i18n, router, query, view };
}

describe('in-place study locale continuity', () => {
  it.each(['en', 'es'] as const)('retains progress, unsaved notes and focused controls from %s and back', async first => {
    const second: Language = first === 'en' ? 'es' : 'en';
    const { i18n, router, query, view } = await mount(first);
    const reads = mocks.api.get.mock.calls.length;
    await userEvent.click(screen.getByRole('button', { name: locales[first].notes }));
    const notes = screen.getByRole('textbox', { name: locales[first].notesLabel });
    fireEvent.change(notes, { target: { value: 'Unsaved learner thought' } });
    notes.focus();
    await act(async () => { await i18n.changeLanguage(second); });
    expect(screen.getByRole('textbox', { name: locales[second].notesLabel })).toBe(notes);
    expect(notes).toHaveFocus();
    expect(notes).toHaveValue('Unsaved learner thought');

    await userEvent.click(screen.getByRole('button', { name: locales[second].index }));
    expect(screen.getByText(progressText(second, 1))).toBeVisible();
    const earlier = screen.getByRole('button', { name: 'Earlier lesson' });
    earlier.focus();
    const current = screen.getByRole('button', { name: 'Pinned lesson' });
    expect(current).toHaveAttribute('aria-current', 'step');
    expect(current).toBeDisabled();

    await act(async () => { await i18n.changeLanguage(first); });
    expect(screen.getByText(progressText(first, 1))).toBeVisible();
    expect(earlier).toHaveFocus();
    expect(screen.getByRole('button', { name: 'Pinned lesson' })).toBe(current);
    expect(notes).not.toBeVisible();
    expect(notes).toHaveValue('Unsaved learner thought');

    // A later read result changes the counters without replacing the lesson or focus.
    await act(async () => { query.setQueryData([mocks.scope, 'courses', 9, 'progress'], {
      ...progress, completed_content_ids: [3, 4], last_content_id: 4, completion_percentage: 100,
    }); });
    expect(await screen.findByText(progressText(first, 2))).toBeVisible();
    expect(earlier).toHaveFocus();
    await act(async () => { await i18n.changeLanguage(second); });
    expect(screen.getByText(progressText(second, 2))).toBeVisible();
    expect(earlier).toHaveFocus();
    expect(current).toHaveAttribute('aria-current', 'step');

    await userEvent.click(screen.getByRole('button', { name: locales[second].notes }));
    expect(screen.getByRole('textbox', { name: locales[second].notesLabel })).toBe(notes);
    expect(notes).toBeVisible();
    expect(notes).toHaveValue('Unsaved learner thought');
    expect(new DraftAdapter(1).read('notes', 4, 7, (value): value is { notes: string } => !!value)).toEqual({ notes: 'Unsaved learner thought' });
    expect(mocks.guard).toHaveBeenLastCalledWith(true);
    expect(router.state.location.pathname + router.state.location.search).toBe('/estudio/7?content_id=4&plan_id=9');
    expect(mocks.api.get).toHaveBeenCalledTimes(reads);
    expect(mocks.api.post).not.toHaveBeenCalled();
    expect(mocks.api.patch).not.toHaveBeenCalled();
    expect(mocks.api.delete).not.toHaveBeenCalled();
    view.unmount(); query.clear(); router.dispose();
  });
});
