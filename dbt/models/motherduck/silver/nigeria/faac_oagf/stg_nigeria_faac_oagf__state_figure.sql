-- One row per printed figure of the OAGF state table (Table III): month, row and column,
-- with the column's printed header and the standard line the seed maps it to.
with
    figures as (select * from {{ source("nigeria_faac_oagf", "state_figures") }}),

    report_columns as (select * from {{ source("nigeria_faac_oagf", "state_columns") }}),

    column_line as (select * from {{ ref("nigeria_faac_state_column_line") }}),

    column_override as (select * from {{ ref("nigeria_faac_state_column_override") }})

select
    figures.shared_month || ' ' || figures.row_number || ' ' || figures.column_id as figure_key,
    figures.shared_month,
    cast(figures.shared_month || '-01' as date) as disbursement_date,
    figures.row_number,
    figures.row_type,
    figures.beneficiary,
    case
        when figures.row_type = 'state' then {{ nigeria_state_name("figures.beneficiary") }}
    end as state,
    figures.lgc_count,
    figures.column_id,
    report_columns.position as column_position,
    report_columns.column_header,
    report_columns.header_key,
    coalesce(column_override.line, column_line.line) as line,
    coalesce(column_override.role, column_line.role) as role,
    figures.amount
from figures
left join
    report_columns
    on figures.shared_month = report_columns.shared_month
    and figures.column_id = report_columns.column_id
left join column_line on report_columns.header_key = column_line.header_key
left join
    column_override
    on figures.shared_month = column_override.shared_month
    and figures.column_id = column_override.column_id
