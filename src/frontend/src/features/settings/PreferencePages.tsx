import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/app/AuthProvider';
import { useAppearance, type ReadingSize } from '@/app/AppearanceProvider';
import { useDirtyGuard } from '@/app/DirtyGuard';
import { ApiError } from '@/lib/api';
import { useInvalidate, useOperation, useResource } from '@/lib/query';
import { validTimezone } from '@/lib/time';
import { Button, Card, ErrorState, Field, Input, LoadingState, PageHeader, SaveStatus, Select } from '@/components/ui';
import { invalid, parsed, parseApp, parseStatus, parseTimezone, type AppConfig, type TimezonePolicy } from './contracts';
import { SettingsBack, useCurrentSettings } from './shared';
export function AppearancePage() {
 const { scope } = useAuth(); const resource = useResource<unknown>(['settings','app'],'/api/settings/app'); const result = parsed(resource.data,parseApp);
 if (resource.isPending) return <LoadingState/>; if (resource.error || result.error || !result.data) return <ErrorState error={resource.error || result.error} retry={() => void resource.refetch()}/>;
 return <AppearanceForm key={scope} initial={result.data}/>;
}
function AppearanceForm({ initial }: { initial: AppConfig }) {
 const { t,i18n } = useTranslation('settings'); const { api } = useAuth(); const appearance = useAppearance(); const invalidate = useInvalidate(); const current = useCurrentSettings(); const [saved,setSaved] = useState(false);
 const form = useForm<AppConfig>({defaultValues:initial}); useDirtyGuard(form.formState.isDirty);
 const save = useOperation<AppConfig,AppConfig>(async values => { let response: AppConfig; try { response = parseApp(await api.post('/api/settings/app',values)); } catch (error) { if (error instanceof ApiError && error.kind !== 'invalid') throw error; return invalid(true); } if (Object.keys(values).some(key => values[key as keyof AppConfig] !== response[key as keyof AppConfig])) return invalid(true); return response; }, async value => {
  if (!current()) return; form.reset(value); setSaved(true);
  appearance.setTheme(value.theme === 'auto' ? 'system' : value.theme); const sizes: Record<AppConfig['font_size'],ReadingSize> = {small:16,medium:18,large:20,'extra-large':24}; appearance.setReadingSize(sizes[value.font_size]); appearance.setAnimations(value.enable_animations);
  await i18n.changeLanguage(value.language); if (!current()) return; await invalidate(['settings','app']);
 });
 return <div className="stack"><SettingsBack/><PageHeader title={t('appearance')} description={t('appearanceHint')}/><Card><form className="stack" onSubmit={form.handleSubmit(values => save.mutate(values))} onChange={() => setSaved(false)}><fieldset disabled={save.isPending} className="form-grid">
 <Field label={t('theme')}><Select {...form.register('theme')}><option value="auto">{t('system')}</option><option value="light">{t('light')}</option><option value="dark">{t('dark')}</option></Select></Field>
 <Field label={t('language')}><Select {...form.register('language')}><option value="es">{t('spanish')}</option><option value="en">{t('english')}</option></Select></Field>
 <Field label={t('readingSize')}><Select {...form.register('font_size')}><option value="small">{t('small')}</option><option value="medium">{t('medium')}</option><option value="large">{t('large')}</option><option value="extra-large">{t('extraLarge')}</option></Select></Field>
 <Field label={t('animations')}><Input type="checkbox" {...form.register('enable_animations')}/></Field></fieldset><Button type="submit" busy={save.isPending}>{t('save')}</Button><ErrorState error={save.error}/><SaveStatus state={save.error?.uncertain ? 'uncertain' : save.isPending ? 'saving' : form.formState.isDirty ? 'dirty' : saved ? 'saved' : 'idle'}>{saved ? t('appearanceSaved') : undefined}</SaveStatus></form></Card></div>;
}
export function TimezonePage() {
 const { scope } = useAuth(); const resource = useResource<unknown>(['settings','timezone'],'/api/settings/timezone'); const result = parsed(resource.data,parseTimezone);
 if (resource.isPending) return <LoadingState/>; if (resource.error || result.error || !result.data) return <ErrorState error={resource.error || result.error} retry={() => void resource.refetch()}/>;
 return <TimezoneForm key={scope} initial={result.data}/>;
}
function TimezoneForm({ initial }: { initial: TimezonePolicy }) {
 const { t } = useTranslation('settings'); const { api } = useAuth(); const invalidate = useInvalidate(); const current = useCurrentSettings(); const [policy,setPolicy] = useState(initial); const [saved,setSaved] = useState(false);
 const form = useForm<{timezone:string}>({defaultValues:{timezone:initial.timezone}}); useDirtyGuard(form.formState.isDirty);
 const save = useOperation<{timezone:string},TimezonePolicy>(async values => { const raw = await api.put('/api/settings/timezone',values); let value: TimezonePolicy; try { value = parseTimezone(raw); } catch { return invalid(true); } if (value.timezone !== values.timezone || value.timezone_source !== 'user') return invalid(true); return value; }, async value => { if (!current()) return; form.reset({timezone:value.timezone}); setPolicy(value); setSaved(true); await invalidate(); });
 return <div className="stack"><SettingsBack/><PageHeader title={t('timezone')} description={t('timezoneDescription')}/><Card><p>{t(policy.timezone_source === 'default' ? 'sourceDefault' : 'sourceUser')}</p><p>{t('localDate',{date:policy.local_date})}</p><p>{t('timePolicy')}</p><form className="stack" onSubmit={form.handleSubmit(values => save.mutate(values))} onChange={() => setSaved(false)}><Field label={t('timezone')} hint={t('timezoneHint')} error={form.formState.errors.timezone?.message}><Input disabled={save.isPending} {...form.register('timezone',{validate:value => validTimezone(value) || t('timezoneInvalid')})}/></Field><Button type="submit" busy={save.isPending}>{t('save')}</Button><ErrorState error={save.error}/><SaveStatus state={save.error?.uncertain ? 'uncertain' : save.isPending ? 'saving' : form.formState.isDirty ? 'dirty' : saved ? 'saved' : 'idle'}>{saved ? t('timezoneSaved') : undefined}</SaveStatus></form></Card></div>;
}
export function ApplicationStatusPage() { const { user } = useAuth(); return user?.role === 'admin' ? <ApplicationStatus/> : <ErrorState error={new ApiError(403,'http',false,'unavailable')}/>; }
function ApplicationStatus() {
 const { t } = useTranslation('settings'); const resource = useResource<unknown>(['settings','status'],'/api/status'); const result = parsed(resource.data,parseStatus);
 return <div className="stack"><PageHeader title={t('status')} description={t('statusDescription')}/>{resource.isPending && <LoadingState/>}<ErrorState error={resource.error || result.error}/>{result.data && <Card><p role="status">{t('online')}</p><p>{t('version',{version:result.data.version})}</p></Card>}<Button variant="secondary" busy={resource.isFetching} onClick={() => void resource.refetch()}>{t('retry')}</Button><Card><p>{t('statusLimits')}</p><p>{t('statusGuide')}</p></Card></div>;
}
