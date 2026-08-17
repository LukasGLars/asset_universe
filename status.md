==============================================================
REACTOR CORE -- PORTFOLIO SNAPSHOT
==============================================================
Position                Shares      Price    Value SEK     Wt
--------------------------------------------------------------
  Gold                     304     816 kr   248,029 kr  22.5%
  Silver                     -     575 kr         0 kr   0.0%
  Eli Lilly                 31  11,249 kr   348,718 kr  31.6%
  Walmart                    -   1,087 kr         0 kr   0.0%
  Cameco                     -     937 kr         0 kr   0.0%
  Vertiv                     -   2,780 kr         0 kr   0.0%
  Broadcom                  73   3,731 kr   272,367 kr  24.7%
  Howmet Aerospace           -   2,749 kr         0 kr   0.0%
  Spiltan Räntefond          -     manual   199,038 kr  18.0%
  War Chest                  -     manual        27 kr   0.0%
  Reactor Core Cash          -     manual    35,830 kr   3.2%
--------------------------------------------------------------
  TPV                                        1,104,009 kr
    Reactor Core            904,944 kr  (82%)
    Home Base               199,038 kr  (18%)
    War Chest                    27 kr  (0%)

==============================================================
FI@50 PACE TRACKER
==============================================================
  Start  (2025-07-21)  :       925,983 kr
  Now                     :     1,104,009 kr
  Target (FI@50)          :    12,934,706 kr
  Years remaining         :  10.9

  AWAR (trailing)         :  +17.8%
  Required CAGR           :  +22.4%
  Status                  :  BEHIND  (-4.6% margin)

  Projected @ AWAR        :     8,822,971 kr
  vs target               :    -4,111,735 kr  (deficit)

  Scenario         CAGR       Projected     FI date   (incl. 6,000 kr/mo contributions)
  ------------------------------------------------------------------------
  Bear           +10%       4,518,368 kr       ~2047
  Conservative   +15%       6,951,978 kr       ~2041
  Base           +20%      10,613,485 kr       ~2038
  Current AWAR   +18%       8,822,971 kr       ~2039
  Bull           +30%      24,009,145 kr       ~2035

==============================================================
MACRO REGIME
==============================================================

  Feature                 Value   Regime  
  ------------------------------------------
  Nominal 10Y             4.68%   HIGH
  Real Yield             +2.41%   HIGH  ^
  Breakeven               2.27%   MID
  HY OAS                267 bps   TIGHT
  IG Credit               1.67%   TIGHT
  Curve 10Y-3M          +82 bps   MID
  Curve 10Y-2Y          +51 bps   MID
  SE 10Y                   nan%   --
  USD                       nan   --

  HY 20d delta  : -6 bps  (tightening)
  Confidence    : HIGH
  Data through  : 2026-08-17

==============================================================
PORTFOLIO SIGNALS
==============================================================

  Base: ry=HIGH  nominal_10y=HIGH  baa10y=TIGHT

  Position          Wt    21d   63d   63d med  252d med  W252     N  Note
  ----------------------------------------------------------------------
  Gold           22.5%   HIGH   LOW     +3.1%     +4.4%   92%   547  ~base fallback
  Silver          0.0%   HIGH   LOW     +3.8%     +4.0%   70%   547  ~base fallback
  Eli Lilly      31.6%    MID  HIGH     -0.7%     -0.7%   35%   139  
  Walmart         0.0%    MID   LOW     +0.9%     +0.9%   68%    94  
  Cameco          0.0%   HIGH   LOW     +0.4%     -1.0%   47%  1173  ~base fallback
  Vertiv          0.0%    MID   LOW     +0.6%     -2.4%   44%   546  ~base fallback
  Broadcom       24.7%    MID   LOW     -0.1%     -0.1%   49%    49  

==============================================================
TACTICAL RULES
==============================================================

  Silver GSR Tactical
    GSR now        : 67.84  (as of 2026-08-17)
    60d GSR peak   : 71.56
    Fall from peak : 5.2%  (yes)
    T1 threshold   : 83.36  |  T2: 86.45  |  Exit: 62.56
    Signal         : INACTIVE
    Action         : No action -- hold base

  AVGO Trend Diagnostic  [guard RETIRED as a rotation rule -- PR #88]
    AVGO now       : $392.43  (as of 2026-08-17)
    200d SMA       : $368.35  (+6.5% gap)
    5d ROC         : -7.1%  (gap-down buy level: -10%)
    Signal         : BASE  (trigger: none)  -- informational, no rotation
    LLY stress     : inactive  ($1183.16 vs 200d SMA $1043.17, 5d ROC -4.0%)
    Joint stress   : inactive  -- retired alongside the guard, shown for continuity only
    Action         : No action -- guard retired as a rotation rule (see PR #88); reading is diagnostic only

  AVGO Volatility-Targeted Weight
    Trailing 21d vol : 42.0% (annualized)
    Long-run avg vol : 35.3% (annualized)
    Scalar           : 0.84x  (clipped to [0.30x, 1.30x])
    Target weights   : Gold 27.6%  AVGO 33.7%  LLY 38.7%

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
    Best candidate : HWM (Howmet Aerospace Inc.)  $289.12  (ext +4.8%, 21d med +2.4%, ave +3.6%, win 64.6%, div THIN, drift +0.0%)
    Plan           : buy near $289.12, hold ~21d, stop = MA50-5% then trails 3% once +5% gain
    Open           : run_entry_screen.py --open HWM <fill_price> <shares> <capital_sek>
    VIX review     : 15.19  (33% percentile, flat) -- for review, not a gate
    Basket-crash   : none eligible today

==============================================================
NEXT CONTRIBUTION
==============================================================

  Next kr        -> Broadcom (AVGO)
    Current wt (of Reactor Core) : 30.1%
    Target wt (current regime)   : 33.7%
    Gap                          : +3.6%
    Gate                         : OPEN
    Note: Silver excluded -- funded by its own GSR trigger, not new contributions

  AVGO Rebalance Check  [existing capital, band: 5%]
    Gold status: HOLD  (27.4% actual vs 27.6% target, gap +0.2%)
    AVGO status: HOLD  (30.1% actual vs 33.7% target, gap +3.6%)
    LLY status: HOLD  (38.5% actual vs 38.7% target, gap +0.2%)

==============================================================
  Regime check (2026-08-17): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)
Building regime labels ...
  Conditions    : {'ry_regime': 'HIGH', 'baa10y_regime': 'TIGHT'}
  Matched dates : 1391  (2004-05-07 - 2026-08-17)  MODERATE

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
  NRG       N=1269  mu= +21.0%  sigma= 27.8%  hist=23yr  [ROBUST]
  TRGP      N= 630  mu=  +3.4%  sigma= 16.4%  hist=16yr  [SINGLE]
  PWR       N=1269  mu= +19.9%  sigma= 27.4%  hist=27yr  [ROBUST]
  STLD      N=1269  mu= +15.3%  sigma= 30.3%  hist=27yr  [ROBUST]
  BKNG      N=1269  mu= +32.5%  sigma= 47.4%  hist=27yr  [ROBUST]
  CF        excluded (see EXCLUDE_TICKERS)
  EXV1.DE   no data
  FOXA      hist=7yr  (below min 10yr, skipped)
  CMI       N=1269  mu= +25.0%  sigma= 29.2%  hist=27yr  [ROBUST]
  DASH      hist=6yr  (below min 10yr, skipped)
  GM        N= 630  mu=  +7.4%  sigma= 12.9%  hist=16yr  [SINGLE]
  CEG       hist=5yr  (below min 10yr, skipped)
  CFG       N= 630  mu= +14.7%  sigma= 13.7%  hist=12yr  [SINGLE]
  CIEN      N=1269  mu= +22.3%  sigma= 28.2%  hist=27yr  [ROBUST]
  TPR       N=1269  mu= +18.6%  sigma= 31.1%  hist=26yr  [ROBUST]
  WDC       N=1269  mu= +22.5%  sigma= 39.0%  hist=27yr  [ROBUST]
  NVDA      N=1269  mu= +23.5%  sigma= 32.4%  hist=27yr  [ROBUST]
  GS        N=1269  mu= +12.7%  sigma= 23.4%  hist=27yr  [ROBUST]
  RL        N=1269  mu= +14.8%  sigma= 26.3%  hist=27yr  [ROBUST]
  PHAG.L    no data
  COHR      max_up=71%  (M&A / corporate event detected, skipped)
  FOX       hist=7yr  (below min 10yr, skipped)
  EME       N=1269  mu= +16.1%  sigma= 26.6%  hist=27yr  [ROBUST]
  GRMN      N=1269  mu= +30.5%  sigma= 31.2%  hist=26yr  [ROBUST]
  DELL      hist=10yr  (below min 10yr, skipped)
  FSLR      N= 864  mu= +23.6%  sigma= 53.3%  hist=20yr  [MODERATE]
  FIX       N=1269  mu= +20.7%  sigma= 27.9%  hist=27yr  [ROBUST]
  PM        N= 630  mu= +10.8%  sigma= 13.7%  hist=18yr  [SINGLE]
  APH       N=1269  mu= +16.8%  sigma= 24.3%  hist=27yr  [ROBUST]
  FTNT      N= 630  mu=  -8.8%  sigma= 10.3%  hist=17yr  [SINGLE]
  CRWD      hist=7yr  (below min 10yr, skipped)
  AAPL      N=1269  mu= +19.6%  sigma= 28.6%  hist=27yr  [ROBUST]
  SYF       N= 630  mu= +11.4%  sigma= 17.7%  hist=12yr  [SINGLE]
  4GLD.DE   no data
  ETR       N=1269  mu= +13.3%  sigma= 18.5%  hist=27yr  [ROBUST]
  GC_F      N=1269  mu=  +9.8%  sigma= 11.5%  hist=26yr  [ROBUST]

Cross-sectional prior mu : +18.4%  (shrinkage target)
Shrinkage lambda         : 100  (asset needs N>>100 to be fully trusted)

Optimizing (50 restarts, 30 candidates) ...

========================================================================
PORTFOLIO OPTIMIZER  --  Regime: RY=HIGH + BAA10Y=TIGHT
========================================================================
  Universe       : top 50 screen candidates + GC_F
  Matched dates  : 1391  MODERATE
  Shrinkage      : lambda=100  prior=+18.4%

  Ticker     Weight   mu(raw)   mu(shr)    sigma      N   Hist       Div
  -----------------------------------------------------------------
  GRMN        31.2%    +30.5%    +29.6%    31.2%   1269    26yr    ROBUST
  LITE        29.7%    +49.5%    +37.4%    60.6%    630    11yr    SINGLE
  BKNG        21.8%    +32.5%    +31.4%    47.4%   1269    27yr    ROBUST
  DECK        12.3%    +31.0%    +30.1%    53.8%   1269    27yr    ROBUST
  GC_F         5.0%     +9.8%    +10.4%    11.5%   1269    26yr    ROBUST  [gold]

  Active positions   : 5  (weight >= 1%)
  Equal-weight g(w)  : +18.6%  (benchmark)
  Optimized g(w)     : +28.6%

  WARNING: only 5 active positions — below recommended minimum of 6.
  Consider reducing MAX_W or increasing N_CANDIDATES.

  NOTE: g(w) is an approximation. mu/sigma are regime-conditional,
  capped at regime end. Shrinkage applied for short-history assets.
========================================================================
