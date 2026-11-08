select 'customer' as model_name
from {{ ref('mart_customer_risk_profile') }}
where
    risk_level != case
        when fraud_rate >= 5 then 'HIGH'
        when fraud_rate >= 1 then 'MEDIUM'
        when labeled_count = 0 then 'UNKNOWN'
        else 'LOW'
    end
union all
select 'merchant' as model_name
from {{ ref('mart_merchant_analytics') }}
where is_suspicious != (labeled_count >= 100 and fraud_rate >= 1)
union all
select 'hourly' as model_name
from {{ ref('mart_hourly_fraud_pattern') }}
where is_high_risk_window != (fraud_rate > overall_fraud_rate)
