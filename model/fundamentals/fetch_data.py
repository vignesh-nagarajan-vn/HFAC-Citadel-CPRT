"""
Download the public data for the industry and market share work.

  data/fundamentals/rba_filings.csv          RB Global 10-Q/10-K list with URLs
  data/fundamentals/rba_automotive_lots.csv  automotive lots sold by quarter, parsed from filings
  data/fundamentals/macro/<SERIES>.csv       FRED monthly series (see config.FRED)

Copart unit growth and industry claim stats are not machine readable (earnings calls, CCC reports).
Those live in hand-entered CSVs next to this data with a source on every row.

Usage: SEC_UA="Your Name you@school.edu" python model/fundamentals/fetch_data.py
"""

import html
import io
import json
import os
import re
import time
import urllib.error
import urllib.request

import pandas as pd

from config import FRED, MACRO_DIR, DATA_DIR, RBA_CIK, SEC_UA_DEFAULT

UA = {"User-Agent": os.environ.get("SEC_UA", SEC_UA_DEFAULT)}
FRED_UA = {"User-Agent": "curl/8.0"}  # FRED rejects the SEC-style agent


def get(url, headers=UA):
    req = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "ignore")


def to_text(raw):
    t = re.sub(r"<[^>]+>", " ", raw)
    t = html.unescape(t).replace("​", " ")
    return re.sub(r"\s+", " ", t)


# ---------------------------------------------------------------- RB Global lots
def rba_filings(since="2023-04-01"):
    sub = json.loads(get(f"https://data.sec.gov/submissions/CIK{int(RBA_CIK):010d}.json"))
    r = pd.DataFrame(sub["filings"]["recent"])
    r = r[r["form"].isin(["10-Q", "10-K"]) & (r["filingDate"] >= since)].copy()
    r["url"] = [f"https://www.sec.gov/Archives/edgar/data/{int(RBA_CIK)}/{a.replace('-', '')}/{d}"
                for a, d in zip(r["accessionNumber"], r["primaryDocument"])]
    return r[["form", "filingDate", "reportDate", "url"]].sort_values("reportDate")


LOTS = re.compile(r"lots sold.{0,500}?Automotive\s+([\d,]+\.\d)\s+([\d,]+\.\d)", re.I)


def parse_lots(text):
    """First Automotive row in the lots-sold-by-sector table: (current, prior-year) in thousands."""
    m = LOTS.search(text[text.lower().find("lots sold by sector"):] if "lots sold by sector"
                    in text.lower() else text)
    if not m:
        return None
    return tuple(float(x.replace(",", "")) for x in m.groups())


def build_quarters(rows):
    """
    rows: (period_end, kind, value, filed). Keep the latest filing for each period (recasts win),
    then back out Q4 as the fiscal year less Q1-Q3.
    """
    df = pd.DataFrame(rows, columns=["period_end", "kind", "lots_k", "filed", "source"])
    df = df.sort_values("filed").drop_duplicates(["period_end", "kind"], keep="last")
    q = df[df["kind"] == "Q"].set_index("period_end")
    out = [dict(period_end=p, lots_k=r["lots_k"], method="reported", source=r["source"])
           for p, r in q.iterrows()]
    for _, fy in df[df["kind"] == "FY"].iterrows():
        yr = fy["period_end"].year
        parts = [pd.Timestamp(f"{yr}-{m}") for m in ("03-31", "06-30", "09-30")]
        if all(p in q.index for p in parts):
            out.append(dict(period_end=pd.Timestamp(f"{yr}-12-31"),
                            lots_k=round(fy["lots_k"] - q.loc[parts, "lots_k"].sum(), 1),
                            method="FY less Q1-Q3", source=fy["source"]))
    res = pd.DataFrame(out).sort_values("period_end")
    # Q1 2023 is an 11-day IAA stub (deal closed Mar 20, 2023): not comparable
    res = res[res["period_end"] > "2023-03-31"]
    res["quarter"] = res["period_end"].dt.to_period("Q").astype(str)
    return res[["quarter", "period_end", "lots_k", "method", "source"]]


def fetch_rba_lots():
    filings = rba_filings()
    filings.to_csv(DATA_DIR / "rba_filings.csv", index=False)
    rows = []
    for _, f in filings.iterrows():
        text = to_text(get(f["url"]))
        vals = parse_lots(text)
        time.sleep(0.2)
        if vals is None:
            print(f"  {f['reportDate']} {f['form']}: lots table not found")
            continue
        end = pd.Timestamp(f["reportDate"])
        kind = "FY" if f["form"] == "10-K" else "Q"
        prior = end - pd.DateOffset(years=1)
        rows.append((end, kind, vals[0], f["filingDate"], f["url"]))
        rows.append((prior, kind, vals[1], f["filingDate"], f["url"]))
        print(f"  {f['reportDate']} {f['form']}: automotive {vals[0]:,.1f}k vs {vals[1]:,.1f}k")
    lots = build_quarters(rows)
    lots.to_csv(DATA_DIR / "rba_automotive_lots.csv", index=False)
    print(f"  wrote {len(lots)} quarters, {lots['quarter'].iloc[0]} to {lots['quarter'].iloc[-1]}")


# -------------------------------------------------------------------------- FRED
def fetch_bls(sid, start=2007, end=2026):
    """CPI series straight from BLS (FRED's CSV endpoint drops some of them). 10-year windows."""
    rows = []
    for y0 in range(start, end + 1, 10):
        url = (f"https://api.bls.gov/publicAPI/v2/timeseries/data/{sid}"
               f"?startyear={y0}&endyear={min(y0 + 9, end)}")
        for d in json.loads(get(url, FRED_UA))["Results"]["series"][0]["data"]:
            if d["period"].startswith("M") and d["period"] != "M13" and d["value"] != "-":
                rows.append((f"{d['year']}-{d['period'][1:]}-01", float(d["value"])))
    return pd.DataFrame(sorted(rows), columns=["date", sid])


def fetch_fred():
    MACRO_DIR.mkdir(parents=True, exist_ok=True)
    for sid, name in FRED.items():
        if sid.startswith("CUSR"):
            df = fetch_bls(sid)
            df.to_csv(MACRO_DIR / f"{sid}.csv", index=False)
            print(f"  {sid}: {name}, {len(df)} rows to {df['date'].iloc[-1]} (BLS)")
            continue
        for attempt in range(4):
            try:
                raw = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", FRED_UA)
            except urllib.error.URLError:
                raw = ""
            if raw.lstrip().lower().startswith(("observation_date", "date")):
                break
            time.sleep(3 * (attempt + 1))
        else:
            print(f"  {sid}: FRED did not return CSV, skipped")
            continue
        df = pd.read_csv(io.StringIO(raw))
        df.columns = ["date", sid]
        df.to_csv(MACRO_DIR / f"{sid}.csv", index=False)
        print(f"  {sid}: {name}, {len(df)} rows to {df['date'].iloc[-1]}")


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("Fetching RB Global automotive lots from SEC ...")
    fetch_rba_lots()
    print("Fetching FRED macro series ...")
    fetch_fred()


if __name__ == "__main__":
    main()
