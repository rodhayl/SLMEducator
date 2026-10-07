import { render } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { materialForm, materialPayload } from '@/features/authoring/contracts';
import { LessonContent } from '@/features/learning/LessonContent';
import { locales } from '@/features/learning/locales';
import type { LearningContent } from '@/features/learning/contracts';
import fixtures from '../fixtures/source_clarification_render.json';

/** The same backend-reviewed outputs used by the Python source-review contract. */
describe('reviewed clarification fixtures through the React rendering boundary', () => {
  it.each(fixtures.cases)('$name remains literal and visible through rerender and editor roundtrip', async item => {
    const i18n = createInstance();
    await i18n.init({ lng: 'en', defaultNS: 'learning', resources: { en: { learning: locales.en } } });
    const data: Record<string, unknown> = item.learner_output;
    const lesson: LearningContent = { id: 1, title: 'Reviewed fixture', content_type: 'lesson', content_data: data };
    const tree = (content: LearningContent) => <I18nextProvider i18n={i18n}><MemoryRouter><LessonContent content={content} /></MemoryRouter></I18nextProvider>;
    const view = render(tree(lesson));
    const assertVisibleAndInert = () => {
      expect(view.container.textContent).toContain(item.question);
      expect(view.container.querySelector('script,img,svg,iframe,[onerror],[onload]')).toBeNull();
      const firstSection = view.container.querySelector('section');
      if (firstSection) expect(firstSection.textContent).toContain(item.question);
    };
    assertVisibleAndInert();

    // A new response object must not turn escaped source text into executable markup.
    view.rerender(tree({ ...lesson, content_data: structuredClone(data) }));
    assertVisibleAndInert();

    // The React editor preserves structured sections rather than flattening them.
    const form = materialForm('lesson', data, lesson.title);
    const saved = materialPayload(form, data);
    view.rerender(tree({ ...lesson, content_data: saved.content_data }));
    assertVisibleAndInert();

    // Already-saved flattened bodies from the old editor remain readable as well.
    view.rerender(tree({ ...lesson, content_data: { body: item.learner_output.content } }));
    assertVisibleAndInert();
    view.rerender(tree({ ...lesson, content_data: { body: item.learner_output.content } }));
    assertVisibleAndInert();
  });
});
