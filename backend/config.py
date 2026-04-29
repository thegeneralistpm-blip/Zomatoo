"""Backend configuration — centralized settings for the API server."""
from __future__ import annotations

import os
from pathlib import Path

# Project root (one level up from backend/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Data paths
CATALOG_PATH = PROJECT_ROOT / "data" / "processed" / "restaurants_clean.csv"

# Groq settings
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
DEFAULT_MODEL = "llama-3.3-70b-versatile"
DEFAULT_TOP_K = 5
DEFAULT_TOP_N = 20

# Server settings
HOST = "127.0.0.1"
PORT = 5000
DEBUG = False
