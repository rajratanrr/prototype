"""
GeoMines-AI — Pydantic Schemas for API Request/Response Models
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum


class SensorType(str, Enum):
    sentinel2 = "sentinel2"
    aster = "aster"
    sar = "sar"
    dem = "dem"


class AnalysisRequest(BaseModel):
    """Request body for starting an analysis."""
    aoi_name: str = Field(default="Nagpur-Balaghat Belt", description="Human-readable name for the area")
    center_lat: float = Field(default=21.5, ge=-90, le=90)
    center_lon: float = Field(default=79.5, ge=-180, le=180)
    radius_km: float = Field(default=30, ge=1, le=500)
    sensors: List[SensorType] = Field(default=[SensorType.sentinel2, SensorType.sar, SensorType.dem])


class JobStatus(BaseModel):
    """Job status response."""
    job_id: str
    status: str  # "queued", "processing", "completed", "failed"
    progress: int = Field(ge=0, le=100)
    message: str = ""


class DrillTarget(BaseModel):
    """Single drill target output."""
    rank: int
    latitude: float
    longitude: float
    mpi_score: float
    confidence_percent: float
    top_shap_factor: str
    recommended_depth_m: int


class ShapImportance(BaseModel):
    """SHAP feature importance."""
    feature_name: str
    importance: float


class AnalysisResult(BaseModel):
    """Complete analysis result."""
    job_id: str
    status: str
    aoi_name: str
    total_area_sq_km: float
    high_mpi_area_percent: float
    num_drill_targets: int
    drill_targets: List[DrillTarget]
    shap_importance: Dict[str, float]
    mpi_heatmap_data: List[List[float]]  # 2D array for frontend rendering
    grid_bounds: Dict[str, float]  # min_lat, max_lat, min_lon, max_lon


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    version: str = "1.0.0"
    demo_mode: bool = True
