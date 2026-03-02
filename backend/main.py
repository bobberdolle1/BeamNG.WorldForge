"""
BeamNG.WorldForge - Backend API Server
FastAPI application for generating BeamNG.drive maps from satellite data
"""

import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn

from api.routes import map_generation, settings
from services.gee.client import initialize_gee

# Determine if running as PyInstaller bundle
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
    STATIC_DIR = BASE_DIR / "static"
else:
    BASE_DIR = Path(__file__).parent
    STATIC_DIR = BASE_DIR / "static"

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the application"""
    # Startup
    print("🚀 Starting BeamNG.WorldForge Backend...")
    try:
        initialize_gee()
        print("✅ Google Earth Engine initialized")
    except Exception as e:
        print(f"⚠️  Warning: GEE initialization failed: {e}")
        print("   The app will start but GEE features won't work")
    
    yield
    
    # Shutdown
    print("👋 Shutting down BeamNG.WorldForge Backend...")

# Create FastAPI app
app = FastAPI(
    title="BeamNG.WorldForge API",
    description="API for generating BeamNG.drive maps from satellite data",
    version="0.1.0 (MVP)",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(map_generation.router, prefix="/api", tags=["map-generation"])
app.include_router(settings.router, tags=["settings"])

# Serve frontend static files if available
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")
    
    @app.get("/")
    async def serve_frontend():
        """Serve frontend index.html"""
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return {"name": "BeamNG.WorldForge API", "version": "1.5.0", "status": "running"}
    
    @app.get("/{full_path:path}")
    async def serve_frontend_routes(full_path: str):
        """Serve frontend for all routes (SPA support)"""
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        
        file_path = STATIC_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        
        raise HTTPException(status_code=404, detail="Not found")
else:
    @app.get("/")
    async def root():
        """Health check endpoint"""
        return {
            "name": "BeamNG.WorldForge API",
            "version": "1.5.0",
            "status": "running",
            "mode": "API-only (no frontend)"
        }

@app.get("/api/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "services": {
            "api": "online",
            "gee": "configured"  # Will add actual check later
        }
    }

if __name__ == "__main__":
    import webbrowser
    import time
    from threading import Timer
    
    port = 8000
    is_bundled = getattr(sys, 'frozen', False)
    
    if is_bundled:
        # Open browser after server starts
        def open_browser():
            time.sleep(2)
            webbrowser.open(f"http://localhost:{port}")
        
        Timer(1, open_browser).start()
        print(f"\n🌍 BeamNG.WorldForge v1.5.0")
        print(f"🚀 Starting server on http://localhost:{port}")
        print(f"🌐 Browser will open automatically...\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )

