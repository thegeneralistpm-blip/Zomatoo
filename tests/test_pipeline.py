"""Phase 6 — Integration tests for the full recommendation pipeline (Phase 2 → 3 → 4)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from phase2.normalize_validate import validate_and_standardize
from phase3.retrieval import RetrievalConfig, load_restaurant_catalog, retrieve_candidates
from phase4.guardrails import validate_and_format_recommendations
from phase4.prompt_builder import build_messages


# ═══════════════════════════════════════════════════════════════════════════
# End-to-end pipeline (Phase 2 → 3 → 4 with dry-run / mocked LLM)
# ═══════════════════════════════════════════════════════════════════════════


class TestEndToEndPipeline:
    """Integration test: raw user input → standardized prefs → candidates → recommendations."""

    def test_full_pipeline_with_deterministic_fallback(self, sample_catalog_df):
        """Run the full pipeline with empty LLM output (deterministic fallback)."""
        # Phase 2: validate raw input
        raw_input = {
            "location": "Koramangala",
            "budget": "medium",
            "cuisine": "Indian",
            "minimum_rating": "3.5",
            "optional_preferences": "family-friendly",
        }
        from dataclasses import asdict

        standardized = validate_and_standardize(raw_input)
        prefs = asdict(standardized)

        # Phase 3: retrieve candidates
        result = retrieve_candidates(
            df=sample_catalog_df,
            standardized_preferences=prefs,
            config=RetrievalConfig(top_n=10),
        )
        assert result["status"] in ("success", "success_with_fallback")
        assert len(result["candidates"]) > 0

        # Phase 4: guardrails with empty LLM (dry-run equivalent)
        final = validate_and_format_recommendations(
            phase3_payload=result,
            llm_parsed={},
            top_k=5,
        )
        assert final["status"] == "fallback"
        assert final["source"] == "deterministic"
        assert len(final["recommendations"]) > 0

    def test_full_pipeline_with_mocked_llm(self, sample_catalog_df):
        """Run the full pipeline with a mocked LLM response."""
        # Phase 2
        raw_input = {
            "location": "Koramangala",
            "budget": "medium",
            "cuisine": "Indian",
            "minimum_rating": "3.0",
            "optional_preferences": "",
        }
        from dataclasses import asdict

        standardized = validate_and_standardize(raw_input)
        prefs = asdict(standardized)

        # Phase 3
        result = retrieve_candidates(
            df=sample_catalog_df,
            standardized_preferences=prefs,
            config=RetrievalConfig(top_n=10),
        )
        assert len(result["candidates"]) > 0

        # Phase 4: build prompt and simulate LLM response
        messages = build_messages(phase3_payload=result, top_k=3)
        assert len(messages) == 2

        # Simulate what a good LLM would return
        candidate_count = min(3, len(result["candidates"]))
        mocked_llm_parsed = {
            "recommendations": [
                {
                    "candidate_id": i + 1,
                    "rank": i + 1,
                    "reason": f"Recommended because it scored well for candidate {i + 1}.",
                }
                for i in range(candidate_count)
            ],
            "comparison_summary": "All candidates are excellent choices in Koramangala.",
        }

        final = validate_and_format_recommendations(
            phase3_payload=result,
            llm_parsed=mocked_llm_parsed,
            top_k=3,
        )
        assert final["status"] == "success"
        assert final["source"] == "llm"
        assert len(final["recommendations"]) == candidate_count
        assert final["comparison_summary"] == "All candidates are excellent choices in Koramangala."


# ═══════════════════════════════════════════════════════════════════════════
# Pipeline with fallback chain validation
# ═══════════════════════════════════════════════════════════════════════════


class TestPipelineFallbackChain:
    """Test that the pipeline gracefully degrades through fallback stages."""

    def test_impossible_preferences_reach_fallback(self, sample_catalog_df):
        """Preferences that match nothing should still produce a deterministic result."""
        raw_input = {
            "location": "Koramangala",
            "budget": "low",
            "cuisine": "Ethiopian",  # Not in our test catalog
            "minimum_rating": "4.5",
            "optional_preferences": "",
        }
        from dataclasses import asdict

        standardized = validate_and_standardize(raw_input)
        prefs = asdict(standardized)

        result = retrieve_candidates(
            df=sample_catalog_df,
            standardized_preferences=prefs,
            config=RetrievalConfig(top_n=5),
        )

        # Should have triggered at least cuisine relaxation
        assert len(result["fallback_actions"]) > 0

        # Phase 4 with empty LLM
        final = validate_and_format_recommendations(
            phase3_payload=result,
            llm_parsed={},
            top_k=3,
        )
        # Should still produce output (either from relaxed candidates or deterministic fallback)
        assert final["status"] in ("fallback", "no_candidates")


# ═══════════════════════════════════════════════════════════════════════════
# Pipeline output contract validation
# ═══════════════════════════════════════════════════════════════════════════


class TestPipelineOutputContract:
    """Verify the final output contract is stable and JSON-serializable."""

    def test_output_is_json_serializable(self, sample_catalog_df):
        raw_input = {
            "location": "Koramangala",
            "budget": "medium",
            "cuisine": "Indian",
            "minimum_rating": "3.5",
        }
        from dataclasses import asdict

        standardized = validate_and_standardize(raw_input)
        prefs = asdict(standardized)

        result = retrieve_candidates(
            df=sample_catalog_df,
            standardized_preferences=prefs,
        )
        final = validate_and_format_recommendations(
            phase3_payload=result,
            llm_parsed={},
            top_k=5,
        )

        # Must be JSON-serializable without errors
        json_str = json.dumps(final, ensure_ascii=True)
        parsed_back = json.loads(json_str)
        assert parsed_back["status"] in ("success", "fallback", "no_candidates")

    def test_output_recommendation_fields(self, sample_catalog_df):
        raw_input = {
            "location": "Koramangala",
            "budget": "medium",
            "cuisine": "Indian",
            "minimum_rating": "3.0",
        }
        from dataclasses import asdict

        standardized = validate_and_standardize(raw_input)
        prefs = asdict(standardized)

        result = retrieve_candidates(
            df=sample_catalog_df,
            standardized_preferences=prefs,
        )
        final = validate_and_format_recommendations(
            phase3_payload=result,
            llm_parsed={},
            top_k=5,
        )

        required_rec_fields = {"rank", "restaurant_name", "location", "cuisine", "cost_for_two", "rating", "reason"}
        for rec in final["recommendations"]:
            assert required_rec_fields.issubset(rec.keys()), f"Missing fields in: {rec.keys()}"


# ═══════════════════════════════════════════════════════════════════════════
# Prompt regression checks
# ═══════════════════════════════════════════════════════════════════════════


class TestPromptRegression:
    """Detect unintentional changes in prompt structure (regression checks)."""

    def test_system_prompt_always_instructs_json_only(self, sample_phase3_payload):
        messages = build_messages(phase3_payload=sample_phase3_payload, top_k=3)
        system = messages[0]["content"].lower()
        assert "json" in system
        assert "no markdown" in system or "strict json" in system

    def test_system_prompt_forbids_hallucination(self, sample_phase3_payload):
        messages = build_messages(phase3_payload=sample_phase3_payload, top_k=3)
        system = messages[0]["content"].lower()
        assert "never invent" in system or "only" in system

    def test_user_prompt_includes_candidate_data(self, sample_phase3_payload):
        messages = build_messages(phase3_payload=sample_phase3_payload, top_k=3)
        user_content = json.loads(messages[1]["content"])
        assert len(user_content["candidates"]) > 0
        assert user_content["candidates"][0]["restaurant_name"] == "Spice Garden"

    def test_user_prompt_includes_constraints(self, sample_phase3_payload):
        messages = build_messages(phase3_payload=sample_phase3_payload, top_k=3)
        user_content = json.loads(messages[1]["content"])
        constraints = user_content["constraints"]
        assert constraints["only_use_provided_candidates"] is True
        assert constraints["return_exactly_top_k"] == 3
        assert "notes" in constraints
