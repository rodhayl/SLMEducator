import { ApiError } from '@/lib/api';
import type { User } from '@/lib/types';

export interface CourseSummary { id: number; creator_id?: number | null; title: string; description: string | null; is_public: boolean; created_at: string }
export interface CourseItem { id: number; title: string; content_type: string; difficulty: number; phase_index: number; order_index: number; created_at: string }
export interface CourseTree extends CourseSummary { phases: { name?: string; title?: string; content_ids?: number[] }[]; contents: CourseItem[]; content_count: number }
export interface CourseWorkflow { status: 'draft' | 'reviewed' | 'published'; version: number; read_only: boolean }
export interface Material { id: number; title: string; content_type: string; difficulty: number; is_personal: boolean; creator_id: number | null; can_edit?: boolean; public_reuse?: boolean }
export interface Student { id: number; username: string; first_name: string; last_name: string; teacher_id: number | null }
export interface CourseForm { title: string; description: string; phases: { name: string; content_ids: number[] }[] }
export interface AssignmentReceipt { study_plan_id: number; assigned_student_ids: number[]; already_assigned_student_ids: number[] }
export interface CourseProgress { study_plan_id: number; completed_content_ids: number[]; last_content_id: number | null; completion_percentage: number }
const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value);
const integer = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
const id = (value: unknown): value is number => integer(value) && value > 0;
const ids = (value: unknown): value is number[] => Array.isArray(value) && value.every(id) && new Set(value).size === value.length;
export function invalidResponse(mutation = false): ApiError { return new ApiError(0, 'invalid', mutation, mutation ? 'uncertain' : 'invalidResponse'); }
export function isCourse(value: unknown): value is CourseSummary {
  return record(value) && id(value.id) && typeof value.title === 'string' && (value.description === null || typeof value.description === 'string') && typeof value.is_public === 'boolean' && typeof value.created_at === 'string' && (value.creator_id === undefined || value.creator_id === null || id(value.creator_id));
}
export function isCourseList(value: unknown): value is CourseSummary[] { return Array.isArray(value) && value.every(isCourse); }
export function isCourseTree(value: unknown): value is CourseTree {
  if (!isCourse(value) || !('phases' in value) || !('contents' in value) || !('content_count' in value)) return false;
  return Array.isArray(value.phases) && value.phases.length <= 101 && value.phases.every(p => record(p) && (p.name === undefined || typeof p.name === 'string') && (p.title === undefined || typeof p.title === 'string')) && Array.isArray(value.contents) && value.contents.every(c => record(c) && id(c.id) && typeof c.title === 'string' && typeof c.content_type === 'string' && integer(c.phase_index) && c.phase_index <= 100 && integer(c.order_index) && c.order_index <= 1000) && new Set(value.contents.map(c => c.id)).size === value.contents.length && integer(value.content_count) && value.content_count === value.contents.length;
}
export function isWorkflow(value: unknown): value is CourseWorkflow { return record(value) && ['draft', 'reviewed', 'published'].includes(String(value.status)) && integer(value.version) && typeof value.read_only === 'boolean'; }
export function isWorkflowReceipt(value: unknown, status: string): value is {status: string; version: number} { return record(value) && value.status === status && integer(value.version); }
export function isMaterial(value: unknown): value is Material { return record(value) && id(value.id) && typeof value.title === 'string' && ['lesson', 'exercise', 'assessment', 'qa'].includes(String(value.content_type)) && integer(value.difficulty) && value.difficulty >= 1 && value.difficulty <= 10 && typeof value.is_personal === 'boolean' && (value.creator_id === null || id(value.creator_id)); }
export function isMaterialList(value: unknown): value is Material[] { return Array.isArray(value) && value.every(isMaterial); }
export function isStudents(value: unknown): value is Student[] { return Array.isArray(value) && value.every(s => record(s) && id(s.id) && typeof s.username === 'string' && typeof s.first_name === 'string' && typeof s.last_name === 'string' && (s.teacher_id === null || id(s.teacher_id))); }
export function canReuse(material: Material, user: User): boolean { return !material.is_personal && (user.role === 'admin' || (user.role === 'teacher' && (material.creator_id === user.id || material.public_reuse === true))); }
/** Visibility of reused material depends on its original author, not an admin's editing privilege. */
export function canAttachMaterial(material: Material, user: User, courseCreatorId: number | null): boolean { return canReuse(material, user) && (material.public_reuse === true || (courseCreatorId !== null && material.creator_id === courseCreatorId)); }
export function isAssignment(value: unknown, planId: number, requested: number[]): value is AssignmentReceipt {
  if (!record(value) || value.study_plan_id !== planId || !ids(value.assigned_student_ids) || !ids(value.already_assigned_student_ids)) return false;
  const received = [...value.assigned_student_ids, ...value.already_assigned_student_ids];
  return received.length === requested.length && new Set(received).size === requested.length && requested.every(item => received.includes(item));
}
export function isProgress(value: unknown, planId: number): value is CourseProgress { return record(value) && value.study_plan_id === planId && ids(value.completed_content_ids) && (value.last_content_id === null || id(value.last_content_id)) && typeof value.completion_percentage === 'number' && Number.isFinite(value.completion_percentage) && value.completion_percentage >= 0 && value.completion_percentage <= 100; }
export function isCourseForm(value: unknown): value is CourseForm {
  if (!record(value) || typeof value.title !== 'string' || value.title.length > 200 || typeof value.description !== 'string' || !Array.isArray(value.phases) || value.phases.length > 101) return false;
  const all: number[] = [];
  for (const phase of value.phases) { if (!record(phase) || typeof phase.name !== 'string' || !ids(phase.content_ids) || phase.content_ids.length > 1001) return false; all.push(...phase.content_ids); }
  return new Set(all).size === all.length;
}
/** Association positions, rather than stale phase.content_ids, are authoritative. */
export function courseForm(tree: CourseTree): CourseForm {
  const count = Math.max(tree.phases.length, ...tree.contents.map(item => item.phase_index + 1), 1);
  return { title: tree.title, description: tree.description ?? '', phases: Array.from({length: count}, (_, index) => ({ name: tree.phases[index]?.name || tree.phases[index]?.title || '', content_ids: tree.contents.filter(item => item.phase_index === index).sort((a, b) => a.order_index - b.order_index).map(item => item.id) })) };
}
export function coursePayload(form: CourseForm) {
  if (!isCourseForm(form) || !form.title.trim() || form.phases.some(phase => !phase.name.trim())) throw new ApiError(422, 'invalid', false, 'validation');
  return { title: form.title.trim(), description: form.description, is_public: false, phases: form.phases.map(phase => ({name: phase.name.trim(), content_ids: [...phase.content_ids]})) };
}
export function materialHref(materialId: number, planId: number): string { return `/materiales/${materialId}?plan_id=${planId}`; }
export function moveItem(items: number[], index: number, direction: -1 | 1): number[] {
  const destination = index + direction, copy = [...items];
  if (index < 0 || destination < 0 || index >= copy.length || destination >= copy.length) return copy;
  [copy[index], copy[destination]] = [copy[destination]!, copy[index]!]; return copy;
}
