"""
Figures for the one-page technical memo.

  memo_figure      main exhibit: 2Y price with levels, weekly RSI, EPS growth at each drawdown trough
  appendix_figure  relative performance vs benchmark/rival/peers and 10-year trailing P/E
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import BENCHMARK, CHART_WINDOW, PEERS, SECTOR, SOURCE_NOTE, TICKER
from indicators import resampled_rsi

plt.rcParams.update({"font.size": 7, "axes.titlesize": 7.5, "axes.titleweight": "bold",
                     "axes.titlelocation": "left", "legend.fontsize": 6,
                     "legend.frameon": False, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25,
                     "grid.linewidth": 0.5})

INK, BLUE, RED, GREY, GREEN = "#1a1a1a", "#1f5fa8", "#c0392b", "#9a9a9a", "#2e8b57"
RIVAL = "RBA"


def _level(ax, y, text, color, x_start):
    ax.axhline(y, color=color, ls="--", lw=0.6)
    ax.annotate(f"{text} ${y:.2f}", (x_start, y), xytext=(2, 1.5), textcoords="offset points",
                va="bottom", fontsize=5.8, color=color)


def memo_figure(r, path):
    df = r["df"].iloc[-CHART_WINDOW:]
    plan = r["plan"]
    stop = plan.loc[plan["level"].str.startswith("stop"), "price"].iloc[0]
    tgt = plan[plan["level"].str.startswith("target")]

    fig = plt.figure(figsize=(7.0, 2.9))
    gs = fig.add_gridspec(2, 2, width_ratios=[2.25, 1], height_ratios=[2.6, 1],
                          wspace=0.3, hspace=0.12)
    ax_p = fig.add_subplot(gs[0, 0])
    ax_r = fig.add_subplot(gs[1, 0], sharex=ax_p)
    ax_b = fig.add_subplot(gs[:, 1])

    # price panel
    ax_p.plot(df.index, df["Close"], color=INK, lw=1.0, label=TICKER)
    ax_p.plot(df.index, df["SMA50"], color=BLUE, lw=0.8, label="50-day")
    ax_p.plot(df.index, df["SMA200"], color=RED, lw=0.8, label="200-day")
    lo, hi = sorted([r["levels"]["vol_node_1"], r["levels"]["sma50"]])
    ax_p.axhspan(lo, hi, color=BLUE, alpha=0.12, lw=0)
    # level lines unlabeled; one key in the empty lower-left corner
    names = {"floor_2021_22": "2021-22 floor", "52w_low": "52w low"}
    key = [(f"Stop ${stop:.2f}", RED), (f"Short entry ${lo:.2f}-{hi:.2f}", BLUE)]
    ax_p.axhline(stop, color=RED, ls="--", lw=0.6)
    for i, (_, t) in enumerate(tgt.iloc[1:].iterrows()):
        k = t["level"].replace("target ", "")
        ax_p.axhline(t["price"], color=GREEN, ls="--", lw=0.6)
        key.append((f"Target {i + 1} ${t['price']:.2f} "
                    f"({names.get(k, k.split('x')[0] + 'x trailing EPS')})", GREEN))
    for i, (text, color) in enumerate(key):
        ax_p.text(0.02, 0.58 - i * 0.065, text, transform=ax_p.transAxes, fontsize=5.8,
                  color=color, va="top")
    for d in r["earnings"]["date"]:
        d = np.datetime64(d)
        if d >= np.datetime64(df.index[0]):
            ax_p.axvline(d, color=GREY, lw=0.4, ls=":", zorder=0)
    ax_p.set_title(f"A. {TICKER} price, 2 years (dotted = earnings)")
    ax_p.set_ylabel("Price ($)")
    ax_p.set_ylim(tgt["price"].min() * 0.92, df["Close"].max() * 1.05)
    ax_p.legend(loc="upper right", ncol=3)
    plt.setp(ax_p.get_xticklabels(), visible=False)

    # weekly RSI panel
    w = resampled_rsi(r["df"]["Close"], "W-FRI")
    w = w[w.index >= df.index[0]]
    ax_r.plot(w.index, w, color="#6a3d9a", lw=0.9)
    ax_r.axhline(30, color=GREY, ls="--", lw=0.6)
    ax_r.axhline(70, color=GREY, ls="--", lw=0.6)
    ax_r.fill_between(w.index, w, 30, where=w < 30, color="#6a3d9a", alpha=0.25)
    ax_r.set_ylim(10, 90)
    ax_r.set_ylabel("Weekly RSI")
    ax_r.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
    ax_r.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))

    # EPS growth at each drawdown trough
    dd = r["drawdowns"].dropna(subset=["ttm_eps_yoy_at_trough_%"])
    labels = [pd.Timestamp(d).strftime("%Y") for d in dd["trough_date"]]
    labels[-1] = "Now"
    vals = dd["ttm_eps_yoy_at_trough_%"].values
    depth = dd["depth_%"].values
    colors = [GREY] * (len(vals) - 1) + [RED]
    x = np.arange(len(vals))
    ax_b.bar(x, vals, 0.6, color=colors)
    for xi, v, dp in zip(x, vals, depth):
        ax_b.annotate(f"{v:+.0f}%\n({dp:.0f}%)", (xi, v), xytext=(0, 2 if v >= 0 else -2),
                      textcoords="offset points", ha="center",
                      va="bottom" if v >= 0 else "top", fontsize=5.6)
    ax_b.axhline(0, color=INK, lw=0.6)
    ax_b.set_xticks(x, labels)
    ax_b.set_ylim(min(vals.min() * 3, -15), vals.max() * 1.35)
    ax_b.set_ylabel("Trailing EPS growth y/y at trough (%)")
    ax_b.set_title("B. EPS growth at each 30%+\ndrawdown trough")
    ax_b.text(0.98, 0.97, "(drawdown depth)", transform=ax_b.transAxes, ha="right", va="top",
              fontsize=5.5, color="0.4")

    fig.text(0.01, 0.005, SOURCE_NOTE, fontsize=5.5, color="0.4")
    fig.subplots_adjust(left=0.07, right=0.985, top=0.86, bottom=0.1)
    fig.savefig(path, dpi=300)
    plt.close(fig)


def appendix_figure(r, path):
    from analysis import relative_series

    rel = relative_series(r["prices"], CHART_WINDOW)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.0, 2.4))

    others = [c for c in rel.columns if c.split()[-1] in PEERS and RIVAL not in c]
    lines = {f"vs {BENCHMARK}": (rel[f"vs {BENCHMARK}"], INK),
             f"vs {SECTOR}": (rel[f"vs {SECTOR}"], BLUE),
             f"vs {RIVAL} (IAA owner)": (rel[f"vs {RIVAL}"], RED),
             "vs other peers*": (rel[others].mean(axis=1), "#e67e22")}
    for label, (series, color) in lines.items():
        ax1.plot(series.index, series, lw=0.9, color=color, label=label)
        ax1.annotate(f"{series.iloc[-1]:.0f}", (series.index[-1], series.iloc[-1]),
                     xytext=(3, 0), textcoords="offset points", va="center", fontsize=6,
                     color=color)
    ax1.axhline(100, color=GREY, ls="--", lw=0.6)
    ax1.set_title(f"C. {TICKER} relative performance (2Y, start = 100)")
    ax1.legend(loc="lower left")
    ax1.text(0.99, 0.97, "*" + ", ".join(p.split()[-1] for p in others), transform=ax1.transAxes,
             ha="right", va="top", fontsize=5.5, color="0.4")
    ax1.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))

    pe = r["valuation"]["pe"].iloc[-2520:]
    vs = r["val_summary"]
    ax2.plot(pe.index, pe, color=INK, lw=0.9)
    ax2.axhline(vs["pe_10y_median"], color=GREY, ls="--", lw=0.6)
    ax2.text(0.02, 0.04, f"Dashed: 10-year median {vs['pe_10y_median']:.0f}x",
             transform=ax2.transAxes, fontsize=5.8, color="0.35")
    ax2.annotate(f"Now {vs['pe_now']:.1f}x", (pe.index[-1], pe.iloc[-1]), xytext=(-4, -2),
                 textcoords="offset points", fontsize=6, color=RED, ha="right", va="top")
    ax2.set_title(f"D. {TICKER} trailing P/E, 10 years")
    ax2.set_ylim(0, pe.max() * 1.1)

    fig.text(0.01, 0.005, SOURCE_NOTE, fontsize=5.5, color="0.4")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, dpi=300)
    plt.close(fig)
