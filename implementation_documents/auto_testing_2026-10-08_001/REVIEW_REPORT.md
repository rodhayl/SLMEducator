# REVIEW REPORT · SLMEducator · campaña auto-2026-10-08-001

Informe de hechos para el agente que revisará y corregirá. Solo hechos objetivos observados en esta
campaña. Sin instrucciones de corrección.

- Campaña: `AUTO_TEST.md`, run `auto-2026-10-08-001`
- Directorio de evidencia: `implementation_documents/auto_testing_2026-10-08_001/`
- Fecha de ejecución: 2026-10-08
- Estado de la campaña: terminada en este entorno (`NOT_RUN = 0` de 117 filas)

## 1. Candidato probado

- Rama: `fix/react-functional-continuation-20261007`
- HEAD: `0f3ff15292f84a7d6877f9f2d6e47a3f646355f4` · árbol `4faf9638a5c558991a60a91b489cda6943a52e4f`
- Base de producto: `642966a93e7e9c9f9c5e93cce0bc842f538846fb` · árbol `e0a3966bddc8bbd4cfc2ab4041668c3162ce86f7`
- Diferencia con la base: solo 4 ficheros documentales (`AUTO_TEST.md`, `MANUAL_TEST1.md`,
  `MANUAL_TEST2.md`, `MANUAL_TEST_HANDOFF.md`)
- Tipo: checkout ejecutado como runtime web local en `http://127.0.0.1:8000` (`src/starter_headless.py`).
  No es el Setup instalado ni un portable.
- Frontend: `src/frontend` compilado durante la campaña (`npm ci --ignore-scripts` + `npm run build`).
- Base de datos: sintética y desechable, creada de cero. Sin datos reales.
- Evidencia: `GUI_CDP` (DevTools/CDP sobre la app real; sin control nativo de pantalla).

## 2. Cobertura (117 filas, denominador explícito)

| Estado | Filas |
|---|---|
| PASS | 45 |
| PARTIAL | 41 |
| FAIL | 4 |
| BLOCKED | 26 |
| NOT_APPLICABLE | 1 |
| NOT_RUN | 0 |

Detalle campo a campo en `COVERAGE.csv`.

## 3. Defectos abiertos (13, detalle en `DEFECTS.md`)

| ID | Sev | Hecho observado |
|---|---|---|
| SLM-AUTO-001 | S3 | El buscador de «Personas» pierde caracteres con escritura rápida (`Demo`→`Deo`, `q=eo`, 0 resultados); con entrada lenta funciona |
| SLM-AUTO-002 | S4 | Biblioteca sin materiales muestra el texto y el botón de «sin resultados por filtro»; «Quitar filtros» no cambia nada |
| SLM-AUTO-003 | S3 | Claves de opción duplicadas: el guardado se rechaza solo con el resumen genérico «Revisa los campos del formulario y reinténtalo.», sin campo señalado |
| SLM-AUTO-004 | **S2** | `/tutor` devuelve 404 y la página renderiza `{"detail":"Not Found"}`. El menú enlaza esa ruta. `src/frontend/src/app/route-contracts.ts` la declara válida (`{ path: '/tutor', label: 'help', roles: all }`); `SPA_PATH` en `src/frontend_delivery.py` no la incluye |
| SLM-AUTO-005 | **S2** | `POST /api/generate/lesson` devuelve 500 en 2 de 2 intentos, inmediatamente después de `POST http://localhost:1234/v1/chat/completions → HTTP 200 OK` (4929 bytes, cuerpo leído completo). Sin traza ni mensaje en `api.log` ni en `logs/slm_educator.log`. Extracto saneado en `evidence/ai_generation_failure.log` |
| SLM-AUTO-006 | S4 | Dos cursos con el mismo título son indistinguibles en la lista y en el selector (sin ID ni estado) |
| SLM-AUTO-007 | S4 | La lección creada desde «Crear material» se muestra al alumno con seis encabezados de sección vacíos (`Resumen`, `Ejemplo resuelto`, `Intento independiente`, `Comentarios`, `Repaso posterior`, `Antes de empezar`) |
| SLM-AUTO-008 | S3 | La rúbrica definida en la evaluación (3 criterios) no aparece en la pantalla de corrección, que solo ofrece puntuación y comentario |
| SLM-AUTO-009 | S4 | Los campos «ID del curso» e «ID del material» del editor de evaluación desaparecen al reabrir. El vínculo creado **sí funciona** (una evaluación con `ID del curso = 2` aparece en la lista de la alumna; sin él, no) |
| SLM-AUTO-010 | S4 | Dos mensajes generados por el servidor se muestran en inglés bajo «Comentarios» sin declaración: `Time limit exceeded. Answers preserved for teacher review.` y `Attempt explicitly closed without submission or grade. The reserved attempt remains consumed.` Origen en código: `src/api/routes/assessment.py`, líneas 1390 y 1393. La pantalla «Mi progreso → Actividad reciente» sí declara que sus descripciones vienen del servidor en inglés |
| SLM-AUTO-011 | S4 | Tras traspasar la matrícula de S1 de T1 a T2, T1 ya no puede abrir la ficha de S1 (`No tienes acceso o el recurso ya no está disponible.`). T1 conserva la autoría (sigue viendo los envíos en «Correcciones»). Pérdida de acceso comprobada; pérdida de notas privadas no observada (no existían notas previas) |
| SLM-AUTO-012 | S3 | Los tres rechazos de archivo en «Fuentes del curso» (vacío 0 B, `.bin`, 11 MB) devuelven solo el resumen genérico, idénticos. Lo guardado no se reemplaza |
| SLM-AUTO-013 | S4 | La lección creada en línea desde el editor del curso muestra el encabezado `Lesson` en inglés dentro de la interfaz en español |

Regresión histórica verificada como corregida: `H-D3` (alta con correo inválido; antes 422 ilegible,
ahora error por campo legible).

## 4. Datos sintéticos existentes (base desechable de la campaña)

- Cuentas: `admin` (ID 1) · `docente_auto08` (ID 2, T1) · `alba_auto08` (ID 3, S1, matriculada con T2) ·
  `bruno_auto08` (ID 4, S2) · `contraste_auto08` (ID 5, T2) · `temporal_auto08` (ID 6, reactivada)
- Claves sintéticas desechables: `admin` = `AutoTest2026Disposable`; resto = `Fracciones#2026Aa`,
  **excepto T1 rotada a `NuevaSintetica#2026Bb`** durante AUTO-AUTH-02
- Materiales 1–5, cursos 1 (borrador duplicado accidental de la campaña), 2 (publicado V1, asignado a
  S1), 3 (revisión en borrador), evaluaciones 1 (publicada, envío 1 con 9/10) y 3 (publicada, 1 min,
  envíos 2 con 10/10 y 3 cerrado sin envío), solicitud de ayuda 1 (resuelta), 2 mensajes sintéticos
- Proveedor configurado en la cuenta T1: `lm_studio` · `http://localhost:1234` ·
  `slm-production-evaluation` (conexión OK 16 951 ms, catálogo de 4 modelos)

## 5. Límites de esta campaña (hechos, no instrucciones)

- Sin control nativo de pantalla: BOOT-01..05, LIFE-01, VIS-04, VIS-06, VIS-07 sin ejecutar.
- Sin Setup vigente construido ni instalado; el histórico `fe954cab4655` no se abrió.
- Sin lector de pantalla, sin zoom nativo medido, sin fixtures de escala (G7 abierto), sin migración SW.
- Descargas e importaciones válidas sin verificar contenido (ficheros fuera del directorio autorizado).
- `env.properties` (ignorado por Git) apunta a `lm_studio`; `env.properties.example` (versionado)
  sigue apuntando a `ollama`/`gpt-oss`.
- Nada de esta campaña modifica producto, tests ni configuración versionada salvo `env.properties`
  (ignorado) y los ficheros de `temp/` (ignorados).
