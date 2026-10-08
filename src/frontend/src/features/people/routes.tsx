import { useEffect, useId, useRef, useState } from 'react';
import { Link, useLocation, useParams, useSearchParams, type RouteObject } from 'react-router';
import { useForm, type FieldPath } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/app/AuthProvider';
import { useDirtyGuard } from '@/app/DirtyGuard';
import { ApiError } from '@/lib/api';
import { positiveId } from '@/lib/ids';
import { useInvalidate, useOperation, useResource } from '@/lib/query';
import type { Role, User } from '@/lib/types';
import { Badge, Button, Card, ConfirmDialog, EmptyState, ErrorState, Field, Input, LoadingState, PageHeader, SaveStatus, Select, Textarea } from '@/components/ui';
import {
  accountRoles, confirmEnrollment, confirmNotes, confirmRecovery, confirmStatus, createPayload,
  isRole, parseCreated, parseNotes, parsePeople, parsePersonDetail, parseProgress, peoplePath, personName,
  validPassword, validationResult, PEOPLE_LIMIT, type CreateValues, type Person,
} from './model';

const listUrl = '/personas';
function detailUrl(person: Person, role: Role) {
  return role === 'teacher' ? `/estudiantes/${person.id}` : `/personas/${person.id}`;
}
function unavailable() { return new ApiError(403, 'http', false, 'unavailable'); }
function usePeople(role: Role | '', includeInactive: boolean, enabled = true) {
  const resource = useResource<unknown>(['people', role, includeInactive], enabled ? peoplePath(role, includeInactive) : null);
  const parsed = validationResult(resource.data, parsePeople);
  return { ...resource, data: parsed.data, error: resource.error || parsed.error };
}
function useReportDirty(dirty: boolean, report: (dirty: boolean) => void) {
  useEffect(() => { report(dirty); return () => report(false); }, [dirty, report]);
}
function listFilters(params:URLSearchParams) {
  const result=new URLSearchParams();for(const key of ['role','state','q']){const value=params.get(key);if(value)result.set(key,value);}
  return result.size?'?'+result:'';
}
function BackLink() {
  const { t } = useTranslation('people'),[params]=useSearchParams(),location=useLocation();
  const {personId,studentId}=useParams(),id=positiveId(personId||studentId),filter=listFilters(params);
  return <Link to={`${listUrl}${filter}${id&&(filter||location.state?.listOrigin===listUrl)?'#person-'+id:''}`}>{t('back')}</Link>;
}

/** Both staff roles enter the same context-aware list; student access does no reads. */
export function PeoplePage() {
  const { user, scope } = useAuth();
  return user && user.role !== 'student'
    ? <PeopleList key={`${scope}:${user.role}`} actor={user} /> : <ErrorState error={unavailable()} />;
}
function PeopleList({ actor }: { actor: User }) {
  const { t } = useTranslation('people');
  const admin = actor.role === 'admin';
  const [params, setParams] = useSearchParams();
  const requestedRole = params.get('role');
  const role: Role | '' = admin ? (isRole(requestedRole) ? requestedRole : '') : 'student';
  const requestedState = params.get('state');
  const state = admin && (requestedState === 'inactive' || requestedState === 'all') ? requestedState : 'active';
  const search = params.get('q') || '';
  const setFilter = (key: string, value: string) => setParams(previous => {
    const next = new URLSearchParams(previous);
    if (value) next.set(key, value); else next.delete(key);
    return next;
  }, { replace: key === 'q', flushSync: key === 'q', preventScrollReset: true });
  const people = usePeople(role, admin && state !== 'active');
  const filtered = people.data?.filter(person => (state !== 'inactive' || !person.active) &&
    `${personName(person)} ${person.username} ${person.email}`.toLocaleLowerCase().includes(search.toLocaleLowerCase()));
  return <div className="stack">
    <PageHeader title={t(admin ? 'people' : 'students')} description={t(admin ? 'peopleDescription' : 'studentsDescription')}
      actions={<Link to={`/personas/nueva${listFilters(params)}`} state={{listOrigin:listUrl}}>{t(admin ? 'createPerson' : 'createStudent')}</Link>} />
    <Card><div className="toolbar">
      {admin && <Field label={t('filterRole')}><Select aria-label={t('filterRole')} value={role} onChange={event => setFilter('role', isRole(event.target.value) ? event.target.value : '')}>
        <option value="">{t('allRoles')}</option>{accountRoles.map(value => <option key={value} value={value}>{t(value)}</option>)}
      </Select></Field>}
      {admin && <Field label={t('filterState')}><Select aria-label={t('filterState')} value={state} onChange={event => setFilter('state', event.target.value)}>
        <option value="active">{t('activeOnly')}</option><option value="all">{t('allStates')}</option><option value="inactive">{t('inactiveOnly')}</option>
      </Select></Field>}
      <Field label={t('search')} hint={t('searchHint')}><Input type="search" aria-label={t('search')} value={search} onChange={event => setFilter('q', event.target.value)} /></Field>
    </div></Card>
    {people.isPending && <LoadingState />}
    {people.error && <ErrorState error={people.error} retry={() => void people.refetch()} />}
    {!people.isPending && !people.error && filtered && <>
      <p className="muted">{t('count', { count: filtered.length })}</p>
      {people.data && people.data.length >= PEOPLE_LIMIT && <p role="status">{t('listLimit')}</p>}
      {!filtered.length ? <EmptyState title={t(admin ? 'empty' : 'emptyStudents')} description={t(admin ? 'emptyDescription' : 'emptyStudentsDescription')} /> :
        <div className="table-wrap"><table><thead><tr><th scope="col">{t('name')}</th><th scope="col">{t('role')}</th><th scope="col">{t('status')}</th><th scope="col">{t('email')}</th></tr></thead>
          <tbody>{filtered.map(person => <tr key={person.id}>
            <th scope="row"><Link id={`person-${person.id}`} to={`${detailUrl(person, actor.role)}${listFilters(params)}`} state={{listOrigin:listUrl}} aria-label={t('openPerson', { name: personName(person) })}>{personName(person)}</Link><div className="muted">{person.username}</div></th>
            <td>{t(person.role)}</td><td><Badge>{t(person.active ? 'active' : 'inactive')}</Badge></td><td>{person.email}</td>
          </tr>)}</tbody></table></div>}
    </>}
    {admin && <p className="muted">{t('listExcludesSelf')}</p>}
  </div>;
}

export function CreatePersonPage() {
  const { user, scope } = useAuth();
  const [params] = useSearchParams(); const requestedRole = params.getAll('role').length === 1 ? params.get('role') : null;
  const initialRole = user?.role === 'teacher' ? 'student' : isRole(requestedRole) ? requestedRole : '';
  return user && user.role !== 'student'
    ? <CreatePersonForm key={`${scope}:${user.role}:${initialRole}`} actor={user} initialRole={initialRole} /> : <ErrorState error={unavailable()} />;
}
const emptyForm = (actor: User): CreateValues => ({ first_name: '', last_name: '', username: '', email: '', password: '', role: actor.role === 'teacher' ? 'student' : '' });
function CreatePersonForm({ actor, initialRole }: { actor: User; initialRole: Role | '' }) {
  const [params]=useSearchParams();
  const { t } = useTranslation('people');
  const { t: errorsT } = useTranslation();
  const { api } = useAuth();
  const invalidate = useInvalidate();
  const [created, setCreated] = useState<Person | null>(null);
  const pending = useRef<CreateValues | null>(null);
  const form = useForm<CreateValues>({ defaultValues: { ...emptyForm(actor), role: initialRole } });
  const operation = useOperation<void, Person>(async () => {
    if (!pending.current) throw new ApiError(422, 'invalid', false, 'validation');
    const payload = createPayload(pending.current, actor);
    const response = await api.post<unknown>('/api/auth/register', payload);
    return parseCreated(response, payload);
  }, async person => {
    pending.current = null; form.reset(emptyForm(actor)); setCreated(person);
    await invalidate(['people']);
  });
  useDirtyGuard(form.formState.isDirty);
  const submit = form.handleSubmit(async values => {
    if (operation.isPending || operation.error?.uncertain) return;
    pending.current = values;
    try { await operation.mutateAsync(); }
    catch (error) {
      if (error instanceof ApiError) {
        const names = ['first_name', 'last_name', 'username', 'email', 'password', 'role'] as const;
        let first: FieldPath<CreateValues> | undefined;
        for (const name of names) {
          const key = error.fieldErrors[name];
          if (key) { form.setError(name, { type: 'server', message: errorsT(`errors.${key}`) }); first ??= name; }
        }
        if (first) form.setFocus(first);
      }
    } finally { pending.current = null; }
  });
  if (created) return <div className="stack">
    <PageHeader title={t('created')} description={t('createdDescription', { name: personName(created) })} />
    <Card><div className="cluster">
      <Link to={`${detailUrl(created, actor.role)}${listFilters(params)}`} state={{listOrigin:listUrl}}>{t(actor.role === 'admin' && created.role === 'student' ? 'enrollNext' : 'openCreated')}</Link>
      <BackLink /><Button variant="secondary" onClick={() => { setCreated(null); operation.reset(); }}>{t('createAnother')}</Button>
    </div></Card>
  </div>;
  const required = { required: t('required'), validate: (value: string) => value.trim().length > 0 || t('required') };
  return <div className="stack">
    <BackLink /><PageHeader title={t(actor.role === 'teacher' ? 'createStudent' : 'createHeading')} description={t('createDescription')} />
    <form className="stack form-page" onSubmit={submit} noValidate>
      {operation.error && <ErrorState error={operation.error} />}
      {operation.error?.uncertain && <Card><p role="status">{t('uncertainCreate')}</p><Link to={listUrl}>{t('checkList')}</Link></Card>}
      {Object.keys(form.formState.errors).length > 0 && <p role="alert">{t('validationSummary')}</p>}
      <Card><h2>{t('identity')}</h2><div className="form-grid">
        <Field label={t('firstName')} error={form.formState.errors.first_name?.message}><Input aria-label={t('firstName')} autoComplete="given-name" aria-invalid={!!form.formState.errors.first_name} {...form.register('first_name', required)} /></Field>
        <Field label={t('lastName')} error={form.formState.errors.last_name?.message}><Input aria-label={t('lastName')} autoComplete="family-name" aria-invalid={!!form.formState.errors.last_name} {...form.register('last_name', required)} /></Field>
        <Field label={t('email')} error={form.formState.errors.email?.message}><Input aria-label={t('email')} type="email" autoComplete="email" aria-invalid={!!form.formState.errors.email} {...form.register('email', { required: t('required'), pattern: { value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/, message: t('invalidEmail') } })} /></Field>
      </div></Card>
      <Card><h2>{t('access')}</h2><div className="form-grid">
        <Field label={t('username')} error={form.formState.errors.username?.message}><Input aria-label={t('username')} autoComplete="off" autoCapitalize="none" aria-invalid={!!form.formState.errors.username} {...form.register('username', required)} /></Field>
        <Field label={t('password')} hint={t('passwordHint')} error={form.formState.errors.password?.message}><Input aria-label={t('password')} type="password" autoComplete="new-password" aria-invalid={!!form.formState.errors.password} {...form.register('password', { validate: value => validPassword(value, 8) || t('passwordInvalid') })} /></Field>
        {actor.role === 'admin' ? <Field label={t('role')} error={form.formState.errors.role?.message}><Select aria-label={t('role')} aria-invalid={!!form.formState.errors.role} {...form.register('role', { required: t('required') })}>
          <option value="">{t('chooseRole')}</option>{accountRoles.map(role => <option key={role} value={role}>{t(role)}</option>)}
        </Select></Field> : <p>{t('teacherCreateHint')}</p>}
      </div>{actor.role === 'admin' && <p className="muted">{t('separateEnrollment')}</p>}</Card>
      <div className="cluster"><Button type="submit" busy={operation.isPending} disabled={operation.isPending || !!operation.error?.uncertain}>{t('create')}</Button><BackLink />
        <SaveStatus state={operation.error?.uncertain ? 'uncertain' : operation.isPending ? 'saving' : form.formState.isDirty ? 'dirty' : 'idle'} />
      </div>
    </form>
  </div>;
}

export function PersonDetailPage() {
  const { user, scope } = useAuth();
  const { personId, studentId } = useParams();
  const id = positiveId(personId ?? studentId);
  return user && user.role !== 'student' && id
    ? <PersonDetail key={`${scope}:${user.role}:${id}`} actor={user} id={id} /> : <ErrorState error={unavailable()} />;
}
function PersonDetail({ actor, id }: { actor: User; id: number }) {
  const resource = useResource<unknown>(['people', id, 'detail'], `/api/auth/users/${id}`);
  const parsed = validationResult(resource.data, data => parsePersonDetail(data, id));
  const error = resource.error || parsed.error;
  async function refresh() {
    const result = await resource.refetch();
    if (result.error) throw result.error;
    return parsePersonDetail(result.data, id);
  }
  return <div className="stack">
    {resource.isPending && <LoadingState />}
    {error && <><BackLink /><ErrorState error={error} retry={() => void resource.refetch()} /></>}
    {parsed.data && <div hidden={!!error} inert={!!error}><PersonDetails actor={actor} person={parsed.data} refresh={refresh} /></div>}
  </div>;
}
function PersonDetails({ actor, person, refresh }: { actor: User; person: Person; refresh: () => Promise<Person> }) {
  const { t } = useTranslation('people');
  const [notesDirty, reportNotes] = useState(false);
  const [enrollmentDirty, reportEnrollment] = useState(false);
  const [recoveryDirty, reportRecovery] = useState(false);
  useDirtyGuard(notesDirty || enrollmentDirty || recoveryDirty);
  return <div className="stack">
    <BackLink /><PageHeader title={personName(person)} description={person.username} actions={<div className="cluster"><Badge>{t(person.active ? 'active' : 'inactive')}</Badge>{person.role === 'student' && person.active && <Link to={`/mensajes?recipient_id=${person.id}&compose=1`}>{t('sendMessage')}</Link>}</div>} />
    <Card><h2>{t('profile')}</h2><dl className="grid"><div><dt>{t('role')}</dt><dd>{t(person.role)}</dd></div><div><dt>{t('email')}</dt><dd>{person.email}</dd></div></dl></Card>
    {person.role === 'student' && <>
      <Enrollment person={person} actor={actor} onDirty={reportEnrollment} refresh={refresh} />
      <Progress studentId={person.id} />
      <PrivateNotes studentId={person.id} onDirty={reportNotes} />
    </>}
    {actor.role === 'admin' && <AccountActions person={person} actor={actor} onDirty={reportRecovery} refresh={refresh} />}
  </div>;
}

function Enrollment({ person, actor, onDirty, refresh }: { person: Person; actor: User; onDirty: (value: boolean) => void; refresh: () => Promise<Person> }) {
  const { t } = useTranslation('people');
  const teachers = usePeople('teacher', false, actor.role === 'admin');
  if (actor.role === 'teacher') return <Card><h2>{t('enrollment')}</h2><p>{t(person.teacher_id === actor.id ? 'assignedToYou' : 'legacyEnrollment')}</p></Card>;
  return <Card><h2>{t('enrollment')}</h2><p>{t('enrollmentDescription')}</p>
    {teachers.isPending && <LoadingState />}
    {teachers.error && <ErrorState error={teachers.error} retry={() => void teachers.refetch()} />}
    {teachers.data && <div hidden={!!teachers.error} inert={!!teachers.error}><EnrollmentForm person={person} teachers={teachers.data.filter(item => item.role === 'teacher' && item.active)} onDirty={onDirty} refresh={refresh} /></div>}
  </Card>;
}
function EnrollmentForm({ person, teachers, onDirty, refresh }: { person: Person; teachers: Person[]; onDirty: (value: boolean) => void; refresh: () => Promise<Person> }) {
  const { t } = useTranslation('people');
  const { api } = useAuth();
  const invalidate = useInvalidate();
  const form = useForm({ defaultValues: { teacher: person.teacher_id === null ? '' : String(person.teacher_id) } });
  const [confirm, setConfirm] = useState(false);
  const [selection, setSelection] = useState<number | null>(null);
  useReportDirty(form.formState.isDirty, onDirty);
  const operation = useOperation<number | null, void>(async teacherId => {
    const result = await api.put<unknown>(`/api/students/${person.id}/teacher`, { teacher_id: teacherId });
    confirmEnrollment(result, person.id, teacherId);
  }, async (_, teacherId) => {
    form.reset({ teacher: teacherId === null ? '' : String(teacherId) }); setConfirm(false);
    await invalidate(['people']);
  });
  const check = useOperation<void, Person>(refresh, server => {
    const selection = form.getValues('teacher');
    const saved = server.teacher_id === null ? '' : String(server.teacher_id);
    form.reset({ teacher: saved });
    if (selection !== saved) form.setValue('teacher', selection, { shouldDirty: true });
    operation.reset();
  });
  const open = form.handleSubmit(values => {
    const selected = values.teacher === '' ? null : positiveId(values.teacher);
    if (values.teacher !== '' && (!selected || !teachers.some(person => person.id === selected))) return;
    setSelection(selected); setConfirm(true);
  });
  const chosen = teachers.find(item => item.id === selection);
  const targetName = selection === null ? t('noTeacher') : chosen ? `${personName(chosen)} (${chosen.username})` : t('teacherId', { id: selection });
  const current = teachers.find(item => item.id === person.teacher_id);
  return <form className="stack" onSubmit={open}>
    <p>{t('currentTeacher')}: {person.teacher_id === null ? t('noTeacher') : current ? personName(current) : t('teacherId', { id: person.teacher_id })}</p>
    <Field label={t('chooseTeacher')}><Select aria-label={t('chooseTeacher')} {...form.register('teacher')}>
      <option value="">{t('noTeacher')}</option>
      {person.teacher_id !== null && !current && <option value={person.teacher_id} disabled>{t('teacherId', { id: person.teacher_id })}</option>}
      {teachers.map(person => <option key={person.id} value={person.id}>{personName(person)} ({person.username})</option>)}
    </Select></Field>
    {teachers.length >= PEOPLE_LIMIT && <p>{t('teacherListLimit')}</p>}
    {operation.error && <ErrorState error={operation.error} />}
    {operation.error?.uncertain && <><p role="status">{t('uncertainAction')}</p><Button variant="secondary" busy={check.isPending} onClick={() => check.mutate()}>{t('refresh')}</Button></>}
    {check.error && <ErrorState error={check.error} />}{check.isSuccess && !operation.isSuccess && <p role="status">{t('checkedEnrollment')}</p>}
    {operation.isSuccess && <p role="status">{t('enrolled')}</p>}
    <div className="cluster"><Button type="submit" disabled={operation.isPending || !!operation.error?.uncertain}>{t('changeEnrollment')}</Button>
      <SaveStatus state={operation.error?.uncertain ? 'uncertain' : operation.isPending ? 'saving' : form.formState.isDirty ? 'dirty' : operation.isSuccess ? 'saved' : 'idle'} /></div>
    <ConfirmDialog open={confirm} onOpenChange={setConfirm} title={t('confirmEnrollment')} description={t('confirmEnrollmentDescription', { student: `${personName(person)} (${person.username})`, teacher: targetName })}
      confirmLabel={t('changeEnrollment')} busy={operation.isPending} onConfirm={() => { if (!operation.error?.uncertain) void operation.mutateAsync(selection).catch(() => undefined).finally(() => setConfirm(false)); }} />
  </form>;
}

function Progress({ studentId }: { studentId: number }) {
  const { t, i18n } = useTranslation('people');
  const resource = useResource<unknown>(['people', studentId, 'progress'], `/api/students/${studentId}/progress`);
  const parsed = validationResult(resource.data, parseProgress);
  const error = resource.error || parsed.error;
  return <Card><h2>{t('progress')}</h2>
    {resource.isPending && <LoadingState />}{error && <ErrorState error={error} retry={() => void resource.refetch()} />}
    {!error && parsed.data && <><dl className="grid">
      <div><dt>{t('lessons')}</dt><dd>{parsed.data.lessons_completed}</dd></div><div><dt>{t('assessments')}</dt><dd>{parsed.data.assessments_taken}</dd></div>
      <div><dt>{t('average')}</dt><dd>{parsed.data.avg_score === null ? t('noScore') : new Intl.NumberFormat(i18n.language, { maximumFractionDigits: 1, style: 'percent' }).format(parsed.data.avg_score / 100)}</dd></div>
      <div><dt>{t('studyTime')}</dt><dd>{t('hours', { value: new Intl.NumberFormat(i18n.language, { maximumFractionDigits: 1 }).format(parsed.data.study_time_hours) })}</dd></div>
    </dl><p className="muted">{t('elapsedHint')}</p></>}
  </Card>;
}
function PrivateNotes({ studentId, onDirty }: { studentId: number; onDirty: (dirty: boolean) => void }) {
  const { t } = useTranslation('people');
  const resource = useResource<unknown>(['people', studentId, 'notes'], `/api/students/${studentId}/notes`);
  const parsed = validationResult(resource.data, parseNotes);
  const error = resource.error || parsed.error;
  return <Card><h2>{t('privateNotes')}</h2><p>{t('notesHint')}</p>
    {resource.isPending && <LoadingState />}{error && <ErrorState error={error} retry={() => void resource.refetch()} />}
    {parsed.data !== null && <div hidden={!!error} inert={!!error}><NotesForm studentId={studentId} initial={parsed.data} onDirty={onDirty} refresh={async () => { const result = await resource.refetch(); if (result.error) throw result.error; return parseNotes(result.data); }} /></div>}
  </Card>;
}
function NotesForm({ studentId, initial, onDirty, refresh }: { studentId: number; initial: string; onDirty: (dirty: boolean) => void; refresh: () => Promise<string> }) {
  const { t } = useTranslation('people');
  const { api } = useAuth();
  const invalidate = useInvalidate();
  const form = useForm({ defaultValues: { notes: initial } });
  const [baseline, setBaseline] = useState(initial);
  const [confirm, setConfirm] = useState(false);
  const [discard, setDiscard] = useState(false);
  useReportDirty(form.formState.isDirty, onDirty);
  const operation = useOperation<string, void>(async notes => {
    confirmNotes(await api.post<unknown>(`/api/students/${studentId}/notes`, { notes }));
  }, async (_, notes) => {
    const latest = form.getValues('notes'); form.reset({ notes }); setBaseline(notes);
    if (latest !== notes) form.setValue('notes', latest, { shouldDirty: true });
    await invalidate(['people', studentId, 'notes']);
  });
  const check = useOperation<void, string>(refresh, server => {
    const current = form.getValues('notes'); form.reset({ notes: server }); setBaseline(server);
    if (current !== server) form.setValue('notes', current, { shouldDirty: true });
    operation.reset();
  });
  const changed = initial !== baseline;
  const showServer = changed || check.isSuccess && form.formState.isDirty;
  return <form className="stack" onSubmit={form.handleSubmit(({ notes }) => {
    if (operation.error?.uncertain) return;
    if (changed) setConfirm(true); else { check.reset(); operation.mutate(notes); }
  })}>
    <Field label={t('notes')}><Textarea rows={8} aria-label={t('notes')} {...form.register('notes')} /></Field>
    {changed && <p role="status">{t('notesChanged')}</p>}
    {showServer && <Button variant="secondary" disabled={operation.isPending} onClick={() => setDiscard(true)}>{t('useServerNotes')}</Button>}
    {check.isSuccess && <p role="status">{t(form.formState.isDirty ? 'checkedNotesDifferent' : 'checkedNotesMatch')}</p>}
    {showServer && <Field label={t('serverNotes')}><Textarea rows={5} aria-label={t('serverNotes')} value={initial} readOnly /></Field>}
    {operation.error && <ErrorState error={operation.error} />}{check.error && <ErrorState error={check.error} />}
    {operation.error?.uncertain && <><p role="status">{t('uncertainAction')}</p><Button variant="secondary" busy={check.isPending} onClick={() => check.mutate()}>{t('checkNotes')}</Button></>}
    <div className="cluster"><Button type="submit" busy={operation.isPending} disabled={operation.isPending || !!operation.error?.uncertain || !form.formState.isDirty}>{t('saveNotes')}</Button>
      <SaveStatus state={operation.error?.uncertain ? 'uncertain' : operation.isPending ? 'saving' : form.formState.isDirty ? 'dirty' : operation.isSuccess ? 'saved' : 'idle'}>{operation.isSuccess && !form.formState.isDirty ? t('notesSaved') : undefined}</SaveStatus>
    </div>
    <ConfirmDialog open={discard} onOpenChange={setDiscard} title={t('discardNotesTitle')} description={t('discardNotesDescription')} confirmLabel={t('useServerNotes')} destructive
      onConfirm={() => { form.reset({ notes: initial }); setBaseline(initial); setDiscard(false); }} />
    <ConfirmDialog open={confirm} onOpenChange={setConfirm} title={t('replaceNotes')} description={t('notesChanged')} confirmLabel={t('saveNotes')} busy={operation.isPending}
      onConfirm={() => { check.reset(); void operation.mutateAsync(form.getValues('notes')).catch(() => undefined).finally(() => setConfirm(false)); }} />
  </form>;
}

function AccountActions({ person, actor, onDirty, refresh }: { person: Person; actor: User; onDirty: (dirty: boolean) => void; refresh: () => Promise<Person> }) {
  const { t } = useTranslation('people');
  const { api } = useAuth();
  const invalidate = useInvalidate();
  const [confirm, setConfirm] = useState(false);
  const [targetActive, setTargetActive] = useState(!person.active);
  const operation = useOperation<boolean, void>(async active => {
    confirmStatus(await api.patch<unknown>(`/api/auth/users/${person.id}/status`, { active, confirm: true }), person.id, active);
  }, async () => { setConfirm(false); await invalidate(['people']); });
  const check = useOperation<void, Person>(refresh, () => operation.reset());
  if (person.id === actor.id) return <Card><p>{t('selfAccountHint')}</p></Card>;
  return <Card><div className="stack"><h2>{t('accountActions')}</h2><p>{t('accountActionsHint')}</p>
    {operation.error && <ErrorState error={operation.error} />}
    {operation.error?.uncertain && <p role="status">{t('uncertainAction')}</p>}
    {operation.isSuccess && <p role="status">{t('accountSaved')}</p>}
    <div className="cluster"><Button variant={person.active ? 'danger' : 'secondary'} disabled={operation.isPending || !!operation.error?.uncertain} onClick={() => { setTargetActive(!person.active); setConfirm(true); }}>{t(person.active ? 'deactivate' : 'activate')}</Button>
      <Button variant="ghost" busy={check.isPending} onClick={() => check.mutate()}>{t('refresh')}</Button></div>
    <ConfirmDialog open={confirm} onOpenChange={setConfirm} title={t(targetActive ? 'confirmActivate' : 'confirmDeactivate')}
      description={t(targetActive ? 'activateDescription' : 'deactivateDescription', { name: `${personName(person)} (${person.username})` })}
      confirmLabel={t(targetActive ? 'activate' : 'deactivate')} destructive={!targetActive} busy={operation.isPending}
      onConfirm={() => { if (!operation.error?.uncertain) void operation.mutateAsync(targetActive).catch(() => undefined).finally(() => setConfirm(false)); }} />
    {check.error && <ErrorState error={check.error} />}{check.isSuccess && <p role="status">{t('checkedAccount')}</p>}
    <RecoveryForm person={person} onDirty={onDirty} />
  </div></Card>;
}
function RecoveryForm({ person, onDirty }: { person: Person; onDirty: (dirty: boolean) => void }) {
  const { t } = useTranslation('people');
  const { api } = useAuth();
  const invalidate = useInvalidate();
  const [confirm, setConfirm] = useState(false);
  const pendingPassword = useRef<string | null>(null);
  const descriptionId = useId();
  const form = useForm({ defaultValues: { password: '', repeat: '' } });
  useReportDirty(form.formState.isDirty, onDirty);
  const operation = useOperation<void, void>(async () => {
    if (pendingPassword.current === null) throw new ApiError(422, 'invalid', false, 'validation');
    const password = pendingPassword.current;
    try { confirmRecovery(await api.post<unknown>(`/api/auth/users/${person.id}/reset-password`, { new_password: password, confirm: true }), person.id); }
    finally { pendingPassword.current = null; }
  }, async () => { form.reset({ password: '', repeat: '' }); setConfirm(false); await invalidate(['people']); });
  return <details><summary>{t('recoveryHeading')}</summary><form className="stack" noValidate onSubmit={form.handleSubmit(values => {
    if (!operation.error?.uncertain) { pendingPassword.current = values.password; setConfirm(true); }
  })}>
    <p id={descriptionId}>{t('recoveryDescription')}</p>
    <Field label={t('newPassword')} hint={t('recoveryPasswordHint')} error={form.formState.errors.password?.message}><Input aria-label={t('newPassword')} aria-describedby={descriptionId} type="password" autoComplete="new-password" {...form.register('password', { validate: value => validPassword(value, 12) || t('passwordInvalid') })} /></Field>
    <Field label={t('repeatPassword')} error={form.formState.errors.repeat?.message}><Input aria-label={t('repeatPassword')} type="password" autoComplete="new-password" {...form.register('repeat', { validate: value => value === form.getValues('password') || t('passwordsDiffer') })} /></Field>
    {operation.error && <ErrorState error={operation.error} />}{operation.error?.uncertain && <p role="status">{t('uncertainRecovery')}</p>}
    {operation.isSuccess && <p role="status">{t('recovered')}</p>}
    <Button type="submit" busy={operation.isPending} disabled={operation.isPending || !!operation.error?.uncertain}>{t('recover')}</Button>
    <ConfirmDialog open={confirm} onOpenChange={open => { setConfirm(open); if (!open) pendingPassword.current = null; }} title={t('confirmRecovery')}
      description={t('recoveryWarning', { name: `${personName(person)} (${person.username})` })} confirmLabel={t('recover')} destructive busy={operation.isPending}
      onConfirm={() => { if (!operation.error?.uncertain) void operation.mutateAsync().catch(() => undefined).finally(() => setConfirm(false)); }} />
  </form></details>;
}

export const routes: RouteObject[] = [
  { path: '/personas', element: <PeoplePage /> },
  { path: '/personas/nueva', element: <CreatePersonPage /> },
  { path: '/personas/:personId', element: <PersonDetailPage /> },
  { path: '/estudiantes/:studentId', element: <PersonDetailPage /> },
];
