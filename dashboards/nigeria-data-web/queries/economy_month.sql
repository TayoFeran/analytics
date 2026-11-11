-- One row per month: the naira exchange rate, consumer prices and inflation (World Bank),
-- with the president in office. For the Economy pages and FAAC in real terms.
select
    month_date,
    president,
    round(naira_per_usd, 4) as naira_per_usd,
    round(cpi_index, 4) as cpi_index,
    round(inflation_yoy, 4) as inflation_yoy
from datamart.nigeria_economy_month
order by month_date
