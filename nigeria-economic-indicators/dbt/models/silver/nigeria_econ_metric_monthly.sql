{{
    config(
        materialized='view',
        schema='silver'
    )
}}

select
    country_code,
    country_name,
    indicator_code,
    indicator_name,
    year,
    month,
    value,
    extracted_at
from {{ source('bronze', 'nigeria_econ_metric_monthly') }}