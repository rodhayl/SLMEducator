import { ApiError } from '@/lib/api';
import { knownInstant } from '@/lib/time';

export const questionTypes = ['multiple_choice', 'true_false', 'short_answer', 'long_answer', 'fill_in_blank'] as const;
export const gradingModes = ['manual', 'ai_assisted', 'ai_automatic'] as const;
export const assistanceModes = ['hints_only', 'explanations', 'disabled'] as const;
export const submissionStatuses = ['draft', 'submitted', 'ai_graded', 'graded', 'returned', 'abandoned'] as const;
export type QuestionType = typeof questionTypes[number];
export type SubmissionStatus = typeof submissionStatuses[number];
export type AssistanceMode = typeof assistanceModes[number];
export interface Choice { value: string; label: string; booleanLabel?: 'true' | 'false' }
export interface Question { options_supported: boolean; content_metadata: Record<string, unknown> | null; rubrics: Rubric[]; id: number; question_text: string; question_type: QuestionType; points: number; options: unknown; correct_answer: string | null }
export interface Criterion { name: string; description: string | null; max_points: number }
export interface Rubric { name: string; description?: string | null; criteria: Criterion[] }
export interface AssessmentSummary { id: number; title: string; description: string | null; is_published: boolean; question_count: number; created_at: string; can_manage: boolean }
export interface Assessment extends AssessmentSummary { questions: Question[]; time_limit_minutes: number | null; max_attempts: number; grading_mode: typeof gradingModes[number]; total_points: number; passing_score: number; rubric: Rubric | null; study_plan_id?: number | null; topic_id?: number | null }
export interface Policy { assessment_id: number; mode: AssistanceMode }
export interface SubmissionSummary { id: number; assessment_id: number; assessment_title: string; student_id: number; student_name: string; status: SubmissionStatus; score: number | null; total_points: number | null; submitted_at: string | null; graded_at: string | null; can_manage?: boolean }
export interface AnswerDetail { response_id: number; question_id: number; question_text: string; question_type: string; given_answer: string | null; correct_answer: string | null; is_correct: boolean | null; points: number | null; max_points: number; feedback: string | null; ai_suggested_score: number | null; ai_suggested_feedback: string | null; ai_confidence: number | null; teacher_override: boolean }
export interface Submission extends SubmissionSummary { feedback: string | null; answers: AnswerDetail[]; started_at?: string | null; expires_at?: string | null; timing_provenance?: string; time_limit_minutes?: number | null }
export interface Answer { question_id: number; response_text: string }
export interface AttemptDraft { answers: Answer[]; savedAt?: string }
export interface Stats { assessment_id: number; total_submissions: number; average_score: number | null; highest_score: number | null; lowest_score: number | null; pass_rate: number | null }
export const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value);
export const id = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value > 0;
const natural = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
const nullableString = (value: unknown): value is string | null => value === null || typeof value === 'string';
const nullableNumber = (value: unknown): value is number | null => value === null || typeof value === 'number' && Number.isFinite(value);
const unique = (values: number[]) => new Set(values).size === values.length;
export function invalidResponse(mutation = false) { return new ApiError(0, 'invalid', mutation, mutation ? 'uncertain' : 'invalidResponse'); }
export function unavailable() { return new ApiError(403, 'http', false, 'unavailable'); }
/** Display labels and submitted values stay independent. Legacy arrays submit text, keyed options submit keys. */
export function choicesFor(question: Pick<Question, 'options' | 'question_type'>): Choice[] | null {
  if (!['multiple_choice', 'true_false'].includes(question.question_type)) return [];
  const canonical = record(question.options) && record(question.options.choices);
  const raw = record(question.options) ? question.options.choices ?? question.options.options ?? question.options : question.options;
  if (raw == null || (Array.isArray(raw) && !raw.length) || (record(raw) && !Object.keys(raw).length)) {
    return question.question_type === 'true_false' ? [{ value: 'True', label: 'True', booleanLabel: 'true' }, { value: 'False', label: 'False', booleanLabel: 'false' }] : [];
  }
  const scalar = (value: unknown): string | null => typeof value === 'string' || typeof value === 'boolean' || typeof value === 'number' && Number.isFinite(value) ? String(value) : null;
  const entries = Array.isArray(raw) ? raw.map(value => [scalar(value), scalar(value)]) : record(raw) ? Object.entries(raw).map(([key, value]) => [canonical ? key : scalar(value), scalar(value)]) : null;
  if (!entries || entries.some(([key, value]) => !key?.trim() || value === null) || new Set(entries.map(([key]) => key)).size !== entries.length) return null;
  return entries.map(([value, label]) => ({ value: value!, label: label! }));
}
export function isSummary(value: unknown): value is AssessmentSummary {
  return record(value) && id(value.id) && typeof value.title === 'string' && nullableString(value.description) && typeof value.is_published === 'boolean' && natural(value.question_count) && typeof value.created_at === 'string' && typeof value.can_manage === 'boolean';
}
export function isAssessmentList(value: unknown): value is AssessmentSummary[] { return Array.isArray(value) && value.every(isSummary) && unique(value.map(item => item.id)); }
export function isQuestion(value: unknown): value is Question {
  return record(value) && typeof value.options_supported === 'boolean' && (value.content_metadata === null || record(value.content_metadata)) && Array.isArray(value.rubrics) && value.rubrics.every(isRubric) && id(value.id) && typeof value.question_text === 'string' && questionTypes.includes(value.question_type as QuestionType) && id(value.points) && nullableString(value.correct_answer) && (choicesFor(value as unknown as Question) !== null || value.options_supported === false); 
}
export function isRubric(value: unknown): value is Rubric {
  return record(value) && typeof value.name === 'string' && (value.description === undefined || nullableString(value.description)) && Array.isArray(value.criteria) && value.criteria.every(item => record(item) && typeof item.name === 'string' && nullableString(item.description) && id(item.max_points));
}
export function isAssessment(value: unknown, expectedId?: number): value is Assessment {
  return isSummary(value) && (expectedId === undefined || value.id === expectedId) && record(value) && Array.isArray(value.questions) && value.questions.every(isQuestion) && unique(value.questions.map(item => item.id)) && value.questions.length === value.question_count && (value.time_limit_minutes === null || id(value.time_limit_minutes)) && id(value.max_attempts) && gradingModes.includes(value.grading_mode as typeof gradingModes[number]) && natural(value.total_points) && natural(value.passing_score) && value.passing_score <= 100 && (value.rubric === null || isRubric(value.rubric));
}
export function isPolicy(value: unknown, assessmentId: number): value is Policy { return record(value) && value.assessment_id === assessmentId && assistanceModes.includes(value.mode as AssistanceMode); }
export function isSubmissionSummary(value: unknown): value is SubmissionSummary {
  return record(value) && id(value.id) && id(value.assessment_id) && id(value.student_id) && typeof value.assessment_title === 'string' && typeof value.student_name === 'string' && submissionStatuses.includes(value.status as SubmissionStatus) && (value.score === null || natural(value.score)) && (value.total_points === null || natural(value.total_points)) && nullableString(value.submitted_at) && nullableString(value.graded_at) && (value.can_manage === undefined || typeof value.can_manage === 'boolean');
}
export function isSubmissionList(value: unknown, ownerId?: number): value is SubmissionSummary[] {
  return Array.isArray(value) && value.every(item => isSubmissionSummary(item) && (ownerId === undefined || item.student_id === ownerId)) && unique(value.map(item => item.id));
}
export function isAnswerDetail(value: unknown): value is AnswerDetail {
  return record(value) && id(value.response_id) && id(value.question_id) && typeof value.question_text === 'string' && typeof value.question_type === 'string' && nullableString(value.given_answer) && nullableString(value.correct_answer) && (value.is_correct === null || typeof value.is_correct === 'boolean') && (value.points === null || natural(value.points)) && id(value.max_points) && (value.points === null || value.points <= value.max_points) && nullableString(value.feedback) && (value.ai_suggested_score === null || natural(value.ai_suggested_score) && value.ai_suggested_score <= value.max_points) && nullableString(value.ai_suggested_feedback) && nullableNumber(value.ai_confidence) && typeof value.teacher_override === 'boolean';
}
export function isSubmission(value: unknown, expectedId?: number, ownerId?: number): value is Submission {
  return isSubmissionSummary(value) && (expectedId === undefined || value.id === expectedId) && (ownerId === undefined || value.student_id === ownerId) && record(value) && nullableString(value.feedback) && Array.isArray(value.answers) && value.answers.every(isAnswerDetail) && unique(value.answers.map(item => item.response_id)) && unique(value.answers.map(item => item.question_id)) && (value.started_at === undefined || nullableString(value.started_at)) && (value.expires_at === undefined || nullableString(value.expires_at)) && (value.timing_provenance === undefined || typeof value.timing_provenance === 'string') && (value.time_limit_minutes === undefined || value.time_limit_minutes === null || id(value.time_limit_minutes));
}
export function isDraft(value: unknown, assessment: Assessment): value is AttemptDraft {
  if (!record(value) || !Array.isArray(value.answers) || !value.answers.every(item => record(item) && id(item.question_id) && typeof item.response_text === 'string' && item.response_text.length <= 2_000_000)) return false;
  const answers = value.answers as Answer[];
  return unique(answers.map(item => item.question_id)) && answers.every(answer => { const question = assessment.questions.find(item => item.id === answer.question_id); if (!question) return false; const choices = choicesFor(question); return choices !== null && (!answer.response_text || !['multiple_choice', 'true_false'].includes(question.question_type) || choices.some(choice => choice.value === answer.response_text)); });
}
export function isStats(value: unknown, assessmentId: number): value is Stats {
  return record(value) && value.assessment_id === assessmentId && natural(value.total_submissions) && ['average_score', 'highest_score', 'lowest_score', 'pass_rate'].every(key => nullableNumber(value[key]) && (value[key] === null || Number(value[key]) >= 0 && Number(value[key]) <= 100));
}
export function confirmStart(value: unknown): number {
  if (!record(value) || !id(value.submission_id) || value.id !== value.submission_id || value.status !== 'draft') throw invalidResponse(true);
  return value.submission_id;
}
export function confirmResult(value: unknown, submissionId: number, close: boolean): void {
  if (!record(value) || value.id !== submissionId || value.submission_id !== submissionId || !(close ? ['abandoned'] : ['submitted', 'ai_graded', 'graded']).includes(String(value.status)) || !(value.score === null || natural(value.score))) throw invalidResponse(true);
}
export function confirmOk(value: unknown): void { if (!record(value) || value.status !== 'ok') throw invalidResponse(true); }
export function validScore(value: string, maximum: number): number | null { if (!value.trim()) return null; const number = Number(value); return Number.isSafeInteger(number) && number >= 0 && number <= maximum ? number : null; }
export function finalizesQuestion(submission: Submission, responseId: number): boolean { return submission.answers.every(answer => answer.response_id === responseId || answer.points !== null); }
export function attemptDeadline(submission: Submission): number | null { return knownInstant(submission.expires_at, submission.timing_provenance); }
export function parsed<T>(data: unknown, validate: (value: unknown) => value is T): { data: T | undefined; error: ApiError | null } {
  if (data === undefined) return { data: undefined, error: null };
  return validate(data) ? { data, error: null } : { data: undefined, error: invalidResponse() };
}
