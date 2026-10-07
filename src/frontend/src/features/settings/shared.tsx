import { useEffect, useRef } from 'react';
import { Link } from 'react-router';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/app/AuthProvider';
/** Explicit mount + identity + credential guard for local callbacks after awaited work. */
export function useCurrentSettings() {
 const { scope, credentialEpoch, getSnapshot } = useAuth(); const mounted = useRef(true);
 useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
 return () => mounted.current && getSnapshot().scope === scope && getSnapshot().credentialEpoch === credentialEpoch && getSnapshot().status === 'authenticated';
}
export function SettingsBack() { const { t } = useTranslation('settings'); return <Link to="/ajustes">{t('back')}</Link>; }
