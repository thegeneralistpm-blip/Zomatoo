"""Pipeline service — orchestrates Phase 2 → 3 → 4 in a single call."""
from __future__ import annotations

import time
import logging
from dataclasses import asdict
from typing import Any

import pandas as pd

from phase2.normalize_validate import ValidationError, validate_and_standardize
from phase3.retrieval import RetrievalConfig, retrieve_candidates
from phase4.guardrails import validate_and_format_recommendations
from phase4.llm_service import rank_with_groq

logger = logging.getLogger(__name__)


class PipelineResult:
    """Container for the full pipeline output plus timing metadata."""

    def __init__(self, payload: dict[str, Any], timings: dict[str, float]):
        self.payload = payload
        self.timings = timings

    def to_dict(self) -> dict[str, Any]:
        result = dict(self.payload)
        result["_timings_ms"] = {k: round(v * 1000, 1) for k, v in self.timings.items()}
        return result


def run_pipeline(
    raw_preferences: dict[str, Any],
    catalog_df: pd.DataFrame,
    top_k: int = 5,
    top_n: int = 20,
    model: str = "llama-3.3-70b-versatile",
    dry_run: bool = False,
) -> PipelineResult:
    """
    Execute the full recommendation pipeline.

    1. Phase 2: Validate and normalize user preferences
    2. Phase 3: Retrieve and score candidate restaurants
    3. Phase 4: LLM ranking with guardrails (or deterministic fallback)

    Returns a PipelineResult with the final payload and per-phase timings.
    """
    timings: dict[str, float] = {}

    # ── Phase 2: Validate & Normalize ─────────────────────────────────
    t0 = time.perf_counter()
    standardized = validate_and_standardize(raw_preferences)
    prefs = asdict(standardized)
    timings["phase2_validate"] = time.perf_counter() - t0
    logger.info("Phase 2 complete: location=%s, cuisines=%s", prefs["location"], prefs["cuisines"])

    # ── Phase 3: Candidate Retrieval ──────────────────────────────────
    t0 = time.perf_counter()
    phase3_result = retrieve_candidates(
        df=catalog_df,
        standardized_preferences=prefs,
        config=RetrievalConfig(top_n=top_n),
    )
    timings["phase3_retrieval"] = time.perf_counter() - t0
    logger.info(
        "Phase 3 complete: status=%s, candidates=%d",
        phase3_result["status"],
        phase3_result.get("candidate_count", 0),
    )

    # ── Phase 4: LLM Ranking ──────────────────────────────────────────
    llm_error = None
    llm_result = None

    if not dry_run and phase3_result.get("candidates"):
        t0 = time.perf_counter()
        try:
            llm_result = rank_with_groq(
                phase3_payload=phase3_result,
                top_k=top_k,
                model=model,
            )
            logger.info("Phase 4 LLM call succeeded: model=%s", model)
        except Exception as exc:
            llm_error = str(exc)
            logger.warning("Phase 4 LLM call failed: %s", llm_error)
        timings["phase4_llm"] = time.perf_counter() - t0
    else:
        timings["phase4_llm"] = 0.0

    # ── Phase 4: Guardrails & Formatting ──────────────────────────────
    t0 = time.perf_counter()
    if llm_result is not None:
        final = validate_and_format_recommendations(
            phase3_payload=phase3_result,
            llm_parsed=llm_result["parsed"],
            top_k=top_k,
        )
        final["llm_model"] = llm_result["model"]
    else:
        final = validate_and_format_recommendations(
            phase3_payload=phase3_result,
            llm_parsed={},
            top_k=top_k,
        )

    if llm_error:
        final["llm_error"] = llm_error

    # Attach filter info
    final["applied_filters"] = phase3_result.get("applied_filters", {})
    final["fallback_actions"] = phase3_result.get("fallback_actions", [])
    timings["phase4_guardrails"] = time.perf_counter() - t0

    return PipelineResult(payload=final, timings=timings)
