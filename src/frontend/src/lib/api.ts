export type ApiErrorKind = 'http' | 'network' | 'invalid' | 'stale';
export class ApiError extends Error {
  constructor(public readonly status = 0, public readonly kind: ApiErrorKind = 'http', public readonly uncertain = false, public readonly messageKey = 'failed', public readonly fieldErrors: Readonly<Record<string, string>> = {}) {
    super(messageKey); this.name = 'ApiError';
  }
}
const safeMessages: Record<string, string> = {
  'Cannot deactivate yourself or the last active administrator': 'lastAdmin',
  'Use the current-password change flow for your own account': 'ownPasswordFlow',
  'Password must be at most 72 UTF-8 bytes': 'passwordBytes',
  'Password does not meet requirements': 'passwordRequirements',
  'Current password is incorrect': 'currentPassword',
  'Choose an active teacher': 'chooseTeacher',
  'Active administrator required': 'activeAdmin',
  'Username already exists': 'usernameExists', 'Email already exists': 'emailExists',
  'Password must be at least 8 characters and contain uppercase, lowercase, digit, and special character': 'registrationPassword',
  'Choose an active teacher for a student account': 'chooseTeacher', 'Invalid role': 'invalidRole',
  'Account creation requires an administrator or teacher': 'staffRequired',
  'Teachers can only create student accounts': 'studentOnly', 'Teachers can only enroll their own learners': 'ownLearners',
  'Students cannot create user accounts': 'staffRequired', 'Invalid username or password': 'credentials',
  'Too many login attempts. Please try again later.': 'rateLimit', 'Account is locked due to too many failed attempts': 'accountLocked',
  'Account lock timestamp has an unknown timezone. Ask the administrator to review its provenance.': 'unknownLockTime',
  'Not authenticated': 'reauth', 'Could not validate credentials': 'reauth', 'Not authorized': 'forbidden',
};
const fields = new Set(['username', 'password', 'email', 'first_name', 'last_name', 'role', 'teacher_id']);
export function responseError(status: number, body: unknown, mutation: boolean): ApiError {
  const detail = body && typeof body === 'object' && 'detail' in body ? body.detail : null;
  const fieldErrors: Record<string, string> = {};
  if (status === 422 && detail && typeof detail === 'object') {
    for (const item of (Array.isArray(detail) ? detail : [detail]).slice(0, 20)) {
      if (!item || typeof item !== 'object') continue;
      const loc: unknown = item.loc;
      if (!Array.isArray(loc) || loc.length !== 2 || loc[0] !== 'body' || !fields.has(loc[1])) continue;
      fieldErrors[loc[1]] = item.type === 'missing' ? 'required' : loc[1] === 'email' ? 'invalidEmail' : 'invalidField';
      if (Object.keys(fieldErrors).length === 4) break;
    }
  }
  const key = status < 500 && typeof detail === 'string' && Object.hasOwn(safeMessages, detail) ? safeMessages[detail] : undefined;
  const fallback = status === 401 ? 'reauth' : status === 403 || status === 404 ? 'unavailable' : status === 409 ? 'conflict' : status === 422 ? 'validation' : status === 429 ? 'rateLimit' : mutation && status >= 500 ? 'uncertain' : 'failed';
  return new ApiError(status, 'http', mutation && status >= 500, key || fallback, fieldErrors);
}
export interface RequestOptions { signal?: AbortSignal; expectedContentTypes?: readonly string[] }
export interface DownloadOptions extends RequestOptions { method?: 'GET' | 'POST'; body?: unknown; expectedContentTypes: readonly string[] }
export interface Lease { token: string | null; epoch: number; scope: string; permitted: boolean; mutationsPermitted?: boolean }
export interface ApiAccess { lease(): Lease; isCurrent(lease: Lease): boolean; unauthorized(): void }
/** All private transport passes here; captured ownership is checked after every await. */
export class ApiClient {
  constructor(private readonly access: ApiAccess, private readonly transport: typeof fetch = (...args) => fetch(...args), private readonly fixedLease?: Lease, private readonly controllers = new Set<AbortController>()) {}
  /** Render-owned clients cannot send an old form through newly switched credentials. */
  bind(expected?: Pick<Lease, 'scope' | 'epoch' | 'permitted'>): ApiClient { return new ApiClient(this.access, this.transport, { ...this.access.lease(), ...expected }, this.controllers); }
  abort() { for (const controller of this.controllers) controller.abort(); this.controllers.clear(); }
  async request<T>(path: string, method = 'GET', body?: unknown, options: RequestOptions = {}): Promise<T> {
    if (!path.startsWith('/api/') || path.includes('\\') || /[\r\n]/.test(path) || new URL(path, 'http://local').pathname.startsWith('/api/') === false) throw new ApiError(0, 'invalid', false, 'invalidRequest');
    const lease = this.fixedLease || this.access.lease();
    if (!this.access.isCurrent(lease)) throw new ApiError(0, 'stale', false, 'cancelled');
    if (!lease.permitted || (method !== 'GET' && lease.mutationsPermitted === false)) throw new ApiError(401, 'http', false, 'reauth');
    const mutation = method !== 'GET';
    const form = typeof FormData !== 'undefined' && body instanceof FormData ? body : null;
    const controller = new AbortController(); this.controllers.add(controller);
    const cancel = () => controller.abort();
    options.signal?.addEventListener('abort', cancel, { once: true });
    if (options.signal?.aborted) controller.abort();
    try {
      let response: Response;
      try {
        response = await this.transport(path, { method, signal: controller.signal, credentials: 'same-origin', cache: 'no-store', headers: { Accept: options.expectedContentTypes?.join(', ') || 'application/json', ...(lease.token ? { Authorization: `Bearer ${lease.token}` } : {}), ...(body !== undefined && !form ? { 'Content-Type': 'application/json' } : {}) }, ...(body !== undefined ? { body: form || JSON.stringify(body) } : {}) });
      } catch {
        if (!this.access.isCurrent(lease) || controller.signal.aborted) throw new ApiError(0, 'stale', mutation, mutation ? 'uncertain' : 'cancelled');
        throw new ApiError(0, 'network', mutation, mutation ? 'uncertain' : 'network');
      }
      if (!this.access.isCurrent(lease)) throw new ApiError(0, 'stale', mutation, mutation ? 'uncertain' : 'cancelled');
      if (response.ok && options.expectedContentTypes) {
        const mediaType = (response.headers.get('Content-Type') || '').split(';')[0]!.trim().toLowerCase();
        if (!options.expectedContentTypes.map(value => value.toLowerCase()).includes(mediaType)) throw new ApiError(response.status, 'invalid', mutation, mutation ? 'uncertain' : 'invalidResponse');
        let blob: Blob;
        try { blob = await response.blob(); } catch { throw new ApiError(response.status, 'invalid', mutation, mutation ? 'uncertain' : 'invalidResponse'); }
        if (!this.access.isCurrent(lease) || controller.signal.aborted) throw new ApiError(0, 'stale', mutation, mutation ? 'uncertain' : 'cancelled');
        return blob as T;
      }
      let data: unknown = null;
      let validJson = response.status === 204;
      if (!validJson) { try { data = await response.json(); validJson = true; } catch { /* Never expose response text. */ } }
      if (!this.access.isCurrent(lease)) throw new ApiError(0, 'stale', mutation, mutation ? 'uncertain' : 'cancelled');
      if (!response.ok) {
        const error = responseError(response.status, data, mutation);
        if (response.status === 401) this.access.unauthorized();
        throw error;
      }
      if (!validJson) throw new ApiError(response.status, 'invalid', mutation, mutation ? 'uncertain' : 'invalidResponse');
      return data as T;
    } finally { options.signal?.removeEventListener('abort', cancel); this.controllers.delete(controller); }
  }
  download(path: string, options: DownloadOptions): Promise<Blob> { return this.request<Blob>(path, options.method || 'GET', options.body, options); }
  get<T>(path: string, options?: RequestOptions) { return this.request<T>(path, 'GET', undefined, options); }
  post<T>(path: string, body?: unknown, options?: RequestOptions) { return this.request<T>(path, 'POST', body, options); }
  put<T>(path: string, body?: unknown, options?: RequestOptions) { return this.request<T>(path, 'PUT', body, options); }
  patch<T>(path: string, body?: unknown, options?: RequestOptions) { return this.request<T>(path, 'PATCH', body, options); }
  delete<T>(path: string, options?: RequestOptions) { return this.request<T>(path, 'DELETE', undefined, options); }
}
