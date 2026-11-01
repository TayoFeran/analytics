select
    make_date(year, 1, 1) as date,
    country_code,
    country_name,
    value as gdp,
    extracted_at::date as extracted_at
from {{ ref("stg_nigeria_world_bank__indicators_annual") }}
where indicator_name ilike '%gdp%'
