import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams, type RouteObject } from 'react-router';
import { useTranslation } from 'react-i18next';
import { useForm, useWatch } from 'react-hook-form';
import { useAppearance } from '@/app/AppearanceProvider';
import { SessionElapsed } from './SessionElapsed';
import { useAuth } from '@/app/AuthProvider';
import { useDirtyGuard } from '@/app/DirtyGuard';
import { ApiError } from '@/lib/api';
import { DraftAdapter } from '@/lib/drafts';
import { positiveId } from '@/lib/ids';
import { useInvalidate, useOperation, useResource } from '@/lib/query';
import { Badge, Button, Card, ConfirmDialog, EmptyState, ErrorState, Field, LoadingState, PageHeader, SaveStatus, Select, Textarea } from '@/components/ui';
import { AnnotationsPanel } from './AnnotationsPanel';
import { PracticeBlock } from './PracticeBlock';
import { LearningHelp } from './LearningHelp';
import { LessonContent } from './LessonContent';
import { contentData, invalidResponse, isLearningContent, isNotesDraft, isProgress, isSession, isSessionFor, isSessionList, isStudyTree, isRecord, materialHref, sessionHref, sessionPlan, type NotesDraft, type StudySession, type StudyTree } from './contracts';
import { knownInstant, validTimezone } from '@/lib/time';
import './learning.css';

function useAlive() {
 const alive = useRef(true);
 useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
 return alive;
}
function SessionDate({session}: {session: StudySession}) {
 const { t, i18n } = useTranslation('learning');
 const timezone = useResource<unknown>(['settings', 'timezone'], '/api/settings/timezone');
 const zone = isRecord(timezone.data) && validTimezone(timezone.data.timezone) ? timezone.data.timezone : 'UTC';
 const instant = knownInstant(session.start_time, session.timestamp_provenance);
 return <span>{instant === null ? t('dateUnknown', {date: session.start_time}) : `${new Intl.DateTimeFormat(i18n.language, {timeZone: zone, dateStyle: 'medium', timeStyle: 'short'}).format(instant)} (${zone})`}</span>;
}
function Unavailable() { const {t} = useTranslation('learning'); return <EmptyState title={t('unavailable')} description={t('invalidLink')} action={<Link to="/cursos">{t('backCourses')}</Link>} />; }

/** A GET-only preview. Session creation, restore and restart require deliberate actions. */
export function MaterialPreviewPage() {
 const {contentId: parameter} = useParams(), [search] = useSearchParams(), {scope} = useAuth();
 const contentId = positiveId(parameter), planId = positiveId(search.get('plan_id'));
 if (!contentId || (search.has('plan_id') && !planId)) return <Unavailable />;
 return <MaterialPreview key={`${scope}:${contentId}:${planId}`} contentId={contentId} planId={planId} />;
}
function MaterialPreview({contentId, planId}: {contentId: number; planId: number | null}) {
 const {api, status} = useAuth(), {t} = useTranslation('learning'), navigate = useNavigate(), alive = useAlive(), invalidate = useInvalidate();
 const content = useResource<unknown>(['learning', 'content', contentId], `/api/content/${contentId}`);
 const history = useResource<unknown>(['learning', 'history', contentId], `/api/learning/history/${contentId}?limit=100`);
 const tree = useResource<unknown>(['courses', planId, 'tree'], planId ? `/api/study-plans/${planId}/tree` : null);
 const [restartOpen, setRestartOpen] = useState(false);
 const start = useOperation<{kind: 'start'|'restart'|'restore'; sessionId?: number}, StudySession>(async input => {
  const result = input.kind === 'restart' ? await api.post<unknown>(`/api/learning/restart/${contentId}${planId ? `?study_plan_id=${planId}` : ''}`) : input.kind === 'restore' ? await api.post<unknown>(`/api/learning/${input.sessionId}/restore`) : await api.post<unknown>('/api/learning/start', {content_id: contentId, ...(planId ? {study_plan_id: planId} : {})});
  if (!isSessionFor(result, contentId, planId, input.kind === 'restore' ? input.sessionId : undefined) || result.status !== 'active') throw invalidResponse(true);
  return result;
 }, async session => { await invalidate(['learning', 'history', contentId]); await invalidate(['learning', 'active']); if (alive.current) navigate(sessionHref(session)); });
 if (content.isPending || (planId && tree.isPending)) return <LoadingState />;
 if (content.error || tree.error) return <ErrorState error={content.error || tree.error} retry={() => { void content.refetch(); if (planId) void tree.refetch(); }} />;
 if (!isLearningContent(content.data) || content.data.id !== contentId || (planId && (!isStudyTree(tree.data, planId) || !tree.data.contents.some(item => item.id === contentId)))) return <ErrorState error={invalidResponse()} />;
 const sessions = isSessionList(history.data, contentId) ? history.data.filter(session => sessionPlan(session) === planId) : null;
 return <div className="stack">
  <Link to={planId ? `/cursos/${planId}` : '/cursos'}>{t(planId ? 'back' : 'backCourses')}</Link>
  <PageHeader title={content.data.title} description={t('materialPreview')} />
  <div className="cluster"><Button busy={start.isPending} onClick={() => start.mutate({kind: 'start'})}>{t(sessions?.some(session => session.status === 'active') ? 'continue' : 'start')}</Button>{!!sessions?.length && <Button variant="secondary" disabled={start.isPending} onClick={() => setRestartOpen(true)}>{t('restart')}</Button>}</div>
  <ErrorState error={start.error} />
  <article className="learning-reader"><LessonContent content={content.data} /></article>
  <section className="stack" aria-label={t('history')}><h2>{t('history')}</h2>{history.isPending ? <LoadingState /> : history.error ? <ErrorState error={history.error} retry={() => { void history.refetch(); }} /> : !sessions ? <ErrorState error={invalidResponse()} /> : !sessions.length ? <p>{t('noHistory')}</p> : <ul className="list">{sessions.map(session => <li key={session.id}><Card><div className="stack"><div className="cluster"><Link to={sessionHref(session)}>{t('sessionNumber', {id: session.id})}</Link><Badge>{t(session.status)}</Badge></div><SessionDate session={session}/>{session.notes && <p>{session.notes.slice(0, 200)}</p>}<Button variant="secondary" disabled={start.isPending} onClick={() => start.mutate({kind: 'restore', sessionId: session.id})}>{t(session.status === 'active' ? 'continue' : 'restore')}</Button></div></Card></li>)}</ul>}</section>
  <p className="muted">{t('serverNeeded')}</p>
  <ConfirmDialog open={restartOpen && status === 'authenticated'} onOpenChange={setRestartOpen} title={t('restartTitle')} description={t('restartDescription')} confirmLabel={t('restart')} busy={start.isPending} onConfirm={() => { setRestartOpen(false); start.mutate({kind: 'restart'}); }} />
 </div>;
}

export function LearningWorkspace() {
 const {sessionId: parameter} = useParams(), [search] = useSearchParams(), {scope} = useAuth();
 const sessionId = positiveId(parameter), contentId = positiveId(search.get('content_id')), planId = positiveId(search.get('plan_id'));
 if (!sessionId || (search.has('content_id') && !contentId) || (search.has('plan_id') && !planId)) return <Unavailable />;
 return <SessionRoute key={`${scope}:${sessionId}:${contentId}:${planId}`} sessionId={sessionId} contentId={contentId} planHint={planId} />;
}
function SessionRoute({sessionId, contentId, planHint}: {sessionId: number; contentId: number | null; planHint: number | null}) {
 const navigate = useNavigate();
 const source = useResource<unknown>(contentId ? ['learning', 'history', contentId] : ['learning', 'active'], contentId ? `/api/learning/history/${contentId}?limit=100` : '/api/learning/active');
 const session = contentId ? isSessionList(source.data, contentId) ? source.data.find(item => item.id === sessionId) : null : isSession(source.data) && source.data.id === sessionId ? source.data : null;
 useEffect(() => { if (!contentId && session && (!planHint || sessionPlan(session) === planHint)) void navigate(sessionHref(session), {replace: true}); }, [contentId, session, planHint, navigate]);
 const planId = session ? sessionPlan(session) : planHint;
 const tree = useResource<unknown>(['courses', planId, 'tree'], session && planId ? `/api/study-plans/${planId}/tree` : null);
 if (source.isPending || (session && planId && tree.isPending)) return <LoadingState />;
 if (source.error || tree.error) return <ErrorState error={source.error || tree.error} retry={() => { void source.refetch(); if (planId) void tree.refetch(); }} />;
 if (!session || (planHint && planId !== planHint) || (planId && (!isStudyTree(tree.data, planId) || !tree.data.contents.some(item => item.id === session.content_id)))) return <Unavailable />;
 return <SessionStudy key={`${session.id}:${session.content_id}:${planId}`} initial={session} plan={planId && isStudyTree(tree.data, planId) ? tree.data : null} />;
}

type StudyAction = {kind: 'save'|'pause'|'navigate'; notes: string; destination?: string} | {kind: 'complete'; notes: string; confidence: number | null; destination?: string};
type StudyResult = {session: StudySession; completed: boolean; destination?: string};
function SessionStudy({initial, plan}: {initial: StudySession; plan: StudyTree | null}) {
 const {user, api, status, scope, getSnapshot} = useAuth(), {t} = useTranslation('learning'), navigate = useNavigate(), invalidate = useInvalidate(), alive = useAlive();
 const {readingSize, setReadingSize} = useAppearance();
 const [session, setSession] = useState(initial), [savedNotes, setSavedNotes] = useState(initial.notes || '');
 const notesForm = useForm<{notes: string}>({defaultValues: {notes: initial.notes || ''}});
 const notes = useWatch({control: notesForm.control, name: 'notes'});
 const setNotes = (value: string) => notesForm.setValue('notes', value, {shouldDirty: true});
 const [drafts] = useState(() => { try { return new DraftAdapter(user!.id); } catch { return null; } });
 const [draft, setDraft] = useState<NotesDraft | null>(() => { const found = drafts?.read('notes', initial.content_id, initial.id, isNotesDraft); return initial.status === 'active' && found && found.notes !== (initial.notes || '') ? found : null; });
 const [localState, setLocalState] = useState<'idle'|'local'|'failed'|'remove-failed'>('idle'), [panel, setPanel] = useState<'index'|'notes'|'help'|null>(null);
 const [annotationDirty, setAnnotationDirty] = useState(false), [practiceDirty, setPracticeDirty] = useState(false), [helpDirty, setHelpDirty] = useState(false);
 const [completeOpen, setCompleteOpen] = useState(false), [confidence, setConfidence] = useState(''), [completionStarted, setCompletionStarted] = useState(false), [completionSaved, setCompletionSaved] = useState(false);
 const completionReceipt = useRef<StudySession | null>(initial.status === 'completed' ? initial : null), completionInput = useRef<{notes: string; confidence: number | null} | null>(null);
 const heading = useRef<HTMLHeadingElement>(null), toolHeading = useRef<HTMLHeadingElement>(null);
 const [destination, setDestination] = useState<string | null>(null);
 const planId = plan?.id ?? null, contentId = session.content_id, back = planId ? `/cursos/${planId}` : '/cursos';
 const items = [...(plan?.contents || [])].sort((a,b) => a.phase_index - b.phase_index || a.order_index - b.order_index), index = items.findIndex(item => item.id === contentId);
 const progress = useResource<unknown>(['courses', planId, 'progress'], planId ? `/api/study-plans/${planId}/my-progress` : null);
 const action = useOperation<StudyAction, StudyResult>(async input => {
  if (input.kind !== 'complete') {
   if (session.status !== 'active') return {session, completed: false, destination: input.destination};
   const receipt = await api.patch<unknown>(`/api/learning/${session.id}/notes`, {notes: input.notes});
   if (!isSessionFor(receipt, contentId, planId, session.id) || receipt.status !== 'active' || receipt.notes !== input.notes) throw invalidResponse(true);
   return {session: receipt, completed: false, destination: input.destination};
  }
  const frozen = completionInput.current || {notes: input.notes, confidence: input.confidence};
  completionInput.current = frozen;
  setCompletionStarted(true);
  let receipt = completionReceipt.current;
  if (!receipt) {
   const result = await api.post<unknown>(`/api/learning/${session.id}/end`, {notes: frozen.notes, ...(frozen.confidence === null ? {} : {difficulty_rating: frozen.confidence})}).finally(() => { void invalidate(['learning', 'active']).catch(() => undefined); });
   if (!isSessionFor(result, contentId, planId, session.id) || result.status !== 'completed' || result.notes !== frozen.notes) throw invalidResponse(true);
   receipt = result;
   if (!alive.current || getSnapshot().scope !== scope || getSnapshot().status !== 'authenticated') throw new ApiError(0, 'stale', true, 'uncertain');
   completionReceipt.current = receipt;
   setSession(receipt); setSavedNotes(receipt.notes || '');
  }
  if (!alive.current || getSnapshot().scope !== scope || getSnapshot().status !== 'authenticated') throw new ApiError(0, 'stale', true, 'uncertain');
  if (planId) {
   const result = await api.post<unknown>(`/api/study-plans/${planId}/progress`, {completed_content_id: contentId});
   if (!isProgress(result, planId, contentId)) throw invalidResponse(true);
  }
  return {session: receipt, completed: true, destination: input.destination};
 }, async result => {
  if (!alive.current) return;
  setSession(result.session); setSavedNotes(result.session.notes || ''); notesForm.reset({notes: result.session.notes || ''});
  setLocalState(drafts?.remove('notes', contentId, session.id) ? 'idle' : 'remove-failed');
  if (result.completed) setCompletionSaved(true);
  await invalidate(['learning', 'history', contentId]);
  await invalidate(['learning', 'active']);
  if (!alive.current) return;
  if (planId) await invalidate(['courses', planId, 'progress']);
  await invalidate(['progress']);
  if (alive.current && result.destination) setDestination(result.destination);
 });
 const restoreNotes = useOperation<NotesDraft, NotesDraft>(async candidate => {
  const history = await api.get<unknown>(`/api/learning/history/${contentId}?limit=100`);
  if (!isSessionList(history, contentId) || !history.some(item => isSessionFor(item, contentId, planId, session.id) && item.status === 'active')) throw invalidResponse();
  if (planId) {
   const currentPlan = await api.get<unknown>(`/api/study-plans/${planId}/tree`);
   if (!isStudyTree(currentPlan, planId) || !currentPlan.contents.some(item => item.id === contentId)) throw invalidResponse();
  }
  return candidate;
 }, candidate => { if (alive.current) { setNotes(candidate.notes); setLocalState('local'); setDraft(null); setPanel('notes'); } });
 const dirty = notes !== savedNotes || annotationDirty || practiceDirty || helpDirty || action.isPending || (completionStarted && !completionSaved);
 useDirtyGuard(dirty);
 useEffect(() => { if (!destination) return; const timer = window.setTimeout(() => { navigate(destination); setDestination(null); }, 0); return () => window.clearTimeout(timer); }, [destination, navigate]);
 useEffect(() => { if (panel) toolHeading.current?.focus(); }, [panel]);
 useEffect(() => { if (planId && status === 'authenticated' && getSnapshot().scope === scope) drafts?.write('learning-location', 'current', 0, {planId, contentId}); }, [drafts, planId, contentId, status, scope, getSnapshot]);
 const save = (kind: 'save'|'pause'|'navigate', target?: string) => action.mutate({kind, notes, destination: target});
 const closePanel = () => { setPanel(null); heading.current?.focus(); };
 const blocked = status !== 'authenticated' || action.isPending || !!draft;
 const immutable = session.status !== 'active' || completionStarted;
 const snapshot = session.content_snapshot;
 const readingTitle = snapshot?.title || t('sessionNumber', {id: session.id});
 useEffect(() => { if (status === 'authenticated' && heading.current && !heading.current.closest('[hidden], [inert]')) { document.title = `${readingTitle} · SLMEducator`; heading.current.focus({preventScroll: true}); } }, [readingTitle, status]);
 const progressMissing = session.status === 'completed' && planId && isProgress(progress.data, planId) && !progress.data.completed_content_ids.includes(contentId);
 const notesError = action.error && action.variables?.kind !== 'complete';
 const openCompletion = () => { if (completionStarted) action.mutate({kind: 'complete', notes, confidence: confidence ? Number(confidence) : null, destination: index >= 0 && index + 1 < items.length ? materialHref(items[index + 1]!.id, planId) : back}); else setCompleteOpen(true); };
 const completionTarget = index >= 0 && index + 1 < items.length ? materialHref(items[index + 1]!.id, planId) : back;
 return <div className="stack">
  <Link to={back}>{t(planId ? 'back' : 'backCourses')}</Link>
  <header className="stack"><h1 ref={heading} tabIndex={-1}>{readingTitle}</h1><div className="cluster"><Badge>{t(session.status)}</Badge><span>{t('sessionNumber', {id: session.id})}</span><SessionDate session={session}/></div><p className="muted">{snapshot ? t('snapshotDescription') : t('missingSnapshot')}</p><SessionElapsed session={session} running={status === 'authenticated'}/></header>
  <div className="cluster learning-controls" aria-label={t('tools')}><Field label={t('readingSize')}><Select value={readingSize} onChange={event => { const size = Number(event.target.value); if (size === 16 || size === 18 || size === 20 || size === 24) setReadingSize(size); }}>{[16,18,20,24].map(size => <option key={size} value={size}>{t('readingSizeValue', {size})}</option>)}</Select></Field>{(['index', 'notes', 'help'] as const).map(tool => <Button key={tool} variant="secondary" aria-expanded={panel === tool} aria-controls={`study-${tool}`} disabled={tool === 'help' && !snapshot} onClick={() => { if (panel === tool) closePanel(); else setPanel(tool); }}>{t(tool === 'help' ? 'helpTab' : tool)}</Button>)}</div>
  <div className="learning-workspace">
   <article className="learning-reader" aria-label={t('snapshot')}>
    {snapshot ? snapshot.content_type === 'exercise' ? <PracticeBlock raw={contentData(snapshot)} contentId={contentId} sessionId={session.id} readOnly={immutable} onDirtyChange={setPracticeDirty}/> : <LessonContent content={snapshot}/> : <p><Link to={materialHref(contentId, planId)}>{t('restart')}</Link></p>}
   </article>
   <aside className="learning-tools" hidden={panel === null} onKeyDown={event => { if (event.key === 'Escape') { event.preventDefault(); closePanel(); } }}>
    <div className="stack"><div className="cluster"><h2 ref={toolHeading} tabIndex={-1}>{t(panel === 'help' ? 'helpTab' : panel || 'tools')}</h2><Button variant="ghost" onClick={closePanel}>{t('closeTool')}</Button></div>
     <div className="learning-tool stack" id="study-index" hidden={panel !== 'index'}>
      {!plan ? <p>{t('noPlan')}</p> : <><h3>{plan.title}</h3>{progress.isPending ? <LoadingState/> : progress.error ? <ErrorState error={progress.error} retry={() => {void progress.refetch();}}/> : !isProgress(progress.data, plan.id) ? <ErrorState error={invalidResponse()}/> : <p>{t('progress', {completed: progress.data.completed_content_ids.length, total: progress.data.total_contents})}</p>}<ol className="list">{items.map(item => <li key={item.id}><Button variant="ghost" aria-current={item.id === contentId ? 'step' : undefined} disabled={blocked || item.id === contentId || (completionStarted && !completionSaved)} onClick={() => save('navigate', materialHref(item.id, planId))}>{item.title}</Button>{isProgress(progress.data, plan.id) && progress.data.completed_content_ids.includes(item.id) && <Badge tone="success">{t('done')}</Badge>}</li>)}</ol></>}
     </div>
     <div className="learning-tool stack" id="study-notes" hidden={panel !== 'notes'}>
      <Field label={t('notesLabel')} hint={t('notesHint')}><Textarea value={notes} rows={10} disabled={blocked || immutable} onChange={event => { if (getSnapshot().scope !== scope || getSnapshot().status !== 'authenticated') return; const value = event.target.value; setNotes(value); setLocalState(drafts?.write('notes', contentId, session.id, {notes: value}) ? 'local' : 'failed'); }}/></Field>
      <SaveStatus state={action.isPending ? 'saving' : notesError ? 'uncertain' : notes !== savedNotes ? 'dirty' : 'saved'}>{action.isPending ? t('notesSaving') : notesError ? t('noteUncertain') : localState === 'remove-failed' ? t('draftRemoveFailed') : localState === 'failed' ? t('storageFailed') : notes !== savedNotes ? t(localState === 'local' ? 'localNotes' : 'notesDirty') : t('savedNotes')}</SaveStatus>
      {!immutable && <Button variant="secondary" busy={action.isPending} disabled={blocked} onClick={() => save('save')}>{t('saveNotes')}</Button>}
      <AnnotationsPanel contentId={contentId} onDirtyChange={setAnnotationDirty}/>
     </div>
     <div className="learning-tool" id="study-help" hidden={panel !== 'help'}><LearningHelp contentId={contentId} planId={planId} sessionId={session.id} contextRevision={session.context_revision} active={panel === 'help' && !!snapshot} onDirtyChange={setHelpDirty}/></div>
    </div>
   </aside>
  </div>
  <ErrorState error={action.error}/>
  {completionStarted && !completionSaved && <p role="status">{t(session.status === 'completed' ? 'completionPending' : 'completionUncertain')}</p>}
  {completionSaved && <div className="stack"><p role="status">{t(planId ? 'completionSaved' : 'sessionSaved')}</p><Link to={completionTarget}>{t(index >= 0 && index + 1 < items.length ? 'nextMaterial' : planId ? 'back' : 'backCourses')}</Link></div>}
  {session.status === 'active' || completionStarted || progressMissing ? <div className="cluster">
   {index > 0 && <Button variant="secondary" disabled={blocked || completionStarted} onClick={() => save('navigate', materialHref(items[index - 1]!.id, planId))}>{t('previous')}</Button>}
   <Button variant="secondary" disabled={blocked || completionStarted} onClick={() => save('pause', back)}>{t('pause')}</Button>
   <Button busy={action.isPending} disabled={blocked || completionSaved || !snapshot} onClick={openCompletion}>{t(planId ? index < items.length - 1 ? 'completeNext' : 'completeReturn' : 'complete')}</Button>
  </div> : <div className="stack"><p>{t('readOnlySession')}</p><Link to={materialHref(contentId, planId)}>{t('restore')}</Link></div>}
  {session.status !== 'active' && <p className="muted">{session.duration_known && session.duration_minutes !== null ? t('duration', {minutes: session.duration_minutes}) : t('durationUnknown')}</p>}
  <p className="muted">{t('serverNeeded')}</p>
  <ConfirmDialog open={!!draft && status === 'authenticated'} onOpenChange={open => { if (!open) navigate(back); }} title={t('draftFound')} description={t('draftDescription')} confirmLabel={t('restoreDraft')} busy={restoreNotes.isPending} onConfirm={() => { if (draft) restoreNotes.mutate(draft); }}>
   <ErrorState error={restoreNotes.error}/>
   {localState === 'remove-failed' && <ErrorState error={new ApiError(0, 'invalid', false, 'storage')}/>}<div className="cluster"><Button variant="secondary" onClick={() => { if (drafts?.remove('notes', contentId, session.id)) setDraft(null); else setLocalState('remove-failed'); }}>{t('discardDraft')}</Button><Button variant="ghost" onClick={() => navigate(back)}>{t('leaveDraft')}</Button></div>
  </ConfirmDialog>
  <ConfirmDialog open={completeOpen && status === 'authenticated'} onOpenChange={setCompleteOpen} title={t('completeTitle')} description={t('completeDescription')} confirmLabel={t('complete')} busy={action.isPending} onConfirm={() => { setCompleteOpen(false); action.mutate({kind: 'complete', notes, confidence: confidence ? Number(confidence) : null, destination: completionTarget}); }}>
   <Field label={t('confidence')} hint={t('confidenceHint')}><Select value={confidence} onChange={event => setConfidence(event.target.value)}><option value="">{t('noRating')}</option>{[1,2,3,4,5].map(value => <option key={value} value={value}>{t(`confidence${value}`)}</option>)}</Select></Field>
  </ConfirmDialog>
 </div>;
}

export const routes: RouteObject[] = [
 {path: 'materiales/:contentId', element: <MaterialPreviewPage/>},
 {path: 'estudio/:sessionId', element: <LearningWorkspace/>},
];
