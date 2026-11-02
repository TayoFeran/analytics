-- Real growth (constant prices), the official "the economy grew X%" figure. It can't be
-- derived from nigeria_gdp, whose dollar values also move with the exchange rate.
select
    make_date(year, 1, 1) as date,
    country_code,
    country_name,
    value / 100 as real_gdp_growth,
    extracted_at::date as extracted_at
from {{ ref("stg_nigeria_world_bank__indicators_annual") }}
where indicator_code = 'NY.GDP.MKTP.KD.ZG'
