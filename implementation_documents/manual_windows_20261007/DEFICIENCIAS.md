# Deficiencias observadas — sesión manual del instalador (2026-10-07)

Registradas por el operador (David) durante `MANUAL_TEST2` sobre el instalador
`fe954cab4655` (SHA-256 `c02c79e2…a1531`). El agente no corrigió nada durante la
evaluación; este documento es el registro para el equipo/agente revisor.

## D1. Menú lateral sin secciones — exigencia de rediseño de la GUI completa

El menú de la izquierda mezcla sin jerarquía la administración (Profesores,
Administradores, Estudiantes…), el estudio (Mi Aprendizaje, Tutor IA,
Evaluaciones, Clasificación, Bandeja de Entrada…) y la creación de contenido
(Crear Contenido, Cola de Ayuda). No queda claro qué es administración, qué es
para estudiar y qué es para crear contenido.

**Exigencia del operador: rehacer y reestilar la GUI completa, moderna, con
secciones claras en el menú.** Esta exigencia es de alcance total (no solo el
menú): ver D2.

## D2. Estilos por rehacer

Revisar todos los estilos: la página «Crear cuenta» es extremadamente estrecha
y no tiene sentido; los estilos generales «son feísimos». Todo necesita
rehacerse y reestilarse para hacerlo moderno. (Operador, con captura.)

Nota técnica para el revisor: el tema por defecto es oscuro; el operador
prefiere claro por defecto (observación añadida en `SESSION_LOG.md`).

## D3. BUG — Crear docente falla con error ilegible «[object Object]»

- **Paso:** admin → «Profesores» → «Crear» → formulario «Crear cuenta»
  (Rol «Docente») → rellenar Nombre/Apellidos/Correo/Usuario/Contraseña →
  pulsar «Crear cuenta».
- **Resultado visible:** caja de error roja con el texto literal
  `[object Object]`. La cuenta no se crea.
- **Evidencia de servidor** (log de la instancia instalada,
  `%LOCALAPPDATA%\Programs\SLMEducator\logs\slm_educator.log`):
  `POST /api/auth/register HTTP/1.1" 422` (una sola llamada; sin reintentos).
- **Causa de la UI** (diagnóstico de solo lectura en
  `src/web/static/js/auth.js`, mismo árbol que la build instalada):
  `AuthService.register` hace `throw new Error(err.detail || 'Registration failed')`.
  Cuando FastAPI devuelve 422 con `detail` estructurado (lista de errores de
  validación), `new Error(<objeto>)` stringifica como `[object Object]` y el
  motivo real queda oculto al usuario.
- **Motivo subyacente del 422:** no determinado (el log de acceso no guarda el
  cuerpo). No se reintentó ni se creó la cuenta por API/SQL (fuera de las reglas
  de la sesión).
- **Impacto:** bloquea el tramo B completo (cuentas de personal desde la UI) y,
  por dependencia, C/D/E/F de la sesión manual.

## Reproducción mínima de D3

1. Instalador `fe954cab4655`, instalación nueva, sesión como `admin`.
2. «Profesores» → «Crear».
3. Formulario «Crear cuenta» con Rol «Docente», datos sintéticos válidos
   (p. ej. Docente/Demo, `docente.demo@example.invalid`, `docente_demo`,
   contraseña propia ≥12 caracteres) y «Crear cuenta».
4. Error rojo `[object Object]`; el acceso registra `POST /api/auth/register 422`.
