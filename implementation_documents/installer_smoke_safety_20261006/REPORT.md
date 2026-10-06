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
