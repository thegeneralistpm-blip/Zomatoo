"""Shared fixtures for Phase 6 test suite."""
from __future__ import annotations

import pytest
import pandas as pd


# ---------------------------------------------------------------------------
# Phase 2 fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def valid_raw_preferences() -> dict:
    """Minimal valid raw user preference payload."""
    return {
        "location": "Bangalore",
        "budget": "medium",
        "cuisine": "Indian",
        "minimum_rating": "3.5",
        "optional_preferences": "family-friendly, outdoor seating",
    }


@pytest.fixture()
def valid_raw_preferences_multi_cuisine() -> dict:
    return {
        "location": "Delhi",
        "budget": "high",
        "cuisine": "North Indian / Chinese",
        "minimum_rating": "4.0",
        "optional_preferences": "",
    }


# ---------------------------------------------------------------------------
# Phase 3 fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_catalog_df() -> pd.DataFrame:
    """Small restaurant catalog for retrieval unit tests."""
    data = [
        {
            "restaurant_name": "Spice Garden",
            "location": "Koramangala",
            "cuisine": "Indian, Chinese",
            "cost_for_two": 1200,
            "rating": 4.2,
        },
        {
            "restaurant_name": "Pasta Palace",
            "location": "Koramangala",
            "cuisine": "Italian",
            "cost_for_two": 1800,
            "rating": 4.5,
        },
        {
            "restaurant_name": "Dragon Wok",
            "location": "Indiranagar",
            "cuisine": "Chinese",
            "cost_for_two": 900,
            "rating": 3.8,
        },
        {
            "restaurant_name": "Tandoori Nights",
            "location": "Koramangala",
            "cuisine": "North Indian",
            "cost_for_two": 600,
            "rating": 4.0,
        },
        {
            "restaurant_name": "Sushi Zen",
            "location": "Koramangala",
            "cuisine": "Japanese",
            "cost_for_two": 2500,
            "rating": 4.7,
        },
        {
            "restaurant_name": "Budget Bites",
            "location": "Koramangala",
            "cuisine": "Fast Food",
            "cost_for_two": 300,
            "rating": 3.2,
        },
        {
            "restaurant_name": "Cafe Mocha",
            "location": "Whitefield",
            "cuisine": "Continental, Beverages",
            "cost_for_two": 700,
            "rating": 4.1,
        },
        {
            "restaurant_name": "Royal Biryani",
            "location": "Koramangala",
            "cuisine": "Indian, Biryani",
            "cost_for_two": 500,
            "rating": 4.3,
        },
    ]
    df = pd.DataFrame(data)
    # Apply the same normalization as load_restaurant_catalog does
    df["location_norm"] = df["location"].astype(str).str.strip().str.lower()
    df["cuisine_norm"] = df["cuisine"].astype(str).str.strip().str.lower()
    df["cost_for_two"] = pd.to_numeric(df["cost_for_two"], errors="coerce")
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    return df


@pytest.fixture()
def standardized_prefs_koramangala_indian() -> dict:
    """Standardized preferences targeting Koramangala + Indian cuisine + medium budget."""
    return {
        "location": "koramangala",
        "budget_label": "medium",
        "budget_min": 801,
        "budget_max": 2000,
        "cuisines": ["indian"],
        "minimum_rating": 3.5,
        "optional_preferences": [],
    }


# ---------------------------------------------------------------------------
# Phase 4 fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_phase3_payload() -> dict:
    """Simulated Phase 3 output for Phase 4 tests."""
    return {
        "status": "success",
        "message": "Candidates generated with strict filters.",
        "fallback_actions": [],
        "applied_filters": {
            "location": "koramangala",
            "minimum_rating": 3.5,
            "budget_max": 2000,
            "preferred_cuisines": ["indian"],
        },
        "candidate_count": 3,
        "candidates": [
            {
                "restaurant_name": "Spice Garden",
                "location": "Koramangala",
                "cuisine": "Indian, Chinese",
                "cost_for_two": 1200,
                "rating": 4.2,
                "pre_llm_score": 0.856,
            },
            {
                "restaurant_name": "Royal Biryani",
                "location": "Koramangala",
                "cuisine": "Indian, Biryani",
                "cost_for_two": 500,
                "rating": 4.3,
                "pre_llm_score": 0.744,
            },
            {
                "restaurant_name": "Tandoori Nights",
                "location": "Koramangala",
                "cuisine": "North Indian",
                "cost_for_two": 600,
                "rating": 4.0,
                "pre_llm_score": 0.72,
            },
        ],
    }


@pytest.fixture()
def valid_llm_parsed() -> dict:
    """Well-formed LLM parsed output matching sample_phase3_payload candidates."""
    return {
        "recommendations": [
            {"candidate_id": 1, "rank": 1, "reason": "Great Indian and Chinese fusion with high rating."},
            {"candidate_id": 2, "rank": 2, "reason": "Excellent biryani at an affordable price point."},
            {"candidate_id": 3, "rank": 3, "reason": "Classic North Indian fare with solid 4.0 rating."},
        ],
        "comparison_summary": "Spice Garden leads with the best mix of cuisine variety and rating.",
    }
