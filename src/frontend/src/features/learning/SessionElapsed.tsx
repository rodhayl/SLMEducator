import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { knownInstant } from '@/lib/time';
import type { StudySession } from './contracts';

export function elapsedSinceStart(session: StudySession, now: number): string | null {
 const start = knownInstant(session.start_time, session.timestamp_provenance);
 if (!session.duration_known || start === null || !Number.isFinite(now) || now < start) return null;
 const seconds = Math.floor((now - start) / 1000);
 return [Math.floor(seconds / 3600), Math.floor(seconds % 3600 / 60), seconds % 60].map(value => String(value).padStart(2, '0')).join(':');
}
/** Display-only clock: it never calls heartbeat, saves progress or estimates server completion. */
export function SessionElapsed({session, running}: {session: StudySession; running: boolean}) {
 const {t} = useTranslation('learning');
 const [now, setNow] = useState(() => Date.now());
 useEffect(() => { if (!running || session.status !== 'active') return; const timer = window.setInterval(() => setNow(Date.now()), 1000); return () => window.clearInterval(timer); }, [running, session.status]);
 if (session.status !== 'active') return null;
 const elapsed = elapsedSinceStart(session, now);
 return <p className="muted">{elapsed === null ? t('durationUnknown') : <>{t('elapsed')}: <span>{elapsed}</span>. {t('elapsedHint')}</>}</p>;
}
