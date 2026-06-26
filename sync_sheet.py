#!/usr/bin/env python3
"""
Read the Google Sheet config tab and patch portfolio.toml with the latest
share counts and manual values.

Requires: sheet shared as "Anyone with the link → Viewer"
Export URL: https://docs.google.com/spreadsheets/d/{ID}/export?format=csv&gid={GID}
"""
import csv
import io
import re
import sys
import tomllib
import urllib.request
from pathlib import Path

SHEET_ID  = "1pnwGgNGblXw5X4x7CFmngksQZpL1MIbMJnJvZdsJCRs"
GID       = "1133887937"
TOML_PATH = Path(__file__).parent / "config" / "portfolio.toml"

# Sheet "Asset" value  →  portfolio.toml name
# Keys are prefix-matched (case-insensitive) so "Spiltan Räntefond Sverige " hits "Spiltan"
ASSET_MAP: dict[str, str] = {
    "PPFB.DE":   "Gold",
    "VZLC.DE":   "Silver",
    "Eli Lilly": "Eli Lilly",
    "Walmart":   "Walmart",
    "Cameco":    "Cameco",
    "Vertiv":    "Vertiv",
    "Broadcom":  "Broadcom",
    "HWM":       "Howmet Aerospace",
    "Howmet":    "Howmet Aerospace",
    "Spiltan":   "Spiltan Räntefond",
    "War Chest": "War Chest",
}


def _lookup(asset: str) -> str | None:
    """Return portfolio.toml name for a sheet asset cell (prefix-tolerant)."""
    a = asset.strip()
    if a in ASSET_MAP:
        return ASSET_MAP[a]
    a_lower = a.lower()
    for key, name in ASSET_MAP.items():
        if a_lower.startswith(key.lower()) or key.lower().startswith(a_lower):
            return name
    return None


def fetch_sheet_rows() -> list[dict]:
    url = (
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
        f"/export?format=csv&gid={GID}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        content_type = resp.headers.get("Content-Type", "")
        raw = resp.read()

    # If redirected to a login page the response is HTML, not CSV
    if "text/html" in content_type:
        raise RuntimeError(
            "Sheet returned HTML — make sure it is shared as "
            "'Anyone with the link → Viewer'."
        )

    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def parse_shares(s: str) -> int | None:
    s = s.strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def parse_value_sek(s: str) -> int | None:
    # "279,453 kr"  →  279453   |   "0 kr"  →  0   |  ""  →  None
    s = s.strip()
    if not s:
        return None
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else None


def patch_toml(text: str, name: str, key: str, new_val: int) -> str:
    """Replace `key = <int>` inside the [[positions]] block named `name`."""
    name_esc = re.escape(name)
    key_esc  = re.escape(key)

    def replacer(m: re.Match) -> str:
        block = m.group(0)
        if re.search(rf'name\s*=\s*"{name_esc}"', block):
            block = re.sub(rf'({key_esc}\s*=\s*)\d+', rf'\g<1>{new_val}', block)
        return block

    return re.sub(
        r'\[\[positions\]\].*?(?=\[\[positions\]\]|\Z)',
        replacer,
        text,
        flags=re.DOTALL,
    )


def main() -> int:
    print("sync_sheet: reading Google Sheet config...")

    try:
        rows = fetch_sheet_rows()
    except Exception as exc:
        print(f"  ERROR fetching sheet: {exc}", file=sys.stderr)
        return 1

    # Parse sheet → updates dict: {toml_name: (key, new_value)}
    updates: dict[str, tuple[str, int]] = {}
    for row in rows:
        asset = row.get("Asset", "").strip()
        if not asset:
            continue
        name = _lookup(asset)
        if name is None:
            continue
        shares_raw = row.get("shares", "").strip()
        value_raw  = row.get("value", "").strip()

        if shares_raw:
            v = parse_shares(shares_raw)
            if v is not None:
                updates[name] = ("shares", v)
        elif value_raw and value_raw not in ("", "0 kr"):
            v = parse_value_sek(value_raw)
            if v is not None:
                updates[name] = ("value_sek", v)

    if not updates:
        print("  No parseable rows in sheet — portfolio.toml unchanged.")
        return 0

    # Load current TOML to compare (read-only, for change detection)
    with open(TOML_PATH, "rb") as f:
        current = tomllib.load(f)

    current_map: dict[str, dict] = {p["name"]: p for p in current["positions"]}

    toml_text = TOML_PATH.read_text(encoding="utf-8")
    changed: list[str] = []

    for name, (key, new_val) in updates.items():
        pos = current_map.get(name, {})
        old_val = pos.get(key)
        if old_val == new_val:
            continue  # already up-to-date
        print(f"  {name}: {key} {old_val} → {new_val}")
        toml_text = patch_toml(toml_text, name, key, new_val)
        changed.append(name)

    if not changed:
        print("  portfolio.toml already up-to-date.")
        return 0

    TOML_PATH.write_text(toml_text, encoding="utf-8")
    print(f"  Saved. Updated: {', '.join(changed)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
