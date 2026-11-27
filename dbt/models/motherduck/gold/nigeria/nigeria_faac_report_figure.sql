-- Every figure the OAGF reports print for a state or a council, with the column header as
-- printed and the standard line it is grouped into. The detail behind
-- nigeria_faac_state_allocation and nigeria_faac_lga_allocation: it shows what "others
-- income" was made of in a month, for example.
with
    state_figures as (
        select * from {{ ref("stg_nigeria_faac_oagf__state_figure") }} where row_type = 'state'
    ),

    lga_figures as (
        select * from {{ ref("stg_nigeria_faac_oagf__lga_figure") }} where row_type = 'lga'
    )

select
    'state ' || figure_key as figure_key,
    'state' as level,
    shared_month,
    disbursement_date,
    state,
    null::integer as lga_sn,
    null::varchar as lga,
    column_id,
    column_position,
    column_header,
    line,
    role,
    amount
from state_figures
union all
select
    'lga ' || figure_key as figure_key,
    'lga' as level,
    shared_month,
    disbursement_date,
    state,
    lga_sn,
    lga,
    column_id,
    column_position,
    column_header,
    line,
    role,
    amount
from lga_figures
