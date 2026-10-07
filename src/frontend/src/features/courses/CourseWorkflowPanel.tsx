import { useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/app/AuthProvider';
import { useInvalidate, useOperation, useResource } from '@/lib/query';
import { ApiError } from '@/lib/api';
import { useContinuation } from '@/features/authoring/MaterialEditor';
import { Badge, Button, Card, ConfirmDialog, EmptyState, ErrorState, LoadingState } from '@/components/ui';
import { invalidResponse, isAssignment, isStudents, isWorkflowReceipt, type AssignmentReceipt, type CourseWorkflow } from './contracts';

type Decision = 'publish' | 'revision' | 'assign' | null;
type WorkflowProps = {planId: number; workflow: CourseWorkflow; dirty: boolean; contentCount: number; isPublic: boolean};
export function CourseWorkflowPanel(props: WorkflowProps) {
  const {scope} = useAuth();
  return <WorkflowPanel key={`${scope}:${props.planId}`} {...props} />;
}
function WorkflowPanel({planId, workflow, dirty, contentCount, isPublic}: WorkflowProps) {
  const {api} = useAuth(), {t} = useTranslation('courses'), invalidate = useInvalidate(), navigate = useNavigate(), current = useContinuation();
  const [decision, setDecision] = useState<Decision>(null), [makePublic, setMakePublic] = useState(isPublic), [notice, setNotice] = useState('');
  const [selected, setSelected] = useState<number[]>([]);
  const students = useResource<unknown>(['course-students', planId], workflow.status === 'published' ? '/api/students/' : null);
  const action = useOperation(async (input: {kind: 'review' | 'publish' | 'revision' | 'assign'; studentIds?: number[]; public?: boolean}) => {
    if (dirty) throw new ApiError(409);
    if (input.kind === 'revision') {
      const data = await api.post<unknown>(`/api/study-plans/${planId}/copy`, {reason: 'revision'});
      if (!data || typeof data !== 'object' || !('id' in data) || !Number.isSafeInteger(data.id) || Number(data.id) < 1 || !('status' in data) || data.status !== 'draft') throw invalidResponse(true);
      return {kind: input.kind, id: Number(data.id)};
    }
    if (input.kind === 'assign') {
      const studentIds = input.studentIds ?? [], availableStudents = students.data;
      if (workflow.status !== 'published' || !studentIds.length || !isStudents(availableStudents) || !studentIds.every(id => availableStudents.some(student => student.id === id))) throw new ApiError(422);
      const receipt = await api.post<unknown>(`/api/study-plans/${planId}/assign`, {student_ids: studentIds});
      if (!isAssignment(receipt, planId, studentIds)) throw invalidResponse(true);
      return {kind: input.kind, receipt};
    }
    if (workflow.read_only || !contentCount || (input.kind === 'publish' && workflow.status !== 'reviewed')) throw new ApiError(409);
    const data = await api.post<unknown>(`/api/study-plans/${planId}/workflow`, {action: input.kind, is_public: input.kind === 'publish' && input.public === true});
    if (!isWorkflowReceipt(data, input.kind === 'review' ? 'reviewed' : 'published')) throw invalidResponse(true);
    return {kind: input.kind};
  }, async result => {
    if (current()) setDecision(null);
    if (result.kind === 'revision' && 'id' in result) { await invalidate(['courses']); if (current()) void navigate(`/cursos/${result.id}/editar`); return; }
    if (current()) {
      if (result.kind === 'assign' && 'receipt' in result) { const receipt = result.receipt as AssignmentReceipt; setNotice(t('assignmentSaved', {assigned: receipt.assigned_student_ids.length, existing: receipt.already_assigned_student_ids.length})); setSelected([]); }
      else setNotice(t(result.kind === 'review' ? 'reviewSaved' : 'publishSaved'));
    }
    await invalidate(['courses']);
  });
  const uncertain = action.error instanceof ApiError && action.error.uncertain;
  const disabled = dirty || action.isPending || uncertain;
  const run = (kind: 'review' | 'publish' | 'revision' | 'assign') => { void action.mutateAsync({kind, studentIds: [...selected], public: makePublic}).catch(() => { if (current()) setDecision(null); }); };
  const toggle = (id: number) => setSelected(current => current.includes(id) ? current.filter(item => item !== id) : [...current, id]);
  return <section className="stack" aria-label={t('workflow')}>
    <Card><div className="stack"><h2>{t('workflow')}</h2><div className="cluster"><Badge>{t(workflow.status)}</Badge><span>{t('version', {number: workflow.version})}</span></div>
      {dirty && <p role="status">{t('saveFirst')}</p>}{workflow.read_only && <p role="status">{t('locked')}</p>}
      {!contentCount && <p>{t('noContentReview')}</p>}
      <div className="cluster"><Button disabled={disabled || workflow.read_only || !contentCount || workflow.status !== 'draft'} onClick={() => run('review')}>{t('review')}</Button><Button disabled={disabled || workflow.read_only || workflow.status !== 'reviewed'} onClick={() => setDecision('publish')}>{t('publish')}</Button><Button variant="secondary" disabled={disabled} onClick={() => setDecision('revision')}>{t('revision')}</Button></div>
      {workflow.status === 'published' && <div className="stack"><h3>{t('students')}</h3>{students.isPending ? <LoadingState /> : students.error ? <ErrorState error={students.error} retry={() => {void students.refetch();}} /> : !isStudents(students.data) ? <ErrorState error={invalidResponse()} /> : !students.data.length ? <EmptyState title={t('studentsEmpty')} /> : <fieldset disabled={disabled}><legend>{t('students')}</legend><div className="stack">{students.data.map(student => <label key={student.id} className="cluster"><input type="checkbox" checked={selected.includes(student.id)} onChange={() => toggle(student.id)} />{t('studentIdentity', {name: `${student.first_name} ${student.last_name}`.trim() || student.username, username: student.username, id: student.id})}</label>)}</div></fieldset>}<p>{t('assignmentIds', {ids: selected.length ? selected.join(', ') : t('noSelection')})}</p><Button disabled={disabled || !selected.length} onClick={() => setDecision('assign')}>{t('assign')}</Button></div>}
      {notice && <p role="status">{notice}</p>}{action.error && <ErrorState error={action.error} />}{uncertain && <p>{t('uncertain')} <Link to="/cursos">{t('back')}</Link></p>}
    </div></Card>
    <ConfirmDialog open={decision !== null} onOpenChange={open => { if (!open && !action.isPending) setDecision(null); }} title={t(decision === 'publish' ? 'publishTitle' : decision === 'assign' ? 'assignTitle' : 'revisionTitle')} description={t(decision === 'publish' ? 'publishDescription' : decision === 'assign' ? 'assignDescription' : 'revisionDescription')} confirmLabel={t(decision === 'publish' ? 'publish' : decision === 'assign' ? 'assign' : 'copy')} busy={action.isPending} onConfirm={() => {if (decision && !disabled) run(decision);}}>
      {decision === 'publish' && <label className="stack"><span><input type="checkbox" checked={makePublic} onChange={event => setMakePublic(event.target.checked)} /> {t('makePublic')}</span><span className="muted">{t('publicHint')}</span></label>}
      {decision === 'assign' && <p>{t('assignmentIds', {ids: selected.join(', ')})}</p>}
    </ConfirmDialog>
  </section>;
}
