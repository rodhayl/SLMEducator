import { describe, expect, it } from 'vitest';
import { isLearningContent, isNotesDraft, isProgress, isSession, isSessionFor, isSessionList, isStudyTree, materialHref, sessionHref } from '@/features/learning/contracts';
import { elapsedSinceStart } from '@/features/learning/SessionElapsed';
import { knownInstant } from '@/lib/time';
const session: import('@/features/learning/contracts').StudySession = { id: 7, content_id: 4, start_time: '2026-10-07T12:00:00Z', status: 'active', notes: '', duration_minutes: 0, duration_known: true, timestamp_provenance: 'utc', content_snapshot: {id:4,title:'Pinned',content_type:'lesson',content_data:{content:'Version one'}}, context_revision:{study_plan_id:9,content_digest:'pinned'} };
describe('learning response ownership contracts', () => {
 it('validates exact session, material and study-plan context', () => {
  expect(isSessionFor(session,4,9,7)).toBe(true);
  expect(isSessionFor(session,4,8,7)).toBe(false);
  expect(isSessionFor(session,4,9,8)).toBe(false);
  expect(isSession({...session,content_snapshot:{...session.content_snapshot,id:5}})).toBe(false);
  expect(isSession({...session,status:'saved'})).toBe(false);
  expect(isSession({...session,duration_minutes:-1})).toBe(false);
 });
 it('accepts explicitly unpinned legacy sessions without replacing their snapshot', () => {
  expect(isSession({...session,content_snapshot:null,context_revision:{provenance:'legacy_unpinned'}})).toBe(true);
  expect(isSession({...session,content_snapshot:undefined})).toBe(false);
 });
 it('rejects wrong-content or duplicate session histories', () => {
  expect(isSessionList([session],4)).toBe(true);
  expect(isSessionList([session],5)).toBe(false);
  expect(isSessionList([session,session],4)).toBe(false);
 });
 it('does not accept status-only or unrelated completion receipts', () => {
  const progress = {study_plan_id:9,completed_content_ids:[4],last_content_id:4,total_contents:2,completion_percentage:50};
  expect(isProgress(progress,9,4)).toBe(true);
  for (const value of [{status:'ok'}, {...progress,completed_content_ids:[]}, {...progress,completed_content_ids:[4,4]}, {...progress,completion_percentage:Infinity}, {...progress,study_plan_id:8}]) expect(isProgress(value,9,4)).toBe(false);
 });
 it('uses study-plan IDs and content IDs without conflation', () => {
  expect(materialHref(4,9)).toBe('/materiales/4?plan_id=9');
  expect(sessionHref(session)).toBe('/estudio/7?content_id=4&plan_id=9');
  expect(materialHref(4,null)).toBe('/materiales/4');
 });
 it('validates course membership structures and known content kinds', () => {
  expect(isStudyTree({id:9,title:'Plan',contents:[{id:4,title:'Lesson',content_type:'lesson',phase_index:0,order_index:0}]},9)).toBe(true);
  expect(isStudyTree({id:9,title:'Plan',contents:[{id:4,title:'Lesson',content_type:'lesson',phase_index:-1,order_index:0}]},9)).toBe(false);
  expect(isLearningContent(session.content_snapshot)).toBe(true);
  expect(isLearningContent({...session.content_snapshot,content_type:'private-rubric'})).toBe(false);
 });
 it('requires notes to be bounded strings', () => { expect(isNotesDraft({notes:'Keep this'})).toBe(true); expect(isNotesDraft({notes:{text:'Invalid'}})).toBe(false); });
 it('uses only known timestamps for the display-only elapsed clock', () => {
  expect(elapsedSinceStart(session, Date.parse(session.start_time)+3_661_000)).toBe('01:01:01');
  expect(elapsedSinceStart({...session,duration_known:false},Date.now())).toBeNull();
  expect(elapsedSinceStart({...session,timestamp_provenance:'legacy_unknown'},Date.now())).toBeNull();
  expect(elapsedSinceStart(session,Date.parse(session.start_time)-1)).toBeNull();
 });
 it('never invents timezone or duration for legacy timestamps', () => {
  expect(knownInstant('2026-10-07T12:00:00','legacy_unknown')).toBeNull();
  expect(knownInstant('2026-10-07T12:00:00Z','legacy_unknown')).toBeNull();
  expect(knownInstant('2026-10-07T12:00:00Z','utc')).toBe(Date.parse('2026-10-07T12:00:00Z'));
 });
});
