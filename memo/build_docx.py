"""Build the Word version of the CPRT short memo (mirrors CPRT_short_memo_v1.tex).

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
OUT = HERE / "CPRT_short_memo_v1.docx"
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

    # Recommendation box
    box = doc.add_table(rows=1, cols=1)
    cell_margins(box, top=60, bottom=60, left=100, right=100)
    cell = box.cell(0, 0)
    cell.width = text_width
    shade(cell, "EEF2F7")
    p = cell.paragraphs[0]
    spacing(p, after=0)
    add_runs(
        p,
        "**Recommendation: short CPRT, price target $21.50 (21% downside).** Copart runs a toll road "
        "on wrecked cars, and fewer cars are using the road. U.S. collision claim frequency keeps falling "
        "(−3.4% y/y). Drivers carry higher deductibles and skip small claims, and cars are getting harder "
        "to crash. Inside that shrinking pool, Copart is losing share to its only real rival, IAA. The stock "
        "is down 57% and a 17.6x P/E looks cheap next to a 34x ten-year median, so the bull case is “buy "
        "the dip.” We think it is a value trap. Earnings are falling for the first time in any of Copart's "
        "major drawdowns, and consensus still expects FY27 EPS growth of 11%. We see FY27 EPS 18% below the Street.",
    )

    section(doc, "Company overview")
    para(
        doc,
        "Copart sells wrecked and unwanted vehicles through online auctions in the U.S. and abroad "
        "(international was 19% of Q4 FY26 revenue). When an insurer decides a car costs more to fix than it "
        "is worth, it declares a total loss and consigns the car to Copart. Copart tows it, stores it, lists it "
        "and sells it to rebuilders, dismantlers, exporters and dealers, and 38% of U.S. units go to "
        "international buyers. Copart keeps buyer and seller fees; the insurer keeps the proceeds. Roughly 80% "
        "of volume comes from insurance companies. FY26 (July year-end) revenue was $4.67B (85% service fees), "
        "operating income $1.65B and EPS $1.55. Copart has $4.5B of cash and securities, no meaningful debt, "
        "and bought back $1.6B of stock in FY26. In September 2026 it agreed to buy ACV Auctions, a "
        "dealer-to-dealer wholesale marketplace, for $10.50 per share in cash (~$1.8B).",
    )

    section(doc, "Industry: a two-player market fed by insurance claims")
    para(
        doc,
        "U.S. salvage auctions are effectively a duopoly: Copart and IAA (owned by RB Global since 2023). "
        "Supply follows a simple chain: *crash → claim → total loss → auction.* Two forces pull in opposite "
        "directions. Rising repair costs (+57% since 2019) push more claimed cars into total losses, so "
        "total-loss frequency hit a record 23.3% in Q2 2026, up from 15.6% in 2015. That lifts the price of "
        "each car. But the number of claims is falling, and Copart is paid per car. A higher total-loss rate "
        "cannot offset a shrinking base of claims forever: total losses are already nearly a quarter of claims.",
    )

    section(doc, "Thesis 1: The supply of wrecked cars is in structural decline")
    bullets(doc, [
        "**Fewer claims, not fewer miles.** U.S. collision claim frequency fell 3.4% y/y in Copart's latest "
        "quarter, after −7.5% in the quarter to October 2025. Repairable claims fell 9.7% in 2025 (CCC). Yet "
        "miles driven are up 2.5% vs. 2019. People still crash; they file less.",
        "**Insurance got expensive, so drivers self-insure.** Auto insurance prices are up 49% since 2019 and "
        "repair prices up 57%. 26% of policyholders now carry a $1,000+ deductible, and 7% skipped a claim over "
        "rate worries (J.D. Power). Insured vehicle-years (earned car years) fell ~4% y/y. Every dropped "
        "collision policy removes a potential Copart car.",
        "**Cars are getting harder to crash.** Automatic emergency braking cuts rear-end crashes by ~50% "
        "(IIHS), and NHTSA makes it mandatory on all new light vehicles from September 2029. As the fleet turns "
        "over, crash frequency keeps falling for a decade. This is structural, not cyclical.",
    ])

    section(doc, "Thesis 2: Copart is losing share inside a shrinking market")
    bullets(doc, [
        "**IAA is taking share every quarter.** Over the same 12 months, IAA's automotive lots grew 5.4% while "
        "Copart's units fell 5.5%. The combined pool fell only 1.6%, so most of Copart's decline is lost share. "
        "Its share of the two-player pool fell **from 63.9% to 61.4%**: about **167k units and $166M of service "
        "revenue** a year (Exhibit 1B).",
        "**The fastest-growing insurer favors the rival.** Management said Q4 FY26 U.S. insurance assignments "
        "would have *grown* 2.3% without one lost customer, vs. a 7.5% decline reported. That customer was ~10% "
        "of Copart's U.S. insurance volume. Industry reports identify it as Progressive, which became the largest "
        "U.S. auto insurer in 2026 and now sends ~90% of its salvage to IAA. Share is following the insurer that "
        "is winning share.",
        "**IAA fixed its weakness.** Under RB Global, IAA cut cycle times by nearly a week and has beaten the "
        "market on units for six straight quarters. Copart's historic edge over a poorly run rival is narrowing.",
    ])

    section(doc, "Thesis 3: Falling earnings make the “cheap” multiple a trap")
    bullets(doc, [
        "**Margins are already breaking.** In Q4 FY26 revenue rose 2.4%, but gross profit fell 5.5%, operating "
        "income fell 10.6% and EPS fell 14.6%. Yards have fixed costs, and U.S. facility cost per unit rose 14.2% "
        "as volume fell. Higher prices per car (+5.4% revenue per unit) are no longer enough.",
        "**A tenth of EPS is interest income, and it is shrinking.** FY26 other income, mostly Treasury bill "
        "interest, was $182M, about 10% of net income. The ACV deal spends ~$1.8B of that cash, costing ~$0.06 "
        "of EPS before ACV's own losses. Management guides ACV to breakeven, not accretion, until FY28.",
        "**This drawdown is different.** In each of Copart's five prior 30%+ drawdowns with earnings data, "
        "trailing EPS was still growing 10–46%, so buying the dip worked. Today trailing EPS is down 3% and "
        "falling. After weekly oversold signals since 1996, the stock's median 6-month return was −0.3%, vs. "
        "+9.9% on a random day.",
    ])

    p = doc.add_paragraph()
    spacing(p, before=3, after=1)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(FIGURE), width=int(text_width * 0.92))
    p = doc.add_paragraph()
    spacing(p, after=3)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_runs(
        p,
        "**Exhibit 1.** Unit growth, IAA vs. Copart U.S. insurance (A); share of the Copart + IAA salvage pool "
        "(B); insurance and repair prices, miles driven and transit ridership, 2019 = 100 (C).",
        size=8,
    )

    section(doc, "Valuation: FY27 EPS of $1.44, 18% below consensus")
    para(
        doc,
        "We build FY27 EPS from units, revenue per unit and margin. In the base case, units fall 3% as the lost "
        "insurer and falling claims carry into the first half, and revenue per unit rises 4% on higher car "
        "values. Operating margin settles at 33%, near the Q4 FY26 exit rate of 32%, and other income falls to "
        "$110M after the ACV payment. That gives **EPS of $1.44 vs. the Street's $1.75**. At 15x, a discount to "
        "share-gaining RB Global (16.8x forward) and a premium to salvage-parts buyer LKQ (7.4x), the base target "
        "is **$21.50**. That implies 9.7x EV/EBITDA, below today's 11.1x.",
    )
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
        "**ACV closing (by end of 2026).** Cash leaves the balance sheet, interest income falls, and ACV's losses "
        "consolidate. That exposes Copart to dealer wholesale, a market led by Manheim and OPENLANE where Copart "
        "has no edge.",
        "**Monthly claims data.** Continued declines in collision frequency and repairable claims (CCC, insurer "
        "disclosures) keep pressure on the unit outlook.",
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
