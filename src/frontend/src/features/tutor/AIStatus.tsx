import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, ConfirmDialog, ErrorState } from '@/components/ui';
import type { useAIRequest } from './useAIRequest';
export function AIStatus({request}:{request:ReturnType<typeof useAIRequest>}) {
 const {t}=useTranslation('tutor'),[confirm,setConfirm]=useState(false);
 const {receipt,policy,usage}=request;
 return <div className="stack">
  <p role="status">{request.busy?t('thinking'):request.message?t(request.message):request.pending?t('interrupted'):request.quotaBlocked?t(usage?.active_request_id?'accountBusy':'limit'):request.policyQuery.error?t('policyUnavailable'):''}</p>
  <ErrorState error={request.error}/>
  {(request.pending || usage?.active_request_id) && <div className="cluster">
   <Button type="button" variant="secondary" onClick={()=>void request.stop()} busy={request.cancelling}>{t('cancelRequest')}</Button>
   {request.pending&&!request.busy&&!request.cancelling&&<><Button type="button" variant="secondary" disabled={!request.canRetry} onClick={()=>void request.retry()}>{t('retrySame')}</Button><Button type="button" variant="secondary" onClick={()=>setConfirm(true)}>{t('newRequest')}</Button></>}
  </div>}
  {request.pending&&<p>{t('pendingHint')}</p>}
  <details><summary>{t('aiDetails')}</summary><div className="stack">
   <p>{policy?t(`policy_${policy.mode}`):t('policyUnavailable')}</p>
   <ErrorState error={request.policyQuery.error}/>
   <p>{usage?t('usage',{used:usage.requests_used_today,limit:usage.requests_limit_daily}):t('usageUnavailable')}</p>
   {usage?.active_request_id&&<p>{t('accountBusy')}</p>}
   <ErrorState error={request.usageQuery.error}/>
   <Button type="button" variant="secondary" disabled={request.busy||request.cancelling} onClick={request.refresh}>{t('refreshStatus')}</Button>
   {receipt&&<><h3>{t('receipt')}</h3><dl>{Object.entries({requestId:receipt.request_id,requestStatus:t(`status_${receipt.status}`),provider:receipt.provider||t('unknown'),model:receipt.model||t('unknown'),elapsed:receipt.elapsed_seconds,tokens:receipt.tokens_used??t('unknown'),maxOutput:receipt.max_output_tokens}).map(([key,value])=><div key={key}><dt>{t(key)}</dt><dd>{value}</dd></div>)}</dl>{receipt.provider_may_continue&&<p>{t('providerContinue')}</p>}</>}
   <p>{t('costUnknown')}</p>
  </div></details>
  <ConfirmDialog open={confirm&&request.active} onOpenChange={setConfirm} title={t('newRequest')} description={t('newRequestWarning')} confirmLabel={t('newRequest')} onConfirm={()=>{request.abandon();setConfirm(false);}}/>
 </div>;
}
