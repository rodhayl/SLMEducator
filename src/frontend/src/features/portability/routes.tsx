import type { RouteObject } from 'react-router';
import { PortabilityPage } from './PortabilityPage';
import { BackupPage } from './BackupPage';
export { PortabilityPage, BackupPage };
export const routes: RouteObject[] = [{path:'ajustes/datos',Component:PortabilityPage},{path:'administracion/copias',Component:BackupPage}];
