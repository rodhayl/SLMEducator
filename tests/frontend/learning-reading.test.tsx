import { render, screen } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { LessonContent } from '@/features/learning/LessonContent';
import { locales } from '@/features/learning/locales';
import type { LearningContent } from '@/features/learning/contracts';
async function reading(content:LearningContent, language:'en'|'es'='en') {const i18n=createInstance();await i18n.init({lng:language,defaultNS:'learning',resources:{en:{learning:locales.en},es:{learning:locales.es}}});return render(<I18nextProvider i18n={i18n}><MemoryRouter><LessonContent content={content}/></MemoryRouter></I18nextProvider>);}
const content:LearningContent={id:1,title:'Lesson',content_type:'lesson',content_data:{}};
describe('study reading content boundaries (DOM only)',()=>{
 it('places source clarifications before objectives and isolates untrusted blocks',async()=>{
  const {container}=await reading({...content,content_data:{sections:[{title:'Source clarification',content:'Clarify the given definition.',source_clarification:true},{title:'Lesson explanation',content:'Safe explanation<script>steal()</script>'}],objectives:['Understand the idea'],summary:'Summary text',worked_example:'Example text'}});
  const headings=screen.getAllByRole('heading');expect(headings[0]).toHaveTextContent('Source clarification');expect(headings[1]).toHaveTextContent('Learning objectives');expect(container.querySelector('script')).toBeNull();expect(screen.getByText('Example text')).toBeVisible();
 });
 it('shows an assessment preview link without rendering supplied solution or rubric fields',async()=>{
  await reading({...content,content_type:'assessment',content_data:{assessment_id:12,instructions:'Read carefully.',correct_answer:'Secret key',rubric:'Secret rubric'}});
  expect(screen.getByRole('link',{name:'Open assessment preview'})).toHaveAttribute('href','/evaluaciones/12');expect(screen.queryByText('Secret key')).not.toBeInTheDocument();expect(screen.queryByText('Secret rubric')).not.toBeInTheDocument();
 });
 it('labels a partial source receipt without claiming content verification',async()=>{
  await reading({...content,content_data:{content:'Prepared reading'},source_selection:{use_coverage:'partial'}});
  expect(screen.getByText(/Partial source: some material was not included/)).toBeVisible();expect(screen.getByText(/does not verify the answer/)).toBeVisible();
 });
 it.each([[100,1000],[50,50],[0,100],[0,0]])('preserves the supplied source receipt %i/%i including zero',async(supplied,total)=>{
  await reading({...content,content_data:{content:'Prepared reading'},source_selection:{supplied_characters:supplied,source_characters:total,use_coverage:supplied<total?'partial':'complete'}});
  const receipt=screen.getByRole('status');expect(receipt).toHaveTextContent(`Source context: ${supplied}/${total} characters.`);expect(receipt).toHaveTextContent('does not verify the answer');
  if(supplied<total)expect(receipt).toHaveTextContent('Partial source');else expect(receipt).not.toHaveTextContent('Partial source');
 });
 it.each([
  [undefined,100],[0,undefined],[null,100],[true,100],['50',100],[-1,100],[0.5,100],
  [101,100],[0,-1],[0,0.5],[0,100001],[NaN,100],[0,Infinity],['<script>secret()</script>',100],
 ])('omits malformed source counts %s/%s without losing the caveat',async(supplied,total)=>{
  const {container}=await reading({...content,content_data:{content:'Prepared reading'},source_selection:{supplied_characters:supplied,source_characters:total,use_coverage:'partial'}});
  const receipt=screen.getByRole('status');expect(receipt).not.toHaveTextContent('Source context:');expect(receipt).toHaveTextContent('Partial source');expect(receipt).toHaveTextContent('does not verify the answer');expect(receipt).not.toHaveTextContent('secret');expect(container.querySelector('script')).toBeNull();
 });
 it('localizes source counts and preserves the Spanish uncertainty caveat',async()=>{
  await reading({...content,content_data:{content:'Lectura preparada'},source_selection:{supplied_characters:0,source_characters:100,use_coverage:'partial'}},'es');
  expect(screen.getByRole('status')).toHaveTextContent('Contexto de la fuente: 0/100 caracteres.');expect(screen.getByRole('status')).toHaveTextContent('Fuente parcial');expect(screen.getByRole('status')).toHaveTextContent('no verifica la respuesta');
 });
 it('has matching English and Spanish interface keys and interpolation placeholders',()=>{
  function entries(value:unknown,prefix=''):Record<string,string> {if(typeof value==='string')return {[prefix]:value};return Object.fromEntries(Object.entries(value as Record<string,unknown>).flatMap(([key,child])=>Object.entries(entries(child,`${prefix}.${key}`))));}
  const en=entries(locales.en),es=entries(locales.es);expect(Object.keys(en).sort()).toEqual(Object.keys(es).sort());for(const key of Object.keys(en))expect(en[key].match(/{{[^}]+}}/g)||[]).toEqual(es[key].match(/{{[^}]+}}/g)||[]);
 });
});
