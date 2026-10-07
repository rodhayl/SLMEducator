import { ApiError } from '@/lib/api';
import { isMaterial, type Material } from '@/features/courses/contracts';
import { practiceOptions } from '@/features/learning/tool-contracts';

export const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value);
export const text = (value: unknown): string => typeof value === 'string' ? value : '';
export const lines = (value: string): string[] => value.split('\n').map(line => line.trim()).filter(Boolean);
export const identifier = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value > 0;
export const hash = (value: unknown): value is string => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
export const responseError = (mutation = false) => new ApiError(0, 'invalid', mutation, mutation ? 'uncertain' : 'invalidResponse');
export const validationError = () => new ApiError(422, 'invalid', false, 'validation');
export interface AuthorMaterial extends Material { content_data: Record<string, unknown>; source_selection?: unknown }
export function isAuthorMaterial(value: unknown): value is AuthorMaterial { return isMaterial(value) && 'content_data' in value && record(value.content_data); }
export type MaterialKind = 'lesson' | 'exercise';
export const lessonTextFields = ['summary', 'worked_example', 'independent_attempt', 'feedback', 'delayed_review', 'prerequisite_check'] as const;
export interface MaterialForm {
 title: string; kind: MaterialKind; difficulty: number;
 sections: {title: string; content: string; source_clarification?: boolean}[];
 objectives: string; key_concepts: string; discussion_questions: string;
 vocabulary: {term: string; definition: string}[];
 summary: string; worked_example: string; independent_attempt: string; feedback: string; delayed_review: string; prerequisite_check: string;
 question: string; exerciseType: string; options: {key: string; value: string}[]; correctAnswer: string; explanation: string; hints: string;
}
export function materialForm(kind: MaterialKind, data: Record<string, unknown> = {}, title = '', difficulty = 1): MaterialForm {
 const sections = Array.isArray(data.sections) ? data.sections.filter(record).map(item => ({...item, title: text(item.title), content: text(item.content ?? item.text), ...(item.source_clarification === true ? {source_clarification: true} : {})})) : [];
 const body = text(data.content || data.body || data.text);
 if (body.trim() && body.trim() !== sections.map(item => item.content).join('\n\n').trim()) sections.unshift({title: '', content: body});
 const list = (key: string) => Array.isArray(data[key]) ? data[key].filter(item => typeof item === 'string').join('\n') : '';
 const options = (practiceOptions(data) || []).map(item => ({key: item.key, value: item.text}));
 const answer = String(data.correct_answer ?? data.answer ?? '');
 const keyMatch = options.find(option => option.key.toLowerCase() === answer.toLowerCase()), textMatches = options.filter(option => option.value.toLowerCase() === answer.toLowerCase());
 return {
  title: title || text(data.title), kind, difficulty, sections: sections.length ? sections : [{title: '', content: ''}],
  objectives: list('objectives'), key_concepts: list('key_concepts'), discussion_questions: list('discussion_questions'),
  vocabulary: Array.isArray(data.vocabulary) ? data.vocabulary.filter(record).map(item => ({term: text(item.term), definition: text(item.definition)})) : [],
  summary: text(data.summary), worked_example: text(data.worked_example), independent_attempt: text(data.independent_attempt), feedback: text(data.feedback), delayed_review: text(data.delayed_review), prerequisite_check: text(data.prerequisite_check),
  question: text(data.question || data.question_text), exerciseType: text(data.type || data.question_type) || 'short_answer', options,
  correctAnswer: keyMatch?.key ?? (textMatches.length === 1 ? textMatches[0]!.key : answer),
  explanation: text(data.explanation), hints: Array.isArray(data.hints) ? list('hints') : text(data.hint),
 };
}
export function materialPayload(form: MaterialForm, original: Record<string, unknown> = {}) {
 if (!form.title.trim() || form.title.length > 200 || !Number.isInteger(form.difficulty) || form.difficulty < 1 || form.difficulty > 10) throw validationError();
 const data = {...original};
 if (form.kind === 'lesson') {
  if (!form.sections.some(section => section.content.trim())) throw validationError();
  for (const key of ['content', 'body', 'text']) delete data[key];
  data.sections = form.sections.map(section => ({...section}));
  for (const key of lessonTextFields) data[key] = form[key];
  for (const key of ['objectives', 'key_concepts', 'discussion_questions'] as const) data[key] = lines(form[key]);
  data.vocabulary = form.vocabulary.map(entry => ({...entry}));
 } else {
  if (!form.question.trim() || !form.correctAnswer.trim()) throw validationError();
  if (form.exerciseType === 'multiple_choice' && (form.options.length < 2 || form.options.some(item => !item.key.trim() || !item.value.trim()) || new Set(form.options.map(item => item.key)).size !== form.options.length || !form.options.some(item => item.key === form.correctAnswer))) throw validationError();
  if (form.exerciseType === 'true_false' && !['true', 'false'].includes(form.correctAnswer.toLowerCase())) throw validationError();
  for (const key of ['answer', 'question_text', 'question_type', 'hint', 'options']) delete data[key];
  Object.assign(data, {question: form.question, type: form.exerciseType, correct_answer: form.correctAnswer, explanation: form.explanation, hints: lines(form.hints)});
  if (form.exerciseType === 'multiple_choice') data.options = Object.fromEntries(form.options.map(option => [option.key, option.value]));
 }
 return {title: form.title.trim(), difficulty: form.difficulty, content_type: form.kind, content_data: data};
}
export function confirmedMaterial(value: unknown, payload: ReturnType<typeof materialPayload>, owner: number, existing?: AuthorMaterial): value is Material {
 return isMaterial(value) && value.title === payload.title && value.content_type === payload.content_type && value.difficulty === payload.difficulty && value.creator_id === (existing ? existing.creator_id : owner) && (!existing || value.id === existing.id);
}

export interface SourceInput {filename: string; extracted_text: string; sections: {reference: string; text: string}[]; source_version: string | null; parser: string | null; coverage: 'complete'|'partial'|'unknown'; truncated: boolean; unreadable_pages: number[]; total_pages: number|null}
export interface SourceDocument {document_id: string; filename: string; extracted_text: string; sections: {reference: string; text: string}[]; original_bytes_hash: string|null; parser: string|null; extraction_coverage: 'complete'|'partial'|'unknown'; truncated: boolean; unreadable_pages: number[]; total_pages: number|null; provenance: string; original_binary_included: false; metadata_revision?: string}
export function isSections(value: unknown): value is SourceInput['sections'] { return Array.isArray(value) && value.length <= 1000 && value.every(item => record(item) && typeof item.reference === 'string' && item.reference.length > 0 && item.reference.length <= 120 && typeof item.text === 'string') && new Set(value.map(item => item.reference)).size === value.length; }
function sourceFields(value: Record<string,unknown>): boolean { return typeof value.filename === 'string' && value.filename.length <= 255 && typeof value.extracted_text === 'string' && value.extracted_text.length <= 100000 && !!value.extracted_text.trim() && isSections(value.sections) && typeof value.truncated === 'boolean' && Array.isArray(value.unreadable_pages) && value.unreadable_pages.every(identifier) && (value.total_pages === null || (Number.isInteger(value.total_pages) && Number(value.total_pages) >= 0)); }
export function isSourceInput(value: unknown): value is SourceInput { return record(value) && sourceFields(value) && (value.source_version === null || hash(value.source_version)) && (value.parser === null || typeof value.parser === 'string') && ['complete','partial','unknown'].includes(String(value.coverage)) && (!Array.isArray(value.sections) || !value.sections.length || value.extracted_text === (value.sections as SourceInput['sections']).map(part => `[${part.reference}]\n${part.text}`).join('\n\n')); }
export function isSourceDocument(value: unknown): value is SourceDocument { return record(value) && sourceFields(value) && (value.parser === null || typeof value.parser === 'string') && ['reported_extraction','authored_or_legacy_text'].includes(String(value.provenance)) && hash(value.document_id) && (value.original_bytes_hash === null || hash(value.original_bytes_hash)) && ['complete','partial','unknown'].includes(String(value.extraction_coverage)) && value.original_binary_included === false; }
export function sourceInput(source: SourceDocument): SourceInput { return {filename: source.filename, extracted_text: source.extracted_text, sections: source.provenance === 'authored_or_legacy_text' ? [] : source.sections, source_version: source.original_bytes_hash, parser: source.parser, coverage: source.extraction_coverage, truncated: source.truncated, unreadable_pages: source.unreadable_pages, total_pages: source.total_pages}; }
export function authoredSource(filename: string, extracted_text: string): SourceInput { return {filename, extracted_text, sections: [], source_version: null, parser: null, coverage: 'unknown', truncated: false, unreadable_pages: [], total_pages: null}; }
export function isSourceReceipt(value: unknown, expectedText: string): value is {source: SourceDocument; document_id: string; review_required: true} { return record(value) && isSourceDocument(value.source) && value.source.extracted_text === expectedText && value.document_id === value.source.document_id && value.review_required === true; }

export type GenerationMode = 'lesson'|'exercise'|'plan'|'outline'|'package';
export interface GenerationForm {mode: GenerationMode; subject: string; topic: string; grade: string; objectives: string; weeks: number; minutes: number; difficulty: string; exerciseType: string; lesson: boolean; exercises: boolean; assessment: boolean; exerciseCount: number; questionCount: number; questionType: string; autoSave: boolean; planId: string; phase: number}
export const generationDefaults: GenerationForm = {mode: 'package', subject: '', topic: '', grade: '', objectives: '', weeks: 4, minutes: 30, difficulty: 'medium', exerciseType: 'multiple_choice', lesson: true, exercises: true, assessment: false, exerciseCount: 4, questionCount: 5, questionType: 'mixed', autoSave: true, planId: '', phase: 0};
export function generationRequest(form: GenerationForm, source: SourceDocument|null) {
 if (!form.subject.trim() || !form.grade.trim() || !['lesson','exercise','plan','outline','package'].includes(form.mode)) throw validationError();
 const sourceText = source?.extracted_text || undefined, objectives = lines(form.objectives);
 if (['plan','outline'].includes(form.mode) && (!Number.isInteger(form.weeks) || form.weeks < 1 || form.weeks > 104)) throw validationError();
 if (form.mode === 'plan') return {path: '/api/generate/study-plan', body: {subject: form.subject, grade_level: form.grade, objectives, duration_weeks: form.weeks}};
 if (form.mode === 'outline') return {path: '/api/generate/course-outline', body: {subject: form.subject, grade_level: form.grade, duration_weeks: form.weeks, source_material: sourceText}};
 if (!form.topic.trim()) throw validationError();
 if (form.mode === 'lesson') {
  if (!Number.isInteger(form.minutes) || form.minutes < 1 || form.minutes > 240) throw validationError();
  return {path: '/api/generate/lesson', body: {topic: form.topic, grade_level: form.grade, learning_objectives: objectives, duration_minutes: form.minutes, source_material: sourceText}};
 }
 if (!['easy','medium','hard'].includes(form.difficulty)) throw validationError();
 if (form.mode === 'exercise') {
  if (!['multiple_choice','true_false','short_answer'].includes(form.exerciseType)) throw validationError();
  return {path: '/api/generate/exercise', body: {topic: form.topic, grade_level: form.grade, learning_objectives: objectives, difficulty: form.difficulty, exercise_type: form.exerciseType, source_material: sourceText}};
 }
 if (!Number.isInteger(form.exerciseCount) || form.exerciseCount < 0 || form.exerciseCount > 12 || !Number.isInteger(form.questionCount) || form.questionCount < 1 || form.questionCount > 20 || !['mixed','multiple_choice','true_false','short_answer','long_answer','fill_in_blank'].includes(form.questionType)) throw validationError();
 const planId = /^\d+$/.test(form.planId) ? Number(form.planId) : null;
 if ((!form.lesson && (!form.exercises || form.exerciseCount === 0) && !form.assessment) || (form.autoSave && !identifier(planId)) || form.phase < 0 || form.phase > 100 || !Number.isInteger(form.phase)) throw validationError();
 return {path: '/api/generate/full-topic-package', body: {subject: form.subject, topic_name: form.topic, grade_level: form.grade, learning_objectives: objectives, include_lesson: form.lesson, include_exercises: form.exercises, include_assessment: form.assessment, num_exercises: form.exerciseCount, exercise_difficulty: form.difficulty, num_assessment_questions: form.questionCount, assessment_difficulty: form.difficulty, assessment_question_types: form.questionType === 'mixed' ? null : [form.questionType], auto_save: form.autoSave, study_plan_id: planId, phase_index: form.phase, source_material: sourceText, source_document_id: source?.document_id || null}};
}
export interface GenerationItem {key: string; status: 'ready'|'running'|'failed'|'cancelled'; content_id?: number; assessment_id?: number|null; error_code?: string}
export interface PackageResult {success: boolean; topic_name: string; lesson: Record<string,unknown>|null; exercises: Record<string,unknown>[]|null; assessment: Record<string,unknown>|null; saved_content_ids: number[]; items: GenerationItem[]; job_key: string}
export function isGenerationItem(value: unknown): value is GenerationItem { return record(value) && typeof value.key === 'string' && /^(lesson|assessment|exercise-\d+)$/.test(value.key) && ['ready','running','failed','cancelled'].includes(String(value.status)) && (value.content_id === undefined || identifier(value.content_id)) && (value.assessment_id === undefined || value.assessment_id === null || identifier(value.assessment_id)); }
export function isPackage(value: unknown, saved: boolean): value is PackageResult {
 if (!record(value) || typeof value.success !== 'boolean' || typeof value.topic_name !== 'string' || !hash(value.job_key) || !Array.isArray(value.items) || !value.items.length || !value.items.every(isGenerationItem) || new Set(value.items.map(item => item.key)).size !== value.items.length || !Array.isArray(value.saved_content_ids) || !value.saved_content_ids.every(identifier)) return false;
 const confirmed = value.items.filter(item => item.status === 'ready' && identifier(item.content_id)).map(item => item.content_id);
 return new Set(value.saved_content_ids).size === value.saved_content_ids.length && new Set(confirmed).size === confirmed.length && value.success === value.items.every(item => item.status === 'ready') && (!saved || value.items.filter(item => item.status === 'ready').every(item => identifier(item.content_id))) && value.saved_content_ids.length === confirmed.length && value.saved_content_ids.every(item => confirmed.includes(item)) && (value.lesson === null || record(value.lesson)) && (value.exercises === null || (Array.isArray(value.exercises) && value.exercises.every(record))) && (value.assessment === null || record(value.assessment));
}
export function isPackageFor(value:unknown, form:GenerationForm): value is PackageResult {
 if(!isPackage(value,form.autoSave)||value.topic_name!==form.topic)return false;
 const keys=[...(form.lesson?['lesson']:[]),...(form.exercises?Array.from({length:form.exerciseCount},(_,index)=>`exercise-${index}`):[]),...(form.assessment?['assessment']:[])];
 return value.items.length===keys.length&&value.items.every(item=>keys.includes(item.key));
}
export interface GenerationJob {items: Record<string,Omit<GenerationItem,'key'>>; phase_index?: number; source_document_id?: string|null; obsolete_source?: boolean; cancel_requested?: boolean}
export function isJobs(value: unknown): value is {jobs: Record<string,GenerationJob>} { return record(value) && record(value.jobs) && Object.entries(value.jobs).every(([key, job]) => hash(key) && record(job) && record(job.items) && Object.entries(job.items).every(([itemKey,item]) => record(item) && isGenerationItem({...item,key:itemKey}))); }
export interface Outline {title: string; description: string; units: {title: string; lessons: {title: string; learning_objectives: string[]; selected: boolean}[]}[]}
export function outlineFrom(value: unknown, mode: 'plan'|'outline'): Outline|null {
 if (!record(value) || !text(value.title).trim() || text(value.title).length > 200) return null;
 const units = mode === 'outline' ? value.units : value.phases;
 if (!Array.isArray(units) || !units.length || units.length > 101) return null;
 const result: Outline = {title: text(value.title), description: text(value.description), units: []};
 for (const unit of units) {
  if (!record(unit) || !text(unit.title || unit.name).trim()) return null;
  const lessons = mode === 'outline' ? unit.lessons : unit.topics;
  if (lessons !== undefined && !Array.isArray(lessons)) return null;
  const items: Outline['units'][number]['lessons'] = [];
  for (const item of (Array.isArray(lessons) ? lessons : [])) {
   if (typeof item === 'string' && item.trim()) items.push({title:item,learning_objectives:[],selected:true});
   else if (record(item) && text(item.title || item.name).trim()) items.push({title:text(item.title || item.name),learning_objectives: Array.isArray(item.learning_objectives) ? item.learning_objectives.filter((entry): entry is string => typeof entry === 'string') : [], selected:true});
   else return null;
  }
  result.units.push({title: text(unit.title || unit.name), lessons: items});
 }
 return result;
}
export function outlinePayload(outline: Outline) { if (!outline.title.trim() || outline.title.length > 200 || !outline.units.length || outline.units.some(unit => !unit.title.trim())) throw validationError(); return {title: outline.title, description: outline.description, is_public: false, phases: outline.units.map(unit => ({name:unit.title,content_ids:[]}))}; }
export interface GenerationDraft {form: GenerationForm; outline: Outline|null; createdPlanId: number|null; outlineSource?: SourceDocument|null; outlineSourcePlanId?: number|null; recoveredSource?: SourceInput|null}
export function isGenerationDraft(value: unknown): value is GenerationDraft {
 if (!record(value) || !record(value.form) || value.recoveredSource != null && !isSourceInput(value.recoveredSource) || (value.createdPlanId !== null && !identifier(value.createdPlanId)) || (value.outlineSource !== undefined && value.outlineSource !== null && (!isSourceDocument(value.outlineSource)||!identifier(value.outlineSourcePlanId)))) return false;
 const form = value.form;
 if (!Object.entries(generationDefaults).every(([key,item])=>typeof form[key]===typeof item) || !['lesson','exercise','plan','outline','package'].includes(String(form.mode)) || (form.planId !== '' && (typeof form.planId !== 'string' || !/^[1-9]\d*$/.test(form.planId) || !identifier(Number(form.planId))))) return false;
 if (value.outline === null) return true;
 if (!record(value.outline) || typeof value.outline.title!=='string' || value.outline.title.length>200 || typeof value.outline.description!=='string' || !Array.isArray(value.outline.units) || value.outline.units.length>101) return false;
 return value.outline.units.every(unit=>record(unit)&&typeof unit.title==='string'&&Array.isArray(unit.lessons)&&unit.lessons.length<=1001&&unit.lessons.every(lesson=>record(lesson)&&typeof lesson.title==='string'&&typeof lesson.selected==='boolean'&&Array.isArray(lesson.learning_objectives)&&lesson.learning_objectives.every(item=>typeof item==='string')));
}
