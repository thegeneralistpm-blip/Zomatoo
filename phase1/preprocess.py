from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd


TARGET_COLUMNS = {
    "restaurant_name": ["restaurant_name", "name", "restaurant", "res_name"],
    "location": ["location", "city", "locality", "area"],
    "cuisine": ["cuisine", "cuisines", "food_type", "category"],
    "cost_for_two": ["cost_for_two", "average_cost_for_two", "cost", "price"],
    "rating": ["rating", "aggregate_rating", "user_rating"],
}


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "n/a", "na"}:
        return None
    return re.sub(r"\s+", " ", text)


def _extract_numeric(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    matches = re.findall(r"\d+(?:\.\d+)?", text)
    if not matches:
        return None
    return float(matches[0])


def _resolve_column(df: pd.DataFrame, aliases: list[str]) -> str | None:
    col_map = {c.lower(): c for c in df.columns}
    for alias in aliases:
        if alias.lower() in col_map:
            return col_map[alias.lower()]
    return None


def _build_standardized_frame(df: pd.DataFrame) -> pd.DataFrame:
    mapped: dict[str, pd.Series] = {}
    for target, aliases in TARGET_COLUMNS.items():
        source_col = _resolve_column(df, aliases)
        mapped[target] = df[source_col] if source_col else pd.Series([None] * len(df))

    out = pd.DataFrame(mapped)
    out["restaurant_name"] = out["restaurant_name"].map(_normalize_text)
    out["location"] = out["location"].map(_normalize_text)
    out["cuisine"] = out["cuisine"].map(_normalize_text)
    out["cost_for_two"] = out["cost_for_two"].map(_extract_numeric)
    out["rating"] = out["rating"].map(_extract_numeric)

    out["restaurant_name_norm"] = out["restaurant_name"].str.lower()
    out["location_norm"] = out["location"].str.lower()
    out["cuisine_norm"] = out["cuisine"].str.lower()
    return out


def clean_restaurant_data(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    stats: dict[str, int] = {"raw_rows": len(df)}
    clean = _build_standardized_frame(df)

    clean = clean.dropna(subset=["restaurant_name", "location"])
    stats["after_required_fields"] = len(clean)

    clean = clean.drop_duplicates(
        subset=["restaurant_name_norm", "location_norm", "cuisine_norm"], keep="first"
    )
    stats["after_dedup"] = len(clean)

    clean = clean[
        clean["rating"].isna() | ((clean["rating"] >= 0.0) & (clean["rating"] <= 5.0))
    ]
    stats["after_rating_filter"] = len(clean)

    clean = clean[["restaurant_name", "location", "cuisine", "cost_for_two", "rating"]]
    clean = clean.reset_index(drop=True)
    stats["final_rows"] = len(clean)
    return clean, stats


def save_outputs(df: pd.DataFrame, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "restaurants_clean.csv"
    parquet_path = output_dir / "restaurants_clean.parquet"
    df.to_csv(csv_path, index=False)
    df.to_parquet(parquet_path, index=False)
    return csv_path, parquet_path
