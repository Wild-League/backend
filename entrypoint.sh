#!/bin/sh
set -e
python manage.py migrate --noinput
if [ "$ENV" = "production" ]; then
	exec gunicorn --bind 0.0.0.0:8000 --chdir /app src.wsgi:application
fi

exec gunicorn --reload --bind 0.0.0.0:8000 --chdir /app src.wsgi:application
