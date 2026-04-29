"""Phase 6 — Unit tests for Phase 4: LLM Recommendation Layer."""
from __future__ import annotations

import json

import pytest

from phase4.guardrails import validate_and_format_recommendations, _fallback_deterministic
from phase4.prompt_builder import build_messages
from phase4.llm_service import _extract_json_object


# ═══════════════════════════════════════════════════════════════════════════
# Prompt builder
# ═══════════════════════════════════════════════════════════════════════════


class TestPromptBuilder:
    """Test that prompt messages are well-formed for LLM consumption."""

    def test_message_count(self, sample_phase3_payload):
        messages = build_messages(phase3_payload=sample_phase3_payload, top_k=3)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_system_prompt_content(self, sample_phase3_payload):
        messages = build_messages(phase3_payload=sample_phase3_payload, top_k=3)
        system = messages[0]["content"]
        assert "restaurant recommendation" in system.lower()
        assert "never invent" in system.lower()

    def test_user_prompt_is_valid_json(self, sample_phase3_payload):
        messages = build_messages(phase3_payload=sample_phase3_payload, top_k=3)
        user_content = json.loads(messages[1]["content"])
        assert "task" in user_content
        assert "constraints" in user_content
        assert "candidates" in user_content

    def test_candidate_count_matches_top_k(self, sample_phase3_payload):
        messages = build_messages(phase3_payload=sample_phase3_payload, top_k=2)
        user_content = json.loads(messages[1]["content"])
        assert len(user_content["candidates"]) == 2

    def test_candidate_fields(self, sample_phase3_payload):
        messages = build_messages(phase3_payload=sample_phase3_payload, top_k=3)
        user_content = json.loads(messages[1]["content"])
        candidate = user_content["candidates"][0]
        assert "candidate_id" in candidate
        assert "restaurant_name" in candidate
        assert "location" in candidate
        assert "cuisine" in candidate
        assert "rating" in candidate
        assert "pre_llm_score" in candidate

    def test_json_schema_included(self, sample_phase3_payload):
        messages = build_messages(phase3_payload=sample_phase3_payload, top_k=3)
        user_content = json.loads(messages[1]["content"])
        schema = user_content["constraints"]["json_schema"]
        assert "recommendations" in schema
        assert "comparison_summary" in schema

    def test_empty_candidates_handled(self):
        payload = {
            "status": "no_match",
            "candidates": [],
            "applied_filters": {},
        }
        messages = build_messages(phase3_payload=payload, top_k=5)
        user_content = json.loads(messages[1]["content"])
        assert user_content["candidates"] == []


# ═══════════════════════════════════════════════════════════════════════════
# JSON extraction from LLM output
# ═══════════════════════════════════════════════════════════════════════════


class TestJsonExtraction:
    """Test _extract_json_object handles various LLM output formats."""

    def test_clean_json(self):
        text = '{"recommendations": [], "comparison_summary": "test"}'
        result = _extract_json_object(text)
        assert result["comparison_summary"] == "test"

    def test_json_with_markdown_fences(self):
        text = '```json\n{"recommendations": [], "comparison_summary": "fenced"}\n```'
        result = _extract_json_object(text)
        assert result["comparison_summary"] == "fenced"

    def test_json_with_surrounding_text(self):
        text = 'Here is my analysis:\n{"recommendations": [], "comparison_summary": "embedded"}\nHope that helps!'
        result = _extract_json_object(text)
        assert result["comparison_summary"] == "embedded"

    def test_no_json_raises_error(self):
        text = "I cannot provide restaurant recommendations for that query."
        with pytest.raises(json.JSONDecodeError):
            _extract_json_object(text)

    def test_empty_string_raises_error(self):
        with pytest.raises(json.JSONDecodeError):
            _extract_json_object("")

    def test_nested_json_object(self):
        text = '{"recommendations": [{"candidate_id": 1, "rank": 1, "reason": "Good"}], "comparison_summary": "ok"}'
        result = _extract_json_object(text)
        assert len(result["recommendations"]) == 1


# ═══════════════════════════════════════════════════════════════════════════
# Guardrails — valid LLM output
# ═══════════════════════════════════════════════════════════════════════════


class TestGuardrailsValidOutput:
    """Test guardrails with well-formed LLM output."""

    def test_valid_llm_output_success(self, sample_phase3_payload, valid_llm_parsed):
        result = validate_and_format_recommendations(
            phase3_payload=sample_phase3_payload,
            llm_parsed=valid_llm_parsed,
            top_k=3,
        )
        assert result["status"] == "success"
        assert result["source"] == "llm"
        assert len(result["recommendations"]) == 3

    def test_recommendations_sorted_by_rank(self, sample_phase3_payload, valid_llm_parsed):
        result = validate_and_format_recommendations(
            phase3_payload=sample_phase3_payload,
            llm_parsed=valid_llm_parsed,
            top_k=3,
        )
        ranks = [r["rank"] for r in result["recommendations"]]
        assert ranks == sorted(ranks)

    def test_comparison_summary_preserved(self, sample_phase3_payload, valid_llm_parsed):
        result = validate_and_format_recommendations(
            phase3_payload=sample_phase3_payload,
            llm_parsed=valid_llm_parsed,
            top_k=3,
        )
        assert "Spice Garden" in result["comparison_summary"]

    def test_restaurant_data_comes_from_candidates(self, sample_phase3_payload, valid_llm_parsed):
        """Verify output restaurant fields come from Phase 3 data, not LLM hallucination."""
        result = validate_and_format_recommendations(
            phase3_payload=sample_phase3_payload,
            llm_parsed=valid_llm_parsed,
            top_k=3,
        )
        # The first recommendation should map to candidate 1 = Spice Garden
        rec1 = result["recommendations"][0]
        assert rec1["restaurant_name"] == "Spice Garden"
        assert rec1["location"] == "Koramangala"


# ═══════════════════════════════════════════════════════════════════════════
# Guardrails — hallucination detection
# ═══════════════════════════════════════════════════════════════════════════


class TestGuardrailsHallucination:
    """Test that recommendations with invalid candidate_ids are rejected."""

    def test_out_of_range_candidate_id_dropped(self, sample_phase3_payload):
        """candidate_id 99 doesn't exist in 3-candidate set; should be dropped."""
        llm_parsed = {
            "recommendations": [
                {"candidate_id": 99, "rank": 1, "reason": "Hallucinated restaurant."},
                {"candidate_id": 1, "rank": 2, "reason": "Real restaurant."},
            ],
            "comparison_summary": "test",
        }
        result = validate_and_format_recommendations(
            phase3_payload=sample_phase3_payload,
            llm_parsed=llm_parsed,
            top_k=3,
        )
        assert result["status"] == "success"
        # Only candidate_id 1 should survive
        assert len(result["recommendations"]) == 1
        assert result["recommendations"][0]["restaurant_name"] == "Spice Garden"

    def test_all_hallucinated_triggers_fallback(self, sample_phase3_payload):
        """If every recommendation is invalid, should fall back to deterministic."""
        llm_parsed = {
            "recommendations": [
                {"candidate_id": 100, "rank": 1, "reason": "Does not exist."},
                {"candidate_id": 200, "rank": 2, "reason": "Also doesn't exist."},
            ],
            "comparison_summary": "test",
        }
        result = validate_and_format_recommendations(
            phase3_payload=sample_phase3_payload,
            llm_parsed=llm_parsed,
            top_k=3,
        )
        assert result["status"] == "fallback"
        assert result["source"] == "deterministic"


# ═══════════════════════════════════════════════════════════════════════════
# Guardrails — duplicate IDs
# ═══════════════════════════════════════════════════════════════════════════


class TestGuardrailsDuplicates:
    """Test that duplicate candidate_ids in LLM output are deduplicated."""

    def test_duplicate_candidate_id_kept_once(self, sample_phase3_payload):
        llm_parsed = {
            "recommendations": [
                {"candidate_id": 1, "rank": 1, "reason": "First mention."},
                {"candidate_id": 1, "rank": 2, "reason": "Duplicate of first."},
                {"candidate_id": 2, "rank": 3, "reason": "Different restaurant."},
            ],
            "comparison_summary": "test",
        }
        result = validate_and_format_recommendations(
            phase3_payload=sample_phase3_payload,
            llm_parsed=llm_parsed,
            top_k=3,
        )
        names = [r["restaurant_name"] for r in result["recommendations"]]
        # Spice Garden should appear only once
        assert names.count("Spice Garden") == 1


# ═══════════════════════════════════════════════════════════════════════════
# Guardrails — missing/invalid fields
# ═══════════════════════════════════════════════════════════════════════════


class TestGuardrailsMissingFields:
    """Test guardrails handle LLM output with missing or invalid fields."""

    def test_missing_reason_drops_recommendation(self, sample_phase3_payload):
        llm_parsed = {
            "recommendations": [
                {"candidate_id": 1, "rank": 1, "reason": ""},
                {"candidate_id": 2, "rank": 2, "reason": "Valid reason here."},
            ],
            "comparison_summary": "test",
        }
        result = validate_and_format_recommendations(
            phase3_payload=sample_phase3_payload,
            llm_parsed=llm_parsed,
            top_k=3,
        )
        assert len(result["recommendations"]) == 1
        assert result["recommendations"][0]["restaurant_name"] == "Royal Biryani"

    def test_non_int_candidate_id_dropped(self, sample_phase3_payload):
        llm_parsed = {
            "recommendations": [
                {"candidate_id": "one", "rank": 1, "reason": "Not an integer ID."},
                {"candidate_id": 2, "rank": 2, "reason": "Valid candidate."},
            ],
            "comparison_summary": "test",
        }
        result = validate_and_format_recommendations(
            phase3_payload=sample_phase3_payload,
            llm_parsed=llm_parsed,
            top_k=3,
        )
        assert len(result["recommendations"]) == 1

    def test_non_int_rank_dropped(self, sample_phase3_payload):
        llm_parsed = {
            "recommendations": [
                {"candidate_id": 1, "rank": "first", "reason": "Bad rank type."},
                {"candidate_id": 2, "rank": 2, "reason": "Valid."},
            ],
            "comparison_summary": "test",
        }
        result = validate_and_format_recommendations(
            phase3_payload=sample_phase3_payload,
            llm_parsed=llm_parsed,
            top_k=3,
        )
        assert len(result["recommendations"]) == 1

    def test_non_list_recommendations_triggers_fallback(self, sample_phase3_payload):
        llm_parsed = {
            "recommendations": "This is not a list.",
            "comparison_summary": "test",
        }
        result = validate_and_format_recommendations(
            phase3_payload=sample_phase3_payload,
            llm_parsed=llm_parsed,
            top_k=3,
        )
        assert result["status"] == "fallback"
        assert result["source"] == "deterministic"

    def test_empty_dict_triggers_fallback(self, sample_phase3_payload):
        result = validate_and_format_recommendations(
            phase3_payload=sample_phase3_payload,
            llm_parsed={},
            top_k=3,
        )
        assert result["status"] == "fallback"
        assert result["source"] == "deterministic"


# ═══════════════════════════════════════════════════════════════════════════
# Deterministic fallback
# ═══════════════════════════════════════════════════════════════════════════


class TestDeterministicFallback:
    """Test the deterministic fallback ranking."""

    def test_fallback_returns_correct_count(self, sample_phase3_payload):
        result = _fallback_deterministic(sample_phase3_payload, top_k=2)
        assert len(result["recommendations"]) == 2

    def test_fallback_sorted_by_score(self, sample_phase3_payload):
        result = _fallback_deterministic(sample_phase3_payload, top_k=3)
        scores = [r["pre_llm_score"] for r in result["recommendations"]]
        assert scores == sorted(scores, reverse=True)

    def test_fallback_status(self, sample_phase3_payload):
        result = _fallback_deterministic(sample_phase3_payload, top_k=3)
        assert result["status"] == "fallback"
        assert result["source"] == "deterministic"

    def test_fallback_has_reason(self, sample_phase3_payload):
        result = _fallback_deterministic(sample_phase3_payload, top_k=3)
        for rec in result["recommendations"]:
            assert rec["reason"]
            assert "deterministic" in rec["reason"].lower()


# ═══════════════════════════════════════════════════════════════════════════
# No candidates edge case
# ═══════════════════════════════════════════════════════════════════════════


class TestNoCandidates:
    """Test guardrails when Phase 3 returned zero candidates."""

    def test_no_candidates_status(self):
        empty_payload = {"status": "no_match", "candidates": [], "applied_filters": {}}
        result = validate_and_format_recommendations(
            phase3_payload=empty_payload,
            llm_parsed={},
            top_k=5,
        )
        assert result["status"] == "no_candidates"
        assert result["recommendations"] == []

    def test_no_candidates_with_valid_llm_output(self):
        """Even if LLM somehow returns output, zero candidates should shortcircuit."""
        empty_payload = {"status": "no_match", "candidates": [], "applied_filters": {}}
        llm_parsed = {
            "recommendations": [
                {"candidate_id": 1, "rank": 1, "reason": "Phantom recommendation."}
            ],
            "comparison_summary": "test",
        }
        result = validate_and_format_recommendations(
            phase3_payload=empty_payload,
            llm_parsed=llm_parsed,
            top_k=5,
        )
        assert result["status"] == "no_candidates"


# ═══════════════════════════════════════════════════════════════════════════
# Comparison summary edge cases
# ═══════════════════════════════════════════════════════════════════════════


class TestComparisonSummary:
    """Test comparison_summary handling."""

    def test_empty_summary_gets_default(self, sample_phase3_payload):
        llm_parsed = {
            "recommendations": [
                {"candidate_id": 1, "rank": 1, "reason": "Good pick."},
            ],
            "comparison_summary": "",
        }
        result = validate_and_format_recommendations(
            phase3_payload=sample_phase3_payload,
            llm_parsed=llm_parsed,
            top_k=3,
        )
        assert result["comparison_summary"]  # Not empty
        assert "selected" in result["comparison_summary"].lower()

    def test_none_summary_gets_default(self, sample_phase3_payload):
        llm_parsed = {
            "recommendations": [
                {"candidate_id": 1, "rank": 1, "reason": "Good pick."},
            ],
        }
        result = validate_and_format_recommendations(
            phase3_payload=sample_phase3_payload,
            llm_parsed=llm_parsed,
            top_k=3,
        )
        assert result["comparison_summary"]  # Not empty
