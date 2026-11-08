with customer_metrics as (
    select
        customer_id,
        min(transaction_time) as first_transaction,
        max(transaction_time) as last_transaction,
        {{ fraud_metrics() }},
        avg(amount) as average_amount
    from {{ ref('stg_transactions') }}
    group by customer_id
)

select
    *,
    case
        when fraud_rate >= 5 then 'HIGH'
        when fraud_rate >= 1 then 'MEDIUM'
        when labeled_count = 0 then 'UNKNOWN'
        else 'LOW'
    end as risk_level
from customer_metrics
