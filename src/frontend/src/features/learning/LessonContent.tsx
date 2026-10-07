import { Link } from 'react-router';
import { useTranslation } from 'react-i18next';
import { ContentRenderer } from '@/components/content/ContentRenderer';
import { EmptyState } from '@/components/ui';
import { contentData, isRecord, type LearningContent } from './contracts';

/** Render only known instructional fields. Each block has its own sanitization boundary. */
export function LessonContent({ content }: { content: LearningContent }) {
  const { t } = useTranslation('learning');
  const data = contentData(content);
  if (typeof data === 'string') return <ContentRenderer value={data} />;
  if (content.content_type === 'assessment') {
    const assessmentId = data.assessment_id;
    return typeof assessmentId === 'number' && Number.isSafeInteger(assessmentId) && assessmentId > 0 ? <div className="stack">{typeof data.instructions === 'string' && <ContentRenderer value={data.instructions} />}<Link to={`/evaluaciones/${assessmentId}`}>{t('openAssessment')}</Link><p className="muted">{t('assessmentPreview')}</p></div> : <EmptyState title={t('needsReview')} />;
  }
  if (content.content_type === 'exercise') return <p>{t('startPractice')}</p>;
  if (content.content_type === 'qa') return <div className="stack">{['question', 'content', 'answer'].map(key => typeof data[key] === 'string' ? <ContentRenderer key={key} value={data[key]} /> : null)}</div>;
  const sections = Array.isArray(data.sections) ? data.sections.filter(isRecord) : [];
  const renderSection = (section: Record<string, unknown>, index: number) => <section key={index} className="stack">{typeof section.title === 'string' && <h2>{section.title}</h2>}{typeof (section.content ?? section.text) === 'string' && <ContentRenderer value={String(section.content ?? section.text)} />}</section>;
  const renderList = (key: string) => Array.isArray(data[key]) && data[key].some(item => typeof item === 'string') ? <section key={key}><h2>{t(`lesson.${key}`)}</h2><ul>{data[key].filter((item): item is string => typeof item === 'string').map((item, index) => <li key={index}><ContentRenderer value={item} /></li>)}</ul></section> : null;
  const usage = isRecord(content.source_selection) ? content.source_selection : null;
  const supplied = usage?.supplied_characters, total = usage?.source_characters;
  const hasCounts = typeof supplied === 'number' && Number.isSafeInteger(supplied) && supplied >= 0 &&
    typeof total === 'number' && Number.isSafeInteger(total) && total >= supplied && total <= 100_000;
  return <div className="stack">
    {usage && <p className="muted" role="status">{hasCounts ? `${t('sourceCounts', { supplied, total })} ` : ''}{usage.use_coverage === 'partial' ? `${t('sourcePartial')} ` : ''}{t('sourceReceipt')}</p>}
    {sections.filter(section => section.source_clarification === true).map(renderSection)}
    {renderList('objectives')}
    {sections.length ? sections.filter(section => section.source_clarification !== true).map(renderSection) : typeof (data.content ?? data.body ?? data.text) === 'string' ? <ContentRenderer value={String(data.content ?? data.body ?? data.text)} /> : <EmptyState title={t('needsReview')} />}
    {typeof data.summary === 'string' && <section><h2>{t('lesson.summary')}</h2><ContentRenderer value={data.summary} /></section>}
    {Array.isArray(data.vocabulary) && data.vocabulary.some(isRecord) && <section><h2>{t('lesson.vocabulary')}</h2><dl>{data.vocabulary.filter(isRecord).map((term, index) => typeof term.term === 'string' && typeof term.definition === 'string' ? <div key={index}><dt>{term.term}</dt><dd><ContentRenderer value={term.definition} /></dd></div> : null)}</dl></section>}
    {['key_concepts', 'discussion_questions'].map(renderList)}
    {['worked_example', 'independent_attempt', 'feedback', 'delayed_review', 'prerequisite_check'].map(key => typeof data[key] === 'string' ? <section key={key}><h2>{t(`lesson.${key}`)}</h2><ContentRenderer value={data[key]} /></section> : null)}
  </div>;
}
