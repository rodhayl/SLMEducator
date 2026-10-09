# DEFECTS · Campaña auto-2026-10-09-002

Registro único de defectos observados en ESTA ejecución. No renumera ni sobrescribe el
DEFECTS.md histórico `auto-2026-10-08-001` ni sus IDs `SLM-AUTO-001..013`; las
reproducciones de esos defectos en este candidato se enlazan desde aquí con su ID
histórico cuando exista evidencia nueva.

Severidad: S1 pérdida/exposición grave o arranque esencial bloqueado · S2 flujo esencial
roto · S3 función degradada · S4 presentación menor.

---

## SLM-AUTO-014 · Dos pruebas Python no portables a locale ANSI en Windows (read_text sin encoding)

- **Estado**: OPEN
- **Severidad**: S4 (la suite de pruebas falla en Windows con locale cp1252; el producto
  no está afectado: los ficheros fuente/dañados no existen, solo la lectura del test)
- **Prioridad**: Baja (bloquea la puerta «todo verde» en Windows, no la funcionalidad)
- **Fecha/run**: 2026-10-09 · `auto-2026-10-09-002`
- **Candidato**: rama `fix/react-functional-continuation-20261007`, HEAD
  `19909e6038c180ce15f5e987928934d34dfc797e`, árbol `e13ba1248a22294582670eade6e27754af8b94a0`
- **Entorno**: Windows 10/11 (10.0.26200), Python 3.14.7 (`venv` del repo),
  `locale.getpreferredencoding(False) = cp1252`
- **Rol**: n/a (suite técnica)
- **Caso relacionado**: puerta AGENTS.md/CONTRIBUTING (pruebas afectadas); plan
  `tests/test_first_run_setup.py`, `tests/test_operational_documentation.py`
- **Precondiciones**: clon UTF-8 estándar; sin variables `PYTHONUTF8`/`PYTHONIOENCODING`
  (configuración de usuario típica en Windows)

### Hecho observado (literal)

Reproducción 1 — `python -m pytest tests/test_first_run_setup.py -q`:

```
FAILED tests/test_first_run_setup.py::test_native_errors_are_allowlisted_and_password_fields_are_masked
tests\test_first_run_setup.py:127: AssertionError
1 failed, 353 passed, 1 warning in 112.05s
```

La línea 126 hace `source = Path(first_run_setup.__file__).read_text()` SIN
`encoding='utf-8'` y la 127 busca el subtexto `show='' if key == 'username' else '•'`.
Diagnóstico técnico (sonda local, sin modificar nada):

- `src/first_run_setup.py` contiene los bytes UTF-8 del bullet (`e2 80 a2`): VERDADERO
- `locale.getpreferredencoding(False)` → `cp1252`
- subtexto presente decodificando como UTF-8 → VERDADERO; decodificando como cp1252 →
  FALSO (el bullet se corrompe y el assert falla)

Reproducción 2 — `python -m pytest tests/test_operational_documentation.py -q`:

```
FAILED tests/test_operational_documentation.py::test_active_ui_guides_do_not_prescribe_removed_qt_modules
E  UnicodeDecodeError: 'charmap' codec can't decode byte 0x9d in position 10384
tests\test_operational_documentation.py:93: (ROOT / "docs/CONTRIBUTING.md").read_text()
1 failed, 153 passed, 1 warning in 22.12s
```

Misma causa: `read_text()` sin `encoding` decodifica UTF-8 como cp1252 y esta vez lanza
la excepción en lugar de corromper en silencio.

### Esperado / Observado

- Esperado: la suite completa pasa en Windows con locale ANSI (la verificación publicada
  en `returned_defects_repair_20261008/VERIFICATION.json` declara 0 fallos, pero su
  ejecución fue en Linux, donde el codec por defecto es UTF-8).
- Observado: 2 FAILED en Windows con los mismos ficheros intactos.

### Frecuencia y efecto

- Frecuencia: 100% en Windows con locale cp1252 (reproducido 2/2).
- Efecto: ninguna sobre datos ni funcionalidad; sí sobre la puerta de pruebas y sobre
  cualquier claim de «suite verde en Windows».

### Hecho observado vs causa comprobada

- Hecho: los dos tests fallan por decodificación locale; verificado con sondas que
  decodifican los mismos bytes con ambos codecs.
- Causa comprobada: ausencia de `encoding='utf-8'` en `Path.read_text()` dentro de los
  tests (código del test, no del producto).
- Hipótesis de por qué no apareció antes: la verificación del candidato se ejecutó en
  Linux; ningún gate previo corrió estos ficheros en Windows con ANSI.

### Alternativa temporal segura

- Ejecutar con `set PYTHONUTF8=1` (o `PYTHONIOENCODING=utf-8`) en Windows mientras el
  arreglo de test no exista. No aplica a productos ni a instalaciones finales.

### Evidencia

- Lotes locales `C:\builds\slm-pytest-batchA.log` y `C:\builds\slm-pytest-batchB.log`
  (fuera de Git; se publicará solo un extracto saneado con hashes en la evidencia de la
  campaña).
- Sonda `C:\builds\probe_encoding.py` con su salida reproduciendo ambos codecs.
- Qué NO se verificó: el mismo test en Linux (no disponible en este entorno).

---

## SLM-AUTO-015 · `scripts/seed_pilot.py` corrompe contenido no-ASCII al sembrar (read_text sin encoding)

- **Estado**: OPEN
- **Severidad**: S3 (corrompe datos reales sembrados: los acentos se guardan mojibake en la
  base; no hay pérdida ni exposición, pero el contenido persistido es incorrecto)
- **Prioridad**: Media (afecta a la herramienta de pilotaje/onboarding `scripts/` que sí se
  distribuye; el runtime de peticiones del núcleo no está afectado)
- **Fecha/run**: 2026-10-09 · `auto-2026-10-09-002`
- **Candidato**: rama `fix/react-functional-continuation-20261007`, HEAD
  `19909e6038c180ce15f5e987928934d34dfc797e`, árbol `e13ba1248a22294582670eade6e27754af8b94a0`
- **Entorno**: Windows 10/11 (10.0.26200), Python 3.13.15 (venv aislado de build),
  `locale.getpreferredencoding(False) = cp1252`, sin `PYTHONUTF8`
- **Rol**: teacher_a (GUI sintética sobre `local_provider_server.py`)
- **Caso relacionado**: mismo clase que SLM-AUTO-014 pero en código de producto/`scripts/`,
  no en tests. Ficheros: `scripts/seed_pilot.py` (línea 73) y `scripts/evaluate_pilot.py`
  (línea 15).
- **Precondiciones**: instalación sintética nueva sembrada con `seed_pilot` sobre el fixture
  UTF-8 `tests/fixtures/pilot/fractions_course.json` en un Windows con locale ANSI.

### Hecho observado (literal, saneado)

En la GUI del candidato (`/cursos/1`, materiales del curso «Fractions…»), el material 3 se
renderiza con mojibake mientras los materiales 1 y 2 (sin acentos) se ven correctos:

```
1. Equal parts / Partes iguales                         (correcto)
2. Compare common denominators / Comparar denominadores iguales   (correcto)
3. Independent retrieval / RecuperaciÃ³n independiente   (MOJIBAKE: Ã³ en lugar de ó)
```

Inspección de la base sintética propia (solo lectura, `synthetic.db` de esta campaña):

```
contents[3].title raw bytes = b'3. Independent retrieval / Recuperaci\xc3\x83\xc2\xb3n independiente'
```

El `ó` correcto en UTF-8 es `\xc3\xb3`; la base guarda `\xc3\x83\xc2\xb3` (doble codificación).
El fixture de origen guarda los bytes CORRECTOS (`\xc3\xb3`) y es UTF-8 válido.

### Causa comprobada (reproducida byte a byte)

`scripts/seed_pilot.py:73`:

```python
fixture = json.loads(
    (ROOT / "tests/fixtures/pilot/fractions_course.json").read_text()   # sin encoding
)
```

`Path.read_text()` sin `encoding=` usa el codec de locale (cp1252 aquí). Los bytes UTF-8
`\xc3\xb3` del fixture se decodifican como cp1252 → en memoria queda la cadena `RecuperaciÃ³n`;
SQLAlchemy la re-codifica a UTF-8 al guardar → `\xc3\x83\xc2\xb3` en la base. Reproducción
local (sonda `C:\builds\repro_seed_mojibake.py`):

```
preferred encoding: cp1252
correct UTF-8 bytes: b'Independent retrieval / Recuperaci\xc3\xb3n independient'
decoded-as-cp1252 title (in memory): '3. Independent retrieval / Recuperación independiente'
re-encoded to utf-8 bytes: b'...Recuperaci\xc3\x83\xc2\xb3n independiente'
MATCHES DB mojibake: True
```

`scripts/evaluate_pilot.py:15` repite el patrón (`read_text()` sin encoding sobre
`docs/pilot/evaluation_cases.json`, que también contiene bytes no-ASCII). Allí el daño es de
lectura/validación, no persistido.

### Esperado / Observado

- Esperado: el contenido sembrado conserva los acentos exactamente como en el fixture UTF-8.
- Observado: cualquier carácter no-ASCII del fixture se guarda como mojibake de doble
  codificación; la GUI lo muestra corrupto.

### Frecuencia y efecto

- Frecuencia: 100% en Windows con locale cp1252 al sembrar el piloto con ese fixture.
- Efecto: contenido persistido incorrecto en instalaciones sembradas con esta herramienta;
  NO afecta al camino de peticiones del runtime ni a la generación IA en caliente.

### Hecho observado vs causa comprobada

- Hecho: mojibake visible en GUI y bytes doble-codificados en la base sintética propia.
- Causa comprobada: `read_text()` sin `encoding='utf-8'` en `scripts/seed_pilot.py` (y patrón
  idéntico en `scripts/evaluate_pilot.py`), con locale cp1252.
- Clasificado como defecto de PRODUCTO/HERRAMIENTA (no de test), a diferencia de SLM-AUTO-014.

### Alternativa temporal segura

- Ejecutar el sembrado con `PYTHONUTF8=1` mientras no exista el arreglo. El arreglo correcto
  es `read_text(encoding="utf-8")` en ambos ficheros de `scripts/`.

### Evidencia

- Captura GUI `evidence/shot-course1-mojibake.png` (material 3 con `Ã³`).
- Salida de la sonda de inspección de la base sintética (bytes crudos de `contents`).
- Sonda `C:\builds\repro_seed_mojibake.py` (fuera de Git) reproduciendo la transformación.
- Fixture `tests/fixtures/pilot/fractions_course.json` (UTF-8 válido, bytes de origen correctos).
- Qué NO se verificó: el mismo sembrado en Linux (no disponible); si el instalador empaquetado
  arrastra `seed_pilot` al runtime de primera ejecución (requiere ciclo de instalación nativo).

