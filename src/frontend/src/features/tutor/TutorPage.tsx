import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/app/AuthProvider';
import { useDirtyGuard, useDirtyState } from '@/app/DirtyGuard';
import { ApiError } from '@/lib/api';
import { positiveId } from '@/lib/ids';
import { useQueryClient } from '@tanstack/react-query';
import { useResource } from '@/lib/query';
import { useDelivery } from '@/features/messages/useDelivery';
import { ContentRenderer } from '@/components/content/ContentRenderer';
import { Badge, Button, Card, ConfirmDialog, ErrorState, Field, LoadingState, PageHeader, Select, Textarea } from '@/components/ui';
import { useAIRequest } from './useAIRequest';
import { AIStatus } from './AIStatus';
import { helpRecord, isTutorSource, newHelpRequestId, responseError, type Assistance } from './contracts';
import './tutor.css';
type Reply={id:number;kind:'ai'|'teacher';body:string;author_name:string;ai_metadata?:unknown};
type Question={id:number;owner_id:number;owner_name?:string;question:string;teacher_status:string;assigned_teacher_id?:number|null;shared_teacher_id?:number|null;teacher_available:boolean;teacher_name:string|null;can_request_teacher:boolean;can_reply:boolean;replies:Reply[]};
function validQuestion(value:unknown):value is Question {return helpRecord(value)&&typeof value.id==='number'&&!!positiveId(value.id)&&typeof value.owner_id==='number'&&!!positiveId(value.owner_id)&&typeof value.question==='string'&&['not_requested','pending','answered','resolved'].includes(String(value.teacher_status))&&typeof value.teacher_available==='boolean'&&typeof value.can_request_teacher==='boolean'&&typeof value.can_reply==='boolean'&&(value.teacher_name===null||typeof value.teacher_name==='string')&&Array.isArray(value.replies)&&value.replies.every(reply=>helpRecord(reply)&&!!positiveId(reply.id)&&['ai','teacher'].includes(String(reply.kind))&&typeof reply.body==='string'&&typeof reply.author_name==='string');}
function questionList(value:unknown):value is Question[]{return Array.isArray(value)&&value.every(validQuestion);}
export function TutorPage(){const {scope}=useAuth();return <Workspace key={scope}/>;}
function Workspace(){
 const {t}=useTranslation('tutor'),{status,user}=useAuth();const [params,setParams]=useSearchParams();
 const selected=positiveId(params.get('thread_id'));const [draftRevision,setDraftRevision]=useState(0);const [dirty,setDirty]=useState(false),[next,setNext]=useState<{id:number|null}|null>(null);
 useDirtyGuard(dirty);const guardDirty=useDirtyState();const [navigation,setNavigation]=useState<{id:number|null}|null>(null);
 useEffect(()=>{if(!navigation||guardDirty||status!=='authenticated')return;const id=navigation.id;setNavigation(null);if(id===null)setDraftRevision(v=>v+1);setParams(previous=>{const p=new URLSearchParams(previous);if(id)p.set('thread_id',String(id));else p.delete('thread_id');return p;});},[navigation,guardDirty,status,setParams]);
 const query=useResource<unknown>(['questions'],'/api/questions');const cache=useQueryClient();const {scope}=useAuth();
 function refresh(){void query.refetch();if(selected)void cache.invalidateQueries({queryKey:[scope,'questions',selected]});}
 function select(id:number|null){setNavigation({id});}
 function choose(id:number|null){setNotice(null);if(id===selected&&id!==null){refresh();return;}if(dirty){setNext({id});return;}select(id);}
 const [notice,setNotice]=useState<unknown>(null);const rows=questionList(query.data)?query.data:null;
 const active=status==='authenticated';
 return <div className="stack tutor-workspace" hidden={!active} inert={!active}>
  <PageHeader title={t('unifiedTitle')} description={t('unifiedHint')} actions={<Link to={user?.role==='student'?'/ayuda':'/solicitudes'}>{t('legacyHelp')}</Link>}/>
  <div className="cluster"><Button onClick={()=>choose(null)}>{t('writeQuestion')}</Button><Button variant="secondary" onClick={refresh}>{t('refreshQuestions')}</Button><Link to="/tutor/historial">{t('legacyQuestions')}</Link></div>
  <ErrorState error={notice}/><ErrorState error={query.error||(query.data!==undefined&&!rows?responseError():null)}/>
  {query.isPending?<LoadingState/>:rows&&<ul className="list">{rows.map(row=><li key={row.id}><Button variant="ghost" onClick={()=>choose(row.id)}>{row.question}</Button>{row.owner_id!==user?.id&&row.owner_name&&<p>{row.owner_name}</p>}{row.teacher_status!=='not_requested'&&<Badge>{t(`teacher_${row.teacher_status}`)}</Badge>}</li>)}</ul>}
  {selected?<SavedQuestion key={selected} id={selected} active={active} onDirty={setDirty} refresh={refresh}/>:<AskQuestion key={`new:${draftRevision}`} params={params} active={active} onDirty={setDirty} refresh={refresh} saved={(id,error)=>{setNotice(error||null);setDirty(false);select(id);void query.refetch();}}/>}
  <ConfirmDialog open={!!next&&active} onOpenChange={open=>{if(!open)setNext(null);}} title={t('discardQuestion')} description={t('discardQuestionHint')} confirmLabel={t('continue')} destructive onConfirm={()=>{setDirty(false);select(next!.id);setNext(null);}}/>
 </div>;
}
function AskQuestion({params,active,onDirty,saved,refresh}:{params:URLSearchParams;active:boolean;onDirty:(v:boolean)=>void;saved:(id:number,error?:unknown)=>void;refresh:()=>void}){
 const {t}=useTranslation('tutor'),{api,user}=useAuth(),begin=useDelivery();const [question,setQuestion]=useState(''),[assistance,setAssistance]=useState<Assistance>('explanation');
 const content=positiveId(params.get('content_id')),plan=positiveId(params.get('plan_id')||params.get('study_plan_id')),session=positiveId(params.get('session_id'));
 const ai=useAIRequest(active,JSON.stringify([content,plan,session]),'/api/questions/ask');
 const caps=useResource<unknown>(['questions','capabilities'],'/api/questions/capabilities');
 const configured=helpRecord(caps.data)&&caps.data.ai_configured===true,teacher=helpRecord(caps.data)&&caps.data.teacher_available===true;
 const [share,setShare]=useState(false),[saving,setSaving]=useState(false),[error,setError]=useState<unknown>(null);const savedId=useRef<number|null>(null),createId=useRef<string|null>(null),flight=useRef(false),teacherTarget=useRef<{id:unknown;name:unknown}|null>(null);
 async function sendTeacher(){if(flight.current||!question.trim())return;flight.current=true;setSaving(true);const task=begin();setError(null);createId.current ||= newHelpRequestId();let id:number|null=savedId.current;
  try{if(!id){const result=await api.post('/api/questions',{client_request_id:createId.current,question:question.trim(),content_id:content,study_plan_id:plan,session_id:session,section_ids:[]},{signal:task.signal});if(!task.current())return;if(!validQuestion(result))throw responseError(true);id=result.id;savedId.current=id;}const sent=await api.post(`/api/questions/${id}/teacher`,{teacher_id:teacherTarget.current?.id,client_request_id:createId.current},{signal:task.signal});if(!task.current())return;if(!validQuestion(sent))throw responseError(true);saved(id);}catch(value){if(task.current()){setError(value);if(value instanceof ApiError&&!value.uncertain&&!id){createId.current=null;}if(id){refresh();setShare(false);if(value instanceof ApiError&&!value.uncertain){setQuestion('');saved(id,value);}}}}finally{task.finish();flight.current=false;setSaving(false);}}

 const refreshed=useRef(false);
 useEffect(()=>{onDirty(!!question||!!ai.pending);},[question,ai.pending,onDirty]);
 useEffect(()=>{if(ai.busy)refreshed.current=true;else if(refreshed.current){refreshed.current=false;refresh();}},[ai.busy,refresh]);
 function ask(){if(!question.trim())return;const payload={question:question.trim(),assistance:ai.policy?.mode==='hints_only'?'hint' as const:assistance,content_id:content,study_plan_id:plan,session_id:session,section_ids:[]};ai.send(payload,result=>{if(result.status==='suggestion'&&positiveId(result.question_id)){setQuestion('');saved(Number(result.question_id));}else ai.setMessage('unavailable');});}
 return <Card className="stack"><p>{t('savedAutomatically')}</p>{(content||plan)&&<p>{t('contextAttached')}</p>}<Field label={t('prompt')}><Textarea maxLength={4000} rows={4} value={question} onChange={event=>setQuestion(event.target.value)} disabled={ai.busy||!!ai.pending||saving||!!createId.current}/></Field><Field label={t('assistance')}><Select value={ai.policy?.mode==='hints_only'?'hint':assistance} disabled={ai.policy?.mode!=='explanations'} onChange={event=>setAssistance(event.target.value as Assistance)}><option value="hint">{t('hint')}</option><option value="explanation">{t('explanation')}</option></Select></Field><Button busy={ai.busy} disabled={!configured||saving||!!createId.current||!question.trim()||!ai.policy||ai.policy.mode==='disabled'||ai.quotaBlocked||!!ai.pending} onClick={ask}>{t('askAI')}</Button>{!configured&&<p role="status">{t('adminConfigNeeded')}</p>}{teacher?<Button variant="secondary" disabled={!question.trim()||saving||ai.busy||!!ai.pending} onClick={()=>{if(!createId.current)teacherTarget.current={id:helpRecord(caps.data)?caps.data.assigned_teacher_id:null,name:helpRecord(caps.data)?caps.data.teacher_name:''};setShare(true);}}>{t('askTeacher')}</Button>:user?.role==='student'&&<p>{t('aiOnly')}</p>}<ErrorState error={error||caps.error}/><AIStatus request={ai}/><ConfirmDialog open={share&&active} onOpenChange={setShare} title={t('askTeacher')} description={t('shareQuestion',{name:teacherTarget.current?.name||''})} confirmLabel={t('askTeacher')} busy={saving} onConfirm={()=>void sendTeacher()}/></Card>;
}
function SavedQuestion({id,active,onDirty,refresh}:{id:number;active:boolean;onDirty:(v:boolean)=>void;refresh:()=>void}){
 const {t}=useTranslation('tutor'),{api,user}=useAuth(),begin=useDelivery();const query=useResource<unknown>(['questions',id],`/api/questions/${id}`);
 const question=validQuestion(query.data)&&query.data.id===id?query.data:null;
 const ai=useAIRequest(active&&question?.owner_id===user?.id,String(id),`/api/questions/${id}/ai`);
 const observedReceipt=useRef<string|null>(null);
 useEffect(()=>{if(ai.receipt?.status==='completed'&&observedReceipt.current!==ai.receipt.request_id){observedReceipt.current=ai.receipt.request_id;void query.refetch();}},[ai.receipt,query]);
 const [body,setBody]=useState(''),[error,setError]=useState<unknown>(null),[busy,setBusy]=useState(false),[share,setShare]=useState(false),[shareId,setShareId]=useState<string|null>(null),[pending,setPending]=useState<{id:string;body:string}|null>(null);const flight=useRef(false),teacherTarget=useRef<{id:number|null|undefined;name:string|null}|null>(null);
 useEffect(()=>{onDirty(!!body||!!pending||!!ai.pending);},[body,pending,ai.pending,onDirty]);
 async function action(kind:'teacher'|'reply'|'resolve'){
  if(!active||flight.current)return;flight.current=true;setBusy(true);const task=begin();setError(null);
  const snapshot=kind==='reply'?(pending||{id:newHelpRequestId(),body:body.trim()}):null;if(snapshot)setPending(snapshot);
  try{const result=await api.post(`/api/questions/${id}/${kind}`,snapshot?{client_request_id:snapshot.id,body:snapshot.body}:kind==='teacher'?{teacher_id:teacherTarget.current?.id,client_request_id:shareId}:undefined,{signal:task.signal});if(!task.current())return;if(!validQuestion(result)||result.id!==id)throw responseError(true);setShare(false);setShareId(null);if(kind==='reply'){setPending(null);setBody('');}await query.refetch();if(task.current())refresh();}catch(value){if(task.current()){setError(value);if(value instanceof ApiError&&!value.uncertain){setPending(null);setShareId(null);if(kind==='teacher'){setShare(false);teacherTarget.current=null;await query.refetch();if(task.current())refresh();}}}}finally{task.finish();flight.current=false;setBusy(false);}
 }
 if(query.isPending)return <LoadingState/>;
 if(!question||query.error)return <ErrorState error={query.error||responseError()} retry={()=>void query.refetch()}/>;
 return <Card className="stack"><h2>{question.question}</h2><div role="log" aria-live="polite">{question.replies.map(reply=><section className="stack" key={reply.id}><h3>{reply.kind==='ai'?t('aiAnswer'):t('teacherAnswer',{name:reply.author_name})}</h3><ContentRenderer value={reply.body}/>{reply.kind==='ai'&&<><p className="muted">{t('unverified')}</p><SavedAIMetadata value={reply.ai_metadata}/></>}</section>)}</div><ErrorState error={error}/>
 {question.owner_id===user?.id&&<><Button busy={ai.busy} disabled={!ai.policy||ai.policy.mode==='disabled'||ai.quotaBlocked||!!ai.pending} onClick={()=>ai.send({question:question.question,assistance:ai.policy?.mode==='hints_only'?'hint':'explanation'},()=>{void query.refetch();refresh();})}>{t(question.replies.some(r=>r.kind==='ai')?'askAIAgain':'askAI')}</Button><AIStatus request={ai}/>{question.can_request_teacher?<><p>{t('assignedTeacher',{name:question.teacher_name})}</p><Button variant="secondary" disabled={busy||question.teacher_status==='pending'&&question.shared_teacher_id===question.assigned_teacher_id} onClick={()=>{if(!shareId)teacherTarget.current={id:question.assigned_teacher_id,name:question.teacher_name};setShareId(previous=>previous||newHelpRequestId());setShare(true);}}>{t('askTeacher')}</Button></>:user?.role==='student'&&<p>{t('aiOnly')}</p>}</>}
 {question.teacher_status!=='not_requested'&&<p role="status">{t(`teacher_${question.teacher_status}`)}</p>}
 {question.can_reply&&<><Field label={t('teacherReply')}><Textarea rows={5} maxLength={50000} value={body} disabled={busy||!!pending} onChange={event=>setBody(event.target.value)}/></Field><Button disabled={busy||!body.trim()} onClick={()=>void action('reply')}>{t(pending?'retrySame':'sendTeacherReply')}</Button></>}
 {question.teacher_status!=='not_requested'&&question.teacher_status!=='resolved'&&(question.can_reply||question.owner_id===user?.id)&&<Button variant="secondary" disabled={busy} onClick={()=>void action('resolve')}>{t('resolveThread')}</Button>}
 <ConfirmDialog open={share&&active} onOpenChange={setShare} title={t('askTeacher')} description={t('shareQuestion',{name:teacherTarget.current?.name})} confirmLabel={t('askTeacher')} busy={busy} onConfirm={()=>void action('teacher')}/>
 </Card>;
}

function SavedAIMetadata({value}:{value:unknown}){const {t}=useTranslation('tutor');if(!helpRecord(value))return null;const candidate=helpRecord(value.source)?value.source:null;const source=candidate&&isTutorSource(candidate,Number(candidate.id),candidate.type==='course')?candidate:null,receipt=helpRecord(value.receipt)?value.receipt:null;return <details><summary>{t('aiDetails')}</summary><p>{t('historicalAnswer')}</p>{receipt&&<p>{t('provider')}: {String(receipt.provider||'')} · {t('model')}: {String(receipt.model||'')}</p>}{receipt&&<p>{t('requestId')}: {String(receipt.request_id||'')} · {t('tokens')}: {String(receipt.tokens_used??t('unknown'))}</p>}{source&&<><p>{String(source.title||'')}</p><p>{t('sourceVersion')}: {String(source.source_version||'')}</p>{Array.isArray(source.references)&&<p>{t('references')}: {source.references.filter(v=>typeof v==='string').join(', ')}</p>}{typeof source.content_data==='string'&&<ContentRenderer value={source.content_data}/>}</>}<p>{t('unverified')}</p></details>;}
