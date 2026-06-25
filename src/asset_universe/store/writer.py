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
