"""sightline.py

Pure logic for Sightline, the hold-or-cut framework: one disclosed
observable per thesis holding, an eroding trigger (YoY < 0), a
constructive trigger (YoY > 0 for two consecutive quarters after a CUT),
and a pre-committed action. Answers hold-or-cut ONLY -- nothing here
feeds sizing, rebalancing, or contribution routing, by construction.

State is derived from the reading history every time rather than stored,
so the file can never disagree with its own readings. The observable
values are entered by hand after reading the release (no API exposes
segment revenue -- confirmed 2026-07-06, see earnings_verdict.py); this
module is the "compare it against the rule" step, not a data source.

No new dependency: writes plain TOML text by hand, same pattern as
earnings_verdict.py / sync_sheet.py.
"""
from __future__ import annotations

import re
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

CONFIG_PATH = Path(__file__).parent / "config" / "sightline.toml"

HOLD, CUT, REQUALIFIED = "HOLD", "CUT", "REQUALIFIED"
CONSTRUCTIVE_QUARTERS = 2

_QUARTER_RE = re.compile(r"^(FY)?(\d{2}|\d{4})Q([1-4])$")


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def parse_quarter(label: str) -> tuple[str, int, int]:
    """'FY26Q3' -> ('FY', 26, 3); '2026Q2' -> ('', 2026, 2). Raises on junk
    so a typo can't silently become a reading that never finds its YoY pair."""
    m = _QUARTER_RE.match(label.strip().upper())
    if not m:
        raise ValueError(f"bad quarter label {label!r} -- expected e.g. FY26Q3 or 2026Q2")
    prefix, year, q = m.groups()
    return prefix or "", int(year), int(q)


def _sort_key(label: str) -> tuple[int, int]:
    _, year, q = parse_quarter(label)
    return year, q


def prior_year_label(label: str) -> str:
    prefix, year, q = parse_quarter(label)
    width = 2 if year < 100 else 4
    return f"{prefix}{year - 1:0{width}d}Q{q}"


def yoy_series(readings: list[dict]) -> list[tuple[str, float, float | None]]:
    """Chronological (quarter, value, yoy) -- yoy is None where the
    same quarter a year earlier hasn't been recorded."""
    by_q = {r["quarter"].upper(): float(r["value"]) for r in readings}
    out = []
    for label in sorted(by_q, key=_sort_key):
        prior = by_q.get(prior_year_label(label))
        yoy = (by_q[label] / prior - 1.0) if prior else None
        out.append((label, by_q[label], yoy))
    return out


def derive_state(readings: list[dict]) -> tuple[str, str]:
    """Walks the readings in order and returns (state, detail).

    HOLD until a quarter prints YoY < 0 (eroding -> CUT). From CUT, two
    consecutive YoY > 0 quarters -> REQUALIFIED, which only re-opens the
    entry test; a later YoY < 0 drops it back to CUT. Quarters with no YoY
    pair are skipped, never treated as either sign.
    """
    state = HOLD
    streak = 0
    latest = None
    for label, value, yoy in yoy_series(readings):
        if yoy is None:
            continue
        latest = (label, value, yoy)
        if yoy < 0:
            state, streak = CUT, 0
        elif state == CUT:
            streak += 1
            if streak >= CONSTRUCTIVE_QUARTERS:
                state = REQUALIFIED
    if latest is None:
        return state, "no YoY pair recorded yet"
    label, value, yoy = latest
    return state, f"{label}: {value:g} ({yoy:+.0%} YoY)"


def record_reading(ticker: str, quarter: str, value: float,
                   path: Path = CONFIG_PATH) -> tuple[str, str]:
    """Appends (or overwrites, same quarter) one reading and rewrites the
    file. Returns the derived (state, detail) so the CLI can print it."""
    parse_quarter(quarter)  # validate before touching the file
    cfg = load_config(path)
    if ticker not in cfg or ticker == "exemptions":
        raise KeyError(f"{ticker} has no Sightline entry in {path}")
    readings = [r for r in cfg[ticker].get("readings", [])
                if r["quarter"].upper() != quarter.upper()]
    readings.append({"quarter": quarter.upper(), "value": float(value)})
    cfg[ticker]["readings"] = sorted(readings, key=lambda r: _sort_key(r["quarter"]))
    _write(cfg, path)
    return derive_state(cfg[ticker]["readings"])


def save_auto_state(ticker: str, accession: str, status: str,
                    path: Path = CONFIG_PATH) -> None:
    """Persists sightline_reader's last-seen filing + outcome so the daily
    run can skip filings it has already handled."""
    cfg = load_config(path)
    cfg[ticker]["auto_last_accession"] = accession
    cfg[ticker]["auto_last_status"] = status
    _write(cfg, path)


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _write(cfg: dict, path: Path) -> None:
    # Keep the leading comment block intact -- it's the human-facing spec.
    header = ""
    if path.exists():
        text = path.read_text(encoding="utf-8")
        m = re.search(r"^\[", text, re.M)
        if m and m.start() > 0:
            header = text[: m.start()].rstrip() + "\n"
    lines = [header]
    for ticker, entry in cfg.items():
        if ticker == "exemptions":
            continue
        lines.append(f"[{ticker}]")
        for k in ("name", "observable", "unit", "eroding", "constructive", "cadence", "action",
                  "auto_last_accession", "auto_last_status"):
            if k in entry:
                lines.append(f'{k:<12} = "{_escape(entry[k])}"')
        lines.append("")
        for r in entry.get("readings", []):
            lines.append(f"[[{ticker}.readings]]")
            lines.append(f'quarter = "{r["quarter"]}"')
            lines.append(f"value   = {float(r['value']):g}")
            lines.append("")
    if "exemptions" in cfg:
        lines.append("# Holdings Sightline does NOT govern. Stated explicitly so an absent entry")
        lines.append("# reads as a decision, not a gap.")
        lines.append("")
        for name, ex in cfg["exemptions"].items():
            lines.append(f"[exemptions.{name}]")
            lines.append(f'reason = "{_escape(ex["reason"])}"')
            lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def format_dashboard_lines(cfg: dict | None = None,
                           auto_lines: dict[str, str] | None = None) -> list[str]:
    """The block fi_tracker.py prints. Field labels are what
    check_signal_changes.py greps, so keep them stable. `auto_lines` is
    sightline_reader's per-ticker 'Auto-read' text, if it ran."""
    cfg = cfg if cfg is not None else load_config()
    auto_lines = auto_lines or {}
    out = ["  Sightline  [hold-or-cut only -- never resizes]"]
    for ticker, entry in cfg.items():
        if ticker == "exemptions":
            continue
        state, detail = derive_state(entry.get("readings", []))
        out.append(f"    {ticker} ({entry.get('name', ticker)})")
        out.append(f"      Observable : {entry['observable']}")
        out.append(f"      Latest     : {detail}")
        out.append(f"      State      : {state}")
        out.append(f"      Eroding    : {entry['eroding']}")
        out.append(f"      Action     : {entry['action']}")
        if ticker in auto_lines:
            out.append(f"      Auto-read  : {auto_lines[ticker]}")
    for name, ex in cfg.get("exemptions", {}).items():
        out.append(f"    {name}: EXEMPT -- {ex['reason']}")
    return out
