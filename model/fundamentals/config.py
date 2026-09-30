"""Shared settings for the CPRT industry and market share work."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "fundamentals"
SEC_DIR = DATA_DIR / "sec"
MACRO_DIR = DATA_DIR / "macro"
OUT_DIR = Path(__file__).resolve().parent / "output"

# SEC asks for a contact in the User-Agent. Set SEC_UA to your own before running.
SEC_UA_DEFAULT = "HFAC Research research@hfac.example"

RBA_CIK = "1046102"   # RB Global, owner of IAA since March 2023

# Copart does not report unit counts in filings. Management said it sold
# "more than 4 million units" in FY2026 (Q4 FY26 call, Sep 10 2026). We use 4.0M as the anchor
# and test 4.25M and 4.5M. The share shift barely moves with the anchor.
CPRT_FY26_UNITS_M = [4.0, 4.25, 4.5]
CPRT_FY26_SERVICE_REV_M = 3969.5   # FY2026 service revenues, Q4 FY26 8-K exhibit 99.1

# Copart fiscal quarters end Oct/Jan/Apr/Jul. Match each to the calendar quarter ending one
# month earlier (two of three months overlap).
FISCAL_TO_CAL_LAG_MONTHS = 1

# FRED series, monthly. Pulled from fredgraph.csv, no API key needed.
FRED = {
    "CPIAUCSL": "CPI: all items",
    "CUSR0000SETE": "CPI: motor vehicle insurance",
    "CUSR0000SETD": "CPI: motor vehicle maintenance and repair",
    "CUSR0000SETA02": "CPI: used cars and trucks",
    "TRFVOLUSM227NFWA": "Vehicle miles traveled (millions, NSA)",
    "TOTALSA": "Light vehicle sales (millions, SAAR)",
    "TRANSIT": "Public transit ridership (thousands)",
}
