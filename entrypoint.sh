#!/usr/bin/env bash
set -e

echo "🚀 Running database migrations..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput

echo "👤 Creating superuser if not exists..."
python manage.py shell < create_superuser.py

echo "🎯 Collecting static files..."
python manage.py collectstatic --noinput

echo "🔥 Starting Gunicorn..."
gunicorn backend.wsgi:application