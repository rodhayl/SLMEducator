import { Link } from 'react-router';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/app/AuthProvider';
import { useResource } from '@/lib/query';
import { isCourseList } from '@/features/courses/contracts';
import { EmptyState, ErrorState, Field, LoadingState, Select } from '@/components/ui';
import { responseError } from './contracts';
export function CourseChoice({value,onChange,disabled=false}: {value:string;onChange:(value:string)=>void;disabled?:boolean}) {
 const {user}=useAuth(),{t}=useTranslation('authoring'), courses=useResource<unknown>(['courses'],'/api/study-plans/');
 if(courses.isPending)return <LoadingState/>;
 if(courses.error)return <ErrorState error={courses.error} retry={()=>{void courses.refetch();}}/>;
 if(!isCourseList(courses.data))return <ErrorState error={responseError()}/>;
 const options=courses.data.filter(course=>user?.role==='admin'||course.creator_id===user?.id);
 if(!options.length)return <EmptyState title={t('noCourses')} action={<Link to="/cursos/nuevo">{t('createCourse')}</Link>}/>;
 return <Field label={t('course')}><Select value={value} disabled={disabled} onChange={event=>onChange(event.target.value)}><option value="">{t('chooseCourse')}</option>{options.map(course=><option key={course.id} value={course.id}>{t('courseOption',{title:course.title,id:course.id})}</option>)}</Select></Field>;
}
