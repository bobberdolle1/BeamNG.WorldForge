# Настройка источников данных - BeamNG.WorldForge

## 📖 Обзор

BeamNG.WorldForge поддерживает несколько источников геоданных с разными уровнями настройки:

| Источник | Бесплатно | Требует регистрации | Качество | Функции |
|----------|-----------|---------------------|----------|---------|
| **OpenTopography** | ✅ | ❌ (опц. для больше квот) | ⭐⭐⭐ | DEM только |
| **Sentinel Hub** | ✅ | ✅ | ⭐⭐⭐⭐ | DEM + Спутниковые снимки |
| **Google Earth Engine** | ✅ | ✅ (сложная настройка) | ⭐⭐⭐⭐⭐ | Все + Архивы |

---

## 🎯 Рекомендации

**Для начинающих:**
- Начните с **OpenTopography** (работает без настройки)
- Или зарегистрируйтесь в **Sentinel Hub** (10 минут настройки, отличное качество)

**Для продвинутых:**
- Используйте **Google Earth Engine** если нужны расширенные функции и исторические данные

---

## 1️⃣ OpenTopography (Самый простой)

### ✅ Преимущества
- Работает БЕЗ регистрации
- Высококачественные DEM данные (SRTM, ASTER, ALOS, Copernicus)
- Бесплатно с ограниченной квотой

### ⚠️ Ограничения
- Только DEM (нет спутниковых снимков RGB)
- Ограниченная квота без API ключа

### 🔧 Настройка

#### Без API ключа (базовый режим):
Ничего не требуется! Просто запустите приложение и выберите "OpenTopography" в качестве источника данных.

#### С API ключом (рекомендуется для частого использования):

1. Зарегистрируйтесь на [OpenTopography.org](https://opentopography.org/)
2. Перейдите в [My Account > Request API Key](https://portal.opentopography.org/requestService)
3. Заполните форму (обычно одобряется мгновенно)
4. Скопируйте полученный API ключ

5. Добавьте в `backend/.env`:
```env
OPENTOPOGRAPHY_API_KEY=your_api_key_here
```

**Готово!** Теперь у вас увеличенная квота для OpenTopography.

---

## 2️⃣ Sentinel Hub (Рекомендуется)

### ✅ Преимущества
- **Бесплатный тариф**: 30,000 processing units/месяц (достаточно для 50+ карт)
- Спутниковые снимки Sentinel-2 (10m RGB)
- Copernicus DEM (30m elevation)
- Отличное качество и скорость

### ⚠️ Ограничения
- Требует регистрацию (бесплатно, 5-10 минут)
- OAuth2 аутентификация (немного сложнее)

### 🔧 Настройка

#### Шаг 1: Создание аккаунта

1. Перейдите на [Sentinel Hub](https://www.sentinel-hub.com/)
2. Нажмите "Sign Up" в правом верхнем углу
3. Зарегистрируйтесь (можно через GitHub/Google)
4. Подтвердите email

#### Шаг 2: Создание OAuth Client

1. Войдите в [Dashboard](https://apps.sentinel-hub.com/dashboard/)
2. Перейдите в **"User Settings" > "OAuth clients"**
3. Нажмите **"+ New OAuth Client"**
4. Заполните форму:
   - **Name**: `BeamNG WorldForge`
   - **Client Type**: `Confidential`
   - **Grant Types**: выберите `Client Credentials`
5. Нажмите **"Create"**

#### Шаг 3: Получение credentials

После создания вы увидите:
- **Client ID** (например: `1234abcd-5678-efgh-90ij-klmnopqrstuv`)
- **Client Secret** (показывается только один раз!)

⚠️ **Важно:** Скопируйте Client Secret немедленно! Он показывается только один раз.

#### Шаг 4: Добавление в конфигурацию

Добавьте в `backend/.env`:
```env
SENTINEL_HUB_CLIENT_ID=your_client_id_here
SENTINEL_HUB_CLIENT_SECRET=your_client_secret_here
```

#### Шаг 5: Проверка

Запустите backend и проверьте доступность источника:
```bash
curl http://localhost:8000/api/data-sources
```

В ответе должен быть:
```json
{
  "id": "sentinel_hub",
  "name": "Sentinel Hub",
  "available": true,
  "recommended": true
}
```

**Готово!** Sentinel Hub настроен и готов к использованию.

### 💰 О квотах

Бесплатный тариф включает:
- **30,000 processing units** в месяц
- **1 processing unit** ≈ одно API обращение

Типичная карта 3×3 км использует:
- ~100 PU для DEM (30m)
- ~200 PU для RGB снимка (10m)
- **Итого: ~300 PU на карту = ~100 карт в месяц**

Проверить использование: [Dashboard > Usage](https://apps.sentinel-hub.com/dashboard/#/usage)

---

## 3️⃣ Google Earth Engine (Опционально)

### ✅ Преимущества
- Огромный архив спутниковых данных (с 1970-х годов)
- Множество датасетов (Landsat, MODIS, etc.)
- Мощные инструменты обработки

### ⚠️ Ограничения
- **Сложная настройка** (требует Google Cloud account)
- Требует создания Service Account
- Более ограничительные квоты для бесплатных аккаунтов

### 🔧 Настройка

#### Шаг 1: Google Cloud Project

1. Перейдите на [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Включите **Earth Engine API**:
   - "APIs & Services" > "Library"
   - Найдите "Earth Engine API"
   - Нажмите "Enable"

#### Шаг 2: Регистрация в Earth Engine

1. Перейдите на [Earth Engine](https://earthengine.google.com/)
2. Нажмите "Sign Up"
3. Выберите "Register a Noncommercial or Commercial Cloud project"
4. Выберите ваш GCP проект
5. Заполните форму и дождитесь одобрения (обычно несколько минут)

#### Шаг 3: Service Account

1. В Google Cloud Console: "IAM & Admin" > "Service Accounts"
2. Нажмите "Create Service Account"
3. Имя: `beamng-worldforge`
4. Роль: **Earth Engine Resource Admin**
5. Нажмите "Create and Continue" > "Done"

#### Шаг 4: JSON ключ

1. Найдите созданный Service Account в списке
2. Нажмите на него > вкладка "Keys"
3. "Add Key" > "Create new key"
4. Формат: **JSON**
5. Скачайте файл

#### Шаг 5: Размещение ключа

Поместите JSON-файл в:
```
backend/config/gee-key.json
```

#### Шаг 6: Конфигурация

Добавьте в `backend/.env`:
```env
GEE_SERVICE_ACCOUNT_KEY=config/gee-key.json
GEE_PROJECT_ID=your-gcp-project-id
```

Замените `your-gcp-project-id` на ID проекта из Google Cloud Console.

**Готово!** Google Earth Engine настроен.

---

## 🔄 Переключение между источниками

### В UI (веб-интерфейсе):

1. Откройте приложение
2. В панели генерации найдите **"Data Source"**
3. Выберите:
   - 🎯 **Auto** - автоматический выбор лучшего доступного
   - ⭐ **Sentinel Hub** - рекомендуется (если настроен)
   - ✅ **OpenTopography** - работает всегда
   - ⚙️ **Google Earth Engine** - если настроен

### Через API:

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_map",
    "bbox": {...},
    "data_source": "sentinel_hub"
  }'
```

### Программно (в коде):

```python
from services.data_sources import DataSourceFactory, DataSourceType

# Automatic selection
source = DataSourceFactory.get_default_source()

# Manual selection
source = DataSourceFactory.create(DataSourceType.SENTINEL_HUB)

# Check availability
available = source.is_available()
```

---

## 🧪 Тестирование источников

### Проверка доступности всех источников:

```bash
curl http://localhost:8000/api/data-sources
```

Ответ покажет статус каждого источника:
```json
{
  "sources": [
    {
      "id": "sentinel_hub",
      "name": "Sentinel Hub",
      "available": true,
      "requires_setup": true,
      "recommended": true
    },
    {
      "id": "opentopography",
      "name": "OpenTopography",
      "available": true,
      "requires_setup": false
    },
    {
      "id": "google_earth_engine",
      "name": "Google Earth Engine",
      "available": false,
      "requires_setup": true
    }
  ],
  "default": "sentinel_hub"
}
```

### Тестирование конкретного источника:

```python
# В Python консоли или Jupyter
from services.data_sources import DataSourceFactory, DataSourceType

# Test Sentinel Hub
sentinel = DataSourceFactory.create(DataSourceType.SENTINEL_HUB)
print(f"Available: {sentinel.is_available()}")
print(f"Requires setup: {sentinel.requires_setup()}")

# Try to fetch data
bbox = [-122.42, 37.77, -122.40, 37.79]  # San Francisco
dem_data, metadata = sentinel.get_dem_data(bbox, resolution=30)
print(f"DEM shape: {dem_data.shape}")
```

---

## 🐛 Устранение проблем

### Sentinel Hub: "401 Unauthorized"

**Причина:** Неверные credentials

**Решение:**
1. Проверьте Client ID и Secret в `.env`
2. Убедитесь, что OAuth client создан как "Confidential"
3. Проверьте, что Grant Type = "Client Credentials"

### OpenTopography: "401 API Key Required"

**Причина:** Превышена бесплатная квота без API ключа

**Решение:**
1. Получите бесплатный API ключ на opentopography.org
2. Добавьте в `.env`: `OPENTOPOGRAPHY_API_KEY=...`

### GEE: "Failed to initialize"

**Причина:** Проблемы с Service Account

**Решение:**
1. Проверьте, что файл `config/gee-key.json` существует
2. Проверьте, что проект зарегистрирован в Earth Engine
3. Проверьте роль Service Account (должна быть Earth Engine Resource Admin)

### Все источники недоступны

**Причина:** Проблемы с интернет-соединением или firewall

**Решение:**
1. Проверьте интернет-соединение
2. Проверьте, что нет блокировок firewall для:
   - `services.sentinel-hub.com`
   - `portal.opentopography.org`
   - `earthengine.googleapis.com`

---

## 📊 Сравнение источников

### Качество данных:

| Параметр | OpenTopography | Sentinel Hub | Google Earth Engine |
|----------|----------------|--------------|---------------------|
| DEM разрешение | 30m | 30m | 30m |
| RGB разрешение | ❌ | 10m | 10m |
| Актуальность | Статичные | Последние 6 мес | Полный архив |
| Облачность фильтр | ❌ | ✅ | ✅ |

### Производительность:

| Параметр | OpenTopography | Sentinel Hub | Google Earth Engine |
|----------|----------------|--------------|---------------------|
| Скорость DEM | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Скорость RGB | ❌ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Надежность | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## 💡 Рекомендации

**Для разработки:**
- Используйте **OpenTopography** (не требует настройки)

**Для production:**
- Используйте **Sentinel Hub** (лучший баланс качества/простоты)

**Для исследований:**
- Используйте **Google Earth Engine** (максимальные возможности)

**Для AI Segmentation:**
- Обязательно используйте источник с RGB: **Sentinel Hub** или **GEE**
- OpenTopography не подходит (только DEM)

---

## 📚 Дополнительные ресурсы

- [Sentinel Hub Documentation](https://docs.sentinel-hub.com/)
- [OpenTopography API Guide](https://portal.opentopography.org/apidocs/)
- [Google Earth Engine Guides](https://developers.google.com/earth-engine/guides)
- [BeamNG WorldForge GitHub](https://github.com/your-repo)
