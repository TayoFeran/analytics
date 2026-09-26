{{
    config(
        materialized='table',
        schema='analytics'
    )
}}

select
  make_date(year,1,1) as date,
  country_code,
  country_name,
  value::int as population,
  extracted_at::date as extracted_at 
from {{ref('nigeria_econ_metric_annual')}}
where indicator_name ilike '%population%'