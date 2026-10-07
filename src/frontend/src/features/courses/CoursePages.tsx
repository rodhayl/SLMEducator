import { useState } from 'react';
import { Link, useParams } from 'react-router';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/app/AuthProvider';
import { useResource } from '@/lib/query';
import { positiveId } from '@/lib/ids';
import { DraftAdapter } from '@/lib/drafts';
import { isRecord, isSession, sessionHref, sessionPlan } from '@/features/learning/contracts';
import { Badge, Card, EmptyState, ErrorState, Field, Input, LoadingState, PageHeader } from '@/components/ui';
import { CourseWorkflowPanel } from './CourseWorkflowPanel';
import { invalidResponse, isCourseList, isCourseTree, isProgress, isWorkflow, materialHref, type CourseTree } from './contracts';

export function CourseListPage() {
  const { user } = useAuth(), { t } = useTranslation('courses');
  const courses = useResource<unknown>(['courses'], '/api/study-plans/');
  const [search, setSearch] = useState('');
  const staff = user?.role === 'teacher' || user?.role === 'admin';
  if (courses.isPending) return <LoadingState />;
  if (courses.error) return <ErrorState error={courses.error} retry={() => { void courses.refetch(); }} />;
  if (!isCourseList(courses.data)) return <ErrorState error={invalidResponse()} />;
  const filtered = courses.data.filter(course => course.title.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()));
  return <div className="stack">
    <PageHeader title={t(staff ? 'title' : 'myCourses')} description={t(staff ? 'subtitle' : 'studentSubtitle')} actions={staff ? <Link to="/cursos/nuevo">{t('newCourse')}</Link> : undefined} />
    <Field label={t('search')}><Input value={search} onChange={event => setSearch(event.target.value)} type="search" /></Field>
    {!courses.data.length ? <EmptyState title={t('empty')} description={t(staff ? 'emptyDescription' : 'studentEmpty')} /> : !filtered.length ? <EmptyState title={t('noMatches')} /> :
      <div className="grid">{filtered.map(course => <Card key={course.id}><div className="stack"><Badge>{t(course.is_public ? 'public' : 'private')}</Badge><h2><Link to={`/cursos/${course.id}`}>{course.title}</Link></h2>{course.description && <p>{course.description}</p>}</div></Card>)}</div>}
  </div>;
}

export function CourseDetailPage() {
  const { courseId } = useParams(), id = positiveId(courseId), { user } = useAuth(), { t } = useTranslation('courses');
  const staff = user?.role === 'teacher' || user?.role === 'admin';
  const tree = useResource<unknown>(['courses', id, 'tree'], id ? `/api/study-plans/${id}/tree` : null);
  const workflow = useResource<unknown>(['courses', id, 'workflow'], id ? `/api/study-plans/${id}/workflow` : null);
  const owned = useResource<unknown>(['courses'], staff ? '/api/study-plans/' : null);
  if (!id) return <EmptyState title={t('unavailable')} />;
  if (tree.isPending) return <LoadingState />;
  if (tree.error) return <ErrorState error={tree.error} retry={() => { void tree.refetch(); }} />;
  if (!isCourseTree(tree.data) || tree.data.id !== id) return <ErrorState error={invalidResponse()} />;
  const course = tree.data;
  const canManage = staff && isCourseList(owned.data) && owned.data.some(plan => plan.id === id);
  return <div className="stack">
    <Link to="/cursos">{t('back')}</Link>
    <PageHeader title={course.title} description={course.description ?? undefined} actions={canManage ? <Link to={`/cursos/${id}/editar`}>{t('editCourse')}</Link> : undefined} />
    <div className="cluster"><Link to={`/ajustes/datos?plan_id=${id}`}>{t('exportCourse')}</Link>{canManage && <><Link to={`/fuentes?plan_id=${id}`}>{t('courseSources')}</Link>{isWorkflow(workflow.data) && !workflow.data.read_only && <Link to={`/generar?plan_id=${id}`}>{t('generateMaterials')}</Link>}</>}</div>
    <div className="cluster"><Badge>{t(course.is_public ? 'public' : 'private')}</Badge><span>{t('materialsCount', { count: course.content_count })}</span></div>
    {user?.role === 'student' && <StudentCourseProgress course={course} />}
    <CourseStructure course={course} />
    {workflow.isSuccess && !isWorkflow(workflow.data) && <ErrorState error={invalidResponse()} />}
    {workflow.error && <ErrorState error={workflow.error} retry={() => { void workflow.refetch(); }} />}
    {canManage && isWorkflow(workflow.data) && <CourseWorkflowPanel planId={id} workflow={workflow.data} dirty={false} contentCount={course.content_count} isPublic={course.is_public} />}
    {staff && owned.error && <ErrorState error={owned.error} retry={() => { void owned.refetch(); }} />}
  </div>;
}

function CourseStructure({ course }: { course: CourseTree }) {
  const { t } = useTranslation('courses');
  const count = Math.max(course.phases.length, ...course.contents.map(item => item.phase_index + 1), 1);
  return <section className="stack" aria-label={t('structure')}>{Array.from({length: count}, (_, index) => {
    const items = course.contents.filter(item => item.phase_index === index).sort((a,b) => a.order_index - b.order_index);
    return <Card key={index}><h2>{course.phases[index]?.name || course.phases[index]?.title || t('phase', {number: index + 1})}</h2>{items.length ? <ol className="list">{items.map(item => <li key={item.id}><Link to={materialHref(item.id, course.id)}>{item.title}</Link></li>)}</ol> : <p className="muted">{t('noItems')}</p>}</Card>;
  })}</section>;
}

function StudentCourseProgress({course}: {course: CourseTree}) {
  const { t } = useTranslation('courses'), {user} = useAuth();
  const progress = useResource<unknown>(['courses', course.id, 'progress'], `/api/study-plans/${course.id}/my-progress`);
  const active = useResource<unknown>(['learning', 'active'], '/api/learning/active');
  if (progress.isPending) return <LoadingState />;
  if (progress.error) return <ErrorState error={progress.error} retry={() => { void progress.refetch(); }} />;
  if (!isProgress(progress.data, course.id)) return <ErrorState error={invalidResponse()} />;
  const data = progress.data;
  const activeSession = isSession(active.data) && active.data.status === 'active' ? active.data : null;
  const activeItem = activeSession && sessionPlan(activeSession) === course.id ? course.contents.find(item => item.id === activeSession.content_id) : undefined;
  const marker = user ? new DraftAdapter(user.id).read('learning-location', 'current', 0, (value): value is {planId: number; contentId: number} => isRecord(value) && typeof value.planId === 'number' && positiveId(value.planId) !== null && typeof value.contentId === 'number' && positiveId(value.contentId) !== null) : null;
  const markedItem = marker?.planId === course.id ? course.contents.find(item => item.id === marker.contentId) : undefined;
  const fallback = course.contents.find(item => item.id === data.last_content_id && !data.completed_content_ids.includes(item.id)) || [...course.contents].sort((a,b) => a.phase_index - b.phase_index || a.order_index - b.order_index).find(item => !data.completed_content_ids.includes(item.id));
  const resume = activeItem || markedItem || fallback;
  const href = activeSession && activeItem ? sessionHref(activeSession) : resume ? materialHref(resume.id, course.id) : null;
  const activeError = active.error || (active.isSuccess && active.data !== null && !activeSession ? invalidResponse() : null);
  return <Card><div className="stack"><p>{t('progress', {percent: data.completion_percentage})}</p><progress max={100} value={data.completion_percentage} aria-label={t('progress', {percent: data.completion_percentage})} />
    {active.isPending ? <LoadingState /> : activeError ? <ErrorState error={activeError} retry={() => {void active.refetch();}} /> : resume && href ? <Link to={href}>{t('continue')}: {resume.title}</Link> : <p>{t(course.content_count ? 'completed' : 'notStarted')}</p>}
  </div></Card>;
}
