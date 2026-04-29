from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from phase2.normalize_validate import ValidationError, validate_and_standardize


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Phase 2 preference capture validation and normalization."
    )
    parser.add_argument(
        "--input-file",
        default="data/phase1/user_input/latest_preferences.json",
        help="Path to raw preference JSON input.",
    )
    parser.add_argument(
        "--output-file",
        default="data/phase2/standardized_preferences.json",
        help="Path for standardized preference JSON output.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    input_path = Path(args.input_file)
    output_path = Path(args.output_file)

    print(f"[Phase2] Reading input: {input_path}")
    raw_payload = load_json(input_path)
    print(f"[Phase2] Raw payload keys: {', '.join(sorted(raw_payload.keys()))}")

    try:
        standardized = validate_and_standardize(raw_payload)
    except ValidationError as exc:
        print(f"[Phase2] Validation failed: {exc}")
        raise SystemExit(1) from exc

    standardized_payload = asdict(standardized)
    save_json(output_path, standardized_payload)

    print(f"[Phase2] Standardized preferences saved: {output_path}")
    print("[Phase2] Done")


if __name__ == "__main__":
    main()
