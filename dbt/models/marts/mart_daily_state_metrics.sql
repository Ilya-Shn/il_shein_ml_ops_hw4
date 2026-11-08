select
    transaction_date,
    state,
    count() as transaction_count,
    sum(amount) as total_amount,
    avg(amount) as average_amount,
    quantileExact(0.95) (amount) as p95_amount,
    countIf(amount_bucket = 'LARGE') / count() as large_transaction_share
from {{ ref('stg_transactions') }}
group by transaction_date, state
