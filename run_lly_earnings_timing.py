"""TEMPORARY (2026-10-16). Sell LLY before or after Q3? Two questions only:
how big is the earnings-day move, and is there a pre-earnings drift worth
waiting for. Delete after reading."""
from __future__ import annotations
import io, sys
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", write_through=True)
import numpy as np, pandas as pd, yfinance as yf

tk = yf.Ticker("LLY")
px = tk.history(period="12y", auto_adjust=True)["Close"]
px.index = pd.to_datetime(px.index).tz_localize(None)

ed = tk.get_earnings_dates(limit=60)
dates = sorted({pd.Timestamp(d).tz_localize(None).normalize() for d in ed.index})
dates = [d for d in dates if px.index.min() < d < px.index.max()]
print(f"LLY  {px.index.min().date()} to {px.index.max().date()}   "
      f"{len(dates)} earnings dates with price coverage\n")

def idx_on_or_after(d):
    pos = px.index.searchsorted(d)
    return pos if pos < len(px) else None

rows = []
for d in dates:
    i = idx_on_or_after(d)
    if i is None or i < 11 or i + 2 >= len(px):
        continue
    rows.append({
        "date": d.date(),
        "pre10": px.iloc[i] / px.iloc[i - 10] - 1,     # 10 sessions into the print
        "day":   px.iloc[i + 1] / px.iloc[i] - 1,      # the reaction
        "post5": px.iloc[i + 6] / px.iloc[i + 1] - 1 if i + 6 < len(px) else np.nan,
    })
df = pd.DataFrame(rows)

base10 = (px / px.shift(10) - 1).dropna()
base1 = px.pct_change().dropna()

def line(label, s, base=None):
    s = pd.Series(s).dropna()
    extra = f"   baseline {base.median():+.2%}" if base is not None else ""
    print(f"  {label:<26} n={len(s):>3}  median {s.median():>+7.2%}  "
          f"mean {s.mean():>+7.2%}  up {float((s>0).mean()):>5.0%}  "
          f"|move| p90 {s.abs().quantile(.9):>6.2%}{extra}")

print("EVENT RISK -- the move you are exposed to by waiting")
line("earnings-day reaction", df["day"], base1)
print(f"    worst  {df['day'].min():+.2%} on {df.loc[df['day'].idxmin(),'date']}")
print(f"    best   {df['day'].max():+.2%} on {df.loc[df['day'].idxmax(),'date']}")
print(f"    moves >3%: {float((df['day'].abs()>0.03).mean()):.0%}   "
      f">5%: {float((df['day'].abs()>0.05).mean()):.0%}")

print("\nIS THERE A RUN-UP WORTH WAITING FOR?")
line("10 sessions into print", df["pre10"], base10)
line("5 sessions after", df["post5"])

print("\nLAST 8 PRINTS")
for _, r in df.tail(8).iterrows():
    print(f"  {r['date']}   pre10 {r['pre10']:>+7.2%}   day {r['day']:>+7.2%}   post5 {r['post5']:>+7.2%}")

h = len(df) // 2
print(f"\nSUB-PERIODS (earnings-day move)")
for lab, part in (("older", df.iloc[:h]), ("recent", df.iloc[h:])):
    print(f"  {lab:<8} n={len(part):>3}  median {part['day'].median():+.2%}  "
          f"up {float((part['day']>0).mean()):.0%}  "
          f"|move| median {part['day'].abs().median():.2%}")
