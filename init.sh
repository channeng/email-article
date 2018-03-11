#!/bin/bash
# export FLASK_APP=/path/to/Personal/email-article/main.py

# Generate migration script (or create new tables)
flask db init

# On the first migration
flask db migrate

# Apply changes from generated migration script to database
flask db upgrade
