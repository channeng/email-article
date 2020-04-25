#!/bin/bash
set -x

PROJECT_DIR=/home/ubuntu/email-article
if [ $(uname) == "Darwin" ]; then
	PROJECT_DIR=$(pwd)
fi

if [ -d $PROJECT_DIR/migrations/ ]; then
	rm -rf $PROJECT_DIR/migrations
fi

if [ -e $PROJECT_DIR/database/app.db ]; then
	sqlite3 $PROJECT_DIR/database/app.db < $PROJECT_DIR/delete_alembic_version.sqlite
fi

if [ $(uname) == "Darwin" ]; then
	flask db init && \
	python $PROJECT_DIR/scripts/sqlite3_migration_fix_alter_table.py && \
	# When developing/debugging, only run `flask db migrate`.
	# Only run `flask db upgrade` after reviewing alembic changes.
	flask db migrate && \
	flask db upgrade
	# flask db migrate
else
	/home/ubuntu/.virtualenvs/env/bin/flask db init && \
	/home/ubuntu/.virtualenvs/env/bin/python $PROJECT_DIR/scripts/sqlite3_migration_fix_alter_table.py && \
	/home/ubuntu/.virtualenvs/env/bin/flask db migrate && \
	/home/ubuntu/.virtualenvs/env/bin/flask db upgrade
	/home/ubuntu/.virtualenvs/env/bin/gunicorn --bind 0.0.0.0:5000 --worker-class gevent --workers 1 main:app
fi
