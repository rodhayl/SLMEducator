/** Lightweight route ownership. Domain implementations load only after navigation. */
export const featurePaths: Record<string, readonly string[]> = {
 tutor: ['tutor'],
 progress: ['progreso'],
 messages: ['mensajes'],
 help: ['ayuda','solicitudes','solicitudes/:requestId'],
 courses: ['cursos','cursos/nuevo','cursos/:courseId','cursos/:courseId/editar'],
 people: ['personas','personas/nueva','personas/:personId','estudiantes/:studentId'],
 learning: ['materiales/:contentId','estudio/:sessionId'],
 settings: ['ajustes','ajustes/perfil','ajustes/seguridad','ajustes/apariencia','ajustes/ia','ajustes/zona-horaria','administracion/estado'],
 portability: ['ajustes/datos','administracion/copias'],
 authoring: ['materiales','materiales/nuevo','materiales/:contentId/editar','generar','fuentes'],
 assessments: ['evaluaciones','evaluaciones/nueva','evaluaciones/historial','evaluaciones/:assessmentId','evaluaciones/:assessmentId/editar','evaluaciones/:assessmentId/historial','intentos/:submissionId','envios/:submissionId','correcciones','correcciones/:submissionId'],
};
