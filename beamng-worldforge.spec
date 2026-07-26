# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the standalone BeamNG.WorldForge executable.

Run via ``python build.py`` rather than invoking PyInstaller directly - the
build script produces the frontend bundle this spec expects at
``backend/static``.
"""

import os

from PyInstaller.utils.hooks import collect_all

# The scientific stack reaches its C-extension layer through dynamic imports
# that PyInstaller's static analysis cannot follow, so the pieces have to be
# collected explicitly. Without this the executable builds fine and then dies
# on startup with errors like "No module named 'numpy._core._exceptions'" or
# "The scipy install you are using seems to be broken".
_COLLECTED_DATAS = []
_COLLECTED_BINARIES = []
_COLLECTED_HIDDEN = []

for _package in ("numpy", "scipy", "rasterio", "matplotlib", "PIL"):
    _datas, _binaries, _hidden = collect_all(_package)
    _COLLECTED_DATAS += _datas
    _COLLECTED_BINARIES += _binaries
    _COLLECTED_HIDDEN += _hidden

# ``backend`` must be importable as the application root: main.py does
# ``from api.routes import ...``, which only resolves with backend/ on the path.
BACKEND_DIR = os.path.join(SPECPATH, "backend")

a = Analysis(
    [os.path.join("backend", "main.py")],
    pathex=[BACKEND_DIR],
    binaries=_COLLECTED_BINARIES,
    datas=[
        *_COLLECTED_DATAS,
        # The compiled frontend. Everything else in `backend/` is picked up as
        # Python modules by the import analysis below.
        (os.path.join("backend", "static"), "static"),
    ],
    # NOTE: `backend/config` is deliberately NOT bundled. It holds settings.key
    # (the Fernet key) and user_settings.enc. Shipping them would hand every
    # person who downloads a release the same encryption key - and with it the
    # ability to decrypt any other user's stored API keys. The config directory
    # is created next to the executable on first run instead.
    hiddenimports=[
        # uvicorn resolves these dynamically, so static analysis misses them.
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        # Application packages reached only through late imports in the pipeline.
        "core.config",
        "core.geo",
        "core.logging_config",
        "core.paths",
        "services.data_sources.sentinel_hub_client",
        "services.data_sources.opentopography_client",
        "services.data_sources.azure_maps_client",
        "services.data_sources.bing_maps_client",
        "services.data_sources.gee_adapter",
        # Third-party packages loaded lazily.
        "rasterio.sample",
        "rasterio.vrt",
        "rasterio._features",
        "matplotlib.backends.backend_agg",
        "scipy.ndimage",
        *_COLLECTED_HIDDEN,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Interactive matplotlib backends pull in Tk/Qt, which are never used:
        # the preview is rendered head-lessly through the Agg backend.
        "tkinter",
        "matplotlib.backends.backend_tkagg",
        "PyQt5",
        "PySide2",
        "pytest",
        # setuptools/pkg_resources is a build-time dependency that nothing here
        # imports at runtime. Bundling it makes PyInstaller inject its
        # pkg_resources runtime hook, which chains into `jaraco.context` ->
        # `backports.tarfile` on Python < 3.12 and crashes the executable at
        # startup with "No module named 'backports'". Excluding it drops ~10 MB
        # and removes the failure mode entirely.
        "setuptools",
        "pkg_resources",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BeamNG-WorldForge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=(
        os.path.join("frontend", "public", "icon.ico")
        if os.path.exists(os.path.join(SPECPATH, "frontend", "public", "icon.ico"))
        else None
    ),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="BeamNG-WorldForge",
)
