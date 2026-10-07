import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router';
import { useForm, useWatch } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/app/AuthProvider';
import { useDirtyGuard } from '@/app/DirtyGuard';
import { DraftAdapter } from '@/lib/drafts';
import { positiveId } from '@/lib/ids';
import { useInvalidate, useOperation } from '@/lib/query';
import { Button, Card, ConfirmDialog, ErrorState, LoadingState, PageHeader, SaveStatus, Textarea } from '@/components/ui';
import { ContentRenderer } from '@/components/content/ContentRenderer';
import { attemptDeadline, choicesFor, confirmResult, isAssessment, isDraft, isSubmission, unavailable, type Answer, type Assessment, type AttemptDraft, type Submission } from './model';
import { SubmissionReading, useValidated } from './shared';

export function AttemptWorkspacePage() {
 const { user, scope } = useAuth(); const { submissionId } = useParams(); const id = positiveId(submissionId);
 return id && user?.role === 'student' ? <AttemptLoader key={`${scope}:${id}`} id={id} ownerId={user.id}/> : <ErrorState error={unavailable()}/>;
}
function AttemptLoader({ id, ownerId }: { id: number; ownerId: number }) {
 const { t } = useTranslation('assessments'); const submission = useValidated(['submission', id], `/api/assessments/submissions/${id}`, value => isSubmission(value, id, ownerId));
 const assessmentId = submission.data?.assessment_id; const assessment = useValidated(['assessment', assessmentId], assessmentId && submission.data?.status === 'draft' ? `/api/assessments/${assessmentId}` : null, value => isAssessment(value, assessmentId));
 if (submission.isPending || submission.data?.status === 'draft' && assessment.isPending) return <LoadingState/>;
 if (submission.error || assessment.error || !submission.data) return <ErrorState error={submission.error || assessment.error || unavailable()} retry={() => { void submission.refetch(); if (assessmentId) void assessment.refetch(); }}/>;
 if (submission.data.status !== 'draft') return <div className="stack"><Link to={`/evaluaciones/${submission.data.assessment_id}/historial`}>{t('history')}</Link><PageHeader title={submission.data.assessment_title} description={t(submission.data.status === 'abandoned' ? 'confirmedClosure' : 'confirmedSubmission')}/><SubmissionReading submission={submission.data}/></div>;
 return assessment.data ? <AttemptWorkspace assessment={assessment.data} submission={submission.data} ownerId={ownerId} refresh={async () => { const result = await submission.refetch(); return !result.error && isSubmission(result.data, id, ownerId); }}/> : <ErrorState error={unavailable()}/>;
}
function AttemptTimer({ submission, timeLimit }: { submission: Submission; timeLimit: number | null }) {
 const { t } = useTranslation('assessments'); const [now, setNow] = useState(() => Date.now()); const deadline = attemptDeadline(submission);
 useEffect(() => { if (deadline === null) return; const handle = window.setInterval(() => setNow(Date.now()), 1000); return () => window.clearInterval(handle); }, [deadline]);
 if (!timeLimit) return <p>{t('noLimit')}</p>;
 if (deadline === null) return <p role="status">{t('timerUnknown')}</p>;
 const remaining = Math.max(0, Math.ceil((deadline - now) / 1000));
 return <div><p>{t('serverTimer')}: <span role="timer" aria-live="off">{String(Math.floor(remaining / 60)).padStart(2, '0')}:{String(remaining % 60).padStart(2, '0')}</span></p>{remaining === 0 && <p role="status">{t('expired')}</p>}</div>;
}
function AttemptWorkspace({ assessment, submission, ownerId, refresh }: { assessment: Assessment; submission: Submission; ownerId: number; refresh: () => Promise<boolean> }) {
 const { t } = useTranslation('assessments'); const { api, status } = useAuth(); const invalidate = useInvalidate(); const drafts = useMemo(() => new DraftAdapter(ownerId), [ownerId]);
 const [draft, setDraft] = useState<AttemptDraft | null>(() => drafts.read('assessment', assessment.id, submission.id, value => isDraft(value, assessment)));
 const form = useForm<{ answers: Answer[] }>({ defaultValues: { answers: assessment.questions.map(question => ({ question_id: question.id, response_text: submission.answers.find(answer => answer.question_id === question.id)?.given_answer || '' })) } });
 const answers = useWatch({ control: form.control, name: 'answers' }); const [draftSaved, setDraftSaved] = useState<boolean | null>(null); const [review, setReview] = useState(false); const [confirm, setConfirm] = useState<'submit' | 'close' | null>(null); const [terminal, setTerminal] = useState<'submit' | 'close' | null>(null); const [checked, setChecked] = useState(false);
 useDirtyGuard(!terminal && form.formState.isDirty);
 useEffect(() => { if (draft || terminal || !form.formState.isDirty || status !== 'authenticated') return; setDraftSaved(drafts.write('assessment', assessment.id, submission.id, { answers, savedAt: new Date().toISOString() })); }, [answers, draft, terminal, status, form.formState.isDirty, drafts, assessment.id, submission.id]);
 const finalize = useOperation(async (input: { action: 'submit' | 'close'; answers: Answer[] }) => { const close = input.action === 'close'; const result = await api.post<unknown>(close ? `/api/assessments/submissions/${submission.id}/close` : `/api/assessments/${assessment.id}/submit`, close ? { reason: 'abandoned', answers: input.answers } : { submission_id: submission.id, answers: input.answers }); confirmResult(result, submission.id, close); return input.action; }, async action => { setTerminal(action); setConfirm(null); drafts.remove('assessment', assessment.id, submission.id); form.reset(form.getValues()); await invalidate(['submission', submission.id]); await invalidate(['submissions']); });
 function restore() { if (!draft) return; for (let index = 0; index < assessment.questions.length; index++) { const answer = draft.answers.find(item => item.question_id === assessment.questions[index].id); if (answer) form.setValue(`answers.${index}.response_text`, answer.response_text, { shouldDirty: true }); } setDraft(null); }
 function discard() { const removed = drafts.remove('assessment', assessment.id, submission.id); setDraftSaved(removed ? null : false); if (removed) setDraft(null); }
 function send() { if (!confirm || blocked) return; const current = form.getValues('answers'); setChecked(false); setDraftSaved(drafts.write('assessment', assessment.id, submission.id, { answers: current, savedAt: new Date().toISOString() })); const action = confirm; setConfirm(null); finalize.mutate({ action, answers: current }); }
 const unavailableChoices = assessment.questions.some(question => !question.options_supported || ['multiple_choice', 'true_false'].includes(question.question_type) && !choicesFor(question)?.length);
 const blocked = finalize.isPending || !!terminal || !!draft || unavailableChoices || !!finalize.error?.uncertain && !checked;
 return <div className="stack"><Link to={`/evaluaciones/${assessment.id}`}>{t('leaveOpen')}</Link><PageHeader title={assessment.title} description={t('attempt')}/><Card><AttemptTimer submission={submission} timeLimit={assessment.time_limit_minutes}/><p className="muted">{t('draftPrivacy')}</p></Card>{draft && <Card><h2>{t('draftAvailable')}</h2><div className="cluster"><Button onClick={restore}>{t('restore')}</Button><Button variant="danger" onClick={discard}>{t('discard')}</Button></div></Card>}{draftSaved !== null && <SaveStatus state={draftSaved ? 'saved' : 'uncertain'}>{t(draftSaved ? 'localDraft' : 'draftFailed')}</SaveStatus>}
 {unavailableChoices && <p role="alert">{t('unsupportedOptions')}</p>}<ErrorState error={finalize.error}/>{finalize.error?.uncertain && <Card><p>{t('mutationUncertain')}</p><Button variant="secondary" onClick={() => { void refresh().then(success => { if (success) setChecked(true); }); }}>{t('refresh')}</Button></Card>}
 <form className="stack" onSubmit={event => { event.preventDefault(); if (!blocked) setConfirm('submit'); }}><fieldset disabled={blocked} className="stack">{assessment.questions.map((question, index) => { const choices = choicesFor(question); return <Card key={question.id}><fieldset className="stack"><legend>{t('previewQuestion', { number: index + 1 })} · {t('points', { count: question.points })}</legend><ContentRenderer value={question.question_text}/>{review ? <ContentRenderer value={choices?.find(choice => choice.value === answers[index]?.response_text)?.label || answers[index]?.response_text || t('noAnswer')}/> : ['multiple_choice', 'true_false'].includes(question.question_type) ? choices?.length ? <><div className="stack">{choices.map((choice, choiceIndex) => <label className="cluster" key={choice.value}><input type="radio" value={choice.value} {...form.register(`answers.${index}.response_text`)} id={`answer-${question.id}-${choiceIndex}`}/><span>{choice.booleanLabel ? t(choice.booleanLabel) : choice.label}</span></label>)}</div><Button variant="ghost" onClick={() => form.setValue(`answers.${index}.response_text`, '', { shouldDirty: true })}>{t('clearAnswer', { number: index + 1 })}</Button></> : <p role="alert">{t('noAnswerControls')}</p> : <Textarea rows={question.question_type === 'long_answer' ? 8 : 4} aria-label={t('answerLabel', { number: index + 1 })} {...form.register(`answers.${index}.response_text`)}/>}</fieldset></Card>; })}<p>{t('unanswered', { count: answers.filter(answer => !answer.response_text.trim()).length })}</p><div className="cluster"><Button variant="secondary" onClick={() => setReview(value => !value)}>{t(review ? 'returnToAnswers' : 'review')}</Button><Button type="submit" busy={finalize.isPending}>{t('submit')}</Button><Button variant="danger" onClick={() => setConfirm('close')}>{t('close')}</Button></div></fieldset></form>
 {terminal && <Card><h2>{t(terminal === 'close' ? 'confirmedClosure' : 'confirmedSubmission')}</h2><Link to={`/envios/${submission.id}`}>{t('finish')}</Link></Card>}
 <ConfirmDialog open={confirm !== null} onOpenChange={open => { if (!open) setConfirm(null); }} title={t(confirm === 'close' ? 'close' : 'submitTitle')} description={t(confirm === 'close' ? 'closeDescription' : 'submitDescription')} confirmLabel={t(confirm === 'close' ? 'close' : 'submit')} destructive={confirm === 'close'} busy={finalize.isPending} onConfirm={send}/></div>;
}
