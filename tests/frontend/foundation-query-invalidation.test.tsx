import { act, renderHook, waitFor } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ReactNode } from 'react';
import { createQueryClient, useInvalidate, useResource } from '@/lib/query';
const auth = vi.hoisted(() => ({api: {get: vi.fn()}, scope: 'owner-1', credentialEpoch: 1, status: 'authenticated', registerResource: () => () => undefined}));
vi.mock('@/app/AuthProvider', () => ({useAuth: () => ({...auth, getSnapshot: () => auth})}));
beforeEach(() => { vi.restoreAllMocks(); auth.scope = 'owner-1'; auth.credentialEpoch = 1; auth.status = 'authenticated'; auth.api.get.mockResolvedValue({value: 'existing'}); });
function setup() {
 const client = createQueryClient();
 const wrapper = ({children}: {children: ReactNode}) => <QueryClientProvider client={client}>{children}</QueryClientProvider>;
 return {client, wrapper};
}
describe('scoped exact detail invalidation', () => {
 it('marks just the requested detail stale without refetching an active editor', async () => {
  const {client, wrapper} = setup();
  const {result} = renderHook(() => ({resource: useResource(['detail', 10], '/api/detail/10'), invalidate: useInvalidate()}), {wrapper});
  await waitFor(() => expect(result.current.resource.isSuccess).toBe(true));
  client.setQueryData(['owner-1', 'detail', 10, 'snapshot'], {immutable: true}); client.setQueryData(['owner-1', 'detail', 11], {other: true}); client.setQueryData(['owner-2', 'detail', 10], {private: true});
  const reads = auth.api.get.mock.calls.length;
  await act(() => result.current.invalidate(['detail', 10], {exact: true, refetchType: 'none'}));
  expect(auth.api.get).toHaveBeenCalledTimes(reads); expect(result.current.resource.data).toEqual({value: 'existing'});
  expect(client.getQueryState(['owner-1', 'detail', 10])?.isInvalidated).toBe(true);
  for (const key of [['owner-1', 'detail', 10, 'snapshot'], ['owner-1', 'detail', 11], ['owner-2', 'detail', 10]]) expect(client.getQueryState(key)?.isInvalidated).toBe(false);
 });
 it.each(['scope', 'credentialEpoch', 'status'] as const)('rejects %s changes before and during invalidation', async field => {
  const {client, wrapper} = setup(); const {result} = renderHook(() => useInvalidate(), {wrapper});
  let resolve!: () => void; const delayed = new Promise<void>(done => {resolve = done;});
  const invalidate = vi.spyOn(client, 'invalidateQueries').mockReturnValue(delayed);
  const pending = result.current(['detail', 10], {exact: true, refetchType: 'none'});
  if (field === 'credentialEpoch') auth.credentialEpoch++; else if (field === 'scope') auth.scope = 'owner-2'; else auth.status = 'locked';
  resolve(); await expect(pending).rejects.toMatchObject({kind: 'stale'});
  await expect(result.current(['detail', 10])).rejects.toMatchObject({kind: 'stale'}); expect(invalidate).toHaveBeenCalledTimes(1);
 });
});
