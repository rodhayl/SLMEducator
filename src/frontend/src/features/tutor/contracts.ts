import { ApiError } from '@/lib/api';
import { isMaterial, type Material } from '@/features/courses/contracts';
import { helpRecord, validHelpSource, type HelpSource } from '@/features/learning/help-contracts';
export { helpFingerprint, helpRecord, newHelpRequestId, validHelpPolicy, validHelpReceipt, validHelpUsage } from '@/features/learning/help-contracts';
export type { HelpPolicy, HelpReceipt, HelpUsage } from '@/features/learning/help-contracts';
export type Assistance = 'hint' | 'explanation';
export interface TutorSource extends HelpSource { type: string; included_characters: number; total_characters: number; fragment_hash: string; selection: 'bounded_default'|'explicit_sections'|'query_sections' }
export interface ChatInput { message: string; content_id: number|null; study_plan_id: number|null; section_ids: string[]; source_version: string|null; assistance: Assistance; conversation_history: {role:'user'|'assistant';content:string}[] }
export interface AnswerInput { question: string; assistance: Assistance }
export type AIInput = ChatInput | AnswerInput;
const natural = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
const hash = (value: unknown) => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
/** Matches the bounded canonical source, including Python's Unicode character counts. */
export function isTutorSource(value: unknown, id: number, course: boolean): value is TutorSource {
 if (!validHelpSource(value, id) || !helpRecord(value)) return false;
 const length = Array.from(value.content_data).length;
 return value.title.length <= 1000 && hash(value.source_version) && hash(value.fragment_hash) && length > 0 && length <= 6000 && value.included_characters === length && natural(value.total_characters) && value.total_characters >= length && value.truncated === (length < value.total_characters) && ['bounded_default','explicit_sections','query_sections'].includes(String(value.selection)) && (course ? value.type === 'course' : ['lesson','exercise','qa','assessment'].includes(String(value.type))) && value.available_sections.length <= 10000 && value.available_sections.every(section => section.id.length <= 200 && section.title.length <= 1000 && section.characters > 0 && section.characters <= 1800) && new Set(value.references).size === value.references.length;
}
export function responseError(mutation = false) { return new ApiError(0, 'invalid', mutation, mutation ? 'uncertain' : 'invalidResponse'); }
export interface QuestionSummary extends Material {content_type:'qa'; shared_with_teacher:boolean; can_edit?:boolean}
export interface Question extends QuestionSummary {content_data:Record<string,unknown> & {question?:string; answer?:string; content?:string}}
export function isQuestionSummary(value:unknown):value is QuestionSummary {return isMaterial(value) && value.content_type === 'qa' && 'shared_with_teacher' in value && typeof value.shared_with_teacher === 'boolean';}
export function isQuestionList(value:unknown):value is QuestionSummary[] {return Array.isArray(value) && value.every(isQuestionSummary) && new Set(value.map(item=>item.id)).size === value.length;}
export function isQuestion(value:unknown):value is Question {if(!isQuestionSummary(value) || !('content_data' in value) || !helpRecord(value.content_data))return false;const data=value.content_data;return ['question','answer','content'].every(key => data[key] === undefined || typeof data[key] === 'string') && ['question','content','answer'].some(key=>typeof data[key]==='string' && !!data[key].trim());}
