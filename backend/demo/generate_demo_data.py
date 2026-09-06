#!/usr/bin/env python3
"""
GeoMines-AI — Synthetic Demo Data Generator
=============================================
Generates realistic synthetic satellite-derived feature arrays,
trains an XGBoost model on known MOIL mine locations, and produces
a pre-computed MPI heatmap + ranked drill targets for the demo.

Run: python -m backend.demo.generate_demo_data
"""

import json
import os
import sys
import numpy as np
from scipy.ndimage import gaussian_filter
from sklearn.model_selection import train_test_split
import xgboost as xgb
import shap
import joblib

# ─── Constants ──────────────────────────────────────────────────────
GRID_SIZE = 300          # 300x300 pixel grid (~30km x 30km at 100m/px for demo)
CENTER_LAT = 21.50       # Center latitude (Sausar Belt, MP)
CENTER_LON = 79.50       # Center longitude
PIXEL_DEG = 0.001        # ~111m per pixel at this latitude
NUM_NEGATIVE = 800       # Negative training samples
SEED = 42
FEATURE_NAMES = [
    "Mn_Index", "Fe_Ratio", "Clay_Index", "Ferrous_Index",
    "NDVI", "Slope", "Fault_Density", "Magnetic_Anomaly"
]

# Real MOIL mine coordinates
MINE_LOCATIONS = [
    {"name": "Dongri Buzurg", "lat": 21.68, "lon": 80.22},
    {"name": "Balaghat", "lat": 21.81, "lon": 80.19},
    {"name": "Gumgaon", "lat": 21.14, "lon": 79.06},
    {"name": "Kandri", "lat": 21.42, "lon": 79.28},
    {"name": "Munsar", "lat": 21.18, "lon": 79.05},
    {"name": "Chikla", "lat": 21.53, "lon": 79.38},
    {"name": "Tirodi", "lat": 21.72, "lon": 79.72},
    {"name": "Sitapatore", "lat": 21.49, "lon": 79.34},
    {"name": "Beldongri", "lat": 21.56, "lon": 79.41},
    {"name": "Bharweli", "lat": 21.80, "lon": 80.18},
]

def get_output_dir():
    """Get the demo_data output directory."""
    base = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(base, "demo_data")
    os.makedirs(out, exist_ok=True)
    return out


def latlon_to_pixel(lat, lon):
    """Convert lat/lon to pixel coordinates in our grid."""
    min_lat = CENTER_LAT - (GRID_SIZE / 2) * PIXEL_DEG
    min_lon = CENTER_LON - (GRID_SIZE / 2) * PIXEL_DEG
    row = int((lat - min_lat) / PIXEL_DEG)
    col = int((lon - min_lon) / PIXEL_DEG)
    row = np.clip(row, 0, GRID_SIZE - 1)
    col = np.clip(col, 0, GRID_SIZE - 1)
    return row, col


def pixel_to_latlon(row, col):
    """Convert pixel coordinates back to lat/lon."""
    min_lat = CENTER_LAT - (GRID_SIZE / 2) * PIXEL_DEG
    min_lon = CENTER_LON - (GRID_SIZE / 2) * PIXEL_DEG
    lat = min_lat + row * PIXEL_DEG
    lon = min_lon + col * PIXEL_DEG
    return round(lat, 5), round(lon, 5)


def generate_base_noise(seed_offset=0):
    """Generate smooth Perlin-like noise using Gaussian-filtered random."""
    rng = np.random.RandomState(SEED + seed_offset)
    raw = rng.randn(GRID_SIZE, GRID_SIZE)
    smooth = gaussian_filter(raw, sigma=15)
    # Normalize to [0, 1]
    smooth = (smooth - smooth.min()) / (smooth.max() - smooth.min() + 1e-8)
    return smooth


def add_mine_blobs(grid, mines, intensity=0.6, sigma=8):
    """Add Gaussian blobs at mine locations to simulate elevated values."""
    result = grid.copy()
    for mine in mines:
        r, c = latlon_to_pixel(mine["lat"], mine["lon"])
        # Only add blob if mine falls within our grid
        if 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE:
            blob = np.zeros((GRID_SIZE, GRID_SIZE))
            blob[r, c] = intensity
            blob = gaussian_filter(blob, sigma=sigma)
            result += blob
    return np.clip(result, 0, 1)


def generate_feature_grids():
    """Generate 8 synthetic feature grids simulating real satellite-derived indices."""
    print("  📡 Generating synthetic spectral index grids...")

    features = {}

    # 1. Manganese Index — high near mines
    mn = generate_base_noise(0) * 0.3
    mn = add_mine_blobs(mn, MINE_LOCATIONS, intensity=0.9, sigma=6)
    features["Mn_Index"] = mn

    # 2. Iron Oxide Ratio — correlated with Mn but noisier
    fe = generate_base_noise(1) * 0.4
    fe = add_mine_blobs(fe, MINE_LOCATIONS, intensity=0.7, sigma=10)
    features["Fe_Ratio"] = fe

    # 3. Clay Alteration Index — moderately elevated near mines
    clay = generate_base_noise(2) * 0.5
    clay = add_mine_blobs(clay, MINE_LOCATIONS, intensity=0.5, sigma=12)
    features["Clay_Index"] = clay

    # 4. Ferrous Mineral Index — weaker correlation
    ferrous = generate_base_noise(3) * 0.6
    ferrous = add_mine_blobs(ferrous, MINE_LOCATIONS, intensity=0.4, sigma=8)
    features["Ferrous_Index"] = ferrous

    # 5. NDVI (vegetation) — LOWER near mines (exposed rock)
    ndvi = generate_base_noise(4) * 0.3 + 0.5  # mostly vegetated
    for mine in MINE_LOCATIONS:
        r, c = latlon_to_pixel(mine["lat"], mine["lon"])
        if 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE:
            blob = np.zeros((GRID_SIZE, GRID_SIZE))
            blob[r, c] = 0.4
            blob = gaussian_filter(blob, sigma=5)
            ndvi -= blob
    features["NDVI"] = np.clip(ndvi, 0, 1)

    # 6. Slope (terrain) — random geological terrain
    slope = generate_base_noise(5) * 0.6 + 0.1
    features["Slope"] = slope

    # 7. Fault Density — elevated along NE-SW lineament + near mines
    fault = generate_base_noise(6) * 0.2
    # Add a diagonal "fault" lineament
    for i in range(GRID_SIZE):
        j = int(i * 0.7 + GRID_SIZE * 0.15)
        if 0 <= j < GRID_SIZE:
            fault[i, max(0, j-3):min(GRID_SIZE, j+3)] += 0.3
    fault = gaussian_filter(fault, sigma=3)
    fault = add_mine_blobs(fault, MINE_LOCATIONS, intensity=0.6, sigma=7)
    features["Fault_Density"] = np.clip(fault, 0, 1)

    # 8. Magnetic Anomaly — strong positives at mine sites
    mag = generate_base_noise(7) * 0.3
    mag = add_mine_blobs(mag, MINE_LOCATIONS, intensity=0.8, sigma=5)
    features["Magnetic_Anomaly"] = mag

    return features


def create_training_data(features):
    """Create labeled training dataset from feature grids + mine locations."""
    print("  🏷️  Creating training dataset...")
    rng = np.random.RandomState(SEED)

    X_list = []
    y_list = []

    # Positive samples: pixels at/near mine locations
    for mine in MINE_LOCATIONS:
        r, c = latlon_to_pixel(mine["lat"], mine["lon"])
        # Sample the mine pixel + nearby pixels (augment)
        for dr in range(-5, 6, 2):
            for dc in range(-5, 6, 2):
                rr = np.clip(r + dr, 0, GRID_SIZE - 1)
                cc = np.clip(c + dc, 0, GRID_SIZE - 1)
                vec = [features[f][rr, cc] for f in FEATURE_NAMES]
                X_list.append(vec)
                y_list.append(1)

    n_pos = len(y_list)
    print(f"    Positive samples: {n_pos}")

    # Negative samples: random locations away from mines
    mine_pixels = set()
    for mine in MINE_LOCATIONS:
        r, c = latlon_to_pixel(mine["lat"], mine["lon"])
        for dr in range(-15, 16):
            for dc in range(-15, 16):
                mine_pixels.add((np.clip(r+dr, 0, GRID_SIZE-1),
                                 np.clip(c+dc, 0, GRID_SIZE-1)))

    neg_count = 0
    while neg_count < NUM_NEGATIVE:
        r = rng.randint(0, GRID_SIZE)
        c = rng.randint(0, GRID_SIZE)
        if (r, c) not in mine_pixels:
            vec = [features[f][r, c] for f in FEATURE_NAMES]
            X_list.append(vec)
            y_list.append(0)
            neg_count += 1

    print(f"    Negative samples: {NUM_NEGATIVE}")

    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.int32)
    return X, y


def train_model(X, y):
    """Train XGBoost binary classifier."""
    print("  🧠 Training XGBoost model...")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=SEED, stratify=y
    )

    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="binary:logistic",
        eval_metric="auc",
        random_state=SEED,
        use_label_encoder=False,
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    # Evaluate
    from sklearn.metrics import roc_auc_score, accuracy_score
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    acc = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)
    print(f"    Test Accuracy: {acc:.3f}")
    print(f"    Test AUC-ROC:  {auc:.3f}")

    return model


def generate_mpi_heatmap(model, features):
    """Run trained model on every pixel to produce MPI heatmap."""
    print("  🗺️  Generating MPI heatmap (this may take a moment)...")

    # Build feature matrix for all pixels
    all_pixels = np.zeros((GRID_SIZE * GRID_SIZE, len(FEATURE_NAMES)), dtype=np.float32)
    for i, fname in enumerate(FEATURE_NAMES):
        all_pixels[:, i] = features[fname].flatten()

    # Predict probabilities
    mpi_flat = model.predict_proba(all_pixels)[:, 1]
    mpi_grid = mpi_flat.reshape(GRID_SIZE, GRID_SIZE)

    # Smooth slightly for visual appeal
    mpi_grid = gaussian_filter(mpi_grid, sigma=1.5)
    mpi_grid = np.clip(mpi_grid, 0, 1)

    print(f"    MPI range: {mpi_grid.min():.3f} — {mpi_grid.max():.3f}")
    print(f"    High-MPI pixels (>0.7): {(mpi_grid > 0.7).sum()}")
    return mpi_grid


def compute_shap_values(model, features):
    """Compute SHAP values for global feature importance."""
    print("  📊 Computing SHAP feature importance...")

    # Use a subset for SHAP (faster)
    rng = np.random.RandomState(SEED)
    sample_rows = rng.randint(0, GRID_SIZE, 500)
    sample_cols = rng.randint(0, GRID_SIZE, 500)
    X_sample = np.zeros((500, len(FEATURE_NAMES)), dtype=np.float32)
    for i, fname in enumerate(FEATURE_NAMES):
        X_sample[:, i] = features[fname][sample_rows, sample_cols]

    explainer = shap.TreeExplainer(model)
    shap_vals = explainer.shap_values(X_sample)

    # Global importance (mean absolute SHAP)
    importance = np.abs(shap_vals).mean(axis=0)
    importance_dict = {}
    for i, fname in enumerate(FEATURE_NAMES):
        importance_dict[fname] = round(float(importance[i]), 4)

    # Sort by importance
    importance_dict = dict(sorted(importance_dict.items(), key=lambda x: -x[1]))
    print(f"    Feature importance: {importance_dict}")
    return importance_dict, shap_vals


def extract_drill_targets(mpi_grid, n_targets=15):
    """Extract top N drill target locations from MPI heatmap."""
    print(f"  📍 Extracting top {n_targets} drill targets...")

    targets = []
    # Create a copy to suppress already-found peaks
    mpi_copy = mpi_grid.copy()

    for rank in range(1, n_targets + 1):
        r, c = np.unravel_index(np.argmax(mpi_copy), mpi_copy.shape)
        score = float(mpi_copy[r, c])
        lat, lon = pixel_to_latlon(r, c)

        # Determine top contributing factor (simplified)
        if score > 0.8:
            top_factor = "Strong Mn-SWIR spectral anomaly"
        elif score > 0.6:
            top_factor = "Fault intersection + magnetic high"
        else:
            top_factor = "Moderate clay alteration signal"

        targets.append({
            "rank": rank,
            "latitude": lat,
            "longitude": lon,
            "mpi_score": round(score, 4),
            "confidence_percent": round(min(score * 100 + np.random.uniform(-5, 5), 99), 1),
            "top_shap_factor": top_factor,
            "recommended_depth_m": int(np.random.uniform(30, 150)),
        })

        # Suppress this peak's neighborhood to find next distinct peak
        r_min = max(0, r - 15)
        r_max = min(GRID_SIZE, r + 15)
        c_min = max(0, c - 15)
        c_max = min(GRID_SIZE, c + 15)
        mpi_copy[r_min:r_max, c_min:c_max] = 0

    for t in targets[:5]:
        print(f"    #{t['rank']}: ({t['latitude']}, {t['longitude']}) — MPI={t['mpi_score']}")

    return targets


def save_all(out_dir, features, model, mpi_grid, targets, shap_importance):
    """Save all generated data to disk."""
    print("  💾 Saving all demo data...")

    # Feature stack (8, H, W)
    feat_stack = np.stack([features[f] for f in FEATURE_NAMES], axis=0).astype(np.float32)
    np.save(os.path.join(out_dir, "sample_features.npy"), feat_stack)

    # MPI heatmap
    np.save(os.path.join(out_dir, "sample_mpi.npy"), mpi_grid.astype(np.float32))

    # Trained model
    joblib.dump(model, os.path.join(out_dir, "trained_model.joblib"))

    # Drill targets
    with open(os.path.join(out_dir, "sample_targets.json"), "w") as f:
        json.dump(targets, f, indent=2)

    # SHAP importance
    with open(os.path.join(out_dir, "shap_importance.json"), "w") as f:
        json.dump(shap_importance, f, indent=2)

    # Grid metadata
    meta = {
        "grid_size": GRID_SIZE,
        "center_lat": CENTER_LAT,
        "center_lon": CENTER_LON,
        "pixel_deg": PIXEL_DEG,
        "min_lat": CENTER_LAT - (GRID_SIZE / 2) * PIXEL_DEG,
        "max_lat": CENTER_LAT + (GRID_SIZE / 2) * PIXEL_DEG,
        "min_lon": CENTER_LON - (GRID_SIZE / 2) * PIXEL_DEG,
        "max_lon": CENTER_LON + (GRID_SIZE / 2) * PIXEL_DEG,
        "feature_names": FEATURE_NAMES,
    }
    with open(os.path.join(out_dir, "grid_metadata.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"  ✅ All files saved to: {out_dir}")


# ─── Main ────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  GeoMines-AI — Demo Data Generator")
    print("=" * 60)

    out_dir = get_output_dir()

    # Step 1: Generate synthetic feature grids
    features = generate_feature_grids()

    # Step 2: Create training data
    X, y = create_training_data(features)

    # Step 3: Train XGBoost
    model = train_model(X, y)

    # Step 4: Generate MPI heatmap
    mpi_grid = generate_mpi_heatmap(model, features)

    # Step 5: Compute SHAP
    shap_importance, _ = compute_shap_values(model, features)

    # Step 6: Extract drill targets
    targets = extract_drill_targets(mpi_grid)

    # Step 7: Save everything
    save_all(out_dir, features, model, mpi_grid, targets, shap_importance)

    print("\n" + "=" * 60)
    print("  ✅ Demo data generation complete!")
    print("  Run the server: uvicorn backend.main:app --reload")
    print("=" * 60)


if __name__ == "__main__":
    main()
