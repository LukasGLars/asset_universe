==============================================================
REACTOR CORE -- PORTFOLIO SNAPSHOT
==============================================================================
Position                Shares      Price    Value SEK     Wt    Tgt   Drift
------------------------------------------------------------------------------
  Gold                     234     803 kr   187,951 kr  17.0%  20.0%   -3.0%
  Silver                     -     541 kr         0 kr   0.0%   0.0%   +0.0%
  Eli Lilly                 19  11,708 kr   222,445 kr  20.1%  20.0%   +0.1%
  Walmart                    -   1,127 kr         0 kr   0.0%   0.0%   +0.0%
  Cameco                     -     865 kr         0 kr   0.0%   0.0%   +0.0%
  Vertiv                     -   2,382 kr         0 kr   0.0%   0.0%   +0.0%
  Broadcom                  65   3,586 kr   233,098 kr  21.1%  20.0%   +1.1%
  Howmet Aerospace           -   2,176 kr         0 kr   0.0%   0.0%   +0.0%
  Spiltan Räntefond     738.53     153 kr   112,773 kr  10.2%   0.0%  +10.2%
  War Chest                  -     manual        19 kr   0.0%   0.0%   +0.0%
  Reactor Core Cash          -     manual    47,104 kr   4.3%  10.0%   -5.7%
  Virtune Bitcoin          193     137 kr    26,458 kr   2.4%   2.5%   -0.1%
  Virtune Staked ETH       432      59 kr    25,592 kr   2.3%   2.5%   -0.2%
  LF Global Index       397.84     626 kr   249,038 kr  22.5%  25.0%   -2.5%
------------------------------------------------------------------------------
  TPV                                        1,104,479 kr
    Reactor Core            690,598 kr  (62.5%)   target 60.0%  drift +2.5%
    Global Index            249,038 kr  (22.5%)   target 25.0%  drift -2.5%
    Home Base               112,773 kr  (10.2%)   target 10.0%  drift +0.2%
    Crypto Sleeve            52,050 kr  ( 4.7%)   target  5.0%  drift -0.3%
    War Chest                    19 kr  ( 0.0%)   target  0.0%  drift +0.0%

==============================================================
FI@50 PACE TRACKER
==============================================================
  Start  (2025-07-21)  :       925,983 kr
  Now                     :     1,104,479 kr
  Threshold (2026 kr)     :    16,150,000 kr   (indexed 2.0%/yr)
  Trigger now             :    16,402,373 kr
  Trigger @ horizon       :    20,798,454 kr
  Years remaining         :  12.0

  AWAR (trailing)         :  +15.4%
  Required CAGR           :  +25.2%
  Status                  :  BEHIND  (-9.8% margin)

  Projected @ AWAR        :     8,449,445 kr
  vs target               :   -12,349,009 kr  (deficit)

  Scenario         CAGR       Projected     FI date   (incl. 6,000 kr/mo contributions)
  ------------------------------------------------------------------------
  Bear           +10%       5,083,150 kr       ~2056
  Conservative   +15%       8,152,445 kr       ~2046
  Base           +20%      12,975,533 kr       ~2042
  Current AWAR   +15%       8,449,445 kr       ~2046
  Bull           +30%      31,842,385 kr       ~2037

==============================================================
MACRO REGIME
==============================================================

  Feature                 Value   Regime  
  ------------------------------------------
  Nominal 10Y             5.24%   HIGH
  Real Yield             +2.91%   HIGH  ^
  Breakeven               2.33%   MID
  HY OAS                311 bps   MID
  IG Credit               1.45%   TIGHT
  Curve 10Y-3M          +95 bps   MID
  Curve 10Y-2Y          +42 bps   LOW
  SE 10Y                   nan%   --
  USD                     121.6   STRONG

  HY 20d delta  : +40 bps  (widening)
  Confidence    : UNCERTAIN
  Data through  : 2026-10-13

==============================================================
PORTFOLIO SIGNALS
==============================================================

  Base: ry=HIGH  nominal_10y=HIGH  baa10y=TIGHT  usd=STRONG

  Position          Wt    21d   63d   63d med  252d med  W252     N  Note
  ----------------------------------------------------------------------
  Gold           17.0%    MID   MID     +0.2%     +0.2%   59%    61  
  Silver          0.0%    LOW   MID     +0.7%     +0.7%   62%    61  
  Eli Lilly      20.1%    MID   MID     +0.2%     -0.5%   45%   576  ~base fallback
  Walmart         0.0%    MID   MID     +0.7%     +0.7%   68%    59  
  Cameco          0.0%    LOW   LOW     +1.8%     +1.8%   67%   115  
  Vertiv          0.0%    MID   LOW     -0.7%     -1.2%   47%   576  ~base fallback
  Broadcom       21.1%    MID   LOW     +0.2%     +0.2%   51%    57  

==============================================================
TACTICAL RULES
==============================================================

  Silver GSR Tactical
    GSR now        : 70.59  (as of 2026-10-13)
    60d GSR peak   : 71.26
    Fall from peak : 0.9%  (no (need >=5% fall for signal))
    T1 threshold   : 83.36  |  T2: 86.45  |  Exit: 62.56
    Signal         : INACTIVE
    Action         : No action -- hold base

  AVGO Trend Diagnostic  [guard RETIRED as a rotation rule -- PR #88]
    AVGO now       : $357.31  (as of 2026-10-13)
    200d SMA       : $367.80  (-2.9% gap)
    5d ROC         : -4.9%  (gap-down buy level: -10%)
    Signal         : DEFENSIVE  (trigger: MA)  -- informational, no rotation
    LLY stress     : inactive  ($1166.51 vs 200d SMA $1076.40, 5d ROC +0.8%)
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
    Forward EPS (+1yr est.)    : $47.57
    Fwd/Trail ratio (normalized): 1.51x  (baseline established 2026-07-06)
    Revenue (latest qtr, actual): $22.97B  (TTM YoY: +49.6%)
    Next-qtr revenue consensus : $22.45B (implied YoY +27.5%)
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
    Best candidate : none eligible today (either no ENTER survivors, or all failed the pre-entry tripwire or execution-drift gate)
    Basket-crash   : none eligible today

  Crypto Trend Sleeve
    Bitcoin (BTC-USD)  $83,064  (as of 2026-10-13)
      Target       : 100%  = 27 225 kr of 27 225 kr
      MA50         : LONG (MA $77,126, flat below $75,584)
      MA100        : LONG (MA $70,605, flat below $69,193)
      MA200        : LONG (MA $73,247, flat below $71,782)
      Last change  : 2026-08-21 -> 100%
    Ethereum (ETH-USD)  $2,496  (as of 2026-10-13)
      Target       : 100%  = 27 225 kr of 27 225 kr
      MA50         : LONG (MA $2,407, flat below $2,359)
      MA100        : LONG (MA $2,097, flat below $2,055)
      MA200        : LONG (MA $2,207, flat below $2,162)
      Last change  : 2026-08-21 -> 100%

==============================================================
NEXT CONTRIBUTION
==============================================================

  Next kr        -> Reactor Core Cash
    Current wt (of Reactor Core) : 4.7%
    Target wt (config)           : 10.0%
    Gap                          : +5.3%
    Gate                         : OPEN
    Note: not funded by contributions -- Virtune Bitcoin, Virtune Staked ETH
    Denominator: 991,687 kr (7 positions carrying a target)

  Rebalance Check  [existing capital, band: 10pp absolute gap to target]
    Broadcom status: HOLD  (23.5% actual vs 20.0% target, gap -3.5%)
    Eli Lilly status: HOLD  (22.4% actual vs 20.0% target, gap -2.4%)
    Gold status: HOLD  (19.0% actual vs 20.0% target, gap +1.0%)
    LF Global Index status: HOLD  (25.1% actual vs 25.0% target, gap -0.1%)
    Reactor Core Cash status: HOLD  (4.7% actual vs 10.0% target, gap +5.3%)
    Virtune Bitcoin status: HOLD  (2.7% actual vs 2.5% target, gap -0.2%)
    Virtune Staked ETH status: HOLD  (2.6% actual vs 2.5% target, gap -0.1%)

  Reactor Core Cash
    Balance        : 47,104 kr  (4.7% vs 10% target)
    Shortfall      : 52,065 kr below target
    Action         : none -- hold. This is the dip sleeve; the AVGO/LLY 5d-ROC trigger spends it, not a contribution.

==============================================================
  Regime check (2026-10-13): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)
Building regime labels ...
  Conditions    : {'ry_regime': 'HIGH', 'baa10y_regime': 'TIGHT'}
  Matched dates : 1405  (2004-05-07 - 2026-10-13)  MODERATE

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
  TRGP      N= 620  mu=  +4.0%  sigma= 16.2%  hist=16yr  [SINGLE]
  IBKR      N= 729  mu=  +6.4%  sigma= 18.7%  hist=19yr  [THIN]
  STLD      N=1238  mu= +16.1%  sigma= 30.2%  hist=27yr  [MODERATE]
  DECK      N=1238  mu= +31.4%  sigma= 53.6%  hist=27yr  [MODERATE]
  PWR       N=1238  mu= +20.4%  sigma= 27.5%  hist=27yr  [MODERATE]
  NRG       N=1238  mu= +22.8%  sigma= 28.1%  hist=23yr  [MODERATE]
  ANET      N= 620  mu= +21.2%  sigma= 25.6%  hist=12yr  [SINGLE]
  CF        excluded (see EXCLUDE_TICKERS)
  BKNG      N=1238  mu= +34.1%  sigma= 48.6%  hist=27yr  [MODERATE]
  CIEN      N=1238  mu= +21.2%  sigma= 27.4%  hist=27yr  [MODERATE]
  GM        N= 620  mu=  +7.5%  sigma= 13.0%  hist=16yr  [SINGLE]
  EXV1.DE   no data
  CMI       N=1238  mu= +26.6%  sigma= 30.0%  hist=27yr  [MODERATE]
  DELL      N= 620  mu=  +5.1%  sigma= 18.8%  hist=10yr  [SINGLE]
  WDC       N=1238  mu= +21.7%  sigma= 38.8%  hist=27yr  [MODERATE]
  GS        N=1238  mu= +12.2%  sigma= 24.0%  hist=27yr  [MODERATE]
  PHAG.L    no data
  FOXA      hist=8yr  (below min 10yr, skipped)
  CFG       N= 620  mu= +15.3%  sigma= 13.3%  hist=12yr  [SINGLE]
  COHR      max_up=71%  (M&A / corporate event detected, skipped)
  CEG       hist=5yr  (below min 10yr, skipped)
  TPR       N=1238  mu= +19.0%  sigma= 31.0%  hist=26yr  [MODERATE]
  NVDA      N=1238  mu= +24.2%  sigma= 32.4%  hist=27yr  [MODERATE]
  RL        N=1238  mu= +15.7%  sigma= 26.4%  hist=27yr  [MODERATE]
  ABB.ST    no data
  FTNT      N= 620  mu=  -9.7%  sigma= 10.6%  hist=17yr  [SINGLE]
  FIX       N=1238  mu= +20.4%  sigma= 27.4%  hist=27yr  [MODERATE]
  EME       N=1238  mu= +17.2%  sigma= 25.9%  hist=27yr  [MODERATE]
  GRMN      N=1238  mu= +31.5%  sigma= 31.9%  hist=26yr  [MODERATE]
  FOX       hist=8yr  (below min 10yr, skipped)
  DASH      hist=6yr  (below min 10yr, skipped)
  TEL2-B.ST  no data
  APH       N=1238  mu= +17.2%  sigma= 24.2%  hist=27yr  [MODERATE]
  FCX       N=1238  mu= +16.6%  sigma= 22.9%  hist=27yr  [MODERATE]
  SSAB-B.ST  no data
  MPWR      N=1230  mu= +20.2%  sigma= 32.3%  hist=22yr  [MODERATE]
  FSLR      N= 850  mu= +26.9%  sigma= 58.8%  hist=20yr  [MODERATE]
  WBD       N=1189  mu= +19.2%  sigma= 24.6%  hist=21yr  [MODERATE]
  SI_F      N=1238  mu= +13.3%  sigma= 20.9%  hist=26yr  [MODERATE]
  GC_F      N=1238  mu= +10.4%  sigma= 10.8%  hist=26yr  [MODERATE]

Cross-sectional prior mu : +18.9%  (shrinkage target)
Shrinkage lambda         : 100  (asset needs N>>100 to be fully trusted)

Optimizing (50 restarts, 31 candidates) ...

========================================================================
PORTFOLIO OPTIMIZER  --  Regime: RY=HIGH + BAA10Y=TIGHT
========================================================================
  Universe       : top 50 screen candidates + GC_F
  Matched dates  : 1405  MODERATE
  Shrinkage      : lambda=100  prior=+18.9%

  Ticker     Weight   mu(raw)   mu(shr)    sigma      N   Hist       Div
  -----------------------------------------------------------------
  GRMN        32.0%    +31.5%    +30.6%    31.9%   1238    26yr  MODERATE
  LITE        28.4%    +50.2%    +37.9%    61.0%    620    11yr    SINGLE
  BKNG        23.8%    +34.1%    +33.0%    48.6%   1238    27yr  MODERATE
  DECK        10.8%    +31.4%    +30.5%    53.6%   1238    27yr  MODERATE
  GC_F         5.0%    +10.4%    +11.0%    10.8%   1238    26yr  MODERATE  [gold]

  Active positions   : 5  (weight >= 1%)
  Equal-weight g(w)  : +19.1%  (benchmark)
  Optimized g(w)     : +29.4%

  WARNING: only 5 active positions — below recommended minimum of 6.
  Consider reducing MAX_W or increasing N_CANDIDATES.

  NOTE: g(w) is an approximation. mu/sigma are regime-conditional,
  capped at regime end. Shrinkage applied for short-history assets.
========================================================================
AVGO peer valuation snapshot -- 2026-10-14

Ticker        Price   TTM EPS   Fwd EPS  Fwd/Trail  Impl.growth   Fwd P/E   PEG(1y)
-----------------------------------------------------------------------------------
MU          $953.19    $75.51   $206.33      2.73x        +173%     4.62x      0.03
AMD         $605.53     $5.76    $15.72      2.73x        +173%    38.52x      0.22
NVDA        $228.52     $7.01    $15.91      2.27x        +127%    14.36x      0.11
MRVL        $268.73     $3.30     $7.28      2.21x        +121%    36.90x      0.31
AVGO*       $357.31     $9.76    $19.39      1.99x         +99%    18.42x      0.19
ASML      $1,717.76    $27.56    $52.67      1.91x         +91%    32.62x      0.36
TSM         $445.12    $13.86    $22.32      1.61x         +61%    19.95x      0.33
ANET        $204.52     $3.46     $5.22      1.51x         +51%    39.20x      0.77
QCOM        $176.86    $11.36    $10.20      0.90x         -10%    17.34x       n/a

* = AVGO

AVGO rank -- growth ratio (highest first): 5 of 9
AVGO rank -- forward P/E (cheapest first): 4 of 9
AVGO rank -- PEG(1y) (cheapest first)    : 3 of 9

Note: PEG(1y) is built on a 1-year forward growth estimate, not the conventional 5-year estimate PEG ratios (including yfinance's own pegRatio field, deliberately not fetched here) normally use. MEMORY.md's 2026-07-06 entry recorded AVGO's PEG as 0.41 alongside a 19.4x forward P/E -- those two never reconciled on the same basis (19.4 / 139% implied growth = 0.14, not 0.41). PEG(1y) above is internally consistent but not comparable to that historical figure or to any 5-year PEG from elsewhere.
