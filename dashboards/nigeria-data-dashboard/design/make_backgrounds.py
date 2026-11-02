"""Draw the Nigeria Data Dashboard page backgrounds (FAAC section) and a placement guide.

Every page is laid out on Power BI's 1280x720 canvas in LAYOUT below, drawn at 2x
(2560x1440), and listed in placement.md so visuals can be placed exactly on the grid.
Backgrounds hold only static elements; anything that changes with a selection is a
live Power BI visual placed on top.

Usage, from this folder (Pillow is only needed here, so it isn't a project dependency):
    uv run --no-project --with pillow python make_backgrounds.py

Images go to design/backgrounds/ unless an output folder is given as the first argument.
Fonts are Segoe UI from C:/Windows/Fonts, the same family Power BI uses.
"""

import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

SCALE = 2
W, H = 1280, 720
FONTS = Path("C:/Windows/Fonts")

# Green & White palette (Option A), agreed 2026-11-02
C = {
    "canvas": "#F3F6F4",
    "side": "#0B3D2E",
    "side_ink": "#E4EFE9",
    "active": "#14563F",
    "gold": "#E2B53E",
    "accent_text": "#0E6B45",
    "card": "#FFFFFF",
    "line": "#DCE5E0",
    "title": "#0F2019",
    "muted": "#6B7C73",
    "series1": "#0E6B45",
    "good": "#0E8A5F",
    "bad": "#C93C3C",
    "equal": "#C98A00",
}

SIDEBAR_W = 192
MAIN_X, MAIN_R = 216, 1256  # main content edges (24 px gutters)
FILTER = (MAIN_X, 72, MAIN_R, 112)  # filter bar container

# Sidebar navigation: (label, page or None if the section isn't built yet, y)
NAV = [
    ("FAAC", "section", 118),
    ("Overview", "overview", 136),
    ("States", "states", 168),
    ("Revenue mix", "revenue-mix", 200),
    ("Deductions", "deductions", 232),
    ("Compare", "compare", 264),
    ("ECONOMY", "section", 310),
    ("Indicators", None, 328),
    ("ELECTIONS", "section", 374),
    ("Results", None, 392),
    ("INFO", "section", 438),
    ("About", "about", 456),
]
NAV_H = 28

STANDARD_FILTERS = [
    # (label, label x, slicer box)
    ("PERIOD", 234, (284, 78, 524, 106)),
    ("ZONE", 552, (590, 78, 754, 106)),
    ("STATE", 770, (812, 78, 992, 106)),
    ("CURRENCY", 1020, (1090, 78, 1244, 106)),
]
FILTER_SEPARATORS = [538, 1006]

# Cards per page: (x1, y1, x2, y2, static label or None, style)
#   style: "card" plain, "kpi" green top strip, "narr" gold left strip
LAYOUT = {
    "overview": {
        "title": "Overview",
        "filters": STANDARD_FILTERS,
        "seps": FILTER_SEPARATORS,
        "cards": [
            (216, 128, 464, 216, "GROSS ALLOCATION", "kpi"),
            (480, 128, 728, 216, "DEDUCTIONS", "kpi"),
            (744, 128, 992, 216, "NET RECEIVED", "kpi"),
            (1008, 128, 1256, 216, "EXCHANGE RATE", "kpi"),
            (216, 232, 866, 696, None, "card"),
            (882, 232, 1256, 456, None, "card"),
            (882, 472, 1256, 696, None, "card"),
        ],
        "visuals": [
            ("Slicer: Period (field parameter, tiles)", (284, 78, 524, 106)),
            ("Slicer: Zone (dropdown)", (590, 78, 754, 106)),
            ("Slicer: State (dropdown)", (812, 78, 992, 106)),
            ("Slicer: Currency ₦/$ (tiles)", (1090, 78, 1244, 106)),
            ("Text: refresh stamp + latest data month", (1040, 22, 1256, 58)),
            ("KPI group: Gross (value, sparkline, change line)", (226, 146, 454, 210)),
            ("KPI group: Deductions", (490, 146, 718, 210)),
            ("KPI group: Net received", (754, 146, 982, 210)),
            ("KPI group: Exchange rate", (1018, 146, 1246, 210)),
            ("Line chart: gross vs net, last 24 months (dynamic title)", (226, 242, 856, 686)),
            ("100% stacked bar: revenue mix, latest period (dynamic title)", (892, 242, 1246, 446)),
            ("Bar chart: top 5 states by net (dynamic title)", (892, 482, 1246, 686)),
        ],
    },
    "states": {
        "title": "States",
        "filters": STANDARD_FILTERS,
        "seps": FILTER_SEPARATORS,
        "cards": [
            (216, 128, 760, 504, None, "card"),
            (776, 128, 1256, 696, None, "card"),
            (216, 520, 760, 696, None, "card"),
        ],
        "visuals": [
            ("Slicers: Period, Zone, State, Currency", (284, 78, 1244, 106)),
            ("Text: refresh stamp", (1040, 22, 1256, 58)),
            ("Shape map: net received by state (TT - State Detail tooltip)", (226, 138, 750, 494)),
            ("Bar chart: all 36 states ranked by net (scrolls)", (786, 138, 1246, 686)),
            (
                "Card row: selected state gross, deductions, net, share of national",
                (226, 530, 750, 686),
            ),
        ],
    },
    "revenue-mix": {
        "title": "Revenue mix",
        "filters": STANDARD_FILTERS,
        "seps": FILTER_SEPARATORS,
        "cards": [
            (216, 128, 1256, 440, None, "card"),
            (216, 456, 728, 696, None, "card"),
            (744, 456, 1256, 696, None, "card"),
        ],
        "visuals": [
            ("Slicers: Period, Zone, State, Currency", (284, 78, 1244, 106)),
            ("Text: refresh stamp", (1040, 22, 1256, 58)),
            ("Stacked area: revenue lines over time", (226, 138, 1246, 430)),
            ("Bar chart: oil derivation by state", (226, 466, 718, 686)),
            (
                "Matrix: revenue lines, current vs previous (metric field parameter)",
                (754, 466, 1246, 686),
            ),
        ],
    },
    "deductions": {
        "title": "Deductions",
        "filters": STANDARD_FILTERS,
        "seps": FILTER_SEPARATORS,
        "cards": [
            (216, 128, 866, 440, None, "card"),
            (882, 128, 1256, 440, None, "card"),
            (216, 456, 1256, 696, None, "card"),
        ],
        "visuals": [
            ("Slicers: Period, Zone, State, Currency", (284, 78, 1244, 106)),
            ("Text: refresh stamp", (1040, 22, 1256, 58)),
            ("Stacked column: deductions by type over time", (226, 138, 856, 430)),
            ("Bar chart: deductions as % of gross, by state", (892, 138, 1246, 430)),
            (
                "Matrix: state x deduction type (metric field parameter, tooltips)",
                (226, 466, 1246, 686),
            ),
        ],
    },
    "compare": {
        "title": "Compare",
        "filters": [
            ("COMPARE BY", 234, (312, 78, 620, 106)),
            ("A", 652, (668, 78, 800, 106)),
            ("B", 818, (834, 78, 966, 106)),
            ("BASIS", 996, (1040, 78, 1172, 106)),
            ("", 1186, (1186, 78, 1248, 106)),
        ],
        "seps": [636, 982, 1180],
        "cards": [
            (216, 128, 1256, 616, None, "card"),
            (216, 632, 1256, 696, None, "narr"),
        ],
        "legend": True,
        "visuals": [
            ("Slicer: Compare by (tiles)", (312, 78, 620, 106)),
            ("Slicer: Side A member (dropdown, Compare_A)", (668, 78, 800, 106)),
            ("Slicer: Side B member (dropdown, Compare_B)", (834, 78, 966, 106)),
            ("Slicer: Basis (calculation group, dropdown)", (1040, 78, 1172, 106)),
            ("Slicer: Currency ₦/$ (tiles)", (1186, 78, 1248, 106)),
            ("Text: refresh stamp", (1040, 22, 1256, 58)),
            ("Text: Side A name and meta (right-aligned)", (226, 136, 660, 160)),
            ("Text: basis label, centre", (660, 136, 812, 160)),
            ("Text: Side B name and meta", (812, 136, 1246, 160)),
            (
                "Matrix or table: Side A values + bars (Compare Side = A), right-aligned",
                (226, 168, 660, 606),
            ),
            ("Table: metric names, centre column", (660, 168, 812, 606)),
            ("Matrix or table: Side B values + bars (Compare Side = B)", (812, 168, 1246, 606)),
            ("Text: Comparison_narrative", (296, 638, 990, 690)),
        ],
    },
    "about": {
        "title": "About",
        "section": None,  # the whole dashboard, not one section
        "filters": [],
        "seps": [],
        "cards": [
            (216, 72, 728, 376, "ABOUT THIS DASHBOARD", "card"),
            (744, 72, 1256, 376, "DATA AND PIPELINE", "card"),
            (216, 392, 728, 696, "DEFINITIONS", "card"),
            (744, 392, 1256, 696, "KNOWN GAPS", "card"),
        ],
        "visuals": [
            ("Text: refresh stamp", (1040, 22, 1256, 58)),
            ("Text box: what the dashboard is, who it's for", (230, 100, 714, 366)),
            ("Text box: sources, GitHub pipeline link, daily refresh", (758, 100, 1242, 366)),
            ("Text box: metric definitions (Metric_definition text)", (230, 420, 714, 686)),
            ("Text box: no FCT, no Oct 2024, FAAC from Jan 2020 only", (758, 420, 1242, 686)),
        ],
    },
}

# Tooltip pages (step 5), each on its own custom-size canvas. Power BI draws a tooltip as
# a plain rectangle, so these fill edge to edge: no rounded card, no shadow.
#   labels: (static text, x, y); hlines: (x1, y, x2); vlines: (x, y1, y2)
TOOLTIPS = {
    "metric-detail": {
        "title": "TT - Metric Detail",
        "size": (360, 300),
        "used_by": "KPI cards (Gross, Deductions, Net), Revenue mix and Deductions matrices",
        "labels": [("VS PREVIOUS", 16, 112), ("LAST 6 MONTHS", 16, 202)],
        "hlines": [(16, 104, 344), (16, 194, 344)],
        "vlines": [],
        "visuals": [
            ("Text: Metric_tooltip_title (metric · area)", (16, 10, 344, 28)),
            ("Text: Metric_tooltip_subtitle (basis, currency)", (16, 28, 344, 42)),
            ("Text: Metric_definition", (16, 46, 344, 98)),
            ("Card: current value (Metric_value, Period Calc = Current)", (16, 126, 176, 162)),
            ("Card: previous value (Metric_value, Period Calc = Previous)", (184, 126, 344, 162)),
            ("Text: change % ▲▼■, Growth/Decline, Periodic_text (coloured)", (16, 166, 344, 186)),
            ("Column chart: Metric_value, last 6 months (Last_6_Period_flag)", (16, 216, 344, 256)),
            ("Text: Metric_tooltip_summary", (16, 260, 344, 292)),
        ],
    },
    "state-detail": {
        "title": "TT - State Detail",
        "size": (320, 240),
        "used_by": "States page map and 36-state ranking bar",
        "labels": [
            ("GROSS", 14, 66),
            ("DEDUCTIONS", 118, 66),
            ("NET", 222, 66),
            ("NET, LAST 6 MONTHS", 14, 142),
        ],
        "hlines": [(14, 58, 306), (14, 134, 306)],
        "vlines": [(110, 66, 104), (214, 66, 104)],
        "visuals": [
            ("Text: State_tooltip_title (state name)", (14, 12, 306, 32)),
            ("Text: zone · region · rank of 36 by net", (14, 34, 306, 52)),
            ("Card: Gross (Period Calc = Current)", (14, 80, 104, 104)),
            ("Card: Deductions (Period Calc = Current)", (118, 80, 208, 104)),
            ("Card: Net (Period Calc = Current)", (222, 80, 306, 104)),
            ("Text: net share of national", (14, 110, 306, 128)),
            ("Column chart: Net, last 6 months (Last_6_Period_flag)", (14, 156, 306, 230)),
        ],
    },
    "compare-metric": {
        "title": "TT - Compare Metric",
        "size": (360, 200),
        "used_by": "Compare page, Side A and Side B tables",
        "labels": [("SIDE A", 16, 92), ("SIDE B", 192, 92)],
        "hlines": [(16, 84, 344), (16, 154, 344)],
        "vlines": [(180, 92, 146)],
        "visuals": [
            ("Text: Metric_tooltip_title (metric · basis, currency)", (16, 12, 344, 32)),
            ("Text: Metric_definition", (16, 34, 344, 78)),
            ("Text: Side A name", (16, 104, 172, 120)),
            ("Card: Side A value (Compare Side = A)", (16, 122, 172, 146)),
            ("Text: Side B name", (192, 104, 344, 120)),
            ("Card: Side B value (Compare Side = B)", (192, 122, 344, 146)),
            ("Text: Compare_tooltip_text, ▲▼■ difference (coloured)", (16, 162, 344, 192)),
        ],
    },
}


def s(v: float) -> int:
    return round(v * SCALE)


def box(b: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    return (s(b[0]), s(b[1]), s(b[2]), s(b[3]))


def font(name: str, size: float) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), s(size))


REG, SEMI, BOLD = "segoeui.ttf", "seguisb.ttf", "segoeuib.ttf"


def tracked(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    f: ImageFont.FreeTypeFont,
    fill: str,
    tracking: float,
) -> None:
    """Draw text with letter spacing (Pillow has none built in)."""
    x, y = s(xy[0]), s(xy[1])
    for ch in text:
        draw.text((x, y), ch, font=f, fill=fill)
        x += draw.textlength(ch, font=f) + s(tracking)


def shadow_card(img: Image.Image, b: tuple[float, float, float, float], radius: float) -> None:
    """Soft shadow under a card: a blurred, offset copy of its shape."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x1, y1, x2, y2 = box(b)
    d.rounded_rectangle((x1, y1 + s(1.5), x2, y2 + s(1.5)), radius=s(radius), fill=(11, 61, 46, 34))
    layer = layer.filter(ImageFilter.GaussianBlur(s(3)))
    img.alpha_composite(layer)


def clip(img: Image.Image, layer: Image.Image, mask: Image.Image) -> None:
    """Blend a coloured layer onto the image only where both it and the mask are opaque.

    Pasting with a mask would copy the layer's transparent corner pixels as black.
    """
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
    img.alpha_composite(layer)


def draw_card(
    img: Image.Image, b: tuple[float, float, float, float], style: str, label: str | None
) -> None:
    shadow_card(img, b, 12)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(box(b), radius=s(12), fill=C["card"], outline=C["line"], width=s(1))
    x1, y1, x2, y2 = b
    if style == "kpi":
        # Green top strip, clipped to the card's rounded top edge
        strip = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(strip)
        sd.rounded_rectangle(box(b), radius=s(12), fill=C["series1"])
        mask = Image.new("L", img.size, 0)
        ImageDraw.Draw(mask).rectangle(box((x1, y1, x2, y1 + 4)), fill=255)
        clip(img, strip, mask)
    if style == "narr":
        strip = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(strip).rounded_rectangle(box(b), radius=s(12), fill=C["gold"])
        mask = Image.new("L", img.size, 0)
        ImageDraw.Draw(mask).rectangle(box((x1, y1, x1 + 5, y2)), fill=255)
        clip(img, strip, mask)
        tracked(
            ImageDraw.Draw(img),
            (x1 + 18, (y1 + y2) / 2 - 7),
            "IN SHORT",
            font(BOLD, 9.5),
            C["accent_text"],
            1.4,
        )
    if label:
        lx = x1 + 14
        ly = y1 + (16 if style == "kpi" else 14)
        tracked(ImageDraw.Draw(img), (lx, ly), label, font(SEMI, 9.5), C["muted"], 1.2)


def draw_sidebar(img: Image.Image, page: str) -> None:
    d = ImageDraw.Draw(img)
    d.rectangle(box((0, 0, SIDEBAR_W, H)), fill=C["side"])
    d.text((s(22), s(24)), "NIGERIA", font=font(BOLD, 19), fill=C["side_ink"])
    d.text((s(22), s(46)), "DATA", font=font(BOLD, 19), fill=C["side_ink"])
    tracked(d, (22, 74), "DASHBOARD", font(REG, 9), "#9FB8AC", 1.6)
    for label, target, y in NAV:
        if target == "section":
            tracked(d, (22, y), label, font(SEMI, 8.5), "#7FA493", 1.5)
            continue
        if target == page:
            d.rounded_rectangle(box((14, y, 178, y + NAV_H)), radius=s(8), fill=C["active"])
        dot_fill = C["gold"] if target == page else ("#5E8A77" if target is None else "#9FBFB1")
        cx, cy, r = 28, y + NAV_H / 2, 3
        d.ellipse(box((cx - r, cy - r, cx + r, cy + r)), fill=dot_fill)
        if target is None:
            # Sections not built yet: label and a "SOON" chip live in the background
            d.text((s(40), s(y + 5)), label, font=font(REG, 12), fill="#5E8A77")
            chip = (134, y + 7, 170, y + NAV_H - 7)
            d.rounded_rectangle(box(chip), radius=s(7), outline="#5E8A77", width=s(1))
            tracked(d, (chip[0] + 6, chip[1] + 1.5), "SOON", font(SEMI, 7.5), "#5E8A77", 0.8)
    foot = [
        "Source: FAAC monthly",
        "disbursement reports,",
        "via MotherDuck.",
        "36 states; FCT isn't",
        "in the reports.",
    ]
    for i, line in enumerate(foot):
        d.text((s(22), s(640 + i * 13)), line, font=font(REG, 9), fill="#8FB0A2")


def draw_header(img: Image.Image, title: str, section: str | None) -> None:
    d = ImageDraw.Draw(img)
    eyebrow = "NIGERIA DATA DASHBOARD" + (f"  ·  {section}" if section else "")
    tracked(d, (MAIN_X, 20), eyebrow, font(SEMI, 9.5), C["accent_text"], 1.8)
    d.text((s(MAIN_X), s(30)), title, font=font(SEMI, 25), fill=C["title"])


def draw_filters(img: Image.Image, spec: dict) -> None:
    if not spec["filters"]:
        return
    shadow_card(img, FILTER, 20)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(box(FILTER), radius=s(20), fill=C["card"], outline=C["line"], width=s(1))
    for label, lx, _ in spec["filters"]:
        if label:
            tracked(d, (lx, 85), label, font(SEMI, 8.5), C["muted"], 1.0)
    for sx in spec["seps"]:
        d.line(box((sx, 82, sx, 102)), fill=C["line"], width=s(1))


def draw_legend(img: Image.Image) -> None:
    d = ImageDraw.Draw(img)
    x, y = 1004, 657
    items = [("Better", C["good"]), ("Worse", C["bad"]), ("Equal", C["equal"])]
    f = font(REG, 9.5)
    for text, colour in items:
        d.ellipse(box((x, y + 3, x + 7, y + 10)), fill=colour)
        d.text((s(x + 11), s(y - 1)), text, font=f, fill=C["muted"])
        x += 11 + d.textlength(text, font=f) / SCALE + 14
    d.text((s(1004), s(y + 14)), "Deductions: higher is worse", font=f, fill=C["muted"])


def draw_compare_guides(img: Image.Image) -> None:
    """Thin divider under the side headers of the butterfly card."""
    d = ImageDraw.Draw(img)
    d.line(box((230, 164, 1242, 164)), fill=C["line"], width=s(1))


def file_name(page: str, spec: dict) -> str:
    """bg_<section>_<page>.png, or bg_<page>.png for dashboard-wide pages like About."""
    section = spec.get("section", "FAAC")
    prefix = f"bg_{section.lower()}_" if section else "bg_"
    return prefix + page.replace("-", "_") + ".png"


def render(page: str, spec: dict, out: Path) -> Path:
    img = Image.new("RGBA", (s(W), s(H)), C["canvas"])
    draw_sidebar(img, page)
    draw_header(img, spec["title"], spec.get("section", "FAAC"))
    draw_filters(img, spec)
    for x1, y1, x2, y2, label, style in spec["cards"]:
        draw_card(img, (x1, y1, x2, y2), style, label)
    if page == "compare":
        draw_compare_guides(img)
    if spec.get("legend"):
        draw_legend(img)
    path = out / file_name(page, spec)
    img.convert("RGB").save(path, optimize=True)
    return path


def tooltip_file_name(page: str) -> str:
    return "tt_faac_" + page.replace("-", "_") + ".png"


def render_tooltip(page: str, spec: dict, out: Path) -> Path:
    tw, th = spec["size"]
    img = Image.new("RGBA", (s(tw), s(th)), C["card"])
    d = ImageDraw.Draw(img)
    d.rectangle(box((0, 0, tw, 4)), fill=C["series1"])
    d.rectangle(box((0, 0, tw - 0.5, th - 0.5)), outline=C["line"], width=s(1))
    for text, x, y in spec["labels"]:
        tracked(d, (x, y), text, font(SEMI, 8), C["muted"], 1.1)
    for x1, y, x2 in spec["hlines"]:
        d.line(box((x1, y, x2, y)), fill=C["line"], width=s(1))
    for x, y1, y2 in spec["vlines"]:
        d.line(box((x, y1, x, y2)), fill=C["line"], width=s(1))
    path = out / tooltip_file_name(page)
    img.convert("RGB").save(path, optimize=True)
    return path


def placement_md() -> str:
    lines = [
        "# Visual placement guide",
        "",
        "Positions on Power BI's 1280×720 canvas",
        "(Format → General → Properties → Size and position).",
        "x/y are the top-left corner; w/h the size.",
        "Generated by `make_backgrounds.py` from the same layout as the background images.",
        "",
        "Navigation buttons (every page): blank buttons with text, transparent fill,",
        "page-navigation action, x 14, width 164, height 28, text left-aligned at 26 px padding,",
        "at these y positions:",
        "",
        "| Page | y |",
        "|---|---|",
    ]
    for label, target, y in NAV:
        if target not in ("section", None):
            lines.append(f"| {label} | {y} |")
    for page, spec in LAYOUT.items():
        lines += [
            "",
            f"## {spec['title']} (`{file_name(page, spec)}`)",
            "",
            "| Visual | x | y | w | h |",
            "|---|---|---|---|---|",
        ]
        for name, (x1, y1, x2, y2) in spec["visuals"]:
            lines.append(f"| {name} | {x1} | {y1} | {x2 - x1} | {y2 - y1} |")
    lines += [
        "",
        "# Tooltip pages",
        "",
        "Set up each one: Format page → Page information → Allow use as tooltip on;",
        "Canvas settings → Type Custom, at the size below; hide the page.",
        "On each visual that uses it: Format → General → Tooltips → Type Report page,",
        "Page = the tooltip page.",
    ]
    for page, spec in TOOLTIPS.items():
        tw, th = spec["size"]
        lines += [
            "",
            f"## {spec['title']} (`{tooltip_file_name(page)}`, {tw}×{th})",
            "",
            f"Used by: {spec['used_by']}.",
            "",
            "| Visual | x | y | w | h |",
            "|---|---|---|---|---|",
        ]
        for name, (x1, y1, x2, y2) in spec["visuals"]:
            lines.append(f"| {name} | {x1} | {y1} | {x2 - x1} | {y2 - y1} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    here = Path(__file__).resolve().parent
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else here / "backgrounds"
    out.mkdir(parents=True, exist_ok=True)
    for page, spec in LAYOUT.items():
        print(f"Wrote {render(page, spec, out).name}")
    for page, spec in TOOLTIPS.items():
        print(f"Wrote {render_tooltip(page, spec, out).name}")
    (here / "placement.md").write_text(placement_md(), encoding="utf-8")
    print("Wrote placement.md")


if __name__ == "__main__":
    main()
