import {describe,expect,it} from 'vitest';
import {filterRequests,helpFilters,parseRequests} from '@/features/help/contracts';
import {helpRequest} from './messages-fixtures';
describe('help request API contracts',()=>{
 it('accepts open and resolved with actual priority, without unread metadata',()=>{expect(parseRequests([helpRequest(),helpRequest({id:22,status:'resolved',priority:5})])).toHaveLength(2);expect(()=>parseRequests([helpRequest({status:'pending' as 'open'})])).toThrow();expect(()=>parseRequests([helpRequest({priority:6})])).toThrow();expect(()=>parseRequests([helpRequest()],7)).toThrow();});
 it('preserves safe list filters and excludes destinations or arbitrary context',()=>{expect(helpFilters(new URLSearchParams('q=angle&status=open&priority=2&return=https://evil.test')).toString()).toBe('q=angle&status=open&priority=2');expect(filterRequests([helpRequest(),helpRequest({id:22,status:'resolved'})],new URLSearchParams('status=open&priority=2&q=ANGLE'))).toHaveLength(1);});
});
