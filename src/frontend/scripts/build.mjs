import { rm } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import { frontendSourceDigest } from './source-identity.mjs';
import { writeBuildManifest } from './build-manifest.mjs';

const root = fileURLToPath(new URL('..', import.meta.url));
const require = createRequire(import.meta.url);
const dist = path.join(root, 'dist');
const environment = Object.fromEntries(Object.entries(process.env).filter(([name]) => !name.startsWith('VITE_')));
environment.NODE_ENV = 'production';
// A failed canonical build must not leave an older artifact marked complete.
await rm(path.join(dist, 'build-manifest.json'), { force: true });
const sourceDigest = await frontendSourceDigest(root);
for (const tool of ['typescript/bin/tsc', 'vite/bin/vite.js']) {
 const executable = tool.startsWith('vite/')
  ? path.join(path.dirname(require.resolve('vite/package.json')), 'bin/vite.js')
  : require.resolve(tool);
 const args = tool.startsWith('vite/') ? ['build', '--mode', 'production'] : ['--noEmit'];
 const result = spawnSync(process.execPath, [executable, ...args], {
  cwd: root, stdio: 'inherit', env: environment,
 });
 if (result.error) throw result.error;
 if (result.status !== 0) throw new Error(`Frontend build tool failed: ${tool}`);
}
await writeBuildManifest(root, sourceDigest);
