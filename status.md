==============================================================
REACTOR CORE -- PORTFOLIO SNAPSHOT
==============================================================
Position                Shares      Price    Value SEK     Wt
--------------------------------------------------------------
  Gold                     304     751 kr   228,228 kr  21.2%
  Silver                     -     489 kr         0 kr   0.0%
  Eli Lilly                 14  11,363 kr   159,082 kr  14.8%
  Walmart                  126   1,101 kr   138,716 kr  12.9%
  Cameco                     -     825 kr         0 kr   0.0%
  Vertiv                     -   2,790 kr         0 kr   0.0%
  Broadcom                  80   3,574 kr   285,889 kr  26.5%
  Howmet Aerospace          11   2,625 kr    28,879 kr   2.7%
  Spiltan Räntefond          -     manual   234,793 kr  21.8%
  War Chest                  -     manual     1,959 kr   0.2%
--------------------------------------------------------------
  TPV                                        1,072,925 kr
    Reactor Core            840,794 kr  (78%)
    Home Base               234,793 kr  (22%)
    War Chest                 1,959 kr  (0%)

==============================================================
FI@50 PACE TRACKER
==============================================================
  Start  (2025-07-21)  :       925,983 kr
  Now                     :     1,072,925 kr
  Target (FI@50)          :    12,934,706 kr
  Years remaining         :  11.0

  AWAR (trailing)         :  +16.1%
  Required CAGR           :  +22.4%
  Status                  :  BEHIND  (-6.4% margin)

  Projected @ AWAR        :     7,559,018 kr
  vs target               :    -5,375,688 kr  (deficit)

  Scenario         CAGR       Projected     FI date   (incl. 6,000 kr/mo contributions)
  ------------------------------------------------------------------------
  Bear           +10%       4,472,442 kr       ~2047
  Conservative   +15%       6,896,266 kr       ~2041
  Base           +20%      10,553,754 kr       ~2038
  Current AWAR   +16%       7,559,018 kr       ~2040
  Bull           +30%      23,997,236 kr       ~2035

==============================================================
MACRO REGIME
==============================================================

  Feature                 Value   Regime  
  ------------------------------------------
  Nominal 10Y             4.57%   HIGH
  Real Yield             +2.35%   HIGH  ^
  Breakeven               2.24%   MID
  HY OAS                271 bps   TIGHT
  IG Credit               1.59%   TIGHT
  Curve 10Y-3M          +70 bps   MID
  Curve 10Y-2Y          +37 bps   LOW
  SE 10Y                  2.78%   MID
  USD                     120.5   STRONG

  HY 20d delta  : +5 bps  (flat)
  Confidence    : HIGH
  Data through  : 2026-07-17

==============================================================
PORTFOLIO SIGNALS
==============================================================

  Base: ry=HIGH  nominal_10y=HIGH  baa10y=TIGHT  usd=STRONG

  Position          Wt    21d   63d   63d med  252d med  W252     N  Note
  ----------------------------------------------------------------------
  Gold           21.2%    LOW   LOW     +0.5%     +0.5%   65%    88  
  Silver          0.0%    LOW   LOW     +2.3%     +2.3%   84%    31  
  Eli Lilly      14.8%   HIGH  HIGH     -0.3%     -0.3%   45%   152  
  Walmart        12.9%    LOW   LOW     +0.2%     +0.2%   55%    62  
  Cameco          0.0%    LOW   LOW     +2.0%     +2.0%   67%    82  
  Vertiv          0.0%    LOW   LOW     +2.1%     +2.1%   58%    65  
  Broadcom       26.5%    LOW   LOW     +0.5%     +0.5%   57%    93  

==============================================================
TACTICAL RULES
==============================================================

  Silver GSR Tactical
    GSR now        : 71.56  (as of 2026-07-17)
    60d GSR peak   : 71.56
    Fall from peak : 0.0%  (no (need >=5% fall for signal))
    T1 threshold   : 83.36  |  T2: 86.45  |  Exit: 62.56
    Signal         : INACTIVE
    Action         : No action -- hold base

  AVGO 200d Guard
    AVGO now       : $370.83  (as of 2026-07-17)
    200d SMA       : $362.48  (+2.3% gap)
    5d ROC         : -7.3%  (crash threshold: -10%)
    Signal         : BASE  (trigger: none)
    LLY stress     : inactive  ($1179.11 vs 200d SMA $1004.96, 5d ROC -0.8%)
    Joint stress   : inactive  (guard AND LLY stress both active)
    Action         : Hold base (Gold 25%, AVGO 55%, LLY 20%)

  AVGO Earnings Checkpoint
    Latest qtr EPS (actual vs est.): $2.44 vs $2.40  (+1.7% surprise)
    TTM EPS (non-GAAP actual)  : $8.13
    Forward EPS (+1yr est.)    : $19.42
    Fwd/Trail ratio (normalized): 2.39x  (peer range 1.17-1.41x; corrected 2026-07-06 from a GAAP/non-GAAP mismatched 3.22x)
    Revenue (latest qtr, actual): $22.19B  (TTM YoY: +32.3%)
    Next-qtr revenue consensus : $29.44B (implied YoY +84.5%)
    Next earnings  : 2026-09-03
    Reminder       : not_due
    Latest quarter : 2026-04-30
    Beat streak    : 4
    Guidance trend : revising up  (+1yr estimate vs. 90 days ago)

  LLY Earnings Checkpoint
    Latest qtr EPS (actual vs est.): $8.55 vs $6.79  (+25.9% surprise)
    TTM EPS (non-GAAP actual)  : $29.42
    Forward EPS (+1yr est.)    : $44.91
    Fwd/Trail ratio (normalized): 1.53x  (baseline established 2026-07-06; in line with peer range 1.17-1.41x)
    Revenue (latest qtr, actual): $19.80B  (TTM YoY: +47.4%)
    Next-qtr revenue consensus : $20.65B (implied YoY +32.7%)
    Next earnings  : 2026-08-05
    Reminder       : not_due
    Latest quarter : 2026-03-31
    Beat streak    : 4
    Guidance trend : revising up  (+1yr estimate vs. 90 days ago)

  Opportunistic Sleeve
    Status         : OPEN -- HWM @ $276.93 (2026-06-24), 11 sh
    Current price  : $272.43  (risk to stop: 111 kr, 0.38% of sleeve capital)
    Time exit      : 2026-07-24  (7d left)
    Binding stop   : $271.39 (HARD)
    Tripwires      : FLAGGED -- run run_entry_screen.py for detail
    Tripwire detail : RS -4.4% [WATCH] | Regime stable [OK] | MA50 $266.22 (slope +10.49) [OK] | Cluster avg -5.2% [WATCH, sector-only match -- low-confidence]
    Risk           : TRIPWIRE

==============================================================
NEXT CONTRIBUTION
==============================================================

  Next kr        -> Broadcom (AVGO)
    Current wt (of Reactor Core) : 34.0%
    Target wt (current regime)   : 55.0%
    Gap                          : +21.0%
    Gate                         : OPEN
    Note: Silver excluded -- funded by its own GSR trigger, not new contributions

==============================================================
  Regime check (2026-07-17): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)
Building regime labels ...
  Conditions    : {'ry_regime': 'HIGH', 'baa10y_regime': 'TIGHT'}
  Matched dates : 1395  (2004-05-07 - 2026-07-17)  MODERATE

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
  IBKR      N= 663  mu=  +7.2%  sigma= 20.3%  hist=19yr  [THIN]
  ANET      N= 546  mu= +23.0%  sigma= 24.5%  hist=12yr  [SINGLE]
  DECK      N=1201  mu= +31.4%  sigma= 55.2%  hist=26yr  [MODERATE]
  NRG       N=1201  mu= +21.2%  sigma= 28.7%  hist=23yr  [MODERATE]
  DASH      hist=6yr  (below min 10yr, skipped)
  PWR       N=1201  mu= +19.2%  sigma= 28.3%  hist=26yr  [MODERATE]
  TRGP      N= 546  mu=  -0.6%  sigma= 12.8%  hist=16yr  [SINGLE]
  CF        excluded (see EXCLUDE_TICKERS)
  BKNG      N=1201  mu= +35.3%  sigma= 47.1%  hist=26yr  [MODERATE]
  STLD      N=1201  mu= +15.2%  sigma= 31.1%  hist=26yr  [MODERATE]
  FOXA      hist=7yr  (below min 10yr, skipped)
  CEG       hist=4yr  (below min 10yr, skipped)
  EXV1.DE   no data
  CMI       N=1201  mu= +25.6%  sigma= 29.9%  hist=26yr  [MODERATE]
  GM        N= 546  mu=  +8.4%  sigma= 13.3%  hist=16yr  [SINGLE]
  NVDA      N=1201  mu= +25.1%  sigma= 32.5%  hist=26yr  [MODERATE]
  EME       N=1201  mu= +16.2%  sigma= 27.4%  hist=26yr  [MODERATE]
  TPR       N=1201  mu= +17.5%  sigma= 31.9%  hist=26yr  [MODERATE]
  RL        N=1201  mu= +15.4%  sigma= 26.9%  hist=26yr  [MODERATE]
  CFG       N= 546  mu= +16.4%  sigma= 13.5%  hist=12yr  [SINGLE]
  WDC       N=1201  mu= +20.2%  sigma= 38.8%  hist=26yr  [MODERATE]
  GS        N=1201  mu= +13.3%  sigma= 23.8%  hist=26yr  [MODERATE]
  FOX       hist=7yr  (below min 10yr, skipped)
  PHAG.L    no data
  CIEN      N=1201  mu= +19.7%  sigma= 27.1%  hist=26yr  [MODERATE]
  GRMN      N=1201  mu= +30.2%  sigma= 32.6%  hist=26yr  [MODERATE]
  COHR      max_up=71%  (M&A / corporate event detected, skipped)
  FSLR      N= 784  mu= +29.1%  sigma= 53.6%  hist=20yr  [MODERATE]
  TSLA      N= 546  mu=  +7.4%  sigma= 16.4%  hist=16yr  [SINGLE]
  ISRG      N=1201  mu= +19.0%  sigma= 34.0%  hist=26yr  [MODERATE]
  PM        N= 546  mu= +10.0%  sigma= 14.1%  hist=18yr  [SINGLE]
  FIX       N=1201  mu= +19.1%  sigma= 28.2%  hist=26yr  [MODERATE]
  SYF       N= 546  mu= +14.9%  sigma= 16.4%  hist=12yr  [SINGLE]
  CRWD      hist=7yr  (below min 10yr, skipped)
  APH       N=1201  mu= +17.5%  sigma= 24.8%  hist=26yr  [MODERATE]
  4GLD.DE   no data
  ETR       N=1201  mu= +13.2%  sigma= 19.1%  hist=26yr  [MODERATE]
  PPFB.DE   no data
  GC_F      N=1201  mu=  +9.2%  sigma= 11.3%  hist=26yr  [MODERATE]

Cross-sectional prior mu : +19.1%  (shrinkage target)
Shrinkage lambda         : 100  (asset needs N>>100 to be fully trusted)

Optimizing (50 restarts, 30 candidates) ...

========================================================================
PORTFOLIO OPTIMIZER  --  Regime: RY=HIGH + BAA10Y=TIGHT
========================================================================
  Universe       : top 50 screen candidates + GC_F
  Matched dates  : 1395  MODERATE
  Shrinkage      : lambda=100  prior=+19.1%

  Ticker     Weight   mu(raw)   mu(shr)    sigma      N   Hist       Div
  -----------------------------------------------------------------
  BKNG        33.4%    +35.3%    +34.1%    47.1%   1201    26yr  MODERATE
  GRMN        24.9%    +30.2%    +29.3%    32.6%   1201    26yr  MODERATE
  LITE        14.7%    +39.8%    +31.0%    54.3%    546    11yr    SINGLE
  DECK        12.3%    +31.4%    +30.4%    55.2%   1201    26yr  MODERATE
  AVGO         5.1%    +33.4%    +27.3%    35.6%    546    17yr    SINGLE
  GC_F         5.0%     +9.2%     +9.9%    11.3%   1201    26yr  MODERATE  [gold]
  FSLR         4.6%    +29.1%    +28.0%    53.6%    784    20yr  MODERATE

  Active positions   : 7  (weight >= 1%)
  Equal-weight g(w)  : +19.2%  (benchmark)
  Optimized g(w)     : +28.0%


  NOTE: g(w) is an approximation. mu/sigma are regime-conditional,
  capped at regime end. Shrinkage applied for short-history assets.
========================================================================
