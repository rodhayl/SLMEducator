import { describe, expect, it } from 'vitest';
import { DraftAdapter } from '@/lib/drafts';
import { authoredSource, generationRequest, isGenerationDraft } from '@/features/authoring/contracts';
import { legacyDesignerSetup } from '@/features/authoring/legacy-designer';

const oldDraft = () => ({ currentConfig: { subject: 'Science', grade_level: '10', duration: 8 }, generatedOutline: { title: 'Recovered course', description: 'Original description', units: [{ title: 'Motion', lessons: [{ title: 'Velocity', learning_objectives: [] }, { title: 'Energy', learning_objectives: ['Compare energy'] }] }] }, createdStudyPlanId: 12, sourceMaterialText: null, sourceCoverage: null, sourceDocumentId: null, sourceSavedVersion: null, generationTasks: [{ unit: 0, lesson: 0, status: 'saved' }, { unit: 0, lesson: 1, status: 'running' }] });
describe('previous designer draft conversion', () => {
 it('keeps configuration, outline and pending topic identity without replaying saved topics', () => {
  const original = oldDraft(); const result = legacyDesignerSetup(original)!;
  expect(result.form).toMatchObject({ mode: 'outline', subject: 'Science', grade: '10', weeks: 8, planId: '12' });
  expect(result.outline?.units[0].lessons).toEqual([{ title: 'Velocity', learning_objectives: ['Understand Velocity'], selected: false }, { title: 'Energy', learning_objectives: ['Compare energy'], selected: true }]);
  expect(result.createdPlanId).toBe(12); expect(isGenerationDraft(result)).toBe(true); expect(original).toEqual(oldDraft());
  const request = generationRequest({ ...result.form, mode: 'package', topic: 'Energy', objectives: 'Compare energy' }, null);
  expect(request.body).toMatchObject({ num_exercises: 4, num_assessment_questions: 5, exercise_difficulty: 'medium', assessment_difficulty: 'medium', assessment_question_types: null, include_assessment: false });
 });
 it('retains the exact topic selection when initial course creation was interrupted', () => { const result=legacyDesignerSetup({...oldDraft(),createdStudyPlanId:null,generationTasks:[{unit:0,lesson:1,status:'pending'}]}); expect(result?.outline?.units[0].lessons.map(lesson=>lesson.selected)).toEqual([false,true]); });
 it('restores a source-only initial draft without inventing a generated outline or saved course', () => {
  const source = authoredSource('notes.txt', 'Source text');
  const result = legacyDesignerSetup({ currentConfig: {}, generatedOutline: null, sourceCoverage: source, sourceMaterialText: source.extracted_text, createdStudyPlanId: null, generationTasks: [] });
  expect(result).toMatchObject({ outline: null, createdPlanId: null, recoveredSource: source, form: { subject: '', grade: '', weeks: 4 } });
 });
 it('keeps incomplete legacy source as unverified authored text rather than inventing file provenance', () => {
  const result = legacyDesignerSetup({ ...oldDraft(), sourceMaterialText: 'Unverified legacy source', sourceCoverage: { filename: 'old.pdf', source_version: 'bad' } });
  expect(result?.recoveredSource).toEqual(authoredSource('old.pdf', 'Unverified legacy source'));
 });
 it('never removes the old owner-scoped entry while reading a compatible setup', () => {
  const drafts = new DraftAdapter(7); drafts.write('course', 'designer', 'active', oldDraft());
  const key = 'slm_draft_v1:7:course:designer:active'; const stored = localStorage.getItem(key);
  expect(legacyDesignerSetup(drafts.read('course', 'designer', 'active', (value): value is Record<string,unknown> => !!value && typeof value === 'object'))).not.toBeNull();
  expect(localStorage.getItem(key)).toBe(stored); expect(new DraftAdapter(8).read('course', 'designer', 'active', (value): value is Record<string,unknown> => !!value && typeof value === 'object')).toBeNull();
 });
 it.each([
  { currentConfig: { duration: 105 } }, { createdStudyPlanId: -1 }, { currentConfig: { subject: {} } },
  { generatedOutline: { title: 'Wrong units', units: 'bad' } }, { generationTasks: [{ unit: -1, lesson: 0, status: 'saved' }] },
  { generationTasks: [{ unit: 0, lesson: 0, status: 'unknown' }] }, { generationTasks: [{unit:0,lesson:0,status:'saved'},{unit:0,lesson:0,status:'running'}] }, { sourceMaterialText: 'x'.repeat(100001) },
 ])('rejects unsafe conversion while leaving its storage recovery to the caller', changes => expect(legacyDesignerSetup({ ...oldDraft(), ...changes })).toBeNull());
 it('rejects a corrupted migrated source manifest', () => expect(isGenerationDraft({ ...legacyDesignerSetup(oldDraft()), recoveredSource: { filename: 'x', extracted_text: 'x' } })).toBe(false));
});
