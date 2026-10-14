import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { useResource } from '@/lib/query';
import { Card, ErrorState, LoadingState, PageHeader } from '@/components/ui';
import { ContentRenderer } from '@/components/content/ContentRenderer';
import { isQuestionList, isQuestion, responseError } from './contracts';
export function LegacyQuestions(){const {t}=useTranslation('tutor');const query=useResource<unknown>(['legacy-questions'],'/api/content/?content_type=qa');return <div className="stack"><PageHeader title={t('legacyQuestions')} actions={<Link to="/tutor">{t('unifiedTitle')}</Link>}/>{query.isPending?<LoadingState/>:query.error?<ErrorState error={query.error}/>:isQuestionList(query.data)?query.data.map(q=><LegacyQuestion key={q.id} id={q.id}/>):<ErrorState error={responseError()}/>}</div>;}
function LegacyQuestion({id}:{id:number}){const query=useResource<unknown>(['legacy-question',id],`/api/content/${id}`);if(query.isPending)return <LoadingState/>;if(query.error||!isQuestion(query.data))return <ErrorState error={query.error||responseError()}/>;return <Card><h2>{query.data.title}</h2><ContentRenderer value={query.data.content_data.question||query.data.content_data.content||''}/>{query.data.content_data.answer&&<ContentRenderer value={query.data.content_data.answer}/>}</Card>;}
