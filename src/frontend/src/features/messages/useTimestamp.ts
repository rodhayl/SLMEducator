import {useTranslation} from 'react-i18next';
import {useResource} from '@/lib/query';
import {formatTimestamp,validTimezone} from '@/lib/time';
import {record} from './contracts';
/** A missing preference uses visibly labelled UTC, never an assumed legacy timezone. */
export function useTimestamp(unknownLabel:string){const {i18n}=useTranslation();const query=useResource<unknown>(['settings','timezone'],'/api/settings/timezone');const zone=record(query.data)&&validTimezone(query.data.timezone)?query.data.timezone:'UTC';return (value:unknown)=>formatTimestamp(value,{locale:i18n.language,timezone:zone,unknownLabel});}
