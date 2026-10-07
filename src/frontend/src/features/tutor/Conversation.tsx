import { useEffect, useRef, useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/app/AuthProvider';
import { Button, Card, ErrorState, Field, Select, Textarea } from '@/components/ui';
import { ContentRenderer } from '@/components/content/ContentRenderer';
import { useResource } from '@/lib/query';
import { positiveId } from '@/lib/ids';
import { isCourseList, isCourseTree, isMaterialList } from '@/features/courses/contracts';
import { AIStatus } from './AIStatus';
import { useAIRequest } from './useAIRequest';
import { helpFingerprint, helpRecord, isTutorSource, responseError, type Assistance, type ChatInput, type TutorSource } from './contracts';
type Exchange = {question:string;response:string;source:TutorSource|null};
export function Conversation({active,visible=true,onDirty,initialContent=null,initialPlan=null}:{active:boolean;visible?:boolean;onDirty:(value:boolean)=>void;initialContent?:number|null;initialPlan?:number|null}) {
 const {t}=useTranslation('tutor'),{status}=useAuth();
 const [planId,setPlanId]=useState<number|null>(initialPlan),[contentId,setContentId]=useState<number|null>(initialContent),[sections,setSections]=useState<string[]>([]),[generation,setGeneration]=useState(0),[exchanges,setExchanges]=useState<Exchange[]>([]);
 const form=useForm<{question:string;assistance:Assistance}>({defaultValues:{question:'',assistance:'hint'}});
 const assistance=useWatch({control:form.control,name:'assistance'});
 const enabled=active&&status==='authenticated', selectedId=contentId||planId;
 const plans=useResource<unknown>(['courses'],enabled?'/api/study-plans/':null);
 const materials=useResource<unknown>(['tutor','materials'],enabled&&!planId?'/api/content/':null);
 const tree=useResource<unknown>(['courses',planId,'tree'],enabled&&planId?`/api/study-plans/${planId}/tree`:null);
 const params=new URLSearchParams();if(contentId)params.set('content_id',String(contentId));if(planId)params.set('study_plan_id',String(planId));
 const sourceQuery=useResource<unknown>(['tutor','source',contentId,planId,generation],enabled&&selectedId?`/api/ai/context?${params}`:null);
 const source=selectedId&&helpRecord(sourceQuery.data)&&isTutorSource(sourceQuery.data.source,selectedId,!contentId)?sourceQuery.data.source:null;
 const context=helpFingerprint([contentId,planId,source?.source_version,sections]);
 const previousContext=useRef(context);
 const request=useAIRequest(enabled,context,'/api/ai/chat');
 const historyContext=`${context}:${request.policyKey}`;
 useEffect(()=>{if(previousContext.current!==historyContext){setExchanges([]);previousContext.current=historyContext;}},[historyContext]);
 const dirty=form.formState.isDirty||!!request.pending;
 useEffect(()=>{onDirty(dirty);return()=>onDirty(false);},[dirty,onDirty]);
 const options=planId?(isCourseTree(tree.data)&&tree.data.id===planId?tree.data.contents:[]):(isMaterialList(materials.data)?materials.data:[]);
 const sourceReady=!selectedId||!!source&&!sourceQuery.isFetching&&!sourceQuery.error;
 const allowed=enabled&&sourceReady&&!!request.policy&&request.policy.mode!=='disabled';
 function changeContext(plan:number|null,content:number|null){setPlanId(plan);setContentId(content);setSections([]);setExchanges([]);request.setMessage('');}
 function send(values:{question:string;assistance:Assistance}) {
  if(!allowed||request.quotaBlocked||request.busy||request.cancelling||request.pending)return;
  const message=values.question.trim();if(!message||message.length>4000){request.setMessage('questionRequired');return;}
  if(sections.length>12||sections.some(id=>!source?.available_sections.some(section=>section.id===id))){request.setMessage('sectionLimit');return;}
  const payload:ChatInput={message,content_id:contentId,study_plan_id:planId,source_version:source?.source_version||null,section_ids:sections,assistance:request.policy?.mode==='hints_only'?'hint':values.assistance,conversation_history:exchanges.flatMap(exchange=>[{role:'user' as const,content:exchange.question},{role:'assistant' as const,content:exchange.response.slice(0,4000)}]).slice(-10)};
  request.send(payload,(value)=>{
   const returned=selectedId&&isTutorSource(value.source,selectedId,!contentId)?value.source:null;
   if(selectedId&&(!returned||returned.source_version!==payload.source_version)||!selectedId&&value.source!==null){request.setMessage('changed');return;}
   if(value.status!=='suggestion'||typeof value.response!=='string'||!value.response.trim()||value.response.length>100000){request.setMessage('unavailable');return;}
   setExchanges(previous=>[...previous,{question:message,response:value.response as string,source:returned}].slice(-5));
   if(form.getValues('question').trim()===message)form.reset({question:'',assistance:values.assistance});
  });
 }
 return <section hidden={!enabled||!visible} inert={!enabled||!visible} className="stack" aria-label={t('conversation')}>
  <p>{t('freeHint')}</p><p className="muted">{t('memoryOnly')}</p>
  <p>{source?t('usingSource',{title:source.title}):!selectedId?t('noSource'):''}</p>
  <details><summary>{t('chooseContext')}</summary><div className="stack">
   <div className="form-grid"><Field label={t('course')}><Select value={planId||''} onChange={event=>changeContext(positiveId(event.target.value),null)}><option value="">{t('noCourse')}</option>{isCourseList(plans.data)&&plans.data.map(plan=><option key={plan.id} value={plan.id}>{plan.title}</option>)}</Select></Field>
   <Field label={t('material')}><Select value={contentId||''} onChange={event=>changeContext(planId,positiveId(event.target.value))}><option value="">{t(planId?'wholeCourse':'noMaterial')}</option>{options.map(material=><option key={material.id} value={material.id}>{material.title}</option>)}</Select></Field></div>
   <ErrorState error={plans.error||materials.error||tree.error}/>
   {plans.isSuccess&&!isCourseList(plans.data)&&<ErrorState error={responseError()}/>}
   {!planId&&materials.isSuccess&&!isMaterialList(materials.data)&&<ErrorState error={responseError()}/>}
   {planId&&tree.isSuccess&&(!isCourseTree(tree.data)||tree.data.id!==planId)&&<ErrorState error={responseError()}/>}
   {selectedId&&<Button type="button" variant="secondary" onClick={()=>{setGeneration(value=>value+1);request.refresh();}}>{t('refreshContext')}</Button>}
   {source&&<><h3>{source.title}</h3><SourceDetails source={source}/><fieldset><legend>{t('sections')}</legend><p>{t('sectionHint')}</p>{source.available_sections.map(section=><label key={section.id} className="cluster"><input type="checkbox" checked={sections.includes(section.id)} disabled={!sections.includes(section.id)&&sections.length>=12} onChange={event=>{setSections(previous=>event.target.checked?[...previous,section.id]:previous.filter(id=>id!==section.id));}}/>{section.title||section.id}</label>)}</fieldset></>}
  </div></details>
  {selectedId&&!sourceReady&&<><p role="status">{sourceQuery.isFetching?t('loadingContext'):t('contextUnavailable')}</p><ErrorState error={sourceQuery.error || (sourceQuery.isSuccess&&!source?responseError():null)}/></>}
  {request.policy?.mode==='disabled'&&<p role="alert">{t('policy_disabled')}</p>}
  <div className="stack" role="log" aria-label={t('conversation')} aria-live="polite">{exchanges.map((exchange,index)=><Card key={index}><h2>{t('you')}</h2><p>{exchange.question}</p><h2>{t('suggestion')}</h2><ContentRenderer value={exchange.response}/><p className="muted">{t('unverified')}</p>{exchange.source&&<SourceDetails source={exchange.source}/>}</Card>)}</div>
  <form className="stack" onSubmit={form.handleSubmit(send)}>
   <Field label={t('assistance')}><Select {...form.register('assistance')} value={request.policy?.mode==='hints_only'?'hint':assistance} disabled={request.policy?.mode!=='explanations'}><option value="hint">{t('hint')}</option><option value="explanation">{t('explanation')}</option></Select></Field>
   <Field label={t('prompt')} error={form.formState.errors.question?t('questionRequired'):undefined}><Textarea rows={4} maxLength={4000} {...form.register('question',{required:true,maxLength:4000,validate:value=>!!value.trim()})}/></Field>
   <Button type="submit" busy={request.busy} disabled={!allowed||request.quotaBlocked||request.cancelling||!!request.pending}>{t('askTutor')}</Button>
  </form>
  <AIStatus request={request} visible={visible}/>
 </section>;
}
export function SourceDetails({source}:{source:TutorSource}) {
 const {t}=useTranslation('tutor');
 return <details><summary>{t('sourceDetails')}</summary><div className="stack"><p>{t(source.truncated?'partialSource':'completeSource',{included:source.included_characters,total:source.total_characters})}</p><p>{t('sourceVersion')}: {source.source_version}</p><p>{t('references')}: {source.references.join(', ')}</p><p>{t(`selection_${source.selection}`)}</p><ContentRenderer value={source.content_data}/><p>{t('unverified')}</p></div></details>;
}
