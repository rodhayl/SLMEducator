import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { createQueryClient } from '@/lib/query';
import { UnreadMessagesBadge } from '@/app/UnreadMessagesBadge';
import { ApiError } from '@/lib/api';
import i18n from '@/i18n';

const auth = vi.hoisted(() => ({ scope: 'account:7', status: 'authenticated', api: { get: vi.fn() }, registerResource: () => () => undefined }));
vi.mock('@/app/AuthProvider', () => ({ useAuth: () => auth }));
beforeEach(async () => { vi.clearAllMocks(); auth.scope = 'account:7'; auth.status = 'authenticated'; await i18n.changeLanguage('en'); });
function mount() { const queries = createQueryClient(); const view = render(<QueryClientProvider client={queries}><UnreadMessagesBadge/></QueryClientProvider>); return { queries, ...view }; }
describe('account-owned unread navigation indicator', () => {
 it('shows the exact count and refreshes with the messages invalidation prefix', async () => {
  auth.api.get.mockResolvedValue({ unread_count: 3 }); const { queries } = mount();
  expect(await screen.findByLabelText('3 unread messages')).toHaveTextContent('3');
  expect(auth.api.get).toHaveBeenCalledWith('/api/classroom/messages/unread-count', expect.objectContaining({ signal: expect.any(AbortSignal) }));
  auth.api.get.mockResolvedValue({ unread_count: 1 }); await act(() => queries.invalidateQueries({ queryKey: ['account:7', 'messages'] }));
  expect(await screen.findByLabelText('1 unread messages')).toHaveTextContent('1');
 });
 it('hides zero instead of claiming an unread message', async () => { auth.api.get.mockResolvedValue({ unread_count: 0 }); const { queries, container } = mount(); await act(() => queries.invalidateQueries()); expect(container).toBeEmptyDOMElement(); });
 it.each([{ unread_count: -1 }, { unread_count: 1.5 }, { unread_count: '2' }, { unread_count: Number.MAX_SAFE_INTEGER + 1 }, null, {}])('does not invent a count from malformed data', async value => { auth.api.get.mockResolvedValue(value); mount(); expect(await screen.findByLabelText('Unread message count is unavailable')).toHaveTextContent('?'); });
 it('reports unavailable on a failed refresh instead of displaying a stale count', async () => { auth.api.get.mockResolvedValue({ unread_count: 4 }); const { queries } = mount(); await screen.findByLabelText('4 unread messages'); auth.api.get.mockRejectedValue(new ApiError(500)); await act(() => queries.invalidateQueries()); expect(await screen.findByLabelText('Unread message count is unavailable')).toBeInTheDocument(); expect(screen.queryByLabelText('4 unread messages')).not.toBeInTheDocument(); });
 it('does no reads while locked', () => { auth.status = 'locked'; mount(); expect(auth.api.get).not.toHaveBeenCalled(); });
});
