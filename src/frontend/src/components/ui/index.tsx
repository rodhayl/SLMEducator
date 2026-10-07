import { cloneElement, isValidElement, useEffect, useId, useRef, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactElement, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react';
import { Dialog } from '@base-ui/react/dialog';
import { useTranslation } from 'react-i18next';
import { usePrivacyStatus } from '@/app/PrivacyContext';
import { ApiError } from '@/lib/api';
export function Button({ variant = 'primary', busy, className = '', children, disabled, type = 'button', ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'danger' | 'ghost'; busy?: boolean }) { return <button {...props} type={type} disabled={disabled || busy} aria-busy={busy || undefined} className={`button button--${variant} ${className}`}>{children}</button>; }
export function Input(props: InputHTMLAttributes<HTMLInputElement>) { return <input {...props} className={`input ${props.className || ''}`} />; }
export function Textarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) { return <textarea {...props} className={`input textarea ${props.className || ''}`} />; }
export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) { return <select {...props} className={`input ${props.className || ''}`} />; }
export function Field({ label, error, hint, children }: { label: ReactNode; error?: ReactNode; hint?: ReactNode; children: ReactNode }) {
 const id = useId(); const control = isValidElement(children) ? children as ReactElement<{ id?: string; 'aria-invalid'?: boolean; 'aria-describedby'?: string }> : null;
 const controlId = control?.props.id || id;
 return <div className="field"><label htmlFor={controlId}>{label}</label>{control ? cloneElement(control, { id: controlId, 'aria-invalid': !!error, 'aria-describedby': [control.props['aria-describedby'], hint ? `${id}-hint` : '', error ? `${id}-error` : ''].filter(Boolean).join(' ') || undefined }) : children}{hint && <p className="field-hint" id={`${id}-hint`}>{hint}</p>}{error && <p className="field-error" id={`${id}-error`}>{error}</p>}</div>;
}
export function Card({ children, className = '' }: { children: ReactNode; className?: string }) { return <section className={`card ${className}`}>{children}</section>; }
export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'success' | 'warning' | 'danger' }) { return <span className={`badge badge--${tone}`}>{children}</span>; }
export function PageHeader({ title, description, actions }: { title: string; description?: ReactNode; actions?: ReactNode }) { const heading = useRef<HTMLHeadingElement>(null); const privacy = usePrivacyStatus(); useEffect(() => { if (privacy === "authenticated" && heading.current && !heading.current.closest("[hidden], [inert]")) { document.title = `${title} · SLMEducator`; if (!document.querySelector("[role=dialog]")) heading.current.focus({ preventScroll: true }); } }, [title, privacy]); return <header className="page-header"><div><h1 ref={heading} tabIndex={-1}>{title}</h1>{description && <p className="muted">{description}</p>}</div>{actions && <div className="cluster">{actions}</div>}</header>; }
export function ErrorState({ error, retry }: { error: unknown; retry?: () => void }) {
 const { t } = useTranslation(); if (!error) return null;
 const safe = error instanceof ApiError ? error : new ApiError();
 return <div className="error-state" role="alert"><p>{t(`errors.${safe.messageKey}`, { defaultValue: t('errors.failed') })}</p>{Object.entries(safe.fieldErrors).length > 0 && <ul>{Object.entries(safe.fieldErrors).map(([field, message]) => <li key={field}>{t(`fields.${field}`)}: {t(`errors.${message}`)}</li>)}</ul>}{retry && <Button variant="secondary" onClick={retry}>{t('retry')}</Button>}</div>;
}
export function LoadingState() { const { t } = useTranslation(); return <p role="status" className="loading-state">{t('loading')}</p>; }
export function EmptyState({ title, description, action }: { title: string; description?: ReactNode; action?: ReactNode }) { return <div className="empty-state"><h2>{title}</h2>{description && <p className="muted">{description}</p>}{action}</div>; }
export function SaveStatus({ state, children }: { state: 'idle' | 'dirty' | 'saving' | 'saved' | 'uncertain'; children?: ReactNode }) { const { t } = useTranslation(); return <p className={`save-status save-status--${state}`} role="status">{children || t(state)}</p>; }
export function ConfirmDialog({ open, onOpenChange, title, description, confirmLabel, onConfirm, destructive, busy, children }: { open: boolean; onOpenChange: (value: boolean) => void; title: string; description: ReactNode; confirmLabel: string; onConfirm: () => void; destructive?: boolean; busy?: boolean; children?: ReactNode }) {
 const { t } = useTranslation(); const privacyStatus = usePrivacyStatus();
 return <Dialog.Root open={open && privacyStatus === 'authenticated'} onOpenChange={onOpenChange}><Dialog.Portal><Dialog.Backdrop className="dialog-backdrop"/><Dialog.Popup className="dialog"><Dialog.Title>{title}</Dialog.Title><Dialog.Description>{description}</Dialog.Description>{children}<div className="cluster dialog-actions"><Button variant="secondary" onClick={() => onOpenChange(false)} disabled={busy}>{t('cancel')}</Button><Button variant={destructive ? 'danger' : 'primary'} onClick={onConfirm} busy={busy}>{confirmLabel}</Button></div></Dialog.Popup></Dialog.Portal></Dialog.Root>;
}
