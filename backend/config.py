"""
GeoMines-AI Backend Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEMO_DATA_DIR = os.path.join(BASE_DIR, "demo", "demo_data")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)
