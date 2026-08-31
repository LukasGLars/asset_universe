==============================================================
REACTOR CORE -- PORTFOLIO SNAPSHOT
==============================================================
Position                Shares      Price    Value SEK     Wt
--------------------------------------------------------------
  Gold                     304     847 kr   257,451 kr  23.9%
  Silver                     -     603 kr         0 kr   0.0%
  Eli Lilly                 31  11,269 kr   349,345 kr  32.4%
  Walmart                    -     989 kr         0 kr   0.0%
  Cameco                     -     959 kr         0 kr   0.0%
  Vertiv                     -   2,466 kr         0 kr   0.0%
  Broadcom                  77   3,538 kr   272,439 kr  25.3%
  Howmet Aerospace           -   2,541 kr         0 kr   0.0%
  Spiltan Räntefond          -     manual   199,038 kr  18.5%
  War Chest                  -     manual        27 kr   0.0%
  Reactor Core Cash          -     manual        24 kr   0.0%
--------------------------------------------------------------
  TPV                                        1,078,325 kr
    Reactor Core            879,260 kr  (81.5%)   target 85.0%  drift -3.5%
    Home Base               199,038 kr  (18.5%)   target 15.0%  drift +3.5%
    War Chest                    27 kr  ( 0.0%)   target  0.0%  drift +0.0%

==============================================================
FI@50 PACE TRACKER
==============================================================
  Start  (2025-07-21)  :       925,983 kr
  Now                     :     1,078,325 kr
  Threshold (2026 kr)     :    16,150,000 kr   (indexed 2.0%/yr)
  Trigger now             :    16,363,291 kr
  Trigger @ horizon       :    20,798,454 kr
  Years remaining         :  12.1

  AWAR (trailing)         :  +14.7%
  Required CAGR           :  +25.1%
  Status                  :  BEHIND  (-10.4% margin)

  Projected @ AWAR        :     7,918,117 kr
  vs target               :   -12,880,337 kr  (deficit)

  Scenario         CAGR       Projected     FI date   (incl. 6,000 kr/mo contributions)
  ------------------------------------------------------------------------
  Bear           +10%       5,067,647 kr       ~2056
  Conservative   +15%       8,157,534 kr       ~2046
  Base           +20%      13,034,528 kr       ~2042
  Current AWAR   +15%       7,918,117 kr       ~2047
  Bull           +30%      32,246,346 kr       ~2037

==============================================================
MACRO REGIME
==============================================================

  Feature                 Value   Regime  
  ------------------------------------------
  Nominal 10Y             4.67%   HIGH
  Real Yield             +2.34%   HIGH  ^
  Breakeven               2.31%   MID
  HY OAS                263 bps   TIGHT
  IG Credit               1.60%   TIGHT
  Curve 10Y-3M          +83 bps   MID
  Curve 10Y-2Y          +39 bps   LOW
  SE 10Y                   nan%   --
  USD                     118.1   STRONG

  HY 20d delta  : -21 bps  (tightening)
  Confidence    : HIGH
  Data through  : 2026-08-28

==============================================================
PORTFOLIO SIGNALS
==============================================================

  Base: ry=HIGH  nominal_10y=HIGH  baa10y=TIGHT  usd=STRONG

  Position          Wt    21d   63d   63d med  252d med  W252     N  Note
  ----------------------------------------------------------------------
  Gold           23.9%   HIGH   MID     -0.2%     -0.2%   38%    45  
  Silver          0.0%   HIGH   LOW     +3.6%     +4.0%   70%   558  ~base fallback
  Eli Lilly      32.4%    MID   MID     +0.2%     -0.6%   42%   556  ~base fallback
  Walmart         0.0%    LOW   LOW     +1.0%     +1.0%   61%    79  
  Cameco          0.0%   HIGH   LOW     -1.8%     -1.8%   43%   556  ~base fallback
  Vertiv          0.0%   HIGH   LOW     +0.1%     -2.4%   44%   556  ~base fallback
  Broadcom       25.3%    LOW   LOW     +1.2%     +1.2%   62%   104  

==============================================================
TACTICAL RULES
==============================================================

  Silver GSR Tactical
    GSR now        : 67.14  (as of 2026-08-28)
    60d GSR peak   : 71.56
    Fall from peak : 6.2%  (yes)
    T1 threshold   : 83.36  |  T2: 86.45  |  Exit: 62.56
    Signal         : INACTIVE
    Action         : No action -- hold base

  AVGO Trend Diagnostic  [guard RETIRED as a rotation rule -- PR #88]
    AVGO now       : $368.79  (as of 2026-08-28)
    200d SMA       : $368.53  (+0.1% gap)
    5d ROC         : +0.1%  (gap-down buy level: -10%)
    Signal         : BASE  (trigger: none)  -- informational, no rotation
    LLY stress     : inactive  ($1174.61 vs 200d SMA $1058.10, 5d ROC -6.4%)
    Joint stress   : inactive  -- retired alongside the guard, shown for continuity only
    Action         : No action -- guard retired as a rotation rule (see PR #88); reading is diagnostic only

  AVGO Volatility-Targeted Weight  [RETIRED 2026-08-18 -- diagnostic only]
    Trailing 21d vol : 43.0% (annualized)
    Long-run avg vol : 35.4% (annualized)
    Scalar           : 0.82x  (clipped to [0.30x, 1.30x])
    Would-be weights : Gold 28.0%  AVGO 32.9%  LLY 39.2%
    NOT ACTED ON     : routing + rebalance use the static base (see MEMORY.md)

  AVGO Earnings Checkpoint
    Latest qtr EPS (actual vs est.): $2.44 vs $2.40  (+1.7% surprise)
    TTM EPS (non-GAAP actual)  : $8.13
    Forward EPS (+1yr est.)    : $19.51
    Fwd/Trail ratio (normalized): 2.40x  (mid-pack vs. real AI/semi peers; corrected 2026-07-06 from a GAAP/non-GAAP mismatched 3.22x)
    Revenue (latest qtr, actual): $22.19B  (TTM YoY: +32.3%)
    Next-qtr revenue consensus : $29.43B (implied YoY +84.5%)
    Next earnings  : 2026-09-02
    Reminder       : DUE
    Latest quarter : 2026-04-30
    Beat streak    : 4
    Guidance trend : revising up  (+1yr estimate vs. 90 days ago)

  LLY Earnings Checkpoint
    Latest qtr EPS (actual vs est.): $8.38 vs $6.58  (+27.3% surprise)
    TTM EPS (non-GAAP actual)  : $31.49
    Forward EPS (+1yr est.)    : $47.23
    Fwd/Trail ratio (normalized): 1.50x  (baseline established 2026-07-06)
    Revenue (latest qtr, actual): $22.97B  (TTM YoY: +49.6%)
    Next-qtr revenue consensus : $22.23B (implied YoY +26.3%)
    Next earnings  : 2026-10-29
    Reminder       : not_due
    Latest quarter : 2026-06-30
    Beat streak    : 4
    Guidance trend : revising up  (+1yr estimate vs. 90 days ago)

  Opportunistic Sleeve
    Status         : CLOSED (0/1 position)
    Best candidate : HOOD (Robinhood Markets, Inc.)  $104.26  (ext +2.9%, 21d med +4.0%, ave +5.3%, win 59.4%, div THIN, drift +0.4%)
    Plan           : buy near $104.26, hold ~21d, stop = MA50-5% then trails 3% once +5% gain
    Open           : run_entry_screen.py --open HOOD <fill_price> <shares> <capital_sek>
    VIX review     : 14.43  (27% percentile, flat) -- for review, not a gate
    Basket-crash   : none eligible today

==============================================================
NEXT CONTRIBUTION
==============================================================

  Next kr        -> Broadcom (AVGO)
    Current wt (of Reactor Core) : 31.0%
    Target wt (current regime)   : 40.0%
    Gap                          : +9.0%
    Gate                         : OPEN
    Note: Silver excluded -- funded by its own GSR trigger, not new contributions

  AVGO Rebalance Check  [existing capital, band: 10%]
    Gold status: HOLD  (29.3% actual vs 25.0% target, gap -4.3%)
    AVGO status: HOLD  (31.0% actual vs 40.0% target, gap +9.0%)
    LLY status: HOLD  (39.7% actual vs 35.0% target, gap -4.7%)

  Idle Reactor Core Cash
    Uninvested     : 24 kr  (0.0% of Reactor Core)
    Action         : deploy -> Broadcom (AVGO)  (~0 shares at 3,538 kr)

==============================================================
  Regime check (2026-08-28): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)
Building regime labels ...
  Conditions    : {'ry_regime': 'HIGH', 'baa10y_regime': 'TIGHT'}
  Matched dates : 1400  (2004-05-07 - 2026-08-28)  MODERATE

Computing capped 252d distributions for 51 candidates ...
  SNDK      hist=2yr  (below min 10yr, skipped)
  APP       hist=5yr  (below min 10yr, skipped)
  HOOD      hist=5yr  (below min 10yr, skipped)
  PLTR      hist=6yr  (below min 10yr, skipped)
  CVNA      hist=9yr  (below min 10yr, skipped)
  GEV       hist=2yr  (below min 10yr, skipped)
  LITE      N= 630  mu= +49.5%  sigma= 60.6%  hist=11yr  [SINGLE]
  VRT       hist=8yr  (below min 10yr, skipped)
  HWM       hist=10yr  (below min 10yr, skipped)
  AVGO      N= 630  mu= +27.7%  sigma= 36.1%  hist=17yr  [SINGLE]
  VST       hist=10yr  (below min 10yr, skipped)
  IBKR      N= 743  mu=  +6.9%  sigma= 19.3%  hist=19yr  [THIN]
  TRGP      N= 630  mu=  +3.4%  sigma= 16.4%  hist=16yr  [SINGLE]
  ANET      N= 630  mu= +19.9%  sigma= 24.2%  hist=12yr  [SINGLE]
  DECK      N=1269  mu= +31.0%  sigma= 53.8%  hist=27yr  [ROBUST]
  NRG       N=1269  mu= +21.0%  sigma= 27.8%  hist=23yr  [ROBUST]
  PWR       N=1269  mu= +19.9%  sigma= 27.4%  hist=27yr  [ROBUST]
  STLD      N=1269  mu= +15.3%  sigma= 30.3%  hist=27yr  [ROBUST]
  CF        excluded (see EXCLUDE_TICKERS)
  BKNG      N=1269  mu= +32.5%  sigma= 47.4%  hist=27yr  [ROBUST]
  CMI       N=1269  mu= +25.0%  sigma= 29.2%  hist=27yr  [ROBUST]
  GM        N= 630  mu=  +7.4%  sigma= 12.9%  hist=16yr  [SINGLE]
  EXV1.DE   no data
  CIEN      N=1269  mu= +22.3%  sigma= 28.2%  hist=27yr  [ROBUST]
  FOXA      hist=7yr  (below min 10yr, skipped)
  CFG       N= 630  mu= +14.7%  sigma= 13.7%  hist=12yr  [SINGLE]
  CEG       hist=5yr  (below min 10yr, skipped)
  WDC       N=1269  mu= +22.5%  sigma= 39.0%  hist=27yr  [ROBUST]
  PHAG.L    no data
  DASH      hist=6yr  (below min 10yr, skipped)
  GS        N=1269  mu= +12.7%  sigma= 23.4%  hist=27yr  [ROBUST]
  TPR       N=1269  mu= +18.6%  sigma= 31.1%  hist=26yr  [ROBUST]
  NVDA      N=1269  mu= +23.5%  sigma= 32.4%  hist=27yr  [ROBUST]
  RL        N=1269  mu= +14.8%  sigma= 26.3%  hist=27yr  [ROBUST]
  COHR      max_up=71%  (M&A / corporate event detected, skipped)
  ABB.ST    no data
  DELL      N= 630  mu=  +4.5%  sigma= 18.4%  hist=10yr  [SINGLE]
  FOX       hist=7yr  (below min 10yr, skipped)
  EME       N=1269  mu= +16.1%  sigma= 26.6%  hist=27yr  [ROBUST]
  GRMN      N=1269  mu= +30.5%  sigma= 31.2%  hist=26yr  [ROBUST]
  TEL2-B.ST  no data
  FIX       N=1269  mu= +20.7%  sigma= 27.9%  hist=27yr  [ROBUST]
  FTNT      N= 630  mu=  -8.8%  sigma= 10.3%  hist=17yr  [SINGLE]
  FSLR      N= 864  mu= +23.6%  sigma= 53.3%  hist=20yr  [MODERATE]
  APH       N=1269  mu= +16.8%  sigma= 24.3%  hist=27yr  [ROBUST]
  PM        N= 630  mu= +10.8%  sigma= 13.7%  hist=18yr  [SINGLE]
  AAPL      N=1269  mu= +19.6%  sigma= 28.6%  hist=27yr  [ROBUST]
  4GLD.DE   no data
  CRWD      hist=7yr  (below min 10yr, skipped)
  ETR       N=1269  mu= +13.3%  sigma= 18.5%  hist=27yr  [ROBUST]
  GC_F      N=1269  mu=  +9.8%  sigma= 11.5%  hist=26yr  [ROBUST]

Cross-sectional prior mu : +18.2%  (shrinkage target)
Shrinkage lambda         : 100  (asset needs N>>100 to be fully trusted)

Optimizing (50 restarts, 30 candidates) ...

========================================================================
PORTFOLIO OPTIMIZER  --  Regime: RY=HIGH + BAA10Y=TIGHT
========================================================================
  Universe       : top 50 screen candidates + GC_F
  Matched dates  : 1400  MODERATE
  Shrinkage      : lambda=100  prior=+18.2%

  Ticker     Weight   mu(raw)   mu(shr)    sigma      N   Hist       Div
  -----------------------------------------------------------------
  GRMN        31.3%    +30.5%    +29.6%    31.2%   1269    26yr    ROBUST
  LITE        29.5%    +49.5%    +37.4%    60.6%    630    11yr    SINGLE
  BKNG        21.8%    +32.5%    +31.4%    47.4%   1269    27yr    ROBUST
  DECK        12.3%    +31.0%    +30.1%    53.8%   1269    27yr    ROBUST
  GC_F         5.0%     +9.8%    +10.4%    11.5%   1269    26yr    ROBUST  [gold]

  Active positions   : 5  (weight >= 1%)
  Equal-weight g(w)  : +18.4%  (benchmark)
  Optimized g(w)     : +28.5%

  WARNING: only 5 active positions — below recommended minimum of 6.
  Consider reducing MAX_W or increasing N_CANDIDATES.

  NOTE: g(w) is an approximation. mu/sigma are regime-conditional,
  capped at regime end. Shrinkage applied for short-history assets.
========================================================================
AVGO peer valuation snapshot -- 2026-08-31

Ticker        Price   TTM EPS   Fwd EPS  Fwd/Trail  Impl.growth   Fwd P/E   PEG(1y)
-----------------------------------------------------------------------------------
MU          $932.86    $45.12   $155.03      3.44x        +244%     6.02x      0.02
AMD         $465.58     $5.76    $15.45      2.68x        +168%    30.13x      0.18
AVGO*       $368.79     $8.13    $19.51      2.40x        +140%    18.91x      0.14
NVDA        $217.55     $7.01    $15.31      2.18x        +118%    14.21x      0.12
MRVL        $216.62     $3.30     $6.64      2.01x        +101%    32.60x      0.32
ASML      $1,696.16    $27.56    $51.69      1.88x         +88%    32.81x      0.37
TSM         $417.52    $13.86    $21.78      1.57x         +57%    19.17x      0.34
ANET        $195.38     $3.46     $5.16      1.49x         +49%    37.87x      0.77
QCOM        $164.19    $11.36    $10.20      0.90x         -10%    16.09x       n/a

* = AVGO

AVGO rank -- growth ratio (highest first): 3 of 9
AVGO rank -- forward P/E (cheapest first): 4 of 9
AVGO rank -- PEG(1y) (cheapest first)    : 3 of 9

Note: PEG(1y) is built on a 1-year forward growth estimate, not the conventional 5-year estimate PEG ratios (including yfinance's own pegRatio field, deliberately not fetched here) normally use. MEMORY.md's 2026-07-06 entry recorded AVGO's PEG as 0.41 alongside a 19.4x forward P/E -- those two never reconciled on the same basis (19.4 / 139% implied growth = 0.14, not 0.41). PEG(1y) above is internally consistent but not comparable to that historical figure or to any 5-year PEG from elsewhere.
