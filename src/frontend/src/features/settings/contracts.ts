import { ApiError } from '@/lib/api';
import { validTimezone } from '@/lib/time';
import type { User } from '@/lib/types';
export function invalid(mutation = false): never { throw new ApiError(200, 'invalid', mutation, mutation ? 'uncertain' : 'invalidResponse'); }
export function record(value: unknown): Record<string, unknown> { if (!value || typeof value !== 'object' || Array.isArray(value)) return invalid(); return value as Record<string, unknown>; }
export function parsed<T>(value: unknown, parse: (value: unknown) => T): { data?: T; error?: ApiError } {
 if (value === undefined) return {}; try { return { data: parse(value) }; } catch (error) { return { error: error instanceof ApiError ? error : new ApiError(200, 'invalid', false, 'invalidResponse') }; }
}
export interface Profile extends User { created_at?: string | null; last_login?: string | null }
export interface ProfileValues { first_name: string; last_name: string; email: string; grade_level: string }
export function parseProfile(value: unknown): Profile {
 const v = record(value);
 if (!Number.isSafeInteger(v.id) || Number(v.id) <= 0 || !['student','teacher','admin'].includes(String(v.role)) || ['username','first_name','last_name','email'].some(k => typeof v[k] !== 'string')) return invalid();
 return { id: Number(v.id), role: v.role as User['role'], username: String(v.username), first_name: String(v.first_name), last_name: String(v.last_name), email: String(v.email), grade_level: typeof v.grade_level === 'string' ? v.grade_level : null, created_at: typeof v.created_at === 'string' ? v.created_at : null, last_login: typeof v.last_login === 'string' ? v.last_login : null };
}
export function profileValues(value: Profile): ProfileValues { return { first_name: value.first_name, last_name: value.last_name, email: value.email, grade_level: value.grade_level || '' }; }
export function passwordValid(value: string) { return Array.from(value).length >= 12 && new TextEncoder().encode(value).length <= 72 && /\p{Uppercase}/u.test(value) && /\p{Lowercase}/u.test(value) && /\p{Decimal_Number}/u.test(value) && /[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/.test(value); }
export function confirmPassword(value: unknown) { let v: Record<string,unknown>; try { v = record(value); } catch { return invalid(true); } if (v.success !== true || v.reauthentication_required !== true) return invalid(true); return true; }
export const providers = ['ollama','lm_studio','openai','openrouter'] as const;
export type Provider = typeof providers[number];
export interface AIConfig { provider: Provider; model: string; endpoint: string | null; has_api_key: boolean; temperature: number; max_tokens: number; reasoning_effort: 'none' | null; compatibility_warnings: string[] }
export interface AIValues { provider: Provider | ''; model: string; endpoint: string; api_key: string; clear_api_key: boolean; temperature: number; max_tokens: number; reasoning_effort: '' | 'none' }
export const aiDefaults: AIConfig = { provider: 'ollama', model: 'llama3', endpoint: null, has_api_key: false, temperature: 0.7, max_tokens: 1000, reasoning_effort: null, compatibility_warnings: [] };
export function parseAI(value: unknown): AIConfig {
 const v = record(value);
 if (!providers.includes(v.provider as Provider) || typeof v.model !== 'string' || !v.model.trim() || !(v.endpoint === null || typeof v.endpoint === 'string') || typeof v.has_api_key !== 'boolean' || typeof v.temperature !== 'number' || !Number.isFinite(v.temperature) || v.temperature < 0 || v.temperature > 2 || !Number.isInteger(v.max_tokens) || Number(v.max_tokens) < 1 || Number(v.max_tokens) > 16384 || ![undefined,null,'none'].includes(v.reasoning_effort as null)) return invalid();
 if (v.api_key !== undefined && v.api_key !== null && v.api_key !== '') return invalid();
 return { provider: v.provider as Provider, model: v.model, endpoint: v.endpoint, has_api_key: v.has_api_key, temperature: v.temperature, max_tokens: Number(v.max_tokens), reasoning_effort: v.reasoning_effort === 'none' ? 'none' : null, compatibility_warnings: Array.isArray(v.compatibility_warnings) ? v.compatibility_warnings.filter((x): x is string => typeof x === 'string') : [] };
}
export function aiValues(value: AIConfig): AIValues { return { ...value, endpoint: value.endpoint || '', api_key: '', clear_api_key: false, reasoning_effort: value.reasoning_effort || '' }; }
export function aiPayload(value: AIValues) { if (!providers.includes(value.provider as Provider)) throw new ApiError(422,'invalid',false,'validation'); return { provider: value.provider as Provider, model: value.model.trim(), endpoint: value.endpoint.trim() || null, temperature: Number(value.temperature), max_tokens: Number(value.max_tokens), reasoning_effort: value.provider === 'lm_studio' && value.reasoning_effort === 'none' ? 'none' : null, clear_api_key: value.clear_api_key, ...(value.api_key && !value.clear_api_key ? { api_key: value.api_key } : {}) }; }
export function sameDestination(value: AIValues, saved: AIConfig) { return value.provider === saved.provider && value.endpoint.trim() === (saved.endpoint || ''); }
export function confirmAI(value: unknown, input: AIValues): AIConfig {
 let result: AIConfig; try { result = parseAI(value); } catch { return invalid(true); }
 const sent = aiPayload(input);
 if (result.provider !== sent.provider || result.model !== sent.model || result.endpoint !== sent.endpoint || result.temperature !== sent.temperature || result.max_tokens !== sent.max_tokens || result.reasoning_effort !== sent.reasoning_effort || (sent.clear_api_key && result.has_api_key)) return invalid(true);
 return result;
}
export function parseModels(value: unknown, provider: Provider): string[] { const v = record(value); if (v.provider !== provider || !Array.isArray(v.models) || v.models.some(x => typeof x !== 'string' || !x.trim())) return invalid(); return [...new Set(v.models as string[])]; }
export interface AITest { status: 'connected'; model: string; provider: Provider; response_time_ms: number }
export function parseTest(value: unknown, input: AIValues): AITest { const v = record(value); if (v.status === 'error') throw new ApiError(200, 'http', false, 'failed'); if (v.status !== 'connected' || v.model !== input.model.trim() || v.provider !== input.provider || typeof v.response_time_ms !== 'number' || v.response_time_ms < 0 || !Number.isFinite(v.response_time_ms)) return invalid(); return { status: 'connected', model: v.model as string, provider: input.provider as Provider, response_time_ms: v.response_time_ms }; }
export interface AppConfig { theme: 'light' | 'dark' | 'auto'; language: 'es' | 'en'; font_size: 'small' | 'medium' | 'large' | 'extra-large'; enable_animations: boolean }
export function parseApp(value: unknown): AppConfig { const v = record(value); if (!['auto','light','dark'].includes(String(v.theme)) || !['es','en'].includes(String(v.language)) || !['small','medium','large','extra-large'].includes(String(v.font_size)) || typeof v.enable_animations !== 'boolean') return invalid(); return { theme: v.theme as AppConfig['theme'], language: v.language as AppConfig['language'], font_size: v.font_size as AppConfig['font_size'], enable_animations: v.enable_animations }; }
export interface TimezonePolicy { timezone: string; timezone_source: 'user' | 'default'; local_date: string; timestamp_policy: string; legacy_timestamps: string; historical_dates: string }
export function parseTimezone(value: unknown): TimezonePolicy { const v = record(value); if (!validTimezone(v.timezone) || !['user','default'].includes(String(v.timezone_source)) || typeof v.local_date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(v.local_date) || v.timestamp_policy !== 'utc_offset_v1' || v.legacy_timestamps !== 'unknown_until_explicit_migration' || v.historical_dates !== 'preserved_as_recorded') return invalid(); return v as unknown as TimezonePolicy; }
export function parseStatus(value: unknown): { status: 'online'; version: string } { const v = record(value); if (v.status !== 'online' || typeof v.version !== 'string' || !v.version.trim()) return invalid(); return { status: 'online', version: v.version }; }

export interface EarnedBadge { id: number; name: string; earned: boolean; earned_at: string | null }
export function parseBadges(value: unknown): EarnedBadge[] { if (!Array.isArray(value)) return invalid(); return value.map(item => { const v = record(item); if (typeof v.id !== 'number' || !Number.isSafeInteger(v.id) || v.id < 1 || typeof v.name !== 'string' || typeof v.earned !== 'boolean' || !(v.earned_at === null || typeof v.earned_at === 'string')) return invalid(); return {id:v.id,name:v.name,earned:v.earned,earned_at:v.earned_at}; }); }
