import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ContentRenderer } from '@/components/content/ContentRenderer';

import { readFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
const cssPath = [resolve('src/styles/base.css'), resolve('src/frontend/src/styles/base.css')].find(existsSync);
if (!cssPath) throw new Error('Repository stylesheet was not found');
const css = readFileSync(cssPath, 'utf8');
const recorded = '- Busca un denominador común para ambas fracciones antes de comparar sus numeradores.\n- Si los denominadores son iguales, la fracción con el numerador más grande es la mayor.';

describe('content list presentation', () => {
  it('restores unordered and ordered markers only within prose', () => {
    expect(css).toMatch(/\.prose ul\s*\{[^}]*list-style-type:\s*disc\s*;/);
    expect(css).toMatch(/\.prose ol\s*\{[^}]*list-style-type:\s*decimal\s*;/);
    expect(css).toMatch(/\.prose ul,\s*\.prose ol\s*\{[^}]*list-style-position:\s*outside\s*;/);
    expect(css).toMatch(/\.list\s*\{[^}]*list-style:\s*none\s*;/);
  });

  it('keeps the recorded response as two semantic items without extra prose', () => {
    const { container } = render(<ContentRenderer value={recorded}/>);
    expect(container.querySelectorAll('.prose > ul > li')).toHaveLength(2);
    expect(container.querySelectorAll('.prose > p')).toHaveLength(0);
    expect([...container.querySelectorAll('li')].map(item => item.textContent)).toEqual(recorded.split('\n').map(line => line.slice(2)));
  });

  it('preserves ordered and mixed nested list semantics', () => {
    const { container } = render(<ContentRenderer value={'1. Primero\n2. Segundo\n   - Detalle'}/>);
    expect(container.querySelectorAll('.prose > ol > li')).toHaveLength(2);
    expect(container.querySelectorAll('ol li ul li')).toHaveLength(1);
  });

  it('leaves an ordinary paragraph and sanitization unchanged', () => {
    const { container } = render(<ContentRenderer value={'Una frase sin lista.\n\n<script>alert(1)</script>'}/>);
    expect(container.querySelector('.prose > p')).toHaveTextContent('Una frase sin lista.');
    expect(container.querySelectorAll('ul, ol, script')).toHaveLength(0);
  });

  it.each(['light', 'dark'])('applies scoped marker styles in %s DOM theme', theme => {
    const previous = document.documentElement.dataset.theme;
    const style = document.createElement('style');
    style.textContent = css;
    document.head.append(style);
    document.documentElement.dataset.theme = theme;
    try {
      const { container } = render(<><ContentRenderer value={recorded}/><ContentRenderer value={'1. Primero\n2. Segundo'}/><ul className="list"><li>Navigation</li></ul></>);
      expect(getComputedStyle(container.querySelector('.prose ul')!).listStyleType).toBe('disc');
      expect(getComputedStyle(container.querySelector('.prose ol')!).listStyleType).toBe('decimal');
      expect(getComputedStyle(container.querySelector('.list')!).listStyle).toBe('none');
    } finally {
      style.remove();
      if (previous === undefined) delete document.documentElement.dataset.theme;
      else document.documentElement.dataset.theme = previous;
    }
  });
});

