import argparse
import csv
import hashlib
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import clickhouse_connect


FIELDS = [
    'transaction_time', 'merch', 'cat_id', 'amount', 'name_1', 'name_2',
    'gender', 'street', 'one_city', 'us_state', 'post_code', 'lat', 'lon',
    'population_city', 'jobs', 'merchant_lat', 'merchant_lon', 'target',
]


def main():
    parser = argparse.ArgumentParser(description='Загрузить исходные CSV в ClickHouse')
    parser.add_argument('files', nargs='+', type=Path)
    args = parser.parse_args()
    client = clickhouse_connect.get_client(host='clickhouse', username='fraud', password='fraud')
    client.command('CREATE DATABASE IF NOT EXISTS transactions_db')
    client.command('DROP TABLE IF EXISTS transactions_db.transactions_loading')
    columns = []
    for name in FIELDS:
        dtype = 'String'
        if name == 'transaction_time':
            dtype = "DateTime('UTC')"
        elif name == 'amount':
            dtype = 'Decimal(18, 2)'
        elif name in ('lat', 'lon', 'merchant_lat', 'merchant_lon'):
            dtype = 'Float64'
        elif name == 'population_city':
            dtype = 'UInt64'
        elif name == 'target':
            dtype = 'Nullable(UInt8)'
        columns.append(f'{name} {dtype}')
    client.command(
        'CREATE TABLE transactions_db.transactions_loading (transaction_id String, '
        + ', '.join(columns) + ') ENGINE = MergeTree ORDER BY (us_state, transaction_time, transaction_id)'
    )
    total = 0
    hashes = set()
    for path in args.files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in hashes:
            raise ValueError('Один файл передан повторно')
        hashes.add(digest)
        batch = []
        with path.open(encoding='utf-8-sig', newline='') as file:
            reader = csv.DictReader(file)
            if set(FIELDS[:-1]) - set(reader.fieldnames or []):
                raise ValueError('В CSV отсутствуют обязательные поля')
            for number, row in enumerate(reader, 1):
                values = dict(row)
                values['transaction_time'] = datetime.fromisoformat(row['transaction_time'])
                values['amount'] = Decimal(row['amount'])
                for name in ('lat', 'lon', 'merchant_lat', 'merchant_lon'):
                    values[name] = float(row[name])
                values['population_city'] = int(row['population_city'])
                values['target'] = int(row['target']) if row.get('target') else None
                if values['target'] not in (None, 0, 1):
                    raise ValueError('Некорректная метка фрода')
                batch.append([f'{digest}:{number}'] + [values[name] for name in FIELDS])
                if len(batch) >= 10000:
                    client.insert('transactions_db.transactions_loading', batch, column_names=['transaction_id'] + FIELDS)
                    total += len(batch)
                    batch.clear()
            if batch:
                client.insert('transactions_db.transactions_loading', batch, column_names=['transaction_id'] + FIELDS)
                total += len(batch)
        print(f'{path.name}: SHA-256 {digest}', flush=True)
    if not total:
        raise ValueError('Нет транзакций')
    exists = client.command('EXISTS TABLE transactions_db.transactions')
    if exists:
        client.command('EXCHANGE TABLES transactions_db.transactions AND transactions_db.transactions_loading')
        client.command('DROP TABLE transactions_db.transactions_loading')
    else:
        client.command('RENAME TABLE transactions_db.transactions_loading TO transactions_db.transactions')
    print(f'Загружено транзакций: {total}')


if __name__ == '__main__':
    main()
