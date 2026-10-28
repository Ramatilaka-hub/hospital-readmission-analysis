"""Load the UCI 'Diabetes 130-US Hospitals (1999-2008)' dataset."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "diabetic_data.csv"
UCI_ID = 296


def read_csv(path: Path) -> pd.DataFrame:
    # "?" marks missing values; the literal text "None" means "test not performed"
    return pd.read_csv(path, keep_default_na=False, na_values=["?", ""])


def load_raw(path: Path = RAW_PATH) -> pd.DataFrame:
    if path.exists():
        return read_csv(path)
    try:
        from ucimlrepo import fetch_ucirepo
    except ImportError as exc:
        raise SystemExit(
            "Dataset not found. Run `pip install ucimlrepo`, or download "
            "diabetic_data.csv from https://archive.ics.uci.edu/dataset/296 "
            f"and save it at {path}"
        ) from exc
    print("Downloading dataset from the UCI repository (id=296)...")
    ds = fetch_ucirepo(id=UCI_ID)
    df = pd.concat([ds.data.ids, ds.data.features, ds.data.targets], axis=1)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return read_csv(path)