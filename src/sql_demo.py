"""Load the cleaned data into SQLite and run sql/queries.sql.
Usage:  python -m src.sql_demo   (run `python -m src.analysis` first)
"""
import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "processed" / "cleaned_encounters.csv"
SQL_PATH = ROOT / "sql" / "queries.sql"
OUT_DIR = ROOT / "reports" / "tables"


def parse_queries(text: str) -> dict:
    parts = re.split(r"^-- name:\s*(\w+)\s*$", text, flags=re.MULTILINE)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}


def run_queries(df: pd.DataFrame, sql_text: str, out_dir: Path = OUT_DIR) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    with sqlite3.connect(":memory:") as conn:
        df.to_sql("encounters", conn, index=False)
        for name, query in parse_queries(sql_text).items():
            results[name] = pd.read_sql_query(query, conn)
            results[name].to_csv(out_dir / f"sql_{name}.csv", index=False)
    return results


def main() -> None:
    if not CSV_PATH.exists():
        raise SystemExit("Run `python -m src.analysis` first.")
    df = pd.read_csv(CSV_PATH)
    for name, res in run_queries(df, SQL_PATH.read_text()).items():
        print(f"\n=== {name} ===\n{res.to_string(index=False)}")


if __name__ == "__main__":
    main()