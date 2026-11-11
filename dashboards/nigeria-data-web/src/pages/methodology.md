---
layout: ../layouts/ArticleLayout.astro
title: Methodology
eyebrow: About the data
description: Where the data comes from, how each figure is calculated, how often it updates, and the known gaps.
updated: 9 November 2026
---

Every number on this site comes from public sources and is calculated the same way every time. This page explains where the data comes from, what each figure means, and what is missing, so you can check our work.

## Where the data comes from

| Data | Source | Coverage |
|---|---|---|
| FAAC allocations to states | Monthly FAAC disbursement reports, published by the Office of the Accountant General of the Federation (OAGF) | 36 states, January 2020 to the latest month added |
| Naira-per-dollar exchange rate | World Bank, official exchange rate (monthly average) | January 2010 to the latest month |
| Consumer prices and inflation | World Bank, consumer price index (CPI) | Prices from January 2010; inflation from January 2011 (it compares with a year earlier) |
| GDP, growth, population | World Bank | Yearly, 1990 to the latest year |
| Presidents and terms | Hand-maintained list of administrations since 1999 | Obasanjo to Tinubu |
| State boundaries (map) | geoBoundaries (GRID3, 2022), CC BY 4.0 | 36 states and the FCT |

FAAC is the Federation Account Allocation Committee. Every month it shares federally collected revenue between the federal government, the 36 states and local governments. This site shows the **state** share.

## How often it updates

- The site is rebuilt **every day** from the latest data in our warehouse.
- **FAAC data arrives monthly.** A month's workbook is added once it is published, usually some weeks after the month ends.
- The **freshness** label on each page compares the latest month we have with today's date. A FAAC month is expected within 45 days after it ends:

Economy pages use two clocks: CPI and the exchange rate are expected within 60 days after a month ends (Late up to 30 days after that), and GDP within 270 days after a year ends (Late up to 90 days after that). The label shows the worse of the two.

| Label | Meaning |
|---|---|
| On time | The latest period is within its expected window |
| Late | Up to 15 days past the expected date |
| Overdue | More than 15 days past the expected date |
| Refresh missed | The site hasn't been rebuilt for more than 3 days |

## What each figure means

### The headline figures

- **Gross allocation**: everything a state was allocated at the monthly FAAC sharing, before deductions: statutory allocation, VAT, oil derivation, exchange gain, ecology fund and other income.
- **Deductions**: money taken from a state's allocation at source, before payment, mostly to repay debts and meet commitments the state has signed up to.
- **Net received**: what the states actually received: gross allocation minus deductions.
- **Exchange rate**: the month's average official naira-per-dollar rate (World Bank).

### Revenue lines (they add up to gross)

- **Statutory allocation**: a state's share of the Federation Account, the pool of federally collected revenue such as oil and gas earnings, company income tax and customs duties. States split it using the revenue allocation formula, which weighs equality, population, land mass and other factors.
- **VAT**: a state's share of Value Added Tax collected nationwide. VAT is pooled and split between the federal government, states and local governments, then among states partly equally and partly by population and where the tax was generated.
- **Oil derivation**: extra money for oil- and gas-producing states. At least 13% of revenue from natural resources goes back to the states that produce them (Constitution, s.162(2)). Most states receive none.
- **Exchange gain**: a state's share of the extra naira the Federation Account earns when dollar revenue is converted at a weaker naira rate than the budget assumed. Only paid in some months.
- **Ecology fund**: a state's share of the Ecological Fund, set aside for problems such as erosion, flooding and desertification.
- **Other income**: smaller or one-off revenue lines that the FAAC report groups as "Others".

### Deduction lines (they add up to deductions)

- **External debt**: repayments on a state's foreign loans (for example from the World Bank), deducted at source by the federal government.
- **Contractual obligations (ISPO)**: Irrevocable Standing Payment Orders, payments a state committed to in advance, usually for bank loans, bonds or contracts, deducted automatically each month.
- **NDDC / HYPPADEC transfer**: half of the ecological fund due to member states, transferred by law to the Niger Delta Development Commission (NDDC) or the Hydroelectric Power Producing Areas Development Commission (HYPPADEC).
- **Other deductions (see note)**: deductions the FAAC report explains in its notes, often repayments of federal loans to states such as budget support or bailout facilities.
- **Deduction (unlabelled)**: a deduction shown in the FAAC report under a column headed only "Deduction", with no further detail.
- **Other deductions**: smaller deductions that the FAAC report groups as "Others".

### Shares and comparisons

- **Deductions share**: deductions as a share of the gross allocation.
- **Share of the national net**: a state's net received as a share of the net received by all 36 states that month.
- **"₦X of every ₦100 kept"**: net received divided by gross allocation, per ₦100.
- **Change vs previous month**: the selected month compared with the month before it, even when that month is outside the dates you picked.
- **Colours**: green means better for the states (more received, fewer deductions, a stronger naira), red means worse, and amber means unchanged.

## How amounts are converted to dollars

Each month's naira amounts are converted at **that month's own** exchange rate. A dollar total across several months is the sum of what each month was worth in dollars at the time. Converting a multi-year naira total at one rate would misstate it.

## The economy figures

- **Inflation**: how much consumer prices rose over the previous 12 months. Lower is better; it doesn't mean prices fell.
- **Naira per US dollar**: the month's average official rate. A higher number means a weaker naira.
- **GDP (nominal)**: the value of everything the economy produced in a year, at that year's prices, in naira or converted to dollars at the year's average rate.
- **Real GDP growth**: how much more was produced than the year before, after removing price rises. Population grows about 2.5% a year, so growth below that means less output per person.
- **GDP per person**: GDP divided by the population. It is an average, not what a typical person earns.
- **World Bank figures can differ from the NBS headline numbers**, for example because of different base years or methods.

### FAAC in real terms

To compare months fairly, amounts are converted to the prices of the latest FAAC month ("today's prices") with the consumer price index: an amount is multiplied by the latest month's CPI divided by its own month's CPI. "As paid" is the amount in naira at the time.

### Presidents

- A **month** belongs to the president whose first FAAC disbursement month it falls in; a **year** belongs to the president in office on 1 July. Years before 1999 have no president.
- **Average inflation** and **average growth** are simple averages of the term's months or years inside the selected range.
- **The naira's value** compares the rate a president inherited (the month before their first month) with the rate they left.
- A term is **partial** (hatched) when the data doesn't cover all of it, for example because monthly prices start in 2010. These comparisons describe outcomes; conditions such as oil prices differed between terms.

## Rounding

Amounts are stored in whole naira and shown in billions (₦) or millions and billions ($), to one decimal place. Because of rounding, the revenue or deduction lines can differ from their total by a few naira.

## Known gaps

- **FCT is not included.** The Federal Capital Territory isn't in the FAAC state workbooks.
- **October 2024 is missing.** There is no workbook for that month, so charts go straight from September to November 2024, and November 2024 is compared with September.
- **Data starts in January 2020.** Earlier years will be added over time.
- **Some workbooks have blank totals.** Where a workbook was saved without its totals, we recompute them from their components, and net received as gross minus deductions. That rule matches every workbook where the totals are filled in.

## Spotted an error?

The code and the calculations behind this site are public. If something looks wrong, please [open an issue on GitHub](https://github.com/TayoFeran/analytics/issues) with the page, the figure and what you expected. Corrections are noted on this page.
