# Building the standalone executable

Most people do not need this page. The app runs fine from source or under
Docker - see [docs/SETUP.md](docs/SETUP.md). Build an executable when you want a
single folder you can hand to someone who has neither Python nor Node installed.

Pre-built Windows binaries:
<https://github.com/bobberdolle1/BeamNG.WorldForge/releases>

## Requirements

| | Version |
|---|---|
| Python | 3.11 or 3.12 |
| Node.js | 18+ |

No system GDAL. `rasterio` ships wheels with GDAL bundled, and the `GDAL` PyPI
package is deliberately not a dependency, so there is nothing to `apt-get`
beyond Python and Node.

```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get install -y python3.11 python3-pip nodejs npm

# Fedora/RHEL
sudo dnf install -y python3.11 python3-pip nodejs npm

# macOS
brew install python@3.11 node
```

## Build

```bash
git clone https://github.com/bobberdolle1/BeamNG.WorldForge.git
cd BeamNG.WorldForge

# requirements-dev.txt, not requirements.txt: PyInstaller is a build-time
# dependency and is no longer installed at runtime.
pip3 install -r backend/requirements-dev.txt

python3 build.py
```

`build.py` runs `npm ci` and `npm run build`, copies the bundle into
`backend/static` so the API serves the UI itself, then packages everything with
PyInstaller using `beamng-worldforge.spec`. The result is
`dist/BeamNG-WorldForge/`.

Useful flag: `python3 build.py --skip-frontend` reuses an existing
`frontend/dist` instead of rebuilding it, which turns a two-minute rebuild into
a ten-second one while you are iterating on the backend.

## Run it

```bash
cd dist/BeamNG-WorldForge
./BeamNG-WorldForge
```

A browser opens at <http://localhost:8000>. The bundled build stores its
`config/`, `output/` and `temp/` directories next to the executable, not in
whatever directory you happened to launch it from.

## Package for distribution

```bash
cd dist

# Linux
tar -czf BeamNG-WorldForge-Linux-x64.tar.gz BeamNG-WorldForge

# macOS
tar -czf BeamNG-WorldForge-macOS-x64.tar.gz BeamNG-WorldForge

# Windows (PowerShell)
Compress-Archive -Path BeamNG-WorldForge -DestinationPath BeamNG-WorldForge-Windows-x64.zip
```

PyInstaller does not cross-compile: a Linux build produces a Linux binary only.
The release workflow (`.github/workflows/build-release.yml`) builds all three on
their respective runners and attaches them to a tag.

Expect roughly 200-250 MB per platform. numpy, scipy, rasterio, OpenCV and
matplotlib account for nearly all of it.

## Troubleshooting

| Symptom | Cause |
|---|---|
| `PyInstaller is not installed` | You installed `requirements.txt`. Install `requirements-dev.txt`. |
| `npm not found on PATH` | Node.js is missing, or on Windows the shell has not picked up `npm.cmd`. Reopen the terminal. |
| Executable starts, then exits with `ModuleNotFoundError` | A dependency the spec does not collect. Add it to `hiddenimports` in `beamng-worldforge.spec`, or to the `collect_all` list if it ships compiled extensions. |
| macOS: `Permission denied` | `chmod +x BeamNG-WorldForge` |
| macOS: "App is damaged and can't be opened" | Gatekeeper quarantine on an unsigned binary: `xattr -cr BeamNG-WorldForge` |
| Windows: SmartScreen warning | The binary is unsigned. "More info" → "Run anyway". |

If the build fails and you only wanted to run the app, use Docker instead:

```bash
docker compose up
# http://localhost:5173
```
