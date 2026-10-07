import { describe, expect, it } from 'vitest';
import { isAnnotationDeleteReceipt, isAnnotationList, isAnnotationReceipt, isPracticeDraft, normalizePractice, practiceSolution, practiceFingerprint } from '../../src/frontend/src/features/learning/tool-contracts';
import { toolLocales } from '../../src/frontend/src/features/learning/tool-locales';

const containers: [string, unknown, string][] = [['array', ['One', 'Two'], 'B'], ['map', { first: 'One', second: 'Two' }, 'second'], ['nested array', { choices: ['One', 'Two'] }, 'B'], ['nested map', { choices: { first: 'One', second: 'Two' } }, 'second']];
describe('canonical practice contracts', () => {
  it.each(containers)('preserves keys and answer text for %s', (_, options, correct_answer) => {
    const questions = normalizePractice({ question: 'Choose two', options, correct_answer })!;
    expect(questions[0].options.map(option => option.text)).toEqual(['One', 'Two']);
    expect(questions[0].options[1].key).toBe(correct_answer);
    expect(practiceSolution(questions[0])).toBe('Two');
    expect(practiceSolution({ ...questions[0], answer: 'Two' })).toBe('Two');
  });
  it('supports multiple questions, alternate names, boolean keys and JSON input', () => {
    const questions = normalizePractice(JSON.stringify({ questions: [{ question_text: 'Is it true?', question_type: 'true_false', correct_answer: false }, { question: 'Explain', answer: 42, hints: ['First', '', null, 'Second'] }] }))!;
    expect(practiceSolution(questions[0])).toBe('False');
    expect(practiceSolution(questions[1])).toBe('42');
    expect(questions[1].hints).toEqual(['First', 'Second']);
  });
  it.each([null, [], '', '<script>bad</script>', {}, { questions: [] }, { questions: [{ question: 'Valid' }, null] }, { question: ' ' }, { question: 'Q', options: [{ text: 'Invalid nested object' }] }])('rejects malformed material %j', raw => { expect(normalizePractice(raw)).toBeNull(); });
  it('validates restored answer values, exact question count, fingerprint and hint bounds', () => {
    const questions = normalizePractice({ question: 'Choose', options: ['One', 'Two'], hints: ['First', 'Second'] })!;
    expect(isPracticeDraft({ answers: ['Two'], hints: [1] }, questions)).toBe(true);
    expect(isPracticeDraft({ answers: ['Two'], hints: [2], fingerprint: practiceFingerprint(questions) }, questions)).toBe(true);
    for (const draft of [{ answers: ['B'], hints: [0] }, { answers: [], hints: [0] }, { answers: ['Two'], hints: [3] }, { answers: ['Two'], hints: [-1] }, { answers: ['Two'], hints: [0.5] }, { answers: ['Two'], hints: [0], fingerprint: 'outdated' }]) expect(isPracticeDraft(draft, questions)).toBe(false);
  });
});

describe('annotation receipt contracts', () => {
  const input = { content_id: 3, annotation_text: 'Synthetic note', annotation_type: 'comment' as const, is_public: false, text_selection_start: null, text_selection_end: null };
  const receipt = { ...input, id: 9, user_id: 1, user_name: 'Synthetic learner', created_at: '2026-10-07T12:00:00+00:00' };
  it('requires matching owner, content, text, type and audience before reporting a save', () => {
    expect(isAnnotationReceipt(receipt, input, 1)).toBe(true);
    for (const patch of [{ user_id: 2 }, { content_id: 4 }, { annotation_text: 'Different note' }, { annotation_type: 'question' }, { is_public: true }, { text_selection_start: 0 }, { id: 0 }]) expect(isAnnotationReceipt({ ...receipt, ...patch }, input, 1)).toBe(false);
  });
  it('rejects nonlists, foreign content and duplicate annotation IDs', () => {
    expect(isAnnotationList([receipt], 3)).toBe(true);
    expect(isAnnotationList({ annotations: [receipt] }, 3)).toBe(false);
    expect(isAnnotationList([receipt], 4)).toBe(false);
    expect(isAnnotationList([receipt, receipt], 3)).toBe(false);
  });
  it('requires the actual delete receipt', () => {
    expect(isAnnotationDeleteReceipt({ status: 'ok', message: 'Annotation deleted' })).toBe(true);
    for (const value of [null, {}, { status: 'ok' }, { status: 'failed', message: 'Annotation deleted' }, { status: 'ok', message: 'Not deleted' }]) expect(isAnnotationDeleteReceipt(value)).toBe(false);
  });
  it('keeps English and Spanish keys and placeholders aligned', () => {
    expect(Object.keys(toolLocales.en).sort()).toEqual(Object.keys(toolLocales.es).sort());
    for (const key of Object.keys(toolLocales.en) as (keyof typeof toolLocales.en)[]) expect(toolLocales.en[key].match(/{{[^}]+}}/g)).toEqual(toolLocales.es[key].match(/{{[^}]+}}/g));
  });
});
