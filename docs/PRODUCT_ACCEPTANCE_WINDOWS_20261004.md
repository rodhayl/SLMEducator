# Aceptación Windows, 2026-10-04

## Identidad y límites

Rama `feat/trustworthy-learning-loop-20261004`. La referencia recibida
`ebc43ff6a17c9b2882a494806ed24b5055f14711` tiene como padre inmediato
`3f47e41c8c04043227ba70589e95dcb7f5e70dca`; este último es el código
probado en el gate previo. El checkout inicial estaba limpio en `main` y se
cambió a la rama solicitada. Se leyeron `AGENTS.md`, `README.md`,
`docs/CONTRIBUTING.md` y `implementation_documents/PRODUCT_ACCEPTANCE_20261004.md`.

Esta ejecución usó exclusivamente bases nuevas y sintéticas. Ninguna base o
configuración privada del usuario se abrió, copió ni publicó. Las bases, paquetes
y logs de ejecución permanecen ignorados por Git. Las cuentas HTTP creadas
fueron dos docentes y dos estudiantes adultos sintéticos.

## Entorno y comandos

- Windows 11 10.0.26200; Python 3.14.7 para instalación y arranque de fuente;
  Python 3.13.15 para el paquete funcional y el gate final; PyInstaller 6.16.0;
  Node 24.21.0 y npm 11.19.0.
- `cmd /c install_dependencies.bat --dev` y `python -m pip check`: PASS en
  entorno virtual nuevo. El primer intento sin elevación falló en `ensurepip`
  por denegación de escritura del sandbox; el mismo instalador terminó bien
  con permisos de escritura apropiados.
- `cmd /c start.bat` con `SLM_DB_PATH` apuntando a `data/acceptance_synthetic.db`:
  PASS, creación de admin sintético y HTTP 200 en `/login.html`.
- Alta y login por HTTP real: admin, dos docentes y dos estudiantes. La lista
  `/api/auth/users?role=student` devolvió sólo `qa_learner_a` al docente A y
  sólo `qa_learner_b` al B: PASS para esta comprobación de matrícula.
- `python -m pytest` de privacidad, recorridos, tres lecciones, cursos,
  fuentes, portabilidad y recuperación: **50 passed**. JUnit inicial:
  `acceptance_focused_junit.xml`.
- `npm ci --ignore-scripts --prefix tests/ui` y `npm test --prefix tests/ui`:
  **154 passed**, cero fallos. Ver `acceptance_dom_test.log`.

## Paquete y defecto reproducido

`build_package.bat --prod` con Python 3.14.7 produjo un EXE, pero PyInstaller
6.16.0 advirtió que Tcl/Tk vivía bajo `//zipfs:` y no lo incorporó. Al iniciar
ese EXE desde `tests`, el proceso permaneció abierto sin ventana ni puerto HTTP
y sin log de arranque. La ausencia de `_tcl_data`/`_tk_data` quedó comprobada.

Se añadió una comprobación previa en `scripts/build_package.py`: si Tcl/Tk
reside en `zipfs`, la construcción termina con código 1 y un mensaje que indica
usar una instalación de Python con directorios Tcl/Tk. El comando repetido en
3.14 rechazó antes de crear el directorio de salida. Se añadió una regresión
específica que pasa.

Con Python 3.13.15 y el mismo script, el paquete se construyó correctamente.
Desde `tests` arrancó en `http://127.0.0.1:8000`, sirvió HTML y assets, aceptó
el login admin sintético, se detuvo (sus procesos propios) y tras reiniciar
volvió a aceptar el mismo login. Los logs locales del paquete muestran
`Server ready` y respuestas HTTP 200. La parada se hizo a nivel de proceso;
el cierre mediante el botón Tk no fue ejercitado.

La prueba de empaquetado que comparaba byte a byte el SQLite `-shm` vivo falló
en Windows por bloqueo de lectura del sistema operativo, antes de ejecutar la
función probada. Se ajustó para comparar bytes donde se permite y tamaño/fecha
donde SQLite bloquea la lectura. Las pruebas de paquete y bootstrap pasaron:
**58 passed**. La nueva prueba de rechazo `zipfs` pasó por separado.

## Matriz de escenarios

| Escenario | Estado | Evidencia o límite |
| --- | --- | --- |
| Instalación y arranque de fuente Windows | PASS | Scripts, Python 3.14, HTTP 200 |
| Paquete Python 3.13 desde otro directorio, login y reinicio | PASS | EXE nativo, HTTP 200, login tras reinicio |
| Paquete Python 3.14 con Tcl/Tk zipfs | FAIL reparado | Antes emitía paquete inutilizable; ahora rechazo temprano explícito |
| Cierre mediante GUI Tk | NO EJERCITADO | Sólo parada de procesos sintéticos |
| Matrícula cruzada por API HTTP | PASS parcial | Dos docentes reciben únicamente su propio estudiante en lista |
| Contenido, notas, soluciones y exportaciones ajenas por API HTTP | NO EJERCITADO | Las pruebas sintéticas enfocadas pasan; falta recorrido HTTP directo completo |
| Inactivación y recuperación administrativa en navegador | NO EJERCITADO | Pruebas sintéticas incluidas en las 50 enfocadas |
| Creación, revisión, publicación, asignación, fuentes y versiones | PASS automatizado | Pruebas sintéticas enfocadas; sin recorrido GUI completo |
| Pausa, reanudación, reinicio, evaluación y cero | PASS automatizado | Pruebas de recorrido y 154 DOM; sin recorrido humano en navegador |
| GUI Chrome DevTools `--isolated` | NO EJERCITADO | MCP rechazó conexión: perfil Chrome DevTools ya ocupado |
| Chrome aislado con Playwright, login español | PASS parcial | Foco por Tab en `INPUT`, sin desbordamiento a 1280 px ni 390 px; capturas adjuntas |
| Inglés, temas, errores, reintentos y zoom nativo 100/200 % | NO EJERCITADO | Requiere inspección DevTools aislada completa |
| Tutor con modelo real gratuito | NO EJERCITADO | Ollama no responde en 11434; no hay comando instalado; autorización solicitada para instalarlo |
| Exportación/importación en segunda instalación sintética | NO EJERCITADO | Contratos automatizados incluidos; no recorrido integral entre instalaciones |
| Copia de seguridad y restauración operativa | NO EJERCITADO | Contratos automatizados incluidos; no restauración manual del paquete |

Capturas complementarias: `acceptance_login_es_100.png` y
`acceptance_login_es_200_mobile.png`. El segundo ensayo pulsó el atajo de zoom,
pero no pudo medir un 200 % nativo de Chrome; no se presenta como tal.

## Evidencia final

La consolidación offline de Python, cobertura y JUnit se registra en
`acceptance_full_test.log`, `acceptance_full_junit.xml` y
`acceptance_coverage.json`. Sus cifras finales y el SHA del checkpoint se
añadirán tras terminar el proceso. No se ejecutaron inferencias pagadas, ni
merge, ni despliegue.
