DBT = docker compose run --rm dbt

.PHONY: up load deps seed run test docs serve lint pre-commit verify all down

up:
	docker compose build dbt
	docker compose up -d --wait clickhouse

load:
	$(DBT) python /work/scripts/load.py /work/data/train.csv /work/data/test.csv

deps:
	$(DBT) dbt deps

seed:
	$(DBT) dbt seed

run:
	$(DBT) dbt run

test:
	mkdir -p results
	$(DBT) sh -c 'dbt test > /work/results/dbt_test.log 2>&1; status=$$?; cat /work/results/dbt_test.log; exit $$status'

docs:
	$(DBT) dbt docs generate

serve:
	docker compose run --rm --service-ports dbt dbt docs serve --host 0.0.0.0 --port 8080 --no-browser

lint:
	$(DBT) sh -c 'cd /work && sqlfluff lint dbt/models dbt/tests dbt/macros'

pre-commit:
	pre-commit run --all-files

verify:
	$(DBT) python /work/scripts/check.py /work/data/train.csv /work/data/test.csv

all:
	$(MAKE) up
	$(MAKE) load
	$(MAKE) deps
	$(MAKE) seed
	$(MAKE) run
	$(MAKE) test
	$(MAKE) lint
	$(MAKE) verify
	$(MAKE) docs

down:
	docker compose down
