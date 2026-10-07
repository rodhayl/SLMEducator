import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/app/AuthProvider';
import { useInvalidate, useOperation } from '@/lib/query';
import { ApiError } from '@/lib/api';
import { Button, ConfirmDialog, ErrorState } from '@/components/ui';
import { helpRecord, isQuestion, responseError } from './contracts';
export function DeleteQuestion({id,active,visible=true,disabled,onGone,onDirty}:{id:number;active:boolean;visible?:boolean;disabled:boolean;onGone:()=>void;onDirty:(dirty:boolean)=>void}) {
 const {t}=useTranslation('tutor'),{api,scope,credentialEpoch,getSnapshot}=useAuth(),invalidate=useInvalidate();
 const [confirm,setConfirm]=useState(false),[pending,setPending]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState<unknown>(null);
 const ownership=useRef({alive:true,revision:0});
 useEffect(()=>{const owner=ownership.current;owner.alive=true;return()=>{owner.alive=false;owner.revision++;};},[active,credentialEpoch]);
 useEffect(()=>{onDirty(pending);return()=>onDirty(false);},[pending,onDirty]);
 function current(revision:number){const auth=getSnapshot();return ownership.current.alive&&ownership.current.revision===revision&&active&&auth.status==='authenticated'&&auth.scope===scope&&auth.credentialEpoch===credentialEpoch;}
 const remove=useOperation(()=>api.delete<unknown>(`/api/content/${id}`));
 const inspect=useOperation(()=>api.get<unknown>(`/api/content/${id}`));
 async function confirmedGone(revision:number){try{await Promise.all([invalidate(['tutor','question',id],{exact:true,refetchType:'none'}),invalidate(['learning','content',id],{exact:true,refetchType:'none'}),invalidate(['tutor','questions'])]);if(current(revision)){setPending(false);onGone();}}catch(value){if(current(revision)){setError(value);setMessage('deleteUnknown');}}}
 async function erase(){if(!active||disabled||remove.isPending||inspect.isPending)return;const revision=ownership.current.revision;setPending(true);setError(null);setConfirm(false);try{const value=await remove.mutateAsync(undefined);if(!helpRecord(value)||value.id!==id||value.message!=='Content deleted successfully')throw responseError(true);await confirmedGone(revision);}catch(value){if(current(revision)){setError(value);setMessage('deleteUnknown');}}}
 async function check(){const revision=ownership.current.revision;setError(null);try{const value=await inspect.mutateAsync(undefined);if(!current(revision))return;if(!isQuestion(value)||value.id!==id)throw responseError();setPending(false);setMessage('stillExists');}catch(value){if(value instanceof ApiError&&value.status===404){await confirmedGone(revision);}else if(current(revision)){setError(value);setMessage('deleteUnknown');}}}
 return <div className="stack"><Button type="button" variant="danger" disabled={!active||disabled||pending||remove.isPending||inspect.isPending} onClick={()=>setConfirm(true)}>{t('deleteQuestion')}</Button>{pending&&!remove.isPending&&<Button type="button" variant="secondary" busy={inspect.isPending} onClick={()=>void check()}>{t('checkDeletion')}</Button>}{message&&<p role="status">{t(message)}</p>}<ErrorState error={error}/><ConfirmDialog open={confirm&&active&&visible} onOpenChange={setConfirm} title={t('deleteQuestion')} description={t('deleteWarning')} confirmLabel={t('deleteQuestion')} destructive onConfirm={()=>void erase()}/></div>;
}
