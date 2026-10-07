import { describe, expect, it } from 'vitest';
import { ApiError } from '@/lib/api';
import { locales } from '@/features/people/locales';
import { accountRoles, confirmEnrollment, confirmNotes, confirmRecovery, confirmStatus, createPayload, parseCreated, parseNotes, parsePeople, parsePerson, parsePersonDetail, parseProgress, peoplePath, validPassword } from '@/features/people/model';
import type { CreateValues } from '@/features/people/model';
import type { User } from '@/lib/types';
const actor: User = { id: 2, role: 'teacher', username: 'teacher', email: 'teacher@example.com', first_name: 'Teacher', last_name: 'Example' };
const person = { ...actor, id: 3, role: 'student', username: 'learner', active: true, teacher_id: 2 };
const values: CreateValues = { username: 'learner', email: 'learner@example.com', first_name: 'Learner', last_name: 'Example', role: 'admin', password: 'Synthetic123!' };
describe('verified People API models', () => {
  it('uses the real three roles and makes teacher ownership non-editable', () => {
    expect(accountRoles).toEqual(['student', 'teacher', 'admin']);
    expect(createPayload(values, actor)).toMatchObject({ role: 'student', teacher_id: 2 });
    expect(() => createPayload(values, { ...actor, role: 'student' })).toThrow(ApiError);
    expect(createPayload(values, { ...actor, role: 'admin' })).not.toHaveProperty('teacher_id');
    expect(() => createPayload({ ...values, role: '' }, { ...actor, role: 'admin' })).toThrow(ApiError);
  });
  it('validates and strips responses before claiming creation', () => {
    const payload = createPayload(values, actor);
    expect(parseCreated({ ...person, password: 'never-propagate', settings: { other: true } }, payload)).not.toHaveProperty('password');
    expect(parsePerson(person)).not.toHaveProperty('settings');
    expect(() => parsePersonDetail(person, 99)).toThrow(ApiError);
    for (const bad of [{}, { ...person, role: 'root' }, { ...person, teacher_id: -1 }, { ...person, id: 0 }, { ...person, active: 'yes' }]) expect(() => parsePerson(bad)).toThrow(ApiError);
    for (const bad of [{ ...person, username: 'different' }, { ...person, role: 'admin' }, { ...person, teacher_id: null }]) {
      try { parseCreated(bad, payload); throw Error('must reject'); } catch (error) { expect(error).toMatchObject({ uncertain: true }); }
    }
    expect(() => parsePeople([person, person])).toThrow(ApiError);
  });
  it('keeps registration and recovery length policies distinct and bounded in UTF-8', () => {
    expect(validPassword('Aa1234!x', 8)).toBe(true);
    expect(validPassword('Aa1234!x', 12)).toBe(false);
    expect(validPassword('Aa123456789!', 12)).toBe(true);
    expect(validPassword(`Aa1!${'é'.repeat(35)}`, 8)).toBe(false);
    expect(validPassword(`Aa1!${'é'.repeat(34)}`, 8)).toBe(true);
    expect(validPassword('NoSymbol1234', 8)).toBe(false);
    expect(validPassword('Ⅳᵃ²!ᵃᵃᵃᵃ', 8)).toBe(true);
  });
  it('does not treat arbitrary success-shaped replies as confirmed mutations', () => {
    expect(() => confirmEnrollment({ student_id: 3, teacher_id: 2 }, 3, 2)).toThrow(ApiError);
    expect(() => confirmStatus({ id: 3, active: false, sessions_revoked: true }, 4, false)).toThrow(ApiError);
    expect(() => confirmRecovery({ id: 3, reset: true }, 3)).toThrow(ApiError);
    expect(() => confirmNotes({ success: 'yes' })).toThrow(ApiError);
    expect(() => confirmEnrollment({ student_id: 3, teacher_id: 2, existing_assignments_preserved: true }, 3, 2)).not.toThrow();
    expect(() => confirmStatus({ id: 3, active: false, sessions_revoked: true }, 3, false)).not.toThrow();
    expect(() => confirmRecovery({ id: 3, reset: true, sessions_revoked: true }, 3)).not.toThrow();
    expect(() => confirmNotes({ success: true })).not.toThrow();
  });
  it('reads only exact progress/notes types and preserves honest no-grade state', () => {
    expect(parseNotes({ notes: '' })).toBe('');
    expect(() => parseNotes({ notes: {} })).toThrow(ApiError);
    const progress = { lessons_completed: 0, assessments_taken: 1, avg_score: null, study_time_hours: 2.5, time_measure: 'elapsed_completed_session_time' };
    expect(parseProgress(progress).avg_score).toBeNull();
    expect(() => parseProgress({ ...progress, study_time_hours: -1 })).toThrow(ApiError);
    expect(() => parseProgress({ ...progress, avg_score: Infinity })).toThrow(ApiError);
  });
  it('discloses the bounded API through explicit role/state requests and complete ES/EN keys', () => {
    expect(peoplePath('teacher', true)).toBe('/api/auth/users?limit=500&role=teacher&include_inactive=true');
    expect(Object.keys(locales.es).sort()).toEqual(Object.keys(locales.en).sort());
    for (const language of Object.values(locales)) for (const value of Object.values(language)) expect(value).not.toBe('');
  });
});
