==============================================================
REACTOR CORE -- PORTFOLIO SNAPSHOT
==============================================================
Position                Shares      Price    Value SEK     Wt
--------------------------------------------------------------
  Gold                     304     860 kr   261,493 kr  24.0%
  Silver                     -     596 kr         0 kr   0.0%
  Eli Lilly                 31  11,823 kr   366,506 kr  33.7%
  Walmart                    -   1,010 kr         0 kr   0.0%
  Cameco                     -     970 kr         0 kr   0.0%
  Vertiv                     -   2,417 kr         0 kr   0.0%
  Broadcom                  77   3,402 kr   261,922 kr  24.1%
  Howmet Aerospace           -   2,496 kr         0 kr   0.0%
  Spiltan Räntefond          -     manual   199,038 kr  18.3%
  War Chest                  -     manual        27 kr   0.0%
  Reactor Core Cash          -     manual        24 kr   0.0%
--------------------------------------------------------------
  TPV                                        1,089,009 kr
    Reactor Core            889,944 kr  (81.7%)   target 85.0%  drift -3.3%
    Home Base               199,038 kr  (18.3%)   target 15.0%  drift +3.3%
    War Chest                    27 kr  ( 0.0%)   target  0.0%  drift +0.0%

==============================================================
FI@50 PACE TRACKER
==============================================================
  Start  (2025-07-21)  :       925,983 kr
  Now                     :     1,089,009 kr
  Threshold (2026 kr)     :    16,150,000 kr   (indexed 2.0%/yr)
  Trigger now             :    16,357,969 kr
  Trigger @ horizon       :    20,798,454 kr
  Years remaining         :  12.1

  AWAR (trailing)         :  +16.0%
  Required CAGR           :  +25.0%
  Status                  :  BEHIND  (-9.0% margin)

  Projected @ AWAR        :     9,019,391 kr
  vs target               :   -11,779,063 kr  (deficit)

  Scenario         CAGR       Projected     FI date   (incl. 6,000 kr/mo contributions)
  ------------------------------------------------------------------------
  Bear           +10%       5,110,720 kr       ~2056
  Conservative   +15%       8,235,672 kr       ~2046
  Base           +20%      13,172,332 kr       ~2042
  Current AWAR   +16%       9,019,391 kr       ~2045
  Bull           +30%      32,644,249 kr       ~2037

==============================================================
MACRO REGIME
==============================================================

  Feature                 Value   Regime  
  ------------------------------------------
  Nominal 10Y             4.74%   HIGH
  Real Yield             +2.40%   HIGH  ^
  Breakeven               2.32%   MID
  HY OAS                270 bps   TIGHT
  IG Credit               1.63%   TIGHT
  Curve 10Y-3M          +83 bps   MID
  Curve 10Y-2Y          +46 bps   LOW
  SE 10Y                   nan%   --
  USD                     118.1   STRONG

  HY 20d delta  : -9 bps  (tightening)
  Confidence    : HIGH
  Data through  : 2026-08-24

==============================================================
PORTFOLIO SIGNALS
==============================================================

  Base: ry=HIGH  nominal_10y=HIGH  baa10y=TIGHT  usd=STRONG

  Position          Wt    21d   63d   63d med  252d med  W252     N  Note
  ----------------------------------------------------------------------
  Gold           24.0%   HIGH   MID     -0.2%     -0.2%   40%    42  
  Silver          0.0%   HIGH   LOW     +3.6%     +4.0%   70%   553  ~base fallback
  Eli Lilly      33.7%   HIGH  HIGH     -0.2%     -0.2%   47%   156  
  Walmart         0.0%    LOW   LOW     +1.0%     +1.0%   61%    79  
  Cameco          0.0%   HIGH   MID     -2.4%     -2.4%   34%    53  
  Vertiv          0.0%    LOW   LOW     +2.3%     +2.3%   64%    86  
  Broadcom       24.1%    LOW   LOW     +0.9%     +0.9%   59%    98  

==============================================================
TACTICAL RULES
==============================================================

  Silver GSR Tactical
    GSR now        : 68.29  (as of 2026-08-24)
    60d GSR peak   : 71.56
    Fall from peak : 4.6%  (no (need >=5% fall for signal))
    T1 threshold   : 83.36  |  T2: 86.45  |  Exit: 62.56
    Signal         : INACTIVE
    Action         : No action -- hold base

  AVGO Trend Diagnostic  [guard RETIRED as a rotation rule -- PR #88]
    AVGO now       : $358.76  (as of 2026-08-24)
    200d SMA       : $368.34  (-2.6% gap)
    5d ROC         : -8.6%  (gap-down buy level: -10%)
    Signal         : DEFENSIVE  (trigger: MA)  -- informational, no rotation
    LLY stress     : inactive  ($1246.93 vs 200d SMA $1052.91, 5d ROC +5.4%)
    Joint stress   : inactive  -- retired alongside the guard, shown for continuity only
    Action         : No action -- guard retired as a rotation rule (see PR #88); reading is diagnostic only

  AVGO Volatility-Targeted Weight  [RETIRED 2026-08-18 -- diagnostic only]
    Trailing 21d vol : 44.3% (annualized)
    Long-run avg vol : 35.3% (annualized)
    Scalar           : 0.80x  (clipped to [0.30x, 1.30x])
    Would-be weights : Gold 28.4%  AVGO 31.9%  LLY 39.7%
    NOT ACTED ON     : routing + rebalance use the static base (see MEMORY.md)

  AVGO Earnings Checkpoint
    Latest qtr EPS (actual vs est.): $2.44 vs $2.40  (+1.7% surprise)
    TTM EPS (non-GAAP actual)  : $8.13
    Forward EPS (+1yr est.)    : $19.50
    Fwd/Trail ratio (normalized): 2.40x  (mid-pack vs. real AI/semi peers; corrected 2026-07-06 from a GAAP/non-GAAP mismatched 3.22x)
    Revenue (latest qtr, actual): $22.19B  (TTM YoY: +32.3%)
    Next-qtr revenue consensus : $29.43B (implied YoY +84.5%)
    Next earnings  : 2026-09-02
    Reminder       : not_due
    Latest quarter : 2026-04-30
    Beat streak    : 4
    Guidance trend : revising up  (+1yr estimate vs. 90 days ago)

  LLY Earnings Checkpoint
    Latest qtr EPS (actual vs est.): $8.38 vs $6.58  (+27.3% surprise)
    TTM EPS (non-GAAP actual)  : $31.49
    Forward EPS (+1yr est.)    : $47.23
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
    Best candidate : HOOD (Robinhood Markets, Inc.)  $103.62  (ext +3.1%, 21d med +3.9%, ave +5.3%, win 59.2%, div THIN, drift -0.0%)
    Plan           : buy near $103.62, hold ~21d, stop = MA50-5% then trails 3% once +5% gain
    Open           : run_entry_screen.py --open HOOD <fill_price> <shares> <capital_sek>
    VIX review     : 15.85  (37% percentile, flat) -- for review, not a gate
    Basket-crash   : WDC (Western Digital Corporation)  $435.38  (sector Technology, -18.8% 5d, 3 peers crashing, drift -0.0%)
    Plan           : buy near $435.38, flat 21d exit, NO stop until +8% gain then trails 8% (no floor before that -- riskier than the extension pathway)
    Open           : run_entry_screen.py --open WDC <fill_price> <shares> <capital_sek> --entry-type basket_crash
    NOTE           : extension pathway also has a candidate today (HOOD) -- that one is preferred (live-validated); this is shown for awareness.

==============================================================
NEXT CONTRIBUTION
==============================================================

  Next kr        -> Broadcom (AVGO)
    Current wt (of Reactor Core) : 29.4%
    Target wt (current regime)   : 40.0%
    Gap                          : +10.6%
    Gate                         : OPEN
    Note: Silver excluded -- funded by its own GSR trigger, not new contributions

  AVGO Rebalance Check  [existing capital, band: 10%]
    Gold status: HOLD  (29.4% actual vs 25.0% target, gap -4.4%)
    AVGO status: BUY  (29.4% actual vs 40.0% target, gap +10.6%) -- ~28 shares (~94,046 kr)
    LLY status: HOLD  (41.2% actual vs 35.0% target, gap -6.2%)

  Idle Reactor Core Cash
    Uninvested     : 24 kr  (0.0% of Reactor Core)
    Action         : deploy -> Broadcom (AVGO)  (~0 shares at 3,402 kr)

==============================================================
  Regime check (2026-08-24): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)
Building regime labels ...
  Conditions    : {'ry_regime': 'HIGH', 'baa10y_regime': 'TIGHT'}
  Matched dates : 1396  (2004-05-07 - 2026-08-24)  MODERATE

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
  TRGP      N= 630  mu=  +3.4%  sigma= 16.4%  hist=16yr  [SINGLE]
  ANET      N= 630  mu= +19.9%  sigma= 24.2%  hist=12yr  [SINGLE]
  DECK      N=1269  mu= +31.0%  sigma= 53.8%  hist=27yr  [ROBUST]
  NRG       N=1269  mu= +21.0%  sigma= 27.8%  hist=23yr  [ROBUST]
  PWR       N=1269  mu= +19.9%  sigma= 27.4%  hist=27yr  [ROBUST]
  STLD      N=1269  mu= +15.3%  sigma= 30.3%  hist=27yr  [ROBUST]
  BKNG      N=1269  mu= +32.5%  sigma= 47.4%  hist=27yr  [ROBUST]
  CF        excluded (see EXCLUDE_TICKERS)
  CMI       N=1269  mu= +25.0%  sigma= 29.2%  hist=27yr  [ROBUST]
  EXV1.DE   no data
  GM        N= 630  mu=  +7.4%  sigma= 12.9%  hist=16yr  [SINGLE]
  FOXA      hist=7yr  (below min 10yr, skipped)
  DASH      hist=6yr  (below min 10yr, skipped)
  CIEN      N=1269  mu= +22.3%  sigma= 28.2%  hist=27yr  [ROBUST]
  CFG       N= 630  mu= +14.7%  sigma= 13.7%  hist=12yr  [SINGLE]
  CEG       hist=5yr  (below min 10yr, skipped)
  WDC       N=1269  mu= +22.5%  sigma= 39.0%  hist=27yr  [ROBUST]
  TPR       N=1269  mu= +18.6%  sigma= 31.1%  hist=26yr  [ROBUST]
  GS        N=1269  mu= +12.7%  sigma= 23.4%  hist=27yr  [ROBUST]
  NVDA      N=1269  mu= +23.5%  sigma= 32.4%  hist=27yr  [ROBUST]
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
  FTNT      N= 630  mu=  -8.8%  sigma= 10.3%  hist=17yr  [SINGLE]
  APH       N=1269  mu= +16.8%  sigma= 24.3%  hist=27yr  [ROBUST]
  PM        N= 630  mu= +10.8%  sigma= 13.7%  hist=18yr  [SINGLE]
  CRWD      hist=7yr  (below min 10yr, skipped)
  AAPL      N=1269  mu= +19.6%  sigma= 28.6%  hist=27yr  [ROBUST]
  4GLD.DE   no data
  GC_F      N=1269  mu=  +9.8%  sigma= 11.5%  hist=26yr  [ROBUST]

Cross-sectional prior mu : +18.8%  (shrinkage target)
Shrinkage lambda         : 100  (asset needs N>>100 to be fully trusted)

Optimizing (50 restarts, 28 candidates) ...

========================================================================
PORTFOLIO OPTIMIZER  --  Regime: RY=HIGH + BAA10Y=TIGHT
========================================================================
  Universe       : top 50 screen candidates + GC_F
  Matched dates  : 1396  MODERATE
  Shrinkage      : lambda=100  prior=+18.8%

  Ticker     Weight   mu(raw)   mu(shr)    sigma      N   Hist       Div
  -----------------------------------------------------------------
  GRMN        31.0%    +30.5%    +29.6%    31.2%   1269    26yr    ROBUST
  LITE        30.0%    +49.5%    +37.6%    60.6%    630    11yr    SINGLE
  BKNG        21.7%    +32.5%    +31.5%    47.4%   1269    27yr    ROBUST
  DECK        12.3%    +31.0%    +30.1%    53.8%   1269    27yr    ROBUST
  GC_F         5.0%     +9.8%    +10.5%    11.5%   1269    26yr    ROBUST  [gold]

  Active positions   : 5  (weight >= 1%)
  Equal-weight g(w)  : +19.0%  (benchmark)
  Optimized g(w)     : +28.7%

  WARNING: only 5 active positions — below recommended minimum of 6.
  Consider reducing MAX_W or increasing N_CANDIDATES.

  NOTE: g(w) is an approximation. mu/sigma are regime-conditional,
  capped at regime end. Shrinkage applied for short-history assets.
========================================================================
