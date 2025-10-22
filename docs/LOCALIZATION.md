# BeamNG.WorldForge - Руководство по локализации

## 📚 Обзор системы локализации

BeamNG.WorldForge использует **i18next** для интернационализации интерфейса.

### Поддерживаемые языки

- 🇬🇧 **English** (en) - основной язык
- 🇷🇺 **Русский** (ru) - полная локализация

## 🏗️ Структура файлов

```
frontend/src/i18n/
├── config.ts           # Конфигурация i18next
└── locales/
    ├── en.json         # Английские переводы
    └── ru.json         # Русские переводы
```

## 📝 Формат файлов перевода

Переводы хранятся в формате JSON с вложенными объектами:

```json
{
  "app": {
    "title": "BeamNG.WorldForge",
    "subtitle": "Generate Maps from Satellite Data"
  },
  "nav": {
    "map": "Map",
    "settings": "Settings"
  }
}
```

## 🔑 Структура ключей локализации

### 1. App (общее приложение)

```json
{
  "app": {
    "title": "Название приложения",
    "subtitle": "Подзаголовок",
    "version": "Версия"
  }
}
```

### 2. Navigation (навигация)

```json
{
  "nav": {
    "map": "Карта",
    "settings": "Настройки"
  }
}
```

### 3. Map (страница карты)

```json
{
  "map": {
    "instructions": {
      "title": "Заголовок инструкций",
      "step1": "Шаг 1",
      "step2": "Шаг 2",
      "step3": "Шаг 3",
      "disabled": "Сообщение при отключении"
    },
    "layers": {
      "title": "Заголовок слоев",
      "street": "Уличная карта",
      "satellite": "Спутник",
      "topographic": "Топография",
      "hybrid": "Гибрид"
    },
    "selection": {
      "size": "{{width}} × {{height}} км",
      "ratio": "соотношение {{ratio}}:1"
    }
  }
}
```

**Примечание:** `{{width}}`, `{{height}}`, `{{ratio}}` - это интерполяционные переменные.

### 4. Settings (страница настроек)

```json
{
  "settings": {
    "title": "Настройки",
    "subtitle": "Описание",
    "apiKeys": {
      "title": "API-ключи",
      "subtitle": "Описание секции",
      "sentinelHubId": {
        "label": "Метка поля",
        "description": "Описание"
      },
      "verify": "Проверить",
      "placeholder": "Введите {{label}}"
    },
    "preferences": {
      "title": "Предпочтения",
      "defaultDataSource": "Источник данных по умолчанию",
      "defaultImageSource": "Источник изображений",
      "language": "Язык"
    },
    "actions": {
      "reset": "Сбросить",
      "save": "Сохранить",
      "saving": "Сохранение..."
    },
    "messages": {
      "saveSuccess": "Успешно сохранено",
      "saveError": "Ошибка сохранения"
    },
    "help": {
      "title": "Нужна помощь?",
      "sentinelHub": "Получить ключи",
      "opentopography": "Получить ключ",
      "azureMaps": "Получить подписку"
    }
  }
}
```

### 5. Generation (генерация карт)

```json
{
  "generation": {
    "title": "Генерация карты",
    "selectArea": "Выберите область",
    "configure": "Настройте",
    "generate": "Сгенерировать",
    "dataSource": "Источник данных",
    "resolution": "Разрешение",
    "heightmapSize": "Размер карты высот",
    "status": {
      "idle": "Готово",
      "processing": "Генерация...",
      "completed": "Завершено",
      "error": "Ошибка"
    }
  }
}
```

### 6. Common (общие элементы)

```json
{
  "common": {
    "loading": "Загрузка...",
    "error": "Ошибка",
    "success": "Успех",
    "cancel": "Отмена",
    "close": "Закрыть",
    "download": "Скачать"
  }
}
```

## 🔧 Использование в коде

### 1. Импорт хука useTranslation

```typescript
import { useTranslation } from 'react-i18next';
```

### 2. Использование в компоненте

```typescript
function MyComponent() {
  const { t } = useTranslation();
  
  return (
    <div>
      <h1>{t('app.title')}</h1>
      <p>{t('app.subtitle')}</p>
    </div>
  );
}
```

### 3. Интерполяция переменных

```typescript
// В переводе: "{{width}} × {{height}} км"
<span>{t('map.selection.size', { width: 5.2, height: 5.2 })}</span>
// Результат: "5.2 × 5.2 км"
```

### 4. Смена языка

```typescript
import { useTranslation } from 'react-i18next';

function LanguageSwitcher() {
  const { i18n } = useTranslation();
  
  const changeLanguage = (lng: string) => {
    i18n.changeLanguage(lng);
    localStorage.setItem('language', lng);
  };
  
  return (
    <select 
      value={i18n.language} 
      onChange={(e) => changeLanguage(e.target.value)}
    >
      <option value="en">English</option>
      <option value="ru">Русский</option>
    </select>
  );
}
```

## ➕ Добавление нового языка

### Шаг 1: Создать файл перевода

Создайте новый файл в `frontend/src/i18n/locales/`:

```bash
frontend/src/i18n/locales/de.json  # Немецкий
```

### Шаг 2: Скопировать структуру

Скопируйте содержимое `en.json` в новый файл и переведите все значения:

```json
{
  "app": {
    "title": "BeamNG.WorldForge",
    "subtitle": "Karten aus Satellitendaten generieren",
    "version": "MVP v0.1.0"
  },
  "nav": {
    "map": "Karte",
    "settings": "Einstellungen"
  }
  // ... и так далее
}
```

### Шаг 3: Зарегистрировать язык

Откройте `frontend/src/i18n/config.ts`:

```typescript
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from './locales/en.json';
import ru from './locales/ru.json';
import de from './locales/de.json';  // Новый импорт

i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      ru: { translation: ru },
      de: { translation: de }  // Новый язык
    },
    lng: localStorage.getItem('language') || 'en',
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false
    }
  });

export default i18n;
```

### Шаг 4: Добавить в переключатель языков

Обновите `frontend/src/components/LanguageSwitcher.tsx`:

```typescript
<select ...>
  <option value="en">English</option>
  <option value="ru">Русский</option>
  <option value="de">Deutsch</option>  // Новая опция
</select>
```

### Шаг 5: Обновить бэкенд модель (опционально)

Если хотите, чтобы язык сохранялся в настройках:

```python
# backend/models/user_settings.py
class UserPreferences(BaseModel):
    # ...
    language: str = Field("en", description="UI language (en, ru, de)")
```

## ✅ Проверка переводов

### 1. Автоматическая проверка

Создайте скрипт `frontend/src/i18n/validate.ts`:

```typescript
import en from './locales/en.json';
import ru from './locales/ru.json';

function validateTranslations() {
  const enKeys = getKeys(en);
  const ruKeys = getKeys(ru);
  
  const missing = enKeys.filter(key => !ruKeys.includes(key));
  const extra = ruKeys.filter(key => !enKeys.includes(key));
  
  if (missing.length > 0) {
    console.error('Missing in RU:', missing);
  }
  if (extra.length > 0) {
    console.warn('Extra in RU:', extra);
  }
}

function getKeys(obj: any, prefix = ''): string[] {
  return Object.keys(obj).reduce((keys: string[], key) => {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (typeof obj[key] === 'object') {
      return [...keys, ...getKeys(obj[key], fullKey)];
    }
    return [...keys, fullKey];
  }, []);
}

validateTranslations();
```

Запустите: `npx ts-node src/i18n/validate.ts`

### 2. Ручная проверка

1. Запустите приложение
2. Переключите язык
3. Проверьте все страницы:
   - Map page
   - Settings page
   - Progress indicators
   - Error messages
4. Убедитесь, что все элементы переведены

## 📐 Правила и рекомендации

### DO ✅

1. **Используйте вложенные объекты** для логической группировки
2. **Будьте последовательны** в именовании ключей
3. **Используйте описательные ключи**: `settings.apiKeys.verify` вместо `btn1`
4. **Сохраняйте структуру** во всех языковых файлах
5. **Используйте интерполяцию** для динамических значений
6. **Сохраняйте технические термины** (BeamNG.drive, API, DEM)
7. **Тестируйте** каждый новый перевод в реальном UI

### DON'T ❌

1. **Не переводите:**
   - Имена собственные (BeamNG.drive)
   - Технические аббревиатуры (API, DEM, AI)
   - URL и пути к файлам
   - Названия компаний (Sentinel Hub, Azure Maps)

2. **Не используйте:**
   - Хардкод текстов в JSX
   - Машинный перевод без проверки
   - Неформальный язык в официальных сообщениях

3. **Избегайте:**
   - Слишком длинных переводов (учитывайте размер UI)
   - Дублирования ключей
   - Удаления ключей без проверки использования

## 🐛 Отладка проблем с локализацией

### Текст не переводится

**Проблема:** Вижу ключ вместо перевода (например, `app.title`)

**Решение:**
1. Проверьте, что ключ существует в JSON-файле
2. Убедитесь, что используете правильный ключ: `t('app.title')`
3. Проверьте консоль на ошибки i18next
4. Перезагрузите страницу

### Некорректный перевод

**Проблема:** Перевод отображается, но некорректно

**Решение:**
1. Откройте соответствующий JSON-файл
2. Найдите ключ и исправьте перевод
3. Сохраните файл
4. Vite автоматически перезагрузит страницу

### Интерполяция не работает

**Проблема:** Вижу `{{variable}}` вместо значения

**Решение:**
```typescript
// ❌ Неправильно
t('map.selection.size')

// ✅ Правильно
t('map.selection.size', { width: 5, height: 5 })
```

### Язык не меняется

**Проблема:** После смены языка интерфейс не обновляется

**Решение:**
1. Проверьте, что вызываете `i18n.changeLanguage(lng)`
2. Убедитесь, что компоненты используют `useTranslation()` хук
3. Очистите localStorage и перезагрузите

## 📊 Статистика покрытия

### Текущее состояние (v0.2.0)

| Компонент | EN | RU | Покрытие |
|-----------|----|----|----------|
| App Header | ✅ | ✅ | 100% |
| Map Page | ✅ | ✅ | 100% |
| Settings Page | ✅ | ✅ | 100% |
| Generation Panel | ✅ | ✅ | 100% |
| Progress Indicator | ✅ | ✅ | 100% |
| Error Messages | ✅ | ✅ | 100% |

**Всего строк:** ~150  
**Языков:** 2  
**Общее покрытие:** 100%

## 🤝 Участие в переводе

Хотите добавить свой язык или улучшить существующий?

1. Fork репозиторий
2. Создайте новый файл перевода или исправьте существующий
3. Протестируйте изменения локально
4. Создайте Pull Request с описанием изменений

### Чек-лист для PR

- [ ] Все ключи из `en.json` присутствуют
- [ ] Нет дополнительных ключей
- [ ] Соблюдена структура JSON
- [ ] Протестировано в реальном UI
- [ ] Соблюдены правила перевода
- [ ] Добавлен язык в переключатель
- [ ] Обновлена документация

---

**Спасибо за помощь в локализации BeamNG.WorldForge!** 🌍
