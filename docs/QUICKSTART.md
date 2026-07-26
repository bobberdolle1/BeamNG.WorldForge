# Quick start / Быстрый старт 🚀

**[English](#english) | [Русский](#russian)**

---

<a name="english"></a>
## 🇬🇧 English

### 1. Start the app

There is nothing to sign up for. The default elevation source, AWS Terrain
Tiles, is anonymous and covers the whole planet at roughly 30 m (10 m over the
continental US).

**Docker (simplest)**

```bash
git clone https://github.com/bobberdolle1/BeamNG.WorldForge
cd BeamNG.WorldForge
docker compose up
```

Open <http://localhost:5173>.

**From source**

```bash
# Terminal 1 - backend
pip install -r backend/requirements.txt
cd backend && uvicorn main:app --reload

# Terminal 2 - frontend
cd frontend && npm ci && npm run dev
```

### 2. Generate a map

1. **Map** page → pick a layer → drag to select a region. The selection is
   square on the ground and the overlay shows its area; the maximum is 400 km².
   Start with 5-20 km².
2. Give the map a name, leave the defaults (30 m DEM, 1024×1024 heightmap).
3. Press **Generate Map**. A typical run takes 30-90 seconds.
4. Download the ZIP.

### 3. Install it

Copy the ZIP into:

| OS | Path |
|---|---|
| Windows | `%USERPROFILE%\Documents\BeamNG.drive\<version>\mods\` |
| macOS | `~/Library/Application Support/BeamNG.drive/<version>/mods/` |
| Linux | `~/.local/share/BeamNG.drive/<version>/mods/` |

Start the game; the level appears under **Freeroam**.

Each archive contains `WORLDFORGE.md` with the terrain's scale values, in case
the heightmap needs importing through the in-game World Editor.

### What you get

Terrain: an accurate heightmap of a real place, at the correct horizontal and
vertical scale. Roads and buildings are placed on it only when AI segmentation
is enabled and Ollama is running; otherwise the level ships with the default
grass material and no objects.

BeamNG loads terrain from a binary `.ter` rather than a PNG. The archive ships
both. The `.ter` follows the community-documented format but has not been
verified in-game - if the level loads empty, import the PNG through the World
Editor using the values in `WORLDFORGE.md`.

### Troubleshooting

| Symptom | Cause |
|---|---|
| "No elevation data source is available" | Nothing reachable. Check your internet connection, or add a provider key in Settings. |
| "AWS Terrain Tiles has no elevation data for this region" | The selection is over open ocean. Pick an area with land. |
| "OpenTopography rejected the API key" | Wrong or inactive key - re-check it in your OpenTopography profile. |
| "Selected area is too large" | Over 400 km². Select a smaller region. |
| "No OpenTopography dataset covers this region" | Region outside dataset coverage (SRTM stops at 60° latitude). Try a lower resolution, which selects a global dataset. |
| Frontend loads but every request fails | Backend not running, or the Vite proxy points at the wrong host. Check <http://localhost:8000/api/health>. |

---

<a name="russian"></a>
## 🇷🇺 Русский

### 1. Запустите приложение

Регистрироваться нигде не нужно. Источник высот по умолчанию, AWS Terrain
Tiles, работает анонимно и покрывает всю планету с разрешением около 30 м
(10 м по континентальным США).

**Docker (проще всего)**

```bash
git clone https://github.com/bobberdolle1/BeamNG.WorldForge
cd BeamNG.WorldForge
docker compose up
```

Откройте <http://localhost:5173>.

**Из исходников**

```bash
# Терминал 1 — бэкенд
pip install -r backend/requirements.txt
cd backend && uvicorn main:app --reload

# Терминал 2 — фронтенд
cd frontend && npm ci && npm run dev
```

### 2. Сгенерируйте карту

1. Страница **Map** → выберите слой → выделите область. Выделение квадратное
   по земле, оверлей показывает площадь; максимум — 400 км². Начните с 5–20 км².
2. Задайте имя карты, оставьте значения по умолчанию (DEM 30 м, 1024×1024).
3. Нажмите **Generate Map**. Обычно это 30–90 секунд.
4. Скачайте ZIP.

### 3. Установите

Скопируйте ZIP в:

| ОС | Путь |
|---|---|
| Windows | `%USERPROFILE%\Documents\BeamNG.drive\<версия>\mods\` |
| macOS | `~/Library/Application Support/BeamNG.drive/<версия>/mods/` |
| Linux | `~/.local/share/BeamNG.drive/<версия>/mods/` |

Запустите игру — уровень появится в разделе **Freeroam**.

В каждом архиве есть `WORLDFORGE.md` со значениями масштаба рельефа — на
случай, если карту высот придётся импортировать через World Editor.

### Что вы получаете

Рельеф: точную карту высот реального места в правильном горизонтальном и
вертикальном масштабе. Дороги и здания ставятся на него только при включённой
AI-сегментации и запущенном Ollama; иначе уровень идёт с материалом травы и без
объектов.

BeamNG грузит рельеф из бинарного `.ter`, а не из PNG. В архиве есть оба. `.ter`
написан по формату из документации сообщества, но в игре не проверен — если
уровень открылся пустым, импортируйте PNG через World Editor со значениями из
`WORLDFORGE.md`.

### Если что-то не так

| Симптом | Причина |
|---|---|
| «No elevation data source is available» | Ничего не доступно. Проверьте интернет или добавьте ключ провайдера в Settings. |
| «AWS Terrain Tiles has no elevation data for this region» | Выделен открытый океан. Выберите область с сушей. |
| «OpenTopography rejected the API key» | Неверный или неактивный ключ — проверьте в профиле OpenTopography. |
| «Selected area is too large» | Больше 400 км². Выберите область меньше. |
| «No OpenTopography dataset covers this region» | Регион вне покрытия датасета (SRTM заканчивается на 60° широты). Попробуйте меньшее разрешение — тогда выбирается глобальный датасет. |
| Фронтенд открывается, но запросы падают | Не запущен бэкенд или прокси Vite смотрит не туда. Проверьте <http://localhost:8000/api/health>. |
