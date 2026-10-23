select
    home_id,
    cut_number,
    cast(cut_date as date) as cut_date,
    cut_pct
from {{ source('raw', 'price_cuts') }}
