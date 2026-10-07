import { ApiError } from '@/lib/api';

export interface PracticeOption { key: string; text: string; booleanLabel?: 'true' | 'false' }
export interface PracticeQuestion { prompt: string; options: PracticeOption[]; hints: string[]; answer: string | null; explanation: string }
export interface PracticeDraft { answers: string[]; hints: number[]; fingerprint?: string }
export type AnnotationType = 'comment' | 'question' | 'highlight';
export interface AnnotationInput { content_id: number; annotation_text: string; annotation_type: AnnotationType; is_public: boolean; text_selection_start: null; text_selection_end: null }
export interface AnnotationRecord { id: number; content_id: number; user_id: number; user_name: string; annotation_text: string; annotation_type: string; is_public: boolean; text_selection_start: number | null; text_selection_end: number | null; created_at: string }
export interface AnnotationDeleteReceipt { status: 'ok'; message: 'Annotation deleted' }

const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value);
const id = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value > 0;
const scalar = (value: unknown): string | null => typeof value === 'string' || typeof value === 'boolean' || (typeof value === 'number' && Number.isFinite(value)) ? String(value) : null;
/** Preserve source option keys independently from the displayed answer text. */
export function practiceOptions(question: Record<string, unknown>): PracticeOption[] | null {
  const options = record(question.options) && question.options.choices != null ? question.options.choices : question.options;
  if (Array.isArray(options) || record(options)) {
    const entries = Array.isArray(options) ? options.map((value, index) => [String.fromCharCode(65 + index), value] as const) : Object.entries(options);
    if (entries.some(([, value]) => scalar(value) === null)) return null;
    return entries.map(([key, value]) => ({ key, text: scalar(value)! }));
  }
  if (options != null) return null;
  if (question.type === 'true_false' || question.question_type === 'true_false') return [{ key: 'true', text: 'True', booleanLabel: 'true' }, { key: 'false', text: 'False', booleanLabel: 'false' }];
  return [];
}
/** Treat malformed teacher/provider material as unavailable instead of inventing questions. */
export function normalizePractice(raw: unknown): PracticeQuestion[] | null {
  if (typeof raw === 'string') { try { raw = JSON.parse(raw); } catch { return null; } }
  if (!record(raw)) return null;
  const values = Array.isArray(raw.questions) ? raw.questions : [raw];
  if (!values.length) return null;
  const result: PracticeQuestion[] = [];
  for (const value of values) {
    if (!record(value)) return null;
    const prompt = value.question || value.question_text;
    const options = practiceOptions(value);
    if (typeof prompt !== 'string' || !prompt.trim() || !options) return null;
    const hints = (Array.isArray(value.hints) ? value.hints : [value.hint]).filter((hint): hint is string => typeof hint === 'string' && !!hint.trim());
    result.push({ prompt, options, hints, answer: scalar(value.correct_answer ?? value.answer), explanation: typeof value.explanation === 'string' ? value.explanation : '' });
  }
  return result;
}
/** Resolve a canonical answer key to its original option text; prose remains ungraded. */
export function practiceSolution(question: PracticeQuestion): string | null {
  if (question.answer === null) return null;
  return question.options.find(option => option.key.toLowerCase() === question.answer!.toLowerCase())?.text ?? question.answer;
}
/** A compact change detector, not authorization; never persist the lesson or answer key in a draft. */
export function practiceFingerprint(questions: PracticeQuestion[]): string {
  const value = JSON.stringify(questions); let hash = 2166136261;
  for (let index = 0; index < value.length; index++) hash = Math.imul(hash ^ value.charCodeAt(index), 16777619);
  return `${value.length}:${(hash >>> 0).toString(16)}`;
}
/** Older supported practice drafts have answer text and hint counts without a fingerprint. */
export function isPracticeDraft(value: unknown, questions: PracticeQuestion[]): value is PracticeDraft {
  if (!record(value) || !Array.isArray(value.answers) || !Array.isArray(value.hints) || value.answers.length !== questions.length || value.hints.length !== questions.length) return false;
  if (value.fingerprint !== undefined && value.fingerprint !== practiceFingerprint(questions)) return false;
  return value.answers.every((answer, index) => typeof answer === 'string' && (!answer || !questions[index].options.length || questions[index].options.some(option => option.text === answer))) && value.hints.every((count, index) => Number.isInteger(count) && count >= 0 && count <= Math.max(1, questions[index].hints.length));
}
export function isAnnotation(value: unknown): value is AnnotationRecord {
  if (!record(value)) return false;
  const offset = (entry: unknown) => entry === null || (typeof entry === 'number' && Number.isSafeInteger(entry) && entry >= 0);
  return id(value.id) && id(value.content_id) && id(value.user_id) && typeof value.user_name === 'string' && typeof value.annotation_text === 'string' && typeof value.annotation_type === 'string' && typeof value.is_public === 'boolean' && typeof value.created_at === 'string' && !!value.created_at && offset(value.text_selection_start) && offset(value.text_selection_end);
}
export function isAnnotationList(value: unknown, contentId: number): value is AnnotationRecord[] {
  return Array.isArray(value) && value.every(entry => isAnnotation(entry) && entry.content_id === contentId) && new Set(value.map(entry => entry.id)).size === value.length;
}
export function isAnnotationReceipt(value: unknown, input: AnnotationInput, ownerId: number): value is AnnotationRecord {
  return isAnnotation(value) && value.content_id === input.content_id && value.user_id === ownerId && value.annotation_text === input.annotation_text && value.annotation_type === input.annotation_type && value.is_public === input.is_public && value.text_selection_start === null && value.text_selection_end === null;
}
export function isAnnotationDeleteReceipt(value: unknown): value is AnnotationDeleteReceipt { return record(value) && value.status === 'ok' && value.message === 'Annotation deleted'; }
export function toolResponseError(mutation = false) { return new ApiError(200, 'invalid', mutation, mutation ? 'uncertain' : 'invalidResponse'); }
