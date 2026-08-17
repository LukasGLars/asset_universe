==============================================================
REACTOR CORE -- PORTFOLIO SNAPSHOT
==============================================================
Position                Shares      Price    Value SEK     Wt
--------------------------------------------------------------
  Gold                     304     810 kr   246,274 kr  22.2%
  Silver                     -     563 kr         0 kr   0.0%
  Eli Lilly                 16  11,231 kr   179,688 kr  16.2%
  Walmart                    -   1,097 kr         0 kr   0.0%
  Cameco                     -     930 kr         0 kr   0.0%
  Vertiv                     -   2,796 kr         0 kr   0.0%
  Broadcom                 101   3,740 kr   377,713 kr  34.1%
  Howmet Aerospace           -   2,752 kr         0 kr   0.0%
  Spiltan Räntefond          -     manual   199,038 kr  18.0%
  War Chest                  -     manual   100,565 kr   9.1%
  Reactor Core Cash          -     manual     3,679 kr   0.3%
--------------------------------------------------------------
  TPV                                        1,106,957 kr
    Reactor Core            807,354 kr  (73%)
    Home Base               199,038 kr  (18%)
    War Chest               100,565 kr  (9%)

==============================================================
FI@50 PACE TRACKER
==============================================================
  Start  (2025-07-21)  :       925,983 kr
  Now                     :     1,106,957 kr
  Target (FI@50)          :    12,934,706 kr
  Years remaining         :  10.9

  AWAR (trailing)         :  +18.1%
  Required CAGR           :  +22.4%
  Status                  :  BEHIND  (-4.3% margin)

  Projected @ AWAR        :     9,062,257 kr
  vs target               :    -3,872,449 kr  (deficit)

  Scenario         CAGR       Projected     FI date   (incl. 6,000 kr/mo contributions)
  ------------------------------------------------------------------------
  Bear           +10%       4,526,720 kr       ~2047
  Conservative   +15%       6,965,553 kr       ~2041
  Base           +20%      10,635,096 kr       ~2038
  Current AWAR   +18%       9,062,257 kr       ~2039
  Bull           +30%      24,060,969 kr       ~2035

==============================================================
MACRO REGIME
==============================================================

  Feature                 Value   Regime  
  ------------------------------------------
  Nominal 10Y             4.63%   HIGH
  Real Yield             +2.39%   HIGH  ^
  Breakeven               2.27%   MID
  HY OAS                271 bps   TIGHT
  IG Credit               1.67%   TIGHT
  Curve 10Y-3M          +82 bps   MID
  Curve 10Y-2Y          +51 bps   MID
  SE 10Y                   nan%   --
  USD                     119.1   STRONG

  HY 20d delta  : +0 bps  (flat)
  Confidence    : HIGH
  Data through  : 2026-08-14

==============================================================
PORTFOLIO SIGNALS
==============================================================

  Base: ry=HIGH  nominal_10y=HIGH  baa10y=TIGHT  usd=STRONG

  Position          Wt    21d   63d   63d med  252d med  W252     N  Note
  ----------------------------------------------------------------------
  Gold           22.2%   HIGH   LOW     +3.1%     +4.4%   92%   546  ~base fallback
  Silver          0.0%   HIGH   LOW     +3.8%     +4.0%   70%   546  ~base fallback
  Eli Lilly      16.2%    MID  HIGH     -0.9%     -0.9%   40%    80  
  Walmart         0.0%    MID   LOW     +0.8%     +1.6%   59%   545  ~base fallback
  Cameco          0.0%   HIGH   LOW     -1.7%     -1.8%   43%   545  ~base fallback
  Vertiv          0.0%    MID   LOW     +0.7%     -2.4%   44%   545  ~base fallback
  Broadcom       34.1%    MID   LOW     -0.1%     -0.1%   49%    49  

==============================================================
TACTICAL RULES
==============================================================

  Silver GSR Tactical
    GSR now        : 68.33  (as of 2026-08-14)
    60d GSR peak   : 71.56
    Fall from peak : 4.5%  (no (need >=5% fall for signal))
    T1 threshold   : 83.36  |  T2: 86.45  |  Exit: 62.56
    Signal         : INACTIVE
    Action         : No action -- hold base

  AVGO Trend Diagnostic  [guard RETIRED as a rotation rule -- PR #88]
    AVGO now       : $392.99  (as of 2026-08-14)
    200d SMA       : $368.25  (+6.7% gap)
    5d ROC         : -8.1%  (gap-down buy level: -10%)
    Signal         : BASE  (trigger: none)  -- informational, no rotation
    LLY stress     : inactive  ($1180.16 vs 200d SMA $1041.33, 5d ROC -0.5%)
    Joint stress   : inactive  -- retired alongside the guard, shown for continuity only
    Action         : No action -- guard retired as a rotation rule (see PR #88); reading is diagnostic only

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
    Best candidate : STLD (Steel Dynamics, Inc.)  $255.77  (ext +2.2%, 21d med +2.8%, ave +2.4%, win 61.1%, div ROBUST, drift -0.0%)
    Plan           : buy near $255.77, hold ~21d, stop = MA50-5% then trails 3% once +5% gain
    Open           : run_entry_screen.py --open STLD <fill_price> <shares> <capital_sek>
    VIX review     : 14.25  (26% percentile, flat) -- for review, not a gate
    Basket-crash   : none eligible today

==============================================================
NEXT CONTRIBUTION
==============================================================

  Next kr        -> Eli Lilly (LLY)
    Current wt (of Reactor Core) : 22.3%
    Target wt (current regime)   : 35.0%
    Gap                          : +12.7%
    Gate                         : OPEN
    Note: Silver excluded -- funded by its own GSR trigger, not new contributions

==============================================================
  Regime check (2026-08-14): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)
Building regime labels ...
  Conditions    : {'ry_regime': 'HIGH', 'baa10y_regime': 'TIGHT'}
  Matched dates : 1399  (2004-05-07 - 2026-08-14)  MODERATE

Computing capped 252d distributions for 51 candidates ...
  SNDK      hist=1yr  (below min 10yr, skipped)
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
  IBKR      N= 747  mu=  +6.8%  sigma= 19.3%  hist=19yr  [THIN]
  ANET      N= 630  mu= +19.9%  sigma= 24.2%  hist=12yr  [SINGLE]
  DECK      N=1278  mu= +30.8%  sigma= 53.7%  hist=27yr  [ROBUST]
  NRG       N=1278  mu= +20.8%  sigma= 27.8%  hist=23yr  [ROBUST]
  TRGP      N= 630  mu=  +3.4%  sigma= 16.4%  hist=16yr  [SINGLE]
  PWR       N=1278  mu= +19.6%  sigma= 27.4%  hist=27yr  [ROBUST]
  STLD      N=1278  mu= +15.2%  sigma= 30.2%  hist=27yr  [ROBUST]
  CF        excluded (see EXCLUDE_TICKERS)
  BKNG      N=1278  mu= +32.2%  sigma= 47.3%  hist=27yr  [ROBUST]
  EXV1.DE   no data
  FOXA      hist=7yr  (below min 10yr, skipped)
  DASH      hist=6yr  (below min 10yr, skipped)
  GM        N= 630  mu=  +7.4%  sigma= 12.9%  hist=16yr  [SINGLE]
  CMI       N=1278  mu= +24.9%  sigma= 29.1%  hist=27yr  [ROBUST]
  CEG       hist=5yr  (below min 10yr, skipped)
  CFG       N= 630  mu= +14.7%  sigma= 13.7%  hist=12yr  [SINGLE]
  TPR       N=1278  mu= +18.3%  sigma= 31.2%  hist=26yr  [ROBUST]
  WDC       N=1278  mu= +22.1%  sigma= 39.0%  hist=27yr  [ROBUST]
  NVDA      N=1278  mu= +23.3%  sigma= 32.3%  hist=27yr  [ROBUST]
  GS        N=1278  mu= +12.4%  sigma= 23.4%  hist=27yr  [ROBUST]
  PHAG.L    no data
  CIEN      N=1278  mu= +22.1%  sigma= 28.2%  hist=27yr  [ROBUST]
  RL        N=1278  mu= +14.7%  sigma= 26.2%  hist=27yr  [ROBUST]
  COHR      max_up=71%  (M&A / corporate event detected, skipped)
  FOX       hist=7yr  (below min 10yr, skipped)
  EME       N=1278  mu= +15.9%  sigma= 26.6%  hist=27yr  [ROBUST]
  GRMN      N=1278  mu= +30.0%  sigma= 31.5%  hist=26yr  [ROBUST]
  DELL      hist=10yr  (below min 10yr, skipped)
  FSLR      N= 868  mu= +24.1%  sigma= 53.2%  hist=20yr  [MODERATE]
  FIX       N=1278  mu= +20.5%  sigma= 27.9%  hist=27yr  [ROBUST]
  PM        N= 630  mu= +10.8%  sigma= 13.7%  hist=18yr  [SINGLE]
  APH       N=1278  mu= +16.7%  sigma= 24.3%  hist=27yr  [ROBUST]
  ISRG      N=1278  mu= +17.5%  sigma= 33.6%  hist=26yr  [ROBUST]
  FTNT      N= 630  mu=  -8.8%  sigma= 10.3%  hist=17yr  [SINGLE]
  CRWD      hist=7yr  (below min 10yr, skipped)
  SYF       N= 630  mu= +11.4%  sigma= 17.7%  hist=12yr  [SINGLE]
  AAPL      N=1278  mu= +19.4%  sigma= 28.6%  hist=27yr  [ROBUST]
  4GLD.DE   no data
  GC_F      N=1278  mu=  +9.8%  sigma= 11.4%  hist=26yr  [ROBUST]

Cross-sectional prior mu : +18.4%  (shrinkage target)
Shrinkage lambda         : 100  (asset needs N>>100 to be fully trusted)

Optimizing (50 restarts, 30 candidates) ...

========================================================================
PORTFOLIO OPTIMIZER  --  Regime: RY=HIGH + BAA10Y=TIGHT
========================================================================
  Universe       : top 50 screen candidates + GC_F
  Matched dates  : 1399  MODERATE
  Shrinkage      : lambda=100  prior=+18.4%

  Ticker     Weight   mu(raw)   mu(shr)    sigma      N   Hist       Div
  -----------------------------------------------------------------
  LITE        30.5%    +49.5%    +37.5%    60.6%    630    11yr    SINGLE
  GRMN        29.6%    +30.0%    +29.2%    31.5%   1278    26yr    ROBUST
  BKNG        22.3%    +32.2%    +31.2%    47.3%   1278    27yr    ROBUST
  DECK        12.6%    +30.8%    +29.9%    53.7%   1278    27yr    ROBUST
  GC_F         5.0%     +9.8%    +10.5%    11.4%   1278    26yr    ROBUST  [gold]

  Active positions   : 5  (weight >= 1%)
  Equal-weight g(w)  : +18.6%  (benchmark)
  Optimized g(w)     : +28.4%

  WARNING: only 5 active positions — below recommended minimum of 6.
  Consider reducing MAX_W or increasing N_CANDIDATES.

  NOTE: g(w) is an approximation. mu/sigma are regime-conditional,
  capped at regime end. Shrinkage applied for short-history assets.
========================================================================
