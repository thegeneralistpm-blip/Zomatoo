from datasets import load_dataset
import pandas as pd


def load_raw_dataset(dataset_id: str, split: str = "train") -> pd.DataFrame:
    """Load the raw Zomato dataset split from Hugging Face."""
    ds = load_dataset(dataset_id, split=split)
    return ds.to_pandas()
