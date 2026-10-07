import { describe,expect,it } from 'vitest';
import { allowedPurposes,canManagePlan,exportPath,parseBackup,parseDraftReceipt,parseImportText,parsePlans,parsePreview,selectionKey } from '@/features/portability/contracts';
import { locales } from '@/features/portability/locales';
import { account,backupPreview,preview } from './settings-fixtures';
describe('Portability purpose and receipt contracts',()=>{
 it('has matching ES/EN labels',()=>expect(Object.keys(locales.en).sort()).toEqual(Object.keys(locales.es).sort()));
 it('limits learner to reading and teacher to owned management',()=>{expect(allowedPurposes({...account,role:'student'})).toEqual(['handout']);expect(allowedPurposes(account)).toContain('import');expect(canManagePlan({id:1,title:'other',creator_id:9},account)).toBe(false);expect(canManagePlan({id:1,title:'other',creator_id:9},{...account,role:'admin'})).toBe(true);});
 it('validates purpose, format, graph and counts before download or import',()=>{expect(parsePreview(preview(),'learner','html').audience).toBe('learner');for(const value of [preview('teacher','json'),{...preview(),counts:{contents:-1}},{...preview(),validation:{valid:false}},{...preview(),selected_format:'markdown'}])expect(()=>parsePreview(value,'learner','html')).toThrow();expect(()=>parsePreview({...preview('teacher','json'),available_formats:['html','json']},'teacher','json')).toThrow();});
 it('does not import a reading copy',()=>expect(()=>parsePreview(preview('learner','json'),'teacher')).toThrow());
 it('uses only validated numeric plan identities and requested formats',()=>{expect(()=>parsePlans([{id:'4',title:'unsafe'}])).toThrow();expect(exportPath({id:4,audience:'learner',format:'html'},'preview')).toBe('/api/portability/plans/4/preview?audience=learner&format=html');expect(selectionKey({id:4,audience:'teacher',format:'json'})).toBe('4:teacher:json');});
 it('rejects invalid JSON and non-object packages',()=>{for(const value of ['[1]','null','{bad','"text"'])expect(()=>parseImportText(value)).toThrow();expect(parseImportText('{"version":2}')).toEqual({version:2});});
 it('requires a true new draft receipt and marks malformed write response uncertain',()=>{expect(parseDraftReceipt({study_plan_id:9,status:'draft'},'import')).toBe(9);for(const value of [null,{}, {id:9,status:'published'}, {id:0,status:'draft'}])expect(()=>parseDraftReceipt(value,'revision')).toThrow('uncertain');});
 it('requires exact backup scope and key fingerprint without an encryption key',()=>{expect(parseBackup(backupPreview)).not.toHaveProperty('key');expect(()=>parseBackup({...backupPreview,key_fingerprint:'key'})).toThrow();expect(()=>parseBackup({...backupPreview,audience:'teacher'})).toThrow();});
});
