# BeamNG.WorldForge - Руководство по установке и настройке

## 🎯 Краткий старт (без настройки!)

Приложение работает **из коробки** с бесплатными источниками данных:
- **OpenTopography** - работает без регистрации (базовый функционал)
- **Sentinel Hub** - требует бесплатную регистрацию (рекомендуется)

## Предварительные требования

### Минимальные:
1. **Python 3.11+**
2. **Node.js 18+**
3. **Docker & Docker Compose** (рекомендуется)

### Рекомендуемые:
1. **Sentinel Hub аккаунт** (бесплатный тариф)
2. **OpenTopography API ключ** (опционально, для увеличения квоты)

## 🚀 Установка

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd BeamNG.WorldForge
```

### 2. Настройка Google Earth Engine

#### 2.1. Создание проекта в Google Cloud

1. Перейдите на [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Включите **Earth Engine API**:
   - Перейдите в "APIs & Services" > "Library"
   - Найдите "Earth Engine API"
   - Нажмите "Enable"

#### 2.2. Создание сервисного аккаунта

1. Перейдите в "IAM & Admin" > "Service Accounts"
2. Нажмите "Create Service Account"
3. Укажите имя (например, "beamng-worldforge")
4. Выберите роль: **Earth Engine Resource Admin**
5. Нажмите "Create and Continue"
6. Нажмите "Done"

#### 2.3. Создание JSON-ключа

1. Найдите созданный сервисный аккаунт в списке
2. Нажмите на него
3. Перейдите на вкладку "Keys"
4. Нажмите "Add Key" > "Create new key"
5. Выберите формат **JSON**
6. Скачайте файл

#### 2.4. Размещение ключа

Поместите скачанный JSON-файл в:
```
backend/config/gee-key.json
```

⚠️ **Важно:** Не коммитьте этот файл в Git! Он уже добавлен в `.gitignore`.

### 3. Настройка Backend

```bash
cd backend

# Установка зависимостей через Poetry (рекомендуется)
poetry install

# ИЛИ через pip
pip install -r requirements.txt
```

#### 3.1. Настройка переменных окружения

Создайте файл `backend/.env`:

```env
# Google Earth Engine
GEE_SERVICE_ACCOUNT_KEY=config/gee-key.json
GEE_PROJECT_ID=your-gcp-project-id

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

Замените `your-gcp-project-id` на ID вашего проекта из Google Cloud Console.

### 4. Настройка Frontend

```bash
cd frontend

# Установка зависимостей
pnpm install
# ИЛИ
npm install
```

## 🏃 Запуск приложения

### Запуск Backend

```bash
cd backend

# С Poetry
poetry run uvicorn main:app --reload --port 8000

# ИЛИ напрямую
python -m uvicorn main:app --reload --port 8000
```

Backend будет доступен на `http://localhost:8000`

Проверьте работу:
- API документация: http://localhost:8000/docs
- Health check: http://localhost:8000/api/health

### Запуск Frontend

В другом терминале:

```bash
cd frontend

# С pnpm
pnpm dev

# ИЛИ с npm
npm run dev
```

Frontend будет доступен на `http://localhost:5173`

## 🎯 Первое использование

1. Откройте браузер и перейдите на `http://localhost:5173`
2. На карте выберите регион, кликнув и перетащив мышь
3. В правой панели:
   - Введите название карты (например, "test_map")
   - Настройте разрешение и размер heightmap
   - Нажмите "Generate Map"
4. Дождитесь завершения генерации (прогресс отображается в реальном времени)
5. Скачайте готовый ZIP-файл
6. Поместите его в `Documents/BeamNG.drive/mods/`
7. Запустите BeamNG.drive и проверьте карту!

## 🐛 Устранение неполадок

### Backend не запускается

**Проблема:** `Failed to initialize Google Earth Engine`

**Решение:**
1. Проверьте, что файл `backend/config/gee-key.json` существует
2. Проверьте, что в `.env` указан правильный `GEE_PROJECT_ID`
3. Убедитесь, что Earth Engine API включен в Google Cloud Console

**Проблема:** `ModuleNotFoundError: No module named 'rasterio'`

**Решение:**
```bash
# Установка GDAL зависимостей (Ubuntu/Debian)
sudo apt-get install gdal-bin libgdal-dev

# Установка GDAL зависимостей (macOS)
brew install gdal

# Затем переустановите Python пакеты
pip install --upgrade --force-reinstall rasterio GDAL
```

### Frontend не отображает карту

**Проблема:** Карта Leaflet не загружается

**Решение:**
1. Проверьте консоль браузера на ошибки
2. Убедитесь, что CSS Leaflet загружен (должен быть виден в Network tab)
3. Очистите кэш браузера

### Генерация зависает

**Проблема:** Прогресс останавливается на определенном этапе

**Решение:**
1. Проверьте логи backend в терминале
2. Убедитесь, что выбранный регион не слишком большой (начните с малого)
3. Проверьте доступ к интернету (GEE требует загрузки данных)
4. Увеличьте timeout в настройках (если необходимо)

## 📊 Ограничения MVP версии

Текущая версия (v0.1.0 MVP) поддерживает:
- ✅ Базовую генерацию heightmap из DEM
- ✅ Экспорт в формат BeamNG.drive
- ✅ Интерактивный выбор региона

**Не поддерживается:**
- ❌ AI-сегментация дорог и зданий (Этап 2)
- ❌ Процедурная генерация 3D объектов (Этап 3)
- ❌ Трафик и симуляция (Этап 4)
- ❌ Расширенные текстуры ландшафта

Эти функции будут добавлены в следующих этапах разработки.

## 🔗 Полезные ссылки

- [Google Earth Engine Documentation](https://developers.google.com/earth-engine)
- [BeamNG.drive Modding Wiki](https://documentation.beamng.com/)
- [React Leaflet Documentation](https://react-leaflet.js.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## 💡 Советы

### Оптимизация скорости генерации

1. **Используйте меньшие регионы** для первых тестов (2-5 км²)
2. **Уменьшите разрешение** DEM (используйте 30-50m вместо 10m)
3. **Используйте меньший размер heightmap** (1024x1024 вместо 4096x4096)

### Выбор оптимального региона

- **Хорошо работает:** Равнинные области, города с умеренным рельефом
- **Может быть проблемно:** Очень гористые регионы, океаны (минимальные данные)
- **Рекомендуемый размер:** 0.01-0.05 градусов по широте/долготе (~1-5 км)

### Качество heightmap

- Для детального рельефа: 2048x2048 или выше
- Для больших карт: 1024x1024 (быстрее загружается в игре)
- Учитывайте, что BeamNG.drive может иметь ограничения на размер

## 🤝 Получение помощи

Если у вас возникли проблемы:

1. Проверьте этот документ
2. Посмотрите Issues на GitHub
3. Создайте новый Issue с описанием проблемы
4. Приложите логи backend и скриншоты ошибок

---

**Приятной генерации карт!** 🚗🗺️

