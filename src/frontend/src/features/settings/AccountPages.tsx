import { useState } from 'react';
import { Link } from 'react-router';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/app/AuthProvider';
import { useDirtyGuard } from '@/app/DirtyGuard';
import { ApiError } from '@/lib/api';
import { useInvalidate, useOperation, useResource } from '@/lib/query';
import { formatTimestamp } from '@/lib/time';
import { Badge, Button, Card, ConfirmDialog, ErrorState, Field, Input, LoadingState, PageHeader, SaveStatus } from '@/components/ui';
import { confirmPassword, invalid, parsed, parseProfile, passwordValid, profileValues, parseTimezone, parseBadges, type Profile, type ProfileValues } from './contracts';
import { SettingsBack, useCurrentSettings } from './shared';

export function SettingsPage() {
 const { t } = useTranslation('settings');
 return <div className="stack"><PageHeader title={t('title')} description={t('description')}/><p>{t('accountOnly')}</p><div className="grid">{[['perfil','profile'],['seguridad','security'],['apariencia','appearance'],['ia','ai'],['zona-horaria','timezone'],['datos','data']].map(([path,key]) => <Card key={path}><h2><Link to={`/ajustes/${path}`}>{t(key)}</Link></h2></Card>)}</div></div>;
}
export function ProfilePage() {
 const { user, scope } = useAuth(); const resource = useResource<unknown>(['settings','profile'], '/api/auth/me'); const result = parsed(resource.data, parseProfile);
 if (resource.isPending) return <LoadingState/>;
 if (resource.error || result.error || !result.data || result.data.id !== user?.id) return <ErrorState error={resource.error || result.error || new ApiError(200,'invalid',false,'invalidResponse')} retry={() => void resource.refetch()}/>;
 return <ProfileForm key={scope} initial={result.data}/>;
}
function ProfileForm({ initial }: { initial: Profile }) {
 const { t, i18n } = useTranslation('settings'); const { api, refreshIdentity } = useAuth(); const invalidate = useInvalidate(); const current = useCurrentSettings(); const [saved, setSaved] = useState(false);
 const timezone = useResource<unknown>(['settings','timezone'],'/api/settings/timezone'); const policy = parsed(timezone.data,parseTimezone);
 const form = useForm<ProfileValues>({ defaultValues: profileValues(initial) }); useDirtyGuard(form.formState.isDirty);
 const save = useOperation<ProfileValues, Profile>(async input => {
  const values = {first_name:input.first_name.trim(),last_name:input.last_name.trim(),email:input.email.trim().toLowerCase(),grade_level:input.grade_level.trim()};
  const raw = await api.patch<unknown>('/api/auth/profile', values); let profile: Profile; try { profile = parseProfile(raw); } catch { return invalid(true); }
  if (profile.id !== initial.id || profile.username !== initial.username || profile.role !== initial.role || profile.first_name !== values.first_name || profile.last_name !== values.last_name || profile.email !== values.email || (profile.grade_level || '') !== values.grade_level) return invalid(true);
  return profile;
 }, async profile => { if (!current()) return; form.reset(profileValues(profile)); setSaved(true); await invalidate(['settings','profile']); if (!current()) return; await refreshIdentity(); });
 return <div className="stack"><SettingsBack/><PageHeader title={t('profile')} description={t('profileDescription')}/><Card><div className="cluster"><strong>{initial.username}</strong><Badge>{t(initial.role)}</Badge></div><dl><dt>{t('created')}</dt><dd>{formatTimestamp(initial.created_at,{ locale:i18n.language,timezone:policy.data?.timezone,unknownLabel:t('unknownTime') })}</dd><dt>{t('lastLogin')}</dt><dd>{formatTimestamp(initial.last_login,{ locale:i18n.language,timezone:policy.data?.timezone,unknownLabel:t('unknownTime') })}</dd></dl></Card>
 <OwnBadges timezone={policy.data?.timezone}/><ErrorState error={timezone.error || policy.error}/><Card><form className="stack" onSubmit={form.handleSubmit(value => save.mutate(value))} onChange={() => setSaved(false)}><fieldset disabled={save.isPending} className="form-grid">
 <Field label={t('firstName')} error={form.formState.errors.first_name?.message}><Input autoComplete="given-name" {...form.register('first_name',{ required:t('required'),validate:v => !!v.trim() || t('required') })}/></Field>
 <Field label={t('lastName')} error={form.formState.errors.last_name?.message}><Input autoComplete="family-name" {...form.register('last_name',{ required:t('required'),validate:v => !!v.trim() || t('required') })}/></Field>
 <Field label={t('email')} error={form.formState.errors.email?.message}><Input type="email" autoComplete="email" {...form.register('email',{ required:t('required'),pattern:{value:/^[^\s@]+@[^\s@]+\.[^\s@]+$/,message:t('emailInvalid')} })}/></Field>
 {initial.role === 'student' && <Field label={t('grade')}><Input {...form.register('grade_level')}/></Field>}</fieldset><Button type="submit" busy={save.isPending}>{t('save')}</Button><ErrorState error={save.error}/><SaveStatus state={save.error?.uncertain ? 'uncertain' : save.isPending ? 'saving' : form.formState.isDirty ? 'dirty' : saved ? 'saved' : 'idle'}>{saved ? t('profileSaved') : undefined}</SaveStatus></form></Card></div>;
}
interface PasswordValues { current_password: string; new_password: string; repeat: string }
const blankPasswords: PasswordValues = { current_password:'',new_password:'',repeat:'' };
export function PasswordPage() { const { scope } = useAuth(); return <PasswordForm key={scope}/>; }
function PasswordForm() {
 const { t } = useTranslation('settings'); const { api, requireReauthentication } = useAuth(); const current = useCurrentSettings(); const [confirm, setConfirm] = useState(false); const [saved, setSaved] = useState(false);
 const form = useForm<PasswordValues>({ defaultValues:blankPasswords }); useDirtyGuard(form.formState.isDirty);
 // Void variables prevent secret credentials from entering the mutation cache.
 const change = useOperation<void, boolean>(async () => {
  const values = form.getValues(); const response = await api.post<unknown>('/api/auth/change-password',{current_password:values.current_password,new_password:values.new_password}); return confirmPassword(response);
 }, () => { if (!current()) return; form.reset(blankPasswords); setConfirm(false); setSaved(true); requireReauthentication(); });
 return <div className="stack"><SettingsBack/><PageHeader title={t('security')} description={t('passwordEffect')}/><Card><form className="stack" onSubmit={form.handleSubmit(() => setConfirm(true))}>
 <fieldset disabled={change.isPending} className="stack"><Field label={t('currentPassword')} error={form.formState.errors.current_password?.message}><Input type="password" autoComplete="current-password" {...form.register('current_password',{required:t('required')})}/></Field>
 <Field label={t('newPassword')} hint={t('passwordHint')} error={form.formState.errors.new_password?.message}><Input type="password" autoComplete="new-password" {...form.register('new_password',{validate:v => passwordValid(v) || t('passwordHint')})}/></Field>
 <Field label={t('repeatPassword')} error={form.formState.errors.repeat?.message}><Input type="password" autoComplete="new-password" {...form.register('repeat',{validate:v => v === form.getValues('new_password') || t('passwordMismatch')})}/></Field></fieldset>
 <p className="muted">{t('secretMemory')}</p><Button type="submit" busy={change.isPending}>{t('passwordChange')}</Button><ErrorState error={change.error}/>{saved && <p role="status">{t('passwordSaved')}</p>}</form></Card>
 <ConfirmDialog open={confirm} onOpenChange={setConfirm} title={t('passwordConfirm')} description={t('passwordEffect')} confirmLabel={t('passwordChange')} busy={change.isPending} onConfirm={() => { void form.handleSubmit(() => { void change.mutateAsync(undefined).catch(() => { if (current()) setConfirm(false); }); })(); }}/></div>;
}

function OwnBadges({timezone}: {timezone?:string}) {
 const {t,i18n} = useTranslation('settings'); const resource = useResource<unknown>(['settings','own-badges'],'/api/gamification/badges'); const result = parsed(resource.data,parseBadges); const earned = result.data?.filter(badge => badge.earned);
 return <Card><h2>{t('earnedBadges')}</h2><p className="muted">{t('badgesHint')}</p>{resource.isPending && <LoadingState/>}<ErrorState error={resource.error || result.error} retry={() => void resource.refetch()}/>{earned && !resource.error && <>{earned.length ? <ul>{earned.map(badge => <li key={badge.id}><strong>{badge.name}</strong> · {formatTimestamp(badge.earned_at,{timezone,locale:i18n.language,unknownLabel:t('unknownTime'),dateOnly:true})}</li>)}</ul> : <p>{t('noBadges')}</p>}</>}</Card>;
}
