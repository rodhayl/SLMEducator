import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useFieldArray, useForm, useWatch, type UseFormReturn } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/app/AuthProvider';
import { useDirtyGuard, useDirtyState } from '@/app/DirtyGuard';
import { ApiError } from '@/lib/api';
import { DraftAdapter } from '@/lib/drafts';
import { positiveId } from '@/lib/ids';
import { useInvalidate, useOperation, useResource } from '@/lib/query';
import { Button, Card, EmptyState, ErrorState, Field, Input, LoadingState, PageHeader, SaveStatus, Select, Textarea } from '@/components/ui';
import { CourseWorkflowPanel } from './CourseWorkflowPanel';
import { LessonComposer } from './LessonComposer';
import { canAttachMaterial, courseForm, coursePayload, invalidResponse, isCourse, isCourseForm, isCourseList, isCourseTree, isMaterialList, isWorkflow, materialHref, moveItem, type CourseForm, type CourseTree, type CourseWorkflow, type Material } from './contracts';

export function CourseEditorPage() {
  const {courseId} = useParams(), id = positiveId(courseId), {user, scope} = useAuth(), {t} = useTranslation('courses');
  const staff = user?.role === 'teacher' || user?.role === 'admin';
  const owned = useResource<unknown>(['courses'], staff && id ? '/api/study-plans/' : null);
  const allowed = staff && (!courseId || (id !== null && isCourseList(owned.data) && owned.data.some(plan => plan.id === id)));
  const tree = useResource<unknown>(['courses', id, 'tree'], allowed && id ? `/api/study-plans/${id}/tree` : null);
  const workflow = useResource<unknown>(['courses', id, 'workflow'], allowed && id ? `/api/study-plans/${id}/workflow` : null);
  const materials = useResource<unknown>(['course-materials'], allowed ? '/api/content/' : null);
  if (!staff || (courseId && !id)) return <EmptyState title={t('unavailable')} />;
  if (id && owned.isPending) return <LoadingState />;
  if (owned.error) return <ErrorState error={owned.error} retry={() => {void owned.refetch();}} />;
  if (!allowed) return <EmptyState title={t('editingBlocked')} action={id ? <Link to={`/cursos/${id}`}>{t('viewCourse')}</Link> : undefined} />;
  if (id && (tree.isPending || workflow.isPending)) return <LoadingState />;
  if (tree.error || workflow.error) return <ErrorState error={tree.error || workflow.error} retry={() => {void tree.refetch(); void workflow.refetch();}} />;
  if (id && (!isCourseTree(tree.data) || tree.data.id !== id || !isWorkflow(workflow.data))) return <ErrorState error={invalidResponse()} />;
  return <CourseEditor key={`${scope}:${id ?? 'new'}`} initial={isCourseTree(tree.data) ? tree.data : null} workflow={isWorkflow(workflow.data) ? workflow.data : null} materials={isMaterialList(materials.data) ? materials.data : []} materialsError={materials.error || (materials.isSuccess && !isMaterialList(materials.data) ? invalidResponse() : null)} materialsPending={materials.isPending} retryMaterials={() => {void materials.refetch();}} />;
}

function CourseEditor({initial, workflow, materials, materialsError, materialsPending, retryMaterials}: {initial: CourseTree | null; workflow: CourseWorkflow | null; materials: Material[]; materialsError: unknown; materialsPending: boolean; retryMaterials: () => void}) {
  const {user, api} = useAuth(), {t} = useTranslation('courses'), navigate = useNavigate(), invalidate = useInvalidate();
  const form = useForm<CourseForm>({defaultValues: initial ? courseForm(initial) : {title: '', description: '', phases: [{name: t('phase', {number: 1}), content_ids: []}]}});
  const phases = useFieldArray({control: form.control, name: 'phases'}), values = useWatch({control: form.control});
  const [redirect, setRedirect] = useState<number | null>(null), [notice, setNotice] = useState('');
  const [lessonPhase, setLessonPhase] = useState<string | null>(null), [lessonDirty, setLessonDirty] = useState(false), [lessonBusy, setLessonBusy] = useState(false);
  const [created, setCreated] = useState<Material[]>([]), [storageFailed, setStorageFailed] = useState(false);
  const drafts = useMemo(() => new DraftAdapter(user!.id), [user]);
  const resource = initial?.id ?? 'new';
  const [localDraft, setLocalDraft] = useState(() => drafts.read('course', resource, 'structure', isCourseForm));
  const readOnly = workflow?.read_only === true, dirty = form.formState.isDirty;
  const courseCreatorId = initial ? initial.creator_id ?? null : user!.id;
  const ownsCourse = courseCreatorId === user!.id;
  useDirtyGuard(dirty || lessonDirty || lessonBusy);
  const navigationDirty = useDirtyState();
  useEffect(() => { if (dirty && !readOnly && !localDraft && isCourseForm(values)) setStorageFailed(!drafts.write('course', resource, 'structure', values)); }, [values, dirty, readOnly, localDraft, drafts, resource]);
  useEffect(() => { if (redirect && !dirty && !lessonDirty && !navigationDirty) void navigate(`/cursos/${redirect}/editar`, {replace: true}); }, [redirect, dirty, lessonDirty, navigationDirty, navigate]);
  const save = useOperation(async (value: CourseForm) => {
    if (readOnly || lessonBusy) throw new ApiError(409);
    const retained = new Set(initial?.contents.map(item => item.id) ?? []);
    const allowed = new Set([...materials, ...created].filter(item => canAttachMaterial(item, user!, courseCreatorId)).map(item => item.id));
    if (value.phases.some(phase => phase.content_ids.some(id => !retained.has(id) && !allowed.has(id)))) throw new ApiError(409);
    const payload = coursePayload(value), result = initial ? await api.put<unknown>(`/api/study-plans/${initial.id}`, payload) : await api.post<unknown>('/api/study-plans/', payload);
    if (!isCourse(result) || (initial && result.id !== initial.id) || result.title !== payload.title || result.description !== payload.description || result.is_public) throw invalidResponse(true);
    return result;
  }, async (result, value) => {
    form.reset({...value, title: result.title}); drafts.remove('course', resource, 'structure'); setLocalDraft(null); setNotice(t('saved'));
    if (!initial) setRedirect(result.id);
    await invalidate(['courses']);
  });
  const restore = useOperation(async () => {
    if (!localDraft) throw new ApiError(422);
    if (initial) { const current = await api.get<unknown>(`/api/study-plans/${initial.id}/workflow`); if (!isWorkflow(current)) throw invalidResponse(); if (current.read_only) throw new ApiError(409); }
    const available = await api.get<unknown>('/api/content/');
    if (!isMaterialList(available)) throw invalidResponse();
    const allowed = new Set(available.filter(item => canAttachMaterial(item, user!, courseCreatorId)).map(item => item.id));
    const retained = new Set(initial?.contents.map(item => item.id) ?? []);
    if (localDraft.phases.some(phase => phase.content_ids.some(id => !retained.has(id) && !allowed.has(id)))) throw new ApiError(409);
    return localDraft;
  }, value => {form.reset(value, {keepDefaultValues: true}); setLocalDraft(null); setNotice(t('draftRestored'));});
  const uncertain = save.error instanceof ApiError && save.error.uncertain;
  const busy = save.isPending || uncertain || lessonBusy;
  const disabled = readOnly || busy || !!localDraft;
  const available = [...materials, ...created].filter((item, index, all) => canAttachMaterial(item, user!, courseCreatorId) && all.findIndex(other => other.id === item.id) === index);
  const labels = new Map([...available, ...(initial?.contents ?? [])].map(item => [item.id, item.title]));
  const lessonIndex = phases.fields.findIndex(phase => phase.id === lessonPhase);
  function addLesson(item: Material) {
    const index = phases.fields.findIndex(phase => phase.id === lessonPhase);
    if (index < 0 || !ownsCourse || !canAttachMaterial(item, user!, courseCreatorId)) return;
    setCreated(current => [...current, item]);
    const path = `phases.${index}.content_ids` as const;
    form.setValue(path, [...form.getValues(path), item.id], {shouldDirty: true});
    setNotice(t('lessonSaved')); setLessonPhase(null); setLessonDirty(false);
  }
  return <div className="stack">
    <Link to={initial ? `/cursos/${initial.id}` : '/cursos'}>{t(initial ? 'viewCourse' : 'back')}</Link>
    <PageHeader title={t(initial ? 'editCourse' : 'newCourse')} description={t('draftHint')} />
    {readOnly && <p role="status">{t('locked')}</p>}
    {initial && !ownsCourse && <p role="status">{t('crossAuthorNotice')}</p>}
    {localDraft && !readOnly && <Card><h2>{t('restoreTitle')}</h2><p>{t('restoreDescription')}</p><div className="cluster"><Button disabled={busy || restore.isPending} onClick={() => {void restore.mutateAsync(undefined).catch(() => undefined);}}>{t('restore')}</Button><Button variant="ghost" disabled={busy || restore.isPending} onClick={() => {drafts.remove('course', resource, 'structure'); setLocalDraft(null);}}>{t('discard')}</Button></div>{restore.error && <ErrorState error={restore.error} />}</Card>}
    <form className="stack" onSubmit={form.handleSubmit(value => save.mutateAsync(value).then(() => undefined).catch(() => undefined))}>
      <fieldset disabled={disabled}><div className="stack"><Field label={t('name')} error={form.formState.errors.title?.message}><Input {...form.register('title', {required: t('required'), maxLength: {value: 200, message: t('maxTitle')}, validate: value => !!value.trim() || t('required')})} maxLength={200} /></Field><Field label={t('description')}><Textarea {...form.register('description')} rows={3} /></Field></div></fieldset>
      <section className="stack" aria-label={t('structure')}><h2>{t('structure')}</h2>{materialsPending ? <LoadingState /> : materialsError ? <ErrorState error={materialsError} retry={retryMaterials} /> : !available.length ? <p className="muted">{t('materialEmpty')}</p> : null}
        {phases.fields.map((phase, index) => <PhaseEditor key={phase.id} index={index} form={form} count={phases.fields.length} available={available} labels={labels} disabled={disabled} onMove={direction => phases.move(index, index + direction)} onRemove={() => {phases.remove(index); if (lessonPhase === phase.id) {setLessonPhase(null); setLessonDirty(false);}}} onLesson={() => {if (ownsCourse) setLessonPhase(phase.id);}} lessonDisabled={!!lessonPhase} allowLesson={ownsCourse} planId={initial?.id} />)}
        <Button type="button" variant="secondary" disabled={disabled || phases.fields.length >= 101} onClick={() => phases.append({name: t('phase', {number: phases.fields.length + 1}), content_ids: []})}>{t('addPhase')}</Button>
      </section>
      <div className="cluster"><Button type="submit" busy={save.isPending} disabled={disabled || !!lessonPhase}>{t('save')}</Button><SaveStatus state={uncertain ? 'uncertain' : save.isPending ? 'saving' : dirty ? 'dirty' : save.isSuccess ? 'saved' : 'idle'} /></div>
      {notice && <p role="status">{notice}</p>}{save.error && <ErrorState error={save.error} />}{uncertain && <p>{t('uncertain')} <Link to="/cursos">{t('back')}</Link></p>}
    </form>
    {lessonPhase && lessonIndex >= 0 && !readOnly && ownsCourse && <LessonComposer onCreated={addLesson} onDirty={setLessonDirty} onBusy={setLessonBusy} onCancel={() => {setLessonPhase(null); setLessonDirty(false);}} />}
    {!readOnly && <p className="muted">{t('draftStorage')}</p>}{storageFailed && <p role="alert">{t('draftStorageFailed')}</p>}
    {initial && workflow && <CourseWorkflowPanel planId={initial.id} workflow={workflow} dirty={dirty || lessonDirty || lessonBusy || save.isPending} contentCount={initial.content_count} isPublic={initial.is_public} />}
  </div>;
}

function PhaseEditor({index, form, count, available, labels, disabled, onMove, onRemove, onLesson, lessonDisabled, allowLesson, planId}: {index: number; form: UseFormReturn<CourseForm>; count: number; available: Material[]; labels: Map<number,string>; disabled: boolean; onMove: (direction: -1 | 1) => void; onRemove: () => void; onLesson: () => void; lessonDisabled: boolean; allowLesson: boolean; planId?: number}) {
  const {t} = useTranslation('courses'), [selected, setSelected] = useState('');
  const phaseValues = useWatch({control: form.control, name: 'phases'}), items = phaseValues[index]?.content_ids ?? [];
  const attached = new Set(phaseValues.flatMap(phase => phase.content_ids)), choices = available.filter(item => !attached.has(item.id));
  const path = `phases.${index}.content_ids` as const;
  const selectedId = positiveId(selected);
  return <Card><fieldset disabled={disabled}><div className="stack"><Field label={t('phaseName')} error={form.formState.errors.phases?.[index]?.name?.message}><Input {...form.register(`phases.${index}.name`, {validate: value => !!value.trim() || t('required')})} /></Field>
    <div className="cluster"><Button type="button" variant="ghost" disabled={index === 0} onClick={() => onMove(-1)}>{t('movePhaseUp')}</Button><Button type="button" variant="ghost" disabled={index === count - 1} onClick={() => onMove(1)}>{t('movePhaseDown')}</Button><Button type="button" variant="danger" disabled={lessonDisabled} onClick={onRemove}>{t('removePhase')}</Button></div>
    {items.length ? <ol className="list">{items.map((id, position) => <li key={id}><div className="cluster">{planId ? <Link to={materialHref(id, planId)}>{labels.get(id) ?? t('unnamedMaterial', {id})}</Link> : <span>{labels.get(id) ?? t('unnamedMaterial', {id})}</span>}<Button type="button" variant="ghost" aria-label={`${t('moveUp')}: ${labels.get(id) ?? id}`} disabled={position === 0} onClick={() => form.setValue(path, moveItem(items, position, -1), {shouldDirty: true})}>{t('moveUp')}</Button><Button type="button" variant="ghost" aria-label={`${t('moveDown')}: ${labels.get(id) ?? id}`} disabled={position === items.length - 1} onClick={() => form.setValue(path, moveItem(items, position, 1), {shouldDirty: true})}>{t('moveDown')}</Button><Button type="button" variant="ghost" aria-label={`${t('remove')}: ${labels.get(id) ?? id}`} onClick={() => form.setValue(path, items.filter(item => item !== id), {shouldDirty: true})}>{t('remove')}</Button></div></li>)}</ol> : <p>{t('noItems')}</p>}
    <Field label={t('chooseMaterial')}><Select value={selected} onChange={event => setSelected(event.target.value)}><option value="">{t('choose')}</option>{choices.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</Select></Field>
    <div className="cluster"><Button type="button" variant="secondary" disabled={!selectedId || !choices.some(item => item.id === selectedId) || items.length >= 1001} onClick={() => {if (selectedId && !attached.has(selectedId)) {form.setValue(path, [...items, selectedId], {shouldDirty: true}); setSelected('');}}}>{t('attach')}</Button><Button type="button" variant="secondary" disabled={lessonDisabled || !allowLesson || items.length >= 1001} onClick={onLesson}>{t('newLesson')}</Button></div>
  </div></fieldset></Card>;
}
