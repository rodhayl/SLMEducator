import { useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router';
import { useAuth } from '@/app/AuthProvider';
import { useDirtyGuard } from '@/app/DirtyGuard';
import { Badge, Button, Card, ConfirmDialog, EmptyState, ErrorState, Field, Input, LoadingState, PageHeader, Select, Textarea } from '@/components/ui';
import { ApiError } from '@/lib/api';
import { positiveId } from '@/lib/ids';
import { useInvalidate, useOperation, useResource } from '@/lib/query';
import { useTimestamp } from './useTimestamp';
import { confirmMessage, confirmMessageAction, contactLabel, filterMessages, messageFolder, parseContacts, parseMessages } from './contracts';
import type { MessageAction, MessageInput } from './contracts';
import { useDelivery } from './useDelivery';
type ComposeValues = { recipient_id: string; subject: string; body: string };
type ComposeSeed = { recipient_id: string; subject: string; body: string };
export function MessagesPage() { const {scope}=useAuth(); return <MessagesForAccount key={scope}/>; }
function MessagesForAccount() {
 const {t}=useTranslation('messages'); const timestamp=useTimestamp(t('unknownTime')); const {api,user,status}=useAuth(); const [params,setParams]=useSearchParams();
 const folder=messageFolder(params.get('folder')); const query=params.get('q') || ''; const viewKey=`${folder}:${query}`;
 const [selected,setSelected]=useState<{key:string;ids:number[]}>({key:viewKey,ids:[]});
 const [compose,setCompose]=useState(!!positiveId(params.get('recipient_id') || params.get('to')) || params.get('compose')==='1');
 const [contactSearch,setContactSearch]=useState(''); const [role,setRole]=useState('');
 const [error,setError]=useState<unknown>(null); const [notice,setNotice]=useState(''); const [uncertain,setUncertain]=useState(false); const [bulkBlocked,setBulkBlocked]=useState(false);
 const [deleting,setDeleting]=useState<number[]|null>(null); const [replacement,setReplacement]=useState<ComposeSeed|null>(null); const [retry,setRetry]=useState(false);
 const flight=useRef(false);
 const form=useForm<ComposeValues>({defaultValues:{recipient_id:String(positiveId(params.get('recipient_id') || params.get('to')) || ''),subject:'',body:''}});
 useDirtyGuard(form.formState.isDirty || uncertain);
 const list=useResource<unknown>(['messages',folder],'/api/classroom/messages?folder='+folder);
 const contactParams=new URLSearchParams({limit:'100'}); if(contactSearch.trim())contactParams.set('search',contactSearch.trim()); if(role)contactParams.set('role',role);
 const contactsQuery=useResource<unknown>(['message-contacts',role,contactSearch.trim()],compose ? '/api/classroom/users?'+contactParams : null);
 let rows:ReturnType<typeof parseMessages>=[],contacts:ReturnType<typeof parseContacts>=[],readError:unknown=list.error,contactError:unknown=contactsQuery.error;
 try {if(list.data!==undefined)rows=parseMessages(list.data,user!.id,folder);}catch(value){readError=value;}
 try {if(contactsQuery.data!==undefined)contacts=parseContacts(contactsQuery.data);}catch(value){contactError=value;}
 const visible=filterMessages(rows,query); const ids=selected.key===viewKey ? selected.ids.filter(id=>visible.some(row=>row.id===id)) : [];
 const detail=visible.find(row=>row.id===positiveId(params.get('message'))); const invalidate=useInvalidate(); const begin=useDelivery();
 const send=useOperation(async({values,signal}:{values:MessageInput;signal:AbortSignal})=>confirmMessage(await api.post('/api/classroom/messages',values,{signal}),values,user!.id));
 const bulk=useOperation(async({action,ids,signal,current}:{action:MessageAction;ids:number[];signal:AbortSignal;current:()=>boolean})=>{
  const done:number[]=[]; let failure:unknown=null;
  for(const id of ids){ if(!current())throw new ApiError(0,'stale',true,'uncertain'); try{const value=action==='delete' ? await api.delete(`/api/classroom/messages/${id}`,{signal}) : await api.post(`/api/classroom/messages/${id}/${action}`,undefined,{signal});confirmMessageAction(value,action);done.push(id);}catch(value){failure=value;break;} }
  return {done,failure};
 });
 const busy=send.isPending || bulk.isPending; const available=status==='authenticated';
 function change(name:string,value:string){setSelected({key:'',ids:[]});setParams(previous=>{const next=new URLSearchParams(previous); if(value)next.set(name,value);else next.delete(name);if(name!=='message')next.delete('message');return next;});}
 async function refresh(){if(!available || busy)return; const task=begin();try{await invalidate(['messages']);if(task.current()){const result=await list.refetch();if(!task.current())return;if(result.error)throw result.error;parseMessages(result.data,user!.id,folder);setBulkBlocked(false);setError(null);}}catch(value){if(task.current())setError(value);}finally{task.finish();}}
 function start(seed:ComposeSeed){if(form.formState.isDirty || uncertain){setReplacement(seed);return;}form.reset(seed);setCompose(true);}
 async function sendMessage(values:ComposeValues){
  const recipient=positiveId(values.recipient_id);if(!recipient || !available || busy || flight.current || uncertain || contactError)return;
  const payload={recipient_id:recipient,subject:values.subject.trim(),body:values.body.trim()};if(!payload.subject || !payload.body)return;
  flight.current=true;const task=begin();setError(null);setNotice('');setUncertain(true);
  try{await send.mutateAsync({values:payload,signal:task.signal});if(!task.current())return;setUncertain(false);form.reset({recipient_id:'',subject:'',body:''});setNotice(t('sentSuccess'));try{await invalidate(['messages']);}catch(value){if(task.current()){setError(value);setNotice(t('sentSuccess')+' '+t('refreshFailed'));}}}
  catch(value){if(task.current()){setError(value);if(value instanceof ApiError && !value.uncertain)setUncertain(false);}}
  finally{task.finish();flight.current=false;}
 }
 async function act(action:MessageAction,targets:number[]){
  if(!available || busy || flight.current || bulkBlocked || !targets.length || targets.some(id=>!visible.some(row=>row.id===id)))return;
  const permitted=targets.filter(id=>!['read','unread'].includes(action) || visible.find(row=>row.id===id)?.to_id===user!.id);if(!permitted.length)return;
  flight.current=true;const task=begin();setDeleting(null);setError(null);setNotice('');setBulkBlocked(true);
  try{const result=await bulk.mutateAsync({action,ids:permitted,signal:task.signal,current:task.current});if(!task.current())return;setSelected({key:viewKey,ids:ids.filter(id=>!result.done.includes(id))});setError(result.failure);setNotice(t(result.failure?'partial':'completed',{count:result.done.length,total:permitted.length}));try{await invalidate(['messages']);if(task.current() && !result.failure)setBulkBlocked(false);}catch(value){if(task.current())setError(value);}}
  catch(value){if(task.current())setError(value);}finally{task.finish();flight.current=false;}
 }
 function actions(targets:number[],singleRead:boolean|null=null){return <div className="cluster">{folder==='inbox' && (singleRead===null ? <><Button variant="secondary" onClick={()=>void act('read',targets)} disabled={!targets.length || busy || bulkBlocked}>{t('markRead')}</Button><Button variant="secondary" onClick={()=>void act('unread',targets)} disabled={!targets.length || busy || bulkBlocked}>{t('markUnread')}</Button></> : <Button variant="secondary" onClick={()=>void act(singleRead?'unread':'read',targets)} disabled={busy || bulkBlocked}>{t(singleRead?'markUnread':'markRead')}</Button>)}<Button variant="secondary" onClick={()=>void act(folder==='archived'?'unarchive':'archive',targets)} disabled={!targets.length || busy || bulkBlocked}>{t(folder==='archived'?'unarchive':'archive')}</Button><Button variant="danger" onClick={()=>setDeleting(targets)} disabled={!targets.length || busy || bulkBlocked}>{t('delete')}</Button></div>;}
 return <div className="stack"><PageHeader title={t('title')} description={t('description')} actions={<Button onClick={()=>setCompose(value=>!value)}>{t(compose?'closeCompose':'compose')}</Button>}/>
 <section hidden={!compose} inert={!compose}><Card className="stack"><h2>{t('compose')}</h2><p>{t('memoryOnly')}</p><form className="stack" onSubmit={form.handleSubmit(sendMessage)}>
 <div className="form-grid"><Field label={t('contactSearch')} hint={t('contactHint')}><Input value={contactSearch} onChange={event=>setContactSearch(event.target.value)}/></Field><Field label={t('contactRole')}><Select value={role} onChange={event=>setRole(event.target.value)}><option value="">{t('allRoles')}</option>{['student','teacher','admin'].map(value=><option key={value} value={value}>{t(value)}</option>)}</Select></Field></div>
 {contactsQuery.isFetching && <LoadingState/>}<ErrorState error={contactError}/>{!contactsQuery.isPending && !contacts.length && !contactError && <p>{t('noContacts')}</p>}
 <Field label={t('recipient')} error={form.formState.errors.recipient_id ? t('required'):undefined}><Select value={form.watch('recipient_id')} {...form.register('recipient_id',{required:true,validate:value=>!!positiveId(value)})} disabled={send.isPending}><option value="">{t('choose')}</option>{form.watch('recipient_id') && !contacts.some(contact=>String(contact.id)===form.watch('recipient_id')) && <option value={form.watch('recipient_id')}>{t('personId',{id:form.watch('recipient_id')})}</option>}{contacts.map(contact=><option key={contact.id} value={contact.id}>{contactLabel(contact)}</option>)}</Select></Field>
 {form.watch('recipient_id') && !contacts.some(contact=>String(contact.id)===form.watch('recipient_id')) && <p>{t('contactUnavailable')}</p>}
 <Field label={t('subject')} error={form.formState.errors.subject ? t('required'):undefined}><Input {...form.register('subject',{required:true,validate:value=>!!value.trim()})} disabled={send.isPending}/></Field>
 <Field label={t('body')} error={form.formState.errors.body ? t('required'):undefined}><Textarea rows={6} {...form.register('body',{required:true,validate:value=>!!value.trim()})} disabled={send.isPending}/></Field>
 <Button type="submit" busy={send.isPending} disabled={!available || uncertain || !!contactError}>{t('send')}</Button></form>{uncertain && !send.isPending && <><p role="status">{t('uncertain')}</p><Button variant="secondary" onClick={()=>setRetry(true)}>{t('retrySend')}</Button></>}</Card></section>
 <ErrorState error={error}/>{notice && <p role="status">{notice}</p>}{bulkBlocked && !bulk.isPending && <p role="status">{t('resultUncertain')}</p>}
 <div className="cluster" aria-label={t('title')}>{(['inbox','sent','archived'] as const).map(value=><Button key={value} variant={folder===value?'primary':'secondary'} aria-pressed={folder===value} onClick={()=>change('folder',value)} disabled={bulk.isPending}>{t(value)}</Button>)}</div>
 <div className="toolbar"><Field label={t('search')}><Input value={query} onChange={event=>change('q',event.target.value)} disabled={bulk.isPending}/></Field><Button variant="secondary" onClick={()=>void refresh()} disabled={busy || list.isFetching}>{t('refresh')}</Button></div>
 <p className="muted">{t('archiveSemantics')}</p>{list.isPending ? <LoadingState/> : readError ? <ErrorState error={readError} retry={()=>void refresh()}/> : <><label className="cluster"><input type="checkbox" checked={visible.length>0 && ids.length===visible.length} disabled={!visible.length || busy} onChange={event=>setSelected({key:viewKey,ids:event.target.checked?visible.map(row=>row.id):[]})}/>{t('selectAll')}</label><p>{t('selected',{count:ids.length})}</p>{actions(ids)}
 {!visible.length ? <EmptyState title={t('empty')}/> : <ul className="list">{visible.map(message=><li key={message.id}><Card><div className="cluster"><label><input type="checkbox" aria-label={t('selection',{subject:message.subject})} checked={ids.includes(message.id)} disabled={busy} onChange={event=>setSelected({key:viewKey,ids:event.target.checked?[...ids,message.id]:ids.filter(id=>id!==message.id)})}/></label><Button variant="ghost" onClick={()=>change('message',String(message.id))}>{message.subject}</Button>{message.to_id===user!.id && <Badge>{t(message.read_at?'read':'unread')}</Badge>}</div><p>{t(message.from_id===user!.id?'to':'from')}: {message.from_id===user!.id ? message.recipient_name || t('personId',{id:message.to_id}) : message.sender_name || t('personId',{id:message.from_id})}</p><p className="muted">{timestamp(message.sent_at)}</p></Card></li>)}</ul>}
 {detail && <Card className="stack"><h2>{detail.subject}</h2><p className="prose" style={{whiteSpace:'pre-wrap'}}>{detail.content}</p>{detail.from_id!==user!.id && <Button onClick={()=>start({recipient_id:String(detail.from_id),subject:/^Re:/i.test(detail.subject)?detail.subject:`Re: ${detail.subject}`,body:''})}>{t('reply')}</Button>}{actions([detail.id],!!detail.read_at)}</Card>}</>}
 <ConfirmDialog open={!!deleting} onOpenChange={open=>!open && setDeleting(null)} title={t('confirmDelete')} description={t('deleteDescription',{count:deleting?.length || 0})} confirmLabel={t('delete')} destructive busy={bulk.isPending} onConfirm={()=>void act('delete',deleting || [])}/>
 <ConfirmDialog open={!!replacement} onOpenChange={open=>!open && setReplacement(null)} title={t('discardTitle')} description={t('discardDescription')} confirmLabel={t('replace')} destructive onConfirm={()=>{if(replacement){form.reset(replacement);setUncertain(false);setCompose(true);setReplacement(null);}}}/>
 <ConfirmDialog open={retry} onOpenChange={setRetry} title={t('retryTitle')} description={t('retryDescription')} confirmLabel={t('retrySend')} onConfirm={()=>{setUncertain(false);setRetry(false);}}/>
 </div>;
}
