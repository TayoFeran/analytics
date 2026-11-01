-- Date dimension: one row per day from 1990-01-01 to current_date.
-- Ported from the Redshift sandbox.fo_calendar script.

with all_dates as (
    select cast(d as date) as dt
    from generate_series(date '1990-01-01', current_date, interval 1 day) t(d)
),

date_base as (
    select
        dt                                       as date,
        cast(year(dt) as int)                    as year,
        cast(quarter(dt) as int)                 as qtr_num,
        'Q' || quarter(dt)                       as qtr_name,
        last_day(dt)                             as month_date,
        cast(month(dt) as int)                   as month_num,
        strftime(dt, '%b')                       as month_name,
        strftime(dt, '%b-%y')                    as monthf,
        cast(day(dt) as int)                     as day_num,
        strftime(dt, '%a')                       as day_name,
        strftime(dt, '%d-%b')                    as dayf,
        cast(date_trunc('week', dt) as date) + 6 as week_date,   -- Sunday ending the Mon-Sun week
        cast(dayofweek(dt) as int) + 1           as day_of_week  -- 1 = Sunday ... 7 = Saturday
    from all_dates
),

week_attrs as (
    select
        *,
        dense_rank() over (partition by month_date order by week_date) as week_month_rank,
        dense_rank() over (partition by year order by week_date)       as week_year_num
    from date_base
),

final as (
    select
        *,
        'WK' || week_month_rank || '-' || monthf             as weekf,
        'WK' || week_year_num                                as week_year_name,
        dense_rank() over (order by year * 10 + qtr_num)      as qtr_rank_asc,
        dense_rank() over (order by year * 10 + qtr_num desc) as qtr_rank_desc,
        dense_rank() over (order by month_date)               as month_rank_asc,
        dense_rank() over (order by month_date desc)          as month_rank_desc,
        dense_rank() over (order by week_date)                as week_rank_asc,
        dense_rank() over (order by week_date desc)           as week_rank_desc,
        dense_rank() over (order by date)                     as day_rank_asc,
        dense_rank() over (order by date desc)                as day_rank_desc,
        dense_rank() over (order by year)                     as year_rank_asc
    from week_attrs
)

select
    date,
    day_num,
    day_name,
    dayf,
    day_of_week,
    day_rank_asc,
    day_rank_desc,

    week_date,        -- end of week (Sunday)
    week_year_num,    -- week number within the year
    week_year_name,   -- WK1 - WK53
    weekf,            -- e.g. WK1-Jan-26
    week_month_rank,  -- week number within the month (1-6)
    week_rank_asc,    -- rank of week from inception
    week_rank_desc,

    month_date,       -- last day of month
    month_num,
    month_name,
    monthf,
    month_rank_asc,
    month_rank_desc,

    qtr_num,
    qtr_name,
    qtr_rank_asc,
    qtr_rank_desc,

    year,
    year_rank_asc
from final
order by date desc
