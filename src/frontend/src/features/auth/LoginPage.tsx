import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { Navigate, useLocation, useNavigate } from 'react-router';
import { useTranslation } from 'react-i18next';
import { BookOpen } from 'lucide-react';
import { useAuth } from '@/app/AuthProvider';
import { Button, Card, ErrorState, Field, Input, Select } from '@/components/ui';
import { safeReturnPath } from '@/app/route-contracts';
export function LoginPage({ reauth = false }: { reauth?: boolean }) {
 const { t, i18n } = useTranslation(); const auth = useAuth(); const navigate = useNavigate(); const location = useLocation(); const [error, setError] = useState<unknown>(null);
 const { register, handleSubmit, resetField, formState: { errors, isSubmitting } } = useForm<{ username: string; password: string }>({ defaultValues: { username: reauth ? auth.user?.username || '' : '', password: '' } });
 useEffect(() => { document.title = `${t(reauth ? 'auth.reauthTitle' : 'auth.title')} · SLMEducator`; }, [reauth, t]);
 if (!reauth && auth.status === 'authenticated') return <Navigate to="/inicio" replace/>;
 const submit = handleSubmit(async values => { setError(null); try { await auth.login(values.username, values.password); resetField('password'); if (!reauth) navigate(safeReturnPath(new URLSearchParams(location.search).get('return')), { replace: true }); } catch (failure) { setError(failure); resetField('password'); } });
 return <div className="auth-layout"><Card className="auth-card stack"><div className="brand"><BookOpen aria-hidden="true"/>{t('appName')}</div><h1>{t(reauth ? 'auth.reauthTitle' : 'auth.title')}</h1><p className="muted">{t(reauth ? 'auth.reauthDescription' : 'auth.description')}</p>{reauth && <p>{t('auth.otherAccount')}</p>}<form className="stack" onSubmit={submit} noValidate><ErrorState error={error || auth.error}/><Field label={t('username')} error={errors.username ? t('errors.required') : undefined}><Input autoComplete="username" {...register('username', { required: true })}/></Field><Field label={t('password')} error={errors.password ? t('errors.required') : undefined}><Input type="password" autoComplete="current-password" {...register('password', { required: true })}/></Field><Button type="submit" busy={isSubmitting}>{t(isSubmitting ? 'auth.submitting' : 'auth.submit')}</Button></form><Field label={t('language')}><Select value={i18n.language} onChange={event => void i18n.changeLanguage(event.target.value)}><option value="es">Español</option><option value="en">English</option></Select></Field>{reauth ? <div className="stack"><p className="muted">{t('auth.discardHiddenHint')}</p><Button variant="secondary" onClick={() => void auth.logout('keep')}>{t('auth.discardHidden')}</Button></div> : <p className="muted">{t('auth.noPublicRegistration')}</p>}</Card></div>;
}
