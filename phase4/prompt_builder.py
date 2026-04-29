from __future__ import annotations

import json
from typing import Any


def build_messages(
    phase3_payload: dict[str, Any],
    top_k: int,
) -> list[dict[str, str]]:
    candidates = phase3_payload.get("candidates", [])[:top_k]
    applied_filters = phase3_payload.get("applied_filters", {})

    candidate_rows = []
    for idx, c in enumerate(candidates, start=1):
        candidate_rows.append(
            {
                "candidate_id": idx,
                "restaurant_name": c.get("restaurant_name"),
                "location": c.get("location"),
                "cuisine": c.get("cuisine"),
                "cost_for_two": c.get("cost_for_two"),
                "rating": c.get("rating"),
                "pre_llm_score": c.get("pre_llm_score"),
            }
        )

    system_prompt = (
        "You are a restaurant recommendation ranking assistant. "
        "You must use only the given candidates and never invent restaurants. "
        "Return strict JSON only, with no markdown fences."
    )

    user_prompt = {
        "task": (
            "Rank the best restaurants for this user, explain why each is suitable, "
            "and include a short comparative summary."
        ),
        "constraints": {
            "only_use_provided_candidates": True,
            "return_exactly_top_k": top_k,
            "json_schema": {
                "recommendations": [
                    {
                        "candidate_id": "int",
                        "rank": "int",
                        "reason": "string",
                    }
                ],
                "comparison_summary": "string",
            },
            "notes": [
                "Do not include any candidate_id outside provided list.",
                "Do not include duplicate ranks.",
                "Do not include duplicate candidate_id.",
            ],
        },
        "user_preferences": applied_filters,
        "candidates": candidate_rows,
    }

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=True)},
    ]
