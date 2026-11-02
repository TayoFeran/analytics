select
    make_date(year, month, 1) as date,
    country_code,
    country_name,
    -- Unrounded: inflation is a ratio of two index values, so rounding the index skews it
    value as cpi_rate,
    extracted_at::date as extracted_at
from {{ ref("stg_nigeria_world_bank__indicators_monthly") }}
where indicator_name ilike '%cpi price index%'
