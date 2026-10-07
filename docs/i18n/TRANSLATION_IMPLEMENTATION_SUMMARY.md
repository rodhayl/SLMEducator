# Current localization boundaries

This is a maintained implementation reference, not a claim that every string has
been translated or every accessibility path accepted. Dated implementation and
validation reports remain historical evidence for their recorded versions.

## React learning interface

The frontend bundles `src/frontend/src/i18n/common.ts` plus feature-owned
`src/frontend/src/features/<domain>/locales.ts` catalogs. The router registers the
feature namespace. Components use `react-i18next` hooks. Spanish and English are
the two supported UI languages, with Spanish as the startup/default fallback.

`src/frontend/src/i18n/index.ts` validates the stored startup choice, keeps
`document.documentElement.lang` current and saves the origin-local `slm-language`
preference when possible. Storage failures leave the selection in memory. The
account appearance form has a separate validated `/api/settings/app` save.

Follow the [translation guide](TRANSLATION_GUIDE.md) for key ownership,
double-brace interpolation, accessible labels, language changes and build checks.

## Python translation service

`src/core/services/translation_service.py` still loads `translations/*.json` and
provides translation lookup and language discovery to Python callers. The
`GET /api/settings/translations/{lang}` endpoint uses it. Preserve this maintained
service and its resources; retirement of the Qt educational UI does not make
them unused. Adding these JSON resources alone does not extend React locales.

## Native launcher

The packaged launcher is Tkinter in `src/starter.py`, with its own native strings
and lifecycle controls. It does not import a Qt translation helper or obtain its
strings from the React bundle. Test native launcher changes separately.

## Validation boundaries

Use `npm run check --prefix src/frontend` for the frontend gate. Synthetic tests
cover translation-dependent UI behavior; actual browser layout, assistive
technology, native Windows packaging and educational translation review remain
separate checks. Do not infer complete language coverage from a fallback value
or from a previous implementation report.
