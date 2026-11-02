-- Yearly economy facts: GDP in $ and naira, real growth, population (World Bank)
select
    year_date::date as year_date,
    year::int as year,
    president,
    gdp_usd::double as gdp_usd,
    gdp_naira::double as gdp_naira,
    real_gdp_growth::double as real_gdp_growth,
    population::double as population,
    gdp_per_person_usd::double as gdp_per_person_usd,
    gdp_per_person_naira::double as gdp_per_person_naira,
    avg_naira_per_usd::double as avg_naira_per_usd
from datamart.nigeria_economy_year
