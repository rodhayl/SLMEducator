import { LocalAttemptRecovery } from './LocalAttemptRecovery';
import { useTranslation } from 'react-i18next';
import { Badge, Card, ErrorState } from '@/components/ui';
import { ContentRenderer } from '@/components/content/ContentRenderer';
import { formatTimestamp, validTimezone } from '@/lib/time';
import { useResource } from '@/lib/query';
import { choicesFor, invalidResponse, parsed, record, type Question, type Submission, type SubmissionStatus } from './model';

export function useValidated<T>(key: readonly unknown[], path: string | null, validate: (value: unknown) => value is T) {
 const resource = useResource<unknown>(key, path); const result = parsed(resource.data, validate);
 return { ...resource, data: result.data, error: resource.error || result.error };
}
export function SubmissionBadge({ status }: { status: SubmissionStatus }) { const { t } = useTranslation('assessments'); return <Badge tone={status === 'graded' ? 'success' : status === 'submitted' || status === 'ai_graded' ? 'warning' : 'neutral'}>{t(`status_${status}`)}</Badge>; }
export function Timestamp({ value, provenance }: { value: string | null | undefined; provenance?: string }) {
 const { t, i18n } = useTranslation('assessments');
 const timezone = useResource<unknown>(['settings', 'timezone'], '/api/settings/timezone');
 const zone = !timezone.error && record(timezone.data) && validTimezone(timezone.data.timezone) ? timezone.data.timezone : 'UTC';
 return <>{formatTimestamp(value, { locale: i18n.language, timezone: zone, provenance, unknownLabel: t('unknownTime') })}</>;
}
export function QuestionPreview({ question, number, showKey = false }: { question: Question; number: number; showKey?: boolean }) {
 const { t } = useTranslation('assessments'); const choices = choicesFor(question);
 return <Card><h3>{t('previewQuestion', { number })}</h3><ContentRenderer value={question.question_text}/><p className="muted">{t('points', { count: question.points })}</p>{choices === null ? <ErrorState error={invalidResponse()}/> : !!choices.length && <ul>{choices.map(choice => <li key={choice.value}>{choice.booleanLabel ? t(choice.booleanLabel) : choice.label}</li>)}</ul>}{showKey && question.correct_answer !== null && <p>{t('correctAnswer')}: {question.correct_answer}</p>}</Card>;
}
export function SubmissionReading({ submission, staff = false }: { submission: Submission; staff?: boolean }) {
 const { t } = useTranslation('assessments');
 return <div className="stack"><div className="cluster"><SubmissionBadge status={submission.status}/><span>{submission.status === 'graded' && submission.score !== null ? `${t('finalScore')}: ${submission.score} / ${submission.total_points ?? '—'}` : t('noFinalScore')}</span></div><p>{t('submittedAt')}: <Timestamp value={submission.submitted_at}/></p>{submission.graded_at && <p>{t('gradedAt')}: <Timestamp value={submission.graded_at}/></p>}{submission.feedback && <Card><h2>{t('feedback')}</h2><ContentRenderer value={submission.feedback}/></Card>}{submission.answers.map((answer, index) => <Card key={answer.response_id}><h3>{t('previewQuestion', { number: index + 1 })}</h3><ContentRenderer value={answer.question_text}/><h4>{t(staff ? 'learnerAnswer' : 'yourAnswer')}</h4><ContentRenderer value={answer.given_answer || t('noAnswer')}/>{staff && answer.correct_answer !== null && <p>{t('correctAnswer')}: {answer.correct_answer}</p>}<p>{answer.points === null ? t('missingGrade') : `${answer.points} / ${answer.max_points}`}</p>{answer.feedback && <ContentRenderer value={answer.feedback}/>} {answer.ai_suggested_score !== null && <div className="panel"><p>{t('aiSuggestion')}: {answer.ai_suggested_score} / {answer.max_points}</p>{answer.ai_suggested_feedback && <ContentRenderer value={answer.ai_suggested_feedback}/>}</div>}</Card>)}{!staff && <LocalAttemptRecovery submission={submission}/>}</div>;
}
