import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, Field, Input, Select } from '@/components/ui';
import { validScore, type Rubric } from './model';

/** A reviewable scoring aid; the teacher saves its score and readable breakdown together. */
export function RubricGrading({ rubrics, maximum, onDirtyChange, onApply }: {
 rubrics: Rubric[]; maximum: number; onDirtyChange: (dirty: boolean) => void;
 onApply: (score: number, breakdown: string, previous: string | null) => void;
}) {
 const { t } = useTranslation('assessments');
 const [selected, setSelected] = useState(0); const [inputs, setInputs] = useState<Record<number, string[]>>({});
 const [error, setError] = useState(false); const [previous, setPrevious] = useState<string | null>(null);
 const rubric = rubrics[selected];
 if (!rubric) return null;
 const scores = rubric.criteria.map((criterion, index) => validScore(inputs[selected]?.[index] ?? '', criterion.max_points));
 const total = rubric.criteria.reduce((sum, criterion) => sum + criterion.max_points, 0);
 const complete = total > 0 && scores.every(score => score !== null);
 const earned = scores.reduce<number>((sum, score) => sum + (score ?? 0), 0);
 const score = complete ? Math.round(earned / total * maximum) : null;
 const calculation = complete ? t('rubricScale', {earned, maximum: total, points: maximum, score}) : '';
 function apply() {
  if (!complete || score === null) { setError(true); return; }
  const breakdown = [t('rubricApplied', {name: rubric.name}), ...rubric.criteria.map((criterion, index) => `- ${criterion.name}: ${scores[index]} / ${criterion.max_points}`), calculation].join('\n');
  onApply(score, breakdown, previous); setPrevious(breakdown); onDirtyChange(false); setError(false);
 }
 return <div className="panel stack"><h3>{t('rubric')}</h3>
  {rubrics.length > 1 && <Field label={t('rubricName')}><Select value={selected} onChange={event => { setSelected(Number(event.target.value)); setError(false); onDirtyChange(true); }}>{rubrics.map((item, index) => <option key={index} value={index}>{item.name}</option>)}</Select></Field>}
  <h4>{rubric.name}</h4>{rubric.description && <p>{rubric.description}</p>}<p>{t('rubricHelper')}</p>
  {rubric.criteria.map((criterion, index) => <Field key={index} label={`${criterion.name} (0–${criterion.max_points})`} hint={criterion.description || undefined}>
   <Input type="number" min={0} max={criterion.max_points} step={1} value={inputs[selected]?.[index] ?? ''} onChange={event => { const next = [...(inputs[selected] || [])]; next[index] = event.target.value; setInputs({...inputs, [selected]: next}); onDirtyChange(true); setError(false); }}/>
  </Field>)}
  {!total && <p>{t('rubricNoCriteria')}</p>}{calculation && <p>{calculation}</p>}{error && <p role="alert" className="field-error">{t('rubricIncomplete')}</p>}
  <div className="cluster"><Button variant="secondary" disabled={!total} onClick={apply}>{t('applyRubric')}</Button><Button variant="ghost" onClick={() => { setInputs({}); onDirtyChange(false); setError(false); }}>{t('clearRubricDraft')}</Button></div>
 </div>;
}
