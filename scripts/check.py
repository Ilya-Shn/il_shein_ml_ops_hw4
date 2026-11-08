import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import clickhouse_connect


MARTS = {
    'mart_fraud_by_category': ('category',),
    'mart_fraud_by_state': ('state',),
    'mart_customer_risk_profile': ('customer_id',),
    'mart_hourly_fraud_pattern': ('day_of_week', 'transaction_hour'),
    'mart_merchant_analytics': ('merchant',),
}


def aggregate():
    return dict(n=0, labeled=0, fraud=0, total=0, fraud_total=0, large=0, amounts=[], customers=set(), merchants=set(), first=None, last=None)


def close(actual, expected):
    if expected is None:
        assert actual is None, (actual, expected)
    else:
        assert actual is not None and math.isclose(float(actual), float(expected), rel_tol=1e-10, abs_tol=1e-7), (actual, expected)


def main():
    parser = argparse.ArgumentParser(description='Независимо сверить все витрины с исходными CSV')
    parser.add_argument('files', nargs='+', type=Path)
    args = parser.parse_args()
    client = clickhouse_connect.get_client(host='clickhouse', username='fraud', password='fraud')
    groups = {name: defaultdict(aggregate) for name in [*MARTS, 'mart_daily_state_metrics']}
    sources = []
    customer_ids = {}
    rows = client.query('SELECT customer_id, any(first_name), any(last_name), any(street), any(post_code) FROM analytics.stg_transactions GROUP BY customer_id').result_rows
    for cid, *identity in rows:
        key = tuple(identity)
        assert key not in customer_ids, 'Один клиент получил разные ключи'
        customer_ids[key] = cid
    total = labeled = fraud = cents = 0
    for path in args.files:
        count = 0
        with path.open(encoding='utf-8-sig', newline='') as file:
            for row in csv.DictReader(file):
                time = datetime.fromisoformat(row['transaction_time'])
                state = row['us_state'].strip().upper()
                category = row['cat_id'].strip().lower()
                merchant = row['merch'].strip()
                identity = tuple(row[key].strip() for key in ('name_1', 'name_2', 'street', 'post_code'))
                cid = customer_ids[identity]
                amount = int(Decimal(row['amount']) * 100)
                target = int(row['target']) if row.get('target') else None
                count += 1
                total += 1
                cents += amount
                labeled += target is not None
                fraud += target == 1
                keys = {
                    'mart_daily_state_metrics': (time.date(), state),
                    'mart_fraud_by_category': (category,),
                    'mart_fraud_by_state': (state,),
                    'mart_customer_risk_profile': (cid,),
                    'mart_hourly_fraud_pattern': (time.isoweekday(), time.hour),
                    'mart_merchant_analytics': (merchant,),
                }
                for name, key in keys.items():
                    item = groups[name][key]
                    item['n'] += 1
                    item['labeled'] += target is not None
                    item['fraud'] += target == 1
                    item['total'] += amount
                    item['fraud_total'] += amount if target == 1 else 0
                    if name == 'mart_daily_state_metrics':
                        item['amounts'].append(amount)
                        item['large'] += amount >= 100000
                    if name in ('mart_fraud_by_state', 'mart_merchant_analytics'):
                        item['customers'].add(cid)
                        item['merchants'].add(merchant)
                    if name == 'mart_customer_risk_profile':
                        item['first'] = min(item['first'] or time, time)
                        item['last'] = max(item['last'] or time, time)
        sources.append(dict(file=path.name, rows=count, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    raw = client.query('SELECT count(), count(target), countIf(target = 1), sum(amount), uniqExact(transaction_id) FROM transactions_db.transactions').first_row
    assert raw[0:3] == (total, labeled, fraud), raw
    assert raw[3] == Decimal(cents) / 100 and raw[4] == total, raw
    baseline = 100 * fraud / labeled if labeled else None
    counts = {}
    for name, expected in groups.items():
        result = client.query(f'SELECT * FROM analytics.{name}')
        keys = MARTS.get(name, ('transaction_date', 'state'))
        actual = {tuple(row[k] for k in keys): row for row in result.named_results()}
        assert set(actual) == set(expected), name
        assert len(actual) == result.row_count, f'Повторные ключи: {name}'
        for key, item in expected.items():
            row = actual[key]
            assert row['transaction_count'] == item['n'], (name, key)
            assert row['total_amount'] == Decimal(item['total']) / 100, (name, key)
            if name == 'mart_daily_state_metrics':
                close(row['average_amount'], item['total'] / 100 / item['n'])
                amounts = sorted(item['amounts'])
                p95 = amounts[min(int(0.95 * len(amounts)), len(amounts) - 1)]
                close(row['p95_amount'], p95 / 100)
                close(row['large_transaction_share'], item['large'] / item['n'])
                continue
            rate = 100 * item['fraud'] / item['labeled'] if item['labeled'] else None
            assert row['labeled_count'] == item['labeled'], (name, key)
            assert row['fraud_count'] == item['fraud'], (name, key)
            assert row['fraud_amount'] == Decimal(item['fraud_total']) / 100, (name, key)
            close(row['fraud_rate'], rate)
            if 'unique_customers' in row:
                assert row['unique_customers'] == len(item['customers']), (name, key)
            if 'unique_merchants' in row:
                assert row['unique_merchants'] == len(item['merchants']), (name, key)
            if name == 'mart_customer_risk_profile':
                risk = 'UNKNOWN' if rate is None else 'HIGH' if rate >= 5 else 'MEDIUM' if rate >= 1 else 'LOW'
                assert row['risk_level'] == risk, key
                assert row['first_transaction'].replace(tzinfo=None) == item['first'], key
                assert row['last_transaction'].replace(tzinfo=None) == item['last'], key
                close(row['average_amount'], item['total'] / 100 / item['n'])
            if name == 'mart_merchant_analytics':
                assert row['is_suspicious'] == (item['labeled'] >= 100 and rate is not None and rate >= 1), key
            if name == 'mart_hourly_fraud_pattern':
                close(row['overall_fraud_rate'], baseline)
                flag = rate > baseline if rate is not None and baseline is not None else None
                assert row['is_high_risk_window'] == flag, key
        counts[name] = len(actual)
        print(f'{name}: сверены все поля, строк {len(actual)}', flush=True)
    report = dict(source='https://www.kaggle.com/competitions/teta-ml-1-2025/data', files=sources, transactions=total, labeled=labeled, fraud=fraud, total_amount=str(Decimal(cents) / 100), mart_rows=counts, status='Все витрины совпали с независимым расчётом по CSV')
    Path('/work/results/check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
