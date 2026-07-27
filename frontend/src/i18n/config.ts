import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from './locales/en.json';
import ru from './locales/ru.json';

/**
 * Read the stored language without assuming localStorage is usable.
 *
 * This runs while the module is being imported, where a throw would take the
 * whole app down. Safari in private mode raises on access, and non-browser
 * environments may not provide Storage at all, so fall back to the default.
 */
function storedLanguage(): string | null {
  try {
    return globalThis.localStorage?.getItem('language') ?? null;
  } catch {
    return null;
  }
}

i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      ru: { translation: ru }
    },
    lng: storedLanguage() || 'en',
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false
    }
  });

export default i18n;
