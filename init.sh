#!/bin/bash
if [ -d /home/ubuntu/email-article/migrations/ ]; then
	rm -rf /home/ubuntu/email-article/migrations
fi

if [ -e /home/ubuntu/email-article/database/app.db ]; then
	sqlite3 /home/ubuntu/email-article/database/app.db < /home/ubuntu/email-article/delete_alembic_version.sqlite
fi

/home/ubuntu/.virtualenvs/env/bin/flask db init && \
/home/ubuntu/.virtualenvs/env/bin/flask db migrate && \
/home/ubuntu/.virtualenvs/env/bin/flask db upgrade

/home/ubuntu/.virtualenvs/env/bin/gunicorn --bind 0.0.0.0:5000 --worker-class eventlet --workers 1 main:app
