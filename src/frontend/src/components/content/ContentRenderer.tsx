import { useMemo } from 'react';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
export function safeContent(value: string, format: 'markdown' | 'html' = 'markdown'): string {
 const html = format === 'markdown' ? marked.parse(value, { async: false }) : value;
 const safe = DOMPurify.sanitize(html, { ALLOWED_TAGS: ['p','br','hr','strong','b','em','i','u','s','del','h1','h2','h3','h4','h5','h6','ul','ol','li','blockquote','pre','code','a','table','thead','tbody','tr','th','td','div','span','sup','sub'], ALLOWED_ATTR: ['href','title','colspan','rowspan'], ALLOW_DATA_ATTR: false, ALLOW_ARIA_ATTR: false, SANITIZE_NAMED_PROPS: true });
 const template = document.createElement('template'); template.innerHTML = safe;
 template.content.querySelectorAll('a[href]').forEach(link => {
  try { const url = new URL(link.getAttribute('href')!, window.location.href); if (!['http:','https:','mailto:'].includes(url.protocol)) link.removeAttribute('href'); else if (url.origin !== window.location.origin) link.setAttribute('rel', 'noopener noreferrer'); } catch { link.removeAttribute('href'); }
 });
 return template.innerHTML;
}
export function ContentRenderer({ value, format = 'markdown' }: { value: string; format?: 'markdown' | 'html' }) {
 const html = useMemo(() => { try { return safeContent(value, format); } catch { return null; } }, [value, format]);
 return html === null ? <div className="prose">{value}</div> : <div className="prose" dangerouslySetInnerHTML={{ __html: html }} />;
}
