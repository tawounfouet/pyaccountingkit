.PHONY: up down build logs migrate makemigrations superuser shell test lint format check

up:
	docker compose up -d --build

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f web

migrate:
	docker compose exec web python manage.py migrate

makemigrations:
	docker compose exec web python manage.py makemigrations

superuser:
	docker compose exec web python manage.py createsuperuser

shell:
	docker compose exec web python manage.py shell

test:
	docker compose exec web pytest

lint:
	docker compose exec web ruff check .

format:
	docker compose exec web ruff format .

check:
	docker compose exec web python manage.py check

demo:
	docker compose exec web python manage.py bootstrap_demo

health:
	curl -f http://localhost:8000/health/

validate-structure:
	python scripts/validate_structure.py

accounting-core:
	docker compose exec web python manage.py bootstrap_accounting_core "$(ORG)"

import-fec:
	docker compose exec web python manage.py import_fec "$(FILE)" --organization "$(ORG)" --fiscal-year "$(YEAR)" --username "$(USER)"

import-fec-auto:
	docker compose exec web python manage.py import_fec "$(FILE)" --organization "$(ORG)" --fiscal-year "$(YEAR)" --username "$(USER)" --auto-map --execute

test-reporting:
	docker compose exec web pytest apps/reporting -q

check-reporting:
	docker compose exec web python manage.py check

test-statements:
	docker compose exec web pytest apps/financial_statements -q

bootstrap-statements:
	docker compose exec web python manage.py bootstrap_financial_statements "$(ORG)" --username "$(USER)" --auto-map

test-regulatory:
	docker compose exec web pytest apps/financial_statements/tests/test_sprint7_regulatory_exports.py -q

seed-regulatory:
	docker compose exec web python manage.py seed_regulatory_framework "$(FILE)"
