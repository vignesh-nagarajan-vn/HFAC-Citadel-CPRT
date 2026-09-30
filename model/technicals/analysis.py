"""
Technical studies for the CPRT short pitch. Reads data/, writes CSVs to output/.

  current_state      trend, momentum, volume, volatility right now
  key_levels         resistance above (stops), support below (targets), fibs, volume profile
  drawdown_history   every 30%+ drawdown in CPRT's history
  oversold_study     forward returns after oversold signals (the bounce risk we are shorting into)
  downtrend_study    forward returns in a confirmed downtrend and after rallies into the 50-day
  valuation_history  trailing P/E from reported EPS, to show how "cheap" the stock looks
  earnings_study     next-day and 5-day reaction to each earnings report
  relative_strength  CPRT vs SPY, XLI and peers over 3M to 2Y
  trade_plan         short entry, stop and targets with reward/risk
"""

import numpy as np
import pandas as pd

from config import (BENCHMARK, COOLDOWN, DATA_DIR, DIST200_LEVEL, HORIZONS, OUT_DIR,
                    PEERS, PRICE_DIR, RSI_LEVEL, SECTOR, TICKER)
from indicators import add_indicators, load, resampled_rsi


# ------------------------------------------------------------------ current state
def current_state(df):
    last = df.iloc[-1]
    c = df["Close"]
    # last time CPRT closed this low, ignoring the past year of the current selloff
    older = c.iloc[:-252]
    below = older[older <= last["Close"]]
    down20 = df.iloc[-20:]
    up_vol = down20.loc[down20["Close"].diff() > 0, "Volume"].sum()
    dn_vol = down20.loc[down20["Close"].diff() < 0, "Volume"].sum()
    return {
        "as_of": df.index[-1].date(),
        "close": last["Close"],
        "sma50": last["SMA50"],
        "sma200": last["SMA200"],
        "dist_sma50": last["Close"] / last["SMA50"] - 1,
        "dist_sma200": last["Dist200"],
        "sma50_above_200": last["SMA50"] > last["SMA200"],
        "sma200_slope_20d": last["SMA200"] / df["SMA200"].iloc[-21] - 1,
        "ath": c.max(),
        "ath_date": c.idxmax().date(),
        "drawdown": last["DD"],
        "lowest_since": below.index[-1].date() if len(below) else None,
        "rsi_daily": last["RSI14"],
        "rsi_weekly": resampled_rsi(c, "W-FRI").iloc[-1],
        "rsi_monthly": resampled_rsi(c, "ME").iloc[-1],
        "macd": last["MACD"],
        "macd_sig": last["MACD_sig"],
        "vol_vs_50d": df["Volume"].iloc[-6:-1].mean() / last["Vol50"],
        "updown_vol_20d": up_vol / dn_vol if dn_vol else np.nan,
        "obv_20d_change": df["OBV"].iloc[-1] - df["OBV"].iloc[-21],
        "atr14": last["ATR14"],
        "atr_pct": last["ATR14"] / last["Close"],
        "rv30": last["RV30"],
        "rv252": last["RV252"],
        "ret_1m": c.iloc[-1] / c.iloc[-22] - 1,
        "ret_ytd": c.iloc[-1] / c[c.index.year < df.index[-1].year].iloc[-1] - 1,
        "ret_1y": c.iloc[-1] / c.iloc[-253] - 1,
        "days_below_200d": int((c.iloc[::-1] < df["SMA200"].iloc[::-1]).cumprod().sum()),
    }


# ------------------------------------------------------------------------ levels
def volume_nodes(df, lookback=252, bins=30, top=4):
    """Price zones with the most traded volume over the lookback (volume profile)."""
    d = df.iloc[-lookback:]
    typical = (d["High"] + d["Low"] + d["Close"]) / 3
    hist, edges = np.histogram(typical, bins=bins, weights=d["Volume"])
    mids = (edges[:-1] + edges[1:]) / 2
    order = np.argsort(hist)[::-1][:top]
    return sorted(round(mids[i], 2) for i in order)


def multi_year_floor(df, price, years=6):
    """Highest prior calendar-year low near or under the current price (the 2021-22 floor)."""
    d = df.iloc[-252 * years:-252]
    yearly_low = d["Low"].groupby(d.index.year).min()
    return yearly_low[yearly_low < price * 1.05].max()


def key_levels(df, lookback=252):
    recent = df.iloc[-lookback:]
    hi, lo = recent["High"].max(), recent["Low"].min()
    rng = hi - lo
    lv = {
        "52w_low": lo,
        "52w_high": hi,
        "sma50": df["SMA50"].iloc[-1],
        "sma200": df["SMA200"].iloc[-1],
        "fib_23.6": lo + 0.236 * rng,
        "fib_38.2": lo + 0.382 * rng,
        "fib_50.0": lo + 0.500 * rng,
        "floor_2021_22": multi_year_floor(df, df["Close"].iloc[-1]),
    }
    for i, v in enumerate(volume_nodes(df, lookback)):
        lv[f"vol_node_{i + 1}"] = v
    return lv


# -------------------------------------------------------------------- drawdowns
def drawdown_history(df, min_depth=-0.30):
    """Peak-to-trough episodes deeper than min_depth, with recovery time."""
    c = df["Close"]
    peak = c.cummax()
    dd = c / peak - 1
    rows, i, n = [], 0, len(c)
    while i < n:
        if dd.iloc[i] < 0:
            start = i - 1 if i > 0 else 0
            j = i
            while j < n and dd.iloc[j] < 0:
                j += 1
            seg = dd.iloc[i:j]
            if seg.min() <= min_depth:
                trough = seg.idxmin()
                recovered = j < n
                rows.append({
                    "peak_date": c.index[start].date(),
                    "trough_date": trough.date(),
                    "depth_%": round(seg.min() * 100, 1),
                    "months_to_trough": round((trough - c.index[start]).days / 30.4, 1),
                    "recovery_date": c.index[j].date() if recovered else None,
                    "months_trough_to_recovery": round((c.index[j] - trough).days / 30.4, 1)
                    if recovered else None,
                    "ret_12m_after_trough_%": round((c.iloc[min(c.index.get_loc(trough) + 252, n - 1)]
                                                     / c.loc[trough] - 1) * 100, 1)
                    if c.index.get_loc(trough) + 252 < n else None,
                })
            i = j
        else:
            i += 1
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- signal helpers
def forward_returns(close, dates):
    idx = close.index
    rows = []
    for d in dates:
        i = idx.get_loc(d)
        row = {"date": d.date(), "close": round(close.iloc[i], 2)}
        for name, h in HORIZONS.items():
            row[f"fwd_{name}_%"] = round((close.iloc[i + h] / close.iloc[i] - 1) * 100, 1) \
                if i + h < len(close) else np.nan
        rows.append(row)
    cols = ["date", "close"] + [f"fwd_{n}_%" for n in HORIZONS]
    return pd.DataFrame(rows, columns=cols)


def signal_dates(cond, cooldown=COOLDOWN):
    """First day of each episode, so one selloff is not counted many times."""
    out, last_i = [], -10**9
    for i in np.flatnonzero(cond.values):
        if i - last_i >= cooldown:
            out.append(cond.index[i])
            last_i = i
    return out


def random_median_pctile(fwd_all, sig, n_iter=5000, seed=0):
    """Share of random same-size samples whose median is below the signal median."""
    if len(sig) < 3:
        return np.nan
    rng = np.random.default_rng(seed)
    vals = fwd_all.values
    meds = np.median(rng.choice(vals, size=(n_iter, len(sig)), replace=True), axis=1)
    return (meds < np.median(sig)).mean()


def to_daily(dates, idx):
    """Map weekly/monthly bar labels to the last trading day on or before them."""
    return [idx[idx.searchsorted(d, side="right") - 1] for d in dates]


def downtrend(df):
    """Confirmed downtrend: below a falling 200-day with the 50-day under the 200-day."""
    return ((df["Close"] < df["SMA200"]) & (df["SMA50"] < df["SMA200"])
            & (df["SMA200"] < df["SMA200"].shift(20)))


def signal_definitions(df):
    c = df["Close"]
    w = resampled_rsi(c, "W-FRI")
    m = resampled_rsi(c, "ME")
    # skip the first year after the IPO while RSI and the 200-day warm up
    warm = df.index[252]
    w, m = w[w.index >= warm], m[m.index >= warm]
    daily = (df["RSI14"] < RSI_LEVEL) & (df["Dist200"] < DIST200_LEVEL)
    trend = downtrend(df)
    # rally that tags the falling 50-day from below while the downtrend holds
    retest = trend & (df["High"] >= df["SMA50"]) & (df["Close"].shift(5) < df["SMA50"].shift(5) * 0.97)
    return {
        "daily": ("Daily RSI<30 and >20% below 200d", signal_dates(daily[daily.index >= warm])),
        "weekly": ("Weekly RSI<30", to_daily(signal_dates(w < 30, cooldown=13), df.index)),
        "monthly": ("Monthly RSI<30", to_daily(signal_dates(m < 30, cooldown=6), df.index)),
        "retest": ("Rally into falling 50d in downtrend", signal_dates(retest[retest.index >= warm])),
    }


def signal_study(df):
    c = df["Close"]
    base = {n: (c.shift(-h) / c - 1).dropna() * 100 for n, h in HORIZONS.items()}
    trend = downtrend(df)
    in_trend = {n: base[n][trend.reindex(base[n].index).fillna(False)] for n in HORIZONS}
    all_events, stats = [], []
    for key, (label, dates) in signal_definitions(df).items():
        ev = forward_returns(c, dates)
        ev.insert(0, "signal", key)
        ev.insert(3, "daily_rsi", [round(df.loc[pd.Timestamp(d), "RSI14"], 1) for d in ev["date"]])
        ev.insert(4, "pct_below_200d",
                  [round(df.loc[pd.Timestamp(d), "Dist200"] * 100, 1) for d in ev["date"]])
        all_events.append(ev)
        for n in HORIZONS:
            col = ev[f"fwd_{n}_%"].dropna()
            stats.append(_stat_row(key, label, n, col, base[n]))
    # every day spent in a confirmed downtrend, as its own "signal"
    for n in HORIZONS:
        stats.append(_stat_row("in_downtrend", "Any day in confirmed downtrend", n,
                               in_trend[n], base[n], resample=False))
    return pd.concat(all_events, ignore_index=True), pd.DataFrame(stats), base


def _stat_row(key, label, horizon, col, base, resample=True):
    return {
        "signal": key, "label": label, "horizon": horizon, "n": len(col),
        "signal_median_%": round(col.median(), 1),
        "signal_mean_%": round(col.mean(), 1),
        "signal_hit_rate_%": round((col > 0).mean() * 100, 0),
        "all_days_median_%": round(base.median(), 1),
        "all_days_hit_rate_%": round((base > 0).mean() * 100, 0),
        "pctile_vs_random": round(random_median_pctile(base, col), 2) if resample else np.nan,
    }


# ------------------------------------------------------------- valuation history
def valuation_history(df, earn):
    """Trailing 4-quarter EPS (as reported to Yahoo, split adjusted) and the implied P/E."""
    e = earn.dropna(subset=["eps_actual"]).copy()
    e["date"] = pd.to_datetime(e["date"])
    e = e.sort_values("date").set_index("date")
    ttm = e["eps_actual"].rolling(4).sum().dropna()
    ttm = ttm[ttm > 0]
    eps = ttm.reindex(df.index, method="ffill")
    pe = (df["Close"] / eps).dropna()
    return pd.DataFrame({"close": df["Close"], "ttm_eps": eps, "pe": pe}).dropna()


def add_eps_growth(dd, val):
    """TTM EPS growth at each drawdown trough: prior selloffs happened while earnings still grew."""
    eps = val["ttm_eps"]
    g = []
    for d in pd.to_datetime(dd["trough_date"]):
        i = eps.index.searchsorted(d)
        g.append(round((eps.iloc[i] / eps.iloc[i - 252] - 1) * 100, 1)
                 if 252 <= i < len(eps) else None)
        if i >= len(eps):
            g[-1] = round((eps.iloc[-1] / eps.iloc[-253] - 1) * 100, 1)
    dd = dd.copy()
    dd["ttm_eps_yoy_at_trough_%"] = g
    return dd


def valuation_summary(val):
    pe = val["pe"]
    last10 = pe.iloc[-2520:]
    eps = val["ttm_eps"]
    return {
        "pe_now": pe.iloc[-1],
        "pe_10y_median": last10.median(),
        "pe_10y_min": last10.min(),
        "pe_10y_pctile": (last10 < pe.iloc[-1]).mean(),
        "pe_at_ath": pe.loc[:pd.Timestamp("2025-05-16")].iloc[-1],
        "ttm_eps_now": eps.iloc[-1],
        "ttm_eps_1y_ago": eps.iloc[-253],
        "eps_growth_1y": eps.iloc[-1] / eps.iloc[-253] - 1,
        "eps_growth_3y_cagr": (eps.iloc[-1] / eps.iloc[-757]) ** (1 / 3) - 1,
    }


# ---------------------------------------------------------------- earnings study
def earnings_summary(er, depressed=-15.0, recent=12):
    """Average reaction overall, in the last `recent` reports, and when already depressed."""
    groups = {
        "all": er,
        f"last_{recent}": er.tail(recent),
        f"pre_below_200d_{int(-depressed)}pct": er[er["pre_dist_200d_%"] < depressed],
        "eps_miss": er[er["surprise_%"] < 0],
    }
    rows = []
    for name, g in groups.items():
        rows.append({"group": name, "n": len(g),
                     "avg_abs_next_day_%": round(g["next_day_%"].abs().mean(), 1),
                     "median_next_day_%": round(g["next_day_%"].median(), 1),
                     "up_rate_%": round((g["next_day_%"] > 0).mean() * 100, 0),
                     "median_next_5d_%": round(g["next_5d_%"].median(), 1)})
    return pd.DataFrame(rows)


def earnings_study(df, earn):
    """CPRT reports after the close, so the reaction is next close vs report-day close."""
    c = df["Close"]
    rows = []
    for _, e in earn.dropna(subset=["eps_actual"]).iterrows():
        d = pd.Timestamp(e["date"])
        if d not in c.index:
            continue
        i = c.index.get_loc(d)
        if i + 5 >= len(c) or i < 200:
            continue
        rows.append({
            "date": d.date(),
            "surprise_%": e["surprise_pct"],
            "pre_dist_200d_%": round(df["Dist200"].iloc[i] * 100, 1),
            "next_day_%": round((c.iloc[i + 1] / c.iloc[i] - 1) * 100, 1),
            "next_5d_%": round((c.iloc[i + 5] / c.iloc[i] - 1) * 100, 1),
        })
    return pd.DataFrame(rows)


# -------------------------------------------------------------- relative strength
def relative_strength(prices):
    c = prices[TICKER]["Close"]
    windows = {"3M": 63, "6M": 126, "1Y": 252, "2Y": 504}
    rows = []
    for t in [BENCHMARK, SECTOR] + PEERS:
        o = prices[t]["Close"].reindex(c.index).ffill()
        row = {"vs": t}
        for name, w in windows.items():
            if o.iloc[-w - 1:].isna().any():
                row[f"{name}_spread_%"] = np.nan
                continue
            r_n = c.iloc[-1] / c.iloc[-w - 1] - 1
            r_o = o.iloc[-1] / o.iloc[-w - 1] - 1
            row[f"{name}_spread_%"] = round((r_n - r_o) * 100, 1)
        # where the CPRT/X ratio sits vs its own 10-year range (0 = lowest)
        ratio = (c / o).iloc[-2520:].dropna()
        row["ratio_10y_pctile"] = round((ratio < ratio.iloc[-1]).mean(), 3)
        rows.append(row)
    return pd.DataFrame(rows)


def relative_series(prices, window):
    c = prices[TICKER]["Close"]
    idx = c.index[-window:]
    rel = pd.DataFrame(index=idx)
    for t in [BENCHMARK, SECTOR] + PEERS:
        ratio = (c / prices[t]["Close"].reindex(c.index).ffill()).reindex(idx)
        if ratio.notna().any():
            rel[f"vs {t}"] = ratio / ratio.dropna().iloc[0] * 100
    return rel


# -------------------------------------------------------------------- trade plan
def trade_plan(state, lv, val_sum, exit_pe=15):
    """
    Short, but do not chase the hole: sell the rally into the vol node / falling 50-day.
    Stop is 1.5 ATR above the higher of the 50-day and the 23.6% retrace.
    The last target is valuation, not a chart level: exit_pe x trailing EPS.
    """
    zone = sorted([lv["vol_node_1"], lv["sma50"]])
    entry = sum(zone) / 2
    stop = max(lv["sma50"], lv["fib_23.6"]) + 1.5 * state["atr14"]
    risk = stop - entry
    targets = {"52w_low": lv["52w_low"], "floor_2021_22": lv["floor_2021_22"],
               f"{exit_pe}x_ttm_eps": exit_pe * val_sum["ttm_eps_now"]}
    rows = [{"level": f"entry zone ${zone[0]:.2f}-{zone[1]:.2f} (mid)", "price": entry,
             "pct": (entry / state["close"] - 1) * 100, "reward_risk": None},
            {"level": "stop (1.5 ATR above 50d / 23.6%)", "price": stop,
             "pct": (stop / state["close"] - 1) * 100, "reward_risk": None}]
    for k, v in sorted(targets.items(), key=lambda kv: -kv[1]):
        rows.append({"level": f"target {k}", "price": v, "pct": (v / state["close"] - 1) * 100,
                     "reward_risk": (entry - v) / risk})
    out = pd.DataFrame(rows)
    out["price"] = out["price"].round(2)
    out["pct"] = out["pct"].round(1)
    out["reward_risk"] = out["reward_risk"].astype(float).round(1)
    return out


# -------------------------------------------------------------------------- run
def run():
    OUT_DIR.mkdir(exist_ok=True)
    prices = {p.stem: load(p) for p in PRICE_DIR.glob("*.csv")}
    df = add_indicators(prices[TICKER].copy())
    earn = pd.read_csv(DATA_DIR / "cprt_earnings.csv")
    si = pd.read_csv(DATA_DIR / "cprt_short_interest.csv").iloc[-1]
    street = pd.read_csv(DATA_DIR / "cprt_street.csv").iloc[-1]
    opt_path = DATA_DIR / "cprt_options.csv"
    opt = pd.read_csv(opt_path).iloc[-1] if opt_path.exists() else None

    state = current_state(df)
    lv = key_levels(df)
    dd = drawdown_history(df)
    events, stats, base = signal_study(df)
    val = valuation_history(df, earn)
    val_sum = valuation_summary(val)
    er = earnings_study(df, earn)
    er_sum = earnings_summary(er)
    rs = relative_strength(prices)
    dd = add_eps_growth(dd, val)
    plan = trade_plan(state, lv, val_sum)

    dd.to_csv(OUT_DIR / "drawdown_history.csv", index=False)
    events.to_csv(OUT_DIR / "signal_events.csv", index=False)
    stats.to_csv(OUT_DIR / "signal_stats.csv", index=False)
    val.resample("ME").last().round(2).to_csv(OUT_DIR / "valuation_history.csv")
    er.to_csv(OUT_DIR / "earnings_reactions.csv", index=False)
    er_sum.to_csv(OUT_DIR / "earnings_summary.csv", index=False)
    rs.to_csv(OUT_DIR / "relative_strength.csv", index=False)
    plan.to_csv(OUT_DIR / "trade_plan.csv", index=False)
    pd.Series(lv).round(2).to_csv(OUT_DIR / "key_levels.csv", header=["price"])

    return {"df": df, "prices": prices, "state": state, "levels": lv, "drawdowns": dd,
            "events": events, "stats": stats, "base": base, "valuation": val,
            "val_summary": val_sum, "earnings": er, "earn_summary": er_sum, "earn_raw": earn,
            "rel_strength": rs, "plan": plan, "short": si, "street": street, "options": opt}
