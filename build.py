#!/usr/bin/env python3
"""
Build the standalone BeamNG.WorldForge executable.

Builds the React frontend, copies it into ``backend/static`` so the API can
serve it, then packages everything with PyInstaller.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / "frontend"
BACKEND_DIR = ROOT / "backend"
SPEC_FILE = ROOT / "beamng-worldforge.spec"


def run(command: list[str], cwd: Path | None = None) -> None:
    """
    Run a command, streaming its output.

    Output is streamed rather than captured: the previous version buffered
    everything with ``capture_output=True``, so a ten-minute PyInstaller run
    looked frozen and, on failure, printed only stderr with no build context.
    """
    printable = " ".join(command)
    print(f"\n$ {printable}", flush=True)

    # shell=False: the command is a list, so arguments containing spaces (a
    # checkout under "C:\\Program Files", for instance) no longer break.
    result = subprocess.run(command, cwd=cwd, shell=False)
    if result.returncode != 0:
        sys.exit(f"Command failed with exit code {result.returncode}: {printable}")


def npm_command() -> str:
    """Resolve the npm executable, accounting for npm.cmd on Windows."""
    for candidate in ("npm.cmd", "npm") if sys.platform == "win32" else ("npm",):
        if shutil.which(candidate):
            return candidate
    sys.exit("npm not found on PATH. Install Node.js 18+ and try again.")


def build_frontend() -> Path:
    """Install dependencies if needed and produce the production bundle."""
    print("\n=== Building frontend ===")
    npm = npm_command()

    if not (FRONTEND_DIR / "node_modules").exists():
        # `npm ci` for a reproducible install from the lockfile; fall back to
        # `npm install` when the lockfile is missing or out of sync.
        if (FRONTEND_DIR / "package-lock.json").exists():
            run([npm, "ci"], cwd=FRONTEND_DIR)
        else:
            run([npm, "install"], cwd=FRONTEND_DIR)

    run([npm, "run", "build"], cwd=FRONTEND_DIR)

    dist_dir = FRONTEND_DIR / "dist"
    if not (dist_dir / "index.html").exists():
        sys.exit(f"Frontend build produced no index.html in {dist_dir}")

    print(f"Frontend built: {dist_dir}")
    return dist_dir


def stage_frontend(dist_dir: Path) -> None:
    """Copy the frontend bundle to where the backend serves it from."""
    print("\n=== Staging frontend into backend/static ===")
    static_dir = BACKEND_DIR / "static"

    if static_dir.exists():
        shutil.rmtree(static_dir)
    shutil.copytree(dist_dir, static_dir)

    print(f"Copied {dist_dir} -> {static_dir}")


def build_executable() -> None:
    """Package the backend with PyInstaller."""
    print("\n=== Building executable ===")

    if not SPEC_FILE.exists():
        sys.exit(f"Spec file not found: {SPEC_FILE}")

    # Invoked as a module so the PyInstaller matching *this* interpreter is
    # used. Calling the `pyinstaller` script picks up whichever copy is first
    # on PATH, which in a virtualenv-less setup can be a different Python.
    run([sys.executable, "-m", "PyInstaller", str(SPEC_FILE), "--clean", "--noconfirm"], cwd=ROOT)

    output = ROOT / "dist" / "BeamNG-WorldForge"
    if not output.exists():
        sys.exit(f"Build finished but {output} does not exist")

    print(f"Executable built: {output}")


def check_pyinstaller() -> None:
    """Fail early with an actionable message if PyInstaller is missing."""
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        sys.exit(
            "PyInstaller is not installed.\n"
            "Install the development requirements:\n"
            "    pip install -r backend/requirements-dev.txt"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-frontend",
        action="store_true",
        help="Reuse the existing frontend/dist build instead of rebuilding it",
    )
    args = parser.parse_args()

    print("=== BeamNG.WorldForge build ===")
    check_pyinstaller()

    if args.skip_frontend:
        dist_dir = FRONTEND_DIR / "dist"
        if not (dist_dir / "index.html").exists():
            sys.exit("--skip-frontend was passed but frontend/dist has no build")
    else:
        dist_dir = build_frontend()

    stage_frontend(dist_dir)
    build_executable()

    print("\n=== Build complete ===")
    print("Run it with: dist/BeamNG-WorldForge/BeamNG-WorldForge")


if __name__ == "__main__":
    main()
