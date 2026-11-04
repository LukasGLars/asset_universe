==============================================================
REACTOR CORE -- PORTFOLIO SNAPSHOT
==============================================================================
Position                Shares      Price    Value SEK     Wt    Tgt   Drift
------------------------------------------------------------------------------
  Gold                     234     746 kr   174,486 kr  15.9%  20.0%   -4.1%
  Silver                     -     442 kr         0 kr   0.0%   0.0%   +0.0%
  Eli Lilly                 19  13,785 kr   261,920 kr  23.9%  20.0%   +3.9%
  Walmart                    -   1,221 kr         0 kr   0.0%   0.0%   +0.0%
  Cameco                     -     710 kr         0 kr   0.0%   0.0%   +0.0%
  Vertiv                     -   2,308 kr         0 kr   0.0%   0.0%   +0.0%
  Broadcom                  65   3,249 kr   211,159 kr  19.3%  20.0%   -0.7%
  Howmet Aerospace           -   2,182 kr         0 kr   0.0%   0.0%   +0.0%
  Spiltan Räntefond     738.53     153 kr   112,884 kr  10.3%   0.0%  +10.3%
  War Chest                  -     manual        19 kr   0.0%   0.0%   +0.0%
  Reactor Core Cash          -     manual    96,090 kr   8.8%  10.0%   -1.2%
  Virtune Bitcoin            -     125 kr         0 kr   0.0%   0.0%   +0.0%
  Virtune Staked ETH         -      53 kr         0 kr   0.0%   0.0%   +0.0%
  LF Global Index       397.84     598 kr   237,887 kr  21.7%  30.0%   -8.3%
------------------------------------------------------------------------------
  TPV                                        1,094,445 kr
    Reactor Core            743,655 kr  (67.9%)   target 60.0%  drift +7.9%
    Global Index            237,887 kr  (21.7%)   target 30.0%  drift -8.3%
    Home Base               112,884 kr  (10.3%)   target 10.0%  drift +0.3%
    Crypto Sleeve                 0 kr  ( 0.0%)   target  0.0%  drift +0.0%
    War Chest                    19 kr  ( 0.0%)   target  0.0%  drift +0.0%

==============================================================
FI@50 PACE TRACKER
==============================================================
  Start  (2025-07-21)  :       925,983 kr
  Now                     :     1,094,445 kr
  Threshold (2026 kr)     :    16,150,000 kr   (indexed 2.0%/yr)
  Trigger now             :    16,421,058 kr
  Trigger @ horizon       :    20,798,454 kr
  Years remaining         :  11.9

  AWAR (trailing)         :  +13.8%
  Required CAGR           :  +25.4%
  Status                  :  BEHIND  (-11.6% margin)

  Projected @ AWAR        :     7,204,327 kr
  vs target               :   -13,594,127 kr  (deficit)

  Scenario         CAGR       Projected     FI date   (incl. 6,000 kr/mo contributions)
  ------------------------------------------------------------------------
  Bear           +10%       5,019,933 kr       ~2056
  Conservative   +15%       8,029,860 kr       ~2046
  Base           +20%      12,747,688 kr       ~2042
  Current AWAR   +14%       7,204,327 kr       ~2048
  Bull           +30%      31,131,767 kr       ~2037

==============================================================
MACRO REGIME
==============================================================

  Feature                 Value   Regime  
  ------------------------------------------
  Nominal 10Y             4.91%   HIGH
  Real Yield             +2.62%   HIGH  ^
  Breakeven               2.30%   MID
  HY OAS                343 bps   WIDE
  IG Credit               1.53%   TIGHT
  Curve 10Y-3M          +74 bps   MID
  Curve 10Y-2Y          +34 bps   LOW
  SE 10Y                  3.19%   MID
  USD                     121.7   STRONG

  HY 20d delta  : +31 bps  (widening)
  Confidence    : HIGH
  Data through  : 2026-11-03

==============================================================
PORTFOLIO SIGNALS
==============================================================

  Base: ry=HIGH  nominal_10y=HIGH  baa10y=TIGHT  usd=STRONG

  Position          Wt    21d   63d   63d med  252d med  W252     N  Note
  ----------------------------------------------------------------------
  Gold           15.9%    LOW   LOW     +0.7%     +0.7%   68%   102  
  Silver          0.0%    LOW   LOW     +0.9%     +0.9%   65%    68  
  Eli Lilly      23.9%   HIGH  HIGH     -0.2%     -0.2%   47%   160  
  Walmart         0.0%   HIGH  HIGH     +0.8%     +0.8%   61%   178  
  Cameco          0.0%    LOW   LOW     +1.9%     +1.9%   67%   123  
  Vertiv          0.0%    LOW   LOW     +0.2%     +0.2%   50%   128  
  Broadcom       19.3%    LOW   LOW     +1.2%     +1.2%   63%   122  

==============================================================
TACTICAL RULES
==============================================================

  Silver GSR Tactical
    GSR now        : 79.30  (as of 2026-11-03)
    60d GSR peak   : 79.30
    Fall from peak : 0.0%  (no (need >=5% fall for signal))
    T1 threshold   : 83.36  |  T2: 86.45  |  Exit: 62.56
    Signal         : INACTIVE
    Action         : No action -- hold base

  AVGO Trend Diagnostic  [guard RETIRED as a rotation rule -- PR #88]
    AVGO now       : $332.13  (as of 2026-11-03)
    200d SMA       : $367.02  (-9.5% gap)
    5d ROC         : -3.0%  (gap-down buy level: -10%)
    Signal         : DEFENSIVE  (trigger: MA)  -- informational, no rotation
    LLY stress     : inactive  ($1409.38 vs 200d SMA $1094.15, 5d ROC +9.9%)
    Joint stress   : inactive  -- retired alongside the guard, shown for continuity only
    Action         : No action -- guard retired as a rotation rule (see PR #88); reading is diagnostic only

  AVGO Volatility-Targeted Weight  [RETIRED 2026-08-18 -- diagnostic only]
    Trailing 21d vol : 45.0% (annualized)
    Long-run avg vol : 35.4% (annualized)
    Scalar           : 0.79x  (clipped to [0.30x, 1.30x])
    Would-be weights : Gold 28.6%  AVGO 31.4%  LLY 40.0%
    NOT ACTED ON     : routing + rebalance use the static base (see MEMORY.md)

  AVGO Earnings Checkpoint
    Latest qtr EPS (actual vs est.): $3.32 vs $3.24  (+2.5% surprise)
    TTM EPS (non-GAAP actual)  : $9.76
    Forward EPS (+1yr est.)    : $19.47
    Fwd/Trail ratio (normalized): 1.99x  (mid-pack vs. real AI/semi peers; corrected 2026-07-06 from a GAAP/non-GAAP mismatched 3.22x)
    Revenue (latest qtr, actual): $29.59B  (TTM YoY: +48.7%)
    Next-qtr revenue consensus : $34.91B (implied YoY +93.8%)
    Next earnings  : 2026-12-09
    Reminder       : not_due
    Latest quarter : 2026-07-31
    Beat streak    : 4
    Guidance trend : flat  (+1yr estimate vs. 90 days ago)

  LLY Earnings Checkpoint
    Latest qtr EPS (actual vs est.): $7.48 vs $6.35  (+17.9% surprise)
    TTM EPS (non-GAAP actual)  : $31.95
    Forward EPS (+1yr est.)    : $50.15
    Fwd/Trail ratio (normalized): 1.57x  (baseline established 2026-07-06)
    Revenue (latest qtr, actual): $24.40B  (TTM YoY: +45.5%)
    Next-qtr revenue consensus : $24.76B (implied YoY +28.4%)
    Next earnings  : 2026-10-29
    Reminder       : not_due
    Latest quarter : 2026-09-30
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
      Latest     : 2026Q3: 16 (+58% YoY)
      State      : HOLD
      Eroding    : YoY < 0 in any quarter, OR an FDA boxed warning / market withdrawal for tirzepatide (permanent, no constructive path)
      Action     : CUT: sell the full position
      Auto-read  : recorded 2026Q3 (8-K 2026-10-29)
    gold: EXEMPT -- Strategic anchor, held for a portfolio-level reason. No disclosed observable exists. Exit only on a mission change, which is outside Sightline's scope by construction.
    crypto_sleeve: EXEMPT -- Mechanical sleeve (BTC + staked ETH ETPs): hold-or-cut is delegated to its own MA50/100/200 ensemble rule and the 3-losing-cycles kill switch. No disclosed observable exists.

  Opportunistic Sleeve
    Status         : CLOSED (0/1 position)
    Best candidate : none eligible today (either no ENTER survivors, or all failed the pre-entry tripwire or execution-drift gate)
    Basket-crash   : none eligible today

  Crypto Trend Sleeve
    Status         : inactive -- no crypto leg carries a target (no alerts)

==============================================================
NEXT CONTRIBUTION
==============================================================

  Next kr        -> LF Global Index
    Current wt (of Reactor Core) : 24.2%
    Target wt (config)           : 30.0%
    Gap                          : +5.8%
    Gate                         : OPEN
    Note: not funded by contributions -- 
    Denominator: 981,541 kr (5 positions carrying a target)

  Rebalance Check  [existing capital, band: 10pp absolute gap to target]
    Broadcom status: HOLD  (21.5% actual vs 20.0% target, gap -1.5%)
    Eli Lilly status: HOLD  (26.7% actual vs 20.0% target, gap -6.7%)
    Gold status: HOLD  (17.8% actual vs 20.0% target, gap +2.2%)
    LF Global Index status: HOLD  (24.2% actual vs 30.0% target, gap +5.8%)
    Reactor Core Cash status: HOLD  (9.8% actual vs 10.0% target, gap +0.2%)

  Reactor Core Cash
    Balance        : 96,090 kr  (9.8% vs 10% target)
    Shortfall      : 2,064 kr below target
    Action         : none -- hold. This is the dip sleeve; the AVGO/LLY 5d-ROC trigger spends it, not a contribution.

==============================================================
  Regime check (2026-11-03): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)
Building regime labels ...
  Conditions    : {'ry_regime': 'HIGH', 'baa10y_regime': 'TIGHT'}
  Matched dates : 1420  (2004-05-07 - 2026-11-03)  MODERATE

Computing capped 252d distributions for 51 candidates ...
  SNDK      hist=2yr  (below min 10yr, skipped)
  PLTR      hist=6yr  (below min 10yr, skipped)
  LITE      N= 620  mu= +50.2%  sigma= 61.0%  hist=11yr  [SINGLE]
  HOOD      hist=5yr  (below min 10yr, skipped)
  APP       hist=6yr  (below min 10yr, skipped)
  GEV       hist=3yr  (below min 10yr, skipped)
  CVNA      hist=9yr  (below min 10yr, skipped)
  HWM       hist=10yr  (below min 10yr, skipped)
  VRT       hist=8yr  (below min 10yr, skipped)
  AVGO      N= 620  mu= +26.0%  sigma= 34.1%  hist=17yr  [SINGLE]
  TRGP      N= 620  mu=  +4.0%  sigma= 16.2%  hist=16yr  [SINGLE]
  VST       N= 620  mu= +12.4%  sigma= 22.4%  hist=10yr  [SINGLE]
  IBKR      N= 729  mu=  +6.4%  sigma= 18.7%  hist=19yr  [THIN]
  STLD      N=1238  mu= +16.1%  sigma= 30.2%  hist=27yr  [MODERATE]
  PWR       N=1238  mu= +20.4%  sigma= 27.5%  hist=27yr  [MODERATE]
  DECK      N=1238  mu= +31.4%  sigma= 53.6%  hist=27yr  [MODERATE]
  NRG       N=1238  mu= +22.8%  sigma= 28.1%  hist=23yr  [MODERATE]
  ANET      N= 620  mu= +21.2%  sigma= 25.6%  hist=12yr  [SINGLE]
  DELL      N= 620  mu=  +5.1%  sigma= 18.8%  hist=10yr  [SINGLE]
  CIEN      N=1238  mu= +21.2%  sigma= 27.4%  hist=27yr  [MODERATE]
  CF        excluded (see EXCLUDE_TICKERS)
  BKNG      N=1238  mu= +34.1%  sigma= 48.6%  hist=27yr  [MODERATE]
  GM        N= 620  mu=  +7.5%  sigma= 13.0%  hist=16yr  [SINGLE]
  EXV1.DE   no data
  CMI       N=1238  mu= +26.6%  sigma= 30.0%  hist=27yr  [MODERATE]
  WDC       N=1238  mu= +21.7%  sigma= 38.8%  hist=27yr  [MODERATE]
  COHR      max_up=71%  (M&A / corporate event detected, skipped)
  GS        N=1238  mu= +12.2%  sigma= 24.0%  hist=27yr  [MODERATE]
  CFG       N= 620  mu= +15.3%  sigma= 13.3%  hist=12yr  [SINGLE]
  TPR       N=1238  mu= +19.0%  sigma= 31.0%  hist=26yr  [MODERATE]
  PHAG.L    no data
  NVDA      N=1238  mu= +24.2%  sigma= 32.4%  hist=27yr  [MODERATE]
  CEG       hist=5yr  (below min 10yr, skipped)
  FOXA      hist=8yr  (below min 10yr, skipped)
  FTNT      N= 620  mu=  -9.7%  sigma= 10.6%  hist=17yr  [SINGLE]
  RL        N=1238  mu= +15.7%  sigma= 26.4%  hist=27yr  [MODERATE]
  ABB.ST    no data
  FIX       N=1238  mu= +20.4%  sigma= 27.4%  hist=27yr  [MODERATE]
  GRMN      N=1238  mu= +31.5%  sigma= 31.9%  hist=26yr  [MODERATE]
  FOX       hist=8yr  (below min 10yr, skipped)
  EME       N=1238  mu= +17.2%  sigma= 25.9%  hist=27yr  [MODERATE]
  SSAB-B.ST  no data
  TEL2-B.ST  no data
  APH       N=1238  mu= +17.2%  sigma= 24.2%  hist=27yr  [MODERATE]
  DASH      hist=6yr  (below min 10yr, skipped)
  FCX       N=1238  mu= +16.6%  sigma= 22.9%  hist=27yr  [MODERATE]
  FSLR      N= 850  mu= +26.9%  sigma= 58.8%  hist=20yr  [MODERATE]
  PM        N= 620  mu= +10.6%  sigma= 13.7%  hist=19yr  [SINGLE]
  SI_F      N=1238  mu= +13.3%  sigma= 20.9%  hist=26yr  [MODERATE]
  MPWR      N=1230  mu= +20.2%  sigma= 32.3%  hist=22yr  [MODERATE]
  GC_F      N=1238  mu= +10.4%  sigma= 10.8%  hist=26yr  [MODERATE]

Cross-sectional prior mu : +18.4%  (shrinkage target)
Shrinkage lambda         : 100  (asset needs N>>100 to be fully trusted)

Optimizing (50 restarts, 32 candidates) ...

========================================================================
PORTFOLIO OPTIMIZER  --  Regime: RY=HIGH + BAA10Y=TIGHT
========================================================================
  Universe       : top 50 screen candidates + GC_F
  Matched dates  : 1420  MODERATE
  Shrinkage      : lambda=100  prior=+18.4%

  Ticker     Weight   mu(raw)   mu(shr)    sigma      N   Hist       Div
  -----------------------------------------------------------------
  GRMN        32.2%    +31.5%    +30.6%    31.9%   1238    26yr  MODERATE
  LITE        28.0%    +50.2%    +37.7%    61.0%    620    11yr    SINGLE
  BKNG        23.9%    +34.1%    +32.9%    48.6%   1238    27yr  MODERATE
  DECK        10.9%    +31.4%    +30.4%    53.6%   1238    27yr  MODERATE
  GC_F         5.0%    +10.4%    +11.0%    10.8%   1238    26yr  MODERATE  [gold]

  Active positions   : 5  (weight >= 1%)
  Equal-weight g(w)  : +18.7%  (benchmark)
  Optimized g(w)     : +29.3%

  WARNING: only 5 active positions — below recommended minimum of 6.
  Consider reducing MAX_W or increasing N_CANDIDATES.

  NOTE: g(w) is an approximation. mu/sigma are regime-conditional,
  capped at regime end. Shrinkage applied for short-history assets.
========================================================================
AVGO peer valuation snapshot -- 2026-11-04

Ticker        Price   TTM EPS   Fwd EPS  Fwd/Trail  Impl.growth   Fwd P/E   PEG(1y)
-----------------------------------------------------------------------------------
MU          $855.10    $75.51   $207.76      2.75x        +175%     4.12x      0.02
AMD         $483.90     $6.65    $16.27      2.45x        +145%    29.74x      0.21
NVDA        $206.69     $7.01    $15.91      2.27x        +127%    12.99x      0.10
MRVL        $171.97     $3.30     $7.34      2.23x        +123%    23.42x      0.19
AVGO*       $332.13     $9.76    $19.47      1.99x         +99%    17.06x      0.17
ASML      $1,552.14    $33.89    $56.43      1.67x         +67%    27.50x      0.41
TSM         $404.80    $15.54    $23.43      1.51x         +51%    17.27x      0.34
ANET        $169.91     $3.91     $5.40      1.38x         +38%    31.47x      0.83
QCOM        $164.43    $11.36    $10.16      0.89x         -11%    16.18x       n/a

* = AVGO

AVGO rank -- growth ratio (highest first): 5 of 9
AVGO rank -- forward P/E (cheapest first): 4 of 9
AVGO rank -- PEG(1y) (cheapest first)    : 3 of 9

Note: PEG(1y) is built on a 1-year forward growth estimate, not the conventional 5-year estimate PEG ratios (including yfinance's own pegRatio field, deliberately not fetched here) normally use. MEMORY.md's 2026-07-06 entry recorded AVGO's PEG as 0.41 alongside a 19.4x forward P/E -- those two never reconciled on the same basis (19.4 / 139% implied growth = 0.14, not 0.41). PEG(1y) above is internally consistent but not comparable to that historical figure or to any 5-year PEG from elsewhere.

AVGO and peers vs their OWN stored history (low percentile = cheap for that name)
Ticker     Fwd P/E   pctile   obs
AMD         29.74x       --    14
ANET        31.47x       --    14
ASML        27.50x       --    14
AVGO        17.06x       --    14
MRVL        23.42x       --    14
MU           4.12x       --    14
NVDA        12.99x       --    14
QCOM        16.18x       --    14
TSM         17.27x       --    14
  accruing -- 14/60 observations needed before a percentile is shown. Started 2026-10-18; cannot be backfilled.
