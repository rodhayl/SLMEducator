import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { useAuth } from '@/app/AuthProvider';
import { useResource } from '@/lib/query';
import { Badge, Button, Card, ConfirmDialog, EmptyState, ErrorState, LoadingState } from '@/components/ui';
import { ContentRenderer } from '@/components/content/ContentRenderer';
import { QuestionEditor } from './QuestionEditor';
import { isQuestion, isQuestionList, ownsQuestion, responseError } from './contracts';
export function Questions({active,onDirty,initialId=null}:{active:boolean;onDirty:(value:boolean)=>void;initialId?:number|null}) {
 const {t}=useTranslation('tutor'),{user,status}=useAuth();
 const [selected,setSelected]=useState<number|null>(initialId),[dirty,setDirty]=useState(false),[next,setNext]=useState<{id:number|null}|null>(null),[revision,setRevision]=useState(0);
 const enabled=active&&status==='authenticated',student=user?.role==='student';
 const query=useResource<unknown>(['tutor','questions'],enabled?'/api/content/?content_type=qa':null);
 const detail=useResource<unknown>(['tutor','question',selected],enabled&&selected?`/api/content/${selected}`:null);
 const selection=`${selected}:${revision}`,[hydratedSelection,setHydratedSelection]=useState<string|null>(null);
 // Only gate initial form hydration; background refreshes must not replace dirty fields.
 useEffect(()=>{if(!enabled)setHydratedSelection(null);else if(detail.data&&!detail.error&&!detail.isFetching)setHydratedSelection(selection);},[enabled,detail.data,detail.error,detail.isFetching,selection]);
 const list=isQuestionList(query.data)?query.data:null;
 const visible=list?.filter(item=>item.is_personal&&(student?item.creator_id===user?.id:item.shared_with_teacher));
 const knownIds=list?list.filter(item=>item.creator_id===user?.id).map(item=>item.id):null;
 const record=selected&&isQuestion(detail.data)&&detail.data.id===selected?detail.data:undefined;
 const editing=!selected&&student||!!record&&!!user&&ownsQuestion(record,user.id,user.role);
 function select(id:number|null){if(id!==null&&id===selected)void detail.refetch();setSelected(id);setRevision(value=>value+1);}
 function choose(id:number|null){if(dirty){setNext({id});return;}select(id);}
 const updateDirty=useCallback((value:boolean)=>{setDirty(value);onDirty(value);},[onDirty]);
 return <section hidden={!enabled} inert={!enabled} className="stack" aria-label={t(student?'myQuestions':'sharedQuestions')}>
  <h2>{t(student?'myQuestions':'sharedQuestions')}</h2>
  <div className="cluster">{student&&<Button type="button" variant="secondary" onClick={()=>choose(null)}>{t('newQuestion')}</Button>}<Button type="button" variant="secondary" onClick={()=>void query.refetch()} disabled={query.isFetching}>{t('refreshQuestions')}</Button></div>
  {query.isPending?<LoadingState/>:query.error?<ErrorState error={query.error}/>:!list?<ErrorState error={responseError()}/>:visible?.length?<ul className="list">{visible.map(item=><li key={item.id}><Button type="button" variant="ghost" onClick={()=>choose(item.id)}>{item.title}</Button><Badge>{t(item.shared_with_teacher?'shared':'private')}</Badge></li>)}</ul>:<EmptyState title={t('noQuestions')}/>}
  {selected&&(detail.isPending||hydratedSelection!==selection&&detail.isFetching)?<LoadingState/>:selected&&detail.error?<ErrorState error={detail.error} retry={()=>void detail.refetch()}/>:selected&&!record?<ErrorState error={responseError()}/>:editing?<Card><h2>{t(selected?'editQuestion':'newQuestion')}</h2><QuestionEditor key={`${selected}:${revision}`} initial={record} active={enabled} knownIds={knownIds} onDirty={updateDirty}/></Card>:record?<Card><h2>{record.title}</h2><p>{t('readOnly')}</p><ContentRenderer value={record.content_data.question||record.content_data.content||''}/>{record.content_data.answer&&<><h3>{t('savedAnswer')}</h3><ContentRenderer value={record.content_data.answer}/></>}<p>{t('savedContentHint')}</p><Link to={`/materiales/${record.id}`}>{t('openMaterial')}</Link></Card>:null}
  <ConfirmDialog open={!!next&&enabled} onOpenChange={open=>{if(!open)setNext(null);}} title={t('discardQuestion')} description={t('discardQuestionHint')} confirmLabel={t('continue')} destructive onConfirm={()=>{select(next!.id);setNext(null);setDirty(false);onDirty(false);}}/>
 </section>;
}
