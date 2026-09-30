# CPRT industry and market share: research summary

Internal notes. Numbers regenerate from `run_all.py`; hand-entered inputs carry a source in `data/fundamentals/`.

## 1. Copart is losing share to IAA (RB Global)

- **Share of the two-player salvage pool fell 2.6 pts in one year**, from 63.9% to 61.4% (IAA lots 2025Q3 to 2026Q2 vs Copart FY26 (Aug 2025-Jul 2026)).
- IAA automotive lots grew +5.4% while Copart units fell -5.5%. The combined pool only moved -1.6%, so most of Copart's decline is share, not market.
- **Cost of the lost share: ~167k units a year (4.2% of volume), about $166M of service revenue** at FY26 revenue per unit.
- IAA's lot growth beat Copart's U.S. insurance units in every quarter since early 2025. Latest gap: 18 pts (2026Q2: IAA +10.6% vs Copart -7.5%).
- **One lost insurer explains most of it.** Management said Q4 FY26 U.S. insurance assignments would be +2.3% without one customer loss, vs -7.5% reported. That customer was ~10% of Copart's U.S. insurance volume. Press reports name Progressive (now the #1 U.S. auto insurer), moving from ~75% to ~90% IAA. Neither company has confirmed the name.

Share sensitivity to the Copart unit anchor (management only says "more than 4 million"):

| cprt_fy26_units_m | cprt_share_fy25_% | cprt_share_fy26_% | share_change_pts | units_lost_to_share_k | service_rev_at_risk_$m |
|---|---|---|---|---|---|
| 4 | 63.9 | 61.4 | -2.6 | 167 | 166 |
| 4.25 | 65.3 | 62.8 | -2.5 | 171 | 159 |
| 4.5 | 66.6 | 64.1 | -2.5 | 174 | 153 |

Quarterly unit growth (Copart fiscal quarter matched to the calendar quarter ending a month earlier):

| fiscal_period | cal_quarter | rba_lots_yoy | global_units_yoy | us_ins_yoy | gap_vs_cprt_us_ins |
|---|---|---|---|---|---|
| Q2 FY25 | 2024Q4 | 6.7 |  | 9 | -2.3 |
| Q3 FY25 | 2025Q1 | 7 |  | -0.9 | 7.9 |
| Q4 FY25 | 2025Q2 | 8.8 |  | -2.1 | 10.9 |
| Q1 FY26 | 2025Q3 | 8.6 | -6.7 | -9.5 | 18.1 |
| Q2 FY26 | 2025Q4 | 2.2 | -8 | -10.7 | 12.9 |
| Q3 FY26 | 2026Q1 | 0.9 | -2.4 | -4.2 | 5.1 |
| Q4 FY26 | 2026Q2 | 10.6 | -2.9 | -7.5 | 18.1 |

Caveats: IAA lots include non-salvage and international units, and Canada. Copart unit growth comes from earnings calls, not filings. The two-player pool ignores smaller salvage auctions, so treat the share levels as approximate and the direction as solid.

## 2. Manheim

- Manheim (Cox Automotive, private) sells about 8M dealer and off-lease vehicles a year. It is a wholesale auction, not a salvage auction, and it publishes no unit or share data, so there is no public way to size a Copart-to-Manheim share shift. The outline's claim that Copart is losing share to Manheim is not supported by anything we found.
- Where it matters: Copart is pushing into dealer wholesale (dealer units up, BluCar) and is buying ACV (~800k units a year) for $10.50/share cash. That puts Copart against Manheim and OPENLANE in a market it has never led. Frame it as a diversification bet with execution risk, not as share already lost.

## 3. Macro: fewer claims, not fewer miles

| series | latest | yoy_% | vs_2019_avg_% |
|---|---|---|---|
| CPI: all items | Aug 2026 | 3.7 | 30.7 |
| CPI: motor vehicle insurance | Aug 2026 | -5.1 | 48.8 |
| CPI: motor vehicle maintenance and repair | Aug 2026 | 7.8 | 57.1 |
| CPI: used cars and trucks | Aug 2026 | -2.3 | 29.5 |
| Vehicle miles traveled, 12m sum | Jul 2026 | 0.8 | 2.5 |
| Light vehicle sales, SAAR | Aug 2026 | 1.4 | -2.9 |
| Public transit ridership, 12m sum | May 2026 | 2.2 | -17.9 |

- **Supports the thesis:** repair prices are +57% vs 2019 (+7.8% y/y) and insurance +49%. Drivers raise deductibles, drop collision cover and skip small claims (CCC: repairable claims -9.7% in 2025). Earned car years are down ~4% y/y. That means fewer claims, and fewer cars reaching Copart.
- **Structural, and getting worse:** automatic emergency braking cuts rear-end crashes ~50% (IIHS) and becomes mandatory on new U.S. light vehicles from Sep 2029. The fleet turns over slowly, so crash frequency keeps falling for years.
- **Does not support the thesis:** miles driven are +2.5% vs 2019 and transit ridership is -18%. People are not driving less or moving to transit. Robotaxis are too small to matter (Waymo ~500k paid rides a week). Drop those two points, or reframe them as long-term options.
- **Biggest risk to the short:** auto insurance CPI is now -5.1% y/y. Cheaper premiums could bring back collision cover and small claims, and that would make the claims drop look cyclical. Track this with Pranav's Bloomberg pulls.
- Total-loss frequency is at a record (23.3% in Q2 2026). That lifts price per car but not the car count. Copart's revenue per unit rose 5.4% in Q4 FY26 while total revenue grew only 2.4%.

Sources: `data/fundamentals/industry_stats.csv` (URL on every row), `data/fundamentals/copart_unit_growth.csv`, `data/fundamentals/rba_filings.csv`.
