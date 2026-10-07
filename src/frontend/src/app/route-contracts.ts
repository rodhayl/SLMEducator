import type { Role } from '@/lib/types';
export interface NavigationItem { path: string; label: string; roles: Role[] }
const all: Role[] = ['student', 'teacher', 'admin'];
export const navigation: NavigationItem[] = [
 { path:'/inicio',label:'home',roles:all }, { path:'/cursos',label:'courses',roles:all }, { path:'/evaluaciones',label:'assessments',roles:all },
 { path:'/personas',label:'people',roles:['teacher','admin'] }, { path:'/progreso',label:'progress',roles:['student'] }, { path:'/tutor',label:'help',roles:all }, { path:'/ayuda',label:'requests',roles:['student'] },
 { path:'/correcciones',label:'grading',roles:['teacher','admin'] }, { path:'/solicitudes',label:'requests',roles:['teacher','admin'] },
 { path:'/mensajes',label:'messages',roles:all }, { path:'/ajustes',label:'settings',roles:all },
 { path:'/administracion/copias',label:'backups',roles:['admin'] }, { path:'/administracion/estado',label:'status',roles:['admin'] },
];
const paths = /^\/(?:inicio|cursos(?:\/(?:nuevo|[1-9]\d*(?:\/editar)?))?|materiales(?:\/(?:nuevo|[1-9]\d*(?:\/editar)?))?|generar|fuentes|estudio\/[1-9]\d*|evaluaciones(?:\/(?:nueva|historial|[1-9]\d*(?:\/(?:editar|historial))?))?|intentos\/[1-9]\d*|envios\/[1-9]\d*|correcciones(?:\/[1-9]\d*)?|personas(?:\/(?:nueva|[1-9]\d*))?|estudiantes\/[1-9]\d*|progreso|tutor|ayuda|solicitudes(?:\/[1-9]\d*)?|mensajes|ajustes(?:\/(?:cuenta|perfil|seguridad|apariencia|zona-horaria|ia|datos))?|administracion\/(?:copias|estado))$/;
export function safeReturnPath(value: string | null, origin = window.location.origin): string {
 try { if (!value || !value.startsWith('/') || value.startsWith('//') || value.includes('\\')) return '/inicio'; const url = new URL(value, origin); return url.origin === origin && paths.test(url.pathname) ? url.pathname + url.search + url.hash : '/inicio'; } catch { return '/inicio'; }
}
export function pathRoleAllowed(path: string, role: Role): boolean {
 if (/^\/administracion\//.test(path)) return role === 'admin';
 if (/^\/(personas|estudiantes|correcciones)(\/|$)/.test(path) || /^\/(?:generar|fuentes|materiales\/nuevo)$/.test(path) || /^\/cursos\/nuevo$|^\/cursos\/\d+\/editar$|^\/evaluaciones\/nueva$|^\/evaluaciones\/\d+\/editar$/.test(path)) return role !== 'student';
 return true;
}
