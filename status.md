==============================================================
REACTOR CORE -- PORTFOLIO SNAPSHOT
==============================================================
Position                Shares      Price    Value SEK     Wt
--------------------------------------------------------------
  Gold                     304     774 kr   235,423 kr  21.6%
  Silver                    66     540 kr    35,632 kr   3.3%
  Eli Lilly                 14  11,755 kr   164,575 kr  15.1%
  Walmart                  126   1,083 kr   136,464 kr  12.5%
  Cameco                    93     935 kr    86,944 kr   8.0%
  Vertiv                    31   2,910 kr    90,219 kr   8.3%
  Broadcom                  21   3,491 kr    73,302 kr   6.7%
  Howmet Aerospace          11   2,619 kr    28,805 kr   2.6%
  Spiltan Räntefond          -     manual   234,623 kr  21.6%
  War Chest                  -     manual     1,959 kr   0.2%
--------------------------------------------------------------
  TPV                                        1,086,329 kr
    Reactor Core            851,365 kr  (78%)
    Home Base               234,623 kr  (22%)
    War Chest                 1,959 kr  (0%)

==============================================================
FI@50 PACE TRACKER
==============================================================
  Start  (2025-07-21)  :       925,983 kr
  Now                     :     1,086,329 kr
  Target (FI@50)          :    12,934,706 kr
  Years remaining         :  11.0

  AWAR (trailing)         :  +18.3%
  Required CAGR           :  +22.2%
  Status                  :  BEHIND  (-3.9% margin)

  Projected @ AWAR        :     9,293,601 kr
  vs target               :    -3,641,105 kr  (deficit)

  Scenario         CAGR       Projected     FI date   (incl. 6,000 kr/mo contributions)
  ------------------------------------------------------------------------
  Bear           +10%       4,530,012 kr       ~2047
  Conservative   +15%       6,998,889 kr       ~2041
  Base           +20%      10,731,060 kr       ~2038
  Current AWAR   +18%       9,293,601 kr       ~2039
  Bull           +30%      24,485,974 kr       ~2035

==============================================================
MACRO REGIME
==============================================================

  Feature                 Value   Regime  
  ------------------------------------------
  Nominal 10Y             4.48%   HIGH
  Real Yield             +2.25%   HIGH  ^
  Breakeven               2.23%   MID
  HY OAS                275 bps   TIGHT
  IG Credit               1.54%   TIGHT
  Curve 10Y-3M          +67 bps   MID
  Curve 10Y-2Y          +35 bps   LOW
  SE 10Y                  2.75%   MID
  USD                     120.9   STRONG

  HY 20d delta  : +1 bps  (flat)
  Confidence    : HIGH
  Data through  : 2026-07-02

==============================================================
PORTFOLIO SIGNALS
==============================================================

  Base: ry=HIGH  nominal_10y=HIGH  baa10y=TIGHT  usd=STRONG

  Position          Wt    21d   63d   63d med  252d med  W252     N  Note
  ----------------------------------------------------------------------
  Gold           21.6%    LOW   LOW     +0.7%     +0.7%   75%    63  
  Silver          3.3%    LOW   LOW     +2.3%     +2.3%   84%    31  
  Eli Lilly      15.1%   HIGH  HIGH     -0.2%     -0.2%   46%   137  
  Walmart        12.5%    MID   LOW     +1.4%     +1.4%   60%   526  ~base fallback
  Cameco          8.0%    LOW   LOW     +2.0%     +2.0%   66%    80  
  Vertiv          8.3%    LOW   MID     -0.1%     -0.1%   49%    74  
  Broadcom        6.7%    LOW   MID     +0.4%     +0.4%   65%    46  

==============================================================
TACTICAL RULES
==============================================================

  Silver GSR Tactical
    GSR now        : 67.82  (as of 2026-07-02)
    60d GSR peak   : 69.14
    Fall from peak : 1.9%  (no (need >=5% fall for signal))
    T1 threshold   : 83.36  |  T2: 86.45  |  Exit: 62.56
    Signal         : INACTIVE
    Action         : No action -- hold base

  AVGO 200d Guard
    AVGO now       : $360.45  (as of 2026-07-02)
    200d SMA       : $360.20  (+0.1% gap)
    5d ROC         : -4.9%  (crash threshold: -10%)
    Signal         : BASE  (trigger: none)
    LLY stress     : inactive  ($1213.91 vs 200d SMA $982.55, 5d ROC +7.6%)
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
    Best candidate : none eligible today (either no ENTER survivors, or all failed the pre-entry tripwire gate)

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
  ANET      N= 546  mu= +23.0%  sigma= 24.5%  hist=12yr  [SINGLE]
  DASH      hist=6yr  (below min 10yr, skipped)
  NRG       N=1201  mu= +21.2%  sigma= 28.7%  hist=23yr  [MODERATE]
  CF        excluded (see EXCLUDE_TICKERS)
  BKNG      N=1201  mu= +35.3%  sigma= 47.1%  hist=26yr  [MODERATE]
  PWR       N=1201  mu= +19.2%  sigma= 28.3%  hist=26yr  [MODERATE]
  FOXA      hist=7yr  (below min 10yr, skipped)
  TRGP      N= 546  mu=  -0.6%  sigma= 12.8%  hist=16yr  [SINGLE]
  STLD      N=1201  mu= +15.2%  sigma= 31.1%  hist=26yr  [MODERATE]
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
  COHR      max_up=71%  (M&A / corporate event detected, skipped)
  FSLR      N= 784  mu= +29.1%  sigma= 53.6%  hist=20yr  [MODERATE]
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
