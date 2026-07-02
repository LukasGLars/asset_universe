==============================================================
REACTOR CORE -- PORTFOLIO SNAPSHOT
==============================================================
Position                Shares      Price    Value SEK     Wt
--------------------------------------------------------------
  Gold                     304     769 kr   233,660 kr  21.5%
  Silver                    66     532 kr    35,109 kr   3.2%
  Eli Lilly                 14  11,583 kr   162,164 kr  14.9%
  Walmart                  126   1,058 kr   133,268 kr  12.3%
  Cameco                    93     947 kr    88,032 kr   8.1%
  Vertiv                    31   3,027 kr    93,833 kr   8.6%
  Broadcom                  21   3,590 kr    75,386 kr   6.9%
  Howmet Aerospace          11   2,599 kr    28,590 kr   2.6%
  Spiltan Räntefond          -     manual   234,561 kr  21.6%
  War Chest                  -     manual     1,959 kr   0.2%
--------------------------------------------------------------
  TPV                                        1,087,289 kr
    Reactor Core            850,043 kr  (78%)
    Home Base               234,561 kr  (22%)
    War Chest                 1,959 kr  (0%)

==============================================================
FI@50 PACE TRACKER
==============================================================
  Start  (2025-07-21)  :       925,983 kr
  Now                     :     1,087,289 kr
  Target (FI@50)          :    12,934,706 kr
  Years remaining         :  11.1

  AWAR (trailing)         :  +18.5%
  Required CAGR           :  +22.2%
  Status                  :  BEHIND  (-3.7% margin)

  Projected @ AWAR        :     9,438,298 kr
  vs target               :    -3,496,408 kr  (deficit)

  Scenario         CAGR       Projected     FI date   (incl. 6,000 kr/mo contributions)
  ------------------------------------------------------------------------
  Bear           +10%       4,534,145 kr       ~2047
  Conservative   +15%       7,006,266 kr       ~2041
  Base           +20%      10,743,819 kr       ~2038
  Current AWAR   +18%       9,438,298 kr       ~2039
  Bull           +30%      24,521,213 kr       ~2035

==============================================================
MACRO REGIME
==============================================================

  Feature                 Value   Regime  
  ------------------------------------------
  Nominal 10Y             4.48%   HIGH
  Real Yield             +2.25%   HIGH  ^
  Breakeven               2.23%   MID
  HY OAS                274 bps   TIGHT
  IG Credit               1.54%   TIGHT
  Curve 10Y-3M          +67 bps   MID
  Curve 10Y-2Y          +35 bps   LOW
  SE 10Y                  2.75%   MID
  USD                     120.9   STRONG

  HY 20d delta  : -1 bps  (flat)
  Confidence    : HIGH
  Data through  : 2026-07-02

==============================================================
PORTFOLIO SIGNALS
==============================================================

  Base: ry=HIGH  nominal_10y=HIGH  baa10y=TIGHT  usd=STRONG

  Position          Wt    21d   63d   63d med  252d med  W252     N  Note
  ----------------------------------------------------------------------
  Gold           21.5%     --    --     +3.3%     +4.3%   92%   522  no mom data
  Silver          3.2%     --    --     +4.0%     +3.9%   70%   522  no mom data
  Eli Lilly      14.9%     --    --     -0.1%     -0.6%   43%   525  no mom data
  Walmart        12.3%     --    --     +1.4%     +1.4%   60%   525  no mom data
  Cameco          8.1%     --    --     -0.9%     -1.5%   43%   525  no mom data
  Vertiv          8.6%     --    --     +1.2%     -2.1%   44%   525  no mom data
  Broadcom        6.9%     --    --     +7.4%     +3.6%   60%   525  no mom data

==============================================================
TACTICAL RULES
==============================================================

  Silver GSR Tactical
    GSR now        : 67.71  (as of 2026-07-01)
    60d GSR peak   : 69.14
    Fall from peak : 2.1%  (no (need >=5% fall for signal))
    T1 threshold   : 83.36  |  T2: 86.45  |  Exit: 62.56
    Signal         : INACTIVE
    Action         : No action -- hold base

  AVGO 200d Guard
    AVGO now       : $369.34  (as of 2026-07-01)
    200d SMA       : $360.20  (+2.5% gap)
    5d ROC         : -3.3%  (crash threshold: -10%)
    Signal         : BASE  (trigger: none)
    LLY stress     : inactive  ($1191.74 vs 200d SMA $980.20, 5d ROC +6.7%)
    Joint stress   : inactive  (guard AND LLY stress both active)
    Action         : Hold base (Gold 25%, AVGO 55%, LLY 20%)

  AVGO Earnings Checkpoint
    Trailing EPS   : $6.02
    Forward EPS    : $19.40
    Fwd/Trail ratio: 3.22x  (baseline 2026-07-01: 3.23x)
    Next earnings  : 2026-09-03
    Action         : after the print, check actual AI revenue/EPS against the
                     $56B FY26 / $100B FY27 guided path. Meaningfully short of
                     trajectory -> revisit conviction, even if price > SMA200.

  Opportunistic Sleeve
    Status         : CLOSED (0/1 position)
    Best candidate : CMI (Cummins Inc.)  (ext +1.1%, 30d med +3.6%, div ROBUST, pre-entry tripwires PASSED) -- run run_entry_screen.py for full detail
    VIX review     : 16.59  (42% percentile, falling) -- for review, not a gate

==============================================================
  Regime check (2026-07-02): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)
Building regime labels ...
  Conditions    : {'ry_regime': 'HIGH', 'baa10y_regime': 'TIGHT'}
  Matched dates : 1384  (2004-05-07 - 2026-07-02)  MODERATE

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
  DASH      hist=6yr  (below min 10yr, skipped)
  ANET      N= 546  mu= +23.0%  sigma= 24.5%  hist=12yr  [SINGLE]
  NRG       N=1201  mu= +21.2%  sigma= 28.7%  hist=23yr  [MODERATE]
  CF        excluded (see EXCLUDE_TICKERS)
  BKNG      N=1201  mu= +35.3%  sigma= 47.1%  hist=26yr  [MODERATE]
  PWR       N=1201  mu= +19.2%  sigma= 28.3%  hist=26yr  [MODERATE]
  FOXA      hist=7yr  (below min 10yr, skipped)
  STLD      N=1201  mu= +15.2%  sigma= 31.1%  hist=26yr  [MODERATE]
  TRGP      N= 546  mu=  -0.6%  sigma= 12.8%  hist=16yr  [SINGLE]
  CEG       hist=4yr  (below min 10yr, skipped)
  EXV1.DE   no data
  NVDA      N=1201  mu= +25.1%  sigma= 32.5%  hist=26yr  [MODERATE]
  EME       N=1201  mu= +16.2%  sigma= 27.4%  hist=26yr  [MODERATE]
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
  FSLR      N= 784  mu= +29.1%  sigma= 53.6%  hist=20yr  [MODERATE]
  COHR      max_up=71%  (M&A / corporate event detected, skipped)
  TSLA      N= 546  mu=  +7.4%  sigma= 16.4%  hist=16yr  [SINGLE]
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
  Matched dates  : 1384  MODERATE
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
