"""
Industry figure for our own research (not a memo exhibit yet).

  A  quarterly unit growth: RB Global automotive lots vs Copart U.S. insurance units
  B  two-player salvage share, FY25 vs FY26
  C  insurance and repair prices, miles driven and transit, indexed to 2019
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({"font.size": 7, "axes.titlesize": 7.5, "axes.titleweight": "bold",
                     "axes.titlelocation": "left", "legend.fontsize": 6,
                     "legend.frameon": False, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25,
                     "grid.linewidth": 0.5})

INK, BLUE, RED, GREY, GREEN, ORANGE = "#1a1a1a", "#1f5fa8", "#c0392b", "#9a9a9a", "#2e8b57", "#e67e22"
SOURCE = ("Sources: RB Global 10-Q/10-K, Copart earnings calls, BLS, FRED (FHWA, BEA, APTA); "
          "author calculations")


def industry_figure(r, path):
    fig, (a, b, c) = plt.subplots(1, 3, figsize=(7.0, 2.5),
                                  gridspec_kw={"width_ratios": [1.5, 0.8, 1.3]})

    g = r["gap"]
    x = np.arange(len(g))
    a.bar(x - 0.2, g["rba_lots_yoy"], 0.4, color=RED, label="IAA (RB Global) auto lots")
    a.bar(x + 0.2, g["us_ins_yoy"], 0.4, color=BLUE, label="Copart U.S. insurance units")
    a.axhline(0, color=INK, lw=0.6)
    a.set_xticks(x, [q[-1] + "Q" + q[2:4] for q in g["cal_quarter"]])
    a.set_xlabel("Calendar quarter (Copart quarter ends a month later)", fontsize=5.8)
    a.set_ylim(-13, 21)
    a.set_ylabel("Units y/y (%)")
    a.set_title("A. IAA grows while Copart shrinks")
    a.legend(loc="upper left")

    s = r["share"].iloc[0]
    yrs = ["FY25", "FY26"]
    cp = [s["cprt_share_fy25_%"], s["cprt_share_fy26_%"]]
    b.bar(yrs, cp, 0.55, color=BLUE, label="Copart")
    b.bar(yrs, [100 - v for v in cp], 0.55, bottom=cp, color=RED, label="IAA")
    for i, v in enumerate(cp):
        b.text(i, v / 2, f"{v:.1f}%", ha="center", va="center", color="white", fontsize=6.5)
        b.text(i, v + (100 - v) / 2, f"{100 - v:.1f}%", ha="center", va="center",
               color="white", fontsize=6.5)
    b.set_ylim(0, 100)
    b.set_title(f"B. Two-player share\n({s['share_change_pts']:+.1f} pts, "
                f"~{s['units_lost_to_share_k']:.0f}k units)")
    b.legend(loc="upper center", ncol=2, bbox_to_anchor=(0.5, -0.08))
    b.grid(False)

    m = r["macro"]
    lines = [("CUSR0000SETE", "Auto insurance CPI", RED, None),
             ("CUSR0000SETD", "Repair CPI", ORANGE, None),
             ("TRFVOLUSM227NFWA", "Miles driven (12m)", INK, 12),
             ("TRANSIT", "Transit rides (12m)", GREEN, 12)]
    for sid, label, color, roll in lines:
        if sid not in m:
            continue
        ser = m[sid].rolling(roll).sum().dropna() if roll else m[sid]
        ser = ser[ser.index >= "2019-01-01"]
        ser = ser / ser[ser.index.year == 2019].mean() * 100
        c.plot(ser.index, ser, color=color, lw=0.9, label=label)
        c.annotate(f"{ser.iloc[-1]:.0f}", (ser.index[-1], ser.iloc[-1]), xytext=(2, 0),
                   textcoords="offset points", va="center", fontsize=5.8, color=color)
    c.axhline(100, color=GREY, ls="--", lw=0.6)
    c.set_title("C. Index, 2019 = 100")
    c.xaxis.set_major_locator(matplotlib.dates.YearLocator(2))
    c.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y"))
    c.set_ylim(20, 170)
    c.legend(loc="lower right")

    fig.text(0.01, 0.005, SOURCE, fontsize=5.3, color="0.4")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=300)
    plt.close(fig)
