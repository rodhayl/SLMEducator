import type { RouteObject } from 'react-router';
import { LegacyQuestions } from './Questions';
import { TutorPage } from './TutorPage';
export const routes:RouteObject[]=[{path:'tutor',element:<TutorPage/>},{path:'tutor/historial',element:<LegacyQuestions/>}];
export { TutorPage };
