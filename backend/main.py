"""
GeoMines-AI — FastAPI Application Entry Point
==============================================
Multi-Sensor Space-Tech & Deep Learning Mineral Prospectivity Platform
SIH26009 | Ministry of Steel, Government of India

Run:
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import router
from backend.config import FRONTEND_URL, DEMO_MODE

app = FastAPI(
    title="GeoMines-AI API",
    description="AI-powered Mineral Prospectivity Mapping Platform for Manganese Exploration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow frontend dev server and production Netlify URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL,
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        # Netlify deploy previews and production URLs
        "https://*.netlify.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """Log startup info."""
    mode = "🟢 DEMO MODE" if DEMO_MODE else "🔴 LIVE MODE (GEE required)"
    print(f"\n{'='*60}")
    print(f"  🛰️  GeoMines-AI Backend Starting...")
    print(f"  Mode: {mode}")
    print(f"  Docs: http://localhost:8000/docs")
    print(f"  API:  http://localhost:8000/api/health")
    print(f"{'='*60}\n")
