"""
Test script to verify BeamNG.WorldForge project structure
"""

import os
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

def test_backend_structure():
    """Test that all backend files exist"""
    backend = PROJECT_ROOT / "backend"
    
    required_files = [
        "main.py",
        "requirements.txt",
        "pyproject.toml",
        "api/__init__.py",
        "api/routes/__init__.py",
        "api/routes/map_generation.py",
        "models/__init__.py",
        "models/map_request.py",
        "models/terrain.py",
        "services/__init__.py",
        "services/gee/__init__.py",
        "services/gee/client.py",
        "services/terrain/__init__.py",
        "services/terrain/processor.py",
        "services/export/__init__.py",
        "services/export/beamng_exporter.py",
    ]
    
    for file_path in required_files:
        full_path = backend / file_path
        assert full_path.exists(), f"Missing: {file_path}"
        print(f"[OK] {file_path}")
    
    print("\n[PASS] Backend structure: OK")

def test_frontend_structure():
    """Test that all frontend files exist"""
    frontend = PROJECT_ROOT / "frontend"
    
    required_files = [
        "package.json",
        "tsconfig.json",
        "vite.config.ts",
        "index.html",
        "src/main.tsx",
        "src/App.tsx",
        "src/index.css",
        "src/types.ts",
        "src/components/Header.tsx",
        "src/components/MapSelector.tsx",
        "src/components/GenerationPanel.tsx",
        "src/services/api.ts",
    ]
    
    for file_path in required_files:
        full_path = frontend / file_path
        assert full_path.exists(), f"Missing: {file_path}"
        print(f"[OK] {file_path}")
    
    print("\n[PASS] Frontend structure: OK")

def test_documentation():
    """Test that documentation files exist"""
    docs = PROJECT_ROOT / "docs"
    
    required_files = [
        "SETUP.md",
        "ARCHITECTURE.md",
        "API.md",
    ]
    
    for file_path in required_files:
        full_path = docs / file_path
        assert full_path.exists(), f"Missing: {file_path}"
        print(f"[OK] {file_path}")
    
    # Check README
    readme = PROJECT_ROOT / "README.md"
    assert readme.exists(), "Missing README.md"
    print(f"[OK] README.md")
    
    print("\n[PASS] Documentation: OK")

def test_docker_files():
    """Test that Docker files exist"""
    required_files = [
        "docker-compose.yml",
        "backend/Dockerfile",
        "frontend/Dockerfile",
    ]
    
    for file_path in required_files:
        full_path = PROJECT_ROOT / file_path
        assert full_path.exists(), f"Missing: {file_path}"
        print(f"[OK] {file_path}")
    
    print("\n[PASS] Docker files: OK")

def main():
    print("=" * 60)
    print("BeamNG.WorldForge - Project Structure Test")
    print("=" * 60)
    print()
    
    try:
        test_backend_structure()
        print()
        test_frontend_structure()
        print()
        test_documentation()
        print()
        test_docker_files()
        
        print()
        print("=" * 60)
        print("SUCCESS: ALL TESTS PASSED!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Set up Google Earth Engine credentials")
        print("2. Install backend dependencies: cd backend && pip install -r requirements.txt")
        print("3. Install frontend dependencies: cd frontend && pnpm install")
        print("4. Run backend: cd backend && uvicorn main:app --reload")
        print("5. Run frontend: cd frontend && pnpm dev")
        print("6. Test in browser: http://localhost:5173")
        
        return 0
        
    except AssertionError as e:
        print(f"\nERROR: TEST FAILED: {e}")
        return 1

if __name__ == "__main__":
    exit(main())

