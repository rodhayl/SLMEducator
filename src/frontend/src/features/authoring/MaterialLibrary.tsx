import { Link, useSearchParams } from 'react-router';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/app/AuthProvider';
import { useResource } from '@/lib/query';
import { Badge, Button, Card, EmptyState, ErrorState, Field, Input, LoadingState, PageHeader, Select } from '@/components/ui';
import { isMaterialList } from '@/features/courses/contracts';
import { responseError } from './contracts';
export function MaterialLibraryPage() {
 const {t} = useTranslation('authoring'), {user} = useAuth(), [search,setSearch] = useSearchParams();
 const content = useResource<unknown>(['authoring','library'],'/api/content/');
 const query=search.get('q')||'',type=search.get('tipo')||'',owner=search.get('autor')||'';
 const change=(key:string,value:string)=>{const next=new URLSearchParams(search); if(value)next.set(key,value);else next.delete(key);setSearch(next,{replace:true});};
 const items=isMaterialList(content.data)?content.data.filter(item=>(!type||item.content_type===type)&&(!owner||String(item.creator_id)===owner)&&item.title.toLocaleLowerCase().includes(query.toLocaleLowerCase())):null;
 const staff=user?.role==='teacher'||user?.role==='admin';
 return <div className="stack"><PageHeader title={t('library')} description={t('libraryHint')} actions={staff?<div className="cluster"><Link className="button button--primary" to="/materiales/nuevo">{t('newMaterial')}</Link><Link to="/generar">{t('generate')}</Link></div>:<Link to="/tutor">{t('tutor')}</Link>}/>
 <nav className="cluster" aria-label={t('library')}><Link to="/cursos">{t('courses')}</Link><Link to="/materiales" aria-current="page">{t('library')}</Link></nav>
 <div className="form-grid"><Field label={t('search')}><Input type="search" value={query} onChange={event=>change('q',event.target.value)}/></Field><Field label={t('kind')}><Select value={type} onChange={event=>change('tipo',event.target.value)}><option value="">{t('all')}</option>{['lesson','exercise','assessment','qa'].map(kind=><option key={kind} value={kind}>{t(kind)}</option>)}</Select></Field><Field label={t('ownership')}><Select value={owner} onChange={event=>change('autor',event.target.value)}><option value="">{t('allVisible')}</option><option value={user?.id}>{t('mine')}</option></Select></Field></div>
 {content.isPending?<LoadingState/>:content.error?<ErrorState error={content.error} retry={()=>{void content.refetch();}}/>:!items?<ErrorState error={responseError()}/>:!items.length?<EmptyState title={t('noMaterials')} action={<Button variant="secondary" onClick={()=>setSearch({})}>{t('clearFilters')}</Button>}/>:<ul className="list">{items.map(item=><li key={item.id}><Card><div className="stack"><div className="cluster"><Link to={`/materiales/${item.id}`}>{item.title}</Link><Badge>{t(item.content_type)}</Badge><span>{t('difficultyNumber',{number:item.difficulty})}</span></div><div className="cluster">{item.public_reuse&&<Badge>{t('publicReuse')}</Badge>}{item.is_personal&&<Badge>{t('personal')}</Badge>}{staff&&item.can_edit===true&&item.content_type!=='qa'&&<Link to={`/materiales/${item.id}/editar`}>{t('edit')}</Link>}{item.content_type==='qa'&&<Link to="/tutor">{t('qaHandoff')}</Link>}</div></div></Card></li>)}</ul>}
 </div>;
}
