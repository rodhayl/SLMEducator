import { createContext, useContext, useEffect, useMemo, useState, useSyncExternalStore, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { PrivacyContext } from './PrivacyContext';
import { AuthController } from './auth-controller';
const AuthContext = createContext<AuthController | null>(null);
export function AuthProvider({ children, controller: supplied }: { children: ReactNode; controller?: AuthController }) {
  const queries = useQueryClient();
  const [controller] = useState(() => supplied || new AuthController(queries));
  useEffect(() => {
    void controller.verify();
    const pageshow = (event: PageTransitionEvent) => { if (event.persisted) void controller.verify(); };
    const storage = (event: StorageEvent) => { if (['token', 'user'].includes(event.key || '') && event.newValue !== event.oldValue) { controller.lock(); void controller.verify(); } };
    window.addEventListener('pageshow', pageshow); window.addEventListener('storage', storage);
    return () => { window.removeEventListener('pageshow', pageshow); window.removeEventListener('storage', storage); };
  }, [controller]);
  const status = useSyncExternalStore(controller.subscribe, controller.snapshot).status;
  return <AuthContext.Provider value={controller}><PrivacyContext.Provider value={status}>{children}</PrivacyContext.Provider></AuthContext.Provider>;
}
export function useAuth() {
  const controller = useContext(AuthContext); if (!controller) throw new Error('AuthProvider required');
  const state = useSyncExternalStore(controller.subscribe, controller.snapshot);
  const api = useMemo(() => controller.api.bind({ scope: state.scope, epoch: state.credentialEpoch, permitted: state.status === 'authenticated' }), [controller, state.scope, state.credentialEpoch, state.status]);
  return { ...state, api, login: (username: string, password: string) => controller.login(username, password), logout: (mode: 'keep' | 'delete') => controller.logout(mode), verify: () => controller.verify(), refreshIdentity: () => controller.refreshIdentity(), requireReauthentication: controller.lock, registerResource: controller.registerResource, getSnapshot: controller.snapshot };
}
