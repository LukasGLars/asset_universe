import csv
import os
import tomllib
from pathlib import Path

_HERE = Path(__file__).parent          # src/asset_universe
_ROOT = _HERE.parent.parent            # project root

CONFIG_DIR = _ROOT / "config"


def _load_dotenv() -> None:
    # Standard KEY=VALUE dotenv files
    for filename in (".env",):
        p = _ROOT / filename
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

    # fred_api.env may contain just the raw key or KEY=VALUE
    fred_env = _ROOT / "fred_api.env"
    if fred_env.exists():
        content = fred_env.read_text().strip()
        if "=" in content:
            key, _, value = content.partition("=")
            os.environ.setdefault(key.strip(), value.strip())
        elif content:
            os.environ.setdefault("FRED_API_KEY", content)


def load_settings() -> dict:
    with open(CONFIG_DIR / "settings.toml", "rb") as f:
        return tomllib.load(f)


def raw_data_dir() -> Path:
    return _ROOT / load_settings()["data"]["raw_dir"]


def load_universe(name: str) -> list[str]:
    path = CONFIG_DIR / "universes" / f"{name}.txt"
    return [
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]


def load_fred_series() -> list[dict]:
    with open(CONFIG_DIR / "fred_series.csv", newline="") as f:
        return list(csv.DictReader(f))


def fred_api_key() -> str | None:
    return os.environ.get("FRED_API_KEY") or None


# Load .env on import
_load_dotenv()
