# Candidate package acceptance · 2026-10-14

## Artifact identity

- Source commit: `d6deecf89967e6d37698413b726ed5e656452647`
- Source tree: `2cab18b2f1738a9a7677760896df6e066f58b573`
- Windows production output: `%TEMP%\slm-candidate-d6deecf-prod-20261014`
- Build environment: Python 3.13.15, PyInstaller 6.16.0
- Package tree: 2,323 files, 74,804,664 bytes
- `SLMEducator.exe` SHA-256:
  `9f354849628b9ce9b77fad4ce180a9a0b5bdcc2cd9fc401841456292dac8743b`
- SHA-256 manifest digest:
  `fff1e68fb060b48414f44006c4e691b9d057069409b4d892189e4349f70b80d2`
- Manifest file retained outside the checkout at
  `%TEMP%\slm-candidate-d6deecf-prod-20261014.sha256.manifest`. It lists
  lowercase SHA-256 and relative POSIX path for each package file, sorted
  lexicographically, one entry per line, UTF-8 with a final newline. The
  digest above is SHA-256 of those manifest bytes.

The package output remained separate from every mutable runtime copy. The
source commit and tree were rechecked after the build. The executable hash of
the isolated runtime copy matched the untouched build output.

## Isolated packaged-runtime checks

All package runs used a copy outside the checkout, disposable synthetic
accounts/database/configuration, `--no-browser`, and loopback-only endpoints.
The copy returned `/api/status` with `status=online`, version `2.0.0`, first
on port 8000 and then on port 8001 while a separate synthetic listener held
127.0.0.1:8000. The fallback run used an explicitly isolated temporary
`USERPROFILE`/`HOME`; the launcher and loopback blocker were stopped afterward.

The learner UI showed the synthetic dashboard, course list, lesson study, and
assigned practice. Incorrect and correct answers produced local self-check
feedback; the browser-local draft survived a reload and was restored. No answer
was submitted, graded, or recorded as course progress. The page disclosed that
browser drafts are unencrypted and expire after seven days.

The package tutor checks used a deterministic local HTTP stub, not Gemma:

- Free tutor produced a response, while an unavailable-provider run displayed
  the “no usable suggestion confirmed” state.
- A contextual request used the selected synthetic lesson section and showed
  the source version and section in the receipt.
- Requested bullet and JSON output formats rendered in the UI.
- A delayed stub response was cancelled. The UI showed local cancellation and
  did not render the late answer.
- An immediate second request from that same view was not confirmed. After
  reopening the tutor page, a new request completed successfully. This nuance
  is preserved as partial package-UI evidence, not reported as a same-view
  recovery pass.

The package did not call Gemma. A separate authorized source-checkout probe
after SLM-AUTO-021 returned HTTP 200 with `finish_reason=stop` after
123.985 seconds. The cancellation UI suppressed delivery, the request stayed
busy and concurrent attempts received 409 until provider work completed, and
a subsequent request succeeded in 53.684 seconds. No raw model response was
copied into campaign evidence; the loaded model remained unchanged.

## Isolation caveat

One earlier exploratory port-fallback seed/start attempt did not redirect
`USERPROFILE`/`HOME`. The application imports security helpers that resolve
the encryption key through `Path.home()/.slm_educator`; that attempt may
therefore have read an existing default-profile key or created one. Its
processes were stopped. No default-profile files were inspected, removed, or
changed afterward, and the personal database/configuration and installed app
were not intentionally used. The final port-fallback run was repeated with a
temporary profile. The owner should review the possible default-profile key
access; no automated cleanup is appropriate.

## Acceptance limits

This is package-copy evidence, not an installation or release. The owner’s
installed build remains `29df5ed`; it was not replaced or launched. The
launcher’s native “Abrir SLMEducator” button, slow/failing-start timeout,
keyboard URL entry, DPI behavior, Narrator/audio, and installed-candidate
learning acceptance remain open. The frozen rubric remains 35/36 strict
all-2; reserved `objective-hostile` remains a validation-only weakness.

## Live Gemma 4 packaged-runtime verification (same-view recovery)

On 2026-10-14, the packaged candidate `slm-candidate-d6deecf-prod-20261014` (`SLMEducator.exe` SHA-256 `9f354849628b9ce9b77fad4ce180a9a0b5bdcc2cd9fc401841456292dac8743b`) was executed against the verified live model in LM Studio (`gemma-4-12b-it-qat@q4_k_xl` on `127.0.0.1:1234`) using strict environment isolation:
- Pre-flight standard library check confirmed `HOME`, `USERPROFILE`, `APPDATA`, `LOCALAPPDATA`, `SLM_LOG_DIR`, `SLM_DB_PATH`, and `SLM_CONFIG_FILE` resolved 100% inside disposable temporary directories.
- Synthetic pilot database was seeded with a course and lessons assigned to `learner_a`, with `AIModelConfiguration` targeting LM Studio (`temperature: 0.0`, `reasoning_effort: "none"`, `max_tokens: 2000`).
- Automated headless browser journey (Playwright + Chrome) exercised the candidate on port 8000:
  1. **Free Tutor**: A prompt sent to the candidate produced a verified pedagogical response in 13.15s, displaying visible AI uncertainty (`Sugerencia de IA sin verificar`) and clearing the input textarea. Evidence: `evidence/browser_candidate_gemma4_20261014/tutor_free_gemma4.png`.
  2. **Contextual Tutor**: Course and lesson material ("Partes iguales") were selected. The source details displayed the source version and references (`[content:1/section-1]`). The contextual question was answered accurately referencing the lesson content in 11.63s. Evidence: `evidence/browser_candidate_gemma4_20261014/tutor_contextual_gemma4.png`.
  3. **Tutor Formats**: Formatted output was requested under explanation mode. Structured response rendered safely in the `ContentRenderer` prose container in 11.64s. Evidence: `evidence/browser_candidate_gemma4_20261014/tutor_format_bullets.png`.
  4. **Cancellation and Same-View Recovery**:
     - A multi-step prompt was sent to Gemma 4.
     - "Cancelar solicitud de IA" was clicked locally.
     - Confirmed local cancellation banner appeared: `Cancelación local confirmada. El proveedor puede continuar y podrían aplicarse cargos.`
     - Typed prompt was preserved in the input textarea.
     - Ask button was immediately disabled.
     - Concurrent request POST received HTTP 409 Conflict while inference continued in the background.
     - In-flight background provider completed in 46.41s without leaking any late response into the conversation log.
     - Ask button remained disabled until explicit user action.
     - Expanding "Política de ayuda, uso y recibo" and clicking "Actualizar estado" queried the backend status without auto-submitting; send button re-enabled with the preserved prompt intact.
     - User explicitly clicked send; second request completed successfully with a fresh request ID in 35.72s in the same view without page reload. Evidence: `evidence/browser_candidate_gemma4_20261014/tutor_cancellation_recovered.png`.

## Reconstructed candidate presentation verification · 2026-10-14

### Reconstructed candidate identity

- Source commit: `884afc80e1636edef2e00c7dd1a402ce120fe381`
- Source tree: `4528a2c6de7a2b82cdb54b62324fbf08b5c2d0cf`
- Windows production output: `%TEMP%\slm-candidate-884afc8-prod-20261014`
- Build environment: Python 3.13.15, PyInstaller 6.16.0
- Package tree: 2,442 files, 78,476,699 bytes
- `SLMEducator.exe` SHA-256:
  `3772053b4c2f03bc6761f13a09415d64df67914fa950ece4ce0d6201a815e8c2`
- SHA-256 manifest digest:
  `76bb5cdff5c9ed124c16a55b6aceebd57980f388cfefc159f059b21fee99e41d`
- Manifest file retained outside the checkout at
  `%TEMP%\slm-candidate-884afc8-prod-20261014.sha256.manifest`.

The package output remained separate from every mutable runtime copy. The
source commit and tree were rechecked after the build. The executable hash of
the isolated runtime copy matched the untouched build output.

### Correction of previous format reporting

The previous candidate run of `d6deecf` reported item 3 ("Tutor Formats") as
passing because structured content rendered without crashing in `ContentRenderer`.
However, the capture `tutor_format_bullets.png` demonstrates that although the prompt
requested two bullet points with hyphens (`- regla 1 - regla 2`), the model emitted
a continuous prose paragraph without bullet points. Treating that observation as
a format PASS was contradictory to its visual evidence; the correct historical
evaluation is PARTIAL/FAIL of format.

### Bounded live tutor presentation acceptance (Gemma 4 on LM Studio)

Executed against candidate `slm-candidate-884afc8-prod-20261014` on loopback port
8000 using strictly isolated disposable directories (`%TEMP%\slm-runtime-884afc8-*`),
disposable synthetic SQLite database seeded with `seed_pilot`, and system Chrome 154
(headless) via Playwright:
- Pre-flight standard library check confirmed `HOME`, `USERPROFILE`, `APPDATA`,
  `LOCALAPPDATA`, `SLM_LOG_DIR`, `SLM_DB_PATH`, and `SLM_CONFIG_FILE` resolved
  100% inside disposable temporary directories.
- Effective model: `gemma-4-12b-it-qat@q4_k_xl` on LM Studio (`127.0.0.1:1234`),
  `temperature: 0.0`, `max_tokens: 2000`, `reasoning_effort: "none"`.
- Mode: Explicación (`explanation`). Clean synthetic state per case. One execution
  per case without retries:

1. **Case 1 (Single concise sentence)**:
   - Question: «Explica qué es una fracción en una sola frase breve, sin ejemplos ni listas».
   - HTTP Response: Status 200 in 6.79s (tokens used: 453, receipt request ID `485e4c81-36a6-49c8-b627-b45da1bfea67`).
   - Received `answer`: `"Una fracción representa una parte de un todo que ha sido dividido en partes iguales."`
   - Received `explanation`: `"Una fracción es la expresión matemática que indica cuántas partes de un entero se están considerando cuando este se divide en trozos iguales."`
   - Delivered student response: `"Una fracción es la expresión matemática que indica cuántas partes de un entero se están considerando cuando este se divide en trozos iguales."`
   - Evidence: `evidence/browser_candidate_gemma4_20261014/tutor_presentation_sentence.png`.
   - Result: **PASS** — Exactly one coherent short sentence without examples or lists, respecting requested presentation.

2. **Case 2 (Exactly two bullet points with hyphen)**:
   - Question: «Escribe exactamente dos viñetas breves sobre cómo comparar fracciones; empieza cada viñeta con un guion y no añadas introducción ni cierre».
   - HTTP Response: Status 200 in 8.89s (tokens used: 515, receipt request ID `ba674ce6-75dc-4617-999f-927002f8f443`).
   - Received `answer`: `"- Busca un denominador común para ambas fracciones.\n- Compara los numeradores de las fracciones resultantes."`
   - Received `explanation`: `"Para comparar fracciones, primero debes asegurarte de que tengan el mismo denominador (el número de abajo). Una vez que sean iguales, la fracción con el numerador más grande (el número de arriba) es la mayor. Por ejemplo, 1/4 y 3/4: como tienen el mismo denominador, 3/4 es mayor."`
   - Delivered student response: Continuous prose paragraph with explanation and example; no hyphens, no bullet list.
   - Evidence: `evidence/browser_candidate_gemma4_20261014/tutor_presentation_two_bullets.png`.
   - Result: **PARTIAL / FAIL de formato** — Although the model produced the two hyphenated bullet lines in its internal `answer` field and the educational content is correct, the student-facing `explanation` field (which the tutor delivers to the student) was formatted as a continuous prose paragraph. In accordance with acceptance rules, useful content that breaches the requested format is evaluated as PARTIAL/FAIL of format, not PASS.

### Cancellation, 409 concurrency lock, and same-view recovery

The records from the earlier candidate run remain authoritative and sufficient to substantiate cancellation behavior without re-running that campaign:
- Immediate local cancellation banner (`Cancelación local confirmada. El proveedor puede continuar y podrían aplicarse cargos.`).
- Input prompt preserved in textarea; ask button disabled.
- Concurrent POST received HTTP 409 Conflict while background inference was in-flight (46.41s).
- Late delivery suppression: background provider completion did not leak into the student conversation log.
- Expanding "Política de ayuda, uso y recibo" and clicking "Actualizar estado" queried status without auto-submitting.
- Explicit user resubmission completed successfully with a fresh request ID in 35.72s in the SAME view without page reload (`evidence/browser_candidate_gemma4_20261014/tutor_cancellation_recovered.png`).

## Candidate 97bdee6 reconstruction and tutor presentation acceptance

### Artifact identity

- Source commit: `97bdee6c8f7302877eaa905136768aeb0f55651b`
- Source tree: `289e34706d09876b071d6464dae2df9154e3c8a2`
- Windows production output: `%TEMP%\slm-candidate-97bdee6-prod-20261014`
- Build environment: Python 3.13.15, PyInstaller 6.16.0
- Package tree: 2,442 files, 78,477,637 bytes
- `SLMEducator.exe` SHA-256:
  `1ee4e2c9e354aea701b5a1797e7b9535fcafc92d6d0b2406fecbd54e6cbccb5c`
- SHA-256 manifest digest:
  `b3c8fb922dbf119396f2c0060f6a9a7155d11d8f4ff76bcb682e279c52b11f44`
- Manifest file retained outside the checkout at
  `%TEMP%\slm-candidate-97bdee6-prod-20261014.sha256.manifest`.
- Focused test baseline (offline, contract verification): **127 passed, 1 warning in 69.35s** (exit 0).

The package output remained separate from every mutable runtime copy. The source commit and tree were rechecked after the build. The executable hash of the isolated runtime copy matched the untouched build output. The owner's installed personal application (`29df5ed`) was neither run nor modified.

### Live tutor presentation verification (Gemma 4 on LM Studio)

Executed against candidate `slm-candidate-97bdee6-prod-20261014` on loopback port 8000 using strictly isolated disposable directories (`%TEMP%\slm-runtime-97bdee6-*`), disposable synthetic SQLite database seeded with `seed_pilot`, and system Chrome 154 (headless) via Playwright:
- Pre-flight standard library check confirmed `HOME`, `USERPROFILE`, `APPDATA`, `LOCALAPPDATA`, `SLM_LOG_DIR`, `SLM_DB_PATH`, and `SLM_CONFIG_FILE` resolved 100% inside disposable temporary directories.
- Effective model: `gemma-4-12b-it-qat@q4_k_xl` on LM Studio (`127.0.0.1:1234`), `temperature: 0.0`, `max_tokens: 2000`, `reasoning_effort: "none"`.
- Mode: Explicación (`explanation`). Clean synthetic state. Single run without retries:

- **Case 2 (Exactly two bullet points with hyphen, repaired prompt contract)**:
  - Question: «Escribe exactamente dos viñetas breves sobre cómo comparar fracciones; empieza cada viñeta con un guion y no añadas introducción ni cierre».
  - HTTP Response: Status 200 in 4.43s (tokens used: 495, receipt request ID `c869a304-5f38-424e-9df2-148338cec6e9`).
  - Provider response JSON (`explanation` field):
    ```
    - Busca un denominador común para ambas fracciones antes de comparar sus numeradores.
    - Si los denominadores son iguales, la fracción con el numerador más grande es la mayor.
    ```
  - API delivered text (`response` field):
    `"- Busca un denominador común para ambas fracciones antes de comparar sus numeradores.\n- Si los denominadores son iguales, la fracción con el numerador más grande es la mayor."`
  - Rendered UI presentation:
    The frontend `ContentRenderer` parsed the Markdown hyphenated list into an unordered list (`<ul><li>...</li><li>...</li></ul>`), visibly displaying exactly two bullet points without intro, conclusion, or extra examples.
  - Mathematical correctness:
    1. Finding a common denominator before comparing numerators is mathematically correct and necessary when denominators differ.
    2. With equal denominators, comparing numerators to determine the larger fraction is strictly correct.
  - Evidence: `evidence/browser_candidate_gemma4_20261014/tutor_presentation_two_bullets_97bdee6.png`.
  - Result: **PASS** — Exactly two bullet points starting with hyphen in the delivered markdown text and rendered as two visual bullets in UI, with no introduction, closure, or extra examples outside them, and correct mathematical content.

