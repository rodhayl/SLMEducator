import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { createQueryClient } from '@/lib/query';
import { ApiError } from '@/lib/api';
import { TutorPage } from '@/features/tutor/TutorPage';
import { locales } from '@/features/tutor/locales';

const auth = vi.hoisted(() => ({
 status: 'authenticated', scope: '7:1', credentialEpoch: 1,
 user: {id: 7, role: 'student', username: 'synthetic', first_name: '', last_name: '', email: '', grade_level: null},
 api: {get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn()},
 registerResource: vi.fn(() => () => undefined),
}));
vi.mock('@/app/AuthProvider', () => ({useAuth: () => ({...auth, getSnapshot: () => auth})}));

function deferred<T>() {
 let resolve!: (value: T) => void;
 const promise = new Promise<T>(done => {resolve = done;});
 return {promise, resolve};
}
function receipt(id: string, continuing = false, used = 1) {
 return {request_id: id, status: continuing ? 'cancelled' : 'completed', elapsed_seconds: 1,
  provider: 'synthetic', model: 'fixture', tokens_used: null, max_output_tokens: 800,
  requests_used_today: used, requests_limit_daily: 100, provider_may_continue: continuing, cost_known: false};
}
function answer(payload: Record<string, unknown>, response: string, used = 1) {
 return {receipt: receipt(String(payload.client_request_id), false, used), source: null,
  assistance_policy: {mode: 'explanations'}, effective_assistance: payload.assistance,
  status: 'suggestion', response};
}
async function mount() {
 const i18n = createInstance();
 await i18n.init({lng: 'en', fallbackLng: 'en',
  resources: {en: {tutor: locales.en, translation: {cancel: 'Cancel', errors: {failed: 'Safe error'}}}},
  interpolation: {escapeValue: false}});
 const client = createQueryClient();
 render(<QueryClientProvider client={client}><I18nextProvider i18n={i18n}>
  <MemoryRouter initialEntries={['/tutor']}><TutorPage/></MemoryRouter>
 </I18nextProvider></QueryClientProvider>);
 await waitFor(() => expect(screen.getByRole('button', {name: locales.en.askTutor})).toBeEnabled());
 return client;
}
beforeEach(() => {vi.clearAllMocks();});

describe('same-view cancellation recovery (synthetic, no live provider)', () => {
 it.each([false, true])('recovers only after explicit idle readback; failed refresh first: %s', async failRefresh => {
  const provider = deferred<unknown>();
  let activeId: string | null = null, firstPayload: Record<string, unknown> | null = null;
  let failUsage = false;
  const chatPayloads: Record<string, unknown>[] = [];
  auth.api.get.mockImplementation(async (path: string) => {
   if (path === '/api/ai/assistance-policy') return {mode: 'explanations'};
   if (path === '/api/ai/usage') {
    if (failUsage) throw new ApiError(503, 'http', false, 'failed');
    return {requests_used_today: chatPayloads.length, requests_limit_daily: 100, active_request_id: activeId};
   }
   return [];
  });
  auth.api.post.mockImplementation((path: string, payload: Record<string, unknown>) => {
   if (path === '/api/ai/chat') {
    chatPayloads.push(payload);
    if (chatPayloads.length === 1) {
     firstPayload = payload; activeId = String(payload.client_request_id);
     // Keep the first transport pending despite abort to exercise the late-delivery fence.
     return provider.promise;
    }
    return Promise.resolve(answer(payload, 'Second request succeeded', chatPayloads.length));
   }
   if (path === `/api/ai/requests/${activeId}/cancel`) return Promise.resolve(receipt(activeId!, true));
   throw new Error('Unexpected synthetic mutation');
  });
  const client = await mount();
  const prompt = () => screen.getByLabelText(locales.en.prompt);
  const send = () => screen.getByRole('button', {name: locales.en.askTutor});
  fireEvent.change(prompt(), {target: {value: 'Preserved original question'}});
  fireEvent.click(send());
  await waitFor(() => expect(chatPayloads).toHaveLength(1));
  const firstId = String(firstPayload!.client_request_id);
  fireEvent.click(screen.getByRole('button', {name: locales.en.cancelRequest}));
  await screen.findByText(locales.en.cancelledMessage);
  await waitFor(() => expect(client.getQueryData([auth.scope, 'tutor', 'usage', '/api/ai/chat']))
   .toMatchObject({active_request_id: firstId}));
  expect(send()).toBeDisabled();
  expect(prompt()).toHaveValue('Preserved original question');

  // The provider finishes after cancellation, with no remount, tab switch or new POST.
  activeId = null;
  await act(async () => provider.resolve(answer(firstPayload!, 'Late answer must stay hidden')));
  expect(screen.queryByText('Late answer must stay hidden')).not.toBeInTheDocument();
  expect(send()).toBeDisabled();
  expect(chatPayloads).toHaveLength(1);
  fireEvent.click(screen.getByText(locales.en.aiDetails, {selector: 'summary'}));
  const refresh = () => screen.getByRole('button', {name: locales.en.refreshStatus});

  if (failRefresh) {
   failUsage = true;
   fireEvent.click(refresh());
   await waitFor(() => expect(client.getQueryState([auth.scope, 'tutor', 'usage', '/api/ai/chat'])?.status).toBe('error'));
   expect(send()).toBeDisabled();
   expect(prompt()).toHaveValue('Preserved original question');
   expect(chatPayloads).toHaveLength(1);
   failUsage = false;
  }
  fireEvent.click(refresh());
  await waitFor(() => expect(send()).toBeEnabled());
  expect(prompt()).toHaveValue('Preserved original question');
  expect(chatPayloads).toHaveLength(1);
  expect(auth.api.post).toHaveBeenCalledTimes(2); // One chat and one explicit cancel.
  fireEvent.click(send());
  await waitFor(() => expect(screen.getByText('Second request succeeded')).toBeVisible());
  expect(chatPayloads).toHaveLength(2);
  expect(chatPayloads[1].client_request_id).not.toBe(firstId);
  expect(chatPayloads[1]).toMatchObject({message: 'Preserved original question', conversation_history: []});
  expect(auth.api.post).toHaveBeenCalledTimes(3);
  expect(prompt()).toHaveValue('');
  expect(screen.queryByText('Late answer must stay hidden')).not.toBeInTheDocument();
 });
});
