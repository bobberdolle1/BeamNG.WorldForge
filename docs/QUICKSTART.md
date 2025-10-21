# BeamNG.WorldForge - Быстрый старт 🚀

## За 5 минут до первой карты!

### Шаг 1: Клонирование
```bash
git clone <your-repo-url>
cd BeamNG.WorldForge
```

### Шаг 2: Настройка Google Earth Engine

1. Перейдите на https://console.cloud.google.com/
2. Создайте новый проект
3. Включите **Earth Engine API**
4. Создайте **Service Account**
5. Скачайте JSON ключ
6. Сохраните как `backend/config/gee-key.json`

### Шаг 3: Создайте `.env` файл

**backend/.env:**
```env
GEE_SERVICE_ACCOUNT_KEY=config/gee-key.json
GEE_PROJECT_ID=ваш-project-id
```

### Шаг 4: Запуск с Docker (проще всего!)

```bash
docker-compose up
```

Готово! Откройте http://localhost:5173

---

### Альтернатива: Ручной запуск

**Терминал 1 - Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

**Терминал 2 - Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## Использование

1. **Выберите регион** на карте (кликните и перетащите)
2. **Введите название** карты (например: `test_map`)
3. **Настройте параметры:**
   - Разрешение: 30m (рекомендуется)
   - Размер: 1024x1024 (оптимально)
4. **Нажмите "Generate Map"**
5. **Дождитесь завершения** (~2-5 минут)
6. **Скачайте ZIP** файл
7. **Поместите** в `Documents/BeamNG.drive/mods/`
8. **Запустите BeamNG.drive** и наслаждайтесь!

---

## Рекомендации для первого раза

### Хорошие регионы для тестирования:

**1. San Francisco Downtown** (интересный рельеф)
```
Lat: 37.7749 - 37.8049
Lon: -122.4294 - -122.3994
```

**2. Небольшая равнина** (для быстрого теста)
```
Lat: 40.0000 - 40.0100
Lon: -105.0000 - -104.9900
```

**3. Горная местность** (эффектно)
```
Lat: 46.5000 - 46.5500
Lon: 7.5000 - 7.5500
```

### Советы:

- ✅ Начните с **небольшого региона** (0.01-0.05° по широте/долготе)
- ✅ Используйте **разрешение 30m** для первого теста
- ✅ Выбирайте **1024x1024** для баланса качества/скорости
- ❌ Избегайте **океанов** (мало данных о рельефе)
- ❌ Не выбирайте **слишком большие регионы** сразу

---

## Проверка работоспособности

### Проверка структуры проекта:
```bash
python tests/test_project_structure.py
```

Должно вывести: `SUCCESS: ALL TESTS PASSED!`

### Проверка Backend:
```bash
curl http://localhost:8000/api/health
```

Должно вернуть JSON со статусом "healthy"

### Проверка Frontend:
Откройте http://localhost:5173 в браузере

---

## Устранение проблем

### Backend не запускается?

**Проблема:** "Failed to initialize Google Earth Engine"
```bash
# Проверьте:
1. Файл backend/config/gee-key.json существует?
2. В .env правильный GEE_PROJECT_ID?
3. Earth Engine API включен в Google Cloud Console?
```

**Проблема:** "ModuleNotFoundError"
```bash
# Переустановите зависимости:
pip install -r backend/requirements.txt
```

### Frontend не загружается?

**Проблема:** Белый экран
```bash
# Проверьте консоль браузера (F12)
# Переустановите зависимости:
cd frontend
rm -rf node_modules
npm install
```

**Проблема:** Карта не отображается
```bash
# Проверьте, загружен ли Leaflet CSS
# Очистите кэш браузера (Ctrl+Shift+R)
```

---

## Нужна помощь?

1. 📖 Читайте [docs/SETUP.md](docs/SETUP.md) - подробная инструкция
2. 🏗️ Смотрите [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - техническая архитектура
3. 📡 Изучайте [docs/API.md](docs/API.md) - API документация
4. 🐛 Создайте Issue на GitHub

---

**Приятного использования! 🗺️🚗**

