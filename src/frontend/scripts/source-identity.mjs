import { createHash } from 'node:crypto';
import { lstat, readdir, readFile } from 'node:fs/promises';
import path from 'node:path';

// Keep this inventory and framing identical to frontend_source_digest in Python.
// Tailwind candidates are constrained to src/ by styles/tokens.css.
const files = ['index.html', 'package.json', 'package-lock.json', 'tsconfig.json', 'vite.config.ts'];
const trees = ['src', 'scripts'];
const digest = bytes => createHash('sha256').update(bytes).digest('hex');

export async function frontendSourceDigest(root) {
 const records = [];
 async function visit(relative, optional = false) {
  const filename = path.join(root, relative);
  let info;
  try { info = await lstat(filename); }
  catch (error) { if (optional && error.code === 'ENOENT') return; throw error; }
  if (info.isSymbolicLink()) throw new Error(`Symlinked frontend source input: ${relative}`);
  if (info.isDirectory()) {
   for (const entry of await readdir(filename)) await visit(`${relative}/${entry}`);
  } else if (info.isFile()) {
   const bytes = await readFile(filename);
   records.push({ path: relative, size: bytes.length, sha256: digest(bytes) });
  } else throw new Error(`Frontend source input is not a regular file: ${relative}`);
 }
 if ((await lstat(root)).isSymbolicLink()) throw new Error('Symlinked frontend source root');
 for (const filename of files) {
  if (!(await lstat(path.join(root, filename))).isFile()) throw new Error(`Missing frontend source file: ${filename}`);
  await visit(filename);
 }
 for (const directory of trees) {
  if (!(await lstat(path.join(root, directory))).isDirectory()) throw new Error(`Missing frontend source directory: ${directory}`);
  await visit(directory);
 }
 await visit('public', true);
 records.sort((a, b) => Buffer.compare(Buffer.from(a.path), Buffer.from(b.path)));
 return digest(records.map(record => `${record.path}\0${record.size}\0${record.sha256}\n`).join(''));
}
