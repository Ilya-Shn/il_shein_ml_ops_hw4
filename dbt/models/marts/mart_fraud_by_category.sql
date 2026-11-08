select
    category,
    {{ fraud_metrics() }}
from {{ ref('stg_transactions') }}
group by category
