{{
    config(
        materialized='table',
        schema='analytics'
    )
}}

select --distinct indicator_name
  make_date(year,month,1) as date,
  country_code,
  country_name,
  round(value,0) as exchange_rate,
  extracted_at::date as extracted_at 
from {{ref('nigeria_econ_metric_monthly')}}
where indicator_name ilike '%exchange rate%'