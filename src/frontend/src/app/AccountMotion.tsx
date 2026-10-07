import { useEffect } from 'react';
import { useAuth } from './AuthProvider';
import { useAppearance } from './AppearanceProvider';
import { useResource } from '@/lib/query';
import { parsed, parseApp } from '@/features/settings/contracts';
/** Reuse the account settings query; no extra persistent appearance store. */
export function AccountMotion() {
 const {status,scope}=useAuth(),{setAnimations}=useAppearance();
 const settings=useResource<unknown>(['settings','app'],status==='authenticated'?'/api/settings/app':null);
 const result=parsed(settings.data,parseApp);
 const confirmed=!settings.error&&!result.error?result.data?.enable_animations:undefined;
 useEffect(()=>{setAnimations(true);return()=>setAnimations(true);},[scope,setAnimations]);
 useEffect(()=>{if(status==='authenticated'&&confirmed!==undefined)setAnimations(confirmed);},[status,scope,confirmed,setAnimations]);
 return null;
}
