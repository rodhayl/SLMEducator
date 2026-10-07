import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import { en, es } from './common';
export function bridgeInterpolation(value: unknown): unknown {
  if (typeof value === 'string') return value.replace(/(?<!\{)\{([A-Za-z_][\w]*)\}(?!\})/g, '{{$1}}');
  if (Array.isArray(value)) return value.map(bridgeInterpolation);
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, bridgeInterpolation(item)]));
  return value;
}
let language = 'es'; try { language = localStorage.getItem('slm-language') || 'es'; } catch { /* Browser defaults remain usable. */ }
void i18n.use(initReactI18next).init({ lng: ['en', 'es'].includes(language) ? language : 'es', fallbackLng: 'es', defaultNS: 'common', resources: { en: { common: en }, es: { common: es } }, interpolation: { escapeValue: false }, returnNull: false });
i18n.on('languageChanged', lng => { document.documentElement.lang = lng; try { localStorage.setItem('slm-language', lng); } catch { /* Preference is session-only. */ } });
document.documentElement.lang = i18n.language;
export function registerLocales(namespace: string, locales: { en: object; es: object }) { i18n.addResourceBundle('en', namespace, locales.en, true); i18n.addResourceBundle('es', namespace, locales.es, true); }
export default i18n;
