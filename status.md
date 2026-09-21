==============================================================
REACTOR CORE -- PORTFOLIO SNAPSHOT
==============================================================================
Position                Shares      Price    Value SEK     Wt    Tgt   Drift
------------------------------------------------------------------------------
  Gold                     243     830 kr   201,754 kr  20.0%  20.0%   -0.0%
  Silver                     -     591 kr         0 kr   0.0%   0.0%   +0.0%
  Eli Lilly                 19  11,457 kr   217,674 kr  21.5%  20.0%   +1.5%
  Walmart                    -   1,057 kr         0 kr   0.0%   0.0%   +0.0%
  Cameco                     -     917 kr         0 kr   0.0%   0.0%   +0.0%
  Vertiv                     -   2,467 kr         0 kr   0.0%   0.0%   +0.0%
  Broadcom                  65   3,567 kr   231,836 kr  22.9%  20.0%   +2.9%
  Howmet Aerospace           -   2,236 kr         0 kr   0.0%   0.0%   +0.0%
  Spiltan Räntefond     738.53     153 kr   112,663 kr  11.1%   0.0%  +11.1%
  War Chest                  -     manual        19 kr   0.0%   0.0%   +0.0%
  Reactor Core Cash          -     manual   187,520 kr  18.6%  10.0%   +8.6%
  Virtune Bitcoin          218     137 kr    29,788 kr   2.9%   2.5%   +0.4%
  Virtune Staked ETH       470      63 kr    29,601 kr   2.9%   2.5%   +0.4%
  LF Global Index            -     610 kr         0 kr   0.0%  25.0%  -25.0%
------------------------------------------------------------------------------
  TPV                                        1,010,853 kr
    Reactor Core            838,783 kr  (83.0%)   target 60.0%  drift +23.0%
    Global Index                  0 kr  ( 0.0%)   target 25.0%  drift -25.0%
    Home Base               112,663 kr  (11.1%)   target 10.0%  drift +1.1%
    Crypto Sleeve            59,388 kr  ( 5.9%)   target  5.0%  drift +0.9%
    War Chest                    19 kr  ( 0.0%)   target  0.0%  drift +0.0%

==============================================================
FI@50 PACE TRACKER
==============================================================
  Start  (2025-07-21)  :       925,983 kr
  Now                     :     1,010,853 kr
  Threshold (2026 kr)     :    16,150,000 kr   (indexed 2.0%/yr)
  Trigger now             :    16,381,932 kr
  Trigger @ horizon       :    20,798,454 kr
  Years remaining         :  12.1

  AWAR (trailing)         :  +7.8%
  Required CAGR           :  +25.8%
  Status                  :  BEHIND  (-18.0% margin)

  Projected @ AWAR        :     3,912,076 kr
  vs target               :   -16,886,378 kr  (deficit)

  Scenario         CAGR       Projected     FI date   (incl. 6,000 kr/mo contributions)
  ------------------------------------------------------------------------
  Bear           +10%       4,822,963 kr       ~2057
  Conservative   +15%       7,724,378 kr       ~2047
  Base           +20%      12,286,930 kr       ~2042
  Current AWAR   +8%       3,912,076 kr       ~2066
  Bull           +30%      30,165,062 kr       ~2037

==============================================================
MACRO REGIME
==============================================================

  Feature                 Value   Regime  
  ------------------------------------------
  Nominal 10Y             5.01%   HIGH
  Real Yield             +2.68%   HIGH  ^
  Breakeven               2.34%   HIGH
  HY OAS                268 bps   TIGHT
  IG Credit               1.40%   TIGHT
  Curve 10Y-3M          +79 bps   MID
  Curve 10Y-2Y          +20 bps   LOW
  SE 10Y                  3.02%   MID
  USD                     119.5   STRONG

  HY 20d delta  : -2 bps  (flat)
  Confidence    : HIGH
  Data through  : 2026-09-21

==============================================================
PORTFOLIO SIGNALS
==============================================================

  Base: ry=HIGH  nominal_10y=HIGH  baa10y=TIGHT  usd=STRONG

  Position          Wt    21d   63d   63d med  252d med  W252     N  Note
  ----------------------------------------------------------------------
  Gold           20.0%    LOW  HIGH     +0.4%     +0.4%   62%    53  
  Silver          0.0%    LOW   MID     +0.9%     +0.9%   60%    57  
  Eli Lilly      21.5%    LOW   MID     -0.1%     -0.1%   49%    43  
  Walmart         0.0%   HIGH   LOW     +0.5%     +1.6%   59%   573  ~base fallback
  Cameco          0.0%    MID   LOW     -2.1%     -1.8%   43%   573  ~base fallback
  Vertiv          0.0%    LOW   LOW     +2.5%     +2.5%   61%    96  
  Broadcom       22.9%    MID   LOW     +0.2%     +0.2%   51%    55  

==============================================================
TACTICAL RULES
==============================================================

  Silver GSR Tactical
    GSR now        : 65.79  (as of 2026-09-21)
    60d GSR peak   : 71.56
    Fall from peak : 8.1%  (yes)
    T1 threshold   : 83.36  |  T2: 86.45  |  Exit: 62.56
    Signal         : INACTIVE
    Action         : No action -- hold base

  AVGO Trend Diagnostic  [guard RETIRED as a rotation rule -- PR #88]
    AVGO now       : $362.66  (as of 2026-09-21)
    200d SMA       : $368.30  (-1.5% gap)
    5d ROC         : +5.2%  (gap-down buy level: -10%)
    Signal         : DEFENSIVE  (trigger: MA)  -- informational, no rotation
    LLY stress     : inactive  ($1164.89 vs 200d SMA $1065.55, 5d ROC +2.3%)
    Joint stress   : inactive  -- retired alongside the guard, shown for continuity only
    Action         : No action -- guard retired as a rotation rule (see PR #88); reading is diagnostic only

  AVGO Volatility-Targeted Weight  [RETIRED 2026-08-18 -- diagnostic only]
    Trailing 21d vol : 33.7% (annualized)
    Long-run avg vol : 35.4% (annualized)
    Scalar           : 1.05x  (clipped to [0.30x, 1.30x])
    Would-be weights : Gold 24.2%  AVGO 41.9%  LLY 33.9%
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
    Forward EPS (+1yr est.)    : $47.34
    Fwd/Trail ratio (normalized): 1.50x  (baseline established 2026-07-06)
    Revenue (latest qtr, actual): $22.97B  (TTM YoY: +49.6%)
    Next-qtr revenue consensus : $22.23B (implied YoY +26.3%)
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
    Best candidate : ANET (Arista Networks, Inc.)  $205.42  (ext +9.3%, 21d med +2.8%, ave +3.1%, win 65.0%, div THIN, drift +0.0%)
    Plan           : buy near $205.42, hold ~21d, stop = MA50-5% then trails 3% once +5% gain
    Open           : run_entry_screen.py --open ANET <fill_price> <shares> <capital_sek>
    VIX review     : 14.87  (30% percentile, falling) -- for review, not a gate
    Basket-crash   : none eligible today

  Crypto Trend Sleeve
    Bitcoin (BTC-USD)  $86,385  (as of 2026-09-21)
      Target       : 100%  = 27 225 kr of 27 225 kr
      MA50         : LONG (MA $70,882, flat below $69,465)
      MA100        : LONG (MA $69,788, flat below $68,392)
      MA200        : LONG (MA $73,606, flat below $72,134)
      Last change  : 2026-08-21 -> 100%
    Ethereum (ETH-USD)  $2,770  (as of 2026-09-21)
      Target       : 100%  = 27 225 kr of 27 225 kr
      MA50         : LONG (MA $2,169, flat below $2,126)
      MA100        : LONG (MA $2,030, flat below $1,989)
      MA200        : LONG (MA $2,235, flat below $2,190)
      Last change  : 2026-08-21 -> 100%

==============================================================
NEXT CONTRIBUTION
==============================================================

  Next kr        -> Broadcom (AVGO)
    Current wt (of Reactor Core) : 35.6%
    Target wt (current regime)   : 40.0%
    Gap                          : +4.4%
    Gate                         : OPEN
    Note: Silver excluded -- funded by its own GSR trigger, not new contributions

  AVGO Rebalance Check  [existing capital, band: 10%]
    Gold status: HOLD  (31.0% actual vs 25.0% target, gap -6.0%)
    AVGO status: HOLD  (35.6% actual vs 40.0% target, gap +4.4%)
    LLY status: HOLD  (33.4% actual vs 35.0% target, gap +1.6%)

  Idle Reactor Core Cash
    Uninvested     : 187,520 kr  (22.4% of Reactor Core)
    Action         : deploy -> Broadcom (AVGO)  (~52 shares at 3,567 kr)

==============================================================
  Regime check (2026-09-21): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)
Building regime labels ...
  Conditions    : {'ry_regime': 'HIGH', 'baa10y_regime': 'TIGHT'}
  Matched dates : 1417  (2004-05-07 - 2026-09-21)  MODERATE

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
  EXV1.DE   no data
  GM        N= 630  mu=  +7.4%  sigma= 12.9%  hist=16yr  [SINGLE]
  CIEN      N=1269  mu= +22.3%  sigma= 28.2%  hist=27yr  [ROBUST]
  CMI       N=1269  mu= +25.0%  sigma= 29.2%  hist=27yr  [ROBUST]
  FOXA      hist=8yr  (below min 10yr, skipped)
  PHAG.L    no data
  CFG       N= 630  mu= +14.7%  sigma= 13.7%  hist=12yr  [SINGLE]
  WDC       N=1269  mu= +22.5%  sigma= 39.0%  hist=27yr  [ROBUST]
  CEG       hist=5yr  (below min 10yr, skipped)
  GS        N=1269  mu= +12.7%  sigma= 23.4%  hist=27yr  [ROBUST]
  TPR       N=1269  mu= +18.6%  sigma= 31.1%  hist=26yr  [ROBUST]
  DELL      N= 630  mu=  +4.5%  sigma= 18.4%  hist=10yr  [SINGLE]
  NVDA      N=1269  mu= +23.5%  sigma= 32.4%  hist=27yr  [ROBUST]
  COHR      max_up=71%  (M&A / corporate event detected, skipped)
  RL        N=1269  mu= +14.8%  sigma= 26.3%  hist=27yr  [ROBUST]
  DASH      hist=6yr  (below min 10yr, skipped)
  ABB.ST    no data
  FTNT      N= 630  mu=  -8.8%  sigma= 10.3%  hist=17yr  [SINGLE]
  EME       N=1269  mu= +16.1%  sigma= 26.6%  hist=27yr  [ROBUST]
  FOX       hist=8yr  (below min 10yr, skipped)
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
  Matched dates  : 1417  MODERATE
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
AVGO peer valuation snapshot -- 2026-09-21

Ticker        Price   TTM EPS   Fwd EPS  Fwd/Trail  Impl.growth   Fwd P/E   PEG(1y)
-----------------------------------------------------------------------------------
MU        $1,043.96    $45.12   $158.93      3.52x        +252%     6.57x      0.03
AMD         $615.52     $5.76    $15.57      2.70x        +170%    39.53x      0.23
NVDA        $227.38     $7.01    $15.68      2.24x        +124%    14.50x      0.12
MRVL        $257.38     $3.30     $6.76      2.05x        +105%    38.07x      0.36
AVGO*       $362.66     $9.76    $19.38      1.99x         +99%    18.71x      0.19
ASML      $1,711.32    $27.56    $51.72      1.88x         +88%    33.09x      0.38
TSM         $445.14    $13.86    $21.93      1.58x         +58%    20.30x      0.35
ANET        $205.42     $3.46     $5.19      1.50x         +50%    39.60x      0.79
QCOM        $194.23    $11.36    $10.20      0.90x         -10%    19.03x       n/a

* = AVGO

AVGO rank -- growth ratio (highest first): 5 of 9
AVGO rank -- forward P/E (cheapest first): 3 of 9
AVGO rank -- PEG(1y) (cheapest first)    : 3 of 9

Note: PEG(1y) is built on a 1-year forward growth estimate, not the conventional 5-year estimate PEG ratios (including yfinance's own pegRatio field, deliberately not fetched here) normally use. MEMORY.md's 2026-07-06 entry recorded AVGO's PEG as 0.41 alongside a 19.4x forward P/E -- those two never reconciled on the same basis (19.4 / 139% implied growth = 0.14, not 0.41). PEG(1y) above is internally consistent but not comparable to that historical figure or to any 5-year PEG from elsewhere.
