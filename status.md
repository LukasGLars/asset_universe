==============================================================
REACTOR CORE -- PORTFOLIO SNAPSHOT
==============================================================================
Position                Shares      Price    Value SEK     Wt    Tgt   Drift
------------------------------------------------------------------------------
  Gold                     243     835 kr   202,983 kr  18.6%  20.0%   -1.4%
  Silver                     -     593 kr         0 kr   0.0%   0.0%   +0.0%
  Eli Lilly                 19  11,332 kr   215,306 kr  19.8%  20.0%   -0.2%
  Walmart                    -   1,049 kr         0 kr   0.0%   0.0%   +0.0%
  Cameco                     -     901 kr         0 kr   0.0%   0.0%   +0.0%
  Vertiv                     -   2,451 kr         0 kr   0.0%   0.0%   +0.0%
  Broadcom                  65   3,515 kr   228,467 kr  21.0%  20.0%   +1.0%
  Howmet Aerospace           -   2,257 kr         0 kr   0.0%   0.0%   +0.0%
  Spiltan Räntefond    1,307.31     153 kr   199,417 kr  18.3%   0.0%  +18.3%
  War Chest                  -     manual        19 kr   0.0%   0.0%   +0.0%
  Reactor Core Cash          -     manual   187,520 kr  17.2%  10.0%   +7.2%
  Virtune Bitcoin          218     127 kr    27,725 kr   2.5%   2.5%   +0.0%
  Virtune Staked ETH       470      59 kr    27,636 kr   2.5%   2.5%   +0.0%
  LF Global Index            -     610 kr         0 kr   0.0%  25.0%  -25.0%
------------------------------------------------------------------------------
  TPV                                        1,089,074 kr
    Reactor Core            646,757 kr  (59.4%)   target 60.0%  drift -0.6%
    Global Index                  0 kr  ( 0.0%)   target 25.0%  drift -25.0%
    Home Base               386,937 kr  (35.5%)   target 10.0%  drift +25.5%
    Crypto Sleeve            55,361 kr  ( 5.1%)   target  5.0%  drift +0.1%
    War Chest                    19 kr  ( 0.0%)   target  0.0%  drift +0.0%

==============================================================
FI@50 PACE TRACKER
==============================================================
  Start  (2025-07-21)  :       925,983 kr
  Now                     :     1,089,074 kr
  Threshold (2026 kr)     :    16,150,000 kr   (indexed 2.0%/yr)
  Trigger now             :    16,379,268 kr
  Trigger @ horizon       :    20,798,454 kr
  Years remaining         :  12.1

  AWAR (trailing)         :  +15.0%
  Required CAGR           :  +25.1%
  Status                  :  BEHIND  (-10.1% margin)

  Projected @ AWAR        :     8,154,868 kr
  vs target               :   -12,643,587 kr  (deficit)

  Scenario         CAGR       Projected     FI date   (incl. 6,000 kr/mo contributions)
  ------------------------------------------------------------------------
  Bear           +10%       5,074,284 kr       ~2056
  Conservative   +15%       8,156,000 kr       ~2046
  Base           +20%      13,011,316 kr       ~2042
  Current AWAR   +15%       8,154,868 kr       ~2046
  Bull           +30%      32,083,098 kr       ~2037

==============================================================
MACRO REGIME
==============================================================

  Feature                 Value   Regime  
  ------------------------------------------
  Nominal 10Y             4.94%   HIGH
  Real Yield             +2.61%   HIGH  ^
  Breakeven               2.33%   MID
  HY OAS                270 bps   TIGHT
  IG Credit               1.44%   TIGHT
  Curve 10Y-3M          +87 bps   MID
  Curve 10Y-2Y          +25 bps   LOW
  SE 10Y                  3.02%   MID
  USD                     118.2   STRONG

  HY 20d delta  : -5 bps  (flat)
  Confidence    : HIGH
  Data through  : 2026-09-18

==============================================================
PORTFOLIO SIGNALS
==============================================================

  Base: ry=HIGH  nominal_10y=HIGH  baa10y=TIGHT  usd=STRONG

  Position          Wt    21d   63d   63d med  252d med  W252     N  Note
  ----------------------------------------------------------------------
  Gold           18.6%    LOW   MID     +1.1%     +1.1%   64%    56  
  Silver          0.0%    MID   MID     +0.2%     +0.2%   54%    76  
  Eli Lilly      19.8%    LOW   MID     -0.1%     -0.1%   49%    43  
  Walmart         0.0%    LOW   LOW     +1.0%     +1.0%   62%    90  
  Cameco          0.0%    LOW   LOW     +1.8%     +1.8%   66%   106  
  Vertiv          0.0%    LOW   LOW     +2.5%     +2.5%   61%    96  
  Broadcom       21.0%    LOW   LOW     +0.9%     +0.9%   61%   109  

==============================================================
TACTICAL RULES
==============================================================

  Silver GSR Tactical
    GSR now        : 66.12  (as of 2026-09-18)
    60d GSR peak   : 71.56
    Fall from peak : 7.6%  (yes)
    T1 threshold   : 83.36  |  T2: 86.45  |  Exit: 62.56
    Signal         : INACTIVE
    Action         : No action -- hold base

  AVGO Trend Diagnostic  [guard RETIRED as a rotation rule -- PR #88]
    AVGO now       : $357.61  (as of 2026-09-18)
    200d SMA       : $368.39  (-2.9% gap)
    5d ROC         : -1.2%  (gap-down buy level: -10%)
    Signal         : DEFENSIVE  (trigger: MA)  -- informational, no rotation
    LLY stress     : inactive  ($1152.93 vs 200d SMA $1064.94, 5d ROC +3.3%)
    Joint stress   : inactive  -- retired alongside the guard, shown for continuity only
    Action         : No action -- guard retired as a rotation rule (see PR #88); reading is diagnostic only

  AVGO Volatility-Targeted Weight  [RETIRED 2026-08-18 -- diagnostic only]
    Trailing 21d vol : 33.4% (annualized)
    Long-run avg vol : 35.4% (annualized)
    Scalar           : 1.06x  (clipped to [0.30x, 1.30x])
    Would-be weights : Gold 24.0%  AVGO 42.4%  LLY 33.6%
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
    Best candidate : CF (CF Industries Holdings, Inc.)  $127.70  (ext +1.9%, 21d med +1.9%, ave +2.7%, win 58.3%, div ROBUST, drift +0.0%)
    Plan           : buy near $127.70, hold ~21d, stop = MA50-5% then trails 3% once +5% gain
    Open           : run_entry_screen.py --open CF <fill_price> <shares> <capital_sek>
    VIX review     : 14.81  (30% percentile, falling) -- for review, not a gate
    Basket-crash   : none eligible today

  Crypto Trend Sleeve
    Bitcoin (BTC-USD)  $81,084  (as of 2026-09-18)
      Target       : 100%  = 27 225 kr of 27 225 kr
      MA50         : LONG (MA $70,399, flat below $68,991)
      MA100        : LONG (MA $69,723, flat below $68,328)
      MA200        : LONG (MA $73,606, flat below $72,134)
      Last change  : 2026-08-21 -> 100%
    Ethereum (ETH-USD)  $2,618  (as of 2026-09-18)
      Target       : 100%  = 27 225 kr of 27 225 kr
      MA50         : LONG (MA $2,149, flat below $2,106)
      MA100        : LONG (MA $2,026, flat below $1,985)
      MA200        : LONG (MA $2,236, flat below $2,191)
      Last change  : 2026-08-21 -> 100%

==============================================================
NEXT CONTRIBUTION
==============================================================

  Next kr        -> Broadcom (AVGO)
    Current wt (of Reactor Core) : 35.3%
    Target wt (current regime)   : 40.0%
    Gap                          : +4.7%
    Gate                         : OPEN
    Note: Silver excluded -- funded by its own GSR trigger, not new contributions

  AVGO Rebalance Check  [existing capital, band: 10%]
    Gold status: HOLD  (31.4% actual vs 25.0% target, gap -6.4%)
    AVGO status: HOLD  (35.3% actual vs 40.0% target, gap +4.7%)
    LLY status: HOLD  (33.3% actual vs 35.0% target, gap +1.7%)

  Idle Reactor Core Cash
    Uninvested     : 0 kr  (0.0% of Reactor Core)
    Action         : none -- fully invested

==============================================================
  Regime check (2026-09-18): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)
Building regime labels ...
  Conditions    : {'ry_regime': 'HIGH', 'baa10y_regime': 'TIGHT'}
  Matched dates : 1416  (2004-05-07 - 2026-09-18)  MODERATE

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
  PHAG.L    no data
  CFG       N= 630  mu= +14.7%  sigma= 13.7%  hist=12yr  [SINGLE]
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
  Matched dates  : 1416  MODERATE
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
AVGO peer valuation snapshot -- 2026-09-18

Ticker        Price   TTM EPS   Fwd EPS  Fwd/Trail  Impl.growth   Fwd P/E   PEG(1y)
-----------------------------------------------------------------------------------
MU        $1,015.80    $45.12   $156.53      3.47x        +247%     6.49x      0.03
AMD         $559.82     $5.76    $15.57      2.70x        +170%    35.95x      0.21
NVDA        $222.27     $7.01    $15.68      2.24x        +124%    14.17x      0.11
MRVL        $244.25     $3.30     $6.76      2.05x        +105%    36.13x      0.34
AVGO*       $357.61     $9.76    $19.38      1.99x         +99%    18.45x      0.19
ASML      $1,679.92    $27.56    $51.72      1.88x         +88%    32.48x      0.37
TSM         $434.67    $13.86    $21.93      1.58x         +58%    19.83x      0.34
ANET        $199.39     $3.46     $5.16      1.49x         +49%    38.64x      0.79
QCOM        $177.72    $11.36    $10.20      0.90x         -10%    17.42x       n/a

* = AVGO

AVGO rank -- growth ratio (highest first): 5 of 9
AVGO rank -- forward P/E (cheapest first): 4 of 9
AVGO rank -- PEG(1y) (cheapest first)    : 3 of 9

Note: PEG(1y) is built on a 1-year forward growth estimate, not the conventional 5-year estimate PEG ratios (including yfinance's own pegRatio field, deliberately not fetched here) normally use. MEMORY.md's 2026-07-06 entry recorded AVGO's PEG as 0.41 alongside a 19.4x forward P/E -- those two never reconciled on the same basis (19.4 / 139% implied growth = 0.14, not 0.41). PEG(1y) above is internally consistent but not comparable to that historical figure or to any 5-year PEG from elsewhere.
