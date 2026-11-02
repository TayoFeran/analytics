-- One row per year from 1990: the size of Nigeria's economy in dollars and naira, real
-- growth, population and GDP per person. Yearly fact table of the Nigeria Data Dashboard's
-- Economy section. All World Bank figures, which reflect NBS's 2025 GDP rebasing.
--
-- Dollar GDP moves with the exchange rate, so the year's average rate sits alongside it:
-- a fall in dollar GDP while naira GDP grows is the naira losing value, not the economy shrinking.
with
    gdp_usd as (select date, gdp from {{ ref("nigeria_gdp") }}),

    gdp_naira as (select date, gdp_naira from {{ ref("nigeria_gdp_naira") }}),

    growth as (select date, real_gdp_growth from {{ ref("nigeria_gdp_growth") }}),

    population as (select date, population from {{ ref("nigeria_population") }}),

    -- Monthly rates start in 2010, so earlier years have no average rate
    fx as (
        select date_trunc('year', date)::date as date, avg(exchange_rate) as avg_naira_per_usd
        from {{ ref("nigeria_fx_rate") }}
        group by 1
    ),

    administration as (
        select
            president,
            first_disbursement_month as first_month,
            lead(first_disbursement_month) over (
                order by first_disbursement_month
            ) as next_first_month
        from {{ ref("nigeria_administration") }}
    )

select
    gdp_usd.date as year_date,
    year(gdp_usd.date) as year,
    -- The president in office for most of the year. Handovers are on 29 May, so a handover
    -- year goes to the incoming president. Blank before 1999 (military rule).
    administration.president,
    gdp_usd.gdp as gdp_usd,
    gdp_naira.gdp_naira,
    growth.real_gdp_growth,
    population.population,
    gdp_usd.gdp / population.population as gdp_per_person_usd,
    gdp_naira.gdp_naira / population.population as gdp_per_person_naira,
    fx.avg_naira_per_usd
from gdp_usd
left join gdp_naira on gdp_usd.date = gdp_naira.date
left join growth on gdp_usd.date = growth.date
left join population on gdp_usd.date = population.date
left join fx on gdp_usd.date = fx.date
left join
    administration
    -- 1 July is past the middle of the year, so whoever is in office then has most of it
    on make_date(year(gdp_usd.date), 7, 1) >= administration.first_month
    and (
        administration.next_first_month is null
        or make_date(year(gdp_usd.date), 7, 1) < administration.next_first_month
    )
