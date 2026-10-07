import { act, screen, waitFor } from '@testing-library/react';
import { expect, it } from 'vitest';
import { DraftAdapter } from '@/lib/drafts';
import { mountProgress, json, submission, course, tree, progress } from './progress-fixtures';
it('shows distinct exact-resource course and assessment resume links using GETs only',async()=>{
 const app=await mountProgress();expect(await screen.findByRole('link',{name:'Continue: Pinned polygons'})).toHaveAttribute('href','/estudio/31?content_id=21&plan_id=11');expect(screen.getByRole('link',{name:'Resume Geometry check'})).toHaveAttribute('href','/intentos/41');expect(screen.getByText('Assessment #51 · Attempt #41')).toBeVisible();expect(app.calls.every(call=>call.method==='GET')).toBe(true);expect(app.calls.some(call=>call.path==='/api/gamification/daily-goal')).toBe(false);app.dispose();
});
it('continues the first incomplete material through a read-only preview when there is no active session',async()=>{
 const app=await mountProgress('/inicio','student','en',call=>call.path==='/api/learning/active'?json(null):undefined);expect(await screen.findByRole('link',{name:'Continue: Polygons'})).toHaveAttribute('href','/materiales/21?plan_id=11');expect(app.calls.every(call=>call.method==='GET')).toBe(true);app.dispose();
});
it('keeps explicit course selection available and revalidates its continuation',async()=>{
 const app=await mountProgress('/inicio','student','en',call=>call.path==='/api/study-plans/'?json([course,{...course,id:12,title:'Another course'}]):call.path==='/api/study-plans/12/tree'?json({...tree,id:12,title:'Another course'}):call.path==='/api/study-plans/12/my-progress'?json({...progress,study_plan_id:12,completed_content_ids:[],completion_percentage:0}):undefined);
 await screen.findByRole('link',{name:'Continue: Pinned polygons'});await app.user.selectOptions(screen.getByLabelText('Course to continue'),'12');expect(await screen.findByRole('link',{name:'Continue: Angles'})).toHaveAttribute('href','/materiales/20?plan_id=12');expect(app.calls.every(call=>call.method==='GET')).toBe(true);app.dispose();
});
it('does not turn failed continuation or foreign attempts into empty-success cards',async()=>{
 const app=await mountProgress('/inicio','student','en',call=>call.path==='/api/learning/active'?json({detail:'private exception'},503):call.path==='/api/assessments/submissions'?json([{...submission,student_id:999}]):undefined);await waitFor(()=>expect(screen.getAllByRole('alert').length).toBe(2));expect(screen.queryByText('No open assessments')).not.toBeInTheDocument();expect(screen.queryByRole('link',{name:'Resume Geometry check'})).not.toBeInTheDocument();expect(screen.queryByText('private exception')).not.toBeInTheDocument();app.dispose();
});
it('keeps no-course support useful without an AI or teacher availability check',async()=>{
 const app=await mountProgress('/inicio','student','en',call=>call.path==='/api/learning/active'?json(null):call.path==='/api/study-plans/' || call.path==='/api/assessments/submissions'?json([]):undefined);expect(await screen.findByText('No courses available')).toBeVisible();expect(screen.getAllByRole('link',{name:'Tutor and questions'}).at(-1)).toHaveAttribute('href','/tutor');expect(app.calls.some(call=>/settings\/ai/.test(call.path))).toBe(false);app.dispose();
});
it('shows teacher-owned correction queues without filtering them to currently enrolled students',async()=>{
 const app=await mountProgress('/inicio','teacher');expect(await screen.findByRole('link',{name:'Geometry check · Sam Example'})).toHaveAttribute('href','/correcciones/41?filter=pending');expect(await screen.findByText('No open help requests')).toBeVisible();expect(app.calls.some(call=>/students|gamification|learning\/active/.test(call.path))).toBe(false);app.dispose();
});
it('excludes visible but unmanageable assessments from teacher action counts',async()=>{
 const app=await mountProgress('/inicio','teacher','en',call=>call.path==='/api/assessments/'?json([{id:51,title:'Geometry check',description:null,is_published:true,question_count:1,created_at:'2026-10-07',can_manage:false}]):undefined);expect(await screen.findByText('No submissions waiting for correction')).toBeVisible();expect(screen.queryByRole('link',{name:'Geometry check · Sam Example'})).not.toBeInTheDocument();app.dispose();
});
it('gives administrators people, status and backup entry points without learner metrics',async()=>{
 const app=await mountProgress('/inicio','admin','es');expect(await screen.findByText('El servidor de la aplicación ha respondido · Versión 2.0.0')).toBeVisible();expect(screen.getByRole('link',{name:'Gestionar personas'})).toHaveAttribute('href','/personas');expect(screen.getByRole('link',{name:'Abrir herramientas de copia'})).toHaveAttribute('href','/administracion/copias');expect(app.calls.filter(call=>call.path!=='/api/auth/me').map(call=>call.path)).toEqual(['/api/classroom/messages/unread-count','/api/status']);app.dispose();
});
it('does not surface old-account home data after account replacement',async()=>{
 let resolve!: (value:Response)=>void;const app=await mountProgress('/inicio','student','en',call=>call.path==='/api/assessments/submissions'?new Promise<Response>(done=>{resolve=done;}):undefined);await screen.findByRole('link',{name:'Continue: Pinned polygons'});app.changeAccount(88,'admin');await act(()=>app.controller.login('new','synthetic-password'));await screen.findByRole('link',{name:'Manage people'});await act(async()=>resolve(json([submission])));expect(screen.queryByText('Geometry check')).not.toBeInTheDocument();app.dispose();
});

it('validates and prefers an owner-scoped stored location when no active session exists',async()=>{
 new DraftAdapter(7).write('learning-location','current',0,{planId:12,contentId:21});
 const app=await mountProgress('/inicio','student','en',call=>call.path==='/api/learning/active'?json(null):call.path==='/api/study-plans/'?json([course,{...course,id:12,title:'Stored course'}]):call.path==='/api/study-plans/12/tree'?json({...tree,id:12,title:'Stored course'}):call.path==='/api/study-plans/12/my-progress'?json({...progress,study_plan_id:12,completed_content_ids:[],completion_percentage:0}):undefined);
 expect(await screen.findByRole('link',{name:'Continue: Polygons'})).toHaveAttribute('href','/materiales/21?plan_id=12');expect(screen.getByLabelText('Course to continue')).toHaveValue('12');app.dispose();
});
it('passes over completed courses to offer the next actual incomplete material',async()=>{
 const app=await mountProgress('/inicio','student','en',call=>call.path==='/api/learning/active'?json(null):call.path==='/api/study-plans/'?json([course,{...course,id:12,title:'Next course'}]):call.path==='/api/study-plans/11/my-progress'?json({...progress,completed_content_ids:[20,21],completion_percentage:100}):call.path==='/api/study-plans/12/tree'?json({...tree,id:12,title:'Next course'}):call.path==='/api/study-plans/12/my-progress'?json({...progress,study_plan_id:12,completed_content_ids:[],completion_percentage:0}):undefined);
 expect(await screen.findByRole('link',{name:'Continue: Angles'})).toHaveAttribute('href','/materiales/20?plan_id=12');expect(screen.getByLabelText('Course to continue')).toHaveValue('12');expect(app.calls.every(call=>call.method==='GET')).toBe(true);app.dispose();
});
