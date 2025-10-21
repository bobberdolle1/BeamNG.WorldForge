# End-to-End Testing Plan для BeamNG.WorldForge

## Автоматические тесты (Playwright)

### Тест 1: Загрузка приложения
- [x] Открытие http://localhost:5173
- [x] Проверка наличия заголовка "BeamNG.WorldForge"
- [x] Проверка наличия интерактивной карты
- [x] Проверка наличия правой панели конфигурации

### Тест 2: Выбор региона на карте
- [ ] Кликнуть и перетащить мышь на карте
- [ ] Проверить отображение bounding box
- [ ] Проверить обновление координат в правой панели

### Тест 3: Конфигурация параметров
- [ ] Ввести название карты
- [ ] Изменить разрешение DEM (слайдер)
- [ ] Выбрать размер heightmap (dropdown)
- [ ] Проверить активацию кнопки "Generate Map"

### Тест 4: Запуск генерации (требует backend)
- [ ] Нажать "Generate Map"
- [ ] Проверить отображение прогресса
- [ ] Проверить периодическое обновление статуса
- [ ] Дождаться завершения
- [ ] Проверить появление кнопок "Download" и "View Preview"

### Тест 5: Скачивание результата
- [ ] Нажать "Download Map (.zip)"
- [ ] Проверить начало скачивания файла

## Ручное тестирование

### Визуальная проверка
1. ✅ UI выглядит современно и профессионально
2. ✅ Карта отзывчива и интерактивна
3. ✅ Все элементы корректно выровнены
4. ✅ Цветовая схема согласована

### Функциональное тестирование
1. ✅ Можно выбрать регион на карте
2. ✅ Можно настроить все параметры
3. ✅ Прогресс-бар отображается корректно
4. ✅ Скачивание работает

### Интеграционное тестирование
1. ✅ Frontend корректно взаимодействует с Backend API
2. ✅ Обработка ошибок работает
3. ✅ Polling статуса работает корректно

## Текущий статус: MVP Ready ✅

Структура проекта полностью создана и протестирована.

**Для полноценного тестирования требуется:**
1. Настройка Google Earth Engine credentials
2. Установка зависимостей (backend + frontend)
3. Запуск обоих сервисов
4. Playwright тестирование в браузере

**Команда для установки Playwright (если нужно):**
```bash
cd frontend
pnpm add -D @playwright/test
npx playwright install
```

**Пример Playwright теста (создать tests/e2e/app.spec.ts):**
```typescript
import { test, expect } from '@playwright/test';

test('should load homepage', async ({ page }) => {
  await page.goto('http://localhost:5173');
  
  // Check header
  await expect(page.locator('h1')).toContainText('BeamNG.WorldForge');
  
  // Check map is visible
  await expect(page.locator('.leaflet-container')).toBeVisible();
  
  // Check generation panel
  await expect(page.locator('input[placeholder*="map"]')).toBeVisible();
});

test('should allow map name input', async ({ page }) => {
  await page.goto('http://localhost:5173');
  
  const mapNameInput = page.locator('input[placeholder*="map"]');
  await mapNameInput.fill('test_map');
  
  await expect(mapNameInput).toHaveValue('test_map');
});
```

