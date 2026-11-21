==============================================================
REACTOR CORE -- PORTFOLIO SNAPSHOT
==============================================================================
Position                Shares      Price    Value SEK     Wt    Tgt   Drift
------------------------------------------------------------------------------
  Gold                     234     700 kr   163,803 kr  15.3%  20.0%   -4.7%
  Silver                     -     383 kr         0 kr   0.0%   0.0%   +0.0%
  Eli Lilly                 19  13,735 kr   260,960 kr  24.3%  20.0%   +4.3%
  Walmart                    -   1,305 kr         0 kr   0.0%   0.0%   +0.0%
  Cameco                     -     591 kr         0 kr   0.0%   0.0%   +0.0%
  Vertiv                     -   1,695 kr         0 kr   0.0%   0.0%   +0.0%
  Broadcom                  70   3,104 kr   217,257 kr  20.3%  20.0%   +0.3%
  Howmet Aerospace           -   2,133 kr         0 kr   0.0%   0.0%   +0.0%
  Spiltan Räntefond     738.53     153 kr   113,032 kr  10.5%   0.0%  +10.5%
  War Chest                  -     manual        19 kr   0.0%   0.0%   +0.0%
  Reactor Core Cash          -     manual    80,950 kr   7.5%  10.0%   -2.5%
  Virtune Bitcoin            -     100 kr         0 kr   0.0%   0.0%   +0.0%
  Virtune Staked ETH         -      40 kr         0 kr   0.0%   0.0%   +0.0%
  LF Global Index       397.84     594 kr   236,391 kr  22.0%  30.0%   -8.0%
------------------------------------------------------------------------------
  TPV                                        1,072,412 kr
    Reactor Core            722,970 kr  (67.4%)   target 60.0%  drift +7.4%
    Global Index            236,391 kr  (22.0%)   target 30.0%  drift -8.0%
    Home Base               113,032 kr  (10.5%)   target 10.0%  drift +0.5%
    Crypto Sleeve                 0 kr  ( 0.0%)   target  0.0%  drift +0.0%
    War Chest                    19 kr  ( 0.0%)   target  0.0%  drift +0.0%

==============================================================
FI@50 PACE TRACKER
==============================================================
  Start  (2025-07-21)  :       925,983 kr
  Now                     :     1,072,412 kr
  Threshold (2026 kr)     :    16,150,000 kr   (indexed 2.0%/yr)
  Trigger now             :    16,436,200 kr
  Trigger @ horizon       :    20,798,454 kr
  Years remaining         :  11.9

  AWAR (trailing)         :  +11.6%
  Required CAGR           :  +25.7%
  Status                  :  BEHIND  (-14.1% margin)

  Projected @ AWAR        :     5,731,296 kr
  vs target               :   -15,067,158 kr  (deficit)

  Scenario         CAGR       Projected     FI date   (incl. 6,000 kr/mo contributions)
  ------------------------------------------------------------------------
  Bear           +10%       4,925,951 kr       ~2056
  Conservative   +15%       7,858,405 kr       ~2047
  Base           +20%      12,444,173 kr       ~2042
  Current AWAR   +12%       5,731,296 kr       ~2052
  Bull           +30%      30,252,243 kr       ~2037

==============================================================
MACRO REGIME
==============================================================

  Feature                 Value   Regime  
  ------------------------------------------
  Nominal 10Y             5.04%   HIGH
  Real Yield             +2.88%   HIGH  ^
  Breakeven               2.15%   MID
  HY OAS                352 bps   WIDE
  IG Credit               1.56%   TIGHT
  Curve 10Y-3M          +60 bps   LOW
  Curve 10Y-2Y          +29 bps   LOW
  SE 10Y                  3.17%   MID
  USD                     122.7   STRONG

  HY 20d delta  : +25 bps  (widening)
  Confidence    : HIGH
  Data through  : 2026-11-20

==============================================================
PORTFOLIO SIGNALS
==============================================================

  Base: ry=HIGH  nominal_10y=HIGH  baa10y=TIGHT  usd=STRONG

  Position          Wt    21d   63d   63d med  252d med  W252     N  Note
  ----------------------------------------------------------------------
  Gold           15.3%    LOW   LOW     +0.8%     +0.8%   70%   105  
  Silver          0.0%    LOW   LOW     +0.9%     +0.9%   65%    68  
  Eli Lilly      24.3%    MID  HIGH     -0.9%     -0.9%   40%    82  
  Walmart         0.0%   HIGH  HIGH     +0.7%     +0.7%   60%   176  
  Cameco          0.0%    LOW   LOW     +1.9%     +1.9%   67%   123  
  Vertiv          0.0%    LOW   LOW     +0.2%     +0.2%   50%   128  
  Broadcom       20.3%    LOW   LOW     +2.1%     +2.1%   68%   141  

==============================================================
TACTICAL RULES
==============================================================

  Silver GSR Tactical
    GSR now        : 86.15  (as of 2026-11-20)
    60d GSR peak   : 86.15
    Fall from peak : 0.0%  (no (need >=5% fall for signal))
    T1 threshold   : 83.36  |  T2: 86.45  |  Exit: 62.56
    Signal         : INACTIVE
    Action         : No action -- hold base

  AVGO Trend Diagnostic  [guard RETIRED as a rotation rule -- PR #88]
    AVGO now       : $304.41  (as of 2026-11-20)
    200d SMA       : $367.44  (-17.2% gap)
    5d ROC         : -12.3%  (gap-down buy level: -10%)
    Signal         : DEFENSIVE  (trigger: CRASH)  -- informational, no rotation
    LLY stress     : inactive  ($1347.11 vs 200d SMA $1117.30, 5d ROC -6.7%)
    Joint stress   : inactive  -- retired alongside the guard, shown for continuity only
    Action         : No rotation. The 5d/-10% trigger has fired -- see the Crash Plan block below for the amount (MEMORY.md 'Crash plan').

  AVGO Volatility-Targeted Weight  [RETIRED 2026-08-18 -- diagnostic only]
    Trailing 21d vol : 82.2% (annualized)
    Long-run avg vol : 35.5% (annualized)
    Scalar           : 0.43x  (clipped to [0.30x, 1.30x])
    Would-be weights : Gold 34.5%  AVGO 17.3%  LLY 48.3%
    NOT ACTED ON     : routing + rebalance use the static base (see MEMORY.md)

  AVGO Earnings Checkpoint
    Latest qtr EPS (actual vs est.): $3.32 vs $3.24  (+2.5% surprise)
    TTM EPS (non-GAAP actual)  : $9.76
    Forward EPS (+1yr est.)    : $19.35
    Fwd/Trail ratio (normalized): 1.98x  (mid-pack vs. real AI/semi peers; corrected 2026-07-06 from a GAAP/non-GAAP mismatched 3.22x)
    Revenue (latest qtr, actual): $29.59B  (TTM YoY: +48.7%)
    Next-qtr revenue consensus : $34.90B (implied YoY +93.8%)
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
    Best candidate : APP (AppLovin Corporation)  $348.29  (ext +12.6%, 21d med +2.9%, ave +4.7%, win 56.4%, div THIN, drift -0.0%)
    Plan           : buy near $348.29, hold ~21d, stop = MA50-5% then trails 3% once +5% gain
    Open           : run_entry_screen.py --open APP <fill_price> <shares> <capital_sek>
    VIX review     : 35.89  (96% percentile, spiking) -- for review, not a gate
    Basket-crash   : SNDK (Sandisk Corporation)  $79.24  (sector Technology, -91.0% 5d, 8 peers crashing, drift +0.0%)
    Plan           : buy near $79.24, flat 21d exit, NO stop until +8% gain then trails 8% (no floor before that -- riskier than the extension pathway)
    Open           : run_entry_screen.py --open SNDK <fill_price> <shares> <capital_sek> --entry-type basket_crash
    NOTE           : extension pathway also has a candidate today (APP) -- that one is preferred (live-validated); this is shown for awareness.

  Crypto Trend Sleeve
    Status         : inactive -- no crypto leg carries a target (no alerts)

==============================================================
NEXT CONTRIBUTION
==============================================================

  Next kr        -> LF Global Index
    Current wt (of Reactor Core) : 24.6%
    Target wt (config)           : 30.0%
    Gap                          : +5.4%
    Gate                         : OPEN
    Note: not funded by contributions -- 
    Denominator: 959,361 kr (5 positions carrying a target)

  Recession Mode  [Growth-Trend: S&P < 10m avg AND unemployment > 12m avg, month-end; ON shifts 20% LF Global Index -> cash]
    Recession mode status: OFF  (2026-10: S&P 756 vs 10m avg 727 [above]; unemployment 4.2% vs 12m avg 4.29% [not rising])
    Action: OFF -- targets normal (LF Global Index 30%, cash 10%); LF Global Index is ~51,417 kr below its target.

  Rebalance Check  [existing capital, band: 10pp absolute gap to target]
    Broadcom status: HOLD  (22.6% actual vs 20.0% target, gap -2.6%)
    Eli Lilly status: HOLD  (27.2% actual vs 20.0% target, gap -7.2%)
    Gold status: HOLD  (17.1% actual vs 20.0% target, gap +2.9%)
    LF Global Index status: HOLD  (24.6% actual vs 30.0% target, gap +5.4%)
    Reactor Core Cash status: HOLD  (8.4% actual vs 10.0% target, gap +1.6%)

  Reactor Core Cash
    Balance        : 80,950 kr  (8.4% vs 10% target)
    Shortfall      : 14,986 kr below target
    Action         : none -- hold. This is the dip sleeve; the AVGO/LLY 5d-ROC trigger spends it, not a contribution.

  Crash Plan  [cash 80,950 kr; 3 tranches of 31,979 kr bought in halves, max 2 per holding; trigger 5d <= -10%; caps 28% stock / 38% index]
    Broadcom status: WAITING  (second half in 11 sessions or below the level $262.38)
    Eli Lilly status: ARMED  (5d -6.7%, trigger -10%)
    LF Global Index status: ARMED  (5d -1.9%, trigger -10%)

  Market Watch  [early warnings -- awareness only, no trade; crash plan, band and recession mode act]
    Trend break status: ON  (S&P 690 vs 200d avg 732 (-5.7%); ON = 3 closes in a row below; risk of a 10% drawdown ~4x normal in that state)
    Labour cracking status: OFF  (real-time Sahm 0.00 (>= 0.50); claims 4wk avg 196k, +1% vs 52w low (>= +20%); the path to deep, recession-type falls)
    Curve inverted status: OFF  (10y-3m 5d avg +0.72pp (ON < 0); classic late-cycle warning)
    Volatility stress status: ON  (VIX 35.9 vs VIX3M 30.9 (ON = above for 3 closes); panic-level stress)
    Oil shock status: ON  (WTI 1m avg $92, +53% y/y (ON >= +50%); ~2x the base odds of a 15% fall)

==============================================================
  Regime check (2026-11-20): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)
Building regime labels ...
  Conditions    : {'ry_regime': 'HIGH', 'baa10y_regime': 'TIGHT'}
  Matched dates : 1433  (2004-05-07 - 2026-11-20)  MODERATE

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
  VST       N= 620  mu= +12.4%  sigma= 22.4%  hist=10yr  [SINGLE]
  IBKR      N= 729  mu=  +6.4%  sigma= 18.7%  hist=20yr  [THIN]
  DELL      N= 620  mu=  +5.1%  sigma= 18.8%  hist=10yr  [SINGLE]
  STLD      N=1238  mu= +16.1%  sigma= 30.2%  hist=27yr  [MODERATE]
  PWR       N=1238  mu= +20.4%  sigma= 27.5%  hist=27yr  [MODERATE]
  NRG       N=1238  mu= +22.8%  sigma= 28.1%  hist=23yr  [MODERATE]
  ANET      N= 620  mu= +21.2%  sigma= 25.6%  hist=12yr  [SINGLE]
  DECK      N=1238  mu= +31.4%  sigma= 53.6%  hist=27yr  [MODERATE]
  CF        excluded (see EXCLUDE_TICKERS)
  CIEN      N=1238  mu= +21.2%  sigma= 27.4%  hist=27yr  [MODERATE]
  BKNG      N=1238  mu= +34.1%  sigma= 48.6%  hist=27yr  [MODERATE]
  WDC       N=1238  mu= +21.7%  sigma= 38.8%  hist=27yr  [MODERATE]
  EXV1.DE   no data
  GM        N= 620  mu=  +7.5%  sigma= 13.0%  hist=16yr  [SINGLE]
  CMI       N=1238  mu= +26.6%  sigma= 30.0%  hist=27yr  [MODERATE]
  COHR      max_up=71%  (M&A / corporate event detected, skipped)
  FTNT      N= 620  mu=  -9.7%  sigma= 10.6%  hist=17yr  [SINGLE]
  GS        N=1238  mu= +12.2%  sigma= 24.0%  hist=27yr  [MODERATE]
  CFG       N= 620  mu= +15.3%  sigma= 13.3%  hist=12yr  [SINGLE]
  PHAG.L    no data
  TPR       N=1238  mu= +19.0%  sigma= 31.0%  hist=26yr  [MODERATE]
  NVDA      N=1238  mu= +24.2%  sigma= 32.4%  hist=27yr  [MODERATE]
  CEG       hist=5yr  (below min 10yr, skipped)
  RL        N=1238  mu= +15.7%  sigma= 26.4%  hist=27yr  [MODERATE]
  ABB.ST    no data
  FOXA      hist=8yr  (below min 10yr, skipped)
  SSAB-B.ST  no data
  FIX       N=1238  mu= +20.4%  sigma= 27.4%  hist=27yr  [MODERATE]
  GRMN      N=1238  mu= +31.5%  sigma= 31.9%  hist=26yr  [MODERATE]
  FOX       hist=8yr  (below min 10yr, skipped)
  APH       N=1238  mu= +17.2%  sigma= 24.2%  hist=27yr  [MODERATE]
  EME       N=1238  mu= +17.2%  sigma= 25.9%  hist=27yr  [MODERATE]
  TEL2-B.ST  no data
  FCX       N=1238  mu= +16.6%  sigma= 22.9%  hist=27yr  [MODERATE]
  MPWR      N=1230  mu= +20.2%  sigma= 32.3%  hist=22yr  [MODERATE]
  PM        N= 620  mu= +10.6%  sigma= 13.7%  hist=19yr  [SINGLE]
  DASH      hist=6yr  (below min 10yr, skipped)
  SI_F      N=1238  mu= +13.3%  sigma= 20.9%  hist=26yr  [MODERATE]
  FSLR      N= 850  mu= +26.9%  sigma= 58.8%  hist=20yr  [MODERATE]
  GC_F      N=1238  mu= +10.4%  sigma= 10.8%  hist=26yr  [MODERATE]

Cross-sectional prior mu : +18.5%  (shrinkage target)
Shrinkage lambda         : 100  (asset needs N>>100 to be fully trusted)

Optimizing (50 restarts, 33 candidates) ...

========================================================================
PORTFOLIO OPTIMIZER  --  Regime: RY=HIGH + BAA10Y=TIGHT
========================================================================
  Universe       : top 50 screen candidates + GC_F
  Matched dates  : 1433  MODERATE
  Shrinkage      : lambda=100  prior=+18.5%

  Ticker     Weight   mu(raw)   mu(shr)    sigma      N   Hist       Div
  -----------------------------------------------------------------
  GRMN        32.2%    +31.5%    +30.6%    31.9%   1238    26yr  MODERATE
  LITE        28.1%    +50.2%    +37.7%    61.0%    620    11yr    SINGLE
  BKNG        23.8%    +34.1%    +32.9%    48.6%   1238    27yr  MODERATE
  DECK        10.9%    +31.4%    +30.4%    53.6%   1238    27yr  MODERATE
  GC_F         5.0%    +10.4%    +11.0%    10.8%   1238    26yr  MODERATE  [gold]

  Active positions   : 5  (weight >= 1%)
  Equal-weight g(w)  : +18.8%  (benchmark)
  Optimized g(w)     : +29.3%

  WARNING: only 5 active positions — below recommended minimum of 6.
  Consider reducing MAX_W or increasing N_CANDIDATES.

  NOTE: g(w) is an approximation. mu/sigma are regime-conditional,
  capped at regime end. Shrinkage applied for short-history assets.
========================================================================
AVGO peer valuation snapshot -- 2026-11-21

Ticker        Price   TTM EPS   Fwd EPS  Fwd/Trail  Impl.growth   Fwd P/E   PEG(1y)
-----------------------------------------------------------------------------------
MU          $594.51    $75.51   $208.83      2.77x        +177%     2.85x      0.02
AMD         $424.39     $6.65    $17.64      2.65x        +165%    24.06x      0.15
MRVL        $122.28     $3.30     $7.37      2.23x        +123%    16.59x      0.13
AVGO*       $304.41     $9.76    $19.35      1.98x         +98%    15.73x      0.16
NVDA        $125.53     $8.39    $16.61      1.98x         +98%     7.56x      0.08
ASML      $1,266.22    $33.89    $56.43      1.67x         +67%    22.44x      0.34
ANET        $167.62     $3.91     $6.04      1.54x         +54%    27.77x      0.51
TSM         $318.71    $15.54    $23.39      1.50x         +50%    13.63x      0.27
QCOM        $149.94    $10.53    $12.18      1.16x         +16%    12.31x      0.78

* = AVGO

AVGO rank -- growth ratio (highest first): 4 of 9
AVGO rank -- forward P/E (cheapest first): 5 of 9
AVGO rank -- PEG(1y) (cheapest first)    : 5 of 9

Note: PEG(1y) is built on a 1-year forward growth estimate, not the conventional 5-year estimate PEG ratios (including yfinance's own pegRatio field, deliberately not fetched here) normally use. MEMORY.md's 2026-07-06 entry recorded AVGO's PEG as 0.41 alongside a 19.4x forward P/E -- those two never reconciled on the same basis (19.4 / 139% implied growth = 0.14, not 0.41). PEG(1y) above is internally consistent but not comparable to that historical figure or to any 5-year PEG from elsewhere.

AVGO and peers vs their OWN stored history (low percentile = cheap for that name)
Ticker     Fwd P/E   pctile   obs
AMD         24.06x       --    28
ANET        27.77x       --    28
ASML        22.44x       --    28
AVGO        15.73x       --    28
MRVL        16.59x       --    28
MU           2.85x       --    28
NVDA         7.56x       --    28
QCOM        12.31x       --    28
TSM         13.63x       --    28
  accruing -- 28/60 observations needed before a percentile is shown. Started 2026-10-18; cannot be backfilled.
