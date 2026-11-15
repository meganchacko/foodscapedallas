#!/bin/sh
# Run by the Azure migrate job before each deploy: bring the schema up to date, then (re)grant
# the API's limited role its permissions, so new tables are covered (see app/db/api_role.py).
set -e
alembic upgrade head
python -m app.db.api_role
