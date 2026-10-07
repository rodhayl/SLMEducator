import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/app/AuthProvider';
import { Card, Field, Select } from '@/components/ui';
import { scopeLabels, type BackupPreview, type Plan, type Preview } from './contracts';
export function useCurrentPortability() {
 const {scope,credentialEpoch,getSnapshot} = useAuth(); const mounted = useRef(true);
 useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; },[]);
 return () => mounted.current && getSnapshot().scope === scope && getSnapshot().credentialEpoch === credentialEpoch && getSnapshot().status === 'authenticated';
}
export function PreviewDetails({preview}: {preview:Preview | BackupPreview}) {
 const {t} = useTranslation('portability');
 return <Card><div className="stack"><p role="status">{t('previewReady')}</p><dl><dt>{t('audience')}</dt><dd>{t(preview.audience === 'private_backup' ? 'backupAudience' : preview.audience === 'learner' ? 'learnerAudience' : 'teacherAudience')}</dd>{'package_version' in preview && <><dt>{t('packageVersion')}</dt><dd>{preview.package_version}</dd><dt>{t('compatibleVersions')}</dt><dd>{preview.compatible_versions.join(', ')}</dd></>}{'key_fingerprint' in preview && <><dt>{t('fingerprint')}</dt><dd className="prose">{preview.key_fingerprint}</dd></>}</dl>
 {'counts' in preview && <section><h3>{t('counts')}</h3><dl>{Object.entries(preview.counts).map(([key,count]) => <div key={key}><dt>{t(key,{defaultValue:key})}</dt><dd>{count}</dd></div>)}</dl></section>}
 {(['includes','excludes','warnings'] as const).map(key => <section key={key}><h3>{t(key)}</h3><ul>{preview[key].map((text,index) => <li key={index}>{scopeLabels[text] ? t(scopeLabels[text]) : text}</li>)}</ul></section>)}
 {'validation' in preview && <section><h3>{t('validation')}</h3><p>{t('validated')}</p></section>}</div></Card>;
}

export function CourseSelect({plans,value,onChange,disabled}: {plans:Plan[];value:string;onChange:(value:string)=>void;disabled?:boolean}) { const {t} = useTranslation('portability'); return <Field label={t('course')}><Select value={value} onChange={event => onChange(event.target.value)} disabled={disabled}><option value="">{t('chooseCourse')}</option>{plans.map(plan => <option key={plan.id} value={plan.id}>{plan.title}</option>)}</Select></Field>; }
