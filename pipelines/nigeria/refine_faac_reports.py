"""Nigeria project: turn the OAGF's monthly FAAC reports into tidy CSV files in the repo.

The OAGF (Office of the Accountant-General of the Federation) publishes each month's FAAC
report as a PDF. This script reads the state table (Table III) of every report, checks it
against itself and writes the figures to data/nigeria/faac/oagf/. It runs on a laptop: the
PDFs (about 200 MB) stay outside git, and the daily pipeline only loads the CSV files.

Usage (from the repo root):
    uv run --group refine python pipelines/nigeria/refine_faac_reports.py
    uv run --group refine python pipelines/nigeria/refine_faac_reports.py --pdf-dir <folder> \
        --excel-dir <folder>

--pdf-dir defaults to FAAC_OAGF_PDF_DIR and --excel-dir to FAAC_RAW_EXCEL_DIR (from .env).
A month whose PDF fingerprint (sha256) is unchanged since the last run is reused from the CSV
files instead of being read again. If any month fails a check, nothing is written.
"""

import argparse
import csv
import hashlib
import itertools
import os
import re
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import openpyxl
import pdfplumber
from dotenv import load_dotenv

load_dotenv()

# Bump when the reading logic changes, so every month is read again instead of reused
READER_VERSION = "2"

# 2019 is incomplete (6 months), so it waits until a full year of reports is available
FIRST_SHARED_MONTH = "2020-01"

OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "nigeria" / "faac" / "oagf"

# Months whose PDF state table can't be used, read from the OAGF's raw Excel report instead.
# Paths are relative to --excel-dir.
EXCEL_EXCEPTIONS = {
    "2021-09": (
        "FAAC 21/Disbursement September, 2021.xlsx",
        "PDF shows the full ecology fund with no NDDC/HYPPADEC transfer and its Total Gross "
        "leaves out derivation; the Excel report applies the transfer and adds up",
    ),
    "2023-04": (
        "FAAC 23/Disbursement April, 2023.xlsx",
        "PDF state and LGA tables are a copy of February 2022 (only Table I is April 2023)",
    ),
}

# Months with no LGA figures at all: neither the PDF nor the Excel report has a usable table
NO_LGA_MONTHS = {
    "2021-09": (
        "the Excel report has no LGA detail sheet, and the PDF's LGA table doesn't add up for "
        "Abia, Bauchi, Kano, Yobe, Zamfara (no TOTAL row) and the FCT"
    ),
}

# May 2023: the right half of the LGA table (Katsina to the FCT) prints a Total Allocation
# that is not the sum of the row's own columns, for councils and TOTAL rows alike
MAY_2023_RIGHT_HALF = (
    "Total Allocation column, in the right half of the LGA table, doesn't match the "
    "row's other columns for the councils or the TOTAL row"
)

# Mistakes in the LGA tables of the published reports, kept as printed. The check that finds
# them records a note instead of failing the month, and known_report_errors.csv lists them so
# dbt can flag those states. Key: (shared month, state as the state table prints it).
KNOWN_REPORT_ERRORS = {
    ("2020-06", "KANO"): "TOTAL row's Total Allocation (N2.19bn) doesn't match its own columns "
    "(N6.36bn, as the councils add up)",
    ("2021-02", "KANO"): (
        "councils 1-25 print the N58,259.97 deduction as positive and add it to their totals, "
        "and Kano's 44 councils don't add up to its TOTAL row in any column; the TOTAL row "
        "agrees with the LGA summary page"
    ),
    ("2021-03", "KANO"): "TOTAL row's VAT is N18,000,000 more than the councils add up to",
    ("2021-03", "KATSINA"): "TOTAL row's ecological fund is N79.2m more than the councils "
    "add up to",
    ("2021-05", "KADUNA"): "councils' Total Allocation uses other councils' VAT (from Makarfi "
    "on, council 1's, 2's and so on; Lere's includes N1.56bn); the TOTAL row is right",
    ("2021-05", "KANO"): "TOTAL row's deduction is N69.9m more than the councils', and its "
    "Total Allocation N69.9m less",
    ("2021-08", "RIVERS"): "TOTAL row leaves out council 1, Ahoada, in every column",
    ("2022-02", "KANO"): "councils 1-25's Total Allocation leaves out the non-oil excess account "
    "and counts ecology twice; the TOTAL row is right",
    ("2022-03", "KANO"): "councils 1-25 have the 50% ecology transfer to NDDC/HYPPADEC taken "
    "off, councils 26-44 and the TOTAL row don't",
    ("2022-03", "KATSINA"): "councils' Total Allocation column is wrong; the TOTAL row is right",
    ("2022-03", "KEBBI"): "councils' Total Allocation column is wrong; the TOTAL row is right",
    ("2022-03", "KOGI"): "councils' Total Allocation column is wrong; the TOTAL row is right",
    ("2022-10", "ABIA"): "councils' Total Allocation leaves out the FOREX equalisation and EMTL "
    "columns; the TOTAL row includes them",
    ("2022-10", "KATSINA"): "councils' Total Allocation column is wrong; the TOTAL row is right",
    ("2023-02", "KANO"): "councils' non-oil excess account figures are February 2022's, and the "
    "TOTAL row doesn't match the councils in that column and ecology",
    ("2023-03", "KANO"): "councils 1-25's Total Allocation leaves out column 3 and counts "
    "ecology twice; the TOTAL row is right",
    ("2023-05", "AKWA IBOM"): "TOTAL row's VAT is N345m, the councils add up to N2.15bn; its "
    "Total Allocation follows the wrong VAT",
    ("2023-05", "ANAMBRA"): "TOTAL row's FOREX equalisation share is N137.4m more than the "
    "councils add up to",
    ("2023-05", "KANO"): "councils add up to N105.7m more than the TOTAL row in two "
    "columns and N600 less in a third",
    ("2023-05", "KATSINA"): MAY_2023_RIGHT_HALF,
    ("2023-05", "KEBBI"): MAY_2023_RIGHT_HALF,
    ("2023-05", "KOGI"): MAY_2023_RIGHT_HALF,
    ("2023-05", "KWARA"): MAY_2023_RIGHT_HALF,
    ("2023-05", "LAGOS"): MAY_2023_RIGHT_HALF,
    ("2023-05", "NASSARAWA"): MAY_2023_RIGHT_HALF,
    ("2023-05", "NIGER"): MAY_2023_RIGHT_HALF,
    ("2023-05", "OGUN"): MAY_2023_RIGHT_HALF,
    ("2023-05", "ONDO"): MAY_2023_RIGHT_HALF,
    ("2023-05", "OSUN"): MAY_2023_RIGHT_HALF,
    ("2023-05", "OYO"): MAY_2023_RIGHT_HALF,
    ("2023-05", "PLATEAU"): MAY_2023_RIGHT_HALF,
    ("2023-05", "RIVERS"): MAY_2023_RIGHT_HALF,
    ("2023-05", "SOKOTO"): MAY_2023_RIGHT_HALF,
    ("2023-05", "TARABA"): MAY_2023_RIGHT_HALF,
    ("2023-05", "YOBE"): MAY_2023_RIGHT_HALF,
    ("2023-05", "ZAMFARA"): MAY_2023_RIGHT_HALF,
    ("2023-05", "FCT"): MAY_2023_RIGHT_HALF,
    ("2023-07", "BAUCHI"): "councils' Total Allocation column is wrong; the TOTAL row is right",
    ("2023-08", "ABIA"): "councils' Total Allocation column is wrong; the TOTAL row is right",
    ("2023-09", "ABIA"): "councils' Total Allocation column is wrong; the TOTAL row is right",
    ("2023-11", "KANO"): "councils' deductions add up to N582.6m more than the TOTAL row's",
    ("2026-02", "KANO"): "TOTAL row's statutory allocation is N50 less than the councils",
    ("2026-03", "KANO"): "TOTAL row's statutory allocation is N30 more than the councils",
    ("2026-05", "KANO"): "councils' Total Net Allocation column is wrong; the TOTAL row is right",
}

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]  # fmt: skip
MONTHS = {name[:3].lower(): number for number, name in enumerate(MONTH_NAMES, start=1)}
STATES = {
    "ABIA", "ADAMAWA", "AKWA IBOM", "ANAMBRA", "BAUCHI", "BAYELSA", "BENUE", "BORNO",
    "CROSS RIVER", "DELTA", "EBONYI", "EDO", "EKITI", "ENUGU", "GOMBE", "IMO", "JIGAWA",
    "KADUNA", "KANO", "KATSINA", "KEBBI", "KOGI", "KWARA", "LAGOS", "NASSARAWA", "NASARAWA",
    "NIGER", "OGUN", "ONDO", "OSUN", "OYO", "PLATEAU", "RIVERS", "SOKOTO", "TARABA", "YOBE",
    "ZAMFARA",
}  # fmt: skip

AMOUNT = re.compile(r"^-?[\d,]*\d\.\d{1,2}$")
DASH = {"-", "–", "—"}
SMALL_INT = re.compile(r"^\d{1,3}$")
# "for the month of November, 2025 Shared in December, 2025": data month, then shared month
TITLE = re.compile(
    r"for the month of\s*([A-Za-z]+)\s*,?\s*(\d{4})\s*,?\s*"
    r"shared\s*(?:in)?\s*([A-Za-z]+)\s*,?\s*(\d{4})",
    re.IGNORECASE,
)
FILE_MONTH = re.compile(r"-([A-Za-z]+)-(\d{4})")
# Lines that are never column headers, written without spaces (see column_headers)
NOT_HEADER = re.compile(r"officeofthe|federationaccountdep|ministryof|^tablei+$|^source:")

# One word or character from pdfplumber: text plus its position on the page
Word = dict[str, Any]


class CheckFailed(Exception):
    """A report failed one of the checks; the message says which and why."""


@dataclass
class Row:
    beneficiary: str
    row_type: str  # state, other or total
    lgc_count: int | None
    values: dict[str, float]


@dataclass
class LgaRow:
    state: str  # as the state table prints it
    lga_sn: int | None
    lga: str  # empty on a state's total row
    row_type: str  # lga or total
    values: dict[str, float]


@dataclass
class Report:
    shared_month: str
    source_type: str  # pdf or excel
    file_name: str
    sha256: str
    page: int | None
    columns: list[tuple[str, str]] = field(default_factory=list)  # (column_id, header)
    rows: list[Row] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    lga_columns: list[tuple[str, str]] = field(default_factory=list)
    lga_rows: list[LgaRow] = field(default_factory=list)


def month_number(name: str) -> int:
    return MONTHS[name[:3].lower()]


def next_month(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


def header_key(header: str) -> str:
    """Letters and digits only, so letter-spaced and re-wrapped headers compare equal."""
    return re.sub(r"[^a-z0-9%]", "", header.lower())


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def to_amount(text: str) -> float:
    return 0.0 if text in DASH else float(text.replace(",", ""))


def group_lines(words: list[Word], tolerance: float = 1.5, edge: str = "top") -> list[list[Word]]:
    """Group words into lines by their top (or bottom), left to right.

    Words on one line share their bottom (the baseline) better than their top: a figure
    shrunk or enlarged to fit its cell sits higher or lower at the top.
    """
    lines: list[list[Word]] = []
    for w in sorted(words, key=lambda w: (w[edge], w["x0"])):
        if lines and abs(lines[-1][0][edge] - w[edge]) <= tolerance:
            lines[-1].append(w)
        else:
            lines.append([w])
    for line in lines:
        line.sort(key=lambda w: w["x0"])
    return lines


def tidy_line(line: list[Word], glue_gap: float = 0.6) -> list[Word]:
    """Glue split figures back together and turn bracketed figures into negatives.

    The PDFs print the first digit of many figures as a separate piece that touches the rest
    ("8" + ",145,202,571.72"), and some negatives as "(" followed by the figure. glue_gap
    is in points and scales with the font (the LGA tables go down to 0.6 pt).
    """
    glued: list[Word] = []
    for w in line:
        prev = glued[-1] if glued else None
        if (
            prev
            and w["x0"] - prev["x1"] < glue_gap
            and re.match(r"^[\d,.]", w["text"])
            and re.match(r"^\(?[\d,.]+$", prev["text"])
        ):
            prev["text"] += w["text"]
            prev["x1"] = w["x1"]
        elif (
            prev
            and prev["text"] in DASH
            and w["x0"] - prev["x1"] < glue_gap * 3.3
            and re.match(r"^[\d,]+\.\d", w["text"])
        ):
            # A minus sign printed as its own piece, under half a character before the number
            # (Sep 2022). An empty cell's dash sits mid-cell, well away from the next figure.
            prev["text"] = "-" + w["text"]
            prev["x1"] = w["x1"]
        elif prev and prev["text"] == "(" and re.match(r"^[\d,.]+\)?$", w["text"]):
            prev["text"] = "-" + w["text"].rstrip(")")
            prev["x1"] = w["x1"]
        elif prev and w["text"] == ")" and re.match(r"^[(\-]?[\d,.]+$", prev["text"]):
            # At very small sizes the closing bracket is a piece of its own
            prev["text"] = "-" + prev["text"].lstrip("(-")
            prev["x1"] = w["x1"]
        else:
            glued.append(dict(w))
    # Excel prints ### over a number too wide for its cell; in the PDF the digits survive
    # under it ("1,849,982,094.0#5#" then "#", 2020), so the #s go when a valid figure remains
    glued = [w for w in glued if w["text"].strip("#")]
    for w in glued:
        if "#" in w["text"] and AMOUNT.match(w["text"].replace("#", "").lstrip("(").rstrip(")")):
            w["text"] = w["text"].replace("#", "")
        # A naira sign glued to the figure ("N5,789,470.78", Sep 2022)
        w["text"] = re.sub(r"^(?:=N=|=?N|₦)(?=-?\(?[\d,]+\.\d)", "", w["text"])
        bracketed = re.match(r"^\(([\d,.]+)\)?$", w["text"])
        if bracketed:
            w["text"] = "-" + bracketed.group(1)
    return glued


def column_spans(
    rows: list[list[Word]], tolerance: float = 3.0, merge_gap: float = 25.0
) -> list[tuple[float, float]]:
    """Find the figure columns from the figures themselves.

    Figures are right-aligned, so each column's figures end at about the same x. A dash for
    an empty cell sits elsewhere in the cell, so it starts its own cluster at first. Two
    clusters that never appear in the same row are one column and get merged. Distances are
    in points and scale with the font.
    """
    edges = sorted((w["x1"], row_index) for row_index, row in enumerate(rows) for w in row)
    clusters: list[dict[str, Any]] = []
    for x, row_index in edges:
        if clusters and x - clusters[-1]["right"] <= tolerance:
            clusters[-1]["right"] = x
            clusters[-1]["rows"].add(row_index)
        else:
            clusters.append({"left": x, "right": x, "rows": {row_index}})
    merged = True
    while merged:
        merged = False
        for i in range(len(clusters) - 1):
            a, b = clusters[i], clusters[i + 1]
            if not (a["rows"] & b["rows"]) and b["left"] - a["right"] < merge_gap:
                b["left"] = a["left"]
                b["rows"] |= a["rows"]
                del clusters[i]
                merged = True
                break
    return [(c["left"], c["right"]) for c in clusters]


def printed_column_numbers(lines: list[list[Word]]) -> list[tuple[int, float]]:
    """The row of column numbers under the title ("1 2 3 ... 6=4+5 ..."), with x centres.

    Pieces printed close together ("6", "=", "4", "+5") are joined first. Overlapping header
    text sometimes garbles a number ("Dedu8ctions"), so only the leading digits count.
    """
    for line in lines:
        text = re.sub(r"\s*([=+\-])\s*", r"\1", " ".join(w["text"] for w in line))
        if len(re.findall(r"\b\d+=", text)) < 2:
            continue
        groups: list[Word] = []
        for w in line:
            if groups and w["x0"] - groups[-1]["x1"] < 3:
                groups[-1]["text"] += w["text"]
                groups[-1]["x1"] = w["x1"]
            else:
                groups.append(dict(w))
        numbers = []
        for g in groups:
            digits = re.search(r"\d+", g["text"])
            if digits:
                numbers.append((int(digits.group()), (g["x0"] + g["x1"]) / 2))
        return numbers
    return []


def column_ids(spans: list[tuple[float, float]], numbers: list[tuple[int, float]]) -> list[str]:
    """Name each figure column after the printed number above it.

    Some reports add columns without numbering them; those become 14a, 14b after the
    numbered column before them. Columns 1-3 are S/n, beneficiary and LGC count.
    """
    ids: list[str] = []
    previous_right = 0.0
    base, suffix = "3", 0
    for _left, right in spans:
        hit = [
            n
            for n, centre in numbers
            if n >= 4 and previous_right < centre <= right + 3 and str(n) not in ids
        ]
        if hit:
            base, suffix = str(hit[0]), 0
            ids.append(base)
        else:
            suffix += 1
            ids.append(f"{base}{'abcdefgh'[suffix - 1]}")
        previous_right = right
    numbered = [int(i) for i in ids if i.isdigit()]
    if numbered != sorted(numbered):
        raise CheckFailed(f"printed column numbers out of order: {ids}")
    return ids


def column_headers(
    page_chars: list[Word],
    header_top: float,
    header_bottom: float,
    spans: list[tuple[float, float]],
    ids: list[str],
    scale: float = 1.0,
) -> dict[str, str]:
    """Header text per column, placed one character at a time.

    Placing whole words fails where a word runs across two columns ("EcologyGross"), so each
    character goes to the column whose cell holds its centre. Rotated text is skipped.
    scale multiplies the distances, which are in points, for smaller or larger fonts.
    """
    chars = [
        c
        for c in page_chars
        if header_top <= c["top"] < header_bottom and c.get("upright", True) and c["text"].strip()
    ]
    per_column: dict[str, list[list[Word]]] = {i: [] for i in ids}
    lines = group_lines(chars, tolerance=1.0 * scale)
    # Spaces aren't characters in these PDFs, so lines are compared without them
    squashed = [re.sub(r"\s", "", "".join(c["text"] for c in line)).lower() for line in lines]
    # Everything down to the table's title line is title. Skipping by wording instead would
    # also drop header lines such as "Augmentation of N214 Billion for the Month of Dec 2024".
    title_index = max(
        (
            i
            for i, s in enumerate(squashed)
            if "stategovernments" in s or "distributionofrevenue" in s
        ),
        default=-1,
    )
    month_tail = "|".join(m.lower() for m in MONTH_NAMES)
    for index, (line, text) in enumerate(zip(lines, squashed, strict=True)):
        # The column-number row ("1 2 3 6=4+5") and a title's wrapped tail ("December,2025")
        if (
            index <= title_index
            or NOT_HEADER.search(text)
            or re.fullmatch(r"[\d=+\-()₦,]+", text)
            or re.fullmatch(rf"(sharedin)?({month_tail})?,?\d{{4}}", text)
        ):
            continue
        cells: dict[str, list[Word]] = {}
        for c in line:
            if c["text"] == "₦":
                continue
            centre = (c["x0"] + c["x1"]) / 2
            previous_right = spans[0][1] - (spans[1][1] - spans[0][1])
            for column, (_left, right) in zip(ids, spans, strict=True):
                if previous_right < centre <= right + 3 * scale:
                    cells.setdefault(column, []).append(c)
                    break
                previous_right = right
        for column, cell in cells.items():
            per_column[column].append(cell)
    headers = {}
    for column, cell_lines in per_column.items():
        parts = []
        for cell in cell_lines:
            text = ""
            for i, c in enumerate(cell):
                gap = c["x0"] - cell[i - 1]["x1"] if i else 0
                space = gap > 0.25 * (c["x1"] - c["x0"] + scale)
                text += (" " if space and text else "") + c["text"]
            parts.append(text)
        headers[column] = re.sub(r"\s+", " ", " ".join(parts)).strip()
    return headers


def check_months(report: Report, file_month: tuple[int, int], page1: str, title: str) -> None:
    """The report must be for the file's month. Table I on page 1 decides.

    Later pages sometimes keep a stale title copied from an older report (Aug 2022), and one
    report (Sep 2021) has a typo in the year.
    """
    t1 = TITLE.search(re.sub(r"\s+", " ", page1))
    if not t1:
        raise CheckFailed("Table I title (report month) not found on page 1")
    t1_shared = (int(t1.group(4)), month_number(t1.group(3)))
    t1_implied = next_month(int(t1.group(2)), month_number(t1.group(1)))
    if file_month not in (t1_shared, t1_implied):
        raise CheckFailed(f"Table I is for {t1_shared[0]}-{t1_shared[1]:02d}, not this month")
    if t1_shared != file_month:
        report.notes.append(f"Table I title says shared {t1_shared[0]}-{t1_shared[1]:02d} (typo)")
    t3 = TITLE.search(re.sub(r"\s+", " ", title))
    if not t3:
        report.notes.append("state table title has no month")
        return
    t3_shared = (int(t3.group(4)), month_number(t3.group(3)))
    if t3_shared != file_month:
        t3_implied = next_month(int(t3.group(2)), month_number(t3.group(1)))
        kind = "typo" if t3_implied == file_month else "stale title copied from an older report"
        report.notes.append(
            f"state table title says shared {t3_shared[0]}-{t3_shared[1]:02d} ({kind})"
        )


def check_rows(report: Report) -> None:
    """36 states, and every column adds up to the report's Total row."""
    states = [r for r in report.rows if r.row_type == "state"]
    if len(states) != 36:
        found = {r.beneficiary.upper() for r in states}
        raise CheckFailed(f"{len(states)} states, missing {sorted(STATES - found - {'NASARAWA'})}")
    totals = [r for r in report.rows if r.row_type == "total"]
    if len(totals) != 1:
        raise CheckFailed("Total row not found")
    total = totals[0]
    body = [r for r in report.rows if r.row_type != "total"]
    for column, header in report.columns:
        column_sum = sum(r.values.get(column, 0.0) for r in body)
        printed = total.values.get(column)
        if printed is None or (printed == 0.0 and abs(column_sum) > 1.0):
            report.notes.append(
                f"Total row blank for column {column} ({header}); rows add up to {column_sum:,.2f}"
            )
        elif abs(column_sum - printed) > 1.0:
            raise CheckFailed(
                f"column {column} ({header}): rows add up to {column_sum:,.2f}, "
                f"Total row says {printed:,.2f}"
            )
    # Some PDFs are cut off on the right; dbt computes the missing totals from the lines
    keys = [header_key(h) for _c, h in report.columns]
    missing = [
        name
        for name, key in (("Total Gross", "totalgross"), ("Total Net", "totalnet"))
        if not any(key in k for k in keys)
    ]
    if missing:
        report.notes.append(
            f"table cut off after column {report.columns[-1][0]}: no {' or '.join(missing)} printed"
        )


def read_pdf(path: Path, shared_month: str, digest: str) -> Report:
    """Read Table III (states) from one OAGF PDF report."""
    year, month = (int(x) for x in shared_month.split("-"))
    with pdfplumber.open(path) as pdf:
        page1 = pdf.pages[0].extract_text() or ""
        # Usually page 2, but Feb 2026 puts it after the LGA pages
        found = None
        for number, candidate in enumerate(pdf.pages, start=1):
            candidate_text = candidate.extract_text() or ""
            if (
                re.search(r"to\s+State\s+Governments", candidate_text)
                and "Local Government" not in candidate_text[:600]
            ):
                found = (number, candidate, candidate_text)
                break
        if found is None:
            raise CheckFailed("state table (Table III) not found")
        page_number, page, text = found
        report = Report(shared_month, "pdf", path.name, digest, page_number)
        check_months(report, (year, month), page1, text)
        lines = [tidy_line(line) for line in group_lines(page.extract_words())]
        chars = list(page.chars)
        page_height = float(page.height)

    numbers = printed_column_numbers(lines)
    # Data rows: a beneficiary, then figures, down to the Total row. A label printed a little
    # above its figures (a taller cell) reads as its own line, so it waits for the next line.
    entries: list[tuple[str, int | None, list[Word]]] = []
    pending: list[Word] | None = None
    first_data_top: float | None = None
    for line in lines:
        figures = [w for w in line if AMOUNT.match(w["text"]) or w["text"] in DASH]
        if not figures:
            text = " ".join(w["text"] for w in line)
            starts_row = (
                bool(entries) or text.startswith("Total") or re.match(r"^\d+\s*[A-Za-z]", text)
            )
            pending = (
                line if starts_row and len(line) <= 6 and re.search(r"[A-Za-z]{3}", text) else None
            )
            continue
        label_words = [
            w for w in line if w["x1"] <= figures[0]["x0"] and not SMALL_INT.match(w["text"])
        ]
        counts = [w for w in line if SMALL_INT.match(w["text"]) and w["x1"] <= figures[0]["x0"]]
        if not label_words and pending and line[0]["top"] - pending[0]["top"] < 25:
            label_words = [w for w in pending if not SMALL_INT.match(w["text"])]
            counts = [w for w in pending if SMALL_INT.match(w["text"])] + counts
        pending_line, pending = pending, None
        label = re.sub(r"^\d+\s*", "", " ".join(w["text"] for w in label_words)).strip(" (")
        if not label:
            continue
        # Rows with only a few figures are the small extra beneficiaries (disputed derivation)
        if len(figures) < 6 and not (
            entries
            and len(figures) >= 2
            and re.search(r"deriv|total|fct|forum|hyppadec", label, re.IGNORECASE)
        ):
            continue
        if first_data_top is None:
            first_data_top = (pending_line or line)[0]["top"]
        entries.append((label, int(counts[-1]["text"]) if counts else None, figures))
        if label.lower().startswith("total"):
            break
    if not entries or not entries[-1][0].lower().startswith("total") or first_data_top is None:
        raise CheckFailed("state rows or Total row not found")

    spans = column_spans([figures for _l, _c, figures in entries])
    ids = column_ids(spans, numbers)
    # Headers sit in the band above the first row; title lines in it are skipped by text
    header_top = first_data_top - 0.25 * page_height
    headers = column_headers(chars, header_top, first_data_top - 1, spans, ids)
    report.columns = [(i, headers.get(i, "")) for i in ids]

    for label, lgc_count, figures in entries:
        values: dict[str, float] = {}
        for w in figures:
            column = next(
                (i for i, (_left, right) in zip(ids, spans, strict=True) if w["x1"] <= right + 1.5),
                ids[-1],
            )
            if column in values:
                raise CheckFailed(f"{label}: two figures under column {column}")
            values[column] = to_amount(w["text"])
        report.rows.append(Row(label, row_type(label), lgc_count, values))

    # The S/n repeated at the right edge reads as a column where a row prints "-" there
    for column, header in list(report.columns):
        if header_key(header) == "sn":
            if any(r.values.get(column, 0.0) for r in report.rows):
                raise CheckFailed(f"column {column} is headed S/n but holds figures")
            report.columns.remove((column, header))
            for r in report.rows:
                r.values.pop(column, None)
    check_rows(report)
    with pdfplumber.open(path) as pdf:
        read_pdf_lgas(pdf, report)
    return report


def row_type(label: str) -> str:
    if label.lower().startswith("total"):
        return "total"
    return "state" if label.upper() in STATES else "other"


def read_excel(path: Path, shared_month: str, digest: str, reason: str) -> Report:
    """Read the state table from an OAGF Excel report (for the EXCEL_EXCEPTIONS months).

    The Excel files hold the unrounded formula results; figures are rounded to the kobo as the
    published report prints them. Columns are numbered by position from 4, like the PDFs.
    """
    report = Report(
        shared_month, "excel", path.name, digest, None, notes=[f"read from Excel: {reason}"]
    )
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheet = next(
        ws for ws in workbook.worksheets if ws.title.strip().lower() in {"states", "state details"}
    )
    rows = [list(r) for r in sheet.iter_rows(values_only=True)]
    head_index = next(
        i for i, r in enumerate(rows) if any(str(c).strip() == "Beneficiaries" for c in r if c)
    )
    head = [str(c).strip() if c is not None else "" for c in rows[head_index]]
    first = next(i for i, h in enumerate(head) if h.startswith("No. of LGC")) + 1
    last = len(head) - 1 - head[::-1].index("S/n")
    ids = [str(n) for n in range(4, 4 + last - first)]
    report.columns = [(i, re.sub(r"\s+", " ", head[first + k])) for k, i in enumerate(ids)]
    for r in rows[head_index + 1 :]:
        label = str(r[1]).strip() if r[1] is not None else ""
        if not label or label == "₦":
            continue
        values = {i: round(float(str(r[first + k] or 0)), 2) for k, i in enumerate(ids)}
        lgc_count = int(r[2]) if isinstance(r[2], int | float) else None
        report.rows.append(Row(label, row_type(label), lgc_count, values))
        if label.lower().startswith("total"):
            break
    check_rows(report)
    if shared_month in NO_LGA_MONTHS:
        report.notes.append(f"LGA: no LGA figures: {NO_LGA_MONTHS[shared_month]}")
    elif not read_excel_lgas(workbook, report):
        raise CheckFailed("the Excel report has no LGA detail sheet")
    return report


# LGA tables (local government councils). Each state's councils are numbered from 1 and the
# states come in the state table's order, so the numbering alone groups councils by state.
# Some reports print a state's TOTAL row without a label, or its name off the page, so the
# grouping doesn't rely on labels; the checks then compare every group with the state table.

LGA_LABEL = re.compile(r"^(\d{1,3})([A-Za-z].*)?$")


def state_key(name: str) -> str:
    return re.sub(r"[^a-z]", "", name.lower()).replace("nassarawa", "nasarawa")


FCT_COUNCILS = 6  # Abaji, Bwari, Gwagwalada, Kuje, Kwali, Municipal (AMAC)


def is_fct(group: dict[str, Any]) -> bool:
    """The FCT's area councils: six of them, starting with Abaji or under an FCT total."""
    lgas = group["lgas"]
    label = state_key(group.get("total_label", ""))
    named = "fct" in label or "abuja" in label or (lgas and state_key(lgas[0].lga) == "abaji")
    return len(lgas) == FCT_COUNCILS and bool(named)


def dominant_font_size(page: Any) -> float:
    sizes = [round(float(c["size"]), 1) for c in page.chars if c["text"].strip()]
    return max(set(sizes), key=sizes.count) if sizes else 0.0


def scaled_lines(page: Any, size: float) -> list[list[Word]]:
    """Lines of a page with word and line tolerances scaled to its font size.

    pdfplumber's defaults (3 pt) suit a normal font. The 2021-2022 LGA tables are printed at
    0.6 pt, where the defaults merge neighbouring rows and columns into scrambled text.
    """
    words = page.extract_words(x_tolerance=size * 0.25, y_tolerance=size * 0.4)
    # Rows are about 2.5 font sizes apart; words in one row share their bottom to within
    # about 0.3 (a figure shrunk to fit its cell is a little taller)
    lines = group_lines(words, size * 0.4, edge="bottom")
    return [tidy_line(line, glue_gap=size * 0.15) for line in lines]


def lga_page_kind(lines: list[list[Word]]) -> str:
    # The page's header: every line above the first line with a figure. Some pages have a
    # title, some only column headers (May-Aug 2026), sometimes five lines of them.
    first_data = next(
        (i for i, line in enumerate(lines) if any(AMOUNT.match(w["text"]) for w in line)),
        min(len(lines), 20),
    )
    head = re.sub(r"\s", "", " ".join(w["text"] for line in lines[:first_data] for w in line))
    head = head.lower()
    if "summaryofdistribution" in head:
        return "summary"
    if "distributionofecology" in head or "ecologyrevenueallocation" in head:
        return "other"
    if "revenueallocationtolocalgovernment" in head:
        return "lga"
    if "localgovernment" in head and "statutory" in head:
        return "lga"
    if any(t in head for t in ("officeofthe", "federationaccountdep", "distributionof", "tablei")):
        return "other"
    # A page carrying on the LGA table starts with councils or state names, never with
    # column headers of its own: headers mean another table (working sheets, Jul 2023)
    if any(t in head for t in ("statutory", "beneficiar", "s/no", "s/n")):
        return "other"
    return "continued"


def split_segments(line: list[Word]) -> list[tuple[list[Word], list[Word]]]:
    """Split a line into (label words, figures) pieces: two councils can share one line."""
    segments: list[tuple[list[Word], list[Word]]] = []
    label: list[Word] = []
    figures: list[Word] = []
    for w in line:
        if AMOUNT.match(w["text"]) or w["text"] in DASH:
            figures.append(w)
        else:
            if figures:
                segments.append((label, figures))
                label, figures = [], []
            label.append(w)
    if label or figures:
        segments.append((label, figures))
    return segments


@dataclass
class LgaLine:
    label: str
    figures: list[Word]
    page: int
    label_x: float | None = None  # where the label starts, if there is one


def parse_lga_label(label: str) -> tuple[int, str] | None:
    """'26 KUNCHI', '26KUNCHI' or '19 KANO 26 KUNCHI' (state name on the same line) -> (26, ...)."""
    parsed = split_lga_label(label)
    return (parsed[0], parsed[1]) if parsed else None


def split_lga_label(label: str) -> tuple[int, str, str] | None:
    """(council number, council name, whatever is printed before it) or None.

    The state's merged cell can share a council's row, so '12 EDO TOTAL 9 ETSAKO WEST' is
    council 9 of a state labelled 'EDO TOTAL' (a typo the reports carry).
    """
    tokens = label.split()
    for i in range(len(tokens) - 1, -1, -1):
        match = LGA_LABEL.match(tokens[i])
        if match:
            name = " ".join(([match.group(2)] if match.group(2) else []) + tokens[i + 1 :])
            if not name.strip() or "TOTAL" in name.upper():
                return None
            return int(match.group(1)), name.strip(), " ".join(tokens[:i])
    return None


def read_pdf_lgas(pdf: Any, report: Report) -> None:
    """Read the LGA detail table(s) and check them against the state table."""
    tables: list[list[tuple[int, Any, float, list[list[Word]]]]] = []
    current: list[tuple[int, Any, float, list[list[Word]]]] | None = None
    for number, page in enumerate(pdf.pages, start=1):
        size = dominant_font_size(page)
        if not size:
            continue
        lines = scaled_lines(page, size)
        kind = lga_page_kind(lines)
        if kind == "lga":
            current = [(number, page, size, lines)]
            tables.append(current)
        elif kind == "continued" and current is not None:
            # Council numbers above 60 mean a list across all states: the table has ended
            numbers = [
                p[0]
                for line in lines
                for label_words, _figures in split_segments(line)
                if (p := parse_lga_label(" ".join(w["text"] for w in label_words)))
            ]
            if numbers and max(numbers) > 60:
                current = None
                continue
            current.append((number, page, size, lines))
        elif current is not None or kind == "summary":
            current = None
            if kind == "summary" and tables:
                break
    if not tables:
        raise CheckFailed("LGA table not found")

    # The councils are printed as two halves (states 1-18ish, then the rest). Either both
    # halves share each line, left and right, whatever the number of title pages, or each
    # half has its own run of pages under its own title (Aug-Nov 2024). Each half is one
    # stream, read down the pages; a state cut at the end of the first carries on in the next.
    def segments_of(table: list[tuple[int, Any, float, list[list[Word]]]]) -> list[LgaLine]:
        out = []
        for number, _page, _size, lines in table:
            for line in lines:
                for label_words, figures in split_segments(line):
                    if figures:
                        label = " ".join(w["text"] for w in label_words).strip(" (")
                        label_x = label_words[0]["x0"] if label_words else None
                        out.append(LgaLine(label, figures, number, label_x))
        return out

    # Some reports follow the LGA table with another council list (ecology details) numbered
    # 1-774 across all states. No state has more than 44 councils, so that list is skipped.
    def highest_number(table: list[tuple[int, Any, float, list[list[Word]]]]) -> int:
        numbers = [p[0] for ln in segments_of(table) if (p := parse_lga_label(ln.label))]
        return max(numbers, default=0)

    kept = [t for t in tables if highest_number(t) <= 60]
    if len(kept) < len(tables):
        report.notes.append("LGA: skipped a council list numbered across all states")
    tables = kept
    if not tables:
        raise CheckFailed("LGA table not found")

    every = [ln for table in tables for ln in segments_of(table)]
    # Two blocks per line: the councils' names start at two places about 100 characters
    # apart. The split goes where the right block's names start, after the left block's last
    # column and before any right-hand figure. Measured in font sizes (0.6 to 14 pt).
    size0 = tables[0][0][2]
    starts = sorted(ln.label_x for ln in every if ln.label_x is not None and len(ln.figures) >= 3)
    gaps = [(b - a, b) for a, b in itertools.pairwise(starts)]
    split = None
    if gaps and max(gaps)[0] > 30 * size0:
        # The usual start of a right-hand name; a TOTAL label can start a little further left
        right_starts = [x for x in starts if x >= max(gaps)[1]]
        split = statistics.median(right_starts) - 0.5 * size0
    streams: list[list[LgaLine]] = []
    header_pages: list[tuple[int, Any, float]] = []  # page number, page, font size
    if split is not None:
        # Cut every piece at the split: a right half without a label (a total, or stray
        # figures) would otherwise run on from the left half's council
        left: list[LgaLine] = []
        right: list[LgaLine] = []
        for ln in every:
            # By right edge: figures are right-aligned, so that edge lines up in each column
            on_left = [w for w in ln.figures if w["x1"] < split]
            on_right = [w for w in ln.figures if w["x1"] >= split]
            # The label goes with its figures; a piece that crosses the split keeps it on the
            # left (labels come first) and its right-hand figures go on without one
            if on_left:
                left.append(LgaLine(ln.label, on_left, ln.page))
            if on_right:
                right.append(LgaLine("" if on_left else ln.label, on_right, ln.page))
        streams = [left, right]
        header_pages = [tables[0][0][:3]] * 2
    else:
        for table in tables:
            streams.append(segments_of(table))
            header_pages.append(table[0][:3])
    # A council row has at least 3 figures; fewer is stray text from beside the table
    streams = [[ln for ln in stream if len(ln.figures) >= 3] for stream in streams]

    # Columns per stream, from the figures; headers from the stream's first page
    stream_columns: list[tuple[list[str], list[tuple[float, float]]]] = []
    stream_dropped: list[list[tuple[float, float]]] = []  # stray figures to skip, per stream
    for s, stream in enumerate(streams):
        header_page_number, page, size = header_pages[s]
        scale = size / 4.0
        spans = column_spans([ln.figures for ln in stream], 0.75 * size, 6 * size)
        tol = 0.75 * size

        def rows_in(
            span: tuple[float, float], tol: float = tol, stream: list[LgaLine] = stream
        ) -> set[int]:
            a, b = span
            return {
                k
                for k, ln in enumerate(stream)
                if any(a - tol <= w["x1"] <= b + tol for w in ln.figures)
            }

        # Every real column has a figure or a dash in nearly every row. A sparse column is
        # either the same column printed out of line (a bracketed negative ends further
        # right): merged into its neighbour if they never share a row; or stray figures
        # beside the table: dropped. A real figure dropped by mistake fails the sums check.
        # A column most councils leave blank (Deduction, May 2024: 20 of 406 rows) is still a
        # column when it holds a dash and sits between columns. Stray dashes sit outside
        # the first or last column (Apr 2020, Apr 2021, Dec 2025).
        dropped: list[tuple[float, float]] = []
        blank_columns: list[tuple[float, float]] = []
        while True:
            members = [rows_in(sp) for sp in spans]
            dense = [
                len(m) >= 0.05 * len(stream) or sp in blank_columns
                for m, sp in zip(members, spans, strict=True)
            ]
            sparse = next((k for k, d in enumerate(dense) if not d), None)
            if sparse is None or len(spans) == 1:
                break
            neighbours = sorted(
                (j for j in (sparse - 1, sparse + 1) if 0 <= j < len(spans) and dense[j]),
                key=lambda j: abs(spans[j][1] - spans[sparse][1]),
            )
            target = next((j for j in neighbours if not members[j] & members[sparse]), None)
            count = len(members[sparse])
            a, b = spans[sparse]
            has_dash = any(
                w["text"] in DASH and a - tol <= w["x1"] <= b + tol
                for ln in stream
                for w in ln.figures
            )
            if target is None and has_dash and 0 < sparse < len(spans) - 1:
                blank_columns.append(spans[sparse])
                continue
            if target is not None:
                spans[target] = (
                    min(spans[target][0], spans[sparse][0]),
                    max(spans[target][1], spans[sparse][1]),
                )
                report.notes.append(
                    f"LGA: {count} figures printed out of line, kept in their column"
                )
            else:
                dropped.append(spans[sparse])
                report.notes.append(f"LGA: dropped {count} stray figures beside the table")
            del spans[sparse]
        ids = [str(i) for i in range(1, len(spans) + 1)]
        first_top = min(ln.figures[0]["top"] for ln in stream if ln.page == header_page_number)
        headers = column_headers(
            list(page.chars),
            first_top - 0.3 * float(page.height),
            first_top - size * 0.3,
            spans,
            ids,
            scale=scale,
        )
        stream_dropped.append(dropped)
        if not report.lga_columns:
            report.lga_columns = [(i, headers.get(i, "")) for i in ids]
        elif len(ids) != len(report.lga_columns):
            # Header text can differ slightly between sides; the number of columns can't
            raise CheckFailed(
                f"LGA stream {s + 1} has {len(ids)} columns, the first {len(report.lga_columns)}"
            )
        stream_columns.append((ids, spans))

    # Group councils by state: a new state starts when the numbering drops back
    states = [r for r in report.rows if r.row_type == "state"]
    state_names = {state_key(r.beneficiary) for r in states} | {"fct", "fctabuja", "abuja"}

    def is_total_label(label: str) -> bool:
        # "KANO TOTAL", or just the state's name ("BAUCHI STATE", Feb 2026)
        if "TOTAL" in label.upper():
            return True
        bare = state_key(re.sub(r"\bSTATE\b", "", label.upper()))
        return parse_lga_label(label) is None and bare in state_names

    groups: list[dict[str, Any]] = []
    grand_total: dict[str, float] | None = None
    for s, stream in enumerate(streams):
        ids, spans = stream_columns[s]
        for ln in stream:
            values: dict[str, float] = {}
            size = header_pages[s][2]
            for w in ln.figures:
                if any(a - 0.75 * size <= w["x1"] <= b + 0.75 * size for a, b in stream_dropped[s]):
                    continue  # stray figures beside the table (see the columns above)
                column = next(
                    (
                        i
                        for i, (_l, right) in zip(ids, spans, strict=True)
                        if w["x1"] <= right + 0.4 * size
                    ),
                    None,
                )
                if column is None:
                    raise CheckFailed(
                        f"LGA {ln.label!r} (page {ln.page}): figure {w['text']} right of the table"
                    )
                if column in values:
                    raise CheckFailed(
                        f"LGA {ln.label!r} (page {ln.page}): two figures in column {column}"
                    )
                values[column] = to_amount(w["text"])
            full = split_lga_label(ln.label)
            parsed = (full[0], full[1]) if full else None
            # A council in the label wins: the state cell beside it can say "EDO TOTAL"
            if parsed is None and is_total_label(ln.label):
                if "SUB" in ln.label.upper():
                    continue  # a running subtotal part way down a page ("FCT SUBTOTAL")
                if "GRAND" in ln.label.upper() or (
                    groups
                    and groups[-1]["total"] is not None
                    and state_key(ln.label) in {"total", "totallgcs"}
                ):
                    grand_total = values  # the whole table's total, after the last state
                    continue
                if not groups or groups[-1]["total"] is not None:
                    raise CheckFailed(
                        f"LGA total row {ln.label!r} (page {ln.page}) has no councils"
                    )
                groups[-1]["total"] = values
                groups[-1]["total_label"] = ln.label
            elif parsed:
                sn, name = parsed
                # The state's name can share its first council's row ("TARABA ARDO KOLA",
                # "FCT-ABUJA ABAJI"). Only council 1: later ones may start with the state's
                # name (KANO MUNICIPAL), but no state's first council does.
                # Anything printed before the council (the state's cell) is a cross-check
                prefix = re.sub(r"\b(TOTAL|STATE)\b|\d+", "", full[2].upper()) if full else ""
                hint = prefix.strip() if state_key(prefix) in state_names else ""
                if sn == 1:
                    for words in (3, 2, 1):
                        head = name.split()[:words]
                        rest = name.split()[words:]
                        if rest and state_key(" ".join(head)) in state_names | {"fctabuja"}:
                            hint, name = " ".join(head), " ".join(rest)
                            break
                if (
                    groups
                    and groups[-1]["total"] is not None
                    and sn > 1
                    and sn == groups[-1]["last_sn"] + 1
                ):
                    # A state cut by the end of a column carries on; the TOTAL line before
                    # this was the first part's total (June 2021, Kano 1-25 then 26-44)
                    report.notes.append(
                        f"LGA: part total after council {groups[-1]['last_sn']} "
                        f"(page {ln.page}) skipped; the state continues"
                    )
                    groups[-1]["total"] = None
                    groups[-1]["total_label"] = ""
                if not groups or groups[-1]["total"] is not None or sn <= groups[-1]["last_sn"]:
                    # An open state may still close with an unlabelled TOTAL line (checked below)
                    if groups and groups[-1]["total"] is None and not groups[-1].get("unlabelled"):
                        raise CheckFailed(
                            f"LGA numbering restarts at {name} (page {ln.page}) before the "
                            f"previous state's TOTAL row"
                        )
                    groups.append({"lgas": [], "total": None, "total_label": "", "last_sn": 0})
                if hint:
                    groups[-1]["state_hint"] = hint
                groups[-1]["lgas"].append(LgaRow("", sn, name, "lga", values))
                groups[-1]["last_sn"] = sn
            elif groups and (not ln.label or groups[-1]["total"] is None):
                # Figures with no label: a page subtotal, or a TOTAL row whose label is
                # printed off the page. The group's sums decide which (see below). A label
                # without a council number is treated the same while a state is open:
                # Sep 2021 prints Niger's TOTAL row as "AFIJIO".
                if ln.label:
                    report.notes.append(
                        f"LGA: line {ln.label!r} (page {ln.page}) has no council number, "
                        "checked as a possible TOTAL row"
                    )
                groups[-1].setdefault("unlabelled", []).append(values)

    finish_lga_groups(report, groups, grand_total)


def finish_lga_groups(
    report: Report, groups: list[dict[str, Any]], grand_total: dict[str, float] | None = None
) -> None:
    """Match the groups of councils to the states in order, check them, store them.

    Each group: lgas (LgaRow list), total (values or None), total_label, unlabelled (figure
    lines without a label) and state_hint (a state name printed beside the councils).
    grand_total is the whole table's total row, if printed.
    """
    states = [r for r in report.rows if r.row_type == "state"]
    # The FCT's 6 area councils follow Zamfara, though the state table has no FCT row
    if len(groups) == len(states) + 1 and is_fct(groups[-1]):
        states = [*states, Row("FCT", "state", FCT_COUNCILS, {})]
    if len(groups) != len(states):
        raise CheckFailed(f"LGA table has {len(groups)} states, the state table {len(states)}")
    columns = [i for i, _h in report.lga_columns]
    totals: list[dict[str, float] | None] = []
    for group, state in zip(groups, states, strict=True):
        lgas = group["lgas"]
        for row in lgas:
            row.state = state.beneficiary
        if state.lgc_count is not None and len(lgas) != state.lgc_count:
            raise CheckFailed(
                f"LGA table lists {len(lgas)} councils for {state.beneficiary}, "
                f"the state table {state.lgc_count}"
            )
        for printed in (group.get("total_label", ""), group.get("state_hint", "")):
            words = re.sub(r"\b(TOTAL|STATE)\b", "", printed.upper())
            label = state_key(words)
            if label and label not in state_key(state.beneficiary) + "abuja":
                raise CheckFailed(
                    f"LGA: {printed!r} printed with the councils of {state.beneficiary}"
                )
        total = group["total"]
        if total is None:
            sums = {i: sum(r.values.get(i, 0.0) for r in lgas) for i in columns}
            # An unlabelled figures line that matches the councils' sums is their TOTAL row
            total = next(
                (
                    u
                    for u in group.get("unlabelled", [])
                    if all(abs(sums[i] - u.get(i, 0.0)) <= 1.0 for i in columns)
                ),
                None,
            )
            if total is None and group.get("unlabelled"):
                # None matches: the last one, just before the next state, is the TOTAL row,
                # and the sums check below says which column differs
                total = group["unlabelled"][-1]
            if total is not None:
                report.notes.append(f"LGA: {state.beneficiary} TOTAL row has no label")
        totals.append(total)

    # The FCT sometimes has no total row of its own: the grand total minus the states is one
    if totals[-1] is None and states[-1].beneficiary == "FCT" and grand_total is not None:
        others = [t for t in totals[:-1] if t is not None]
        if len(others) == len(totals) - 1:
            totals[-1] = {
                i: grand_total.get(i, 0.0) - sum(t.get(i, 0.0) for t in others) for i in columns
            }
            report.notes.append("LGA: FCT has no TOTAL row; grand total minus the states used")

    for group, state, total in zip(groups, states, totals, strict=True):
        if total is None:
            raise CheckFailed(f"LGA: no TOTAL row for {state.beneficiary}")
        known = KNOWN_REPORT_ERRORS.get((report.shared_month, state.beneficiary))
        for i, header in report.lga_columns:
            column_sum = sum(r.values.get(i, 0.0) for r in group["lgas"])
            if abs(column_sum - total.get(i, 0.0)) > 1.0:
                if known:
                    report.notes.append(f"LGA: known report error, {state.beneficiary}: {known}")
                    break
                raise CheckFailed(
                    f"LGA: {state.beneficiary} councils add up to {column_sum:,.2f} in column {i} "
                    f"({header}), its TOTAL row says {total.get(i, 0.0):,.2f}"
                )
        report.lga_rows.extend(group["lgas"])
        report.lga_rows.append(LgaRow(state.beneficiary, None, "", "total", total))


def read_excel_lgas(workbook: Any, report: Report) -> bool:
    """Read the LGA table from an OAGF Excel report, if it has one.

    Two blocks of councils side by side, like the PDFs. The state name is printed on only
    some rows, so councils are grouped by their numbering, as in the PDFs, and the names
    are a cross-check. Returns False when the workbook has no LGA detail sheet.
    """
    sheet = next(
        (
            ws
            for ws in workbook.worksheets
            if re.fullmatch(r"lgcs?\s*details", ws.title.strip().lower())
        ),
        None,
    )
    if sheet is None:
        return False
    rows = [list(r) for r in sheet.iter_rows(values_only=True)]
    head_index = next(
        i
        for i, r in enumerate(rows)
        if any(str(c).strip() == "Local Government Councils" for c in r)
    )
    head = [str(c).strip() if c is not None else "" for c in rows[head_index]]
    names = [j for j, h in enumerate(head) if h == "Local Government Councils"]
    groups: list[dict[str, Any]] = []
    for b, j in enumerate(names):
        end = names[b + 1] - 3 if b + 1 < len(names) else len(head)
        value_cols = [k for k in range(j + 1, end) if head[k] and head[k] != "S/n"]
        if b == 0:
            report.lga_columns = [(str(n), head[k]) for n, k in enumerate(value_cols, start=1)]
        elif len(value_cols) != len(report.lga_columns):
            raise CheckFailed("Excel LGA blocks have different columns")
        state_col = next(
            (k for k in range(j - 1, max(j - 4, -1), -1) if head[k] in {"State", "States"}), None
        )
        # The council's number: the nearest S/n left of its name (the right-hand block has
        # the state's number in an unheaded column as well)
        sn_col = max(k for k in range(j) if head[k] == "S/n")
        for r in rows[head_index + 1 :]:
            name = str(r[j]).strip() if r[j] is not None else ""
            cell = str(r[state_col]).strip() if state_col is not None and r[state_col] else ""
            if not name and not cell:
                continue
            values = {
                str(n): round(float(str(r[k] or 0)), 2) for n, k in enumerate(value_cols, start=1)
            }
            sn_cell = r[sn_col]
            is_council = bool(name) and bool(re.fullmatch(r"\d+(\.0)?", str(sn_cell).strip()))
            # A council row wins over the state cell: Apr 2023 prints "EDO TOTAL" beside
            # Edo's first council
            if not is_council and ("TOTAL" in name.upper() or "TOTAL" in cell.upper()):
                if groups and groups[-1]["total"] is None:
                    groups[-1]["total"] = values
                    groups[-1]["total_label"] = name or cell
                continue
            if not is_council:
                continue
            sn = int(float(str(sn_cell)))
            if not groups or groups[-1]["total"] is not None or sn <= groups[-1]["last_sn"]:
                groups.append(
                    {"lgas": [], "total": None, "total_label": "", "last_sn": 0, "state_hint": ""}
                )
            if cell and not cell.replace(".", "").isdigit():
                groups[-1]["state_hint"] = cell
            groups[-1]["lgas"].append(LgaRow("", sn, name, "lga", values))
            groups[-1]["last_sn"] = sn
    for group in groups:
        if group["total"] is None:
            # Councils are rounded to the kobo here, so a computed total is exact enough
            group["total"] = {
                i: round(sum(r.values.get(i, 0.0) for r in group["lgas"]), 2)
                for i, _h in report.lga_columns
            }
            report.notes.append("LGA: an Excel state block has no TOTAL row; its sums are used")
    finish_lga_groups(report, groups)
    return True


def load_previous() -> dict[str, Report]:
    """Reports from the last run, keyed by shared month, to reuse when the file is unchanged."""
    manifest = OUT_DIR / "reports.csv"
    if not manifest.exists():
        return {}
    reports: dict[str, Report] = {}
    with manifest.open(encoding="utf-8", newline="") as f:
        for m in csv.DictReader(f):
            if m["reader_version"] != READER_VERSION:
                continue
            reports[m["shared_month"]] = Report(
                m["shared_month"],
                m["source_type"],
                m["file_name"],
                m["sha256"],
                int(m["page"]) if m["page"] else None,
            )
    with (OUT_DIR / "columns.csv").open(encoding="utf-8", newline="") as f:
        for c in csv.DictReader(f):
            if c["shared_month"] in reports:
                reports[c["shared_month"]].columns.append((c["column_id"], c["column_header"]))
    with (OUT_DIR / "notes.csv").open(encoding="utf-8", newline="") as f:
        for n in csv.DictReader(f):
            if n["shared_month"] in reports:
                reports[n["shared_month"]].notes.append(n["note"])
    rows: dict[tuple[str, int], Row] = {}
    for year_file in sorted((OUT_DIR / "state_figures").glob("*.csv")):
        with year_file.open(encoding="utf-8", newline="") as f:
            for v in csv.DictReader(f):
                if v["shared_month"] not in reports:
                    continue
                key = (v["shared_month"], int(v["row_number"]))
                if key not in rows:
                    rows[key] = Row(
                        v["beneficiary"],
                        v["row_type"],
                        int(v["lgc_count"]) if v["lgc_count"] else None,
                        {},
                    )
                    reports[v["shared_month"]].rows.append(rows[key])
                rows[key].values[v["column_id"]] = float(v["amount"])
    lga_columns = OUT_DIR / "lga_columns.csv"
    if not lga_columns.exists():
        return {}  # written by an older reader, so every month is read again
    with lga_columns.open(encoding="utf-8", newline="") as f:
        for c in csv.DictReader(f):
            if c["shared_month"] in reports:
                reports[c["shared_month"]].lga_columns.append((c["column_id"], c["column_header"]))
    lga_rows: dict[tuple[str, str, str], LgaRow] = {}
    for month_file in sorted((OUT_DIR / "lga_figures").glob("*/*.csv")):
        with month_file.open(encoding="utf-8", newline="") as f:
            for v in csv.DictReader(f):
                if v["shared_month"] not in reports:
                    continue
                lga_key = (v["shared_month"], v["state"], v["lga_sn"])
                if lga_key not in lga_rows:
                    lga_rows[lga_key] = LgaRow(
                        v["state"],
                        int(v["lga_sn"]) if v["lga_sn"] else None,
                        v["lga"],
                        v["row_type"],
                        {},
                    )
                    reports[v["shared_month"]].lga_rows.append(lga_rows[lga_key])
                lga_rows[lga_key].values[v["column_id"]] = float(v["amount"])
    return reports


def find_pdfs(pdf_dir: Path) -> dict[str, Path]:
    pdfs: dict[str, Path] = {}
    for path in sorted(pdf_dir.rglob("*.pdf")):
        match = FILE_MONTH.search(path.name)
        if not match:
            raise SystemExit(f"Error: can't read the month from the file name {path.name}")
        shared_month = f"{match.group(2)}-{month_number(match.group(1)):02d}"
        if shared_month < FIRST_SHARED_MONTH:
            continue
        if shared_month in pdfs:
            raise SystemExit(
                f"Error: two PDFs for {shared_month}: {pdfs[shared_month].name}, {path.name}"
            )
        pdfs[shared_month] = path
    return pdfs


def check_duplicates(reports: list[Report]) -> None:
    """A Total row identical to another month's means a copied table, not new figures."""
    seen: dict[tuple[float, ...], str] = {}
    for report in reports:
        total = next(r for r in report.rows if r.row_type == "total")
        key = tuple(sorted(round(v, 2) for v in total.values.values() if v))
        if key in seen:
            raise CheckFailed(
                f"{report.shared_month}: Total row identical to {seen[key]} (copied table)"
            )
        seen[key] = report.shared_month


def write_outputs(reports: list[Report]) -> int:
    figures_dir = OUT_DIR / "state_figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "reports.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["shared_month", "source_type", "file_name", "sha256", "page", "reader_version"])
        for r in reports:
            w.writerow(
                [r.shared_month, r.source_type, r.file_name, r.sha256, r.page or "", READER_VERSION]
            )
    with (OUT_DIR / "columns.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["shared_month", "position", "column_id", "column_header", "header_key"])
        for r in reports:
            for position, (column, header) in enumerate(r.columns, start=1):
                w.writerow([r.shared_month, position, column, header, header_key(header)])
    with (OUT_DIR / "notes.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["shared_month", "note"])
        for r in reports:
            for note in r.notes:
                w.writerow([r.shared_month, note])
    figure_rows = 0
    years = sorted({r.shared_month[:4] for r in reports})
    for stale in figures_dir.glob("*.csv"):
        if stale.stem not in years:
            stale.unlink()
    for year in years:
        with (figures_dir / f"{year}.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    "shared_month",
                    "row_number",
                    "beneficiary",
                    "row_type",
                    "lgc_count",
                    "column_id",
                    "amount",
                ]
            )
            for r in reports:
                if r.shared_month[:4] != year:
                    continue
                for row_number, row in enumerate(r.rows, start=1):
                    for column, _header in r.columns:
                        if column in row.values:
                            w.writerow(
                                [
                                    r.shared_month,
                                    row_number,
                                    row.beneficiary,
                                    row.row_type,
                                    "" if row.lgc_count is None else row.lgc_count,
                                    column,
                                    f"{row.values[column]:.2f}",
                                ]
                            )
                            figure_rows += 1
    return figure_rows


def write_lga_outputs(reports: list[Report]) -> int:
    """LGA columns, one figures file per month, and the known report errors."""
    with (OUT_DIR / "lga_columns.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["shared_month", "position", "column_id", "column_header", "header_key"])
        for r in reports:
            for position, (column, header) in enumerate(r.lga_columns, start=1):
                w.writerow([r.shared_month, position, column, header, header_key(header)])
    months = {r.shared_month for r in reports}
    with (OUT_DIR / "known_report_errors.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["shared_month", "state", "error"])
        for (month, state), error in sorted(KNOWN_REPORT_ERRORS.items()):
            if month in months:
                w.writerow([month, state, error])
    figures_dir = OUT_DIR / "lga_figures"
    wanted = {
        figures_dir / r.shared_month[:4] / f"{r.shared_month}.csv" for r in reports if r.lga_rows
    }
    for stale in figures_dir.glob("*/*.csv"):
        if stale not in wanted:
            stale.unlink()
    figure_rows = 0
    for r in reports:
        if not r.lga_rows:
            continue
        path = figures_dir / r.shared_month[:4] / f"{r.shared_month}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(
                ["shared_month", "state", "lga_sn", "lga", "row_type", "column_id", "amount"]
            )
            for row in r.lga_rows:
                for column, _header in r.lga_columns:
                    if column in row.values:
                        w.writerow(
                            [
                                r.shared_month,
                                row.state,
                                "" if row.lga_sn is None else row.lga_sn,
                                row.lga,
                                row.row_type,
                                column,
                                f"{row.values[column]:.2f}",
                            ]
                        )
                        figure_rows += 1
    return figure_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Refine the OAGF FAAC reports into CSV files.")
    parser.add_argument("--pdf-dir", default=os.getenv("FAAC_OAGF_PDF_DIR"))
    parser.add_argument("--excel-dir", default=os.getenv("FAAC_RAW_EXCEL_DIR"))
    args = parser.parse_args()
    if not args.pdf_dir or not Path(args.pdf_dir).is_dir():
        raise SystemExit("Error: set --pdf-dir or FAAC_OAGF_PDF_DIR to the folder of OAGF PDFs")

    previous = load_previous()
    pdfs = find_pdfs(Path(args.pdf_dir))
    reports: list[Report] = []
    failures: list[str] = []
    reused = 0
    for shared_month, pdf in pdfs.items():
        path = pdf
        try:
            if shared_month in EXCEL_EXCEPTIONS:
                if not args.excel_dir:
                    raise CheckFailed("needs --excel-dir or FAAC_RAW_EXCEL_DIR (Excel exception)")
                relative, reason = EXCEL_EXCEPTIONS[shared_month]
                path = Path(args.excel_dir) / relative
                source_type = "excel"
            else:
                path, reason, source_type = pdf, "", "pdf"
            digest = sha256_of(path)
            old = previous.get(shared_month)
            if old and old.sha256 == digest and old.source_type == source_type:
                reports.append(old)
                reused += 1
                continue
            print(f"Reading {shared_month} from {path.name}", flush=True)
            if source_type == "excel":
                reports.append(read_excel(path, shared_month, digest, reason))
            else:
                reports.append(read_pdf(path, shared_month, digest))
        except CheckFailed as e:
            failures.append(f"{shared_month} ({path.name}): {e}")
    try:
        check_duplicates(reports)
    except CheckFailed as e:
        failures.append(str(e))
    if failures:
        for failure in failures:
            print(f"Error: {failure}", file=sys.stderr)
        raise SystemExit(f"Error: {len(failures)} month(s) failed; nothing written")

    # Date order, so a new month adds lines at the end of its year's file
    reports.sort(key=lambda r: r.shared_month)
    figure_rows = write_outputs(reports)
    lga_figure_rows = write_lga_outputs(reports)
    print(
        f"Wrote {len(reports)} months ({len(reports) - reused} read, {reused} unchanged), "
        f"{figure_rows} state figures and {lga_figure_rows} LGA figures to "
        f"{OUT_DIR.relative_to(OUT_DIR.parents[3])}"
    )


if __name__ == "__main__":
    main()
