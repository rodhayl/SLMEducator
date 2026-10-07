import { useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/app/AuthProvider';
import { useDirtyGuard } from '@/app/DirtyGuard';
import { positiveId } from '@/lib/ids';
import { Button, PageHeader } from '@/components/ui';
import { Conversation } from './Conversation';
import { Questions } from './Questions';
import './tutor.css';
export function TutorPage(){const {scope}=useAuth();return <TutorWorkspace key={scope}/>;}
function TutorWorkspace(){
 const {t}=useTranslation('tutor'),{status,user}=useAuth(),[params]=useSearchParams();
 const [mode,setMode]=useState(params.get('tab')==='questions'||params.has('question_id')?'questions':'conversation');
 const [chatDirty,setChatDirty]=useState(false),[questionDirty,setQuestionDirty]=useState(false);
 useDirtyGuard(chatDirty||questionDirty);
 const active=status==='authenticated';
 return <div className="stack tutor-workspace" hidden={!active} inert={!active}>
  <PageHeader title={t('title')} description={t('subtitle')} actions={<Link to="/ayuda">{t(user?.role==='student'?'myRequests':'helpRequests')}</Link>}/>
  <div className="cluster"><Button variant={mode==='conversation'?'primary':'secondary'} aria-pressed={mode==='conversation'} onClick={()=>setMode('conversation')}>{t('conversation')}</Button><Button variant={mode==='questions'?'primary':'secondary'} aria-pressed={mode==='questions'} onClick={()=>setMode('questions')}>{t(user?.role==='student'?'myQuestions':'sharedQuestions')}</Button></div>
  <Conversation active={active&&mode==='conversation'} onDirty={setChatDirty} initialContent={positiveId(params.get('content_id'))} initialPlan={positiveId(params.get('plan_id')||params.get('study_plan_id'))}/>
  <Questions active={active&&mode==='questions'} onDirty={setQuestionDirty} initialId={positiveId(params.get('question_id'))}/>
 </div>;
}
