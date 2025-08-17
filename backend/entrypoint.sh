#!/usr/bin/env bash
set -e
echo "Waiting for DB ${MYSQL_HOST:-db}:${MYSQL_PORT:-3306} ..."
until nc -z "${MYSQL_HOST:-db}" "${MYSQL_PORT:-3306}"; do
  sleep 1
done
python manage.py migrate --noinput
exec python manage.py runserver 0.0.0.0:8000
