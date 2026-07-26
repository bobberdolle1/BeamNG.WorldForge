# Quick start / Быстрый старт 🚀

**[English](#english) | [Русский](#russian)**

---

<a name="english"></a>
## 🇬🇧 English

### 1. Get an elevation data source

The quickest option is a **free OpenTopography API key** - registration takes
about a minute:

1. Go to <https://opentopography.org/> and create an account.
2. Open your profile → **myOpenTopo** → request an API key.
3. Copy the key.

> Google Earth Engine also works, but it needs a Google Cloud project, an
> enabled Earth Engine API and a service account. Start with OpenTopography.

### 2. Start the app

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

### 3. Add your key

Open the **Settings** page, paste the OpenTopography key, press **Validate**,
then **Save**. Keys are encrypted before being written to disk.

You can also put it in `backend/.env` instead:

```env
OPENTOPOGRAPHY_API_KEY=your-key-here
```

### 4. Generate a map

1. **Map** page → pick a layer → drag to select a square region.
   Watch the area readout; the maximum is 400 km². Start with 5-20 km².
2. Give the map a name, leave the defaults (30 m DEM, 1024×1024 heightmap).
3. Press **Generate Map**. A typical run takes 30-90 seconds.
4. Download the ZIP.

### 5. Install it

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
vertical scale. Roads, buildings and textures are **not** generated - the level
ships with the default grass material and no objects.

### Troubleshooting

| Symptom | Cause |
|---|---|
| "No elevation data source is available" | No API key configured. Add one on the Settings page. |
| "OpenTopography rejected the API key" | Wrong or inactive key - re-check it in your OpenTopography profile. |
| "Selected area is too large" | Over 400 km². Select a smaller region. |
| "No OpenTopography dataset covers this region" | Region outside dataset coverage (SRTM stops at 60° latitude). Try a lower resolution, which selects a global dataset. |
| Frontend loads but every request fails | Backend not running, or the Vite proxy points at the wrong host. Check <http://localhost:8000/api/health>. |

---

<a name="russian"></a>
## 🇷🇺 Русский

### 1. Получите источник данных о высотах

Проще всего — **бесплатный API-ключ OpenTopography**, регистрация занимает
около минуты:

1. Зайдите на <https://opentopography.org/> и создайте аккаунт.
2. Профиль → **myOpenTopo** → запросите API-ключ.
3. Скопируйте ключ.

> Google Earth Engine тоже работает, но требует проект в Google Cloud,
> включённый Earth Engine API и сервисный аккаунт. Начните с OpenTopography.

### 2. Запустите приложение

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

### 3. Добавьте ключ

Откройте страницу **Settings**, вставьте ключ OpenTopography, нажмите
**Validate**, затем **Save**. Ключи шифруются перед записью на диск.

Либо укажите его в `backend/.env`:

```env
OPENTOPOGRAPHY_API_KEY=ваш-ключ
```

### 4. Сгенерируйте карту

1. Страница **Map** → выберите слой → выделите квадратную область.
   Смотрите на площадь; максимум — 400 км². Начните с 5–20 км².
2. Задайте имя карты, оставьте значения по умолчанию (DEM 30 м, 1024×1024).
3. Нажмите **Generate Map**. Обычно это 30–90 секунд.
4. Скачайте ZIP.

### 5. Установите

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
вертикальном масштабе. Дороги, здания и текстуры **не** генерируются — уровень
идёт с материалом травы по умолчанию и без объектов.

### Если что-то не так

| Симптом | Причина |
|---|---|
| «No elevation data source is available» | Не настроен API-ключ. Добавьте его в Settings. |
| «OpenTopography rejected the API key» | Неверный или неактивный ключ — проверьте в профиле OpenTopography. |
| «Selected area is too large» | Больше 400 км². Выберите область меньше. |
| «No OpenTopography dataset covers this region» | Регион вне покрытия датасета (SRTM заканчивается на 60° широты). Попробуйте меньшее разрешение — тогда выбирается глобальный датасет. |
| Фронтенд открывается, но запросы падают | Не запущен бэкенд или прокси Vite смотрит не туда. Проверьте <http://localhost:8000/api/health>. |
