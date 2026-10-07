import { useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { Link, useParams, useSearchParams } from 'react-router';
import { useAuth } from '@/app/AuthProvider';
import { useDirtyGuard } from '@/app/DirtyGuard';
import { Badge, Button, Card, ConfirmDialog, EmptyState, ErrorState, Field, Input, LoadingState, PageHeader, Select, Textarea } from '@/components/ui';
import { ApiError } from '@/lib/api';
import { positiveId } from '@/lib/ids';
import { useInvalidate, useOperation, useResource } from '@/lib/query';
import { useTimestamp } from '@/features/messages/useTimestamp';
import { helpRecord, newHelpRequestId, validHelpSource } from '@/features/learning/help-contracts';
import { useDelivery } from '@/features/messages/useDelivery';
import { confirmRequest, filterRequests, helpFilters, parseRequestContext, parseRequests, requestSubject } from './contracts';
import type { HelpRequest, RequestContext, RequestInput } from './contracts';
import { HelpResponse } from './HelpResponse';
export function HelpPage(){const {scope}=useAuth();return <HelpList key={scope}/>;}
function HelpList(){
 const {t}=useTranslation('help');const timestamp=useTimestamp(t('unknownTime'));const {user}=useAuth();const [params,setParams]=useSearchParams();const [refreshError,setRefreshError]=useState<unknown>(null);
 const query=useResource<unknown>(['help-requests'],'/api/classroom/help');const begin=useDelivery();let rows:HelpRequest[]=[],error:unknown=query.error;
 try{if(query.data!==undefined)rows=parseRequests(query.data,user?.role==='student'?user.id:undefined);}catch(value){error=value;}
 const visible=filterRequests(rows,params);const filters=helpFilters(params);const context=parseRequestContext(params);
 function filter(key:string,value:string){setParams(previous=>{const next=new URLSearchParams(previous);if(value)next.set(key,value);else next.delete(key);return next;});}
 async function refresh(){const task=begin();try{const result=await query.refetch();if(task.current())setRefreshError(result.error);}finally{task.finish();}}
 return <div className="stack"><PageHeader title={t(user?.role==='student'?'mine':'title')} description={t('description')} actions={<><Link to="/tutor">{t('tutor')}</Link><Link to="/mensajes">{t('messages')}</Link></>}/><p>{t('replyLocation')}</p>
 {user?.role==='student' && (context ? <NewRequest key={JSON.stringify(context)} context={context}/> : <p role="alert">{t('contextInvalid')}</p>)}
 <div className="form-grid"><Field label={t('search')}><Input value={params.get('q') || ''} onChange={event=>filter('q',event.target.value)}/></Field><Field label={t('status')}><Select value={params.get('status') || 'all'} onChange={event=>filter('status',event.target.value)}><option value="all">{t('all')}</option><option value="open">{t('open')}</option><option value="resolved">{t('resolved')}</option></Select></Field><Field label={t('priority')}><Select value={params.get('priority') || ''} onChange={event=>filter('priority',event.target.value)}><option value="">{t('allPriorities')}</option>{[1,2,3,4,5].map(value=><option key={value} value={value}>{t(`priority${value}`)}</option>)}</Select></Field></div>
 <Button variant="secondary" onClick={()=>void refresh()} disabled={query.isFetching}>{t('refresh')}</Button><ErrorState error={refreshError}/>
 {query.isPending ? <LoadingState/> : error ? <ErrorState error={error} retry={()=>void refresh()}/> : !visible.length ? <EmptyState title={t('empty')}/> : <ul className="list">{visible.map(request=><li key={request.id}><Card><h2><Link to={`/solicitudes/${request.id}${filters.size?'?'+filters:''}`}>{requestSubject(request,t('detail',{id:request.id}))}</Link></h2><div className="cluster"><Badge tone={request.status==='resolved'?'success':'warning'}>{t(request.status)}</Badge><Badge>{t('priorityValue',{value:request.priority})}</Badge></div><p>{request.student_name || t('student',{id:request.student_id})}</p>{request.content_title && <p>{request.content_title}</p>}{request.study_plan_title && <p>{request.study_plan_title}</p>}<p>{timestamp(request.created_at)}</p></Card></li>)}</ul>}
 </div>;
}
function NewRequest({context}:{context:RequestContext}){
 const {t}=useTranslation('help');const {api,user,status}=useAuth();const invalidate=useInvalidate();const begin=useDelivery();
 const [expanded,setExpanded]=useState(!!context.content_id || !!context.study_plan_id);const [pending,setPending]=useState<RequestInput|null>(null);const [result,setResult]=useState<HelpRequest|null>(null);const [error,setError]=useState<unknown>(null);const [confirmNew,setConfirmNew]=useState(false);
 const flight=useRef(false);const form=useForm<{subject:string;description:string;urgency:string}>({defaultValues:{subject:'',description:'',urgency:'1'}});useDirtyGuard(form.formState.isDirty || !!pending);
 const contextParams=new URLSearchParams();for(const key of ['content_id','study_plan_id','session_id'] as const)if(context[key])contextParams.set(key,String(context[key]));
 const needsContext=contextParams.size>0;const sourceQuery=useResource<unknown>(['help-request-context',context],needsContext?`/api/ai/context?${contextParams}`:null);
 const source=helpRecord(sourceQuery.data) && validHelpSource(sourceQuery.data.source,context.content_id || context.study_plan_id || 0) ? sourceQuery.data.source:null;
 const allowed=status==='authenticated' && (!needsContext || !!source && !sourceQuery.error && !sourceQuery.isFetching);
 const create=useOperation(async({payload,signal}:{payload:RequestInput;signal:AbortSignal})=>confirmRequest(await api.post('/api/classroom/help',payload,{signal}),payload,user!.id));
 async function submit(values:{subject:string;description:string;urgency:string}){
  if(!allowed || create.isPending || flight.current || result)return;const next={...context,subject:values.subject.trim(),description:values.description.trim(),urgency:Number(values.urgency),client_request_id:pending?.client_request_id || newHelpRequestId()};
  if(!next.subject || !next.description || next.description.length>12000 || ![1,2,3,4,5].includes(next.urgency))return;
  if(pending && JSON.stringify(pending)!==JSON.stringify(next)){setError(new ApiError(409,'http',false,'conflict'));return;}
  flight.current=true;const task=begin();setPending(next);setError(null);
  try{const receipt=await create.mutateAsync({payload:next,signal:task.signal});if(!task.current())return;setPending(null);setResult(receipt);form.reset(values);try{await invalidate(['help-requests']);}catch(value){if(task.current())setError(value);}}
  catch(value){if(task.current()){setError(value);if(value instanceof ApiError && !value.uncertain)setPending(null);}}finally{task.finish();flight.current=false;}
 }
 function clear(){setPending(null);setResult(null);setError(null);form.reset({subject:'',description:'',urgency:'1'});setConfirmNew(false);}
 return <Card className="stack"><Button variant="secondary" aria-expanded={expanded} onClick={()=>setExpanded(value=>!value)}>{t('new')}</Button><div hidden={!expanded} inert={!expanded} className="stack"><p>{t('memory')}</p><ErrorState error={error || sourceQuery.error}/>{needsContext && sourceQuery.isFetching && <LoadingState/>}{needsContext && !sourceQuery.isFetching && !source && <p role="alert">{t('contextInvalid')}</p>}<p>{t('context')}: {source?.title || t('noContext')}</p>
 {result ? <><p role="status">{t(result.status==='resolved'?'createdResolved':'created',{id:result.id})}</p><Link to={`/solicitudes/${result.id}`}>{t('detail',{id:result.id})}</Link><Button variant="secondary" onClick={clear}>{t('newHelp')}</Button></> : <form className="stack" onSubmit={form.handleSubmit(submit)}><Field label={t('subject')} error={form.formState.errors.subject?t('required'):undefined}><Input maxLength={200} {...form.register('subject',{required:true,maxLength:200,validate:value=>!!value.trim()})} disabled={create.isPending}/></Field><Field label={t('descriptionField')} error={form.formState.errors.description?t('required'):undefined}><Textarea rows={5} maxLength={12000} {...form.register('description',{required:true,maxLength:12000,validate:value=>!!value.trim()})} disabled={create.isPending}/></Field><Field label={t('priority')}><Select {...form.register('urgency')} disabled={create.isPending}>{[1,2,3,4,5].map(value=><option key={value} value={value}>{t(`priority${value}`)}</option>)}</Select></Field><Button type="submit" busy={create.isPending} disabled={!allowed}>{t(pending?'retryHelp':'send')}</Button>{pending && !create.isPending && <><p role="status">{t('uncertain')}</p><Button variant="secondary" onClick={()=>setConfirmNew(true)}>{t('newHelp')}</Button></>}</form>}
 </div><ConfirmDialog open={confirmNew} onOpenChange={setConfirmNew} title={t('newHelpTitle')} description={t('newHelpDescription')} confirmLabel={t('newHelp')} onConfirm={clear}/></Card>;
}
export function HelpDetailPage(){const {scope}=useAuth();const {requestId}=useParams();const id=positiveId(requestId);const {t}=useTranslation('help');return id?<HelpDetail key={`${scope}:${id}`} id={id}/>:<EmptyState title={t('unavailable')}/>;}
function HelpDetail({id}:{id:number}){
 const {t}=useTranslation('help');const timestamp=useTimestamp(t('unknownTime'));const {user}=useAuth();const [params]=useSearchParams();const query=useResource<unknown>(['help-requests'],'/api/classroom/help');let request:HelpRequest|undefined,error:unknown=query.error;
 try{if(query.data!==undefined)request=parseRequests(query.data,user?.role==='student'?user.id:undefined).find(item=>item.id===id);}catch(value){error=value;}
 const filters=helpFilters(params);const staff=user?.role==='teacher'||user?.role==='admin';
 return <div className="stack"><PageHeader title={t('detail',{id})} actions={<Link to={`${staff?'/solicitudes':'/ayuda'}${filters.size?'?'+filters:''}`}>{t('back')}</Link>}/>{query.isPending?<LoadingState/>:error?<ErrorState error={error} retry={()=>void query.refetch()}/>:!request?<EmptyState title={t('unavailable')}/>:<><Card className="stack"><h2>{requestSubject(request,t('detail',{id}))}</h2><p>{request.student_name || t('student',{id:request.student_id})} · {t('student',{id:request.student_id})}</p><div className="cluster"><Badge tone={request.status==='resolved'?'success':'warning'}>{t(request.status)}</Badge><Badge>{t('priorityValue',{value:request.priority})}</Badge></div><p>{timestamp(request.created_at)}</p><p className="prose" style={{whiteSpace:'pre-wrap'}}>{request.request_text}</p><RequestContextLinks request={request}/></Card>{staff?<HelpResponse request={request}/>:<Card><p>{t('replyLocation')}</p><Link to="/mensajes">{t('messages')}</Link></Card>}</>}</div>;
}
export function RequestContextLinks({request}:{request:HelpRequest}){const {t}=useTranslation('help');return <div className="stack"><h3>{t('context')}</h3>{!request.content_id && !request.study_plan_id && !request.question_id && <p>{t('noContext')}</p>}{request.content_id && <Link to={`/materiales/${request.content_id}${request.study_plan_id?'?plan_id='+request.study_plan_id:''}`}>{request.content_title || t('content')}</Link>}{request.study_plan_id && <Link to={`/cursos/${request.study_plan_id}`}>{request.study_plan_title || t('course')}</Link>}{request.question_id && <p>{t('question')}: {request.question_text || request.question_id}</p>}</div>;}
