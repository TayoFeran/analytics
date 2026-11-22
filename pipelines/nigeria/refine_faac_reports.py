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
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import openpyxl
import pdfplumber
from dotenv import load_dotenv

load_dotenv()

# Bump when the reading logic changes, so every month is read again instead of reused
READER_VERSION = "1"

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
class Report:
    shared_month: str
    source_type: str  # pdf or excel
    file_name: str
    sha256: str
    page: int | None
    columns: list[tuple[str, str]] = field(default_factory=list)  # (column_id, header)
    rows: list[Row] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


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


def group_lines(words: list[Word], tolerance: float = 1.5) -> list[list[Word]]:
    """Group words into lines by their top, left to right."""
    lines: list[list[Word]] = []
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if lines and abs(lines[-1][0]["top"] - w["top"]) <= tolerance:
            lines[-1].append(w)
        else:
            lines.append([w])
    for line in lines:
        line.sort(key=lambda w: w["x0"])
    return lines


def tidy_line(line: list[Word]) -> list[Word]:
    """Glue split figures back together and turn bracketed figures into negatives.

    The PDFs print the first digit of many figures as a separate piece that touches the rest
    ("8" + ",145,202,571.72"), and some negatives as "(" followed by the figure.
    """
    glued: list[Word] = []
    for w in line:
        prev = glued[-1] if glued else None
        if (
            prev
            and w["x0"] - prev["x1"] < 0.6
            and re.match(r"^[\d,.]", w["text"])
            and re.match(r"^\(?[\d,.]+$", prev["text"])
        ):
            prev["text"] += w["text"]
            prev["x1"] = w["x1"]
        elif prev and prev["text"] == "(" and re.match(r"^[\d,.]+\)?$", w["text"]):
            prev["text"] = "-" + w["text"].rstrip(")")
            prev["x1"] = w["x1"]
        else:
            glued.append(dict(w))
    for w in glued:
        bracketed = re.match(r"^\(([\d,.]+)\)$", w["text"])
        if bracketed:
            w["text"] = "-" + bracketed.group(1)
    return glued


def column_spans(rows: list[list[Word]]) -> list[tuple[float, float]]:
    """Find the figure columns from the figures themselves.

    Figures are right-aligned, so each column's figures end at about the same x. A dash for
    an empty cell sits elsewhere in the cell, so it starts its own cluster at first. Two
    clusters that never appear in the same row are one column and get merged.
    """
    edges = sorted((w["x1"], row_index) for row_index, row in enumerate(rows) for w in row)
    clusters: list[dict[str, Any]] = []
    for x, row_index in edges:
        if clusters and x - clusters[-1]["right"] <= 3.0:
            clusters[-1]["right"] = x
            clusters[-1]["rows"].add(row_index)
        else:
            clusters.append({"left": x, "right": x, "rows": {row_index}})
    merged = True
    while merged:
        merged = False
        for i in range(len(clusters) - 1):
            a, b = clusters[i], clusters[i + 1]
            if not (a["rows"] & b["rows"]) and b["left"] - a["right"] < 25:
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
) -> dict[str, str]:
    """Header text per column, placed one character at a time.

    Placing whole words fails where a word runs across two columns ("EcologyGross"), so each
    character goes to the column whose cell holds its centre. Rotated text is skipped.
    """
    chars = [
        c
        for c in page_chars
        if header_top <= c["top"] < header_bottom and c.get("upright", True) and c["text"].strip()
    ]
    per_column: dict[str, list[list[Word]]] = {i: [] for i in ids}
    lines = group_lines(chars, tolerance=1.0)
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
                if previous_right < centre <= right + 3:
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
                text += (" " if gap > 0.25 * (c["x1"] - c["x0"] + 1) and text else "") + c["text"]
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
    return report


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
    print(
        f"Wrote {len(reports)} months ({len(reports) - reused} read, {reused} unchanged), "
        f"{figure_rows} figures to {OUT_DIR.relative_to(OUT_DIR.parents[3])}"
    )


if __name__ == "__main__":
    main()
