==============================================================
REACTOR CORE -- PORTFOLIO SNAPSHOT
==============================================================
Position                Shares      Price    Value SEK     Wt
--------------------------------------------------------------
  Gold                     304     806 kr   244,976 kr  22.1%
  Silver                     -     552 kr         0 kr   0.0%
  Eli Lilly                 31  11,682 kr   362,128 kr  32.7%
  Walmart                    -   1,098 kr         0 kr   0.0%
  Cameco                     -     915 kr         0 kr   0.0%
  Vertiv                     -   2,597 kr         0 kr   0.0%
  Broadcom                  73   3,622 kr   264,370 kr  23.9%
  Howmet Aerospace           -   2,789 kr         0 kr   0.0%
  Spiltan Räntefond          -     manual   199,038 kr  18.0%
  War Chest                  -     manual        27 kr   0.0%
  Reactor Core Cash          -     manual    35,830 kr   3.2%
--------------------------------------------------------------
  TPV                                        1,106,368 kr
    Reactor Core            907,303 kr  (82%)
    Home Base               199,038 kr  (18%)
    War Chest                    27 kr  (0%)

==============================================================
FI@50 PACE TRACKER
==============================================================
  Start  (2025-07-21)  :       925,983 kr
  Now                     :     1,106,368 kr
  Target (FI@50)          :    12,934,706 kr
  Years remaining         :  12.1

  AWAR (trailing)         :  +17.9%
  Required CAGR           :  +19.6%
  Status                  :  BEHIND  (-1.7% margin)

  Projected @ AWAR        :    11,025,119 kr
  vs target               :    -1,909,587 kr  (deficit)

  Scenario         CAGR       Projected     FI date   (incl. 6,000 kr/mo contributions)
  ------------------------------------------------------------------------
  Bear           +10%       5,175,150 kr       ~2047
  Conservative   +15%       8,350,558 kr       ~2041
  Base           +20%      13,371,934 kr       ~2038
  Current AWAR   +18%      11,025,119 kr       ~2039
  Bull           +30%      33,206,473 kr       ~2035

==============================================================
MACRO REGIME
==============================================================

  Feature                 Value   Regime  
  ------------------------------------------
  Nominal 10Y             4.72%   HIGH
  Real Yield             +2.44%   HIGH  ^
  Breakeven               2.30%   MID
  HY OAS                270 bps   TIGHT
  IG Credit               1.69%   TIGHT
  Curve 10Y-3M          +85 bps   MID
  Curve 10Y-2Y          +52 bps   MID
  SE 10Y                   nan%   --
  USD                     118.9   STRONG

  HY 20d delta  : +1 bps  (flat)
  Confidence    : HIGH
  Data through  : 2026-08-18

==============================================================
PORTFOLIO SIGNALS
==============================================================

  Base: ry=HIGH  nominal_10y=HIGH  baa10y=TIGHT  usd=STRONG

  Position          Wt    21d   63d   63d med  252d med  W252     N  Note
  ----------------------------------------------------------------------
  Gold           22.1%   HIGH   LOW     +3.0%     +4.4%   92%   548  ~base fallback
  Silver          0.0%   HIGH   LOW     +3.8%     +4.0%   70%   548  ~base fallback
  Eli Lilly      32.7%   HIGH  HIGH     -0.2%     -0.2%   47%   156  
  Walmart         0.0%    MID   LOW     +0.8%     +1.6%   59%   547  ~base fallback
  Cameco          0.0%   HIGH   LOW     -1.7%     -1.8%   43%   547  ~base fallback
  Vertiv          0.0%    LOW   LOW     +2.3%     +2.3%   64%    86  
  Broadcom       23.9%    MID   LOW     -0.1%     -0.1%   49%    49  

==============================================================
TACTICAL RULES
==============================================================

  Silver GSR Tactical
    GSR now        : 69.22  (as of 2026-08-18)
    60d GSR peak   : 71.56
    Fall from peak : 3.3%  (no (need >=5% fall for signal))
    T1 threshold   : 83.36  |  T2: 86.45  |  Exit: 62.56
    Signal         : INACTIVE
    Action         : No action -- hold base

  AVGO Trend Diagnostic  [guard RETIRED as a rotation rule -- PR #88]
    AVGO now       : $380.00  (as of 2026-08-18)
    200d SMA       : $368.33  (+3.2% gap)
    5d ROC         : -8.7%  (gap-down buy level: -10%)
    Signal         : BASE  (trigger: none)  -- informational, no rotation
    LLY stress     : inactive  ($1225.73 vs 200d SMA $1045.25, 5d ROC +0.9%)
    Joint stress   : inactive  -- retired alongside the guard, shown for continuity only
    Action         : No action -- guard retired as a rotation rule (see PR #88); reading is diagnostic only

  AVGO Volatility-Targeted Weight  [RETIRED 2026-08-18 -- diagnostic only]
    Trailing 21d vol : 43.2% (annualized)
    Long-run avg vol : 35.3% (annualized)
    Scalar           : 0.82x  (clipped to [0.30x, 1.30x])
    Would-be weights : Gold 28.0%  AVGO 32.7%  LLY 39.2%
    NOT ACTED ON     : routing + rebalance use the static base (see MEMORY.md)

  AVGO Earnings Checkpoint
    Latest qtr EPS (actual vs est.): $2.44 vs $2.40  (+1.7% surprise)
    TTM EPS (non-GAAP actual)  : $8.13
    Forward EPS (+1yr est.)    : $19.53
    Fwd/Trail ratio (normalized): 2.40x  (mid-pack vs. real AI/semi peers; corrected 2026-07-06 from a GAAP/non-GAAP mismatched 3.22x)
    Revenue (latest qtr, actual): $22.19B  (TTM YoY: +32.3%)
    Next-qtr revenue consensus : $29.44B (implied YoY +84.5%)
    Next earnings  : 2026-09-02
    Reminder       : not_due
    Latest quarter : 2026-04-30
    Beat streak    : 4
    Guidance trend : revising up  (+1yr estimate vs. 90 days ago)

  LLY Earnings Checkpoint
    Latest qtr EPS (actual vs est.): $8.38 vs $6.58  (+27.3% surprise)
    TTM EPS (non-GAAP actual)  : $31.49
    Forward EPS (+1yr est.)    : $47.33
    Fwd/Trail ratio (normalized): 1.50x  (baseline established 2026-07-06)
    Revenue (latest qtr, actual): $22.97B  (TTM YoY: +49.6%)
    Next-qtr revenue consensus : $22.23B (implied YoY +26.3%)
    Next earnings  : 2026-10-29
    Reminder       : not_due
    Latest quarter : 2026-06-30
    Beat streak    : 4
    Guidance trend : revising up  (+1yr estimate vs. 90 days ago)

  Opportunistic Sleeve
    Status         : CLOSED (0/1 position)
    Best candidate : STLD (Steel Dynamics, Inc.)  $249.81  (ext +0.2%, 21d med +2.7%, ave +2.4%, win 60.9%, div ROBUST, drift +0.0%)
    Plan           : buy near $249.81, hold ~21d, stop = MA50-5% then trails 3% once +5% gain
    Open           : run_entry_screen.py --open STLD <fill_price> <shares> <capital_sek>
    VIX review     : 15.84  (37% percentile, flat) -- for review, not a gate
    Basket-crash   : none eligible today

==============================================================
NEXT CONTRIBUTION
==============================================================

  Next kr        -> Broadcom (AVGO)
    Current wt (of Reactor Core) : 29.1%
    Target wt (current regime)   : 40.0%
    Gap                          : +10.9%
    Gate                         : OPEN
    Note: Silver excluded -- funded by its own GSR trigger, not new contributions

  AVGO Rebalance Check  [existing capital, band: 10%]
    Gold status: HOLD  (27.0% actual vs 25.0% target, gap -2.0%)
    AVGO status: BUY  (29.1% actual vs 40.0% target, gap +10.9%) -- ~27 shares (~98,552 kr)
    LLY status: HOLD  (39.9% actual vs 35.0% target, gap -4.9%)

==============================================================
  Regime check (2026-08-18): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)
Building regime labels ...
  Conditions    : {'ry_regime': 'HIGH', 'baa10y_regime': 'TIGHT'}
  Matched dates : 1392  (2004-05-07 - 2026-08-18)  MODERATE

Computing capped 252d distributions for 51 candidates ...
  SNDK      hist=2yr  (below min 10yr, skipped)
  APP       hist=5yr  (below min 10yr, skipped)
  HOOD      hist=5yr  (below min 10yr, skipped)
  PLTR      hist=6yr  (below min 10yr, skipped)
  CVNA      hist=9yr  (below min 10yr, skipped)
  GEV       hist=2yr  (below min 10yr, skipped)
  LITE      N= 630  mu= +49.5%  sigma= 60.6%  hist=11yr  [SINGLE]
  SATS      max_up=73%  (M&A / corporate event detected, skipped)
  HWM       hist=10yr  (below min 10yr, skipped)
  VRT       hist=8yr  (below min 10yr, skipped)
  AVGO      N= 630  mu= +27.7%  sigma= 36.1%  hist=17yr  [SINGLE]
  VST       hist=10yr  (below min 10yr, skipped)
  IBKR      N= 743  mu=  +6.9%  sigma= 19.3%  hist=19yr  [THIN]
  ANET      N= 630  mu= +19.9%  sigma= 24.2%  hist=12yr  [SINGLE]
  DECK      N=1269  mu= +31.0%  sigma= 53.8%  hist=27yr  [ROBUST]
  TRGP      N= 630  mu=  +3.4%  sigma= 16.4%  hist=16yr  [SINGLE]
  NRG       N=1269  mu= +21.0%  sigma= 27.8%  hist=23yr  [ROBUST]
  PWR       N=1269  mu= +19.9%  sigma= 27.4%  hist=27yr  [ROBUST]
  STLD      N=1269  mu= +15.3%  sigma= 30.3%  hist=27yr  [ROBUST]
  BKNG      N=1269  mu= +32.5%  sigma= 47.4%  hist=27yr  [ROBUST]
  CF        excluded (see EXCLUDE_TICKERS)
  CMI       N=1269  mu= +25.0%  sigma= 29.2%  hist=27yr  [ROBUST]
  EXV1.DE   no data
  FOXA      hist=7yr  (below min 10yr, skipped)
  DASH      hist=6yr  (below min 10yr, skipped)
  GM        N= 630  mu=  +7.4%  sigma= 12.9%  hist=16yr  [SINGLE]
  CFG       N= 630  mu= +14.7%  sigma= 13.7%  hist=12yr  [SINGLE]
  CEG       hist=5yr  (below min 10yr, skipped)
  CIEN      N=1269  mu= +22.3%  sigma= 28.2%  hist=27yr  [ROBUST]
  WDC       N=1269  mu= +22.5%  sigma= 39.0%  hist=27yr  [ROBUST]
  TPR       N=1269  mu= +18.6%  sigma= 31.1%  hist=26yr  [ROBUST]
  NVDA      N=1269  mu= +23.5%  sigma= 32.4%  hist=27yr  [ROBUST]
  GS        N=1269  mu= +12.7%  sigma= 23.4%  hist=27yr  [ROBUST]
  PHAG.L    no data
  RL        N=1269  mu= +14.8%  sigma= 26.3%  hist=27yr  [ROBUST]
  COHR      max_up=71%  (M&A / corporate event detected, skipped)
  ABB.ST    no data
  FOX       hist=7yr  (below min 10yr, skipped)
  EME       N=1269  mu= +16.1%  sigma= 26.6%  hist=27yr  [ROBUST]
  GRMN      N=1269  mu= +30.5%  sigma= 31.2%  hist=26yr  [ROBUST]
  DELL      hist=10yr  (below min 10yr, skipped)
  TEL2-B.ST  no data
  FIX       N=1269  mu= +20.7%  sigma= 27.9%  hist=27yr  [ROBUST]
  FSLR      N= 864  mu= +23.6%  sigma= 53.3%  hist=20yr  [MODERATE]
  PM        N= 630  mu= +10.8%  sigma= 13.7%  hist=18yr  [SINGLE]
  APH       N=1269  mu= +16.8%  sigma= 24.3%  hist=27yr  [ROBUST]
  FTNT      N= 630  mu=  -8.8%  sigma= 10.3%  hist=17yr  [SINGLE]
  CRWD      hist=7yr  (below min 10yr, skipped)
  AAPL      N=1269  mu= +19.6%  sigma= 28.6%  hist=27yr  [ROBUST]
  SYF       N= 630  mu= +11.4%  sigma= 17.7%  hist=12yr  [SINGLE]
  GC_F      N=1269  mu=  +9.8%  sigma= 11.5%  hist=26yr  [ROBUST]

Cross-sectional prior mu : +18.6%  (shrinkage target)
Shrinkage lambda         : 100  (asset needs N>>100 to be fully trusted)

Optimizing (50 restarts, 29 candidates) ...

========================================================================
PORTFOLIO OPTIMIZER  --  Regime: RY=HIGH + BAA10Y=TIGHT
========================================================================
  Universe       : top 50 screen candidates + GC_F
  Matched dates  : 1392  MODERATE
  Shrinkage      : lambda=100  prior=+18.6%

  Ticker     Weight   mu(raw)   mu(shr)    sigma      N   Hist       Div
  -----------------------------------------------------------------
  GRMN        31.1%    +30.5%    +29.6%    31.2%   1269    26yr    ROBUST
  LITE        29.8%    +49.5%    +37.5%    60.6%    630    11yr    SINGLE
  BKNG        21.8%    +32.5%    +31.5%    47.4%   1269    27yr    ROBUST
  DECK        12.3%    +31.0%    +30.1%    53.8%   1269    27yr    ROBUST
  GC_F         5.0%     +9.8%    +10.5%    11.5%   1269    26yr    ROBUST  [gold]

  Active positions   : 5  (weight >= 1%)
  Equal-weight g(w)  : +18.8%  (benchmark)
  Optimized g(w)     : +28.6%

  WARNING: only 5 active positions — below recommended minimum of 6.
  Consider reducing MAX_W or increasing N_CANDIDATES.

  NOTE: g(w) is an approximation. mu/sigma are regime-conditional,
  capped at regime end. Shrinkage applied for short-history assets.
========================================================================
