import { useEffect, useId, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/app/AuthProvider';
import { ContentRenderer } from '@/components/content/ContentRenderer';
import { Button, Card, ConfirmDialog, ErrorState, Field, Input, Select, Textarea } from '@/components/ui';
import { ApiError } from '@/lib/api';
import { positiveId } from '@/lib/ids';
import { useOperation, useResource } from '@/lib/query';
import { helpFingerprint, helpRecord, newHelpRequestId, validHelpPolicy, validHelpReceipt, validHelpSource, validHelpUsage, validTeacherReceipt } from './help-contracts';
import type { HelpPolicy, HelpReceipt, HelpSource, TeacherPayload, TeacherReceipt, TutorPayload } from './help-contracts';

export interface LearningHelpProps {
  contentId: number; planId: number | null; sessionId: number;
  contextRevision: Record<string, unknown> | null; active: boolean;
  onDirtyChange?: (dirty: boolean) => void;
}
type Pending = { id: string; fingerprint: string };
type Exchange = { question: string; response: string; source: HelpSource };
type TutorForm = { question: string; assistance: 'hint' | 'explanation' };
type TeacherForm = { subject: string; description: string; urgency: string };

/** Account/context replacement clears buffers; hiding preserves them in memory. */
export function LearningHelp(props: LearningHelpProps) {
  const { scope } = useAuth();
  return <HelpForContext key={helpFingerprint([scope, props.contentId, props.planId, props.sessionId, props.contextRevision])} {...props} />;
}
function HelpForContext({ contentId, planId, sessionId, contextRevision, active, onDirtyChange }: LearningHelpProps) {
  const { t } = useTranslation('learning');
  const { api, user, status } = useAuth();
  const labelId = useId();
  const [mode, setMode] = useState<'tutor' | 'teacher'>('tutor');
  const [generation, setGeneration] = useState(0);
  const [sections, setSections] = useState<string[]>([]);
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [pendingTutor, setPendingTutor] = useState<Pending | null>(null);
  const [pendingTeacher, setPendingTeacher] = useState<Pending | null>(null);
  const [receipt, setReceipt] = useState<{ value: HelpReceipt; at: number } | null>(null);
  const [teacherReceipt, setTeacherReceipt] = useState<TeacherReceipt | null>(null);
  const [policyOverride, setPolicyOverride] = useState<{ value: HelpPolicy; at: number } | null>(null);
  const [invalidContext, setInvalidContext] = useState(false);
  const [tutorMessage, setTutorMessage] = useState('');
  const [teacherMessage, setTeacherMessage] = useState('');
  const [cancelMessage, setCancelMessage] = useState('');
  const [error, setError] = useState<unknown>(null);
  const [confirm, setConfirm] = useState<'tutor' | 'teacher' | null>(null);
  const epoch = useRef({ value: 0 });
  const tutorDelivery = useRef({ revision: 0, controller: null as AbortController | null });
  const controllers = useRef(new Set<AbortController>());
  const flights = useRef({ tutor: false, teacher: false, cancel: false });
  const previousSource = useRef<string | null>(null);
  const dirtyCallback = useRef(onDirtyChange);
  const tutorForm = useForm<TutorForm>({ defaultValues: { question: '', assistance: 'hint' } });
  const teacherForm = useForm<TeacherForm>({ defaultValues: { subject: '', description: '', urgency: '1' } });
  const validContext = !!positiveId(contentId) && !!positiveId(sessionId) && (planId === null || !!positiveId(planId));
  const enabled = active && status === 'authenticated' && validContext;
  const contextKey = [contentId, planId, sessionId, helpFingerprint(contextRevision), generation];
  const params = new URLSearchParams({ content_id: String(contentId), session_id: String(sessionId) });
  if (planId !== null) params.set('study_plan_id', String(planId));
  const sourceQuery = useResource<unknown>(['learning-help', 'source', ...contextKey], enabled ? `/api/ai/context?${params}` : null);
  const policyQuery = useResource<unknown>(['learning-help', 'policy', ...contextKey], enabled ? '/api/ai/assistance-policy' : null);
  const usageQuery = useResource<unknown>(['learning-help', 'usage', ...contextKey], enabled ? '/api/ai/usage' : null);
  const source = helpRecord(sourceQuery.data) && validHelpSource(sourceQuery.data.source, contentId) ? sourceQuery.data.source : null;
  const policy = policyOverride && policyOverride.at >= policyQuery.dataUpdatedAt ? policyOverride.value : (validHelpPolicy(policyQuery.data) ? policyQuery.data : null);
  const readUsage = validHelpUsage(usageQuery.data) ? usageQuery.data : null;
  const usage = receipt && receipt.at >= usageQuery.dataUpdatedAt ? { ...receipt.value, active_request_id: receipt.value.provider_may_continue ? receipt.value.request_id : null } : readUsage;
  const loading = sourceQuery.isFetching || policyQuery.isFetching;
  const loaded = enabled && !loading && !invalidContext && !!source && !!policy;
  const dirty = tutorForm.formState.isDirty || teacherForm.formState.isDirty || !!pendingTutor || !!pendingTeacher;
  useEffect(() => { onDirtyChange?.(dirty); }, [dirty, onDirtyChange]);
  useEffect(() => { dirtyCallback.current = onDirtyChange; }, [onDirtyChange]);
  useEffect(() => () => { dirtyCallback.current?.(false); }, []);
  useEffect(() => {
    if (!source) return;
    if (previousSource.current && previousSource.current !== source.source_version) setExchanges([]);
    previousSource.current = source.source_version;
    setSections(previous => previous.filter(id => source.available_sections.some(section => section.id === id)));
  }, [source]);
  useEffect(() => {
    const currentControllers = controllers.current; const ownership = epoch.current;
    return () => { ownership.value++; for (const value of currentControllers) value.abort(); currentControllers.clear(); };
  }, [status]);
  const tutorOperation = useOperation((request: { payload: TutorPayload & { client_request_id: string }; signal: AbortSignal }) => api.post<unknown>('/api/ai/chat', request.payload, { signal: request.signal }));
  const teacherOperation = useOperation((request: { payload: TeacherPayload & { client_request_id: string }; signal: AbortSignal }) => api.post<unknown>('/api/classroom/help', request.payload, { signal: request.signal }));
  const cancelOperation = useOperation((request: { id: string; signal: AbortSignal }) => api.post<unknown>(`/api/ai/requests/${encodeURIComponent(request.id)}/cancel`, undefined, { signal: request.signal }));
  const busy = tutorOperation.isPending || cancelOperation.isPending;
  const quotaBlocked = !!usage && (usage.requests_used_today >= usage.requests_limit_daily && !pendingTutor || !!usage.active_request_id && usage.active_request_id !== pendingTutor?.id);
  function refresh() {
    if (!enabled || busy || teacherOperation.isPending) return;
    epoch.current.value++; setInvalidContext(false); setPolicyOverride(null);
    setError(null); setGeneration(value => value + 1);
  }
  function controller() { const value = new AbortController(); controllers.current.add(value); return value; }
  function remember(value: HelpReceipt) { setReceipt({ value, at: Date.now() }); void usageQuery.refetch(); }
  function requestError(value: unknown, target: 'tutor' | 'teacher') {
    setError(value);
    if (target === 'teacher') { setTeacherMessage('teacherUnconfirmed'); return; }
    if (value instanceof ApiError && [403, 409].includes(value.status)) { setInvalidContext(true); setTutorMessage('changed'); }
    else setTutorMessage(value instanceof ApiError && value.status === 429 ? 'limit' : 'interrupted');
  }
  async function sendTutor(values: TutorForm) {
    if (!loaded || !source || !policy || policy.mode === 'disabled' || quotaBlocked || flights.current.tutor || flights.current.cancel) return;
    const message = values.question.trim();
    if (!message || message.length > 4000) { setTutorMessage('required'); return; }
    if (sections.length > 12 || sections.some(id => !source.available_sections.some(section => section.id === id))) { setTutorMessage('sectionLimit'); return; }
    const history: TutorPayload['conversation_history'] = exchanges.flatMap(exchange => [{ role: 'user' as const, content: exchange.question }, { role: 'assistant' as const, content: exchange.response.slice(0, 4000) }]).slice(-10);
    const payload: TutorPayload = { message, content_id: contentId, study_plan_id: planId, session_id: sessionId, assistance: policy.mode === 'hints_only' ? 'hint' : values.assistance, section_ids: sections, source_version: source.source_version, conversation_history: history };
    const fingerprint = helpFingerprint(payload);
    if (pendingTutor && pendingTutor.fingerprint !== fingerprint) { setTutorMessage('requestPending'); return; }
    const pending = pendingTutor || { id: newHelpRequestId(), fingerprint };
    flights.current.tutor = true; setPendingTutor(pending); setTutorMessage(''); setCancelMessage(''); setError(null);
    const captured = epoch.current.value; const delivery = tutorDelivery.current.revision; const abort = controller(); tutorDelivery.current.controller = abort;
    try {
      const result = await tutorOperation.mutateAsync({ payload: { ...payload, client_request_id: pending.id }, signal: abort.signal });
      if (captured !== epoch.current.value || delivery !== tutorDelivery.current.revision) return;
      if (!helpRecord(result) || !validHelpReceipt(result.receipt, pending.id)) { setTutorMessage('receiptUnconfirmed'); return; }
      remember(result.receipt); setPendingTutor(null);
      if (!validHelpPolicy(result.assistance_policy) || result.assistance_policy.mode === 'disabled' || result.effective_assistance !== payload.assistance || result.assistance_policy.mode === 'hints_only' && result.effective_assistance !== 'hint' || !validHelpSource(result.source, contentId) || result.source.source_version !== payload.source_version) {
        setInvalidContext(true); setTutorMessage('changed'); return;
      }
      setPolicyOverride({ value: result.assistance_policy, at: Date.now() });
      if (result.receipt.status !== 'completed' || result.status !== 'suggestion' || typeof result.response !== 'string' || !result.response.trim()) { setTutorMessage('unavailable'); return; }
      const exchange = { question: message, response: result.response, source: result.source };
      setExchanges(previous => [...previous, exchange].slice(-5));
      tutorForm.reset({ question: '', assistance: result.assistance_policy.mode === 'hints_only' ? 'hint' : values.assistance });
    } catch (value) { if (captured === epoch.current.value && delivery === tutorDelivery.current.revision) requestError(value, 'tutor'); }
    finally { controllers.current.delete(abort); flights.current.tutor = false; if (tutorDelivery.current.controller === abort) tutorDelivery.current.controller = null; }
  }
  async function cancelTutor() {
    const id = pendingTutor?.id || usage?.active_request_id;
    if (!enabled || !id || flights.current.cancel) return;
    flights.current.cancel = true; tutorDelivery.current.revision++; tutorDelivery.current.controller?.abort();
    const captured = epoch.current.value; const abort = controller(); setCancelMessage('cancelling'); setTutorMessage(''); setError(null);
    try {
      const result = await cancelOperation.mutateAsync({ id, signal: abort.signal });
      if (captured !== epoch.current.value) return;
      if (!validHelpReceipt(result, id)) { setCancelMessage('cancelUnconfirmed'); return; }
      remember(result); setPendingTutor(null); setCancelMessage(result.status === 'cancelled' ? 'cancelDone' : 'cancelFinished');
    } catch (value) { if (captured === epoch.current.value) { setError(value); setCancelMessage('cancelUnconfirmed'); } }
    finally { controllers.current.delete(abort); flights.current.cancel = false; }
  }
  async function sendTeacher(values: TeacherForm) {
    if (!enabled || user?.role !== 'student' || teacherReceipt || flights.current.teacher) return;
    const subject = values.subject.trim(), description = values.description.trim(), urgency = Number(values.urgency);
    if (!subject || subject.length > 200 || !description || description.length > 4000 || ![1, 2, 3].includes(urgency)) { setTeacherMessage('teacherRequired'); return; }
    const payload: TeacherPayload = { subject, description, urgency, content_id: contentId, study_plan_id: planId, session_id: sessionId };
    const fingerprint = helpFingerprint(payload);
    if (pendingTeacher && pendingTeacher.fingerprint !== fingerprint) { setTeacherMessage('teacherUnconfirmed'); return; }
    const pending = pendingTeacher || { id: newHelpRequestId(), fingerprint };
    flights.current.teacher = true; setPendingTeacher(pending); setTeacherMessage(''); setError(null);
    const captured = epoch.current.value; const abort = controller();
    try {
      const result = await teacherOperation.mutateAsync({ payload: { ...payload, client_request_id: pending.id }, signal: abort.signal });
      if (captured !== epoch.current.value) return;
      if (!validTeacherReceipt(result, payload, pending.id, user.id, contextRevision)) { setTeacherMessage('teacherUnconfirmed'); return; }
      setTeacherReceipt(result); setPendingTeacher(null); teacherForm.reset(values);
    } catch (value) { if (captured === epoch.current.value) requestError(value, 'teacher'); }
    finally { controllers.current.delete(abort); flights.current.teacher = false; }
  }
  function prepareNew() {
    if (!enabled || busy || teacherOperation.isPending) return;
    if (confirm === 'tutor') { setPendingTutor(null); setTutorMessage(''); setCancelMessage(''); refresh(); }
    else { setPendingTeacher(null); setTeacherReceipt(null); setTeacherMessage(''); teacherForm.reset({ subject: '', description: '', urgency: '1' }); }
    setConfirm(null);
  }
  function changeSection(id: string, checked: boolean) {
    if (checked && sections.length >= 12) { setTutorMessage('sectionLimit'); return; }
    setSections(previous => checked ? [...previous, id] : previous.filter(value => value !== id)); setExchanges([]);
  }
  return <section hidden={!active || status !== 'authenticated'} inert={!active || status !== 'authenticated'} aria-labelledby={labelId}>
    <Card className="stack"><h2 id={labelId}>{t('help.title')}</h2><p className="muted">{t('help.memoryOnly')}</p>
      <div className="cluster"><Button variant={mode === 'tutor' ? 'primary' : 'secondary'} aria-pressed={mode === 'tutor'} onClick={() => setMode('tutor')}>{t('help.tutor')}</Button><Button variant={mode === 'teacher' ? 'primary' : 'secondary'} aria-pressed={mode === 'teacher'} onClick={() => setMode('teacher')}>{t('help.teacher')}</Button></div>
      <ErrorState error={error} />
      <div hidden={mode !== 'tutor'} className="stack">
        <Button variant="secondary" onClick={refresh} disabled={!enabled || busy || teacherOperation.isPending || loading}>{t('help.refresh')}</Button>
        {loading ? <p role="status">{t('help.loading')}</p> : (!loaded && <p role="alert">{t('help.loadFailed')}</p>)}
        <ErrorState error={sourceQuery.error || policyQuery.error} />
        {policy && <p role="status">{t(`help.${policy.mode}`)}</p>}
        {source && <div className="stack"><p>{t('help.context')}: {source.title}</p><p>{t('help.sourceVersion')}: {source.source_version}</p><p>{t(source.truncated ? 'help.partial' : 'help.complete')}</p><p>{t('help.unverified')}</p>
          <details><summary>{t('help.preview')}</summary><ContentRenderer value={source.content_data} /></details>
          <fieldset disabled={!loaded || busy} className="stack"><legend>{t('help.sections')}</legend><p>{t('help.sectionHelp')}</p>{source.available_sections.map(section => <label className="cluster" key={section.id}><input type="checkbox" checked={sections.includes(section.id)} onChange={event => changeSection(section.id, event.target.checked)} />{section.title || section.id} ({section.characters} {t('help.characters')})</label>)}</fieldset>
        </div>}
        <div role="log" aria-live="polite" aria-label={t('help.reply')} className="stack">{exchanges.map((exchange, index) => <Card key={index}><h3>{t('help.you')}</h3><p>{exchange.question}</p><h3>{t('help.reply')}</h3><ContentRenderer value={exchange.response} /><p>{t('help.unverified')}</p><p>{t('help.sourceVersion')}: {exchange.source.source_version}</p><p>{t('help.references')}: {exchange.source.references.join(', ')}</p>{exchange.source.truncated && <p>{t('help.partial')}</p>}</Card>)}</div>
        <form className="stack" onSubmit={tutorForm.handleSubmit(sendTutor, () => setTutorMessage('required'))}>
          <Field label={t('help.assistance')}><Select {...tutorForm.register('assistance')} disabled={!loaded || policy?.mode !== 'explanations' || busy} value={policy?.mode === 'hints_only' ? 'hint' : tutorForm.watch('assistance')}><option value="hint">{t('help.hint')}</option><option value="explanation" disabled={policy?.mode !== 'explanations'}>{t('help.explanation')}</option></Select></Field>
          <Field label={t('help.question')} error={tutorForm.formState.errors.question ? t('help.required') : undefined}><Textarea rows={3} maxLength={4000} {...tutorForm.register('question', { required: true, maxLength: 4000 })} disabled={busy} /></Field>
          <p role="status">{tutorOperation.isPending ? t('help.sending') : tutorMessage ? t(`help.${tutorMessage}`) : pendingTutor ? t('help.interrupted') : ''}</p>
          <div className="cluster"><Button type="submit" busy={tutorOperation.isPending} disabled={!loaded || policy?.mode === 'disabled' || quotaBlocked || cancelOperation.isPending}>{t('help.send')}</Button>{(pendingTutor || usage?.active_request_id) && <Button variant="secondary" onClick={() => void cancelTutor()} busy={cancelOperation.isPending} disabled={!enabled}>{t('help.cancel')}</Button>}{pendingTutor && !busy && <Button variant="secondary" onClick={() => setConfirm('tutor')}>{t('help.newTutor')}</Button>}</div>
        </form>
        <p role="status">{usage ? `${t('help.usage')}: ${usage.requests_used_today} / ${usage.requests_limit_daily}` : t('help.usageUnavailable')}</p>
        {usage?.active_request_id && <p>{t('help.requestActive')}</p>}{usage && usage.requests_used_today >= usage.requests_limit_daily && <p>{t('help.limit')}</p>}
        {cancelMessage && <p role="status">{t(`help.${cancelMessage}`)}</p>}{receipt && <ReceiptDetails receipt={receipt.value} />}<p className="muted">{t('help.costUnknown')}</p>
      </div>
      <div hidden={mode !== 'teacher'} className="stack"><p>{t('help.teacherContext')}</p>
        {user?.role !== 'student' ? <p>{t('help.teacherStudent')}</p> : teacherReceipt ? <><p role="status">{t(teacherReceipt.status === 'resolved' ? 'help.teacherResolved' : 'help.teacherReceipt', { id: teacherReceipt.id })}</p><Button variant="secondary" onClick={() => { setTeacherReceipt(null); teacherForm.reset({ subject: '', description: '', urgency: '1' }); }}>{t('help.newTeacher')}</Button></> : <form className="stack" onSubmit={teacherForm.handleSubmit(sendTeacher, () => setTeacherMessage('teacherRequired'))}>
          <Field label={t('help.subject')} error={teacherForm.formState.errors.subject ? t('help.teacherRequired') : undefined}><Input maxLength={200} {...teacherForm.register('subject', { required: true, maxLength: 200 })} disabled={teacherOperation.isPending} /></Field>
          <Field label={t('help.description')} error={teacherForm.formState.errors.description ? t('help.teacherRequired') : undefined}><Textarea rows={4} maxLength={4000} {...teacherForm.register('description', { required: true, maxLength: 4000 })} disabled={teacherOperation.isPending} /></Field>
          <Field label={t('help.urgency')}><Select {...teacherForm.register('urgency')} disabled={teacherOperation.isPending}><option value="1">{t('help.normal')}</option><option value="2">{t('help.soon')}</option><option value="3">{t('help.urgent')}</option></Select></Field>
          <p role="status">{teacherOperation.isPending ? t('help.teacherSending') : teacherMessage ? t(`help.${teacherMessage}`) : pendingTeacher ? t('help.teacherUnconfirmed') : ''}</p>
          <Button type="submit" busy={teacherOperation.isPending} disabled={!enabled}>{t('help.teacherSend')}</Button>{pendingTeacher && !teacherOperation.isPending && <Button variant="secondary" onClick={() => setConfirm('teacher')}>{t('help.newTeacher')}</Button>}
        </form>}
      </div>
      <ConfirmDialog open={!!confirm && enabled} onOpenChange={open => { if (!open) setConfirm(null); }} title={t(confirm === 'teacher' ? 'help.newTeacher' : 'help.newTutor')} description={t(confirm === 'teacher' ? 'help.newTeacherConfirm' : 'help.newTutorConfirm')} confirmLabel={t(confirm === 'teacher' ? 'help.newTeacher' : 'help.newTutor')} onConfirm={prepareNew} busy={busy || teacherOperation.isPending} />
    </Card>
  </section>;
}
function ReceiptDetails({ receipt }: { receipt: HelpReceipt }) {
  const { t } = useTranslation('learning');
  const rows = { requestId: receipt.request_id, receiptStatus: t(`help.${receipt.status}`), provider: receipt.provider || t('help.unknown'), model: receipt.model || t('help.unknown'), elapsed: receipt.elapsed_seconds, tokens: receipt.tokens_used ?? t('help.unknown'), maxOutput: receipt.max_output_tokens };
  return <Card><h3>{t('help.receipt')}</h3><dl>{Object.entries(rows).map(([key, value]) => <div key={key}><dt>{t(`help.${key}`)}</dt><dd>{value}</dd></div>)}</dl>{receipt.provider_may_continue && <p>{t('help.providerContinue')}</p>}</Card>;
}
