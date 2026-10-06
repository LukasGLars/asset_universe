==============================================================
REACTOR CORE -- PORTFOLIO SNAPSHOT
==============================================================================
Position                Shares      Price    Value SEK     Wt    Tgt   Drift
------------------------------------------------------------------------------
  Gold                     243     809 kr   196,483 kr  19.4%  20.0%   -0.6%
  Silver                     -     558 kr         0 kr   0.0%   0.0%   +0.0%
  Eli Lilly                 19  11,471 kr   217,946 kr  21.5%  20.0%   +1.5%
  Walmart                    -   1,054 kr         0 kr   0.0%   0.0%   +0.0%
  Cameco                     -     878 kr         0 kr   0.0%   0.0%   +0.0%
  Vertiv                     -   2,545 kr         0 kr   0.0%   0.0%   +0.0%
  Broadcom                  65   3,638 kr   236,449 kr  23.4%  20.0%   +3.4%
  Howmet Aerospace           -   2,304 kr         0 kr   0.0%   0.0%   +0.0%
  Spiltan Räntefond     738.53     153 kr   112,714 kr  11.1%   0.0%  +11.1%
  War Chest                  -     manual        19 kr   0.0%   0.0%   +0.0%
  Reactor Core Cash          -     manual   187,520 kr  18.5%  10.0%   +8.5%
  Virtune Bitcoin          218     142 kr    30,969 kr   3.1%   2.5%   +0.6%
  Virtune Staked ETH       470      64 kr    30,315 kr   3.0%   2.5%   +0.5%
  LF Global Index            -     624 kr         0 kr   0.0%  25.0%  -25.0%
------------------------------------------------------------------------------
  TPV                                        1,012,416 kr
    Reactor Core            838,398 kr  (82.8%)   target 60.0%  drift +22.8%
    Global Index                  0 kr  ( 0.0%)   target 25.0%  drift -25.0%
    Home Base               112,714 kr  (11.1%)   target 10.0%  drift +1.1%
    Crypto Sleeve            61,284 kr  ( 6.1%)   target  5.0%  drift +1.1%
    War Chest                    19 kr  ( 0.0%)   target  0.0%  drift +0.0%

==============================================================
FI@50 PACE TRACKER
==============================================================
  Start  (2025-07-21)  :       925,983 kr
  Now                     :     1,012,416 kr
  Threshold (2026 kr)     :    16,150,000 kr   (indexed 2.0%/yr)
  Trigger now             :    16,395,260 kr
  Trigger @ horizon       :    20,798,454 kr
  Years remaining         :  12.0

  AWAR (trailing)         :  +7.7%
  Required CAGR           :  +25.9%
  Status                  :  BEHIND  (-18.2% margin)

  Projected @ AWAR        :     3,850,869 kr
  vs target               :   -16,947,585 kr  (deficit)

  Scenario         CAGR       Projected     FI date   (incl. 6,000 kr/mo contributions)
  ------------------------------------------------------------------------
  Bear           +10%       4,806,069 kr       ~2057
  Conservative   +15%       7,685,579 kr       ~2047
  Base           +20%      12,206,270 kr       ~2042
  Current AWAR   +8%       3,850,869 kr       ~2066
  Bull           +30%      29,875,338 kr       ~2037

==============================================================
MACRO REGIME
==============================================================

  Feature                 Value   Regime  
  ------------------------------------------
  Nominal 10Y             5.28%   HIGH
  Real Yield             +2.92%   HIGH  ^
  Breakeven               2.36%   HIGH
  HY OAS                310 bps   MID
  IG Credit               1.47%   TIGHT
  Curve 10Y-3M         +109 bps   MID
  Curve 10Y-2Y          +47 bps   MID
  SE 10Y                   nan%   --
  USD                     121.4   STRONG

  HY 20d delta  : +42 bps  (widening)
  Confidence    : UNCERTAIN
  Data through  : 2026-10-05

==============================================================
PORTFOLIO SIGNALS
==============================================================

  Base: ry=HIGH  nominal_10y=HIGH  baa10y=TIGHT  usd=STRONG

  Position          Wt    21d   63d   63d med  252d med  W252     N  Note
  ----------------------------------------------------------------------
  Gold           19.4%    LOW   MID     +0.7%     +0.7%   58%    60  
  Silver          0.0%    LOW   MID     +0.6%     +0.6%   58%    55  
  Eli Lilly      21.5%    MID   LOW     +0.1%     +0.1%   51%    47  
  Walmart         0.0%    LOW   LOW     +0.8%     +0.8%   62%    98  
  Cameco          0.0%    LOW   LOW     +1.6%     +1.6%   62%   104  
  Vertiv          0.0%    LOW   LOW     +2.1%     +2.1%   56%    94  
  Broadcom       23.4%    MID   LOW     +0.4%     +0.4%   56%    54  

==============================================================
TACTICAL RULES
==============================================================

  Silver GSR Tactical
    GSR now        : 68.14  (as of 2026-10-05)
    60d GSR peak   : 71.56
    Fall from peak : 4.8%  (no (need >=5% fall for signal))
    T1 threshold   : 83.36  |  T2: 86.45  |  Exit: 62.56
    Signal         : INACTIVE
    Action         : No action -- hold base

  AVGO Trend Diagnostic  [guard RETIRED as a rotation rule -- PR #88]
    AVGO now       : $362.51  (as of 2026-10-05)
    200d SMA       : $367.01  (-1.2% gap)
    5d ROC         : +3.7%  (gap-down buy level: -10%)
    Signal         : DEFENSIVE  (trigger: MA)  -- informational, no rotation
    LLY stress     : inactive  ($1143.12 vs 200d SMA $1073.04, 5d ROC -3.5%)
    Joint stress   : inactive  -- retired alongside the guard, shown for continuity only
    Action         : No action -- guard retired as a rotation rule (see PR #88); reading is diagnostic only

  AVGO Volatility-Targeted Weight  [RETIRED 2026-08-18 -- diagnostic only]
    Trailing 21d vol : 33.0% (annualized)
    Long-run avg vol : 35.4% (annualized)
    Scalar           : 1.07x  (clipped to [0.30x, 1.30x])
    Would-be weights : Gold 23.8%  AVGO 42.9%  LLY 33.3%
    NOT ACTED ON     : routing + rebalance use the static base (see MEMORY.md)

  AVGO Earnings Checkpoint
    Latest qtr EPS (actual vs est.): $3.32 vs $3.24  (+2.5% surprise)
    TTM EPS (non-GAAP actual)  : $9.76
    Forward EPS (+1yr est.)    : $19.39
    Fwd/Trail ratio (normalized): 1.99x  (mid-pack vs. real AI/semi peers; corrected 2026-07-06 from a GAAP/non-GAAP mismatched 3.22x)
    Revenue (latest qtr, actual): $29.59B  (TTM YoY: +48.7%)
    Next-qtr revenue consensus : $34.89B (implied YoY +93.7%)
    Next earnings  : 2026-12-09
    Reminder       : not_due
    Latest quarter : 2026-07-31
    Beat streak    : 4
    Guidance trend : flat  (+1yr estimate vs. 90 days ago)

  LLY Earnings Checkpoint
    Latest qtr EPS (actual vs est.): $8.38 vs $6.58  (+27.3% surprise)
    TTM EPS (non-GAAP actual)  : $31.49
    Forward EPS (+1yr est.)    : $47.59
    Fwd/Trail ratio (normalized): 1.51x  (baseline established 2026-07-06)
    Revenue (latest qtr, actual): $22.97B  (TTM YoY: +49.6%)
    Next-qtr revenue consensus : $22.36B (implied YoY +27.1%)
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
    Best candidate : ANET (Arista Networks, Inc.)  $206.90  (ext +6.6%, 21d med +3.0%, ave +3.1%, win 65.6%, div THIN, drift +0.8%)
    Plan           : buy near $206.90, hold ~21d, stop = MA50-5% then trails 3% once +5% gain
    Open           : run_entry_screen.py --open ANET <fill_price> <shares> <capital_sek>
    VIX review     : 15.52  (35% percentile, flat) -- for review, not a gate
    Basket-crash   : none eligible today

  Crypto Trend Sleeve
    Bitcoin (BTC-USD)  $85,787  (as of 2026-10-05)
      Target       : 100%  = 27 225 kr of 27 225 kr
      MA50         : LONG (MA $74,825, flat below $73,329)
      MA100        : LONG (MA $70,229, flat below $68,825)
      MA200        : LONG (MA $73,468, flat below $71,999)
      Last change  : 2026-08-21 -> 100%
    Ethereum (ETH-USD)  $2,711  (as of 2026-10-05)
      Target       : 100%  = 27 225 kr of 27 225 kr
      MA50         : LONG (MA $2,330, flat below $2,284)
      MA100        : LONG (MA $2,072, flat below $2,030)
      MA200        : LONG (MA $2,224, flat below $2,179)
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
    Gold status: HOLD  (30.2% actual vs 25.0% target, gap -5.2%)
    AVGO status: HOLD  (36.3% actual vs 40.0% target, gap +3.7%)
    LLY status: HOLD  (33.5% actual vs 35.0% target, gap +1.5%)

  Idle Reactor Core Cash
    Uninvested     : 187,520 kr  (22.4% of Reactor Core)
    Action         : deploy -> Broadcom (AVGO)  (~51 shares at 3,638 kr)

==============================================================
  Regime check (2026-10-05): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)
Building regime labels ...
  Conditions    : {'ry_regime': 'HIGH', 'baa10y_regime': 'TIGHT'}
  Matched dates : 1412  (2004-05-07 - 2026-10-05)  MODERATE

Computing capped 252d distributions for 51 candidates ...
  SNDK      hist=2yr  (below min 10yr, skipped)
  APP       hist=5yr  (below min 10yr, skipped)
  PLTR      hist=6yr  (below min 10yr, skipped)
  HOOD      hist=5yr  (below min 10yr, skipped)
  LITE      N= 620  mu= +50.2%  sigma= 61.0%  hist=11yr  [SINGLE]
  GEV       hist=3yr  (below min 10yr, skipped)
  CVNA      hist=9yr  (below min 10yr, skipped)
  VRT       hist=8yr  (below min 10yr, skipped)
  HWM       hist=10yr  (below min 10yr, skipped)
  AVGO      N= 620  mu= +26.0%  sigma= 34.1%  hist=17yr  [SINGLE]
  VST       hist=10yr  (below min 10yr, skipped)
  IBKR      N= 733  mu=  +6.3%  sigma= 18.7%  hist=19yr  [THIN]
  TRGP      N= 620  mu=  +4.0%  sigma= 16.2%  hist=16yr  [SINGLE]
  PWR       N=1251  mu= +19.9%  sigma= 27.5%  hist=27yr  [ROBUST]
  NRG       N=1251  mu= +21.3%  sigma= 27.9%  hist=23yr  [ROBUST]
  ANET      N= 620  mu= +21.2%  sigma= 25.6%  hist=12yr  [SINGLE]
  STLD      N=1251  mu= +15.7%  sigma= 30.1%  hist=27yr  [ROBUST]
  DECK      N=1251  mu= +31.7%  sigma= 53.6%  hist=27yr  [ROBUST]
  CF        excluded (see EXCLUDE_TICKERS)
  BKNG      N=1251  mu= +32.4%  sigma= 47.5%  hist=27yr  [ROBUST]
  CIEN      N=1251  mu= +21.7%  sigma= 27.4%  hist=27yr  [ROBUST]
  GM        N= 620  mu=  +7.5%  sigma= 13.0%  hist=16yr  [SINGLE]
  EXV1.DE   no data
  CMI       N=1251  mu= +25.5%  sigma= 29.2%  hist=27yr  [ROBUST]
  DELL      N= 620  mu=  +5.1%  sigma= 18.8%  hist=10yr  [SINGLE]
  WDC       N=1251  mu= +22.0%  sigma= 38.5%  hist=27yr  [ROBUST]
  PHAG.L    no data
  CFG       N= 620  mu= +15.3%  sigma= 13.3%  hist=12yr  [SINGLE]
  FOXA      hist=8yr  (below min 10yr, skipped)
  CEG       hist=5yr  (below min 10yr, skipped)
  GS        N=1251  mu= +12.7%  sigma= 23.4%  hist=27yr  [ROBUST]
  TPR       N=1251  mu= +18.7%  sigma= 31.0%  hist=26yr  [ROBUST]
  COHR      max_up=71%  (M&A / corporate event detected, skipped)
  NVDA      N=1251  mu= +23.5%  sigma= 32.2%  hist=27yr  [ROBUST]
  RL        N=1251  mu= +15.3%  sigma= 26.5%  hist=27yr  [ROBUST]
  ABB.ST    no data
  FTNT      N= 620  mu=  -9.7%  sigma= 10.6%  hist=17yr  [SINGLE]
  DASH      hist=6yr  (below min 10yr, skipped)
  FOX       hist=8yr  (below min 10yr, skipped)
  GRMN      N=1251  mu= +30.6%  sigma= 31.2%  hist=26yr  [ROBUST]
  FIX       N=1251  mu= +20.4%  sigma= 27.3%  hist=27yr  [ROBUST]
  EME       N=1251  mu= +16.2%  sigma= 26.4%  hist=27yr  [ROBUST]
  TEL2-B.ST  no data
  APH       N=1251  mu= +16.8%  sigma= 24.3%  hist=27yr  [ROBUST]
  FSLR      N= 854  mu= +24.1%  sigma= 53.6%  hist=20yr  [MODERATE]
  SSAB-B.ST  no data
  PM        N= 620  mu= +10.6%  sigma= 13.7%  hist=19yr  [SINGLE]
  AAPL      N=1251  mu= +20.0%  sigma= 28.5%  hist=27yr  [ROBUST]
  SI_F      N=1251  mu= +11.5%  sigma= 22.4%  hist=26yr  [ROBUST]
  4GLD.DE   no data
  GC_F      N=1251  mu=  +9.7%  sigma= 11.2%  hist=26yr  [ROBUST]

Cross-sectional prior mu : +18.2%  (shrinkage target)
Shrinkage lambda         : 100  (asset needs N>>100 to be fully trusted)

Optimizing (50 restarts, 30 candidates) ...

========================================================================
PORTFOLIO OPTIMIZER  --  Regime: RY=HIGH + BAA10Y=TIGHT
========================================================================
  Universe       : top 50 screen candidates + GC_F
  Matched dates  : 1412  MODERATE
  Shrinkage      : lambda=100  prior=+18.2%

  Ticker     Weight   mu(raw)   mu(shr)    sigma      N   Hist       Div
  -----------------------------------------------------------------
  GRMN        30.7%    +30.6%    +29.7%    31.2%   1251    26yr    ROBUST
  LITE        29.5%    +50.2%    +37.6%    61.0%    620    11yr    SINGLE
  BKNG        20.8%    +32.4%    +31.4%    47.5%   1251    27yr    ROBUST
  DECK        13.9%    +31.7%    +30.7%    53.6%   1251    27yr    ROBUST
  GC_F         5.0%     +9.7%    +10.3%    11.2%   1251    26yr    ROBUST  [gold]

  Active positions   : 5  (weight >= 1%)
  Equal-weight g(w)  : +18.5%  (benchmark)
  Optimized g(w)     : +28.7%

  WARNING: only 5 active positions — below recommended minimum of 6.
  Consider reducing MAX_W or increasing N_CANDIDATES.

  NOTE: g(w) is an approximation. mu/sigma are regime-conditional,
  capped at regime end. Shrinkage applied for short-history assets.
========================================================================
AVGO peer valuation snapshot -- 2026-10-06

Ticker        Price   TTM EPS   Fwd EPS  Fwd/Trail  Impl.growth   Fwd P/E   PEG(1y)
-----------------------------------------------------------------------------------
AMD         $631.75     $5.76    $15.72      2.73x        +173%    40.18x      0.23
NVDA        $238.90     $7.01    $15.80      2.25x        +125%    15.12x      0.12
MRVL        $271.25     $3.30     $6.75      2.05x        +105%    40.19x      0.38
AVGO*       $362.51     $9.76    $19.39      1.99x         +99%    18.69x      0.19
ASML      $1,859.86    $27.56    $51.73      1.88x         +88%    35.95x      0.41
TSM         $485.80    $13.86    $22.03      1.59x         +59%    22.05x      0.37
ANET        $206.90     $3.46     $5.20      1.50x         +50%    39.77x      0.79
QCOM        $180.79    $11.36    $10.20      0.90x         -10%    17.73x       n/a
MU        $1,063.96       n/a   $206.68        n/a          n/a       n/a       n/a

* = AVGO

AVGO rank -- growth ratio (highest first): 4 of 9
AVGO rank -- forward P/E (cheapest first): 3 of 9
AVGO rank -- PEG(1y) (cheapest first)    : 2 of 9

Note: PEG(1y) is built on a 1-year forward growth estimate, not the conventional 5-year estimate PEG ratios (including yfinance's own pegRatio field, deliberately not fetched here) normally use. MEMORY.md's 2026-07-06 entry recorded AVGO's PEG as 0.41 alongside a 19.4x forward P/E -- those two never reconciled on the same basis (19.4 / 139% implied growth = 0.14, not 0.41). PEG(1y) above is internally consistent but not comparable to that historical figure or to any 5-year PEG from elsewhere.
