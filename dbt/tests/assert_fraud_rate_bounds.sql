{% set marts = ['mart_fraud_by_category', 'mart_fraud_by_state', 'mart_customer_risk_profile',
                'mart_hourly_fraud_pattern', 'mart_merchant_analytics'] %}
{% for mart in marts %}
    select '{{ mart }}' as model_name
    from {{ ref(mart) }}
    where
        fraud_rate < 0 or fraud_rate > 100
        or fraud_count > labeled_count or labeled_count > transaction_count
        or (labeled_count = 0 and fraud_rate is not null)
        or (labeled_count > 0 and fraud_rate is null)
        or abs(fraud_rate - 100.0 * fraud_count / nullIf(labeled_count, 0)) > 0.000001
    {% if not loop.last %}
        union all
    {% endif %}
{% endfor %}
