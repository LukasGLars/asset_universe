==============================================================
REACTOR CORE -- PORTFOLIO SNAPSHOT
==============================================================
Position                Shares      Price    Value SEK     Wt
--------------------------------------------------------------
  Gold                     250     769 kr   192,284 kr  17.4%
  Silver                    66     525 kr    34,682 kr   3.1%
  Eli Lilly                 14  11,767 kr   164,745 kr  14.9%
  Walmart                  126   1,127 kr   141,984 kr  12.8%
  Cameco                    93   1,018 kr    94,652 kr   8.6%
  Vertiv                    31   2,961 kr    91,778 kr   8.3%
  Broadcom                  21   3,555 kr    74,664 kr   6.8%
  Howmet Aerospace          11   2,619 kr    28,808 kr   2.6%
  Spiltan Räntefond          -     manual   279,489 kr  25.3%
  War Chest                  -     manual     1,959 kr   0.2%
--------------------------------------------------------------
  TPV                                        1,103,420 kr
    Reactor Core            823,597 kr  (75%)
    Home Base               279,489 kr  (25%)
    War Chest                 1,959 kr  (0%)

==============================================================
FI@50 PACE TRACKER
==============================================================
  Start  (2025-07-21)  :       925,983 kr
  Now                     :     1,103,420 kr
  Target (FI@50)          :    12,934,706 kr
  Years remaining         :  11.1

  AWAR (trailing)         :  +20.5%
  Required CAGR           :  +24.9%
  Status                  :  BEHIND  (-4.4% margin)

  Projected @ AWAR        :     8,700,109 kr
  vs target               :    -4,234,597 kr  (deficit)

  Scenario         CAGR       Projected     FI date
  --------------------------------------------------
  Bear           +10%       3,166,518 kr       ~2052
  Conservative   +15%       5,177,435 kr       ~2044
  Base           +20%       8,290,067 kr       ~2040
  Current AWAR   +21%       8,700,109 kr       ~2039
  Bull           +30%      20,093,650 kr       ~2035

==============================================================
MACRO REGIME
==============================================================

  Feature                 Value   Regime  
  ------------------------------------------
  Nominal 10Y             4.40%   HIGH
  Real Yield             +2.19%   HIGH  ^
  Breakeven               2.20%   MID
  HY OAS                278 bps   TIGHT
  IG Credit               1.54%   TIGHT
  Curve 10Y-3M          +55 bps   LOW
  Curve 10Y-2Y          +31 bps   LOW
  SE 10Y                  2.75%   MID
  USD                       nan   --

  HY 20d delta  : +6 bps  (widening)
  Confidence    : HIGH
  Data through  : 2026-06-26

==============================================================
PORTFOLIO SIGNALS
==============================================================

  Base: ry=HIGH  nominal_10y=HIGH  baa10y=TIGHT

  Position          Wt    21d   63d   63d med  252d med  W252     N  Note
  ----------------------------------------------------------------------
  Gold           17.4%    LOW   LOW     +0.7%     +0.7%   75%    64  
  Silver          3.1%    LOW   LOW     +2.3%     +2.3%   84%    31  
  Eli Lilly      14.9%   HIGH  HIGH     -0.1%     -0.1%   48%   180  
  Walmart        12.8%    LOW   LOW     +0.5%     +0.5%   62%   196  
  Cameco          8.6%    MID   MID     -0.2%     -0.2%   48%   149  
  Vertiv          8.3%    LOW   MID     -0.3%     -0.3%   47%    72  
  Broadcom        6.8%    LOW  HIGH     +0.8%     +0.8%   56%    62  

==============================================================
  Regime check (2026-06-26): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)
Traceback (most recent call last):
  File "/home/runner/work/asset_universe/asset_universe/run_optimizer.py", line 28, in <module>
    from scipy.optimize import minimize
ModuleNotFoundError: No module named 'scipy'
