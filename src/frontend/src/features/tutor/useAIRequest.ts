import { useEffect, useRef, useState } from 'react';
import { useAuth } from '@/app/AuthProvider';
import { useOperation, useResource } from '@/lib/query';
import { ApiError } from '@/lib/api';
import { helpFingerprint, helpRecord, newHelpRequestId, validHelpPolicy, validHelpReceipt, validHelpUsage, type AIInput, type HelpReceipt, type HelpUsage } from './contracts';
type Pending = {id:string;payload:AIInput;context:string;policy:string;accept:(value:Record<string,unknown>,payload:AIInput)=>void};
/** No effect replays a POST. Interrupted attempts keep their immutable request identity. */
export function useAIRequest(active:boolean, context:string, endpoint:'/api/ai/chat'|'/api/ai/answer-question') {
 const {api,scope,status,credentialEpoch,getSnapshot} = useAuth();
 const [pending,setPending] = useState<Pending|null>(null), [receipt,setReceipt] = useState<HelpReceipt|null>(null);
 const [usageReceipt,setUsageReceipt]=useState<HelpUsage|null>(null);
 const [busy,setBusy] = useState(false), [cancelling,setCancelling] = useState(false), [message,setMessage] = useState(''), [error,setError] = useState<unknown>(null);
 const epoch = useRef({value:0}), flight = useRef(false), cancellation = useRef(false), controllers = useRef(new Set<AbortController>());
 const policyQuery = useResource<unknown>(['tutor','policy',endpoint], active ? '/api/ai/assistance-policy' : null);
 const usageQuery = useResource<unknown>(['tutor','usage',endpoint], active ? '/api/ai/usage' : null);
 const policyKey=helpFingerprint(policyQuery.error ? null : policyQuery.data);
 const policy = !policyQuery.error && validHelpPolicy(policyQuery.data) ? policyQuery.data : null, usage = usageReceipt || (validHelpUsage(usageQuery.data) ? usageQuery.data : null);
 const post = useOperation((request:{payload:AIInput & {client_request_id:string}; signal:AbortSignal})=>api.post<unknown>(endpoint,request.payload,{signal:request.signal}));
 const cancel = useOperation((request:{id:string;signal:AbortSignal})=>api.post<unknown>(`/api/ai/requests/${encodeURIComponent(request.id)}/cancel`,undefined,{signal:request.signal}));
 useEffect(()=>{const owned = controllers.current, ownership=epoch.current; ownership.value++; setBusy(false); setCancelling(false); return ()=>{ownership.value++; for(const controller of owned)controller.abort(); owned.clear();};},[active,context,status,credentialEpoch,policyKey]);
 function current(captured:number) {const value=getSnapshot();return epoch.current.value===captured && active && value.status==='authenticated' && value.scope===scope && value.credentialEpoch===credentialEpoch;}
 function refresh() {if(active && status==='authenticated'){const captured=epoch.current.value;void policyQuery.refetch();void usageQuery.refetch().then(result=>{if(current(captured)&&!result.error&&validHelpUsage(result.data))setUsageReceipt(null);});}}
 function remember(value:HelpReceipt){setReceipt(value);setUsageReceipt({requests_used_today:value.requests_used_today,requests_limit_daily:value.requests_limit_daily,active_request_id:value.provider_may_continue?value.request_id:null});}
 async function execute(request:Pending) {
  if(!active || status!=='authenticated' || !policy || policy.mode==='disabled' || flight.current || cancellation.current || request.context!==context || request.policy!==policyKey)return;
  flight.current=true;const captured=epoch.current.value, controller=new AbortController();controllers.current.add(controller);setBusy(true);setPending(request);setMessage('');setError(null);
  try {
   const result=await post.mutateAsync({payload:{...request.payload,client_request_id:request.id},signal:controller.signal});
   if(!current(captured))return;
   if(!helpRecord(result)||!validHelpReceipt(result.receipt,request.id)){setMessage('receiptUnknown');return;}
   remember(result.receipt);setPending(null);refresh();
   if(result.receipt.status!=='completed'){setMessage('unavailable');return;}
   if(!validHelpPolicy(result.assistance_policy)||result.assistance_policy.mode==='disabled'||result.effective_assistance!==request.payload.assistance || result.assistance_policy.mode==='hints_only' && result.effective_assistance!=='hint'){setMessage('changed');return;}
   request.accept(result,request.payload);
  }catch(value){if(current(captured)){setError(value);setMessage(value instanceof ApiError && value.status===429?'limit':value instanceof ApiError && [403,409].includes(value.status)?'changed':'interrupted');}}
  finally{controllers.current.delete(controller);flight.current=false;if(current(captured))setBusy(false);}
 }
 function send(payload:AIInput,accept:Pending['accept']) {if(pending){setMessage('pendingHint');return;}void execute({id:newHelpRequestId(),payload,context,policy:policyKey,accept});}
 async function stop() {
  const id=pending?.id || usage?.active_request_id;
  if(!id || !active || status!=='authenticated' || cancellation.current)return;
  cancellation.current=true;epoch.current.value++;for(const controller of controllers.current)controller.abort();controllers.current.clear();setBusy(false);setCancelling(true);setError(null);
  const captured=epoch.current.value,controller=new AbortController();controllers.current.add(controller);
  try {const result=await cancel.mutateAsync({id,signal:controller.signal});if(!current(captured))return;if(!validHelpReceipt(result,id)){setMessage('cancelUnknown');return;}remember(result);setPending(null);setMessage(result.status==='cancelled'?'cancelledMessage':'alreadyFinished');refresh();}
  catch(value){if(current(captured)){setError(value);setMessage('cancelUnknown');}}
  finally{controllers.current.delete(controller);cancellation.current=false;if(current(captured))setCancelling(false);}
 }
 const quotaBlocked=!!usage && (usage.requests_used_today>=usage.requests_limit_daily || !!usage.active_request_id);
 return {active:active&&status==='authenticated',pending,receipt,busy,cancelling,message,error,policy,policyKey,usage,policyQuery,usageQuery,quotaBlocked,send,stop,refresh,setMessage,retry:()=>pending && execute(pending),canRetry:!!pending && pending.context===context&&pending.policy===policyKey,abandon:()=>{if(busy||cancelling)return;setPending(null);setMessage('');refresh();}};
}
