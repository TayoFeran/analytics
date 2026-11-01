select country_code, country_name, indicator_code, indicator_name, year, month, value, extracted_at
from {{ source("world_bank", "nigeria_econ_metric_monthly") }}
