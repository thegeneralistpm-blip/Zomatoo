from __future__ import annotations

from typing import Any


def _fallback_deterministic(phase3_payload: dict[str, Any], top_k: int) -> dict[str, Any]:
    candidates = list(phase3_payload.get("candidates", []))
    candidates = sorted(
        candidates,
        key=lambda c: (
            float(c.get("pre_llm_score") or 0.0),
            float(c.get("rating") or 0.0),
            str(c.get("restaurant_name") or ""),
        ),
        reverse=True,
    )[:top_k]

    recommendations = []
    for idx, c in enumerate(candidates, start=1):
        reason = (
            "Selected by deterministic fallback based on pre-LLM score, "
            "rating, and cuisine alignment from retrieval output."
        )
        recommendations.append(
            {
                "rank": idx,
                "restaurant_name": c.get("restaurant_name"),
                "location": c.get("location"),
                "cuisine": c.get("cuisine"),
                "cost_for_two": c.get("cost_for_two"),
                "rating": c.get("rating"),
                "pre_llm_score": c.get("pre_llm_score"),
                "reason": reason,
            }
        )

    return {
        "status": "fallback",
        "source": "deterministic",
        "recommendations": recommendations,
        "comparison_summary": "Fallback ranking was used because LLM output was unavailable or invalid.",
    }


def validate_and_format_recommendations(
    phase3_payload: dict[str, Any],
    llm_parsed: dict[str, Any],
    top_k: int,
) -> dict[str, Any]:
    candidates = list(phase3_payload.get("candidates", []))
    if not candidates:
        return {
            "status": "no_candidates",
            "source": "phase3",
            "recommendations": [],
            "comparison_summary": "No candidates available from Phase 3.",
        }

    recs = llm_parsed.get("recommendations")
    summary = llm_parsed.get("comparison_summary", "")
    if not isinstance(recs, list):
        return _fallback_deterministic(phase3_payload, top_k)

    candidate_map = {idx: c for idx, c in enumerate(candidates, start=1)}
    used_ids: set[int] = set()
    formatted: list[dict[str, Any]] = []

    for rec in recs:
        if not isinstance(rec, dict):
            continue
        candidate_id = rec.get("candidate_id")
        rank = rec.get("rank")
        reason = str(rec.get("reason", "")).strip()

        if not isinstance(candidate_id, int):
            continue
        if candidate_id not in candidate_map or candidate_id in used_ids:
            continue
        if not isinstance(rank, int):
            continue
        if not reason:
            continue

        base = candidate_map[candidate_id]
        formatted.append(
            {
                "rank": rank,
                "restaurant_name": base.get("restaurant_name"),
                "location": base.get("location"),
                "cuisine": base.get("cuisine"),
                "cost_for_two": base.get("cost_for_two"),
                "rating": base.get("rating"),
                "pre_llm_score": base.get("pre_llm_score"),
                "reason": reason,
            }
        )
        used_ids.add(candidate_id)

    formatted = sorted(formatted, key=lambda row: row["rank"])[:top_k]
    if not formatted:
        return _fallback_deterministic(phase3_payload, top_k)

    return {
        "status": "success",
        "source": "llm",
        "recommendations": formatted,
        "comparison_summary": summary
        if isinstance(summary, str) and summary.strip()
        else "Top options were selected based on match quality and user preferences.",
    }
