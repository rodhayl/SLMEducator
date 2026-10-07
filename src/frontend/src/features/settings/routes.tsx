import type { RouteObject } from 'react-router';
import { SettingsPage, ProfilePage, PasswordPage } from './AccountPages';
import { AppearancePage, TimezonePage, ApplicationStatusPage } from './PreferencePages';
import { AISettingsPage } from './AISettingsPage';
export { SettingsPage, ProfilePage, PasswordPage, AppearancePage, TimezonePage, ApplicationStatusPage, AISettingsPage };
export const routes: RouteObject[] = [
 {path:'ajustes',Component:SettingsPage},{path:'ajustes/perfil',Component:ProfilePage},{path:'ajustes/seguridad',Component:PasswordPage},{path:'ajustes/apariencia',Component:AppearancePage},{path:'ajustes/ia',Component:AISettingsPage},{path:'ajustes/zona-horaria',Component:TimezonePage},{path:'administracion/estado',Component:ApplicationStatusPage},
];
