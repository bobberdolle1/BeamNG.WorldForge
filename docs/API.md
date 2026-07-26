# BeamNG.WorldForge REST API

Base URL: `http://localhost:8000/api`

Interactive documentation generated from the code is available while the server
is running:

* Swagger UI - <http://localhost:8000/docs>
* ReDoc - <http://localhost:8000/redoc>
* OpenAPI schema - <http://localhost:8000/openapi.json>

## Authentication

**There is none.** Every endpoint is open to anyone who can reach the port.
The server binds to `127.0.0.1` by default; change `API_HOST` only if you intend
to expose it on a network you trust.

## Conventions

* All request and response bodies are JSON.
* Validation failures return **422** with a flat, human-readable `detail` string
  plus a structured `errors` array:

```json
{
  "detail": "bbox: Value error, Selected area is too large (1015104.9 km2). The maximum is 400 km2 - select a smaller region.",
  "errors": [
    { "field": "bbox", "message": "Value error, Selected area is too large ...", "type": "value_error" }
  ]
}
```

---

## Map generation

### `POST /api/generate`

Queue a generation job. Returns immediately with **202 Accepted**; poll
`/api/status/{job_id}` for progress.

**Request body**

| Field | Type | Default | Notes |
|---|---|---|---|
| `name` | string | required | 3-80 chars. Slugified server-side: `"San Francisco"` becomes `san_francisco`. Rejected if nothing usable remains. |
| `bbox` | object | required | `min_lat`, `max_lat`, `min_lon`, `max_lon`. Must be non-degenerate (`min < max`) and cover 0.01-400 km². |
| `resolution` | int | `30` | DEM ground resolution in metres, 10-500. |
| `heightmap_size` | int | `1024` | Output heightmap edge length. Power of two, 256-4096. |
| `data_source` | string | `"auto"` | `auto`, `opentopography`, `sentinel_hub`, `azure_maps`, `bing_maps`, `google_earth_engine`. |
| `use_ai_segmentation` | bool | `false` | Needs Ollama and an imagery source. Failure degrades the run rather than aborting it. |

**Example**

```bash
curl -X POST http://localhost:8000/api/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "san francisco downtown",
    "bbox": {"min_lat": 37.7749, "max_lat": 37.8049,
             "min_lon": -122.4294, "max_lon": -122.3994},
    "resolution": 30,
    "heightmap_size": 1024,
    "data_source": "auto"
  }'
```

**Response `202`**

```json
{
  "success": true,
  "message": "Map generation started",
  "map_id": "9c3f5b02-0f6a-4a0b-9c3a-8a2b1c0d5e6f",
  "map_name": "san_francisco_downtown",
  "download_url": null,
  "preview_url": null,
  "error": null
}
```

Note `map_name`: it is the slug the server derived, and it determines the
archive filename.

---

### `GET /api/status/{job_id}`

**Response `200`**

```json
{
  "job_id": "9c3f5b02-0f6a-4a0b-9c3a-8a2b1c0d5e6f",
  "status": "completed",
  "progress": 100,
  "message": "Done - san_francisco_downtown.zip (4.2 MB)",
  "map_name": "san_francisco_downtown",
  "error": null,
  "download_url": "/api/download/9c3f5b02-...",
  "preview_url": "/api/preview/9c3f5b02-...",
  "stats": {
    "data_source": "OpenTopography",
    "terrain": {
      "width": 111, "height": 122,
      "min_elevation": -3.0, "max_elevation": 279.0,
      "elevation_range": 282.0, "nodata_fraction": 0.0
    },
    "archive_size_mb": 4.2,
    "dem_resolution_m": 30
  },
  "created_at": 1753564800.0,
  "updated_at": 1753564847.5
}
```

**Statuses:** `queued` → `processing` → `completed` | `failed` | `cancelled`.

`download_url` and `preview_url` appear only once the job reaches `completed`.

**`404`** - unknown job, or the job expired. Finished jobs are kept for
`JOB_RETENTION_SECONDS` (24 hours by default).

---

### `GET /api/download/{job_id}`

Returns the mod archive as `application/zip`.

| Status | Meaning |
|---|---|
| `200` | The ZIP file. |
| `404` | Unknown/expired job, or the artefact was cleaned up. |
| `409` | Job failed (`detail` holds the reason) or is still running. |

The served path comes from the job's recorded artefacts, never from a path
rebuilt out of the requested name.

---

### `GET /api/preview/{job_id}`

Returns the colourised heightmap preview as `image/png`. Same status codes as
the download endpoint.

---

### `GET /api/jobs`

Lists known jobs, newest first.

```json
{ "jobs": [ { "job_id": "...", "status": "completed" } ], "count": 1 }
```

### `DELETE /api/jobs/{job_id}`

Deletes a finished job and the files it produced. Returns `409` while the job is
still running.

---

## Data sources

### `GET /api/data-sources`

```json
{
  "sources": [
    {
      "id": "opentopography",
      "name": "OpenTopography",
      "description": "OpenTopography - High-quality global elevation data\n...",
      "available": true,
      "requires_setup": true,
      "provides": ["dem"],
      "recommended": true,
      "deprecated": false
    }
  ],
  "default": "opentopography",
  "message": "Use 'auto' to let the server pick the best configured source."
}
```

`provides` tells you what a source can actually serve - `dem`, `imagery`, or
both. A source missing credentials reports `available: false` with the reason in
`description` rather than failing the whole request.

---

## Settings

### `GET /api/settings`

Returns stored settings with every secret masked (`***abcd`).

```json
{
  "api_keys": {
    "sentinel_hub_client_id": "***9f2a",
    "sentinel_hub_client_secret": "***c41d",
    "opentopography_api_key": "***7b3e",
    "azure_maps_subscription_key": null,
    "bing_maps_api_key": null,
    "gee_project_id": "my-gcp-project"
  },
  "preferences": {
    "default_data_source": "auto",
    "default_image_source": "sentinel_hub",
    "language": "en"
  }
}
```

`gee_project_id` is not a secret and is returned in the clear.

### `PUT /api/settings`

Partial update. Omitted fields are preserved, and values that look like the mask
this API produces are ignored - so posting the form back unchanged cannot
destroy a stored key. Send an explicit empty string to clear one.

```bash
curl -X PUT http://localhost:8000/api/settings \
  -H 'Content-Type: application/json' \
  -d '{"api_keys": {"opentopography_api_key": "your-key"},
       "preferences": {"language": "ru"}}'
```

### `POST /api/settings/validate/{service}`

Checks a credential against the live provider without storing it. `service` is
one of `sentinel_hub`, `opentopography`, `azure_maps`, `bing_maps`.

Credentials travel in the **request body**, never the query string.

```bash
curl -X POST http://localhost:8000/api/settings/validate/sentinel_hub \
  -H 'Content-Type: application/json' \
  -d '{"api_key": "client-id", "api_secret": "client-secret"}'
```

```json
{ "valid": true, "message": "Sentinel Hub credentials are valid", "error": null }
```

Sentinel Hub needs both `api_key` (the client ID) and `api_secret`; the check
performs a real OAuth2 client-credentials exchange.

### `GET /api/settings/defaults`

Recommended defaults and the catalogue of supported sources.

---

## Health

### `GET /api/health`

```json
{
  "status": "healthy",
  "version": "1.6.0",
  "jobs": { "total": 3, "active": 1 },
  "frontend_bundled": true
}
```

---

## Polling example

```python
import time
import requests

BASE = "http://localhost:8000/api"

job = requests.post(f"{BASE}/generate", json={
    "name": "san_francisco_downtown",
    "bbox": {"min_lat": 37.7749, "max_lat": 37.8049,
             "min_lon": -122.4294, "max_lon": -122.3994},
}).json()

job_id = job["map_id"]

while True:
    status = requests.get(f"{BASE}/status/{job_id}").json()
    print(f"{status['progress']:3d}%  {status['message']}")

    if status["status"] == "completed":
        archive = requests.get(f"{BASE}{status['download_url'][4:]}")
        open(f"{status['map_name']}.zip", "wb").write(archive.content)
        break

    if status["status"] in ("failed", "cancelled"):
        raise SystemExit(status["error"])

    time.sleep(2)
```

---

## Errors

| Status | When |
|---|---|
| `404` | Unknown job, missing artefact, or an unmatched `/api/` path. |
| `409` | Artefact requested for a job that failed or is still running; deleting a running job. |
| `422` | Request body failed validation. |
| `500` | Unexpected server error - check the server log. |

A generation that fails does **not** return an HTTP error: the request itself was
accepted, so the failure appears on the job as `status: "failed"` with `error`
set to an actionable message (for example, which data source needs configuring).
