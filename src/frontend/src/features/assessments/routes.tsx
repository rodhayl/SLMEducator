import type { RouteObject } from 'react-router';
import { AssessmentListPage, AssessmentPreviewPage, SubmissionDetailPage, SubmissionHistoryPage } from './AssessmentPages';
import { AssessmentEditorPage } from './AssessmentEditor';
import { AttemptWorkspacePage } from './AttemptWorkspace';
import { GradingQueuePage, GradingWorkspacePage } from './GradingWorkspace';
export { AssessmentListPage, AssessmentPreviewPage, SubmissionDetailPage, SubmissionHistoryPage, AssessmentEditorPage, AttemptWorkspacePage, GradingQueuePage, GradingWorkspacePage };
export const routes: RouteObject[] = [
 { path: 'evaluaciones', Component: AssessmentListPage },
 { path: 'evaluaciones/nueva', Component: AssessmentEditorPage },
 { path: 'evaluaciones/historial', Component: SubmissionHistoryPage },
 { path: 'evaluaciones/:assessmentId', Component: AssessmentPreviewPage },
 { path: 'evaluaciones/:assessmentId/editar', Component: AssessmentEditorPage },
 { path: 'evaluaciones/:assessmentId/historial', Component: SubmissionHistoryPage },
 { path: 'intentos/:submissionId', Component: AttemptWorkspacePage },
 { path: 'envios/:submissionId', Component: SubmissionDetailPage },
 { path: 'correcciones', Component: GradingQueuePage },
 { path: 'correcciones/:submissionId', Component: GradingWorkspacePage },
];
