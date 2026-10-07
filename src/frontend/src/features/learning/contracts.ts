import { ApiError } from '@/lib/api';

export const isRecord = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value);
const id = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value > 0;
const natural = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
export interface LearningContent { id: number; title: string; content_type: 'lesson' | 'exercise' | 'assessment' | 'qa'; content_data: Record<string, unknown> | string; source_selection?: unknown }
export interface StudySession { id: number; content_id: number; status: 'active' | 'completed' | 'failed' | 'closed'; start_time: string; notes: string | null; duration_minutes: number | null; timestamp_provenance: string; duration_known: boolean; content_snapshot: LearningContent | null; context_revision: Record<string, unknown> | null }
export interface StudyItem { id: number; title: string; content_type: string; phase_index: number; order_index: number }
export interface StudyTree { id: number; title: string; contents: StudyItem[] }
export interface StudyProgress { study_plan_id: number; completed_content_ids: number[]; last_content_id: number | null; total_contents: number; completion_percentage: number }
export interface NotesDraft { notes: string }
export function invalidResponse(mutation = false) { return new ApiError(0, 'invalid', mutation, mutation ? 'uncertain' : 'invalidResponse'); }
export function isLearningContent(value: unknown): value is LearningContent {
  return isRecord(value) && id(value.id) && typeof value.title === 'string' && ['lesson', 'exercise', 'assessment', 'qa'].includes(String(value.content_type)) && (typeof value.content_data === 'string' || isRecord(value.content_data));
}
export function isSession(value: unknown): value is StudySession {
  return isRecord(value) && id(value.id) && id(value.content_id) && ['active', 'completed', 'failed', 'closed'].includes(String(value.status)) && typeof value.start_time === 'string' && (value.notes === null || typeof value.notes === 'string') && (value.duration_minutes === null || natural(value.duration_minutes)) && typeof value.timestamp_provenance === 'string' && typeof value.duration_known === 'boolean' && (value.content_snapshot === null || (isLearningContent(value.content_snapshot) && value.content_snapshot.id === value.content_id)) && (value.context_revision === null || (isRecord(value.context_revision) && (value.context_revision.study_plan_id === undefined || value.context_revision.study_plan_id === null || id(value.context_revision.study_plan_id))));
}
export function sessionPlan(session: StudySession): number | null { const value = session.context_revision?.study_plan_id; return id(value) ? value : null; }
export function isSessionFor(value: unknown, contentId: number, planId: number | null, sessionId?: number): value is StudySession { return isSession(value) && value.content_id === contentId && sessionPlan(value) === planId && (sessionId === undefined || value.id === sessionId); }
export function isSessionList(value: unknown, contentId: number): value is StudySession[] { return Array.isArray(value) && value.every(item => isSession(item) && item.content_id === contentId) && new Set(value.map(item => item.id)).size === value.length; }
export function isStudyTree(value: unknown, planId: number): value is StudyTree {
  return isRecord(value) && value.id === planId && typeof value.title === 'string' && Array.isArray(value.contents) && value.contents.every(item => isRecord(item) && id(item.id) && typeof item.title === 'string' && typeof item.content_type === 'string' && natural(item.phase_index) && natural(item.order_index)) && new Set(value.contents.map(item => item.id)).size === value.contents.length;
}
export function isProgress(value: unknown, planId: number, completedId?: number): value is StudyProgress {
  return isRecord(value) && value.study_plan_id === planId && Array.isArray(value.completed_content_ids) && value.completed_content_ids.every(id) && new Set(value.completed_content_ids).size === value.completed_content_ids.length && (completedId === undefined || value.completed_content_ids.includes(completedId)) && (value.last_content_id === null || id(value.last_content_id)) && natural(value.total_contents) && value.completed_content_ids.length <= value.total_contents && (completedId === undefined || value.last_content_id === completedId) && typeof value.completion_percentage === 'number' && Number.isFinite(value.completion_percentage) && value.completion_percentage >= 0 && value.completion_percentage <= 100;
}
export function isNotesDraft(value: unknown): value is NotesDraft { return isRecord(value) && typeof value.notes === 'string' && value.notes.length <= 2_000_000; }
export function sessionHref(session: StudySession): string { return `/estudio/${session.id}?content_id=${session.content_id}${sessionPlan(session) ? `&plan_id=${sessionPlan(session)}` : ''}`; }
export function materialHref(contentId: number, planId: number | null): string { return `/materiales/${contentId}${planId ? `?plan_id=${planId}` : ''}`; }
export function contentData(content: LearningContent): Record<string, unknown> | string { if (typeof content.content_data !== 'string') return content.content_data; try { const parsed: unknown = JSON.parse(content.content_data); return isRecord(parsed) ? parsed : content.content_data; } catch { return content.content_data; } }
