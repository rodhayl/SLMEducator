import { afterEach,beforeEach,describe,expect,it,vi } from 'vitest';
import { act,fireEvent,screen,waitFor,within } from '@testing-library/react';
import { mountSettings,json } from './settings-fixtures';
import { aiDefaults } from '@/features/settings/contracts';
const mounted:Array<Awaited<ReturnType<typeof mountSettings>>>=[];
const mount:typeof mountSettings=async(...args)=>{const result=await mountSettings(...args);mounted.push(result);return result;};
beforeEach(()=>vi.spyOn(window,'scrollTo').mockImplementation(()=>undefined));
afterEach(()=>{mounted.splice(0).forEach(h=>h.dispose());vi.restoreAllMocks();});
describe('Account/settings synthetic UI',()=>{
 it('shows profile unknown timestamp provenance and saves only own fields',async()=>{
  const h=await mount('/ajustes/perfil','student');expect(await screen.findByText('Synthetic participation badge')).toBeInTheDocument();expect(screen.queryByText('Not earned')).not.toBeInTheDocument();expect(await screen.findByText(/2025-01-01T10:00:00 \(Timezone unknown\)/)).toBeInTheDocument();
  await h.user.clear(screen.getByLabelText('First name'));await h.user.type(screen.getByLabelText('First name'),'Sam');await h.user.click(screen.getByRole('button',{name:'Save changes'}));
  expect(await screen.findByText('Your profile was saved.')).toBeInTheDocument();expect(h.calls.find(c=>c.path==='/api/auth/profile')?.body).toEqual({first_name:'Sam',last_name:'Example',email:'teacher@example.test',grade_level:'8'});expect(h.controller.snapshot().user?.first_name).toBe('Sam');
 });
 it('normalizes profile fields to the backend contract before confirming save',async()=>{
  const h=await mount('/ajustes/perfil','student');await h.user.clear(await screen.findByLabelText('First name'));await h.user.type(screen.getByLabelText('First name'),'  Sam  ');await h.user.clear(screen.getByLabelText('Email'));await h.user.type(screen.getByLabelText('Email'),'SAM@Example.Test');await h.user.click(screen.getByRole('button',{name:'Save changes'}));expect(await screen.findByText('Your profile was saved.')).toBeInTheDocument();expect(screen.getByLabelText('First name')).toHaveValue('Sam');expect(screen.getByLabelText('Email')).toHaveValue('sam@example.test');
 });
 it('password confirmation stores no mutation variables and locks after confirmed revocation',async()=>{
  const h=await mount('/ajustes/seguridad');const secret='SyntheticExample123!';
  await h.user.type(await screen.findByLabelText('Current password'),'OldSynthetic123!');await h.user.type(screen.getByLabelText('New password'),secret);await h.user.type(screen.getByLabelText('Repeat new password'),secret);
  await h.user.click(screen.getByRole('button',{name:'Change password'}));expect(h.calls.filter(c=>c.path==='/api/auth/change-password')).toHaveLength(0);
  await h.user.click(within(await screen.findByRole('dialog')).getByRole('button',{name:'Change password'}));await waitFor(()=>expect(h.controller.snapshot().status).toBe('locked'));
  expect(h.queries.getMutationCache().getAll().every(m=>m.state.variables===undefined)).toBe(true);expect(JSON.stringify(h.queries.getMutationCache().getAll().map(m=>m.state.data))).not.toContain(secret);expect(localStorage.getItem('slm-drafts')).toBeNull();
 });
 it('rejects mismatched passwords without a request',async()=>{
  const h=await mount('/ajustes/seguridad');await h.user.type(await screen.findByLabelText('Current password'),'OldSynthetic123!');await h.user.type(screen.getByLabelText('New password'),'SyntheticExample123!');await h.user.type(screen.getByLabelText('Repeat new password'),'different');await h.user.click(screen.getByRole('button',{name:'Change password'}));expect(await screen.findByText('The new passwords must match.')).toBeInTheDocument();expect(h.calls.some(c=>c.path==='/api/auth/change-password')).toBe(false);
 });
 it('tests form values separately from saving and keeps provider credentials out of cache',async()=>{
  const h=await mount('/ajustes/ia');const key='SyntheticKeyOnly';await screen.findByLabelText('Model name');expect(h.calls.some(c=>c.path.includes('/ai/test')||c.path.includes('/ai/models'))).toBe(false);
  await h.user.type(screen.getByLabelText('New provider API key'),key);await h.user.clear(screen.getByLabelText('Model name'));await h.user.type(screen.getByLabelText('Model name'),'synthetic-model');await h.user.click(screen.getByRole('button',{name:'Test connection'}));expect(await screen.findByText(/Connected to ollama \/ synthetic-model/)).toBeInTheDocument();expect(h.calls.some(c=>c.path==='/api/settings/ai'&&c.method==='POST')).toBe(false);
  expect(h.queries.getMutationCache().getAll().every(m=>m.state.variables===undefined)).toBe(true);expect(JSON.stringify(h.queries.getMutationCache().getAll().map(m=>m.state.data))).not.toContain(key);
  await h.user.click(screen.getByRole('button',{name:'Save changes'}));expect(await screen.findByText('AI configuration saved.')).toBeInTheDocument();expect(screen.getByLabelText('New provider API key')).toHaveValue('');expect(h.calls.find(c=>c.path==='/api/settings/ai'&&c.method==='POST')?.body?.api_key).toBe(key);
 });
 it('explains configured catalog provenance and blocks unsaved destinations',async()=>{
  const h=await mount('/ajustes/ia');const button=await screen.findByRole('button',{name:'Load configured model catalog'});await h.user.click(button);expect(await screen.findByText(/Catalog from saved ollama configuration/)).toBeInTheDocument();await h.user.type(screen.getByLabelText('Endpoint URL'),'http://different.test');expect(button).toBeDisabled();expect(screen.queryByText(/Catalog from saved ollama configuration/)).not.toBeInTheDocument();expect(h.calls.filter(c=>c.path.includes('/ai/models'))).toHaveLength(1);
 });
 it('rechecks saved catalog destination before any provider request',async()=>{
  const h=await mount('/ajustes/ia');await screen.findByLabelText('Model name');h.intercept(call=>call.path==='/api/settings/ai'&&call.method==='GET'?json({...aiDefaults,endpoint:'http://changed.test'}):undefined);await h.user.click(screen.getByRole('button',{name:'Load configured model catalog'}));expect(await screen.findByRole('alert')).toBeInTheDocument();expect(h.calls.some(c=>c.path.includes('/ai/models'))).toBe(false);expect(screen.getByRole('button',{name:'Load configured model catalog'})).toBeDisabled();
 });
 it('repairs only a known unsupported saved configuration without automatic provider calls',async()=>{
  const h=await mount('/ajustes/ia','admin','en',call=>call.path==='/api/settings/ai'&&call.method==='GET'?json({detail:'unsupported'},409):undefined);
  expect(await screen.findByText(/saved provider is unsupported/)).toBeInTheDocument();expect(screen.getByRole('button',{name:'Load configured model catalog'})).toBeDisabled();expect(screen.getByRole('button',{name:'Save changes'})).toBeDisabled();await h.user.selectOptions(screen.getByLabelText('Provider'),'ollama');await h.user.click(screen.getByRole('button',{name:'Save changes'}));expect(await screen.findByText('AI configuration saved.')).toBeInTheDocument();expect(h.calls.some(c=>c.path.includes('/ai/test'))).toBe(false);
 });
 it('malformed saves do not clear form secrets or show success',async()=>{
  const h=await mount('/ajustes/ia');await h.user.type(await screen.findByLabelText('New provider API key'),'SyntheticKeep');h.intercept(call=>call.path==='/api/settings/ai'&&call.method==='POST'?json({...aiDefaults,model:'wrong'}):undefined);await h.user.click(screen.getByRole('button',{name:'Save changes'}));expect(await screen.findByRole('alert')).toBeInTheDocument();expect(screen.getByLabelText('New provider API key')).toHaveValue('SyntheticKeep');expect(screen.queryByText('AI configuration saved.')).not.toBeInTheDocument();
 });
 it('applies confirmed appearance through the shared provider',async()=>{
  const h=await mount('/ajustes/apariencia');await screen.findByRole('heading',{name:'Appearance and language'});const card=screen.getByRole('button',{name:'Save changes'}).closest('form')!;
  await h.user.selectOptions(within(card).getByLabelText('Theme'),'dark');await h.user.selectOptions(within(card).getByLabelText('Reading text size'),'extra-large');await h.user.click(within(card).getByLabelText('Enable interface animations'));await h.user.click(within(card).getByRole('button',{name:'Save changes'}));expect(await screen.findByText('Appearance and language saved.')).toBeInTheDocument();expect(document.documentElement.dataset.theme).toBe('dark');expect(document.documentElement.style.getPropertyValue('--reading-size')).toBe('1.5rem');
 });
 it('timezone input is explicit and updates provenance without migration',async()=>{
  const h=await mount('/ajustes/zona-horaria');expect(await screen.findByText('Source: application default (UTC)')).toBeInTheDocument();const input=screen.getByLabelText('Timezone');await h.user.clear(input);await h.user.type(input,'Europe/Madrid');await h.user.click(screen.getByRole('button',{name:'Save changes'}));expect(await screen.findByText('Timezone saved. Historical records were not converted.')).toBeInTheDocument();expect(h.calls.find(c=>c.path==='/api/settings/timezone'&&c.method==='PUT')?.body).toEqual({timezone:'Europe/Madrid'});expect(screen.getByText('Source: your explicit selection')).toBeInTheDocument();
 });
 it('does no application status query for a student direct route',async()=>{const h=await mount('/administracion/estado','student');await waitFor(()=>expect(h.controller.snapshot().status).toBe('authenticated'));expect(h.calls.some(c=>c.path==='/api/status')).toBe(false);});
 it('shows only read-only status for admin and no global AI manager',async()=>{const h=await mount('/administracion/estado','admin');expect(await screen.findByText('Reported server version: 2.0.0')).toBeInTheDocument();expect(screen.queryByRole('button',{name:/stop|start|restart/i})).not.toBeInTheDocument();expect(h.calls.every(c=>c.method==='GET')).toBe(true);});
 it('late old-account AI save cannot clear a new account form',async()=>{
  const h=await mount('/ajustes/ia');await h.user.type(await screen.findByLabelText('New provider API key'),'OldAccountKey');let finish!:(response:Response)=>void;h.intercept(call=>call.path==='/api/settings/ai'&&call.method==='POST'?new Promise<Response>(resolve=>{finish=resolve;}):undefined);await h.user.click(screen.getByRole('button',{name:'Save changes'}));await waitFor(()=>expect(finish).toBeDefined());h.changeAccount('teacher',9);await act(async()=>{await h.controller.login('synthetic-9','unused');});await screen.findByLabelText('New provider API key');fireEvent.change(screen.getByLabelText('New provider API key'),{target:{value:'NewAccountKey'}});await act(async()=>finish(json({...aiDefaults,has_api_key:true})));expect(screen.getByLabelText('New provider API key')).toHaveValue('NewAccountKey');expect(screen.queryByText('AI configuration saved.')).not.toBeInTheDocument();
 });
});
