"""Phase 6 — Unit tests for Phase 3: Candidate Retrieval Engine."""
from __future__ import annotations

import pandas as pd
import pytest

from phase3.retrieval import RetrievalConfig, retrieve_candidates, _compute_score, _tokenize_cuisines


# ═══════════════════════════════════════════════════════════════════════════
# Tokenize cuisines helper
# ═══════════════════════════════════════════════════════════════════════════


class TestTokenizeCuisines:
    """Test internal cuisine tokenization helper."""

    def test_single_cuisine(self):
        assert _tokenize_cuisines("Indian") == {"indian"}

    def test_multi_cuisine(self):
        result = _tokenize_cuisines("Indian, Chinese, Italian")
        assert result == {"indian", "chinese", "italian"}

    def test_empty_string(self):
        assert _tokenize_cuisines("") == set()

    def test_whitespace_trimmed(self):
        result = _tokenize_cuisines("  Indian ,  Chinese  ")
        assert result == {"indian", "chinese"}


# ═══════════════════════════════════════════════════════════════════════════
# Score computation
# ═══════════════════════════════════════════════════════════════════════════


class TestScoreComputation:
    """Test pre-LLM score calculation logic."""

    def test_perfect_match_score(self):
        """A candidate matching cuisine, having 5-star rating, and in-budget should score ~1.0."""
        row = pd.Series({
            "cuisine_norm": "indian",
            "rating": 5.0,
            "cost_for_two": 1000,
        })
        prefs = {
            "cuisines": ["indian"],
            "budget_min": 800,
            "budget_max": 2000,
        }
        score = _compute_score(row, prefs)
        assert score == 1.0

    def test_no_cuisine_match(self):
        """Missing cuisine match should drop ~0.4 from score."""
        row = pd.Series({
            "cuisine_norm": "japanese",
            "rating": 5.0,
            "cost_for_two": 1000,
        })
        prefs = {
            "cuisines": ["indian"],
            "budget_min": 800,
            "budget_max": 2000,
        }
        score = _compute_score(row, prefs)
        assert score == pytest.approx(0.6, abs=0.01)

    def test_out_of_budget_score_penalized(self):
        """Cost way above budget max should reduce budget component."""
        row = pd.Series({
            "cuisine_norm": "indian",
            "rating": 4.0,
            "cost_for_two": 5000,
        })
        prefs = {
            "cuisines": ["indian"],
            "budget_min": 0,
            "budget_max": 800,
        }
        score = _compute_score(row, prefs)
        # Should have cuisine (0.4) + rating (0.32) + minimal budget
        assert score < 0.8

    def test_nan_rating_handled(self):
        """NaN rating should not crash and should skip rating component."""
        row = pd.Series({
            "cuisine_norm": "indian",
            "rating": float("nan"),
            "cost_for_two": 500,
        })
        prefs = {
            "cuisines": ["indian"],
            "budget_min": 0,
            "budget_max": 800,
        }
        score = _compute_score(row, prefs)
        # cuisine 0.4 + budget 0.2 = 0.6 (no rating component)
        assert score == pytest.approx(0.6, abs=0.01)

    def test_zero_budget_max_no_crash(self):
        """Budget max of 0 should not cause division errors."""
        row = pd.Series({
            "cuisine_norm": "indian",
            "rating": 4.0,
            "cost_for_two": 500,
        })
        prefs = {
            "cuisines": ["indian"],
            "budget_min": 0,
            "budget_max": 0,
        }
        score = _compute_score(row, prefs)
        assert isinstance(score, float)


# ═══════════════════════════════════════════════════════════════════════════
# Candidate retrieval — strict filters
# ═══════════════════════════════════════════════════════════════════════════


class TestStrictRetrieval:
    """Test candidate retrieval with strict (non-fallback) filters."""

    def test_location_filter(self, sample_catalog_df, standardized_prefs_koramangala_indian):
        result = retrieve_candidates(
            df=sample_catalog_df,
            standardized_preferences=standardized_prefs_koramangala_indian,
        )
        assert result["status"] == "success"
        for c in result["candidates"]:
            assert c["location"].lower() == "koramangala"

    def test_cuisine_filter(self, sample_catalog_df, standardized_prefs_koramangala_indian):
        result = retrieve_candidates(
            df=sample_catalog_df,
            standardized_preferences=standardized_prefs_koramangala_indian,
        )
        # All candidates should have "indian" in their cuisine
        for c in result["candidates"]:
            assert "indian" in c["cuisine"].lower()

    def test_budget_filter(self, sample_catalog_df, standardized_prefs_koramangala_indian):
        result = retrieve_candidates(
            df=sample_catalog_df,
            standardized_preferences=standardized_prefs_koramangala_indian,
        )
        for c in result["candidates"]:
            if c["cost_for_two"] is not None:
                assert c["cost_for_two"] <= 2000

    def test_rating_filter(self, sample_catalog_df, standardized_prefs_koramangala_indian):
        result = retrieve_candidates(
            df=sample_catalog_df,
            standardized_preferences=standardized_prefs_koramangala_indian,
        )
        for c in result["candidates"]:
            if c["rating"] is not None:
                assert c["rating"] >= 3.5

    def test_top_n_limit(self, sample_catalog_df, standardized_prefs_koramangala_indian):
        config = RetrievalConfig(top_n=2)
        result = retrieve_candidates(
            df=sample_catalog_df,
            standardized_preferences=standardized_prefs_koramangala_indian,
            config=config,
        )
        assert len(result["candidates"]) <= 2

    def test_candidates_sorted_by_score(self, sample_catalog_df, standardized_prefs_koramangala_indian):
        result = retrieve_candidates(
            df=sample_catalog_df,
            standardized_preferences=standardized_prefs_koramangala_indian,
        )
        scores = [c["pre_llm_score"] for c in result["candidates"]]
        assert scores == sorted(scores, reverse=True)

    def test_output_has_required_keys(self, sample_catalog_df, standardized_prefs_koramangala_indian):
        result = retrieve_candidates(
            df=sample_catalog_df,
            standardized_preferences=standardized_prefs_koramangala_indian,
        )
        assert "status" in result
        assert "candidates" in result
        assert "applied_filters" in result
        assert "fallback_actions" in result

    def test_candidate_records_have_required_fields(self, sample_catalog_df, standardized_prefs_koramangala_indian):
        result = retrieve_candidates(
            df=sample_catalog_df,
            standardized_preferences=standardized_prefs_koramangala_indian,
        )
        required_fields = {"restaurant_name", "location", "cuisine", "cost_for_two", "rating", "pre_llm_score"}
        for c in result["candidates"]:
            assert required_fields.issubset(c.keys())


# ═══════════════════════════════════════════════════════════════════════════
# Fallback behavior
# ═══════════════════════════════════════════════════════════════════════════


class TestFallbackRetrieval:
    """Test controlled filter relaxation when strict filters yield zero results."""

    def test_relaxed_cuisine_when_no_strict_match(self, sample_catalog_df):
        """When no restaurants match cuisine, should relax and still return results."""
        prefs = {
            "location": "koramangala",
            "budget_label": "medium",
            "budget_min": 801,
            "budget_max": 2000,
            "cuisines": ["mexican"],  # Not in catalog
            "minimum_rating": 3.0,
            "optional_preferences": [],
        }
        result = retrieve_candidates(df=sample_catalog_df, standardized_preferences=prefs)
        assert "relaxed_cuisine_constraint" in result["fallback_actions"]
        assert len(result["candidates"]) > 0

    def test_relaxed_rating_when_needed(self, sample_catalog_df):
        """Extremely high rating threshold should trigger rating relaxation."""
        prefs = {
            "location": "whitefield",
            "budget_label": "low",
            "budget_min": 0,
            "budget_max": 100,  # Very low budget
            "cuisines": ["mexican"],  # Not in catalog
            "minimum_rating": 4.9,
            "optional_preferences": [],
        }
        result = retrieve_candidates(df=sample_catalog_df, standardized_preferences=prefs)
        assert any("reduced_min_rating" in a for a in result["fallback_actions"])

    def test_no_match_at_all(self, sample_catalog_df):
        """Impossible constraints should return no_match status."""
        prefs = {
            "location": "timbuktu",  # Not in catalog
            "budget_label": "low",
            "budget_min": 0,
            "budget_max": 1,  # Too low
            "cuisines": ["martian-food"],
            "minimum_rating": 5.0,
            "optional_preferences": [],
        }
        config = RetrievalConfig(max_fallback_steps=0)  # Disable fallback
        result = retrieve_candidates(df=sample_catalog_df, standardized_preferences=prefs, config=config)
        assert result["status"] == "no_match"
        assert result["candidates"] == []

    def test_fallback_status_indicated(self, sample_catalog_df):
        """When fallback was triggered, status should reflect it."""
        prefs = {
            "location": "koramangala",
            "budget_label": "medium",
            "budget_min": 801,
            "budget_max": 2000,
            "cuisines": ["peruvian"],  # Not in catalog
            "minimum_rating": 3.0,
            "optional_preferences": [],
        }
        result = retrieve_candidates(df=sample_catalog_df, standardized_preferences=prefs)
        assert result["status"] == "success_with_fallback"


# ═══════════════════════════════════════════════════════════════════════════
# Empty catalog
# ═══════════════════════════════════════════════════════════════════════════


class TestEmptyCatalog:
    """Test retrieval with empty or malformed catalog."""

    def test_empty_dataframe(self):
        empty_df = pd.DataFrame(columns=[
            "restaurant_name", "location", "cuisine", "cost_for_two", "rating",
            "location_norm", "cuisine_norm",
        ])
        prefs = {
            "location": "delhi",
            "budget_label": "medium",
            "budget_min": 801,
            "budget_max": 2000,
            "cuisines": ["indian"],
            "minimum_rating": 3.0,
            "optional_preferences": [],
        }
        result = retrieve_candidates(df=empty_df, standardized_preferences=prefs)
        assert result["status"] == "no_match"
        assert result["candidates"] == []
