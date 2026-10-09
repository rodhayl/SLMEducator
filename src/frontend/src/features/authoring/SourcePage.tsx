import { useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import { useForm, useWatch } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/app/AuthProvider';
import { useDirtyGuard } from '@/app/DirtyGuard';
import { useInvalidate, useOperation, useResource } from '@/lib/query';
import { ApiError } from '@/lib/api';
import { positiveId } from '@/lib/ids';
import { isWorkflow } from '@/features/courses/contracts';
import { Badge, Button, Card, ConfirmDialog, EmptyState, ErrorState, Field, Input, LoadingState, PageHeader, SaveStatus, Textarea } from '@/components/ui';
import { CourseChoice } from './CourseChoice';
import { StaffRequired, useContinuation } from './MaterialEditor';
import { authoredSource, isSourceDocument, isSourceInput, isSourceReceipt, record, responseError, sourceInput, validationError, type SourceDocument, type SourceInput } from './contracts';
export function SourcePage() {
 const {user,scope}=useAuth(),{t}=useTranslation('authoring'),[search,setSearch]=useSearchParams(),id=positiveId(search.get('plan_id'));
 if(user?.role==='student')return <StaffRequired/>;
 if(search.has('plan_id')&&!id)return <EmptyState title={t('unavailable')}/>;
 return <div className="stack"><PageHeader title={t('sources')} description={t('sourceHint')}/><CourseChoice value={id?String(id):''} onChange={value=>setSearch(value?{plan_id:value}:{})}/>{id&&<SourceRoute key={`${scope}:${id}`} planId={id}/>}</div>;
}
function SourceRoute({planId}:{planId:number}) {
 const source=useResource<unknown>(['authoring','source',planId],`/api/study-plans/${planId}/source`), workflow=useResource<unknown>(['courses',planId,'workflow'],`/api/study-plans/${planId}/workflow`);
 if(source.isPending||workflow.isPending)return <LoadingState/>;
 if(source.error||workflow.error)return <ErrorState error={source.error||workflow.error} retry={()=>{void source.refetch();void workflow.refetch();}}/>;
 if(!record(source.data)||!(source.data.source===null||isSourceDocument(source.data.source))||!isWorkflow(workflow.data))return <ErrorState error={responseError()}/>;
 return <SourceEditor planId={planId} initial={source.data.source} readOnly={workflow.data.read_only} key={planId}/>;
}
function SourceEditor({planId,initial,readOnly}:{planId:number;initial:SourceDocument|null;readOnly:boolean}) {
 const {api}=useAuth(),{t}=useTranslation('authoring'),current=useContinuation(),invalidate=useInvalidate();
 const [manifest,setManifest]=useState<SourceInput|null>(initial?sourceInput(initial):null),[proposal,setProposal]=useState<SourceInput|null>(null),[decision,setDecision]=useState<'save'|'adopt'|'reload'|null>(null),[notice,setNotice]=useState('');
 const form=useForm<{filename:string;content:string}>({defaultValues:{filename:initial?.filename||t('authoredText'),content:initial?.extracted_text||''}}), values=useWatch({control:form.control});
 const upload=useOperation(async(file:File)=>{const error=!/\.(pdf|txt|md)$/i.test(file.name)?'fileType':file.size===0?'fileEmpty':file.size>10*1024*1024?'fileSize':null;if(error)throw new ApiError(422,'invalid',false,'validation',{file:error});const data=new FormData();data.append('file',file);const result=await api.post<unknown>('/api/upload/source-material',data);if(!isSourceInput(result))throw responseError();return result;},result=>{if(current())setProposal(result);});
 const save=useOperation(async()=>{const value=form.getValues(),input=manifest&&value.content===manifest.extracted_text?{...manifest,filename:value.filename}:authoredSource(value.filename,value.content);if(!isSourceInput(input))throw validationError();const result=await api.put<unknown>(`/api/study-plans/${planId}/source`,input);if(!isSourceReceipt(result,input.extracted_text))throw responseError(true);return result;},async result=>{if(!current())return;setManifest(sourceInput(result.source));form.reset({filename:result.source.filename,content:result.source.extracted_text});setDecision(null);setNotice(t('sourceSaved'));await invalidate(['authoring','source',planId]);await invalidate(['courses']);});
 const reload=useOperation(async()=>{const result=await api.get<unknown>(`/api/study-plans/${planId}/source`);if(!record(result)||!(result.source===null||isSourceDocument(result.source)))throw responseError();return result.source;},result=>{if(!current())return;setManifest(result?sourceInput(result):null);form.reset({filename:result?.filename||t('authoredText'),content:result?.extracted_text||''});setDecision(null);setProposal(null);save.reset();});
 const busy=save.isPending||reload.isPending,conflictBusy=busy||upload.isPending,uncertain=save.error instanceof ApiError&&save.error.uncertain;
 const fileError=upload.error instanceof ApiError && ['fileType','fileEmpty','fileSize'].includes(upload.error.fieldErrors.file) ? upload.error.fieldErrors.file : null;
 useDirtyGuard(form.formState.isDirty||!!proposal||save.isPending||upload.isPending);
 return <div className="stack"><div className="cluster"><Link to={`/cursos/${planId}/editar`}>{t('courseWorkflow')}</Link><Link to={`/generar?plan_id=${planId}`}>{t('generate')}</Link></div>{readOnly&&<EmptyState title={t('readOnly')} description={t('revisionHint')} action={<Link to={`/cursos/${planId}/editar`}>{t('createRevision')}</Link>}/>}
 <SaveStatus state={uncertain?'uncertain':busy?'saving':form.formState.isDirty?'dirty':save.isSuccess?'saved':'idle'}/>
 {!readOnly&&<Field label={t('upload')} hint={t('uploadHint')} error={fileError?<span role="alert">{t(fileError)}</span>:undefined}><Input type="file" accept=".pdf,.txt,.md" disabled={conflictBusy||uncertain} onChange={event=>{const file=event.target.files?.[0];if(file)upload.mutate(file);event.target.value='';}}/></Field>}
 {upload.isPending&&<LoadingState/>}{upload.error&&!fileError&&<ErrorState error={upload.error}/>}
 {proposal&&<Card><div className="stack"><h2>{t('extractedProposal')}</h2><SourceCoverage source={proposal}/><p>{t('uploadNotSaved')}</p><Button disabled={conflictBusy} onClick={()=>setDecision('adopt')}>{t('useExtracted')}</Button></div></Card>}
 <form className="stack" onSubmit={form.handleSubmit(()=>setDecision('save'))}><fieldset disabled={readOnly||busy||uncertain}><div className="stack"><Field label={t('filename')}><Input maxLength={255} {...form.register('filename',{required:t('required')})}/></Field><Field label={t('sourceText')} error={form.formState.errors.content?.message}><Textarea rows={14} maxLength={100000} {...form.register('content',{validate:value=>!!value.trim()||t('required')})}/></Field></div></fieldset>{manifest&&<SourceCoverage source={values.content===manifest.extracted_text?manifest:authoredSource(values.filename||'',values.content||'')}/>}<p>{t('sourceEditWarning')}</p><div className="cluster">{!readOnly&&<Button type="submit" busy={save.isPending} disabled={conflictBusy||uncertain}>{t('saveSource')}</Button>}<Button type="button" variant="secondary" disabled={conflictBusy} onClick={()=>setDecision('reload')}>{t('reloadSaved')}</Button></div></form>
 {notice&&<p role="status">{notice}</p>}{save.error&&<ErrorState error={save.error}/>} {reload.error&&<ErrorState error={reload.error}/>} {uncertain&&<p>{t('uncertain')}</p>}
 <ConfirmDialog open={decision!==null} onOpenChange={open=>{if(!open&&!conflictBusy)setDecision(null);}} title={t(decision==='save'?'replaceSourceTitle':decision==='adopt'?'useExtracted':'reloadTitle')} description={t(decision==='save'?'replaceSourceDescription':'reloadDescription')} confirmLabel={t(decision==='save'?'saveSource':decision==='adopt'?'useExtracted':'reloadSaved')} busy={conflictBusy} onConfirm={()=>{if(conflictBusy)return;if(decision==='save')save.mutate(undefined);else if(decision==='reload')reload.mutate(undefined);else if(proposal){setManifest(proposal);form.setValue('filename',proposal.filename,{shouldDirty:true});form.setValue('content',proposal.extracted_text,{shouldDirty:true});setProposal(null);setDecision(null);}}}/>
 </div>;
}
export function SourceCoverage({source}:{source:SourceInput}) {const {t}=useTranslation('authoring');return <div className="stack"><div className="cluster"><Badge>{t(`coverage.${source.coverage}`)}</Badge><span>{t('characters',{count:source.extracted_text.length})}</span>{source.truncated&&<Badge tone="warning">{t('truncated')}</Badge>}</div>{source.unreadable_pages.length>0&&<p>{t('unreadablePages',{pages:source.unreadable_pages.join(', ')})}</p>}<details><summary>{t('sourceDetails')}</summary><p>{source.filename}</p><p>{t('fileHash')}: {source.source_version||t('unknown')}</p><p>{t('parser')}: {source.parser||t('unknown')}</p><p>{t('sourceSections')}: {source.sections.map(part=>part.reference).join(', ')||t('authoredText')}</p><p>{t('noBinary')}</p></details></div>;}
