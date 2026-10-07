import { browserStorage } from './storage';
const PREFIX = 'slm_draft_v1:';
export const DRAFT_TTL = 7 * 24 * 60 * 60 * 1000;
export type DraftKind = 'assessment' | 'practice' | 'notes' | 'course' | 'learning-location';
const allowed = new Set<DraftKind>(['assessment', 'practice', 'notes', 'course', 'learning-location']);
/** Storage is origin-scoped, unencrypted and fallible. Only this owner's exact keys are touched. */
export class DraftAdapter {
  private readonly owner: string;
  constructor(ownerId: number | string, private readonly storage: Storage = browserStorage()) { this.owner = String(ownerId); }
  private key(kind: DraftKind, resource: string | number, attempt: string | number) {
    if (!/^[1-9]\d*$/.test(this.owner) || !allowed.has(kind)) throw new Error('Invalid draft scope');
    return PREFIX + [this.owner, kind, resource, attempt].map(v => encodeURIComponent(String(v))).join(':');
  }
  read<T>(kind: DraftKind, resource: string | number, attempt: string | number, validate: (value: unknown) => value is T): T | null {
    try {
      const key = this.key(kind, resource, attempt), entry = JSON.parse(this.storage.getItem(key) || 'null');
      if (!entry || entry.owner !== this.owner || !Number.isFinite(entry.expiresAt) || entry.expiresAt <= Date.now() || entry.expiresAt > Date.now() + DRAFT_TTL + 60_000 || !validate(entry.value)) return null;
      return entry.value;
    } catch { return null; }
  }
  write(kind: DraftKind, resource: string | number, attempt: string | number, value: unknown): boolean {
    try { this.storage.setItem(this.key(kind, resource, attempt), JSON.stringify({ owner: this.owner, expiresAt: Date.now() + DRAFT_TTL, value })); return true; } catch { return false; }
  }
  remove(kind: DraftKind, resource: string | number, attempt: string | number): boolean {
    try { this.storage.removeItem(this.key(kind, resource, attempt)); return true; } catch { return false; }
  }
  private ownerKeys() {
    const prefix = `${PREFIX}${encodeURIComponent(this.owner)}:`;
    return Array.from({ length: this.storage.length }, (_, i) => this.storage.key(i)).filter((key): key is string => !!key?.startsWith(prefix));
  }
  hasDrafts(): boolean { try { return this.ownerKeys().length > 0; } catch { return false; } }
  clearOwner(): boolean { try { for (const key of this.ownerKeys()) this.storage.removeItem(key); return true; } catch { return false; } }
}
