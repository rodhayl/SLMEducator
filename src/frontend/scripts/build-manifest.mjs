import { readFile, readdir, stat, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { frontendSourceDigest } from './source-identity.mjs';

export async function writeBuildManifest(root, sourceDigest) {
 const dist = path.join(root, 'dist');
 const lock = JSON.parse(await readFile(path.join(root, 'package-lock.json'), 'utf8'));
 // These development packages contribute literal code/CSS to the shipped output.
 // Build-only tools do not otherwise enter the runtime notice inventory.
 const shippedDevPackages = new Set(['node_modules/tailwindcss']);
 for (const packagePath of shippedDevPackages) if (!lock.packages[packagePath]) throw new Error(`Missing shipped notice dependency: ${packagePath}`);
 const licenses = [];
 for (const [packagePath, record] of Object.entries(lock.packages)) {
  if (!packagePath || (record.dev && !shippedDevPackages.has(packagePath)) || record.optional) continue;
  const directory = path.join(root, packagePath);
  let pkg; try { pkg = JSON.parse(await readFile(path.join(directory, 'package.json'), 'utf8')); } catch { continue; }
  const notices = [];
  for (const filename of await readdir(directory)) if (/^(license|licence|copying|notice)(\.|$)/i.test(filename)) { const file = path.join(directory, filename); if ((await stat(file)).isFile()) notices.push({ file: filename, text: await readFile(file, 'utf8') }); }
  licenses.push({ name: pkg.name, version: pkg.version, license: pkg.license || record.license || 'SEE NOTICES', shipped_from_dev_dependency: shippedDevPackages.has(packagePath), notices });
 }
 await writeFile(path.join(dist, 'third-party-notices.json'), JSON.stringify({ packages: licenses }, null, 2) + '\n');
 const assets = [];
 async function visit(directory) {
  for (const entry of await readdir(directory, { withFileTypes:true })) {
   const filename = path.join(directory, entry.name);
   if (entry.isSymbolicLink()) throw new Error('Build output must not contain symbolic links');
   if (entry.isDirectory()) await visit(filename);
   else if (entry.isFile() && entry.name !== 'build-manifest.json') { const bytes = await readFile(filename); assets.push({ path:path.relative(dist, filename).split(path.sep).join('/'), size:bytes.length, sha256:createHash('sha256').update(bytes).digest('hex') }); }
  }
 }
 await visit(dist);
 assets.sort((a,b) => a.path.localeCompare(b.path));
 if (!assets.some(asset => asset.path === 'index.html') || !assets.some(asset => asset.path === '.vite/manifest.json')) throw new Error('Vite output incomplete');
 if (await frontendSourceDigest(root) !== sourceDigest) throw new Error('Frontend sources changed during build; rebuild explicitly.');
 await writeFile(path.join(dist, 'build-manifest.json'), JSON.stringify({ schema_version:2, frontend:'slm-educator', source_identity_version:1, source_sha256:sourceDigest, lockfile_sha256:createHash('sha256').update(await readFile(path.join(root, 'package-lock.json'))).digest('hex'), assets }, null, 2) + '\n');
 console.log(`Verified ${assets.length} local assets and ${licenses.length} dependency license records.`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
 throw new Error('Use npm run build; a manifest cannot be refreshed over existing output.');
}
