-- One row per year: the size of the economy in naira and dollars, real growth, population
-- and GDP per person (World Bank). A year goes to the president in office on 1 July;
-- years before 1999 have no president.
select
    year,
    president,
    round(gdp_usd)::bigint as gdp_usd,
    round(gdp_naira)::bigint as gdp_naira,
    round(real_gdp_growth, 4) as real_gdp_growth,
    round(population)::bigint as population,
    round(gdp_per_person_usd, 2) as gdp_per_person_usd,
    round(gdp_per_person_naira, 2) as gdp_per_person_naira,
    round(avg_naira_per_usd, 4) as avg_naira_per_usd
from datamart.nigeria_economy_year
order by year
