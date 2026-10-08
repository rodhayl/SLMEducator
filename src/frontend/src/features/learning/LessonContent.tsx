import { Link } from 'react-router';
import { useTranslation } from 'react-i18next';
import { ContentRenderer } from '@/components/content/ContentRenderer';
import { EmptyState } from '@/components/ui';
import { contentData, isRecord, type LearningContent } from './contracts';

const nonblank = (value: unknown): value is string => typeof value === 'string' && !!value.trim();
const sectionBody = (section: Record<string, unknown>): string => [section.content, section.text].find(nonblank) ?? [section.content, section.text].find((value): value is string => typeof value === 'string') ?? '';

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
  const body = [data.content, data.body, data.text].find((value): value is string => typeof value === 'string' && value.trim().length > 0) ?? '';
  const sectionText = sections.map(section => typeof (section.content ?? section.text) === 'string' ? String(section.content ?? section.text) : '').join('\n\n');
  const readableSections = sections.filter(section => nonblank(sectionBody(section)));
  const fallbackSectionText = sections.map(sectionBody).join('\n\n');
  const distinctBody = !!body.trim() && ![sectionText, fallbackSectionText].some(text => body.trim() === text.trim());
  const renderSection = (section: Record<string, unknown>, index: number) => <section key={index} className="stack">{nonblank(section.title) && <h2>{section.title}</h2>}<ContentRenderer value={sectionBody(section)} /></section>;
  const renderList = (key: string) => Array.isArray(data[key]) && data[key].some(nonblank) ? <section key={key}><h2>{t(`lesson.${key}`)}</h2><ul>{data[key].filter(nonblank).map((item, index) => <li key={index}><ContentRenderer value={item} /></li>)}</ul></section> : null;
  const vocabulary = Array.isArray(data.vocabulary) ? data.vocabulary.filter(isRecord).filter((term): term is {term: string; definition: string} => typeof term.term === 'string' && typeof term.definition === 'string' && (nonblank(term.term) || nonblank(term.definition))) : [];
  const usage = isRecord(content.source_selection) ? content.source_selection : null;
  const supplied = usage?.supplied_characters, total = usage?.source_characters;
  const hasCounts = typeof supplied === 'number' && Number.isSafeInteger(supplied) && supplied >= 0 &&
    typeof total === 'number' && Number.isSafeInteger(total) && total >= supplied && total <= 100_000;
  return <div className="stack">
    {usage && <p className="muted" role="status">{hasCounts ? `${t('sourceCounts', { supplied, total })} ` : ''}{usage.use_coverage === 'partial' ? `${t('sourcePartial')} ` : ''}{t('sourceReceipt')}</p>}
    {readableSections.filter(section => section.source_clarification === true).map(renderSection)}
    {renderList('objectives')}
    {distinctBody && <ContentRenderer value={body} />}
    {readableSections.length ? readableSections.filter(section => section.source_clarification !== true).map(renderSection) : !distinctBody && <EmptyState title={t('needsReview')} />}
    {nonblank(data.summary) && <section><h2>{t('lesson.summary')}</h2><ContentRenderer value={data.summary} /></section>}
    {vocabulary.length > 0 && <section><h2>{t('lesson.vocabulary')}</h2><dl>{vocabulary.map((term, index) => <div key={index}><dt>{term.term}</dt><dd><ContentRenderer value={term.definition} /></dd></div>)}</dl></section>}
    {['key_concepts', 'discussion_questions'].map(renderList)}
    {['worked_example', 'independent_attempt', 'feedback', 'delayed_review', 'prerequisite_check'].map(key => nonblank(data[key]) ? <section key={key}><h2>{t(`lesson.${key}`)}</h2><ContentRenderer value={data[key]} /></section> : null)}
  </div>;
}
