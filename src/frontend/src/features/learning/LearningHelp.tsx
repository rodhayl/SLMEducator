import { Link } from 'react-router';
import { useTranslation } from 'react-i18next';
export interface LearningHelpProps { contentId:number;planId:number|null;sessionId:number;contextRevision:Record<string,unknown>|null;active:boolean;onDirtyChange?:(dirty:boolean)=>void }
export function LearningHelp({contentId,planId,sessionId,active}:LearningHelpProps){const {t}=useTranslation('tutor');const params=new URLSearchParams({content_id:String(contentId),session_id:String(sessionId)});if(planId)params.set('plan_id',String(planId));return <section hidden={!active} inert={!active}><Link to={`/tutor?${params}`}>{t('unifiedTitle')}</Link></section>;}
