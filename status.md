==============================================================
REACTOR CORE -- PORTFOLIO SNAPSHOT
==============================================================================
Position                Shares      Price    Value SEK     Wt    Tgt   Drift
------------------------------------------------------------------------------
  Gold                     234     709 kr   165,897 kr  15.1%  20.0%   -4.9%
  Silver                     -     361 kr         0 kr   0.0%   0.0%   +0.0%
  Eli Lilly                 19  14,262 kr   270,982 kr  24.7%  25.0%   -0.3%
  Walmart                    -   1,352 kr         0 kr   0.0%   0.0%   +0.0%
  Cameco                     -     631 kr         0 kr   0.0%   0.0%   +0.0%
  Vertiv                     -   1,776 kr         0 kr   0.0%   0.0%   +0.0%
  Broadcom                  66   3,082 kr   203,417 kr  18.5%  15.0%   +3.5%
  Visa                       6   4,348 kr    26,085 kr   2.4%   5.0%   -2.6%
  Howmet Aerospace           -   2,162 kr         0 kr   0.0%   0.0%   +0.0%
  Spiltan Räntefond     738.53     153 kr   113,084 kr  10.3%   0.0%  +10.3%
  War Chest                  -     manual        19 kr   0.0%   0.0%   +0.0%
  Reactor Core Cash          -     manual    66,810 kr   6.1%  10.0%   -3.9%
  Virtune Bitcoin            -     102 kr         0 kr   0.0%   0.0%   +0.0%
  Virtune Staked ETH         -      41 kr         0 kr   0.0%   0.0%   +0.0%
  LF Global Index       419.65     598 kr   251,017 kr  22.9%  25.0%   -2.1%
------------------------------------------------------------------------------
  TPV                                        1,097,312 kr
    Reactor Core            733,192 kr  (66.8%)   target 65.0%  drift +1.8%
    Global Index            251,017 kr  (22.9%)   target 25.0%  drift -2.1%
    Home Base               113,084 kr  (10.3%)   target 10.0%  drift +0.3%
    Crypto Sleeve                 0 kr  ( 0.0%)   target  0.0%  drift +0.0%
    War Chest                    19 kr  ( 0.0%)   target  0.0%  drift +0.0%

==============================================================
FI@50 PACE TRACKER
==============================================================
  Start  (2025-07-21)  :       925,983 kr
  Now                     :     1,097,312 kr
  Threshold (2026 kr)     :    16,150,000 kr   (indexed 2.0%/yr)
  Trigger now             :    16,440,657 kr
  Trigger @ horizon       :    20,798,454 kr
  Years remaining         :  11.9

  AWAR (trailing)         :  +13.4%
  Required CAGR           :  +25.6%
  Status                  :  BEHIND  (-12.1% margin)

  Projected @ AWAR        :     6,871,577 kr
  vs target               :   -13,926,877 kr  (deficit)

  Scenario         CAGR       Projected     FI date   (incl. 6,000 kr/mo contributions)
  ------------------------------------------------------------------------
  Bear           +10%       4,995,748 kr       ~2056
  Conservative   +15%       7,973,276 kr       ~2046
  Base           +20%      12,629,101 kr       ~2042
  Current AWAR   +13%       6,871,577 kr       ~2049
  Bull           +30%      30,703,938 kr       ~2037

==============================================================
MACRO REGIME
==============================================================

  Feature                 Value   Regime  
  ------------------------------------------
  Nominal 10Y             4.91%   HIGH
  Real Yield             +2.79%   HIGH  ^
  Breakeven               2.12%   MID
  HY OAS                372 bps   WIDE
  IG Credit               1.61%   TIGHT
  Curve 10Y-3M          +51 bps   LOW
  Curve 10Y-2Y          +24 bps   LOW
  SE 10Y                  3.17%   MID
  USD                     123.6   STRONG

  HY 20d delta  : +42 bps  (widening)
  Confidence    : HIGH
  Data through  : 2026-11-25

==============================================================
PORTFOLIO SIGNALS
==============================================================

  Base: ry=HIGH  nominal_10y=HIGH  baa10y=TIGHT  usd=STRONG

  Position          Wt    21d   63d   63d med  252d med  W252     N  Note
  ----------------------------------------------------------------------
  Gold           15.1%    LOW   LOW     +0.8%     +0.8%   72%   103  
  Silver          0.0%    LOW   LOW     +0.9%     +0.9%   66%    67  
  Eli Lilly      24.7%   HIGH  HIGH     -0.6%     -0.6%   43%   172  
  Walmart         0.0%   HIGH  HIGH     +0.6%     +0.6%   58%   171  
  Cameco          0.0%    LOW   LOW     +1.9%     +1.9%   68%   121  
  Vertiv          0.0%    LOW   LOW     -0.1%     -0.1%   49%   126  
  Broadcom       18.5%    LOW   LOW     +2.1%     +2.1%   68%   138  

==============================================================
TACTICAL RULES
==============================================================

  Silver GSR Tactical
    GSR now        : 85.84  (as of 2026-11-25)
    60d GSR peak   : 87.24
    Fall from peak : 1.6%  (no (need >=5% fall for signal))
    T1 threshold   : 83.36  |  T2: 86.45  |  Exit: 62.56
    Signal         : INACTIVE
    Action         : No action -- hold base

  AVGO Trend Diagnostic  [guard RETIRED as a rotation rule -- PR #88]
    AVGO now       : $300.86  (as of 2026-11-25)
    200d SMA       : $366.95  (-18.0% gap)
    5d ROC         : -15.0%  (gap-down buy level: -10%)
    Signal         : DEFENSIVE  (trigger: CRASH)  -- informational, no rotation
    LLY stress     : inactive  ($1392.22 vs 200d SMA $1122.53, 5d ROC +0.7%)
    Joint stress   : inactive  -- retired alongside the guard, shown for continuity only
    Action         : No rotation. The 5d/-10% trigger has fired -- see the Crash Plan block below for the amount (MEMORY.md 'Crash plan').

  AVGO Volatility-Targeted Weight  [RETIRED 2026-08-18 -- diagnostic only]
    Trailing 21d vol : 82.1% (annualized)
    Long-run avg vol : 35.5% (annualized)
    Scalar           : 0.43x  (clipped to [0.30x, 1.30x])
    Would-be weights : Gold 34.5%  AVGO 17.3%  LLY 48.2%
    NOT ACTED ON     : routing + rebalance use the static base (see MEMORY.md)

  AVGO Earnings Checkpoint
    Latest qtr EPS (actual vs est.): $3.32 vs $3.24  (+2.5% surprise)
    TTM EPS (non-GAAP actual)  : $9.76
    Forward EPS (+1yr est.)    : $19.33
    Fwd/Trail ratio (normalized): 1.98x  (mid-pack vs. real AI/semi peers; corrected 2026-07-06 from a GAAP/non-GAAP mismatched 3.22x)
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
    Forward EPS (+1yr est.)    : $50.87
    Fwd/Trail ratio (normalized): 1.59x  (baseline established 2026-07-06)
    Revenue (latest qtr, actual): $24.40B  (TTM YoY: +45.5%)
    Next-qtr revenue consensus : $24.73B (implied YoY +28.2%)
    Next earnings  : 2027-02-03
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
    V (Visa)
      Observable : Payments volume growth, constant dollars, as stated in each quarterly release
      Latest     : 2026Q3: +9% YoY
      State      : HOLD
      Eroding    : YoY < 0 in any quarter (the release states the growth rate; a decline means card spending itself is shrinking)
      Action     : CUT: sell the full position
      Auto-read  : already_recorded 2026Q3 (8-K 2026-10-27)
    gold: EXEMPT -- Strategic anchor, held for a portfolio-level reason. No disclosed observable exists. Exit only on a mission change, which is outside Sightline's scope by construction.
    crypto_sleeve: EXEMPT -- Mechanical sleeve (BTC + staked ETH ETPs): hold-or-cut is delegated to its own MA50/100/200 ensemble rule and the 3-losing-cycles kill switch. No disclosed observable exists.
    global_index: EXEMPT -- Broad market index fund: no single thesis to break. Held for diversification; governed by its target and the rebalance band only.

  Opportunistic Sleeve
    Status         : CLOSED (0/1 position)
    Best candidate : none eligible today (either no ENTER survivors, or all failed the pre-entry tripwire or execution-drift gate)
    Basket-crash   : SNDK (Sandisk Corporation)  $73.61  (sector Technology, -90.5% 5d, 3 peers crashing, drift -0.0%)
    Plan           : buy near $73.61, flat 21d exit, NO stop until +8% gain then trails 8% (no floor before that -- riskier than the extension pathway)
    Open           : run_entry_screen.py --open SNDK <fill_price> <shares> <capital_sek> --entry-type basket_crash

  Crypto Trend Sleeve
    Status         : inactive -- no crypto leg carries a target (no alerts)

==============================================================
NEXT CONTRIBUTION
==============================================================

  Next kr        -> Reactor Core Cash
    Current wt (of Reactor Core) : 6.8%
    Target wt (config)           : 10.0%
    Gap                          : +3.2%
    Gate                         : OPEN
    Note: not funded by contributions -- 
    Denominator: 984,210 kr (6 positions carrying a target)

  Recession Mode  [Growth-Trend: S&P < 10m avg AND unemployment > 12m avg, month-end; ON shifts 20% LF Global Index -> cash]
    Recession mode status: OFF  (2026-10: S&P 756 vs 10m avg 727 [above]; unemployment 4.2% vs 12m avg 4.29% [not rising])
    Action: OFF -- targets normal (LF Global Index 25%, cash 10%); LF Global Index is ~0 kr below its target.

  Rebalance Check  [existing capital, band: 10pp absolute gap to target]
    Broadcom status: HOLD  (20.7% actual vs 15.0% target, gap -5.7%)
    Eli Lilly status: HOLD  (27.5% actual vs 25.0% target, gap -2.5%)
    Gold status: HOLD  (16.9% actual vs 20.0% target, gap +3.1%)
    LF Global Index status: HOLD  (25.5% actual vs 25.0% target, gap -0.5%)
    Reactor Core Cash status: HOLD  (6.8% actual vs 10.0% target, gap +3.2%)
    Visa status: HOLD  (2.7% actual vs 5.0% target, gap +2.3%)

  Reactor Core Cash
    Balance        : 66,810 kr  (6.8% vs 10% target)
    Shortfall      : 31,611 kr below target
    Action         : none -- hold. This is the dip sleeve; the AVGO/LLY 5d-ROC trigger spends it, not a contribution.

  Crash Plan  [cash 66,810 kr; 3 tranches of 32,807 kr bought in halves, max 2 per holding; trigger 5d <= -10%; caps Broadcom 25%, Eli Lilly 28%, LF Global Index 38%]
    Broadcom status: PAUSED  (5d -15.0%; no crash buys -- operator pause; resume: python crash_plan.py resume "Broadcom")
    Eli Lilly status: ARMED  (5d +0.7%, trigger -10%)
    LF Global Index status: ARMED  (5d -1.1%, trigger -10%)

  Market Watch  [early warnings -- awareness only, no trade; crash plan, band and recession mode act]
    Trend break status: ON  (S&P 717 vs 200d avg 732 (-2.1%); ON = 3 closes in a row below; risk of a 10% drawdown ~4x normal in that state)
    Labour cracking status: OFF  (real-time Sahm 0.00 (>= 0.50); claims 4wk avg 195k, +1% vs 52w low (>= +20%); the path to deep, recession-type falls)
    Curve inverted status: OFF  (10y-3m 5d avg +0.58pp (ON < 0); classic late-cycle warning)
    Volatility stress status: ON  (VIX 28.3 vs VIX3M 26.3 (ON = above for 3 closes); panic-level stress)
    Oil shock status: OFF  (WTI 1m avg $89, +49% y/y (ON >= +50%); ~2x the base odds of a 15% fall)

==============================================================
  Regime check (2026-11-25): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)
Building regime labels ...
  Conditions    : {'ry_regime': 'HIGH', 'baa10y_regime': 'TIGHT'}
  Matched dates : 1436  (2004-05-07 - 2026-11-25)  MODERATE

Computing capped 252d distributions for 51 candidates ...
  SNDK      hist=2yr  (below min 10yr, skipped)
  PLTR      hist=6yr  (below min 10yr, skipped)
  LITE      N= 620  mu= +50.2%  sigma= 61.0%  hist=11yr  [SINGLE]
  HOOD      hist=5yr  (below min 10yr, skipped)
  APP       hist=6yr  (below min 10yr, skipped)
  GEV       hist=3yr  (below min 10yr, skipped)
  CVNA      hist=10yr  (below min 10yr, skipped)
  HWM       N= 620  mu= +22.0%  sigma= 20.8%  hist=10yr  [SINGLE]
  VRT       hist=8yr  (below min 10yr, skipped)
  AVGO      N= 620  mu= +26.0%  sigma= 34.1%  hist=17yr  [SINGLE]
  TRGP      N= 620  mu=  +4.0%  sigma= 16.2%  hist=16yr  [SINGLE]
  DELL      N= 620  mu=  +5.1%  sigma= 18.8%  hist=10yr  [SINGLE]
  IBKR      N= 729  mu=  +6.4%  sigma= 18.7%  hist=20yr  [THIN]
  VST       N= 620  mu= +12.4%  sigma= 22.4%  hist=10yr  [SINGLE]
  STLD      N=1238  mu= +16.1%  sigma= 30.2%  hist=27yr  [MODERATE]
  PWR       N=1238  mu= +20.4%  sigma= 27.5%  hist=27yr  [MODERATE]
  NRG       N=1238  mu= +22.8%  sigma= 28.1%  hist=23yr  [MODERATE]
  ANET      N= 620  mu= +21.2%  sigma= 25.6%  hist=12yr  [SINGLE]
  CF        excluded (see EXCLUDE_TICKERS)
  DECK      N=1238  mu= +31.4%  sigma= 53.6%  hist=27yr  [MODERATE]
  CIEN      N=1238  mu= +21.2%  sigma= 27.4%  hist=27yr  [MODERATE]
  BKNG      N=1238  mu= +34.1%  sigma= 48.6%  hist=27yr  [MODERATE]
  WDC       N=1238  mu= +21.7%  sigma= 38.8%  hist=27yr  [MODERATE]
  GM        N= 620  mu=  +7.5%  sigma= 13.0%  hist=16yr  [SINGLE]
  EXV1.DE   no data
  CMI       N=1238  mu= +26.6%  sigma= 30.0%  hist=27yr  [MODERATE]
  COHR      max_up=71%  (M&A / corporate event detected, skipped)
  FTNT      N= 620  mu=  -9.7%  sigma= 10.6%  hist=17yr  [SINGLE]
  GS        N=1238  mu= +12.2%  sigma= 24.0%  hist=27yr  [MODERATE]
  CFG       N= 620  mu= +15.3%  sigma= 13.3%  hist=12yr  [SINGLE]
  PHAG.L    no data
  NVDA      N=1238  mu= +24.2%  sigma= 32.4%  hist=27yr  [MODERATE]
  TPR       N=1238  mu= +19.0%  sigma= 31.0%  hist=26yr  [MODERATE]
  CEG       hist=5yr  (below min 10yr, skipped)
  RL        N=1238  mu= +15.7%  sigma= 26.4%  hist=27yr  [MODERATE]
  ABB.ST    no data
  FOXA      hist=8yr  (below min 10yr, skipped)
  SSAB-B.ST  no data
  GRMN      N=1238  mu= +31.5%  sigma= 31.9%  hist=26yr  [MODERATE]
  FIX       N=1238  mu= +20.4%  sigma= 27.4%  hist=27yr  [MODERATE]
  FOX       hist=8yr  (below min 10yr, skipped)
  APH       N=1238  mu= +17.2%  sigma= 24.2%  hist=27yr  [MODERATE]
  FCX       N=1238  mu= +16.6%  sigma= 22.9%  hist=27yr  [MODERATE]
  EME       N=1238  mu= +17.2%  sigma= 25.9%  hist=27yr  [MODERATE]
  TEL2-B.ST  no data
  MPWR      N=1230  mu= +20.2%  sigma= 32.3%  hist=22yr  [MODERATE]
  PM        N= 620  mu= +10.6%  sigma= 13.7%  hist=19yr  [SINGLE]
  DASH      hist=6yr  (below min 10yr, skipped)
  SI_F      N=1238  mu= +13.3%  sigma= 20.9%  hist=26yr  [MODERATE]
  4GLD.DE   no data
  GC_F      N=1238  mu= +10.4%  sigma= 10.8%  hist=26yr  [MODERATE]

Cross-sectional prior mu : +18.2%  (shrinkage target)
Shrinkage lambda         : 100  (asset needs N>>100 to be fully trusted)

Optimizing (50 restarts, 32 candidates) ...

========================================================================
PORTFOLIO OPTIMIZER  --  Regime: RY=HIGH + BAA10Y=TIGHT
========================================================================
  Universe       : top 50 screen candidates + GC_F
  Matched dates  : 1436  MODERATE
  Shrinkage      : lambda=100  prior=+18.2%

  Ticker     Weight   mu(raw)   mu(shr)    sigma      N   Hist       Div
  -----------------------------------------------------------------
  GRMN        32.3%    +31.5%    +30.5%    31.9%   1238    26yr  MODERATE
  LITE        27.9%    +50.2%    +37.6%    61.0%    620    11yr    SINGLE
  BKNG        23.9%    +34.1%    +32.9%    48.6%   1238    27yr  MODERATE
  DECK        10.9%    +31.4%    +30.4%    53.6%   1238    27yr  MODERATE
  GC_F         5.0%    +10.4%    +11.0%    10.8%   1238    26yr  MODERATE  [gold]

  Active positions   : 5  (weight >= 1%)
  Equal-weight g(w)  : +18.5%  (benchmark)
  Optimized g(w)     : +29.3%

  WARNING: only 5 active positions — below recommended minimum of 6.
  Consider reducing MAX_W or increasing N_CANDIDATES.

  NOTE: g(w) is an approximation. mu/sigma are regime-conditional,
  capped at regime end. Shrinkage applied for short-history assets.
========================================================================
AVGO peer valuation snapshot -- 2026-11-26

Ticker        Price   TTM EPS   Fwd EPS  Fwd/Trail  Impl.growth   Fwd P/E   PEG(1y)
-----------------------------------------------------------------------------------
MU          $601.25    $75.51   $204.99      2.71x        +171%     2.93x      0.02
AMD         $406.03     $6.65    $17.61      2.65x        +165%    23.06x      0.14
MRVL        $130.93     $3.30     $7.38      2.24x        +124%    17.75x      0.14
AVGO*       $300.86     $9.76    $19.33      1.98x         +98%    15.57x      0.16
NVDA        $149.30     $8.39    $16.61      1.98x         +98%     8.99x      0.09
ASML      $1,303.08    $33.89    $56.94      1.68x         +68%    22.88x      0.34
ANET        $163.99     $3.91     $6.04      1.54x         +54%    27.16x      0.50
TSM         $342.34    $15.54    $23.39      1.50x         +50%    14.64x      0.29
QCOM        $168.66    $10.53    $12.18      1.16x         +16%    13.85x      0.88

* = AVGO

AVGO rank -- growth ratio (highest first): 4 of 9
AVGO rank -- forward P/E (cheapest first): 5 of 9
AVGO rank -- PEG(1y) (cheapest first)    : 5 of 9

Note: PEG(1y) is built on a 1-year forward growth estimate, not the conventional 5-year estimate PEG ratios (including yfinance's own pegRatio field, deliberately not fetched here) normally use. MEMORY.md's 2026-07-06 entry recorded AVGO's PEG as 0.41 alongside a 19.4x forward P/E -- those two never reconciled on the same basis (19.4 / 139% implied growth = 0.14, not 0.41). PEG(1y) above is internally consistent but not comparable to that historical figure or to any 5-year PEG from elsewhere.

AVGO and peers vs their OWN stored history (low percentile = cheap for that name)
Ticker     Fwd P/E   pctile   obs
AMD         23.06x       --    33
ANET        27.16x       --    33
ASML        22.88x       --    33
AVGO        15.57x       --    33
MRVL        17.75x       --    33
MU           2.93x       --    33
NVDA         8.99x       --    33
QCOM        13.85x       --    33
TSM         14.64x       --    33
  accruing -- 33/60 observations needed before a percentile is shown. Started 2026-10-18; cannot be backfilled.
