"""
GeoMines-AI — API Routes
All endpoint handlers for the FastAPI backend.
"""
import json
import os
import uuid
import numpy as np
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import io
import csv

from backend.models.schemas import (
    AnalysisRequest, JobStatus, AnalysisResult, DrillTarget, HealthResponse
)
from backend.config import DEMO_DATA_DIR, DEMO_MODE, OUTPUTS_DIR

router = APIRouter()

# In-memory job store (use Redis/DB in production)
_jobs = {}


def _load_demo_results(job_id: str, aoi_name: str, request=None) -> AnalysisResult:
    """
    Load pre-computed demo data and ADAPT it to the selected AOI.
    Each region gets unique coordinates, scores, and SHAP rankings
    by using the AOI name as a deterministic seed for perturbation.
    """
    # ── AOI-specific configuration ──────────────────────────────
    AOI_PROFILES = {
        "Nagpur-Balaghat Belt": {
            "center_lat": 21.50, "center_lon": 79.50,
            "area_km": 1109, "high_mpi": 1.36,
            "top_minerals": "Braunite, Hausmannite",
            "geology": "Sausar Group metasediments",
            "shap_order": ["Mn_Index", "Fault_Density", "Fe_Ratio", "NDVI",
                           "Ferrous_Index", "Magnetic_Anomaly", "Slope", "Clay_Index"],
        },
        "Dharwar Belt (Karnataka)": {
            "center_lat": 15.30, "center_lon": 75.70,
            "area_km": 870, "high_mpi": 0.92,
            "top_minerals": "Pyrolusite, Psilomelane",
            "geology": "Dharwar Supergroup volcano-sedimentary",
            "shap_order": ["Fe_Ratio", "Mn_Index", "Clay_Index", "Fault_Density",
                           "NDVI", "Slope", "Ferrous_Index", "Magnetic_Anomaly"],
        },
        "Iron Ore Group (Odisha)": {
            "center_lat": 22.00, "center_lon": 85.50,
            "area_km": 1340, "high_mpi": 0.78,
            "top_minerals": "Pyrolusite, Manganite",
            "geology": "Banded Iron Formation (BIF) associated",
            "shap_order": ["Magnetic_Anomaly", "Fe_Ratio", "Mn_Index", "Slope",
                           "Fault_Density", "NDVI", "Clay_Index", "Ferrous_Index"],
        },
        "Singhbhum Belt (Jharkhand)": {
            "center_lat": 22.40, "center_lon": 86.20,
            "area_km": 650, "high_mpi": 0.61,
            "top_minerals": "Braunite, Rhodonite",
            "geology": "Precambrian Iron Ore Group",
            "shap_order": ["Fault_Density", "Magnetic_Anomaly", "Fe_Ratio", "Mn_Index",
                           "Clay_Index", "NDVI", "Ferrous_Index", "Slope"],
        },
    }

    # Get profile for selected AOI (fallback to Nagpur-Balaghat)
    profile = AOI_PROFILES.get(aoi_name, AOI_PROFILES["Nagpur-Balaghat Belt"])
    center_lat = profile["center_lat"]
    center_lon = profile["center_lon"]

    # Use request coordinates if provided
    if request:
        center_lat = request.center_lat
        center_lon = request.center_lon

    # ── Deterministic seed from AOI name ────────────────────────
    seed = sum(ord(c) for c in aoi_name) % 10000
    rng = np.random.RandomState(seed)

    # ── Load base MPI heatmap and perturb it ────────────────────
    mpi_base = np.load(os.path.join(DEMO_DATA_DIR, "sample_mpi.npy"))

    # Roll/shift the heatmap to create a unique pattern per AOI
    shift_r = seed % mpi_base.shape[0]
    shift_c = (seed * 7) % mpi_base.shape[1]
    mpi = np.roll(np.roll(mpi_base, shift_r, axis=0), shift_c, axis=1)

    # Add slight noise so it's not identical
    noise = rng.uniform(-0.05, 0.05, mpi.shape)
    mpi = np.clip(mpi + noise, 0, 1)

    # Adjust intensity based on region's prospectivity
    intensity_factor = profile["high_mpi"] / 1.36  # normalize to Nagpur baseline
    mpi = np.clip(mpi * (0.7 + 0.3 * intensity_factor), 0, 1)

    # ── Compute grid bounds centered on the selected AOI ────────
    pixel_deg = 0.001
    grid_size = mpi.shape[0]
    half_span = (grid_size / 2) * pixel_deg
    grid_bounds = {
        "min_lat": round(center_lat - half_span, 5),
        "max_lat": round(center_lat + half_span, 5),
        "min_lon": round(center_lon - half_span, 5),
        "max_lon": round(center_lon + half_span, 5),
    }

    # ── Generate region-specific drill targets ──────────────────
    mpi_copy = mpi.copy()
    targets = []
    top_factors = [
        f"Strong {profile['top_minerals'].split(',')[0]} spectral anomaly",
        f"Fault intersection + magnetic high in {profile['geology']}",
        f"Fe-Mn oxide alteration zone detected",
        f"Low vegetation + high SWIR reflectance",
        f"Structural lineament convergence",
    ]

    for rank in range(1, 16):
        r, c = np.unravel_index(np.argmax(mpi_copy), mpi_copy.shape)
        score = float(mpi_copy[r, c])

        # Convert pixel to lat/lon in this AOI's grid
        t_lat = round(grid_bounds["min_lat"] + r * pixel_deg, 4)
        t_lon = round(grid_bounds["min_lon"] + c * pixel_deg, 4)

        targets.append(DrillTarget(
            rank=rank,
            latitude=t_lat,
            longitude=t_lon,
            mpi_score=round(score, 4),
            confidence_percent=round(min(score * 100 + rng.uniform(-8, 3), 99), 1),
            top_shap_factor=top_factors[(rank - 1) % len(top_factors)],
            recommended_depth_m=int(rng.uniform(25, 160)),
        ))

        # Suppress neighborhood to find next distinct peak
        r_min, r_max = max(0, r - 15), min(grid_size, r + 15)
        c_min, c_max = max(0, c - 15), min(grid_size, c + 15)
        mpi_copy[r_min:r_max, c_min:c_max] = 0

    # ── Build region-specific SHAP importance ───────────────────
    base_values = [1.7, 1.5, 1.3, 1.1, 0.7, 0.4, 0.35, 0.22]
    shap_imp = {}
    for i, feat in enumerate(profile["shap_order"]):
        val = base_values[i] + rng.uniform(-0.15, 0.15)
        shap_imp[feat] = round(val, 4)

    # ── Downsample heatmap for JSON transfer ────────────────────
    step = max(1, mpi.shape[0] // 100)
    mpi_small = mpi[::step, ::step].tolist()

    high_mpi_pct = float((mpi > 0.7).sum() / mpi.size * 100)

    return AnalysisResult(
        job_id=job_id,
        status="completed",
        aoi_name=aoi_name,
        total_area_sq_km=profile["area_km"],
        high_mpi_area_percent=round(high_mpi_pct, 2),
        num_drill_targets=len(targets),
        drill_targets=targets,
        shap_importance=shap_imp,
        mpi_heatmap_data=mpi_small,
        grid_bounds=grid_bounds,
    )


# ─── Endpoints ───────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="ok", version="1.0.0", demo_mode=DEMO_MODE)


@router.post("/analyze", response_model=JobStatus)
async def start_analysis(request: AnalysisRequest):
    """Start a new mineral prospectivity analysis."""
    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {
        "status": "completed",  # Demo mode: instant completion
        "progress": 100,
        "aoi_name": request.aoi_name,
        "request": request,
    }
    return JobStatus(
        job_id=job_id,
        status="completed",
        progress=100,
        message="Analysis complete (demo mode)"
    )


@router.get("/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Check the status of an analysis job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    job = _jobs[job_id]
    return JobStatus(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        message="Analysis complete" if job["status"] == "completed" else "Processing..."
    )


@router.get("/results/{job_id}", response_model=AnalysisResult)
async def get_results(job_id: str):
    """Get analysis results for a completed job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    job = _jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not yet completed")

    return _load_demo_results(job_id, job["aoi_name"], request=job.get("request"))


@router.get("/download/{job_id}/{fmt}")
async def download_results(job_id: str, fmt: str):
    """Download results in specified format (csv, kml, json)."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Load targets
    with open(os.path.join(DEMO_DATA_DIR, "sample_targets.json")) as f:
        targets = json.load(f)

    if fmt == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=targets[0].keys())
        writer.writeheader()
        writer.writerows(targets)
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=drill_targets_{job_id}.csv"}
        )

    elif fmt == "kml":
        try:
            import simplekml
            kml = simplekml.Kml()
            kml.document.name = "GeoMines-AI Drill Targets"
            for t in targets:
                pnt = kml.newpoint(
                    name=f"Target #{t['rank']} (MPI: {t['mpi_score']})",
                    coords=[(t["longitude"], t["latitude"])],
                    description=f"MPI Score: {t['mpi_score']}\nConfidence: {t['confidence_percent']}%\nTop Factor: {t['top_shap_factor']}\nRecommended Depth: {t['recommended_depth_m']}m"
                )
                pnt.style.iconstyle.color = simplekml.Color.red
                pnt.style.iconstyle.scale = 1.2
            kml_str = kml.kml()
            return StreamingResponse(
                io.BytesIO(kml_str.encode()),
                media_type="application/vnd.google-earth.kml+xml",
                headers={"Content-Disposition": f"attachment; filename=drill_targets_{job_id}.kml"}
            )
        except ImportError:
            raise HTTPException(status_code=500, detail="simplekml not installed")

    elif fmt == "json":
        return JSONResponse(content=targets)

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {fmt}. Use csv, kml, or json.")


@router.get("/demo/mines")
async def get_mine_locations():
    """Return known MOIL mine locations for map display."""
    mines_file = os.path.join(os.path.dirname(DEMO_DATA_DIR), "mine_locations.json")
    if os.path.exists(mines_file):
        with open(mines_file) as f:
            # Skip the first line (docstring comment) if needed
            content = f.read()
            # Find the JSON array
            start = content.find("[")
            if start >= 0:
                return json.loads(content[start:])
    # Fallback hardcoded
    return [
        {"name": "Dongri Buzurg", "lat": 21.68, "lon": 80.22, "mineral": "Braunite"},
        {"name": "Balaghat", "lat": 21.81, "lon": 80.19, "mineral": "Braunite + Pyrolusite"},
        {"name": "Gumgaon", "lat": 21.14, "lon": 79.06, "mineral": "Pyrolusite"},
        {"name": "Kandri", "lat": 21.42, "lon": 79.28, "mineral": "Braunite"},
        {"name": "Chikla", "lat": 21.53, "lon": 79.38, "mineral": "Braunite"},
        {"name": "Tirodi", "lat": 21.72, "lon": 79.72, "mineral": "Braunite"},
    ]
