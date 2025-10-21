"""
BeamNG.WorldForge - Backend API Server
FastAPI application for generating BeamNG.drive maps from satellite data
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import uvicorn

from api.routes import map_generation
from services.gee.client import initialize_gee

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

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "name": "BeamNG.WorldForge API",
        "version": "0.1.0 (MVP)",
        "status": "running",
        "stage": "MVP - Basic terrain generation"
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
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

