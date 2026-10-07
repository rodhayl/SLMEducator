# React appearance hook reference

This retained documentation URL now describes the current React API. The former
Qt theme API is retired. See [React appearance system](THEME_SYSTEM.md) for the
behavior and styling contract.

Import from `@/app/AppearanceProvider` beneath `AppearanceProvider`:

```tsx
import { useTranslation } from 'react-i18next';
import { useAppearance } from '@/app/AppearanceProvider';
import { Button } from '@/components/ui';

export function DarkThemeButton() {
  const { setTheme } = useAppearance();
  const { t } = useTranslation();
  return <Button onClick={() => setTheme('dark')}>{t('dark')}</Button>;
}
```

The hook exposes:

- `theme: Theme` and `setTheme(value: Theme)`, where `Theme` is `light | dark | system`
- `readingSize: ReadingSize` and `setReadingSize(value: ReadingSize)`, where `ReadingSize` is `16 | 18 | 20 | 24`
- `animations: boolean` and `setAnimations(value: boolean)`

Theme and reading size initialize from validated origin-local preferences with
`system` and `18` defaults; write failures leave session-only state. Animation
state starts enabled and is not separately persisted by this provider. Setters
change presentation in the current browser; they do not save an account setting.
The account settings form performs and validates that separate API save first.

Use semantic CSS variables such as `--background`, `--surface`, `--foreground`,
`--primary` and `--border` from the shared styles. Never set independent per-feature
document themes or use reading size as a substitute for browser zoom testing.

Source: [AppearanceProvider.tsx](../../src/frontend/src/app/AppearanceProvider.tsx).
