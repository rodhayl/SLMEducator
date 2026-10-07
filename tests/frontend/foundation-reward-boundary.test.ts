import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const root = existsSync(resolve('src/frontend/src')) ? resolve('src/frontend/src') : resolve('src');
function sources(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? sources(path) : /\.[cm]?[jt]sx?$/.test(entry.name) ? [path] : [];
  });
}

describe('server-owned rewards and assessed mastery', () => {
  it('never introduces direct client XP awards or mastery-review writes', () => {
    const files = sources(root);
    expect(files.length).toBeGreaterThan(0);
    for (const file of files) {
      const source = readFileSync(file, 'utf8');
      expect(source, file).not.toContain('/api/gamification/award-xp');
      expect(source, file).not.toContain('/api/mastery/review');
    }
  });
});
