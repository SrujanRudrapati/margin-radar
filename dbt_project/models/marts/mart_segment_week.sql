-- Point-in-time weekly segment funnel. Each event counts in its own event week; state columns
-- (awaiting_offer, unsold_inventory_usd) use only dates <= the end of the week. Numerators and
-- denominators only; ratios live in the semantic layer. Zero-filled over 36 segments x n_weeks.
with segments as (
    select
        m.market, b.band, p.product,
        m.market || '-' || b.band || '-' || p.product as segment
    from (values ('M01'), ('M02'), ('M03'), ('M04'), ('M05'), ('M06')) as m(market)
    cross join (values ('B1'), ('B2'), ('B3')) as b(band)
    cross join (values ('cash'), ('CNML')) as p(product)
),

grid as (
    select
        segments.*,
        w.week,
        cast(date '{{ var("start_date") }}' + cast(7 * w.week as integer) as date) as week_start
    from segments
    cross join (select unnest(range({{ var("n_weeks") }})) as week) as w
),

homes as (
    select * from {{ ref('stg_homes') }}
),

offers as (
    select segment, {{ week_index('offer_date') }} as week,
        count(*) as offers, sum(spread_pct) as spread_sum
    from homes group by all
),

contracts as (
    select segment, {{ week_index('contract_date') }} as week, count(*) as contracts
    from homes where contract_date is not null group by all
),

cancellations as (
    select segment, {{ week_index('cancel_date') }} as week,
        count(*) filter (where outcome = 'fell_through') as fell_through,
        count(*) filter (where outcome = 'company_declined') as company_declined
    from homes where cancel_date is not null group by all
),

closes as (
    select segment, {{ week_index('close_date') }} as week,
        count(*) as closes, sum(offer_price) as acquisition_usd, sum(cash_paid_usd) as cash_paid_usd
    from homes where close_date is not null group by all
),

listings as (
    select segment, {{ week_index('list_date') }} as week, count(*) as listed
    from homes where list_date is not null group by all
),

first_offers as (
    select segment, {{ week_index('first_buyer_offer_date') }} as week,
        count(*) as first_offers, sum(days_to_first_offer) as dtfo_sum, sum(showings) as showings_sum
    from homes where first_buyer_offer_date is not null group by all
),

cuts as (
    select homes.segment, {{ week_index('stg_price_cuts.cut_date') }} as week, count(*) as price_cuts
    from {{ ref('stg_price_cuts') }} as stg_price_cuts
    inner join homes using (home_id)
    group by all
),

renos as (
    select segment, {{ week_index('reno_complete_date') }} as week,
        count(*) as renos_completed, sum(reno_estimate_usd) as reno_estimate_sum,
        sum(reno_actual_usd) as reno_actual_sum
    from homes where reno_complete_date is not null group by all
),

resales as (
    select segment, {{ week_index('resale_date') }} as week,
        count(*) as resales, sum(resale_price) as resale_usd,
        sum(model_valuation) as model_valuation_sold_sum, sum(cm_usd) as cm_usd,
        sum(holding_cost_usd) as holding_cost_sum, sum(hold_days) as hold_days_sum,
        sum(cash_paid_usd) as resold_cash_paid_usd
    from homes where resale_date is not null group by all
),

joined as (
    select
        grid.segment, grid.market, grid.band, grid.product, grid.week, grid.week_start,
        coalesce(offers.offers, 0) as offers,
        coalesce(offers.spread_sum, 0) as spread_sum,
        coalesce(contracts.contracts, 0) as contracts,
        coalesce(cancellations.fell_through, 0) as fell_through,
        coalesce(cancellations.company_declined, 0) as company_declined,
        coalesce(closes.closes, 0) as closes,
        coalesce(closes.acquisition_usd, 0) as acquisition_usd,
        coalesce(listings.listed, 0) as listed,
        coalesce(first_offers.first_offers, 0) as first_offers,
        coalesce(first_offers.dtfo_sum, 0) as dtfo_sum,
        coalesce(first_offers.showings_sum, 0) as showings_sum,
        coalesce(cuts.price_cuts, 0) as price_cuts,
        coalesce(renos.renos_completed, 0) as renos_completed,
        coalesce(renos.reno_estimate_sum, 0) as reno_estimate_sum,
        coalesce(renos.reno_actual_sum, 0) as reno_actual_sum,
        coalesce(resales.resales, 0) as resales,
        coalesce(resales.resale_usd, 0) as resale_usd,
        coalesce(resales.model_valuation_sold_sum, 0) as model_valuation_sold_sum,
        coalesce(resales.cm_usd, 0) as cm_usd,
        coalesce(resales.holding_cost_sum, 0) as holding_cost_sum,
        coalesce(resales.hold_days_sum, 0) as hold_days_sum,
        coalesce(closes.cash_paid_usd, 0) - coalesce(resales.resold_cash_paid_usd, 0) as inventory_change_usd
    from grid
    left join offers using (segment, week)
    left join contracts using (segment, week)
    left join cancellations using (segment, week)
    left join closes using (segment, week)
    left join listings using (segment, week)
    left join first_offers using (segment, week)
    left join cuts using (segment, week)
    left join renos using (segment, week)
    left join resales using (segment, week)
),

with_state as (
    select
        *,
        -- listings (and first offers) strictly before this week's start
        coalesce(sum(listed - first_offers) over (
            partition by segment order by week rows between unbounded preceding and 1 preceding), 0
        ) as awaiting_offer,
        sum(inventory_change_usd) over (
            partition by segment order by week rows between unbounded preceding and current row
        ) as unsold_inventory_usd
    from joined
)

select
    segment, market, band, product, week, week_start,
    offers, spread_sum, contracts, fell_through, company_declined, closes, acquisition_usd,
    awaiting_offer, first_offers, dtfo_sum, showings_sum, price_cuts,
    renos_completed, reno_estimate_sum, reno_actual_sum,
    resales, resale_usd, model_valuation_sold_sum, cm_usd, holding_cost_sum, hold_days_sum,
    unsold_inventory_usd
from with_state
