# Architecture

## Overview

BeamNG.WorldForge is a two-part application: a React single-page frontend and a
FastAPI backend. The backend does all the work; the frontend selects a region
and polls for progress.

```
┌──────────────────────────────────────────────────────────────┐
│  Frontend - React + TypeScript + Vite                        │
│  Leaflet region picker · settings UI · Three.js preview      │
└────────────────────────────┬─────────────────────────────────┘
                             │ REST (JSON), /api proxied in dev
┌────────────────────────────▼─────────────────────────────────┐
│  Backend - FastAPI                                           │
│                                                              │
│  api/routes/      thin HTTP layer: validate, queue, serve     │
│        │                                                     │
│  services/pipeline.py   orchestration + progress reporting    │
│        │                                                     │
│        ├── data_sources/   provider clients (DEM / imagery)   │
│        ├── terrain/        DEM cleaning, heightmap generation  │
│        ├── export/         BeamNG mod packaging               │
│        └── jobs.py         job registry with TTL cleanup      │
│                                                              │
│  core/            config, logging, path safety, geo maths     │
└────────────────────────────┬─────────────────────────────────┘
                             │
        ┌────────────────────┴──────────────────┐
        │                                       │
┌───────▼────────────────┐        ┌─────────────▼─────────────┐
│ Geodata providers      │        │ Local filesystem          │
│ OpenTopography         │        │ temp/   working files     │
│ Sentinel Hub           │        │ output/ ZIP archives      │
│ Azure Maps             │        │ config/ encrypted keys    │
│ Google Earth Engine    │        └───────────────────────────┘
└────────────────────────┘
```

## Layers

The design rule is that each layer only knows about the one beneath it.

### `api/routes/` - HTTP

Request validation, job bookkeeping, file serving. Contains no generation
logic: the previous version had a 200-line pipeline inline in a route handler,
which made it impossible to test without an HTTP client.

### `services/pipeline.py` - orchestration

Owns the sequence of stages and reports progress. Two properties matter:

* **It is synchronous.** FastAPI dispatches sync background tasks to a worker
  thread pool. Declaring the pipeline `async` while its body blocked (HTTP
  downloads, SciPy resampling, PNG encoding) put all of that on the event loop
  and froze every concurrent request, including the status polling the UI
  depends on.
* **Progress is declarative.** Stages and their weights live in one table
  (`BASE_STAGES`, `AI_STAGES`) and the reported percentage is derived from it.
  The frontend mirrors that table in `src/lib/stages.ts`.

Failures never escape: they are recorded on the job. A background task that
raises dies silently and leaves the job stuck in `processing` forever.

### `services/data_sources/` - providers

Every provider implements `DataSourceInterface` and declares its
`capabilities` (`dem`, `imagery`, or both). Callers pick a provider by
capability rather than by calling a method and catching `NotImplementedError`.

`DataSourceFactory` caches instances (they hold OAuth tokens worth reusing) and
subscribes to settings changes so the cache is dropped when a key is saved.
Credentials come from `SettingsManager`, falling back to environment variables.

| Provider | DEM | Imagery | Setup |
|---|---|---|---|
| OpenTopography | ✅ Copernicus, SRTM, NASADEM, ALOS | — | Free API key |
| Sentinel Hub | ✅ Copernicus GLO-30 | ✅ Sentinel-2 (10 m) | Free tier, OAuth2 |
| Azure Maps | — | ✅ aerial tiles | Subscription key |
| Bing Maps | — | ✅ aerial tiles | Retired by Microsoft |
| Google Earth Engine | ✅ | ✅ | Service account |

### `services/terrain/` - DEM processing

```
raw DEM ──► detect nodata ──► fill from nearest valid ──► resample ──► normalise
            (NaN, -32768,     (distance transform)        (to N×N)     (to 16-bit)
             -9999, |v|>9000)
```

Nodata handling is the part that matters. Replacing voids with `0.0` - as the
original did - creates kilometre-deep cliffs on mountain tiles, and because the
heightmap is normalised against min/max, a single voided pixel compresses the
real elevation range into a sliver of the available bit depth.

`TerrainData` holds a NumPy array. It used to be a Pydantic model with
`elevation: list`, so a 2048×2048 DEM was converted into ~4.2 million
individually validated Python floats and immediately converted back.

### `services/export/` - packaging

```
<map_name>.zip
└── levels/<map_name>/
    ├── info.json                      level metadata
    ├── main.level.json                terrain scale, sun, weather
    ├── items.level.json               objects (empty by default)
    ├── preview.png                    thumbnail
    ├── WORLDFORGE.md                  provenance + import notes
    ├── art/terrains/main_terrain/
    │   ├── heightmap.png              16-bit grayscale
    │   └── layers.json                material layers
    └── vectors/*.json                 detected features (AI runs only)
```

Two values in `main.level.json` make the terrain match reality:

* `squareSize` - metres per heightmap pixel, computed from the bbox's true
  ground size divided by the heightmap resolution. Hardcoding it (it was `2.0`)
  meant a 1 km and a 20 km selection produced identically sized terrain.
* `minHeight` + `heightScale` - the real elevation span. The PNG is normalised
  to the full 16-bit range, so without these the terrain has an arbitrary
  vertical exaggeration.

### `services/jobs.py` - job registry

In-memory, lock-guarded, with TTL cleanup of finished jobs and the files they
produced. Artefacts are recorded explicitly, so download endpoints resolve a
stored path rather than rebuilding one from a user-supplied name.

For a single-user desktop application, in-memory is the right trade-off: jobs
are meaningless across restarts anyway. A multi-worker deployment would need
shared storage (Redis), because each uvicorn worker has its own registry.

### `core/` - cross-cutting

| Module | Responsibility |
|---|---|
| `config.py` | `pydantic-settings` configuration. Resolves directories absolutely against the app root - or, when frozen, next to the executable - rather than against the current working directory. |
| `logging_config.py` | Single logging setup, aligned with uvicorn's loggers. |
| `paths.py` | Map-name validation/slugification and `safe_join`, which verifies a resolved path stays inside its base directory (symlinks included). |
| `geo.py` | Degrees↔metres conversion, bbox sizing, raster dimension calculation. |

## Request flow

```
POST /api/generate
  │
  ├─ Pydantic validates: name slug, bbox extent (0.01-400 km²),
  │  power-of-two heightmap size                       → 422 on failure
  ├─ job_store.create()                                → job id
  ├─ background_tasks.add_task(pipeline.run, ...)      → worker thread
  └─ 202 Accepted { map_id, map_name }

GET /api/status/{id}   polled every 2 s by the frontend
  └─ queued → processing (progress 0-99) → completed | failed

GET /api/download/{id}
  └─ resolves job.artifacts["archive"]; 409 if the job failed or is running
```

## Concurrency

* One semaphore bounds simultaneous generations (`MAX_CONCURRENT_JOBS`,
  default 2). Each run holds a full DEM plus its resampled heightmap in memory.
* The job store is guarded by an `RLock`; background threads and request
  handlers both touch it.
* A background task sweeps expired jobs every 15 minutes.

## Frontend

| Path | Responsibility |
|---|---|
| `components/MapSelector.tsx` | Leaflet map, layer switching, square region selection |
| `components/GenerationPanel.tsx` | Configuration form and result actions |
| `hooks/useGenerationJob.ts` | Job lifecycle: start, poll, error handling |
| `lib/stages.ts` | Stage table mirroring the backend's |
| `services/api.ts` | Axios client; normalises errors into `ApiError` carrying the server's `detail` |
| `pages/SettingsPage.tsx` | API key management |
| `components/ThreePreview.tsx` | Three.js heightmap viewer, lazy-loaded |

The 3D viewer is behind `React.lazy`, and Three.js, Leaflet, React and i18next
are split into separate chunks, so the initial download does not include a
renderer most sessions never open.

## Testing

`tests/` holds the backend suite. Every test runs against an isolated temporary
data root and with provider credentials stripped from the environment, so
results do not depend on whose machine they run on or whether a third-party API
happens to be up.

```bash
pytest                    # everything
pytest -m "not network"   # what CI runs
```

The frontend has its own Vitest suite under `frontend/src`, and
`tests/test_api_contract.py` bridges the two: it parses the frontend's API
client and asserts every path and method it calls exists in the backend's
OpenAPI schema. Without that bridge each side can pass on its own while
disagreeing across the HTTP boundary - which is exactly how a settings-page
break once shipped.

```bash
cd frontend && npm test
```

## Known limitations

* **No authentication.** Intended for local use.
* **In-memory jobs.** They do not survive a restart and are not shared between
  uvicorn workers.
* **Terrain only.** Roads, buildings, textures and props are not generated. The
  code under `services/code_generation/` and `services/beamng_integration/`
  targets that goal but is not wired into the pipeline.
* **BeamNG's level format is not fully documented.** The archive follows the
  observed structure; a heightmap may still need importing through the in-game
  World Editor, which is why every archive ships a `WORLDFORGE.md` with the
  exact scale values.
