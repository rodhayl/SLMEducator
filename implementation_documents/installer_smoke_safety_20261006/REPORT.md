# Installer smoke safety corrections

Local validation: 2026-10-06, based on PR #3 head
`197764b3e792d42fb73227345e510f3718c46785`. Exact input and changed-file
identities are in [SOURCE_IDENTITY.json](SOURCE_IDENTITY.json).

## Changes

- Skip before setup on either actual redirected Start Menu/Desktop shortcut or
  exact current/legacy app registration. Rollback checks the registered target
  and owned uninstaller; no global process kill or registry deletion.
- Use Windows PowerShell `Start-Process -Wait` and a fresh exit-code marker to
  establish process-tree completion. Failed partial installations roll back only
  after this verified wait. Timeout, interruption, incomplete marker, foreign
  state or unsuccessful cleanup retains target/uninstaller and logs. A timeout
  does not prove descendants stopped; inspect owned processes before cleanup.
- Mutate valid disposable SQLite/config content before preservation hashes, so
  resetting to the same packaged seed fails the test.
- Simulate Windows in three mocked orchestration tests, keeping real non-Windows
  rejection. Correct narrow safety and password-output claims in the guides.

[Microsoft documents the descendant wait](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/start-process?view=powershell-5.1).

## Local verification and limits

- Linux/Python 3.12: **38 passed, 1 native-only skip** across the static installer,
  synthetic lifecycle contract, and opt-in Windows lifecycle modules.
- Controlled regressions include both shortcut collisions; failed initial and
  later install rollback; timeouts at all three setup stages; same-seed negative
  controls; missing/stale/mismatched completion markers; shell failure;
  interrupted wait; literal path quoting; and failure/ownership cleanup fences.
- Focused Ruff correctness rules and mypy with Windows target pass for the three
  changed Python files. This is not full-project lint, typing or coverage.
- These results precede publication. No native Windows Setup/PowerShell execution,
  application run, user profile, credential, real database or Actions check was
  used during preparation. A skip or synthetic pass is not a native Windows PASS.

The recipe, builder and runtime remain unchanged. The existing `fe954cab4655`
installer remains the manual candidate; no rebuild was performed or required by
these test-only corrections. Recheck its recorded local hash before use, launch
non-elevated and select a genuinely fresh destination with no registration or
shortcut collisions. The unchanged recipe does not protect unregistered
portable destinations. Historical native receipts remain historical. Human
launcher-X/process-tree/port observation and a later disposable native run of
this hardened smoke remain pending.

## Native Windows validation (2026-10-07)

The corrections were incorporated into branch
`feature/windows-installer-inno-20261006` by cherry-picking
`e1e46d8af811a117f365a3872bccc5563a4a066b` onto head
`197764b3e792d42fb73227345e510f3718c46785`; the result is commit `1562190`.
No conflict arose, and no product, recipe or builder file changed.

- One follow-up Windows-only correction was needed after the cherry-pick, in
  `tests/test_installer_lifecycle_contract.py` only: `sqlite3.connect` used as a
  context manager commits but never closes, so on Windows the disposable
  cleanup `rmtree` failed with `WinError 32` on the open `slm_educator.db`
  (Linux unlinks open files, which is why the earlier Linux run passed). Both
  contract-test connections now use the same `closing()` pattern as the smoke
  module. `SOURCE_IDENTITY.json` keeps recording the received commit only;
  this post-validation edit is documented here and in the branch history.
- Windows 11 10.0.26200, Python 3.13.15 (worktree venv, pytest 9.0.2):
  `tests/test_build_installer.py` + `tests/test_installer_lifecycle_contract.py`
  = **38 passed** (3.96 s). Focused flake8 and mypy pass on the three changed
  Python files.
- Hardened native smoke (opt-in), reusing the delivered installer without
  rebuild: install → in-place refusal → uninstall → reinstall, with the mutated
  synthetic DB/config preserved by hash. **1 passed in 19.04 s** with
  `SLM_INSTALLER_SETUP` =
  `...\.manual-windows-worktree\dist\SLMEducator-installer-fe954cab4655\SLMEducator-Setup-2.0.0-fe954cab4655.exe`
  and `SLM_INSTALLER_PAYLOAD_SHA256` =
  `e60912db796fa59b8aa9c8f8ea405b112e46eb27915fde8360acb3f385f3c230`.
- Installer identity re-verified before and after the native run: 31,456,307
  bytes, SHA-256
  `c02c79e21e6d04d327ed11223203c85ef95fd5b796fbc6a2c771ed5f952a1531`; payload
  EXE, DB and config hashes unchanged after the smoke.
- Profile isolation was checked read-only before the run (no HKCU
  `Software\Microsoft\Windows\CurrentVersion\Uninstall\{40301115-8D29-4D37-A067-F025278BCDC0}`
  registration in either view; no Start Menu/Desktop `SLMEducator` shortcut) and
  after it (registry, shortcuts and processes clean; disposable `--basetemp`
  `C:\tmp\slm-installer-lifecycle-20261007-9f0c3af4` removed following the
  passing run).
- Still pending and unchanged: the human launcher-X observation; no claim of
  real model inference or educational efficacy follows from any of this.
