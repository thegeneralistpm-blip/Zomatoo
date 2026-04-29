"""Phase 7 — Flask API server with monitoring, caching, and CORS."""
from __future__ import annotations

import json
import hashlib
import logging
import math
import os
import sys
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Ensure project root is on sys.path so phase2/phase3/phase4 imports work
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env from project root
load_dotenv(PROJECT_ROOT / ".env")

from flask import Flask, jsonify, request
from flask_cors import CORS

from backend.config import CATALOG_PATH, DEFAULT_MODEL, DEFAULT_TOP_K, DEFAULT_TOP_N, HOST, PORT, DEBUG
from backend.services.pipeline import PipelineResult, run_pipeline
from phase2.normalize_validate import ValidationError
from phase3.retrieval import load_restaurant_catalog

# ── Logging ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("backend")

# ── Flask App ─────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ── Catalog (loaded once at startup) ─────────────────────────────────────
catalog_df = None
catalog_row_count = 0

try:
    logger.info("Loading restaurant catalog from %s ...", CATALOG_PATH)
    catalog_df = load_restaurant_catalog(str(CATALOG_PATH))
    catalog_row_count = len(catalog_df)
    logger.info("Catalog loaded: %d rows", catalog_row_count)
except Exception as exc:
    logger.error("Failed to load catalog: %s", exc)

# ── Simple LRU Cache ─────────────────────────────────────────────────────
CACHE_MAX_SIZE = 100
_cache: OrderedDict[str, dict] = OrderedDict()

# ── Metrics Store (in-memory) ────────────────────────────────────────────
_metrics: dict[str, Any] = {
    "total_requests": 0,
    "success_count": 0,
    "fallback_count": 0,
    "error_count": 0,
    "validation_error_count": 0,
    "cache_hits": 0,
    "cache_misses": 0,
    "avg_latency_ms": 0.0,
    "total_latency_ms": 0.0,
    "phase_timings_sum_ms": {
        "phase2_validate": 0.0,
        "phase3_retrieval": 0.0,
        "phase4_llm": 0.0,
        "phase4_guardrails": 0.0,
    },
}


def _cache_key(payload: dict) -> str:
    """Generate a deterministic cache key from request payload."""
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def _cache_get(key: str) -> dict | None:
    if key in _cache:
        _cache.move_to_end(key)
        _metrics["cache_hits"] += 1
        return _cache[key]
    _metrics["cache_misses"] += 1
    return None


def _cache_put(key: str, value: dict) -> None:
    _cache[key] = value
    _cache.move_to_end(key)
    if len(_cache) > CACHE_MAX_SIZE:
        _cache.popitem(last=False)


def _sanitize_for_json(obj: Any) -> Any:
    """Replace NaN/Infinity with None for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


# ═══════════════════════════════════════════════════════════════════════════
# Routes
# ═══════════════════════════════════════════════════════════════════════════


@app.route("/api/health", methods=["GET"])
def health():
    """Service health check."""
    return jsonify({
        "status": "ok",
        "catalog_loaded": catalog_df is not None,
        "catalog_rows": catalog_row_count,
        "groq_key_set": bool(os.getenv("GROQ_API_KEY", "").strip()),
    })


@app.route("/api/metadata", methods=["GET"])
def metadata():
    """Return available locations, cuisines, and budget options for form population."""
    if catalog_df is None:
        return jsonify({"status": "error", "message": "Catalog not loaded."}), 503

    locations = sorted(catalog_df["location_norm"].dropna().unique().tolist())
    cuisines_raw = catalog_df["cuisine_norm"].dropna().str.split(",").explode().str.strip()
    cuisines = sorted(set(c for c in cuisines_raw if c))

    return jsonify({
        "locations": locations,
        "cuisines": cuisines,
        "budget_options": ["low", "medium", "high"],
        "rating_range": {"min": 0, "max": 5},
    })


@app.route("/api/recommend", methods=["POST"])
def recommend():
    """Main recommendation endpoint — runs the full Phase 2→3→4 pipeline."""
    if catalog_df is None:
        return jsonify({"status": "error", "error_type": "internal", "message": "Catalog not loaded."}), 503

    payload = request.get_json(silent=True) or {}
    _metrics["total_requests"] += 1

    # Check cache
    ck = _cache_key(payload)
    cached = _cache_get(ck)
    if cached is not None:
        logger.info("Cache HIT for key=%s", ck)
        cached_response = dict(cached)
        cached_response["_cached"] = True
        return jsonify(cached_response)

    logger.info("Cache MISS for key=%s — running pipeline", ck)
    start_time = time.perf_counter()

    try:
        result: PipelineResult = run_pipeline(
            raw_preferences=payload,
            catalog_df=catalog_df,
            top_k=payload.get("top_k", DEFAULT_TOP_K),
            top_n=DEFAULT_TOP_N,
            model=payload.get("model", DEFAULT_MODEL),
            dry_run=payload.get("dry_run", False),
        )
    except ValidationError as exc:
        _metrics["validation_error_count"] += 1
        _metrics["error_count"] += 1
        return jsonify({
            "status": "error",
            "error_type": "validation",
            "message": str(exc),
        }), 400
    except Exception as exc:
        _metrics["error_count"] += 1
        logger.exception("Pipeline error: %s", exc)
        return jsonify({
            "status": "error",
            "error_type": "internal",
            "message": "An unexpected error occurred. Please try again.",
        }), 500

    elapsed = time.perf_counter() - start_time
    response_data = _sanitize_for_json(result.to_dict())
    response_data["_latency_ms"] = round(elapsed * 1000, 1)

    # Update metrics
    if response_data.get("source") == "deterministic":
        _metrics["fallback_count"] += 1
    else:
        _metrics["success_count"] += 1

    _metrics["total_latency_ms"] += elapsed * 1000
    if _metrics["total_requests"] > 0:
        _metrics["avg_latency_ms"] = round(
            _metrics["total_latency_ms"] / _metrics["total_requests"], 1
        )

    for phase_key in _metrics["phase_timings_sum_ms"]:
        if phase_key in result.timings:
            _metrics["phase_timings_sum_ms"][phase_key] += round(result.timings[phase_key] * 1000, 1)

    # Cache the result
    _cache_put(ck, response_data)

    return jsonify(response_data)


@app.route("/api/metrics", methods=["GET"])
def metrics():
    """Monitoring endpoint — returns aggregated request metrics."""
    return jsonify({
        "total_requests": _metrics["total_requests"],
        "success_count": _metrics["success_count"],
        "fallback_count": _metrics["fallback_count"],
        "error_count": _metrics["error_count"],
        "validation_error_count": _metrics["validation_error_count"],
        "cache_hits": _metrics["cache_hits"],
        "cache_misses": _metrics["cache_misses"],
        "cache_size": len(_cache),
        "cache_max_size": CACHE_MAX_SIZE,
        "avg_latency_ms": _metrics["avg_latency_ms"],
        "phase_timings_sum_ms": _metrics["phase_timings_sum_ms"],
    })


# ═══════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=DEBUG)
