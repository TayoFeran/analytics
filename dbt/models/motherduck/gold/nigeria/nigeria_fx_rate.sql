select  -- distinct indicator_name
    make_date(year, month, 1) as date,
    country_code,
    country_name,
    -- Unrounded: in 2010 a whole naira was about 0.7% of the rate
    value as exchange_rate,
    extracted_at::date as extracted_at
from {{ ref("stg_nigeria_world_bank__indicators_monthly") }}
where indicator_name ilike '%exchange rate%'
