import { useId, useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/app/AuthProvider';
import { useDirtyGuard } from '@/app/DirtyGuard';
import { ApiError } from '@/lib/api';
import { useInvalidate, useOperation, useResource } from '@/lib/query';
import { Button, Card, ErrorState, Field, Input, LoadingState, PageHeader, SaveStatus, Select } from '@/components/ui';
import { aiDefaults, aiPayload, aiValues, confirmAI, parsed, parseAI, parseModels, parseTest, providers, sameDestination, type AIConfig, type AITest, type AIValues } from './contracts';
import { SettingsBack, useCurrentSettings } from './shared';
export function AISettingsPage() {
 const { scope } = useAuth(); const { t } = useTranslation('settings'); const resource = useResource<unknown>(['settings','ai'],'/api/settings/ai'); const result = parsed(resource.data,parseAI);
 if (resource.isPending) return <LoadingState/>;
 if (resource.error?.status === 409) return <AISettingsForm key={scope} initial={aiDefaults} repair/>;
 if (resource.error || result.error || !result.data) return <ErrorState error={resource.error || result.error} retry={() => void resource.refetch()}/>;
 return <div className="stack"><AISettingsForm key={scope} initial={result.data}/><p className="muted">{t('accountOnly')}</p></div>;
}
function endpointValid(value: string) { if (!value.trim()) return true; try { const url = new URL(value); return ['http:','https:'].includes(url.protocol) && !url.username && !url.password && !url.hash; } catch { return false; } }
function AISettingsForm({ initial, repair = false }: { initial: AIConfig; repair?: boolean }) {
 const { t } = useTranslation('settings'); const { api } = useAuth(); const current = useCurrentSettings(); const invalidate = useInvalidate(); const listId = useId();
 const [savedConfig,setSavedConfig] = useState(initial); const [saved,setSaved] = useState(false); const [repairing,setRepairing] = useState(repair); const [testResult,setTestResult] = useState<AITest | null>(null); const [catalog,setCatalog] = useState<{models:string[];provider:string;endpoint:string|null} | null>(null);
 const form = useForm<AIValues>({defaultValues:{...aiValues(initial),provider:repair ? '' : initial.provider}}); const provider = useWatch({control:form.control,name:'provider'}); const endpoint = useWatch({control:form.control,name:'endpoint'}); const clearKey = useWatch({control:form.control,name:'clear_api_key'}); useDirtyGuard(form.formState.isDirty);
 // Credentials live only in RHF's in-memory form and a request-local closure. Mutation variables and results never contain them.
 const save = useOperation<void,AIConfig>(async () => { const values = form.getValues(); return confirmAI(await api.post('/api/settings/ai',aiPayload(values)),values); }, async config => { if (!current()) return; setSavedConfig(config); form.reset(aiValues(config)); setSaved(true); setRepairing(false); setTestResult(null); setCatalog(null); await invalidate(['settings','ai']); });
 const test = useOperation<void,AITest>(async () => { const values = form.getValues(); return parseTest(await api.post('/api/settings/ai/test',aiPayload(values)),values); }, result => { if (current()) setTestResult(result); });
 const models = useOperation<void,{models:string[];provider:string;endpoint:string|null}>(async () => {
  const observed = parseAI(await api.get('/api/settings/ai')); if (!current()) throw new ApiError(0,'stale',false,'cancelled');
  if (!sameDestination(form.getValues(),observed)) { setSavedConfig(observed); throw new ApiError(409,'http',false,'conflict'); }
  const names = parseModels(await api.get(`/api/settings/ai/models?provider=${observed.provider}`),observed.provider);
  return {models:names,provider:observed.provider,endpoint:observed.endpoint};
 }, value => { if (current()) setCatalog(value); });
 const busy = save.isPending || test.isPending || models.isPending; const destinationMatches = !repairing && sameDestination({...form.getValues(),provider,endpoint},savedConfig);
 const edited = () => { setSaved(false); setTestResult(null); setCatalog(null); save.reset(); test.reset(); models.reset(); };
 return <div className="stack"><SettingsBack/><PageHeader title={t('ai')} description={t('aiDescription')}/>{repairing && <p role="status">{t('repair')}</p>}{savedConfig.compatibility_warnings.length > 0 && <p role="status">{t('compatibilityWarning')}</p>}
 <Card><form className="stack" onSubmit={form.handleSubmit(() => save.mutate(undefined))} onChange={edited}><fieldset disabled={busy} className="stack"><div className="form-grid">
 <Field label={t('provider')}><Select {...form.register('provider',{required:t('required')})}><option value="" disabled>{t('chooseProvider')}</option>{providers.map(value => <option key={value} value={value}>{({ollama:'Ollama',lm_studio:'LM Studio',openai:'OpenAI',openrouter:'OpenRouter'})[value]}</option>)}</Select></Field>
 <Field label={t('model')} error={form.formState.errors.model?.message}><Input list={listId} {...form.register('model',{required:t('required'),validate:v => !!v.trim() || t('required')})}/></Field>
 <Field label={t('endpoint')} hint={t('endpointHint')} error={form.formState.errors.endpoint?.message}><Input type="url" autoComplete="off" {...form.register('endpoint',{validate:v => endpointValid(v) || t('endpointInvalid')})}/></Field>
 <Field label={t('apiKey')} hint={t(savedConfig.has_api_key ? 'keySaved' : 'keyMissing')}><Input type="password" autoComplete="off" disabled={clearKey} {...form.register('api_key')}/></Field>
 <Field label={t('clearKey')} hint={t('keyClearHint')}><Input type="checkbox" {...form.register('clear_api_key')}/></Field>
 <Field label={t('temperature')} error={form.formState.errors.temperature?.message}><Input type="number" min="0" max="2" step="0.1" {...form.register('temperature',{valueAsNumber:true,validate:v => (Number.isFinite(v) && v >= 0 && v <= 2) || t('invalidRange')})}/></Field>
 <Field label={t('maxTokens')} error={form.formState.errors.max_tokens?.message}><Input type="number" min="1" max="16384" step="1" {...form.register('max_tokens',{valueAsNumber:true,validate:v => (Number.isInteger(v) && v >= 1 && v <= 16384) || t('invalidRange')})}/></Field>
 {provider === 'lm_studio' && <Field label={t('reasoning')}><Select {...form.register('reasoning_effort')}><option value="">{t('reasoningDefault')}</option><option value="none">{t('reasoningNone')}</option></Select></Field>}</div>
 <p>{t('keyDestination')}</p><p className="muted">{t('secretMemory')}</p><Button type="submit" busy={save.isPending} disabled={busy || !provider}>{t('save')}</Button></fieldset><ErrorState error={save.error}/><SaveStatus state={save.error?.uncertain ? 'uncertain' : save.isPending ? 'saving' : form.formState.isDirty ? 'dirty' : saved ? 'saved' : 'idle'}>{saved ? t('aiSaved') : undefined}</SaveStatus>
 <section className="stack"><h2>{t('test')}</h2><p>{t('testDescription')}</p><Button variant="secondary" busy={test.isPending} disabled={busy || !provider} onClick={() => { setTestResult(null); void form.handleSubmit(() => test.mutate(undefined))(); }}>{t('test')}</Button><ErrorState error={test.error}/>{testResult && <p role="status">{t('testSuccess',{provider:testResult.provider,model:testResult.model,ms:testResult.response_time_ms})}</p>}</section>
 <section className="stack"><h2>{t('catalog')}</h2><p>{t('catalogDescription')}</p>{!destinationMatches && <p role="status">{t('catalogSaveFirst')}</p>}<Button variant="secondary" disabled={busy || !destinationMatches} busy={models.isPending} onClick={() => { setCatalog(null); models.mutate(undefined); }}>{t('catalog')}</Button><ErrorState error={models.error}/>{catalog && <><p>{t('catalogFrom',{provider:catalog.provider,endpoint:catalog.endpoint || t('defaultEndpoint')})}</p><p role="status">{catalog.models.length ? t('catalogLoaded',{count:catalog.models.length}) : t('catalogEmpty')}</p><datalist id={listId}>{catalog.models.map(model => <option key={model} value={model}/>)}</datalist></>}</section></form></Card></div>;
}
