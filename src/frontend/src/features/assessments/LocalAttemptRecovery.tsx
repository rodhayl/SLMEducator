import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/app/AuthProvider';
import { Button, Card } from '@/components/ui';
import { DraftAdapter } from '@/lib/drafts';
import { id, record, type AttemptDraft, type Submission } from './model';

function isRecovery(value: unknown): value is AttemptDraft {
 if (!record(value) || !Array.isArray(value.answers) || !value.answers.length || value.answers.length > 2000) return false;
 return value.answers.every(answer => record(answer) && id(answer.question_id) && typeof answer.response_text === 'string' && answer.response_text.length <= 2_000_000) && new Set(value.answers.map(answer => answer.question_id)).size === value.answers.length;
}

/** Only render after the current account's exact submission was verified by the caller. */
export function LocalAttemptRecovery({ submission }: { submission: Submission }) {
 const { user } = useAuth();
 return user?.role === 'student' && user.id === submission.student_id && submission.status !== 'draft' ? <Recovery key={`${user.id}:${submission.id}`} ownerId={user.id} submission={submission}/> : null;
}
function Recovery({ ownerId, submission }: { ownerId: number; submission: Submission }) {
 const { t } = useTranslation('assessments'); const [open, setOpen] = useState(false);
 const [draft] = useState(() => new DraftAdapter(ownerId).read('assessment', submission.assessment_id, submission.id, isRecovery));
 if (!draft) return null;
 return <Card><h2>{t('closedLocalDraft')}</h2><p>{t('closedLocalDraftHint')}</p><Button variant="secondary" aria-expanded={open} onClick={() => setOpen(value => !value)}>{t('showClosedLocalDraft')}</Button>{open && <ul className="list">{draft.answers.map(answer => <li key={answer.question_id}><h3>{t('localQuestionId', { id: answer.question_id })}</h3><p className="prose" style={{ whiteSpace: 'pre-wrap' }}>{answer.response_text || t('noAnswer')}</p></li>)}</ul>}</Card>;
}
