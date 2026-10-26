/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/yfinance/scrapers/analysis.py:135: Pandas4Warning: The inplace keyword in DataFrame.set_index is deprecated and will be removed in a future version (PDEP-8).
See https://pandas.pydata.org/docs/dev/whatsnew/v3.1.0.html#deprecation-inplace for more details.
  df.set_index('quarter', inplace=True)
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/yfinance/scrapers/analysis.py:135: Pandas4Warning: The inplace keyword in DataFrame.set_index is deprecated and will be removed in a future version (PDEP-8).
See https://pandas.pydata.org/docs/dev/whatsnew/v3.1.0.html#deprecation-inplace for more details.
  df.set_index('quarter', inplace=True)
==============================================================
REACTOR CORE -- PORTFOLIO SNAPSHOT
==============================================================================
Position                Shares      Price    Value SEK     Wt    Tgt   Drift
------------------------------------------------------------------------------
  Gold                     234     770 kr   180,160 kr  16.7%  20.0%   -3.3%
  Silver                     -     488 kr         0 kr   0.0%   0.0%   +0.0%
  Eli Lilly                 19  12,637 kr   240,102 kr  22.2%  20.0%   +2.2%
  Walmart                    -   1,190 kr         0 kr   0.0%   0.0%   +0.0%
  Cameco                     -     780 kr         0 kr   0.0%   0.0%   +0.0%
  Vertiv                     -   1,928 kr         0 kr   0.0%   0.0%   +0.0%
  Broadcom                  65   3,192 kr   207,488 kr  19.2%  20.0%   -0.8%
  Howmet Aerospace           -   1,845 kr         0 kr   0.0%   0.0%   +0.0%
  Spiltan Räntefond     738.53     153 kr   112,788 kr  10.4%   0.0%  +10.4%
  War Chest                  -     manual        19 kr   0.0%   0.0%   +0.0%
  Reactor Core Cash          -     manual    56,282 kr   5.2%  10.0%   -4.8%
  Virtune Bitcoin          193     132 kr    25,401 kr   2.4%   2.5%   -0.1%
  Virtune Staked ETH       262      55 kr    14,352 kr   1.3%   2.5%   -1.2%
  LF Global Index       397.84     613 kr   243,870 kr  22.6%  25.0%   -2.4%
------------------------------------------------------------------------------
  TPV                                        1,080,463 kr
    Reactor Core            684,032 kr  (63.3%)   target 60.0%  drift +3.3%
    Global Index            243,870 kr  (22.6%)   target 25.0%  drift -2.4%
    Home Base               112,788 kr  (10.4%)   target 10.0%  drift +0.4%
    Crypto Sleeve            39,753 kr  ( 3.7%)   target  5.0%  drift -1.3%
    War Chest                    19 kr  ( 0.0%)   target  0.0%  drift +0.0%

==============================================================
FI@50 PACE TRACKER
==============================================================
  Start  (2025-07-21)  :       925,983 kr
  Now                     :     1,080,463 kr
  Threshold (2026 kr)     :    16,150,000 kr   (indexed 2.0%/yr)
  Trigger now             :    16,413,048 kr
  Trigger @ horizon       :    20,798,454 kr
  Years remaining         :  12.0

  AWAR (trailing)         :  +13.0%
  Required CAGR           :  +25.5%
  Status                  :  BEHIND  (-12.5% margin)

  Projected @ AWAR        :     6,603,900 kr
  vs target               :   -14,194,554 kr  (deficit)

  Scenario         CAGR       Projected     FI date   (incl. 6,000 kr/mo contributions)
  ------------------------------------------------------------------------
  Bear           +10%       4,989,813 kr       ~2056
  Conservative   +15%       7,984,978 kr       ~2046
  Base           +20%      12,683,161 kr       ~2042
  Current AWAR   +13%       6,603,900 kr       ~2049
  Bull           +30%      31,013,288 kr       ~2037

==============================================================
MACRO REGIME
==============================================================

  Feature                 Value   Regime  
  ------------------------------------------
  Nominal 10Y             4.96%   HIGH
  Real Yield             +2.64%   HIGH  ^
  Breakeven               2.34%   HIGH
  HY OAS                340 bps   WIDE
  IG Credit               1.46%   TIGHT
  Curve 10Y-3M          +78 bps   MID
  Curve 10Y-2Y          +31 bps   LOW
  SE 10Y                  3.19%   MID
  USD                     121.4   STRONG

  HY 20d delta  : +60 bps  (widening)
  Confidence    : UNCERTAIN
  Data through  : 2026-10-23

==============================================================
PORTFOLIO SIGNALS
==============================================================

  Base: ry=HIGH  nominal_10y=HIGH  baa10y=TIGHT  usd=STRONG

  Position          Wt    21d   63d   63d med  252d med  W252     N  Note
  ----------------------------------------------------------------------
  Gold           16.7%    LOW   LOW     +0.8%     +0.8%   68%   100  
  Silver          0.0%    LOW   LOW     +0.9%     +0.9%   65%    68  
  Eli Lilly      22.2%   HIGH   MID     +0.4%     +0.4%   62%    45  
  Walmart         0.0%   HIGH  HIGH     +0.8%     +0.8%   61%   172  
  Cameco          0.0%    LOW   LOW     +1.8%     +1.8%   66%   118  
  Vertiv          0.0%    LOW   LOW     -1.1%     -1.1%   46%   118  
  Broadcom       19.2%    LOW   LOW     +1.0%     +1.0%   62%   124  

==============================================================
TACTICAL RULES
==============================================================

  Silver GSR Tactical
    GSR now        : 74.31  (as of 2026-10-23)
    60d GSR peak   : 74.31
    Fall from peak : 0.0%  (no (need >=5% fall for signal))
    T1 threshold   : 83.36  |  T2: 86.45  |  Exit: 62.56
    Signal         : INACTIVE
    Action         : No action -- hold base

  AVGO Trend Diagnostic  [guard RETIRED as a rotation rule -- PR #88]
    AVGO now       : $321.68  (as of 2026-10-23)
    200d SMA       : $367.33  (-12.4% gap)
    5d ROC         : -2.2%  (gap-down buy level: -10%)
    Signal         : DEFENSIVE  (trigger: MA)  -- informational, no rotation
    LLY stress     : inactive  ($1273.46 vs 200d SMA $1083.98, 5d ROC +1.3%)
    Joint stress   : inactive  -- retired alongside the guard, shown for continuity only
    Action         : No action -- guard retired as a rotation rule (see PR #88); reading is diagnostic only

  AVGO Volatility-Targeted Weight  [RETIRED 2026-08-18 -- diagnostic only]
    Trailing 21d vol : 37.6% (annualized)
    Long-run avg vol : 35.4% (annualized)
    Scalar           : 0.94x  (clipped to [0.30x, 1.30x])
    Would-be weights : Gold 26.0%  AVGO 37.6%  LLY 36.4%
    NOT ACTED ON     : routing + rebalance use the static base (see MEMORY.md)

  AVGO Earnings Checkpoint
    Latest qtr EPS (actual vs est.): $3.32 vs $3.24  (+2.5% surprise)
    TTM EPS (non-GAAP actual)  : $9.76
    Forward EPS (+1yr est.)    : $19.43
    Fwd/Trail ratio (normalized): 1.99x  (mid-pack vs. real AI/semi peers; corrected 2026-07-06 from a GAAP/non-GAAP mismatched 3.22x)
    Revenue (latest qtr, actual): $29.59B  (TTM YoY: +48.7%)
    Next-qtr revenue consensus : $34.90B (implied YoY +93.8%)
    Next earnings  : 2026-12-09
    Reminder       : not_due
    Latest quarter : 2026-07-31
    Beat streak    : 4
    Guidance trend : flat  (+1yr estimate vs. 90 days ago)

  LLY Earnings Checkpoint
    Latest qtr EPS (actual vs est.): $8.38 vs $6.58  (+27.3% surprise)
    TTM EPS (non-GAAP actual)  : $31.49
    Forward EPS (+1yr est.)    : $47.22
    Fwd/Trail ratio (normalized): 1.50x  (baseline established 2026-07-06)
    Revenue (latest qtr, actual): $22.97B  (TTM YoY: +49.6%)
    Next-qtr revenue consensus : $22.62B (implied YoY +28.5%)
    Next earnings  : 2026-10-29
    Reminder       : DUE
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
    Basket-crash   : HWM (Howmet Aerospace Inc.)  $185.91  (sector Industrials, -15.9% 5d, 2 peers crashing, drift +0.3%)
    Plan           : buy near $185.91, flat 21d exit, NO stop until +8% gain then trails 8% (no floor before that -- riskier than the extension pathway)
    Open           : run_entry_screen.py --open HWM <fill_price> <shares> <capital_sek> --entry-type basket_crash

  Crypto Trend Sleeve
    Bitcoin (BTC-USD)  $80,844  (as of 2026-10-23)
      Target       : 100%  = 24 191 kr of 24 191 kr
      MA50         : LONG (MA $80,032, flat below $78,431)
      MA100        : LONG (MA $71,687, flat below $70,253)
      MA200        : LONG (MA $72,791, flat below $71,335)
      Last change  : 2026-08-21 -> 100%
    Ethereum (ETH-USD)  $2,374  (as of 2026-10-23)
      Target       : 67%  = 16 128 kr of 24 191 kr
      MA50         : FLAT (MA $2,492, long above $2,542)
      MA100        : LONG (MA $2,140, flat below $2,097)
      MA200        : LONG (MA $2,175, flat below $2,131)
      Last change  : 2026-10-22 -> 67%

==============================================================
NEXT CONTRIBUTION
==============================================================

  Next kr        -> Reactor Core Cash
    Current wt (of Reactor Core) : 5.8%
    Target wt (config)           : 10.0%
    Gap                          : +4.2%
    Gate                         : OPEN
    Note: not funded by contributions -- Virtune Bitcoin, Virtune Staked ETH
    Denominator: 967,655 kr (7 positions carrying a target)

  Rebalance Check  [existing capital, band: 10pp absolute gap to target]
    Broadcom status: HOLD  (21.4% actual vs 20.0% target, gap -1.4%)
    Eli Lilly status: HOLD  (24.8% actual vs 20.0% target, gap -4.8%)
    Gold status: HOLD  (18.6% actual vs 20.0% target, gap +1.4%)
    LF Global Index status: HOLD  (25.2% actual vs 25.0% target, gap -0.2%)
    Reactor Core Cash status: HOLD  (5.8% actual vs 10.0% target, gap +4.2%)
    Virtune Bitcoin status: HOLD  (2.6% actual vs 2.5% target, gap -0.1%)
    Virtune Staked ETH status: HOLD  (1.5% actual vs 2.5% target, gap +1.0%)

  Reactor Core Cash
    Balance        : 56,282 kr  (5.8% vs 10% target)
    Shortfall      : 40,484 kr below target
    Action         : none -- hold. This is the dip sleeve; the AVGO/LLY 5d-ROC trigger spends it, not a contribution.

==============================================================
  Regime check (2026-10-23): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)
Building regime labels ...
  Conditions    : {'ry_regime': 'HIGH', 'baa10y_regime': 'TIGHT'}
  Matched dates : 1413  (2004-05-07 - 2026-10-23)  MODERATE

Computing capped 252d distributions for 51 candidates ...
  SNDK      hist=2yr  (below min 10yr, skipped)
  PLTR      hist=6yr  (below min 10yr, skipped)
  APP       hist=6yr  (below min 10yr, skipped)
  LITE      N= 620  mu= +50.2%  sigma= 61.0%  hist=11yr  [SINGLE]
  HOOD      hist=5yr  (below min 10yr, skipped)
  GEV       hist=3yr  (below min 10yr, skipped)
  CVNA      hist=9yr  (below min 10yr, skipped)
  HWM       hist=10yr  (below min 10yr, skipped)
  VRT       hist=8yr  (below min 10yr, skipped)
  AVGO      N= 620  mu= +26.0%  sigma= 34.1%  hist=17yr  [SINGLE]
  VST       N= 620  mu= +12.4%  sigma= 22.4%  hist=10yr  [SINGLE]
  TRGP      N= 620  mu=  +4.0%  sigma= 16.2%  hist=16yr  [SINGLE]
  IBKR      N= 729  mu=  +6.4%  sigma= 18.7%  hist=19yr  [THIN]
  STLD      N=1238  mu= +16.1%  sigma= 30.2%  hist=27yr  [MODERATE]
  PWR       N=1238  mu= +20.4%  sigma= 27.5%  hist=27yr  [MODERATE]
  DECK      N=1238  mu= +31.4%  sigma= 53.6%  hist=27yr  [MODERATE]
  NRG       N=1238  mu= +22.8%  sigma= 28.1%  hist=23yr  [MODERATE]
  ANET      N= 620  mu= +21.2%  sigma= 25.6%  hist=12yr  [SINGLE]
  CF        excluded (see EXCLUDE_TICKERS)
  DELL      N= 620  mu=  +5.1%  sigma= 18.8%  hist=10yr  [SINGLE]
  CIEN      N=1238  mu= +21.2%  sigma= 27.4%  hist=27yr  [MODERATE]
  BKNG      N=1238  mu= +34.1%  sigma= 48.6%  hist=27yr  [MODERATE]
  GM        N= 620  mu=  +7.5%  sigma= 13.0%  hist=16yr  [SINGLE]
  EXV1.DE   no data
  CMI       N=1238  mu= +26.6%  sigma= 30.0%  hist=27yr  [MODERATE]
  WDC       N=1238  mu= +21.7%  sigma= 38.8%  hist=27yr  [MODERATE]
  GS        N=1238  mu= +12.2%  sigma= 24.0%  hist=27yr  [MODERATE]
  COHR      max_up=71%  (M&A / corporate event detected, skipped)
  CFG       N= 620  mu= +15.3%  sigma= 13.3%  hist=12yr  [SINGLE]
  PHAG.L    no data
  TPR       N=1238  mu= +19.0%  sigma= 31.0%  hist=26yr  [MODERATE]
  FOXA      hist=8yr  (below min 10yr, skipped)
  CEG       hist=5yr  (below min 10yr, skipped)
  NVDA      N=1238  mu= +24.2%  sigma= 32.4%  hist=27yr  [MODERATE]
  RL        N=1238  mu= +15.7%  sigma= 26.4%  hist=27yr  [MODERATE]
  FTNT      N= 620  mu=  -9.7%  sigma= 10.6%  hist=17yr  [SINGLE]
  ABB.ST    no data
  FIX       N=1238  mu= +20.4%  sigma= 27.4%  hist=27yr  [MODERATE]
  GRMN      N=1238  mu= +31.5%  sigma= 31.9%  hist=26yr  [MODERATE]
  EME       N=1238  mu= +17.2%  sigma= 25.9%  hist=27yr  [MODERATE]
  FOX       hist=8yr  (below min 10yr, skipped)
  DASH      hist=6yr  (below min 10yr, skipped)
  TEL2-B.ST  no data
  SSAB-B.ST  no data
  APH       N=1238  mu= +17.2%  sigma= 24.2%  hist=27yr  [MODERATE]
  FCX       N=1238  mu= +16.6%  sigma= 22.9%  hist=27yr  [MODERATE]
  FSLR      N= 850  mu= +26.9%  sigma= 58.8%  hist=20yr  [MODERATE]
  MPWR      N=1230  mu= +20.2%  sigma= 32.3%  hist=22yr  [MODERATE]
  SI_F      N=1238  mu= +13.3%  sigma= 20.9%  hist=26yr  [MODERATE]
  PM        N= 620  mu= +10.6%  sigma= 13.7%  hist=19yr  [SINGLE]
  GC_F      N=1238  mu= +10.4%  sigma= 10.8%  hist=26yr  [MODERATE]

Cross-sectional prior mu : +18.4%  (shrinkage target)
Shrinkage lambda         : 100  (asset needs N>>100 to be fully trusted)

Optimizing (50 restarts, 32 candidates) ...

========================================================================
PORTFOLIO OPTIMIZER  --  Regime: RY=HIGH + BAA10Y=TIGHT
========================================================================
  Universe       : top 50 screen candidates + GC_F
  Matched dates  : 1413  MODERATE
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
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/yfinance/scrapers/analysis.py:135: Pandas4Warning: The inplace keyword in DataFrame.set_index is deprecated and will be removed in a future version (PDEP-8).
See https://pandas.pydata.org/docs/dev/whatsnew/v3.1.0.html#deprecation-inplace for more details.
  df.set_index('quarter', inplace=True)
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/yfinance/scrapers/analysis.py:135: Pandas4Warning: The inplace keyword in DataFrame.set_index is deprecated and will be removed in a future version (PDEP-8).
See https://pandas.pydata.org/docs/dev/whatsnew/v3.1.0.html#deprecation-inplace for more details.
  df.set_index('quarter', inplace=True)
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/yfinance/scrapers/analysis.py:135: Pandas4Warning: The inplace keyword in DataFrame.set_index is deprecated and will be removed in a future version (PDEP-8).
See https://pandas.pydata.org/docs/dev/whatsnew/v3.1.0.html#deprecation-inplace for more details.
  df.set_index('quarter', inplace=True)
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/yfinance/scrapers/analysis.py:135: Pandas4Warning: The inplace keyword in DataFrame.set_index is deprecated and will be removed in a future version (PDEP-8).
See https://pandas.pydata.org/docs/dev/whatsnew/v3.1.0.html#deprecation-inplace for more details.
  df.set_index('quarter', inplace=True)
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/yfinance/scrapers/analysis.py:135: Pandas4Warning: The inplace keyword in DataFrame.set_index is deprecated and will be removed in a future version (PDEP-8).
See https://pandas.pydata.org/docs/dev/whatsnew/v3.1.0.html#deprecation-inplace for more details.
  df.set_index('quarter', inplace=True)
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/yfinance/scrapers/analysis.py:135: Pandas4Warning: The inplace keyword in DataFrame.set_index is deprecated and will be removed in a future version (PDEP-8).
See https://pandas.pydata.org/docs/dev/whatsnew/v3.1.0.html#deprecation-inplace for more details.
  df.set_index('quarter', inplace=True)
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/yfinance/scrapers/analysis.py:135: Pandas4Warning: The inplace keyword in DataFrame.set_index is deprecated and will be removed in a future version (PDEP-8).
See https://pandas.pydata.org/docs/dev/whatsnew/v3.1.0.html#deprecation-inplace for more details.
  df.set_index('quarter', inplace=True)
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/yfinance/scrapers/analysis.py:135: Pandas4Warning: The inplace keyword in DataFrame.set_index is deprecated and will be removed in a future version (PDEP-8).
See https://pandas.pydata.org/docs/dev/whatsnew/v3.1.0.html#deprecation-inplace for more details.
  df.set_index('quarter', inplace=True)
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/yfinance/scrapers/analysis.py:135: Pandas4Warning: The inplace keyword in DataFrame.set_index is deprecated and will be removed in a future version (PDEP-8).
See https://pandas.pydata.org/docs/dev/whatsnew/v3.1.0.html#deprecation-inplace for more details.
  df.set_index('quarter', inplace=True)
AVGO peer valuation snapshot -- 2026-10-26

Ticker        Price   TTM EPS   Fwd EPS  Fwd/Trail  Impl.growth   Fwd P/E   PEG(1y)
-----------------------------------------------------------------------------------
MU          $877.55    $75.51   $206.89      2.74x        +174%     4.24x      0.02
AMD         $516.79     $5.76    $15.76      2.74x        +174%    32.79x      0.19
NVDA        $210.96     $7.01    $15.91      2.27x        +127%    13.26x      0.10
MRVL        $228.51     $3.30     $7.33      2.22x        +122%    31.18x      0.26
AVGO*       $321.68     $9.76    $19.43      1.99x         +99%    16.55x      0.17
ASML      $1,571.80    $33.89    $55.93      1.65x         +65%    28.10x      0.43
ANET        $172.37     $3.46     $5.22      1.51x         +51%    33.01x      0.65
TSM         $418.51    $15.54    $23.39      1.50x         +50%    17.90x      0.35
QCOM        $175.91    $11.36    $10.19      0.90x         -10%    17.26x       n/a

* = AVGO

AVGO rank -- growth ratio (highest first): 5 of 9
AVGO rank -- forward P/E (cheapest first): 3 of 9
AVGO rank -- PEG(1y) (cheapest first)    : 3 of 9

Note: PEG(1y) is built on a 1-year forward growth estimate, not the conventional 5-year estimate PEG ratios (including yfinance's own pegRatio field, deliberately not fetched here) normally use. MEMORY.md's 2026-07-06 entry recorded AVGO's PEG as 0.41 alongside a 19.4x forward P/E -- those two never reconciled on the same basis (19.4 / 139% implied growth = 0.14, not 0.41). PEG(1y) above is internally consistent but not comparable to that historical figure or to any 5-year PEG from elsewhere.

AVGO and peers vs their OWN stored history (low percentile = cheap for that name)
Ticker     Fwd P/E   pctile   obs
AMD         32.79x       --     6
ANET        33.01x       --     6
ASML        28.10x       --     6
AVGO        16.55x       --     6
MRVL        31.18x       --     6
MU           4.24x       --     6
NVDA        13.26x       --     6
QCOM        17.26x       --     6
TSM         17.90x       --     6
  accruing -- 6/60 observations needed before a percentile is shown. Started 2026-10-18; cannot be backfilled.
