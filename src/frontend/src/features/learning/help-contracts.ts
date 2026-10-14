/** Runtime checks for the existing read-only context and explicit help endpoints. */
export type HelpPolicy = { mode: 'hints_only' | 'explanations' | 'disabled' };
export interface HelpSource {
  id: number; title: string; source_version: string; content_data: string; truncated: boolean;
  references: string[]; available_sections: { id: string; title: string; characters: number }[];
}
export interface HelpUsage { active_request_id: string | null; requests_used_today: number; requests_limit_daily: number }
export interface HelpReceipt {
  request_id: string; status: 'completed' | 'failed' | 'cancelled' | 'timed_out'; elapsed_seconds: number;
  provider: string; model: string; tokens_used: number | null; max_output_tokens: number;
  requests_used_today: number; requests_limit_daily: number; provider_may_continue: boolean; cost_known: false;
}
export function helpRecord(value: unknown): value is Record<string, unknown> { return !!value && typeof value === 'object' && !Array.isArray(value); }
const natural = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
export function validHelpPolicy(value: unknown): value is HelpPolicy { return helpRecord(value) && ['hints_only', 'explanations', 'disabled'].includes(String(value.mode)); }
export function validHelpUsage(value: unknown): value is HelpUsage {
  return helpRecord(value) && (value.active_request_id === null || typeof value.active_request_id === 'string' && /^[A-Za-z0-9_-]{1,80}$/.test(value.active_request_id)) && natural(value.requests_used_today) && natural(value.requests_limit_daily) && value.requests_limit_daily > 0;
}
export function validHelpSource(value: unknown, contentId: number): value is HelpSource {
  if (!helpRecord(value) || value.id !== contentId || typeof value.title !== 'string' || typeof value.content_data !== 'string' || typeof value.source_version !== 'string' || !value.source_version || typeof value.truncated !== 'boolean' || !Array.isArray(value.available_sections) || !value.available_sections.length || !Array.isArray(value.references)) return false;
  const sections = value.available_sections;
  if (!sections.every(section => helpRecord(section) && typeof section.id === 'string' && section.id.length > 0 && typeof section.title === 'string' && natural(section.characters))) return false;
  const ids = new Set(sections.map(section => section.id));
  return ids.size === sections.length && value.references.every(reference => typeof reference === 'string' && ids.has(reference));
}
export function validHelpReceipt(value: unknown, id: string): value is HelpReceipt {
  return helpRecord(value) && value.request_id === id && ['completed', 'failed', 'cancelled', 'timed_out'].includes(String(value.status)) && typeof value.elapsed_seconds === 'number' && Number.isFinite(value.elapsed_seconds) && value.elapsed_seconds >= 0 && typeof value.provider === 'string' && typeof value.model === 'string' && (value.tokens_used === null || natural(value.tokens_used)) && natural(value.max_output_tokens) && value.max_output_tokens > 0 && natural(value.requests_used_today) && natural(value.requests_limit_daily) && value.requests_limit_daily > 0 && typeof value.provider_may_continue === 'boolean' && value.cost_known === false;
}
/** Stable nested JSON identity prevents key ordering from changing a session snapshot. */
export function helpFingerprint(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(helpFingerprint).join(',')}]`;
  if (helpRecord(value)) return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${helpFingerprint(value[key])}`).join(',')}}`;
  return JSON.stringify(value) ?? 'null';
}
export function newHelpRequestId(): string { return crypto.randomUUID(); }
