# BeamNG.WorldForge 🌍

> **Generate BeamNG.drive terrain from real-world elevation data**
>
> **Генерация рельефа для BeamNG.drive из реальных данных о высотах**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.8.0-blue.svg)](CHANGELOG.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://github.com/bobberdolle1/BeamNG.WorldForge/releases)

**[English](#english) | [Русский](#russian)**

---

<a name="english"></a>
## 🇬🇧 English

Pick a region on a map, and WorldForge downloads real elevation data for it,
turns it into a 16-bit heightmap, and packages it as a BeamNG.drive mod.

**No API key required.** The default elevation source is anonymous, so a fresh
clone generates its first map without registering anywhere.

### What it actually does

| ✅ Works today | 🚧 Partial / experimental |
|---|---|
| Keyless elevation from AWS Terrain Tiles | AI detection of roads and buildings (needs a local Ollama install) |
| Optional OpenTopography / Sentinel Hub / Earth Engine sources | Satellite imagery download (needs Sentinel Hub or Azure Maps) |
| Void filling, resampling, 16-bit heightmap generation | Binary `.ter` terrain (community-documented format, not verified in-game) |
| True-square region selection and terrain scale | |
| Detected roads exported as BeamNG decal roads | |
| Detected buildings extruded to COLLADA and placed on the terrain | |
| BeamNG mod archive (`levels/<name>/…`, zipped) | |
| Heightmap preview image and interactive 3D view | |
| Encrypted API key storage with a settings UI | |
| English / Russian interface | |

**What you get** is terrain: an accurate heightmap of a real place, at the right
horizontal and vertical scale, packaged as a level. With AI segmentation on
(and Ollama running) detected roads and buildings are placed on it too;
without it the level ships with the default grass material and no objects.

One caveat worth knowing up front: BeamNG loads terrain from a binary `.ter`
file, not from a PNG. The archive contains both. The `.ter` is written to the
format documented by the modding community but has **not** been verified by
loading a generated level in the game - if it is rejected, importing the PNG
through the in-game World Editor always works, and each archive ships a
`WORLDFORGE.md` with the exact scale values for that.

### Requirements

Nothing, to generate terrain. The default source - [AWS Terrain
Tiles](https://registry.opendata.aws/terrain-tiles/) - is anonymous and global,
roughly 30 m resolution worldwide and 10 m over the continental United States.

Optional, for better data or extra features:

* [OpenTopography](https://opentopography.org/) - free key, alternative DEM products
* [Sentinel Hub](https://www.sentinel-hub.com/) - free tier, adds satellite imagery
* [Ollama](https://ollama.ai/) - local install, enables road/building detection

### Quick start

**Docker (all platforms)**

```bash
git clone https://github.com/bobberdolle1/BeamNG.WorldForge
cd BeamNG.WorldForge
docker compose up
# Open http://localhost:5173, then add your API key on the Settings page
```

**From source**

```bash
# Backend
pip install -r backend/requirements.txt
cd backend && uvicorn main:app --reload      # http://localhost:8000

# Frontend, in a second terminal
cd frontend && npm ci && npm run dev         # http://localhost:5173
```

**Standalone executable**

```bash
pip install -r backend/requirements-dev.txt
python build.py
./dist/BeamNG-WorldForge/BeamNG-WorldForge   # opens http://localhost:8000
```

Prebuilt binaries for Windows, macOS and Linux are attached to each
[release](https://github.com/bobberdolle1/BeamNG.WorldForge/releases).

### Using it

1. **Map** - pick a layer, drag to select a region. The selection is square on
   the ground, and the overlay shows its size in km²; the maximum is 400 km².
2. **Settings** (optional) - add an OpenTopography or Sentinel Hub key and
   press Verify. Keys are encrypted with Fernet before being written to disk.
3. **Configure** - name the map, choose a DEM resolution (10-100 m) and a
   heightmap size (512-4096, power of two).
4. **Generate** - progress is reported per stage. Typical run: 30-90 seconds.
5. **Download** the ZIP and drop it in
   `Documents/BeamNG.drive/<version>/mods/`.

### How generation works

```
Select region  →  Download DEM  →  Fill voids  →  Resample  →  Normalise  →  Package
  (Leaflet)       (provider API)   (nearest       (to N×N)     (to 16-bit)   (ZIP mod)
                                    valid sample)
```

Elevation values are normalised across the full 16-bit range; the real vertical
span is carried in `main.level.json` as `minHeight` + `heightScale`, and the
horizontal scale (`squareSize`) is computed from the selected region's true
ground size.

### Technology

**Frontend:** React 18, TypeScript, Vite, React Leaflet, Three.js, i18next, Tailwind
**Backend:** Python 3.11+, FastAPI, NumPy, SciPy, rasterio, Pillow, Pydantic
**Data:** AWS Terrain Tiles (default, keyless), OpenTopography, Sentinel Hub, Azure Maps, Google Earth Engine

### Documentation

| Document | Contents |
|---|---|
| [Setup](docs/SETUP.md) | Installation and configuration |
| [Data sources](docs/SETUP_DATA_SOURCES.md) | Getting API keys |
| [Architecture](docs/ARCHITECTURE.md) | How the code is organised |
| [API reference](docs/API.md) | REST endpoints |
| [UI guide](docs/UI_GUIDE.md) | Interface walkthrough |
| [Localization](docs/LOCALIZATION.md) | Adding a language |
| [Contributing](CONTRIBUTING.md) | Development workflow |
| [Changelog](CHANGELOG.md) | Version history |

### Security notes

* The API has **no authentication**. Bind it to `127.0.0.1` (the default) unless
  you are deliberately exposing it on a trusted network.
* API keys are encrypted at rest with a Fernet key stored in
  `backend/config/settings.key`. That file is git-ignored and must never be
  committed or shipped in a release.
* Map names are validated and slugified before touching the filesystem.

### Development

```bash
pip install -r backend/requirements-dev.txt
pytest                    # backend suite, incl. the frontend/backend contract test
ruff check backend        # backend lint

cd frontend
npm run lint
npm run typecheck
npm test                  # Vitest suite
npm run build
```

`backend/static/` is generated, not committed: `python build.py` copies
`frontend/dist` into it so the API can serve the UI from a single process. When
running the two dev servers separately you do not need it.

### License

MIT - see [LICENSE](LICENSE).

### Acknowledgments

AWS Open Data and the Tilezen/Mapzen Terrain Tiles project, OpenTopography,
Copernicus / ESA, Sentinel Hub, Google Earth Engine, Ollama, and the
BeamNG.drive community.

Terrain Tiles is a composite of public-domain and CC-BY sources; see its
[attribution notes](https://github.com/tilezen/joerd/blob/master/docs/attribution.md).

---

<a name="russian"></a>
## 🇷🇺 Русский

Выберите регион на карте — WorldForge скачает для него реальные данные о
высотах, превратит их в 16-битную карту высот и упакует в мод для
BeamNG.drive.

**API-ключ не нужен.** Источник высот по умолчанию работает анонимно, поэтому
свежий клон делает первую карту без регистрации где-либо.

### Что реально работает

| ✅ Работает сейчас | 🚧 Частично / экспериментально |
|---|---|
| Высоты из AWS Terrain Tiles без ключа | AI-распознавание дорог и зданий (нужен локальный Ollama) |
| Опционально OpenTopography / Sentinel Hub / Earth Engine | Загрузка спутниковых снимков (нужен Sentinel Hub или Azure Maps) |
| Заполнение пропусков, ресемплинг, 16-битная карта высот | Бинарный `.ter` (формат по документации сообщества, в игре не проверен) |
| Честно квадратное выделение и масштаб рельефа | |
| Найденные дороги как decal-дороги BeamNG | |
| Найденные здания — экструзия в COLLADA и посадка на рельеф | |
| Архив мода BeamNG (`levels/<имя>/…`) | |
| Превью карты высот и интерактивный 3D-просмотр | |
| Зашифрованное хранение API-ключей + UI настроек | |
| Английский / русский интерфейс | |

**Вы получаете рельеф**: точную карту высот реального места, в правильном
горизонтальном и вертикальном масштабе, упакованную как уровень. С включённой
AI-сегментацией (и запущенным Ollama) на него ставятся найденные дороги и
здания; без неё уровень идёт с материалом травы и без объектов.

Важная оговорка: BeamNG грузит рельеф из бинарного `.ter`, а не из PNG. В
архиве есть оба файла. `.ter` пишется по формату из документации сообщества, но
**не проверен** загрузкой уровня в игре — если он не подойдёт, импорт PNG через
встроенный World Editor работает всегда, и в каждом архиве лежит
`WORLDFORGE.md` с нужными значениями масштаба.

### Требования

Для генерации рельефа — ничего. Источник по умолчанию, [AWS Terrain
Tiles](https://registry.opendata.aws/terrain-tiles/), работает анонимно и
глобально: около 30 м по миру и 10 м по континентальным США.

Опционально, ради качества данных или дополнительных функций:

* [OpenTopography](https://opentopography.org/) — бесплатный ключ, другие наборы DEM
* [Sentinel Hub](https://www.sentinel-hub.com/) — бесплатный тариф, добавляет спутниковые снимки
* [Ollama](https://ollama.ai/) — локально, включает распознавание дорог и зданий

### Быстрый старт

**Docker (любая ОС)**

```bash
git clone https://github.com/bobberdolle1/BeamNG.WorldForge
cd BeamNG.WorldForge
docker compose up
# Откройте http://localhost:5173 и добавьте ключ на странице Settings
```

**Из исходников**

```bash
# Бэкенд
pip install -r backend/requirements.txt
cd backend && uvicorn main:app --reload      # http://localhost:8000

# Фронтенд, во втором терминале
cd frontend && npm ci && npm run dev         # http://localhost:5173
```

**Standalone-приложение**

```bash
pip install -r backend/requirements-dev.txt
python build.py
./dist/BeamNG-WorldForge/BeamNG-WorldForge   # откроет http://localhost:8000
```

Готовые сборки для Windows, macOS и Linux приложены к каждому
[релизу](https://github.com/bobberdolle1/BeamNG.WorldForge/releases).

### Как пользоваться

1. **Map** — выберите слой и выделите область. Выделение квадратное по земле,
   оверлей показывает площадь в км²; максимум — 400 км².
2. **Settings** (опционально) — добавьте ключ OpenTopography или Sentinel Hub и
   нажмите Verify. Ключи шифруются Fernet перед записью на диск.
3. **Configure** — задайте имя карты, разрешение DEM (10–100 м) и размер карты
   высот (512–4096, степень двойки).
4. **Generate** — прогресс показывается по этапам. Обычно 30–90 секунд.
5. **Скачайте** ZIP и положите в
   `Documents/BeamNG.drive/<версия>/mods/`.

### Как устроена генерация

```
Выбор региона →  Загрузка DEM  → Заполнение → Ресемплинг → Нормализация → Упаковка
  (Leaflet)      (API источника)   пропусков    (в N×N)     (в 16 бит)     (ZIP-мод)
```

Высоты нормализуются на весь 16-битный диапазон; реальный вертикальный размах
передаётся в `main.level.json` через `minHeight` и `heightScale`, а
горизонтальный масштаб (`squareSize`) вычисляется из настоящего размера
выбранной области на местности.

### Технологии

**Фронтенд:** React 18, TypeScript, Vite, React Leaflet, Three.js, i18next, Tailwind
**Бэкенд:** Python 3.11+, FastAPI, NumPy, SciPy, rasterio, Pillow, Pydantic
**Данные:** AWS Terrain Tiles (по умолчанию, без ключа), OpenTopography, Sentinel Hub, Azure Maps, Google Earth Engine

### Безопасность

* У API **нет аутентификации**. Держите его на `127.0.0.1` (по умолчанию), если
  сознательно не выставляете наружу в доверенной сети.
* Ключи шифруются Fernet-ключом из `backend/config/settings.key`. Этот файл в
  `.gitignore` — его нельзя коммитить и нельзя класть в релизы.
* Имена карт валидируются и приводятся к слагу до любого обращения к ФС.

### Разработка

```bash
pip install -r backend/requirements-dev.txt
pytest                    # тесты бэкенда, включая контрактный тест с фронтендом
ruff check backend        # линтер бэкенда

cd frontend
npm run lint
npm run typecheck
npm test                  # тесты Vitest
npm run build
```

`backend/static/` генерируется, а не коммитится: `python build.py` копирует туда
`frontend/dist`, чтобы API мог отдавать интерфейс одним процессом. При запуске
двух dev-серверов по отдельности он не нужен.

### Лицензия

MIT — см. [LICENSE](LICENSE).

---

## 🏗️ Project layout

```
BeamNG.WorldForge/
├── backend/
│   ├── core/            # Config, logging, path safety, geo maths
│   ├── api/routes/      # REST endpoints
│   ├── models/          # Pydantic request/response models
│   └── services/
│       ├── pipeline.py       # Generation orchestration
│       ├── jobs.py           # Job registry with TTL cleanup
│       ├── data_sources/     # AWS Terrain, OpenTopography, Sentinel Hub, Azure, GEE
│       ├── terrain/          # DEM cleaning, heightmap generation
│       ├── export/           # BeamNG mod packaging + binary .ter writer
│       ├── beamng_integration/ # Roads, buildings and meshes from vectors
│       ├── ai_segmentation/  # Optional: Ollama vision segmentation
│       └── vector_extraction/# Optional: masks -> GeoJSON
├── frontend/src/
│   ├── components/      # UI + 3D visualisation
│   ├── hooks/           # Job polling
│   ├── lib/             # Stage table shared with the backend
│   └── services/        # API client
├── tests/               # Backend suite + frontend/backend contract test
└── docs/                # Documentation
```

---

Made with ❤️ for the BeamNG.drive community
Сделано с ❤️ для сообщества BeamNG.drive
