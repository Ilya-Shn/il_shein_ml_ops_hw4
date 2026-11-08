with normalized as (
    select
        transaction_id,
        toDateTime(transaction_time) as transaction_time,
        trimBoth(merch) as merchant,
        lowerUTF8(trimBoth(cat_id)) as category,
        toDecimal64(amount, 2) as amount,
        trimBoth(name_1) as first_name,
        trimBoth(name_2) as last_name,
        upperUTF8(trimBoth(gender)) as gender,
        trimBoth(street) as street,
        trimBoth(post_code) as post_code,
        upperUTF8(trimBoth(us_state)) as state,
        toFloat64(lat) as latitude,
        toFloat64(lon) as longitude,
        toFloat64(merchant_lat) as merchant_latitude,
        toFloat64(merchant_lon) as merchant_longitude,
        cast(target, 'Nullable(UInt8)') as is_fraud
    from {{ source('transactions_db', 'transactions') }}
)

select
    *,
    {{ dbt_utils.generate_surrogate_key(['first_name', 'last_name', 'street', 'post_code']) }} as customer_id,
    toDate(transaction_time) as transaction_date,
    toHour(transaction_time) as transaction_hour,
    {{ dbt_date.day_of_week('transaction_time') }} as day_of_week,
    {{ amount_bucket('amount') }} as amount_bucket
from normalized
