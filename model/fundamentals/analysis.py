"""
Industry and market share studies for the CPRT short. Reads data/fundamentals/, writes to output/.

  growth_gap      quarterly unit growth: RB Global automotive lots vs Copart units
  share_shift     Copart share of the two-player (Copart + IAA) salvage pool, FY25 vs FY26
  lost_customer   what the one lost insurer is worth, from management's own ex-customer number
  macro_table     insurance and repair inflation, miles driven, car sales, transit vs 2019
"""

import pandas as pd

from config import (CPRT_FY26_SERVICE_REV_M, CPRT_FY26_UNITS_M, DATA_DIR,
                    FISCAL_TO_CAL_LAG_MONTHS, FRED, MACRO_DIR, OUT_DIR)


def load():
    lots = pd.read_csv(DATA_DIR / "rba_automotive_lots.csv", parse_dates=["period_end"])
    cprt = pd.read_csv(DATA_DIR / "copart_unit_growth.csv", parse_dates=["period_end"])
    return lots, cprt


# -------------------------------------------------------------------- growth gap
def growth_gap(lots, cprt):
    lots = lots.set_index("quarter")["lots_k"]
    q = cprt[cprt["fiscal_period"].str.startswith("Q")].copy()
    q["cal_quarter"] = (q["period_end"] - pd.DateOffset(months=FISCAL_TO_CAL_LAG_MONTHS)) \
        .dt.to_period("Q").astype(str)
    prior = (pd.PeriodIndex(q["cal_quarter"], freq="Q") - 4).astype(str)
    q["rba_lots_k"] = q["cal_quarter"].map(lots)
    q["rba_lots_yoy"] = [round((lots.get(c) / lots.get(p) - 1) * 100, 1)
                         if c in lots and p in lots else None
                         for c, p in zip(q["cal_quarter"], prior)]
    q["gap_vs_cprt_global"] = (q["rba_lots_yoy"] - q["global_units_yoy"]).round(1)
    q["gap_vs_cprt_us_ins"] = (q["rba_lots_yoy"] - q["us_ins_yoy"]).round(1)
    cols = ["fiscal_period", "cal_quarter", "rba_lots_k", "rba_lots_yoy", "global_units_yoy",
            "global_ins_yoy", "us_ins_yoy", "gap_vs_cprt_global", "gap_vs_cprt_us_ins"]
    return q[cols].reset_index(drop=True)


# ------------------------------------------------------------------- share shift
def trailing_lots(lots, fy_end):
    """Four calendar quarters matched to a Copart fiscal year (Aug-Jul -> Jul-Jun)."""
    end = (pd.Timestamp(fy_end) - pd.DateOffset(months=FISCAL_TO_CAL_LAG_MONTHS)).to_period("Q")
    qs = [str(end - i) for i in range(4)]
    s = lots.set_index("quarter")["lots_k"]
    return s.loc[qs].sum() / 1000, qs[-1], qs[0]


def share_shift(lots, cprt):
    fy = cprt.set_index("fiscal_period")
    g = fy.loc["FY26", "global_units_yoy"] / 100
    rba26, q0, q1 = trailing_lots(lots, "2026-07-31")
    rba25, _, _ = trailing_lots(lots, "2025-07-31")
    rows = []
    for u26 in CPRT_FY26_UNITS_M:
        u25 = u26 / (1 + g)
        s25, s26 = u25 / (u25 + rba25), u26 / (u26 + rba26)
        at_constant = (u26 + rba26) * s25
        lost = at_constant - u26
        rows.append({
            "cprt_fy26_units_m": u26, "cprt_fy25_units_m": round(u25, 3),
            "iaa_lots_fy25_m": round(rba25, 3), "iaa_lots_fy26_m": round(rba26, 3),
            "cprt_share_fy25_%": round(s25 * 100, 1), "cprt_share_fy26_%": round(s26 * 100, 1),
            "share_change_pts": round((s26 - s25) * 100, 1),
            "units_lost_to_share_k": int(round(lost * 1000)),
            "units_lost_%_of_cprt": round(lost / u26 * 100, 1),
            "service_rev_at_risk_$m": int(round(lost * CPRT_FY26_SERVICE_REV_M / u26)),
        })
    out = pd.DataFrame(rows)
    out.attrs["window"] = f"IAA lots {q0} to {q1} vs Copart FY26 (Aug 2025-Jul 2026)"
    out.attrs["iaa_growth"] = rba26 / rba25 - 1
    out.attrs["cprt_growth"] = g
    out.attrs["pool_growth"] = (out.loc[0, "cprt_fy26_units_m"] + rba26) / \
        (out.loc[0, "cprt_fy25_units_m"] + rba25) - 1
    return out


# ----------------------------------------------------------------- lost customer
def lost_customer(cprt):
    """Management: ex one customer, Q4 FY26 U.S. insurance assignments +2.3% instead of -7.5%."""
    reported, ex = -7.5, 2.3
    return {"reported_%": reported, "ex_customer_%": ex, "swing_pts": ex - reported,
            "customer_share_of_us_ins_%": round((ex - reported) / (100 + ex) * 100, 1)}


# ------------------------------------------------------------------------- macro
def macro_series():
    out = {}
    for sid in FRED:
        p = MACRO_DIR / f"{sid}.csv"
        if p.exists():
            s = pd.read_csv(p, parse_dates=["date"]).set_index("date")[sid]
            out[sid] = pd.to_numeric(s, errors="coerce").dropna()
    return out


def macro_table(m):
    rows = []

    def add(name, s):
        last = s.index[-1]
        base = s[s.index.year == 2019].mean()
        rows.append({"series": name, "latest": last.strftime("%b %Y"),
                     "yoy_%": round((s.iloc[-1] / s.iloc[-13] - 1) * 100, 1),
                     "vs_2019_avg_%": round((s.iloc[-1] / base - 1) * 100, 1)})

    for sid in ["CPIAUCSL", "CUSR0000SETE", "CUSR0000SETD", "CUSR0000SETA02"]:
        if sid in m:
            add(FRED[sid], m[sid])
    if "TRFVOLUSM227NFWA" in m:
        add("Vehicle miles traveled, 12m sum", m["TRFVOLUSM227NFWA"].rolling(12).sum().dropna())
    if "TOTALSA" in m:
        add("Light vehicle sales, SAAR", m["TOTALSA"])
    if "TRANSIT" in m:
        add("Public transit ridership, 12m sum", m["TRANSIT"].rolling(12).sum().dropna())
    return pd.DataFrame(rows)


# -------------------------------------------------------------------------- run
def run():
    OUT_DIR.mkdir(exist_ok=True)
    lots, cprt = load()
    gap = growth_gap(lots, cprt)
    share = share_shift(lots, cprt)
    cust = lost_customer(cprt)
    m = macro_series()
    mt = macro_table(m)

    gap.to_csv(OUT_DIR / "growth_gap.csv", index=False)
    share.to_csv(OUT_DIR / "share_shift.csv", index=False)
    mt.to_csv(OUT_DIR / "macro_table.csv", index=False)
    return {"lots": lots, "cprt": cprt, "gap": gap, "share": share, "customer": cust,
            "macro": m, "macro_table": mt}
