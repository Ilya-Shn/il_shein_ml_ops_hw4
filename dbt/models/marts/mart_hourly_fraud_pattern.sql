with hourly_metrics as (
    select
        day_of_week,
        transaction_hour,
        {{ fraud_metrics() }}
    from {{ ref('stg_transactions') }}
    group by day_of_week, transaction_hour
),

baseline as (
    select 100.0 * countIf(is_fraud = 1) / nullIf(count(is_fraud), 0) as overall_fraud_rate
    from {{ ref('stg_transactions') }}
)

select
    hourly_metrics.*,
    baseline.overall_fraud_rate,
    hourly_metrics.fraud_rate > baseline.overall_fraud_rate as is_high_risk_window
from hourly_metrics
cross join baseline
