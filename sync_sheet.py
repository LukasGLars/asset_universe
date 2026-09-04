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
import time
import tomllib
import urllib.error
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
    "Cash":      "Reactor Core Cash",
    # Crypto trend sleeve ETPs (Virtune, Nasdaq Stockholm). Prefix-matched like
    # the rest, so "Virtune Bitcoin ETP" or "Virtune BTC" both resolve.
    "Virtune Bitcoin":    "Virtune Bitcoin",
    "Virtune BTC":        "Virtune Bitcoin",
    "Virtune Staked ETH": "Virtune Staked ETH",
    "Virtune ETH":        "Virtune Staked ETH",
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


def fetch_sheet_rows(retries: int = 3, backoff_seconds: float = 2.0) -> list[dict]:
    """Fetch the sheet CSV, retrying on transient network errors (timeouts,
    connection resets) -- a single blip on Google's export endpoint
    previously took down the whole watchdog job with no second attempt
    (real failure 2026-07-16: "The read operation timed out"). Content
    errors (e.g. HTML instead of CSV, meaning the sheet sharing setting is
    wrong) are not retried -- retrying wouldn't fix those."""
    url = (
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
        f"/export?format=csv&gid={GID}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    raw = content_type = None
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                content_type = resp.headers.get("Content-Type", "")
                raw = resp.read()
            last_exc = None
            break
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_exc = exc
            if attempt < retries:
                print(f"  fetch attempt {attempt}/{retries} failed ({exc}), "
                      f"retrying in {backoff_seconds:.0f}s...", file=sys.stderr)
                time.sleep(backoff_seconds)
                backoff_seconds *= 2

    if last_exc is not None:
        raise RuntimeError(f"sheet fetch failed after {retries} attempts") from last_exc

    # If redirected to a login page the response is HTML, not CSV
    if "text/html" in content_type:
        raise RuntimeError(
            "Sheet returned HTML -- make sure it is shared as "
            "'Anyone with the link -> Viewer'."
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
    unmapped: list[str] = []
    for row in rows:
        asset = row.get("Asset", "").strip()
        if not asset:
            continue
        name = _lookup(asset)
        if name is None:
            # Loud, not silent: an unmapped row means the operator added a
            # holding to the sheet that this script does not know about, so it
            # silently never reaches portfolio.toml and TPV is quietly wrong.
            # That failure mode is invisible from the dashboard -- the number
            # just looks plausible and small.
            unmapped.append(asset)
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

    if unmapped:
        print(f"  WARNING: {len(unmapped)} sheet row(s) not in ASSET_MAP, ignored: "
              f"{', '.join(unmapped)}", file=sys.stderr)
        print("  Add them to ASSET_MAP and give them a [[positions]] block, or "
              "their value never reaches TPV.", file=sys.stderr)

    if not updates:
        print("  No parseable rows in sheet -- portfolio.toml unchanged.")
        return 0

    # Load current TOML to compare (read-only, for change detection)
    with open(TOML_PATH, "rb") as f:
        current = tomllib.load(f)

    current_map: dict[str, dict] = {p["name"]: p for p in current["positions"]}

    toml_text = TOML_PATH.read_text(encoding="utf-8")
    changed: list[str] = []

    missing = [n for n in updates if n not in current_map]
    if missing:
        # patch_toml() is a regex over existing [[positions]] blocks: with no
        # block to match it is a no-op, but the old code still printed the
        # change and reported success. Fail loudly instead -- a wrong TPV that
        # looks fine is worse than a failed sync.
        print(f"  ERROR: sheet names have no [[positions]] block in portfolio.toml: "
              f"{', '.join(missing)}", file=sys.stderr)
        return 1

    for name, (key, new_val) in updates.items():
        pos = current_map.get(name, {})
        old_val = pos.get(key)
        if old_val == new_val:
            continue  # already up-to-date
        print(f"  {name}: {key} {old_val} -> {new_val}")
        toml_text = patch_toml(toml_text, name, key, new_val)
        changed.append(name)

    if not changed:
        print("  portfolio.toml already up-to-date.")
        return 0

    TOML_PATH.write_text(toml_text, encoding="utf-8")

    # Verify the regex actually took. A silently-missed substitution leaves a
    # stale number that every downstream figure (TPV, bucket weights, FI pace)
    # is then computed from.
    with open(TOML_PATH, "rb") as f:
        after = {p["name"]: p for p in tomllib.load(f)["positions"]}
    bad = [n for n in changed if after.get(n, {}).get(updates[n][0]) != updates[n][1]]
    if bad:
        print(f"  ERROR: patch did not apply for: {', '.join(bad)}", file=sys.stderr)
        return 1

    print(f"  Saved. Updated: {', '.join(changed)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
