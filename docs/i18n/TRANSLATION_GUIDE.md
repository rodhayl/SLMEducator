# React translation guide

The active learning interface uses `i18next` and `react-i18next`. Its supported
languages are Spanish (`es`) and English (`en`). Spanish is the startup default
and fallback; this is not browser-language detection.

## Catalogs and registration

- Shared labels live in [common.ts](../../src/frontend/src/i18n/common.ts).
- Each feature exports `locales = { en: {...}, es: {...} }` from
  `src/frontend/src/features/<domain>/locales.ts`.
- [router.tsx](../../src/frontend/src/app/router.tsx) registers these feature
  catalogs under their feature-directory name through `registerLocales`.
- [i18n/index.ts](../../src/frontend/src/i18n/index.ts) owns initialization,
  registration, language preference and document language.

Use `useTranslation('<domain>')` in a feature. Use `useTranslation()` for the
shared `common` namespace. Reuse common strings where their meaning matches.

```tsx
// Example feature locales.ts
export const locales = {
  en: { saved: 'Material {{id}} saved.' },
  es: { saved: 'Material {{id}} guardado.' },
};

// Inside a React component in that feature:
const { t } = useTranslation('authoring');
const message = t('saved', { id: materialId });
```

Use double-brace interpolation (`{{name}}`) and keep placeholders identical in
both languages. `registerLocales` registers values as supplied; it does not
convert single-brace placeholders automatically. Render translations as React
text. Do not inject translation HTML. Course content written by users remains in
its original language and uses the shared content-rendering boundary.

## Language changes and persistence

The login and application-shell controls call `i18n.changeLanguage('es')` or
`i18n.changeLanguage('en')`. React translation hooks update the visible strings;
no page reload is required. Initialization accepts only `en` or `es` from the
origin-local `slm-language` preference, otherwise selecting Spanish. Language
changes update `document.documentElement.lang` and attempt to save that browser
preference. If storage is unavailable, the current in-memory choice still works.

The account appearance form separately saves `/api/settings/app` and applies the
confirmed language to the browser. Do not assume a local language change saves an
account setting or synchronizes other devices.

## Adding or changing text

1. Add matching keys in both English and Spanish within the relevant catalog.
2. Translate labels, instructions, errors, statuses and accessible names, including
   icon-only buttons. Preserve placeholders and meaningful uncertainty messages.
3. Add or update focused tests in `tests/frontend/` for both languages, including
   re-rendering after a language change where relevant.
4. Run `npm run check --prefix src/frontend` with the locked toolchain prepared.
   This includes typecheck, lint, synthetic DOM tests and the production build.

Adding a third language requires explicit frontend resources, accepted-language
validation, selectors, settings contracts and tests. Adding a JSON file under the
repository's `translations/` directory alone does not add a React language.

## Separate Python and launcher surfaces

The retained [Python translation service](../../src/core/services/translation_service.py)
loads repository `translations/*.json` for its own callers, including the settings
translation endpoint. It is not the source of the bundled React catalogs. The
native Tkinter launcher maintains its own strings. See
[localization boundaries](TRANSLATION_IMPLEMENTATION_SUMMARY.md).

A missing translation can render a fallback or key; that is not a completeness
check. Verify visible text and accessible names. DOM checks do not replace actual
browser layout, screen-reader or native launcher acceptance.
