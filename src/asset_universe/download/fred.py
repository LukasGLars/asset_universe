import pandas as pd


def fetch(series_id: str, start: str, end: str, fred) -> pd.DataFrame | None:
    """
    Download a FRED series.
    Returns DataFrame with columns [date, value] or None if no data.
    `fred` is a fredapi.Fred instance.
    """
    s = fred.get_series(series_id, observation_start=start, observation_end=end)

    if s is None or s.empty:
        return None

    df = s.dropna().reset_index()
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    return df
