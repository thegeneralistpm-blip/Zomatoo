"""Phase 6 — Unit tests for Phase 2: User Preference Validation & Normalization."""
from __future__ import annotations

import pytest

from phase2.normalize_validate import ValidationError, validate_and_standardize
from phase2.schema import StandardizedPreference


# ═══════════════════════════════════════════════════════════════════════════
# Happy-path tests
# ═══════════════════════════════════════════════════════════════════════════


class TestValidInput:
    """Tests that valid inputs produce correct standardized output."""

    def test_valid_minimal_input(self, valid_raw_preferences):
        result = validate_and_standardize(valid_raw_preferences)
        assert isinstance(result, StandardizedPreference)
        assert result.location == "bangalore"
        assert result.budget_label == "medium"
        assert result.budget_min == 801
        assert result.budget_max == 2000
        assert result.cuisines == ["indian"]
        assert result.minimum_rating == 3.5
        assert result.optional_preferences == ["family-friendly", "outdoor seating"]

    def test_multi_cuisine_slash_separated(self, valid_raw_preferences_multi_cuisine):
        result = validate_and_standardize(valid_raw_preferences_multi_cuisine)
        assert "indian" in result.cuisines
        assert "chinese" in result.cuisines
        assert result.location == "delhi"

    def test_multi_cuisine_comma_separated(self):
        payload = {
            "location": "Mumbai",
            "budget": "low",
            "cuisine": "Italian, Chinese",
            "minimum_rating": "2.0",
        }
        result = validate_and_standardize(payload)
        assert set(result.cuisines) == {"italian", "chinese"}

    def test_multi_cuisine_pipe_separated(self):
        payload = {
            "location": "Delhi",
            "budget": "high",
            "cuisine": "Indian | Italian | Chinese",
            "minimum_rating": "3.0",
        }
        result = validate_and_standardize(payload)
        assert len(result.cuisines) == 3

    def test_multi_cuisine_plus_separated(self):
        payload = {
            "location": "Delhi",
            "budget": "high",
            "cuisine": "Indian + Chinese",
            "minimum_rating": "3.0",
        }
        result = validate_and_standardize(payload)
        assert set(result.cuisines) == {"indian", "chinese"}


# ═══════════════════════════════════════════════════════════════════════════
# Cuisine alias mapping
# ═══════════════════════════════════════════════════════════════════════════


class TestCuisineAliases:
    """Test that cuisine aliases are correctly resolved to canonical names."""

    def test_north_indian_maps_to_indian(self):
        payload = {
            "location": "Delhi",
            "budget": "medium",
            "cuisine": "North Indian",
            "minimum_rating": "3.0",
        }
        result = validate_and_standardize(payload)
        assert result.cuisines == ["indian"]

    def test_south_indian_maps_to_indian(self):
        payload = {
            "location": "Chennai",
            "budget": "low",
            "cuisine": "South Indian",
            "minimum_rating": "3.0",
        }
        result = validate_and_standardize(payload)
        assert result.cuisines == ["indian"]

    def test_desi_maps_to_indian(self):
        payload = {
            "location": "Delhi",
            "budget": "medium",
            "cuisine": "Desi",
            "minimum_rating": "3.0",
        }
        result = validate_and_standardize(payload)
        assert result.cuisines == ["indian"]

    def test_indo_chinese_maps_to_chinese(self):
        payload = {
            "location": "Kolkata",
            "budget": "low",
            "cuisine": "Indo Chinese",
            "minimum_rating": "2.5",
        }
        result = validate_and_standardize(payload)
        assert result.cuisines == ["chinese"]

    def test_deduplicated_after_alias_mapping(self):
        """North Indian + Indian should resolve to just ['indian']."""
        payload = {
            "location": "Delhi",
            "budget": "medium",
            "cuisine": "North Indian, Indian",
            "minimum_rating": "3.0",
        }
        result = validate_and_standardize(payload)
        assert result.cuisines == ["indian"]


# ═══════════════════════════════════════════════════════════════════════════
# Budget validation
# ═══════════════════════════════════════════════════════════════════════════


class TestBudgetValidation:
    """Test budget field validation and range mapping."""

    @pytest.mark.parametrize(
        "budget, expected_min, expected_max",
        [
            ("low", 0, 800),
            ("medium", 801, 2000),
            ("high", 2001, 100000),
        ],
    )
    def test_valid_budget_ranges(self, budget, expected_min, expected_max):
        payload = {
            "location": "Delhi",
            "budget": budget,
            "cuisine": "Indian",
            "minimum_rating": "3.0",
        }
        result = validate_and_standardize(payload)
        assert result.budget_min == expected_min
        assert result.budget_max == expected_max

    def test_budget_case_insensitive(self):
        payload = {
            "location": "Delhi",
            "budget": "MEDIUM",
            "cuisine": "Indian",
            "minimum_rating": "3.0",
        }
        result = validate_and_standardize(payload)
        assert result.budget_label == "medium"

    def test_invalid_budget_value(self):
        payload = {
            "location": "Delhi",
            "budget": "ultra-premium",
            "cuisine": "Indian",
            "minimum_rating": "3.0",
        }
        with pytest.raises(ValidationError, match="budget must be one of"):
            validate_and_standardize(payload)


# ═══════════════════════════════════════════════════════════════════════════
# Rating validation
# ═══════════════════════════════════════════════════════════════════════════


class TestRatingValidation:
    """Test minimum_rating field validation."""

    def test_rating_zero_is_valid(self):
        payload = {
            "location": "Delhi",
            "budget": "low",
            "cuisine": "Indian",
            "minimum_rating": "0",
        }
        result = validate_and_standardize(payload)
        assert result.minimum_rating == 0.0

    def test_rating_five_is_valid(self):
        payload = {
            "location": "Delhi",
            "budget": "low",
            "cuisine": "Indian",
            "minimum_rating": "5",
        }
        result = validate_and_standardize(payload)
        assert result.minimum_rating == 5.0

    def test_rating_decimal_is_valid(self):
        payload = {
            "location": "Delhi",
            "budget": "low",
            "cuisine": "Indian",
            "minimum_rating": "3.7",
        }
        result = validate_and_standardize(payload)
        assert result.minimum_rating == 3.7

    def test_rating_negative_rejected(self):
        payload = {
            "location": "Delhi",
            "budget": "low",
            "cuisine": "Indian",
            "minimum_rating": "-1",
        }
        with pytest.raises(ValidationError, match="between 0 and 5"):
            validate_and_standardize(payload)

    def test_rating_above_five_rejected(self):
        payload = {
            "location": "Delhi",
            "budget": "low",
            "cuisine": "Indian",
            "minimum_rating": "6",
        }
        with pytest.raises(ValidationError, match="between 0 and 5"):
            validate_and_standardize(payload)

    def test_rating_non_numeric_rejected(self):
        payload = {
            "location": "Delhi",
            "budget": "low",
            "cuisine": "Indian",
            "minimum_rating": "excellent",
        }
        with pytest.raises(ValidationError, match="minimum_rating must be a number"):
            validate_and_standardize(payload)

    def test_rating_none_rejected(self):
        payload = {
            "location": "Delhi",
            "budget": "low",
            "cuisine": "Indian",
            "minimum_rating": None,
        }
        with pytest.raises(ValidationError, match="minimum_rating must be a number"):
            validate_and_standardize(payload)


# ═══════════════════════════════════════════════════════════════════════════
# Missing / empty field validation
# ═══════════════════════════════════════════════════════════════════════════


class TestMissingFields:
    """Test that missing or empty required fields raise ValidationError."""

    def test_missing_location(self):
        payload = {"budget": "low", "cuisine": "Indian", "minimum_rating": "3.0"}
        with pytest.raises(ValidationError, match="location"):
            validate_and_standardize(payload)

    def test_empty_location(self):
        payload = {
            "location": "",
            "budget": "low",
            "cuisine": "Indian",
            "minimum_rating": "3.0",
        }
        with pytest.raises(ValidationError, match="location"):
            validate_and_standardize(payload)

    def test_missing_budget(self):
        payload = {"location": "Delhi", "cuisine": "Indian", "minimum_rating": "3.0"}
        with pytest.raises(ValidationError, match="budget"):
            validate_and_standardize(payload)

    def test_missing_cuisine(self):
        payload = {"location": "Delhi", "budget": "low", "minimum_rating": "3.0"}
        with pytest.raises(ValidationError, match="cuisine"):
            validate_and_standardize(payload)

    def test_empty_cuisine(self):
        payload = {
            "location": "Delhi",
            "budget": "low",
            "cuisine": "   ",
            "minimum_rating": "3.0",
        }
        with pytest.raises(ValidationError, match="cuisine"):
            validate_and_standardize(payload)

    def test_completely_empty_payload(self):
        with pytest.raises(ValidationError):
            validate_and_standardize({})


# ═══════════════════════════════════════════════════════════════════════════
# Optional preferences
# ═══════════════════════════════════════════════════════════════════════════


class TestOptionalPreferences:
    """Test optional_preferences parsing edge cases."""

    def test_none_returns_empty_list(self):
        payload = {
            "location": "Delhi",
            "budget": "low",
            "cuisine": "Indian",
            "minimum_rating": "3.0",
            "optional_preferences": None,
        }
        result = validate_and_standardize(payload)
        assert result.optional_preferences == []

    def test_empty_string_returns_empty_list(self):
        payload = {
            "location": "Delhi",
            "budget": "low",
            "cuisine": "Indian",
            "minimum_rating": "3.0",
            "optional_preferences": "",
        }
        result = validate_and_standardize(payload)
        assert result.optional_preferences == []

    def test_missing_key_returns_empty_list(self):
        payload = {
            "location": "Delhi",
            "budget": "low",
            "cuisine": "Indian",
            "minimum_rating": "3.0",
        }
        result = validate_and_standardize(payload)
        assert result.optional_preferences == []

    def test_list_input_preserved(self):
        payload = {
            "location": "Delhi",
            "budget": "low",
            "cuisine": "Indian",
            "minimum_rating": "3.0",
            "optional_preferences": ["rooftop", "live music"],
        }
        result = validate_and_standardize(payload)
        assert result.optional_preferences == ["rooftop", "live music"]

    def test_duplicates_removed(self):
        payload = {
            "location": "Delhi",
            "budget": "low",
            "cuisine": "Indian",
            "minimum_rating": "3.0",
            "optional_preferences": "wifi, Wifi, WIFI",
        }
        result = validate_and_standardize(payload)
        assert result.optional_preferences == ["wifi"]


# ═══════════════════════════════════════════════════════════════════════════
# Text normalization
# ═══════════════════════════════════════════════════════════════════════════


class TestTextNormalization:
    """Test whitespace handling and case normalization."""

    def test_location_trimmed_and_lowered(self):
        payload = {
            "location": "  BANGALORE  ",
            "budget": "low",
            "cuisine": "Indian",
            "minimum_rating": "3.0",
        }
        result = validate_and_standardize(payload)
        assert result.location == "bangalore"

    def test_extra_internal_whitespace_collapsed(self):
        payload = {
            "location": "New   Delhi",
            "budget": "low",
            "cuisine": "Indian",
            "minimum_rating": "3.0",
        }
        result = validate_and_standardize(payload)
        assert result.location == "new delhi"
