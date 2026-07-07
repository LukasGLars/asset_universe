==============================================================
REACTOR CORE -- PORTFOLIO SNAPSHOT
==============================================================
Position                Shares      Price    Value SEK     Wt
--------------------------------------------------------------
  Gold                     304     777 kr   236,351 kr  21.5%
  Silver                    66     543 kr    35,815 kr   3.3%
  Eli Lilly                 14  11,569 kr   161,964 kr  14.7%
  Walmart                  126   1,067 kr   134,403 kr  12.2%
  Cameco                    93     940 kr    87,413 kr   8.0%
  Vertiv                     -   3,070 kr         0 kr   0.0%
  Broadcom                  49   3,604 kr   176,620 kr  16.1%
  Howmet Aerospace          11   2,679 kr    29,470 kr   2.7%
  Spiltan Räntefond          -     manual   234,623 kr  21.4%
  War Chest                  -     manual     1,959 kr   0.2%
--------------------------------------------------------------
  TPV                                        1,091,425 kr
    Reactor Core            862,037 kr  (79%)
    Home Base               234,623 kr  (21%)
    War Chest                 1,959 kr  (0%)

==============================================================
FI@50 PACE TRACKER
==============================================================
  Start  (2025-07-21)  :       925,983 kr
  Now                     :     1,091,425 kr
  Target (FI@50)          :    12,934,706 kr
  Years remaining         :  11.0

  AWAR (trailing)         :  +18.7%
  Required CAGR           :  +22.2%
  Status                  :  BEHIND  (-3.5% margin)

  Projected @ AWAR        :     9,589,700 kr
  vs target               :    -3,345,006 kr  (deficit)

  Scenario         CAGR       Projected     FI date   (incl. 6,000 kr/mo contributions)
  ------------------------------------------------------------------------
  Bear           +10%       4,539,088 kr       ~2047
  Conservative   +15%       7,011,231 kr       ~2041
  Base           +20%      10,746,995 kr       ~2038
  Current AWAR   +19%       9,589,700 kr       ~2039
  Bull           +30%      24,507,193 kr       ~2035

==============================================================
MACRO REGIME
==============================================================

  Feature                 Value   Regime  
  ------------------------------------------
  Nominal 10Y             4.49%   HIGH
  Real Yield             +2.26%   HIGH  ^
  Breakeven               2.24%   MID
  HY OAS                274 bps   TIGHT
  IG Credit               1.54%   TIGHT
  Curve 10Y-3M          +61 bps   LOW
  Curve 10Y-2Y          +35 bps   LOW
  SE 10Y                   nan%   --
  USD                     120.7   STRONG

  HY 20d delta  : -2 bps  (flat)
  Confidence    : HIGH
  Data through  : 2026-07-06

==============================================================
PORTFOLIO SIGNALS
==============================================================

  Base: ry=HIGH  nominal_10y=HIGH  baa10y=TIGHT  usd=STRONG

  Position          Wt    21d   63d   63d med  252d med  W252     N  Note
  ----------------------------------------------------------------------
  Gold           21.5%    LOW   LOW     +0.7%     +0.7%   75%    63  
  Silver          3.3%    LOW   LOW     +2.3%     +2.3%   84%    31  
  Eli Lilly      14.7%   HIGH  HIGH     -0.2%     -0.2%   47%   146  
  Walmart        12.2%    LOW   LOW     +0.5%     +0.5%   59%    63  
  Cameco          8.0%    LOW   LOW     +2.0%     +2.0%   67%    82  
  Vertiv          0.0%    LOW   MID     -0.0%     -0.0%   49%    75  
  Broadcom       16.1%    LOW  HIGH     -0.1%     -0.1%   50%    70  

==============================================================
TACTICAL RULES
==============================================================

  Silver GSR Tactical
    GSR now        : 67.10  (as of 2026-07-06)
    60d GSR peak   : 69.14
    Fall from peak : 2.9%  (no (need >=5% fall for signal))
    T1 threshold   : 83.36  |  T2: 86.45  |  Exit: 62.56
    Signal         : INACTIVE
    Action         : No action -- hold base

  AVGO 200d Guard
    AVGO now       : $373.90  (as of 2026-07-06)
    200d SMA       : $360.28  (+3.8% gap)
    5d ROC         : +2.4%  (crash threshold: -10%)
    Signal         : BASE  (trigger: none)
    LLY stress     : inactive  ($1200.06 vs 200d SMA $984.74, 5d ROC -0.7%)
    Joint stress   : inactive  (guard AND LLY stress both active)
    Action         : Hold base (Gold 25%, AVGO 55%, LLY 20%)

  AVGO Earnings Checkpoint
    TTM EPS (non-GAAP actual)  : $8.13
    Forward EPS (+1yr est.)    : $19.40
    Fwd/Trail ratio (normalized): 2.39x  (peer range 1.17-1.41x; corrected 2026-07-06 from a GAAP/non-GAAP mismatched 3.22x)
    Next earnings  : 2026-09-03
    Reminder       : not_due
    Latest quarter : 2026-04-30
    Beat streak    : 4
    Guidance trend : revising up  (+1yr estimate vs. 90 days ago)
    Action         : after the print, check actual AI revenue/EPS against the
                     $56B FY26 / $100B FY27 guided path. Meaningfully short of
                     trajectory -> revisit conviction, even if price > SMA200.
    MANUAL REVIEW  : AI revenue pace vs. guided path and Anthropic/OpenAI
                     contract-timing commentary aren't in any API -- read the
                     actual release/call. Beat streak + guidance trend above are
                     automated pre-checks only, not a substitute for those two.

  LLY Earnings Checkpoint
    TTM EPS (non-GAAP actual)  : $29.42
    Forward EPS (+1yr est.)    : $44.47
    Fwd/Trail ratio (normalized): 1.51x  (baseline established 2026-07-06; in line with peer range 1.17-1.41x)
    Next earnings  : 2026-08-05
    Reminder       : not_due
    Latest quarter : 2026-03-31
    Beat streak    : 4
    Guidance trend : revising up  (+1yr estimate vs. 90 days ago)
    Action         : after the print, check GLP-1/AI-healthcare growth against
                     guidance. Baseline established today -- compare future ratio
                     prints against this.

  Opportunistic Sleeve
    Status         : CLOSED (0/1 position)
    Best candidate : RL (Ralph Lauren Corporation)  (ext +6.0%, 27d med +2.0%, div ROBUST, pre-entry tripwires PASSED) -- run run_entry_screen.py for full detail
    VIX review     : 15.57  (35% percentile, falling) -- for review, not a gate

==============================================================
NEXT CONTRIBUTION
==============================================================

  Next kr        -> Broadcom (AVGO)
    Current wt (of Reactor Core) : 20.5%
    Target wt (current regime)   : 55.0%
    Gap                          : +34.5%
    Gate                         : OPEN
    Note: Silver excluded -- funded by its own GSR trigger, not new contributions

==============================================================
  Regime check (2026-07-06): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)
Building regime labels ...
  Conditions    : {'ry_regime': 'HIGH', 'baa10y_regime': 'TIGHT'}
  Matched dates : 1386  (2004-05-07 - 2026-07-06)  MODERATE

Computing capped 252d distributions for 51 candidates ...
  SNDK      hist=1yr  (below min 10yr, skipped)
  APP       hist=5yr  (below min 10yr, skipped)
  HOOD      hist=5yr  (below min 10yr, skipped)
  PLTR      hist=6yr  (below min 10yr, skipped)
  CVNA      hist=9yr  (below min 10yr, skipped)
  GEV       hist=2yr  (below min 10yr, skipped)
  SATS      max_up=73%  (M&A / corporate event detected, skipped)
  LITE      N= 546  mu= +39.8%  sigma= 54.3%  hist=11yr  [SINGLE]
  HWM       hist=10yr  (below min 10yr, skipped)
  VRT       hist=8yr  (below min 10yr, skipped)
  AVGO      N= 546  mu= +33.4%  sigma= 35.6%  hist=17yr  [SINGLE]
  VST       hist=10yr  (below min 10yr, skipped)
  IBKR      N= 663  mu=  +7.2%  sigma= 20.3%  hist=19yr  [THIN]
  DECK      N=1201  mu= +31.4%  sigma= 55.2%  hist=26yr  [MODERATE]
  ANET      N= 546  mu= +23.0%  sigma= 24.5%  hist=12yr  [SINGLE]
  NRG       N=1201  mu= +21.2%  sigma= 28.7%  hist=23yr  [MODERATE]
  DASH      hist=6yr  (below min 10yr, skipped)
  CF        excluded (see EXCLUDE_TICKERS)
  PWR       N=1201  mu= +19.2%  sigma= 28.3%  hist=26yr  [MODERATE]
  BKNG      N=1201  mu= +35.3%  sigma= 47.1%  hist=26yr  [MODERATE]
  FOXA      hist=7yr  (below min 10yr, skipped)
  TRGP      N= 546  mu=  -0.6%  sigma= 12.8%  hist=16yr  [SINGLE]
  STLD      N=1201  mu= +15.2%  sigma= 31.1%  hist=26yr  [MODERATE]
  CEG       hist=4yr  (below min 10yr, skipped)
  EXV1.DE   no data
  EME       N=1201  mu= +16.2%  sigma= 27.4%  hist=26yr  [MODERATE]
  NVDA      N=1201  mu= +25.1%  sigma= 32.5%  hist=26yr  [MODERATE]
  CMI       N=1201  mu= +25.6%  sigma= 29.9%  hist=26yr  [MODERATE]
  GM        N= 546  mu=  +8.4%  sigma= 13.3%  hist=16yr  [SINGLE]
  RL        N=1201  mu= +15.4%  sigma= 26.9%  hist=26yr  [MODERATE]
  TPR       N=1201  mu= +17.5%  sigma= 31.9%  hist=26yr  [MODERATE]
  FOX       hist=7yr  (below min 10yr, skipped)
  CFG       N= 546  mu= +16.4%  sigma= 13.5%  hist=12yr  [SINGLE]
  WDC       N=1201  mu= +20.2%  sigma= 38.8%  hist=26yr  [MODERATE]
  GS        N=1201  mu= +13.3%  sigma= 23.8%  hist=26yr  [MODERATE]
  GRMN      N=1201  mu= +30.2%  sigma= 32.6%  hist=26yr  [MODERATE]
  PHAG.L    no data
  CIEN      N=1201  mu= +19.7%  sigma= 27.1%  hist=26yr  [MODERATE]
  COHR      max_up=71%  (M&A / corporate event detected, skipped)
  TSLA      N= 546  mu=  +7.4%  sigma= 16.4%  hist=16yr  [SINGLE]
  FSLR      N= 784  mu= +29.1%  sigma= 53.6%  hist=20yr  [MODERATE]
  ISRG      N=1201  mu= +19.0%  sigma= 34.0%  hist=26yr  [MODERATE]
  PM        N= 546  mu= +10.0%  sigma= 14.1%  hist=18yr  [SINGLE]
  SYF       N= 546  mu= +14.9%  sigma= 16.4%  hist=12yr  [SINGLE]
  CRWD      hist=7yr  (below min 10yr, skipped)
  APH       N=1201  mu= +17.5%  sigma= 24.8%  hist=26yr  [MODERATE]
  FIX       N=1201  mu= +19.1%  sigma= 28.2%  hist=26yr  [MODERATE]
  4GLD.DE   no data
  PPFB.DE   no data
  ETR       N=1201  mu= +13.2%  sigma= 19.1%  hist=26yr  [MODERATE]
  GC_F      N=1201  mu=  +9.2%  sigma= 11.3%  hist=26yr  [MODERATE]

Cross-sectional prior mu : +19.1%  (shrinkage target)
Shrinkage lambda         : 100  (asset needs N>>100 to be fully trusted)

Optimizing (50 restarts, 30 candidates) ...

========================================================================
PORTFOLIO OPTIMIZER  --  Regime: RY=HIGH + BAA10Y=TIGHT
========================================================================
  Universe       : top 50 screen candidates + GC_F
  Matched dates  : 1386  MODERATE
  Shrinkage      : lambda=100  prior=+19.1%

  Ticker     Weight   mu(raw)   mu(shr)    sigma      N   Hist       Div
  -----------------------------------------------------------------
  BKNG        33.4%    +35.3%    +34.1%    47.1%   1201    26yr  MODERATE
  GRMN        24.9%    +30.2%    +29.3%    32.6%   1201    26yr  MODERATE
  LITE        14.7%    +39.8%    +31.0%    54.3%    546    11yr    SINGLE
  DECK        12.3%    +31.4%    +30.4%    55.2%   1201    26yr  MODERATE
  AVGO         5.1%    +33.4%    +27.3%    35.6%    546    17yr    SINGLE
  GC_F         5.0%     +9.2%     +9.9%    11.3%   1201    26yr  MODERATE  [gold]
  FSLR         4.6%    +29.1%    +28.0%    53.6%    784    20yr  MODERATE

  Active positions   : 7  (weight >= 1%)
  Equal-weight g(w)  : +19.2%  (benchmark)
  Optimized g(w)     : +28.0%


  NOTE: g(w) is an approximation. mu/sigma are regime-conditional,
  capped at regime end. Shrinkage applied for short-history assets.
========================================================================
