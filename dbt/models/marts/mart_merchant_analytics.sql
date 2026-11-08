with merchant_metrics as (
    select
        merchant,
        {{ fraud_metrics() }},
        uniqExact(customer_id) as unique_customers
    from {{ ref('stg_transactions') }}
    group by merchant
)

select
    *,
    labeled_count >= 100 and fraud_rate >= 1 as is_suspicious
from merchant_metrics
