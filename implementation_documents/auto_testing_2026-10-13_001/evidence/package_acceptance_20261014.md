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
