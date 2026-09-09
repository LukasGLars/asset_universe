==============================================================
REACTOR CORE -- PORTFOLIO SNAPSHOT
==============================================================================
Position                Shares      Price    Value SEK     Wt    Tgt   Drift
------------------------------------------------------------------------------
  Gold                     243     818 kr   198,724 kr  18.5%  20.0%   -1.5%
  Silver                     -     579 kr         0 kr   0.0%   0.0%   +0.0%
  Eli Lilly                 19  10,768 kr   204,590 kr  19.1%  20.0%   -0.9%
  Walmart                    -   1,016 kr         0 kr   0.0%   0.0%   +0.0%
  Cameco                     -     977 kr         0 kr   0.0%   0.0%   +0.0%
  Vertiv                     -   2,786 kr         0 kr   0.0%   0.0%   +0.0%
  Broadcom                  65   3,531 kr   229,521 kr  21.4%  20.0%   +1.4%
  Howmet Aerospace           -   2,218 kr         0 kr   0.0%   0.0%   +0.0%
  Spiltan Räntefond    1,307.31     153 kr   199,417 kr  18.6%   0.0%  +18.6%
  War Chest                  -     manual        19 kr   0.0%   0.0%   +0.0%
  Reactor Core Cash          -     manual   187,520 kr  17.5%  10.0%   +7.5%
  Virtune Bitcoin          218     125 kr    27,250 kr   2.5%   2.5%   +0.0%
  Virtune Staked ETH       470      56 kr    26,555 kr   2.5%   2.5%   -0.0%
  LF Global Index            -     600 kr         0 kr   0.0%  25.0%  -25.0%
------------------------------------------------------------------------------
  TPV                                        1,073,596 kr
    Reactor Core            632,835 kr  (58.9%)   target 60.0%  drift -1.1%
    Global Index                  0 kr  ( 0.0%)   target 25.0%  drift -25.0%
    Home Base               386,937 kr  (36.0%)   target 10.0%  drift +26.0%
    Crypto Sleeve            53,805 kr  ( 5.0%)   target  5.0%  drift +0.0%
    War Chest                    19 kr  ( 0.0%)   target  0.0%  drift +0.0%

==============================================================
FI@50 PACE TRACKER
==============================================================
  Start  (2025-07-21)  :       925,983 kr
  Now                     :     1,073,596 kr
  Threshold (2026 kr)     :    16,150,000 kr   (indexed 2.0%/yr)
  Trigger now             :    16,371,277 kr
  Trigger @ horizon       :    20,798,454 kr
  Years remaining         :  12.1

  AWAR (trailing)         :  +13.9%
  Required CAGR           :  +25.2%
  Status                  :  BEHIND  (-11.3% margin)

  Projected @ AWAR        :     7,304,478 kr
  vs target               :   -13,493,977 kr  (deficit)

  Scenario         CAGR       Projected     FI date   (incl. 6,000 kr/mo contributions)
  ------------------------------------------------------------------------
  Bear           +10%       5,039,017 kr       ~2056
  Conservative   +15%       8,102,100 kr       ~2046
  Base           +20%      12,931,485 kr       ~2042
  Current AWAR   +14%       7,304,478 kr       ~2048
  Bull           +30%      31,924,060 kr       ~2037

==============================================================
MACRO REGIME
==============================================================

  Feature                 Value   Regime  
  ------------------------------------------
  Nominal 10Y             4.78%   HIGH
  Real Yield             +2.43%   HIGH  ^
  Breakeven               2.37%   HIGH
  HY OAS                268 bps   TIGHT
  IG Credit               1.57%   TIGHT
  Curve 10Y-3M          +86 bps   MID
  Curve 10Y-2Y          +41 bps   LOW
  SE 10Y                   nan%   --
  USD                     118.1   STRONG

  HY 20d delta  : -2 bps  (flat)
  Confidence    : HIGH
  Data through  : 2026-09-08

==============================================================
PORTFOLIO SIGNALS
==============================================================

  Base: ry=HIGH  nominal_10y=HIGH  baa10y=TIGHT  usd=STRONG

  Position          Wt    21d   63d   63d med  252d med  W252     N  Note
  ----------------------------------------------------------------------
  Gold           18.5%    MID   MID     +0.2%     +0.2%   60%    62  
  Silver          0.0%   HIGH   MID     -1.1%     -1.1%   40%    58  
  Eli Lilly      19.1%    LOW   LOW     +1.4%     +1.4%   73%   103  
  Walmart         0.0%    LOW   LOW     +1.0%     +1.0%   62%    91  
  Cameco          0.0%    MID   MID     -0.3%     -0.3%   47%    49  
  Vertiv          0.0%    MID   LOW     -0.3%     -2.4%   44%   563  ~base fallback
  Broadcom       21.4%    LOW   LOW     +0.9%     +0.9%   61%   109  

==============================================================
TACTICAL RULES
==============================================================

  Silver GSR Tactical
    GSR now        : 66.33  (as of 2026-09-08)
    60d GSR peak   : 71.56
    Fall from peak : 7.3%  (yes)
    T1 threshold   : 83.36  |  T2: 86.45  |  Exit: 62.56
    Signal         : INACTIVE
    Action         : No action -- hold base

  AVGO Trend Diagnostic  [guard RETIRED as a rotation rule -- PR #88]
    AVGO now       : $368.56  (as of 2026-09-08)
    200d SMA       : $369.18  (-0.2% gap)
    5d ROC         : -0.5%  (gap-down buy level: -10%)
    Signal         : DEFENSIVE  (trigger: MA)  -- informational, no rotation
    LLY stress     : inactive  ($1123.91 vs 200d SMA $1062.25, 5d ROC -2.8%)
    Joint stress   : inactive  -- retired alongside the guard, shown for continuity only
    Action         : No action -- guard retired as a rotation rule (see PR #88); reading is diagnostic only

  AVGO Volatility-Targeted Weight  [RETIRED 2026-08-18 -- diagnostic only]
    Trailing 21d vol : 36.8% (annualized)
    Long-run avg vol : 35.4% (annualized)
    Scalar           : 0.96x  (clipped to [0.30x, 1.30x])
    Would-be weights : Gold 25.7%  AVGO 38.4%  LLY 35.9%
    NOT ACTED ON     : routing + rebalance use the static base (see MEMORY.md)

  AVGO Earnings Checkpoint
    Latest qtr EPS (actual vs est.): $3.32 vs $3.24  (+2.5% surprise)
    TTM EPS (non-GAAP actual)  : $7.06
    Forward EPS (+1yr est.)    : $19.39
    Fwd/Trail ratio (normalized): 2.75x  (mid-pack vs. real AI/semi peers; corrected 2026-07-06 from a GAAP/non-GAAP mismatched 3.22x)
    Revenue (latest qtr, actual): $22.19B  (TTM YoY: +32.3%)
    Next-qtr revenue consensus : $34.88B (implied YoY +93.6%)
    Next earnings  : 2026-09-02
    Reminder       : not_due
    Latest quarter : 2026-07-31
    Beat streak    : 3
    Guidance trend : flat  (+1yr estimate vs. 90 days ago)

  LLY Earnings Checkpoint
    Latest qtr EPS (actual vs est.): $8.38 vs $6.58  (+27.3% surprise)
    TTM EPS (non-GAAP actual)  : $31.49
    Forward EPS (+1yr est.)    : $47.26
    Fwd/Trail ratio (normalized): 1.50x  (baseline established 2026-07-06)
    Revenue (latest qtr, actual): $22.97B  (TTM YoY: +49.6%)
    Next-qtr revenue consensus : $22.22B (implied YoY +26.2%)
    Next earnings  : 2026-10-29
    Reminder       : not_due
    Latest quarter : 2026-06-30
    Beat streak    : 4
    Guidance trend : revising up  (+1yr estimate vs. 90 days ago)

  Opportunistic Sleeve
    Status         : CLOSED (0/1 position)
    Best candidate : TRGP (Targa Resources Corp.)  $294.29  (ext +5.8%, 21d med +2.1%, ave +2.6%, win 66.4%, div THIN, drift +0.6%)
    Plan           : buy near $294.29, hold ~21d, stop = MA50-5% then trails 3% once +5% gain
    Open           : run_entry_screen.py --open TRGP <fill_price> <shares> <capital_sek>
    VIX review     : 15.72  (36% percentile, flat) -- for review, not a gate
    Basket-crash   : none eligible today

  Crypto Trend Sleeve
    Bitcoin (BTC-USD)  $78,474  (as of 2026-09-08)
      Target       : 100%  = 27 225 kr of 27 225 kr
      MA50         : LONG (MA $68,024, flat below $66,663)
      MA100        : LONG (MA $69,705, flat below $68,311)
      MA200        : LONG (MA $74,174, flat below $72,690)
      Last change  : 2026-08-21 -> 100%
    Ethereum (ETH-USD)  $2,484  (as of 2026-09-08)
      Target       : 100%  = 27 225 kr of 27 225 kr
      MA50         : LONG (MA $2,031, flat below $1,990)
      MA100        : LONG (MA $2,012, flat below $1,972)
      MA200        : LONG (MA $2,264, flat below $2,219)
      Last change  : 2026-08-21 -> 100%

==============================================================
NEXT CONTRIBUTION
==============================================================

  Next kr        -> Broadcom (AVGO)
    Current wt (of Reactor Core) : 36.3%
    Target wt (current regime)   : 40.0%
    Gap                          : +3.7%
    Gate                         : OPEN
    Note: Silver excluded -- funded by its own GSR trigger, not new contributions

  AVGO Rebalance Check  [existing capital, band: 10%]
    Gold status: HOLD  (31.4% actual vs 25.0% target, gap -6.4%)
    AVGO status: HOLD  (36.3% actual vs 40.0% target, gap +3.7%)
    LLY status: HOLD  (32.3% actual vs 35.0% target, gap +2.7%)

  Idle Reactor Core Cash
    Uninvested     : 0 kr  (0.0% of Reactor Core)
    Action         : none -- fully invested

==============================================================
  Regime check (2026-09-08): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)
Building regime labels ...
  Conditions    : {'ry_regime': 'HIGH', 'baa10y_regime': 'TIGHT'}
  Matched dates : 1407  (2004-05-07 - 2026-09-08)  MODERATE

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
  FOXA      hist=7yr  (below min 10yr, skipped)
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
  FOX       hist=7yr  (below min 10yr, skipped)
  FTNT      N= 630  mu=  -8.8%  sigma= 10.3%  hist=17yr  [SINGLE]
  GRMN      N=1269  mu= +30.5%  sigma= 31.2%  hist=26yr  [ROBUST]
  FIX       N=1269  mu= +20.7%  sigma= 27.9%  hist=27yr  [ROBUST]
  TEL2-B.ST  no data
  APH       N=1269  mu= +16.8%  sigma= 24.3%  hist=27yr  [ROBUST]
  FSLR      N= 864  mu= +23.6%  sigma= 53.3%  hist=20yr  [MODERATE]
  PM        N= 630  mu= +10.8%  sigma= 13.7%  hist=18yr  [SINGLE]
  AAPL      N=1269  mu= +19.6%  sigma= 28.6%  hist=27yr  [ROBUST]
  SI_F      N=1269  mu= +11.8%  sigma= 22.5%  hist=26yr  [ROBUST]
  4GLD.DE   no data
  SSAB-B.ST  no data
  GC_F      N=1269  mu=  +9.8%  sigma= 11.5%  hist=26yr  [ROBUST]

Cross-sectional prior mu : +18.1%  (shrinkage target)
Shrinkage lambda         : 100  (asset needs N>>100 to be fully trusted)

Optimizing (50 restarts, 30 candidates) ...

========================================================================
PORTFOLIO OPTIMIZER  --  Regime: RY=HIGH + BAA10Y=TIGHT
========================================================================
  Universe       : top 50 screen candidates + GC_F
  Matched dates  : 1407  MODERATE
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
AVGO peer valuation snapshot -- 2026-09-09

Ticker        Price   TTM EPS   Fwd EPS  Fwd/Trail  Impl.growth   Fwd P/E   PEG(1y)
-----------------------------------------------------------------------------------
MU        $1,000.26    $45.12   $155.03      3.44x        +244%     6.45x      0.03
AMD         $505.74     $5.76    $15.61      2.71x        +171%    32.39x      0.19
NVDA        $225.73     $7.01    $15.52      2.21x        +121%    14.55x      0.12
MRVL        $225.41     $3.30     $6.72      2.04x        +104%    33.54x      0.32
ASML      $1,764.85    $27.56    $51.72      1.88x         +88%    34.12x      0.39
TSM         $439.00    $13.86    $21.93      1.58x         +58%    20.02x      0.34
ANET        $194.96     $3.46     $5.16      1.49x         +49%    37.78x      0.77
QCOM        $174.09    $11.36    $10.22      0.90x         -10%    17.04x       n/a
AVGO*       $368.56       n/a    $19.39        n/a          n/a       n/a       n/a

* = AVGO

AVGO rank -- growth ratio (highest first): n/a of 9
AVGO rank -- forward P/E (cheapest first): n/a of 9
AVGO rank -- PEG(1y) (cheapest first)    : n/a of 9

Note: PEG(1y) is built on a 1-year forward growth estimate, not the conventional 5-year estimate PEG ratios (including yfinance's own pegRatio field, deliberately not fetched here) normally use. MEMORY.md's 2026-07-06 entry recorded AVGO's PEG as 0.41 alongside a 19.4x forward P/E -- those two never reconciled on the same basis (19.4 / 139% implied growth = 0.14, not 0.41). PEG(1y) above is internally consistent but not comparable to that historical figure or to any 5-year PEG from elsewhere.
