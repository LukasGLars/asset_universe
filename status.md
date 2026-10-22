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
  Gold                     234     782 kr   183,092 kr  16.7%  20.0%   -3.3%
  Silver                     -     519 kr         0 kr   0.0%   0.0%   +0.0%
  Eli Lilly                 19  12,591 kr   239,233 kr  21.8%  20.0%   +1.8%
  Walmart                    -   1,167 kr         0 kr   0.0%   0.0%   +0.0%
  Cameco                     -     813 kr         0 kr   0.0%   0.0%   +0.0%
  Vertiv                     -   2,102 kr         0 kr   0.0%   0.0%   +0.0%
  Broadcom                  65   3,347 kr   217,561 kr  19.9%  20.0%   -0.1%
  Howmet Aerospace           -   2,062 kr         0 kr   0.0%   0.0%   +0.0%
  Spiltan Räntefond     738.53     153 kr   112,818 kr  10.3%   0.0%  +10.3%
  War Chest                  -     manual        19 kr   0.0%   0.0%   +0.0%
  Reactor Core Cash          -     manual    48,997 kr   4.5%  10.0%   -5.5%
  Virtune Bitcoin          193     134 kr    25,881 kr   2.4%   2.5%   -0.1%
  Virtune Staked ETH       391      57 kr    22,103 kr   2.0%   2.5%   -0.5%
  LF Global Index       397.84     619 kr   246,070 kr  22.5%  25.0%   -2.5%
------------------------------------------------------------------------------
  TPV                                        1,095,775 kr
    Reactor Core            688,883 kr  (62.9%)   target 60.0%  drift +2.9%
    Global Index            246,070 kr  (22.5%)   target 25.0%  drift -2.5%
    Home Base               112,818 kr  (10.3%)   target 10.0%  drift +0.3%
    Crypto Sleeve            47,985 kr  ( 4.4%)   target  5.0%  drift -0.6%
    War Chest                    19 kr  ( 0.0%)   target  0.0%  drift +0.0%

==============================================================
FI@50 PACE TRACKER
==============================================================
  Start  (2025-07-21)  :       925,983 kr
  Now                     :     1,095,775 kr
  Threshold (2026 kr)     :    16,150,000 kr   (indexed 2.0%/yr)
  Trigger now             :    16,409,489 kr
  Trigger @ horizon       :    20,798,454 kr
  Years remaining         :  12.0

  AWAR (trailing)         :  +14.4%
  Required CAGR           :  +25.3%
  Status                  :  BEHIND  (-10.9% margin)

  Projected @ AWAR        :     7,616,303 kr
  vs target               :   -13,182,151 kr  (deficit)

  Scenario         CAGR       Projected     FI date   (incl. 6,000 kr/mo contributions)
  ------------------------------------------------------------------------
  Bear           +10%       5,043,730 kr       ~2056
  Conservative   +15%       8,079,573 kr       ~2046
  Base           +20%      12,845,062 kr       ~2042
  Current AWAR   +14%       7,616,303 kr       ~2047
  Bull           +30%      31,457,181 kr       ~2037

==============================================================
MACRO REGIME
==============================================================

  Feature                 Value   Regime  
  ------------------------------------------
  Nominal 10Y             5.12%   HIGH
  Real Yield             +2.77%   HIGH  ^
  Breakeven               2.37%   HIGH
  HY OAS                327 bps   WIDE
  IG Credit               1.44%   TIGHT
  Curve 10Y-3M          +88 bps   MID
  Curve 10Y-2Y          +32 bps   LOW
  SE 10Y                  3.19%   MID
  USD                     121.4   STRONG

  HY 20d delta  : +54 bps  (widening)
  Confidence    : UNCERTAIN
  Data through  : 2026-10-21

==============================================================
PORTFOLIO SIGNALS
==============================================================

  Base: ry=HIGH  nominal_10y=HIGH  baa10y=TIGHT  usd=STRONG

  Position          Wt    21d   63d   63d med  252d med  W252     N  Note
  ----------------------------------------------------------------------
  Gold           16.7%    LOW   MID     +0.7%     +0.7%   61%    69  
  Silver          0.0%    LOW   MID     +0.6%     +0.6%   61%    69  
  Eli Lilly      21.8%   HIGH   MID     +0.4%     +0.4%   61%    44  
  Walmart         0.0%   HIGH  HIGH     +0.8%     +0.8%   61%   172  
  Cameco          0.0%    LOW   LOW     +1.8%     +1.8%   66%   118  
  Vertiv          0.0%    LOW   LOW     -1.1%     -1.1%   46%   118  
  Broadcom       19.9%    LOW   LOW     +1.0%     +1.0%   62%   124  

==============================================================
TACTICAL RULES
==============================================================

  Silver GSR Tactical
    GSR now        : 71.78  (as of 2026-10-21)
    60d GSR peak   : 73.99
    Fall from peak : 3.0%  (no (need >=5% fall for signal))
    T1 threshold   : 83.36  |  T2: 86.45  |  Exit: 62.56
    Signal         : INACTIVE
    Action         : No action -- hold base

  AVGO Trend Diagnostic  [guard RETIRED as a rotation rule -- PR #88]
    AVGO now       : $337.80  (as of 2026-10-21)
    200d SMA       : $367.53  (-8.1% gap)
    5d ROC         : -2.4%  (gap-down buy level: -10%)
    Signal         : DEFENSIVE  (trigger: MA)  -- informational, no rotation
    LLY stress     : inactive  ($1270.75 vs 200d SMA $1081.90, 5d ROC +5.1%)
    Joint stress   : inactive  -- retired alongside the guard, shown for continuity only
    Action         : No action -- guard retired as a rotation rule (see PR #88); reading is diagnostic only

  AVGO Volatility-Targeted Weight  [RETIRED 2026-08-18 -- diagnostic only]
    Trailing 21d vol : 35.9% (annualized)
    Long-run avg vol : 35.4% (annualized)
    Scalar           : 0.98x  (clipped to [0.30x, 1.30x])
    Would-be weights : Gold 25.3%  AVGO 39.3%  LLY 35.4%
    NOT ACTED ON     : routing + rebalance use the static base (see MEMORY.md)

  AVGO Earnings Checkpoint
    Latest qtr EPS (actual vs est.): $3.32 vs $3.24  (+2.5% surprise)
    TTM EPS (non-GAAP actual)  : $9.76
    Forward EPS (+1yr est.)    : $19.40
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
    Basket-crash   : none eligible today

  Crypto Trend Sleeve
    Bitcoin (BTC-USD)  $84,243  (as of 2026-10-21)
      Target       : 100%  = 27 225 kr of 27 225 kr
      MA50         : LONG (MA $79,318, flat below $77,732)
      MA100        : LONG (MA $71,313, flat below $69,887)
      MA200        : LONG (MA $72,936, flat below $71,477)
      Last change  : 2026-08-21 -> 100%
    Ethereum (ETH-USD)  $2,475  (as of 2026-10-21)
      Target       : 100%  = 27 225 kr of 27 225 kr
      MA50         : LONG (MA $2,472, flat below $2,423)
      MA100        : LONG (MA $2,126, flat below $2,084)
      MA200        : LONG (MA $2,184, flat below $2,140)
      Last change  : 2026-08-21 -> 100%

==============================================================
NEXT CONTRIBUTION
==============================================================

  Next kr        -> Reactor Core Cash
    Current wt (of Reactor Core) : 5.0%
    Target wt (config)           : 10.0%
    Gap                          : +5.0%
    Gate                         : OPEN
    Note: not funded by contributions -- Virtune Bitcoin, Virtune Staked ETH
    Denominator: 982,938 kr (7 positions carrying a target)

  Rebalance Check  [existing capital, band: 10pp absolute gap to target]
    Broadcom status: HOLD  (22.1% actual vs 20.0% target, gap -2.1%)
    Eli Lilly status: HOLD  (24.3% actual vs 20.0% target, gap -4.3%)
    Gold status: HOLD  (18.6% actual vs 20.0% target, gap +1.4%)
    LF Global Index status: HOLD  (25.0% actual vs 25.0% target, gap -0.0%)
    Reactor Core Cash status: HOLD  (5.0% actual vs 10.0% target, gap +5.0%)
    Virtune Bitcoin status: HOLD  (2.6% actual vs 2.5% target, gap -0.1%)
    Virtune Staked ETH status: HOLD  (2.2% actual vs 2.5% target, gap +0.3%)

  Reactor Core Cash
    Balance        : 48,997 kr  (5.0% vs 10% target)
    Shortfall      : 49,297 kr below target
    Action         : none -- hold. This is the dip sleeve; the AVGO/LLY 5d-ROC trigger spends it, not a contribution.

==============================================================
  Regime check (2026-10-21): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)
Building regime labels ...
  Conditions    : {'ry_regime': 'HIGH', 'baa10y_regime': 'TIGHT'}
  Matched dates : 1411  (2004-05-07 - 2026-10-21)  MODERATE

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
  Matched dates  : 1411  MODERATE
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
AVGO peer valuation snapshot -- 2026-10-22

Ticker        Price   TTM EPS   Fwd EPS  Fwd/Trail  Impl.growth   Fwd P/E   PEG(1y)
-----------------------------------------------------------------------------------
MU          $873.94    $75.51   $206.85      2.74x        +174%     4.23x      0.02
AMD         $511.72     $5.76    $15.76      2.74x        +174%    32.46x      0.19
NVDA        $213.46     $7.01    $15.91      2.27x        +127%    13.41x      0.11
MRVL        $224.43     $3.30     $7.33      2.22x        +122%    30.62x      0.25
AVGO*       $322.73     $9.76    $19.40      1.99x         +99%    16.64x      0.17
ASML      $1,592.12    $33.89    $55.93      1.65x         +65%    28.47x      0.44
ANET        $171.71     $3.46     $5.22      1.51x         +51%    32.88x      0.65
TSM         $414.35    $15.54    $23.39      1.50x         +50%    17.72x      0.35
QCOM        $174.88    $11.36    $10.19      0.90x         -10%    17.16x       n/a

* = AVGO

AVGO rank -- growth ratio (highest first): 5 of 9
AVGO rank -- forward P/E (cheapest first): 3 of 9
AVGO rank -- PEG(1y) (cheapest first)    : 3 of 9

Note: PEG(1y) is built on a 1-year forward growth estimate, not the conventional 5-year estimate PEG ratios (including yfinance's own pegRatio field, deliberately not fetched here) normally use. MEMORY.md's 2026-07-06 entry recorded AVGO's PEG as 0.41 alongside a 19.4x forward P/E -- those two never reconciled on the same basis (19.4 / 139% implied growth = 0.14, not 0.41). PEG(1y) above is internally consistent but not comparable to that historical figure or to any 5-year PEG from elsewhere.

AVGO and peers vs their OWN stored history (low percentile = cheap for that name)
Ticker     Fwd P/E   pctile   obs
AMD         32.46x       --     4
ANET        32.88x       --     4
ASML        28.47x       --     4
AVGO        16.64x       --     4
MRVL        30.62x       --     4
MU           4.23x       --     4
NVDA        13.41x       --     4
QCOM        17.16x       --     4
TSM         17.72x       --     4
  accruing -- 4/60 observations needed before a percentile is shown. Started 2026-10-18; cannot be backfilled.
