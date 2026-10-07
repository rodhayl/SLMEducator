import { describe, expect, it } from 'vitest';
import { choicesFor, isDraft, isSubmission, validScore, finalizesQuestion, attemptDeadline, confirmResult, confirmStart, isAssessment, isSubmissionList } from '@/features/assessments/model';
import { canPublish, editorPayload, editorValues, generatedAssessmentValues } from '@/features/assessments/editor-model';
import { locales } from '@/features/assessments/locales';
import { assessment, submission } from './assessments-fixtures';
describe('assessment contracts', () => {
 it('keeps canonical keys independent of labels and preserves legacy text arrays', () => { expect(choicesFor(assessment.questions[0])).toEqual([{ value: 'A', label: 'One, half' }, { value: 'B', label: 'Two thirds' }]); expect(choicesFor({ question_type: 'multiple_choice', options: { choices: ['A, B', 'C'] } })).toEqual([{ value: 'A, B', label: 'A, B' }, { value: 'C', label: 'C' }]); expect(choicesFor({ question_type: 'multiple_choice', options: { choices: ['x', {}] } })).toBeNull(); });
 it('uses canonical English boolean values independent of translated labels', () => { expect(choicesFor({ question_type: 'true_false', options: null })?.map(item => item.value)).toEqual(['True', 'False']); });
 it('distinguishes zero, empty, negative, fractional and missing grades', () => { expect(validScore('0', 10)).toBe(0); for (const input of ['', ' ', '-1', '0.5', '11', 'NaN']) expect(validScore(input, 10)).toBeNull(); expect(isSubmission(submission, 55, 3)).toBe(true); expect(isSubmission({ ...submission, score: 0 }, 55)).toBe(true); expect(isSubmission({ ...submission, score: undefined }, 55)).toBe(false); });
 it('finalizes when every other score is present including zero', () => { expect(finalizesQuestion(submission, 202)).toBe(true); expect(finalizesQuestion(submission, 201)).toBe(false); });
 it('requires identity, shape and owner for private records', () => { expect(isAssessment(assessment, 11)).toBe(false); expect(isAssessment({ ...assessment, can_manage: undefined })).toBe(false); expect(isSubmission(submission, 55, 4)).toBe(false); expect(isSubmissionList([submission, submission], 3)).toBe(false); expect(isSubmission({ ...submission, answers: [{ ...submission.answers[0], points: 99 }] })).toBe(false); });
 it('validates exact-question draft scope without restoring bad canonical values', () => { expect(isDraft({ answers: [{ question_id: 101, response_text: 'A' }] }, assessment)).toBe(true); for (const answers of [[{ question_id: 999, response_text: 'A' }], [{ question_id: 101, response_text: 'One, half' }], [{ question_id: 101, response_text: 'A' }, { question_id: 101, response_text: 'B' }]]) expect(isDraft({ answers }, assessment)).toBe(false); });
 it('never treats offset-free historical timer values as UTC', () => { expect(attemptDeadline(submission)).toBe(Date.parse(submission.expires_at!)); expect(attemptDeadline({ ...submission, timing_provenance: 'legacy_unknown' })).toBeNull(); expect(attemptDeadline({ ...submission, expires_at: '2026-10-07T11:00:00' })).toBeNull(); });
 it('rejects mismatched or malformed mutation receipts', () => { expect(confirmStart({ id: 55, submission_id: 55, status: 'draft' })).toBe(55); expect(() => confirmStart({ id: 56, submission_id: 55, status: 'draft' })).toThrow(); expect(() => confirmResult({ id: 55, submission_id: 55, status: 'graded', score: 0 }, 55, false)).not.toThrow(); expect(() => confirmResult({ id: 55, submission_id: 55, status: 'draft', score: null }, 55, false)).toThrow(); expect(() => confirmResult({ id: 55, submission_id: 55, status: 'graded', score: 0 }, 55, true)).toThrow(); });
 it('editor round-trips keyed labels with commas, zero pass score and null time', () => { const values = editorValues(assessment); values.passing_score = '0'; values.time_limit_minutes = ''; const payload = editorPayload(values); expect(payload).toMatchObject({ passing_score: 0, time_limit_minutes: null, is_published: false, questions: [{ options: { choices: { A: 'One, half', B: 'Two thirds' } }, correct_answer: 'A' }, { correct_answer: null }] }); expect(canPublish(values, 'disabled')).toBe(true); });
 it('drafts may omit keys but publication may not; malformed fields fail closed', () => { const values = editorValues(assessment); values.questions[0].correct_answer = ''; expect(editorPayload(values)).not.toBeNull(); expect(canPublish(values, 'hints_only')).toBe(false); values.questions[0].choices[1].value = 'a'; expect(editorPayload(values)).toBeNull(); });
 it('metadata-only edits never resend immutable scoring rules', () => { expect(editorPayload(editorValues(assessment), true)).toEqual({ title: 'Fractions', description: 'Read carefully', max_attempts: 2 }); });
 it('has complete ES/EN keys', () => { expect(Object.keys(locales.en).sort()).toEqual(Object.keys(locales.es).sort()); });
});
describe('assessment compatibility and asset fidelity', () => {
 it('preserves raw-map historical submitted text rather than guessing canonical keys', () => { expect(choicesFor({ question_type: 'multiple_choice', options: { A: 'three', B: 'four' } })).toEqual([{ value: 'three', label: 'three' }, { value: 'four', label: 'four' }]); });
 it('round-trips opaque question assets and unchanged option containers exactly', () => { const data = structuredClone(assessment); data.questions[0].options = { choices: ['One, half', 'Two thirds'], future_option_metadata: { x: 0 } }; data.questions[0].correct_answer = 'One, half'; data.questions[0].content_metadata = { explanation: 'Private explanation', hints: ['Private hint'], unknown_future_asset: [null, false, 0] }; data.questions[0].rubrics = [{ name: 'Question rubric', description: 'Private description', criteria: [{ name: 'Reason', description: 'Private criterion', max_points: 10 }] }]; const values = editorValues(data, true); const payload = editorPayload(values); expect(payload).toMatchObject({ questions: [{ content_metadata: data.questions[0].content_metadata, rubrics: data.questions[0].rubrics, options: data.questions[0].options, correct_answer: 'One, half' }, {}] }); });
 it('preserves a case-insensitive legacy key without falsely demanding a new key', () => { const data = structuredClone(assessment); data.questions[0].correct_answer = ' a '; expect(editorPayload(editorValues(data))).toMatchObject({ questions: [{ correct_answer: ' a ' }, {}] }); });
});

describe('generated assessment editor adaptation', () => {
 it('preserves question rubrics, hints, explanation and opaque metadata before save', () => { const values = generatedAssessmentValues({ title: 'Proposal', questions: [{ question: 'Explain', type: 'short_answer', points: 10, correct_answer: 'Private key', content_metadata: { future: { a: 0 } }, hints: ['hint'], explanation: 'explanation', rubric: { criteria: [{ name: 'Reasoning', max_points: 10 }] } }] }); expect(values).not.toBeNull(); expect(editorPayload(values!)).toMatchObject({ questions: [{ content_metadata: { future: { a: 0 }, hints: ['hint'], explanation: 'explanation' }, rubrics: [{ name: 'Generated draft rubric', criteria: [{ name: 'Reasoning', max_points: 10 }] }] }] }); });
 it('never guesses a generated letter key from an option array index', () => { const values = generatedAssessmentValues({ title: 'Proposal', questions: [{ question: 'Choose', type: 'multiple_choice', points: 10, options: ['Three', 'Four'], correct_answer: 'B' }] }); expect(values).toBeNull(); });
 it('rejects a malformed rubric without silently dropping it', () => { expect(generatedAssessmentValues({ title: 'Proposal', questions: [{ question: 'Explain', points: 10, rubric: { criteria: [{ name: 'Reasoning', max_points: 5 }] } }] })).toBeNull(); });
});

describe('fresh generated multiple-choice normalization', () => {
 const proposal = (options: unknown, correct_answer: unknown) => ({title: 'Fresh proposal', questions: [{question: 'Choose', type: 'multiple_choice', points: 10, options, correct_answer}]});
 it.each(['B', ' b ', 'Four', ' four '])('normalizes a fresh raw letter map answer %s to its canonical key', answer => {
  const values = generatedAssessmentValues(proposal({A: 'Three', B: 'Four'}, answer));
  expect(values).not.toBeNull(); expect(editorPayload(values!)).toMatchObject({questions: [{options: {choices: {A: 'Three', B: 'Four'}}, correct_answer: 'B'}]}); expect(canPublish(values!, 'hints_only')).toBe(true);
 });
 it.each([['Four', '2'], ['2', '2']])('normalizes fresh arrays using unambiguous numbered keys (%s)', (answer, key) => {
  const values = generatedAssessmentValues(proposal(['Three', 'Four'], answer));
  expect(values).not.toBeNull(); expect(editorPayload(values!)).toMatchObject({questions: [{options: {choices: {'1': 'Three', '2': 'Four'}}, correct_answer: key}]});
 });
 it.each([
  [{A: 'Three', B: 'Four'}, 'C'], [{A: 'Three', B: 'Four'}, null],
  [{A: 'B', B: 'Four'}, 'B'], [{A: 'same', B: 'Same'}, 'same'],
  [{A: 'Three', ' a ': 'Four'}, 'A'], [{'ß': 'Three', ss: 'Four'}, 'ss'], [{'ẞ': 'Three', ss: 'Four'}, 'ss'], [{'ς': 'Three', 'σ': 'Four'}, 'σ'], [{A: '', B: 'Four'}, 'B'], [['Three', 'Four'], 'B'],
 ])('rejects invalid or ambiguous freshly generated options and answers (%j, %j)', (options, answer) => { expect(generatedAssessmentValues(proposal(options, answer))).toBeNull(); });
 it('strips hidden fresh option siblings while normalizing a displayed answer', () => {
  const values = generatedAssessmentValues(proposal({choices: {A: 'Three', B: 'Four'}, correct_answer: 'B', explanation: 'Hidden provider key', rubric: {secret: true}}, 'Four'));
  expect(values!.questions[0].source_options).toEqual({choices: {A: 'Three', B: 'Four'}});
  expect(editorPayload(values!)).toMatchObject({questions: [{options: {choices: {A: 'Three', B: 'Four'}}, correct_answer: 'B'}]});
 });
 it.each([[4, '4'], [true, 'true'], [false, 'false']])('accepts an unambiguous scalar fresh answer %j', (answer, label) => {
  const values = generatedAssessmentValues(proposal({A: 'Other label', B: label}, answer));
  expect(values?.questions[0].correct_answer).toBe('B');
 });
 it('rejects nonfinite fresh answer values', () => { expect(generatedAssessmentValues(proposal({A: 'Infinity', B: 'Other'}, Infinity))).toBeNull(); });
});
