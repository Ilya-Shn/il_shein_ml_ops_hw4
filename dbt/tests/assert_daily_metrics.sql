select
    transaction_date,
    state
from {{ ref('mart_daily_state_metrics') }}
where
    transaction_count = 0
    or total_amount < 0
    or average_amount < 0
    or p95_amount < 0
    or large_transaction_share < 0 or large_transaction_share > 1
    or abs(average_amount - toFloat64(total_amount) / transaction_count) > 0.000001
