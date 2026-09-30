"""
Run the full CPRT technical analysis.

  python model/technicals/run_all.py             # fetch fresh data, then analyze
  python model/technicals/run_all.py --no-fetch  # reuse data/ already on disk

Writes to model/technicals/output/:
  memo_figure.png, appendix_figure.png   charts
  summary.txt                            every number in one place
  memo_snippets.md                       the few stats meant for the memo
  *.csv                                  study tables
"""

import argparse

import charts
from analysis import run
from config import OUT_DIR, TICKER


def pct(x, sign=True):
    return f"{x * 100:+.1f}%" if sign else f"{x * 100:.1f}%"


def build_summary(r):
    s, lv, si, opt, st, vs = (r["state"], r["levels"], r["short"], r["options"], r["street"],
                              r["val_summary"])
    L = [f"{TICKER} TECHNICAL SUMMARY as of {s['as_of']} (last bar may be intraday)",
         "=" * 64,
         "", "TREND",
         f"  Close                       ${s['close']:.2f}",
         f"  50-day / 200-day SMA        ${s['sma50']:.2f} / ${s['sma200']:.2f}"
         f"  ({'50 above 200' if s['sma50_above_200'] else '50 below 200'})",
         f"  Distance from 50 / 200-day  {pct(s['dist_sma50'])} / {pct(s['dist_sma200'])}",
         f"  200-day slope, last 20d     {pct(s['sma200_slope_20d'])}",
         f"  Days in a row below 200-day {s['days_below_200d']}",
         f"  All-time high (adjusted)    ${s['ath']:.2f} on {s['ath_date']}",
         f"  Drawdown from ATH           {pct(s['drawdown'])}",
         f"  Lowest close since          {s['lowest_since']} (excluding the past year)",
         f"  Return 1M / YTD / 1Y        {pct(s['ret_1m'])} / {pct(s['ret_ytd'])} / {pct(s['ret_1y'])}",
         "", "MOMENTUM",
         f"  RSI(14) daily / weekly / monthly  {s['rsi_daily']:.1f} / {s['rsi_weekly']:.1f} / "
         f"{s['rsi_monthly']:.1f}",
         f"  MACD vs signal              {s['macd']:.2f} vs {s['macd_sig']:.2f}"
         f" ({'above' if s['macd'] > s['macd_sig'] else 'below'} signal)",
         "", "VOLUME AND VOLATILITY",
         f"  Volume last 5d vs 50d avg   {s['vol_vs_50d']:.2f}x",
         f"  Up/down volume, 20d         {s['updown_vol_20d']:.2f}",
         f"  OBV, last 20d               {'rising' if s['obv_20d_change'] > 0 else 'falling'}",
         f"  ATR(14)                     ${s['atr14']:.2f} ({pct(s['atr_pct'], False)} of price)",
         f"  Realized vol 1M / 1Y        {pct(s['rv30'], False)} / {pct(s['rv252'], False)}",
         "", "VALUATION (trailing EPS as reported to Yahoo)",
         f"  Trailing P/E now            {vs['pe_now']:.1f}x (10Y median {vs['pe_10y_median']:.1f}x, "
         f"{vs['pe_10y_pctile'] * 100:.1f} pctile)",
         f"  P/E at the May 2025 high    {vs['pe_at_ath']:.1f}x",
         f"  TTM EPS now / 1Y ago        ${vs['ttm_eps_now']:.2f} / ${vs['ttm_eps_1y_ago']:.2f} "
         f"({pct(vs['eps_growth_1y'])}); 3Y CAGR {pct(vs['eps_growth_3y_cagr'])}",
         "", "POSITIONING AND STREET",
         f"  Short interest              {si['short_pct_float'] * 100:.1f}% of float, "
         f"{si['days_to_cover']:.1f} days to cover (as of {si['as_of']})",
         f"  Short interest change m/m   "
         f"{pct(si['shares_short'] / si['shares_short_prior_month'] - 1)}",
         f"  Street mean / median target ${st['targetMeanPrice']:.2f} / ${st['targetMedianPrice']:.2f} "
         f"(range ${st['targetLowPrice']:.0f}-{st['targetHighPrice']:.0f}, "
         f"{int(st['numberOfAnalystOpinions'])} analysts, rating '{st['recommendationKey']}')"]
    if opt is not None:
        L.append(f"  Earnings implied move       +/-{opt['implied_move_pct']:.1f}% "
                 f"(ATM straddle, {opt['expiry']} expiry)")
    L += ["", "KEY LEVELS (52-week window unless named)"]
    for k, v in lv.items():
        L.append(f"  {k:<14} ${v:7.2f}  ({(v / s['close'] - 1) * 100:+.1f}% from here)")
    L += ["", "TRADE PLAN (short; pct is vs today's close)", r["plan"].to_string(index=False)]
    L += ["", "SIGNAL STUDY (median forward return vs all days)",
          r["stats"].drop(columns="label").to_string(index=False),
          "  pctile_vs_random: share of random same-size samples with a lower median.",
          "  For a short, low is good. Small samples and overlapping regimes. Context, not proof."]
    L += ["", "EARNINGS REACTIONS (next close vs report-day close)",
          r["earn_summary"].to_string(index=False)]
    L += ["", "RELATIVE STRENGTH (CPRT return minus other, percentage points)",
          r["rel_strength"].to_string(index=False),
          "  ratio_10y_pctile: where CPRT/other sits in its 10-year range (0 = lowest)."]
    L += ["", "DRAWDOWNS OVER 30% SINCE 1994", r["drawdowns"].to_string(index=False)]
    return "\n".join(L)


def build_snippets(r):
    s, si, opt, plan, vs = r["state"], r["short"], r["options"], r["plan"], r["val_summary"]
    st = r["stats"].set_index(["signal", "horizon"])
    wk6 = st.loc[("weekly", "6M")]
    rt6 = st.loc[("retest", "6M")]
    ev = r["events"]
    recent_rt = ev[(ev["signal"] == "retest") & (ev["date"].astype(str) >= "2025-06-01")]
    es = r["earn_summary"].set_index("group")
    rs = r["rel_strength"].set_index("vs")
    dd = r["drawdowns"].dropna(subset=["ttm_eps_yoy_at_trough_%"])
    prior = dd.iloc[:-1]
    stop = plan.iloc[1]
    entry = plan.iloc[0]
    last_t = plan.iloc[-1]
    return "\n".join([
        f"# CPRT technicals: memo snippets (as of {s['as_of']})",
        "",
        "Candidate lines for the technicals section. Pick 4 or 5.",
        "",
        f"- **This drawdown is different.** CPRT is {abs(s['drawdown']) * 100:.0f}% below its "
        f"May 2025 high, the deepest fall since 2003. In all {len(prior)} prior 30%+ drawdowns "
        f"with EPS data, trailing EPS was still growing "
        f"({prior['ttm_eps_yoy_at_trough_%'].min():+.0f}% to "
        f"{prior['ttm_eps_yoy_at_trough_%'].max():+.0f}% y/y). Today it is "
        f"{dd['ttm_eps_yoy_at_trough_%'].iloc[-1]:+.0f}%.",
        f"- **Cheap is the trap.** Trailing P/E is {vs['pe_now']:.1f}x vs a 10-year median of "
        f"{vs['pe_10y_median']:.0f}x ({vs['pe_10y_pctile'] * 100:.1f} percentile). The multiple "
        f"de-rated from {vs['pe_at_ath']:.0f}x as EPS growth stalled, so it can keep falling.",
        f"- **Dip-buying has not worked.** After {int(wk6['n'])} weekly RSI<30 signals since 1996 "
        f"the median 6M return was {wk6['signal_median_%']:+.1f}% vs {wk6['all_days_median_%']:+.1f}% "
        f"for all days. Both rallies into the falling 50-day since mid-2025 failed "
        f"({', '.join(f'{v:+.0f}%' for v in recent_rt['fwd_3M_%'].dropna())} over 3M).",
        f"- **Losing to its direct rival.** CPRT trailed RB Global (owner of IAA) by "
        f"{abs(rs.loc['RBA', '2Y_spread_%']):.0f} pts over 2Y and the S&P 500 by "
        f"{abs(rs.loc['SPY', '1Y_spread_%']):.0f} pts over 1Y.",
        f"- **Prints keep disappointing.** The stock fell after {100 - es.loc['last_12', 'up_rate_%']:.0f}% "
        f"of the last 12 reports. On EPS misses it fell {abs(es.loc['eps_miss', 'median_next_day_%']):.1f}% "
        f"next day (median, n={int(es.loc['eps_miss', 'n'])}).",
        f"- **Not a crowded short.** Short interest is {si['short_pct_float'] * 100:.1f}% of float "
        f"({si['days_to_cover']:.1f} days to cover), down "
        f"{abs(si['shares_short'] / si['shares_short_prior_month'] - 1) * 100:.0f}% m/m. Squeeze risk is low.",
        f"- **Trade plan.** Sell rallies at ${entry['price']:.2f} (entry zone), stop ${stop['price']:.2f}, "
        f"target ${last_t['price']:.2f} ({last_t['level'].replace('target ', '')}) for "
        f"{last_t['reward_risk']:.1f}x reward/risk.",
        "",
        "Caveats to keep in mind (not for the memo unless asked):",
        f"- CPRT has been a long-run compounder. Rallies into the falling 50-day used to work for "
        f"longs (median 6M {rt6['signal_median_%']:+.0f}%, {rt6['signal_hit_rate_%']:.0f}% up, "
        f"n={int(rt6['n'])}). The short case rests on the recent regime break, not the long history.",
        f"- The stock is already oversold (daily RSI {s['rsi_daily']:.0f}) and at the 2021-22 floor "
        f"(${r['levels']['floor_2021_22']:.2f}). Shorting here means shorting into support; wait for a rally.",
        (f"- Options imply +/-{opt['implied_move_pct']:.1f}% on the next print ({opt['expiry']} expiry). "
         f"That is wider than the stop distance, so size for a gap." if opt is not None else ""),
        "- The ACV deal (all cash, $10.50/share) could be sold as a growth story. Watch the reaction.",
    ])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--no-fetch", action="store_true")
    a = p.parse_args()
    if not a.no_fetch:
        import fetch_data
        fetch_data.main()

    r = run()
    charts.memo_figure(r, OUT_DIR / "memo_figure.png")
    charts.appendix_figure(r, OUT_DIR / "appendix_figure.png")
    summary = build_summary(r)
    (OUT_DIR / "summary.txt").write_text(summary + "\n", encoding="utf-8")
    (OUT_DIR / "memo_snippets.md").write_text(build_snippets(r) + "\n", encoding="utf-8")
    print(summary)
    print(f"\nFiles written to {OUT_DIR}")


if __name__ == "__main__":
    main()
