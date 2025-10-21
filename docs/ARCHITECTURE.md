# Архитектура BeamNG.WorldForge

## 📐 Обзор системы

BeamNG.WorldForge - это full-stack приложение для автоматической генерации карт BeamNG.drive на основе реальных спутниковых данных.

```
┌─────────────────────────────────────────────────────────────┐
│                      USER INTERFACE                          │
│          React + Vite + TypeScript + Leaflet                │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP/REST API
┌───────────────────────▼─────────────────────────────────────┐
│                    BACKEND API                               │
│                  FastAPI + Python                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  API Routes                                          │   │
│  │  - /api/generate  - /api/status  - /api/download   │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         │                                    │
│  ┌──────────────────────▼──────────────────────────────┐   │
│  │           Service Layer                              │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │   │
│  │  │   GEE    │  │ Terrain  │  │ Export   │          │   │
│  │  │  Client  │  │Processor │  │ Service  │          │   │
│  │  └──────────┘  └──────────┘  └──────────┘          │   │
│  └─────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────┘
                        │
           ┌────────────┴────────────┐
           │                         │
┌──────────▼──────────┐   ┌─────────▼─────────┐
│ Google Earth Engine │   │  File System      │
│   - DEM Data        │   │  - Heightmaps     │
│   - Satellite RGB   │   │  - ZIP Archives   │
└─────────────────────┘   └───────────────────┘
```

## 🏗️ Компоненты системы

### Frontend (React)

**Технологии:**
- React 18 + TypeScript
- Vite (bundler)
- React Leaflet (карты)
- TailwindCSS (стилизация)
- Axios (HTTP клиент)

**Основные компоненты:**

1. **MapSelector** (`src/components/MapSelector.tsx`)
   - Интерактивная карта с OpenStreetMap
   - Выбор региона drag-and-drop
   - Отображение bounding box

2. **GenerationPanel** (`src/components/GenerationPanel.tsx`)
   - Форма настройки параметров карты
   - Отображение прогресса генерации
   - Скачивание результатов

3. **Header** (`src/components/Header.tsx`)
   - Навигация и брендинг

**Data Flow:**
```
User selects region → BoundingBox state
User configures settings → MapGenerationRequest
Click "Generate" → API call → Poll for status
Status = completed → Download ZIP
```

### Backend (FastAPI)

**Технологии:**
- Python 3.11+
- FastAPI (web framework)
- Uvicorn (ASGI server)
- Pydantic (validation)

**Структура:**

```
backend/
├── main.py                 # FastAPI app entry point
├── api/
│   └── routes/
│       └── map_generation.py  # API endpoints
├── models/
│   ├── map_request.py      # Request/Response models
│   └── terrain.py          # Terrain data models
└── services/
    ├── gee/
    │   └── client.py       # Google Earth Engine integration
    ├── terrain/
    │   └── processor.py    # DEM → Heightmap conversion
    └── export/
        └── beamng_exporter.py  # BeamNG format export
```

### API Endpoints

#### POST `/api/generate`
**Описание:** Инициирует генерацию карты

**Request:**
```json
{
  "name": "san_francisco",
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
  "map_id": "uuid-here"
}
```

#### GET `/api/status/{job_id}`
**Описание:** Получить статус генерации

**Response:**
```json
{
  "job_id": "uuid",
  "status": "processing",
  "progress": 50,
  "message": "Generating heightmap...",
  "download_url": null,
  "preview_url": null
}
```

#### GET `/api/download/{job_id}`
**Описание:** Скачать сгенерированный ZIP

**Response:** File download (application/zip)

## 🔄 Pipeline генерации карты

### Этап 1: Получение DEM (Digital Elevation Model)

```python
# services/gee/client.py
def get_dem_data(bbox, resolution=30):
    # 1. Создать region geometry из bbox
    # 2. Загрузить DEM dataset (SRTM/ASTER)
    # 3. Clip к региону
    # 4. Скачать GeoTIFF
    # 5. Конвертировать в numpy array
    return elevation_array, metadata
```

**Источники данных:**
- SRTM (Shuttle Radar Topography Mission) - 30m
- ASTER GDEM - 30m
- Возможность переключения на другие источники

### Этап 2: Обработка Terrain

```python
# services/terrain/processor.py
class TerrainProcessor:
    def process_dem(elevation_data):
        # 1. Очистка от NaN/invalid values
        # 2. Создание TerrainData model
        return terrain_data
    
    def generate_heightmap(terrain_data, config):
        # 1. Resize до target size (с interpolation)
        # 2. Нормализация к 16-bit (0-65535)
        # 3. Применение vertical scale
        return heightmap_array
```

**Нормализация:**
```
normalized = (elevation - min) / (max - min) * 65535
```

### Этап 3: Экспорт в BeamNG

```python
# services/export/beamng_exporter.py
def create_map_structure(map_name, heightmap_path):
    # 1. Создать структуру каталогов
    # 2. Копировать heightmap
    # 3. Генерировать JSON файлы:
    #    - info.json (метаданные)
    #    - main.level.json (конфигурация уровня)
    #    - layers.json (текстуры ландшафта)
    #    - items.level.json (объекты)
    # 4. Упаковать в ZIP
    return zip_path
```

**Структура мода:**
```
modname.zip/
└── levels/
    └── modname/
        ├── info.json
        ├── main.level.json
        ├── items.level.json
        └── art/
            └── terrains/
                └── main_terrain/
                    ├── heightmap.png
                    └── layers.json
```

## 📊 Модели данных

### BoundingBox
```python
class BoundingBox:
    min_lat: float  # -90 to 90
    max_lat: float
    min_lon: float  # -180 to 180
    max_lon: float
```

### TerrainData
```python
class TerrainData:
    elevation: List[List[float]]  # 2D array
    min_elevation: float
    max_elevation: float
    width: int
    height: int
```

### HeightmapConfig
```python
class HeightmapConfig:
    size: int = 1024          # 512, 1024, 2048, 4096
    bit_depth: int = 16       # 8 or 16
    vertical_scale: float = 1.0
    interpolation: str = "bilinear"  # nearest, bilinear, bicubic
```

## 🔮 Будущие этапы развития

### Этап 2: AI Сегментация (qwen3-vl)

```
Satellite RGB → qwen3-vl:235b-cloud → Segmentation Masks
                                       ├── Roads
                                       ├── Buildings
                                       ├── Water
                                       ├── Forest
                                       └── Other
```

### Этап 3: AI Генерация кода (qwen3-coder)

```
Segmentation Masks → qwen3-coder:480b-cloud → Generated Code
                                               ├── JBeam roads
                                               ├── Procedural buildings
                                               ├── Traffic routes
                                               └── Decor objects
```

### Этап 4: 3D Preview & Traffic

- Three.js/Babylon.js 3D viewer
- Real-time heightmap visualization
- Traffic simulation preview
- Interactive camera controls

## 🔧 Оптимизации

### Производительность

1. **Асинхронная обработка:**
   - Background tasks с FastAPI
   - Будущее: Celery + Redis для очередей

2. **Кэширование:**
   - Кэш DEM данных для повторных запросов
   - Кэш сегментационных масок (Этап 2)

3. **Streaming:**
   - Chunked download для больших файлов
   - WebSocket для real-time прогресса

### Масштабируемость

- Горизонтальное масштабирование backend (stateless)
- CDN для static assets
- S3/облачное хранилище для сгенерированных карт
- Load balancer для множественных инстансов

## 🔐 Безопасность

1. **API Key management:**
   - GEE credentials в environment variables
   - Не коммитить в Git

2. **Rate limiting:**
   - Ограничение запросов на генерацию
   - Защита от DDoS

3. **Input validation:**
   - Pydantic models для всех inputs
   - Проверка размера bounding box

4. **File handling:**
   - Безопасное именование файлов
   - Очистка temp файлов
   - Ограничение размера выходных файлов

## 📈 Мониторинг

**Планируется добавить:**
- Логирование (structlog)
- Метрики (Prometheus)
- Трейсинг (OpenTelemetry)
- Error tracking (Sentry)

---

**Версия документа:** 1.0 (MVP)  
**Дата обновления:** 2024-01-XX

