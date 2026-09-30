> $\color{red}\textsf{We originally planned to pitch NKE long (buy the dip). After early research we switched to a CPRT short.}$
- The old repo is kept for reference: [HFAC-Citadel-NKE](https://github.com/vignesh-nagarajan-vn/HFAC-Citadel-NKE).

# HFAC x Citadel Stock Pitch: Technical Analysis

Valuation model and supporting analysis for the 2026 HFAC x Citadel Intercollegiate Stock Pitch Competition.

- **Pitch:** Short CPRT, structural decline / value trap thesis, $21.50 target (−21%), 6–12 month horizon
- **Memo covers:** company and industry overview, thesis, valuation, catalysts, risks and mitigants
- **Team lead / HFAC selectee:** Vignesh Nagarajan (submits the application and memo)
- **Team:** Vignesh Nagarajan, Pranav Krishnan, Saatvik Rao
- **Memo:** [v1 (PDF)](memo/CPRT_short_memo_v1.pdf), 2 pages, submission draft
- **Links:** [Competition info](https://www.harvardfac.org/hfac-citadel-pitch-comp), [Google Doc](https://docs.google.com/document/d/1W0Z29RHcEgl9cZ-dJxxJexGG5ROe01wZisUpLVy-FxQ/edit?usp=sharing) (team only)

> **Note:** The memo and model must be anonymized per competition rules (no team, school, or club identifiers). This README is internal.

## Repo Map

```
data/                     price, earnings, short interest, options, street data
  prices/                 daily OHLCV per ticker
  fundamentals/           RB Global lots (SEC), Copart unit growth, industry stats, macro
model/
  technicals/             technical analysis (Python)
    output/               charts, tables, memo snippets
  fundamentals/           market share and macro work (Python)
    output/               industry chart, tables, research summary
memo/                     pitch memo v1 and one-page technical memo (PDF + LaTeX source)
requirements.txt
```

## Memo

[`memo/CPRT_short_memo_v1.pdf`](memo/CPRT_short_memo_v1.pdf) is the 2-page submission draft: overview, industry, three thesis points, valuation, catalysts, risks. Valuation comes from `model/fundamentals/valuation.py` (FY27 bear/base/bull EPS; base $1.44 vs Street $1.75, 15x = $21.50). Rebuild with `pdflatex CPRT_short_memo_v1.tex` from `memo/`. Save later drafts as `_v2`, `_v3` rather than overwriting.

Open items before submission: swap Yahoo consensus and peer multiples for Bloomberg pulls, cross-check the target against the team DCF, and confirm the Progressive details (press reports, not company disclosure).

## Technical Analysis

```
pip install -r requirements.txt
python model/technicals/run_all.py             # fetch data, then analyze
python model/technicals/run_all.py --no-fetch  # reuse data/ on disk
```

| File | Role |
|---|---|
| `fetch_data.py` | Downloads prices, earnings, short interest, options and a Street snapshot into `data/` |
| `indicators.py` | SMA, RSI, MACD, ATR, OBV, drawdown, volatility |
| `analysis.py` | Oversold and downtrend signals, drawdowns vs EPS growth, trailing P/E, earnings reactions, relative strength, levels, short trade plan |
| `charts.py` | Memo and appendix figures |
| `run_all.py` | Runs everything, writes `output/` |

Key outputs: `memo_figure.png` (main memo exhibit), `appendix_figure.png`, `memo_snippets.md` (stats for the memo), `summary.txt` (every number).

One-page technical memo: [`memo/technical_memo.pdf`](memo/technical_memo.pdf). Rebuild with `pdflatex technical_memo.tex` from `memo/` after rerunning the pipeline.

## Industry and Market Share

```
SEC_UA="Your Name you@school.edu" python model/fundamentals/run_all.py   # fetch, then analyze
python model/fundamentals/run_all.py --no-fetch                          # reuse data/fundamentals/
```

| File | Role |
|---|---|
| `fetch_data.py` | Parses RB Global automotive lots from 10-Q/10-K filings, pulls CPI (BLS), miles driven, car sales and transit (FRED) |
| `analysis.py` | Quarterly growth gap, Copart vs IAA share shift, lost-customer sizing, macro vs 2019 |
| `charts.py` | Industry figure |
| `valuation.py` | FY27 scenario EPS, price targets and probability-weighted target (run on its own) |
| `run_all.py` | Runs everything, writes `output/` |

Copart unit growth (earnings calls) and industry claim stats (CCC, IIHS, NHTSA, J.D. Power) are hand-entered in `data/fundamentals/` with a source on every row. Findings: [`model/fundamentals/output/summary.md`](model/fundamentals/output/summary.md).

## Progress & Contributions

- **Vignesh Nagarajan:** Leads the technical analysis. Built the Python pipeline that pulls 32 years of CPRT, benchmark and peer data and studies trend, momentum, oversold and downtrend signals, drawdown history against EPS growth, valuation, earnings reactions, relative strength, short interest and options-implied moves. It produces the memo exhibit, key levels and a stop/target plan for the short. Also built the market share work, which parses RB Global's SEC filings to size Copart's share loss to IAA, and drafted memo v1 with a FY27 scenario valuation. Reviewed the approach with a mentor who has an MBA and prior banking experience.
- **Pranav Krishnan and Saatvik Rao:** Lead the fundamental analysis and equity research, covering Copart's business, the salvage auction industry, competitors (RB Global/IAA, Manheim) and the drivers of structural decline. Pranav is pulling consensus estimates and industry data from the Bloomberg Terminal. Building the DCF model, which projects revenue, margins and free cash flow to reach an intrinsic value per share, with sensitivity tables on WACC and terminal growth to test the short case. Pranav consulted two finance mentors, a Top 5 finalist at NIBC and a macro trader at an asset manager in New York City.
