{% set marts = ['mart_fraud_by_category', 'mart_fraud_by_state', 'mart_customer_risk_profile',
                'mart_hourly_fraud_pattern', 'mart_merchant_analytics'] %}
with expected as (
    select
        count() as transaction_count,
        count(is_fraud) as labeled_count,
        countIf(is_fraud = 1) as fraud_count,
        sum(amount) as total_amount,
        sumIf(amount, is_fraud = 1) as fraud_amount
    from {{ ref('stg_transactions') }}
)

{% for mart in marts %}
    select '{{ mart }}' as model_name
    from {{ ref(mart) }}
    having
        sum(transaction_count) != (select expected.transaction_count from expected)
        or sum(labeled_count) != (select expected.labeled_count from expected)
        or sum(fraud_count) != (select expected.fraud_count from expected)
        or sum(total_amount) != (select expected.total_amount from expected)
        or sum(fraud_amount) != (select expected.fraud_amount from expected)
    union all
{% endfor %}
select 'mart_daily_state_metrics' as model_name
from {{ ref('mart_daily_state_metrics') }}
having
    sum(transaction_count) != (select expected.transaction_count from expected)
    or sum(total_amount) != (select expected.total_amount from expected)
