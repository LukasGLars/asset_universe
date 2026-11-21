import pandas as pd
from pathlib import Path


def write_or_append(path: Path, new_df: pd.DataFrame) -> int:
    """
    Write new_df to parquet at path.
    If file exists, appends and deduplicates on 'date'.
    Returns number of net-new rows written (0 means already up to date).
    """
    if path.exists():
        existing = pd.read_parquet(path)
        combined = (
            pd.concat([existing, new_df], ignore_index=True)
            .drop_duplicates(subset=["date"])
            .sort_values("date")
            .reset_index(drop=True)
        )
        n_new = len(combined) - len(existing)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        combined = new_df.sort_values("date").reset_index(drop=True)
        n_new = len(combined)

    if n_new > 0:
        combined.to_parquet(path, index=False)

    return n_new


def write_replacing(path: Path, new_df: pd.DataFrame) -> int:
    """Write new_df as the truth for its own date range: existing rows from
    new_df's first date onward are dropped and replaced (rows before it are
    kept). For sources that re-serve a dated history each run -- e.g. Avanza
    -- so a corrected or mis-dated row is repaired rather than kept forever
    by write_or_append's keep-first de-duplication.
    Returns the change in row count (can be 0 or negative after a repair)."""
    new_df = new_df.sort_values("date").reset_index(drop=True)
    if path.exists():
        existing = pd.read_parquet(path)
        keep = existing[pd.to_datetime(existing["date"]) < pd.to_datetime(new_df["date"].iloc[0])]
        combined = pd.concat([keep, new_df], ignore_index=True)
        delta = len(combined) - len(existing)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        combined, delta = new_df, len(new_df)
    combined.to_parquet(path, index=False)
    return delta
