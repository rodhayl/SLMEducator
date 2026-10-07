import { useRef, useState } from 'react';
import { Link } from 'react-router';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/app/AuthProvider';
import { useDirtyGuard } from '@/app/DirtyGuard';
import { ApiError } from '@/lib/api';
import { positiveId } from '@/lib/ids';
import { useInvalidate, useOperation } from '@/lib/query';
import { Button, Card, ConfirmDialog, EmptyState, ErrorState, Field, Input } from '@/components/ui';
import { exportPath, MAX_IMPORT_BYTES, parseDraftReceipt, parseImportText, parsePreview, type Plan, type Preview } from './contracts';
import { CourseSelect, PreviewDetails, useCurrentPortability } from './shared';
export function ImportPanel() {
 const {t} = useTranslation('portability'); const {api,credentialEpoch} = useAuth(); const current = useCurrentPortability(); const invalidate = useInvalidate(); const revision = useRef(0); const [fileKey,setFileKey] = useState(0);
 const [file,setFile] = useState<File|null>(null); const [prepared,setPrepared] = useState<{package:Record<string,unknown>;preview:Preview;epoch:number}|null>(null); const [confirm,setConfirm] = useState(false); const [created,setCreated] = useState<number|null>(null);
 const usable = prepared?.epoch === credentialEpoch ? prepared : null; useDirtyGuard(!!file && !created);
 const review = useOperation<void,void>(async () => {
  const selected = file, ticket = revision.current; if (!selected || selected.size > MAX_IMPORT_BYTES) throw new ApiError(422,'invalid',false,'validation');
  const text = await selected.text(); if (!current() || ticket !== revision.current) return;
  const candidate = parseImportText(text); const preview = parsePreview(await api.post('/api/portability/import/preview',{package:candidate}),'teacher');
  if (current() && ticket === revision.current) setPrepared({package:candidate,preview,epoch:credentialEpoch});
 });
 const create = useOperation<void,number>(async () => { if (!usable) throw new ApiError(409,'invalid',false,'conflict'); return parseDraftReceipt(await api.post('/api/portability/import',{package:usable.package,confirm:true}),'import'); }, async id => {
  if (!current()) return; setCreated(id); setPrepared(null); setFile(null); setConfirm(false); setFileKey(value => value + 1); await invalidate(['courses']);
 });
 const edit = (next:File|null) => { revision.current++; setFile(next); setPrepared(null); setConfirm(false); setCreated(null); review.reset(); create.reset(); };
 return <section className="stack"><Card><h2>{t('import')}</h2><p>{t('importHint')}</p><Field label={t('file')} hint={t('fileHint')}><Input key={fileKey} type="file" accept=".json,application/json" disabled={create.isPending} onChange={event => edit(event.target.files?.[0] || null)}/></Field><Button disabled={!file || review.isPending || create.isPending} busy={review.isPending} onClick={() => {setPrepared(null);review.mutate(undefined);}}>{t('previewImport')}</Button></Card>
 <ErrorState error={review.error || create.error}/>{create.error?.uncertain && <p>{t('uncertain')} <Link to="/cursos">{t('courses')}</Link></p>}{usable && <PreviewDetails preview={usable.preview}/>}<Button disabled={!usable || review.isPending || create.isPending || create.error?.uncertain} busy={create.isPending} onClick={() => setConfirm(true)}>{t('confirmImport')}</Button>{created && <Card><p role="status">{t('imported')}</p><Link to={`/cursos/${created}/editar`}>{t('openDraft')}</Link></Card>}
 <ConfirmDialog open={confirm && !!usable} onOpenChange={setConfirm} title={t('importTitle')} description={t('importHint')} confirmLabel={t('confirmImport')} busy={create.isPending} onConfirm={() => {if (!create.error?.uncertain) void create.mutateAsync(undefined).catch(() => { if (current()) setConfirm(false); });}}/></section>;
}
export function RevisionPanel({plans,initialId}: {plans:Plan[];initialId:number|null}) {
 const {t} = useTranslation('portability'); const {api,credentialEpoch} = useAuth(); const current = useCurrentPortability(); const invalidate = useInvalidate(); const revision = useRef(0);
 const [planId,setPlanId] = useState(initialId && plans.some(plan => plan.id === initialId) ? String(initialId) : ''); const [preview,setPreview] = useState<{id:number;value:Preview;epoch:number}|null>(null); const [confirm,setConfirm] = useState(false); const [created,setCreated] = useState<number|null>(null);
 const usable = preview?.epoch === credentialEpoch && preview.id === positiveId(planId) ? preview : null;
 const review = useOperation<void,void>(async () => { const id = positiveId(planId), ticket = revision.current; if (!id || !plans.some(plan => plan.id === id)) throw new ApiError(422,'invalid',false,'validation'); const value = parsePreview(await api.get(exportPath({id,audience:'teacher',format:'json'},'preview')),'teacher','json'); if (current() && ticket === revision.current) setPreview({id,value,epoch:credentialEpoch}); });
 const create = useOperation<void,number>(async () => { if (!usable) throw new ApiError(409,'invalid',false,'conflict'); return parseDraftReceipt(await api.post(`/api/study-plans/${usable.id}/copy`,{reason:'revision'}),'revision'); }, async id => { if (!current()) return; setCreated(id); setPreview(null); setConfirm(false); await invalidate(['courses']); });
 if (!plans.length) return <EmptyState title={t('noOwnedCourses')} description={t('noOwnedCoursesHint')}/>;
 return <section className="stack"><Card><h2>{t('revision')}</h2><p>{t('revisionHint')}</p><CourseSelect plans={plans} value={planId} disabled={create.isPending} onChange={value => {revision.current++;setPlanId(value);setPreview(null);setConfirm(false);setCreated(null);review.reset();create.reset();}}/><Button disabled={!positiveId(planId) || review.isPending || create.isPending} busy={review.isPending} onClick={() => {setPreview(null);review.mutate(undefined);}}>{t('previewRevision')}</Button></Card>
 <ErrorState error={review.error || create.error}/>{create.error?.uncertain && <p>{t('uncertain')} <Link to="/cursos">{t('courses')}</Link></p>}{usable && <PreviewDetails preview={usable.value}/>}<Button disabled={!usable || create.isPending || create.error?.uncertain} busy={create.isPending} onClick={() => setConfirm(true)}>{t('confirmRevision')}</Button>{created && <Card><p role="status">{t('imported')}</p><Link to={`/cursos/${created}/editar`}>{t('openDraft')}</Link></Card>}
 <ConfirmDialog open={confirm && !!usable} onOpenChange={setConfirm} title={t('revisionTitle')} description={t('revisionHint')} confirmLabel={t('confirmRevision')} busy={create.isPending} onConfirm={() => {if (!create.error?.uncertain) void create.mutateAsync(undefined).catch(() => { if (current()) setConfirm(false); });}}/></section>;
}
