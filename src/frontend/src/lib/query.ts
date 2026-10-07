import { useEffect, useRef } from 'react';
import { QueryClient, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/app/AuthProvider';
import { ApiError } from './api';
export function createQueryClient() { return new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false, refetchOnReconnect: false, staleTime: 30_000, gcTime: 5 * 60_000 }, mutations: { retry: false, gcTime: 0 } } }); }
export function useResource<T>(key: readonly unknown[], path: string | null) {
  const { api, scope, status, registerResource } = useAuth();
  useEffect(() => path ? registerResource(path) : undefined, [path, scope, registerResource]);
  // A disabled observer must not replace a live observer's query function or expose its cached data.
  const queryKey = path ? [scope, ...key] : [scope, '__disabled_resource__', ...key];
  return useQuery<T, ApiError>({ queryKey, queryFn: ({ signal }) => {
    if (!path) throw new ApiError(0, 'invalid', false, 'unavailable');
    return api.get<T>(path, { signal });
  }, enabled: !!path && status === 'authenticated' });
}
export function useInvalidate() {
  const queries = useQueryClient(); const { scope, credentialEpoch, getSnapshot } = useAuth();
  return async (key: readonly unknown[] = [], options: { exact?: boolean; refetchType?: 'active' | 'inactive' | 'all' | 'none' } = {}) => {
    const current = () => getSnapshot().scope === scope && getSnapshot().credentialEpoch === credentialEpoch && getSnapshot().status === 'authenticated';
    if (!current()) throw new ApiError(0, 'stale', false, 'cancelled');
    await queries.invalidateQueries({ ...options, queryKey: [scope, ...key] });
    if (!current()) throw new ApiError(0, 'stale', false, 'cancelled');
  };
}
export function useOperation<Input, Output>(operation: (input: Input) => Promise<Output>, onSuccess?: (value: Output, input: Input) => void | Promise<void>) {
  const { scope, credentialEpoch, getSnapshot } = useAuth();
  const owner = useRef(scope); const lock = useRef(false);
  useEffect(() => { owner.current = scope; lock.current = false; }, [scope]);
  const mutation = useMutation<Output, ApiError, Input>({ mutationFn: operation, retry: false, gcTime: 0 });
  async function mutateAsync(input: Input): Promise<Output> {
    if (getSnapshot().scope !== scope || getSnapshot().credentialEpoch !== credentialEpoch) throw new ApiError(0, 'stale', false, 'cancelled');
    if (getSnapshot().status !== 'authenticated') throw new ApiError(401, 'http', false, 'reauth');
    if (lock.current) throw new ApiError(409, 'http', false, 'busy');
    const captured = scope; lock.current = true;
    try {
      const value = await mutation.mutateAsync(input);
      if (getSnapshot().scope !== captured || getSnapshot().credentialEpoch !== credentialEpoch || getSnapshot().status !== 'authenticated') throw new ApiError(0, 'stale', true, 'uncertain');
      await onSuccess?.(value, input); return value;
    } finally { if (owner.current === captured) lock.current = false; }
  }
  return { ...mutation, mutateAsync, mutate: (input: Input) => { void mutateAsync(input).catch(() => undefined); } };
}
