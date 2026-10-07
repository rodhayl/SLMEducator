# SLMEducator React frontend

This frontend is a static React/TypeScript application. FastAPI remains the API and runtime host. Node is required only for explicit development/build work; it is not a packaged runtime dependency. The final visual, real-browser and native Windows acceptance gates remain separate from synthetic/build verification.

## Explicit development commands

Use Node 22.22 or later (the initial spike used Node 24.19.0) and the committed npm lockfile:

```sh
cd src/frontend
npm ci --ignore-scripts
npm run check
```

`check` runs strict TypeScript, ESLint, all `tests/frontend/` tests and the production build. Repository-level tests resolve the locked dependencies installed in this frontend directory; no repository-root dependency installation or filesystem link is needed. The esbuild platform binary is supplied by its locked optional platform package; no arbitrary post-install scripts are required. Tests run serially with synthetic transport fixtures. Actual API verification is in `tests/integration/test_frontend_vertical_contract.py`, using the repository's offline test setup and disposable SQLite database.

`npm run build` is the canonical build command. It removes the previous completion manifest, fingerprints inputs before TypeScript/Vite run, and only writes a new completion manifest if the same inputs remain after compilation. Running the manifest module by itself is rejected. It writes `dist/`, Vite's `.vite/manifest.json`, `build-manifest.json` with SHA-256/size for every packaged file, and `third-party-notices.json` assembled from installed locked runtime packages plus the declared shipped-CSS dependency Tailwind. The notices file is an inventory, not an independent license audit. The schema-2 manifest also carries a source-input digest (identity version 1). Inputs are `index.html`, `package.json`, `package-lock.json`, `tsconfig.json`, `vite.config.ts`, every file under `src/` and `scripts/`, and optional `public/`. Paths, byte sizes and SHA-256 values use deterministic UTF-8 byte ordering; no source contents or environment values are embedded. Tailwind scans only `src/`. Vite does not load `.env` files, and the canonical build excludes `VITE_*` environment injection; frontend configuration stays with relative `/api` and backend-owned settings. Input links fail closed; `node_modules`, `dist`, docs and tests are not production inputs. If future configuration imports inputs outside this inventory, extend both source-identity implementations and their parity test first.

Packaging checks the digest before and after staging, so an old dist cannot silently accompany newer TypeScript/CSS/configuration. Packaged runtime checks only the embedded identity and artifact bytes, without source files, npm or Node. This detects accidental staleness and torn builds; it is not a signature, tamper-proof attestation, or guarantee of reproducibility across tool/platform/environment differences. Generated files and dependencies are ignored; do not commit them.

The runtime uses relative `/api/` requests, so a packaged application's selected port stays authoritative. No remote assets, fonts, CDN, offline request replay, persistent private Query cache or Node server is required. The server exposes a narrow retirement-only service worker for recognized old caches; the new app does not register one.

## Contribution boundaries

Read `CONTRACTS.md`. Domain implementations are registered by their lightweight paths in `src/app/feature-routes.ts` and loaded lazily. TanStack Query owns remote reads. Auth owns verified identity and credentials; forms and narrowly scoped reducers own local edits. Shared primitives implement portal privacy as well as document-shell privacy.

Never create a feature-local raw fetch client, token store, HTML injection site or fallback to legacy JavaScript. Render API errors through the safe shared adapter. Validate resource IDs and mutation receipts at runtime. For credentials, pass `void` to mutation hooks and read transient form values inside the operation so secrets do not enter Query mutation variables.

Drafts are explicit, owner/resource/attempt-scoped, seven-day, origin-local and unencrypted. Only established formats are supported. A failed write is not a save. Session expiry keeps private in-memory work hidden; same-account access is revalidated before showing it, and mutations are never replayed automatically. Different identity or role drops the prior private buffer and caches.

DOM tests do not certify painted layout, real zoom, a screen reader, native Windows packaging or real-provider model behavior. Those remain separate acceptance gates.
