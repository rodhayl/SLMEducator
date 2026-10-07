import { positiveId } from '@/lib/ids';
/** Compatibility translation only on /inicio. Hash, then view, then tab matches legacy precedence. */
export function legacyDashboardDestination(pathname: string, search: string, hash: string): string | null {
  if (pathname !== '/inicio') return null;
  const params = new URLSearchParams(search);
  const requested = hash.slice(1) || params.get('view') || params.get('tab');
  const view = requested === 'study-plans' ? 'library' : requested;
  const destinations: Record<string, string> = {
    overview: '/inicio', inbox: '/mensajes', library: '/materiales', assessments: '/evaluaciones',
    grading: '/correcciones', students: '/personas?role=student', teachers: '/personas?role=teacher',
    admins: '/personas?role=admin', leaderboard: '/progreso?tab=leaderboard', 'help-queue': '/solicitudes',
    create: '/generar', tutor: '/tutor', settings: '/ajustes/perfil',
  };
  if (!view || !Object.hasOwn(destinations, view)) return null;
  const helpRequested = params.get('from_session') === '1' && params.get('ask_help') === '1' && positiveId(params.get('content_id'));
  const target = new URL(helpRequested ? '/ayuda' : destinations[view]!, 'http://local');
  for (const key of ['content_id','plan_id']) { const value = positiveId(params.get(key)); if (value) target.searchParams.set(key, String(value)); }
  for (const key of ['from_session','ask_help']) if (params.get(key) === '1') target.searchParams.set(key, '1');
  if (view === 'grading') { const filter = params.get('grading_filter') || params.get('filter'); if (filter && ['pending','graded','all'].includes(filter)) target.searchParams.set('filter', filter); }
  if (params.get('mode') === 'review') target.searchParams.set('mode', 'review');
  return target.pathname + target.search;
}
