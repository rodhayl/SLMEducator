import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router';
import { useFieldArray, useForm, useWatch } from 'react-hook-form';
import { useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/app/AuthProvider';
import { useDirtyGuard } from '@/app/DirtyGuard';
import { useInvalidate, useOperation, useResource } from '@/lib/query';
import { ApiError } from '@/lib/api';
import { positiveId } from '@/lib/ids';
import { Badge, Button, Card, ConfirmDialog, EmptyState, ErrorState, Field, Input, LoadingState, PageHeader, SaveStatus, Select, Textarea } from '@/components/ui';
import { ContentRenderer } from '@/components/content/ContentRenderer';
import { confirmedMaterial, isAuthorMaterial, lessonTextFields, materialForm, materialPayload, record, responseError, type AuthorMaterial, type MaterialForm, type MaterialKind } from './contracts';

export function StaffRequired() { const {t} = useTranslation('authoring'); return <EmptyState title={t('staffRequired')} action={<Link to="/tutor">{t('tutor')}</Link>} />; }
export function useContinuation() {
 const {scope, credentialEpoch, getSnapshot} = useAuth(), alive = useRef(true);
 useEffect(() => {alive.current = true; return () => {alive.current = false;};}, []);
 return useCallback(() => alive.current && getSnapshot().scope === scope && getSnapshot().credentialEpoch === credentialEpoch && getSnapshot().status === 'authenticated', [scope,credentialEpoch,getSnapshot]);
}
export function MaterialEditorPage() {
 const {contentId: parameter} = useParams(), {user, scope} = useAuth(), {t} = useTranslation('authoring');
 const contentId = positiveId(parameter);
 if (user?.role === 'student') return <StaffRequired />;
 if (parameter !== undefined && !contentId) return <EmptyState title={t('unavailable')} />;
 return <EditorRoute key={`${scope}:${contentId}`} contentId={contentId} />;
}
function EditorRoute({contentId}: {contentId:number|null}) {
 const {t} = useTranslation('authoring'), [dirty, setDirty] = useState(false);
 const material = useResource<unknown>(['authoring','material',contentId], contentId ? `/api/content/${contentId}` : null);
 useDirtyGuard(dirty);
 if (contentId && material.isPending) return <LoadingState />;
 if (material.error) return <ErrorState error={material.error} retry={() => {void material.refetch();}} />;
 if (contentId && (!isAuthorMaterial(material.data) || material.data.id !== contentId)) return <ErrorState error={responseError()} />;
 const initial = isAuthorMaterial(material.data) ? material.data : undefined;
 if (initial?.content_type === 'assessment') return <EmptyState title={t('assessmentEditor')} action={positiveId(String(initial.content_data.assessment_id)) ? <Link to={`/evaluaciones/${initial.content_data.assessment_id}/editar`}>{t('openAssessment')}</Link> : undefined} />;
 if (initial?.content_type === 'qa') return <EmptyState title={t('qaHandoff')} action={<Link to="/tutor">{t('tutor')}</Link>} />;
 if (initial && initial.can_edit !== true) return <EmptyState title={t('readOnly')} description={t('revisionHint')} action={<Link to="/cursos">{t('courses')}</Link>} />;
 return <div className="stack"><Link to="/materiales">{t('library')}</Link><PageHeader title={t(initial ? 'editMaterial' : 'newMaterial')} description={t('manualHint')} /><MaterialComposer initial={initial} onDirty={setDirty}/></div>;
}
export function MaterialComposer({initial, proposal, onDirty, onSaved}: {initial?: AuthorMaterial; proposal?: {kind: MaterialKind; data: Record<string, unknown>; title?: string}; onDirty: (dirty: boolean) => void; onSaved?: (id: number) => void}) {
 const {api, user, scope} = useAuth(), {t} = useTranslation('authoring'), invalidate = useInvalidate(), current = useContinuation(), queries = useQueryClient();
 const [base, setBase] = useState(initial), [savedId, setSavedId] = useState(initial?.id ?? null), [confirm, setConfirm] = useState<'delete'|'reload'|null>(null), [deleted, setDeleted] = useState(false), [preview, setPreview] = useState(false);
 const original = useRef(initial?.content_data || proposal?.data || {});
 const form = useForm<MaterialForm>({defaultValues: materialForm(initial?.content_type === 'exercise' || proposal?.kind === 'exercise' ? 'exercise' : 'lesson', initial?.content_data || proposal?.data || {}, initial?.title || proposal?.title, initial?.difficulty)});
 const values = useWatch({control:form.control}) as MaterialForm;
 const sections = useFieldArray({control:form.control,name:'sections'}), options = useFieldArray({control:form.control,name:'options'}), vocabulary = useFieldArray({control:form.control,name:'vocabulary'});
 const save = useOperation(async (value: MaterialForm) => {
  const payload = materialPayload(value, original.current);
  const result = savedId ? await api.put<unknown>(`/api/content/${savedId}`, {title:payload.title,difficulty:payload.difficulty,content_data:payload.content_data}) : await api.post<unknown>('/api/content/', {...payload,is_personal:false});
  if (!confirmedMaterial(result,payload,user!.id,base)) throw responseError(true);
  return {result,payload,value};
 }, async ({result,payload,value}) => {
  const confirmed = {...result,can_edit:true,content_data:payload.content_data}; queries.setQueryData([scope,'authoring','material',result.id],confirmed);
  if (current()) { setSavedId(result.id); setBase(confirmed); original.current = payload.content_data; form.reset(value); onSaved?.(result.id); }
  await Promise.all([invalidate(['learning','content',result.id], {exact:true,refetchType:'none'}), invalidate(['authoring','library']), invalidate(['course-materials']), invalidate(['courses'])]);
 });
 const remove = useOperation(async () => {
  if (!savedId) throw responseError();
  const result = await api.delete<unknown>(`/api/content/${savedId}`);
  if (!record(result) || result.id !== savedId || result.message !== 'Content deleted successfully') throw responseError(true);
  return savedId;
 }, async id => {if (current()) { setDeleted(true); setConfirm(null); form.reset(); } await Promise.all([invalidate(['learning','content',id], {exact:true,refetchType:'none'}), invalidate(['authoring'], {refetchType:'none'}), invalidate(['course-materials']), invalidate(['courses'])]);});
 const reload = useOperation(async () => {
  if (!savedId) throw responseError();
  const result = await api.get<unknown>(`/api/content/${savedId}`);
  if (!isAuthorMaterial(result) || result.id !== savedId || result.can_edit !== true) throw responseError();
  return result;
 }, result => {if (!current()) return; original.current = result.content_data; setBase(result); form.reset(materialForm(result.content_type === 'exercise' ? 'exercise' : 'lesson',result.content_data,result.title,result.difficulty)); save.reset(); remove.reset(); setConfirm(null);});
 const busy = save.isPending || remove.isPending || reload.isPending, uncertain = [save.error,remove.error].some(error => error instanceof ApiError && error.uncertain), dirty = !deleted && (form.formState.isDirty || (!savedId && !!proposal) || busy);
 useEffect(() => {onDirty(dirty); return () => onDirty(false);}, [dirty,onDirty]);
 if (deleted) return <EmptyState title={t('deleted')} action={<Link to="/materiales">{t('library')}</Link>} />;
 const required = {validate: (value: string) => !!value.trim() || t('required')};
 return <div className="stack"><form className="stack" onSubmit={form.handleSubmit(value => save.mutateAsync(value).then(() => undefined).catch(() => undefined))}>
  <SaveStatus state={uncertain ? 'uncertain' : busy ? 'saving' : dirty ? 'dirty' : save.isSuccess ? 'saved' : 'idle'} />
  {savedId && <p role="status">{t('savedMaterial', {id:savedId})} <Link to={`/materiales/${savedId}`}>{t('read')}</Link></p>}
  <fieldset disabled={busy || uncertain}><div className="stack">
   <div className="form-grid"><Field label={t('title')} error={form.formState.errors.title?.message}><Input maxLength={200} {...form.register('title',required)} /></Field><Field label={t('kind')}><Select {...form.register('kind')} disabled={!!savedId || !!proposal}><option value="lesson">{t('lesson')}</option><option value="exercise">{t('exercise')}</option></Select></Field><Field label={t('difficulty')} error={form.formState.errors.difficulty?.message}><Input type="number" min={1} max={10} {...form.register('difficulty',{valueAsNumber:true,validate:value => Number.isInteger(value) && value >= 1 && value <= 10 || t('rangeDifficulty')})} /></Field></div>
   {values.kind === 'lesson' ? <>
    <h2>{t('sections')}</h2>{sections.fields.map((section,index) => <Card key={section.id}><div className="stack"><Field label={t('sectionTitle',{number:index+1})}><Input {...form.register(`sections.${index}.title`)} /></Field><Field label={t('sectionContent',{number:index+1})}><Textarea rows={8} {...form.register(`sections.${index}.content`)} /></Field>{section.source_clarification && <Badge>{t('sourceClarification')}</Badge>}<div className="cluster"><Button type="button" variant="secondary" disabled={index===0} aria-label={t('moveUp',{number:index+1})} onClick={() => sections.move(index,index-1)}>{t('up')}</Button><Button type="button" variant="secondary" disabled={index===sections.fields.length-1} aria-label={t('moveDown',{number:index+1})} onClick={() => sections.move(index,index+1)}>{t('down')}</Button><Button type="button" variant="danger" disabled={sections.fields.length===1} onClick={() => sections.remove(index)}>{t('removeSection')}</Button></div></div></Card>)}<Button type="button" variant="secondary" onClick={() => sections.append({title:'',content:''})}>{t('addSection')}</Button>
    <details><summary>{t('lessonDetails')}</summary><div className="stack">{(['objectives','key_concepts','discussion_questions',...lessonTextFields] as const).map(key => <Field key={key} label={t(key)}><Textarea rows={3} {...form.register(key)} /></Field>)}<h3>{t('vocabulary')}</h3>{vocabulary.fields.map((item,index) => <div key={item.id} className="form-grid"><Field label={t('term',{number:index+1})}><Input {...form.register(`vocabulary.${index}.term`)} /></Field><Field label={t('definition',{number:index+1})}><Textarea {...form.register(`vocabulary.${index}.definition`)} /></Field><Button type="button" variant="danger" onClick={() => vocabulary.remove(index)}>{t('removeTerm')}</Button></div>)}<Button type="button" variant="secondary" onClick={() => vocabulary.append({term:'',definition:''})}>{t('addTerm')}</Button></div></details>
   </> : <>
    <Field label={t('exerciseType')}><Select {...form.register('exerciseType')}><option value="short_answer">{t('short_answer')}</option><option value="multiple_choice">{t('multiple_choice')}</option><option value="true_false">{t('true_false')}</option>{!['short_answer','multiple_choice','true_false'].includes(values.exerciseType) && <option value={values.exerciseType}>{values.exerciseType}</option>}</Select></Field>
    <Field label={t('question')} error={form.formState.errors.question?.message}><Textarea {...form.register('question',required)} /></Field>
    {values.exerciseType === 'multiple_choice' && <><h2>{t('choices')}</h2>{options.fields.map((option,index) => <div key={option.id} className="form-grid"><Field label={t('choiceKey',{number:index+1})}><Input {...form.register(`options.${index}.key`,required)} /></Field><Field label={t('choiceText',{number:index+1})}><Input {...form.register(`options.${index}.value`,required)} /></Field><Button type="button" variant="danger" onClick={() => options.remove(index)}>{t('removeChoice')}</Button></div>)}<Button type="button" variant="secondary" onClick={() => {let index=options.fields.length+1; const keys=form.getValues('options').map(item=>item.key); while(keys.includes(String(index))) index++; options.append({key:String(index),value:''});}}>{t('addChoice')}</Button></>}
    <Field label={t('correctAnswer')} error={form.formState.errors.correctAnswer?.message}>{values.exerciseType === 'multiple_choice' ? <Select {...form.register('correctAnswer',required)}><option value="">{t('choose')}</option>{values.options.map((option,index) => <option key={index} value={option.key}>{option.value || option.key}</option>)}</Select> : values.exerciseType === 'true_false' ? <Select {...form.register('correctAnswer',required)}><option value="">{t('choose')}</option><option value="true">{t('true')}</option><option value="false">{t('false')}</option></Select> : <Textarea {...form.register('correctAnswer',required)} />}</Field>
    <Field label={t('explanation')}><Textarea {...form.register('explanation')} /></Field><Field label={t('hints')}><Textarea {...form.register('hints')} /></Field>
   </>}
  </div></fieldset>
  <div className="cluster"><Button type="submit" busy={save.isPending} disabled={busy || uncertain}>{t('saveDraft')}</Button><Button type="button" variant="secondary" onClick={() => setPreview(!preview)} aria-expanded={preview}>{t('preview')}</Button>{savedId && <><Button type="button" variant="secondary" disabled={busy} onClick={() => setConfirm('reload')}>{t('reloadSaved')}</Button><Button type="button" variant="danger" disabled={busy || uncertain} onClick={() => setConfirm('delete')}>{t('delete')}</Button></>}</div>
  {[save.error,remove.error,reload.error].filter(Boolean).map((error,index) => <ErrorState key={index} error={error} />)}{uncertain && <p>{t('uncertain')} <Link to="/materiales">{t('checkLibrary')}</Link></p>}
 </form>{preview && <Card><div className="stack"><h2>{t('preview')}</h2>{values.kind === 'lesson' ? values.sections.map((section,index) => <section key={index}><h3>{section.title}</h3><ContentRenderer value={section.content}/></section>) : <><ContentRenderer value={values.question}/><ul>{values.options.map((option,index)=><li key={index}>{option.value}</li>)}</ul><ContentRenderer value={values.explanation}/></>}</div></Card>}
 <ConfirmDialog open={confirm!==null} onOpenChange={open => {if(!open&&!busy)setConfirm(null);}} title={t(confirm==='delete'?'deleteTitle':'reloadTitle')} description={t(confirm==='delete'?'deleteDescription':'reloadDescription')} confirmLabel={t(confirm==='delete'?'delete':'reloadSaved')} destructive busy={busy} onConfirm={() => {if(confirm==='delete')remove.mutate(undefined); else reload.mutate(undefined);}}/>
 </div>;
}
