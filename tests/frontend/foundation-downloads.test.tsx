import { describe,it,expect,vi } from 'vitest';
import { act,renderHook } from '@testing-library/react';
import { ApiClient } from '@/lib/api';
import { useFileDownload } from '@/lib/downloads';
const auth=vi.hoisted(()=>({scope:'1:1',credentialEpoch:1,status:'authenticated'}));
vi.mock('@/app/AuthProvider',()=>({useAuth:()=>({...auth,getSnapshot:()=>auth})}));
function harness(transport:typeof fetch){let epoch=1;return {switchAccount(){epoch++;},api:new ApiClient({lease:()=>({token:'synthetic',epoch,scope:'1:1',permitted:true}),isCurrent:lease=>lease.epoch===epoch,unauthorized(){}},transport)};}
describe('owned binary export',()=>{
 it('validates MIME type, supports POST, and never decodes binary as JSON',async()=>{const transport=vi.fn().mockResolvedValue(new Response('archive',{headers:{'Content-Type':'application/zip'}}));const blob=await harness(transport).api.download('/api/portability/backup',{method:'POST',body:{confirm:true},expectedContentTypes:['application/zip']});expect(blob.size).toBe(7);expect(blob.type).toBe('application/zip');expect(transport.mock.calls[0][1]).toMatchObject({method:'POST',headers:{Authorization:'Bearer synthetic',Accept:'application/zip'}});});
 it('rejects an HTML error disguised as a successful ZIP response',async()=>{await expect(harness(vi.fn().mockResolvedValue(new Response('<h1>Error</h1>',{headers:{'Content-Type':'text/html'}}))).api.download('/api/portability/backup',{expectedContentTypes:['application/zip']})).rejects.toMatchObject({kind:'invalid',uncertain:false});});
 it('discards bytes decoded after the credential epoch changes',async()=>{let release!:(value:Blob)=>void;const response={ok:true,status:200,headers:new Headers({'Content-Type':'application/zip'}),blob:()=>new Promise<Blob>(done=>{release=done;})} as Response;const h=harness(vi.fn().mockResolvedValue(response));const pending=h.api.download('/api/portability/backup',{expectedContentTypes:['application/zip']});await Promise.resolve();h.switchAccount();release(new Blob(['private']));await expect(pending).rejects.toMatchObject({kind:'stale'});});
 it('keeps POST binary network outcome unknown and does not retry',async()=>{const transport=vi.fn().mockRejectedValue(Error());await expect(harness(transport).api.download('/api/portability/backup',{method:'POST',body:{confirm:true},expectedContentTypes:['application/zip']})).rejects.toMatchObject({uncertain:true});expect(transport).toHaveBeenCalledOnce();});
 it('sanitizes filename, bounds URL lifetime and rejects a stale handoff',()=>{
  auth.scope='1:1';auth.credentialEpoch=1;auth.status='authenticated';vi.useFakeTimers();
  const create=vi.fn().mockReturnValue('blob:synthetic'),revoke=vi.fn();class TestURL extends URL { static createObjectURL=create; static revokeObjectURL=revoke; } vi.stubGlobal('URL',TestURL);
  const click=vi.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(function(this:HTMLAnchorElement){expect(this.download).toBe('report_bad_.zip');});
  const view=renderHook(()=>useFileDownload());act(()=>view.result.current(new Blob(['synthetic']),'report/bad?.zip'));expect(document.querySelector('a[download]')).toBeNull();expect(revoke).not.toHaveBeenCalled();act(()=>vi.advanceTimersByTime(60_000));expect(revoke).toHaveBeenCalledWith('blob:synthetic');auth.scope='2:1';expect(()=>view.result.current(new Blob(['old']),'old.zip')).toThrow();expect(create).toHaveBeenCalledTimes(1);view.unmount();click.mockRestore();vi.useRealTimers();vi.unstubAllGlobals();
 });
});
