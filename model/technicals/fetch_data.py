"""
Download everything the technical analysis needs and save it under data/.

  data/prices/<TICKER>.csv        daily OHLCV, split/dividend adjusted
  data/cprt_earnings.csv          past and upcoming earnings dates with EPS surprise
  data/cprt_short_interest.csv    short interest snapshot (appended each run)
  data/cprt_options.csv           ATM straddle for the first expiry after next earnings
  data/cprt_street.csv            analyst price targets and ratings snapshot (appended each run)

Usage: python model/technicals/fetch_data.py
"""

from datetime import date

import pandas as pd
import yfinance as yf

from config import ALL_TICKERS, DATA_DIR, PRICE_DIR, TICKER


def fetch_prices():
    PRICE_DIR.mkdir(parents=True, exist_ok=True)
    raw = yf.download(ALL_TICKERS, period="max", auto_adjust=True,
                      progress=False, group_by="ticker")
    for t in ALL_TICKERS:
        df = raw[t][["Open", "High", "Low", "Close", "Volume"]].dropna()
        df.index.name = "Date"
        df.round(4).to_csv(PRICE_DIR / f"{t}.csv")
        print(f"  {t}: {len(df)} rows, {df.index[0].date()} to {df.index[-1].date()}")


def fetch_earnings(tk):
    ed = tk.get_earnings_dates(limit=100).reset_index()
    ed.columns = ["datetime", "eps_est", "eps_actual", "surprise_pct"]
    ed["date"] = pd.to_datetime(ed["datetime"]).dt.tz_localize(None).dt.date
    ed = ed.drop(columns="datetime").sort_values("date")
    ed.to_csv(DATA_DIR / "cprt_earnings.csv", index=False)
    print(f"  earnings: {len(ed)} dates, next {ed[ed['eps_actual'].isna()]['date'].min()}")
    return ed


def _append(path, row, key):
    df = pd.read_csv(path) if path.exists() else pd.DataFrame()
    df = pd.concat([df, pd.DataFrame([row])]).drop_duplicates(key, keep="last")
    df.to_csv(path, index=False)


def fetch_short_interest(info):
    row = {
        "pulled": date.today(),
        "as_of": pd.to_datetime(info.get("dateShortInterest"), unit="s").date(),
        "shares_short": info.get("sharesShort"),
        "shares_short_prior_month": info.get("sharesShortPriorMonth"),
        "short_pct_float": info.get("shortPercentOfFloat"),
        "days_to_cover": info.get("shortRatio"),
    }
    _append(DATA_DIR / "cprt_short_interest.csv", row, "as_of")
    print(f"  short interest: {row['short_pct_float']:.1%} of float as of {row['as_of']}")


def fetch_street(info):
    """Consensus snapshot. Placeholder until Bloomberg pulls replace it."""
    keys = ["targetMeanPrice", "targetMedianPrice", "targetHighPrice", "targetLowPrice",
            "numberOfAnalystOpinions", "recommendationMean", "recommendationKey",
            "trailingPE", "forwardPE", "enterpriseToEbitda", "marketCap"]
    row = {"pulled": date.today(), **{k: info.get(k) for k in keys}}
    _append(DATA_DIR / "cprt_street.csv", row, "pulled")
    print(f"  street: mean target ${row['targetMeanPrice']}, {row['numberOfAnalystOpinions']} analysts, "
          f"fwd P/E {row['forwardPE']:.1f}")


def fetch_options(tk, earnings):
    """ATM straddle on the first expiry after the next earnings date = implied move."""
    nxt = earnings[earnings["eps_actual"].isna()]["date"].min()
    expiries = [e for e in tk.options if pd.Timestamp(e).date() > nxt]
    if not expiries:
        print("  options: no expiry after next earnings")
        return
    exp = expiries[0]
    spot = tk.history(period="1d")["Close"].iloc[-1]
    chain = tk.option_chain(exp)
    k = chain.calls.iloc[(chain.calls["strike"] - spot).abs().argmin()]["strike"]
    call = chain.calls[chain.calls["strike"] == k].iloc[0]
    put = chain.puts[chain.puts["strike"] == k].iloc[0]
    mid = lambda o: (o["bid"] + o["ask"]) / 2 if o["bid"] > 0 else o["lastPrice"]
    straddle = mid(call) + mid(put)
    row = {"pulled": date.today(), "expiry": exp, "spot": round(spot, 2), "strike": k,
           "call_mid": round(mid(call), 2), "put_mid": round(mid(put), 2),
           "straddle": round(straddle, 2), "implied_move_pct": round(straddle / spot * 100, 1),
           "call_iv": round(call["impliedVolatility"], 3),
           "put_iv": round(put["impliedVolatility"], 3)}
    pd.DataFrame([row]).to_csv(DATA_DIR / "cprt_options.csv", index=False)
    print(f"  options: {exp} ATM straddle implies +/-{row['implied_move_pct']}%")


def main():
    DATA_DIR.mkdir(exist_ok=True)
    print("Fetching prices ...")
    fetch_prices()
    tk = yf.Ticker(TICKER)
    info = tk.info
    print("Fetching CPRT extras ...")
    earnings = fetch_earnings(tk)
    fetch_short_interest(info)
    fetch_street(info)
    fetch_options(tk, earnings)


if __name__ == "__main__":
    main()
