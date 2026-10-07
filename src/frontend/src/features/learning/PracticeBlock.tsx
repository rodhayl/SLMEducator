import { useEffect, useMemo, useRef, useState, type ChangeEvent } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/app/AuthProvider';
import { DraftAdapter } from '@/lib/drafts';
import { positiveId } from '@/lib/ids';
import { useOperation } from '@/lib/query';
import { Button, Card, EmptyState, ErrorState, Field, SaveStatus, Select, Textarea } from '@/components/ui';
import { isPracticeDraft, normalizePractice, practiceFingerprint, practiceSolution, toolResponseError, type PracticeDraft, type PracticeQuestion } from './tool-contracts';

export interface PracticeBlockProps { raw: unknown; contentId: number; sessionId: number; readOnly?: boolean; onDirtyChange?: (dirty: boolean) => void }
/** Keep mounted while auxiliary panels are hidden; ownership/context changes reset its buffer. */
export function PracticeBlock({ raw, contentId, sessionId, readOnly = false, onDirtyChange }: PracticeBlockProps) {
  const { user, scope, status } = useAuth(), { t } = useTranslation('learning');
  const questions = useMemo(() => normalizePractice(raw), [raw]);
  if (!user || !positiveId(contentId) || !positiveId(sessionId)) return null;
  if (!questions) return <EmptyState title={t('practiceUnavailable')} />;
  return <div hidden={status !== 'authenticated'} inert={status !== 'authenticated'}><PracticeForm key={`${scope}:${contentId}:${sessionId}:${practiceFingerprint(questions)}`} questions={questions} contentId={contentId} sessionId={sessionId} ownerId={user.id} readOnly={readOnly} onDirtyChange={onDirtyChange} /></div>;
}

function openDrafts(ownerId: number): DraftAdapter | null {
  try { const storage = window.localStorage; void storage.length; return new DraftAdapter(ownerId, storage); } catch { return null; }
}
function PracticeForm({ questions: initialQuestions, contentId, sessionId, ownerId, readOnly, onDirtyChange }: { questions: PracticeQuestion[]; contentId: number; sessionId: number; ownerId: number; readOnly: boolean; onDirtyChange?: (dirty: boolean) => void }) {
  const { api, status, scope, getSnapshot } = useAuth(), { t } = useTranslation('learning');
  const [questions] = useState(initialQuestions);
  const [drafts] = useState(() => openDrafts(ownerId));
  const [candidate, setCandidate] = useState<PracticeDraft | null>(null), [ready, setReady] = useState(false);
  const [unavailable, setUnavailable] = useState(!drafts), [dirty, setDirty] = useState(false), [saved, setSaved] = useState(false);
  const [feedback, setFeedback] = useState<(null | 'empty' | 'check')[]>(() => questions.map(() => null));
  const active = useRef(false), editable = useRef(!readOnly);
  useEffect(() => { editable.current = !readOnly && status === 'authenticated'; }, [readOnly, status]);
  const form = useForm<PracticeDraft>({ defaultValues: { answers: questions.map(() => ''), hints: questions.map(() => 0) } });
  const hints = useWatch({ control: form.control, name: 'hints' });
  const answers = useWatch({ control: form.control, name: 'answers' });
  useEffect(() => { active.current = true; return () => { active.current = false; }; }, []);
  useEffect(() => {
    const found = drafts?.read('practice', contentId, sessionId, (value): value is PracticeDraft => isPracticeDraft(value, questions));
    setCandidate(found && (found.answers.some(Boolean) || found.hints.some(Boolean)) ? found : null); setReady(true);
  }, [drafts, contentId, sessionId, questions]);
  useEffect(() => { onDirtyChange?.(dirty); }, [dirty, onDirtyChange]);
  useEffect(() => () => { onDirtyChange?.(false); }, [onDirtyChange]);
  const restore = useOperation(async (value: PracticeDraft) => {
    const latest = await api.get<unknown>(`/api/content/${contentId}`);
    if (!latest || typeof latest !== 'object' || !('id' in latest) || latest.id !== contentId) throw toolResponseError();
    // Access is revalidated against current content. Answers belong to the parent's fixed session snapshot.
    if (!isPracticeDraft(value, questions)) throw toolResponseError();
    return value;
  }, value => { if (active.current && editable.current) { form.reset(value); setCandidate(null); setSaved(true); } });
  function canEdit() { const current = getSnapshot(); return active.current && editable.current && current.scope === scope && current.status === 'authenticated'; }
  function persist() {
    if (!canEdit() || candidate) return;
    const value = { ...form.getValues(), fingerprint: practiceFingerprint(questions) };
    const success = drafts?.write('practice', contentId, sessionId, value) ?? false;
    setSaved(success); setUnavailable(!success); setDirty(!success && (value.answers.some(Boolean) || value.hints.some(Boolean)));
  }
  function discard() {
    if (!canEdit()) return;
    if (drafts?.remove('practice', contentId, sessionId)) { setCandidate(null); restore.reset(); }
    else setUnavailable(true);
  }
  function hint(index: number) { if (!canEdit()) return; form.setValue(`hints.${index}`, Math.min((form.getValues(`hints.${index}`) || 0) + 1, Math.max(1, questions[index].hints.length))); persist(); }
  function check(index: number) {
    if (!canEdit()) return;
    const empty = !form.getValues(`answers.${index}`).trim();
    setFeedback(current => current.map((value, position) => position === index ? empty ? 'empty' : 'check' : value));
    if (empty) form.setFocus(`answers.${index}`);
  }
  const disabled = readOnly || status !== 'authenticated' || !ready || !!candidate || restore.isPending;
  return <section className="stack" aria-label={t('practiceTitle')}><h2>{t('practiceTitle')}</h2><p>{t('practiceNotice')}</p>
    <p className="muted">{t('practiceStorageNotice')}</p>
    {candidate && <Card><div className="stack"><p>{t('practiceDraftFound')}</p><div className="cluster"><Button busy={restore.isPending} disabled={readOnly || status !== 'authenticated'} onClick={() => { if (canEdit()) void restore.mutateAsync(candidate).catch(() => undefined); }}>{t('practiceRestore')}</Button><Button variant="secondary" disabled={readOnly || restore.isPending || status !== 'authenticated'} onClick={discard}>{t('practiceDiscard')}</Button></div></div></Card>}
    {restore.error && <ErrorState error={restore.error} />}
    {unavailable && <SaveStatus state={dirty ? 'dirty' : 'idle'}>{t('practiceStorageUnavailable')}</SaveStatus>}
    {saved && !unavailable && <SaveStatus state="saved">{t('practiceDraftSaved')}</SaveStatus>}
    {questions.map((question, index) => {
      const revealed = hints[index] || 0, availableHints = question.hints.length ? question.hints : [t('practiceDefaultHint')];
      const solution = practiceSolution(question), matched = solution !== null && question.options.length > 0 && answers[index]?.trim().toLocaleLowerCase() === solution.trim().toLocaleLowerCase();
      const input = form.register(`answers.${index}`);
      const change = (event: ChangeEvent<HTMLSelectElement | HTMLTextAreaElement>) => { if (!canEdit()) return; void input.onChange(event); setFeedback(current => current.map((value, position) => position === index ? null : value)); persist(); };
      return <Card key={index}><div className="stack"><Field label={question.prompt}>{question.options.length ? <Select {...input} onChange={change} disabled={disabled}><option value="">{t('practiceChoose')}</option>{question.options.map(option => <option key={option.key} value={option.text}>{option.booleanLabel ? t(option.booleanLabel === 'true' ? 'practiceTrue' : 'practiceFalse') : option.text}</option>)}</Select> : <Textarea {...input} onChange={change} disabled={disabled} rows={3} />}</Field>
        <div className="cluster"><Button variant="secondary" disabled={disabled || revealed >= availableHints.length} onClick={() => hint(index)}>{t('practiceHint')}</Button><Button variant="secondary" disabled={disabled} onClick={() => check(index)}>{t('practiceCheck')}</Button></div>
        <div role="status" aria-live="polite">{revealed > 0 && <ul>{availableHints.slice(0, revealed).map((value, position) => <li key={position}>{value}</li>)}</ul>}{feedback[index] === 'empty' && <p>{t('practiceAttemptFirst')}</p>}{feedback[index] === 'check' && (solution === null ? <p>{t('practiceNoKey')}</p> : <><p>{t(matched ? 'practiceMatch' : 'practiceCompare')}</p><p>{t('practiceAnswer', { answer: question.options.find(option => option.text === solution)?.booleanLabel ? t(solution.toLowerCase() === 'true' ? 'practiceTrue' : 'practiceFalse') : solution })}</p>{question.explanation && <p>{question.explanation}</p>}<p>{t('practiceNotGrade')}</p></>)}</div>
      </div></Card>;
    })}
  </section>;
}
