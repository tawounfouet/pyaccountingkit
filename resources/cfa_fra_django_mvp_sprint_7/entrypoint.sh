#!/bin/sh
set -e

echo "Waiting for database..."
python - <<'PY'
import os
import time

import psycopg

dsn = os.environ.get(
    "DATABASE_URL",
    "postgresql://cfa_fra:cfa_fra@db:5432/cfa_fra",
)

for attempt in range(30):
    try:
        with psycopg.connect(dsn):
            print("Database is ready.")
            break
    except Exception as exc:
        if attempt == 29:
            raise
        print(f"Database not ready ({exc}); retrying...")
        time.sleep(2)
PY

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
