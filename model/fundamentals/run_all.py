"""
Run the industry and market share work.

  python model/fundamentals/run_all.py             # fetch SEC + macro data, then analyze
  python model/fundamentals/run_all.py --no-fetch  # reuse data/fundamentals/ on disk

Writes to model/fundamentals/output/:
  industry_figure.png   growth gap, share shift, macro index
  summary.md            findings, each tied to a number and a source
  *.csv                 study tables
"""

import argparse

import pandas as pd

import charts
from analysis import run
from config import OUT_DIR


def md_table(df):
    cols = list(df.columns)
    rows = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        rows.append("| " + " | ".join("" if pd.isna(v) else f"{v:g}" if isinstance(v, float)
                                      else str(v) for v in r) + " |")
    return "\n".join(rows)


def build_summary(r):
    sh, g, c, mt = r["share"], r["gap"], r["customer"], r["macro_table"].set_index("series")
    s = sh.iloc[0]
    last = g.iloc[-1]
    ins, rep = mt.loc["CPI: motor vehicle insurance"], mt.loc["CPI: motor vehicle maintenance and repair"]
    vmt, trn = mt.loc["Vehicle miles traveled, 12m sum"], mt.loc["Public transit ridership, 12m sum"]
    return "\n".join([
        "# CPRT industry and market share: research summary",
        "",
        "Internal notes. Numbers regenerate from `run_all.py`; hand-entered inputs carry a source "
        "in `data/fundamentals/`.",
        "",
        "## 1. Copart is losing share to IAA (RB Global)",
        "",
        f"- **Share of the two-player salvage pool fell {abs(s['share_change_pts']):.1f} pts in one year**, "
        f"from {s['cprt_share_fy25_%']:.1f}% to {s['cprt_share_fy26_%']:.1f}% "
        f"({sh.attrs['window']}).",
        f"- IAA automotive lots grew {sh.attrs['iaa_growth'] * 100:+.1f}% while Copart units fell "
        f"{sh.attrs['cprt_growth'] * 100:+.1f}%. The combined pool only moved "
        f"{sh.attrs['pool_growth'] * 100:+.1f}%, so most of Copart's decline is share, not market.",
        f"- **Cost of the lost share: ~{s['units_lost_to_share_k']:.0f}k units a year "
        f"({s['units_lost_%_of_cprt']:.1f}% of volume), about ${s['service_rev_at_risk_$m']:.0f}M of "
        f"service revenue** at FY26 revenue per unit.",
        f"- IAA's lot growth beat Copart's U.S. insurance units in every quarter since early 2025. "
        f"Latest gap: {last['gap_vs_cprt_us_ins']:.0f} pts ({last['cal_quarter']}: IAA "
        f"{last['rba_lots_yoy']:+.1f}% vs Copart {last['us_ins_yoy']:+.1f}%).",
        f"- **One lost insurer explains most of it.** Management said Q4 FY26 U.S. insurance "
        f"assignments would be {c['ex_customer_%']:+.1f}% without one customer loss, vs "
        f"{c['reported_%']:+.1f}% reported. That customer was ~{c['customer_share_of_us_ins_%']:.0f}% "
        f"of Copart's U.S. insurance volume. Press reports name Progressive (now the #1 U.S. auto "
        f"insurer), moving from ~75% to ~90% IAA. Neither company has confirmed the name.",
        "",
        "Share sensitivity to the Copart unit anchor (management only says \"more than 4 million\"):",
        "",
        md_table(sh[["cprt_fy26_units_m", "cprt_share_fy25_%", "cprt_share_fy26_%",
                     "share_change_pts", "units_lost_to_share_k", "service_rev_at_risk_$m"]]),
        "",
        "Quarterly unit growth (Copart fiscal quarter matched to the calendar quarter ending a "
        "month earlier):",
        "",
        md_table(g[["fiscal_period", "cal_quarter", "rba_lots_yoy", "global_units_yoy",
                    "us_ins_yoy", "gap_vs_cprt_us_ins"]]),
        "",
        "Caveats: IAA lots include non-salvage and international units, and Canada. Copart unit "
        "growth comes from earnings calls, not filings. The two-player pool ignores smaller "
        "salvage auctions, so treat the share levels as approximate and the direction as solid.",
        "",
        "## 2. Manheim",
        "",
        "- Manheim (Cox Automotive, private) sells about 8M dealer and off-lease vehicles a year. "
        "It is a wholesale auction, not a salvage auction, and it publishes no unit or share "
        "data, so there is no public way to size a Copart-to-Manheim share shift. The outline's "
        "claim that Copart is losing share to Manheim is not supported by anything we found.",
        "- Where it matters: Copart is pushing into dealer wholesale (dealer units up, BluCar) "
        "and is buying ACV (~800k units a year) for $10.50/share cash. That puts Copart against "
        "Manheim and OPENLANE in a market it has never led. Frame it as a diversification bet "
        "with execution risk, not as share already lost.",
        "",
        "## 3. Macro: fewer claims, not fewer miles",
        "",
        md_table(r["macro_table"]),
        "",
        f"- **Supports the thesis:** repair prices are {rep['vs_2019_avg_%']:+.0f}% vs 2019 "
        f"({rep['yoy_%']:+.1f}% y/y) and insurance {ins['vs_2019_avg_%']:+.0f}%. Drivers raise "
        "deductibles, drop collision cover and skip small claims (CCC: repairable claims -9.7% in "
        "2025). Earned car years are down ~4% y/y. That means fewer claims, and fewer cars "
        "reaching Copart.",
        "- **Structural, and getting worse:** automatic emergency braking cuts rear-end crashes "
        "~50% (IIHS) and becomes mandatory on new U.S. light vehicles from Sep 2029. The fleet "
        "turns over slowly, so crash frequency keeps falling for years.",
        f"- **Does not support the thesis:** miles driven are {vmt['vs_2019_avg_%']:+.1f}% vs 2019 "
        f"and transit ridership is {trn['vs_2019_avg_%']:+.0f}%. People are not driving less or "
        "moving to transit. Robotaxis are too small to matter (Waymo ~500k paid rides a week). "
        "Drop those two points, or reframe them as long-term options.",
        f"- **Biggest risk to the short:** auto insurance CPI is now {ins['yoy_%']:+.1f}% y/y. "
        "Cheaper premiums could bring back collision cover and small claims, and that would make "
        "the claims drop look cyclical. Track this with Pranav's Bloomberg pulls.",
        "- Total-loss frequency is at a record (23.3% in Q2 2026). That lifts price per car but "
        "not the car count. Copart's revenue per unit rose 5.4% in Q4 FY26 while total revenue "
        "grew only 2.4%.",
        "",
        "Sources: `data/fundamentals/industry_stats.csv` (URL on every row), "
        "`data/fundamentals/copart_unit_growth.csv`, `data/fundamentals/rba_filings.csv`.",
    ])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--no-fetch", action="store_true")
    a = p.parse_args()
    if not a.no_fetch:
        import fetch_data
        fetch_data.main()

    r = run()
    charts.industry_figure(r, OUT_DIR / "industry_figure.png")
    summary = build_summary(r)
    (OUT_DIR / "summary.md").write_text(summary + "\n", encoding="utf-8")
    print(summary)
    print(f"\nFiles written to {OUT_DIR}")


if __name__ == "__main__":
    main()
