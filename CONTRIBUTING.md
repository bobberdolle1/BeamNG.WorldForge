# Contributing

Thanks for wanting to help. This page covers how to get a working checkout, what
the tooling expects, and what a reviewable change looks like.

Be respectful, be constructive, be collaborative.

---

## Getting set up

You need Python 3.11 or 3.12 and Node.js 18+. **No API keys and no system GDAL.**
The default elevation source is anonymous, `rasterio` bundles GDAL in its wheels,
and every test that would touch the network is skipped by default — so a fresh
clone can run the whole suite offline.

```bash
git clone https://github.com/your-username/BeamNG.WorldForge.git
cd BeamNG.WorldForge

pip install -r backend/requirements-dev.txt   # runtime + pytest, ruff, PyInstaller
cd frontend && npm ci && cd ..

git checkout -b feature/your-feature-name
```

Run it:

```bash
cd backend && uvicorn main:app --reload    # :8000
cd frontend && npm run dev                 # :5173  <- open this one
```

[docs/SETUP.md](docs/SETUP.md) is the full configuration reference; Ollama and
data-source credentials are optional and only unlock the AI segmentation path.

---

## The checks

CI (`.github/workflows/ci.yml`) runs exactly these. Run them locally before
opening a PR and there are no surprises.

```bash
# Backend
ruff check backend
pytest -m "not network"

# Frontend
cd frontend
npm run lint
npm run typecheck
npm test
npm run build
```

Notes:

- **`-m "not network"` matters.** Tests marked `@pytest.mark.network` hit real
  geodata APIs. CI deselects them so a third-party outage cannot turn the build
  red. `conftest.py` additionally blocks outbound sockets in unmarked tests, so
  an accidentally-live test fails loudly instead of quietly depending on the
  internet.
- `ruff format --check` is **not** enforced yet. Reformatting the legacy modules
  would bury real changes under whitespace. Don't run `ruff format` on files your
  change doesn't already touch.
- `pytest` alone (without `-m`) runs the network tests too. That is worth doing
  once when you touch a data source client.

---

## Writing tests

Every behavioural change needs one. The bar is not coverage percentage, it is:
*would this test have failed before the fix?*

A few patterns this repo relies on:

- `tests/test_api_contract.py` pins every path the frontend calls to a route the
  backend actually declares. Renaming an endpoint on one side without the other
  fails here rather than in production.
- `tests/test_ai_pipeline.py` runs the full AI path with only the model call
  stubbed — parsing, rasterising, tracing, projecting and packaging are all real.
- `tests/test_project_structure.py` guards paths that the PyInstaller spec, the
  Dockerfiles and CI hard-code.

**Never widen an `except` to make a test pass.** The AI stage catches broadly so
that a flaky model does not fail a whole generation, but
`services/pipeline.py:_PROGRAMMING_ERRORS` deliberately re-raises `NameError`,
`AttributeError`, `TypeError`, `ImportError`, `IndexError` and `KeyError`. A
swallowed `NameError` is what made AI segmentation silently do nothing for every
user, twice.

Frontend tests use Vitest + Testing Library, with `axios-mock-adapter` for the
API boundary. Test behaviour through the rendered UI, not component internals.

---

## Style

**Python** — PEP 8, type hints, `from __future__ import annotations`. Ruff
enforces pycodestyle, pyflakes, import order, pyupgrade, bugbear, comprehensions
and simplification rules; line length is 100.

**TypeScript** — functional components, hooks, explicit prop interfaces. No
`any` that `unknown` plus a narrow would handle.

**Comments** explain *why*, not *what*. A comment that restates the line above it
is noise; a comment recording why a non-obvious choice was made is the most
valuable thing in the file. If you fix a bug in a subtle place, say what the bug
was — that is what stops it coming back.

**Geometry** goes through `backend/core/geo.py`. Longitude degrees are not
equally wide everywhere; the `cos(latitude)` factor was missing in four separate
places before that module existed. Don't reintroduce a fifth.

---

## Commits and pull requests

[Conventional Commits](https://www.conventionalcommits.org/):

```
feat(3d): add water rendering
fix(api): handle empty road data
docs: document the AWS Terrain default
refactor(terrain): drop the pydantic round-trip on the DEM grid
test(pipeline): cover the no-imagery degradation path
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`.

In the PR description, say what changed and how you verified it. "Verified" means
you ran something — paste the relevant output. If a claim is unverified, say so;
an honest "I could not test this in game" is worth more than a confident guess.

Update the docs in the same PR when behaviour changes. `tests/test_docs.py`
checks documentation against the code for a few classes of drift, but it cannot
tell that a paragraph is now describing the old UI.

---

## Where things live

```
backend/
├── api/routes/       FastAPI endpoints (thin: validate, delegate, respond)
├── core/             config, logging, paths, geo, projection — no business logic
├── models/           pydantic request/response models
└── services/
    ├── data_sources/     elevation and imagery clients + the auto-selection factory
    ├── terrain/          DEM → heightmap
    ├── vector_extraction/ masks → polylines and polygons
    ├── beamng_integration/ roads, buildings, meshes
    ├── export/           .ter writer, level layout, mod archive
    ├── ai_segmentation/  optional; imagery → detections
    ├── ollama/           model client and reply parsing
    ├── pipeline.py       the stage sequence — start here
    └── jobs.py           in-memory job registry with TTL cleanup

frontend/src/
├── components/       UI, including 3d/ for the Three.js preview
├── pages/            route-level screens
├── hooks/            useGenerationJob owns the polling lifecycle
├── lib/              pure helpers (selection maths, stage metadata)
├── services/api.ts   the only place that talks to the backend
└── i18n/locales/     en.json and ru.json — keep them in lockstep

tests/                backend suite (pytest); frontend tests sit beside their source
docs/                 see docs/ARCHITECTURE.md for how the pieces fit
```

`services/pipeline.py` is the best entry point for understanding the system: it
is the ordered list of everything that happens to a generation request.

---

## Good first contributions

- Water bodies and vegetation in the exported level
- In-game verification of the generated mod — the `.ter` binary format is
  community-documented and **has not been confirmed in BeamNG**. A report either
  way is genuinely valuable.
- More elevation sources, especially national high-resolution datasets
- Accessibility and mobile layout
- Translations beyond `en` and `ru` — see [docs/LOCALIZATION.md](docs/LOCALIZATION.md)

Check [GitHub Issues](https://github.com/bobberdolle1/BeamNG.WorldForge/issues)
before starting anything large, and open one to discuss the approach first.

---

## Resources

- [Architecture](docs/ARCHITECTURE.md)
- [API reference](docs/API.md)
- [Setup and configuration](docs/SETUP.md)
- [Data sources](docs/SETUP_DATA_SOURCES.md)
- [Building the executable](BUILD_INSTRUCTIONS.md)
