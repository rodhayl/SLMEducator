import { createContext, useCallback, useContext, useEffect, useId, useMemo, useState, type ReactNode } from 'react';
import { useBlocker } from 'react-router';
import { useTranslation } from 'react-i18next';
import { ConfirmDialog } from '@/components/ui';
import { useAuth } from './AuthProvider';
const DirtyContext = createContext<{ dirty: boolean; set: (id: string, dirty: boolean) => void }>({ dirty: false, set() {} });
export function DirtyProvider({ children }: { children: ReactNode }) {
 const [entries, setEntries] = useState<Set<string>>(new Set());
 const set = useCallback((id: string, dirty: boolean) => { setEntries(previous => { if (previous.has(id) === dirty) return previous; const next = new Set(previous); if (dirty) next.add(id); else next.delete(id); return next; }); }, []);
 const value = useMemo(() => ({ dirty: entries.size > 0, set }), [entries, set]);
 return <DirtyContext.Provider value={value}>{children}</DirtyContext.Provider>;
}
export function useDirtyState() { return useContext(DirtyContext).dirty; }
export function useDirtyGuard(dirty: boolean) {
 const id = useId(); const { set } = useContext(DirtyContext);
 useEffect(() => { set(id, dirty); return () => set(id, false); }, [id, dirty, set]);
}
export function NavigationGuard() {
 const dirty = useDirtyState(); const { status } = useAuth(); const { t } = useTranslation();
 const blocker = useBlocker(({ currentLocation, nextLocation }) => (status === 'locked' || (dirty && status === 'authenticated')) && (currentLocation.pathname !== nextLocation.pathname || currentLocation.search !== nextLocation.search));
 useEffect(() => { const beforeUnload = (event: BeforeUnloadEvent) => { if (dirty) { event.preventDefault(); event.returnValue = ''; } }; window.addEventListener('beforeunload', beforeUnload); return () => window.removeEventListener('beforeunload', beforeUnload); }, [dirty]);
 return <ConfirmDialog open={blocker.state === 'blocked'} onOpenChange={open => { if (!open && blocker.state === 'blocked') blocker.reset(); }} title={t('unsavedTitle')} description={t('unsavedDescription')} confirmLabel={t('leave')} destructive onConfirm={() => { if (blocker.state === 'blocked') blocker.proceed(); }}/>;
}
