import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { fileURLToPath, URL } from 'node:url';
export default defineConfig({
 plugins: [react(), tailwindcss()],
 resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
 base: '/',
 // The static UI uses backend settings and relative /api; never load private .env files.
 envDir: false,
 build: { manifest: true, sourcemap: false, outDir: 'dist', emptyOutDir: true, rollupOptions: { output: { manualChunks: (id: string) => /\/node_modules\/(react|react-dom|react-router|scheduler)\//.test(id) ? 'framework' : undefined } } },
 server: { fs: { allow: [fileURLToPath(new URL('../..', import.meta.url))] } },
 test: { root: fileURLToPath(new URL('../..', import.meta.url)), environment: 'jsdom', globals: true, include: ['tests/frontend/**/*.{test,spec}.{ts,tsx}'], setupFiles: [fileURLToPath(new URL('../../tests/frontend/setup.ts', import.meta.url))], pool: 'forks', maxWorkers: 1, fileParallelism: false },
});
