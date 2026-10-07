import { describe,it,expect } from 'vitest';
import { readFileSync,readdirSync,existsSync } from 'node:fs';
import { resolve,join } from 'node:path';
import { featurePaths } from '@/app/feature-routes';
import { navigation } from '@/app/route-contracts';
import { en,es } from '@/i18n/common';
const root=existsSync(resolve('src/frontend/src')) ? resolve('src/frontend/src') : resolve('src');
const sourceFiles=(directory:string):string[]=>readdirSync(directory,{withFileTypes:true}).flatMap(entry=>entry.isDirectory()?sourceFiles(join(directory,entry.name)):/\.(tsx?|css)$/.test(entry.name)?[join(directory,entry.name)]:[]);
function keys(value:object,prefix=''):string[]{return Object.entries(value).flatMap(([key,item])=>typeof item==='object'&&item!==null?keys(item,`${prefix}${key}.`):[`${prefix}${key}`]);}
describe('single frontend ownership graph',()=>{
 it('has matching common ES/EN keys and interpolation placeholders',()=>{expect(keys(en).sort()).toEqual(keys(es).sort());const stringify=(value:object):string=>Object.values(value).flatMap(item=>typeof item==='object'&&item!==null?stringify(item):[String(item)]).join('\n');expect(stringify(en).match(/{{\w+}}/g)).toEqual(stringify(es).match(/{{\w+}}/g));});
 it('implements every navigation destination without migration placeholders',()=>{const paths=new Set(['inicio',...Object.values(featurePaths).flat()]);for(const item of navigation)expect(paths.has(item.path.slice(1)),item.path).toBe(true);expect(paths.has('ajustes/datos')).toBe(true);expect(readFileSync(join(root,'app/router.tsx'),'utf8')).not.toContain('PendingPage');});
 it('has unique lazy domain paths',()=>{const paths=Object.values(featurePaths).flat();expect(new Set(paths).size).toBe(paths.length);expect(paths).toContain('estudio/:sessionId');expect(paths).toContain('personas/nueva');});
 it('has one HTML injection boundary and no imported executable legacy GUI',()=>{const files=sourceFiles(root);const injection=files.filter(file=>readFileSync(file,'utf8').includes('dangerouslySetInnerHTML'));expect(injection).toEqual([join(root,'components/content/ContentRenderer.tsx')]);for(const file of files){const content=readFileSync(file,'utf8');expect(content, file).not.toMatch(/window\.(AuthService|SLM\w+)|bootstrap\.|on(?:click|change)=|static\/js\/|src\/web\//);}});
 it('has no credentials or query data persistence outside approved adapters',()=>{for(const file of sourceFiles(root).filter(file=>file.includes('/features/'))){const content=readFileSync(file,'utf8');expect(content,file).not.toMatch(/localStorage\.|sessionStorage\.|\bfetch\(/);}});
 it('keeps the API origin relative and prohibits automatic mutation retry',()=>{const api=readFileSync(join(root,'lib/api.ts'),'utf8');const query=readFileSync(join(root,'lib/query.ts'),'utf8');expect(api).not.toMatch(/127\.0\.0\.1|localhost|https:\/\//);expect(query).toContain('mutations: { retry: false');});
});

describe('measured theme token pairs',()=>{
 const css=readFileSync(join(root,'styles/tokens.css'),'utf8');
 const palette=(pattern:RegExp)=>Object.fromEntries([...(css.match(pattern)?.[1]||'').matchAll(/--([\w-]+):\s*(#[a-fA-F0-9]{3,6})/g)].map(match=>[match[1],match[2]]));
 const light=palette(/:root\s*\{([^}]+)}/),dark=palette(/:root\[data-theme='dark'\]\s*\{([^}]+)}/);
 const luminance=(hex:string)=>{if(hex.length===4)hex='#'+[...hex.slice(1)].map(c=>c+c).join('');return [1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)/255).reduce((sum,value,index)=>sum+(value<=.04045?value/12.92:((value+.055)/1.055)**2.4)*[.2126,.7152,.0722][index]!,0);};
 const contrast=(a:string,b:string)=>{const [lo,hi]=[luminance(a),luminance(b)].sort((x,y)=>x-y);return (hi!+.05)/(lo!+.05);};
 for(const [name,tokens] of [['light',light],['dark',dark]] as const){
  it.each([['foreground','background',4.5],['secondary','surface',4.5],['on-primary','primary',4.5],['danger','danger-soft',4.5],['success','surface',4.5],['warning','surface',4.5],['border','surface',3]] as const)(`${name}: %s on %s meets its explicit threshold`,(text,surface,min)=>expect(contrast(tokens[text]!,tokens[surface]!)).toBeGreaterThanOrEqual(min));
 }
});
