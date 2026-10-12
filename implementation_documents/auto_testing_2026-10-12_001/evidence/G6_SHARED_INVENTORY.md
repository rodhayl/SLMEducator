# PLAN-G6 · Inventario de código compartido (deuda diagnosticada, sin refactor)

Fecha: 2026-10-12 · run auto-2026-10-12-001 (continuación 002).
Alcance: solo inventario/diagnóstico técnico. No PASS GUI, no refactor
(conforme a AUTO_TEST.md §13 y a CONTINUITY_GAPS_20261007.md).

## Superficie compartida (`src/frontend/src/`)

| Módulo | Ficheros | Líneas (aprox.) | Rol |
|---|---|---|---|
| `lib/` | api, downloads, drafts, ids, query, storage, time, types (8) | 244 | Transporte, borradores locales, descargas, reloj |
| `app/` | AppShell, AuthProvider, auth-controller, AppearanceProvider, DirtyGuard, feature-routes, route-contracts, router, retire-legacy-worker, legacy-dashboard, AccountMotion, PrivacyContext, UnreadMessagesBadge (13) | ~330 | Shell, sesión, guardia de suciedad, rutas, retiro legacy |
| `components/{ui,content}` | UI kit + render de contenido | — | Controles y ContentRenderer compartidos |

## Hooks compartidos por característica (nº de ficheros que los usan)

| Hook | Usuarios | Observación de deuda |
|---|---|---|
| `useOperation` | 28 | Mutaciones con recibo/confirmación; mismo patrón en 12 áreas |
| `useResource` | 24 | Lecturas con validación; mismo patrón en 12 áreas |
| `useInvalidate` | 23 | Relectura tras mutación |
| `useDirtyGuard` | 18 | Guardia beforeunload; verificado en vivo esta noche (aula, generación) |
| `useDelivery` | 3 (help ×2, messages) | Continuaciones ligadas a cuenta/época; solo en ayuda y mensajes |
| `useCurrentSettings` | 4 (settings) | Lectura de ajustes con época de credenciales |

## Deuda identificada (para trabajo separado, no de esta campaña)

1. **Densidad de `people/routes.tsx`** (395 líneas, lista+detalle+matrícula+notas+cuenta en un fichero) frente al resto de áreas divididas por fichero.
2. **`learning/routes.tsx`** (217 líneas) mezcla vista previa, workspace de sesión y paneles; el resto de áreas separa rutas de páginas.
3. **`GenerationPage.tsx`** concentra cinco modos + esquema + lote + recuperación + legacy en un solo workspace (verificado funcionalmente esta noche sin defecto).
4. `useDelivery` solo existe en 2 áreas; tutor/generación usan continuaciones propias (`controller`/`stop` refs) — consolidación posible pero con semántica distinta (cancelación de proveedor), no mecánica.
5. `retire-legacy-worker.ts` (23 líneas) + `RETIREMENT_WORKER` (backend) duplican la noción de "dos cachés legacy" también fijada en tests — convergencia documental, no de código.

Ningún punto anterior es defecto funcional: todo lo compartido listado está
ejercitado por las suites (vitest 967/967) y por los recorridos GUI de esta
campaña. Se entrega como mapa para una refactorización futura explícitamente
autorizada, fuera de esta campaña de pruebas.
