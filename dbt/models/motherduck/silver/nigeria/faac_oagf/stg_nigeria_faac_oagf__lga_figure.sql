-- One row per printed figure of the OAGF LGA table: month, council (or a state's TOTAL
-- row) and column, with the column's printed header, the standard line the seed maps it to
-- and the council's name from the nigeria_lga reference list.
with
    figures as (select * from {{ source("nigeria_faac_oagf", "lga_figures") }}),

    report_columns as (select * from {{ source("nigeria_faac_oagf", "lga_columns") }}),

    column_line as (select * from {{ ref("nigeria_faac_lga_column_line") }}),

    councils as (select * from {{ ref("nigeria_lga") }}),

    named as (
        select
            figures.*,
            {{ nigeria_state_name("figures.state") }} as state_name,
            report_columns.position as column_position,
            report_columns.column_header,
            report_columns.header_key,
            column_line.line,
            column_line.role
        from figures
        left join
            report_columns
            on figures.shared_month = report_columns.shared_month
            and figures.column_id = report_columns.column_id
        left join column_line on report_columns.header_key = column_line.header_key
    )

select
    named.shared_month
    || ' '
    || named.state
    || ' '
    || coalesce(cast(named.lga_sn as varchar), 'total')
    || ' '
    || named.column_id as figure_key,
    named.shared_month,
    cast(named.shared_month || '-01' as date) as disbursement_date,
    named.row_type,
    -- As the report prints it, for joining to known_report_errors
    named.state as report_state,
    named.state_name as state,
    named.lga_sn,
    councils.lga,
    named.lga as lga_as_printed,
    named.column_id,
    named.column_position,
    named.column_header,
    named.header_key,
    named.line,
    named.role,
    named.amount,
    -- Deductions are printed negative in most months and positive in some (May 2021).
    -- They are taken off the council's total either way, so they're kept as a positive
    -- amount to subtract, like the state table's. The few reports that add a positive
    -- deduction instead are listed in known_report_errors.
    case when named.role = 'deduction' then abs(named.amount) else named.amount end as line_amount
from named
left join councils on named.state_name = councils.state and named.lga_sn = councils.lga_sn
