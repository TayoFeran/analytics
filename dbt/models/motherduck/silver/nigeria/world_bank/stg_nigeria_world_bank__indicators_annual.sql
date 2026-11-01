select country_code, country_name, indicator_code, indicator_name, year, value, extracted_at
from {{ source("nigeria_world_bank", "indicators_annual") }}
