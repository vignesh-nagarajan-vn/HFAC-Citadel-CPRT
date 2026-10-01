"""Build the Word version of the CPRT short memo (mirrors CPRT_short_memo_v2.tex).

Usage: python memo/build_docx.py
"""
import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

HERE = Path(__file__).resolve().parent
OUT = HERE / "CPRT_short_memo_v2.docx"
FIGURE = HERE.parent / "model" / "fundamentals" / "output" / "industry_figure.png"

NAVY = RGBColor(0x1F, 0x3A, 0x5F)
GRAY = RGBColor(0x80, 0x80, 0x80)
FONT = "Calibri"
BODY_PT = 9.5


def add_runs(par, text, size=BODY_PT, color=None):
    """Add text with **bold** and *italic* inline markup."""
    for tok in re.split(r"(\*\*.+?\*\*|\*.+?\*)", text):
        if not tok:
            continue
        bold = tok.startswith("**")
        italic = not bold and tok.startswith("*")
        tok = tok.strip("*") if (bold or italic) else tok
        run = par.add_run(tok)
        run.bold = bold
        run.italic = italic
        run.font.size = Pt(size)
        if color is not None:
            run.font.color.rgb = color
    return par


def spacing(par, before=0, after=3, line=1.0):
    fmt = par.paragraph_format
    fmt.space_before = Pt(before)
    fmt.space_after = Pt(after)
    fmt.line_spacing = line


def shade(element, hex_fill):
    pr = element._tc.get_or_add_tcPr() if hasattr(element, "_tc") else element._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    pr.append(shd)


def cell_margins(table, top=20, bottom=20, left=60, right=60):
    tblPr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for side, val in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tblPr.append(mar)


def border(cell, side, sz=8):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = tcPr.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tcPr.append(borders)
    el = OxmlElement(f"w:{side}")
    el.set(qn("w:val"), "single")
    el.set(qn("w:sz"), str(sz))
    el.set(qn("w:color"), "000000")
    borders.append(el)


def booktabs(table, header_rows=1, mid_rows=()):
    """Top/bottom rules plus a rule under the header and above given rows."""
    rows = table.rows
    for c in rows[0].cells:
        border(c, "top", 10)
    for c in rows[header_rows - 1].cells:
        border(c, "bottom", 6)
    for r in mid_rows:
        for c in rows[r].cells:
            border(c, "top", 6)
    for c in rows[-1].cells:
        border(c, "bottom", 10)


def section(doc, title):
    p = doc.add_paragraph()
    spacing(p, before=5, after=1)
    p.paragraph_format.keep_with_next = True
    add_runs(p, f"**{title}**", size=10, color=NAVY)


def para(doc, text, after=3):
    p = doc.add_paragraph()
    spacing(p, after=after)
    return add_runs(p, text)


def bullets(doc, items):
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        spacing(p, after=1)
        p.paragraph_format.left_indent = Inches(0.16)
        p.paragraph_format.first_line_indent = Inches(-0.12)
        add_runs(p, item)


def table(doc, rows, widths, align_right_from=1, size=8, bold_rows=(), mid_rows=()):
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    cell_margins(t)
    for i, row in enumerate(rows):
        for j, text in enumerate(row):
            cell = t.cell(i, j)
            cell.width = widths[j]
            p = cell.paragraphs[0]
            spacing(p, after=0)
            if j >= align_right_from:
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            add_runs(p, f"**{text}**" if (i in bold_rows and text) else text, size=size)
    booktabs(t, mid_rows=mid_rows)
    return t


def build():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.5), Inches(11)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Inches(0.55))
    text_width = sec.page_width - sec.left_margin - sec.right_margin

    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(BODY_PT)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)

    # Header
    p = doc.add_paragraph()
    spacing(p, after=1)
    p.paragraph_format.tab_stops.add_tab_stop(text_width, WD_TAB_ALIGNMENT.RIGHT)
    add_runs(p, "**Copart, Inc. (NASDAQ: CPRT)**\t**SHORT**", size=15, color=NAVY)
    p = doc.add_paragraph()
    spacing(p, after=4)
    add_runs(
        p,
        "Price $27.36 (Sep 30, 2026)  |  Price target $21.50 (−21%)  |  Market cap $25.3B  |  "
        "17.6x P/E  |  11.1x EV/EBITDA  |  6–12 mo.",
        size=8.5,
    )

    # Recommendation box: recommendation, thesis, variant view
    box = doc.add_table(rows=1, cols=1)
    cell_margins(box, top=60, bottom=60, left=100, right=100)
    cell = box.cell(0, 0)
    cell.width = text_width
    shade(cell, "EEF2F7")
    box_pars = [
        "**Recommendation: short CPRT, price target $21.50 (21% downside, 6–12 months).** Copart runs a toll "
        "road on wrecked cars and is paid per car, and fewer cars are using the road.",
        "**Thesis.** (1) *Supply is shrinking for structural reasons:* drivers file fewer collision claims because "
        "insurance and repairs got expensive, and safer cars crash less. (2) *Copart is losing share of what is "
        "left* to IAA, its only real rival. (3) *Earnings are now falling:* fewer cars through fixed-cost yards cut "
        "profit faster than revenue, so the “cheap” multiple is a value trap.",
        "**Variant view.** The Street treats the 57% drawdown as a cyclical dip to buy: the stock trades at 17.6x "
        "P/E vs. a 34x ten-year median, and consensus has FY27 EPS growing 11% to $1.75. We think the unit decline "
        "is structural and share-driven, so it will not reverse with the cycle. We see FY27 EPS of $1.44, 18% "
        "below the Street. Unlike every prior Copart drawdown, earnings are falling this time.",
    ]
    for i, text in enumerate(box_pars):
        p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
        spacing(p, after=0 if i == len(box_pars) - 1 else 2)
        add_runs(p, text)

    section(doc, "Company overview")
    para(
        doc,
        "Copart sells wrecked and unwanted vehicles through online auctions in the U.S. and abroad (19% of Q4 "
        "FY26 revenue is international). When an insurer decides a car costs more to fix than it is worth (a "
        "total loss), it consigns the car to Copart, which tows, stores and sells it to rebuilders, dismantlers, "
        "exporters and dealers for buyer and seller fees. About 80% of volume comes from insurers, so Copart's "
        "revenue depends on how many cars insurers total. FY26 (July year-end) revenue was $4.67B (85% service "
        "fees), operating income $1.65B and EPS $1.55. Copart holds $4.5B of cash and securities with no "
        "meaningful debt, bought back $1.6B of stock in FY26, and in September 2026 agreed to buy dealer "
        "wholesale marketplace ACV Auctions for ~$1.8B in cash.",
    )

    section(doc, "Industry: a two-player market fed by insurance claims")
    para(
        doc,
        "U.S. salvage auctions are effectively a duopoly: Copart and IAA (owned by RB Global since 2023). "
        "Supply follows a simple chain: *crash → claim → total loss → auction.* Rising repair costs push more "
        "claimed cars into total losses (a record 23.3% of claims in Q2 2026, vs. 15.6% in 2015), which lifts "
        "the value of each car. But Copart is paid per car, and the number of claims is falling. With total "
        "losses already near a quarter of claims, a higher total-loss rate can no longer make up for a "
        "shrinking base of claims.",
    )

    section(doc, "Thesis 1: The supply of wrecked cars is in structural decline")
    bullets(doc, [
        "**Expensive insurance and repairs push drivers out of the claims system (Exhibit 1C).** Since 2019, auto "
        "insurance prices are up 49% and repair prices up 57%, far ahead of 31% overall inflation. Drivers respond "
        "by raising deductibles (26% now carry $1,000+), dropping collision cover and paying for small repairs "
        "themselves (7% skipped a claim over rate worries, J.D. Power). Each of these is a crash that never "
        "becomes a claim, and so never becomes a Copart car. That is why collision claim frequency fell 3.4% y/y "
        "in Copart's latest quarter and repairable claims fell 9.7% in 2025 (CCC).",
        "**People are not driving less, so the problem is claims, not traffic (Exhibit 1C).** Miles driven are 2% "
        "above 2019 and transit ridership is still 18% below it, so as many cars are on the road as ever. Crash "
        "exposure has not fallen; claims have. This undercuts the bull case that volume returns as driving "
        "recovers: driving has already recovered and Copart's units still fell. Volume returns only if insurance "
        "gets cheap enough to bring drivers back to filing, and repair costs, still up 7.8% y/y, push the other way.",
        "**Safer cars will shrink the pool for a decade.** Automatic emergency braking cuts rear-end crashes by "
        "~50% (IIHS) and is mandatory on all new U.S. light vehicles from September 2029. As older cars are "
        "replaced, fewer crashes happen at all, which lowers Copart's supply even if claim filing recovers. This "
        "is a structural headwind, not a cycle to wait out.",
    ])

    section(doc, "Thesis 2: Copart is losing share inside a shrinking market")
    bullets(doc, [
        "**IAA is winning the cars Copart loses (Exhibit 1A).** IAA's unit growth has beaten Copart's U.S. "
        "insurance units in every quarter since early 2025, by up to 18 points. If falling claims were the only "
        "problem, both companies would shrink together. Instead, over the last 12 months IAA grew 5.4% while "
        "Copart fell 5.5%, and the combined pool fell only 1.6%. Most of Copart's decline is lost share, not a "
        "weak market.",
        "**The lost share is worth ~$166M of revenue a year (Exhibit 1B).** Copart's share of the two-player pool "
        "fell from 63.9% to 61.4% in one year, about 167k cars. At Copart's fee per car that is $166M of service "
        "revenue, ~4% of the total, moving to a rival. It lands on yards whose costs do not fall with volume, so "
        "the hit to profit is larger than the hit to revenue (Thesis 3).",
        "**The lost customer is the insurer that is growing fastest.** Management said U.S. insurance units would "
        "have *grown* 2.3% in Q4 FY26 without one lost customer, vs. a 7.5% decline reported. Industry reports "
        "name Progressive, now the largest U.S. auto insurer, which sends ~90% of its salvage to IAA. As "
        "Progressive adds policyholders, IAA adds cars automatically. IAA has also cut cycle times by nearly a "
        "week under RB Global, so Copart's old service edge over a poorly run rival is gone.",
    ])

    section(doc, "Thesis 3: Falling earnings make the “cheap” multiple a trap")
    bullets(doc, [
        "**Fewer cars through fixed-cost yards means falling profit.** Copart pays for its yards, tow network and "
        "staff whether 4.0M or 4.5M cars arrive. In Q4 FY26 revenue per car rose 5.4% but U.S. facility cost per "
        "car rose 14.2%, so revenue grew 2.4% while operating income fell 10.6% and EPS fell 14.6%. Higher car "
        "values no longer cover the cost of lost volume, and each further unit decline cuts profit faster than "
        "revenue.",
        "**The cash cushion under EPS is being spent.** Interest on Copart's cash ($182M of other income) was "
        "about 10% of FY26 net income. The ACV deal spends ~$1.8B of that cash, removing ~$0.06 of EPS before "
        "ACV's own losses, and management does not expect ACV to add to earnings until FY28. One support under "
        "EPS goes away just as the core business weakens.",
        "**Why buying the dip fails this time.** In Copart's five prior 30%+ drawdowns, trailing EPS was still "
        "growing 10–46%, so the stock recovered once sentiment turned. Today trailing EPS is down 3% and falling, "
        "and a low P/E is only cheap if earnings hold. Since 1996, buying CPRT after weekly oversold signals "
        "returned a median −0.3% over six months, vs. +9.9% on a random day.",
    ])

    p = doc.add_paragraph()
    spacing(p, before=3, after=1)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(FIGURE), width=int(text_width * 0.84))
    p = doc.add_paragraph()
    spacing(p, after=3)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_runs(
        p,
        "**Exhibit 1.** (A) Y/y unit growth: IAA has outgrown Copart's U.S. insurance units every quarter since "
        "early 2025. (B) Copart's share of the Copart + IAA pool fell 2.6 pts in a year. (C) 2019 = 100: "
        "insurance and repair prices are up 50%+, pushing drivers to skip claims, while miles driven are flat "
        "and transit is down, so fewer claims does not mean less driving.",
        size=8,
    )

    section(doc, "Valuation: FY27 EPS of $1.44, 18% below consensus")
    para(
        doc,
        "We build FY27 EPS from units, revenue per unit and margin (Exhibit 2). In the base case, units fall 3% "
        "as the lost insurer and falling claims carry into the first half, and revenue per unit rises 4% on "
        "higher car values. Operating margin settles at 33%, near the Q4 FY26 exit rate of 32%, because fixed "
        "yard costs are spread over fewer cars, and other income falls to $110M after the ACV payment. That gives "
        "**EPS of $1.44 vs. the Street's $1.75**. At 15x, a discount to share-gaining RB Global (16.8x forward) "
        "and a premium to salvage-parts buyer LKQ (7.4x), the base target is **$21.50**. That implies 9.7x "
        "EV/EBITDA, below today's 11.1x.",
    )
    p = doc.add_paragraph()
    spacing(p, before=2, after=2)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    add_runs(p, "**Exhibit 2.** FY27 EPS scenarios and price targets", size=8)
    rows = [
        ["Scenario (prob.)", "Units", "Rev./unit", "Op. margin", "FY27 EPS", "vs. Street", "P/E", "Target", "vs. price"],
        ["Bear (25%)", "−6%", "+3%", "31.0%", "$1.30", "−26%", "13x", "$16.84", "−38%"],
        ["Base (50%)", "−3%", "+4%", "33.0%", "$1.44", "−18%", "15x", "$21.54", "−21%"],
        ["Bull (25%)", "+2%", "+5%", "36.5%", "$1.70", "−3%", "20x", "$33.90", "+24%"],
        ["Probability-weighted", "", "", "", "", "", "", "$23.45", "−14%"],
    ]
    widths = [Inches(1.35)] + [Inches(0.72)] * 8
    table(doc, rows, widths, bold_rows=(0, 2), mid_rows=(4,))
    p = para(
        doc,
        "Probability-weighted, the expected downside (~20 pts) is more than 3x the expected upside (~6 pts), and "
        "even the bull case needs a unit recovery that no data point supports today.",
    )
    p.paragraph_format.space_before = Pt(3)

    section(doc, "Catalysts")
    bullets(doc, [
        "**Q1 FY27 earnings (Nov 19, 2026).** Consensus is $0.40 vs. $0.41 a year ago. Another quarter of falling "
        "U.S. insurance units and cost-per-unit growth should push FY27 estimates toward our $1.44.",
        "**RB Global Q3 results (early Nov 2026).** A seventh straight quarter of IAA unit gains would confirm the "
        "share shift is not a one-customer event.",
        "**ACV closing (by end of 2026).** Interest income falls and ACV's losses consolidate, pushing Copart into "
        "dealer wholesale, led by Manheim and OPENLANE, where it has no edge.",
        "**Monthly claims data.** Further declines in collision frequency and repairable claims (CCC, insurers) "
        "keep pressure on units.",
    ])

    section(doc, "Risks and mitigants")
    risks = [
        ["Risk", "Mitigant"],
        ["Claims recover as insurance prices fall (auto insurance CPI −5.1% y/y)",
         "Repair prices are still rising (+7.8% y/y) and deductibles are sticky, so small claims stay unfiled. "
         "AEB lowers crash frequency whatever insurance costs. We cover if collision frequency turns positive for "
         "two quarters."],
        ["Easier comps once the lost customer laps in early 2027",
         "The base case already assumes a smaller decline (units −3%). The margin and interest-income pressure "
         "does not depend on the comp."],
        ["Hurricane season brings a burst of catastrophe volume",
         "Catastrophe units are one-off and flatter revenue and units, not the trend. Copart reports volumes "
         "ex-catastrophe."],
        ["Buybacks and the ACV story support the stock",
         "ACV uses ~$1.8B of the cash that funded buybacks. Short interest is only 4.6% of float (3.3 days to "
         "cover), so squeeze risk is low."],
        ["Stock already down 57%",
         "Cheap on trailing P/E, but on our FY27 EPS the stock trades at 19x with falling units. We size the "
         "position with a stop at $32.60 (above the 50-day average and the 23.6% retracement)."],
    ]
    table(doc, risks, [int(text_width * 0.29), int(text_width * 0.71)], align_right_from=99,
          bold_rows=(0,))

    p = doc.add_paragraph()
    spacing(p, before=4, after=0)
    add_runs(
        p,
        "Sources: Copart FY2026 10-K and Q4 FY26 earnings release and calls (FY25–FY26); RB Global 10-Q/10-K "
        "filings; CCC Intelligent Solutions Crash Course 2026; J.D. Power 2025 U.S. Auto Claims Satisfaction "
        "Study; IIHS; NHTSA FMVSS 127; BLS CPI; FRED (FHWA, APTA); Yahoo Finance prices and consensus (Sep 30, "
        "2026); industry press on insurer allocations. Share estimates use Copart's stated >4M FY26 units; the "
        "share shift is −2.5 to −2.6 pts across a 4.0–4.5M unit range. Estimates and targets are the authors'.",
        size=7,
        color=GRAY,
    )

    doc.save(OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    build()
