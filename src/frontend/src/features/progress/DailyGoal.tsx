import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/app/AuthProvider';
import { useDirtyGuard } from '@/app/DirtyGuard';
import { useInvalidate, useOperation } from '@/lib/query';
import { ApiError } from '@/lib/api';
import { Button, Card, ErrorState, Field, Input, SaveStatus, Select, LoadingState } from '@/components/ui';
import { confirmGoal, goalInput, goalMatches, goalTypes, parseGoal, type GoalClock, type GoalInput, type GoalProgress, type GoalReceipt } from './contracts';
import { useCurrentProgress, useRead } from './shared';
export function GoalPolicy({goal}: {goal: GoalClock}) {
 const {t} = useTranslation('progress');
 return <div className="muted"><p>{t('currentTimezone',{zone:goal.timezone})}</p><p>{t('goalDayTimezone',{zone:goal.day_provenance === 'recorded' ? goal.day_timezone : t(goal.day_provenance === 'current_policy' ? 'currentPolicy' : 'unknownTime')})}</p>{goal.mixed_day_policy && <p>{t('mixedPolicy')}</p>}</div>;
}
export function DailyGoal() {
 const {t} = useTranslation('progress'); const {scope} = useAuth();
 // Unlike GET /daily-goal, this endpoint does not create a goal from defaults.
 const query = useRead(['progress','goal'],'/api/gamification/daily-goal/progress',parseGoal);
 const [initial,setInitial]=useState<GoalProgress|null>(null);
 useEffect(()=>{if(query.data)setInitial(previous=>previous || query.data!);},[query.data]);
 return <Card><h2>{t('goal')}</h2>{!initial && query.isPending && <LoadingState/>}<ErrorState error={query.error} retry={()=>void query.refetch()}/>{initial && <GoalEditor key={scope} initial={initial} refresh={async () => {const result=await query.refetch();if(result.error)throw result.error;return parseGoal(result.data);}}/>}</Card>;
}
interface GoalValues { type: string; target: string; default: boolean }
function values(goal: GoalProgress): GoalValues { return {type:goal.goal_type || 'lessons',target:String(goal.has_goal ? goal.target : 3),default:false}; }
function GoalEditor({initial,refresh}: {initial: GoalProgress; refresh: () => Promise<GoalProgress>}) {
 const {t} = useTranslation('progress'); const {api} = useAuth(); const current = useCurrentProgress(); const invalidate = useInvalidate();
 const form = useForm<GoalValues>({defaultValues:values(initial)}); const [goal,setGoal]=useState(initial); const [receipt,setReceipt]=useState<GoalReceipt|null>(null); const [error,setError]=useState<unknown>(null); const [refreshError,setRefreshError]=useState<unknown>(null); const [pending,setPending]=useState<GoalInput|null>(null); const [checked,setChecked]=useState<GoalProgress|null>(null); const [checking,setChecking]=useState(false);
 const save = useOperation(async (input:GoalInput) => confirmGoal(await api.post('/api/gamification/daily-goal',input),input));
 useDirtyGuard(form.formState.isDirty || !!pending || save.isPending);
 async function submit(input:GoalValues) {
  const payload=goalInput(input.type,input.target,input.default); if(!payload || pending || save.isPending)return;
  setPending(payload);setError(null);setRefreshError(null);setReceipt(null);setChecked(null);
  try {
   const result=await save.mutateAsync(payload);if(!current())return;
   setPending(null);setReceipt(result);form.reset({...input,default:false});setGoal({...result,goal_type:result.goal_type,target:result.target_value,current:result.current_value,has_goal:true,percentage:Math.min(100,Math.round(result.current_value/result.target_value*100))});
   try {await invalidate(['progress','goal']);} catch(value) {if(current())setRefreshError(value);}
  } catch(value) {if(current()){setError(value);if(value instanceof ApiError && !value.uncertain)setPending(null);}}
 }
 async function check() {
  setChecking(true);setRefreshError(null);try {const result=await refresh();if(current()){setChecked(result);setGoal(result);}}catch(value){if(current())setRefreshError(value);}finally{if(current())setChecking(false);}
 }
 function acceptRead() {if(!checked)return;form.reset(values(checked));setPending(null);setError(null);setReceipt(null);setChecked(null);}
 return <div className="stack"><p className="muted">{t('goalHint')}</p><p className="muted">{t('goalEditing')}</p>{goal.has_goal ? <><p>{t('goalProgress',{current:goal.current,target:goal.target,unit:t(`unit_${goal.goal_type}`)})}</p><progress max={100} value={goal.percentage} aria-label={t('goalProgress',{current:goal.current,target:goal.target,unit:t(`unit_${goal.goal_type}`)})}/><p>{t(goal.current>=goal.target?'targetReached':'targetPending')}</p><p>{t(goal.completed?'serverGoalComplete':'serverGoalOpen')}</p>{goal.completed && goal.current<goal.target && <p role="status">{t('goalCompletionMismatch')}</p>}</> : <p>{t('noGoal')}</p>}<GoalPolicy goal={goal}/>
 <form className="stack" onSubmit={form.handleSubmit(submit)} onChange={()=>setReceipt(null)}><fieldset className="form-grid" disabled={save.isPending || !!pending}><Field label={t('goalType')}><Select {...form.register('type')}>{goalTypes.map(type=><option value={type} key={type}>{t(`unit_${type}`)}</option>)}</Select></Field><Field label={t('target')} error={form.formState.errors.target?t('targetError'):undefined}><Input type="number" min="1" max="2147483647" step="1" {...form.register('target',{validate:value=>!!goalInput(form.getValues('type'),value,false)})}/></Field><label className="cluster"><input type="checkbox" {...form.register('default')}/>{t('defaultGoal')}</label></fieldset><Button type="submit" busy={save.isPending} disabled={!!pending}>{t('saveGoal')}</Button></form>
 <ErrorState error={error}/><ErrorState error={refreshError}/><SaveStatus state={save.isPending?'saving':pending?'uncertain':form.formState.isDirty?'dirty':receipt?'saved':'idle'}>{receipt?t('goalSaved',{date:receipt.goal_date,zone:receipt.timezone}):undefined}</SaveStatus>
 {pending && !save.isPending && <div className="stack"><p>{t('goalUncertain')}</p><Button variant="secondary" busy={checking} onClick={()=>void check()}>{t('checkGoal')}</Button>{checked && <><p>{t(goalMatches(checked,pending)?'matchingGoal':'differentGoal')}</p>{pending.save_as_default && <p>{t('defaultUnknown')}</p>}<Button variant="secondary" onClick={acceptRead}>{t('useServerGoal')}</Button></>}</div>}
 </div>;
}
