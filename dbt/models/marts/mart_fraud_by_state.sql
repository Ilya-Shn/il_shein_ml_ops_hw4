select
    state,
    {{ fraud_metrics() }},
    uniqExact(customer_id) as unique_customers,
    uniqExact(merchant) as unique_merchants
from {{ ref('stg_transactions') }}
group by state
