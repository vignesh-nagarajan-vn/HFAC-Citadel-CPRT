"""Pure indicator functions. Input is a DataFrame with Open, High, Low, Close, Volume."""

import numpy as np
import pandas as pd


def load(path):
    return pd.read_csv(path, parse_dates=["Date"], index_col="Date").sort_index()


def rsi(close, n=14):
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + gain / loss)


def resampled_rsi(close, rule, n=14):
    return rsi(close.resample(rule).last().dropna(), n)


def atr(df, n=14):
    prev = df["Close"].shift()
    tr = pd.concat([df["High"] - df["Low"],
                    (df["High"] - prev).abs(),
                    (df["Low"] - prev).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def add_indicators(df):
    c = df["Close"]
    df["SMA50"] = c.rolling(50).mean()
    df["SMA200"] = c.rolling(200).mean()
    mid, sd = c.rolling(20).mean(), c.rolling(20).std()
    df["BB_up"], df["BB_lo"] = mid + 2 * sd, mid - 2 * sd
    df["RSI14"] = rsi(c)
    ema12, ema26 = c.ewm(span=12, adjust=False).mean(), c.ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_sig"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["OBV"] = (np.sign(c.diff()).fillna(0) * df["Volume"]).cumsum()
    df["Vol50"] = df["Volume"].rolling(50).mean()
    df["ATR14"] = atr(df)
    df["DD"] = c / c.cummax() - 1          # drawdown from all-time high
    df["Dist200"] = c / df["SMA200"] - 1   # stretch vs 200-day
    ret = np.log(c).diff()
    df["RV30"] = ret.rolling(21).std() * np.sqrt(252)
    df["RV252"] = ret.rolling(252).std() * np.sqrt(252)
    return df
