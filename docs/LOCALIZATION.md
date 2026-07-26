# Localization

The UI is translated with [i18next](https://www.i18next.com/) and
[react-i18next](https://react.i18next.com/). Two languages ship today:

| Language | Code | Keys | Status |
|---|---|---|---|
| English | `en` | 109 | Source of truth |
| Русский | `ru` | 109 | Complete |

`frontend/src/i18n/locales.test.ts` fails the build if the two files ever
disagree on which keys exist, so a missing translation is caught before review
rather than after release.

## Layout

```
frontend/src/i18n/
├── config.ts                   i18next initialisation
└── locales/
    ├── en.json                 the source of truth
    └── ru.json
```

Keys are nested objects, addressed with dots. Top-level sections:

| Section | Covers |
|---|---|
| `app` | Title, subtitle, version in the header |
| `nav` | Header navigation |
| `map` | Map page: instructions, layer switcher, search, selection readout |
| `settings` | Settings page: API keys, preferences, actions, messages, help links |
| `generation` | Generation panel: form, stage labels, results, error strings |
| `preview` | 3D preview panel |
| `common` | Shared words — loading, error, cancel, close, download |

## Using translations

```tsx
import { useTranslation } from 'react-i18next'

function MapHeader() {
  const { t } = useTranslation()
  return <h1>{t('app.title')}</h1>
}
```

Interpolation uses `{{name}}` placeholders:

```json
{ "map": { "selection": { "size": "{{width}} × {{height}} km" } } }
```

```tsx
t('map.selection.size', { width: 5.2, height: 5.2 })   // "5.2 × 5.2 km"
```

Changing language, as `LanguageSwitcher.tsx` does it:

```tsx
const { i18n } = useTranslation()
i18n.changeLanguage(code)
localStorage.setItem('language', code)
```

The choice is read back from `localStorage` in `config.ts` on the next load.

There is a second path: the Settings page stores `preferences.language` on the
server and applies it after a successful save, so the language follows the
install rather than the browser. The header switcher is the per-browser
override; whichever ran last wins for the current session.

## Pipeline stage labels

`generation.progress.*` is the one section that is not addressed literally.
`ProgressIndicator` builds the key at runtime:

```tsx
t(`generation.progress.${step.labelKey}`, { defaultValue: step.key })
```

`labelKey` comes from `frontend/src/lib/stages.ts`, which mirrors `BASE_STAGES`
and `AI_STAGES` in `backend/services/pipeline.py`. **Adding a pipeline stage
means touching three places:** the backend tuple, `stages.ts`, and both locale
files. The `defaultValue` keeps a missed translation from rendering as a raw key,
so an untranslated stage degrades to `fetch_dem` rather than
`generation.progress.downloadingDEM` — visible, but not broken.

Because these keys are never written out literally, a plain grep will not find
them. Do not delete an unreferenced `generation.progress.*` key without checking
`stages.ts` first.

## Adding a language

1. **Copy the source file.**

   ```bash
   cp frontend/src/i18n/locales/en.json frontend/src/i18n/locales/de.json
   ```

   Translate the values; leave every key exactly as it is.

2. **Register it** in `frontend/src/i18n/config.ts`:

   ```ts
   import de from './locales/de.json'

   resources: {
     en: { translation: en },
     ru: { translation: ru },
     de: { translation: de },
   }
   ```

3. **Add it to the switcher** in `frontend/src/components/LanguageSwitcher.tsx`.

4. **Widen the backend field** in `backend/models/user_settings.py` so the
   preference survives a save, and update the `UI_LANGUAGE` row in
   [SETUP.md](SETUP.md).

5. **Extend the parity test** in `frontend/src/i18n/locales.test.ts` so the new
   file is checked against `en.json` too.

## Checking your work

```bash
cd frontend && npm test        # includes the locale parity check
```

Then run the UI and switch languages with the header control. Look at all four
surfaces — map, settings, an in-flight generation, and a failed one. Error
strings are the ones that get missed, because you have to cause an error to see
them.

## Conventions

Keep untranslated: product names (BeamNG.drive, Sentinel Hub, Azure Maps),
technical abbreviations (API, DEM, AI, GeoTIFF), URLs and file paths.

Keep the key structure identical across files, always. If a phrase does not
apply in a language, translate it anyway — deleting the key breaks parity and
falls back to English mid-sentence, which reads worse than a stiff translation.

Watch the length. German and Russian run 20-30 % longer than English, and the
generation panel is a fixed-width sidebar. If a translation wraps to three lines
where English took one, shorten it rather than widening the layout.

Never hardcode a user-visible string in JSX. If you are adding UI, you are adding
keys in the same commit.
