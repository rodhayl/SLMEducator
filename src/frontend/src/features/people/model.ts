import { ApiError } from '@/lib/api';
import { positiveId } from '@/lib/ids';
import type { Role, User } from '@/lib/types';

/** Canonical roles serialized by UserRole and /api/auth. */
export const accountRoles = ['student', 'teacher', 'admin'] as const satisfies readonly Role[];
export const PEOPLE_LIMIT = 500;
export interface Person extends User { active: boolean; teacher_id: number | null }
export interface StudentProgress {
  lessons_completed: number; assessments_taken: number; avg_score: number | null;
  study_time_hours: number; time_measure: 'elapsed_completed_session_time';
}
export interface CreateValues {
  first_name: string; last_name: string; username: string; email: string;
  password: string; role: Role | '';
}
export type CreatePayload = Omit<CreateValues, 'role'> & { role: Role; teacher_id?: number };

function record(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown> : null;
}
function invalid(mutation = false): never {
  throw new ApiError(200, 'invalid', mutation, mutation ? 'uncertain' : 'invalidResponse');
}
export function isRole(value: unknown): value is Role {
  return accountRoles.some(role => role === value);
}
/** Whitelist fields so secrets or arbitrary extra server fields never reach UI/cache output. */
export function parsePerson(value: unknown, mutation = false): Person {
  const data = record(value);
  if (!data || !positiveId(data.id) || !isRole(data.role) ||
      typeof data.username !== 'string' || !data.username ||
      typeof data.first_name !== 'string' || typeof data.last_name !== 'string' ||
      typeof data.email !== 'string' || typeof data.active !== 'boolean' ||
      (data.teacher_id !== null && !positiveId(data.teacher_id))) return invalid(mutation);
  return {
    id: Number(data.id), username: data.username, email: data.email, role: data.role,
    first_name: data.first_name, last_name: data.last_name, active: data.active,
    teacher_id: data.teacher_id === null ? null : Number(data.teacher_id),
    grade_level: typeof data.grade_level === 'string' ? data.grade_level : null,
  };
}
export function parsePersonDetail(value: unknown, expectedId: number): Person {
  const person = parsePerson(value);
  if (person.id !== expectedId) return invalid();
  return person;
}
export function parsePeople(value: unknown): Person[] {
  if (!Array.isArray(value)) return invalid();
  const people = value.map(item => parsePerson(item));
  if (new Set(people.map(person => person.id)).size !== people.length) return invalid();
  return people;
}
export function parseCreated(value: unknown, payload: CreatePayload): Person {
  const person = parsePerson(value, true);
  if (person.role !== payload.role || person.username !== payload.username ||
      person.teacher_id !== (payload.teacher_id ?? null) || !person.active) return invalid(true);
  return person;
}
export function createPayload(values: CreateValues, actor: User): CreatePayload {
  if (actor.role !== 'admin' && actor.role !== 'teacher') throw new ApiError(403, 'http', false, 'forbidden');
  const role = actor.role === 'teacher' ? 'student' : values.role;
  if (!isRole(role)) throw new ApiError(422, 'http', false, 'invalidRole');
  return { ...values, role, ...(actor.role === 'teacher' ? { teacher_id: actor.id } : {}) };
}
export function peoplePath(role: Role | '', includeInactive: boolean): string {
  const params = new URLSearchParams({ limit: String(PEOPLE_LIMIT) });
  if (role) params.set('role', role);
  if (includeInactive) params.set('include_inactive', 'true');
  return `/api/auth/users?${params}`;
}
export function personName(person: Pick<User, 'first_name' | 'last_name' | 'username'>): string {
  return `${person.first_name} ${person.last_name}`.trim() || person.username;
}
/** Client preflight accepts Unicode numbers; Python isdigit remains authoritative. */
export function validPassword(value: string, minimum: 8 | 12): boolean {
  return [...value].length >= minimum && new TextEncoder().encode(value).length <= 72 &&
    /\p{Uppercase}/u.test(value) && /\p{Lowercase}/u.test(value) && /\p{Number}/u.test(value) &&
    [...value].some(char => '!@#$%^&*()_+-=[]{}|;:,.<>?'.includes(char));
}
export function parseProgress(value: unknown): StudentProgress {
  const data = record(value);
  const nonnegative = (n: unknown): n is number => typeof n === 'number' && Number.isFinite(n) && n >= 0;
  if (!data || !nonnegative(data.lessons_completed) || !nonnegative(data.assessments_taken) ||
      !nonnegative(data.study_time_hours) || (data.avg_score !== null && !nonnegative(data.avg_score)) ||
      data.time_measure !== 'elapsed_completed_session_time') return invalid();
  return { lessons_completed: data.lessons_completed, assessments_taken: data.assessments_taken,
    avg_score: data.avg_score, study_time_hours: data.study_time_hours, time_measure: data.time_measure };
}
export function parseNotes(value: unknown): string {
  const data = record(value);
  return data && typeof data.notes === 'string' ? data.notes : invalid();
}
export function confirmNotes(value: unknown): void {
  if (record(value)?.success !== true) invalid(true);
}
export function confirmEnrollment(value: unknown, studentId: number, teacherId: number | null): void {
  const data = record(value);
  if (!data || data.student_id !== studentId || data.teacher_id !== teacherId ||
      data.existing_assignments_preserved !== true) invalid(true);
}
export function confirmStatus(value: unknown, id: number, active: boolean): void {
  const data = record(value);
  if (!data || data.id !== id || data.active !== active || data.sessions_revoked !== true) invalid(true);
}
export function confirmRecovery(value: unknown, id: number): void {
  const data = record(value);
  if (!data || data.id !== id || data.reset !== true || data.sessions_revoked !== true) invalid(true);
}
export function validationResult<T>(value: unknown, parse: (data: unknown) => T): { data: T | null; error: ApiError | null } {
  if (value === undefined) return { data: null, error: null };
  try { return { data: parse(value), error: null }; }
  catch { return { data: null, error: new ApiError(200, 'invalid', false, 'invalidResponse') }; }
}
