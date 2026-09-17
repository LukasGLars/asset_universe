==============================================================
REACTOR CORE -- PORTFOLIO SNAPSHOT
==============================================================================
Position                Shares      Price    Value SEK     Wt    Tgt   Drift
------------------------------------------------------------------------------
  Gold                     243     827 kr   201,076 kr  18.6%  20.0%   -1.4%
  Silver                     -     589 kr         0 kr   0.0%   0.0%   +0.0%
  Eli Lilly                 19  11,354 kr   215,731 kr  20.0%  20.0%   -0.0%
  Walmart                    -   1,052 kr         0 kr   0.0%   0.0%   +0.0%
  Cameco                     -     914 kr         0 kr   0.0%   0.0%   +0.0%
  Vertiv                     -   2,379 kr         0 kr   0.0%   0.0%   +0.0%
  Broadcom                  65   3,422 kr   222,413 kr  20.6%  20.0%   +0.6%
  Howmet Aerospace           -   2,224 kr         0 kr   0.0%   0.0%   +0.0%
  Spiltan Räntefond    1,307.31     153 kr   199,417 kr  18.5%   0.0%  +18.5%
  War Chest                  -     manual        19 kr   0.0%   0.0%   +0.0%
  Reactor Core Cash          -     manual   187,520 kr  17.4%  10.0%   +7.4%
  Virtune Bitcoin          218     124 kr    27,032 kr   2.5%   2.5%   +0.0%
  Virtune Staked ETH       470      57 kr    26,705 kr   2.5%   2.5%   -0.0%
  LF Global Index            -     601 kr         0 kr   0.0%  25.0%  -25.0%
------------------------------------------------------------------------------
  TPV                                        1,079,914 kr
    Reactor Core            639,220 kr  (59.2%)   target 60.0%  drift -0.8%
    Global Index                  0 kr  ( 0.0%)   target 25.0%  drift -25.0%
    Home Base               386,937 kr  (35.8%)   target 10.0%  drift +25.8%
    Crypto Sleeve            53,737 kr  ( 5.0%)   target  5.0%  drift -0.0%
    War Chest                    19 kr  ( 0.0%)   target  0.0%  drift +0.0%

==============================================================
FI@50 PACE TRACKER
==============================================================
  Start  (2025-07-21)  :       925,983 kr
  Now                     :     1,079,914 kr
  Threshold (2026 kr)     :    16,150,000 kr   (indexed 2.0%/yr)
  Trigger now             :    16,378,380 kr
  Trigger @ horizon       :    20,798,454 kr
  Years remaining         :  12.1

  AWAR (trailing)         :  +14.2%
  Required CAGR           :  +25.2%
  Status                  :  BEHIND  (-11.0% margin)

  Projected @ AWAR        :     7,520,653 kr
  vs target               :   -13,277,801 kr  (deficit)

  Scenario         CAGR       Projected     FI date   (incl. 6,000 kr/mo contributions)
  ------------------------------------------------------------------------
  Bear           +10%       5,046,878 kr       ~2056
  Conservative   +15%       8,109,862 kr       ~2046
  Base           +20%      12,935,362 kr       ~2042
  Current AWAR   +14%       7,520,653 kr       ~2047
  Bull           +30%      31,889,262 kr       ~2037

==============================================================
MACRO REGIME
==============================================================

  Feature                 Value   Regime  
  ------------------------------------------
  Nominal 10Y             5.01%   HIGH
  Real Yield             +2.68%   HIGH  ^
  Breakeven               2.33%   MID
  HY OAS                270 bps   TIGHT
  IG Credit               1.43%   TIGHT
  Curve 10Y-3M          +82 bps   MID
  Curve 10Y-2Y          +27 bps   LOW
  SE 10Y                  3.02%   MID
  USD                     118.2   STRONG

  HY 20d delta  : -3 bps  (flat)
  Confidence    : HIGH
  Data through  : 2026-09-17

==============================================================
PORTFOLIO SIGNALS
==============================================================

  Base: ry=HIGH  nominal_10y=HIGH  baa10y=TIGHT  usd=STRONG

  Position          Wt    21d   63d   63d med  252d med  W252     N  Note
  ----------------------------------------------------------------------
  Gold           18.6%    LOW   MID     +1.0%     +1.0%   63%    57  
  Silver          0.0%    MID   MID     +0.2%     +0.2%   54%    76  
  Eli Lilly      20.0%    LOW   MID     -0.1%     -0.1%   49%    43  
  Walmart         0.0%    LOW   LOW     +1.0%     +1.0%   62%    90  
  Cameco          0.0%    MID   LOW     -2.1%     -1.8%   43%   570  ~base fallback
  Vertiv          0.0%    LOW   LOW     +2.5%     +2.5%   61%    96  
  Broadcom       20.6%    LOW   LOW     +0.9%     +0.9%   61%   109  

==============================================================
TACTICAL RULES
==============================================================

  Silver GSR Tactical
    GSR now        : 66.59  (as of 2026-09-17)
    60d GSR peak   : 71.56
    Fall from peak : 6.9%  (yes)
    T1 threshold   : 83.36  |  T2: 86.45  |  Exit: 62.56
    Signal         : INACTIVE
    Action         : No action -- hold base

  AVGO Trend Diagnostic  [guard RETIRED as a rotation rule -- PR #88]
    AVGO now       : $347.30  (as of 2026-09-17)
    200d SMA       : $368.52  (-5.8% gap)
    5d ROC         : -3.7%  (gap-down buy level: -10%)
    Signal         : DEFENSIVE  (trigger: MA)  -- informational, no rotation
    LLY stress     : inactive  ($1152.44 vs 200d SMA $1064.45, 5d ROC +2.6%)
    Joint stress   : inactive  -- retired alongside the guard, shown for continuity only
    Action         : No action -- guard retired as a rotation rule (see PR #88); reading is diagnostic only

  AVGO Volatility-Targeted Weight  [RETIRED 2026-08-18 -- diagnostic only]
    Trailing 21d vol : 35.0% (annualized)
    Long-run avg vol : 35.4% (annualized)
    Scalar           : 1.01x  (clipped to [0.30x, 1.30x])
    Would-be weights : Gold 24.8%  AVGO 40.4%  LLY 34.8%
    NOT ACTED ON     : routing + rebalance use the static base (see MEMORY.md)

  AVGO Earnings Checkpoint
    Latest qtr EPS (actual vs est.): $3.32 vs $3.24  (+2.5% surprise)
    TTM EPS (non-GAAP actual)  : $9.76
    Forward EPS (+1yr est.)    : $19.38
    Fwd/Trail ratio (normalized): 1.99x  (mid-pack vs. real AI/semi peers; corrected 2026-07-06 from a GAAP/non-GAAP mismatched 3.22x)
    Revenue (latest qtr, actual): $29.59B  (TTM YoY: +48.7%)
    Next-qtr revenue consensus : $34.88B (implied YoY +93.6%)
    Next earnings  : 2026-12-09
    Reminder       : not_due
    Latest quarter : 2026-07-31
    Beat streak    : 4
    Guidance trend : flat  (+1yr estimate vs. 90 days ago)

  LLY Earnings Checkpoint
    Latest qtr EPS (actual vs est.): $8.38 vs $6.58  (+27.3% surprise)
    TTM EPS (non-GAAP actual)  : $31.49
    Forward EPS (+1yr est.)    : $47.32
    Fwd/Trail ratio (normalized): 1.50x  (baseline established 2026-07-06)
    Revenue (latest qtr, actual): $22.97B  (TTM YoY: +49.6%)
    Next-qtr revenue consensus : $22.22B (implied YoY +26.2%)
    Next earnings  : 2026-10-29
    Reminder       : not_due
    Latest quarter : 2026-06-30
    Beat streak    : 4
    Guidance trend : revising up  (+1yr estimate vs. 90 days ago)

  Sightline  [hold-or-cut only -- never resizes]
    AVGO (Broadcom)
      Observable : AI semiconductor revenue, as stated by management each quarter
      Latest     : FY26Q3: 16.7 (+221% YoY)
      State      : HOLD
      Eroding    : YoY < 0 in any quarter
      Action     : CUT: sell the full position
      Auto-read  : already_recorded FY26Q3 (8-K 2026-09-02)
    LLY (Eli Lilly)
      Observable : Mounjaro + Zepbound combined worldwide revenue
      Latest     : 2026Q2: 14.8 (+72% YoY)
      State      : HOLD
      Eroding    : YoY < 0 in any quarter, OR an FDA boxed warning / market withdrawal for tirzepatide (permanent, no constructive path)
      Action     : CUT: sell the full position
      Auto-read  : already_recorded 2026Q2 (8-K 2026-08-05)
    gold: EXEMPT -- Strategic anchor, held for a portfolio-level reason. No disclosed observable exists. Exit only on a mission change, which is outside Sightline's scope by construction.
    crypto_sleeve: EXEMPT -- Mechanical sleeve (BTC + staked ETH ETPs): hold-or-cut is delegated to its own MA50/100/200 ensemble rule and the 3-losing-cycles kill switch. No disclosed observable exists.

  Opportunistic Sleeve
    Status         : CLOSED (0/1 position)
    Best candidate : GM (General Motors Company)  $86.62  (ext +2.2%, 21d med +0.9%, ave +2.0%, win 57.4%, div THIN, drift -0.0%)
    Plan           : buy near $86.62, hold ~21d, stop = MA50-5% then trails 3% once +5% gain
    Open           : run_entry_screen.py --open GM <fill_price> <shares> <capital_sek>
    VIX review     : 15.44  (34% percentile, falling) -- for review, not a gate
    Basket-crash   : none eligible today

  Crypto Trend Sleeve
    Bitcoin (BTC-USD)  $76,437  (as of 2026-09-17)
      Target       : 100%  = 27 225 kr of 27 225 kr
      MA50         : LONG (MA $70,060, flat below $68,659)
      MA100        : LONG (MA $69,693, flat below $68,300)
      MA200        : LONG (MA $73,652, flat below $72,179)
      Last change  : 2026-08-21 -> 100%
    Ethereum (ETH-USD)  $2,447  (as of 2026-09-17)
      Target       : 100%  = 27 225 kr of 27 225 kr
      MA50         : LONG (MA $2,133, flat below $2,090)
      MA100        : LONG (MA $2,023, flat below $1,982)
      MA200        : LONG (MA $2,238, flat below $2,194)
      Last change  : 2026-08-21 -> 100%

==============================================================
NEXT CONTRIBUTION
==============================================================

  Next kr        -> Broadcom (AVGO)
    Current wt (of Reactor Core) : 34.8%
    Target wt (current regime)   : 40.0%
    Gap                          : +5.2%
    Gate                         : OPEN
    Note: Silver excluded -- funded by its own GSR trigger, not new contributions

  AVGO Rebalance Check  [existing capital, band: 10%]
    Gold status: HOLD  (31.5% actual vs 25.0% target, gap -6.5%)
    AVGO status: HOLD  (34.8% actual vs 40.0% target, gap +5.2%)
    LLY status: HOLD  (33.7% actual vs 35.0% target, gap +1.3%)

  Idle Reactor Core Cash
    Uninvested     : 0 kr  (0.0% of Reactor Core)
    Action         : none -- fully invested

==============================================================
  Regime check (2026-09-17): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)
Building regime labels ...
  Conditions    : {'ry_regime': 'HIGH', 'baa10y_regime': 'TIGHT'}
  Matched dates : 1415  (2004-05-07 - 2026-09-17)  MODERATE

Computing capped 252d distributions for 51 candidates ...
  SNDK      hist=2yr  (below min 10yr, skipped)
  APP       hist=5yr  (below min 10yr, skipped)
  PLTR      hist=6yr  (below min 10yr, skipped)
  HOOD      hist=5yr  (below min 10yr, skipped)
  LITE      N= 630  mu= +49.5%  sigma= 60.6%  hist=11yr  [SINGLE]
  GEV       hist=2yr  (below min 10yr, skipped)
  CVNA      hist=9yr  (below min 10yr, skipped)
  VRT       hist=8yr  (below min 10yr, skipped)
  HWM       hist=10yr  (below min 10yr, skipped)
  AVGO      N= 630  mu= +27.7%  sigma= 36.1%  hist=17yr  [SINGLE]
  VST       hist=10yr  (below min 10yr, skipped)
  IBKR      N= 743  mu=  +6.9%  sigma= 19.3%  hist=19yr  [THIN]
  TRGP      N= 630  mu=  +3.4%  sigma= 16.4%  hist=16yr  [SINGLE]
  PWR       N=1269  mu= +19.9%  sigma= 27.4%  hist=27yr  [ROBUST]
  ANET      N= 630  mu= +19.9%  sigma= 24.2%  hist=12yr  [SINGLE]
  NRG       N=1269  mu= +21.0%  sigma= 27.8%  hist=23yr  [ROBUST]
  DECK      N=1269  mu= +31.0%  sigma= 53.8%  hist=27yr  [ROBUST]
  STLD      N=1269  mu= +15.3%  sigma= 30.3%  hist=27yr  [ROBUST]
  CF        excluded (see EXCLUDE_TICKERS)
  BKNG      N=1269  mu= +32.5%  sigma= 47.4%  hist=27yr  [ROBUST]
  GM        N= 630  mu=  +7.4%  sigma= 12.9%  hist=16yr  [SINGLE]
  EXV1.DE   no data
  CIEN      N=1269  mu= +22.3%  sigma= 28.2%  hist=27yr  [ROBUST]
  CMI       N=1269  mu= +25.0%  sigma= 29.2%  hist=27yr  [ROBUST]
  FOXA      hist=8yr  (below min 10yr, skipped)
  CFG       N= 630  mu= +14.7%  sigma= 13.7%  hist=12yr  [SINGLE]
  PHAG.L    no data
  WDC       N=1269  mu= +22.5%  sigma= 39.0%  hist=27yr  [ROBUST]
  CEG       hist=5yr  (below min 10yr, skipped)
  GS        N=1269  mu= +12.7%  sigma= 23.4%  hist=27yr  [ROBUST]
  TPR       N=1269  mu= +18.6%  sigma= 31.1%  hist=26yr  [ROBUST]
  NVDA      N=1269  mu= +23.5%  sigma= 32.4%  hist=27yr  [ROBUST]
  DELL      N= 630  mu=  +4.5%  sigma= 18.4%  hist=10yr  [SINGLE]
  COHR      max_up=71%  (M&A / corporate event detected, skipped)
  RL        N=1269  mu= +14.8%  sigma= 26.3%  hist=27yr  [ROBUST]
  DASH      hist=6yr  (below min 10yr, skipped)
  ABB.ST    no data
  EME       N=1269  mu= +16.1%  sigma= 26.6%  hist=27yr  [ROBUST]
  FOX       hist=8yr  (below min 10yr, skipped)
  FTNT      N= 630  mu=  -8.8%  sigma= 10.3%  hist=17yr  [SINGLE]
  GRMN      N=1269  mu= +30.5%  sigma= 31.2%  hist=26yr  [ROBUST]
  FIX       N=1269  mu= +20.7%  sigma= 27.9%  hist=27yr  [ROBUST]
  TEL2-B.ST  no data
  APH       N=1269  mu= +16.8%  sigma= 24.3%  hist=27yr  [ROBUST]
  FSLR      N= 864  mu= +23.6%  sigma= 53.3%  hist=20yr  [MODERATE]
  SSAB-B.ST  no data
  PM        N= 630  mu= +10.8%  sigma= 13.7%  hist=18yr  [SINGLE]
  AAPL      N=1269  mu= +19.6%  sigma= 28.6%  hist=27yr  [ROBUST]
  SI_F      N=1269  mu= +11.8%  sigma= 22.5%  hist=26yr  [ROBUST]
  4GLD.DE   no data
  GC_F      N=1269  mu=  +9.8%  sigma= 11.5%  hist=26yr  [ROBUST]

Cross-sectional prior mu : +18.1%  (shrinkage target)
Shrinkage lambda         : 100  (asset needs N>>100 to be fully trusted)

Optimizing (50 restarts, 30 candidates) ...

========================================================================
PORTFOLIO OPTIMIZER  --  Regime: RY=HIGH + BAA10Y=TIGHT
========================================================================
  Universe       : top 50 screen candidates + GC_F
  Matched dates  : 1415  MODERATE
  Shrinkage      : lambda=100  prior=+18.1%

  Ticker     Weight   mu(raw)   mu(shr)    sigma      N   Hist       Div
  -----------------------------------------------------------------
  GRMN        31.3%    +30.5%    +29.6%    31.2%   1269    26yr    ROBUST
  LITE        29.5%    +49.5%    +37.3%    60.6%    630    11yr    SINGLE
  BKNG        21.9%    +32.5%    +31.4%    47.4%   1269    27yr    ROBUST
  DECK        12.4%    +31.0%    +30.1%    53.8%   1269    27yr    ROBUST
  GC_F         5.0%     +9.8%    +10.4%    11.5%   1269    26yr    ROBUST  [gold]

  Active positions   : 5  (weight >= 1%)
  Equal-weight g(w)  : +18.4%  (benchmark)
  Optimized g(w)     : +28.5%

  WARNING: only 5 active positions — below recommended minimum of 6.
  Consider reducing MAX_W or increasing N_CANDIDATES.

  NOTE: g(w) is an approximation. mu/sigma are regime-conditional,
  capped at regime end. Shrinkage applied for short-history assets.
========================================================================
AVGO peer valuation snapshot -- 2026-09-17

Ticker        Price   TTM EPS   Fwd EPS  Fwd/Trail  Impl.growth   Fwd P/E   PEG(1y)
-----------------------------------------------------------------------------------
MU          $977.50    $45.12   $156.53      3.47x        +247%     6.24x      0.03
AMD         $545.09     $5.76    $15.57      2.70x        +170%    35.01x      0.21
NVDA        $219.34     $7.01    $15.68      2.24x        +124%    13.99x      0.11
MRVL        $240.76     $3.30     $6.76      2.05x        +105%    35.61x      0.34
AVGO*       $347.30     $9.76    $19.38      1.99x         +99%    17.92x      0.18
ASML      $1,629.67    $27.56    $51.72      1.88x         +88%    31.51x      0.36
TSM         $430.26    $13.86    $21.93      1.58x         +58%    19.62x      0.34
ANET        $199.53     $3.46     $5.16      1.49x         +49%    38.67x      0.79
QCOM        $188.71    $11.36    $10.20      0.90x         -10%    18.49x       n/a

* = AVGO

AVGO rank -- growth ratio (highest first): 5 of 9
AVGO rank -- forward P/E (cheapest first): 3 of 9
AVGO rank -- PEG(1y) (cheapest first)    : 3 of 9

Note: PEG(1y) is built on a 1-year forward growth estimate, not the conventional 5-year estimate PEG ratios (including yfinance's own pegRatio field, deliberately not fetched here) normally use. MEMORY.md's 2026-07-06 entry recorded AVGO's PEG as 0.41 alongside a 19.4x forward P/E -- those two never reconciled on the same basis (19.4 / 139% implied growth = 0.14, not 0.41). PEG(1y) above is internally consistent but not comparable to that historical figure or to any 5-year PEG from elsewhere.
