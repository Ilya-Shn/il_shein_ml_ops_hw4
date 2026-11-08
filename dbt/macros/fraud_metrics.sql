{% macro fraud_metrics() -%}
count() as transaction_count,
count(is_fraud) as labeled_count,
countIf(is_fraud = 1) as fraud_count,
100.0 * countIf(is_fraud = 1) / nullIf(count(is_fraud), 0) as fraud_rate,
sum(amount) as total_amount,
sumIf(amount, is_fraud = 1) as fraud_amount
{%- endmacro %}
