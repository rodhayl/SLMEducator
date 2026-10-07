import { useEffect, useRef } from 'react';
import { useAuth } from '@/app/AuthProvider';
/** Private continuations are bound to mount, account and credential epoch. */
export function useDelivery() {
 const { scope, credentialEpoch, status, getSnapshot } = useAuth();
 const lifetime = useRef({ mounted: true, controllers: new Set<AbortController>() });
 useEffect(() => { const value = lifetime.current; value.mounted = true; return () => { value.mounted = false; for (const controller of value.controllers) controller.abort(); value.controllers.clear(); }; }, []);
 useEffect(() => { const value = lifetime.current; return () => { for (const controller of value.controllers) controller.abort(); value.controllers.clear(); }; }, [scope, credentialEpoch, status]);
 return () => {
  const controller = new AbortController(); lifetime.current.controllers.add(controller);
  const current = () => lifetime.current.mounted && getSnapshot().scope === scope && getSnapshot().credentialEpoch === credentialEpoch && getSnapshot().status === 'authenticated';
  return { signal: controller.signal, current, abort: () => controller.abort(), finish: () => lifetime.current.controllers.delete(controller) };
 };
}
