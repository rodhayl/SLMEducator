import type { RouteObject } from 'react-router';
import { HelpPage, HelpDetailPage } from './HelpPages';
export const routes:RouteObject[]=[{path:'ayuda',Component:HelpPage},{path:'solicitudes',Component:HelpPage},{path:'solicitudes/:requestId',Component:HelpDetailPage}];
export { HelpPage, HelpDetailPage };
