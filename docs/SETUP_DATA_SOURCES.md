# Data sources

**[English](#english) | [Русский](#russian)**

---

<a name="english"></a>
## 🇬🇧 English

### At a glance

| Source | Key needed | Elevation | Imagery | Notes |
|---|---|---|---|---|
| **AWS Terrain Tiles** | **No** | ✅ ~30 m global, ~10 m in the continental US | — | The default. Nothing to configure. |
| OpenTopography | Yes, free | ✅ Copernicus, SRTM, NASADEM, ALOS | — | Choice of DEM products; better than the composite in some regions |
| Sentinel Hub | Yes, free tier | ✅ Copernicus GLO-30 | ✅ Sentinel-2, 10 m | The only free source that also supplies imagery |
| Azure Maps | Yes, free tier | — | ✅ Aerial tiles | Imagery only |
| Google Earth Engine | Yes, service account | ✅ | ✅ | Powerful, and by far the most setup |
| ~~Bing Maps~~ | — | — | — | **Retired by Microsoft.** Use Azure Maps. |

Elevation is all you need for terrain. Imagery is only used by the optional AI
segmentation, which additionally needs Ollama.

### Which one should I use?

**Just generating terrain?** Nothing. AWS Terrain Tiles is already the default
and needs no account.

**Terrain looks coarse for your area?** Add an OpenTopography key and pick a
finer product; some national datasets beat the global composite.

**Want AI road and building detection?** You need imagery: Sentinel Hub (free)
or Azure Maps, plus a local Ollama install.

---

### AWS Terrain Tiles - the default

Anonymous public GeoTIFF tiles hosted on AWS Open Data, a composite of SRTM,
3DEP and several national datasets.

Nothing to set up. Verify it is reachable:

```bash
curl -sI https://s3.amazonaws.com/elevation-tiles-prod/geotiff/0/0/0.tif | head -1
```

Attribution: the dataset mixes public-domain and CC-BY sources. See the
[Tilezen attribution notes](https://github.com/tilezen/joerd/blob/master/docs/attribution.md)
if you redistribute derived maps.

Limits: resolution varies by region, and there is no data over open ocean -
selecting a sea area returns a clear error rather than a flat map.

---

### OpenTopography

Elevation only, with a choice of DEM products: Copernicus 30/90 m, SRTM,
NASADEM, ALOS World 3D.

> An API key is **required**. Older documentation said the global datasets
> worked anonymously; that stopped being true in 2022.

1. Register at <https://opentopography.org/>
2. Profile → **myOpenTopo** → request an API key
3. Paste it into **Settings → OpenTopography API Key**, press **Verify**, then
   **Save** — or set `OPENTOPOGRAPHY_API_KEY` in `backend/.env`

Coverage is not uniform: SRTM stops at 60° latitude and Copernicus has voids
over some water. The client tries progressively coarser products when one has
no data for your region, rather than failing outright.

---

### Sentinel Hub

The only free source that provides both elevation and imagery. Free tier:
30,000 processing units per month, which is far more than casual use needs.

1. Register at <https://www.sentinel-hub.com/>
2. Dashboard → **User settings** → **OAuth clients** → create a new client
3. Copy the **Client ID** and **Client Secret** — the secret is shown once
4. Enter **both** in Settings and press **Verify**

Both halves are required. Verification performs a real OAuth2
client-credentials token exchange, so a green result means the pair genuinely
works.

> Before 1.6.0 the check sent the client ID as a bearer token, which the API
> always rejects — valid credentials were reported invalid every time. If you
> gave up on Sentinel Hub because of that, try again.

---

### Azure Maps

Aerial imagery only; no elevation. Free S0 tier: 1,000 transactions/day.

1. Create an Azure account and an Azure Maps resource
2. Copy a subscription key from **Authentication**
3. Enter it in Settings and press **Verify**

Pair it with AWS Terrain or OpenTopography for the elevation half.

---

### Google Earth Engine

Both elevation and imagery, with deep archives — and by far the most setup. Only
worth it if you already use Earth Engine.

1. Create a Google Cloud project and enable the Earth Engine API
2. Register the project at <https://code.earthengine.google.com/register>
3. Create a service account and download its JSON key
4. Save it as `backend/config/gee-key.json`
5. Set `GEE_PROJECT_ID` in `backend/.env`

Unlike the others this cannot be configured from the UI: it needs a key file on
the server.

---

### Bing Maps — retired

Microsoft has retired the Bing Maps APIs. The client remains only so existing
keys keep working; do not start here. Use Azure Maps.

---

### How a source gets chosen

With `data_source: "auto"` (the default) the server takes the first configured
and reachable source in this order:

**Elevation:** AWS Terrain → OpenTopography → Sentinel Hub → Earth Engine
**Imagery:** Sentinel Hub → Azure Maps → Earth Engine

AWS is first because it always works. Pick a specific source in the generation
panel to override.

`GET /api/data-sources` reports what is available and why anything is not.

### Where keys are stored

Keys entered in the UI are encrypted with Fernet into
`backend/config/user_settings.enc`. The key that decrypts it is
`backend/config/settings.key` — git-ignored, and never shipped in a release.

Environment variables override stored values, which is the right way to inject
credentials into a container.

> Versions up to 1.5.1 committed `settings.key` to the repository. If you used
> one of those, rotate every key you entered.

---

<a name="russian"></a>
## 🇷🇺 Русский

### Кратко

| Источник | Нужен ключ | Высоты | Снимки | Примечания |
|---|---|---|---|---|
| **AWS Terrain Tiles** | **Нет** | ✅ ~30 м по миру, ~10 м по США | — | По умолчанию. Настраивать нечего. |
| OpenTopography | Да, бесплатный | ✅ Copernicus, SRTM, NASADEM, ALOS | — | Выбор наборов DEM; местами лучше глобальной сборки |
| Sentinel Hub | Да, бесплатный тариф | ✅ Copernicus GLO-30 | ✅ Sentinel-2, 10 м | Единственный бесплатный источник со снимками |
| Azure Maps | Да, бесплатный тариф | — | ✅ Аэрофотоснимки | Только снимки |
| Google Earth Engine | Да, сервисный аккаунт | ✅ | ✅ | Мощно и сложнее всего в настройке |
| ~~Bing Maps~~ | — | — | — | **Закрыт Microsoft.** Используйте Azure Maps. |

Для рельефа достаточно высот. Снимки нужны только опциональной AI-сегментации,
которой вдобавок требуется Ollama.

### Что выбрать

**Просто нужен рельеф?** Ничего. AWS Terrain Tiles уже стоит по умолчанию и не
требует аккаунта.

**Рельеф выглядит грубо в вашем регионе?** Добавьте ключ OpenTopography и
выберите более точный набор — местные датасеты иногда лучше глобальной сборки.

**Нужно AI-распознавание дорог и зданий?** Понадобятся снимки: Sentinel Hub
(бесплатно) или Azure Maps, плюс локальный Ollama.

---

### AWS Terrain Tiles — по умолчанию

Анонимные публичные GeoTIFF-тайлы на AWS Open Data: сборка из SRTM, 3DEP и
нескольких национальных наборов.

Настраивать нечего. Проверить доступность:

```bash
curl -sI https://s3.amazonaws.com/elevation-tiles-prod/geotiff/0/0/0.tif | head -1
```

Атрибуция: набор смешивает public-domain и CC-BY источники, см.
[примечания Tilezen](https://github.com/tilezen/joerd/blob/master/docs/attribution.md),
если распространяете производные карты.

Ограничения: разрешение зависит от региона, над открытым океаном данных нет —
там вы получите понятную ошибку, а не плоскую карту.

---

### OpenTopography

Только высоты, зато с выбором наборов: Copernicus 30/90 м, SRTM, NASADEM,
ALOS World 3D.

> API-ключ **обязателен**. Старая документация утверждала, что глобальные
> датасеты работают анонимно — это перестало быть правдой в 2022 году.

1. Зарегистрируйтесь на <https://opentopography.org/>
2. Профиль → **myOpenTopo** → запросите API-ключ
3. Вставьте в **Settings → OpenTopography API Key**, нажмите **Verify**, затем
   **Save** — или задайте `OPENTOPOGRAPHY_API_KEY` в `backend/.env`

Покрытие неравномерное: SRTM заканчивается на 60° широты, у Copernicus есть
пропуски над водой. Клиент перебирает более грубые наборы, если у выбранного
нет данных на регион, вместо того чтобы просто упасть.

---

### Sentinel Hub

Единственный бесплатный источник, дающий и высоты, и снимки. Бесплатный тариф —
30 000 единиц обработки в месяц, для обычного использования с большим запасом.

1. Зарегистрируйтесь на <https://www.sentinel-hub.com/>
2. Dashboard → **User settings** → **OAuth clients** → создайте клиента
3. Скопируйте **Client ID** и **Client Secret** — секрет показывается один раз
4. Введите **оба** в Settings и нажмите **Verify**

Нужны обе половины. Проверка выполняет настоящий обмен OAuth2
client-credentials, так что зелёный результат означает рабочую пару.

> До версии 1.6.0 проверка отправляла Client ID как bearer-токен, который API
> всегда отвергает — валидные ключи неизменно показывались невалидными. Если вы
> из-за этого отказались от Sentinel Hub, попробуйте снова.

---

### Azure Maps

Только аэрофотоснимки, высот нет. Бесплатный тариф S0: 1000 транзакций в день.

1. Создайте аккаунт Azure и ресурс Azure Maps
2. Скопируйте ключ подписки из раздела **Authentication**
3. Введите в Settings и нажмите **Verify**

Сочетайте с AWS Terrain или OpenTopography для высот.

---

### Google Earth Engine

И высоты, и снимки, и глубокие архивы — и самая сложная настройка. Имеет смысл,
только если вы уже работаете с Earth Engine.

1. Создайте проект в Google Cloud и включите Earth Engine API
2. Зарегистрируйте проект на <https://code.earthengine.google.com/register>
3. Создайте сервисный аккаунт и скачайте JSON-ключ
4. Сохраните как `backend/config/gee-key.json`
5. Задайте `GEE_PROJECT_ID` в `backend/.env`

В отличие от остальных, через UI не настраивается: нужен файл ключа на сервере.

---

### Bing Maps — закрыт

Microsoft закрыл API Bing Maps. Клиент оставлен только чтобы продолжали
работать существующие ключи; начинать с него не стоит. Используйте Azure Maps.

---

### Как выбирается источник

При `data_source: "auto"` (по умолчанию) сервер берёт первый настроенный и
доступный источник в таком порядке:

**Высоты:** AWS Terrain → OpenTopography → Sentinel Hub → Earth Engine
**Снимки:** Sentinel Hub → Azure Maps → Earth Engine

AWS первый, потому что работает всегда. Конкретный источник можно выбрать в
панели генерации.

`GET /api/data-sources` показывает, что доступно и почему остальное — нет.

### Где хранятся ключи

Введённые через UI ключи шифруются Fernet в
`backend/config/user_settings.enc`. Расшифровывает их
`backend/config/settings.key` — файл в `.gitignore`, в релизы не попадает.

Переменные окружения имеют приоритет над сохранёнными значениями — это
правильный способ передавать credentials в контейнер.

> Версии до 1.5.1 включительно коммитили `settings.key` в репозиторий. Если вы
> пользовались одной из них, перевыпустите все введённые ключи.
