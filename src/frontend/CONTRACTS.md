# Frontend contribution contracts

All paths are relative to `src/frontend/src`. Tests live in `tests/frontend/` at repository root. The root foundation worker owns app/, lib/, components/, styles/, i18n/index.ts, config, package and main.tsx. Domain workers own their feature directory, local locale module and focused tests. Do not edit API/core or legacy GUI from a domain task.

## Imports

Use `@/` for src. React Router Data mode, no route loaders/actions making API calls. Export named page components and a `routes: RouteObject[]` from `features/<domain>/routes.tsx`; root adds their lightweight paths to app/feature-routes.ts and loads each route module lazily in the single router. Protected routes are beneath AppShell. Path params require positive integer validation (`positiveId`). Role checks improve presentation; backend remains authority.

- `useAuth()` from `@/app/AuthProvider`: `{ user: User | null, scope: string, status: 'checking'|'anonymous'|'authenticated'|'locked', api: ApiClient, login(username,password): Promise<void>, logout(mode:'keep'|'delete'): Promise<void> }`. Identity is confirmed; scope changes on account replacement/logout. Private forms remain mounted but hidden/inert during same-account reauth. Never store secrets in drafts/query keys/logs.
- `useResource<T>(key: readonly unknown[], path: string | null)` from `@/lib/query`: wraps Query with `[scope,...key]`, signal, no automatic retry/refocus. `null` disables. Registers active protected resource for reauth access checks. Return normal UseQueryResult.
- `useOperation<Input,Output>(operation: (input:Input)=>Promise<Output>, onSuccess?: (value:Output,input:Input)=>void|Promise<void>)` from `@/lib/query`: single-flight mutation, retry 0, identity-safe callbacks. Return normal useMutation fields with `mutateAsync` guarded.
- `useInvalidate()` from `@/lib/query`: returns `(key?:readonly unknown[])=>Promise<void>`, scoped invalidation only; rejects if identity/credential epoch changes before or during its await.
- `api.get<T>(path, {signal?})`, `api.post<T>(path,body?,{signal?})`, `api.put<T>`, `api.patch<T>`, `api.delete<T>`. Body may be explicit FormData for multipart source uploads; its browser boundary header is preserved. Relative `/api/` only; status checked; JSON parse errors and network mutation failures classified unknown outcome; no automatic mutation replay. Domain validates response shape before claiming save.
- `ApiError` from `@/lib/api`: `status`, `kind` (`http|network|invalid|stale`), `uncertain`, `messageKey`, safe `fieldErrors`. Render `<ErrorState error={error}/>`; never raw detail or arbitrary Error.message.
- `positiveId(value)` from `@/lib/ids`: returns positive integer or null.
- `useDirtyGuard(dirty)` from `@/app/DirtyGuard`: mounts navigation/unload guard; one guard per page. Clear only after valid confirmed save. RHF manages dirty forms.
- `DraftAdapter` from `@/lib/drafts`: constructor(ownerId, storage?), read(kind,resource,attempt,validate), write(kind,resource,attempt,value), remove, clearOwner, hasDrafts. Seven-day TTL. Allowed established kinds only: `assessment`, `practice`, `notes`, `course`, `learning-location`. Restore explicitly and revalidate resource first. No password/provider key drafts.

## Components

`@/components/ui` exports Button (native props + variant:'primary'|'secondary'|'danger'|'ghost', busy?), Input, Textarea, Select (native props), Field ({label,error?,hint?,children}), Card ({children,className?}), Badge ({children,tone?}), PageHeader ({title,description?,actions?}), ErrorState ({error,retry?}), LoadingState, EmptyState ({title,description?,action?}), SaveStatus ({state:'idle'|'dirty'|'saving'|'saved'|'uncertain',children?}), ConfirmDialog ({open,onOpenChange,title,description,confirmLabel,onConfirm,destructive?,busy?,children?}). Shared CSS utilities: stack, cluster, grid, form-grid, prose, muted, panel, table-wrap, list, toolbar.

`@/components/content/ContentRenderer` exports ContentRenderer({value:string,format?:'markdown'|'html'}) using one sanitization boundary.

## Localization

Use `useTranslation('<domain>')`. Export `export const locales = { en: {...}, es: {...} }` from feature `locales.ts`; foundation registers modules. Do not mutate global catalog files concurrently. Labels, statuses, aria and errors require both languages. User content remains as written.

## Ownership

Foundation: auth, shell, routing integration, primitives, safety adapters, base styles, dependencies. Other domains may propose primitive changes but ask foundation to apply them. Features must not introduce second caches, raw fetch, storage token handling, generic dialogs, button styles or legacy globals.

## Time

Import knownInstant, validTimezone, formatTimestamp from @/lib/time. Offset-free and legacy_unknown records never become assumed UTC. formatTimestamp requires localized unknownLabel and accepts explicit locale/timezone; UTC is the display default only.

Async success callbacks must recheck identity, credential epoch, mount and relevant resource after every awaited continuation before navigating or changing private UI. Shared API and useInvalidate reject stale continuations, but arbitrary awaited work still needs an explicit guard.

Binary exports use api.download(path,{method?,body?,expectedContentTypes,signal?}) and useFileDownload() from @/lib/downloads. Blob decoding and URL handoff are credential/identity-bound; object URLs are revoked on auth change/unmount/pagehide or after 60 seconds. Do not retain blobs or credentials in Query mutation state. useAuth.refreshIdentity() rechecks /me for profile display; requireReauthentication() locks after confirmed password rotation.

A stale rejection from onSuccess invalidation does not mean the already-confirmed mutation failed. Do not replay it or deliver old UI state. Current-owner refresh failures belong in a separate safe refresh/read error while preserving the confirmed server outcome. Fire-and-forget invalidations must catch stale rejection explicitly.
