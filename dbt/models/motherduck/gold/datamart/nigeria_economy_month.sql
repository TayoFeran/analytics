-- One row per month from January 2010: the naira's official exchange rate, consumer prices
-- and how each changed over the year. Monthly fact table of the Nigeria Data Dashboard's
-- Economy section. Both series are World Bank figures, which can differ from NBS headlines.
--
-- The year-on-year changes are ratios, stored ready-made so the report never sums them.
with
    fx as (select date, exchange_rate from {{ ref("nigeria_fx_rate") }}),

    cpi as (select date, cpi_rate from {{ ref("nigeria_consumer_price_index") }}),

    administration as (
        select
            president,
            first_disbursement_month as first_month,
            -- The next administration's first month ends this one (blank for the one in office)
            lead(first_disbursement_month) over (
                order by first_disbursement_month
            ) as next_first_month
        from {{ ref("nigeria_administration") }}
    ),

    -- The two series end in different months, so take every month either one has
    months as (
        select date
        from fx
        union
        select date
        from cpi
    ),

    monthly as (
        select
            months.date as month_date, fx.exchange_rate as naira_per_usd, cpi.cpi_rate as cpi_index
        from months
        left join fx on months.date = fx.date
        left join cpi on months.date = cpi.date
    )

select
    monthly.month_date,
    administration.president,
    monthly.naira_per_usd,
    -- Negative = a naira buys fewer dollars than a year earlier (it lost value)
    year_ago.naira_per_usd / monthly.naira_per_usd - 1 as naira_value_change_yoy,
    monthly.cpi_index,
    -- Year on year, because the index isn't seasonally adjusted: it dips every January
    monthly.cpi_index / year_ago.cpi_index - 1 as inflation_yoy
from monthly
left join
    monthly as year_ago on year_ago.month_date = (monthly.month_date - interval 12 month)::date
left join
    administration
    on monthly.month_date >= administration.first_month
    and (
        administration.next_first_month is null
        or monthly.month_date < administration.next_first_month
    )
