import { useEffect, useRef } from 'react';
import { useAuth } from '@/app/AuthProvider';
import { ApiError } from './api';
/** User-triggered download only. Object URLs are never stored and have a bounded lifetime. */
export function useFileDownload() {
  const { scope, credentialEpoch, status, getSnapshot } = useAuth();
  const urls = useRef(new Map<string, ReturnType<typeof setTimeout>>());
  useEffect(() => {
    const active = urls.current;
    const cleanup = () => { for (const [url, timer] of active) { clearTimeout(timer); URL.revokeObjectURL(url); } active.clear(); };
    window.addEventListener('pagehide', cleanup);
    return () => { window.removeEventListener('pagehide', cleanup); cleanup(); };
  }, [scope, credentialEpoch, status]);
  return (blob: Blob, filename: string) => {
    const current = getSnapshot();
    if (current.scope !== scope || current.credentialEpoch !== credentialEpoch || current.status !== 'authenticated') throw new ApiError(0, 'stale', false, 'cancelled');
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    const name = Array.from(filename, character => character.codePointAt(0)! < 32 || ['\\', '/', ':', '*', '?', '"', '<', '>', '|'].includes(character) ? '_' : character).join('').slice(0, 160) || 'download';
    link.href = url; link.download = name;
    try { document.body.append(link); link.click(); }
    catch { URL.revokeObjectURL(url); throw new ApiError(0, 'invalid', false, 'failed'); }
    finally { link.remove(); }
    urls.current.set(url, setTimeout(() => { URL.revokeObjectURL(url); urls.current.delete(url); }, 60_000));
  };
}
