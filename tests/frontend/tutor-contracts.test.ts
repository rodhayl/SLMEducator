import { describe, expect, it } from 'vitest';
import { isTutorSource, isQuestion, ownsQuestion, questionMatches, questionPayload, questionReceipt } from '@/features/tutor/contracts';
import { locales } from '@/features/tutor/locales';
export const source={id:11,title:'Synthetic source',type:'lesson',source_version:'a'.repeat(64),fragment_hash:'b'.repeat(64),content_data:'Bounded source',included_characters:14,total_characters:14,truncated:false,selection:'bounded_default',references:['content:11/section-1'],available_sections:[{id:'content:11/section-1',title:'First section',characters:14}]};
export const question={id:51,title:'Synthetic question',content_type:'qa',creator_id:7,is_personal:true,shared_with_teacher:false,can_edit:true,difficulty:1,content_data:{question:'Why?',answer:''}};
describe('Tutor source and question contracts',()=>{
 it('validates bounded real source metadata without accepting extra fabricated references',()=>{
  expect(isTutorSource(source,11,false)).toBe(true);
  for(const patch of [{id:12},{type:'course'},{source_version:'not-a-version'},{included_characters:13},{content_data:'x'.repeat(6001),included_characters:6001,total_characters:6001},{total_characters:13},{references:['invented']},{references:[source.references[0],source.references[0]]},{available_sections:[{...source.available_sections[0],characters:1801}]}])expect(isTutorSource({...source,...patch},11,false)).toBe(false);
  expect(isTutorSource({...source,id:21,type:'course'},21,true)).toBe(true);
  expect(isTutorSource({...source,content_data:'😀',included_characters:1,total_characters:1},11,false)).toBe(true);
 });
 it('keeps student ownership separate from read visibility and response metadata',()=>{
  expect(isQuestion(question)).toBe(true);expect(ownsQuestion(question as never,7,'student')).toBe(true);
  expect(ownsQuestion({...question,shared_with_teacher:true} as never,8,'teacher')).toBe(false);
  expect(ownsQuestion(question as never,9,'admin')).toBe(false);
  const payload=questionPayload({title:' Synthetic question ',question:' Why? ',answer:'',shared:false});
  expect(payload).toEqual({title:'Synthetic question',content_data:{question:'Why?',answer:''},shared_with_teacher:false});
  expect(questionReceipt(question,payload,7)).toBe(true);expect(questionReceipt({...question,creator_id:8},payload,7)).toBe(false);
  expect(questionMatches({...question,content_data:{question:'Other',answer:''}},payload,7)).toBe(false);
  expect(()=>questionPayload({title:'Title',question:'',answer:'Answer',shared:false})).toThrow();
 });
 it('supplies the same Spanish and English states',()=>{expect(Object.keys(locales.en).sort()).toEqual(Object.keys(locales.es).sort());});
});
