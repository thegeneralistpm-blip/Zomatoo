from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class RetrievalConfig:
    top_n: int = 20
    rating_relax_step: float = 0.5
    budget_relax_step: int = 400
    max_fallback_steps: int = 4


def load_restaurant_catalog(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    required_cols = {"restaurant_name", "location", "cuisine", "cost_for_two", "rating"}
    missing = required_cols.difference(df.columns)
    if missing:
        raise ValueError(f"Catalog is missing required columns: {sorted(missing)}")

    df["location_norm"] = df["location"].astype(str).str.strip().str.lower()
    df["cuisine_norm"] = df["cuisine"].astype(str).str.strip().str.lower()
    df["cost_for_two"] = pd.to_numeric(df["cost_for_two"], errors="coerce")
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    return df


def _tokenize_cuisines(raw: str) -> set[str]:
    return {token.strip().lower() for token in str(raw).split(",") if token.strip()}


def _compute_score(row: pd.Series, prefs: dict[str, Any]) -> float:
    score = 0.0
    pref_cuisines = set(prefs.get("cuisines", []))
    row_cuisines = _tokenize_cuisines(row.get("cuisine_norm", ""))

    if pref_cuisines and row_cuisines.intersection(pref_cuisines):
        score += 0.4

    rating = row.get("rating")
    if pd.notna(rating):
        score += min(float(rating) / 5.0, 1.0) * 0.4

    budget_min = float(prefs.get("budget_min", 0))
    budget_max = float(prefs.get("budget_max", 0))
    cost = row.get("cost_for_two")
    if pd.notna(cost) and budget_max > 0:
        if budget_min <= float(cost) <= budget_max:
            score += 0.2
        else:
            distance = abs(float(cost) - budget_max)
            score += max(0.0, 0.2 - (distance / max(budget_max, 1.0)) * 0.2)

    return round(score, 4)


def _filter_candidates(
    df: pd.DataFrame,
    location: str | None,
    min_rating: float,
    budget_max: int,
    preferred_cuisines: list[str],
) -> pd.DataFrame:
    filtered = df
    if location:
        filtered = filtered[filtered["location_norm"] == location]
    filtered = filtered[filtered["rating"].isna() | (filtered["rating"] >= min_rating)]
    filtered = filtered[filtered["cost_for_two"].isna() | (filtered["cost_for_two"] <= budget_max)]

    if preferred_cuisines:
        pref_set = set(preferred_cuisines)
        cuisine_mask = filtered["cuisine_norm"].map(
            lambda value: len(_tokenize_cuisines(value).intersection(pref_set)) > 0
        )
        filtered = filtered[cuisine_mask]

    return filtered.copy()


def retrieve_candidates(
    df: pd.DataFrame,
    standardized_preferences: dict[str, Any],
    config: RetrievalConfig | None = None,
) -> dict[str, Any]:
    cfg = config or RetrievalConfig()

    location = str(standardized_preferences["location"]).strip().lower()
    min_rating = float(standardized_preferences["minimum_rating"])
    budget_max = int(standardized_preferences["budget_max"])
    preferred_cuisines = list(standardized_preferences.get("cuisines", []))

    fallback_actions: list[str] = []

    candidates = _filter_candidates(
        df=df,
        location=location,
        min_rating=min_rating,
        budget_max=budget_max,
        preferred_cuisines=preferred_cuisines,
    )

    if candidates.empty:
        fallback_actions.append("relaxed_cuisine_constraint")
        candidates = _filter_candidates(
            df=df,
            location=location,
            min_rating=min_rating,
            budget_max=budget_max,
            preferred_cuisines=[],
        )

    if candidates.empty and cfg.max_fallback_steps >= 2:
        min_rating = round(max(0.0, min_rating - cfg.rating_relax_step), 1)
        fallback_actions.append(f"reduced_min_rating_to_{min_rating}")
        candidates = _filter_candidates(
            df=df,
            location=location,
            min_rating=min_rating,
            budget_max=budget_max,
            preferred_cuisines=[],
        )

    if candidates.empty and cfg.max_fallback_steps >= 3:
        budget_max = budget_max + cfg.budget_relax_step
        fallback_actions.append(f"increased_budget_max_to_{budget_max}")
        candidates = _filter_candidates(
            df=df,
            location=location,
            min_rating=min_rating,
            budget_max=budget_max,
            preferred_cuisines=[],
        )

    if candidates.empty and cfg.max_fallback_steps >= 4:
        fallback_actions.append("relaxed_location_constraint")
        candidates = _filter_candidates(
            df=df,
            location=None,
            min_rating=min_rating,
            budget_max=budget_max,
            preferred_cuisines=[],
        )

    if candidates.empty:
        return {
            "status": "no_match",
            "message": "No candidates found even after fallback relaxation.",
            "fallback_actions": fallback_actions,
            "applied_filters": {
                "location": location,
                "minimum_rating": min_rating,
                "budget_max": budget_max,
                "preferred_cuisines": preferred_cuisines,
            },
            "candidates": [],
        }

    candidates["pre_llm_score"] = candidates.apply(
        lambda row: _compute_score(row, standardized_preferences), axis=1
    )
    candidates = candidates.sort_values(
        by=["pre_llm_score", "rating", "restaurant_name"],
        ascending=[False, False, True],
    ).head(cfg.top_n)
    candidates = candidates.where(pd.notna(candidates), None)

    records = candidates[
        ["restaurant_name", "location", "cuisine", "cost_for_two", "rating", "pre_llm_score"]
    ].to_dict(orient="records")

    status = "success_with_fallback" if fallback_actions else "success"
    message = (
        "Candidates generated with fallback relaxation."
        if fallback_actions
        else "Candidates generated with strict filters."
    )

    return {
        "status": status,
        "message": message,
        "fallback_actions": fallback_actions,
        "applied_filters": {
            "location": location,
            "minimum_rating": min_rating,
            "budget_max": budget_max,
            "preferred_cuisines": preferred_cuisines,
        },
        "candidate_count": len(records),
        "candidates": records,
    }
