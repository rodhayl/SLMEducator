import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams, useSearchParams } from 'react-router';
import { useAuth } from '@/app/AuthProvider';
import { Badge, Button, Card, EmptyState, ErrorState, Field, Input, LoadingState, PageHeader, Select } from '@/components/ui';
import { positiveId } from '@/lib/ids';
import { useResource } from '@/lib/query';
import { useTimestamp } from '@/features/messages/useTimestamp';
import { useDelivery } from '@/features/messages/useDelivery';
import { filterRequests, helpFilters, parseRequests, requestSubject } from './contracts';
import type { HelpRequest } from './contracts';
export function HelpPage(){const {scope}=useAuth();return <HelpList key={scope}/>;}
function HelpList(){
 const {t}=useTranslation('help');const timestamp=useTimestamp(t('unknownTime'));const {user}=useAuth();const [params,setParams]=useSearchParams();const [refreshError,setRefreshError]=useState<unknown>(null);
 const query=useResource<unknown>(['help-requests'],'/api/classroom/help');const begin=useDelivery();let rows:HelpRequest[]=[],error:unknown=query.error;
 try{if(query.data!==undefined)rows=parseRequests(query.data,user?.role==='student'?user.id:undefined);}catch(value){error=value;}
 const visible=filterRequests(rows,params);const filters=helpFilters(params);
 function filter(key:string,value:string){setParams(previous=>{const next=new URLSearchParams(previous);if(value)next.set(key,value);else next.delete(key);return next;});}
 async function refresh(){const task=begin();try{const result=await query.refetch();if(task.current())setRefreshError(result.error);}finally{task.finish();}}
 return <div className="stack"><PageHeader title={t(user?.role==='student'?'mine':'title')} description={t('description')} actions={<><Link to="/tutor">{t('tutor')}</Link><Link to="/mensajes">{t('messages')}</Link></>}/><p>{t('replyLocation')}</p>

 <div className="form-grid"><Field label={t('search')}><Input value={params.get('q') || ''} onChange={event=>filter('q',event.target.value)}/></Field><Field label={t('status')}><Select value={params.get('status') || 'all'} onChange={event=>filter('status',event.target.value)}><option value="all">{t('all')}</option><option value="open">{t('open')}</option><option value="resolved">{t('resolved')}</option></Select></Field><Field label={t('priority')}><Select value={params.get('priority') || ''} onChange={event=>filter('priority',event.target.value)}><option value="">{t('allPriorities')}</option>{[1,2,3,4,5].map(value=><option key={value} value={value}>{t(`priority${value}`)}</option>)}</Select></Field></div>
 <Button variant="secondary" onClick={()=>void refresh()} disabled={query.isFetching}>{t('refresh')}</Button><ErrorState error={refreshError}/>
 {query.isPending ? <LoadingState/> : error ? <ErrorState error={error} retry={()=>void refresh()}/> : !visible.length ? <EmptyState title={t('empty')}/> : <ul className="list">{visible.map(request=><li key={request.id}><Card><h2><Link to={`/solicitudes/${request.id}${filters.size?'?'+filters:''}`}>{requestSubject(request,t('detail',{id:request.id}))}</Link></h2><div className="cluster"><Badge tone={request.status==='resolved'?'success':'warning'}>{t(request.status)}</Badge><Badge>{t('priorityValue',{value:request.priority})}</Badge></div><p>{request.student_name || t('student',{id:request.student_id})}</p>{request.content_title && <p>{request.content_title}</p>}{request.study_plan_title && <p>{request.study_plan_title}</p>}<p>{timestamp(request.created_at)}</p></Card></li>)}</ul>}
 </div>;
}
export function HelpDetailPage(){const {scope}=useAuth();const {requestId}=useParams();const id=positiveId(requestId);const {t}=useTranslation('help');return id?<HelpDetail key={`${scope}:${id}`} id={id}/>:<EmptyState title={t('unavailable')}/>;}
function HelpDetail({id}:{id:number}){
 const {t}=useTranslation('help');const timestamp=useTimestamp(t('unknownTime'));const {user}=useAuth();const [params]=useSearchParams();const query=useResource<unknown>(['help-requests'],'/api/classroom/help');let request:HelpRequest|undefined,error:unknown=query.error;
 try{if(query.data!==undefined)request=parseRequests(query.data,user?.role==='student'?user.id:undefined).find(item=>item.id===id);}catch(value){error=value;}
 const filters=helpFilters(params);const staff=user?.role==='teacher'||user?.role==='admin';
 return <div className="stack"><PageHeader title={t('detail',{id})} actions={<Link to={`${staff?'/solicitudes':'/ayuda'}${filters.size?'?'+filters:''}`}>{t('back')}</Link>}/>{query.isPending?<LoadingState/>:error?<ErrorState error={error} retry={()=>void query.refetch()}/>:!request?<EmptyState title={t('unavailable')}/>:<><Card className="stack"><h2>{requestSubject(request,t('detail',{id}))}</h2><p>{request.student_name || t('student',{id:request.student_id})} · {t('student',{id:request.student_id})}</p><div className="cluster"><Badge tone={request.status==='resolved'?'success':'warning'}>{t(request.status)}</Badge><Badge>{t('priorityValue',{value:request.priority})}</Badge></div><p>{timestamp(request.created_at)}</p><p className="prose" style={{whiteSpace:'pre-wrap'}}>{request.request_text}</p><RequestContextLinks request={request}/>{positiveId(request.question_thread_id)&&<Link to={`/tutor?thread_id=${request.question_thread_id}`}>{t('tutor')}</Link>}</Card><Card><p>{t('replyLocation')}</p><Link to="/mensajes">{t('messages')}</Link></Card></>}</div>;
}
export function RequestContextLinks({request}:{request:HelpRequest}){const {t}=useTranslation('help');return <div className="stack"><h3>{t('context')}</h3>{!request.content_id && !request.study_plan_id && !request.question_id && <p>{t('noContext')}</p>}{request.content_id && <Link to={`/materiales/${request.content_id}${request.study_plan_id?'?plan_id='+request.study_plan_id:''}`}>{request.content_title || t('content')}</Link>}{request.study_plan_id && <Link to={`/cursos/${request.study_plan_id}`}>{request.study_plan_title || t('course')}</Link>}{request.question_id && <p>{t('question')}: {request.question_text || request.question_id}</p>}</div>;}
