# Tooltips: FAAC section

Design agreed on 2026-11-02 (step 5 of the build). Positions are in [`placement.md`](placement.md), and the backgrounds are `backgrounds/tt_faac_*.png`. The DAX below goes into the semantic model in step 6.

## Which visual uses which tooltip

| Visual | Tooltip |
|---|---|
| Overview KPI cards: Gross, Deductions, Net | TT - Metric Detail |
| Revenue mix matrix; Deductions matrix (state × type) | TT - Metric Detail |
| States map; 36-state ranking bar | TT - State Detail |
| Compare page, Side A and Side B tables | TT - Compare Metric |
| Overview line chart (gross vs net) | TT - Overview Month: HTML card (`Overview_month_tt_html`), gross and net for the hovered month with change vs the month before |
| Revenue mix stacked area | Default: month, revenue line, value, `VAT_share` / `Oil_Derivation_share` |
| Deductions stacked column | Default: month, deduction line, value, `Deductions_share` |
| Top 5 states bar; oil derivation by state | Default: state, value, `Net_share_national` |
| Deductions % of gross bar | Default: state, `Deductions_share`, `Deductions`, `Gross` |
| Exchange rate card | Default: `FX_rate_avg`, `FX_rate_definition` |

Charts over time use default tooltips because **Period Calc's "Current" is always the latest month with data**: it ignores the hovered month on purpose. A Metric Detail tooltip on the Jan 2024 point of a trend would show Apr 2026 figures. A default tooltip shows the hovered month's own values.

## How a tooltip knows the hovered metric

- **Matrices and Compare tables** have the metric field parameter in the visual, so the hovered row or column passes `Metric_param` to the tooltip.
- **KPI cards** show a fixed measure. Each card gets a visual-level filter, e.g. `Metric_param = Gross allocation`. The filter doesn't change the card's own number, but Power BI passes visual filters on to the tooltip page.
- The field parameter has two extra columns. `Metric_key` holds the measure name, and every lookup uses it, so renaming a display label never breaks a tooltip. `Metric_family` (Income / Deduction / Net) drives the colour rule.

```dax
Metric_param = {
    ( "Gross allocation",               NAMEOF ( 'Dax'[Gross] ),                  0,  "Gross",                 "Income" ),
    ( "Statutory allocation",           NAMEOF ( 'Dax'[Statutory] ),              1,  "Statutory",             "Income" ),
    ( "VAT",                            NAMEOF ( 'Dax'[VAT] ),                    2,  "VAT",                   "Income" ),
    ( "Oil derivation",                 NAMEOF ( 'Dax'[Oil_Derivation] ),         3,  "Oil_Derivation",        "Income" ),
    ( "Exchange gain",                  NAMEOF ( 'Dax'[Exchange_Gain] ),          4,  "Exchange_Gain",         "Income" ),
    ( "Ecology fund",                   NAMEOF ( 'Dax'[Ecology] ),                5,  "Ecology",               "Income" ),
    ( "Other income",                   NAMEOF ( 'Dax'[Others_Income] ),          6,  "Others_Income",         "Income" ),
    ( "Total deductions",               NAMEOF ( 'Dax'[Deductions] ),             7,  "Deductions",            "Deduction" ),
    ( "External debt",                  NAMEOF ( 'Dax'[External_Debt] ),          8,  "External_Debt",         "Deduction" ),
    ( "Contractual obligations (ISPO)", NAMEOF ( 'Dax'[Contractual_Obligation] ), 9,  "Contractual_Obligation", "Deduction" ),
    ( "NDDC / HYPPADEC transfer",       NAMEOF ( 'Dax'[NDDC_Transfer] ),          10, "NDDC_Transfer",         "Deduction" ),
    ( "Other deductions (see note)",    NAMEOF ( 'Dax'[Other_Deductions_Note] ),  11, "Other_Deductions_Note", "Deduction" ),
    ( "Deduction (unlabelled)",         NAMEOF ( 'Dax'[Deduction_Misc] ),         12, "Deduction_Misc",        "Deduction" ),
    ( "Other deductions",               NAMEOF ( 'Dax'[Other_Deduction] ),        13, "Other_Deduction",       "Deduction" ),
    ( "Net received",                   NAMEOF ( 'Dax'[Net] ),                    14, "Net",                   "Net" )
}
-- Columns renamed after creation: Metric_param, Metric_param Fields, Metric_param Order,
-- Metric_key, Metric_family
```

## Reading a field parameter in DAX

A field parameter's name column (`Period[Period]`, `Metric_param[Metric_param]`) is tied to its hidden
`Fields` column as a composite key, so DAX can't read it on its own: `SELECTEDVALUE ( Period[Period] )`
fails with "Column [Period] is part of composite key". Read a column outside the key instead:

- `Period`: the order column, `SWITCH ( SELECTEDVALUE ( Period[Period Order] ), 1, "Quarterly", 2, "Yearly", "Monthly" )`.
- `Metric_param`: `Metric_key` for lookups, or `Metric_label` (a plain calculated copy of the name) for display
  and for matrix rows and columns.

The DAX in this file is the design draft. The semantic model is the source of truth.

## Definitions (approved)

All of these sit in `06 Titles & Labels\Tooltips`. The About page's Definitions box is a table of `Metric_param[Metric_label]` and `Metric_definition`, so every definition lives in one place.

```dax
Metric_definition =
-- Plain-language explanation of the hovered metric, keyed on Metric_key
VAR _k = SELECTEDVALUE ( Metric_param[Metric_key] )
RETURN
    SWITCH (
        _k,
        "Gross", "Everything the state was allocated at the monthly FAAC sharing, before deductions: statutory allocation, VAT, oil derivation, exchange gain, ecology fund and other income.",
        "Statutory", "The state's share of the Federation Account, the pool of federally collected revenue such as oil and gas earnings, company income tax and customs duties. States split it using the revenue allocation formula, which weighs equality, population, land mass and other factors.",
        "VAT", "The state's share of Value Added Tax collected nationwide. VAT is pooled and split between the federal government, states and local governments, then among states partly equally and partly by population and where the tax was generated.",
        "Oil_Derivation", "Extra money for oil- and gas-producing states: at least 13% of revenue from natural resources goes back to the states that produce them (Constitution, s.162(2)). Most states receive none.",
        "Exchange_Gain", "The state's share of the extra naira the Federation Account earns when dollar revenue is converted at a weaker naira rate than the budget assumed. Only paid in some months.",
        "Ecology", "The state's share of the Ecological Fund, set aside from the Federation Account for problems such as erosion, flooding and desertification.",
        "Others_Income", "Smaller or one-off revenue lines that the FAAC report groups as ""Others"".",
        "Deductions", "Money taken from the state's allocation at source, before payment, mostly to repay debts and meet commitments the state has signed up to.",
        "External_Debt", "Repayments on the state's foreign loans (for example from the World Bank), deducted at source by the federal government.",
        "Contractual_Obligation", "Irrevocable Standing Payment Orders (ISPOs): payments the state committed to in advance, usually for bank loans, bonds or contracts, deducted automatically each month.",
        "NDDC_Transfer", "Half of the ecological fund due to member states, transferred by law to the Niger Delta Development Commission (NDDC) or the Hydroelectric Power Producing Areas Development Commission (HYPPADEC).",
        "Other_Deductions_Note", "Other deductions that the FAAC report explains in its notes, often repayments of federal loans to states such as budget support or bailout facilities.",
        "Deduction_Misc", "A deduction shown in the FAAC report under a column headed only ""Deduction"", with no further detail.",
        "Other_Deduction", "Smaller deductions that the FAAC report groups as ""Others"".",
        "Net", "What the state actually received: gross allocation minus deductions."
    )

FX_rate_definition = "The month's average official naira-per-dollar rate (World Bank). Each month's naira amounts are converted at that month's own rate."
Deductions_share_definition = "The share of the gross allocation taken as deductions."
Net_share_definition = "The state's share of the net received by all 36 states."
```

## Measures behind TT - Metric Detail

```dax
Metric_value =
-- Value of the hovered metric; the format string follows the ₦/$ switch like the base measures
VAR _k = SELECTEDVALUE ( Metric_param[Metric_key] )
RETURN
    SWITCH (
        _k,
        "Gross", [Gross], "Statutory", [Statutory], "VAT", [VAT],
        "Oil_Derivation", [Oil_Derivation], "Exchange_Gain", [Exchange_Gain],
        "Ecology", [Ecology], "Others_Income", [Others_Income],
        "Deductions", [Deductions], "External_Debt", [External_Debt],
        "Contractual_Obligation", [Contractual_Obligation], "NDDC_Transfer", [NDDC_Transfer],
        "Other_Deductions_Note", [Other_Deductions_Note], "Deduction_Misc", [Deduction_Misc],
        "Other_Deduction", [Other_Deduction], "Net", [Net]
    )

-- Thin wrappers over Period Calc, filed in 03 Period Comparison\Metric (tooltip)
Metric_value_curr = CALCULATE ( [Metric_value], 'Period Calc'[Name] = "Current" )
Metric_value_prev = CALCULATE ( [Metric_value], 'Period Calc'[Name] = "Previous" )
Metric_value_PnP  = CALCULATE ( [Metric_value], 'Period Calc'[Name] = "Change %" )
Metric_value_G&D  = CALCULATE ( [Metric_value], 'Period Calc'[Name] = "Trend" )

Metric_value_colour =
-- Income and net: up is good. Deductions: up is bad. No change: amber.
VAR _fam = SELECTEDVALUE ( Metric_param[Metric_family] )
VAR _chg = [Metric_value_PnP]
RETURN
    SWITCH (
        TRUE (),
        ISBLANK ( _chg ) || ROUND ( _chg, 4 ) = 0, "#C98A00",
        ( _chg > 0 ) = ( _fam <> "Deduction" ), "#0E8A5F",
        "#C93C3C"
    )

Metric_change_text =
-- "▲ 8.9% Growth · vs Last Month"
VAR _chg = [Metric_value_PnP]
VAR _mark =
    SWITCH ( TRUE (), ROUND ( _chg, 4 ) = 0, UNICHAR ( 9632 ), _chg > 0, UNICHAR ( 9650 ), UNICHAR ( 9660 ) )
RETURN
    _mark & " " & FORMAT ( ABS ( _chg ), "0.0%" ) & " " & [Metric_value_G&D] & " · " & [Periodic_text]

Metric_tooltip_title =
VAR _name = SELECTEDVALUE ( Metric_param[Metric_label], "Metric" )
VAR _area =
    SWITCH (
        TRUE (),
        HASONEVALUE ( nigeria_state[state] ), VALUES ( nigeria_state[state] ),
        HASONEVALUE ( nigeria_state[zone] ), VALUES ( nigeria_state[zone] ),
        "All states"
    )
RETURN UPPER ( _name & " · " & _area )

Metric_tooltip_subtitle =
SELECTEDVALUE ( Basis[Basis], "Monthly average" ) & ", "
    & IF ( SELECTEDVALUE ( Currency[Currency], "₦" ) = "$", "US dollars", "naira" )

Metric_tooltip_summary =
-- "Oil derivation was ₦18.4bn in Apr 2026, up 8.9% vs last month."
VAR _name = SELECTEDVALUE ( Metric_param[Metric_label], "This metric" )
VAR _v = [Metric_value_curr]
VAR _chg = [Metric_value_PnP]
VAR _sym = IF ( SELECTEDVALUE ( Currency[Currency], "₦" ) = "$", "$", "₦" )
VAR _a = ABS ( _v )
VAR _amount =
    _sym
        & SWITCH (
            TRUE (),
            _a >= 1e12, FORMAT ( _v / 1e12, "0.0" ) & "tn",
            _a >= 1e9, FORMAT ( _v / 1e9, "0.0" ) & "bn",
            _a >= 1e6, FORMAT ( _v / 1e6, "0.0" ) & "m",
            FORMAT ( _v, "#,0" )
        )
VAR _last = [Latest_month]
VAR _when =
    SWITCH (
        SWITCH ( SELECTEDVALUE ( Period[Period Order] ), 1, "Quarterly", 2, "Yearly", "Monthly" ),
        "Quarterly", "Q" & QUARTER ( _last ) & " " & YEAR ( _last ) & " to date",
        "Yearly", YEAR ( _last ) & " to date",
        FORMAT ( _last, "mmm yyyy" )
    )
VAR _move =
    SWITCH (
        TRUE (),
        ISBLANK ( _chg ), "",
        ROUND ( _chg, 4 ) = 0, ", unchanged " & LOWER ( [Periodic_text] ),
        ", " & IF ( _chg > 0, "up ", "down " ) & FORMAT ( ABS ( _chg ), "0.0%" ) & " " & LOWER ( [Periodic_text] )
    )
RETURN
    IF ( ISBLANK ( _v ), BLANK (), _name & " was " & _amount & " in " & _when & _move & "." )
```

Mini chart: a column chart of `Metric_value` by `calendar_table[monthf]`, filtered to `Last_6_Period_flag = 1`, coloured `#0E6B45`, with axes off and a data label on the last column only.

## Measures behind TT - State Detail

```dax
State_tooltip_title = UPPER ( SELECTEDVALUE ( nigeria_state[state] ) )

State_tooltip_subtitle =
-- "South South · South · Rank 2 of 36 by net"
VAR _net = [Net_curr]
VAR _rank =
    CALCULATE (
        RANKX ( VALUES ( nigeria_state[state] ), [Net_curr], _net, DESC ),
        REMOVEFILTERS ( nigeria_state )
    )
VAR _n =
    CALCULATE (
        COUNTROWS ( FILTER ( VALUES ( nigeria_state[state] ), NOT ISBLANK ( [Net_curr] ) ) ),
        REMOVEFILTERS ( nigeria_state )
    )
RETURN
    SELECTEDVALUE ( nigeria_state[zone] ) & " · " & SELECTEDVALUE ( nigeria_state[region] )
        & " · Rank " & _rank & " of " & _n & " by net"

-- 02 Rates & Averages\Shares
Net_share_national =
DIVIDE ( [Net_curr], CALCULATE ( [Net_curr], REMOVEFILTERS ( nigeria_state ) ), 0 )
```

`REMOVEFILTERS ( nigeria_state )` ranks against every state even when the Zone slicer is set, so "of 36" stays true. `_n` counts only states with data, which leaves out FCT.

## Measures behind TT - Compare Metric

```dax
Compare_tooltip_text =
-- "▲ Tinubu 185.0% higher than Buhari", coloured with Metric_B_colour
VAR _a = CALCULATE ( [Metric_value], 'Compare Side'[Name] = "A" )
VAR _b = CALCULATE ( [Metric_value], 'Compare Side'[Name] = "B" )
VAR _d = DIVIDE ( _b - _a, _a )
VAR _mark =
    SWITCH ( TRUE (), ROUND ( _d, 4 ) = 0, UNICHAR ( 9632 ), _d > 0, UNICHAR ( 9650 ), UNICHAR ( 9660 ) )
RETURN
    SWITCH (
        TRUE (),
        ISBLANK ( _a ) || ISBLANK ( _b ), "No data for one side.",
        ROUND ( _d, 4 ) = 0, _mark & " " & [Side_B_label] & " and " & [Side_A_label] & " are equal",
        _mark & " " & [Side_B_label] & " " & FORMAT ( ABS ( _d ), "0.0%" )
            & IF ( _d > 0, " higher", " lower" ) & " than " & [Side_A_label]
    )
```

The side values use `Metric_value` with `'Compare Side'[Name] = "A"` / `"B"`. The title is `Metric_param` and `Metric_tooltip_subtitle` joined with " · ".

# Tooltips: Economy section

Design agreed on 2026-11-02. Positions are in [`placement.md`](placement.md), and the backgrounds are `backgrounds/tt_economy_*.png`. The DAX below goes into the semantic model in step 6.

## Which visual uses which tooltip

| Visual | Tooltip |
|---|---|
| Overview: inflation line chart | TT - Inflation Month: HTML card (`Inflation_month_tt_html`), inflation for the hovered month with the change vs the month before and a year earlier (down = green) |
| Overview: naira line chart | TT - Naira Month: HTML card (`Naira_month_tt_html`), naira per US dollar for the hovered month with the change vs the month before and a year earlier (weaker naira = red) |
| Economy size: GDP in naira | TT - GDP Naira Year: HTML card (`GdpNaira_year_tt_html`), value, the same year in US dollars, change vs the year before |
| Economy size: GDP in US dollars | TT - GDP Dollar Year: HTML card (`GdpUsd_year_tt_html`), value, the year's naira rate, change vs the year before |
| Economy size: real GDP growth | TT - Growth Year: HTML card (`Growth_year_tt_html`), growth, population growth, change in points vs the year before |
| Economy size: GDP per person | TT - Per Person Year: HTML card (`PerPerson_year_tt_html`), dollars, naira, change vs the year before |
| FAAC in real terms: monthly column chart | TT - Real Terms Month: HTML card (`Real_month_tt_html`), as paid, in today's prices, change vs the month before in the selected basis, and the price rise in words |
| Presidents: all three bar charts | TT - President Detail |
| Overview KPI cards | Default: the card's value, its as-of text and its definition |
| FAAC in real terms KPI cards | Default: the value and `Today_prices_definition` |

These tooltips work differently from the FAAC ones. The Economy measures have no period switch, so a hovered month, year or president passes straight through as a filter. Each tooltip shows the hovered point's own values using the plain base measures (`Inflation_yoy`, `GDP_naira`, `Net_paid`...), not the `_latest` card measures.

## Definitions (approved)

They sit in `06 Titles & Labels\Tooltips`, next to the FAAC definitions.

```dax
Inflation_definition = "How much prices rose compared with the same month a year earlier (World Bank consumer price index)."
Naira_value_definition = "How many more or fewer US dollars a naira buys than before. Negative means the naira lost value."
Real_growth_definition = "How much the economy grew in the year after removing price rises."
GDP_per_person_definition = "The economy's total output divided by the population. It is an average, not what a typical person earns."
Today_prices_definition =
"Today's prices: each month's amount restated in " & FORMAT ( [Price_base_month], "mmm yyyy" )
    & " prices, using the World Bank consumer price index."

Econ_month_definitions = "Inflation: " & [Inflation_definition] & "  Naira value: " & [Naira_value_definition]
Econ_year_definitions = "Real growth: " & [Real_growth_definition] & "  Per person: " & [GDP_per_person_definition]
President_definitions =
"Averages are over the months or years each president was in office. Naira value compares the rate at the start and end of the term. "
    & "A year goes to the president in office for most of it."
```

## Measures behind TT - Economy Month

Replaced on 2026-11-06 by two HTML cards, one per chart: TT - Inflation Month (`Inflation_month_tt_html`) and TT - Naira Month (`Naira_month_tt_html`). The original design is kept below for reference.

```dax
Econ_month_tooltip_title =
-- e.g. "Jul 2026 · Tinubu"
FORMAT ( MAX ( econ_month[month_date] ), "mmm yyyy" ) & " · " & SELECTEDVALUE ( econ_month[president] )
```

The three cards are `Inflation_yoy`, `Naira_per_usd` and `Naira_value_change_yoy`. Naira value is green when positive and red when negative.

## Measures behind TT - Economy Year

Replaced on 2026-11-06 by four HTML cards, one per Economy size chart (see the table above). The original design is kept below for reference.

```dax
Econ_year_tooltip_title =
-- e.g. "2024 · Tinubu"; years before 1999 have no president
MAX ( econ_year[year] ) & " · " & COALESCE ( SELECTEDVALUE ( econ_year[president] ), "Before 1999 (military rule)" )

GDP_year_tooltip_text =
-- e.g. "From 2023, GDP rose 18.7% in naira but fell 48.2% in dollars: the naira lost value, the economy didn't shrink."
VAR _y = MAX ( econ_year[year] )
VAR _n = [GDP_naira]
VAR _u = [GDP_usd]
VAR _n0 = CALCULATE ( [GDP_naira], REMOVEFILTERS ( econ_year ), REMOVEFILTERS ( calendar_table ), REMOVEFILTERS ( dim_administration ), econ_year[year] = _y - 1 )
VAR _u0 = CALCULATE ( [GDP_usd], REMOVEFILTERS ( econ_year ), REMOVEFILTERS ( calendar_table ), REMOVEFILTERS ( dim_administration ), econ_year[year] = _y - 1 )
VAR _cn = DIVIDE ( _n, _n0 ) - 1
VAR _cu = DIVIDE ( _u, _u0 ) - 1
RETURN
    IF (
        NOT ISBLANK ( _n0 ),
        "From " & ( _y - 1 ) & ", GDP " & IF ( _cn >= 0, "rose ", "fell " ) & FORMAT ( ABS ( _cn ), "0.0%" )
            & " in naira" & IF ( ( _cn >= 0 ) = ( _cu >= 0 ), " and ", " but " )
            & IF ( _cu >= 0, "rose ", "fell " ) & FORMAT ( ABS ( _cu ), "0.0%" ) & " in dollars"
            & IF ( _cn > 0 && _cu < 0, ": the naira lost value, the economy didn't shrink.", "." )
    )
```

The average ₦ per $ card uses `Naira_per_usd`, which averages the hovered year's months. It is blank before 2010.

## Measures behind TT - Real Terms Month

```dax
Real_terms_tooltip_title =
-- e.g. "Jan 2020 · Buhari"
FORMAT ( MAX ( faac[disbursement_date] ), "mmm yyyy" ) & " · " & SELECTEDVALUE ( faac[president] )

Price_multiplier =
-- How many times prices rose between the hovered month and the base month, e.g. 3.40
VAR _base = [Price_base_month]
VAR _base_cpi = CALCULATE ( MAX ( econ_month[cpi_index] ), REMOVEFILTERS (), econ_month[month_date] = _base )
RETURN
    DIVIDE ( _base_cpi, MAX ( econ_month[cpi_index] ) )
-- formatString: "×"0.00

Real_terms_tooltip_text =
-- e.g. "Prices rose 3.40× from Jan 2020 to Apr 2026 (CPI 300.7 → 1,021.2), so ₦206.8bn then
-- bought what ₦702.2bn buys in Apr 2026."
VAR _m = MAX ( faac[disbursement_date] )
VAR _base = [Price_base_month]
VAR _cpi = MAX ( econ_month[cpi_index] )
VAR _base_cpi = CALCULATE ( MAX ( econ_month[cpi_index] ), REMOVEFILTERS (), econ_month[month_date] = _base )
VAR _p = [Net_paid]
VAR _t = [Net_today_prices]
RETURN
    SWITCH (
        TRUE (),
        ISBLANK ( _cpi ), "Price data for " & FORMAT ( _m, "mmm yyyy" ) & " isn't out yet.",
        _m = _base, "This is the base month, so today's prices equal what was paid.",
        "Prices rose " & FORMAT ( [Price_multiplier], "0.00" ) & "× from " & FORMAT ( _m, "mmm yyyy" ) & " to "
            & FORMAT ( _base, "mmm yyyy" ) & " (CPI " & FORMAT ( _cpi, "#,0.0" ) & " → " & FORMAT ( _base_cpi, "#,0.0" )
            & "), so ₦" & FORMAT ( _p / 1e9, "#,0.0" ) & "bn then bought what ₦" & FORMAT ( _t / 1e9, "#,0.0" )
            & "bn buys in " & FORMAT ( _base, "mmm yyyy" ) & "."
    )
```

## Measures behind TT - President Detail

```dax
President_tooltip_title =
COALESCE ( SELECTEDVALUE ( dim_administration[full_name] ), "Before 1999 (military rule)" )

President_tooltip_subtitle =
-- e.g. "APC · 29 May 2015 to 29 May 2023 · 96 months of data"
VAR _end = SELECTEDVALUE ( dim_administration[term_end] )
RETURN
    IF (
        HASONEVALUE ( dim_administration[president] ),
        SELECTEDVALUE ( dim_administration[party] ) & " · "
            & FORMAT ( SELECTEDVALUE ( dim_administration[term_start] ), "d mmm yyyy" ) & " to "
            & IF ( ISBLANK ( _end ), "present", FORMAT ( _end, "d mmm yyyy" ) )
            & " · " & FORMAT ( [Term_months] + 0, "#,0" ) & " months of data",
        "Years " & MIN ( econ_year[year] ) & " to " & MAX ( econ_year[year] )
    )

Term_rate_text =
-- e.g. "₦198.86 in May 2015 → ₦461.42 in Apr 2023"
VAR _first = CALCULATE ( MIN ( econ_month[month_date] ), NOT ISBLANK ( econ_month[naira_per_usd] ) )
VAR _last = CALCULATE ( MAX ( econ_month[month_date] ), NOT ISBLANK ( econ_month[naira_per_usd] ) )
RETURN
    IF (
        NOT ISBLANK ( _first ),
        FORMAT ( CALCULATE ( [Naira_per_usd], econ_month[month_date] = _first ), "₦#,0.00" ) & " in " & FORMAT ( _first, "mmm yyyy" )
            & " → " & FORMAT ( CALCULATE ( [Naira_per_usd], econ_month[month_date] = _last ), "₦#,0.00" ) & " in " & FORMAT ( _last, "mmm yyyy" ),
        "No monthly exchange rate data for this term yet"
    )
```

The cards are `Inflation_yoy`, `Term_naira_change` and `Real_GDP_growth`, and the coverage line is `Term_coverage_text`.

## Measures for the FAAC in real terms KPI cards

These were found missing in step 4 and are added with the tooltip measures, in `01 Base\Real terms`.

```dax
Real_first_month = CALCULATE ( MIN ( faac[disbursement_date] ) )
Real_latest_month = CALCULATE ( MAX ( faac[disbursement_date] ) )

Net_first_month =
VAR _m = EOMONTH ( [Real_first_month], 0 )
RETURN
    CALCULATE ( [Net_prices], calendar_table[month_date] = _m )

Net_latest_month =
VAR _m = EOMONTH ( [Real_latest_month], 0 )
RETURN
    CALCULATE ( [Net_prices], calendar_table[month_date] = _m )

Change_as_paid =
VAR _m1 = EOMONTH ( [Real_first_month], 0 )
VAR _m2 = EOMONTH ( [Real_latest_month], 0 )
RETURN
    DIVIDE (
        CALCULATE ( [Net_paid], calendar_table[month_date] = _m2 ),
        CALCULATE ( [Net_paid], calendar_table[month_date] = _m1 )
    ) - 1

Change_real =
VAR _m1 = EOMONTH ( [Real_first_month], 0 )
VAR _m2 = EOMONTH ( [Real_latest_month], 0 )
RETURN
    DIVIDE (
        CALCULATE ( [Net_today_prices], calendar_table[month_date] = _m2 ),
        CALCULATE ( [Net_today_prices], calendar_table[month_date] = _m1 )
    ) - 1
```

`calendar_table[month_date]` is the **last** day of the month, hence `EOMONTH`.
