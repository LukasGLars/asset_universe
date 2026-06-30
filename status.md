==============================================================
REACTOR CORE -- PORTFOLIO SNAPSHOT
==============================================================
Position                Shares      Price    Value SEK     Wt
--------------------------------------------------------------
  Gold                     250     757 kr   189,297 kr  17.2%
  Silver                    66     511 kr    33,750 kr   3.1%
  Eli Lilly                 14  11,941 kr   167,179 kr  15.2%
  Walmart                  126   1,113 kr   140,193 kr  12.7%
  Cameco                    93   1,005 kr    93,426 kr   8.5%
  Vertiv                    31   2,980 kr    92,391 kr   8.4%
  Broadcom                  21   3,616 kr    75,938 kr   6.9%
  Howmet Aerospace          11   2,608 kr    28,683 kr   2.6%
  Spiltan Räntefond          -     manual   279,489 kr  25.4%
  War Chest                  -     manual     1,959 kr   0.2%
--------------------------------------------------------------
  TPV                                        1,106,938 kr
    Reactor Core            820,858 kr  (74%)
    Home Base               279,489 kr  (25%)
    War Chest                 1,959 kr  (0%)

==============================================================
FI@50 PACE TRACKER
==============================================================
  Start  (2025-07-21)  :       925,983 kr
  Now                     :     1,106,938 kr
  Target (FI@50)          :    12,934,706 kr
  Years remaining         :  11.1

  AWAR (trailing)         :  +20.9%
  Required CAGR           :  +24.9%
  Status                  :  BEHIND  (-4.0% margin)

  Projected @ AWAR        :     9,001,411 kr
  vs target               :    -3,933,295 kr  (deficit)

  Scenario         CAGR       Projected     FI date
  --------------------------------------------------
  Bear           +10%       3,175,785 kr       ~2052
  Conservative   +15%       5,191,955 kr       ~2044
  Base           +20%       8,312,348 kr       ~2039
  Current AWAR   +21%       9,001,411 kr       ~2039
  Bull           +30%      20,143,240 kr       ~2035

==============================================================
MACRO REGIME
==============================================================

  Feature                 Value   Regime  
  ------------------------------------------
  Nominal 10Y             4.38%   HIGH
  Real Yield             +2.16%   HIGH  ^
  Breakeven               2.24%   MID
  HY OAS                280 bps   TIGHT
  IG Credit               1.55%   TIGHT
  Curve 10Y-3M          +57 bps   LOW
  Curve 10Y-2Y          +30 bps   LOW
  SE 10Y                  2.75%   MID
  USD                     120.9   STRONG

  HY 20d delta  : +8 bps  (widening)
  Confidence    : HIGH
  Data through  : 2026-06-30

==============================================================
PORTFOLIO SIGNALS
==============================================================

  Base: ry=HIGH  nominal_10y=HIGH  baa10y=TIGHT  usd=STRONG

  Position          Wt    21d   63d   63d med  252d med  W252     N  Note
  ----------------------------------------------------------------------
  Gold           17.2%     --    --     +3.3%     +4.3%   92%   520  no mom data
  Silver          3.1%     --    --     +4.0%     +3.9%   70%   520  no mom data
  Eli Lilly      15.2%     --    --     -0.2%     -0.6%   43%   523  no mom data
  Walmart        12.7%     --    --     +1.4%     +1.4%   60%   523  no mom data
  Cameco          8.5%     --    --     -0.9%     -1.5%   43%   523  no mom data
  Vertiv          8.4%     --    --     +1.1%     -2.1%   44%   523  no mom data
  Broadcom        6.9%     --    --     +7.4%     +3.6%   60%   523  no mom data

==============================================================
TACTICAL RULES
==============================================================

  Silver GSR Tactical
    GSR now        : 69.14  (as of 2026-06-29)
    60d GSR peak   : 69.14
    Fall from peak : 0.0%  (no (need >=5% fall for signal))
    T1 threshold   : 83.36  |  T2: 86.45  |  Exit: 62.56
    Signal         : INACTIVE
    Action         : No action -- hold base

  AVGO 200d Guard
    AVGO now       : $372.45  (as of 2026-06-29)
    200d SMA       : $360.04  (+3.4% gap)
    Signal         : BASE
    Action         : Hold base (Gold 25%, AVGO 55%, LLY 20%)

==============================================================
  Regime check (2026-06-30): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)
Traceback (most recent call last):
  File "/home/runner/work/asset_universe/asset_universe/run_optimizer.py", line 28, in <module>
    from scipy.optimize import minimize
ModuleNotFoundError: No module named 'scipy'
