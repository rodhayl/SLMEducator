# React appearance system

The active learning interface uses the shared
[AppearanceProvider](../../src/frontend/src/app/AppearanceProvider.tsx),
[CSS tokens](../../src/frontend/src/styles/tokens.css) and
[base styles](../../src/frontend/src/styles/base.css). There is no maintained Qt
theme controller. The native Tkinter launcher is a separate interface and does
not consume React appearance state.

## Behavior

- Theme choices are `light`, `dark` and `system`. The default is `system`; it
  follows `prefers-color-scheme` changes and writes the resolved value to the
  document's `data-theme` attribute.
- The browser preference is stored under `slm-theme`. Invalid or unavailable
  stored values fall back to `system`. A failed storage write leaves the current
  in-memory choice usable.
- Reading sizes are `16`, `18`, `20` and `24`, defaulting to `18`. They are stored
  under `slm-reading-size` and applied as `--reading-size` in rem to `.prose`.
  This control does not change actual browser zoom.
- Animations start with the system behavior. Once signed in, the shell loads
  the current account's `/api/settings/app` through the shared scoped query and
  applies a validated `enable_animations` value, including on a fresh opening
  outside Settings. `false` writes `data-motion="reduced"`. The prior account's
  value is reset on account replacement/logout. Unavailable or invalid initial
  settings leave system behavior; a failed same-account refresh does not erase
  an already confirmed preference. There is no separate localStorage entry.
  Shared CSS always respects `prefers-reduced-motion`.

The shell theme control changes the browser preference immediately. The account
appearance form shares `/api/settings/app`. Motion is applied from a confirmed
read at sign-in/reopening, while theme, reading size and language keep their
browser-local initialization. Only a matching successful save applies all four
form values to this browser. Unsaved form changes do not change motion.
The server value `auto` maps to the provider value `system`. Do not describe the
browser preference as automatically synchronized across accounts or devices.

## Contribution rules

Use `useAppearance()` and the shared UI primitives. Add semantic color/style
changes to the shared token/base stylesheet rather than a second theme manager
or feature-local overrides. Keep focus visibility, readable states, keyboard
access, reduced motion and forced-color styling intact. Translate labels in both
supported languages using the [translation guide](../i18n/TRANSLATION_GUIDE.md).

See the [hook reference](API_THEME_MANAGER.md),
[frontend contracts](../../src/frontend/CONTRACTS.md) and
[frontend build instructions](../../src/frontend/README.md).

## Verification

[Appearance DOM tests](../../tests/frontend/foundation-appearance.test.tsx) cover
preference storage, invalid-value defaults, reading-size units and animation
state. Settings tests cover the save boundary, motion on reopening, account replacement
and invalid/late preferences. Run `npm run check --prefix
src/frontend` from a prepared checkout after relevant changes. DOM checks do not
certify painted contrast, a screen reader, native Windows or actual browser zoom;
use the separate browser/native acceptance gates for those claims.
