import { useEffect, useRef, useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { useAuth } from '@/app/AuthProvider';
import { useInvalidate, useOperation } from '@/lib/query';
import { Button, Card, ConfirmDialog, ErrorState, Field, Input, SaveStatus, Textarea } from '@/components/ui';
import { ContentRenderer } from '@/components/content/ContentRenderer';
import { DeleteQuestion } from './DeleteQuestion';
import { ApiError } from '@/lib/api';
import { AIStatus } from './AIStatus';
import { useAIRequest } from './useAIRequest';
import { helpFingerprint, isQuestion, isQuestionList, ownsQuestion, questionForm, questionMatches, questionPayload, questionReceipt, responseError, type Question, type QuestionForm, type QuestionPayload } from './contracts';
type PendingSave={payload:QuestionPayload;values:QuestionForm;baseline:number[];id:number|null};
export function QuestionEditor({initial,active,visible=true,knownIds,onDirty}:{initial?:Question;active:boolean;visible?:boolean;knownIds:number[]|null;onDirty:(value:boolean)=>void}) {
 const {t}=useTranslation('tutor'),{api,user,scope,status,credentialEpoch,getSnapshot}=useAuth(),invalidate=useInvalidate(),queries=useQueryClient();
 const [saved,setSaved]=useState<Question|undefined>(initial),[baseline,setBaseline]=useState(questionForm(initial)),[pending,setPending]=useState<PendingSave|null>(null),[candidates,setCandidates]=useState<Question[]>([]),[message,setMessage]=useState(''),[error,setError]=useState<unknown>(null),[confirm,setConfirm]=useState<'retry'|'answer'|null>(null),[suggestion,setSuggestion]=useState('');
 const [deleted,setDeleted]=useState(false),[deleting,setDeleting]=useState(false),[saving,setSaving]=useState(false);
 const form=useForm<QuestionForm>({defaultValues:questionForm(initial)}),values=useWatch({control:form.control}) as QuestionForm;
 const epoch=useRef({value:0}),controllers=useRef(new Set<AbortController>()),operationBusy=useRef(false);
 const canEdit=!saved||!!user&&ownsQuestion(saved,user.id,user.role);
 const enabled=active&&status==='authenticated'&&user?.role==='student'&&canEdit&&!deleted;
 const ai=useAIRequest(enabled,helpFingerprint([saved?.id||null,values.question]),'/api/ai/answer-question');
 useEffect(()=>{setSuggestion('');},[values.question]);
 useEffect(()=>{const owned=controllers.current,ownership=epoch.current;ownership.value++;setSaving(false);return()=>{ownership.value++;for(const controller of owned)controller.abort();owned.clear();};},[active,status,credentialEpoch]);
 function current(captured:number){const value=getSnapshot();return captured===epoch.current.value&&enabled&&value.scope===scope&&value.credentialEpoch===credentialEpoch&&value.status==='authenticated';}
 const save=useOperation((input:{id:number|null;payload:QuestionPayload;signal:AbortSignal})=>input.id?api.put<unknown>(`/api/content/${input.id}`,input.payload,{signal:input.signal}):api.post<unknown>('/api/content/',{...input.payload,content_type:'qa',is_personal:true},{signal:input.signal}));
 const reconcile=useOperation((input:{path:string;signal:AbortSignal})=>api.get<unknown>(input.path,{signal:input.signal}));
 const dirty=!deleted&&(helpFingerprint(values)!==helpFingerprint(baseline)||!!pending||!!ai.pending||deleting);
 useEffect(()=>{onDirty(dirty);return()=>onDirty(false);},[dirty,onDirty]);
 function finish(record:Question,snapshot:PendingSave,captured:number){
  if(!current(captured)||!user||!questionMatches(record,snapshot.payload,user.id,snapshot.id||undefined))return;
  queries.setQueryData([scope,'tutor','question',record.id],record);
  const confirmed=questionForm(record);setSaved(record);setBaseline(confirmed);setPending(null);setCandidates([]);setMessage('saved');setError(null);
  if(helpFingerprint(form.getValues())===helpFingerprint(snapshot.values))form.reset(confirmed);
  void Promise.all([invalidate(['learning','content',record.id],{exact:true,refetchType:'none'}),invalidate(['tutor','questions'])]).catch(value=>{if(current(captured))setError(value);});
 }
 async function persist(input:QuestionForm){
  if(!enabled||pending||operationBusy.current||!knownIds||!user)return;
  let payload:QuestionPayload;try{payload=questionPayload(input,saved?.content_data);}catch(value){setError(value);return;}
  const snapshot:PendingSave={payload,values:{...input},baseline:[...knownIds],id:saved?.id||null};
  operationBusy.current=true;setSaving(true);let accepted=false;const captured=epoch.current.value,controller=new AbortController();controllers.current.add(controller);setPending(snapshot);setMessage('');setError(null);setCandidates([]);
  try{
   const result=await save.mutateAsync({id:snapshot.id,payload,signal:controller.signal});
   if(!questionReceipt(result,payload,user.id,snapshot.id||undefined))throw responseError(true);
   accepted=true;snapshot.id=result.id;
   await Promise.all([invalidate(['tutor','question',result.id],{exact:true,refetchType:'none'}),invalidate(['learning','content',result.id],{exact:true,refetchType:'none'}),invalidate(['tutor','questions'])]);if(!current(captured))return;
   setPending({...snapshot});
   const detail=await api.get<unknown>(`/api/content/${result.id}`,{signal:controller.signal});if(!current(captured))return;
   if(!questionMatches(detail,payload,user.id,result.id))throw responseError(true);
   finish(detail,snapshot,captured);
  }catch(value){if(current(captured)){setError(value);if(!accepted&&value instanceof ApiError&&value.kind==='http'&&value.status>=400&&value.status<500&&!value.uncertain){setPending(null);setMessage('');}else setMessage('saveUnknown');}}
  finally{controllers.current.delete(controller);operationBusy.current=false;if(current(captured))setSaving(false);}
 }
 async function inspectOutcome(){
  if(!pending||!enabled||operationBusy.current||!user)return;
  operationBusy.current=true;const captured=epoch.current.value,controller=new AbortController();controllers.current.add(controller);setError(null);setCandidates([]);setMessage('checkingSave');
  try{
   if(pending.id){const detail=await reconcile.mutateAsync({path:`/api/content/${pending.id}`,signal:controller.signal});if(!current(captured))return;if(questionMatches(detail,pending.payload,user.id,pending.id)){finish(detail,pending,captured);return;}if(!isQuestion(detail)||detail.creator_id!==user.id)throw responseError();setMessage('saveDifferent');return;}
   const list=await reconcile.mutateAsync({path:'/api/content/?content_type=qa',signal:controller.signal});if(!current(captured))return;if(!isQuestionList(list))throw responseError();
   const possible=list.filter(item=>!pending.baseline.includes(item.id)&&questionReceipt(item,pending.payload,user.id));
   if(possible.length>50){setMessage('tooManyMatches');return;}
   const matches:Question[]=[];
   for(const item of possible){const detail=await api.get<unknown>(`/api/content/${item.id}`,{signal:controller.signal});if(!current(captured))return;if(questionMatches(detail,pending.payload,user.id,item.id))matches.push(detail);}
   setCandidates(matches);setMessage(matches.length?'reviewMatches':'noMatch');
  }catch(value){if(current(captured)){setError(value);setMessage('saveUnknown');}}
  finally{controllers.current.delete(controller);operationBusy.current=false;}
 }
 function askAI(){
  const question=form.getValues('question').trim();if(!question||question.length>4000){ai.setMessage('questionRequired');return;}
  if(!enabled||!ai.policy||ai.quotaBlocked||ai.pending)return;
  ai.send({question,assistance:ai.policy.mode==='hints_only'?'hint':'explanation'},result=>{if(result.success!==true||typeof result.answer!=='string'||!result.answer.trim()||result.answer.length>50000){ai.setMessage('unavailable');return;}setSuggestion(result.answer);});
 }
 const busy=saving||save.isPending||reconcile.isPending;
 function applySuggestion(){form.setValue('answer',suggestion,{shouldDirty:true});setConfirm(null);}
 if(deleted)return <p role="status">{t('deletedQuestion')}</p>;
 return <div className="stack">
  <form className="stack" onSubmit={form.handleSubmit(persist)}>
   <SaveStatus state={pending?(busy?'saving':'uncertain'):dirty?'dirty':message==='saved'?'saved':'idle'}/>
   {saved&&<p>{t('savedId',{id:saved.id})}</p>}
   <Field label={t('questionTitle')} error={form.formState.errors.title?t('required'):undefined}><Input maxLength={200} {...form.register('title',{required:true,validate:value=>!!value.trim()})} disabled={!canEdit}/></Field>
   <Field label={t('questionText')} error={form.formState.errors.question?t('questionRequired'):undefined}><Textarea rows={4} maxLength={4000} {...form.register('question',{required:true,validate:value=>!!value.trim(),maxLength:4000})} disabled={!canEdit}/></Field>
   <Field label={t('savedAnswer')}><Textarea rows={5} maxLength={50000} {...form.register('answer')} disabled={!canEdit}/></Field>
   <label className="cluster"><input type="checkbox" {...form.register('shared')} disabled={!canEdit}/>{t('shareTeacher')}</label><p className="muted">{t('sharingHint')}</p>
   <div className="cluster"><Button type="submit" busy={save.isPending} disabled={!enabled||!!pending||busy||deleting||!knownIds}>{t('saveQuestion')}</Button><Button type="button" variant="secondary" disabled={!enabled||!ai.policy||ai.policy.mode==='disabled'||ai.quotaBlocked||!!ai.pending||ai.cancelling} busy={ai.busy} onClick={askAI}>{t('askAI')}</Button></div>
  </form>
  <ErrorState error={error}/>{message&&<p role="status">{t(message)}</p>}
  {pending&&!busy&&<Card><div className="stack"><p>{t('saveUnknownHint')}</p><Button type="button" variant="secondary" onClick={()=>void inspectOutcome()}>{t('checkSaved')}</Button>{candidates.map(item=><Card key={item.id}><h3>{item.title} (#{item.id})</h3><ContentRenderer value={item.content_data.question||''}/>{item.content_data.answer&&<ContentRenderer value={item.content_data.answer}/>}<Button type="button" onClick={()=>finish(item,{...pending,id:item.id},epoch.current.value)}>{t('useSavedEntry')}</Button></Card>)}<Button type="button" variant="secondary" onClick={()=>setConfirm('retry')}>{t('allowSaveAgain')}</Button></div></Card>}
  {suggestion&&<Card><h3>{t('suggestion')}</h3><ContentRenderer value={suggestion}/><p>{t('unverified')}</p><p>{t('answerNotSaved')}</p><Button type="button" variant="secondary" onClick={()=>{if(form.getValues('answer').trim())setConfirm('answer');else applySuggestion();}}>{t('useAnswer')}</Button></Card>}
  <AIStatus request={ai} visible={visible}/>
  {saved&&<DeleteQuestion id={saved.id} active={enabled} visible={visible} disabled={busy||!!pending||!!ai.pending} onDirty={setDeleting} onGone={()=>{setDeleted(true);form.reset();}}/>}
  {saved&&<Link to={`/ayuda?content_id=${saved.id}`}>{t('askTeacherAbout')}</Link>}
  <ConfirmDialog open={!!confirm&&enabled&&visible} onOpenChange={open=>{if(!open)setConfirm(null);}} title={t(confirm==='answer'?'useAnswer':'allowSaveAgain')} description={t(confirm==='answer'?'replaceAnswerWarning':'saveAgainWarning')} confirmLabel={t(confirm==='answer'?'useAnswer':'allowSaveAgain')} onConfirm={()=>{if(confirm==='answer')applySuggestion();else{setPending(null);setCandidates([]);setMessage('');setConfirm(null);}}}/>
 </div>;
}
