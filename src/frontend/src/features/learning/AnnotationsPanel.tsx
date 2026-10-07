import { useEffect, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/app/AuthProvider';
import { ApiError } from '@/lib/api';
import { formatTimestamp, validTimezone } from '@/lib/time';
import { positiveId } from '@/lib/ids';
import { useInvalidate, useOperation, useResource } from '@/lib/query';
import { Badge, Button, Card, ConfirmDialog, EmptyState, ErrorState, Field, LoadingState, SaveStatus, Select, Textarea } from '@/components/ui';
import { isAnnotationDeleteReceipt, isAnnotationList, isAnnotationReceipt, toolResponseError, type AnnotationInput, type AnnotationRecord, type AnnotationType } from './tool-contracts';

export interface AnnotationsPanelProps { contentId: number; onDirtyChange?: (dirty: boolean) => void }
interface AnnotationForm { text: string; type: AnnotationType; audience: 'private' | 'shared' }
type Operation = { kind: 'save'; body: AnnotationInput; snapshot: AnnotationForm } | { kind: 'delete'; annotation: AnnotationRecord };
const emptyForm: AnnotationForm = { text: '', type: 'comment', audience: 'private' };
/** Unsent text is memory-only; the study page keeps this component mounted when hidden. */
export function AnnotationsPanel({ contentId, onDirtyChange }: AnnotationsPanelProps) {
  const { user, scope, status } = useAuth();
  if (!user || !positiveId(contentId)) return null;
  return <div hidden={status !== 'authenticated'} inert={status !== 'authenticated'}><AnnotationsForm key={`${scope}:${contentId}`} contentId={contentId} onDirtyChange={onDirtyChange} /></div>;
}
function AnnotationsForm({ contentId, onDirtyChange }: AnnotationsPanelProps) {
  const { user, api, status, scope, getSnapshot } = useAuth(), { t, i18n } = useTranslation('learning'), invalidate = useInvalidate();
  const timezone = useResource<unknown>(['settings', 'timezone'], '/api/settings/timezone');
  const zone = timezone.data && typeof timezone.data === 'object' && 'timezone' in timezone.data && validTimezone(timezone.data.timezone) ? timezone.data.timezone : 'UTC';
  const resource = useResource<unknown>(['annotations', contentId], `/api/annotations/?content_id=${contentId}`);
  const form = useForm<AnnotationForm>({ defaultValues: emptyForm });
  const [decision, setDecision] = useState<Operation | null>(null), [notice, setNotice] = useState('');
  const [reviewed, setReviewed] = useState(false), [reviewing, setReviewing] = useState(false), [reviewError, setReviewError] = useState<unknown>(null);
  const active = useRef(false), ownerId = user!.id;
  useEffect(() => { active.current = true; return () => { active.current = false; }; }, []);
  const annotations = isAnnotationList(resource.data, contentId) && resource.data.every(entry => entry.user_id === ownerId || (entry.is_public && user?.role !== 'student')) ? resource.data : null;
  const operation = useOperation(async (input: Operation) => {
    if (input.kind === 'save') {
      const receipt = await api.post<unknown>('/api/annotations/', input.body);
      if (!isAnnotationReceipt(receipt, input.body, ownerId)) throw toolResponseError(true);
    } else {
      if (input.annotation.user_id !== ownerId || input.annotation.content_id !== contentId) throw new ApiError(403);
      const receipt = await api.delete<unknown>(`/api/annotations/${input.annotation.id}`);
      if (!isAnnotationDeleteReceipt(receipt)) throw toolResponseError(true);
    }
    return input;
  }, async input => {
    if (!active.current) return;
    if (input.kind === 'save' && JSON.stringify(form.getValues()) === JSON.stringify(input.snapshot)) form.reset(emptyForm);
    setDecision(null); setReviewed(false); setNotice(input.kind === 'save' ? 'annotationSaved' : 'annotationDeleted');
    await invalidate(['annotations', contentId]);
  });
  const uncertain = operation.error instanceof ApiError && operation.error.uncertain;
  const dirty = form.formState.isDirty || uncertain;
  useEffect(() => { onDirtyChange?.(dirty); }, [dirty, onDirtyChange]);
  useEffect(() => () => { onDirtyChange?.(false); }, [onDirtyChange]);
  const disabled = status !== 'authenticated' || operation.isPending;
  function saveInput(values: AnnotationForm): Operation {
    return { kind: 'save', snapshot: { ...values }, body: { content_id: contentId, annotation_text: values.text.trim(), annotation_type: values.type, is_public: values.audience === 'shared', text_selection_start: null, text_selection_end: null } };
  }
  function run(input: Operation) {
    if (disabled || getSnapshot().scope !== scope || getSnapshot().status !== 'authenticated') return;
    setNotice(''); setReviewed(false); setReviewError(null);
    void operation.mutateAsync(input).catch(() => { if (active.current) setDecision(null); });
  }
  async function checkSaved() {
    if (getSnapshot().scope !== scope || getSnapshot().status !== 'authenticated') return;
    setReviewing(true); setReviewError(null);
    try {
      const result = await resource.refetch();
      if (!active.current) return;
      if (result.error) throw result.error;
      if (!isAnnotationList(result.data, contentId)) throw toolResponseError();
      const previous = operation.variables;
      if (previous?.kind === 'delete' && !result.data.some(entry => entry.id === previous.annotation.id)) { operation.reset(); setNotice('annotationGone'); setReviewed(false); return; }
      setReviewed(true);
    } catch (error) { if (active.current) setReviewError(error); }
    finally { if (active.current) setReviewing(false); }
  }
  function retryDecision() {
    const previous = operation.variables;
    if (previous?.kind === 'delete') setDecision(previous);
    else void form.handleSubmit(values => setDecision(saveInput(values)))();
  }
  const operationState = operation.isPending ? 'saving' : uncertain ? 'uncertain' : form.formState.isDirty ? 'dirty' : notice ? 'saved' : 'idle';
  return <section className="stack" aria-label={t('annotationsTitle')}><h2>{t('annotationsTitle')}</h2>
    <form className="stack" onSubmit={form.handleSubmit(values => { if (!uncertain) run(saveInput(values)); })}>
      <Field label={t('annotationText')} error={form.formState.errors.text && t('annotationRequired')}><Textarea rows={4} {...form.register('text', { validate: value => !!value.trim() })} disabled={status !== 'authenticated'} /></Field>
      <div className="form-grid"><Field label={t('annotationType')}><Select {...form.register('type')} disabled={status !== 'authenticated'}><option value="comment">{t('annotationComment')}</option><option value="question">{t('annotationQuestion')}</option><option value="highlight">{t('annotationHighlight')}</option></Select></Field><Field label={t('annotationAudience')} hint={t('annotationAudienceHint')}><Select {...form.register('audience')} disabled={status !== 'authenticated'}><option value="private">{t('annotationPrivate')}</option><option value="shared">{t('annotationShared')}</option></Select></Field></div>
      <p className="muted">{t('annotationMemoryHint')}</p><Button type="submit" busy={operation.isPending} disabled={disabled || uncertain}>{t('annotationSave')}</Button>
    </form>
    <SaveStatus state={operationState}>{notice && !form.formState.isDirty ? t(notice) : undefined}</SaveStatus>{notice && form.formState.isDirty && <p role="status">{t(notice)}</p>}<ErrorState error={operation.error} />
    {uncertain && <div className="stack"><p role="status">{t('annotationUnknown')}</p><div className="cluster"><Button variant="secondary" busy={reviewing} disabled={disabled} onClick={() => { void checkSaved(); }}>{t('annotationCheckSaved')}</Button>{reviewed && <Button variant="secondary" disabled={disabled} onClick={retryDecision}>{t('annotationRetry')}</Button>}</div>{reviewed && <p role="status">{t('annotationChecked')}</p>}<ErrorState error={reviewError} /></div>}
    {resource.isPending ? <LoadingState /> : resource.error ? <ErrorState error={resource.error} retry={() => { void resource.refetch(); }} /> : !annotations ? <ErrorState error={toolResponseError()} /> : !annotations.length ? <EmptyState title={t('annotationsEmpty')} description={t('annotationsEmptyHint')} /> : <div className="stack">{annotations.map(annotation => <Card key={annotation.id}><div className="stack"><p className="prose">{annotation.annotation_text}</p><p className="muted">{t('annotationAuthor', { name: annotation.user_name })}</p><p className="muted">{formatTimestamp(annotation.created_at, {timezone: zone, locale: i18n.language, unknownLabel: t('annotationTimeUnknown')})}</p><div className="cluster"><Badge>{t(({comment:'annotationComment',question:'annotationQuestion',highlight:'annotationHighlight',note:'annotationNote'} as Record<string,string>)[annotation.annotation_type] || 'annotationTypeUnknown')}</Badge><Badge>{t(annotation.is_public ? annotation.user_id === ownerId ? 'annotationShared' : 'annotationSharedAuthor' : 'annotationPrivate')}</Badge>{annotation.user_id === ownerId && <Button variant="danger" disabled={disabled || uncertain} onClick={() => setDecision({ kind: 'delete', annotation })}>{t('annotationDelete')}</Button>}</div></div></Card>)}</div>}
    <ConfirmDialog open={decision !== null && status === 'authenticated'} onOpenChange={open => { if (!open && !operation.isPending) setDecision(null); }} title={t(uncertain ? 'annotationRetryTitle' : 'annotationDeleteTitle')} description={t(uncertain ? 'annotationRetryDescription' : 'annotationDeleteDescription')} confirmLabel={t(uncertain ? 'annotationRetry' : 'annotationDelete')} destructive={decision?.kind === 'delete'} busy={operation.isPending} onConfirm={() => { if (decision) run(decision); }}>{decision?.kind === 'delete' && <p>{decision.annotation.annotation_text}</p>}</ConfirmDialog>
  </section>;
}
