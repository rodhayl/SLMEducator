import { useCallback, useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router';
import { useTranslation } from 'react-i18next';
import { legacyDashboardDestination } from '@/app/legacy-dashboard';
import { useAuth } from '@/app/AuthProvider';
import { DraftAdapter } from '@/lib/drafts';
import { positiveId } from '@/lib/ids';
import { Card, EmptyState, Field, PageHeader, Select } from '@/components/ui';
import { isRecord, isSession, sessionHref, sessionPlan, type StudySession } from '@/features/learning/contracts';
import { isCourseList, isCourseTree, isProgress, materialHref, type CourseSummary } from '@/features/courses/contracts';
import { isAssessmentList, isSubmissionList } from '@/features/assessments/model';
import { parseRequests } from '@/features/help/contracts';
import { parseStatus } from '@/features/settings/contracts';
import { invalid } from '@/features/progress/contracts';
import { ReadState, useRead, validated } from '@/features/progress/shared';

interface LocationMarker {planId:number;contentId:number}
function markerValid(value:unknown):value is LocationMarker {return isRecord(value) && typeof value.planId==='number' && positiveId(value.planId)!==null && typeof value.contentId==='number' && positiveId(value.contentId)!==null;}
export function HomePage() {
 const location=useLocation();const navigate=useNavigate();const {t}=useTranslation('home');const {user,scope}=useAuth();
 useEffect(()=>{const destination=legacyDashboardDestination(location.pathname,location.search,location.hash);if(destination && destination!==location.pathname+location.search+location.hash)void navigate(destination,{replace:true});},[location.pathname,location.search,location.hash,navigate]);
 if(!user)return null;
 return <div className="stack" key={scope}><PageHeader title={t('title',{name:user.first_name || user.username})} description={t(`intro_${user.role}`)}/>{user.role==='student'?<StudentHome/>:user.role==='teacher'?<TeacherHome/>:<AdminHome/>}</div>;
}
function StudentHome() {
 const {t}=useTranslation('home');const {user}=useAuth();
 const active=useRead(['learning','active'],'/api/learning/active',value=>value===null?null:isSession(value) && value.status==='active'?value:invalid());
 const attempts=useRead(['submissions'],'/api/assessments/submissions',value=>validated(value,(data): data is import('@/features/assessments/model').SubmissionSummary[]=>isSubmissionList(data,user!.id)));
 const drafts=attempts.data?.filter(item=>item.status==='draft');
 return <><div className="grid"><Card className="stack"><h2>{t('continueCourse')}</h2><ReadState query={active}>{active.data!==undefined && <ContinueCourse active={active.data}/>}</ReadState></Card><Card className="stack"><h2>{t('resumeAssessment')}</h2><p className="muted">{t('attemptHint')}</p><ReadState query={attempts}>{drafts && (drafts.length?<ul className="list">{drafts.map(attempt=><li key={attempt.id}><h3>{attempt.assessment_title}</h3><p>{t('attemptIdentity',{assessment:attempt.assessment_id,attempt:attempt.id})}</p><Link className="button button--primary" to={`/intentos/${attempt.id}`}>{t('resumeNamed',{title:attempt.assessment_title})}</Link></li>)}</ul>:<EmptyState title={t('noAttempt')}/>)}</ReadState><Link to="/evaluaciones">{t('browseAssessments')}</Link></Card></div><Card><h2>{t('studySupport')}</h2><p>{t('supportHint')}</p><div className="cluster"><Link to="/cursos">{t('allCourses')}</Link><Link to="/tutor">{t('help')}</Link><Link to="/ayuda">{t('helpRequests')}</Link><Link to="/progreso">{t('progress')}</Link></div></Card></>;
}
function ContinueCourse({active}: {active:StudySession|null}) {
 const {t}=useTranslation('home');const {user}=useAuth();const plans=useRead(['courses'],'/api/study-plans/',value=>validated(value,isCourseList));const [selection,setSelection]=useState<number|null>(null);
 const [skipped,setSkipped]=useState<number[]>([]);
 const onExhausted=useCallback((id:number)=>{if(selection===null)setSkipped(previous=>previous.includes(id)?previous:[...previous,id]);},[selection]);
 const [marker]=useState(()=>user?new DraftAdapter(user.id).read('learning-location','current',0,markerValid):null);
 const activePlan=active?sessionPlan(active):null;const ordered=[...(plans.data || [])].sort((a,b)=>Number(b.id===activePlan)-Number(a.id===activePlan) || Number(b.id===marker?.planId)-Number(a.id===marker?.planId));
 const selected=plans.data?.find(plan=>plan.id===selection) || ordered.find(plan=>!skipped.includes(plan.id)) || ordered[0];
 return <div className="stack">{active && !activePlan && <div className="panel"><h3>{t('continueMaterial')}</h3><p>{active.content_snapshot?.title || t('materialIdentity',{id:active.content_id})}</p><p>{t('sessionIdentity',{id:active.id})}</p><Link to={sessionHref(active)}>{t('resumeMaterial')}</Link></div>}<ReadState query={plans}>{plans.data && (selected?<><Field label={t('chooseCourse')}><Select value={selected.id} onChange={event=>setSelection(Number(event.target.value))}>{plans.data.map(plan=><option key={plan.id} value={plan.id}>{plan.title}</option>)}</Select></Field><CourseResume key={selected.id} plan={selected} active={active} marker={marker} onExhausted={onExhausted}/></>:<EmptyState title={t('noCourse')} description={t('noCourseHint')}/>)}</ReadState></div>;
}
function CourseResume({plan,active,marker,onExhausted}: {plan:CourseSummary;active:StudySession|null;marker:LocationMarker|null;onExhausted:(id:number)=>void}) {
 const {t}=useTranslation('home');const tree=useRead(['courses',plan.id,'tree'],`/api/study-plans/${plan.id}/tree`,value=>isCourseTree(value) && value.id===plan.id?value:invalid());
 const progress=useRead(['courses',plan.id,'progress'],`/api/study-plans/${plan.id}/my-progress`,value=>isProgress(value,plan.id)?value:invalid());
 const completed=new Set(progress.data?.completed_content_ids || []);const contents=[...(tree.data?.contents || [])].sort((a,b)=>a.phase_index-b.phase_index || a.order_index-b.order_index);
 const open=active && sessionPlan(active)===plan.id?contents.find(item=>item.id===active.content_id):undefined;
 const marked=marker?.planId===plan.id?contents.find(item=>item.id===marker.contentId && !completed.has(item.id)):undefined;
 const next=open || marked || contents.find(item=>item.id===progress.data?.last_content_id && !completed.has(item.id)) || contents.find(item=>!completed.has(item.id));
 const href=next?(open && active?sessionHref(active):materialHref(next.id,plan.id)):null;
 const nextTitle=open && active?.content_snapshot ? active.content_snapshot.title : next?.title;
 const incompatible=tree.data && progress.data && progress.data.completed_content_ids.some(id=>!tree.data!.contents.some(item=>item.id===id));
 const exhausted=!!tree.data && !!progress.data && !tree.error && !progress.error && !incompatible && !next;
 useEffect(()=>{if(exhausted)onExhausted(plan.id);},[exhausted,onExhausted,plan.id]);
 return <ReadState query={tree}><ReadState query={progress}>{tree.data && progress.data && (incompatible?<EmptyState title={t('progressChanged')} action={<Link to={`/cursos/${plan.id}`}>{t('openCourse')}</Link>}/>:<div className="stack"><h3>{tree.data.title}</h3><p>{t('completed',{count:completed.size,total:contents.length})}</p><progress max={Math.max(contents.length,1)} value={completed.size} aria-label={t('completed',{count:completed.size,total:contents.length})}/>{next && href?<><p>{nextTitle}</p><Link className="button button--primary" to={href}>{t('continueNamed',{title:nextTitle})}</Link></>:<p>{t(contents.length?'courseCompleted':'courseEmpty')}</p>}<Link to={`/cursos/${plan.id}`}>{t('openCourse')}</Link></div>)}</ReadState></ReadState>;
}
function TeacherHome() {
 const {t}=useTranslation('home');const grading=useRead(['grading-queue'],'/api/assessments/submissions?status=submitted&status=graded&status=ai_graded&status=returned',value=>validated(value,isSubmissionList));const assessments=useRead(['assessments'],'/api/assessments/',value=>validated(value,isAssessmentList));const help=useRead(['help-requests'],'/api/classroom/help',parseRequests);
 const manageable=new Set(assessments.data?.filter(item=>item.can_manage).map(item=>item.id));const waiting=grading.data?.filter(item=>manageable.has(item.assessment_id) && ['submitted','ai_graded','returned'].includes(item.status));const requests=help.data?.filter(item=>item.status==='open').sort((a,b)=>b.priority-a.priority || a.id-b.id);
 return <><div className="grid"><Card><h2>{t('grading')}</h2><p>{t('gradingScope')}</p><ReadState query={grading}><ReadState query={assessments}>{waiting && (waiting.length?<><p>{t('waitingCount',{count:waiting.length})}</p><ul className="list">{waiting.slice(0,3).map(item=><li key={item.id}><Link to={`/correcciones/${item.id}?filter=pending`}>{item.assessment_title} · {item.student_name}</Link></li>)}</ul></>:<EmptyState title={t('noGrading')}/>)}</ReadState></ReadState><Link to="/correcciones?filter=pending">{t('openGrading')}</Link></Card><Card><h2>{t('helpRequests')}</h2><ReadState query={help}>{requests && (requests.length?<><p>{t('openRequests',{count:requests.length})}</p><ul className="list">{requests.slice(0,3).map(request=><li key={request.id}><Link to={`/solicitudes/${request.id}?status=open`}>{request.subject || t('requestIdentity',{id:request.id})}</Link><p>{request.student_name || t('studentIdentity',{id:request.student_id})} · {t('priority',{value:request.priority})}</p></li>)}</ul></>:<EmptyState title={t('noRequests')}/>)}</ReadState><Link to="/solicitudes?status=open">{t('openHelp')}</Link></Card></div><Card><h2>{t('teaching')}</h2><div className="cluster"><Link to="/cursos">{t('courses')}</Link><Link to="/personas?role=student">{t('students')}</Link><Link to="/personas/nueva">{t('createStudent')}</Link><Link to="/mensajes">{t('messages')}</Link><Link to="/progreso?tab=leaderboard">{t('participation')}</Link></div></Card></>;
}
function AdminHome() {
 const {t}=useTranslation('home');const status=useRead(['settings','status'],'/api/status',parseStatus);
 return <div className="grid"><Card><h2>{t('people')}</h2><p>{t('peopleHint')}</p><div className="stack"><Link className="button button--primary" to="/personas">{t('managePeople')}</Link><Link to="/personas/nueva">{t('createPerson')}</Link></div></Card><Card><h2>{t('status')}</h2><ReadState query={status}>{status.data && <p>{t('serverVersion',{version:status.data.version})}</p>}</ReadState><p className="muted">{t('statusHint')}</p><Link to="/administracion/estado">{t('openStatus')}</Link></Card><Card><h2>{t('backups')}</h2><p>{t('backupHint')}</p><Link to="/administracion/copias">{t('openBackups')}</Link></Card></div>;
}
