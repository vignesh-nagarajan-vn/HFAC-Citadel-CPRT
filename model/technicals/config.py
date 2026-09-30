"""Shared settings for the CPRT technical analysis."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
PRICE_DIR = DATA_DIR / "prices"
OUT_DIR = Path(__file__).resolve().parent / "output"

TICKER = "CPRT"
BENCHMARK = "SPY"
SECTOR = "XLI"
# RBA owns IAA (salvage rival). OPLN is dealer wholesale. LKQ buys salvage parts. KMX is used retail.
# ACVA is left out: it trades at Copart's $10.50 cash offer.
PEERS = ["RBA", "OPLN", "LKQ", "KMX"]
ALL_TICKERS = [TICKER, BENCHMARK, SECTOR] + PEERS

# trading days, matches the 3-12 month pitch horizon
HORIZONS = {"3M": 63, "6M": 126, "12M": 252}

# oversold signal definition (the bull case we have to beat)
RSI_LEVEL = 30
DIST200_LEVEL = -0.20
COOLDOWN = 40

CHART_WINDOW = 504  # 2 years of trading days
SOURCE_NOTE = "Source: Yahoo Finance, author calculations"
