# 🛰️ GeoMines-AI

**Multi-Sensor Space-Tech & Deep Learning Mineral Prospectivity Platform**

> SIH26009 | Ministry of Steel, Government of India | Smart India Hackathon 2026

---

## 🚀 Quick Start (Demo Mode)
### Prerequisites
- Python 3.10+
- Node.js 18+
- npm

### Step 1: Install Backend Dependencies
```bash
cd geomines-ai
pip install -r requirements.txt
```

### Step 2: Generate Demo Data
```bash
python -m backend.demo.generate_demo_data
```

### Step 3: Start Backend API
```bash
cp .env.example .env
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 4: Start Frontend (new terminal)
```bash
cd frontend
npm install
npm run dev
```

### Step 5: Open Browser
Navigate to **http://localhost:5173** and click **"Run AI Analysis"**

---

## 📊 What This Does

1. **Ingests** multi-sensor satellite data (Sentinel-2, ASTER, SAR, DEM)
2. **Extracts** spectral mineral indices (Mn-Index, Fe-Ratio, Clay, Ferrous)
3. **Runs** XGBoost ensemble ML model trained on known MOIL mine locations
4. **Generates** 10m-resolution Mineral Potential Index (MPI) heatmap
5. **Ranks** GPS drill targets with SHAP explainability
6. **Exports** results as CSV, KML, and PDF reports

---

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React.js, Vite, Leaflet.js, Recharts |
| Backend | FastAPI (Python), Uvicorn |
| ML/AI | XGBoost, Scikit-learn, SHAP |
| Data | NumPy, SciPy, Rasterio |

---

## 📂 Project Structure

```
geomines-ai/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── config.py             # Configuration
│   ├── api/routes.py         # API endpoints
│   ├── models/schemas.py     # Pydantic models
│   ├── demo/
│   │   ├── generate_demo_data.py  # Synthetic data generator
│   │   └── demo_data/        # Pre-computed results
│   └── services/             # ML pipeline services
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/            # Page views
│   │   └── api/              # API client
│   └── package.json
├── netlify.toml              # Netlify build and redirect configuration
├── render.yaml               # Render.com backend service configuration
└── requirements.txt
```

---

## ☁️ Cloud Deployment

### 1. Frontend on Netlify
The frontend is pre-configured with `netlify.toml` and client-side SPA routing (`_redirects`).
- **Base directory:** `frontend`
- **Build command:** `npm run build`
- **Publish directory:** `frontend/dist` (or `dist` via `netlify.toml`)
- **Environment Variable:** `VITE_API_URL` = `https://<your-render-backend-url>/api`

### 2. Backend on Render.com
Configured via `render.yaml` as a Web Service:
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- **Environment Variable:** `DEMO_MODE=true`

