from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from phase3.retrieval import RetrievalConfig, load_restaurant_catalog, retrieve_candidates


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 3 candidate retrieval engine.")
    parser.add_argument(
        "--catalog-file",
        default="data/processed/restaurants_clean.csv",
        help="Path to cleaned restaurant catalog from Phase 1.",
    )
    parser.add_argument(
        "--preferences-file",
        default="data/phase2/standardized_preferences.json",
        help="Path to standardized preferences from Phase 2.",
    )
    parser.add_argument(
        "--output-file",
        default="data/phase3/candidate_set.json",
        help="Path to write candidate output.",
    )
    parser.add_argument("--top-n", default=20, type=int, help="Top candidates to return.")
    return parser.parse_args()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _save_json(path: Path, payload: dict) -> None:
    def _sanitize(value):
        if isinstance(value, dict):
            return {k: _sanitize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_sanitize(v) for v in value]
        if isinstance(value, float) and math.isnan(value):
            return None
        return value

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_sanitize(payload), indent=2, allow_nan=False), encoding="utf-8"
    )


def main() -> None:
    args = parse_args()
    catalog_path = Path(args.catalog_file)
    preferences_path = Path(args.preferences_file)
    output_path = Path(args.output_file)

    if not catalog_path.exists():
        raise FileNotFoundError(f"Catalog file not found: {catalog_path}")
    if not preferences_path.exists():
        raise FileNotFoundError(f"Preferences file not found: {preferences_path}")

    print(f"[Phase3] Loading catalog: {catalog_path}")
    df = load_restaurant_catalog(str(catalog_path))
    print(f"[Phase3] Catalog rows: {len(df)}")

    print(f"[Phase3] Loading preferences: {preferences_path}")
    prefs = _load_json(preferences_path)

    result = retrieve_candidates(
        df=df,
        standardized_preferences=prefs,
        config=RetrievalConfig(top_n=args.top_n),
    )

    _save_json(output_path, result)
    print(f"[Phase3] Status: {result['status']}")
    print(f"[Phase3] Candidate count: {result.get('candidate_count', 0)}")
    print(f"[Phase3] Output saved: {output_path}")
    print("[Phase3] Done")


if __name__ == "__main__":
    main()
