import { useEffect, useRef, type ReactNode } from 'react';
import { useAuth } from '@/app/AuthProvider';
import { useResource } from '@/lib/query';
import { ApiError } from '@/lib/api';
import { ErrorState, LoadingState } from '@/components/ui';
export function useRead<T>(key: readonly unknown[], path: string | null, parse: (value: unknown) => T) {
 const query = useResource<unknown>(key, path); let data: T | undefined; let error: unknown = query.error;
 try { if (query.data !== undefined) data = parse(query.data); } catch (value) { error = value; }
 return {...query, data, error};
}
export function ReadState({query,children}: {query: {isPending: boolean; error: unknown; refetch: () => Promise<unknown>}; children: ReactNode}) {
 return query.isPending ? <LoadingState/> : query.error ? <ErrorState error={query.error} retry={() => void query.refetch()}/> : <>{children}</>;
}
/** Bind form continuations to the live mount, authenticated account and credential epoch. */
export function useCurrentProgress() {
 const {scope,credentialEpoch,getSnapshot} = useAuth(); const mounted = useRef(true);
 useEffect(() => { mounted.current = true; return () => {mounted.current = false;}; }, []);
 return () => mounted.current && getSnapshot().scope === scope && getSnapshot().credentialEpoch === credentialEpoch && getSnapshot().status === 'authenticated';
}
export function validated<T>(value: unknown, validate: (value: unknown) => value is T): T { if (!validate(value)) throw new ApiError(200,'invalid',false,'invalidResponse'); return value; }
