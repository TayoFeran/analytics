select
    make_date(year, month, 1) as date,
    country_code,
    country_name,
    round(value, 0) as cpi_rate,
    extracted_at::date as extracted_at
from {{ ref("stg_world_bank__indicators_monthly") }}
where indicator_name ilike '%cpi price index%'
