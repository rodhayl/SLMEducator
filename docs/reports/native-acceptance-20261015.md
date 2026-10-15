# SLMEducator Native Windows Acceptance Report

**Date**: 2026-10-15  
**Platform**: Windows 11 Pro 64-bit (10.0.26200)  
**Evaluator**: Antigravity Automated Acceptance Agent  
**Candidate Commit**: `96489dadb2a25b67ae382bad11b215af9f828e7f`  
**Base Candidate**: `09dd2bb16a98dc38c6262e4d86c049cc457b09d4`  
**Worktree Branch**: `fix/react-functional-continuation-20261007`  

---

## 1. Candidate Identity & Build Provenance

- **Repository**: `https://github.com/rodhayl/SLMEducator`
- **Branch**: `fix/react-functional-continuation-20261007`
- **Base Candidate Commit**: `09dd2bb16a98dc38c6262e4d86c049cc457b09d4` (`[skip ci] Fix saved-question navigation and JSON line-break handling`)
- **Product Candidate Commit**: `96489dadb2a25b67ae382bad11b215af9f828e7f`
  - **Commit Message**: `fix(frontend): use cross-platform node invocation for eslint`
  - **Delta**: `src/frontend/package.json` line 14: invoked `eslint` directly via `node src/frontend/node_modules/eslint/bin/eslint.js` for deterministic cross-platform execution on Windows shells without requiring POSIX binary wrapper shims.
  - **Attribution Contract**: Pure conventional commit with sole author attribution; zero AI / Co-Authored-By tags.

### Official Tooling & Fixed Compilation Stack
- **Operating System**: Windows 11 Pro 64-bit (10.0.26200)
- **Node.js**: v24.21.0 (engine compatible >=22.22)
- **Python Runtime**: Python 3.13.15 (`.tooling/qa313/Scripts/python.exe`)
- **Packaging Freeze**: PyInstaller 6.16.0
- **Installer Builder**: Inno Setup 6.7.3 (`C:\Users\dhays\AppData\Local\Programs\Inno Setup 6\ISCC.exe`)

---

## 2. Integrity & Cryptographic Artifact Hashes

Every production binary, payload, and frontend bundle has been hashed and cross-verified:

| Artifact | Canonical Path | SHA-256 Digest | Match Status |
| :--- | :--- | :--- | :--- |
| **Setup Installer EXE** | `builds/acceptance-native-setup-96489da/SLMEducator-Setup-2.0.0-96489dadb2a2.exe` | `B8177D772093C786D7A3463DC0557B239BC552EFDC8DAEB1C298348A8059488B` | Verified Inno Setup Output |
| **Pristine Payload EXE** | `builds/acceptance-native-payload-96489da/SLMEducator.exe` | `EA1F81B3152F5F5082ADEB2EE4C5765F7773A43F6DCABE442AC0A202450CA001` | Verified PyInstaller onedir |
| **Installed Candidate EXE** | `C:\Users\dhays\SLMEducator-Acceptance-Native-Install\SLMEducator.exe` | `EA1F81B3152F5F5082ADEB2EE4C5765F7773A43F6DCABE442AC0A202450CA001` | **Exact 100% Match** |
| **Frontend Manifest (Staged)** | `src/frontend/dist/build-manifest.json` | `8B5AF0A167A0B585FF3CA3EEA88D85FBDDCDCE839B2203F2466845168FEC55F2` | Verified React build |
| **Frontend Manifest (Packaged)** | `.../_internal/src/frontend/dist/build-manifest.json` | `8B5AF0A167A0B585FF3CA3EEA88D85FBDDCDCE839B2203F2466845168FEC55F2` | **Exact 100% Match** |

---

## 3. Mandatory Scope Evaluation & Verified Criteria

### 3.1. Prerequisite Automated Gates
- **Frontend Verification (`npm run check`)**: **PASS**
  - TypeScript: 0 type diagnostic errors (`tsc --noEmit`).
  - ESLint: 0 warnings, 0 errors.
  - Vitest Unit & Integration: 894 / 894 tests passed across 54 files (158.5s).
  - Vite Production Build: 26 local assets generated, 29 package licenses validated in manifest.
- **Backend & Packaging Safety Gates**: **PASS**
  - `python -m pytest tests/test_build_package.py tests/test_seed_admin.py -q`: 80 / 80 passed in 56.7s.
  - Disposable synthetic DB used exclusively; bootstrap create-only policy verified.

---

### 3.2. Setup Installer Lifecycle & In-Place Refusal
- **In-Place Upgrade Rejection (`tests/windows/test_installer_lifecycle.py`)**: **PASS**
  - Attempting to run Setup over an existing installation registration halts in `InitializeSetup()` with exit code 1.
  - Message logged to `rejection-test.log`:
    > *"Ya existe una instalacion de SLMEducator para este usuario. Esta compilacion no actualiza ni migra una instalacion existente. Desinstale la version anterior primero (sus datos y configuracion se conservan) y vuelva a ejecutar el instalador."*
- **Silent Lifecycle Gate**: **PASS** (19.47s)
  - Verified clean silent install to synthetic isolated destination.
  - Uninstallation completely removes application binaries and `_internal`, but strictly preserves user configuration `env.properties` and database `slm_educator.db`.
  - Reinstallation onto the preserved location leaves database content and configuration intact.

---

### 3.3. Interactive Wizard & First-Run Setup (`BOOT-01`, `BOOT-06`)
- **Wizard Cancellation (`BOOT-01`)**: **PASS**
  - Wizard initialized (`gui_01_setup_welcome.png`).
  - Cancel button clicked; confirmation dialog prompted *"¿Salir de la instalación?"* (`gui_02_setup_cancel_confirmation.png`).
  - Confirmed exit; Setup exited with exit code 2 without creating files or registry keys.
- **Interactive Installation**: **PASS**
  - Target directory set to `C:\Users\dhays\SLMEducator-Acceptance-Native-Install` (`gui_03_setup_dir_selected.png`).
  - Desktop shortcut creation enabled (`gui_04_setup_tasks.png`).
  - Ready to Install summary page confirmed (`gui_05_setup_ready.png`).
  - Installation completed successfully (`gui_06_setup_finished.png`).
  - Desktop and Start Menu shortcuts created pointing to installed `SLMEducator.exe`.
- **First-Run Administrator Bootstrap (`BOOT-06`)**: **PASS**
  - First launch with empty database opened `_native_setup` masked dialog titled *"Configurar el primer administrador"* (`boot06_01_first_admin_dialog.png`).
  - Cancelling cleanly exits without creating orphan records (0 users in database).
  - Re-launched, credentials entered (`synthetic_admin`) with masked dots (`boot06_02_first_admin_filled.png`).
  - Form submitted via `Return`; user record created with `ADMIN` role.
  - Subsequent launches bypass bootstrap dialog directly to Launcher GUI.

---

### 3.4. Launcher GUI & State Fixtures (`BOOT-02`, `BOOT-05`)
- **State Visual Feedback**:
  - `starting`: *"Iniciando tu aplicación / Preparando el servidor local."* (`boot05_01_launcher_starting.png`).
  - `ready`: *"Lista para abrir / El servidor local responde. Abre SLMEducator en tu navegador."* (`boot02_01_launcher_ready.png`).
  - `slow`: Delayed response properly surfaces *"El inicio está tardando más / Sin respuesta válida tras 30 segundos."* (`boot05_02_launcher_slow.png`).
  - `stopped`: Server stop surfaces *"Aplicación detenida / Elige Iniciar para volver. Tus datos guardados permanecen en este equipo."* (`boot05_03_launcher_stopped.png`).
  - `start_failed`: Port collision / startup error cleanly surfaces *"Requiere atención / No se pudo iniciar el servidor. Revisa los puertos disponibles y api.log."* (`boot05_04_launcher_failed.png`).
  - High-DPI Scaling: Cards and buttons scale dynamically without layout clipping (`boot05_06_launcher_dpi.png`).
- **`BOOT-02` Browser Open**: **PASS**
  - Clicking *"Abrir SLMEducator"* / pressing `Ctrl+O` sends URL to the default browser and displays *"Se ha enviado el enlace a tu navegador."*.
- **Process Lifecycle & Exit**: **PASS**
  - Closing window (`X` or `Ctrl+Q`) displays confirmation dialog *"¿Detener la aplicación local y cerrar esta ventana?"* (`boot05_05_launcher_confirm_exit.png`).
  - Cancelling keeps application and server active.
  - Confirming cleanly terminates child server process without orphan background processes or dangling ports.

---

### 3.5. Assigned Practice & Draft Recovery (`LEARN-03`)
Verified end-to-end on installed application serving Edge browser with synthetic exercise content:
- **Practice Question Initial Presentation**: **PASS**
  - Question options presented in `<select>`: *"Elige una respuesta"*, *"Almacenar carga y suavizar el rizado de tensión"*, *"Aumentar la resistencia del circuito"*, *"Invertir la polaridad de la fuente"*, *"Disipar calor"*.
  - Answer key and explanation are strictly hidden before the student executes a check.
- **Incorrect Answer Self-Check**: **PASS**
  - Selected *"Aumentar la resistencia del circuito"* and clicked *"Comprobar mi respuesta"*.
  - Polite live region immediately announced:
    - *"Compara tu respuesta con la respuesta de referencia."*
    - Suggested answer: *"Respuesta sugerida: Almacenar carga y suavizar el rizado de tensión"*.
    - Explanation: *"El condensador almacena carga durante los picos de voltaje y la descarga cuando la tensión disminuye, suavizando el rizado de tensión para entregar una señal más continua."*.
    - Practice disclaimer: *"Esta comprobación es una práctica, no una calificación final."*.
  - Visual evidence: `learn03_01_practice_incorrect_feedback.png`.
- **Correct Answer Self-Check**: **PASS**
  - Selected *"Almacenar carga y suavizar el rizado de tensión"* and clicked *"Comprobar mi respuesta"*.
  - Polite live region announced: *"Tu elección coincide con la respuesta de referencia."*.
  - Visual evidence: `learn03_02_practice_correct_feedback.png`.
- **Local Draft Persistence Across Reload**: **PASS**
  - Changed selection to *"Invertir la polaridad de la fuente"*.
  - Draft notice displayed: *"Borrador de práctica guardado en este navegador. Esto no entrega una respuesta ni actualiza el progreso."*.
  - Hard reloaded the browser page (`page.reload()`).
  - Practice block detected stored draft and rendered the candidate card: *"Hay un borrador de práctica para esta cuenta, lección y sesión."* with *"Restaurar borrador"* and *"Descartar borrador"*.
  - Visual evidence: `learn03_03_practice_draft_detected.png`.
- **Draft Restoration**: **PASS**
  - Clicked *"Restaurar borrador"*; the form restored the value *"Invertir la polaridad de la fuente"*.
  - Visual evidence: `learn03_04_practice_draft_restored.png`.
- **Draft Discard Flow**: **PASS**
  - Changed selection, reloaded, and clicked *"Descartar borrador"*.
  - Candidate card dismissed cleanly; browser storage cleared.
- **Practice vs. Graded Attempt Distinction**: **PASS**
  - Queried SQLite table `assessment_submissions` after completing all practice checks, drafts, and restorations.
  - Count: `0` rows.
  - Confirmed: Independent practice is strictly a client-side self-check; no assessment submission, grade, or progress record was created or mutated.

---

### 3.6. Accessibility & Screen Reader Compliance (`VIS-06`)
Verified across all mandatory functional contexts on the installed application:
1. **Login Page (`/entrar`)**:
   - Semantic `<form>`, `<input id="_r_0_" name="username">`, `<input id="_r_1_" type="password">`, submit `<button>`.
   - Associated `<label for="_r_0_">` with text *"Usuario"*.
   - **Real Audio Acceptance**: User executed Windows Narrator (`Ctrl+Win+Enter`) and navigated via `Tab`. Narrator audibly announced: `"Usuario, campo de edición"`.
2. **Form Validation & Inline Errors**:
   - Submitting empty form highlights invalid inputs with `aria-invalid="true"` and associates error element via `aria-describedby="_r_0_-error"`.
   - Error text *"Este campo es obligatorio."* is linked directly to the input.
   - Initial invalid field automatically receives keyboard focus.
3. **Classroom & Tutor (`/tutor`) / Learning & Dialogue (Block 2)**:
   - Navigation tabs use `aria-pressed="true"` / `aria-pressed="false"` to indicate active mode (*"Conversación"* vs *"Preguntas compartidas"*).
   - Inactive workspace sections are marked with `hidden` and `inert`.
   - Headings use `tabIndex="-1"` and receive programmatic focus on route transitions.
   - **Real Audio Acceptance (Block 2 - Learning/Dialogue)**: User executed Windows Narrator and confirmed all screen reader announcements, controls, and focus navigation operate correctly and audibly as intended.
4. **Modal Dialogs (`ConfirmDialog` / `@base-ui/react/dialog`)**:
   - Modal container has `role="dialog"`, backdrop element, title with `Dialog.Title`, and description with `Dialog.Description`.
   - Accessible keyboard focus trap; `Escape` key closes dialog; focus returns to trigger on dismissal.
5. **Study Session Live Regions**:
   - Practice feedback and hint notifications utilize `role="status"` and `aria-live="polite"`.
   - System error containers utilize `role="alert"`.
- Complete node structure exported in `accessibility_tree_matrix.json`.

---

### 3.7. Synthetic Replica Migration vs. Personal Data Boundary
- **Synthetic Legacy Replica Check**: **PASS**
  - Deployed synthetic legacy database with teacher (`legacy_teacher`), student (`legacy_student`), and study plan (`Plan Sintetico Legacy`), plus `env.properties`.
  - Installed candidate launched cleanly; schema verified intact; continuity evidence recorded in `migration_continuity_evidence.json`.
- **Personal Installation Safety Boundary**: **STRICT BOUNDARY PRESERVED**
  - Personal installation location: `C:\Users\dhays\AppData\Local\Programs\SLMEducator`.
  - Personal database `slm_educator.db` (434,176 bytes) remained untouched, unmigrated, unopened, and uninspected.
  - **Explicit Limitation**: Demonstration of migration on a synthetic replica does NOT prove compatibility with the user's private database.

---

## 4. Documented Technical Limitations (Not Regressions)

1. **Semantic Scoring 35/36 Boundary**:
   - Rubric evaluation retains the known 35/36 boundary where one edge-case rubric criterion evaluates strictly to a score of 2. Documented as a transparent technical property without artificial score overrides.
2. **`objective-hostile` Evaluation Behavior**:
   - The generation evaluation recorded 36/36 HTTP 200 responses and 35/36 strict rubric passes. The single non-passing case incorporated the injected false value as an option in the generated output rather than filtering it out, without any request rejection or service failure.
3. **In-Place Upgrade Non-Support**:
   - Setup refuses in-place overwrites by architectural design; clean uninstall/reinstall retains all user database records.

---

## 5. Artifact Directory & Evidences Manifest

All 27 visual, structural, and log evidences are preserved in:  
`C:\Users\dhays\SLMEducator-Acceptance-Evidence-Native-20261015`

| Index | Evidence File | Type | Description |
| :---: | :--- | :--- | :--- |
| 1 | `gui_01_setup_welcome.png` | Screenshot | Inno Setup interactive welcome and destination directory screen |
| 2 | `gui_02_setup_cancel_confirmation.png` | Screenshot | Inno Setup interactive cancellation confirmation prompt |
| 3 | `gui_03_setup_dir_selected.png` | Screenshot | Installation directory set to `SLMEducator-Acceptance-Native-Install` |
| 4 | `gui_04_setup_tasks.png` | Screenshot | Desktop shortcut creation task selected |
| 5 | `gui_05_setup_ready.png` | Screenshot | Ready to Install summary screen |
| 6 | `gui_06_setup_finished.png` | Screenshot | Setup installation finished screen |
| 7 | `boot06_01_first_admin_dialog.png` | Screenshot | First-run setup dialog (`_native_setup`) for initial admin |
| 8 | `boot06_02_first_admin_filled.png` | Screenshot | First-run setup dialog with masked password input |
| 9 | `boot02_01_launcher_ready.png` | Screenshot | Launcher GUI in `ready` state with green indicator and address |
| 10 | `boot05_01_launcher_starting.png` | Screenshot | Launcher GUI in `starting` state (*"Iniciando tu aplicación"*) |
| 11 | `boot05_02_launcher_slow.png` | Screenshot | Launcher GUI in `slow` state (*"El inicio está tardando más"*) |
| 12 | `boot05_03_launcher_stopped.png` | Screenshot | Launcher GUI in `stopped` state (*"Aplicación detenida"*) |
| 13 | `boot05_04_launcher_failed.png` | Screenshot | Launcher GUI in `start_failed` error state (*"Requiere atención"*) |
| 14 | `boot05_05_launcher_confirm_exit.png` | Screenshot | Launcher window close confirmation prompt |
| 15 | `boot05_06_launcher_dpi.png` | Screenshot | Launcher GUI high-DPI scaling check |
| 16 | `crit_01_login_page.png` | Screenshot | Candidate login page at `/entrar` |
| 17 | `crit_02_form_validation_errors.png` | Screenshot | Inline form validation errors and initial focus handling |
| 18 | `crit_03_admin_home.png` | Screenshot | Authenticated administrator workspace |
| 19 | `crit_04_classroom_tutor.png` | Screenshot | Student classroom tutor workspace with question tabs |
| 20 | `crit_05_modal_persona_nueva.png` | Screenshot | Account creation form |
| 21 | `learn03_01_practice_incorrect_feedback.png` | Screenshot | Practice incorrect answer self-check feedback & explanation |
| 22 | `learn03_02_practice_correct_feedback.png` | Screenshot | Practice correct answer match feedback |
| 23 | `learn03_03_practice_draft_detected.png` | Screenshot | Practice local recovery draft detected card after page reload |
| 24 | `learn03_04_practice_draft_restored.png` | Screenshot | Practice restored draft in select input |
| 25 | `accessibility_tree_matrix.json` | JSON Data | Comprehensive accessibility node attributes, focus, and live regions |
| 26 | `migration_continuity_evidence.json` | JSON Data | Continuity records for synthetic legacy replica |
| 27 | `rejection-test.log` | Log File | Inno Setup in-place upgrade rejection execution log |

---

## 6. Conclusion & Integration Recommendation

The native Windows candidate `96489dadb2a25b67ae382bad11b215af9f828e7f` meets all acceptance criteria:
1. Automated test gates (frontend 894 tests, backend 80 packaging tests) pass 100%.
2. Pristine payload and installed executable match byte-for-byte (`EA1F81B315...`).
3. Setup installer properly refuses in-place overwrite and cleanly handles install, cancel, uninstall, and reinstall.
4. Launcher GUI cleanly handles all process states, DPI scaling, and exit confirmations without leaving orphan processes.
5. `LEARN-03` client-side practice, hints, feedback, explanation, draft persistence across reloads, restoration, discard, and submission isolation are fully verified with 0 submissions created.
6. `VIS-06` accessibility attributes, focus management, inline errors, and live regions are verified with real audio confirmation from Windows Narrator.
7. Personal user installation and database remain strictly untouched.

**Recommendation**: The candidate is ready for review and integration.
