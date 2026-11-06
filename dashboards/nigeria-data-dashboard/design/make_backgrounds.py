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
    ("Overview", "economy-overview", 328),
    ("Economy size", "economy-size", 360),
    ("FAAC in real terms", "real-terms", 392),
    ("Presidents", "presidents", 424),
    ("ELECTIONS", "section", 470),
    ("Results", None, 488),
    ("INFO", "section", 534),
    ("About", "about", 552),
]
NAV_H = 28

STANDARD_FILTERS = [
    # (label, label x, slicer box). DATES (From / To months) added 2026-11-05:
    # the To month is the latest month for every measure.
    ("PERIOD", 234, (278, 78, 504, 106)),
    ("DATES", 520, (562, 78, 742, 106)),
    ("ZONE", 758, (792, 78, 946, 106)),
    ("STATE", 962, (998, 78, 1110, 106)),
    ("CURRENCY", 1126, (1192, 78, 1244, 106)),
]
FILTER_SEPARATORS = [512, 750, 954, 1118]

# Economy pages: a years range slicer and a president dropdown. No currency switch: each
# chart's title says which currency it shows.
ECONOMY_FILTERS = [
    ("YEARS", 234, (282, 78, 560, 106)),
    ("PRESIDENT", 588, (660, 78, 860, 106)),
]
ECONOMY_SEPARATORS = [574]

# Sidebar footer, per section (None = dashboard-wide pages like About)
FOOTER = {
    "FAAC": [
        "Source: FAAC monthly",
        "disbursement reports,",
        "via MotherDuck.",
        "36 states; FCT isn't",
        "in the reports.",
    ],
    "ECONOMY": [
        "Source: World Bank",
        "(exchange rate, CPI,",
        "GDP, population), via",
        "MotherDuck. Can differ",
        "from NBS headlines.",
    ],
    None: [
        "Sources: FAAC monthly",
        "disbursement reports",
        "and the World Bank,",
        "via MotherDuck.",
    ],
}

# Cards per page: (x1, y1, x2, y2, static label or None, style)
#   style: "card" plain, "kpi" green top strip, "narr" gold left strip
LAYOUT = {
    "overview": {
        "title": "Overview",
        "filters": STANDARD_FILTERS,
        "seps": FILTER_SEPARATORS,
        # Look-and-feel upgrade (2026-11-05): the KPI cards and the banner are HTML
        # visuals that draw their own boxes, so the background only holds the chart cards
        "cards": [
            (216, 232, 776, 640, None, "card"),
            (792, 232, 1256, 460, None, "card"),
            (792, 472, 1256, 640, None, "card"),
        ],
        "visuals": [
            ("Slicer: Period (field parameter, tiles)", (278, 78, 504, 106)),
            ("Slicer: Date range From (dropdown)", (562, 78, 648, 106)),
            ("Slicer: Date range To (dropdown)", (656, 78, 742, 106)),
            ("Slicer: Zone (dropdown)", (792, 78, 946, 106)),
            ("Slicer: State (dropdown)", (998, 78, 1110, 106)),
            ("Slicer: Currency ₦/$ (dropdown)", (1192, 78, 1244, 106)),
            ("HTML: freshness strip", (716, 8, 1256, 68)),
            ("HTML: flip cards Gross, Deductions, Net, Exchange rate", (216, 124, 1256, 220)),
            (
                "Line chart: gross vs net, last 24 months (TT - Overview Month)",
                (226, 242, 766, 630),
            ),
            ("HTML: rotating shelf, top 5 states", (792, 232, 1256, 460)),
            ("100% stacked bar: revenue mix, latest period (dynamic title)", (802, 482, 1246, 630)),
            ("HTML: insight banner", (216, 654, 1256, 704)),
        ],
    },
    "states": {
        "title": "States",
        "filters": STANDARD_FILTERS,
        "seps": FILTER_SEPARATORS,
        # Look-and-feel upgrade (2026-11-05): no card row; the map fills the left column and the
        # insight banner (an HTML visual) sits below both cards
        "cards": [
            (216, 124, 756, 640, None, "card"),
            (772, 124, 1256, 640, None, "card"),
        ],
        "visuals": [
            ("Slicers: Period, Dates (From, To), Zone, State, Currency", (278, 78, 1244, 106)),
            ("HTML: freshness strip", (716, 8, 1256, 68)),
            (
                "Shape map: net received by state (TT - State Detail, HTML card)",
                (226, 134, 746, 630),
            ),
            ("Bar chart: Zone > State drill, coloured by zone, labels", (782, 134, 1246, 604)),
            ("HTML: zone legend", (790, 610, 1240, 630)),
            ("HTML: insight banner", (216, 654, 1256, 704)),
        ],
    },
    "revenue-mix": {
        "title": "Revenue mix",
        "filters": STANDARD_FILTERS,
        "seps": FILTER_SEPARATORS,
        # Look-and-feel upgrade (2026-11-05): shorter cards leave room for the insight banner
        "cards": [
            (216, 124, 1256, 392, None, "card"),
            (216, 404, 728, 640, None, "card"),
            (744, 404, 1256, 640, None, "card"),
        ],
        "visuals": [
            ("Slicers: Period, Dates (From, To), Zone, State, Currency", (278, 78, 1244, 106)),
            ("HTML: freshness strip", (716, 8, 1256, 68)),
            ("Stacked area: revenue lines over time (TT - Revenue Month)", (226, 134, 1246, 382)),
            ("Bar chart: oil derivation by state, coloured by zone", (226, 414, 718, 594)),
            ("HTML: zone legend", (234, 610, 710, 630)),
            ("Table: revenue lines, this vs previous period, share bars", (754, 414, 1246, 630)),
            ("HTML: insight banner", (216, 654, 1256, 704)),
        ],
    },
    "deductions": {
        "title": "Deductions",
        "filters": STANDARD_FILTERS,
        "seps": FILTER_SEPARATORS,
        # Look-and-feel upgrade (2026-11-05): shorter cards leave room for the insight banner
        "cards": [
            (216, 124, 840, 386, None, "card"),
            (856, 124, 1256, 386, None, "card"),
            (216, 398, 1256, 640, None, "card"),
        ],
        "visuals": [
            ("Slicers: Period, Dates (From, To), Zone, State, Currency", (278, 78, 1244, 106)),
            ("HTML: freshness strip", (716, 8, 1256, 68)),
            ("Line chart: deduction lines over time (TT - Deductions Month)", (226, 134, 830, 376)),
            ("Bar chart: external debt by state, coloured by zone", (866, 134, 1246, 350)),
            ("HTML: zone legend", (872, 356, 1240, 376)),
            ("Matrix: state x line, green heat (TT - Metric Detail)", (226, 408, 1246, 630)),
            ("HTML: insight banner", (216, 654, 1256, 704)),
        ],
    },
    "compare": {
        "title": "Compare",
        # All filters as dropdowns in one row, with the date range (agreed 2026-11-05)
        "filters": [
            ("COMPARE BY", 234, (300, 78, 410, 106)),
            ("A", 424, (438, 78, 528, 106)),
            ("B", 542, (556, 78, 646, 106)),
            ("BASIS", 662, (702, 78, 842, 106)),
            ("CURRENCY", 856, (922, 78, 982, 106)),
            ("DATES", 996, (1040, 78, 1244, 106)),
        ],
        "seps": [418, 536, 654, 850, 990],
        "cards": [
            (216, 124, 1256, 624, None, "card"),
        ],
        "visuals": [
            ("Slicers: Compare by, A, B, Basis, Currency, Dates", (300, 78, 1244, 106)),
            ("HTML: freshness strip", (716, 8, 1256, 68)),
            ("Text: side names and meta, basis label", (226, 130, 1246, 156)),
            ("Table: A value and bar, metric, change, B bar and value", (226, 164, 1246, 614)),
            ("HTML: insight banner with legend", (216, 636, 1256, 704)),
        ],
    },
    "economy-overview": {
        "title": "Overview",
        "section": "ECONOMY",
        "slug": "overview",
        "filters": ECONOMY_FILTERS,
        "seps": ECONOMY_SEPARATORS,
        # Look-and-feel upgrade (2026-11-06): flip cards and banner draw their own boxes
        "cards": [
            (216, 232, 728, 640, None, "card"),
            (744, 232, 1256, 640, None, "card"),
        ],
        "visuals": [
            ("Slicer: Years (between)", (282, 78, 560, 106)),
            ("Slicer: President (dropdown)", (660, 78, 860, 106)),
            ("HTML: freshness strip", (716, 8, 1256, 68)),
            ("HTML: flip cards Inflation, Naira, Growth, GDP per person", (216, 124, 1256, 220)),
            (
                "Line chart: inflation by month, by president (TT - Inflation Month)",
                (226, 242, 718, 630),
            ),
            ("HTML: Inflation_explain_html, hidden until the bookmark", (216, 232, 728, 640)),
            ("Buttons: What it means / Back to chart (inflation)", (580, 238, 716, 266)),
            (
                "Line chart: naira per US dollar by month, by president (TT - Inflation Month)",
                (754, 242, 1246, 630),
            ),
            ("HTML: Naira_explain_html, hidden until the bookmark", (744, 232, 1256, 640)),
            ("Buttons: What it means / Back to chart (naira)", (1108, 238, 1244, 266)),
            ("HTML: Economy_insight_html key takeaway", (216, 654, 1256, 704)),
        ],
    },
    "economy-size": {
        "title": "Economy size",
        "section": "ECONOMY",
        "slug": "size",
        "filters": ECONOMY_FILTERS,
        "seps": ECONOMY_SEPARATORS,
        # Look-and-feel upgrade (2026-11-06): four equal chart cards, banner draws its own box
        "cards": [
            (216, 124, 728, 376, None, "card"),
            (744, 124, 1256, 376, None, "card"),
            (216, 388, 728, 640, None, "card"),
            (744, 388, 1256, 640, None, "card"),
        ],
        "visuals": [
            ("Slicer: Years (between)", (282, 78, 560, 106)),
            ("Slicer: President (dropdown)", (660, 78, 860, 106)),
            ("HTML: freshness strip", (716, 8, 1256, 68)),
            ("Columns: GDP in naira by president (TT - GDP Naira Year)", (226, 132, 718, 344)),
            ("HTML: President_legend_html (naira chart)", (232, 348, 712, 368)),
            ("Columns: GDP in dollars by president (TT - GDP Dollar Year)", (754, 132, 1246, 344)),
            ("HTML: President_legend_html (dollar chart)", (760, 348, 1240, 368)),
            ("Columns: real GDP growth + population line (TT - Growth Year)", (226, 396, 718, 632)),
            ("Line: GDP per person, US dollars (TT - Per Person Year)", (754, 396, 1246, 632)),
            ("HTML: <chart>_explain_html per card, hidden until bookmark", (216, 124, 1256, 640)),
            ("Buttons: What it means / Back to chart, top right of cards", (580, 132, 716, 160)),
            ("HTML: GDP_insight_html key takeaway", (216, 654, 1256, 704)),
        ],
    },
    "real-terms": {
        "title": "FAAC in real terms",
        "section": "ECONOMY",
        "slug": "real_terms",
        "filters": ECONOMY_FILTERS + [("PRICES", 890, (940, 78, 1244, 106))],
        "seps": ECONOMY_SEPARATORS + [876],
        "cards": [
            (216, 128, 464, 216, "FIRST MONTH", "kpi"),
            (480, 128, 728, 216, "LATEST MONTH", "kpi"),
            (744, 128, 992, 216, "CHANGE, AS PAID", "kpi"),
            (1008, 128, 1256, 216, "CHANGE, IN REAL TERMS", "kpi"),
            (216, 232, 1256, 600, None, "card"),
            (216, 616, 1256, 696, None, "narr"),
        ],
        "visuals": [
            ("Slicer: Years (between)", (282, 78, 560, 106)),
            ("Slicer: President (dropdown)", (660, 78, 860, 106)),
            ("Slicer: Prices, As paid / Today's prices (tiles)", (940, 78, 1244, 106)),
            ("Text: refresh stamp", (1040, 22, 1256, 58)),
            ("KPI group: first month net (as paid and real)", (226, 146, 454, 210)),
            ("KPI group: latest month net", (490, 146, 718, 210)),
            ("KPI group: change as paid", (754, 146, 982, 210)),
            ("KPI group: change in real terms", (1018, 146, 1246, 210)),
            ("Column chart: Net_prices by month (title Real_terms_title)", (226, 242, 1246, 590)),
            ("Text: Real_terms_narrative", (296, 624, 1246, 690)),
        ],
    },
    "presidents": {
        "title": "Presidents",
        "section": "ECONOMY",
        "slug": "presidents",
        # No president filter: this page compares them
        "filters": [("YEARS", 234, (282, 78, 560, 106))],
        "seps": [],
        "cards": [
            (216, 128, 552, 520, "AVERAGE INFLATION", "card"),
            (568, 128, 904, 520, "NAIRA VALUE OVER THE TERM", "card"),
            (920, 128, 1256, 520, "AVERAGE REAL GDP GROWTH", "card"),
            (216, 536, 1256, 600, None, "card"),
            (216, 616, 1256, 696, None, "narr"),
        ],
        "visuals": [
            ("Slicer: Years (between)", (282, 78, 560, 106)),
            ("Text: refresh stamp", (1040, 22, 1256, 58)),
            ("Bar chart: Inflation_yoy by president, in term order", (226, 152, 542, 510)),
            ("Bar chart: Term_naira_change by president", (578, 152, 894, 510)),
            (
                "Bar chart: Real_GDP_growth by president (blank = Before 1999)",
                (930, 152, 1246, 510),
            ),
            ("Table: Term_coverage_text by president (partial terms only)", (226, 544, 1246, 592)),
            ("Text: Administration_narrative", (296, 624, 1246, 690)),
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
    "month": {
        "title": "TT - Economy Month",
        "section": "ECONOMY",
        "size": (320, 200),
        "used_by": "Economy Overview, inflation and naira line charts",
        "labels": [("INFLATION", 14, 48), ("₦ PER $", 118, 48), ("NAIRA VALUE", 222, 48)],
        "hlines": [(14, 40, 306), (14, 96, 306)],
        "vlines": [(110, 48, 86), (214, 48, 86)],
        "visuals": [
            ("Text: Econ_month_tooltip_title (month · president)", (14, 12, 306, 32)),
            ("Card: Inflation_yoy", (14, 62, 104, 86)),
            ("Card: Naira_per_usd", (118, 62, 208, 86)),
            ("Card: Naira_value_change_yoy (coloured by sign)", (222, 62, 306, 86)),
            ("Text: Econ_month_definitions", (14, 104, 306, 192)),
        ],
    },
    "year": {
        "title": "TT - Economy Year",
        "section": "ECONOMY",
        "size": (360, 250),
        "used_by": "Economy size, all four charts",
        "labels": [
            ("GDP (₦)", 16, 48),
            ("GDP ($)", 128, 48),
            ("REAL GROWTH", 240, 48),
            ("PER PERSON ($)", 16, 104),
            ("PER PERSON (₦)", 128, 104),
            ("AVG ₦ PER $", 240, 104),
        ],
        "hlines": [(16, 40, 344), (16, 96, 344), (16, 152, 344)],
        "vlines": [(120, 48, 86), (232, 48, 86), (120, 104, 142), (232, 104, 142)],
        "visuals": [
            ("Text: Econ_year_tooltip_title (year · president)", (16, 12, 344, 32)),
            ("Card: GDP_naira", (16, 62, 112, 86)),
            ("Card: GDP_usd", (128, 62, 224, 86)),
            ("Card: Real_GDP_growth", (240, 62, 344, 86)),
            ("Card: GDP_per_person_usd", (16, 118, 112, 142)),
            ("Card: GDP_per_person_naira", (128, 118, 224, 142)),
            ("Card: avg ₦ per $ (Naira_per_usd)", (240, 118, 344, 142)),
            ("Text: GDP_year_tooltip_text (naira vs dollar change)", (16, 160, 344, 200)),
            ("Text: Econ_year_definitions", (16, 202, 344, 244)),
        ],
    },
    "real-terms": {
        "title": "TT - Real Terms Month",
        "section": "ECONOMY",
        "size": (340, 220),
        "used_by": "FAAC in real terms, the monthly column chart",
        "labels": [("AS PAID", 16, 48), ("× PRICES", 124, 48), ("IN TODAY'S PRICES", 232, 48)],
        "hlines": [(16, 40, 324), (16, 96, 324), (16, 158, 324)],
        "vlines": [(120, 48, 86), (228, 48, 86)],
        "visuals": [
            ("Text: Real_terms_tooltip_title (month · president)", (16, 12, 324, 32)),
            ("Card: Net_paid", (16, 62, 116, 86)),
            ("Card: Price_multiplier", (124, 62, 224, 86)),
            ("Card: Net_today_prices", (232, 62, 324, 86)),
            ("Text: Real_terms_tooltip_text (the calculation in words)", (16, 104, 324, 150)),
            ("Text: Today_prices_definition", (16, 166, 324, 212)),
        ],
    },
    "president": {
        "title": "TT - President Detail",
        "section": "ECONOMY",
        "size": (360, 280),
        "used_by": "Presidents page, all three bar charts",
        "labels": [
            ("AVG INFLATION", 16, 64),
            ("NAIRA VALUE", 128, 64),
            ("AVG REAL GROWTH", 240, 64),
            ("NAIRA PER $", 16, 120),
        ],
        "hlines": [(16, 56, 344), (16, 112, 344), (16, 162, 344)],
        "vlines": [(120, 64, 102), (232, 64, 102)],
        "visuals": [
            ("Text: President_tooltip_title (full name)", (16, 10, 344, 30)),
            ("Text: President_tooltip_subtitle (party, term, months of data)", (16, 32, 344, 50)),
            ("Card: Inflation_yoy", (16, 78, 112, 102)),
            ("Card: Term_naira_change (coloured by sign)", (128, 78, 224, 102)),
            ("Card: Real_GDP_growth", (240, 78, 344, 102)),
            ("Text: Term_rate_text (start rate → end rate)", (16, 134, 344, 154)),
            ("Text: Term_coverage_text (amber, partial terms only)", (16, 170, 344, 190)),
            ("Text: President_definitions", (16, 196, 344, 272)),
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


def draw_sidebar(img: Image.Image, page: str, section: str | None) -> None:
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
    for i, line in enumerate(FOOTER[section]):
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
    return prefix + spec.get("slug", page).replace("-", "_") + ".png"


def render(page: str, spec: dict, out: Path) -> Path:
    img = Image.new("RGBA", (s(W), s(H)), C["canvas"])
    section = spec.get("section", "FAAC")
    draw_sidebar(img, page, section)
    draw_header(img, spec["title"], section)
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


def tooltip_file_name(page: str, spec: dict) -> str:
    """tt_<section>_<page>.png"""
    return f"tt_{spec.get('section', 'FAAC').lower()}_" + page.replace("-", "_") + ".png"


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
    path = out / tooltip_file_name(page, spec)
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
            f"## {spec['title']} (`{tooltip_file_name(page, spec)}`, {tw}×{th})",
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
