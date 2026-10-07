import type { RouteObject } from 'react-router';
import { CourseDetailPage, CourseListPage } from './CoursePages';
import { CourseEditorPage } from './CourseEditor';
export const routes: RouteObject[] = [
  {path: 'cursos', Component: CourseListPage},
  {path: 'cursos/nuevo', Component: CourseEditorPage},
  {path: 'cursos/:courseId', Component: CourseDetailPage},
  {path: 'cursos/:courseId/editar', Component: CourseEditorPage},
];
