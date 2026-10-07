import { QueryClient } from '@tanstack/react-query';
import { ApiClient, ApiError, responseError, type Lease } from '@/lib/api';
import { browserStorage } from '@/lib/storage';
import { positiveId } from '@/lib/ids';
import { DraftAdapter } from '@/lib/drafts';
import type { User, Role } from '@/lib/types';
export type AuthStatus = 'checking' | 'anonymous' | 'authenticated' | 'locked';
export interface AuthSnapshot { status: AuthStatus; user: User | null; scope: string; credentialEpoch: number; error: ApiError | null }
export function normalizeUser(value: unknown): User {
  if (!value || typeof value !== 'object') throw new ApiError(200, 'invalid', false, 'invalidResponse');
  const input = value as Record<string, unknown>;
  const roleValue = input.role && typeof input.role === 'object' && 'value' in input.role ? input.role.value : input.role;
  const role = typeof roleValue === 'string' ? roleValue.trim().toLowerCase().split('.').at(-1) : '';
  if (typeof input.id !== 'number' || !positiveId(input.id) || !['student', 'teacher', 'admin'].includes(role || '') || typeof input.username !== 'string') throw new ApiError(200, 'invalid', false, 'invalidResponse');
  return { id: Number(input.id), username: input.username, role: role as Role, first_name: typeof input.first_name === 'string' ? input.first_name : '', last_name: typeof input.last_name === 'string' ? input.last_name : '', email: typeof input.email === 'string' ? input.email : '', grade_level: typeof input.grade_level === 'string' ? input.grade_level : null };
}
export class AuthController {
  private state: AuthSnapshot = { status: 'checking', user: null, scope: 'unverified', credentialEpoch: 0, error: null };
  private listeners = new Set<() => void>();
  private token: string | null = null;
  private epoch = 0;
  private sequence = 0;
  private verifying = false;
  private resources = new Map<string, number>();
  readonly api: ApiClient;
  constructor(private readonly queries: QueryClient, private readonly storage: Storage = browserStorage(), private readonly transport: typeof fetch = (...args) => fetch(...args)) {
    this.api = new ApiClient({ lease: () => ({ token: this.token, epoch: this.epoch, scope: this.state.scope, permitted: this.state.status === 'authenticated' || this.verifying, mutationsPermitted: this.state.status === 'authenticated' }), isCurrent: lease => this.current(lease), unauthorized: () => this.lock() }, transport);
  }
  private current(lease: Lease) { return lease.epoch === this.epoch && lease.scope === this.state.scope; }
  snapshot = () => this.state;
  subscribe = (callback: () => void) => { this.listeners.add(callback); return () => { this.listeners.delete(callback); }; };
  private emit(patch: Partial<AuthSnapshot>) { this.state = { ...this.state, ...patch, credentialEpoch: this.epoch }; for (const listener of this.listeners) listener(); }
  private invalidateIdentity() { this.epoch++; this.api.abort(); void this.queries.cancelQueries(); }
  private newScope(user: User | null) { return `${user?.id ?? 'anonymous'}:${++this.sequence}`; }
  private store(token: string | null, user: User | null) { try { if (token && user) { this.storage.setItem('token', token); this.storage.setItem('user', JSON.stringify(user)); } else { this.storage.removeItem('token'); this.storage.removeItem('user'); } return true; } catch { return false; } }
  registerResource = (path: string) => { this.resources.set(path, (this.resources.get(path) || 0) + 1); return () => { const count = (this.resources.get(path) || 1) - 1; if (count) this.resources.set(path, count); else this.resources.delete(path); }; }
  lock = () => { this.verifying = false; this.invalidateIdentity(); this.emit({ status: this.state.user ? 'locked' : 'anonymous', error: new ApiError(401, 'http', false, 'reauth') }); };
  async verify() {
    this.invalidateIdentity(); const epoch = this.epoch;
    this.emit({ status: this.state.user ? 'locked' : 'checking', error: null });
    try { this.token = this.storage.getItem('token'); } catch { /* Retain in-memory token. */ }
    if (!this.token) { this.queries.clear(); this.emit({ status: 'anonymous', user: null, scope: this.newScope(null) }); return; }
    this.verifying = true;
    try {
      const user = normalizeUser(await this.api.get('/api/auth/me'));
      if (epoch !== this.epoch) return;
      await this.accept(user, this.token, this.state.user?.id === user.id && this.state.user.role === user.role, epoch);
    } catch (error) {
      if (epoch !== this.epoch) return;
      this.verifying = false;
      this.emit({ status: this.state.user ? 'locked' : 'anonymous', error: error instanceof ApiError ? error : new ApiError(0, 'invalid', false, 'failed') });
    }
  }
  private async accept(user: User, token: string, same: boolean, epoch: number) {
    if (epoch !== this.epoch) throw new ApiError(0, 'stale', false, 'cancelled');
    this.token = token;
    if (same) {
      // The buffer remains hidden until current permissions on every mounted resource are confirmed.
      for (const path of [...this.resources.keys()]) await this.api.get(path);
      if (epoch !== this.epoch) return;
      await this.queries.invalidateQueries({ refetchType: 'none' });
    } else { this.queries.clear(); this.resources.clear(); }
    if (epoch !== this.epoch) throw new ApiError(0, 'stale', false, 'cancelled');
    this.verifying = false;
    this.store(token, user);
    this.emit({ user, status: 'authenticated', scope: same ? this.state.scope : this.newScope(user), error: null });
  }
  async login(username: string, password: string) {
    this.invalidateIdentity(); const epoch = this.epoch;
    let response: Response;
    try { response = await this.transport('/api/auth/login', { method: 'POST', cache: 'no-store', headers: { 'Content-Type': 'application/x-www-form-urlencoded', Accept: 'application/json' }, body: new URLSearchParams({ username, password }) }); }
    catch { throw new ApiError(0, 'network', false, 'network'); }
    if (epoch !== this.epoch) throw new ApiError(0, 'stale', false, 'cancelled');
    let data: unknown; try { data = await response.json(); } catch { throw new ApiError(response.status, 'invalid', false, 'invalidResponse'); }
    if (epoch !== this.epoch) throw new ApiError(0, 'stale', false, 'cancelled');
    if (!response.ok) throw responseError(response.status, data, false);
    if (!data || typeof data !== 'object' || !('access_token' in data) || typeof data.access_token !== 'string' || !data.access_token || !('user' in data)) throw new ApiError(200, 'invalid', false, 'invalidResponse');
    const user = normalizeUser(data.user);
    this.token = data.access_token; this.verifying = true;
    // Do not trust the login payload alone as the current identity/role.
    try {
      const confirmed = normalizeUser(await this.api.get('/api/auth/me'));
      if (confirmed.id !== user.id) throw new ApiError(200, 'invalid', false, 'invalidResponse');
      await this.accept(confirmed, data.access_token, this.state.user?.id === confirmed.id && this.state.user.role === confirmed.role, epoch);
    } catch (error) { if (epoch === this.epoch) this.verifying = false; throw error; }
  }
  async refreshIdentity() {
    const epoch = this.epoch;
    const user = normalizeUser(await this.api.bind().get('/api/auth/me'));
    if (epoch !== this.epoch || this.state.status !== 'authenticated') throw new ApiError(0, 'stale', false, 'cancelled');
    if (user.id !== this.state.user?.id || user.role !== this.state.user.role) { await this.verify(); return; }
    this.store(this.token, user);
    this.emit({ user });
  }
  async logout(mode: 'keep' | 'delete') {
    if (mode === 'delete' && this.state.user && !new DraftAdapter(this.state.user.id, this.storage).clearOwner()) throw new ApiError(0, 'invalid', false, 'storage');
    this.invalidateIdentity(); this.verifying = false; this.token = null; const cleared = this.store(null, null); this.resources.clear(); this.queries.clear();
    this.emit({ status: 'anonymous', user: null, scope: this.newScope(null), error: cleared ? null : new ApiError(0, 'invalid', false, 'logoutStorage') });
  }
}
