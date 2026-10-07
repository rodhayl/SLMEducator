/** Offset-free historical records retain their unknown provenance. UTC is only a display default. */
export function validTimezone(value: unknown): value is string {
 if (typeof value !== 'string' || !value.trim()) return false;
 try { new Intl.DateTimeFormat('en', { timeZone: value }); return true; } catch { return false; }
}
export function knownInstant(value: unknown, provenance?: string): number | null {
 if (provenance === 'legacy_unknown' || typeof value !== 'string' || !/T| /.test(value) || !/(?:Z|[+-]\d{2}:\d{2})$/i.test(value)) return null;
 const instant = Date.parse(value); return Number.isFinite(instant) ? instant : null;
}
export interface TimeFormatOptions { provenance?: string; timezone?: string; locale?: string; dateOnly?: boolean; unknownLabel: string }
export function formatTimestamp(value: unknown, options: TimeFormatOptions): string {
 if (value === null || value === undefined || value === '') return '—';
 if (typeof value !== 'string') return options.unknownLabel;
 const instant = knownInstant(value, options.provenance);
 if (instant === null) return `${value} (${options.unknownLabel})`;
 const timezone = validTimezone(options.timezone) ? options.timezone : 'UTC';
 return new Intl.DateTimeFormat(options.locale, { timeZone:timezone, year:'numeric',month:'short',day:'numeric',...(options.dateOnly ? {} : { hour:'2-digit',minute:'2-digit',second:'2-digit' }) }).format(new Date(instant)) + ` (${timezone})`;
}
