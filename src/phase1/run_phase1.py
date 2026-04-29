from __future__ import annotations

import argparse
from pathlib import Path

from .data_ingestion import load_raw_dataset
from .preprocess import clean_restaurant_data, save_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 1 data pipeline.")
    parser.add_argument(
        "--dataset-id",
        default="ManikaSaini/zomato-restaurant-recommendation",
        help="Hugging Face dataset id.",
    )
    parser.add_argument("--split", default="train", help="Dataset split.")
    parser.add_argument(
        "--output-dir", default="data/processed", help="Directory for cleaned outputs."
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)

    print(f"[Phase1] Loading dataset {args.dataset_id} split={args.split}")
    raw = load_raw_dataset(args.dataset_id, args.split)
    print(f"[Phase1] Raw rows: {len(raw)}")

    clean, stats = clean_restaurant_data(raw)
    print("[Phase1] Cleaning stats:")
    for key, value in stats.items():
        print(f"  - {key}: {value}")

    csv_path, parquet_path = save_outputs(clean, output_dir)
    print(f"[Phase1] Saved CSV: {csv_path}")
    print(f"[Phase1] Saved Parquet: {parquet_path}")
    print("[Phase1] Done")


if __name__ == "__main__":
    main()
