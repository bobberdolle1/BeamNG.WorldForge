# BeamNG.WorldForge API Documentation

## Base URL
```
http://localhost:8000/api
```

## Authentication
Currently no authentication required (MVP version).

## Endpoints

### 1. Health Check

#### GET `/api/health`

Проверка состояния API.

**Response:**
```json
{
  "status": "healthy",
  "services": {
    "api": "online",
    "gee": "configured"
  }
}
```

---

### 2. Generate Map

#### POST `/api/generate`

Начать генерацию карты из спутниковых данных.

**Request Body:**
```json
{
  "name": "string",           // Название карты (латиница, snake_case)
  "bbox": {
    "min_lat": number,        // Минимальная широта (-90 до 90)
    "max_lat": number,        // Максимальная широта
    "min_lon": number,        // Минимальная долгота (-180 до 180)
    "max_lon": number         // Максимальная долгота
  },
  "resolution": number,       // (Опционально) Разрешение DEM в метрах (10-100, default: 30)
  "heightmap_size": number    // (Опционально) Размер heightmap (512, 1024, 2048, 4096, default: 1024)
}
```

**Example:**
```json
{
  "name": "san_francisco_test",
  "bbox": {
    "min_lat": 37.7749,
    "max_lat": 37.8049,
    "min_lon": -122.4294,
    "max_lon": -122.3994
  },
  "resolution": 30,
  "heightmap_size": 1024
}
```

**Response:**
```json
{
  "success": true,
  "message": "Map generation started",
  "map_id": "550e8400-e29b-41d4-a716-446655440000",
  "download_url": null,
  "preview_url": null
}
```

**Status Codes:**
- `200 OK` - Генерация успешно запущена
- `422 Unprocessable Entity` - Неверные параметры запроса

---

### 3. Get Generation Status

#### GET `/api/status/{job_id}`

Получить текущий статус генерации карты.

**Path Parameters:**
- `job_id` (string) - UUID задачи генерации

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",     // "starting" | "processing" | "completed" | "failed"
  "progress": 50,             // 0-100
  "message": "Generating heightmap...",
  "error": null,              // Сообщение об ошибке (если status = "failed")
  "download_url": null,       // URL для скачивания (если status = "completed")
  "preview_url": null         // URL превью (если status = "completed")
}
```

**Status Values:**
- `starting` - Инициализация задачи
- `processing` - Генерация в процессе
- `completed` - Генерация завершена успешно
- `failed` - Произошла ошибка

**Status Codes:**
- `200 OK` - Статус получен
- `404 Not Found` - Задача не найдена

---

### 4. Download Map

#### GET `/api/download/{job_id}`

Скачать сгенерированную карту в формате ZIP.

**Path Parameters:**
- `job_id` (string) - UUID задачи генерации

**Response:**
- Content-Type: `application/zip`
- File download

**Status Codes:**
- `200 OK` - Файл отправлен
- `400 Bad Request` - Генерация еще не завершена
- `404 Not Found` - Задача или файл не найдены

---

### 5. Get Preview

#### GET `/api/preview/{job_id}`

Получить превью heightmap (цветное изображение для визуализации).

**Path Parameters:**
- `job_id` (string) - UUID задачи генерации

**Response:**
- Content-Type: `image/png`
- Preview image

**Status Codes:**
- `200 OK` - Изображение отправлено
- `400 Bad Request` - Генерация еще не завершена
- `404 Not Found` - Задача или файл не найдены

---

## Error Handling

Все ошибки возвращаются в формате:

```json
{
  "detail": "Error message here"
}
```

### Common Error Codes

- `400 Bad Request` - Неверный запрос
- `404 Not Found` - Ресурс не найден
- `422 Unprocessable Entity` - Ошибка валидации
- `500 Internal Server Error` - Внутренняя ошибка сервера

---

## Rate Limiting

**MVP версия:** Отсутствует

**Планируется:**
- 10 запросов на генерацию в час на IP
- 100 запросов статуса в минуту

---

## Data Models

### BoundingBox
```typescript
interface BoundingBox {
  min_lat: number;  // -90 to 90
  max_lat: number;  // -90 to 90
  min_lon: number;  // -180 to 180
  max_lon: number;  // -180 to 180
}
```

### MapGenerationRequest
```typescript
interface MapGenerationRequest {
  name: string;                    // 3-50 characters
  bbox: BoundingBox;
  resolution?: number;             // 10-100, default: 30
  heightmap_size?: number;         // 512|1024|2048|4096, default: 1024
}
```

### GenerationStatus
```typescript
interface GenerationStatus {
  job_id: string;
  status: 'starting' | 'processing' | 'completed' | 'failed';
  progress: number;                // 0-100
  message: string;
  error?: string;
  download_url?: string;
  preview_url?: string;
}
```

---

## Examples

### Complete Flow Example (JavaScript)

```javascript
// 1. Start generation
const generateResponse = await fetch('http://localhost:8000/api/generate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'my_test_map',
    bbox: {
      min_lat: 37.7749,
      max_lat: 37.8049,
      min_lon: -122.4294,
      max_lon: -122.3994
    },
    resolution: 30,
    heightmap_size: 1024
  })
});

const { map_id } = await generateResponse.json();

// 2. Poll for status
const pollStatus = async () => {
  const statusResponse = await fetch(`http://localhost:8000/api/status/${map_id}`);
  const status = await statusResponse.json();
  
  console.log(`Progress: ${status.progress}% - ${status.message}`);
  
  if (status.status === 'completed') {
    console.log('Generation completed!');
    window.location.href = status.download_url;
  } else if (status.status === 'failed') {
    console.error('Generation failed:', status.error);
  } else {
    setTimeout(pollStatus, 2000); // Poll every 2 seconds
  }
};

pollStatus();
```

### Python Example

```python
import requests
import time

# Start generation
response = requests.post('http://localhost:8000/api/generate', json={
    'name': 'my_test_map',
    'bbox': {
        'min_lat': 37.7749,
        'max_lat': 37.8049,
        'min_lon': -122.4294,
        'max_lon': -122.3994
    },
    'resolution': 30,
    'heightmap_size': 1024
})

job_id = response.json()['map_id']

# Poll for completion
while True:
    status_response = requests.get(f'http://localhost:8000/api/status/{job_id}')
    status = status_response.json()
    
    print(f"Progress: {status['progress']}% - {status['message']}")
    
    if status['status'] == 'completed':
        # Download the map
        map_response = requests.get(f"http://localhost:8000{status['download_url']}")
        with open('my_test_map.zip', 'wb') as f:
            f.write(map_response.content)
        print('Map downloaded!')
        break
    elif status['status'] == 'failed':
        print(f"Generation failed: {status['error']}")
        break
    
    time.sleep(2)
```

---

## Interactive Documentation

FastAPI предоставляет автоматическую интерактивную документацию:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

Там вы можете тестировать все endpoints прямо из браузера.

---

**Version:** 0.1.0 (MVP)  
**Last Updated:** 2024-01-XX

