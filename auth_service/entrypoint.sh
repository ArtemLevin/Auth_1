#!/bin/bash
set -e

while ! exec 6<>/dev/tcp/db/5432; do
  echo "Waiting for postgres..."
  sleep 1
done
echo "Postgres is available!"

while ! exec 6<>/dev/tcp/redis/6379; do
  echo "Waiting for redis..."
  sleep 1
done
echo "Redis is available!"

echo "Running migrations..."
alembic -c /app/alembic.ini upgrade head

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
