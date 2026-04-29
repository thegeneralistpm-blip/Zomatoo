from __future__ import annotations

from typing import Any

from phase2.schema import StandardizedPreference, UserPreferenceInput


BUDGET_RANGES = {
    "low": (0, 800),
    "medium": (801, 2000),
    "high": (2001, 100000),
}

CUISINE_ALIASES = {
    "north indian": "indian",
    "south indian": "indian",
    "desi": "indian",
    "indo chinese": "chinese",
    "chindian": "chinese",
}


class ValidationError(ValueError):
    pass


def _clean_text(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValidationError(f"{field_name} is required.")
    return " ".join(text.split())


def _parse_optional_preferences(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = [str(v).strip().lower() for v in value if str(v).strip()]
        return list(dict.fromkeys(items))
    text = str(value).strip()
    if not text:
        return []
    items = [part.strip().lower() for part in text.split(",") if part.strip()]
    return list(dict.fromkeys(items))


def _parse_cuisine_list(raw: str) -> list[str]:
    separators = [",", "/", "|", "+"]
    normalized = raw
    for sep in separators:
        normalized = normalized.replace(sep, ",")
    parts = [p.strip().lower() for p in normalized.split(",") if p.strip()]
    if not parts:
        raise ValidationError("cuisine is required.")

    canonical = [CUISINE_ALIASES.get(p, p) for p in parts]
    return list(dict.fromkeys(canonical))


def _parse_rating(value: Any) -> float:
    try:
        rating = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError("minimum_rating must be a number.") from exc
    if rating < 0 or rating > 5:
        raise ValidationError("minimum_rating must be between 0 and 5.")
    return round(rating, 1)


def validate_and_standardize(raw_payload: dict[str, Any]) -> StandardizedPreference:
    location = _clean_text(raw_payload.get("location"), "location").lower()
    budget = _clean_text(raw_payload.get("budget"), "budget").lower()
    cuisine_raw = _clean_text(raw_payload.get("cuisine"), "cuisine")
    minimum_rating = _parse_rating(raw_payload.get("minimum_rating"))
    optional_preferences = _parse_optional_preferences(
        raw_payload.get("optional_preferences")
    )

    if budget not in BUDGET_RANGES:
        valid = ", ".join(BUDGET_RANGES.keys())
        raise ValidationError(f"budget must be one of: {valid}.")

    budget_min, budget_max = BUDGET_RANGES[budget]
    cuisines = _parse_cuisine_list(cuisine_raw)

    _ = UserPreferenceInput(
        location=location,
        budget=budget,
        cuisine=cuisine_raw,
        minimum_rating=minimum_rating,
        optional_preferences=optional_preferences,
    )

    return StandardizedPreference(
        location=location,
        budget_label=budget,
        budget_min=budget_min,
        budget_max=budget_max,
        cuisines=cuisines,
        minimum_rating=minimum_rating,
        optional_preferences=optional_preferences,
    )
