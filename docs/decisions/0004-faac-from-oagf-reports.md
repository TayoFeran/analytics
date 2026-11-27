# 0004: FAAC figures from the OAGF's published reports

- Status: accepted
- Date: 2026-11-22

## Context

FAAC data came from hand-refined workbooks: the state table (Table III) of each monthly OAGF report, retyped into an `Income` and a `Deduction` sheet. That has limits (#36):

- The refined files hold the 36 states only. The 774 local government councils (LGAs) are only in the original reports.
- Each new month needs manual work, and the NBS page that hosted the Excel reports is no longer reachable. The OAGF website publishes the same reports as PDF.
- October 2024 was missing.

The OAGF PDFs are text, not scanned images, so the figures can be read exactly. Their layout changes over the years (15 to 24 columns, new revenue lines, different page sizes), and some reports contain mistakes of their own.

## Decision

1. **The OAGF PDF is the source**, as published on the [OAGF FAAC report page](https://oagf.gov.ng/publications/faac-report/). `pipelines/nigeria/refine_faac_reports.py` reads each report and writes tidy CSV files to `data/nigeria/faac/oagf/`. The daily pipeline loads those CSV files and never reads a PDF.
2. **The PDFs stay outside git.** They are about 200 MB and never change once published. The repo keeps a manifest (`reports.csv`) with each file's SHA-256 fingerprint, so every figure can be traced to the exact file it came from. The repo owner keeps the PDFs, with a backup.
3. **Every report is checked against itself before anything is written.** The report must be for the right month, according to Table I on page 1. It must list 36 states, every column must add up to the report's own Total row, and no month may repeat another month's Total row. If any month fails, nothing is written.
4. **The published report wins** over the earlier hand-refined workbooks wherever they differ.
5. **Two months come from the OAGF's raw Excel report instead**, because their PDF state table can't be used:
   - **April 2023:** the PDF's state and LGA tables are a copy of February 2022. Only Table I is April 2023.
   - **September 2021:** the PDF shows each state's full ecology fund with no NDDC/HYPPADEC transfer, and its Total Gross leaves out derivation, so its totals don't add up. The Excel report applies the 50% transfer, as every other month does, and adds up.
6. **Months are named by the month the money was shared** (the "shared in" month), as the refined files were.
7. **LGAs come from the same reports**, one CSV file per month. Each state's councils must add up to the state's TOTAL row. Where the report's own figures don't add up, they are **kept as printed and flagged** (`known_report_errors.csv`), not corrected: there is no second source to correct them from. April 2023's LGAs come from its Excel report, like its state table.
8. **September 2021 has no LGA figures.** Its Excel report has no LGA sheet, and its PDF LGA table doesn't add up for five states and the FCT (Zamfara has no TOTAL row at all). A gap is more honest than figures we can't check.
9. **dbt seeds decide which line each column belongs to.** Headers change almost every month, so `dbt/seeds/sandbox/nigeria_faac_state_column_line.csv` and `nigeria_faac_lga_column_line.csv` map every printed header to one of the lines the site already uses, and the grouping can be read and changed in one place. One-off distributions, EMTL, augmentation and solid minerals go to "others", as in the refined workbooks. The gold tables compute totals from the lines, and a dbt test fails if they don't match the report's printed totals, except where the report's mistake is known.

## What the checks found

Checked against the hand-refined workbooks for January 2020 to April 2026 (2,700 state-months), statutory allocation agreed everywhere and gross VAT everywhere but one header misread, since fixed. The remaining differences, where the report wins:

- **August 2021:** the refined file left out the 50% ecology transfer to HYPPADEC for its 6 states (₦24-32 million each).
- **November 2024:** for 4 states, the Excel report transfers more than the state's ecology fund (₦1.2-1.6 million); the PDF caps the transfer at the fund.
- **April 2021:** ₦2-35 per state on the net amount.
- **May 2023:** the Excel report, and so the refined file, has four one-off lines (the two forex equalisation distributions, solid minerals and the FGN Treasury Crude Account) 57% higher for every state than the PDF. The PDF agrees with its own summary of the states' share (Table I). This month's state table is cut off before its totals, so the first comparison, of totals only, missed it.
- **July 2023:** the refined file has ₦400,000 less in other deductions for Imo. The PDF's figures add up to its own totals.

Comparing every line, not only the totals, also showed two months where the refined file put a column under a different line: May 2021 (exchange gain under others) and October 2022 (the ₦60 billion non-oil distribution and EMTL under exchange gain). The totals agree; the new data follows the printed headers.

Report quirks the refine script records in `notes.csv`:

- Eight reports are cut off on the right, with no Total Gross or Total Net printed. dbt computes those totals from the lines instead.
- The printed column formulas ("18=6+11+12+13+14") are often out of date. They are not used as checks.
- Some state-table titles are stale (August 2022 says July 2022) or have a typo (September 2021 says 2022). Table I decides the month.
- July 2025's Total row is blank for one column.

## What the LGA checks found

Every month lists 774 councils (the 36 states' councils and the FCT's 6 area councils). The refine script checks that each state's councils add up to its TOTAL row, and dbt checks that each council's own columns add up to its printed Total Allocation. In 19 months, 91 state-months fail one of these because of a mistake in the report. Kano is the most common (14 months). The mistakes are of a few kinds:

- The councils' own Total Allocation column uses a wrong formula for some or all councils (for example leaving out a new revenue line such as EMTL in February 2023, repeating the VAT, or taking another council's VAT), while the state's TOTAL row is right.
- The state's TOTAL row has a wrong figure: a typo of ₦30-50, ₦18 million too much VAT, ₦79 million too much ecology, or one council left out.
- A deduction printed positive and added to the total instead of taken off.
- The ecology columns don't fit: the 50% transfer to NDDC/HYPPADEC is printed as 0, or is more than half the ecology fund (July 2023, May 2023 Delta).
- May 2023 is the worst month: the whole right half of its LGA table (Katsina to the FCT, 18 entries) prints a Total Allocation that isn't the sum of the row's own columns, for councils and TOTAL rows alike.

Each is listed, with what is wrong, in `known_report_errors.csv`. The revenue lines themselves are kept as printed, and the gold table computes each council's net from them, so a wrong printed total never reaches the site.

## Consequences

- Adding a month: save the OAGF PDF, run the refine script, open a PR with the new CSV rows.
- Reading a new layout can fail a check. That stops the refine step, not the website: the site keeps the last good data until the reader is fixed.
- The refined workbooks are retired to `archive/nigeria/faac/`, and `load_faac_allocations.py` and the models built from them (`nigeria_faac_income`, `nigeria_faac_deduction`) were removed once the website ran on the new data (#36).
- 2019 waits until a full year of reports is available.
