#!/usr/bin/env python3
"""
Build script for BeamNG.WorldForge standalone executable
Builds frontend, packages backend with PyInstaller
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

def run_command(cmd, cwd=None):
    """Execute shell command"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result.stdout

def build_frontend():
    """Build React frontend"""
    print("\n=== Building Frontend ===")
    frontend_dir = Path("frontend")
    
    if not (frontend_dir / "node_modules").exists():
        print("Installing frontend dependencies...")
        run_command("npm install", cwd=frontend_dir)
    
    print("Building frontend...")
    run_command("npm run build", cwd=frontend_dir)
    
    dist_dir = frontend_dir / "dist"
    if not dist_dir.exists():
        print("Error: Frontend build failed - dist directory not found")
        sys.exit(1)
    
    print(f"Frontend built successfully: {dist_dir}")
    return dist_dir

def prepare_backend():
    """Prepare backend for packaging"""
    print("\n=== Preparing Backend ===")
    backend_dir = Path("backend")
    
    # Copy frontend dist to backend
    frontend_dist = Path("frontend/dist")
    backend_static = backend_dir / "static"
    
    if backend_static.exists():
        shutil.rmtree(backend_static)
    
    shutil.copytree(frontend_dist, backend_static)
    print(f"Copied frontend to: {backend_static}")
    
    return backend_dir

def build_executable(backend_dir):
    """Build executable with PyInstaller"""
    print("\n=== Building Executable ===")
    
    spec_file = Path("beamng-worldforge.spec")
    if not spec_file.exists():
        print("Error: beamng-worldforge.spec not found")
        sys.exit(1)
    
    run_command(f"pyinstaller {spec_file} --clean --noconfirm")
    
    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("Error: Build failed - dist directory not found")
        sys.exit(1)
    
    print(f"Executable built successfully in: {dist_dir}")

def main():
    """Main build process"""
    print("=== BeamNG.WorldForge Build Script ===")
    
    # Check if pyinstaller is installed
    try:
        subprocess.run(["pyinstaller", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: PyInstaller not found. Install with: pip install pyinstaller")
        sys.exit(1)
    
    # Build steps
    build_frontend()
    backend_dir = prepare_backend()
    build_executable(backend_dir)
    
    print("\n=== Build Complete ===")
    print("Executable location: dist/BeamNG-WorldForge")

if __name__ == "__main__":
    main()
