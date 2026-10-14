import {describe,it,expect} from 'vitest';
import {isQuestion,isQuestionList,isTutorSource} from '@/features/tutor/contracts';
import {locales} from '@/features/tutor/locales';
describe('Read-only legacy questions and source contracts',()=>{
 it('requires valid legacy content before rendering history',()=>{expect(isQuestion({})).toBe(false);expect(isQuestionList([{}])).toBe(false);expect(isTutorSource({},1,false)).toBe(false);});
 it('supplies the same Spanish and English states',()=>{expect(Object.keys(locales.en).sort()).toEqual(Object.keys(locales.es).sort());});
});
