import { useEffect, useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/app/AuthProvider';
import { useInvalidate, useOperation } from '@/lib/query';
import { ApiError } from '@/lib/api';
import { Button, Card, ConfirmDialog, ErrorState, Field, Input, Textarea } from '@/components/ui';
import { ContentRenderer } from '@/components/content/ContentRenderer';
import { invalidResponse, isMaterial, type Material } from './contracts';
interface LessonForm {title: string; content: string; difficulty: number}
export function LessonComposer({onCreated, onDirty, onBusy, onCancel}: {onCreated: (item: Material) => void; onDirty: (dirty: boolean) => void; onBusy: (busy: boolean) => void; onCancel: () => void}) {
  const {t} = useTranslation('courses'), {api, user} = useAuth(), invalidate = useInvalidate();
  const form = useForm<LessonForm>({defaultValues: {title: '', content: '', difficulty: 1}}), content = useWatch({control: form.control, name: 'content'});
  const [confirmCancel, setConfirmCancel] = useState(false);
  const save = useOperation(async (value: LessonForm) => {
    const data = await api.post<unknown>('/api/content/', {title: value.title.trim(), content_type: 'lesson', content_data: {content: value.content}, difficulty: value.difficulty, is_personal: false});
    if (!isMaterial(data) || data.content_type !== 'lesson' || data.is_personal || data.creator_id !== user?.id || data.title !== value.title.trim()) throw invalidResponse(true);
    return data;
  }, async data => {form.reset(); onDirty(false); onCreated(data); await invalidate(['course-materials']);});
  useEffect(() => {onDirty(form.formState.isDirty);}, [form.formState.isDirty, onDirty]);
  useEffect(() => {onBusy(save.isPending); return () => onBusy(false);}, [save.isPending, onBusy]);
  const uncertain = save.error instanceof ApiError && save.error.uncertain;
  return <Card><div className="stack"><h2>{t('newLesson')}</h2><p>{t('lessonHint')}</p><form className="stack" onSubmit={form.handleSubmit(value => save.mutateAsync(value).then(() => undefined).catch(() => undefined))}><fieldset disabled={save.isPending || uncertain}><div className="stack">
    <Field label={t('lessonTitle')} error={form.formState.errors.title?.message}><Input autoFocus {...form.register('title', {required: t('required'), maxLength: {value: 200, message: t('maxTitle')}, validate: value => !!value.trim() || t('required')})} maxLength={200} /></Field>
    <Field label={t('difficulty')} error={form.formState.errors.difficulty?.message}><Input type="number" min={1} max={10} step={1} {...form.register('difficulty', {valueAsNumber: true, validate: value => Number.isInteger(value) && value >= 1 && value <= 10 || t('invalidDifficulty')})} /></Field>
    <Field label={t('lessonBody')} error={form.formState.errors.content?.message}><Textarea rows={10} {...form.register('content', {validate: value => !!value.trim() || t('required')})} /></Field>
  </div></fieldset><div className="cluster"><Button type="submit" busy={save.isPending} disabled={uncertain}>{t('createLesson')}</Button><Button type="button" variant="ghost" disabled={save.isPending} onClick={() => form.formState.isDirty ? setConfirmCancel(true) : onCancel()}>{t('cancel')}</Button></div>{save.error && <ErrorState error={save.error} />}{uncertain && <p>{t('uncertain')}</p>}</form>
    {content.trim() && <section aria-label={t('lessonPreview')}><h3>{t('lessonPreview')}</h3><ContentRenderer value={content} /></section>}
    <ConfirmDialog open={confirmCancel} onOpenChange={setConfirmCancel} title={t('discard')} description={t('dirty')} confirmLabel={t('discard')} onConfirm={onCancel} destructive />
  </div></Card>;
}
