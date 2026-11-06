==============================================================
REACTOR CORE -- PORTFOLIO SNAPSHOT
==============================================================================
Position                Shares      Price    Value SEK     Wt    Tgt   Drift
------------------------------------------------------------------------------
  Gold                     234     777 kr   181,881 kr  17.0%  20.0%   -3.0%
  Silver                     -     464 kr         0 kr   0.0%   0.0%   +0.0%
  Eli Lilly                 19  13,280 kr   252,323 kr  23.6%  20.0%   +3.6%
  Walmart                    -   1,243 kr         0 kr   0.0%   0.0%   +0.0%
  Cameco                     -     665 kr         0 kr   0.0%   0.0%   +0.0%
  Vertiv                     -   1,720 kr         0 kr   0.0%   0.0%   +0.0%
  Broadcom                  65   2,837 kr   184,396 kr  17.2%  20.0%   -2.8%
  Howmet Aerospace           -   1,955 kr         0 kr   0.0%   0.0%   +0.0%
  Spiltan Räntefond     738.53     153 kr   112,921 kr  10.6%   0.0%  +10.6%
  War Chest                  -     manual        19 kr   0.0%   0.0%   +0.0%
  Reactor Core Cash          -     manual    96,090 kr   9.0%  10.0%   -1.0%
  Virtune Bitcoin            -     124 kr         0 kr   0.0%   0.0%   +0.0%
  Virtune Staked ETH         -      53 kr         0 kr   0.0%   0.0%   +0.0%
  LF Global Index       397.84     608 kr   241,702 kr  22.6%  30.0%   -7.4%
------------------------------------------------------------------------------
  TPV                                        1,069,332 kr
    Reactor Core            714,690 kr  (66.8%)   target 60.0%  drift +6.8%
    Global Index            241,702 kr  (22.6%)   target 30.0%  drift -7.4%
    Home Base               112,921 kr  (10.6%)   target 10.0%  drift +0.6%
    Crypto Sleeve                 0 kr  ( 0.0%)   target  0.0%  drift +0.0%
    War Chest                    19 kr  ( 0.0%)   target  0.0%  drift +0.0%

==============================================================
FI@50 PACE TRACKER
==============================================================
  Start  (2025-07-21)  :       925,983 kr
  Now                     :     1,069,332 kr
  Threshold (2026 kr)     :    16,150,000 kr   (indexed 2.0%/yr)
  Trigger now             :    16,422,839 kr
  Trigger @ horizon       :    20,798,454 kr
  Years remaining         :  11.9

  AWAR (trailing)         :  +11.8%
  Required CAGR           :  +25.6%
  Status                  :  BEHIND  (-13.9% margin)

  Projected @ AWAR        :     5,825,478 kr
  vs target               :   -14,972,976 kr  (deficit)

  Scenario         CAGR       Projected     FI date   (incl. 6,000 kr/mo contributions)
  ------------------------------------------------------------------------
  Bear           +10%       4,938,644 kr       ~2056
  Conservative   +15%       7,890,309 kr       ~2046
  Base           +20%      12,513,586 kr       ~2042
  Current AWAR   +12%       5,825,478 kr       ~2052
  Bull           +30%      30,512,556 kr       ~2037

==============================================================
MACRO REGIME
==============================================================

  Feature                 Value   Regime  
  ------------------------------------------
  Nominal 10Y             4.90%   HIGH
  Real Yield             +2.64%   HIGH  ^
  Breakeven               2.24%   MID
  HY OAS                332 bps   WIDE
  IG Credit               1.52%   TIGHT
  Curve 10Y-3M          +67 bps   LOW
  Curve 10Y-2Y          +38 bps   LOW
  SE 10Y                   nan%   --
  USD                     121.7   STRONG

  HY 20d delta  : +23 bps  (widening)
  Confidence    : HIGH
  Data through  : 2026-11-05

==============================================================
PORTFOLIO SIGNALS
==============================================================

  Base: ry=HIGH  nominal_10y=HIGH  baa10y=TIGHT  usd=STRONG

  Position          Wt    21d   63d   63d med  252d med  W252     N  Note
  ----------------------------------------------------------------------
  Gold           17.0%    MID   LOW     +0.4%     +0.4%   62%    56  
  Silver          0.0%    LOW   LOW     +0.9%     +0.9%   65%    68  
  Eli Lilly      23.6%   HIGH  HIGH     -0.2%     -0.2%   47%   160  
  Walmart         0.0%   HIGH  HIGH     +0.8%     +0.8%   61%   177  
  Cameco          0.0%    LOW   LOW     +1.9%     +1.9%   67%   123  
  Vertiv          0.0%    LOW   LOW     +0.2%     +0.2%   50%   128  
  Broadcom       17.2%    LOW   LOW     +1.2%     +1.2%   63%   122  

==============================================================
TACTICAL RULES
==============================================================

  Silver GSR Tactical
    GSR now        : 79.05  (as of 2026-11-05)
    60d GSR peak   : 79.30
    Fall from peak : 0.3%  (no (need >=5% fall for signal))
    T1 threshold   : 83.36  |  T2: 86.45  |  Exit: 62.56
    Signal         : INACTIVE
    Action         : No action -- hold base

  AVGO Trend Diagnostic  [guard RETIRED as a rotation rule -- PR #88]
    AVGO now       : $291.53  (as of 2026-11-05)
    200d SMA       : $366.81  (-20.5% gap)
    5d ROC         : -15.5%  (gap-down buy level: -10%)
    Signal         : DEFENSIVE  (trigger: CRASH)  -- informational, no rotation
    LLY stress     : inactive  ($1364.73 vs 200d SMA $1097.50, 5d ROC -0.7%)
    Joint stress   : inactive  -- retired alongside the guard, shown for continuity only
    Action         : No rotation. The 5d/-10% trigger has fired -- see the Crash Plan block below for the amount (MEMORY.md 'Crash plan').

  AVGO Volatility-Targeted Weight  [RETIRED 2026-08-18 -- diagnostic only]
    Trailing 21d vol : 54.4% (annualized)
    Long-run avg vol : 35.4% (annualized)
    Scalar           : 0.65x  (clipped to [0.30x, 1.30x])
    Would-be weights : Gold 30.8%  AVGO 26.0%  LLY 43.2%
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
      Eroding    : YoY < 0 in any quarter, OR next quarter GUIDED below the same quarter a year earlier (forward rule, 2026-11-04)
      Action     : CUT: sell the full position
      Auto-read  : already_recorded FY26Q3 (8-K 2026-09-02)
    LLY (Eli Lilly)
      Observable : Mounjaro + Zepbound combined worldwide revenue
      Latest     : 2026Q3: 16 (+58% YoY)
      State      : HOLD
      Eroding    : YoY < 0 in any quarter, OR a NEW FDA boxed warning (beyond the thyroid C-cell warning on the label since 2022) / market withdrawal for tirzepatide (permanent, no constructive path)
      Action     : CUT: sell the full position
      Auto-read  : recorded 2026Q3 (8-K 2026-10-29)
    gold: EXEMPT -- Strategic anchor, held for a portfolio-level reason. No disclosed observable exists. Exit only on a mission change, which is outside Sightline's scope by construction.
    crypto_sleeve: EXEMPT -- Mechanical sleeve (BTC + staked ETH ETPs): hold-or-cut is delegated to its own MA50/100/200 ensemble rule and the 3-losing-cycles kill switch. No disclosed observable exists.
    global_index: EXEMPT -- Broad market index fund: no single thesis to break. Held for diversification; governed by its target and the rebalance band only.

  Opportunistic Sleeve
    Status         : CLOSED (0/1 position)
    Best candidate : none eligible today (either no ENTER survivors, or all failed the pre-entry tripwire or execution-drift gate)
    Basket-crash   : LITE (Lumentum Holdings Inc.)  $509.70  (sector Technology, -44.6% 5d, 8 peers crashing, drift -0.0%)
    Plan           : buy near $509.70, flat 21d exit, NO stop until +8% gain then trails 8% (no floor before that -- riskier than the extension pathway)
    Open           : run_entry_screen.py --open LITE <fill_price> <shares> <capital_sek> --entry-type basket_crash

  Crypto Trend Sleeve
    Status         : inactive -- no crypto leg carries a target (no alerts)

==============================================================
NEXT CONTRIBUTION
==============================================================

  Next kr        -> LF Global Index
    Current wt (of Reactor Core) : 25.3%
    Target wt (config)           : 30.0%
    Gap                          : +4.7%
    Gate                         : OPEN
    Note: not funded by contributions -- 
    Denominator: 956,392 kr (5 positions carrying a target)

  Rebalance Check  [existing capital, band: 10pp absolute gap to target]
    Broadcom status: HOLD  (19.3% actual vs 20.0% target, gap +0.7%)
    Eli Lilly status: HOLD  (26.4% actual vs 20.0% target, gap -6.4%)
    Gold status: HOLD  (19.0% actual vs 20.0% target, gap +1.0%)
    LF Global Index status: HOLD  (25.3% actual vs 30.0% target, gap +4.7%)
    Reactor Core Cash status: HOLD  (10.0% actual vs 10.0% target, gap -0.0%)

  Reactor Core Cash
    Balance        : 96,090 kr  (10.0% vs 10% target)
    Above target   : 451 kr
    Action         : deploy -> LF Global Index

  Crash Plan  [cash 96,090 kr; 3 tranches of 31,880 kr bought in halves, max 2 per holding; trigger 5d <= -10%; caps 28% stock / 38% index]
    Broadcom status: FIRED  (5d -15.5%) -- BUY 15,940 kr (first half of tranche 1 of max 2 for this holding); second half in 21 sessions or below $262.38; then record: python crash_plan.py bought "Broadcom" --close 291.53 --half 15940
    Eli Lilly status: ARMED  (5d -0.7%, trigger -10%)
    LF Global Index status: ARMED  (5d -1.7%, trigger -10%)

==============================================================
  Regime check (2026-11-05): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)
Building regime labels ...
  Conditions    : {'ry_regime': 'HIGH', 'baa10y_regime': 'TIGHT'}
  Matched dates : 1422  (2004-05-07 - 2026-11-05)  MODERATE

Computing capped 252d distributions for 51 candidates ...
  SNDK      hist=2yr  (below min 10yr, skipped)
  LITE      N= 620  mu= +50.2%  sigma= 61.0%  hist=11yr  [SINGLE]
  PLTR      hist=6yr  (below min 10yr, skipped)
  HOOD      hist=5yr  (below min 10yr, skipped)
  APP       hist=6yr  (below min 10yr, skipped)
  GEV       hist=3yr  (below min 10yr, skipped)
  CVNA      hist=10yr  (below min 10yr, skipped)
  HWM       hist=10yr  (below min 10yr, skipped)
  VRT       hist=8yr  (below min 10yr, skipped)
  AVGO      N= 620  mu= +26.0%  sigma= 34.1%  hist=17yr  [SINGLE]
  TRGP      N= 620  mu=  +4.0%  sigma= 16.2%  hist=16yr  [SINGLE]
  VST       N= 620  mu= +12.4%  sigma= 22.4%  hist=10yr  [SINGLE]
  IBKR      N= 729  mu=  +6.4%  sigma= 18.7%  hist=19yr  [THIN]
  STLD      N=1238  mu= +16.1%  sigma= 30.2%  hist=27yr  [MODERATE]
  PWR       N=1238  mu= +20.4%  sigma= 27.5%  hist=27yr  [MODERATE]
  DELL      N= 620  mu=  +5.1%  sigma= 18.8%  hist=10yr  [SINGLE]
  DECK      N=1238  mu= +31.4%  sigma= 53.6%  hist=27yr  [MODERATE]
  NRG       N=1238  mu= +22.8%  sigma= 28.1%  hist=23yr  [MODERATE]
  ANET      N= 620  mu= +21.2%  sigma= 25.6%  hist=12yr  [SINGLE]
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
  FTNT      N= 620  mu=  -9.7%  sigma= 10.6%  hist=17yr  [SINGLE]
  NVDA      N=1238  mu= +24.2%  sigma= 32.4%  hist=27yr  [MODERATE]
  FOXA      hist=8yr  (below min 10yr, skipped)
  RL        N=1238  mu= +15.7%  sigma= 26.4%  hist=27yr  [MODERATE]
  CEG       hist=5yr  (below min 10yr, skipped)
  ABB.ST    no data
  FIX       N=1238  mu= +20.4%  sigma= 27.4%  hist=27yr  [MODERATE]
  GRMN      N=1238  mu= +31.5%  sigma= 31.9%  hist=26yr  [MODERATE]
  FOX       hist=8yr  (below min 10yr, skipped)
  SSAB-B.ST  no data
  EME       N=1238  mu= +17.2%  sigma= 25.9%  hist=27yr  [MODERATE]
  TEL2-B.ST  no data
  APH       N=1238  mu= +17.2%  sigma= 24.2%  hist=27yr  [MODERATE]
  DASH      hist=6yr  (below min 10yr, skipped)
  FCX       N=1238  mu= +16.6%  sigma= 22.9%  hist=27yr  [MODERATE]
  PM        N= 620  mu= +10.6%  sigma= 13.7%  hist=19yr  [SINGLE]
  FSLR      N= 850  mu= +26.9%  sigma= 58.8%  hist=20yr  [MODERATE]
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
  Matched dates  : 1422  MODERATE
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
AVGO peer valuation snapshot -- 2026-11-06

Ticker        Price   TTM EPS   Fwd EPS  Fwd/Trail  Impl.growth   Fwd P/E   PEG(1y)
-----------------------------------------------------------------------------------
MU          $656.39    $75.51   $207.76      2.75x        +175%     3.16x      0.02
AMD         $404.40     $6.65    $16.30      2.45x        +145%    24.81x      0.17
NVDA        $181.60     $7.01    $15.91      2.27x        +127%    11.41x      0.09
MRVL        $133.55     $3.30     $7.34      2.23x        +123%    18.19x      0.15
AVGO*       $291.53     $9.76    $19.47      1.99x         +99%    14.98x      0.15
ASML      $1,356.65    $33.89    $56.43      1.67x         +67%    24.04x      0.36
TSM         $353.10    $15.54    $23.39      1.50x         +50%    15.10x      0.30
ANET        $159.16     $3.91     $5.42      1.38x         +38%    29.39x      0.76
QCOM        $156.75    $10.53    $12.85      1.22x         +22%    12.20x      0.55

* = AVGO

AVGO rank -- growth ratio (highest first): 5 of 9
AVGO rank -- forward P/E (cheapest first): 4 of 9
AVGO rank -- PEG(1y) (cheapest first)    : 4 of 9

Note: PEG(1y) is built on a 1-year forward growth estimate, not the conventional 5-year estimate PEG ratios (including yfinance's own pegRatio field, deliberately not fetched here) normally use. MEMORY.md's 2026-07-06 entry recorded AVGO's PEG as 0.41 alongside a 19.4x forward P/E -- those two never reconciled on the same basis (19.4 / 139% implied growth = 0.14, not 0.41). PEG(1y) above is internally consistent but not comparable to that historical figure or to any 5-year PEG from elsewhere.

AVGO and peers vs their OWN stored history (low percentile = cheap for that name)
Ticker     Fwd P/E   pctile   obs
AMD         24.81x       --    15
ANET        29.39x       --    15
ASML        24.04x       --    15
AVGO        14.98x       --    15
MRVL        18.19x       --    15
MU           3.16x       --    15
NVDA        11.41x       --    15
QCOM        12.20x       --    15
TSM         15.10x       --    15
  accruing -- 15/60 observations needed before a percentile is shown. Started 2026-10-18; cannot be backfilled.
