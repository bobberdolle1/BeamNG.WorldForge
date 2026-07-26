# Setup and configuration

For the fastest path to a first map, see [QUICKSTART](QUICKSTART.md), which is
bilingual. This page is the configuration reference: every option, where state
lives, and how to run the app in each supported way.

## Requirements

| | Needed for |
|---|---|
| Python 3.11 or 3.12 | Backend |
| Node.js 18+ | Frontend (not needed if you only run the standalone build) |
| Docker + Compose | The containerised path, instead of the two above |

No system GDAL. `rasterio` ships wheels with GDAL bundled, and the `GDAL` PyPI
package - which does need system libraries and a compiler - is deliberately not
a dependency.

No API keys either. The default elevation source is anonymous.

## Install

```bash
git clone https://github.com/bobberdolle1/BeamNG.WorldForge
cd BeamNG.WorldForge

pip install -r backend/requirements.txt          # runtime
pip install -r backend/requirements-dev.txt      # + tests, linter, PyInstaller
```

Dependencies are pinned in those two files. `backend/pyproject.toml` carries
packaging metadata and the ruff configuration, and reads its dependency list
from `requirements.txt` so the two cannot disagree.

Frontend:

```bash
cd frontend && npm ci
```

## Running

### Two dev servers

```bash
cd backend && uvicorn main:app --reload        # http://localhost:8000
cd frontend && npm run dev                     # http://localhost:5173
```

Open the Vite server on :5173. It proxies `/api` to the backend, so both are
same-origin from the browser's point of view.

### Docker

```bash
docker compose up
```

Backend on :8000, frontend on :5173. Generated data lives in named volumes
(`worldforge-config`, `worldforge-output`, `worldforge-temp`), so rebuilding the
image does not discard finished maps or the encrypted settings file.

### Single process

```bash
python build.py            # builds the frontend into backend/static
cd backend && uvicorn main:app
```

The API then serves the UI itself at http://localhost:8000. This is also what
the standalone executable does - see
[BUILD_INSTRUCTIONS](../BUILD_INSTRUCTIONS.md).

## Configuration

Every setting is an environment variable, read at startup and validated. An
unrecognised value fails immediately rather than silently falling back to a
default deep inside a service. Copy `backend/.env.example` to `backend/.env` to
set them from a file.

API keys can also be entered in the Settings page, where they are encrypted at
rest. Environment variables take precedence over stored values.

### Server

| Variable | Default | Notes |
|---|---|---|
| `API_HOST` | `127.0.0.1` | Use `0.0.0.0` only when you intend to expose the API. There is **no authentication** on any endpoint. |
| `API_PORT` | `8000` | |
| `LOG_LEVEL` | `INFO` | `CRITICAL`, `ERROR`, `WARNING`, `INFO`, `DEBUG` |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Comma-separated browser origins |

### Storage

| Variable | Default | Notes |
|---|---|---|
| `OUTPUT_DIR` | `output` | Finished mod archives |
| `TEMP_DIR` | `temp` | Heightmaps, previews, masks |
| `CONFIG_DIR` | `config` | Encryption key and encrypted settings |
| `JOB_RETENTION_SECONDS` | `86400` | How long a finished job and its files are kept |
| `MAX_CONCURRENT_JOBS` | `2` | Each running job holds a full DEM in memory |

Relative paths resolve against the `backend` directory - or, in the standalone
executable, against the directory holding the executable. Never against the
shell's working directory, so it does not matter where you start the server
from.

### Generation defaults

| Variable | Default | Notes |
|---|---|---|
| `DEFAULT_DATA_SOURCE` | `auto` | `auto`, `aws_terrain`, `opentopography`, `sentinel_hub`, `azure_maps`, `google_earth_engine` |
| `DEFAULT_IMAGE_SOURCE` | `sentinel_hub` | Only used by AI segmentation |
| `UI_LANGUAGE` | `en` | `en` or `ru` |

### Data source credentials

All optional. See [SETUP_DATA_SOURCES](SETUP_DATA_SOURCES.md) for what each one
buys you and how to obtain it.

```env
OPENTOPOGRAPHY_API_KEY=
SENTINEL_HUB_CLIENT_ID=
SENTINEL_HUB_CLIENT_SECRET=
AZURE_MAPS_SUBSCRIPTION_KEY=
GEE_SERVICE_ACCOUNT_KEY=config/gee-key.json
GEE_PROJECT_ID=
```

### AI segmentation

Off by default. Needs [Ollama](https://ollama.ai/) running locally; without it
generation still succeeds and simply detects nothing.

```env
OLLAMA_HOST=http://localhost:11434
OLLAMA_VL_MODEL=qwen3-vl:235b-cloud
```

## Where state lives

```
backend/
├── config/
│   ├── settings.key          Fernet key - git-ignored, never commit or ship it
│   └── user_settings.enc     Encrypted API keys and preferences
├── output/<map>.zip          Finished mods
└── temp/<map>/               Heightmap, preview, masks, vectors
```

`config/settings.key` is generated on first run with `0600` permissions. It
decrypts `user_settings.enc`: anyone holding it can read every stored key.

## Verifying the install

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/data-sources     # aws_terrain should be available
```

```bash
pytest -m "not network"    # backend suite
cd frontend && npm test    # frontend suite
```

## Troubleshooting

| Symptom | Cause |
|---|---|
| `pip install` fails building GDAL | An old `requirements.txt`. Current versions do not depend on the GDAL package; pull and reinstall. |
| "No elevation data source is available" | The AWS bucket is unreachable. Check outbound HTTPS, or configure another source in Settings. |
| Frontend loads but every request fails | Backend not running, or `VITE_API_URL` points at a host the browser cannot reach. Check `/api/health` directly. |
| Settings save but generation ignores them | Fixed in 1.6.0 - upgrade. Data sources used to read only environment variables. |
| `docker compose up` aborts on a missing `.env` | Fixed in 1.6.0; the file is optional now. |
| Everything works but the level is empty in game | Expected until the `.ter` format is confirmed. Import `heightmap.png` through the World Editor using the values in the archive's `WORLDFORGE.md`. |

## Production notes

There is no authentication, no rate limiting and no multi-user isolation. This
is a local tool. If you must expose it:

- Put it behind a reverse proxy that handles authentication.
- Keep `API_HOST` bound to localhost and let the proxy reach it.
- Jobs are held in memory, so run a single worker. Two uvicorn workers each get
  their own registry, and half the status polls would 404.
