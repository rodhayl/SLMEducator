import { describe,it,expect } from 'vitest';
import { knownInstant,validTimezone,formatTimestamp } from '@/lib/time';
describe('explicit timestamp provenance',()=>{
 it.each(['2026-10-07T08:00:00','2026-10-07 08:00:00','2026-10-07','not a date','2026-10-07Z'])('does not assume UTC for %s',value=>expect(knownInstant(value)).toBeNull());
 it('respects legacy unknown even with apparent offset',()=>expect(knownInstant('2026-10-07T08:00:00Z','legacy_unknown')).toBeNull());
 it('accepts explicit offset with known provenance',()=>expect(knownInstant('2026-10-07T10:00:00+02:00','explicit_offset')).toBe(Date.parse('2026-10-07T08:00:00Z')));
 it('validates IANA zone and uses declared UTC display fallback',()=>{expect(validTimezone('Europe/Madrid')).toBe(true);expect(validTimezone('imagined/zone')).toBe(false);expect(formatTimestamp('2026-10-07T08:00:00Z',{timezone:'bad',locale:'en',unknownLabel:'unknown'})).toContain('(UTC)');});
 it('keeps localized unknown label and historical original text',()=>expect(formatTimestamp('2026-10-07T08:00:00',{unknownLabel:'zona desconocida'})).toBe('2026-10-07T08:00:00 (zona desconocida)'));
 it('shows empty as absent, not zero epoch',()=>expect(formatTimestamp(null,{unknownLabel:'unknown'})).toBe('—'));
});
