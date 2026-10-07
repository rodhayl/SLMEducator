import type { RouteObject } from 'react-router';
import { MaterialLibraryPage } from './MaterialLibrary';
import { MaterialEditorPage } from './MaterialEditor';
import { GenerationPage } from './GenerationPage';
import { SourcePage } from './SourcePage';
export const routes:RouteObject[]=[
 {path:'materiales',Component:MaterialLibraryPage},
 {path:'materiales/nuevo',Component:MaterialEditorPage},
 {path:'materiales/:contentId/editar',Component:MaterialEditorPage},
 {path:'generar',Component:GenerationPage},
 {path:'fuentes',Component:SourcePage},
];
