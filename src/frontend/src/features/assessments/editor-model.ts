import { record, choicesFor, gradingModes, questionTypes, type Assessment, type AssistanceMode, type QuestionType, type Rubric } from './model';
export interface EditableChoice { value: string; label: string }
export interface EditableQuestion { content_metadata: Record<string, unknown> | null; rubrics: Rubric[]; source_options: unknown; source_choices: EditableChoice[]; source_type: QuestionType; question_text: string; question_type: QuestionType; points: string; correct_answer: string; choices: EditableChoice[] }
export interface EditorValues { title: string; description: string; time_limit_minutes: string; max_attempts: string; passing_score: string; grading_mode: typeof gradingModes[number]; study_plan_id: string; topic_id: string; questions: EditableQuestion[]; rubric_name: string; rubric_description: string; criteria: { name: string; description: string; max_points: string }[] }
export const newQuestion = (): EditableQuestion => ({ content_metadata: null, rubrics: [], source_options: null, source_choices: [], source_type: 'multiple_choice', question_text: '', question_type: 'multiple_choice', points: '10', correct_answer: '', choices: [{ value: 'A', label: '' }, { value: 'B', label: '' }] });
export function editorValues(data?: Assessment, copy = false): EditorValues {
 return { title: data?.title || '', description: data?.description || '', time_limit_minutes: data?.time_limit_minutes?.toString() || '', max_attempts: String(data?.max_attempts ?? 1), passing_score: String(data?.passing_score ?? 70), grading_mode: data?.grading_mode || 'manual', study_plan_id: copy ? '' : data?.study_plan_id?.toString() || '', topic_id: copy ? '' : data?.topic_id?.toString() || '', questions: data ? data.questions.map(question => ({ content_metadata: question.content_metadata, rubrics: question.rubrics, source_options: question.options, source_choices: choicesFor(question)?.map(choice => ({ value: choice.value, label: choice.label })) || [], source_type: question.question_type, question_text: question.question_text, question_type: question.question_type, points: String(question.points), correct_answer: question.correct_answer || '', choices: choicesFor(question)?.map(choice => ({ value: choice.value, label: choice.label })) || [] })) : [newQuestion()], rubric_name: data?.rubric?.name || '', rubric_description: data?.rubric?.description || '', criteria: data?.rubric?.criteria.map(item => ({ name: item.name, description: item.description || '', max_points: String(item.max_points) })) || [] };
}
function integer(value: string, min: number, max: number) { const number = Number(value); return value.trim() && Number.isSafeInteger(number) && number >= min && number <= max ? number : null; }
export function editorPayload(values: EditorValues, metadataOnly = false) {
 const maxAttempts = integer(values.max_attempts, 1, 100);
 if (!values.title.trim() || maxAttempts === null) return null;
 const metadata = { title: values.title.trim(), description: values.description, max_attempts: maxAttempts };
 if (metadataOnly) return metadata;
 const passing = integer(values.passing_score, 0, 100); const time = values.time_limit_minutes.trim() ? integer(values.time_limit_minutes, 1, 1440) : null;
 if (passing === null || values.time_limit_minutes.trim() && time === null || !gradingModes.includes(values.grading_mode)) return null;
 const questions = [];
 for (const question of values.questions) {
  const points = integer(question.points, 1, 10000); if (!question.question_text.trim() || points === null || !questionTypes.includes(question.question_type)) return null;
  const objective = ['multiple_choice', 'true_false'].includes(question.question_type);
  if (objective && (question.choices.length < 2 || question.choices.some(choice => !choice.value.trim() || !choice.label.trim()) || new Set(question.choices.map(choice => choice.value.trim().toLocaleLowerCase())).size !== question.choices.length)) return null;
  if (objective && question.correct_answer && !question.choices.some(choice => choice.value.trim().toLocaleLowerCase() === question.correct_answer.trim().toLocaleLowerCase())) return null;
  questions.push({ content_metadata: question.content_metadata, rubrics: question.rubrics, question_text: question.question_text, question_type: question.question_type, points, correct_answer: question.correct_answer || null, options: objective ? question.source_type === question.question_type && question.source_choices.length > 0 && JSON.stringify(question.choices) === JSON.stringify(question.source_choices) ? question.source_options : { ...(record(question.source_options) && Object.hasOwn(question.source_options, 'choices') ? question.source_options : {}), choices: Object.fromEntries(question.choices.map(choice => [choice.value, choice.label])) } : null });
 }
 const criteria = [];
 for (const criterion of values.criteria) { const points = integer(criterion.max_points, 1, 10000); if (!criterion.name.trim() || points === null) return null; criteria.push({ name: criterion.name, description: criterion.description || null, max_points: points }); }
 if (criteria.length && !values.rubric_name.trim()) return null;
 const linkedIds: Record<string, number> = {};
 for (const key of ['study_plan_id', 'topic_id'] as const) { if (!values[key].trim()) continue; const value = integer(values[key], 1, Number.MAX_SAFE_INTEGER); if (value === null) return null; linkedIds[key] = value; }
 return { ...metadata, ...linkedIds, time_limit_minutes: time, passing_score: passing, grading_mode: values.grading_mode, is_published: false, questions, rubric: values.rubric_name.trim() ? { name: values.rubric_name, description: values.rubric_description || null, criteria } : null };
}
export function canPublish(values: EditorValues, policy: AssistanceMode | null): boolean { const payload = editorPayload(values); return !!policy && !!payload && 'questions' in payload && !!payload.questions.length && values.questions.every(question => !['multiple_choice', 'true_false'].includes(question.question_type) || !!question.correct_answer); }
/** Fresh provider output has no stored answer history; canonicalize only this ingress. */
function generatedMultipleChoice(options: unknown, answer: unknown) {
 const wrapped = record(options) && Object.hasOwn(options, 'choices');
 const source = wrapped ? options.choices : options;
 const entries: [string, unknown][] | null = Array.isArray(source) ? source.map((label, index) => [String(index + 1), label]) : record(source) ? Object.entries(source) : null;
 const normalized = (value: string) => value.trim().toLowerCase();
 // Match the fresh backend contract; two rounds also collapse capital sharp S aliases.
 const keyIdentity = (value: string) => value.trim().toUpperCase().toLowerCase().toUpperCase().toLowerCase();
 if (!entries || entries.length < 2 || entries.some(([key, label]) => !key.trim() || typeof label !== 'string' || !label.trim()) || new Set(entries.map(([key]) => keyIdentity(key))).size !== entries.length || answer == null || typeof answer === 'number' && !Number.isFinite(answer)) return null;
 const matches = entries.filter(([key, label]) => normalized(key) === normalized(String(answer)) || normalized(String(label)) === normalized(String(answer)));
 if (matches.length !== 1) return null;
 return { options: { choices: Object.fromEntries(entries) }, correct_answer: matches[0][0] };
}
/** Convert a fresh local generator proposal; stored legacy definitions use editorValues unchanged. */
export function generatedAssessment(raw: unknown): Assessment | null {
 if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
 const data = raw as Record<string, unknown>; if (typeof data.title !== 'string' || !Array.isArray(data.questions) || !data.questions.length) return null;
 const questions: Assessment['questions'] = [];
 const rubric = (value: unknown): Rubric | null => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  const input = value as Record<string, unknown>; if (input.name != null && typeof input.name !== 'string' || !Array.isArray(input.criteria) || !input.criteria.length) return null;
  const criteria = [];
  for (const row of input.criteria) { if (!row || typeof row !== 'object' || typeof row.name !== 'string' || !Number.isSafeInteger(row.max_points) || row.max_points <= 0 || row.max_points > 10000 || row.description != null && typeof row.description !== 'string') return null; criteria.push({ name: row.name, description: row.description ?? null, max_points: row.max_points }); }
  return { name: typeof input.name === 'string' && input.name.trim() ? input.name : 'Generated draft rubric', description: typeof input.description === 'string' ? input.description : null, criteria };
 };
 for (let index = 0; index < data.questions.length; index++) {
  const rawQuestion: unknown = data.questions[index]; if (!rawQuestion || typeof rawQuestion !== 'object' || Array.isArray(rawQuestion)) return null; const item = rawQuestion as Record<string, unknown>;
  const text = item.question_text ?? item.question; const kind = item.question_type ?? item.type ?? 'short_answer'; const points = item.points ?? 10;
  if (typeof text !== 'string' || !questionTypes.includes(kind as QuestionType) || typeof points !== 'number' || !Number.isSafeInteger(points) || points <= 0 || points > 10000 || item.correct_answer != null && !['string', 'number', 'boolean'].includes(typeof item.correct_answer)) return null;
  const canonical = kind === 'multiple_choice' ? generatedMultipleChoice(item.options, item.correct_answer) : null;
  if (kind === 'multiple_choice' && !canonical) return null;
  const options = canonical?.options ?? (Array.isArray(item.options) ? { choices: item.options } : item.options ?? null);
  if (options !== null && (typeof options !== 'object' || Array.isArray(options))) return null;
  const questionRubrics: Rubric[] = [];
  const rubricItems = Array.isArray(item.rubrics) ? item.rubrics : item.rubric ? [item.rubric] : [];
  for (const entry of rubricItems) { const parsed = rubric(entry); if (!parsed || parsed.criteria.reduce((total, criterion) => total + criterion.max_points, 0) !== points) return null; questionRubrics.push(parsed); }
  const metadata = item.content_metadata && typeof item.content_metadata === 'object' && !Array.isArray(item.content_metadata) ? item.content_metadata as Record<string, unknown> : {};
  const question = { id: index + 1, question_text: text, question_type: kind as QuestionType, points, options, correct_answer: canonical?.correct_answer ?? (item.correct_answer == null ? null : String(item.correct_answer)), content_metadata: { ...metadata, ...(Object.hasOwn(item, 'explanation') ? { explanation: item.explanation } : {}), ...(Object.hasOwn(item, 'hints') ? { hints: item.hints } : {}) }, rubrics: questionRubrics, options_supported: true };
  const choices = choicesFor(question); if (choices === null) return null;
  question.options_supported = !['multiple_choice', 'true_false'].includes(question.question_type) || choices.some(choice => choice.value.trim().toLocaleLowerCase() === question.correct_answer?.trim().toLocaleLowerCase());
  questions.push(question);
 }
 const globalRubric = data.rubric == null ? null : rubric(data.rubric); if (data.rubric != null && !globalRubric) return null;
 return { id: 1, title: data.title, description: typeof data.description === 'string' ? data.description : null, can_manage: true, is_published: false, question_count: questions.length, created_at: '', questions, time_limit_minutes: null, max_attempts: 1, grading_mode: 'ai_assisted', total_points: questions.reduce((total, question) => total + question.points, 0), passing_score: typeof data.passing_score === 'number' && Number.isInteger(data.passing_score) && data.passing_score >= 0 && data.passing_score <= 100 ? data.passing_score : 70, rubric: globalRubric };
}
export function generatedAssessmentValues(raw: unknown): EditorValues | null { const data = generatedAssessment(raw); return data ? editorValues(data, true) : null; }
