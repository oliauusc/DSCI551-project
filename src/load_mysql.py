"""Load cleaned College Scorecard data into MySQL.

Usage (from the repo root):
  python -m src.load_mysql institutions    --raw data/raw/MERGED2023-24_PP.csv
  python -m src.load_mysql fields_of_study --input data/cleaned/fields_of_study.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src import transform
from src.query_mysql import get_engine

TABLE_CLEANERS = {
    "institutions": transform.clean_institutions,
    "fields_of_study": transform.clean_fields_of_study,
}


def load_dataframe(df: pd.DataFrame, table: str, if_exists: str = "append") -> int:
    """Write a cleaned DataFrame to `table`; returns the row count written.

    The schema is created by sql/01_create_schema.sql, so the default is
    `append`; `replace` re-creates the table and is mainly for re-runs.
    """
    if table not in TABLE_CLEANERS:
        raise ValueError(f"Unknown table {table!r}; expected one of {sorted(TABLE_CLEANERS)}")
    engine = get_engine()
    with engine.begin() as conn:
        df.to_sql(table, con=conn, if_exists=if_exists, index=False, chunksize=1000)
    return len(df)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("table", choices=sorted(TABLE_CLEANERS))
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--raw", type=Path, help="raw Scorecard CSV; cleaned in memory before loading"
    )
    source.add_argument("--input", type=Path, help="already-cleaned CSV, loaded as-is")
    parser.add_argument(
        "--if-exists", default="append", choices=["append", "replace"],
        help="append to the existing table (default) or drop and re-create it",
    )
    args = parser.parse_args(argv)

    if args.raw is not None:
        raw = pd.read_csv(args.raw, low_memory=False)
        df = TABLE_CLEANERS[args.table](raw)
    else:
        df = pd.read_csv(args.input)

    rows = load_dataframe(df, args.table, if_exists=args.if_exists)
    print(f"Loaded {rows:,} rows into {args.table}.")


if __name__ == "__main__":
    main()
