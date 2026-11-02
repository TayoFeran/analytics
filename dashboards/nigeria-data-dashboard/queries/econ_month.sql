-- Monthly economy facts: exchange rate, CPI and their year-on-year changes (World Bank)
select
    month_date::date as month_date,
    president,
    naira_per_usd::double as naira_per_usd,
    naira_value_change_yoy::double as naira_value_change_yoy,
    cpi_index::double as cpi_index,
    inflation_yoy::double as inflation_yoy
from datamart.nigeria_economy_month
