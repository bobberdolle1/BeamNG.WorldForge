# BeamNG.WorldForge 🌍

> **Generate BeamNG.drive terrain from real-world elevation data**
>
> **Генерация рельефа для BeamNG.drive из реальных данных о высотах**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.6.0-blue.svg)](CHANGELOG.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://github.com/bobberdolle1/BeamNG.WorldForge/releases)

**[English](#english) | [Русский](#russian)**

---

<a name="english"></a>
## 🇬🇧 English

Pick a region on a map, and WorldForge downloads real elevation data for it,
turns it into a 16-bit heightmap, and packages it as a BeamNG.drive mod.

### What it actually does

| ✅ Works today | 🚧 Partial / experimental |
|---|---|
| Region selection on an interactive map | AI detection of roads and buildings (needs a local Ollama install) |
| Elevation download from OpenTopography, Sentinel Hub or Earth Engine | Satellite imagery download (needs Sentinel Hub or Azure Maps) |
| Void filling, resampling, 16-bit heightmap generation | JBeam road and building-mesh generation (code exists, not wired into the pipeline) |
| Correct terrain scale derived from the selected region | |
| BeamNG mod archive (`levels/<name>/…`, zipped) | |
| Heightmap preview image and interactive 3D view | |
| Encrypted API key storage with a settings UI | |
| English / Russian interface | |

**What you get** is terrain: an accurate heightmap of a real place, at the right
horizontal and vertical scale, packaged as a level. Roads, buildings, textures
and props are **not** generated - the level ships with the default grass
material and no objects. Each archive contains a `WORLDFORGE.md` with the exact
scale values in case the heightmap needs importing through the in-game World
Editor.

### Requirements

* An elevation data source. The quickest is a **free OpenTopography API key**
  (registration takes about a minute): <https://opentopography.org/>
* For satellite imagery and the optional AI features: a
  [Sentinel Hub](https://www.sentinel-hub.com/) free-tier account, plus
  [Ollama](https://ollama.ai/) running locally.

Without any key configured the app starts and the UI works, but generation fails
with a message telling you which source to configure.

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

1. **Settings** - paste your OpenTopography (or Sentinel Hub) key and press
   Validate. Keys are encrypted with Fernet before being written to disk.
2. **Map** - pick a layer, drag to select a square region. The panel shows the
   area in km²; the maximum is 400 km².
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
**Data:** OpenTopography, Sentinel Hub, Azure Maps, Google Earth Engine

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
pytest                    # backend test suite
ruff check backend        # backend lint

cd frontend
npm run lint
npm run typecheck
npm run build
```

### License

MIT - see [LICENSE](LICENSE).

### Acknowledgments

OpenTopography, Copernicus / ESA, Sentinel Hub, Google Earth Engine, Ollama,
and the BeamNG.drive community.

---

<a name="russian"></a>
## 🇷🇺 Русский

Выберите регион на карте — WorldForge скачает для него реальные данные о
высотах, превратит их в 16-битную карту высот и упакует в мод для
BeamNG.drive.

### Что реально работает

| ✅ Работает сейчас | 🚧 Частично / экспериментально |
|---|---|
| Выбор региона на интерактивной карте | AI-распознавание дорог и зданий (нужен локальный Ollama) |
| Загрузка высот из OpenTopography, Sentinel Hub или Earth Engine | Загрузка спутниковых снимков (нужен Sentinel Hub или Azure Maps) |
| Заполнение пропусков, ресемплинг, 16-битная карта высот | Генерация JBeam-дорог и мешей зданий (код есть, но в пайплайн не подключён) |
| Корректный масштаб рельефа по выбранной области | |
| Архив мода BeamNG (`levels/<имя>/…`) | |
| Превью карты высот и интерактивный 3D-просмотр | |
| Зашифрованное хранение API-ключей + UI настроек | |
| Английский / русский интерфейс | |

**Вы получаете рельеф**: точную карту высот реального места, в правильном
горизонтальном и вертикальном масштабе, упакованную как уровень. Дороги,
здания, текстуры и объекты **не** генерируются — уровень идёт с материалом
травы по умолчанию и без объектов. В каждом архиве лежит `WORLDFORGE.md` с
точными значениями масштаба на случай, если карту высот придётся импортировать
через встроенный World Editor.

### Требования

* Источник данных о высотах. Проще всего — **бесплатный API-ключ
  OpenTopography** (регистрация занимает минуту): <https://opentopography.org/>
* Для спутниковых снимков и AI-функций: аккаунт
  [Sentinel Hub](https://www.sentinel-hub.com/) (бесплатный тариф) и локально
  запущенный [Ollama](https://ollama.ai/).

Без ключей приложение запустится и интерфейс будет работать, но генерация
завершится с сообщением о том, какой источник нужно настроить.

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

1. **Settings** — вставьте ключ OpenTopography (или Sentinel Hub) и нажмите
   Validate. Ключи шифруются Fernet перед записью на диск.
2. **Map** — выберите слой и выделите квадратную область. Панель показывает
   площадь в км²; максимум — 400 км².
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
**Данные:** OpenTopography, Sentinel Hub, Azure Maps, Google Earth Engine

### Безопасность

* У API **нет аутентификации**. Держите его на `127.0.0.1` (по умолчанию), если
  сознательно не выставляете наружу в доверенной сети.
* Ключи шифруются Fernet-ключом из `backend/config/settings.key`. Этот файл в
  `.gitignore` — его нельзя коммитить и нельзя класть в релизы.
* Имена карт валидируются и приводятся к слагу до любого обращения к ФС.

### Разработка

```bash
pip install -r backend/requirements-dev.txt
pytest                    # тесты бэкенда
ruff check backend        # линтер бэкенда

cd frontend
npm run lint
npm run typecheck
npm run build
```

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
│       ├── data_sources/     # OpenTopography, Sentinel Hub, Azure, GEE
│       ├── terrain/          # DEM cleaning, heightmap generation
│       ├── export/           # BeamNG mod packaging
│       ├── ai_segmentation/  # Optional: Ollama vision segmentation
│       └── vector_extraction/# Optional: masks -> GeoJSON
├── frontend/src/
│   ├── components/      # UI + 3D visualisation
│   ├── hooks/           # Job polling
│   ├── lib/             # Stage table shared with the backend
│   └── services/        # API client
├── tests/               # Backend test suite
└── docs/                # Documentation
```

---

Made with ❤️ for the BeamNG.drive community
Сделано с ❤️ для сообщества BeamNG.drive
