from __future__ import annotations

import argparse
import json
from pathlib import Path

from phase4.guardrails import validate_and_format_recommendations
from phase4.llm_service import rank_with_groq


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 4 LLM recommendation layer.")
    parser.add_argument(
        "--input-file",
        default="data/phase3/candidate_set.json",
        help="Path to Phase 3 candidate set JSON.",
    )
    parser.add_argument(
        "--output-file",
        default="data/phase4/recommendations.json",
        help="Path to write final recommendations.",
    )
    parser.add_argument("--top-k", type=int, default=5, help="Number of final recommendations.")
    parser.add_argument(
        "--model",
        default="llama-3.3-70b-versatile",
        help="Groq model name.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip Groq call and force deterministic fallback output.",
    )
    return parser.parse_args()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def main() -> None:
    args = parse_args()
    input_path = Path(args.input_file)
    output_path = Path(args.output_file)

    if not input_path.exists():
        raise FileNotFoundError(f"Input candidate file not found: {input_path}")

    phase3_payload = _load_json(input_path)
    llm_error = None
    llm_result: dict | None = None

    if not args.dry_run:
        try:
            llm_result = rank_with_groq(
                phase3_payload=phase3_payload,
                top_k=args.top_k,
                model=args.model,
            )
        except Exception as exc:  # noqa: BLE001
            llm_error = str(exc)

    if llm_result is None:
        final_payload = validate_and_format_recommendations(
            phase3_payload=phase3_payload,
            llm_parsed={},
            top_k=args.top_k,
        )
    else:
        final_payload = validate_and_format_recommendations(
            phase3_payload=phase3_payload,
            llm_parsed=llm_result["parsed"],
            top_k=args.top_k,
        )
        final_payload["llm_model"] = llm_result["model"]

    if llm_error:
        final_payload["llm_error"] = llm_error

    _save_json(output_path, final_payload)
    print(f"[Phase4] Status: {final_payload.get('status')}")
    print(f"[Phase4] Source: {final_payload.get('source')}")
    print(f"[Phase4] Recommendations: {len(final_payload.get('recommendations', []))}")
    print(f"[Phase4] Output saved: {output_path}")
    print("[Phase4] Done")


if __name__ == "__main__":
    main()
