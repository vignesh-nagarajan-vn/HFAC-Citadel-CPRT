"""
FY27 (Aug 2026-Jul 2027) scenario EPS and price targets for the CPRT short.

FY26 base from the Q4 FY26 8-K (exhibit 99.1) and 10-K. Street figures are a Yahoo Finance
snapshot (Sep 30 2026) until Bloomberg pulls replace them.

Usage: python model/fundamentals/valuation.py
"""

import pandas as pd

from config import OUT_DIR

PRICE = 27.36
FY26 = {"revenue": 4666.2, "op_income": 1652.6, "net_income": 1484.3, "eps": 1.55,
        "other_income": 182.3,     # FY26 other income, mostly T-bill interest (10-K: -$16.5M, -8.3%)
        "da": 229.4,               # EBITDA $1,882M less operating income
        "tax": 0.193}
CASH = 4489.8                      # cash and securities, Jul 31 2026
DEBT = 88.4
SHARES_BASIC = 926.3
SHARES_DILUTED = 935.0             # basic plus ~9M of options, in line with FY26 dilution
ACV_COST = 169.8 * 10.50           # $10.50 cash x ACV shares outstanding = ~$1.78B
STREET_FY27_EPS = 1.75

# units, revenue per unit, operating margin, other income ($M), exit P/E, probability
SCENARIOS = {
    "bear": dict(units=-0.06, rpu=0.03, margin=0.310, other=100, pe=13, prob=0.25),
    "base": dict(units=-0.03, rpu=0.04, margin=0.330, other=110, pe=15, prob=0.50),
    "bull": dict(units=0.02, rpu=0.05, margin=0.365, other=140, pe=20, prob=0.25),
}


def scenario(s):
    rev = FY26["revenue"] * (1 + s["units"]) * (1 + s["rpu"])
    op = rev * s["margin"]
    ni = (op + s["other"]) * (1 - FY26["tax"])
    eps = ni / SHARES_DILUTED
    net_cash = CASH - DEBT - ACV_COST
    ebitda = op + FY26["da"]
    return {"units_%": s["units"] * 100, "rev_per_unit_%": s["rpu"] * 100,
            "revenue_$m": rev, "op_margin_%": s["margin"] * 100, "op_income_$m": op,
            "other_income_$m": s["other"], "net_income_$m": ni, "eps": eps,
            "eps_vs_street_%": (eps / STREET_FY27_EPS - 1) * 100, "pe": s["pe"],
            "target": eps * s["pe"], "vs_price_%": (eps * s["pe"] / PRICE - 1) * 100,
            "implied_ev_ebitda": (eps * s["pe"] * SHARES_BASIC - net_cash) / ebitda,
            "prob": s["prob"]}


def run():
    df = pd.DataFrame({k: scenario(v) for k, v in SCENARIOS.items()}).T
    weighted = (df["target"] * df["prob"]).sum()
    ev = PRICE * SHARES_BASIC - CASH + DEBT
    context = {
        "price": PRICE, "market_cap_$m": PRICE * SHARES_BASIC, "ev_$m": ev,
        "ev_ebitda_ttm": ev / (FY26["op_income"] + FY26["da"]),
        "pe_ttm": PRICE / FY26["eps"],
        "interest_share_of_eps_%": FY26["other_income"] * (1 - FY26["tax"]) / FY26["net_income"] * 100,
        "acv_cost_$m": ACV_COST,
        "acv_lost_interest_eps": ACV_COST * 0.04 * (1 - FY26["tax"]) / SHARES_DILUTED,
        "weighted_target": weighted, "weighted_vs_price_%": (weighted / PRICE - 1) * 100,
    }
    return df, context


def main():
    OUT_DIR.mkdir(exist_ok=True)
    df, ctx = run()
    df.round(2).to_csv(OUT_DIR / "valuation_scenarios.csv", index_label="scenario")
    pd.Series(ctx).round(2).to_csv(OUT_DIR / "valuation_context.csv", header=["value"])
    print(df.round(2).T.to_string())
    print(pd.Series(ctx).round(2).to_string())


if __name__ == "__main__":
    main()
