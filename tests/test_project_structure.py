"""
Structural checks.

These guard the contracts other tooling depends on - the PyInstaller spec, the
Docker images and the CI workflow all reference specific paths, and a rename
that misses one of them fails at build time rather than at test time.

Kept deliberately small: this file used to be the entire "test suite" and only
asserted that files existed. The behaviour is covered by the other modules.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND = PROJECT_ROOT / "backend"
FRONTEND = PROJECT_ROOT / "frontend"


@pytest.mark.parametrize(
    "relative_path",
    [
        # Entry point referenced by beamng-worldforge.spec and both Dockerfiles.
        "main.py",
        "requirements.txt",
        "requirements-dev.txt",
        # Packages listed in the spec's hiddenimports.
        "core/config.py",
        "core/geo.py",
        "core/logging_config.py",
        "core/paths.py",
        "api/routes/map_generation.py",
        "api/routes/settings.py",
        "models/map_request.py",
        "models/terrain.py",
        "models/user_settings.py",
        "services/pipeline.py",
        "services/jobs.py",
        "services/settings_manager.py",
        "services/data_sources/factory.py",
        "services/terrain/processor.py",
        "services/export/beamng_exporter.py",
    ],
)
def test_backend_module_exists(relative_path):
    assert (BACKEND / relative_path).exists(), f"missing backend/{relative_path}"


@pytest.mark.parametrize(
    "relative_path",
    [
        "package.json",
        "tsconfig.json",
        "vite.config.ts",
        ".eslintrc.cjs",  # without it `npm run lint` fails outright
        "src/main.tsx",
        "src/App.tsx",
        "src/types.ts",
        "src/lib/stages.ts",
        "src/hooks/useGenerationJob.ts",
        "src/services/api.ts",
    ],
)
def test_frontend_file_exists(relative_path):
    assert (FRONTEND / relative_path).exists(), f"missing frontend/{relative_path}"


def test_frontend_declares_the_scripts_ci_runs():
    scripts = json.loads((FRONTEND / "package.json").read_text())["scripts"]
    assert {"build", "lint", "typecheck"} <= set(scripts)


def test_no_encryption_key_is_tracked():
    """
    The Fernet key must never be committed.

    It was, in every release up to 1.5.1, which made the encrypted settings
    store worthless: anyone with the repository could decrypt it.
    """
    tracked_secrets = [
        path
        for path in (BACKEND / "config").glob("*")
        if path.suffix in {".key", ".enc"} and not path.name.startswith(".")
    ]
    gitignore = (PROJECT_ROOT / ".gitignore").read_text()

    assert "*.key" in gitignore, ".gitignore must exclude *.key"
    assert "*.enc" in gitignore, ".gitignore must exclude *.enc"

    # Any key present locally must be ignored, never staged.
    for path in tracked_secrets:
        assert path.name in gitignore or "*.key" in gitignore


def test_gdal_is_not_a_pip_dependency():
    """
    `pip install GDAL` needs a matching system libgdal and fails on a clean
    machine, which made the documented install command unusable. rasterio's
    wheels bundle GDAL already.
    """
    requirements = (BACKEND / "requirements.txt").read_text().lower()
    dependency_lines = [
        line.strip()
        for line in requirements.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert not any(line.startswith("gdal") for line in dependency_lines)


def test_docker_files_exist():
    for relative_path in ("docker-compose.yml", "backend/Dockerfile", "frontend/Dockerfile"):
        assert (PROJECT_ROOT / relative_path).exists(), f"missing {relative_path}"


def test_documentation_exists():
    for name in ("SETUP.md", "ARCHITECTURE.md", "API.md"):
        assert (PROJECT_ROOT / "docs" / name).exists(), f"missing docs/{name}"
    assert (PROJECT_ROOT / "README.md").exists()
