from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class UserPreferenceInput:
    location: str
    budget: str
    cuisine: str
    minimum_rating: float
    optional_preferences: list[str] = field(default_factory=list)


@dataclass
class StandardizedPreference:
    location: str
    budget_label: str
    budget_min: int
    budget_max: int
    cuisines: list[str]
    minimum_rating: float
    optional_preferences: list[str]
