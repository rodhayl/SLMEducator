import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/app/AuthProvider';
import { ApiError } from '@/lib/api';
import { useFileDownload } from '@/lib/downloads';
import { useOperation } from '@/lib/query';
import { Button, Card, ConfirmDialog, ErrorState, PageHeader } from '@/components/ui';
import { parseBackup, type BackupPreview } from './contracts';
import { PreviewDetails, useCurrentPortability } from './shared';
export function BackupPage() { const {user,scope} = useAuth(); return user?.role === 'admin' ? <BackupWorkspace key={scope}/> : <ErrorState error={new ApiError(403,'http',false,'unavailable')}/>; }
function BackupWorkspace() {
 const {t} = useTranslation('portability'); const {api,credentialEpoch} = useAuth(); const current = useCurrentPortability(); const download = useFileDownload();
 const [preview,setPreview] = useState<{value:BackupPreview;epoch:number}|null>(null); const [confirm,setConfirm] = useState(false); const [downloaded,setDownloaded] = useState(false); const usable = preview?.epoch === credentialEpoch ? preview : null;
 const review = useOperation<void,BackupPreview>(async () => parseBackup(await api.get('/api/portability/backup/preview')),value => { if (current()) setPreview({value,epoch:credentialEpoch}); });
 const save = useOperation<void,void>(async () => { if (!usable) throw new ApiError(409,'invalid',false,'conflict'); const blob = await api.download('/api/portability/backup',{method:'POST',body:{confirm:true},expectedContentTypes:['application/vnd.slmeducator.backup+json']}); if (!current()) return; download(blob,'slmeducator-private-database.slmbackup'); },() => {if (current()) {setDownloaded(true);setConfirm(false);setPreview(null);}});
 return <div className="stack"><PageHeader title={t('backup')} description={t('backupDescription')}/><Card><p>{t('backupWarning')}</p><p>{t('backupNotInstallation')}</p><Button disabled={review.isPending || save.isPending} busy={review.isPending} onClick={() => {setPreview(null);setDownloaded(false);review.mutate(undefined);}}>{t('previewBackup')}</Button></Card><ErrorState error={review.error || save.error}/>{usable && <PreviewDetails preview={usable.value}/>}<Button disabled={!usable || save.isPending || review.isPending} busy={save.isPending} onClick={() => setConfirm(true)}>{t('downloadBackup')}</Button>{downloaded && <p role="status">{t('downloaded')}</p>}<Card><h2>{t('restore')}</h2><ol>{['restoreStep1','restoreStep2','restoreStep3','restoreStep4'].map(key => <li key={key}>{t(key)}</li>)}</ol></Card>
 <ConfirmDialog open={confirm && !!usable} onOpenChange={setConfirm} title={t('backupConfirm')} description={t('backupWarning')} confirmLabel={t('downloadBackup')} busy={save.isPending} onConfirm={() => { void save.mutateAsync(undefined).catch(() => { if (current()) setConfirm(false); }); }}/></div>;
}
