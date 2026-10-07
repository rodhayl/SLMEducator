import { act, render, screen, waitFor } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { createQueryClient, useResource } from '@/lib/query';
const auth = vi.hoisted(() => ({ api: { get: vi.fn() }, scope: 'owner-1', status: 'authenticated', registerResource: vi.fn(() => () => undefined) }));
vi.mock('@/app/AuthProvider', () => ({ useAuth: () => auth }));
afterEach(() => { vi.clearAllMocks(); });
function Readers({ disabled = true }: { disabled?: boolean }) {
 const active = useResource<{ value: string }>(['shared'], '/api/value');
 const inactive = useResource<{ value: string }>(['shared'], disabled ? null : '/api/value');
 return <><p data-testid="active">{active.data?.value || 'empty'}</p><p data-testid="inactive">{inactive.data?.value || 'empty'}</p></>;
}
describe('resource observer ownership', () => {
 it('does not let a null-path observer replace an active request on invalidation', async () => {
  auth.api.get.mockResolvedValueOnce({ value: 'first' }).mockResolvedValue({ value: 'second' });
  const query = createQueryClient();
  render(<QueryClientProvider client={query}><Readers /></QueryClientProvider>);
  await waitFor(() => expect(screen.getByTestId('active')).toHaveTextContent('first'));
  await act(() => query.invalidateQueries({ queryKey: ['owner-1', 'shared'] }));
  await waitFor(() => expect(screen.getByTestId('active')).toHaveTextContent('second'));
  for (const call of auth.api.get.mock.calls) expect(call[0]).toBe('/api/value');
  query.clear();
 });
 it('does not expose an active resource result through a disabled resource', async () => {
  auth.api.get.mockResolvedValue({ value: 'private-resource' });
  const query = createQueryClient();
  const view = render(<QueryClientProvider client={query}><Readers /></QueryClientProvider>);
  await waitFor(() => expect(screen.getByTestId('active')).toHaveTextContent('private-resource'));
  expect(screen.getByTestId('inactive')).toHaveTextContent('empty');
  view.rerender(<QueryClientProvider client={query}><Readers disabled={false}/></QueryClientProvider>);
  await waitFor(() => expect(screen.getByTestId('inactive')).toHaveTextContent('private-resource'));
  view.rerender(<QueryClientProvider client={query}><Readers /></QueryClientProvider>);
  expect(screen.getByTestId('inactive')).toHaveTextContent('empty');
  query.clear();
 });
});
