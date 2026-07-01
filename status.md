==============================================================
REACTOR CORE -- PORTFOLIO SNAPSHOT
==============================================================
Position                Shares      Price    Value SEK     Wt
--------------------------------------------------------------
  Gold                     250     759 kr   189,754 kr  17.2%
  Silver                    66     528 kr    34,833 kr   3.1%
  Eli Lilly                 14  11,645 kr   163,033 kr  14.7%
  Walmart                  126   1,100 kr   138,554 kr  12.5%
  Cameco                    93     989 kr    91,973 kr   8.3%
  Vertiv                    31   3,251 kr   100,773 kr   9.1%
  Broadcom                  21   3,668 kr    77,019 kr   7.0%
  Howmet Aerospace          11   2,610 kr    28,714 kr   2.6%
  Spiltan Räntefond          -     manual   279,489 kr  25.3%
  War Chest                  -     manual     1,959 kr   0.2%
--------------------------------------------------------------
  TPV                                        1,110,223 kr
    Reactor Core            824,653 kr  (74%)
    Home Base               279,489 kr  (25%)
    War Chest                 1,959 kr  (0%)

==============================================================
FI@50 PACE TRACKER
==============================================================
  Start  (2025-07-21)  :       925,983 kr
  Now                     :     1,110,223 kr
  Target (FI@50)          :    12,934,706 kr
  Years remaining         :  11.1

  AWAR (trailing)         :  +21.2%
  Required CAGR           :  +24.9%
  Status                  :  BEHIND  (-3.7% margin)

  Projected @ AWAR        :     9,285,326 kr
  vs target               :    -3,649,380 kr  (deficit)

  Scenario         CAGR       Projected     FI date
  --------------------------------------------------
  Bear           +10%       3,184,378 kr       ~2052
  Conservative   +15%       5,205,370 kr       ~2044
  Base           +20%       8,332,856 kr       ~2039
  Current AWAR   +21%       9,285,326 kr       ~2039
  Bull           +30%      20,188,511 kr       ~2035

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
  Gold           17.2%    LOW   LOW     +0.7%     +0.7%   75%    63  
  Silver          3.1%    LOW   LOW     +2.3%     +2.3%   84%    31  
  Eli Lilly      14.7%   HIGH  HIGH     -0.2%     -0.2%   46%   138  
  Walmart        12.5%    LOW   LOW     +0.7%     +0.7%   62%    58  
  Cameco          8.3%    LOW   MID     -0.3%     -0.3%   49%    47  
  Vertiv          9.1%    MID  HIGH     +0.4%     +0.4%   53%    77  
  Broadcom        7.0%    LOW  HIGH     +0.8%     +0.8%   56%    62  

==============================================================
TACTICAL RULES
==============================================================

  Silver GSR Tactical
    GSR now        : 67.64  (as of 2026-06-30)
    60d GSR peak   : 69.14
    Fall from peak : 2.2%  (no (need >=5% fall for signal))
    T1 threshold   : 83.36  |  T2: 86.45  |  Exit: 62.56
    Signal         : INACTIVE
    Action         : No action -- hold base

  AVGO 200d Guard
    AVGO now       : $377.75  (as of 2026-06-30)
    200d SMA       : $360.14  (+4.9% gap)
    Signal         : BASE
    Action         : Hold base (Gold 25%, AVGO 55%, LLY 20%)

  AVGO Earnings Checkpoint
    Trailing EPS   : $6.01
    Forward EPS    : $19.40
    Fwd/Trail ratio: 3.23x  (baseline 2026-07-01: 3.23x)
    Next earnings  : 2026-09-03
    Action         : after the print, check actual AI revenue/EPS against the
                     $56B FY26 / $100B FY27 guided path. Meaningfully short of
                     trajectory -> revisit conviction, even if price > SMA200.

  Opportunistic Sleeve
    Status         : CLOSED (0/1 position)
    Best candidate : PWR (Quanta Services, Inc.)  (ext +1.6%, 26d med +3.6%, div ROBUST, pre-entry tripwires PASSED) -- run run_entry_screen.py for full detail
    VIX review     : 16.45  (42% percentile, falling) -- for review, not a gate

==============================================================
  Regime check (2026-06-30): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)
Building regime labels ...
  Conditions    : {'ry_regime': 'HIGH', 'baa10y_regime': 'TIGHT'}
  Matched dates : 1398  (2004-04-30 - 2026-06-30)  MODERATE

Computing capped 252d distributions for 51 candidates ...
  SNDK      hist=1yr  (below min 10yr, skipped)
  APP       hist=5yr  (below min 10yr, skipped)
  HOOD      hist=5yr  (below min 10yr, skipped)
  PLTR      hist=6yr  (below min 10yr, skipped)
  CVNA      hist=9yr  (below min 10yr, skipped)
  GEV       hist=2yr  (below min 10yr, skipped)
  SATS      max_up=73%  (M&A / corporate event detected, skipped)
  LITE      N= 546  mu= +39.8%  sigma= 54.3%  hist=11yr  [SINGLE]
  HWM       hist=10yr  (below min 10yr, skipped)
  VRT       hist=8yr  (below min 10yr, skipped)
  AVGO      N= 546  mu= +33.4%  sigma= 35.6%  hist=17yr  [SINGLE]
  VST       hist=10yr  (below min 10yr, skipped)
  IBKR      N= 667  mu=  +7.2%  sigma= 20.2%  hist=19yr  [THIN]
  DASH      hist=6yr  (below min 10yr, skipped)
  ANET      N= 546  mu= +23.0%  sigma= 24.5%  hist=12yr  [SINGLE]
  NRG       N=1217  mu= +21.0%  sigma= 28.6%  hist=23yr  [MODERATE]
  DECK      N=1217  mu= +31.0%  sigma= 54.9%  hist=26yr  [MODERATE]
  CF        excluded (see EXCLUDE_TICKERS)
  PWR       N=1217  mu= +19.0%  sigma= 28.2%  hist=26yr  [MODERATE]
  BKNG      N=1217  mu= +34.9%  sigma= 46.9%  hist=26yr  [MODERATE]
  FOXA      hist=7yr  (below min 10yr, skipped)
  STLD      N=1217  mu= +15.1%  sigma= 31.0%  hist=26yr  [MODERATE]
  TRGP      N= 546  mu=  -0.6%  sigma= 12.8%  hist=16yr  [SINGLE]
  CEG       hist=4yr  (below min 10yr, skipped)
  EXV1.DE   no data
  NVDA      N=1217  mu= +24.9%  sigma= 32.4%  hist=26yr  [MODERATE]
  CMI       N=1217  mu= +25.3%  sigma= 29.8%  hist=26yr  [MODERATE]
  GM        N= 546  mu=  +8.4%  sigma= 13.3%  hist=16yr  [SINGLE]
  FOX       hist=7yr  (below min 10yr, skipped)
  TPR       N=1217  mu= +17.3%  sigma= 31.8%  hist=26yr  [MODERATE]
  RL        N=1217  mu= +15.3%  sigma= 26.8%  hist=26yr  [MODERATE]
  WDC       N=1217  mu= +19.9%  sigma= 38.6%  hist=26yr  [MODERATE]
  CFG       N= 546  mu= +16.4%  sigma= 13.5%  hist=12yr  [SINGLE]
  EME       N=1217  mu= +16.1%  sigma= 27.2%  hist=26yr  [MODERATE]
  GS        N=1217  mu= +13.1%  sigma= 23.7%  hist=26yr  [MODERATE]
  GRMN      N=1217  mu= +29.8%  sigma= 32.5%  hist=25yr  [MODERATE]
  FSLR      N= 788  mu= +29.0%  sigma= 53.5%  hist=20yr  [MODERATE]
  PHAG.L    no data
  TSLA      N= 546  mu=  +7.4%  sigma= 16.4%  hist=16yr  [SINGLE]
  ISRG      N=1217  mu= +18.8%  sigma= 33.8%  hist=26yr  [MODERATE]
  COHR      max_up=71%  (M&A / corporate event detected, skipped)
  CIEN      N=1217  mu= +19.5%  sigma= 26.9%  hist=26yr  [MODERATE]
  PM        N= 546  mu= +10.0%  sigma= 14.1%  hist=18yr  [SINGLE]
  SYF       N= 546  mu= +14.9%  sigma= 16.4%  hist=12yr  [SINGLE]
  CRWD      hist=7yr  (below min 10yr, skipped)
  4GLD.DE   no data
  PPFB.DE   no data
  ETR       N=1217  mu= +13.0%  sigma= 19.0%  hist=26yr  [MODERATE]
  APH       N=1217  mu= +17.2%  sigma= 24.7%  hist=26yr  [MODERATE]
  AAPL      N=1217  mu= +20.5%  sigma= 28.9%  hist=26yr  [MODERATE]
  GC_F      N=1217  mu=  +9.1%  sigma= 11.3%  hist=26yr  [MODERATE]

Cross-sectional prior mu : +19.0%  (shrinkage target)
Shrinkage lambda         : 100  (asset needs N>>100 to be fully trusted)

Optimizing (50 restarts, 30 candidates) ...

========================================================================
PORTFOLIO OPTIMIZER  --  Regime: RY=HIGH + BAA10Y=TIGHT
========================================================================
  Universe       : top 50 screen candidates + GC_F
  Matched dates  : 1398  MODERATE
  Shrinkage      : lambda=100  prior=+19.0%

  Ticker     Weight   mu(raw)   mu(shr)    sigma      N   Hist       Div
  -----------------------------------------------------------------
  BKNG        32.8%    +34.9%    +33.7%    46.9%   1217    26yr  MODERATE
  GRMN        23.8%    +29.8%    +29.0%    32.5%   1217    25yr  MODERATE
  LITE        15.2%    +39.8%    +31.0%    54.3%    546    11yr    SINGLE
  DECK        12.0%    +31.0%    +30.1%    54.9%   1217    26yr  MODERATE
  AVGO         6.3%    +33.4%    +27.3%    35.6%    546    17yr    SINGLE
  GC_F         5.0%     +9.1%     +9.8%    11.3%   1217    26yr  MODERATE  [gold]
  FSLR         4.9%    +29.0%    +27.9%    53.5%    788    20yr  MODERATE

  Active positions   : 7  (weight >= 1%)
  Equal-weight g(w)  : +19.1%  (benchmark)
  Optimized g(w)     : +27.8%


  NOTE: g(w) is an approximation. mu/sigma are regime-conditional,
  capped at regime end. Shrinkage applied for short-history assets.
========================================================================
