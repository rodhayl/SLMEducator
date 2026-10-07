import { useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/app/AuthProvider';
import { ApiError } from '@/lib/api';
import { positiveId } from '@/lib/ids';
import { useFileDownload } from '@/lib/downloads';
import { useOperation, useResource } from '@/lib/query';
import type { User } from '@/lib/types';
import { Button, Card, ConfirmDialog, EmptyState, ErrorState, Field, LoadingState, PageHeader, Select } from '@/components/ui';
import { allowedPurposes, canManagePlan, exportFormats, exportPath, parsed, parsePlans, parsePreview, selectionKey, type ExportFormat, type Plan, type Preview, type Purpose, type Selection } from './contracts';
import { CourseSelect, PreviewDetails, useCurrentPortability } from './shared';
import { ImportPanel, RevisionPanel } from './WritePanels';
export function PortabilityPage() { const {user,scope} = useAuth(); return user ? <PortabilityWorkspace key={`${scope}:${user.role}`} actor={user}/> : <ErrorState error={new ApiError(403,'http',false,'unavailable')}/>; }
function PortabilityWorkspace({actor}: {actor:User}) {
 const {t} = useTranslation('portability'); const [params] = useSearchParams(); const purposes = allowedPurposes(actor); const [purpose,setPurpose] = useState<Purpose>('handout');
 const plans = useResource<unknown>(['portability','plans'],'/api/study-plans/'); const result = parsed(plans.data,parsePlans);
 const requestedId = positiveId(params.get('plan_id')); const manageable = result.data?.filter(plan => canManagePlan(plan,actor));
 return <div className="stack"><Link to="/ajustes">{t('back')}</Link><PageHeader title={t('title')} description={t('description')}/><Card><Field label={t('purpose')}><Select value={purpose} onChange={event => { const next = event.target.value as Purpose; if (purposes.includes(next)) setPurpose(next); }}>{purposes.map(value => <option key={value} value={value}>{t(value)}</option>)}</Select></Field>{actor.role === 'admin' && <p><Link to="/administracion/copias">{t('backup')}</Link></p>}</Card>
 {purpose === 'import' ? <ImportPanel key="import"/> : <>{plans.isPending && <LoadingState/>}<ErrorState error={plans.error || result.error} retry={() => void plans.refetch()}/>{result.data && !plans.error && !result.error && (purpose === 'revision' ? <RevisionPanel key="revision" plans={manageable || []} initialId={requestedId}/> : <ExportPanel key={purpose} plans={purpose === 'teacher' ? manageable || [] : result.data} initialId={requestedId} audience={purpose === 'teacher' ? 'teacher' : 'learner'}/>)}</>}
 </div>;
}
function ExportPanel({plans,initialId,audience}: {plans:Plan[];initialId:number|null;audience:Selection['audience']}) {
 const {t} = useTranslation('portability'); const {api,credentialEpoch} = useAuth(); const current = useCurrentPortability(); const download = useFileDownload();
 const revision = useRef(0); const [planId,setPlanId] = useState(initialId && plans.some(plan => plan.id === initialId) ? String(initialId) : ''); const [format,setFormat] = useState<ExportFormat>(audience === 'teacher' ? 'json' : 'html'); const [preview,setPreview] = useState<{selection:Selection;value:Preview;epoch:number}|null>(null); const [confirm,setConfirm] = useState(false); const [downloaded,setDownloaded] = useState(false);
 const selection: Selection | null = positiveId(planId) && plans.some(plan => plan.id === Number(planId)) ? {id:Number(planId),audience,format} : null;
 const usable = preview && preview.epoch === credentialEpoch && selection && selectionKey(preview.selection) === selectionKey(selection) ? preview : null;
 const review = useOperation<void,{selection:Selection;value:Preview;ticket:number}>(async () => { const ticket = revision.current; if (!selection) throw new ApiError(422,'invalid',false,'validation'); return {selection,ticket,value:parsePreview(await api.get(exportPath(selection,'preview')),audience,format)}; }, value => { if (current() && value.ticket === revision.current) setPreview({...value,epoch:credentialEpoch}); });
 const save = useOperation<void,void>(async () => { if (!usable) throw new ApiError(409,'invalid',false,'conflict'); const selected = usable.selection; const blob = await api.download(exportPath(selected,'export'),{expectedContentTypes:[exportFormats[selected.format].type]}); if (!current()) return; download(blob,`course-${selected.id}-${selected.audience}.${exportFormats[selected.format].extension}`); }, () => { if (current()) { setDownloaded(true); setConfirm(false); } });
 const edit = () => { revision.current++; setPreview(null); setConfirm(false); setDownloaded(false); review.reset(); save.reset(); }; const busy = review.isPending || save.isPending;
 if (!plans.length) return <EmptyState title={t(audience === 'teacher' ? 'noOwnedCourses' : 'noCourses')} description={t(audience === 'teacher' ? 'noOwnedCoursesHint' : 'noCoursesHint')}/>;
 return <section className="stack"><Card><h2>{t(audience === 'teacher' ? 'teacher' : 'handout')}</h2><p>{t(audience === 'teacher' ? 'teacherHint' : 'handoutHint')}</p><div className="form-grid"><CourseSelect plans={plans} value={planId} disabled={save.isPending} onChange={value => {edit();setPlanId(value);}}/><Field label={t('format')}><Select value={format} disabled={save.isPending || audience === 'teacher'} onChange={event => {edit();setFormat(event.target.value as ExportFormat);}}>{(audience === 'teacher' ? ['json'] : ['html','markdown','json']).map(value => <option key={value} value={value}>{t(value)}</option>)}</Select></Field></div><Button disabled={!selection || busy} busy={review.isPending} onClick={() => {setPreview(null);setDownloaded(false);review.mutate(undefined);}}>{t('preview')}</Button></Card>
 <ErrorState error={review.error || save.error}/>{usable && <PreviewDetails preview={usable.value}/>}<Button disabled={!usable || busy} busy={save.isPending} onClick={() => setConfirm(true)}>{t('download')}</Button>{downloaded && <p role="status">{t('downloaded')}</p>}
 <ConfirmDialog open={confirm && !!usable} onOpenChange={setConfirm} title={t('confirmExport')} description={t('confirmExportHint')} confirmLabel={t('download')} busy={save.isPending} onConfirm={() => { void save.mutateAsync(undefined).catch(() => { if (current()) setConfirm(false); }); }}/></section>;
}
