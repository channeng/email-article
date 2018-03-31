#!/bin/bash
if [ -e /home/ubuntu/email-article/database/app.db ] && [ -d /home/ubuntu/email-article/migrations/ ]; then
    /home/ubuntu/.virtualenvs/env/bin/flask db upgrade
elif [ -e /home/ubuntu/email-article/database/app.db ]; then
    /home/ubuntu/.virtualenvs/env/bin/flask db migrate && \
    /home/ubuntu/.virtualenvs/env/bin/flask db upgrade
else
    /home/ubuntu/.virtualenvs/env/bin/flask db init && \
    /home/ubuntu/.virtualenvs/env/bin/flask db migrate && \
    /home/ubuntu/.virtualenvs/env/bin/flask db upgrade
fi

/home/ubuntu/.virtualenvs/env/bin/gunicorn --bind 0.0.0.0:5000 --worker-class eventlet --workers 1 main:app
