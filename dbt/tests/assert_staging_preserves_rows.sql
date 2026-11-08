select 1 as mismatch
where
    (select count() from {{ ref('stg_transactions') }})
    != (select count() from {{ source('transactions_db', 'transactions') }})
    or (select count(is_fraud) from {{ ref('stg_transactions') }})
    != (select count(target) from {{ source('transactions_db', 'transactions') }})
